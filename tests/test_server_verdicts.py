"""Verdict, stale-client, reconciliation, and reset protocol coverage."""

from __future__ import annotations

import http.client
import json
import threading
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from flask import request

from vault_cleaner.server import app as server_app
from vault_cleaner.server.app import (
    _validate_verdict_payload_data,
    build_server,
    create_app,
)
from vault_cleaner.server.errors import ApiError
from vault_cleaner.server.session import Session, session_metadata

ORIGIN = "http://127.0.0.1:43123"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client_session(tmp_path):
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_bytes(b'{"schema_version":1,"vetoes":[]}\n')
    session = Session(
        overrides_path=str(overrides_path),
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
        yield client, session
    finally:
        session.close()


def upload_armor(client):
    body = (FIXTURES / "armor.csv").read_bytes()
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


def replace_report(
    monkeypatch, session, *, decision_changes=None, drop_first=False, drop_count=1
):
    old_run = session.report
    assert old_run is not None
    sections = list(old_run.sections)
    section = sections[0]
    decisions = list(section.decisions)
    if drop_first:
        decisions = decisions[drop_count:]
    if decision_changes:
        index, changes = decision_changes
        decisions[index] = replace(decisions[index], **changes)
    sections[0] = replace(section, decisions=tuple(decisions))
    candidate = replace(
        old_run,
        sections=tuple(sections),
        fingerprint=old_run.fingerprint + "-replacement",
    )
    monkeypatch.setattr(server_app, "run_report", lambda **_kwargs: candidate)
    return candidate


def verdict_payload(metadata, decisions, *, report_revision=None, verdict_revision=None):
    return {
        "report_revision": metadata["report_revision"]
        if report_revision is None
        else report_revision,
        "verdict_revision": metadata["verdict_revision"]
        if verdict_revision is None
        else verdict_revision,
        "fingerprint": metadata["fingerprint"],
        "decisions": decisions,
    }


def post_verdict(client, metadata, decisions, **revisions):
    return client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=verdict_payload(metadata, decisions, **revisions),
    )


def test_verdict_batch_is_atomic_and_ordered(client_session):
    client, session = client_session
    uploaded = upload_armor(client)
    assert uploaded.status_code == 200
    metadata = uploaded.json
    proposals = metadata["snapshot"]["sections"][0]["decisions"]
    decisions = [
        {"id": proposals[2]["id"], "verdict": "vetoed"},
        {"id": proposals[0]["id"], "verdict": "approved"},
    ]
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=verdict_payload(metadata, decisions),
    )
    assert response.status_code == 200
    assert response.json["state"] == "reviewing"
    assert response.json["verdict_revision"] == 1
    assert [entry["id"] for entry in response.json["verdicts"]] == [
        proposals[0]["id"],
        proposals[2]["id"],
    ]

    before = deepcopy(session.verdicts)
    bad = decisions + [{"id": "99999999999999999999", "verdict": "vetoed"}]
    failed = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=verdict_payload(response.json, bad),
    )
    assert failed.status_code == 400
    assert failed.json["error"]["code"] == "bad_request"
    assert session.verdicts == before
    assert session.verdict_revision == 1


def test_report_present_metadata_verdicts_are_deep_copies(client_session):
    client, session = client_session
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    accepted = post_verdict(
        client, metadata, [{"id": proposal["id"], "verdict": "vetoed"}]
    )
    assert accepted.status_code == 200
    returned = session_metadata(session)
    returned["verdicts"][0]["verdict"] = "approved"
    assert session.verdicts == [{"id": proposal["id"], "verdict": "vetoed"}]


@pytest.mark.parametrize(
    "decision",
    [
        {"id": 4001, "verdict": "vetoed"},
        {"id": "4001", "verdict": "vetoed", "extra": 1},
    ],
)
def test_verdict_entries_are_strict(client_session, decision):
    client, _session = client_session
    metadata = upload_armor(client).json
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=verdict_payload(metadata, [decision]),
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "bad_request"


