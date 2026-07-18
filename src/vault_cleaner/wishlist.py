"""Download, cache, and parse DIM wishlist files.

The format is informal (PLAN.md risks): real lists contain title/description
blocks, `//` comments, stray prose, and malformed lines. Anything that isn't
a well-formed `dimwishlist:` line is skipped, never fatal — but lines that
*try* to be wishlist entries and fail are counted so a format change shows up
in the stats instead of silently matching nothing.
"""

from __future__ import annotations

import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# DIM's "these perks on any weapon" sentinel item id. Wildcard entries are
# skipped (v1 matches per-item only) but counted, so we know they exist.
WILDCARD_ITEM_HASH = 69420

# dimwishlist:item=HASH[&perks=1,2,3][#notes:...]  — negative HASH = trash
LINE_RE = re.compile(r"^dimwishlist:item=(-?\d+)(?:&perks=([\d,]+))?(?:#.*)?$")


class WishlistError(Exception):
    """A wishlist could not be fetched at all (no download, no cache)."""


@dataclass
class Wishlist:
    """Keep/trash rolls per item hash. An empty perk set on a trash entry
    means every roll of that item is trash."""

    name: str = ""
    keep: dict[int, list[frozenset[int]]] = field(default_factory=dict)
    trash: dict[int, list[frozenset[int]]] = field(default_factory=dict)
    skipped: int = 0  # malformed dimwishlist: lines
    wildcards: int = 0  # wildcard-item entries (unsupported in v1)

    @property
    def entries(self) -> int:
        return sum(len(v) for v in self.keep.values()) + sum(len(v) for v in self.trash.values())

    def merge(self, other: "Wishlist") -> None:
        for item, rolls in other.keep.items():
            self.keep.setdefault(item, []).extend(rolls)
        for item, rolls in other.trash.items():
            self.trash.setdefault(item, []).extend(rolls)
        self.skipped += other.skipped
        self.wildcards += other.wildcards


def parse_wishlist(text: str, name: str = "") -> Wishlist:
    wl = Wishlist(name=name)
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("dimwishlist:"):
            continue  # titles, comments, prose — not ours to police
        m = LINE_RE.match(line)
        if not m:
            wl.skipped += 1
            continue
        item = int(m.group(1))
        trash = item < 0
        item = abs(item)
        if item == WILDCARD_ITEM_HASH:
            wl.wildcards += 1
            continue
        perks = frozenset(int(p) for p in (m.group(2) or "").split(",") if p)
        if m.group(2) is not None and not perks:
            # perks= was given but held no perks (e.g. "perks=,"): treating
            # that as an empty set would silently escalate a typo into
            # "any roll" / "whole item" — count it as malformed instead.
            wl.skipped += 1
            continue
        bucket = wl.trash if trash else wl.keep
        bucket.setdefault(item, []).append(perks)
    return wl


def _download(url: str, timeout: int = 30) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # noqa: S310 — config-supplied https URLs
        return r.read().decode("utf-8", errors="replace")


def fetch(
    name: str,
    url: str,
    cache_dir: str | Path = "wishlists",
    max_age_days: float = 7,
    refresh: bool = False,
) -> Path:
    """Return a path to a local copy of the wishlist, downloading if the
    cache is missing or stale. A failed download falls back to a stale cache
    with a warning; with no cache at all it raises WishlistError."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{name}.txt"

    fresh = path.exists() and (time.time() - path.stat().st_mtime) < max_age_days * 86400
    if fresh and not refresh:
        return path

    try:
        text = _download(url)
    except OSError as e:
        if path.exists():
            print(f"warning: {name}: download failed ({e}); using stale cache {path}", file=sys.stderr)
            return path
        raise WishlistError(f"{name}: download failed and no cached copy exists: {e}") from e

    path.write_text(text, encoding="utf-8")
    return path


def load_all(cfg: dict, refresh: bool = False) -> Wishlist:
    """Fetch + parse every configured source into one merged Wishlist."""
    sources = cfg["wishlists"]["sources"]
    if not sources:
        raise WishlistError("no [wishlists.sources] configured in config.toml")
    merged = Wishlist(name="merged")
    for name, url in sources.items():
        path = fetch(
            name, url,
            cache_dir=cfg["paths"]["wishlist_cache_dir"],
            max_age_days=cfg["wishlists"]["max_age_days"],
            refresh=refresh,
        )
        merged.merge(parse_wishlist(path.read_text(encoding="utf-8"), name))
    return merged
