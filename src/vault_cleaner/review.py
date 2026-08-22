"""Persistent review overrides and the reviewed DIM export (#36).

A **review manifest** is the handoff back from a review UI: it names the
report run it was produced against and records an approve/veto verdict per
proposed decision. A **veto** suppresses one proposed junk/review row. It
does not tag the item `keep`, change its existing DIM tag, or rerank its
group — overrides apply strictly after the ordered rules pipeline, so an
extra copy may survive without changing the chosen winner.

Vetoes persist in `data/overrides.json` so they survive re-running the
report against a fresh export. Everything crossing the process boundary
here is untrusted input: manifests are validated against the current run's
fingerprint before anything is applied, no filesystem path is ever read out
of manifest content, and `Id`/`Hash` stay opaque strings throughout.

"Manifest" in this module always means a review manifest. The Bungie
static manifest is `vault_cleaner.manifest`, an unrelated thing.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from vault_cleaner.report_run import (
    EXPORT_KINDS,
    RULESET_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
    ReportDecision,
    ReportRun,
)
from vault_cleaner.review_session import (
    OVERRIDES_SCHEMA_VERSION,
    ManifestDecision,
    MergeResult,
    OverrideStore,
    Veto,
    merge_verdicts,
    ordered_vetoes,
    utc_now,
)

MANIFEST_SCHEMA_VERSION = 1
DEFAULT_OVERRIDES_PATH = "data/overrides.json"

VERDICTS = frozenset({"approved", "vetoed"})

# DIM instance ids are decimal uint64 (20 digits covers 2**64-1). Validated
# for shape only — never parsed as a number, since the value must survive
# round trips that Python ints and spreadsheets both mangle.
ID_RE = re.compile(r"[0-9]{1,20}")
_MANIFEST_KEYS = frozenset({"schema_version", "snapshot", "decisions", "generated_at"})
_SNAPSHOT_KEYS = frozenset({"schema_version", "ruleset_version", "fingerprint"})
_DECISION_KEYS = frozenset({"id", "kind", "hash", "name", "action", "reason", "verdict"})
_OVERRIDES_KEYS = frozenset({"schema_version", "updated_at", "vetoes"})
_VETO_KEYS = frozenset(
    {"id", "kind", "hash", "name", "action", "reason", "fingerprint", "recorded_at"}
)

MAX_TEXT = 200


class ReviewError(ValueError):
    """A review manifest or overrides file could not be used."""


class ReviewManifestError(ReviewError):
    """A review manifest is malformed, unversioned, or self-inconsistent."""


class FingerprintMismatchError(ReviewError):
    """A review manifest describes a different report run than this one."""


class OverridesError(ReviewError):
    """The persisted overrides file is malformed."""


@dataclass(frozen=True)
class ReviewManifest:
    schema_version: int
    snapshot_schema_version: int
    ruleset_version: int
    fingerprint: str
    decisions: tuple[ManifestDecision, ...]

    @property
    def vetoed(self) -> tuple[ManifestDecision, ...]:
        return tuple(d for d in self.decisions if d.verdict == "vetoed")

    @property
    def approved(self) -> tuple[ManifestDecision, ...]:
        return tuple(d for d in self.decisions if d.verdict == "approved")


@dataclass(frozen=True)
class StaleVeto:
    veto: Veto
    detail: str


@dataclass(frozen=True)
class OverrideStatus:
    """How each persisted veto relates to the current report run."""

    active: tuple[tuple[Veto, ReportDecision], ...]
    stale: tuple[StaleVeto, ...]
    orphaned: tuple[Veto, ...]
    unchecked: tuple[Veto, ...]

    @property
    def active_ids(self) -> frozenset[str]:
        return frozenset(veto.id for veto, _ in self.active)


def empty_store() -> OverrideStore:
    return OverrideStore(schema_version=OVERRIDES_SCHEMA_VERSION, vetoes=())


def _reject_nan(value: str) -> float:
    raise ReviewError(f"non-finite JSON number {value!r} is not allowed")


def _load_json_object(path: Path, error: type[ReviewError], what: str) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    # UnicodeDecodeError is a ValueError, not an OSError, so mis-encoded bytes
    # used to escape as a traceback instead of a reportable refusal. The bytes
    # are rejected either way; this only makes the rejection sayable.
    except (OSError, UnicodeDecodeError) as e:
        raise error(f"could not read {what} {path}: {e}") from e
    try:
        data = json.loads(text, parse_constant=_reject_nan)
    except (json.JSONDecodeError, ReviewError) as e:
        raise error(f"{path}: not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise error(f"{path}: {what} must be a JSON object")
    return data


def check_keys(
    data: Mapping[str, object],
    allowed: frozenset[str],
    error: type[ReviewError],
    where: str,
) -> None:
    """Reject unknown keys outright.

    Strictness is the point: a manifest arrives from a browser, and silently
    ignoring keys we do not understand is how an unexpected `output_path` or
    `input` key becomes a way to steer this tool at other files.
    """
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise error(f"{where}: unknown key(s) {unknown} — expected {sorted(allowed)}")


def require_text(
    data: Mapping[str, object],
    key: str,
    error: type[ReviewError],
    where: str,
    *,
    allow_empty: bool = False,
) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise error(f"{where}: {key!r} must be a string")
    if not allow_empty and not value:
        raise error(f"{where}: {key!r} must not be empty")
    if len(value) > MAX_TEXT:
        raise error(f"{where}: {key!r} is longer than {MAX_TEXT} characters")
    return value


def require_id(data: Mapping[str, object], error: type[ReviewError], where: str) -> str:
    value = data.get("id")
    if not isinstance(value, str):
        raise error(f"{where}: 'id' must be a string, not {type(value).__name__}")
    if not ID_RE.fullmatch(value):
        raise error(
            f"{where}: 'id' {value!r} is not a DIM instance id "
            "(1-20 decimal digits, unquoted)"
        )
    return value


def require_kind(data: Mapping[str, object], error: type[ReviewError], where: str) -> str:
    """Validate a persisted veto's export kind.

    Unlike the rest of a veto's metadata, `kind` is load-bearing: `classify`
    reads it to decide whether a missing id means the export was skipped or
    the item is gone. An unrecognised value could only ever land in the
    `unchecked` bucket, so a hand-edited typo would be reported forever as
    "that export was not loaded" — a false explanation for a malformed file.
    """
    value = require_text(data, "kind", error, where)
    if value not in EXPORT_KINDS:
        raise error(
            f"{where}: kind {value!r} is not a known export kind "
            f"({', '.join(sorted(EXPORT_KINDS))})"
        )
    return value


def _require_version(
    data: Mapping[str, object],
    key: str,
    expected: int,
    error: type[ReviewError],
    where: str,
) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise error(f"{where}: {key!r} must be an integer")
    if value != expected:
        raise error(
            f"{where}: {key} {value} is not supported by this build "
            f"(expected {expected})"
        )
    return value


def parse_manifest(path: str | Path) -> ReviewManifest:
    """Load and fully validate a review manifest.

    Nothing here trusts the file: versions must match this build exactly,
    unknown keys are rejected, and an id may not appear twice — a repeated
    id means the UI recorded two verdicts for one proposal, and guessing
    which one the reviewer meant is not this tool's call.
    """
    path = Path(path)
    data = _load_json_object(path, ReviewManifestError, "review manifest")
    where = str(path)
    check_keys(data, _MANIFEST_KEYS, ReviewManifestError, where)
    _require_version(
        data, "schema_version", MANIFEST_SCHEMA_VERSION, ReviewManifestError, where
    )
    if "generated_at" in data:
        require_text(data, "generated_at", ReviewManifestError, where)

    snapshot = data.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ReviewManifestError(f"{where}: 'snapshot' must be an object")
    check_keys(snapshot, _SNAPSHOT_KEYS, ReviewManifestError, f"{where}: snapshot")
    snapshot_version = _require_version(
        snapshot,
        "schema_version",
        SNAPSHOT_SCHEMA_VERSION,
        ReviewManifestError,
        f"{where}: snapshot",
    )
    ruleset_version = _require_version(
        snapshot,
        "ruleset_version",
        RULESET_VERSION,
        ReviewManifestError,
        f"{where}: snapshot",
    )
    fingerprint = require_text(
        snapshot, "fingerprint", ReviewManifestError, f"{where}: snapshot"
    )

    raw_decisions = data.get("decisions")
    if not isinstance(raw_decisions, list):
        raise ReviewManifestError(f"{where}: 'decisions' must be a list")

    decisions = []
    seen: dict[str, str] = {}
    for index, entry in enumerate(raw_decisions):
        at = f"{where}: decisions[{index}]"
        if not isinstance(entry, dict):
            raise ReviewManifestError(f"{at}: must be an object")
        check_keys(entry, _DECISION_KEYS, ReviewManifestError, at)
        item_id = require_id(entry, ReviewManifestError, at)
        verdict = require_text(entry, "verdict", ReviewManifestError, at)
        if verdict not in VERDICTS:
            raise ReviewManifestError(
                f"{at}: verdict {verdict!r} must be one of {sorted(VERDICTS)}"
            )
        if item_id in seen:
            detail = (
                f"conflicting verdicts {seen[item_id]!r} and {verdict!r}"
                if seen[item_id] != verdict
                else f"duplicate {verdict!r} entries"
            )
            raise ReviewManifestError(f"{at}: id {item_id} appears twice — {detail}")
        seen[item_id] = verdict
        decisions.append(
            ManifestDecision(
                id=item_id,
                kind=require_text(entry, "kind", ReviewManifestError, at),
                hash=require_text(entry, "hash", ReviewManifestError, at),
                name=require_text(
                    entry, "name", ReviewManifestError, at, allow_empty=True
                ),
                action=require_text(entry, "action", ReviewManifestError, at),
                reason=require_text(entry, "reason", ReviewManifestError, at),
                verdict=verdict,
            )
        )

    return ReviewManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        snapshot_schema_version=snapshot_version,
        ruleset_version=ruleset_version,
        fingerprint=fingerprint,
        decisions=tuple(decisions),
    )


def check_manifest_matches(manifest: ReviewManifest, run: ReportRun) -> None:
    """Refuse a manifest produced against different inputs.

    The fingerprint covers exports, decision config, wishlists, the Bungie
    manifest, and the ruleset version, so any drift in what the rules saw
    lands here. This is a refusal, not a warning: applying stale verdicts
    would suppress rows the reviewer never actually looked at.
    """
    if manifest.fingerprint != run.fingerprint:
        raise FingerprintMismatchError(
            "review manifest was produced against a different report run\n"
            f"  manifest fingerprint: {manifest.fingerprint}\n"
            f"  current fingerprint:  {run.fingerprint}\n"
            "Exports, config, wishlists, or the Bungie manifest changed. "
            "Re-run the report, review it again, and re-export the manifest."
        )


def load_overrides(path: str | Path) -> OverrideStore:
    """Load persisted vetoes; a missing file is an empty store, not an error."""
    path = Path(path)
    if not path.exists():
        return empty_store()
    data = _load_json_object(path, OverridesError, "overrides file")
    where = str(path)
    check_keys(data, _OVERRIDES_KEYS, OverridesError, where)
    _require_version(
        data, "schema_version", OVERRIDES_SCHEMA_VERSION, OverridesError, where
    )

    raw_vetoes = data.get("vetoes")
    if not isinstance(raw_vetoes, list):
        raise OverridesError(f"{where}: 'vetoes' must be a list")

    vetoes = []
    seen = set()
    for index, entry in enumerate(raw_vetoes):
        at = f"{where}: vetoes[{index}]"
        if not isinstance(entry, dict):
            raise OverridesError(f"{at}: must be an object")
        check_keys(entry, _VETO_KEYS, OverridesError, at)
        item_id = require_id(entry, OverridesError, at)
        if item_id in seen:
            raise OverridesError(f"{at}: id {item_id} appears twice")
        seen.add(item_id)
        vetoes.append(
            Veto(
                id=item_id,
                kind=require_kind(entry, OverridesError, at),
                hash=require_text(entry, "hash", OverridesError, at),
                name=require_text(entry, "name", OverridesError, at, allow_empty=True),
                action=require_text(entry, "action", OverridesError, at),
                reason=require_text(entry, "reason", OverridesError, at),
                fingerprint=require_text(entry, "fingerprint", OverridesError, at),
                recorded_at=require_text(entry, "recorded_at", OverridesError, at),
            )
        )

    return OverrideStore(
        schema_version=OVERRIDES_SCHEMA_VERSION,
        vetoes=ordered_vetoes(vetoes),
    )


def store_dict(store: OverrideStore, *, updated_at: str) -> dict:
    return {
        "schema_version": store.schema_version,
        "updated_at": updated_at,
        "vetoes": [
            {
                "id": veto.id,
                "kind": veto.kind,
                "hash": veto.hash,
                "name": veto.name,
                "action": veto.action,
                "reason": veto.reason,
                "fingerprint": veto.fingerprint,
                "recorded_at": veto.recorded_at,
            }
            for veto in ordered_vetoes(store.vetoes)
        ],
    }


def save_overrides(
    store: OverrideStore, path: str | Path, *, updated_at: str | None = None
) -> Path:
    """Write the overrides file atomically.

    This is the durable record of every review the user has already done, so
    a half-written file is worse than no write at all: serialize into a temp
    file in the same directory, fsync it, then `os.replace` — which is atomic
    within a filesystem — and fsync the directory so the rename itself
    survives a power loss.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = store_dict(store, updated_at=updated_at or utc_now())

    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise

    _fsync_directory(path.parent)
    return path