@pytest.mark.parametrize("verdict", [1, True, "maybe"])
def test_valid_id_rejects_unknown_numeric_and_boolean_verdicts(
    client_session, verdict
):
    client, _session = client_session
    metadata = upload_armor(client).json
    item_id = metadata["snapshot"]["sections"][0]["decisions"][0]["id"]
    response = post_verdict(
        client, metadata, [{"id": item_id, "verdict": verdict}]
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "payload_change",
    [
        lambda payload: payload.update(extra=True),
        lambda payload: payload.update(decisions={}),
        lambda payload: payload.update(decisions=["not-an-object"]),
        lambda payload: payload.update(
            decisions=[{"id": "not-a-dim-id", "verdict": "vetoed"}]
        ),
        lambda payload: payload.update(
            decisions=[{"id": "4051", "verdict": "vetoed"}, {"id": "4051", "verdict": "approved"}]
        ),
        lambda payload: payload.update(
            decisions=[{"id": "99999999999999999999", "verdict": "vetoed"}]
        ),
        lambda payload: payload.update(decisions=[{"id": "4051"}]),
    ],
)
def test_verdict_root_and_batch_shapes_are_rejected(client_session, payload_change):
    client, _session = client_session
    metadata = upload_armor(client).json
    payload = verdict_payload(metadata, [])
    payload_change(payload)
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=payload,
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "bad_request"


def test_malformed_json_is_rejected(client_session):
    client, _session = client_session
    upload_armor(client)
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN, "Content-Type": "application/json"},
        data=b"{not-json",
    )
    assert response.status_code == 400
    assert response.json["error"]["code"] == "bad_request"


def test_both_verdict_batch_caps_are_enforced(client_session, monkeypatch):
    client, _session = client_session
    metadata = upload_armor(client).json
    too_many_for_report = [
        {"id": "4051", "verdict": "vetoed"}
        for _index in range(6)
    ]
    response = post_verdict(client, metadata, too_many_for_report)
    assert response.status_code == 400
    monkeypatch.setattr(server_app, "MAX_VERDICT_ENTRIES", 1)
    response = post_verdict(
        client,
        metadata,
        [
            {"id": "4051", "verdict": "vetoed"},
            {"id": "4052", "verdict": "vetoed"},
        ],
    )
    assert response.status_code == 400


def test_hard_verdict_cap_is_independent_of_report_size():
    decisions = [
        {"id": str(index), "verdict": "vetoed"}
        for index in range(1, 50_002)
    ]
    payload = {
        "report_revision": 1,
        "verdict_revision": 0,
        "fingerprint": "fingerprint",
        "decisions": decisions,
    }
    with pytest.raises(ApiError) as error:
        _validate_verdict_payload_data(payload)
    assert error.value.code == "bad_request"


def test_missing_verdict_is_not_treated_as_null(client_session):
    client, session = client_session
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    response = post_verdict(client, metadata, [{"id": proposal["id"]}])
    assert response.status_code == 400
    assert session.verdicts == []


def test_verdicts_noop_and_clear_absent_do_not_bump(client_session):
    client, session = client_session
    overrides = Path(session.overrides_path)
    before_overrides = overrides.read_bytes()
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    first = post_verdict(client, metadata, [{"id": proposal["id"], "verdict": "vetoed"}])
    assert first.status_code == 200
    repeated = post_verdict(
        client,
        first.json,
        [{"id": proposal["id"], "verdict": "vetoed"}],
    )
    assert repeated.status_code == 200
    assert repeated.json["verdict_revision"] == 1
    clear_absent = post_verdict(
        client,
        repeated.json,
        [{"id": proposal["id"], "verdict": None}],
    )
    assert clear_absent.status_code == 200
    assert clear_absent.json["verdict_revision"] == 2
    clear_absent_again = post_verdict(
        client,
        clear_absent.json,
        [{"id": proposal["id"], "verdict": None}],
    )
    assert clear_absent_again.status_code == 200
    assert clear_absent_again.json["verdict_revision"] == 2
    assert isinstance(clear_absent_again.json["verdicts"], list)
    assert session.verdicts == []
    assert overrides.read_bytes() == before_overrides


