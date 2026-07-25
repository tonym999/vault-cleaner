"""Reusable all-passes report run and versioned snapshot model."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from vault_cleaner.config import ConfigError, load_config
from vault_cleaner.parse import load_armor, load_ghosts, load_weapons
from vault_cleaner.pipeline import (
    ArmorPipelineResult,
    ManifestIdentity,
    WishlistSourceIdentity,
    canonical_sha256,
    json_safe,
    resolve_armor,
    resolve_weapons,
    sha256_file,
)
from vault_cleaner.report import reason_slug
from vault_cleaner.rules import ghosts as ghost_rules
from vault_cleaner.rules import rails
from vault_cleaner.rules.armor import ArmorEvaluation
from vault_cleaner.rules.dupes import Decision

SNAPSHOT_SCHEMA_VERSION = 1
# Bump only when decision semantics change. Snapshot presentation/schema
# changes are deliberately independent so they do not invalidate reviews.
RULESET_VERSION = 1
DEFAULT_EXPORT_PATHS = {
    "weapons": "data/in/destiny-weapon.csv",
    "armor": "data/in/destiny-armor.csv",
    "ghosts": "data/in/destiny-ghost.csv",
}


class NoExportsError(FileNotFoundError):
    """None of the requested DIM exports exist."""


class SourceReadError(OSError):
    """An export vanished or became unreadable during report construction."""


@dataclass(frozen=True)
class SourceMetadata:
    kind: str
    path: str
    item_count: int
    sha256: str


@dataclass(frozen=True)
class ReportWarning:
    """A runtime warning whose path is rendered at the output boundary."""

    kind: str
    path: str
    reason: str

    def render(self, *, redact_path: bool = False) -> str:
        path = Path(self.path).name if redact_path else self.path
        return f"skipping {self.kind}: {path} {self.reason}"


@dataclass(frozen=True)
class ReportDecision:
    id: str
    kind: str
    hash: str
    name: str
    owner: str
    action: str
    tag: str
    note: str
    kept_id: str
    reason: str
    original_tag: str
    original_notes: str
    protection_level: str | None
    protection_reason: str
    locked: bool
    equipped: bool
    in_loadout: bool

    def import_row(self) -> dict[str, str]:
        return {
            "Id": self.id,
            "Hash": self.hash,
            "Tag": self.tag,
            "Notes": self.note,
        }


@dataclass(frozen=True)
class ArmorSectionDetails:
    scored: int
    evaluations: tuple[ArmorEvaluation, ...]
    cited_ids: frozenset[str]
    kept_elsewhere: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class ReportSection:
    kind: str
    source: SourceMetadata
    decisions: tuple[ReportDecision, ...]
    armor: ArmorSectionDetails | None = None


@dataclass(frozen=True)
class ReportRun:
    sections: tuple[ReportSection, ...]
    effective_config: dict
    keep_trash_conflicts: int
    warnings: tuple[ReportWarning, ...]
    wishlists_used: bool
    wishlist_sources: tuple[WishlistSourceIdentity, ...]
    manifest: ManifestIdentity | None
    fingerprint: str

    def summary_sections(self) -> list[tuple[str, list[ReportDecision]]]:
        return [
            (section.kind, list(section.decisions))
            for section in self.sections
        ]

    def import_rows(self) -> list[dict[str, str]]:
        return [
            decision.import_row()
            for section in self.sections
            for decision in section.decisions
        ]


def _normalize_config(cfg: Mapping[str, object]) -> dict:
    """Make effective config JSON-safe without changing its values."""
    try:
        normalized = json_safe(cfg)
    except (TypeError, ValueError) as e:
        raise ConfigError(f"effective config is not snapshot-safe: {e}") from e
    if not isinstance(normalized, dict):
        raise ConfigError("effective config must be a JSON object")
    return normalized


def _snapshot_config(cfg: Mapping[str, object]) -> dict:
    """Return a JSON-safe config copy with directory values redacted."""
    normalized = _normalize_config(cfg)
    paths = normalized.get("paths")
    if isinstance(paths, dict):
        normalized["paths"] = {
            key: Path(str(value)).name or "."
            for key, value in paths.items()
        }
    return normalized


def _fingerprint_config(cfg: Mapping[str, object]) -> dict:
    """Return only config values whose changes can affect decisions."""
    normalized = _normalize_config(cfg)
    # Directory choices only locate external bytes. Those bytes are already
    # covered by export, wishlist, and manifest identities.
    normalized.pop("paths", None)
    return normalized


def _snapshot_source(source: SourceMetadata) -> dict:
    data = asdict(source)
    data["path"] = Path(source.path).name
    return data


def compute_fingerprint(
    source_digests: Mapping[str, str],
    effective_config: Mapping[str, object],
    wishlist_sources: tuple[WishlistSourceIdentity, ...] = (),
    manifest: ManifestIdentity | None = None,
    *,
    ruleset_version: int = RULESET_VERSION,
) -> str:
    """Fingerprint every input that can change report decisions."""
    payload = {
        "ruleset_version": ruleset_version,
        "sources": dict(sorted(source_digests.items())),
        "effective_config": _fingerprint_config(effective_config),
        "wishlists": [asdict(source) for source in wishlist_sources],
        "manifest": asdict(manifest) if manifest else None,
    }
    return canonical_sha256(payload)


def _decision_records(
    kind: str,
    decisions: list[Decision],
    items: pd.DataFrame,
    crafted_level_protect: int,
) -> tuple[ReportDecision, ...]:
    rows = {str(row["Id"]): row for _, row in items.iterrows()}
    records = []
    for decision in decisions:
        row = rows[str(decision.id)]
        if kind == "ghosts":
            # ghost_rules only returns unprotected rows. Exotic rarity is
            # deliberately not a ghost rail, so the generic rails helper
            # cannot be used here.
            level, protection_reason = None, ""
        else:
            level, protection_reason = rails.protection(
                row, crafted_level_protect
            )
        records.append(
            ReportDecision(
                id=str(decision.id),
                kind=kind,
                hash=str(decision.hash),
                name=str(decision.name),
                owner=str(decision.owner),
                action=decision.action,
                tag=decision.tag,
                note=decision.note,
                kept_id=str(decision.kept_id),
                reason=reason_slug(decision.note)[1],
                original_tag=str(row["Tag"]),
                original_notes=str(row["Notes"]),
                protection_level=level,
                protection_reason=protection_reason,
                locked=rails.is_true(row.get("Locked", "")),
                equipped=rails.is_true(row.get("Equipped", "")),
                in_loadout=bool(str(row.get("Loadouts", "")).strip()),
            )
        )
    return tuple(records)


def _evaluation_snapshot(
    evaluation: ArmorEvaluation,
    cited_ids: frozenset[str],
    kept_elsewhere: frozenset[tuple[str, str]],
) -> dict:
    data = asdict(evaluation)
    data["cited_by_close_pass"] = evaluation.id in cited_ids
    data["combo_kept_elsewhere"] = (
        evaluation.hash,
        evaluation.item_archetype,
    ) in kept_elsewhere
    return data


def snapshot_dict(run: ReportRun) -> dict:
    """Return the stable, JSON-safe schema consumed by later M7 tickets."""
    sections = []
    for section in run.sections:
        section_data = {
            "kind": section.kind,
            "source": _snapshot_source(section.source),
            "decisions": [asdict(decision) for decision in section.decisions],
        }
        if section.armor is not None:
            section_data["armor"] = {
                "scored": section.armor.scored,
                "evaluations": [
                    _evaluation_snapshot(
                        evaluation,
                        section.armor.cited_ids,
                        section.armor.kept_elsewhere,
                    )
                    for evaluation in section.armor.evaluations
                ],
                "cited_ids": sorted(section.armor.cited_ids),
                "kept_elsewhere": [
                    {"hash": item_hash, "archetype": archetype}
                    for item_hash, archetype in sorted(section.armor.kept_elsewhere)
                ],
            }
        sections.append(section_data)

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "ruleset_version": RULESET_VERSION,
        "fingerprint": run.fingerprint,
        "inputs": {
            "sources": [_snapshot_source(section.source) for section in run.sections],
            "effective_config": _snapshot_config(run.effective_config),
            "wishlists_used": run.wishlists_used,
            "wishlist_sources": [
                asdict(source) for source in run.wishlist_sources
            ],
            "manifest": asdict(run.manifest) if run.manifest else None,
        },
        "keep_trash_conflicts": run.keep_trash_conflicts,
        "warnings": [
            warning.render(redact_path=True) for warning in run.warnings
        ],
        "sections": sections,
    }


def snapshot_json(run: ReportRun) -> str:
    return json.dumps(
        snapshot_dict(run),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def run_report(
    *,
    config_path: str | Path = "config.toml",
    weapons_path: str | Path = DEFAULT_EXPORT_PATHS["weapons"],
    armor_path: str | Path = DEFAULT_EXPORT_PATHS["armor"],
    ghosts_path: str | Path = DEFAULT_EXPORT_PATHS["ghosts"],
    no_wishlists: bool = False,
) -> ReportRun:
    """Load available exports and run every ordered rules pipeline."""
    cfg = load_config(config_path)
    effective_config = _normalize_config(cfg)
    warnings = []
    sections = []
    conflicts = 0
    wishlists_used = False
    wishlist_sources: tuple[WishlistSourceIdentity, ...] = ()
    manifest = None

    specs = (
        ("weapons", Path(weapons_path), load_weapons),
        ("armor", Path(armor_path), load_armor),
        ("ghosts", Path(ghosts_path), load_ghosts),
    )
    for kind, path, loader in specs:
        try:
            digest_before = sha256_file(path)
        except FileNotFoundError:
            warnings.append(
                ReportWarning(kind=kind, path=str(path), reason="not found")
            )
            continue
        except OSError as e:
            raise SourceReadError(
                f"could not fingerprint {kind} export {path}: {e}"
            ) from e

        try:
            items = loader(path)
        except FileNotFoundError:
            raise SourceReadError(
                f"{kind} export disappeared while being read: {path}"
            ) from None
        except OSError as e:
            raise SourceReadError(f"could not read {kind} export {path}: {e}") from e

        try:
            source_digest = sha256_file(path)
        except OSError as e:
            raise SourceReadError(
                f"{kind} export became unreadable while fingerprinting {path}: {e}"
            ) from e
        if source_digest != digest_before:
            raise SourceReadError(f"{kind} export changed while being read: {path}")
        source = SourceMetadata(
            kind=kind,
            path=str(path),
            item_count=len(items),
            sha256=source_digest,
        )
        armor_details = None
        if kind == "weapons":
            result = resolve_weapons(items, cfg, no_wishlists)
            decisions = result.decisions
            conflicts = result.keep_trash_conflicts
            wishlists_used = result.wishlists_used
            wishlist_sources = result.wishlist_sources
            manifest = result.manifest
        elif kind == "armor":
            armor_result: ArmorPipelineResult = resolve_armor(items, cfg)
            decisions = armor_result.decisions
            armor_details = ArmorSectionDetails(
                scored=armor_result.scored,
                evaluations=armor_result.evaluations,
                cited_ids=armor_result.cited_ids,
                kept_elsewhere=armor_result.kept_elsewhere,
            )
        else:
            decisions = ghost_rules.run(items)

        sections.append(
            ReportSection(
                kind=kind,
                source=source,
                decisions=_decision_records(
                    kind,
                    decisions,
                    items,
                    cfg["rails"]["crafted_level_protect"],
                ),
                armor=armor_details,
            )
        )

    if not sections:
        raise NoExportsError("no exports found in data/in/ — nothing to report on")

    fingerprint = compute_fingerprint(
        {section.kind: section.source.sha256 for section in sections},
        effective_config,
        wishlist_sources,
        manifest,
    )
    return ReportRun(
        sections=tuple(sections),
        effective_config=effective_config,
        keep_trash_conflicts=conflicts,
        warnings=tuple(warnings),
        wishlists_used=wishlists_used,
        wishlist_sources=wishlist_sources,
        manifest=manifest,
        fingerprint=fingerprint,
    )
