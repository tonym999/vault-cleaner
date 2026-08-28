"""Security and transport contract for the local review server."""

from __future__ import annotations

import http.client
import json
import threading
from collections.abc import Callable, Mapping
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit

import pytest

from vault_cleaner.server import app as server_app
from vault_cleaner.server.app import (
    SESSION_COOKIE_NAME,
    AssetSpec,
    build_server,
    create_app,
)
from vault_cleaner.server.errors import ERROR_REGISTRY, ApiError
from vault_cleaner.server.limits import (
    MAX_EXPORT_BYTES,
    MAX_JSON_BODY_BYTES,
    MAX_REQUEST_BODY_BYTES,
    MAX_TOTAL_EXPORT_BYTES,
)
from vault_cleaner.server.session import (
    BOOTSTRAP_TTL_SECONDS,
    Session,
    session_metadata,
)

TEST_PORT = 43123
TEST_HOST = f"127.0.0.1:{TEST_PORT}"
TEST_ORIGIN = f"http://{TEST_HOST}"
BOOTSTRAP_TOKEN = "bootstrap-secret"
SESSION_TOKEN = "session-secret"

IDLE_METADATA = {
    "schema_version": 1,
    "state": "idle",
    "report_revision": 0,
    "verdict_revision": 0,
    "fingerprint": None,
    "snapshot": None,
    "verdicts": [],
    "override_status": [],
}
CLOSED_METADATA = {
    **IDLE_METADATA,
    "state": "closed",
}


def build_client(
    tmp_path,
    *,
    clock: Callable[[], float] = lambda: 1000.0,
    assets: Mapping[str, AssetSpec] | None = None,
):
    """Build a Flask test client with a test-owned overrides path.

    The session reads ``overrides.json`` from ``tmp_path``. Pass a directory
    owned by the current test to prevent shared override state.
    """
    session = Session(
        overrides_path=str(tmp_path / "overrides.json"),
        clock=clock,
        bootstrap_token=BOOTSTRAP_TOKEN,
        session_token=SESSION_TOKEN,
    )
    session.configure_bound_port(TEST_PORT)
    app = create_app(session, assets=assets)
    app.config["TESTING"] = True
    return app.test_client(), session, app


def bootstrap(client, token: str = BOOTSTRAP_TOKEN):
    return client.get(f"/bootstrap?token={token}", base_url=TEST_ORIGIN)


def session_state(session: Session) -> dict:
    """Capture comparable session state without retaining mutable aliases."""
    return {
        "bootstrap_token": session.bootstrap_token,
        "session_token": session.session_token,
        "bootstrap_issued_at": session.bootstrap_issued_at,
        "bound_port": session.bound_port,
        "shutdown_callback": session.shutdown_callback,
        "metadata": session_metadata(session),
    }


def assert_security_headers(response) -> None:
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'none'"
    )
    assert not any(
        name.casefold().startswith("access-control-")
        for name, _value in response.headers
    )


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    assert set(response.json) == {"error"}
    assert set(response.json["error"]) == {"code", "message"}
    assert response.json["error"]["code"] == code
    assert isinstance(response.json["error"]["message"], str)
    assert response.json["error"]["message"]
    assert_security_headers(response)


def test_bootstrap_is_one_time_and_sets_the_host_only_session_cookie(tmp_path):
    client, session, _app = build_client(tmp_path)

    response = bootstrap(client)

    assert response.status_code == 303
    assert response.headers["Location"] == "/"
    cookie = response.headers["Set-Cookie"]
    assert cookie.startswith("vault_cleaner_session=session-secret;")
    assert "HttpOnly" in cookie
    assert "SameSite=Strict" in cookie
    assert "Path=/" in cookie
    assert "Domain=" not in cookie
    assert session.bootstrap_token is None
    assert_security_headers(response)

    replay = bootstrap(client)
    assert_error(replay, 401, "invalid_bootstrap")
    assert replay.json["error"]["message"].endswith("already been used")