def test_stale_variants_return_stable_body_and_revision_headers(client_session):
    client, session = client_session
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    payload = verdict_payload(metadata, [{"id": proposal["id"], "verdict": "vetoed"}])
    before = session_metadata(session)
    changed = dict(payload, report_revision=0)
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=changed,
    )
    assert response.status_code == 409
    assert response.json == {
        "error": {
            "code": "stale_report",
            "message": "report revision is stale; reload the current report before retrying",
        }
    }
    assert response.headers["Vault-Cleaner-Report-Revision"] == "1"
    assert response.headers["Vault-Cleaner-Verdict-Revision"] == "0"
    assert session_metadata(session) == before

    stale_unknown = dict(
        payload,
        report_revision=0,
        decisions=[{"id": "99999999999999999999", "verdict": "vetoed"}],
    )
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=stale_unknown,
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "stale_report"
    assert response.headers["Vault-Cleaner-Report-Revision"] == "1"
    assert response.headers["Vault-Cleaner-Verdict-Revision"] == "0"
    assert session_metadata(session) == before

    stale_over_count = dict(
        payload,
        report_revision=0,
        decisions=[
            {"id": str(10_000 + index), "verdict": "vetoed"}
            for index in range(6)
        ],
    )
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=stale_over_count,
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "stale_report"
    assert session_metadata(session) == before

    changed = dict(payload, fingerprint="wrong")
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=changed,
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "stale_report"
    assert session_metadata(session) == before

    changed = dict(payload, verdict_revision=1)
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=changed,
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "stale_verdicts"
    assert session_metadata(session) == before


def test_stale_verdict_failures_preserve_complete_session_state(client_session):
    client, session = client_session
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    accepted = post_verdict(
        client, metadata, [{"id": proposal["id"], "verdict": "vetoed"}]
    )
    before = {
        "state": session.state,
        "report": session.report,
        "staging": session.staging_dir,
        "report_revision": session.report_revision,
        "verdict_revision": session.verdict_revision,
        "verdicts": deepcopy(session.verdicts),
        "fingerprint": session.fingerprint,
        "snapshot": deepcopy(session.snapshot),
    }
    stale = post_verdict(
        client,
        accepted.json,
        [{"id": proposal["id"], "verdict": "approved"}],
        verdict_revision=0,
    )
    assert stale.status_code == 409
    assert stale.json["error"]["code"] == "stale_verdicts"
    assert stale.headers["Vault-Cleaner-Report-Revision"] == "1"
    assert stale.headers["Vault-Cleaner-Verdict-Revision"] == "1"
    assert session.state == before["state"]
    assert session.report is before["report"]
    assert session.staging_dir == before["staging"]
    assert session.report_revision == before["report_revision"]
    assert session.verdict_revision == before["verdict_revision"]
    assert session.verdicts == before["verdicts"]
    assert session.fingerprint == before["fingerprint"]
    assert session.snapshot == before["snapshot"]


def test_stale_reset_variants_have_coherent_headers_and_no_mutation(client_session):
    client, session = client_session
    assert upload_armor(client).status_code == 200
    before = session_metadata(session)
    for payload in (
        {"report_revision": 0, "verdict_revision": 0},
        {"report_revision": 1, "verdict_revision": 1},
    ):
        response = client.post(
            "/api/reset",
            base_url=ORIGIN,
            headers={"Origin": ORIGIN},
            json=payload,
        )
        assert response.status_code == 409
        assert response.json["error"]["code"] in {"stale_report", "stale_verdicts"}
        assert response.headers["Vault-Cleaner-Report-Revision"] == "1"
        assert response.headers["Vault-Cleaner-Verdict-Revision"] == "0"
        assert session_metadata(session) == before


def test_clear_last_verdict_and_reset_preserve_overrides(client_session, tmp_path):
    client, session = client_session
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    response = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=verdict_payload(metadata, [{"id": proposal["id"], "verdict": "vetoed"}]),
    )
    assert response.status_code == 200
    cleared = client.post(
        "/api/verdicts",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json=verdict_payload(
            response.json,
            [{"id": proposal["id"], "verdict": None}],
        ),
    )
    assert cleared.status_code == 200
    assert cleared.json["state"] == "exports-loaded"
    assert cleared.json["verdict_revision"] == 2

    overrides = tmp_path / "overrides.json"
    before = overrides.read_bytes() if overrides.exists() else None
    reset = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": cleared.json["report_revision"],
            "verdict_revision": cleared.json["verdict_revision"],
        },
    )
    assert reset.status_code == 200
    assert reset.json["state"] == "idle"
    assert reset.json["report_revision"] == 2
    assert reset.json["verdict_revision"] == 2
    assert (overrides.read_bytes() if overrides.exists() else None) == before
    assert session.report is None


