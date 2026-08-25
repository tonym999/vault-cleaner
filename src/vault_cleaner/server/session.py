"""Single-session state and mutation serialization primitives."""

from __future__ import annotations

import hashlib
import secrets
import shutil
import time
from collections.abc import Callable
from copy import deepcopy
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Any, Literal

from flask import current_app

from vault_cleaner.report_run import ReportRun, snapshot_dict
from vault_cleaner.review import (
    OverridesError,
    OverrideStatus,
    classify,
    empty_store,
    load_overrides_bytes,
)
from vault_cleaner.review_session import OverrideStore

BOOTSTRAP_TTL_SECONDS = 5 * 60
SESSION_EXTENSION_KEY = "vault_cleaner_session"
REPORT_REVISION_HEADER = "Vault-Cleaner-Report-Revision"
VERDICT_REVISION_HEADER = "Vault-Cleaner-Verdict-Revision"
BootstrapResult = Literal["ok", "invalid", "expired"]
_UNSET = object()


def _stale_error(code: str, message: str) -> None:
    # Import locally to keep this state module independent of the Flask app's
    # error-handler implementation.
    from vault_cleaner.server.errors import ApiError

    raise ApiError(code, 409, message)


def check_expected_revisions(
    session: Session,
    expected_report_revision: int,
    *,
    expected_verdict_revision: int | None = None,
    fingerprint: str | None = None,
) -> None:
    """Check mutation preconditions in the protocol's required order.

    Callers must invoke this inside ``@serialized``.  No state is changed by
    this helper, and report revision mismatches always win over the
    fingerprint and verdict checks.  Finalize can reuse the same seam.
    """
    if expected_report_revision != session.report_revision:
        _stale_error(
            "stale_report",
            "report revision is stale; reload the current report before retrying",
        )
    if fingerprint is not None:
        current = session.report.fingerprint if session.report is not None else None
        if current != fingerprint:
            _stale_error(
                "stale_report",
                "report fingerprint is stale; reload the current report before retrying",
            )
    if (
        expected_verdict_revision is not None
        and expected_verdict_revision != session.verdict_revision
    ):
        _stale_error(
            "stale_verdicts",
            "verdict revision is stale; reload the current verdicts before retrying",
        )


def proposal_ids_in_order(session: Session) -> list[str]:
    """Return current report proposal ids in deterministic report order."""
    if session.report is None:
        return []
    return [
        decision.id
        for section in session.report.sections
        for decision in section.decisions
    ]


def order_verdicts(
    session: Session, verdicts: list[dict[str, str]] | tuple[dict[str, str], ...]
) -> list[dict[str, str]]:
    """Order non-null verdict entries by the current proposal sequence."""
    if session.report is None:
        return deepcopy(list(verdicts))
    by_id = {entry["id"]: entry for entry in verdicts}
    return [
        deepcopy(entry)
        for item_id in proposal_ids_in_order(session)
        if (entry := by_id.get(item_id))
    ]


def revision_headers(session: Session) -> dict[str, str]:
    """Snapshot both monotonic revisions as one coherent header pair."""
    with session.mutation_lock:
        return {
            REPORT_REVISION_HEADER: str(session.report_revision),
            VERDICT_REVISION_HEADER: str(session.verdict_revision),
        }