def test_bootstrap_rejects_bad_query_shapes_without_consuming_token(tmp_path):
    client, session, _app = build_client(tmp_path)

    for path in (
        "/bootstrap",
        "/bootstrap?token=",
        "/bootstrap?token=a&token=b",
        "/bootstrap?token=a&extra=b",
    ):
        response = client.get(path, base_url=TEST_ORIGIN)
        if path == "/bootstrap?token=":
            assert_error(response, 401, "invalid_bootstrap")
        else:
            assert_error(response, 400, "bad_request")
        assert session.bootstrap_token == BOOTSTRAP_TOKEN


def test_non_ascii_bootstrap_credential_is_a_normal_auth_failure(tmp_path):
    client, session, _app = build_client(tmp_path)

    response = bootstrap(client, "café")

    assert_error(response, 401, "invalid_bootstrap")
    assert session.bootstrap_token == BOOTSTRAP_TOKEN


@pytest.mark.parametrize("method", ["head", "options"])
def test_only_get_bootstrap_is_exempt_from_authentication(method, tmp_path):
    client, session, _app = build_client(tmp_path)

    response = getattr(client, method)(
        f"/bootstrap?token={BOOTSTRAP_TOKEN}",
        base_url=TEST_ORIGIN,
    )

    if method == "head":
        assert response.status_code == 401
        assert response.data == b""
        assert_security_headers(response)
    else:
        assert_error(response, 401, "authentication_required")
    assert session.bootstrap_token == BOOTSTRAP_TOKEN


def test_authenticated_head_cannot_consume_the_bootstrap_token(tmp_path):
    client, session, _app = build_client(tmp_path)
    client.set_cookie(
        SESSION_COOKIE_NAME,
        SESSION_TOKEN,
        domain="127.0.0.1",
    )

    response = client.head(
        f"/bootstrap?token={BOOTSTRAP_TOKEN}",
        base_url=TEST_ORIGIN,
    )

    assert response.status_code == 404
    assert response.data == b""
    assert_security_headers(response)
    assert session.bootstrap_token == BOOTSTRAP_TOKEN


def test_expired_bootstrap_gives_restart_hint_and_does_not_exit(tmp_path):
    now = [1000.0]
    client, session, _app = build_client(tmp_path, clock=lambda: now[0])
    now[0] += BOOTSTRAP_TTL_SECONDS

    response = bootstrap(client)

    assert_error(response, 401, "expired_bootstrap")
    assert "restart vault-cleaner serve" in response.json["error"]["message"]
    assert session.bootstrap_token == BOOTSTRAP_TOKEN


def test_unauthenticated_routes_are_refused_without_state_change(tmp_path):
    client, session, _app = build_client(tmp_path)
    before = session_state(session)

    for method, path in (("get", "/"), ("get", "/api/report"), ("post", "/api/shutdown")):
        response = getattr(client, method)(
            path,
            base_url=TEST_ORIGIN,
            headers={"Origin": TEST_ORIGIN},
        )
        assert_error(response, 401, "authentication_required")

    assert session_state(session) == before


def test_non_ascii_session_cookie_is_a_normal_auth_failure(tmp_path):
    client, _session, _app = build_client(tmp_path)
    client.set_cookie(
        SESSION_COOKIE_NAME,
        "café",
        domain="127.0.0.1",
    )

    response = client.get("/api/report", base_url=TEST_ORIGIN)

    assert_error(response, 401, "authentication_required")


@pytest.mark.parametrize("path", ["/bootstrap?token=bootstrap-secret", "/api/report"])
def test_wrong_host_is_rejected_before_authentication_and_changes_nothing(path, tmp_path):
    client, session, _app = build_client(tmp_path)
    before = session_state(session)

    response = client.get(path, base_url="http://localhost:43123")

    assert_error(response, 400, "invalid_host")
    assert session_state(session) == before