def _fsync_directory(directory: Path) -> None:
    """Best-effort durability for the rename itself.

    Everything here runs after `os.replace` has already committed, so no
    failure below may propagate — open, fsync *and* close alike: reporting an
    error for a write that actually succeeded would abort the caller before it
    writes the reviewed CSV, leaving persisted vetoes and no export to match
    them. Directory handles are refused outright on some platforms and
    directory fsync on some filesystems; the file is intact either way.
    """
    dir_fd = None
    try:
        dir_fd = os.open(directory, os.O_RDONLY)
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        if dir_fd is not None:
            try:
                os.close(dir_fd)
            except OSError:
                pass


def classify(store: OverrideStore, run: ReportRun) -> OverrideStatus:
    """Sort persisted vetoes into active / stale / orphaned / unchecked.

    A veto only applies while it still describes the proposal the reviewer
    actually saw. If the rules now propose something else for that item, the
    veto goes stale rather than silently suppressing an unreviewed decision —
    the item resurfacing for review is the safe direction to fail.
    """
    proposals = {
        decision.id: decision
        for section in run.sections
        for decision in section.decisions
    }
    present = {
        section.kind: section.item_ids for section in run.sections
    }
    loaded_kinds = set(present)

    active, stale, orphaned, unchecked = [], [], [], []
    for veto in store.vetoes:
        decision = proposals.get(veto.id)
        if decision is not None:
            if (decision.action, decision.reason) == (veto.action, veto.reason):
                active.append((veto, decision))
            else:
                stale.append(
                    StaleVeto(
                        veto,
                        f"now proposed as {decision.action}/{decision.reason}, "
                        f"vetoed as {veto.action}/{veto.reason} — re-review it",
                    )
                )
            continue
        if veto.kind not in loaded_kinds:
            unchecked.append(veto)
        elif veto.id in present[veto.kind]:
            stale.append(
                StaleVeto(veto, "still in the vault, but no longer proposed for cleanup")
            )
        else:
            orphaned.append(veto)

    return OverrideStatus(
        active=tuple(active),
        stale=tuple(stale),
        orphaned=tuple(orphaned),
        unchecked=tuple(unchecked),
    )


