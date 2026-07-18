"""Perk name → hash bridge via Bungie's public manifest.

Wishlists identify perks by hash; the DIM export gives perk *names*. The
bridge is DestinyInventoryItemDefinition from the static manifest content —
public JSON, no API key, no OAuth, no account data, so it stays inside the
project's no-Bungie-API-integration rule (PLAN.md non-goals cover live
inventory access, not static game-content downloads).

The full definitions file is ~200MB, so it's downloaded once, reduced to a
compact name→hashes map (~1MB) cached under the manifest cache dir, and only
re-fetched when Bungie ships a new manifest *version* (checked via the small
index endpoint once the cache goes stale). One name can map to several
hashes — base and enhanced perk variants share a display name — and the map
keeps all of them deliberately.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

MANIFEST_INDEX_URL = "https://www.bungie.net/Platform/Destiny2/Manifest/"
CONTENT_BASE = "https://www.bungie.net"
CACHE_FILENAME = "perk-name-map.json"


class ManifestError(Exception):
    """The perk map could not be produced (no download, no cache)."""


def _get_json(url: str, timeout: int = 300) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 — fixed bungie.net URLs
        return json.load(r)


def _extract_names(defs: dict) -> dict[str, list[int]]:
    """name (casefolded) → all plug item hashes carrying that display name."""
    names: dict[str, list[int]] = {}
    for h, d in defs.items():
        if not d.get("plug"):
            continue
        name = d.get("displayProperties", {}).get("name", "")
        if name:
            names.setdefault(name.casefold(), []).append(int(h))
    return names


def _read_cache(cache: Path) -> dict | None:
    """Return the cached document, or None if it's missing, unreadable,
    corrupt, or structurally invalid (treated identically: rebuild)."""
    try:
        data = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("version"), str):
        return None
    names = data.get("names")
    if not isinstance(names, dict):
        return None
    return data


def load_perk_map(
    cache_dir: str | Path,
    max_age_days: float = 30,
    refresh: bool = False,
) -> dict[str, frozenset[int]]:
    cache_dir = Path(cache_dir)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ManifestError(f"cannot create manifest cache dir {cache_dir}: {e}") from e
    cache = cache_dir / CACHE_FILENAME

    cached = _read_cache(cache)
    if cached is not None and not refresh:
        try:
            age_ok = (time.time() - cache.stat().st_mtime) < max_age_days * 86400
        except OSError:
            age_ok = False
        if age_ok:
            return {n: frozenset(hs) for n, hs in cached["names"].items()}

    # Stale, missing, or forced: ask the (small) index what the current
    # version is before committing to the ~200MB definitions download.
    try:
        index = _get_json(MANIFEST_INDEX_URL, timeout=30)
        version = index["Response"]["version"]
        defs_path = index["Response"]["jsonWorldComponentContentPaths"]["en"][
            "DestinyInventoryItemDefinition"
        ]
    except (OSError, ValueError, KeyError) as e:
        if cached is not None:
            print(f"warning: manifest index unavailable ({e}); using cached perk map", file=sys.stderr)
            return {n: frozenset(hs) for n, hs in cached["names"].items()}
        raise ManifestError(f"manifest index unavailable and no cached perk map: {e}") from e

    if cached is not None and cached["version"] == version and not refresh:
        try:
            cache.touch()  # same manifest — restart the freshness clock
        except OSError:
            pass  # worst case we re-check the index again next run
        return {n: frozenset(hs) for n, hs in cached["names"].items()}

    print(f"downloading Bungie manifest {version} (~200MB, cached after this)...", file=sys.stderr)
    try:
        defs = _get_json(CONTENT_BASE + defs_path)
    except (OSError, ValueError) as e:
        if cached is not None:
            print(f"warning: manifest download failed ({e}); using cached perk map", file=sys.stderr)
            return {n: frozenset(hs) for n, hs in cached["names"].items()}
        raise ManifestError(f"manifest download failed and no cached perk map: {e}") from e

    names = _extract_names(defs)
    try:
        cache.write_text(json.dumps({"version": version, "names": names}), encoding="utf-8")
    except OSError as e:
        # The map is in hand — a failed cache write costs a re-download next
        # run, not this one.
        print(f"warning: could not write perk map cache {cache}: {e}", file=sys.stderr)
    return {n: frozenset(hs) for n, hs in names.items()}
