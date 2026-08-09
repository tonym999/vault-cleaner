"""Flask application and loopback server lifecycle."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Mapping
from typing import Any, TextIO

from flask import Flask, Response, jsonify, redirect, request
from werkzeug.exceptions import BadRequest, HTTPException, RequestEntityTooLarge
from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler, make_server

from vault_cleaner.config import load_config
from vault_cleaner.manifest import load_perk_map_data
from vault_cleaner.review import DEFAULT_OVERRIDES_PATH
from vault_cleaner.server.errors import ApiError, error_payload
from vault_cleaner.server.limits import MAX_REQUEST_BODY_BYTES
from vault_cleaner.server.session import (
    SESSION_EXTENSION_KEY,
    Session,
    serialized,
    session_metadata,
)
from vault_cleaner.wishlist import load_all_with_sources

LOOPBACK_HOST = "127.0.0.1"
SESSION_COOKIE_NAME = "vault_cleaner_session"

PLACEHOLDER_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vault Cleaner</title>
</head>
<body>
  <main>
    <h1>Vault Cleaner</h1>
    <p>The local review server is ready. The review interface arrives in a later update.</p>
  </main>
</body>
</html>
"""

AssetProvider = Callable[[], bytes]
AssetSpec = tuple[str, AssetProvider]
DEFAULT_ASSETS: Mapping[str, AssetSpec] = {
    "/": ("text/html; charset=utf-8", lambda: PLACEHOLDER_HTML.encode("utf-8")),
}


class RedactingRequestHandler(WSGIRequestHandler):
    """Werkzeug request logger that never records a bootstrap query string."""

    _BOOTSTRAP_QUERY = re.compile(r"(?i)(/bootstrap)\?[^ ]*")

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        request_line = self._BOOTSTRAP_QUERY.sub(r"\1?[REDACTED]", self.requestline)
        self.log("info", '"%s" %s %s', request_line, code, size)


def _api_error(code: str, status: int, message: str) -> ApiError:
    return ApiError(code, status, message)