def _constant_time_equals(candidate: str | None, secret: str) -> bool:
    """Compare UTF-8 credentials without letting unusual text raise."""
    if not isinstance(candidate, str):
        return False
    try:
        return secrets.compare_digest(candidate.encode(), secret.encode())
    except UnicodeEncodeError:
        return False


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
        self._shutdown_callback_called = False

        self.state = "idle"
        self.report_revision = 0
        self.verdict_revision = 0
        self.report: ReportRun | None = None
        self.staging_dir: Path | None = None
        self.export_digests: dict[str, str] = {}
        self.export_sizes: dict[str, int] = {}
        self.override_store: OverrideStore
        # Internal state for #67 finalize drift detection; deliberately absent
        # from the schema-version-1 report response.
        self.override_digest: str | None
        self.finalized_csv_bytes: bytes | None = None
        self.approved_still_vetoed_count = 0
        self._retired_staging_dirs: set[Path] = set()
        self._candidate_staging_dirs: set[Path] = set()
        self._closed = False

        self.override_store, self.override_digest = self.read_override_snapshot()

        # These compatibility fields are retained for callers that used the
        # #64 session seam directly.  When a report exists, metadata derives
        # from ``report`` and these fields are updated atomically with it.
        self.fingerprint: str | None = None
        self.snapshot: dict[str, Any] | None = None
        self.verdicts: list[dict[str, str]] = []
        self.override_status: list[dict[str, str]] = []

    @property
    def expected_host(self) -> str:
        if self.bound_port is None:
            raise RuntimeError("session has not been bound to a port")
        if self.bound_port == 80:
            return "127.0.0.1"
        return f"127.0.0.1:{self.bound_port}"

    @property
    def expected_origin(self) -> str:
        return f"http://{self.expected_host}"

    def configure_bound_port(self, port: int) -> None:
        if self.bound_port is not None:
            raise RuntimeError("session port is already configured")
        self.bound_port = port

    def exchange_bootstrap(self, candidate: str) -> BootstrapResult:
        """Consume the bootstrap credential atomically.

        Returns ``ok``, ``invalid``, or ``expired``. The comparison remains
        constant-time while the live token exists, and concurrent successful
        exchanges are prevented by the same session lock later mutations use.
        """
        with self.mutation_lock:
            token = self.bootstrap_token
            if token is None or not _constant_time_equals(candidate, token):
                return "invalid"
            if self.clock() - self.bootstrap_issued_at >= BOOTSTRAP_TTL_SECONDS:
                return "expired"
            self.bootstrap_token = None
            return "ok"

    def authenticated(self, candidate: str | None) -> bool:
        return _constant_time_equals(candidate, self.session_token)

    def read_override_snapshot(self) -> tuple[OverrideStore, str | None]:
        """Read and validate the durable override bytes and their digest.

        The missing-file case is intentionally distinct from an empty file:
        it establishes a baseline that can later detect an externally-created
        overrides file.  Callers use this seam before mutating session state.
        """
        override_path = Path(self.overrides_path)
        try:
            override_bytes = override_path.read_bytes()
        except FileNotFoundError:
            return empty_store(), None
        except OSError as error:
            raise OverridesError(
                f"could not read overrides file {override_path}: {error}"
            ) from error
        store = load_overrides_bytes(override_bytes, source=str(override_path))
        return store, hashlib.sha256(override_bytes).hexdigest()

    def read_override_digest(self) -> str | None:
        """Hash the current override file without parsing or exposing it."""
        override_path = Path(self.overrides_path)
        try:
            override_bytes = override_path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as error:
            raise OverridesError(
                f"could not read overrides file {override_path}: {error}"
            ) from error
        return hashlib.sha256(override_bytes).hexdigest()

    @property
    def closed(self) -> bool:
        """Return whether shutdown has started, under the mutation lock."""
        with self.mutation_lock:
            return self._closed

    def mark_closed(self) -> None:
        """Invalidate all live state and enter the terminal state.

        This deliberately does not perform filesystem I/O.  The shutdown
        response can therefore expose a coherent terminal envelope before its
        ``call_on_close`` cleanup callback runs.  ``close`` performs the
        retryable physical cleanup and is safe to call afterwards (or again).
        """
        with self.mutation_lock:
            if self._closed:
                return
            self._closed = True
            self.state = "closed"
            if self.staging_dir is not None:
                self._retired_staging_dirs.add(self.staging_dir)
            self.report = None
            self.export_digests = {}
            self.export_sizes = {}
            self.fingerprint = None
            self.snapshot = None
            self.verdicts = []
            self.override_status = []
            self.staging_dir = None
            self.finalized_csv_bytes = None
            self.approved_still_vetoed_count = 0

    def request_shutdown(self) -> None:
        # Mark the session closed before handing control to the server.  A
        # concurrent upload therefore observes the same lock-protected
        # shutdown boundary as an explicit ``close()`` call.
        with self.mutation_lock:
            callback = (
                None
                if self._shutdown_callback_called
                else self.shutdown_callback
            )
            self._shutdown_callback_called = True
        try:
            self.close()
        finally:
            if callback is not None:
                callback()

    def close(self) -> None:
        """Invalidate the run and release every upload directory.

        The report fields are cleared before any filesystem work begins.  A
        failed removal therefore leaves only an opaque, session-owned retry
        path; it cannot leave the API pointing at an accepted export after
        close.
        """
        self.mark_closed()
        with self.mutation_lock:
            candidates = set(self._candidate_staging_dirs)
            retired = set(self._retired_staging_dirs)
            # Register every path before attempting cleanup.  If an
            # unexpected exception escapes the cleanup seam, the path remains
            # private session state for a later close() retry.
            self._candidate_staging_dirs.update(candidates)
            self._retired_staging_dirs.update(retired)
            for directory in candidates:
                try:
                    self.cleanup_directory(directory, candidate=True)
                except Exception as cleanup_error:  # noqa: BLE001 - cleanup must not block shutdown
                    del cleanup_error
                    self._candidate_staging_dirs.add(directory)
            for directory in retired:
                try:
                    self.cleanup_directory(directory)
                except Exception as cleanup_error:  # noqa: BLE001 - cleanup must remain retryable
                    del cleanup_error
                    self._retired_staging_dirs.add(directory)

    def reset_live_state(
        self,
        *,
        override_store: OverrideStore | None = None,
        override_digest: str | None | object = _UNSET,
    ) -> None:
        """Discard non-durable session state while preserving revisions.

        Reset is the one operation that can return a live session to ``idle``.
        Cleanup is best effort and remains retryable through the private path
        sets, just like shutdown cleanup.
        """
        with self.mutation_lock:
            if self._closed:
                raise RuntimeError("session is closed")
            paths = set(self._candidate_staging_dirs)
            if self.staging_dir is not None:
                paths.add(self.staging_dir)
            paths.update(self._retired_staging_dirs)
            self._retired_staging_dirs.update(paths)
            self.report = None
            self.export_digests = {}
            self.export_sizes = {}
            self.fingerprint = None
            self.snapshot = None
            self.verdicts = []
            self.override_status = []
            self.staging_dir = None
            if override_store is not None:
                self.override_store = override_store
            if override_digest is not _UNSET:
                assert override_digest is None or isinstance(override_digest, str)
                self.override_digest = override_digest
            self.finalized_csv_bytes = None
            self.approved_still_vetoed_count = 0
            self.state = "idle"
            for directory in paths:
                try:
                    self.cleanup_directory(directory)
                except Exception as cleanup_error:  # noqa: BLE001 - reset must remain coherent
                    del cleanup_error
                    self._retired_staging_dirs.add(directory)

    def track_candidate(self, directory: Path) -> None:
        """Register a newly-created candidate directory for cleanup."""
        directory = Path(directory)
        with self.mutation_lock:
            if self._closed:
                raise RuntimeError("session is closed")
            self._candidate_staging_dirs.add(directory)

    def adopt_candidate(self, directory: Path) -> Path | None:
        """Promote a tracked candidate and return the previously live path."""
        directory = Path(directory)
        with self.mutation_lock:
            if self._closed:
                raise RuntimeError("session is closed")
            if directory not in self._candidate_staging_dirs:
                raise RuntimeError("candidate directory is not tracked")
            previous = self.staging_dir
            self._candidate_staging_dirs.discard(directory)
            self.staging_dir = directory
            return previous

    def track_retired(self, directory: Path) -> None:
        """Retain an old directory for a later best-effort cleanup retry."""
        directory = Path(directory)
        with self.mutation_lock:
            self._retired_staging_dirs.add(directory)

    def retire_directory(self, directory: Path) -> bool:
        """Retire an old live directory without failing the committed upload."""
        directory = Path(directory)
        with self.mutation_lock:
            self._retired_staging_dirs.add(directory)
            try:
                return self.cleanup_directory(directory)
            except Exception:  # noqa: BLE001 - post-commit retirement is best effort
                # Adoption is the commit boundary.  Cleanup is best effort;
                # retain the opaque path for ``close()`` to retry.
                self._retired_staging_dirs.add(directory)
                return False

    def cleanup_directory(self, directory: Path, *, candidate: bool = False) -> bool:
        """Try to remove a server-owned directory and retain failures.

        Cleanup is deliberately best-effort at the HTTP boundary: a transient
        filesystem failure must not turn into a response containing a private
        path. Failed removals remain in the corresponding session-owned set so
        a later ``close()`` can retry them.
        """
        directory = Path(directory)
        with self.mutation_lock:
            try:
                shutil.rmtree(directory)
            except FileNotFoundError:
                removed = True
            except OSError:
                removed = False
            else:
                removed = not directory.exists()

            if removed:
                self._candidate_staging_dirs.discard(directory)
                self._retired_staging_dirs.discard(directory)
                if self.staging_dir == directory:
                    self.staging_dir = None
            elif candidate:
                self._candidate_staging_dirs.add(directory)
            else:
                self._retired_staging_dirs.add(directory)
            return removed


