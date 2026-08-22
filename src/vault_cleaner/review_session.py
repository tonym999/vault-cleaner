"""Pure review-session proposal retention and verdict merging primitives.

The session-facing review API works with a report that may be replaced while
the user is looking at it.  A verdict can cross that boundary only when the
proposal it describes is unchanged in both runs.  This module owns that
cross-fingerprint rule and the small, manifest-free merge core used by the
server and by the CLI adapter in :mod:`vault_cleaner.review`.

The review-manifest parser remains in ``review.py``.  The data classes shared
by the parser and the merge core live here so this module does not need to
import the parser back (and therefore cannot form a circular import).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from vault_cleaner.report_run import ReportDecision, ReportRun

OVERRIDES_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ManifestDecision:
    """One reviewed proposal, as recorded by a review UI."""

    id: str
    kind: str
    hash: str
    name: str
    action: str
    reason: str
    verdict: str


@dataclass(frozen=True)
class Veto:
    """A persisted veto, with enough metadata to explain itself later.

    The display fields describe the proposal as it stood when the veto was
    recorded. They exist to make a stale or orphaned entry readable months
    later; identity is ``id`` alone.
    """

    id: str
    kind: str
    hash: str
    name: str
    action: str
    reason: str
    fingerprint: str
    recorded_at: str


@dataclass(frozen=True)
class OverrideStore:
    schema_version: int
    vetoes: tuple[Veto, ...]

    def by_id(self) -> dict[str, Veto]:
        return {veto.id: veto for veto in self.vetoes}


@dataclass(frozen=True)
class MergeResult:
    """The result of folding veto verdicts into an override store.

    ``unknown_ids`` and ``already_vetoed_but_approved`` normally contain
    :class:`ManifestDecision` objects when called through ``merge_manifest``.
    The manifest-free core has no display copy to carry for a plain
    ``id -> verdict`` mapping, so it returns the corresponding ids there.
    Keeping the fields (and their names) unchanged preserves the CLI adapter's
    existing diagnostics while allowing the session API to use the core
    without constructing a manifest.
    """

    store: OverrideStore
    added: tuple[Veto, ...]
    updated: tuple[Veto, ...]
    unchanged: tuple[Veto, ...]
    already_vetoed_but_approved: tuple[Any, ...]
    unknown_ids: tuple[Any, ...]


@dataclass(frozen=True)
class RetentionResult:
    """Verdicts that survived reconciliation and the ids discarded.

    ``retained`` preserves the input verdict entries in their original
    order.  ``discarded`` is an ordered tuple of ids, including ids whose
    proposal disappeared from the new run.  The small id properties are
    convenient for callers that store verdicts separately from their ids.
    """

    retained: tuple[Any, ...]
    discarded: tuple[str, ...]

    @property
    def retained_ids(self) -> tuple[str, ...]:
        return tuple(_verdict_id(entry) for entry in self.retained)

    @property
    def discarded_ids(self) -> tuple[str, ...]:
        return self.discarded


def _field(value: object, name: str) -> object:
    """Read a proposal field from a dataclass or a snapshot-style mapping."""
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _verdict_id(value: object) -> str:
    if isinstance(value, str):
        return value
    item_id = _field(value, "id")
    if not isinstance(item_id, str):
        raise TypeError("verdict id must be a string")
    return item_id


def _verdict_entries(verdicts: object) -> tuple[object, ...]:
    """Normalise the two session-friendly verdict representations.

    The server protocol stores an array of ``{"id", "verdict"}`` objects,
    while a caller doing pure Python work may naturally have an
    ``id -> verdict`` mapping.  Preserve array entries verbatim; mappings are
    represented as tiny dictionaries so the returned retained values can be
    fed straight back into the protocol.
    """
    if isinstance(verdicts, Mapping):
        # A single protocol entry is a mapping too, but it is not an
        # id-to-verdict map.  Treat it as one entry so malformed input still
        # receives the same id validation below.
        if "id" in verdicts or "verdict" in verdicts:
            return (verdicts,)
        return tuple(
            {"id": item_id, "verdict": verdict}
            for item_id, verdict in verdicts.items()
        )
    return tuple(verdicts)  # type: ignore[arg-type]


def same_proposal(a: object, b: object) -> bool:
    """Return whether two proposals have the same cross-run identity.

    Only the five fields that define the proposal's decision identity are
    compared.  Display metadata such as ``name`` and ``owner`` deliberately
    does not participate.
    """
    return (
        _field(a, "id"),
        _field(a, "kind"),
        _field(a, "hash"),
        _field(a, "action"),
        _field(a, "reason"),
    ) == (
        _field(b, "id"),
        _field(b, "kind"),
        _field(b, "hash"),
        _field(b, "action"),
        _field(b, "reason"),
    )


def _run_proposals(run: ReportRun) -> dict[str, ReportDecision]:
    return {
        decision.id: decision
        for section in run.sections
        for decision in section.decisions
    }


def retain_verdicts(
    verdicts: object,
    old_run: ReportRun,
    new_run: ReportRun,
) -> RetentionResult:
    """Retain verdict entries whose complete proposal identity is unchanged.

    Reconciliation is intentionally stricter than a lookup by id: a changed
    proposal and a proposal missing from the new run are both discarded.
    ``same_proposal`` is called only here; the persisted-veto classification
    and manifest merge paths have different, established semantics.
    """
    old_proposals = _run_proposals(old_run)
    new_proposals = _run_proposals(new_run)
    retained: list[object] = []
    discarded: list[str] = []

    for entry in _verdict_entries(verdicts):
        item_id = _verdict_id(entry)
        old_proposal = old_proposals.get(item_id)
        new_proposal = new_proposals.get(item_id)
        if old_proposal is not None and new_proposal is not None and same_proposal(
            old_proposal, new_proposal
        ):
            retained.append(entry)
        else:
            discarded.append(item_id)

    return RetentionResult(retained=tuple(retained), discarded=tuple(discarded))


def _entry_verdict(entry: object) -> object:
    if isinstance(entry, Mapping):
        return entry.get("verdict")
    if isinstance(entry, ManifestDecision):
        return entry.verdict
    return getattr(entry, "verdict", entry)


def _entry_for_id(entry: object, item_id: str) -> object:
    """Return metadata-bearing entries for adapter diagnostics when present."""
    if isinstance(entry, ManifestDecision):
        return entry
    if isinstance(entry, Mapping) and "id" in entry:
        return entry
    return item_id


def _ordered(vetoes: Iterable[Veto]) -> tuple[Veto, ...]:
    return tuple(sorted(vetoes, key=lambda veto: (veto.kind, veto.id)))


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def merge_verdicts(
    store: OverrideStore,
    id_to_verdict: Mapping[str, object] | Iterable[object],
    run: ReportRun,
    *,
    recorded_at: str | None = None,
) -> MergeResult:
    """Merge a validated id-to-verdict collection without a manifest.

    The report run is authoritative for every persisted veto field.  A
    ``ManifestDecision`` value is also accepted for adapter use so unknown
    and already-vetoed diagnostics retain their old display metadata; plain
    session verdicts use their id as the diagnostic value.
    """
    recorded_at = recorded_at or _now()
    proposals = _run_proposals(run)
    if isinstance(id_to_verdict, Mapping):
        entries = []
        for item_id, entry in id_to_verdict.items():
            if not isinstance(item_id, str):
                raise TypeError("verdict id must be a string")
            entries.append((item_id, entry))
        entries = tuple(entries)
    else:
        entries = tuple((_verdict_id(entry), entry) for entry in id_to_verdict)

    existing = store.by_id()
    original_ids = store.by_id()
    added: list[Veto] = []
    updated: list[Veto] = []
    unchanged: list[Veto] = []
    unknown: list[object] = []

    for item_id, entry in entries:
        verdict = _entry_verdict(entry)
        if verdict != "vetoed":
            continue
        if item_id not in proposals:
            unknown.append(_entry_for_id(entry, item_id))
            continue

        decision = proposals[item_id]
        veto = Veto(
            id=decision.id,
            kind=decision.kind,
            hash=decision.hash,
            name=decision.name,
            action=decision.action,
            reason=decision.reason,
            fingerprint=run.fingerprint,
            recorded_at=recorded_at,
        )
        previous = existing.get(veto.id)
        if previous is None:
            added.append(veto)
        elif (previous.action, previous.reason) == (veto.action, veto.reason):
            # Keep the original recorded_at: nothing about the veto changed.
            veto = previous
            unchanged.append(veto)
        else:
            updated.append(veto)
        existing[veto.id] = veto

    approved_but_vetoed = tuple(
        _entry_for_id(entry, item_id)
        for item_id, entry in entries
        if _entry_verdict(entry) == "approved" and item_id in original_ids
    )

    merged = OverrideStore(
        schema_version=OVERRIDES_SCHEMA_VERSION,
        vetoes=_ordered(existing.values()),
    )
    return MergeResult(
        store=merged,
        added=tuple(added),
        updated=tuple(updated),
        unchanged=tuple(unchanged),
        already_vetoed_but_approved=approved_but_vetoed,
        unknown_ids=tuple(unknown),
    )


__all__ = [
    "OVERRIDES_SCHEMA_VERSION",
    "ManifestDecision",
    "MergeResult",
    "OverrideStore",
    "RetentionResult",
    "Veto",
    "merge_verdicts",
    "retain_verdicts",
    "same_proposal",
]