def test_reset_clears_all_session_paths_and_retries_unexpected_cleanup(
    client_session, tmp_path, monkeypatch
):
    client, session = client_session
    overrides = Path(session.overrides_path)
    overrides.write_bytes(b'{"schema_version":1,"vetoes":[]}\n')
    # The session loaded its override store before this test writes the exact
    # same valid bytes; reset must not read or rewrite it.
    before_overrides = overrides.read_bytes()
    uploaded = upload_armor(client)
    assert uploaded.status_code == 200
    candidate = tmp_path / "candidate"
    retired = tmp_path / "retired"
    candidate.mkdir()
    retired.mkdir()
    session.track_candidate(candidate)
    session.track_retired(retired)
    live = session.staging_dir
    assert live is not None

    original_cleanup = session.cleanup_directory
    failed = True

    def fail_once(directory, *, candidate=False):
        nonlocal failed
        if failed:
            failed = False
            raise ValueError("injected cleanup failure")
        return original_cleanup(directory, candidate=candidate)

    monkeypatch.setattr(session, "cleanup_directory", fail_once)
    response = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={"report_revision": 1, "verdict_revision": 0},
    )
    assert response.status_code == 200
    assert response.json["state"] == "idle"
    assert response.json["report_revision"] == 2
    assert response.json["verdict_revision"] == 0
    assert session.report is None
    assert session.fingerprint is None
    assert session.snapshot is None
    assert session.verdicts == []
    assert overrides.read_bytes() == before_overrides
    assert session._retired_staging_dirs or session._candidate_staging_dirs

    retry = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={"report_revision": 2, "verdict_revision": 0},
    )
    assert retry.status_code == 200
    assert not live.exists()
    assert not candidate.exists()
    assert not retired.exists()
    assert session.export_digests == {}
    assert session.export_sizes == {}
    assert session.staging_dir is None
    assert not session._candidate_staging_dirs
    assert not session._retired_staging_dirs


def test_reset_idle_is_noop_and_closed_session_cannot_revive(client_session):
    client, session = client_session
    idle = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={"report_revision": 0, "verdict_revision": 0},
    )
    assert idle.status_code == 200
    assert idle.json["state"] == "idle"
    assert idle.json["report_revision"] == 0
    assert idle.json["verdict_revision"] == 0

    closed = client.post(
        "/api/shutdown", base_url=ORIGIN, headers={"Origin": ORIGIN}
    )
    refused = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": closed.json["report_revision"],
            "verdict_revision": closed.json["verdict_revision"],
        },
    )
    assert refused.status_code == 409
    assert refused.json["error"]["code"] == "illegal_state"
    assert session.state == "closed"
    assert session.closed


def test_changed_upload_retains_full_identity_and_identical_upload_reports_ids(
    client_session, monkeypatch
):
    client, session = client_session
    original_body = (FIXTURES / "armor.csv").read_bytes()
    metadata = upload_armor(client).json
    proposals = metadata["snapshot"]["sections"][0]["decisions"]
    selected = [
        {"id": proposals[0]["id"], "verdict": "vetoed"},
        {"id": proposals[1]["id"], "verdict": "approved"},
    ]
    reviewed = post_verdict(client, metadata, selected)
    assert reviewed.status_code == 200
    replace_report(monkeypatch, session)
    changed_body = original_body + b"\n"
    response = client.post(
        "/api/exports/armor",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(changed_body)),
        },
        data=changed_body,
    )
    assert response.status_code == 200
    assert response.json["retained_verdict_ids"] == [
        proposals[0]["id"],
        proposals[1]["id"],
    ]
    assert response.json["discarded_verdict_ids"] == []
    assert response.json["verdict_revision"] == 1
    assert response.json["state"] == "reviewing"

    identical = client.post(
        "/api/exports/armor",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(changed_body)),
        },
        data=changed_body,
    )
    assert identical.status_code == 200
    assert identical.json["retained_verdict_ids"] == [
        proposals[0]["id"],
        proposals[1]["id"],
    ]
    assert identical.json["discarded_verdict_ids"] == []
    assert identical.json["verdict_revision"] == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", "ghosts"),
        ("hash", "changed-hash"),
        ("action", "changed-action"),
        ("reason", "changed-reason"),
    ],
)
def test_changed_upload_discards_each_changed_identity_field(
    client_session, monkeypatch, field, value
):
    client, session = client_session
    original_body = (FIXTURES / "armor.csv").read_bytes()
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    reviewed = post_verdict(
        client, metadata, [{"id": proposal["id"], "verdict": "vetoed"}]
    )
    assert reviewed.status_code == 200
    replace_report(monkeypatch, session, decision_changes=(0, {field: value}))
    changed_body = original_body + b"\n"
    response = client.post(
        "/api/exports/armor",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(changed_body)),
        },
        data=changed_body,
    )
    assert response.status_code == 200
    assert response.json["retained_verdict_ids"] == []
    assert response.json["discarded_verdict_ids"] == [proposal["id"]]
    assert response.json["verdict_revision"] == 2
    assert response.json["state"] == "exports-loaded"