def apply_vetoes(run: ReportRun, vetoed_ids: Iterable[str]) -> list[ReportDecision]:
    """Return the run's decisions minus vetoed ids, in unchanged order.

    Filtering happens after the pipeline has already chosen winners, so
    suppressing a losing copy leaves the winner exactly as the rules ranked
    it — one more copy simply survives this cleanup.
    """
    suppressed = frozenset(vetoed_ids)
    return [
        decision
        for section in run.sections
        for decision in section.decisions
        if decision.id not in suppressed
    ]


def merge_manifest(
    store: OverrideStore,
    manifest: ReviewManifest,
    run: ReportRun,
    *,
    recorded_at: str | None = None,
) -> MergeResult:
    """Fold a validated manifest's vetoes into the persisted store.

    Approving an id never removes an existing veto. Applying a manifest is
    additive by design: a review UI that forgot a previous session's vetoes
    must not be able to resurrect junk decisions the user already rejected.
    Un-vetoing is an explicit edit of the overrides file.
    """
    # The core deliberately sees only id -> verdict.  The manifest's display
    # copy is untrusted and must not influence persisted Veto metadata.
    id_to_verdict = {entry.id: entry.verdict for entry in manifest.decisions}
    merged = merge_verdicts(
        store,
        id_to_verdict,
        run,
        recorded_at=recorded_at or utc_now(),
    )
    # Keep the old diagnostic payloads (names and kinds are useful on the CLI)
    # at this adapter boundary; the manifest-free core can only report ids.
    unknown = {entry.id: entry for entry in manifest.vetoed}
    approved = {entry.id: entry for entry in manifest.approved}
    return replace(
        merged,
        unknown_ids=tuple(unknown.get(item_id, item_id) for item_id in merged.unknown_ids),
        already_vetoed_but_approved=tuple(
            approved.get(item_id, item_id)
            for item_id in merged.already_vetoed_but_approved
        ),
    )


def imported_junk_tags(status: OverrideStatus) -> tuple[tuple[Veto, ReportDecision], ...]:
    """Active vetoes whose item is *already* tagged junk in DIM.

    Vetoing suppresses a proposal; it cannot untag an item that a previous
    cleanup already tagged and imported. Those need a manual tag change in
    DIM, so the CLI has to say so rather than implying the veto undid it.
    """
    return tuple(
        (veto, decision)
        for veto, decision in status.active
        if decision.original_tag == "junk"
    )