def _override_status_payload(status: OverrideStatus) -> list[dict[str, str]]:
    """Serialize classify's buckets in a stable, browser-friendly order."""
    entries: list[dict[str, str]] = []
    for veto, _decision in status.active:
        entries.append(
            {
                "id": veto.id,
                "status": "active",
                "detail": "still matches a proposal; it is being suppressed",
            }
        )
    for stale in status.stale:
        entries.append(
            {
                "id": stale.veto.id,
                "status": "stale",
                "detail": stale.detail,
            }
        )
    for veto in status.orphaned:
        entries.append(
            {
                "id": veto.id,
                "status": "orphaned",
                "detail": "no longer in the export",
            }
        )
    for veto in status.unchecked:
        entries.append(
            {
                "id": veto.id,
                "status": "unchecked",
                "detail": f"{veto.kind} export not loaded this run",
            }
        )
    return entries


def session_metadata(session: Session) -> dict[str, Any]:
    """Build the sole schema-version-1 session response envelope."""
    with session.mutation_lock:
        run = session.report
        if run is None:
            snapshot = deepcopy(session.snapshot)
            fingerprint = session.fingerprint
            override_status = deepcopy(session.override_status)
        else:
            snapshot = snapshot_dict(run)
            fingerprint = run.fingerprint
            override_status = _override_status_payload(
                classify(session.override_store, run)
            )
        return {
            "schema_version": 1,
            "state": session.state,
            "report_revision": session.report_revision,
            "verdict_revision": session.verdict_revision,
            "fingerprint": fingerprint,
            "snapshot": snapshot,
            "verdicts": order_verdicts(session, session.verdicts),
            "override_status": override_status,
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