def create_app(
    session: Session,
    *,
    assets: Mapping[str, AssetSpec] | None = None,
) -> Flask:
    """Build the authenticated application around one session."""
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BODY_BYTES
    app.extensions[SESSION_EXTENSION_KEY] = session
    asset_map = dict(DEFAULT_ASSETS if assets is None else assets)

    @app.before_request
    def enforce_request_envelope() -> None:
        if request.headers.get("Host") != session.expected_host:
            raise _api_error(
                "invalid_host",
                400,
                f"Host must be exactly {session.expected_host}",
            )

        is_bootstrap_exchange = (
            request.endpoint == "bootstrap" and request.method == "GET"
        )
        if not is_bootstrap_exchange:
            supplied = request.cookies.get(SESSION_COOKIE_NAME)
            if not session.authenticated(supplied):
                raise _api_error(
                    "authentication_required",
                    401,
                    "authentication required; restart vault-cleaner serve and open its URL",
                )

        if (
            request.method == "POST"
            and request.headers.get("Origin") != session.expected_origin
        ):
            raise _api_error(
                "invalid_origin",
                403,
                f"Origin must be exactly {session.expected_origin}",
            )

    @app.after_request
    def secure_response(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple[Response, int]:
        return jsonify(error_payload(error.code, error.message)), error.status

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error: RequestEntityTooLarge) -> tuple[Response, int]:
        payload = error_payload("payload_too_large", "request body exceeds the allowed limit")
        return jsonify(payload), 413

    @app.errorhandler(BadRequest)
    def handle_bad_request(_error: BadRequest) -> tuple[Response, int]:
        return jsonify(error_payload("bad_request", "malformed request")), 400

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> tuple[Response, int]:
        if error.code in {404, 405}:
            return jsonify(error_payload("not_found", "route or asset not found")), 404
        app.logger.error("unexpected HTTP error %s: %s", error.code, error)
        return jsonify(error_payload("internal_error", "internal server error")), 500

    @app.errorhandler(Exception)
    def handle_internal_error(error: Exception) -> tuple[Response, int]:
        app.logger.exception("unhandled server error")
        return jsonify(error_payload("internal_error", "internal server error")), 500

    @app.get("/bootstrap", endpoint="bootstrap")
    def bootstrap() -> Response:
        if request.method != "GET":
            raise _api_error("not_found", 404, "route or asset not found")
        if set(request.args) != {"token"} or len(request.args.getlist("token")) != 1:
            raise _api_error(
                "bad_request",
                400,
                "bootstrap requires exactly one token query parameter",
            )
        candidate = request.args["token"]
        result = session.exchange_bootstrap(candidate)
        if result == "expired":
            raise _api_error(
                "expired_bootstrap",
                401,
                "bootstrap token expired; restart vault-cleaner serve and open its new URL",
            )
        if result != "ok":
            raise _api_error(
                "invalid_bootstrap",
                401,
                "bootstrap token is invalid or has already been used",
            )
        response = redirect("/", code=303)
        response.set_cookie(
            SESSION_COOKIE_NAME,
            session.session_token,
            httponly=True,
            samesite="Strict",
            path="/",
        )
        return response

    def add_asset(path: str, content_type: str, provider: AssetProvider, index: int) -> None:
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError(f"asset path must be absolute and host-local: {path!r}")

        def serve_asset() -> Response:
            return Response(provider(), content_type=content_type)

        app.add_url_rule(
            path,
            endpoint=f"asset_{index}",
            view_func=serve_asset,
            methods=["GET"],
        )

    for asset_index, (asset_path, (content_type, provider)) in enumerate(
        asset_map.items()
    ):
        add_asset(asset_path, content_type, provider, asset_index)

    @app.get("/api/report")
    def report() -> Response:
        return jsonify(session_metadata(session))

    def unavailable() -> None:
        raise _api_error(
            "illegal_state",
            409,
            "operation is not available in the idle session",
        )

    for kind in ("weapons", "armor", "ghosts"):
        app.add_url_rule(
            f"/api/exports/{kind}",
            endpoint=f"upload_{kind}",
            view_func=unavailable,
            methods=["POST"],
        )
    app.add_url_rule(
        "/api/verdicts", endpoint="verdicts", view_func=unavailable, methods=["POST"]
    )
    app.add_url_rule(
        "/api/finalize", endpoint="finalize", view_func=unavailable, methods=["POST"]
    )
    app.add_url_rule(
        "/api/finalized.csv",
        endpoint="finalized_csv",
        view_func=unavailable,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/reset", endpoint="reset", view_func=unavailable, methods=["POST"]
    )

    @app.post("/api/shutdown")
    @serialized
    def shutdown() -> Response:
        if request.get_data(cache=False):
            raise _api_error("bad_request", 400, "shutdown request body must be empty")
        response = jsonify(session_metadata(session))
        response.call_on_close(session.request_shutdown)
        return response

    return app


def prewarm(config_path: str) -> dict[str, Any]:
    """Populate external wishlist inputs before any socket is bound."""
    cfg = load_config(config_path)
    if not cfg["wishlists"]["sources"]:
        return cfg
    load_all_with_sources(cfg)
    load_perk_map_data(
        cfg["paths"]["manifest_cache_dir"],
        cfg["manifest"]["max_age_days"],
    )
    return cfg


def build_server(
    session: Session,
    port: int,
    *,
    assets: Mapping[str, AssetSpec] | None = None,
) -> BaseWSGIServer:
    """Bind the threaded Werkzeug server and finish the origin contract."""
    app = create_app(session, assets=assets)
    server = make_server(
        LOOPBACK_HOST,
        port,
        app,
        threaded=True,
        request_handler=RedactingRequestHandler,
    )
    session.configure_bound_port(server.server_port)
    session.shutdown_callback = server.shutdown
    return server


def run_server(
    *,
    config_path: str,
    overrides_path: str = DEFAULT_OVERRIDES_PATH,
    no_wishlists: bool,
    port: int,
    stdout: TextIO | None = None,
) -> int:
    """Pre-warm, bind, print the bootstrap URL, and serve until stopped."""
    if not no_wishlists:
        prewarm(config_path)
    else:
        load_config(config_path)

    output = stdout if stdout is not None else sys.stdout
    session = Session(
        overrides_path=overrides_path,
        config_path=config_path,
        no_wishlists=no_wishlists,
    )
    server: BaseWSGIServer | None = None
    try:
        server = build_server(session, port)
        print(
            f"http://{session.expected_host}/bootstrap?token={session.bootstrap_token}",
            file=output,
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    finally:
        session.close()
        if server is not None:
            server.server_close()
    return 0
