"""The spike application: the production app plus the built frontend (#206).

``create_spike_app`` calls the unmodified production ``create_app`` and adds
the built Svelte frontend to its fixed resource allow-list.  Nothing in
``src/vault_cleaner`` is edited, so the production ``before_request`` (Host,
cookie, Origin) and ``after_request`` (``no-store``, the CSP and the other
security headers) cover every spike route.

Routes added, all ``GET``, all from a fixed mapping of path to file name:

* ``/spike/``: the built ``index.html``;
* ``/spike/assets/app.js`` and ``/spike/assets/app.css``: the build's two
  stable-named outputs;
* with ``probes=True`` only, the S7 library probe pages under
  ``/spike/probes/``, listed from the probe build directory at start-up.

No request value ever selects a file.  The slice needs no route of its own:
it reads ``GET /api/report`` and posts to the unmodified mutation routes.

The policy.  ``create_app`` sets the CSP in an ``after_request`` function,
and Flask runs those in reverse order of registration, so nothing registered
here could change the header afterwards.  ``csp_additions`` therefore wraps
``app.wsgi_app`` and rewrites the header **for paths under ``/spike/``
only**, and only with additions from the owner's pre-approved list.  With no
additions (the default, and what the slice uses) the wrapper is not installed
and every response carries production's policy unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from flask import Flask
from werkzeug.serving import BaseWSGIServer, make_server

from vault_cleaner.server.app import (
    DEFAULT_ASSETS,
    LOOPBACK_HOST,
    SERVER_CSP,
    AssetSpec,
    RedactingRequestHandler,
    create_app,
)
from vault_cleaner.server.session import Session

SPIKE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = SPIKE_DIR / "frontend" / "dist"
PROBES_DIST = SPIKE_DIR / "probes" / "dist"
SPIKE_PREFIX = "/spike/"
HTML = "text/html; charset=utf-8"
JS = "text/javascript; charset=utf-8"
CSS = "text/css; charset=utf-8"

# URL path -> (content type, file name relative to the build directory).
SLICE_FILES: Mapping[str, tuple[str, str]] = {
    "/spike/": (HTML, "index.html"),
    "/spike/assets/app.js": (JS, "assets/app.js"),
    "/spike/assets/app.css": (CSS, "assets/app.css"),
}
# The same three files as they would sit, flat, in ``vault_cleaner/ui/``,
# where today's ``package-data`` globs already pick them up (experiment S8).
PACKAGED_NAMES: Mapping[str, str] = {
    "index.html": "review_app.html",
    "assets/app.js": "review_app.js",
    "assets/app.css": "review_app.css",
}
PROBE_NAMES = ("plain", "shadcn", "skeleton", "daisy")
CONTENT_TYPES = {".html": HTML, ".js": JS, ".css": CSS}


def probe_files() -> dict[str, tuple[str, str]]:
    """The probe build's own outputs, listed when the app is created.

    The four probe pages share chunks whose names the bundler chooses, so
    this allow-list is read from the build directory once, at start-up.  A
    file with any other extension is not served.  No request selects a name.
    """
    listed: dict[str, tuple[str, str]] = {}
    for path in sorted(PROBES_DIST.rglob("*")):
        if path.is_file() and path.suffix in CONTENT_TYPES:
            name = path.relative_to(PROBES_DIST).as_posix()
            listed[f"/spike/probes/{name}"] = (CONTENT_TYPES[path.suffix], name)
    return listed


# The owner's pre-approved additions (plan, "The security envelope").
APPROVED_ADDITIONS: Mapping[str, tuple[str, str]] = {
    "img": ("img-src", "img-src 'self' data:"),
    "font": ("font-src", "font-src 'self'"),
    "style-inline": ("style-src", "style-src 'self' 'unsafe-inline'"),
}
# What the slice needs, from experiment S7: nothing.
SLICE_CSP_ADDITIONS: tuple[str, ...] = ()

ReadFile = Callable[[str], bytes]


def directory_source(root: Path) -> ReadFile:
    """Read build outputs from a directory, by allow-listed name only."""

    def read(name: str) -> bytes:
        return (root / name).read_bytes()

    return read


def package_source() -> ReadFile:
    """Read the slice from ``vault_cleaner.ui`` package resources (S8)."""
    resources = files("vault_cleaner.ui")

    def read(name: str) -> bytes:
        return resources.joinpath(PACKAGED_NAMES[name]).read_bytes()

    return read


def policy_with(additions: Iterable[str]) -> str:
    """Production's policy plus pre-approved additions, and nothing else."""
    directives = [part.strip() for part in SERVER_CSP.split(";")]
    for key in additions:
        name, replacement = APPROVED_ADDITIONS[key]
        existing = [index for index, part in enumerate(directives) if part.startswith(name + " ")]
        if existing:
            directives[existing[0]] = replacement
        else:
            directives.append(replacement)
    return "; ".join(directives)


def _provider(read: ReadFile, name: str) -> Callable[[], bytes]:
    def provide() -> bytes:
        return read(name)

    return provide


def spike_assets(read_slice: ReadFile, *, probes: bool) -> dict[str, AssetSpec]:
    """Production's allow-list plus the spike's fixed resources."""
    assets: dict[str, AssetSpec] = dict(DEFAULT_ASSETS)
    for path, (content_type, name) in SLICE_FILES.items():
        assets[path] = (content_type, _provider(read_slice, name))
    if probes:
        read_probe = directory_source(PROBES_DIST)
        for path, (content_type, name) in probe_files().items():
            assets[path] = (content_type, _provider(read_probe, name))
    return assets


class _SpikePolicy:
    """Rewrite the CSP header for ``/spike/`` paths; pass everything else."""

    def __init__(self, wrapped: Any, policy: str) -> None:
        self._wrapped = wrapped
        self._policy = policy

    def __call__(self, environ: dict, start_response: Callable) -> Any:
        if not environ.get("PATH_INFO", "").startswith(SPIKE_PREFIX):
            return self._wrapped(environ, start_response)

        def rewritten(status: str, headers: list, exc_info: Any = None) -> Any:
            replaced = [
                (name, self._policy if name.lower() == "content-security-policy" else value)
                for name, value in headers
            ]
            return start_response(status, replaced, exc_info)

        return self._wrapped(environ, rewritten)


def create_spike_app(
    session: Session,
    *,
    read_slice: ReadFile | None = None,
    probes: bool = False,
    csp_additions: Iterable[str] = SLICE_CSP_ADDITIONS,
) -> Flask:
    """Wrap the production app and serve the built frontend beside it."""
    read = read_slice if read_slice is not None else directory_source(FRONTEND_DIST)
    app = create_app(session, assets=spike_assets(read, probes=probes))
    additions = tuple(csp_additions)
    if additions:
        app.wsgi_app = _SpikePolicy(app.wsgi_app, policy_with(additions))
    return app


def build_spike_server(
    session: Session,
    port: int,
    *,
    read_slice: ReadFile | None = None,
    probes: bool = False,
    csp_additions: Iterable[str] = SLICE_CSP_ADDITIONS,
) -> BaseWSGIServer:
    """``build_server`` for the spike app, with the same origin contract."""
    app = create_spike_app(
        session, read_slice=read_slice, probes=probes, csp_additions=csp_additions
    )
    server = make_server(
        LOOPBACK_HOST, port, app, threaded=True, request_handler=RedactingRequestHandler
    )
    session.configure_bound_port(server.server_port)
    session.shutdown_callback = server.shutdown
    return server
