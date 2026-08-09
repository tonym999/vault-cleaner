"""Single-session state and mutation serialization primitives."""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from functools import wraps
from threading import RLock
from typing import Any

from flask import current_app

BOOTSTRAP_TTL_SECONDS = 5 * 60
SESSION_EXTENSION_KEY = "vault_cleaner_session"


class Session:
    """Mutable state for exactly one authenticated local review session."""

    def __init__(
        self,
        *,
        overrides_path: str,
        config_path: str = "config.toml",
        no_wishlists: bool = False,
        clock: Callable[[], float] = time.monotonic,
        bootstrap_token: str | None = None,
        session_token: str | None = None,
    ) -> None:
        self.overrides_path = overrides_path
        self.config_path = config_path
        self.no_wishlists = no_wishlists
        self.clock = clock
        self.bootstrap_token = bootstrap_token or secrets.token_urlsafe(32)
        self.session_token = session_token or secrets.token_urlsafe(32)
        self.bootstrap_issued_at = clock()
        self.bound_port: int | None = None
        self.mutation_lock = RLock()
        self.shutdown_callback: Callable[[], None] | None = None

        self.state = "idle"
        self.report_revision = 0
        self.verdict_revision = 0
        self.fingerprint: str | None = None
        self.snapshot: dict[str, Any] | None = None
        self.verdicts: list[dict[str, str]] = []
        self.override_status: list[dict[str, str]] = []

    @property
    def expected_host(self) -> str:
        if self.bound_port is None:
            raise RuntimeError("session has not been bound to a port")
        return f"127.0.0.1:{self.bound_port}"

    @property
    def expected_origin(self) -> str:
        return f"http://{self.expected_host}"

    def configure_bound_port(self, port: int) -> None:
        if self.bound_port is not None:
            raise RuntimeError("session port is already configured")
        self.bound_port = port

    def exchange_bootstrap(self, candidate: str) -> str:
        """Consume the bootstrap credential atomically.

        Returns ``ok``, ``invalid``, or ``expired``. The comparison remains
        constant-time while the live token exists, and concurrent successful
        exchanges are prevented by the same session lock later mutations use.
        """
        with self.mutation_lock:
            token = self.bootstrap_token
            if token is None or not secrets.compare_digest(candidate, token):
                return "invalid"
            if self.clock() - self.bootstrap_issued_at >= BOOTSTRAP_TTL_SECONDS:
                return "expired"
            self.bootstrap_token = None
            return "ok"

    def authenticated(self, candidate: str | None) -> bool:
        return candidate is not None and secrets.compare_digest(
            candidate, self.session_token
        )

    def request_shutdown(self) -> None:
        callback = self.shutdown_callback
        if callback is not None:
            callback()

    def close(self) -> None:
        """Release session resources.

        Issue #64 owns no temporary resources, so this is deliberately a
        documented no-op. The upload child fills it in without changing the
        server's ``try/finally`` lifecycle.
        """


def session_metadata(session: Session) -> dict[str, Any]:
    """Build the sole schema-version-1 session response envelope."""
    return {
        "schema_version": 1,
        "state": session.state,
        "report_revision": session.report_revision,
        "verdict_revision": session.verdict_revision,
        "fingerprint": session.fingerprint,
        "snapshot": session.snapshot,
        "verdicts": list(session.verdicts),
        "override_status": list(session.override_status),
    }


def serialized[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """Wrap a complete mutation's check-and-apply in the session lock."""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        session: Session = current_app.extensions[SESSION_EXTENSION_KEY]
        with session.mutation_lock:
            return func(*args, **kwargs)

    wrapper.__vault_cleaner_serialized__ = True
    return wrapper
