"""Transactional finalization and cached CSV protocol coverage (#67)."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from vault_cleaner import cli
from vault_cleaner.report_run import run_report
from vault_cleaner.review import OverridesError, save_overrides
from vault_cleaner.review_session import OverrideStore, Veto
from vault_cleaner.server import app as server_app
from vault_cleaner.server.app import create_app
from vault_cleaner.server.session import Session

ORIGIN = "http://127.0.0.1:43123"
FIXTURE = Path(__file__).parent / "fixtures" / "armor.csv"


@pytest.fixture
def client_session(tmp_path):
    overrides = tmp_path / "overrides.json"
    session = Session(
        overrides_path=str(overrides),
        config_path="config.toml",
        no_wishlists=True,
        bootstrap_token="bootstrap",
        session_token="session",
    )
    session.configure_bound_port(43123)
    app = create_app(session)
    app.config["TESTING"] = True
    client = app.test_client()
    assert client.get("/bootstrap?token=bootstrap", base_url=ORIGIN).status_code == 303
    try:
        yield client, session, overrides
    finally:
        session.close()


def upload(client):
    body = FIXTURE.read_bytes()
    return client.post(
        "/api/exports/armor",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(body)),
        },
        data=body,
    )


def finalize_payload(metadata, **overrides):
    payload = {
        "report_revision": metadata["report_revision"],
        "verdict_revision": metadata["verdict_revision"],
        "fingerprint": metadata["fingerprint"],
    }
    payload.update(overrides)
    return payload


def finalize(client, metadata, **overrides):
    return client.post(
        "/api/finalize",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=finalize_payload(metadata, **overrides),
    )


def build_client(tmp_path, *, overrides_bytes=None, once=False):
    overrides = tmp_path / "overrides.json"
    if overrides_bytes is not None:
        overrides.write_bytes(overrides_bytes)
    session = Session(
        overrides_path=str(overrides),
        config_path="nonexistent.toml",
        no_wishlists=True,
        bootstrap_token="bootstrap",
        session_token="session",
    )
    session.configure_bound_port(43123)
    app = create_app(session, once=once)
    app.config["TESTING"] = True
    client = app.test_client()
    assert client.get("/bootstrap?token=bootstrap", base_url=ORIGIN).status_code == 303
    return client, session, overrides


def upload_all(client):
    for kind, filename in (
        ("weapons", "weapons_dupes.csv"),
        ("armor", "armor.csv"),
        ("ghosts", "ghosts_cleanup.csv"),
    ):
        body = (FIXTURE.parent / filename).read_bytes()
        response = client.post(
            f"/api/exports/{kind}",
            base_url=ORIGIN,
            headers={
                "Origin": ORIGIN,
                "Content-Type": "text/csv",
                "Content-Length": str(len(body)),
            },
            data=body,
        )
        assert response.status_code == 200
    return response


def cli_args(command, output, overrides, *, manifest=None):
    args = [
        command,
        "--weapons", str(FIXTURE.parent / "weapons_dupes.csv"),
        "--armor", str(FIXTURE.parent / "armor.csv"),
        "--ghosts", str(FIXTURE.parent / "ghosts_cleanup.csv"),
        "--no-wishlists",
        "--config", "nonexistent.toml",
        "--overrides", str(overrides),
        "--output", str(output),
        "--write",
    ]
    if manifest is not None:
        args[1:1] = ["--manifest", str(manifest)]
    return args


def report_for_parity():
    return run_report(
        config_path="nonexistent.toml",
        weapons_path=FIXTURE.parent / "weapons_dupes.csv",
        armor_path=FIXTURE.parent / "armor.csv",
        ghosts_path=FIXTURE.parent / "ghosts_cleanup.csv",
        no_wishlists=True,
    )


def test_finalize_caches_bytes_and_uses_one_response_contract(client_session):
    client, session, overrides = client_session
    uploaded = upload(client)
    assert uploaded.status_code == 200

    first = finalize(client, uploaded.json)
    assert first.status_code == 200
    assert first.content_type == "text/csv; charset=utf-8"
    assert first.headers["Content-Disposition"] == 'attachment; filename="dim-import.csv"'
    assert first.headers["Vault-Cleaner-Report-Revision"] == "1"
    assert first.headers["Vault-Cleaner-Verdict-Revision"] == "0"
    assert first.headers["Vault-Cleaner-Approved-Still-Vetoed"] == "0"
    first_bytes = first.data
    persisted = overrides.read_bytes()

    retry = finalize(client, uploaded.json)
    downloaded = client.get("/api/finalized.csv", base_url=ORIGIN)
    assert retry.status_code == downloaded.status_code == 200
    assert retry.data == downloaded.data == first_bytes
    for response in (first, retry, downloaded):
        assert response.headers["Content-Disposition"] == 'attachment; filename="dim-import.csv"'
        assert response.headers["Vault-Cleaner-Report-Revision"] == "1"
        assert response.headers["Vault-Cleaner-Verdict-Revision"] == "0"
        assert response.headers["Vault-Cleaner-Approved-Still-Vetoed"] == "0"
    assert overrides.read_bytes() == persisted
    assert session.state == "finalized"
    assert session.finalized_csv_bytes == first_bytes

    # Finalized sessions remain reportable but all live mutations are refused.
    assert client.get("/api/report", base_url=ORIGIN).json["state"] == "finalized"


@pytest.mark.parametrize(
    ("kind", "filename"),
    [
        ("weapons", "weapons_dupes.csv"),
        ("armor", "armor.csv"),
        ("ghosts", "ghosts_cleanup.csv"),
    ],
)
def test_upload_mutation_is_rejected_for_every_kind_after_finalization(
    client_session, kind, filename
):
    client, session, _overrides = client_session
    uploaded = upload(client)
    completed = finalize(client, uploaded.json)
    assert completed.status_code == 200

    body = (FIXTURE.parent / filename).read_bytes()
    refused = client.post(
        f"/api/exports/{kind}",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(body)),
        },
        data=body,
    )
    assert refused.status_code == 409
    assert refused.json["error"]["code"] == "illegal_state"
    assert session.state == "finalized"


def test_finalize_rejects_closed_session_before_body_validation(client_session):
    client, session, _overrides = client_session
    session.close()

    response = client.post(
        "/api/finalize",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        data=b"not-json",
    )

    assert response.status_code == 409
    assert response.json["error"]["code"] == "illegal_state"
    assert response.json["error"]["message"] == (
        "finalize is not available after session shutdown"
    )


def test_once_finalize_shuts_down_only_after_successful_response_close(tmp_path):
    client, session, _overrides = build_client(tmp_path, once=True)
    callbacks = []
    session.shutdown_callback = lambda: callbacks.append("shutdown")
    try:
        uploaded = upload(client)
        response = finalize(client, uploaded.json)
        assert response.status_code == 200
        assert response.headers["Vault-Cleaner-Serve-Once"] == "true"
        assert callbacks == []
        assert session.state == "finalized"
        response.close()
        assert callbacks == ["shutdown"]
        assert session.state == "closed"
    finally:
        session.close()


def test_finalized_csv_rejects_closed_once_session_with_terminal_message(tmp_path):
    client, session, _overrides = build_client(tmp_path, once=True)
    try:
        uploaded = upload(client)
        response = finalize(client, uploaded.json)
        assert response.status_code == 200
        response.close()
        assert session.closed

        unavailable = client.get("/api/finalized.csv", base_url=ORIGIN)
        assert unavailable.status_code == 409
        assert unavailable.json["error"] == {
            "code": "illegal_state",
            "message": "finalized CSV is not available after session shutdown",
        }
    finally:
        session.close()


def test_once_failed_finalize_does_not_schedule_shutdown(tmp_path, monkeypatch):
    client, session, _overrides = build_client(tmp_path, once=True)
    callbacks = []
    session.shutdown_callback = lambda: callbacks.append("shutdown")

    def fail(_rows):
        raise RuntimeError("render failed")

    monkeypatch.setattr(server_app, "render_import_csv", fail)
    try:
        uploaded = upload(client)
        response = finalize(client, uploaded.json)
        assert response.status_code == 500
        response.close()
        assert callbacks == []
        assert session.state == "exports-loaded"
    finally:
        session.close()


def test_once_idempotent_retry_after_response_failure_schedules_shutdown(
    tmp_path, monkeypatch
):
    client, session, _overrides = build_client(tmp_path, once=True)
    callbacks = []
    session.shutdown_callback = lambda: callbacks.append("shutdown")
    original = server_app._finalized_csv_response
    failed = True

    def fail_once(target):
        nonlocal failed
        if failed:
            failed = False
            raise RuntimeError("response construction failed")
        return original(target)

    monkeypatch.setattr(server_app, "_finalized_csv_response", fail_once)
    try:
        uploaded = upload(client)
        first = finalize(client, uploaded.json)
        assert first.status_code == 500
        assert session.state == "finalized"
        assert callbacks == []
        monkeypatch.setattr(server_app, "_finalized_csv_response", original)
        retry = finalize(client, uploaded.json)
        assert retry.status_code == 200
        assert callbacks == []
        retry.close()
        assert callbacks == ["shutdown"]
    finally:
        session.close()


def test_server_csv_matches_cli_report_write_byte_for_byte(tmp_path):
    client, session, _overrides = build_client(tmp_path)
    try:
        uploaded = upload_all(client)
        server_response = finalize(client, uploaded.json)
        cli_output = tmp_path / "cli-report.csv"
        cli_overrides = tmp_path / "cli-overrides.json"
        assert cli.main(cli_args("report", cli_output, cli_overrides)) == 0
        assert server_response.data == cli_output.read_bytes()
    finally:
        session.close()


def test_server_csv_matches_cli_review_write_with_existing_vetoes(tmp_path):
    report = report_for_parity()
    decision = report.sections[0].decisions[0]
    veto = Veto(
        id=decision.id,
        kind=decision.kind,
        hash=decision.hash,
        name=decision.name,
        action=decision.action,
        reason=decision.reason,
        fingerprint=report.fingerprint,
        recorded_at="2026-08-25T00:00:00Z",
    )
    source_overrides = tmp_path / "source-overrides.json"
    save_overrides(OverrideStore(schema_version=1, vetoes=(veto,)), source_overrides)
    client, session, _overrides = build_client(
        tmp_path,
        overrides_bytes=source_overrides.read_bytes(),
    )
    try:
        uploaded = upload_all(client)
        server_response = finalize(client, uploaded.json)
        cli_output = tmp_path / "cli-review.csv"
        cli_overrides = tmp_path / "cli-review-overrides.json"
        cli_overrides.write_bytes(source_overrides.read_bytes())
        assert cli.main(cli_args("review", cli_output, cli_overrides)) == 0
        assert server_response.data == cli_output.read_bytes()
    finally:
        session.close()


def test_server_csv_matches_cli_review_manifest_write_byte_for_byte(tmp_path):
    report = report_for_parity()
    selected = list(report.sections[0].decisions[:3])
    manifest = tmp_path / "review-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-08-25T00:00:00Z",
                "snapshot": {
                    "schema_version": 1,
                    "ruleset_version": 1,
                    "fingerprint": report.fingerprint,
                },
                "decisions": [
                    {
                        "id": decision.id,
                        "kind": decision.kind,
                        "hash": decision.hash,
                        "name": decision.name,
                        "action": decision.action,
                        "reason": decision.reason,
                        "verdict": "vetoed" if index < 2 else "approved",
                    }
                    for index, decision in enumerate(selected)
                ],
            }
        ),
        encoding="utf-8",
    )
    client, session, _overrides = build_client(tmp_path)
    try:
        uploaded = upload_all(client)
        selected_verdicts = [
            {"id": decision.id, "verdict": "vetoed" if index < 2 else "approved"}
            for index, decision in enumerate(selected)
        ]
        reviewed = client.post(
            "/api/verdicts",
            base_url=ORIGIN,
            headers={"Origin": ORIGIN},
            json={
                "report_revision": uploaded.json["report_revision"],
                "verdict_revision": uploaded.json["verdict_revision"],
                "fingerprint": uploaded.json["fingerprint"],
                "decisions": selected_verdicts,
            },
        )
        assert reviewed.status_code == 200
        server_response = finalize(client, reviewed.json)
        cli_output = tmp_path / "cli-manifest-review.csv"
        cli_overrides = tmp_path / "cli-manifest-overrides.json"
        assert cli.main(
            cli_args("review", cli_output, cli_overrides, manifest=manifest)
        ) == 0
        assert server_response.data == cli_output.read_bytes()
    finally:
        session.close()


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        {"report_revision": 1, "verdict_revision": 0, "fingerprint": "x", "extra": 1},
        {"report_revision": True, "verdict_revision": 0, "fingerprint": "x"},
        {"report_revision": 1, "verdict_revision": 0},
        {"report_revision": 1.0, "verdict_revision": 0, "fingerprint": "x"},
        {"report_revision": 1, "verdict_revision": 0, "fingerprint": 1},
    ],
)
def test_finalize_validation_is_strict_and_non_mutating(client_session, payload):
    client, session, _overrides = client_session
    _uploaded = upload(client)
    before = (session.state, session.report_revision, session.verdict_revision, deepcopy(session.verdicts))
    response = client.post(
        "/api/finalize",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        data=payload if isinstance(payload, bytes) else None,
        json=payload if isinstance(payload, dict) else None,
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "bad_request"
    assert (session.state, session.report_revision, session.verdict_revision, session.verdicts) == before


def test_finalize_rejects_stale_report_fingerprint_and_verdict_without_mutation(
    client_session,
):
    client, session, _overrides = client_session
    uploaded = upload(client)
    before = (session.state, session.report_revision, session.verdict_revision, session.override_store)
    stale_report = finalize(client, uploaded.json, report_revision=0)
    assert stale_report.status_code == 409
    assert stale_report.json["error"]["code"] == "stale_report"
    stale_fingerprint = finalize(client, uploaded.json, fingerprint="0" * 64)
    assert stale_fingerprint.status_code == 409
    assert stale_fingerprint.json["error"]["code"] == "stale_report"
    proposal = uploaded.json["snapshot"]["sections"][0]["decisions"][0]
    reviewed = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": uploaded.json["report_revision"],
            "verdict_revision": uploaded.json["verdict_revision"],
            "fingerprint": uploaded.json["fingerprint"],
            "decisions": [{"id": proposal["id"], "verdict": "vetoed"}],
        },
    )
    assert reviewed.status_code == 200
    before_stale_verdict = (
        session.state,
        session.report_revision,
        session.verdict_revision,
        deepcopy(session.verdicts),
        session.override_store,
    )
    stale_verdict = finalize(client, reviewed.json, verdict_revision=0)
    assert stale_verdict.status_code == 409
    assert stale_verdict.json["error"]["code"] == "stale_verdicts"
    assert (
        session.state,
        session.report_revision,
        session.verdict_revision,
        session.verdicts,
        session.override_store,
    ) == before_stale_verdict
    assert before[0] == "exports-loaded"


def test_session_veto_suppresses_only_that_row_and_unreviewed_proposals_remain(
    client_session,
):
    client, session, _overrides = client_session
    uploaded = upload(client)
    proposals = uploaded.json["snapshot"]["sections"][0]["decisions"]
    vetoed_id = proposals[0]["id"]
    retained_id = proposals[1]["id"]
    reviewed = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": uploaded.json["report_revision"],
            "verdict_revision": uploaded.json["verdict_revision"],
            "fingerprint": uploaded.json["fingerprint"],
            "decisions": [{"id": vetoed_id, "verdict": "vetoed"}],
        },
    )
    assert reviewed.status_code == 200
    response = finalize(client, reviewed.json)
    assert response.status_code == 200
    assert f'"""{vetoed_id}"""'.encode() not in response.data
    assert f'"""{retained_id}"""'.encode() in response.data
    assert session.state == "finalized"


def test_finalize_refuses_initially_missing_override_file_created(client_session):
    client, session, overrides = client_session
    uploaded = upload(client)
    before_store = session.override_store
    before_digest = session.override_digest
    external = b'{"schema_version":1,"vetoes":[]}\n'
    overrides.write_bytes(external)
    before = session.state
    response = finalize(client, uploaded.json)
    assert response.status_code == 409
    assert response.json["error"]["code"] == "overrides_changed"
    assert session.state == before == "exports-loaded"
    assert session.finalized_csv_bytes is None
    assert session.override_store == before_store
    assert session.override_digest == before_digest
    assert overrides.read_bytes() == external


def test_finalize_refuses_changed_existing_override_file(tmp_path):
    original = b'{"schema_version":1,"vetoes":[]}\n'
    external = b'{ "schema_version": 1, "vetoes": [] }\n'
    client, session, overrides = build_client(tmp_path, overrides_bytes=original)
    try:
        uploaded = upload(client)
        before_store = session.override_store
        before_digest = session.override_digest
        overrides.write_bytes(external)
        response = finalize(client, uploaded.json)
        assert response.status_code == 409
        assert response.json["error"]["code"] == "overrides_changed"
        assert overrides.read_bytes() == external
        assert session.state == "exports-loaded"
        assert session.override_store == before_store
        assert session.override_digest == before_digest
    finally:
        session.close()


def test_finalize_refuses_deletion_of_an_existing_override_file(tmp_path):
    overrides = tmp_path / "overrides.json"
    overrides.write_bytes(b'{"schema_version":1,"vetoes":[]}\n')
    session = Session(
        overrides_path=str(overrides),
        config_path="config.toml",
        no_wishlists=True,
        bootstrap_token="bootstrap",
        session_token="session",
    )
    session.configure_bound_port(43123)
    app = create_app(session)
    app.config["TESTING"] = True
    client = app.test_client()
    try:
        assert client.get("/bootstrap?token=bootstrap", base_url=ORIGIN).status_code == 303
        uploaded = upload(client)
        before_store = session.override_store
        before_digest = session.override_digest
        overrides.unlink()
        response = finalize(client, uploaded.json)
        assert response.status_code == 409
        assert response.json["error"]["code"] == "overrides_changed"
        assert session.state == "exports-loaded"
        assert session.override_store == before_store
        assert session.override_digest == before_digest
    finally:
        session.close()


def test_persisted_veto_and_session_approval_conflict_stays_suppressed(
    client_session,
):
    client, session, overrides = client_session
    uploaded = upload(client)
    proposal = uploaded.json["snapshot"]["sections"][0]["decisions"][0]
    veto = Veto(
        id=proposal["id"],
        kind=proposal["kind"],
        hash=proposal["hash"],
        name=proposal["name"],
        action=proposal["action"],
        reason=proposal["reason"],
        fingerprint=uploaded.json["fingerprint"],
        recorded_at="2026-08-25T00:00:00Z",
    )
    store = OverrideStore(schema_version=1, vetoes=(veto,))
    save_overrides(store, overrides)
    session.override_store = store
    session.override_digest = hashlib.sha256(overrides.read_bytes()).hexdigest()
    reviewed = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": 1,
            "verdict_revision": 0,
            "fingerprint": uploaded.json["fingerprint"],
            "decisions": [{"id": proposal["id"], "verdict": "approved"}],
        },
    )
    assert reviewed.status_code == 200
    response = finalize(client, reviewed.json)
    assert response.status_code == 200
    assert response.headers["Vault-Cleaner-Approved-Still-Vetoed"] == "1"
    assert f'"""{proposal["id"]}"""'.encode() not in response.data


def test_reset_invalid_override_refresh_preserves_the_live_review(client_session):
    client, session, overrides = client_session
    upload(client)
    before = (session.state, session.report_revision, session.verdict_revision, session.staging_dir)
    overrides.write_bytes(b"not-json")
    response = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={"report_revision": 1, "verdict_revision": 0},
    )
    assert response.status_code == 500
    assert response.json["error"]["code"] == "internal_error"
    assert str(overrides) not in response.get_data(as_text=True)
    assert (session.state, session.report_revision, session.verdict_revision, session.staging_dir) == before


def test_reset_refreshes_drifted_baseline_and_allows_a_new_review(client_session):
    client, session, overrides = client_session
    uploaded = upload(client)
    overrides.write_bytes(b'{"schema_version":1,"vetoes":[]}\n')
    refused = finalize(client, uploaded.json)
    assert refused.status_code == 409

    reset = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={"report_revision": 1, "verdict_revision": 0},
    )
    assert reset.status_code == 200
    assert session.state == "idle"
    uploaded_again = upload(client)
    assert uploaded_again.status_code == 200
    completed = finalize(client, uploaded_again.json)
    assert completed.status_code == 200
    assert session.state == "finalized"


def test_reset_clears_finalized_cache_and_finalized_route_after_success(client_session):
    client, session, _overrides = client_session
    uploaded = upload(client)
    completed = finalize(client, uploaded.json)
    assert completed.status_code == 200
    reset = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": uploaded.json["report_revision"],
            "verdict_revision": uploaded.json["verdict_revision"],
        },
    )
    assert reset.status_code == 200
    assert session.state == "idle"
    assert session.finalized_csv_bytes is None
    unavailable = client.get("/api/finalized.csv", base_url=ORIGIN)
    assert unavailable.status_code == 409
    assert unavailable.json["error"]["code"] == "illegal_state"


def test_post_finalize_external_edit_does_not_change_cache_and_reset_adopts_it(
    client_session,
):
    client, session, overrides = client_session
    uploaded = upload(client)
    completed = finalize(client, uploaded.json)
    cached = completed.data
    external = b'{"schema_version":1,"vetoes":[]}\n'
    overrides.write_bytes(external)
    downloaded = client.get("/api/finalized.csv", base_url=ORIGIN)
    assert downloaded.status_code == 200
    assert downloaded.data == cached
    assert session.state == "finalized"
    reset = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": uploaded.json["report_revision"],
            "verdict_revision": uploaded.json["verdict_revision"],
        },
    )
    assert reset.status_code == 200
    assert session.override_store == OverrideStore(schema_version=1, vetoes=())
    assert session.override_digest == hashlib.sha256(external).hexdigest()


def test_verdict_mutation_is_rejected_after_finalization(client_session):
    client, session, _overrides = client_session
    uploaded = upload(client)
    completed = finalize(client, uploaded.json)
    proposal = uploaded.json["snapshot"]["sections"][0]["decisions"][0]
    refused = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": completed.headers["Vault-Cleaner-Report-Revision"],
            "verdict_revision": completed.headers["Vault-Cleaner-Verdict-Revision"],
            "fingerprint": uploaded.json["fingerprint"],
            "decisions": [{"id": proposal["id"], "verdict": "vetoed"}],
        },
    )
    assert refused.status_code == 409
    assert refused.json["error"]["code"] == "illegal_state"
    assert session.state == "finalized"


def test_render_failure_happens_before_persistence(client_session, monkeypatch):
    client, session, overrides = client_session
    uploaded = upload(client)
    injected = str(session.staging_dir)

    def fail(_rows):
        raise RuntimeError(f"render failed at {injected}")

    monkeypatch.setattr(server_app, "render_import_csv", fail)
    response = finalize(client, uploaded.json)
    assert response.status_code == 500
    assert response.json["error"]["code"] == "internal_error"
    assert session.state == "exports-loaded"
    assert session.finalized_csv_bytes is None
    assert not overrides.exists()
    assert injected not in response.get_data(as_text=True)
    assert str(overrides) not in response.get_data(as_text=True)


def test_upload_report_failure_body_redacts_staging_and_override_paths(
    client_session, monkeypatch, tmp_path
):
    client, session, overrides = client_session
    injected = tmp_path / "injected-report-path"

    def fail(**_kwargs):
        raise RuntimeError(f"report failed at {injected}")

    monkeypatch.setattr(server_app, "run_report", fail)
    body = FIXTURE.read_bytes()
    response = client.post(
        "/api/exports/armor",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(body)),
        },
        data=body,
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 500
    assert str(injected) not in text
    assert str(overrides) not in text
    assert session.staging_dir is None


def test_upload_staging_failure_body_redacts_temp_and_override_paths(
    client_session, monkeypatch, tmp_path
):
    client, session, overrides = client_session
    injected = tmp_path / "injected-staging-path"
    real_tempfile = server_app.tempfile

    class FailingTempfile:
        def mkdtemp(self, **_kwargs):
            raise OSError(f"cannot allocate {injected}")

        def __getattr__(self, name):
            return getattr(real_tempfile, name)

    monkeypatch.setattr(server_app, "tempfile", FailingTempfile())
    body = FIXTURE.read_bytes()
    response = client.post(
        "/api/exports/armor",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(body)),
        },
        data=body,
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 500
    assert str(injected) not in text
    assert str(overrides) not in text
    assert session.staging_dir is None


def test_persistence_failure_happens_before_session_commit(client_session, monkeypatch):
    client, session, overrides = client_session
    uploaded = upload(client)

    def fail(*_args, **_kwargs):
        raise OSError(f"write failed at {overrides}")

    monkeypatch.setattr(server_app, "save_overrides", fail)
    response = finalize(client, uploaded.json)
    assert response.status_code == 500
    assert session.state == "exports-loaded"
    assert session.finalized_csv_bytes is None
    assert not overrides.exists()
    assert str(overrides) not in response.get_data(as_text=True)


def test_post_commit_response_failure_leaves_recoverable_finalized_state(
    client_session, monkeypatch
):
    client, session, overrides = client_session
    uploaded = upload(client)
    original = server_app._finalized_csv_response
    failed = True

    def fail_once(target):
        nonlocal failed
        if failed:
            failed = False
            raise RuntimeError("response construction failed")
        return original(target)

    monkeypatch.setattr(server_app, "_finalized_csv_response", fail_once)
    failed_response = finalize(client, uploaded.json)
    assert failed_response.status_code == 500
    assert session.state == "finalized"
    assert session.finalized_csv_bytes is not None
    assert overrides.exists()

    monkeypatch.setattr(server_app, "_finalized_csv_response", original)
    recovered = client.get("/api/finalized.csv", base_url=ORIGIN)
    assert recovered.status_code == 200
    assert recovered.data == session.finalized_csv_bytes


def test_finalize_failure_bodies_do_not_leak_filesystem_paths(client_session, monkeypatch):
    client, session, overrides = client_session
    uploaded = upload(client)
    injected = str(overrides)

    def fail():
        raise OverridesError(f"could not read {injected}")

    monkeypatch.setattr(session, "read_override_digest", fail)
    response = finalize(client, uploaded.json)
    assert response.status_code == 500
    assert injected not in response.get_data(as_text=True)
    assert str(session.staging_dir) not in response.get_data(as_text=True)


def test_report_route_failure_body_redacts_session_paths(client_session, monkeypatch):
    client, session, overrides = client_session
    upload(client)
    injected = str(session.staging_dir)
    original = server_app.session_metadata

    def fail(_session):
        raise RuntimeError(f"report serialization failed at {injected}")

    monkeypatch.setattr(server_app, "session_metadata", fail)
    response = client.get("/api/report", base_url=ORIGIN)
    assert response.status_code == 500
    text = response.get_data(as_text=True)
    assert injected not in text
    assert str(overrides) not in text
    monkeypatch.setattr(server_app, "session_metadata", original)
    assert session.state == "exports-loaded"