def test_missing_host_is_rejected_without_consuming_bootstrap(tmp_path):
    client, session, _app = build_client(tmp_path)

    response = client.get(
        f"/bootstrap?token={BOOTSTRAP_TOKEN}",
        base_url=TEST_ORIGIN,
        environ_overrides={"HTTP_HOST": ""},
    )

    assert_error(response, 400, "invalid_host")
    assert session.bootstrap_token == BOOTSTRAP_TOKEN


@pytest.mark.parametrize(
    "path",
    [
        "/api/exports/weapons",
        "/api/exports/armor",
        "/api/exports/ghosts",
        "/api/verdicts",
        "/api/finalize",
        "/api/reset",
        "/api/shutdown",
    ],
)
@pytest.mark.parametrize("origin", [None, "http://localhost:43123", "null"])
def test_every_post_requires_the_exact_origin_without_changing_state(path, origin, tmp_path):
    client, session, _app = build_client(tmp_path)
    assert bootstrap(client).status_code == 303
    before = session_state(session)
    headers = {} if origin is None else {"Origin": origin}

    response = client.post(path, base_url=TEST_ORIGIN, headers=headers)

    assert_error(response, 403, "invalid_origin")
    assert session_state(session) == before


@pytest.mark.parametrize("origin", ["http://localhost:43123", "null"])
def test_get_rejects_a_present_noncanonical_origin(origin, tmp_path):
    client, session, _app = build_client(tmp_path)
    assert bootstrap(client).status_code == 303
    before = session_state(session)

    response = client.get(
        "/api/report",
        base_url=TEST_ORIGIN,
        headers={"Origin": origin},
    )

    assert_error(response, 403, "invalid_origin")
    assert session_state(session) == before


def test_authenticated_root_and_idle_report(tmp_path):
    client, _session, _app = build_client(tmp_path)
    assert bootstrap(client).status_code == 303

    root = client.get("/", base_url=TEST_ORIGIN)
    report = client.get("/api/report", base_url=TEST_ORIGIN)

    assert root.status_code == 200
    assert root.content_type == "text/html; charset=utf-8"
    assert b"vault-cleaner review" in root.data
    assert b"/assets/review.css" in root.data
    assert b"/assets/review_server.js" in root.data
    assert report.status_code == 200
    assert report.json == IDLE_METADATA
    assert_security_headers(root)
    assert_security_headers(report)


def test_default_server_assets_are_packaged_and_allowlisted(tmp_path):
    client, _session, app = build_client(tmp_path)
    assert bootstrap(client).status_code == 303
    expected = {
        "/": ("text/html; charset=utf-8", "review_server.html"),
        "/assets/review.css": ("text/css; charset=utf-8", "review.css"),
        "/assets/review_ui.js": ("text/javascript; charset=utf-8", "review_ui.js"),
        "/assets/review_server.js": (
            "text/javascript; charset=utf-8", "review_server.js"
        ),
    }
    assert {
        rule.rule for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/assets") or rule.rule == "/"
    } == set(expected)
    resources = files("vault_cleaner.ui")
    for path, (content_type, name) in expected.items():
        response = client.get(path, base_url=TEST_ORIGIN)
        assert response.status_code == 200
        assert response.content_type == content_type
        assert response.data == resources.joinpath(name).read_bytes()
        assert_security_headers(response)

    html = client.get("/", base_url=TEST_ORIGIN).get_data(as_text=True)
    assert "<script>" not in html
    assert "<style>" not in html
    assert "<form" not in html.lower()

@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/api/verdicts"),
        ("post", "/api/finalize"),
        ("get", "/api/finalized.csv"),
    ],
)
def test_later_child_routes_use_the_stable_idle_error(method, path, tmp_path):
    client, _session, _app = build_client(tmp_path)
    assert bootstrap(client).status_code == 303

    response = getattr(client, method)(
        path,
        base_url=TEST_ORIGIN,
        headers={"Origin": TEST_ORIGIN},
    )

    assert_error(response, 409, "illegal_state")


