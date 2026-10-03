"""The spike application: the production app plus Jinja routes (#137).

``create_spike_app`` calls the unmodified production ``create_app`` and then
adds resources and routes to the app it returns.  Nothing in
``src/vault_cleaner`` is edited, so the production ``before_request``
(Host, cookie, Origin) and ``after_request`` (``no-store``, CSP, and the
other security headers) cover every spike route.

Routes added, all ``GET``:

* ``/spike/``: the persistent shell, rendered from ``shell.html``;
* ``/spike/assets/spike.js``, ``/spike/assets/whole.js`` and
  ``/spike/assets/spike.css``: fixed files read from ``static/``;
* ``/spike/fragments/armor-duplicates``: the rendered fragment, with the
  revision header pair;
* ``/spike/whole``: the whole-page shape for experiment E9.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from context import GROUP_KIND_FILTERS, build_context
from flask import Flask, Response, request
from jinja2 import Environment
from render_env import TemplateSource, build_environment
from werkzeug.serving import BaseWSGIServer, make_server

from vault_cleaner.server.app import (
    DEFAULT_ASSETS,
    LOOPBACK_HOST,
    AssetSpec,
    RedactingRequestHandler,
    create_app,
)
from vault_cleaner.server.errors import ApiError
from vault_cleaner.server.session import Session, revision_headers, session_metadata

STATIC = Path(__file__).resolve().parent / "static"
FRAGMENT_PATH = "/spike/fragments/armor-duplicates"
WHOLE_PAGE_PATH = "/spike/whole"
SHELL_PATH = "/spike/"
SPIKE_STATIC = {
    "/spike/assets/spike.js": ("text/javascript; charset=utf-8", "spike.js"),
    "/spike/assets/whole.js": ("text/javascript; charset=utf-8", "whole.js"),
    "/spike/assets/spike.css": ("text/css; charset=utf-8", "spike.css"),
}
SPIKE_ROUTES = (SHELL_PATH, *SPIKE_STATIC, FRAGMENT_PATH, WHOLE_PAGE_PATH)
HTML = "text/html; charset=utf-8"
FILTER_KEYS = frozenset({"kind", "guardian_class"})
MAX_FILTER_VALUE = 200

EnvelopeTransform = Callable[[dict[str, Any]], dict[str, Any]]


def _static(name: str) -> Callable[[], bytes]:
    path = STATIC / name

    def read() -> bytes:
        return path.read_bytes()

    return read


def spike_assets(environment: Environment) -> dict[str, AssetSpec]:
    """Production's allow-list plus the spike's fixed resources."""

    def shell() -> bytes:
        return environment.get_template("shell.html").render().encode("utf-8")

    assets: dict[str, AssetSpec] = dict(DEFAULT_ASSETS)
    assets[SHELL_PATH] = (HTML, shell)
    for path, (content_type, name) in SPIKE_STATIC.items():
        assets[path] = (content_type, _static(name))
    return assets


# [filters-b:start] validated query parameters (experiment E10, candidate b)
def _validated_filters(args: Any) -> dict[str, str]:
    """Accept only the two measured filters, each at most once."""
    if set(args) - FILTER_KEYS:
        raise ApiError("bad_request", 400, "unsupported fragment parameter")
    values: dict[str, str] = {"kind": "all", "guardian_class": ""}
    for key in FILTER_KEYS & set(args):
        supplied = args.getlist(key)
        if len(supplied) != 1 or len(supplied[0]) > MAX_FILTER_VALUE:
            raise ApiError("bad_request", 400, "invalid fragment parameter")
        values[key] = supplied[0]
    if values["kind"] not in GROUP_KIND_FILTERS:
        raise ApiError("bad_request", 400, "invalid fragment parameter")
    return values
# [filters-b:end]


def create_spike_app(
    session: Session,
    *,
    template_source: TemplateSource | None = None,
    transform_envelope: EnvelopeTransform | None = None,
) -> Flask:
    """Wrap the production app.

    ``transform_envelope`` exists for experiment E2 only: it lets the proof
    overlay hostile values on the envelope before the context is built.
    """
    environment = build_environment(template_source)
    app = create_app(session, assets=spike_assets(environment))

    def current() -> tuple[dict[str, Any], Mapping[str, str]]:
        """One coherent envelope and header pair, taken under the lock."""
        with session.mutation_lock:
            if session.closed:
                raise ApiError(
                    "illegal_state", 409, "report is not available after session shutdown"
                )
            envelope = session_metadata(session)
            headers = revision_headers(session)
        if transform_envelope is not None:
            envelope = transform_envelope(envelope)
        return envelope, headers

    def rendered(template: str, filters: Mapping[str, str]) -> Response:
        envelope, headers = current()
        context = build_context(envelope, **filters)
        body = environment.get_template(template).render(**context)
        response = Response(body, content_type=HTML)
        for name, value in headers.items():
            response.headers[name] = value
        return response

    def fragment() -> Response:
        return rendered("armor_duplicates.html", _validated_filters(request.args))

    def whole_page() -> Response:
        if request.args:
            raise ApiError("bad_request", 400, "unsupported page parameter")
        return rendered("whole_page.html", {"kind": "all", "guardian_class": ""})

    app.add_url_rule(
        FRAGMENT_PATH, endpoint="spike_fragment", view_func=fragment, methods=["GET"]
    )
    app.add_url_rule(
        WHOLE_PAGE_PATH, endpoint="spike_whole", view_func=whole_page, methods=["GET"]
    )
    return app


def build_spike_server(
    session: Session,
    port: int,
    *,
    template_source: TemplateSource | None = None,
    transform_envelope: EnvelopeTransform | None = None,
) -> BaseWSGIServer:
    """``build_server`` for the spike app, with the same origin contract."""
    app = create_spike_app(
        session, template_source=template_source, transform_envelope=transform_envelope
    )
    server = make_server(
        LOOPBACK_HOST, port, app, threaded=True, request_handler=RedactingRequestHandler
    )
    session.configure_bound_port(server.server_port)
    session.shutdown_callback = server.shutdown
    return server