def test_changed_upload_names_all_discarded_and_bumps_once(client_session, monkeypatch):
    client, session = client_session
    original_body = (FIXTURES / "armor.csv").read_bytes()
    metadata = upload_armor(client).json
    proposals = metadata["snapshot"]["sections"][0]["decisions"]
    reviewed = post_verdict(
        client,
        metadata,
        [
            {"id": proposals[0]["id"], "verdict": "vetoed"},
            {"id": proposals[1]["id"], "verdict": "approved"},
        ],
    )
    assert reviewed.status_code == 200
    replace_report(monkeypatch, session, drop_first=True, drop_count=2)
    changed_body = original_body + b"\n"
    response = client.post(
        "/api/exports/armor",
        base_url=ORIGIN,
        headers={
            "Origin": ORIGIN,
            "Content-Type": "text/csv",
            "Content-Length": str(len(changed_body)),
        },
        data=changed_body,
    )
    assert response.status_code == 200
    assert response.json["retained_verdict_ids"] == []
    assert response.json["discarded_verdict_ids"] == [
        proposals[0]["id"],
        proposals[1]["id"],
    ]
    assert response.json["verdict_revision"] == 2
    assert response.json["state"] == "exports-loaded"


def test_repeated_shutdown_returns_terminal_envelope(client_session):
    client, session = client_session
    metadata = upload_armor(client).json
    proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
    reviewing = post_verdict(
        client, metadata, [{"id": proposal["id"], "verdict": "vetoed"}]
    )
    assert reviewing.status_code == 200
    report_revision = reviewing.json["report_revision"]
    verdict_revision = reviewing.json["verdict_revision"]
    live_staging = session.staging_dir
    assert session.report is not None
    assert live_staging is not None
    first = client.post(
        "/api/shutdown", base_url=ORIGIN, headers={"Origin": ORIGIN}
    )
    second = client.post(
        "/api/shutdown", base_url=ORIGIN, headers={"Origin": ORIGIN}
    )
    first.close()
    second.close()
    assert first.status_code == second.status_code == 200
    assert first.json == second.json
    assert first.json["state"] == "closed"
    assert first.json["report_revision"] == report_revision
    assert first.json["verdict_revision"] == verdict_revision
    assert session.report is None
    assert session.snapshot is None
    assert session.fingerprint is None
    assert session.verdicts == []
    assert session.staging_dir is None
    assert not live_staging.exists()
    assert session.closed
    refused = client.post(
        "/api/reset",
        base_url=ORIGIN,
        headers={"Origin": ORIGIN},
        json={
            "report_revision": report_revision,
            "verdict_revision": verdict_revision,
        },
    )
    assert refused.status_code == 409
    assert session.report is None
    assert session.report_revision == report_revision
    assert session.verdict_revision == verdict_revision


def test_every_mutating_route_is_serialized(client_session):
    client, _session = client_session
    app = client.application
    for rule in app.url_map.iter_rules():
        if "POST" in rule.methods:
            view = app.view_functions[rule.endpoint]
            assert getattr(view, "__vault_cleaner_serialized__", False), rule.rule