@pytest.mark.parametrize(
    "path",
    [
        "/not-allowlisted",
        "/assets/app.js",
        "/assets/%2e%2e/secret",
        "/api/manifest",
        "/api/exports/manifest",
    ],
)
def test_non_allowlisted_traversal_and_manifest_paths_are_404(path, tmp_path):
    client, _session, _app = build_client(tmp_path)
    assert bootstrap(client).status_code == 303

    response = client.get(path, base_url=TEST_ORIGIN)

    assert_error(response, 404, "not_found")


def test_route_table_is_exact_and_has_no_manifest_endpoint(tmp_path):
    _client, _session, app = build_client(tmp_path)
    rules = {rule.rule for rule in app.url_map.iter_rules()}

    assert rules == {
        "/bootstrap",
        "/",
        "/assets/review.css",
        "/assets/review_ui.js",
        "/assets/review_server.js",
        "/api/report",
        "/api/exports/weapons",
        "/api/exports/armor",
        "/api/exports/ghosts",
        "/api/verdicts",
        "/api/finalize",
        "/api/finalized.csv",
        "/api/reset",
        "/api/shutdown",
    }
    assert all("manifest" not in rule for rule in rules)


@pytest.mark.parametrize(
    "path", ["/bootstrap", "/api", "/api/report", "/api/future"]
)
def test_assets_cannot_shadow_reserved_server_routes(path, tmp_path):
    session = Session(overrides_path=str(tmp_path / "overrides.json"))
    session.configure_bound_port(TEST_PORT)

    with pytest.raises(ValueError, match="reserved server route"):
        create_app(session, assets={path: ("text/plain", lambda: b"shadow")})


def test_shutdown_is_serialized_and_runs_only_when_response_closes(tmp_path):
    client, session, app = build_client(tmp_path)
    called = []
    session.shutdown_callback = lambda: called.append(True)
    assert bootstrap(client).status_code == 303

    response = client.post(
        "/api/shutdown",
        base_url=TEST_ORIGIN,
        headers={"Origin": TEST_ORIGIN},
    )

    assert response.status_code == 200
    assert response.json == CLOSED_METADATA
    assert called == []
    response.close()
    assert called == [True]
    assert getattr(
        app.view_functions["shutdown"], "__vault_cleaner_serialized__", False
    )


def test_shutdown_callback_runs_when_close_raises(monkeypatch, tmp_path):
    client, session, _app = build_client(tmp_path)
    events = []
    session.shutdown_callback = lambda: events.append("callback")

    def fail_close():
        events.append("close")
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(session, "close", fail_close)
    assert bootstrap(client).status_code == 303

    response = client.post(
        "/api/shutdown",
        base_url=TEST_ORIGIN,
        headers={"Origin": TEST_ORIGIN},
    )

    with pytest.raises(RuntimeError, match="cleanup failed"):
        response.close()
    assert events == ["close", "callback"]


def test_shutdown_rejects_a_nonempty_body_without_calling_shutdown(tmp_path):
    client, session, _app = build_client(tmp_path)
    called = []
    session.shutdown_callback = lambda: called.append(True)
    assert bootstrap(client).status_code == 303

    response = client.post(
        "/api/shutdown",
        base_url=TEST_ORIGIN,
        headers={"Origin": TEST_ORIGIN},
        data=b"not empty",
    )

    assert_error(response, 400, "bad_request")
    response.close()
    assert called == []


def test_flask_wide_body_cap_returns_the_stable_413_shape(tmp_path):
    client, _session, _app = build_client(tmp_path)
    assert bootstrap(client).status_code == 303

    response = client.post(
        "/api/shutdown",
        base_url=TEST_ORIGIN,
        headers={"Origin": TEST_ORIGIN},
        data=b"x",
        environ_overrides={"CONTENT_LENGTH": str(MAX_REQUEST_BODY_BYTES + 1)},
    )

    assert_error(response, 413, "payload_too_large")


