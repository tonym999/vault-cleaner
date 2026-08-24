"""Reusable lifecycle expectations and real-socket concurrency coverage."""

from __future__ import annotations

import http.client
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import request

from vault_cleaner.server import app as server_app
from vault_cleaner.server.app import build_server
from vault_cleaner.server.session import Session, session_metadata

HOST = "127.0.0.1"
BOOTSTRAP_TOKEN = "lifecycle-bootstrap"
SESSION_TOKEN = "lifecycle-session"
FIXTURES = Path(__file__).parent / "fixtures"

_WAIT_SECONDS = 5
_PRESERVED = object()


@dataclass(frozen=True)
class LifecycleExpectation:
    """Visible state shape shared by lifecycle tests and future #66 tests."""

    state: str
    closed: bool
    report_revision: int | object
    verdict_revision: int | object
    report: bool
    fingerprint: bool
    snapshot: bool
    verdict_count: int
    staging: bool
    candidates: int
    retired: int


LIFECYCLE_EXPECTATIONS = {
    "idle": LifecycleExpectation(
        state="idle",
        closed=False,
        report_revision=0,
        verdict_revision=0,
        report=False,
        fingerprint=False,
        snapshot=False,
        verdict_count=0,
        staging=False,
        candidates=0,
        retired=0,
    ),
    "exports-loaded": LifecycleExpectation(
        state="exports-loaded",
        closed=False,
        report_revision=1,
        verdict_revision=0,
        report=True,
        fingerprint=True,
        snapshot=True,
        verdict_count=0,
        staging=True,
        candidates=0,
        retired=0,
    ),
    # close intentionally preserves the visible state and monotonic revisions
    # until #66 chooses the terminal protocol envelope.
    "closed": LifecycleExpectation(
        state="exports-loaded",
        closed=True,
        report_revision=_PRESERVED,
        verdict_revision=_PRESERVED,
        report=False,
        fingerprint=False,
        snapshot=False,
        verdict_count=0,
        staging=False,
        candidates=0,
        retired=0,
    ),
}


def lifecycle_snapshot(session: Session) -> dict[str, Any]:
    """Capture mutable lifecycle state without retaining aliases."""
    with session.mutation_lock:
        metadata = session_metadata(session)
        return {
            "state": session.state,
            "closed": session._closed,
            "report_revision": session.report_revision,
            "verdict_revision": session.verdict_revision,
            "report": session.report is not None,
            "fingerprint": metadata["fingerprint"] is not None,
            "snapshot": metadata["snapshot"] is not None,
            "verdict_count": len(session.verdicts),
            "staging": session.staging_dir is not None,
            "candidates": len(session._candidate_staging_dirs),
            "retired": len(session._retired_staging_dirs),
        }


