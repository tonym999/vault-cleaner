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
from urllib.parse import urlsplit

# DIM's "these perks on any weapon" sentinel item id. Wildcard entries are
# skipped (v1 matches per-item only) but counted, so we know they exist.
WILDCARD_ITEM_HASH = 69420

# dimwishlist:item=HASH[&perks=1,2,3][#notes:...]  — negative HASH = trash.
# Destiny hashes are uint32, so digit runs are bounded (an unbounded \d+
# would let a pathological line crash int() via Python's digit limit).
# `&perks=` with an empty value is real and deliberate: the Aegis trash
# list writes whole-item entries that way.
LINE_RE = re.compile(r"^dimwishlist:item=(-?\d{1,10})(?:&perks=([\d,]*))?(?:#.*)?$")


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

    def merge(self, other: Wishlist) -> None:
        for item, rolls in other.keep.items():
            self.keep.setdefault(item, []).extend(rolls)
        for item, rolls in other.trash.items():
            self.trash.setdefault(item, []).extend(rolls)
        self.skipped += other.skipped
        self.wildcards += other.wildcards


@dataclass(frozen=True)
class WishlistSourceData:
    """The exact cached bytes parsed for one configured wishlist source."""

    name: str
    url: str
    content: bytes


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
        raw = m.group(2)
        tokens = [p for p in (raw or "").split(",") if p]
        if any(len(p) > 10 for p in tokens):
            wl.skipped += 1  # longer than any uint32 — malformed, never crash
            continue
        perks = frozenset(int(p) for p in tokens)
        if raw and not perks:
            # perks= held only separators (e.g. "perks=,"): treating that as
            # an empty set would silently escalate a typo into "any roll" /
            # "whole item" — count it as malformed instead. (A fully empty
            # "&perks=" is the deliberate whole-item convention and parses.)
            wl.skipped += 1
            continue
        bucket = wl.trash if trash else wl.keep
        bucket.setdefault(item, []).append(perks)
    return wl


def _download(url: str, timeout: int = 30) -> str:
    scheme = urlsplit(url).scheme.casefold()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported wishlist URL scheme {scheme!r}")
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def _is_fresh_cache(path: Path, max_age_days: float) -> bool:
    if max_age_days <= 0:
        return False
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return False
    return age < max_age_days * 86400


def _has_readable_cache(path: Path) -> bool:
    try:
        with path.open("rb"):
            return True
    except OSError:
        return False


def fetch(
    name: str,
    url: str,
    cache_dir: str | Path = "wishlists",
    max_age_days: float = 7,
    refresh: bool = False,
) -> Path:
    """Return a path to a local copy of the wishlist, downloading if the
    cache is missing or stale. A failed download falls back to a stale cache
    with a warning; with no cache at all it raises WishlistError. A
    non-positive ``max_age_days`` always attempts a download instead of
    accepting the cache as fresh."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{name}.txt"

    if _is_fresh_cache(path, max_age_days) and not refresh:
        return path

    try:
        text = _download(url)
    except (OSError, ValueError) as e:  # ValueError: malformed/unsupported URL
        if _has_readable_cache(path):
            print(f"warning: {name}: download failed ({e}); using stale cache {path}", file=sys.stderr)
            return path
        raise WishlistError(f"{name}: download failed and no cached copy exists: {e}") from e

    path.write_text(text, encoding="utf-8")
    return path


def load_all_with_sources(
    cfg: dict,
    refresh: bool = False,
) -> tuple[Wishlist, tuple[WishlistSourceData, ...]]:
    """Fetch each source, then parse and return the same captured bytes."""
    sources = cfg["wishlists"]["sources"]
    if not sources:
        raise WishlistError("no [wishlists.sources] configured in config.toml")
    merged = Wishlist(name="merged")
    loaded = []
    for name, url in sources.items():
        path = fetch(
            name, url,
            cache_dir=cfg["paths"]["wishlist_cache_dir"],
            max_age_days=cfg["wishlists"]["max_age_days"],
            refresh=refresh,
        )
        try:
            content = path.read_bytes()
            text = content.decode("utf-8")
        except (OSError, UnicodeError) as e:
            raise WishlistError(f"{name}: could not read cached wishlist {path}: {e}") from e
        merged.merge(parse_wishlist(text, name))
        loaded.append(WishlistSourceData(name=name, url=url, content=content))
    return merged, tuple(loaded)


def load_all(cfg: dict, refresh: bool = False) -> Wishlist:
    """Compatibility wrapper returning the merged configured wishlists."""
    return load_all_with_sources(cfg, refresh)[0]