def test_registered_errors_all_produce_the_stable_schema():
    for code, spec in ERROR_REGISTRY.items():
        error = ApiError(code, spec.status, "safe detail")
        assert error.code == code
        assert error.status == spec.status

    with pytest.raises(ValueError, match="unregistered"):
        ApiError("invented", 400, "detail")
    with pytest.raises(ValueError, match="registered as"):
        ApiError("bad_request", 500, "detail")


@pytest.mark.parametrize("code", sorted(ERROR_REGISTRY))
def test_every_registered_error_round_trips_through_the_flask_schema(code, tmp_path):
    spec = ERROR_REGISTRY[code]

    def fail() -> bytes:
        raise ApiError(code, spec.status, "safe detail")

    client, _session, _app = build_client(
        tmp_path,
        assets={"/": ("text/html; charset=utf-8", fail)}
    )
    assert bootstrap(client).status_code == 303

    response = client.get("/", base_url=TEST_ORIGIN)

    assert_error(response, spec.status, code)
    assert response.json["error"]["message"] == "safe detail"


def test_named_limits_and_flask_wide_body_cap_are_pinned(tmp_path):
    _client, _session, app = build_client(tmp_path)

    assert MAX_EXPORT_BYTES == 32 * 1024 * 1024
    assert MAX_TOTAL_EXPORT_BYTES == 96 * 1024 * 1024
    assert MAX_JSON_BODY_BYTES == 1024 * 1024
    assert MAX_REQUEST_BODY_BYTES == MAX_EXPORT_BYTES
    assert app.config["MAX_CONTENT_LENGTH"] == MAX_REQUEST_BODY_BYTES


def test_production_tokens_are_distinct_and_high_entropy(tmp_path):
    session = Session(overrides_path=str(tmp_path / "overrides.json"))

    assert session.bootstrap_token != session.session_token
    assert len(session.bootstrap_token) >= 32
    assert len(session.session_token) >= 32


def test_port_80_uses_the_browser_canonical_host_and_origin(tmp_path):
    session = Session(overrides_path=str(tmp_path / "overrides.json"))

    session.configure_bound_port(80)

    assert session.expected_host == "127.0.0.1"
    assert session.expected_origin == "http://127.0.0.1"


def test_session_metadata_is_a_deep_copy_of_mutable_state(tmp_path):
    session = Session(overrides_path=str(tmp_path / "overrides.json"))
    session.snapshot = {"groups": [{"name": "original"}]}
    session.verdicts = [{"id": "one", "verdict": "keep"}]
    session.override_status = [{"id": "one", "status": "active"}]

    metadata = session_metadata(session)
    metadata["snapshot"]["groups"][0]["name"] = "changed"
    metadata["verdicts"][0]["verdict"] = "junk"
    metadata["override_status"][0]["status"] = "changed"

    assert session.snapshot == {"groups": [{"name": "original"}]}
    assert session.verdicts == [{"id": "one", "verdict": "keep"}]
    assert session.override_status == [{"id": "one", "status": "active"}]


def test_session_metadata_rejects_unknown_state(tmp_path):
    session = Session(overrides_path=str(tmp_path / "overrides.json"))
    session.state = "future-state"

    with pytest.raises(
        RuntimeError, match="session state is outside the schema-v1 vocabulary"
    ):
        session_metadata(session)


def test_sanitized_500_logs_locally_but_leaks_no_path(caplog, tmp_path):
    private_path = "/private/session/staging/export.csv"

    def fail() -> bytes:
        raise OSError(private_path)

    client, _session, _app = build_client(
        tmp_path,
        assets={"/": ("text/html; charset=utf-8", fail)}
    )
    assert bootstrap(client).status_code == 303

    response = client.get("/", base_url=TEST_ORIGIN)

    assert_error(response, 500, "internal_error")
    assert private_path not in response.get_data(as_text=True)
    assert private_path in caplog.text