def test_real_socket_same_revision_verdicts_are_serialized(monkeypatch, tmp_path):
    """Two real HTTP requests cannot both commit one verdict revision."""
    session = Session(
        overrides_path=str(tmp_path / "overrides.json"),
        config_path="config.toml",
        no_wishlists=True,
        bootstrap_token="bootstrap",
        session_token="session",
    )
    server = build_server(session, 0)
    app = server.app
    first_inside = threading.Event()
    second_arrived = threading.Event()
    release_first = threading.Event()
    first_seen = threading.Event()
    original_metadata = server_app.session_metadata

    @app.before_request
    def observe_arrival():
        if request.path == "/api/verdicts" and first_seen.is_set():
            second_arrived.set()

    def block_first(target_session):
        if request.path == "/api/verdicts" and not first_seen.is_set():
            first_seen.set()
            first_inside.set()
            assert release_first.wait(timeout=5)
        return original_metadata(target_session)

    monkeypatch.setattr(server_app, "session_metadata", block_first)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    first_result: dict[str, object] = {}
    second_result: dict[str, object] = {}
    first_done = threading.Event()
    second_done = threading.Event()
    connections: list[http.client.HTTPConnection] = []

    def request_verdict(result, done):
        connection = http.client.HTTPConnection("127.0.0.1", session.bound_port, timeout=5)
        connections.append(connection)
        try:
            body = json.dumps(result.pop("request")).encode()
            connection.request(
                "POST",
                "/api/verdicts",
                body=body,
                headers={
                    "Cookie": "vault_cleaner_session=session",
                    "Origin": session.expected_origin,
                    "Content-Type": "application/json",
                    "Content-Length": str(len(body)),
                },
            )
            response = connection.getresponse()
            result["status"] = response.status
            result["payload"] = json.loads(response.read())
            result["report_header"] = response.getheader(
                "Vault-Cleaner-Report-Revision"
            )
            result["verdict_header"] = response.getheader(
                "Vault-Cleaner-Verdict-Revision"
            )
        except Exception as error:  # noqa: BLE001 - capture request-thread failures
            result["error"] = error
        finally:
            connection.close()
            done.set()

    try:
        bootstrap_connection = http.client.HTTPConnection(
            "127.0.0.1", session.bound_port, timeout=5
        )
        bootstrap_connection.request("GET", "/bootstrap?token=bootstrap")
        bootstrap_response = bootstrap_connection.getresponse()
        bootstrap_response.read()
        assert bootstrap_response.status == 303
        bootstrap_cookie = bootstrap_response.getheader("Set-Cookie")
        assert bootstrap_cookie is not None
        cookie = bootstrap_cookie.split(";", 1)[0]
        body = (FIXTURES / "armor.csv").read_bytes()
        bootstrap_connection.request(
            "POST",
            "/api/exports/armor",
            body=body,
            headers={
                "Cookie": cookie,
                "Origin": session.expected_origin,
                "Content-Type": "text/csv",
                "Content-Length": str(len(body)),
            },
        )
        upload_response = bootstrap_connection.getresponse()
        metadata = json.loads(upload_response.read())
        assert upload_response.status == 200
        proposal = metadata["snapshot"]["sections"][0]["decisions"][0]
        request_payload = {
            "report_revision": metadata["report_revision"],
            "verdict_revision": metadata["verdict_revision"],
            "fingerprint": metadata["fingerprint"],
            "decisions": [{"id": proposal["id"], "verdict": "vetoed"}],
        }
        first_result["request"] = dict(request_payload)
        second_result["request"] = dict(request_payload)
        first_thread = threading.Thread(
            target=request_verdict, args=(first_result, first_done)
        )
        second_thread = threading.Thread(
            target=request_verdict, args=(second_result, second_done)
        )
        first_thread.start()
        assert first_inside.wait(timeout=5)
        second_thread.start()
        assert second_arrived.wait(timeout=5)
        assert not second_done.is_set()
        release_first.set()
        assert first_done.wait(timeout=5)
        assert second_done.wait(timeout=5)
        first_thread.join(timeout=5)
        second_thread.join(timeout=5)
        assert not first_thread.is_alive()
        assert not second_thread.is_alive()
        assert "error" not in first_result
        assert "error" not in second_result
        statuses = {first_result["status"], second_result["status"]}
        assert statuses == {200, 409}
        loser = first_result if first_result["status"] == 409 else second_result
        assert loser["payload"]["error"]["code"] == "stale_verdicts"
        assert loser["report_header"] == "1"
        assert loser["verdict_header"] == "1"
        assert session.verdict_revision == 1
        assert session.verdicts == [{"id": proposal["id"], "verdict": "vetoed"}]
    finally:
        release_first.set()
        for connection in connections:
            connection.close()
        server.shutdown()
        server_thread.join(timeout=5)
        assert not server_thread.is_alive()
        server.server_close()
        session.close()
