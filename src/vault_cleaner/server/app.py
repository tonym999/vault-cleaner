"""Flask application and loopback server lifecycle."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TextIO

import pandas as pd
from flask import Flask, Response, current_app, jsonify, redirect, request
from werkzeug.exceptions import BadRequest, HTTPException, RequestEntityTooLarge
from werkzeug.serving import BaseWSGIServer, WSGIRequestHandler, make_server

from vault_cleaner.config import load_config
from vault_cleaner.export_discovery import EXPORT_FILENAMES
from vault_cleaner.manifest import load_perk_map_data
from vault_cleaner.parse import (
    ExportDecodeError,
    load_armor_bytes,
    load_ghosts_bytes,
    load_weapons_bytes,
)
from vault_cleaner.report_run import run_report, snapshot_dict
from vault_cleaner.review import (
    DEFAULT_OVERRIDES_PATH,
    ReviewManifestError,
    check_keys,
    require_id,
    require_text,
)
from vault_cleaner.review_session import retain_verdicts
from vault_cleaner.server.errors import ApiError, error_payload
from vault_cleaner.server.limits import (
    MAX_EXPORT_BYTES,
    MAX_JSON_BODY_BYTES,
    MAX_REQUEST_BODY_BYTES,
    MAX_TOTAL_EXPORT_BYTES,
)
from vault_cleaner.server.session import (
    SESSION_EXTENSION_KEY,
    Session,
    check_expected_revisions,
    order_verdicts,
    proposal_ids_in_order,
    revision_headers,
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
UPLOAD_LOADERS = {
    "weapons": load_weapons_bytes,
    "armor": load_armor_bytes,
    "ghosts": load_ghosts_bytes,
}
UPLOAD_STATES = frozenset({"idle", "exports-loaded", "reviewing"})
MAX_VERDICT_ENTRIES = 50_000
VERDICT_ROOT_KEYS = frozenset(
    {"report_revision", "verdict_revision", "fingerprint", "decisions"}
)
RESET_ROOT_KEYS = frozenset({"report_revision", "verdict_revision"})
VERDICT_ENTRY_KEYS = frozenset({"id", "verdict"})
DEFAULT_ASSETS: Mapping[str, AssetSpec] = {
    "/": ("text/html; charset=utf-8", lambda: PLACEHOLDER_HTML.encode("utf-8")),
}


def _validate_upload_content_length(raw_length: str | None) -> int:
    """Validate an upload length without reading or allocating its body."""
    if (
        raw_length is None
        or not raw_length.isascii()
        or not raw_length.isdigit()
    ):
        raise ApiError(
            "length_required",
            411,
            "upload requires a numeric Content-Length",
        )
    content_length = int(raw_length)
    if content_length > MAX_EXPORT_BYTES:
        raise ApiError(
            "payload_too_large",
            413,
            "export exceeds the allowed size",
        )
    return content_length


def _validate_total_export_size(
    sizes: Mapping[str, int], kind: str, size: int, limit: int
) -> dict[str, int]:
    """Return candidate per-kind sizes or reject the aggregate cap."""
    candidate_sizes = dict(sizes)
    candidate_sizes[kind] = size
    if sum(candidate_sizes.values()) > limit:
        raise ApiError(
            "payload_too_large",
            413,
            "combined exports exceed the allowed size",
        )
    return candidate_sizes


def _load_json_object(body: bytes, where: str) -> dict[str, object]:
    """Decode one bounded JSON object without exposing filesystem details."""
    if len(body) > MAX_JSON_BODY_BYTES:
        raise ApiError("payload_too_large", 413, "JSON request exceeds the allowed size")
    try:
        text = body.decode("utf-8")
        value = json.loads(text, parse_constant=_reject_json_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise ApiError("bad_request", 400, f"{where} must be valid JSON") from None
    if not isinstance(value, dict):
        raise ApiError("bad_request", 400, f"{where} must be a JSON object")
    return value


def _reject_json_constant(constant: str) -> object:
    raise ValueError(f"non-finite JSON value {constant}")


def _json_body(where: str) -> dict[str, object]:
    if request.content_length is not None and request.content_length > MAX_JSON_BODY_BYTES:
        raise ApiError("payload_too_large", 413, "JSON request exceeds the allowed size")
    return _load_json_object(request.get_data(cache=False, as_text=False), where)


def _require_revision(data: Mapping[str, object], key: str, where: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ApiError("bad_request", 400, f"{where}: {key!r} must be an integer")
    if value < 0:
        raise ApiError("bad_request", 400, f"{where}: {key!r} must not be negative")
    return value


def _validate_verdict_payload_data(
    payload: Mapping[str, object],
) -> tuple[int, int, str, list[dict[str, object]]]:
    """Validate payload shape before report-dependent stale checks."""
    try:
        check_keys(payload, VERDICT_ROOT_KEYS, ReviewManifestError, "verdict request")
        report_revision = _require_revision(payload, "report_revision", "verdict request")
        verdict_revision = _require_revision(payload, "verdict_revision", "verdict request")
        fingerprint = require_text(
            payload, "fingerprint", ReviewManifestError, "verdict request"
        )
        raw_decisions = payload.get("decisions")
        if not isinstance(raw_decisions, list):
            raise ReviewManifestError("verdict request: 'decisions' must be a list")
        if len(raw_decisions) > MAX_VERDICT_ENTRIES:
            raise ReviewManifestError("verdict request contains too many decisions")
        decisions: list[dict[str, object]] = []
        seen: set[str] = set()
        for index, raw_entry in enumerate(raw_decisions):
            where = f"verdict request: decisions[{index}]"
            if not isinstance(raw_entry, dict):
                raise ReviewManifestError(f"{where}: must be an object")
            check_keys(raw_entry, VERDICT_ENTRY_KEYS, ReviewManifestError, where)
            item_id = require_id(raw_entry, ReviewManifestError, where)
            if item_id in seen:
                raise ReviewManifestError(f"{where}: id appears twice")
            seen.add(item_id)
            if "verdict" not in raw_entry:
                raise ReviewManifestError(f"{where}: missing 'verdict'")
            verdict = raw_entry["verdict"]
            if verdict is not None:
                require_text(raw_entry, "verdict", ReviewManifestError, where)
                if verdict not in {"approved", "vetoed"}:
                    raise ReviewManifestError(
                        f"{where}: verdict must be approved, vetoed, or null"
                    )
            decisions.append({"id": item_id, "verdict": verdict})
        return report_revision, verdict_revision, fingerprint, decisions
    except ReviewManifestError:
        raise ApiError("bad_request", 400, "verdict request contains invalid fields") from None


def _validate_current_verdict_ids(
    decisions: list[dict[str, object]], proposal_ids: set[str]
) -> None:
    """Apply report-dependent count and id checks after stale preconditions."""
    if len(decisions) > len(proposal_ids):
        raise ApiError(
            "bad_request", 400, "verdict request contains invalid fields"
        )
    if any(entry["id"] not in proposal_ids for entry in decisions):
        raise ApiError(
            "bad_request", 400, "verdict request contains invalid fields"
        )


class RedactingRequestHandler(WSGIRequestHandler):
    """Werkzeug request logger that never records a bootstrap query string."""

    _BOOTSTRAP_QUERY = re.compile(r"(?i)(/bootstrap)\?[^ ]*")

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        request_line = self._BOOTSTRAP_QUERY.sub(r"\1?[REDACTED]", self.requestline)
        self.log("info", '"%s" %s %s', request_line, code, size)


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
            raise ApiError(
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
                raise ApiError(
                    "authentication_required",
                    401,
                    "authentication required; restart vault-cleaner serve and open its URL",
                )

        origin = request.headers.get("Origin")
        if origin is not None and origin != session.expected_origin:
            raise ApiError(
                "invalid_origin",
                403,
                f"Origin must be exactly {session.expected_origin}",
            )
        if request.method == "POST" and origin is None:
            raise ApiError(
                "invalid_origin",
                403,
                f"Origin must be exactly {session.expected_origin}",
            )

    @app.after_request
    def secure_response(response: Response) -> Response:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        return response

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError) -> tuple[Response, int]:
        response = jsonify(error_payload(error.code, error.message))
        if error.code in {"stale_report", "stale_verdicts"}:
            for name, value in revision_headers(session).items():
                response.headers[name] = value
        return response, error.status

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
        # Flask implicitly adds HEAD to GET routes. Keep this check so an
        # authenticated HEAD cannot consume or probe the bootstrap credential.
        if request.method != "GET":
            raise ApiError("not_found", 404, "route or asset not found")
        if set(request.args) != {"token"} or len(request.args.getlist("token")) != 1:
            raise ApiError(
                "bad_request",
                400,
                "bootstrap requires exactly one token query parameter",
            )
        candidate = request.args["token"]
        result = session.exchange_bootstrap(candidate)
        if result == "expired":
            raise ApiError(
                "expired_bootstrap",
                401,
                "bootstrap token expired; restart vault-cleaner serve and open its new URL",
            )
        if result != "ok":
            raise ApiError(
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
        if path == "/bootstrap" or path == "/api" or path.startswith("/api/"):
            raise ValueError(f"asset path uses a reserved server route: {path!r}")

        def serve_asset() -> Response:
            return Response(provider(), content_type=content_type)

        app.add_url_rule(
            path,
            endpoint=f"asset_{index}",
            view_func=serve_asset,
            methods=["GET"],
        )

    @app.get("/api/report")
    def report() -> Response:
        with session.mutation_lock:
            if session.closed:
                raise ApiError(
                    "illegal_state",
                    409,
                    "report is not available after session shutdown",
                )
            return jsonify(session_metadata(session))

    def unavailable() -> None:
        raise ApiError(
            "illegal_state",
            409,
            "operation is not available in the idle session",
        )

    def _reject_upload_transport() -> bytes:
        """Read exactly one bounded request body with an explicit length."""
        if "Transfer-Encoding" in request.headers:
            raise ApiError(
                "length_required",
                411,
                "chunked transfer encoding is not supported; send Content-Length",
            )
        content_length = _validate_upload_content_length(
            request.headers.get("Content-Length")
        )
        body = request.get_data(cache=False, as_text=False)
        if len(body) != content_length:
            raise ApiError("bad_request", 400, "upload body length does not match Content-Length")
        return body

    def _construct_upload(kind: str, body: bytes) -> tuple[list[str], list[str]]:
        """Build a report in a private candidate directory, then commit it."""
        if session.closed:
            raise ApiError(
                "illegal_state",
                409,
                "export upload is not available after session shutdown",
            )
        digest = hashlib.sha256(body).hexdigest()
        size = len(body)
        if session.export_digests.get(kind) == digest:
            current = order_verdicts(session, session.verdicts)
            return (
                [entry["id"] for entry in current],
                [],
            )

        candidate_sizes = _validate_total_export_size(
            session.export_sizes, kind, size, MAX_TOTAL_EXPORT_BYTES
        )
        candidate = Path(
            tempfile.mkdtemp(prefix="vault-cleaner-uploads-")
        )
        try:
            session.track_candidate(candidate)
        except RuntimeError:
            # A close cannot race the serialized upload, but keep this guard
            # beside allocation so a future caller cannot leak a candidate.
            session.cleanup_directory(candidate, candidate=True)
            raise ApiError(
                "illegal_state",
                409,
                "export upload is not available after session shutdown",
            ) from None

        # Everything through snapshot construction is pre-commit work.  Once
        # adopt_candidate succeeds, the candidate is live and must never be
        # removed by rollback handling.
        try:
            candidate_digests = dict(session.export_digests)
            candidate_digests[kind] = digest

            for existing_kind in session.export_digests:
                if existing_kind == kind:
                    continue
                source = session.staging_dir
                if source is None:
                    raise RuntimeError("accepted export has no staging directory")
                shutil.copyfile(
                    source / EXPORT_FILENAMES[existing_kind],
                    candidate / EXPORT_FILENAMES[existing_kind],
                )
            (candidate / EXPORT_FILENAMES[kind]).write_bytes(body)

            try:
                candidate_report = run_report(
                    input_dir=candidate,
                    config_path=session.config_path,
                    no_wishlists=session.no_wishlists,
                )
            except Exception:
                current_app.logger.exception("report construction failed for uploaded %s export", kind)
                raise ApiError(
                    "report_failed",
                    500,
                    "could not construct a report from the uploaded exports",
                ) from None

            # Finish all candidate-derived computation before changing any
            # live session field. The normal snapshot is pure, but keeping it
            # on the candidate side preserves the transaction if that
            # presentation step ever gains a new failure mode.
            candidate_snapshot = snapshot_dict(candidate_report)
            if session.report is None:
                retained_entries: list[dict[str, str]] = []
                discarded_ids: list[str] = []
            else:
                retention = retain_verdicts(
                    session.verdicts, session.report, candidate_report
                )
                retained_entries = [dict(entry) for entry in retention.retained]
                discarded_ids = list(retention.discarded_ids)
            candidate_verdicts = {
                entry["id"]: entry for entry in retained_entries
            }
            candidate_ordered_verdicts = [
                candidate_verdicts[item_id]
                for item_id in (
                    decision.id
                    for section in candidate_report.sections
                    for decision in section.decisions
                )
                if item_id in candidate_verdicts
            ]
            old_verdict_map = {
                entry["id"]: entry["verdict"] for entry in session.verdicts
            }
            new_verdict_map = {
                entry["id"]: entry["verdict"]
                for entry in candidate_ordered_verdicts
            }
            verdict_set_changed = old_verdict_map != new_verdict_map
        except BaseException:
            session.cleanup_directory(candidate, candidate=True)
            raise

        previous = session.adopt_candidate(candidate)
        session.report = candidate_report
        session.export_digests = candidate_digests
        session.export_sizes = candidate_sizes
        session.report_revision += 1
        session.verdicts = candidate_ordered_verdicts
        if verdict_set_changed:
            session.verdict_revision += 1
        session.state = "reviewing" if session.verdicts else "exports-loaded"
        session.fingerprint = candidate_report.fingerprint
        # Keep the compatibility fields coherent without making them the
        # source of truth; /api/report derives from the ReportRun.
        session.snapshot = candidate_snapshot

        if previous is not None:
            # Retirement is post-commit housekeeping.  It is deliberately
            # outside the rollback span so an injected cleanup failure cannot
            # delete the newly adopted directory or corrupt live metadata.
            try:
                session.retire_directory(previous)
            except Exception:
                current_app.logger.exception("retiring the previous upload directory failed")
                session.track_retired(previous)
        return (
            [entry["id"] for entry in candidate_ordered_verdicts],
            discarded_ids,
        )

    def upload(kind: str) -> Response:
        if session.closed:
            raise ApiError(
                "illegal_state",
                409,
                "export upload is not available after session shutdown",
            )
        if session.state not in UPLOAD_STATES:
            raise ApiError(
                "illegal_state",
                409,
                "export upload is not available in the current session state",
            )
        content_type = request.mimetype
        if content_type not in {"text/csv", "application/octet-stream"}:
            raise ApiError(
                "unsupported_media_type",
                415,
                "export Content-Type must be text/csv or application/octet-stream",
            )
        body = _reject_upload_transport()
        try:
            UPLOAD_LOADERS[kind](body)
        except ExportDecodeError:
            raise ApiError("bad_request", 400, "export is not valid UTF-8") from None
        except (ValueError, pd.errors.ParserError):
            raise ApiError("invalid_export", 422, "export CSV or schema is invalid") from None
        retained_ids, discarded_ids = _construct_upload(kind, body)
        payload = session_metadata(session)
        payload["retained_verdict_ids"] = retained_ids
        payload["discarded_verdict_ids"] = discarded_ids
        return jsonify(payload)

    def serialized_upload(kind: str) -> Callable[[], Response]:
        @serialized
        def handler() -> Response:
            return upload(kind)

        return handler

    def _validate_verdict_payload() -> tuple[int, int, str, list[dict[str, object]]]:
        payload = _json_body("verdict request")
        return _validate_verdict_payload_data(payload)

    @serialized
    def verdicts() -> Response:
        if session.closed or session.report is None or session.state not in UPLOAD_STATES:
            raise ApiError(
                "illegal_state", 409, "verdicts are not available in the current session state"
            )
        report_revision, verdict_revision, fingerprint, decisions = (
            _validate_verdict_payload()
        )
        check_expected_revisions(
            session,
            report_revision,
            expected_verdict_revision=verdict_revision,
            fingerprint=fingerprint,
        )
        _validate_current_verdict_ids(decisions, set(proposal_ids_in_order(session)))
        current = {entry["id"]: entry["verdict"] for entry in session.verdicts}
        changed = False
        for entry in decisions:
            item_id = entry["id"]
            verdict = entry["verdict"]
            if verdict is None:
                if item_id in current:
                    del current[item_id]
                    changed = True
            elif current.get(item_id) != verdict:
                current[item_id] = verdict
                changed = True
        if changed:
            session.verdict_revision += 1
            entries = [
                {"id": item_id, "verdict": verdict}
                for item_id, verdict in current.items()
            ]
            session.verdicts = order_verdicts(session, entries)
            session.state = "reviewing" if session.verdicts else "exports-loaded"
        payload = session_metadata(session)
        payload["verdicts"] = order_verdicts(session, session.verdicts)
        return jsonify(payload)

    @serialized
    def reset() -> Response:
        payload = _json_body("reset request")
        try:
            check_keys(payload, RESET_ROOT_KEYS, ReviewManifestError, "reset request")
        except ReviewManifestError:
            raise ApiError("bad_request", 400, "reset request contains invalid fields") from None
        if session.closed:
            raise ApiError("illegal_state", 409, "session is closed")
        report_revision = _require_revision(payload, "report_revision", "reset request")
        verdict_revision = _require_revision(payload, "verdict_revision", "reset request")
        check_expected_revisions(
            session,
            report_revision,
            expected_verdict_revision=verdict_revision,
        )
        had_report = session.report is not None or bool(session.export_digests)
        had_verdicts = bool(session.verdicts)
        if had_report:
            session.report_revision += 1
        if had_verdicts:
            session.verdict_revision += 1
        session.reset_live_state()
        return jsonify(session_metadata(session))

    for kind in ("weapons", "armor", "ghosts"):
        handler = serialized_upload(kind)
        app.add_url_rule(
            f"/api/exports/{kind}",
            endpoint=f"upload_{kind}",
            view_func=handler,
            methods=["POST"],
        )
    app.add_url_rule(
        "/api/verdicts", endpoint="verdicts", view_func=verdicts, methods=["POST"]
    )

    @serialized
    def finalize() -> Response:
        unavailable()

    app.add_url_rule(
        "/api/finalize", endpoint="finalize", view_func=finalize, methods=["POST"]
    )
    app.add_url_rule(
        "/api/finalized.csv",
        endpoint="finalized_csv",
        view_func=unavailable,
        methods=["GET"],
    )
    app.add_url_rule(
        "/api/reset", endpoint="reset", view_func=reset, methods=["POST"]
    )

    @app.post("/api/shutdown")
    @serialized
    def shutdown() -> Response:
        if request.get_data(cache=False):
            raise ApiError("bad_request", 400, "shutdown request body must be empty")
        # Invalidate in-memory state before creating the acknowledgement.  The
        # callback performs retryable physical cleanup and stops the socket.
        session.mark_closed()
        response = jsonify(session_metadata(session))
        response.call_on_close(session.request_shutdown)
        return response

    for asset_index, (asset_path, (content_type, provider)) in enumerate(
        asset_map.items()
    ):
        add_asset(asset_path, content_type, provider, asset_index)

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
    session: Session | None = None
    server: BaseWSGIServer | None = None
    try:
        session = Session(
            overrides_path=overrides_path,
            config_path=config_path,
            no_wishlists=no_wishlists,
        )
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
        if session is not None:
            try:
                session.close()
            finally:
                if server is not None:
                    server.server_close()
        elif server is not None:
            server.server_close()
    return 0