def test_real_server_binds_loopback_redacts_log_and_stops_after_ack(caplog, tmp_path):
    session = Session(
        overrides_path=str(tmp_path / "overrides.json"),
        bootstrap_token=BOOTSTRAP_TOKEN,
        session_token=SESSION_TOKEN,
    )
    server = build_server(session, 0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", session.bound_port, timeout=5)

    try:
        assert server.server_address[0] == "127.0.0.1"
        assert session.bound_port != 0

        connection.request("GET", f"/bootstrap?token={BOOTSTRAP_TOKEN}")
        boot = connection.getresponse()
        boot.read()
        assert boot.status == 303
        cookie = boot.getheader("Set-Cookie").split(";", 1)[0]

        connection.request("GET", "/", headers={"Cookie": cookie})
        root = connection.getresponse()
        root.read()
        assert root.status == 200

        connection.request(
            "POST",
            "/api/shutdown",
            body=b"",
            headers={
                "Cookie": cookie,
                "Origin": session.expected_origin,
                "Content-Length": "0",
            },
        )
        shutdown = connection.getresponse()
        payload = json.loads(shutdown.read())
        assert shutdown.status == 200
        assert payload == CLOSED_METADATA
        thread.join(timeout=5)
        assert not thread.is_alive()

        log = caplog.text
        assert BOOTSTRAP_TOKEN not in log
        assert log.count("/bootstrap?[REDACTED]") == 1
        assert '"GET / HTTP/1.1" 200' in log
    finally:
        connection.close()
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
        server.server_close()


def test_run_server_prints_a_bootstrap_url_that_works(monkeypatch, tmp_path):
    servers = []
    original_build_server = server_app.build_server

    def capture_server(session, port, *, assets=None, once=False):
        assert once is False
        assert assets is server_app.DEFAULT_ASSETS
        server = original_build_server(session, port, assets=assets, once=once)
        servers.append(server)
        return server

    class SignalledOutput:
        def __init__(self):
            self.parts = []
            self.ready = threading.Event()

        def write(self, value):
            self.parts.append(value)
            if "\n" in value:
                self.ready.set()
            return len(value)

        def flush(self):
            pass

        def value(self):
            return "".join(self.parts).strip()

    monkeypatch.setattr(server_app, "build_server", capture_server)
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    output = SignalledOutput()
    result = []
    thread = threading.Thread(
        target=lambda: result.append(
            server_app.run_server(
                config_path=str(config_path),
                overrides_path=str(tmp_path / "overrides.json"),
                no_wishlists=True,
                port=0,
                stdout=output,
            )
        )
    )
    thread.start()
    connection = None

    try:
        assert output.ready.wait(timeout=5)
        url = urlsplit(output.value())
        assert url.scheme == "http"
        assert url.hostname == "127.0.0.1"
        assert url.port not in (None, 0)
        assert url.path == "/bootstrap"
        token = parse_qs(url.query, strict_parsing=True)["token"]
        assert len(token) == 1

        connection = http.client.HTTPConnection(url.hostname, url.port, timeout=5)
        connection.request("GET", f"{url.path}?{url.query}")
        boot = connection.getresponse()
        boot.read()
        assert boot.status == 303
        cookie = boot.getheader("Set-Cookie").split(";", 1)[0]

        connection.request(
            "POST",
            "/api/shutdown",
            body=b"",
            headers={
                "Cookie": cookie,
                "Origin": f"http://{url.netloc}",
                "Content-Length": "0",
            },
        )
        shutdown = connection.getresponse()
        shutdown.read()
        assert shutdown.status == 200
        thread.join(timeout=5)
        assert not thread.is_alive()
        assert result == [0]
    finally:
        if connection is not None:
            connection.close()
        if thread.is_alive() and servers:
            servers[0].shutdown()
            thread.join(timeout=5)