def assert_lifecycle_state(
    session: Session,
    name: str,
    *,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assert one table row, preserving revisions when the table says so."""
    expected = LIFECYCLE_EXPECTATIONS[name]
    actual = lifecycle_snapshot(session)
    for field in (
        "state",
        "closed",
        "report",
        "fingerprint",
        "snapshot",
        "verdict_count",
        "staging",
        "candidates",
        "retired",
    ):
        assert actual[field] == getattr(expected, field), field

    for field in ("report_revision", "verdict_revision"):
        expected_revision = getattr(expected, field)
        if expected_revision is _PRESERVED:
            assert previous is not None
            assert actual[field] == previous[field], field
        else:
            assert actual[field] == expected_revision, field
    return actual


def _run_upload(
    port: int,
    cookie: str,
    body: bytes,
    result: dict[str, Any],
    completed: threading.Event,
) -> None:
    connection = http.client.HTTPConnection(HOST, port, timeout=_WAIT_SECONDS)
    try:
        connection.request(
            "POST",
            "/api/exports/weapons",
            body=body,
            headers={
                "Cookie": cookie,
                "Origin": f"http://{HOST}:{port}",
                "Content-Type": "text/csv",
                "Content-Length": str(len(body)),
            },
        )
        response = connection.getresponse()
        result["status"] = response.status
        result["payload"] = json.loads(response.read())
    except (OSError, ValueError, http.client.HTTPException) as error:
        result["error"] = error
    finally:
        connection.close()
        completed.set()


def _run_shutdown(
    port: int,
    cookie: str,
    result: dict[str, Any],
    completed: threading.Event,
) -> None:
    connection = http.client.HTTPConnection(HOST, port, timeout=_WAIT_SECONDS)
    try:
        connection.request(
            "POST",
            "/api/shutdown",
            body=b"",
            headers={
                "Cookie": cookie,
                "Origin": f"http://{HOST}:{port}",
                "Content-Length": "0",
            },
        )
        response = connection.getresponse()
        result["status"] = response.status
        result["payload"] = json.loads(response.read())
    except (OSError, ValueError, http.client.HTTPException) as error:
        result["error"] = error
    finally:
        connection.close()
        completed.set()


def test_real_socket_upload_waits_for_report_before_shutdown(
    monkeypatch, tmp_path
):
    """A shutdown request cannot overtake an upload holding the mutation lock."""
    staging_root = tmp_path / "server-staging"
    staging_root.mkdir()
    real_mkdtemp = server_app.tempfile.mkdtemp

    def local_mkdtemp(*, prefix):
        return real_mkdtemp(prefix=prefix, dir=staging_root)

    monkeypatch.setattr(server_app.tempfile, "mkdtemp", local_mkdtemp)

    session = Session(
        overrides_path=str(tmp_path / "overrides.json"),
        config_path="config.toml",
        no_wishlists=True,
        bootstrap_token=BOOTSTRAP_TOKEN,
        session_token=SESSION_TOKEN,
    )
    server = build_server(session, 0)
    app = server.app
    shutdown_arrived = threading.Event()
    report_entered = threading.Event()
    release_report = threading.Event()
    shutdown_callback_entered = threading.Event()
    release_shutdown = threading.Event()
    shutdown_complete = threading.Event()
    events: list[str] = []

    @app.before_request
    def mark_shutdown_arrival() -> None:
        if request.path == "/api/shutdown":
            events.append("shutdown-arrived")
            shutdown_arrived.set()

    original_run_report = server_app.run_report

    def blocked_run_report(**kwargs):
        events.append("report-start")
        report_entered.set()
        if not release_report.wait(timeout=_WAIT_SECONDS):
            raise RuntimeError("upload release barrier timed out")
        result = original_run_report(**kwargs)
        events.append("report-end")
        return result

    monkeypatch.setattr(server_app, "run_report", blocked_run_report)
    original_request_shutdown = session.request_shutdown

    def blocked_request_shutdown() -> None:
        events.append("shutdown-callback-entered")
        shutdown_callback_entered.set()
        try:
            if not release_shutdown.wait(timeout=_WAIT_SECONDS):
                raise RuntimeError("shutdown release barrier timed out")
            original_request_shutdown()
        finally:
            events.append("shutdown-callback-finished")
            shutdown_complete.set()

    session.request_shutdown = blocked_request_shutdown

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    port = session.bound_port
    assert port is not None
    connection = http.client.HTTPConnection(HOST, port, timeout=_WAIT_SECONDS)
    upload_thread: threading.Thread | None = None
    shutdown_thread: threading.Thread | None = None
    upload_result: dict[str, Any] = {}
    shutdown_result: dict[str, Any] = {}
    upload_done = threading.Event()
    shutdown_done = threading.Event()

    try:
        connection.request("GET", f"/bootstrap?token={BOOTSTRAP_TOKEN}")
        bootstrap_response = connection.getresponse()
        bootstrap_response.read()
        assert bootstrap_response.status == 303
        cookie_header = bootstrap_response.getheader("Set-Cookie")
        assert cookie_header is not None
        cookie = cookie_header.split(";", 1)[0]
        connection.close()

        assert_lifecycle_state(session, "idle")
        body = (FIXTURES / "weapons.csv").read_bytes()
        upload_thread = threading.Thread(
            target=_run_upload,
            args=(port, cookie, body, upload_result, upload_done),
        )
        upload_thread.start()
        assert report_entered.wait(timeout=_WAIT_SECONDS)

        shutdown_thread = threading.Thread(
            target=_run_shutdown,
            args=(port, cookie, shutdown_result, shutdown_done),
        )
        shutdown_thread.start()
        assert shutdown_arrived.wait(timeout=_WAIT_SECONDS)
        assert not shutdown_callback_entered.is_set()

        release_report.set()
        assert upload_done.wait(timeout=_WAIT_SECONDS)
        assert "error" not in upload_result
        assert upload_result["status"] == 200
        assert upload_result["payload"]["state"] == "exports-loaded"
        assert upload_result["payload"]["report_revision"] == 1
        assert shutdown_callback_entered.wait(timeout=_WAIT_SECONDS)
        loaded_state = assert_lifecycle_state(session, "exports-loaded")

        release_shutdown.set()
        assert shutdown_complete.wait(timeout=_WAIT_SECONDS)
        assert shutdown_done.wait(timeout=_WAIT_SECONDS)
        assert "error" not in shutdown_result
        assert shutdown_result["status"] == 200
        assert shutdown_result["payload"]["state"] == loaded_state["state"]
        assert shutdown_result["payload"]["report_revision"] == loaded_state[
            "report_revision"
        ]
        assert shutdown_result["payload"]["fingerprint"] is not None

        upload_thread.join(timeout=_WAIT_SECONDS)
        shutdown_thread.join(timeout=_WAIT_SECONDS)
        assert not upload_thread.is_alive()
        assert not shutdown_thread.is_alive()
        assert events.index("report-start") < events.index("shutdown-arrived")
        assert events.index("shutdown-arrived") < events.index("report-end")
        assert events.index("report-end") < events.index("shutdown-callback-entered")
        assert_lifecycle_state(session, "closed", previous=loaded_state)
        assert list(staging_root.iterdir()) == []
        assert not session._candidate_staging_dirs
        assert not session._retired_staging_dirs
        server_thread.join(timeout=_WAIT_SECONDS)
        assert not server_thread.is_alive()
    finally:
        release_report.set()
        release_shutdown.set()
        if upload_thread is not None:
            upload_thread.join(timeout=_WAIT_SECONDS)
        if shutdown_thread is not None:
            shutdown_thread.join(timeout=_WAIT_SECONDS)
        if server_thread.is_alive():
            server.shutdown()
            server_thread.join(timeout=_WAIT_SECONDS)
        server.server_close()
        session.close()
