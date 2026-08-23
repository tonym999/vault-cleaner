"""Focused coverage for the M8 upload transaction and session lifecycle."""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from vault_cleaner.report_run import run_report, snapshot_dict
from vault_cleaner.review import save_overrides
from vault_cleaner.review_session import OverrideStore, Veto
from vault_cleaner.server import app as server_app
from vault_cleaner.server import session as server_session
from vault_cleaner.server.app import (
    _validate_total_export_size,
    _validate_upload_content_length,
    create_app,
)
from vault_cleaner.server.errors import ApiError
from vault_cleaner.server.limits import MAX_EXPORT_BYTES, MAX_TOTAL_EXPORT_BYTES, MIB
from vault_cleaner.server.session import Session

HOST = "127.0.0.1:43123"
ORIGIN = f"http://{HOST}"
FIXTURES = Path(__file__).parent / "fixtures"


@contextmanager
def make_client(tmp_path):
    session = Session(
        overrides_path=str(tmp_path / "overrides.json"),
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
        yield client, session
    finally:
        session.close()


def post_upload(client, kind: str, content: bytes, *, content_type="text/csv", **extra):
    headers = {
        "Origin": ORIGIN,
        "Content-Type": content_type,
        "Content-Length": str(len(content)),
        **extra,
    }
    return client.post(
        f"/api/exports/{kind}", base_url=ORIGIN, headers=headers, data=content
    )


@pytest.mark.parametrize(
    ("kind", "fixture"),
    [("weapons", "weapons.csv"), ("armor", "armor.csv"), ("ghosts", "ghosts.csv")],
)
def test_each_export_kind_builds_a_partial_report(tmp_path, kind, fixture):
    with make_client(tmp_path) as (client, session):
        response = post_upload(client, kind, (FIXTURES / fixture).read_bytes())

        assert response.status_code == 200
        assert response.json["state"] == "exports-loaded"
        assert response.json["report_revision"] == 1
        assert [section["kind"] for section in response.json["snapshot"]["sections"]] == [kind]
        canonical = {
            "weapons": "destiny-weapon.csv",
            "armor": "destiny-armor.csv",
            "ghosts": "destiny-ghost.csv",
        }[kind]
        assert all(
            section["source"]["path"] == canonical
            for section in response.json["snapshot"]["sections"]
        )
        assert session.staging_dir is not None


def test_uploads_combine_using_canonical_names_and_keep_skip_warnings(tmp_path):
    with make_client(tmp_path) as (client, _session):
        response = post_upload(client, "weapons", (FIXTURES / "weapons.csv").read_bytes())

        assert response.status_code == 200
        snapshot = response.json["snapshot"]
        assert snapshot["warnings"]
        assert {warning["path"] for warning in snapshot["warnings"]} == {
            "destiny-armor.csv",
            "destiny-ghost.csv",
        }
        assert {section["source"]["path"] for section in snapshot["sections"]} == {
            "destiny-weapon.csv"
        }


def test_all_three_uploads_combine_into_one_report(tmp_path):
    with make_client(tmp_path) as (client, session):
        for kind, fixture in (
            ("weapons", "weapons.csv"),
            ("armor", "armor.csv"),
            ("ghosts", "ghosts.csv"),
        ):
            response = post_upload(client, kind, (FIXTURES / fixture).read_bytes())
            assert response.status_code == 200

        report = client.get("/api/report", base_url=ORIGIN)
        assert report.status_code == 200
        assert {section["kind"] for section in report.json["snapshot"]["sections"]} == {
            "weapons",
            "armor",
            "ghosts",
        }
        assert report.json["snapshot"]["warnings"] == []
        assert session.export_digests.keys() == {"weapons", "armor", "ghosts"}
        assert session.staging_dir is not None
        assert {
            path.name for path in session.staging_dir.iterdir()
        } == {"destiny-weapon.csv", "destiny-armor.csv", "destiny-ghost.csv"}


def test_identical_upload_is_a_noop_but_changed_upload_revises(tmp_path):
    with make_client(tmp_path) as (client, session):
        original = (FIXTURES / "weapons.csv").read_bytes()
        assert post_upload(client, "weapons", original).status_code == 200
        live = session.staging_dir
        assert live is not None
        assert post_upload(client, "weapons", original).json["report_revision"] == 1
        assert session.staging_dir == live

        changed = original + b"\n"
        response = post_upload(client, "weapons", changed)
        assert response.status_code == 200
        assert response.json["report_revision"] == 2
        assert session.staging_dir != live
        assert not live.exists()


def test_schema_failure_does_not_replace_the_previous_valid_upload(tmp_path):
    with make_client(tmp_path) as (client, session):
        original = (FIXTURES / "weapons.csv").read_bytes()
        assert post_upload(client, "weapons", original).status_code == 200
        before = {
            "digests": session.export_digests.copy(),
            "sizes": session.export_sizes.copy(),
            "staging": session.staging_dir,
            "report": session.report,
            "report_revision": session.report_revision,
            "verdict_revision": session.verdict_revision,
            "verdicts": deepcopy(session.verdicts),
            "state": session.state,
            "fingerprint": session.fingerprint,
            "snapshot": deepcopy(session.snapshot),
        }

        response = post_upload(client, "weapons", b"Name,Id\nnot-a-dim-row,1\n")
        assert response.status_code == 422
        body = response.get_data(as_text=True)
        assert str(tmp_path) not in body
        assert str(tmp_path / "overrides.json") not in body
        assert session.export_digests == before["digests"]
        assert session.export_sizes == before["sizes"]
        assert session.staging_dir == before["staging"]
        assert session.report == before["report"]
        assert session.report_revision == before["report_revision"]
        assert session.verdict_revision == before["verdict_revision"]
        assert session.verdicts == before["verdicts"]
        assert session.state == before["state"]
        assert session.fingerprint == before["fingerprint"]
        assert session.snapshot == before["snapshot"]
        assert not session._candidate_staging_dirs


def test_report_failure_rolls_back_and_removes_candidate(monkeypatch, tmp_path):
    with make_client(tmp_path) as (client, session):
        candidate_root = tmp_path / "candidates"
        candidate_root.mkdir()
        real_mkdtemp = server_app.tempfile.mkdtemp

        def local_mkdtemp(*, prefix):
            return real_mkdtemp(prefix=prefix, dir=candidate_root)

        monkeypatch.setattr(server_app.tempfile, "mkdtemp", local_mkdtemp)
        original = (FIXTURES / "weapons.csv").read_bytes()
        assert post_upload(client, "weapons", original).status_code == 200
        before_candidates = set(candidate_root.iterdir())
        live = session.staging_dir
        session.verdict_revision = 4
        session.verdicts = [{"id": "6917", "verdict": "vetoed"}]
        before = {
            "digests": session.export_digests.copy(),
            "sizes": session.export_sizes.copy(),
            "staging": session.staging_dir,
            "report": session.report,
            "report_revision": session.report_revision,
            "verdict_revision": session.verdict_revision,
            "verdicts": deepcopy(session.verdicts),
            "state": session.state,
            "fingerprint": session.fingerprint,
            "snapshot": deepcopy(session.snapshot),
        }

        def fail(**_kwargs):
            raise RuntimeError("/private/candidate/path")

        monkeypatch.setattr(server_app, "run_report", fail)
        response = post_upload(client, "weapons", original + b"\n")

        assert response.status_code == 500
        body = response.get_data(as_text=True)
        assert "/private/candidate/path" not in body
        assert str(tmp_path) not in body
        assert session.export_digests == before["digests"]
        assert session.export_sizes == before["sizes"]
        assert session.staging_dir == before["staging"] == live
        assert session.report == before["report"]
        assert session.report_revision == before["report_revision"]
        assert session.verdict_revision == before["verdict_revision"]
        assert session.verdicts == before["verdicts"]
        assert session.state == before["state"]
        assert session.fingerprint == before["fingerprint"]
        assert session.snapshot == before["snapshot"]
        assert not session._candidate_staging_dirs
        assert set(candidate_root.iterdir()) == before_candidates


@pytest.mark.parametrize(
    ("headers", "status", "code"),
    [
        ({"Content-Type": "text/csv"}, 411, "length_required"),
        ({"Content-Type": "text/csv", "Transfer-Encoding": "chunked"}, 411, "length_required"),
        ({"Content-Type": "text/csv", "Content-Length": "not-a-number"}, 411, "length_required"),
        ({"Content-Type": "application/json"}, 415, "unsupported_media_type"),
        ({}, 415, "unsupported_media_type"),
    ],
)
def test_upload_transport_contract(tmp_path, headers, status, code):
    with make_client(tmp_path) as (client, _session):
        response = client.post(
            "/api/exports/weapons",
            base_url=ORIGIN,
            headers={"Origin": ORIGIN, **headers},
            data=b"x",
            environ_overrides=(
                {"CONTENT_LENGTH": ""}
                if "Content-Length" not in headers
                else {"CONTENT_LENGTH": headers["Content-Length"]}
            ),
        )
        assert response.status_code == status
        assert response.json["error"]["code"] == code


def test_invalid_utf8_is_a_clean_bad_request(tmp_path):
    with make_client(tmp_path) as (client, _session):
        response = post_upload(client, "weapons", b"\xff")

        assert response.status_code == 400
        assert response.json["error"]["code"] == "bad_request"
        body = response.get_data(as_text=True)
        assert str(tmp_path) not in body
        assert "overrides.json" not in body


def test_individual_content_length_boundaries_are_checked_before_body_reading():
    assert _validate_upload_content_length(str(MAX_EXPORT_BYTES)) == MAX_EXPORT_BYTES
    with pytest.raises(ApiError, match="export exceeds"):
        _validate_upload_content_length(str(MAX_EXPORT_BYTES + 1))


def test_exact_aggregate_boundary_is_allowed_and_lower_injected_cap_rejects():
    sizes = {"weapons": 32 * MIB, "armor": 32 * MIB}
    assert _validate_total_export_size(
        sizes, "ghosts", 32 * MIB, MAX_TOTAL_EXPORT_BYTES
    ) == {**sizes, "ghosts": 32 * MIB}
    with pytest.raises(ApiError, match="combined exports"):
        _validate_total_export_size(sizes, "ghosts", 32 * MIB, 96 * MIB - 1)


def test_aggregate_limit_can_be_injected_for_the_rejection_branch(monkeypatch, tmp_path):
    monkeypatch.setattr(server_app, "MAX_TOTAL_EXPORT_BYTES", 100)
    with make_client(tmp_path) as (client, session):
        content = (FIXTURES / "weapons.csv").read_bytes()
        assert post_upload(client, "weapons", content).status_code == 413
        assert session.report is None
        assert session.staging_dir is None


def test_missing_overrides_have_a_distinct_digest_and_close_is_idempotent(tmp_path):
    with make_client(tmp_path) as (client, session):
        assert session.override_digest is None
        assert post_upload(client, "weapons", (FIXTURES / "weapons.csv").read_bytes()).status_code == 200
        staging = session.staging_dir
        session.close()
        session.close()
        assert staging is not None and not staging.exists()


def test_close_before_upload_rejects_without_staging_a_candidate(tmp_path, monkeypatch):
    with make_client(tmp_path) as (client, session):
        session.close()
        monkeypatch.setattr(
            server_app.tempfile,
            "mkdtemp",
            lambda **_kwargs: pytest.fail("closed upload allocated a candidate"),
        )

        response = post_upload(client, "weapons", (FIXTURES / "weapons.csv").read_bytes())

        assert response.status_code == 409
        assert response.json["error"]["code"] == "illegal_state"
        assert session.report is None
        assert session.export_digests == {}
        assert session.export_sizes == {}
        assert session.staging_dir is None


def test_close_invalidates_all_accepted_export_state(tmp_path):
    with make_client(tmp_path) as (client, session):
        assert post_upload(client, "weapons", (FIXTURES / "weapons.csv").read_bytes()).status_code == 200
        session.verdict_revision = 2
        session.verdicts = [{"id": "6917", "verdict": "vetoed"}]
        staging = session.staging_dir
        assert staging is not None

        session.close()

        assert session.closed
        assert session.state == "idle"
        assert session.report_revision == 0
        assert session.verdict_revision == 0
        assert session.report is None
        assert session.export_digests == {}
        assert session.export_sizes == {}
        assert session.fingerprint is None
        assert session.snapshot is None
        assert session.verdicts == []
        assert session.override_status == []
        assert session.staging_dir is None
        assert not staging.exists()
        assert client.get("/api/report", base_url=ORIGIN).json == {
            "schema_version": 1,
            "state": "idle",
            "report_revision": 0,
            "verdict_revision": 0,
            "fingerprint": None,
            "snapshot": None,
            "verdicts": [],
            "override_status": [],
        }


def test_override_digest_is_of_the_exact_loaded_bytes(tmp_path):
    content = b'{"schema_version":1,"vetoes":[]}\n'
    path = tmp_path / "overrides.json"
    path.write_bytes(content)
    session = Session(overrides_path=str(path))

    assert session.override_digest == hashlib.sha256(content).hexdigest()
    session.close()


def test_session_close_cleans_live_candidate_and_retired_directories(tmp_path):
    session = Session(overrides_path=str(tmp_path / "overrides.json"))
    live = tmp_path / "live"
    candidate = tmp_path / "candidate"
    retired = tmp_path / "retired"
    for directory in (live, candidate, retired):
        directory.mkdir()
        (directory / "export.csv").write_bytes(b"x")
    session.staging_dir = live
    session.track_candidate(candidate)
    session.track_retired(retired)

    session.close()
    session.close()

    assert not any(directory.exists() for directory in (live, candidate, retired))
    assert session.staging_dir is None
    assert not session._candidate_staging_dirs
    assert not session._retired_staging_dirs


def test_close_retries_a_directory_when_deletion_temporarily_fails(
    monkeypatch, tmp_path
):
    session = Session(overrides_path=str(tmp_path / "overrides.json"))
    live = tmp_path / "live"
    live.mkdir()
    session.staging_dir = live
    real_rmtree = server_session.shutil.rmtree
    failed = True

    def fail_once(path, *args, **kwargs):
        nonlocal failed
        if failed:
            failed = False
            raise OSError("temporary deletion failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(server_session.shutil, "rmtree", fail_once)
    session.close()
    assert live.exists()
    assert session.staging_dir is None
    assert live not in session._candidate_staging_dirs
    assert live in session._retired_staging_dirs

    session.close()
    assert not live.exists()
    assert session.staging_dir is None
    assert not session._retired_staging_dirs


def test_failed_candidate_cleanup_remains_tracked_until_close(
    monkeypatch, tmp_path
):
    with make_client(tmp_path) as (client, session):
        original = (FIXTURES / "weapons.csv").read_bytes()
        assert post_upload(client, "weapons", original).status_code == 200
        real_rmtree = server_session.shutil.rmtree
        failed = True

        def fail_candidate_once(path, *args, **kwargs):
            nonlocal failed
            if failed and Path(path).name.startswith("vault-cleaner-uploads-"):
                failed = False
                raise OSError("temporary candidate deletion failure")
            return real_rmtree(path, *args, **kwargs)

        monkeypatch.setattr(server_session.shutil, "rmtree", fail_candidate_once)
        monkeypatch.setattr(
            server_app,
            "run_report",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("candidate failed")),
        )
        response = post_upload(client, "weapons", original + b"\n")

        assert response.status_code == 500
        assert len(session._candidate_staging_dirs) == 1
        candidate = next(iter(session._candidate_staging_dirs))
        assert candidate.exists()
        assert str(candidate) not in response.get_data(as_text=True)

        session.close()
        assert not candidate.exists()
        assert not session._candidate_staging_dirs


def test_post_commit_retirement_failure_keeps_new_live_state(
    monkeypatch, tmp_path
):
    with make_client(tmp_path) as (client, session):
        original = (FIXTURES / "weapons.csv").read_bytes()
        assert post_upload(client, "weapons", original).status_code == 200
        previous = session.staging_dir
        assert previous is not None
        real_cleanup = session.cleanup_directory
        failed = True

        def fail_retirement_once(path, *args, **kwargs):
            nonlocal failed
            if failed and Path(path) == previous:
                failed = False
                raise RuntimeError("retirement failed after commit")
            return real_cleanup(path, *args, **kwargs)

        monkeypatch.setattr(session, "cleanup_directory", fail_retirement_once)
        response = post_upload(client, "weapons", original + b"\n")

        assert response.status_code == 200
        current = session.staging_dir
        assert current is not None and current != previous and current.exists()
        assert session.report is not None
        assert response.json["snapshot"] == snapshot_dict(session.report)
        assert session.export_digests["weapons"] == hashlib.sha256(
            original + b"\n"
        ).hexdigest()
        assert previous in session._retired_staging_dirs


def test_report_override_status_has_exact_schema_for_every_classification(tmp_path):
    run = run_report(
        config_path="config.toml",
        armor_path=FIXTURES / "armor.csv",
        no_wishlists=True,
    )
    active = run.sections[0].decisions[0]
    stale = run.sections[0].decisions[1]
    store = OverrideStore(
        schema_version=1,
        vetoes=(
            Veto(
                active.id,
                active.kind,
                active.hash,
                active.name,
                active.action,
                active.reason,
                run.fingerprint,
                "2026-08-23T00:00:00Z",
            ),
            Veto(
                stale.id,
                stale.kind,
                stale.hash,
                stale.name,
                stale.action,
                "different-reason",
                run.fingerprint,
                "2026-08-23T00:00:00Z",
            ),
            Veto(
                "9999999999999999999",
                "armor",
                "hash",
                "gone",
                "junk",
                "reason",
                run.fingerprint,
                "2026-08-23T00:00:00Z",
            ),
            Veto(
                "8888888888888888888",
                "ghosts",
                "hash",
                "unloaded",
                "junk",
                "reason",
                run.fingerprint,
                "2026-08-23T00:00:00Z",
            ),
        ),
    )
    overrides_path = tmp_path / "overrides.json"
    save_overrides(store, overrides_path, updated_at="2026-08-23T00:00:00Z")
    session = Session(
        overrides_path=str(overrides_path),
        config_path="config.toml",
        no_wishlists=True,
        bootstrap_token="bootstrap",
        session_token="session",
    )
    session.configure_bound_port(43123)
    session.report = run
    session.state = "exports-loaded"
    client = create_app(session).test_client()
    assert client.get("/bootstrap?token=bootstrap", base_url=ORIGIN).status_code == 303

    response = client.get("/api/report", base_url=ORIGIN)

    assert response.status_code == 200
    assert response.json["snapshot"] == snapshot_dict(run)
    assert response.json["override_status"] == [
        {
            "id": active.id,
            "status": "active",
            "detail": "still matches a proposal; it is being suppressed",
        },
        {
            "id": stale.id,
            "status": "stale",
            "detail": (
                f"now proposed as {stale.action}/{stale.reason}, vetoed as "
                f"{stale.action}/different-reason — re-review it"
            ),
        },
        {
            "id": "9999999999999999999",
            "status": "orphaned",
            "detail": "no longer in the export",
        },
        {
            "id": "8888888888888888888",
            "status": "unchecked",
            "detail": "ghosts export not loaded this run",
        },
    ]
    assert all(set(entry) == {"id", "status", "detail"} for entry in response.json["override_status"])
    session.close()
