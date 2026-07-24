"""Reusable ordered weapons and armor pipelines.

The CLI commands and all-passes report call these functions so rule ordering,
external-input identity, and decision semantics have one implementation.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

import pandas as pd

from vault_cleaner.manifest import PerkMapData, load_perk_map_data
from vault_cleaner.rules import armor as armor_rules
from vault_cleaner.rules import armor_close, armor_dupes, dupes
from vault_cleaner.rules import weapons as weapons_rules
from vault_cleaner.rules.armor import ArmorEvaluation
from vault_cleaner.rules.dupes import Decision
from vault_cleaner.wishlist import WishlistError, load_all


@dataclass(frozen=True)
class WishlistSourceIdentity:
    name: str
    url: str
    sha256: str


@dataclass(frozen=True)
class ManifestIdentity:
    version: str
    sha256: str


@dataclass
class WeaponPipelineResult:
    decisions: list[Decision]
    keep_trash_conflicts: int
    wishlists_used: bool
    wishlist_sources: tuple[WishlistSourceIdentity, ...] = ()
    manifest: ManifestIdentity | None = None


@dataclass
class ArmorPipelineResult:
    decisions: list[Decision]
    scored: int
    evaluations: tuple[ArmorEvaluation, ...]
    cited_ids: frozenset[str]
    kept_elsewhere: frozenset[tuple[str, str]]


def json_safe(value: object) -> object:
    """Normalize TOML-compatible values into deterministic JSON values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not valid JSON")
        return value
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, Mapping):
        normalized = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(
                    "JSON object keys must be strings, "
                    f"got {type(key).__name__}"
                )
            normalized[key] = json_safe(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    raise TypeError(f"unsupported JSON value {type(value).__name__}")


def canonical_sha256(value: object) -> str:
    payload = json.dumps(
        json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it all at once."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wishlist_identities(cfg: dict) -> tuple[WishlistSourceIdentity, ...]:
    cache_dir = Path(cfg["paths"]["wishlist_cache_dir"])
    identities = []
    for name, url in sorted(cfg["wishlists"]["sources"].items()):
        path = cache_dir / f"{name}.txt"
        try:
            digest = sha256_file(path)
        except OSError as e:
            raise WishlistError(
                f"{name}: cached wishlist disappeared before it could be fingerprinted: {e}"
            ) from e
        identities.append(WishlistSourceIdentity(name=name, url=url, sha256=digest))
    return tuple(identities)


def _manifest_identity(data: PerkMapData) -> ManifestIdentity:
    semantic_map = {
        name: sorted(hashes)
        for name, hashes in sorted(data.names.items())
    }
    return ManifestIdentity(
        version=data.version,
        sha256=canonical_sha256(semantic_map),
    )


def resolve_weapons(
    weapons: pd.DataFrame,
    cfg: dict,
    no_wishlists: bool = False,
) -> WeaponPipelineResult:
    """Run rails → wishlist → dupes and retain external input identities."""
    crafted_level = cfg["rails"]["crafted_level_protect"]
    if no_wishlists or not cfg["wishlists"]["sources"]:
        return WeaponPipelineResult(
            decisions=dupes.resolve(weapons, crafted_level),
            keep_trash_conflicts=0,
            wishlists_used=False,
        )

    wishlists = load_all(cfg)
    perk_data = load_perk_map_data(
        cfg["paths"]["manifest_cache_dir"],
        cfg["manifest"]["max_age_days"],
    )
    result = weapons_rules.run(weapons, wishlists, perk_data.names, crafted_level)
    return WeaponPipelineResult(
        decisions=result.decisions,
        keep_trash_conflicts=result.keep_trash_conflicts,
        wishlists_used=True,
        wishlist_sources=_wishlist_identities(cfg),
        manifest=_manifest_identity(perk_data),
    )


def resolve_armor(armor: pd.DataFrame, cfg: dict) -> ArmorPipelineResult:
    """Run rails → exact dupes → close dupes → score, earlier rules first."""
    decisions = armor_dupes.run(armor, cfg["rails"]["crafted_level_protect"])
    remaining = armor[~armor["Id"].isin({decision.id for decision in decisions})]

    close_decisions = armor_close.run(remaining, cfg)
    decisions += close_decisions
    remaining = remaining[
        ~remaining["Id"].isin({decision.id for decision in close_decisions})
    ]

    # Review-noted pieces stay in the vault, and cited close-pass partners
    # survive by construction. Both count for the score pass's last-of-kind
    # guard.
    review_ids = {decision.id for decision in decisions if decision.action == "review"}
    cited = {decision.kept_id for decision in close_decisions}
    kept_elsewhere = frozenset(
        (row["Hash"], row["Archetype"])
        for _, row in armor[armor["Id"].isin(review_ids | cited)].iterrows()
    )
    score_result = armor_rules.run(remaining, cfg, kept_elsewhere)

    # A close note must never cite a piece that this later score pass junks.
    score_decisions = [
        decision
        for decision in score_result.decisions
        if not (decision.action == "junk" and decision.id in cited)
    ]
    return ArmorPipelineResult(
        decisions=decisions + score_decisions,
        scored=score_result.scored,
        evaluations=tuple(score_result.evaluations),
        cited_ids=frozenset(cited),
        kept_elsewhere=kept_elsewhere,
    )
