"""Download, cache, and parse DIM wishlist files.

The format is informal (PLAN.md risks): real lists contain title/description
blocks, `//` comments, stray prose, and malformed lines. Anything that isn't
a well-formed `dimwishlist:` line is skipped, never fatal — but lines that
*try* to be wishlist entries and fail are counted so a format change shows up
in the stats instead of silently matching nothing.
"""

from __future__ import annotations

import collections.abc
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
LINE_RE = re.compile(r"^dimwishlist:item=(-?\d{1,10})(?:&perks=([\d,]*))?(#.*)?$")

FAMILY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ACTIVITIES = ("any", "pve", "pvp")
TIER_FORMATS = ("none", "ciceron-aegis")
SOURCE_KEYS = frozenset({"url", "family", "activity", "tier_format"})
TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}

TITLE_RE = re.compile(r"^@?title:(.+)$")
DESC_RE = re.compile(r"^@?description:(.+)$")
CICERON_KEEP_TIER_RE = re.compile(r"^(?:\([^()]{1,40} version\) - )?Aegis Endgame ([SA]) Tier\.")
CICERON_TRASH_TIER_RE = re.compile(r"^([DEF]) Tier\.")


class WishlistError(Exception):
    """A wishlist could not be fetched at all (no download, no cache)."""


class WishlistConfigError(ValueError):
    """Invalid [wishlists.sources] configuration."""


@dataclass(frozen=True)
class WishlistSourceSpec:
    name: str
    url: str
    family: str
    activity: str  # one of ACTIVITIES
    tier_format: str  # one of TIER_FORMATS


def source_specs(sources: collections.abc.Mapping[str, object]) -> tuple[WishlistSourceSpec, ...]:
    if not isinstance(sources, collections.abc.Mapping):
        raise WishlistConfigError(f"must be a table, got {type(sources).__name__}")

    specs: list[WishlistSourceSpec] = []
    for name, val in sources.items():
        if isinstance(val, str):
            if not val:
                raise WishlistConfigError(f"{name}: url cannot be empty")
            specs.append(
                WishlistSourceSpec(
                    name=name,
                    url=val,
                    family=name,
                    activity="any",
                    tier_format="none",
                )
            )
        elif isinstance(val, collections.abc.Mapping):
            unknown = sorted(set(val.keys()) - SOURCE_KEYS)
            if unknown:
                raise WishlistConfigError(f"{name}: unknown key(s): {', '.join(unknown)}")

            if "url" not in val:
                raise WishlistConfigError(f"{name}: missing required key 'url'")
            url = val["url"]
            if not isinstance(url, str) or isinstance(url, bool):
                raise WishlistConfigError(f"{name}.url must be a string, got {type(url).__name__}")
            if not url:
                raise WishlistConfigError(f"{name}: url cannot be empty")

            if "family" not in val:
                raise WishlistConfigError(f"{name}: missing required key 'family'")
            family = val["family"]
            if not isinstance(family, str) or isinstance(family, bool):
                raise WishlistConfigError(f"{name}.family must be a string, got {type(family).__name__}")
            if not FAMILY_RE.match(family):
                raise WishlistConfigError(f"{name}: invalid family {family!r}; must match {FAMILY_RE.pattern}")

            activity = val.get("activity", "any")
            if not isinstance(activity, str) or isinstance(activity, bool):
                raise WishlistConfigError(f"{name}.activity must be a string, got {type(activity).__name__}")
            if activity not in ACTIVITIES:
                raise WishlistConfigError(f"{name}: invalid activity {activity!r}; must be one of {ACTIVITIES}")

            tier_format = val.get("tier_format", "none")
            if not isinstance(tier_format, str) or isinstance(tier_format, bool):
                raise WishlistConfigError(f"{name}.tier_format must be a string, got {type(tier_format).__name__}")
            if tier_format not in TIER_FORMATS:
                raise WishlistConfigError(f"{name}: invalid tier_format {tier_format!r}; must be one of {TIER_FORMATS}")

            specs.append(
                WishlistSourceSpec(
                    name=name,
                    url=url,
                    family=family,
                    activity=activity,
                    tier_format=tier_format,
                )
            )
        else:
            raise WishlistConfigError(f"{name}: expected a string URL or table, got {type(val).__name__}")

    return tuple(specs)


@dataclass(frozen=True, slots=True)
class WishlistEntry:
    source: str
    family: str
    polarity: str  # "keep" | "trash"
    item_hash: int
    perks: frozenset[int]  # the same object stored in keep/trash
    notes: str | None  # effective notes, stripped; None if absent or empty after strip
    tags: tuple[str, ...]  # casefolded tokens in file order, duplicates removed
    section_title: str | None  # most recent title: text, stripped
    activities: frozenset[str]  # subset of {"pve", "pvp"}
    activity_basis: str  # "tags" | "source" | "unknown"
    tier: str | None  # "S".."F"
    tier_status: str  # "parsed" | "unrecognized" | "not-declared"


@dataclass
class Wishlist:
    """Keep/trash rolls per item hash. An empty perk set on a trash entry
    means every roll of that item is trash."""

    name: str = ""
    family: str = ""
    keep: dict[int, list[frozenset[int]]] = field(default_factory=dict)
    trash: dict[int, list[frozenset[int]]] = field(default_factory=dict)
    keep_evidence: dict[int, list[WishlistEntry]] | None = None
    trash_evidence: dict[int, list[WishlistEntry]] | None = None
    skipped: int = 0  # malformed dimwishlist: lines
    wildcards: int = 0  # wildcard-item entries (unsupported in v1)
    section_titles: int = 0
    ignored_note_segments: int = 0
    declared_title: str | None = None
    declared_description: str | None = None

    @property
    def entries(self) -> int:
        return sum(len(v) for v in self.keep.values()) + sum(len(v) for v in self.trash.values())

    def merge(self, other: Wishlist) -> None:
        has_self_evidence = self.keep_evidence is not None
        has_other_evidence = other.keep_evidence is not None
        if has_self_evidence != has_other_evidence:
            raise ValueError("cannot merge evidence-bearing wishlist with evidence-free wishlist")

        for item, rolls in other.keep.items():
            self.keep.setdefault(item, []).extend(rolls)
        for item, rolls in other.trash.items():
            self.trash.setdefault(item, []).extend(rolls)

        if has_self_evidence:
            assert self.keep_evidence is not None
            assert other.keep_evidence is not None
            assert self.trash_evidence is not None
            assert other.trash_evidence is not None
            for item, entries in other.keep_evidence.items():
                self.keep_evidence.setdefault(item, []).extend(entries)
            for item, entries in other.trash_evidence.items():
                self.trash_evidence.setdefault(item, []).extend(entries)

        self.skipped += other.skipped
        self.wildcards += other.wildcards
        self.section_titles += other.section_titles
        self.ignored_note_segments += other.ignored_note_segments


@dataclass(frozen=True)
class WishlistSourceData:
    """The exact cached bytes parsed for one configured wishlist source."""

    name: str
    url: str
    content: bytes


def parse_wishlist(
    text: str,
    name: str = "",
    *,
    spec: WishlistSourceSpec | None = None,
    evidence: bool = False,
) -> Wishlist:
    if evidence and spec is None:
        raise ValueError("spec is required when evidence=True")

    text = text.replace("\r\r\n", "\r\n")

    wl = Wishlist(
        name=name,
        family=spec.family if spec is not None else "",
        keep_evidence={} if evidence else None,
        trash_evidence={} if evidence else None,
    )

    if not evidence:
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

    assert spec is not None
    block_notes: str | None = None
    current_title: str | None = None

    last_raw: str | None = None
    last_parsed: tuple[str | None, tuple[str, ...], bool] = (None, (), False)

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("//notes:"):
            block_notes = line[len("//notes:"):]
        elif line == "" or line.startswith("//"):
            block_notes = None

        tm = TITLE_RE.match(line)
        if tm:
            t_text = tm.group(1).strip()
            current_title = t_text
            wl.section_titles += 1
            if wl.declared_title is None:
                wl.declared_title = t_text

        dm = DESC_RE.match(line)
        if dm:
            d_text = dm.group(1).strip()
            if wl.declared_description is None:
                wl.declared_description = d_text

        if not line.startswith("dimwishlist:"):
            continue

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
            wl.skipped += 1
            continue
        perks = frozenset(int(p) for p in tokens)
        if raw and not perks:
            wl.skipped += 1
            continue

        tail_raw = m.group(3)
        if tail_raw and tail_raw.startswith("#notes:"):
            tail = tail_raw[len("#notes:"):]
            tail_head = tail.split("|", 1)[0]
            if len(tail_head) > 1:
                chosen_source = tail
            else:
                chosen_source = block_notes
        else:
            chosen_source = block_notes

        if chosen_source is None:
            notes = None
            tags = ()
            has_ignored = False
        elif chosen_source == last_raw:
            notes, tags, has_ignored = last_parsed
        else:
            parts = chosen_source.split("|")
            left = parts[0].strip()
            notes = left if left else None
            segments = parts[1:]
            has_ignored = False
            tags = ()
            if segments:
                first_seg = segments[0]
                m_tags = re.match(r"^\s*tags:([^|]*)$", first_seg)
                if m_tags:
                    tag_str = m_tags.group(1)
                    tag_tokens = []
                    seen_tags = set()
                    for t in re.split(r"[,\s]+", tag_str):
                        if not t:
                            continue
                        cf = t.casefold()
                        if cf not in seen_tags:
                            seen_tags.add(cf)
                            tag_tokens.append(cf)
                    tags = tuple(tag_tokens)
                    if len(segments) > 1:
                        has_ignored = True
                else:
                    has_ignored = True
            last_raw = chosen_source
            last_parsed = (notes, tags, has_ignored)

        if has_ignored:
            wl.ignored_note_segments += 1

        derived_act = set()
        for t in tags:
            if t == "pve" or t.startswith("pve-") or t == "god-pve":
                derived_act.add("pve")
            if t == "pvp" or t.startswith("pvp-") or t == "god-pvp":
                derived_act.add("pvp")
        if derived_act:
            activities = frozenset(derived_act)
            activity_basis = "tags"
        elif spec.activity in ("pve", "pvp"):
            activities = frozenset({spec.activity})
            activity_basis = "source"
        else:
            activities = frozenset()
            activity_basis = "unknown"

        tier: str | None = None
        if spec.tier_format == "ciceron-aegis":
            if notes is not None:
                tier_re = CICERON_TRASH_TIER_RE if trash else CICERON_KEEP_TIER_RE
                tm_tier = tier_re.search(notes)
                if tm_tier:
                    tier = tm_tier.group(1)
                    tier_status = "parsed"
                else:
                    tier_status = "unrecognized"
            else:
                tier_status = "unrecognized"
        else:
            tier_status = "not-declared"

        entry = WishlistEntry(
            source=name,
            family=spec.family,
            polarity="trash" if trash else "keep",
            item_hash=item,
            perks=perks,
            notes=notes,
            tags=tags,
            section_title=current_title,
            activities=activities,
            activity_basis=activity_basis,
            tier=tier,
            tier_status=tier_status,
        )

        bucket = wl.trash if trash else wl.keep
        bucket.setdefault(item, []).append(perks)
        assert wl.trash_evidence is not None and wl.keep_evidence is not None
        evidence_bucket = wl.trash_evidence if trash else wl.keep_evidence
        evidence_bucket.setdefault(item, []).append(entry)

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


@dataclass(frozen=True)
class FetchResult:
    path: Path
    status: str  # "cache" | "downloaded" | "stale-cache-after-failed-download"
    cache_written_at: float | None  # st_mtime after the call; None if stat fails
    error: str | None = None  # download error text for the stale fallback


def fetch_with_status(
    name: str,
    url: str,
    cache_dir: str | Path = "wishlists",
    max_age_days: float = 7,
    refresh: bool = False,
) -> FetchResult:
    """Return FetchResult for a local copy of the wishlist, downloading if
    the cache is missing or stale. A failed download falls back to a stale cache
    with a warning; with no usable cache at all it raises WishlistError."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{name}.txt"

    def _get_mtime(p: Path) -> float | None:
        try:
            return p.stat().st_mtime
        except OSError:
            return None

    if _is_fresh_cache(path, max_age_days) and not refresh:
        return FetchResult(
            path=path,
            status="cache",
            cache_written_at=_get_mtime(path),
            error=None,
        )

    try:
        text = _download(url)
    except (OSError, ValueError) as e:  # ValueError: malformed/unsupported URL
        if _has_readable_cache(path):
            print(f"warning: {name}: download failed ({e}); using stale cache {path}", file=sys.stderr)
            return FetchResult(
                path=path,
                status="stale-cache-after-failed-download",
                cache_written_at=_get_mtime(path),
                error=str(e),
            )
        raise WishlistError(f"{name}: download failed and no usable cached copy exists: {e}") from e

    path.write_text(text, encoding="utf-8", newline="")
    return FetchResult(
        path=path,
        status="downloaded",
        cache_written_at=_get_mtime(path),
        error=None,
    )


def fetch(
    name: str,
    url: str,
    cache_dir: str | Path = "wishlists",
    max_age_days: float = 7,
    refresh: bool = False,
) -> Path:
    """Return a path to a local copy of the wishlist, downloading if the
    cache is missing or stale. A failed download falls back to a stale cache
    with a warning; with no usable cache at all it raises WishlistError. A
    non-positive ``max_age_days`` always attempts a download instead of
    accepting the cache as fresh."""
    return fetch_with_status(
        name,
        url,
        cache_dir=cache_dir,
        max_age_days=max_age_days,
        refresh=refresh,
    ).path


@dataclass(frozen=True)
class WishlistSourceStatus:
    spec: WishlistSourceSpec
    fetch: FetchResult
    max_age_days: float
    declared_title: str | None
    declared_description: str | None
    keep_entries: int
    keep_items: int
    trash_entries: int
    trash_items: int
    skipped: int
    wildcards: int
    noted_entries: int
    tagged_entries: int
    tier_counts: tuple[tuple[str, int], ...]  # S,A,B,C,D,E,F order, zero counts omitted
    unrecognized_tier_entries: int
    ignored_note_segment_entries: int  # this source's own Wishlist.ignored_note_segments, never the merged sum
    content_revision: None = None  # never declared by the selected files; always None in this ticket


@dataclass(frozen=True)
class WishlistEvidenceSet:
    merged: Wishlist  # evidence-bearing
    sources: tuple[WishlistSourceData, ...]  # identical to load_all_with_sources
    statuses: tuple[WishlistSourceStatus, ...]


def load_source_with_evidence(
    spec: WishlistSourceSpec,
    cfg: dict,
    refresh: bool = False,
) -> tuple[Wishlist, WishlistSourceData, WishlistSourceStatus]:
    cache_dir = cfg["paths"]["wishlist_cache_dir"]
    max_age = float(cfg["wishlists"]["max_age_days"])
    fetch_res = fetch_with_status(
        spec.name,
        spec.url,
        cache_dir=cache_dir,
        max_age_days=max_age,
        refresh=refresh,
    )
    try:
        content = fetch_res.path.read_bytes()
        text = content.decode("utf-8")
    except (OSError, UnicodeError) as e:
        raise WishlistError(f"{spec.name}: could not read cached wishlist {fetch_res.path}: {e}") from e

    wl = parse_wishlist(text, spec.name, spec=spec, evidence=True)
    source_data = WishlistSourceData(name=spec.name, url=spec.url, content=content)

    all_entries = [
        e
        for entries in list((wl.keep_evidence or {}).values()) + list((wl.trash_evidence or {}).values())
        for e in entries
    ]
    noted_count = sum(1 for e in all_entries if e.notes is not None)
    tagged_count = sum(1 for e in all_entries if len(e.tags) > 0)
    unrec_tier_count = sum(1 for e in all_entries if e.tier_status == "unrecognized")

    raw_tier_counts: dict[str, int] = {}
    for e in all_entries:
        if e.tier_status == "parsed" and e.tier:
            raw_tier_counts[e.tier] = raw_tier_counts.get(e.tier, 0) + 1

    tier_order = ("S", "A", "B", "C", "D", "E", "F")
    tier_counts = tuple(
        (t, raw_tier_counts[t]) for t in tier_order if raw_tier_counts.get(t, 0) > 0
    )

    status = WishlistSourceStatus(
        spec=spec,
        fetch=fetch_res,
        max_age_days=max_age,
        declared_title=wl.declared_title,
        declared_description=wl.declared_description,
        keep_entries=sum(len(v) for v in wl.keep.values()),
        keep_items=len(wl.keep),
        trash_entries=sum(len(v) for v in wl.trash.values()),
        trash_items=len(wl.trash),
        skipped=wl.skipped,
        wildcards=wl.wildcards,
        noted_entries=noted_count,
        tagged_entries=tagged_count,
        tier_counts=tier_counts,
        unrecognized_tier_entries=unrec_tier_count,
        ignored_note_segment_entries=wl.ignored_note_segments,
        content_revision=None,
    )
    return wl, source_data, status


def load_all_with_evidence(
    cfg: dict,
    refresh: bool = False,
) -> WishlistEvidenceSet:
    sources = cfg["wishlists"]["sources"]
    if not sources:
        raise WishlistError("no [wishlists.sources] configured in config.toml")
    specs = source_specs(sources)
    merged = Wishlist(name="merged", keep_evidence={}, trash_evidence={})
    loaded_sources: list[WishlistSourceData] = []
    loaded_statuses: list[WishlistSourceStatus] = []
    for spec in specs:
        wl, src_data, status = load_source_with_evidence(spec, cfg, refresh=refresh)
        merged.merge(wl)
        loaded_sources.append(src_data)
        loaded_statuses.append(status)
    return WishlistEvidenceSet(
        merged=merged,
        sources=tuple(loaded_sources),
        statuses=tuple(loaded_statuses),
    )


def load_all_with_sources(
    cfg: dict,
    refresh: bool = False,
) -> tuple[Wishlist, tuple[WishlistSourceData, ...]]:
    """Fetch each source, then parse and return the same captured bytes."""
    sources = cfg["wishlists"]["sources"]
    if not sources:
        raise WishlistError("no [wishlists.sources] configured in config.toml")
    specs = source_specs(sources)
    merged = Wishlist(name="merged")
    loaded = []
    for spec in specs:
        path = fetch(
            spec.name,
            spec.url,
            cache_dir=cfg["paths"]["wishlist_cache_dir"],
            max_age_days=cfg["wishlists"]["max_age_days"],
            refresh=refresh,
        )
        try:
            content = path.read_bytes()
            text = content.decode("utf-8")
        except (OSError, UnicodeError) as e:
            raise WishlistError(f"{spec.name}: could not read cached wishlist {path}: {e}") from e
        merged.merge(parse_wishlist(text, spec.name))
        loaded.append(WishlistSourceData(name=spec.name, url=spec.url, content=content))
    return merged, tuple(loaded)


def load_all(cfg: dict, refresh: bool = False) -> Wishlist:
    """Compatibility wrapper returning the merged configured wishlists."""
    return load_all_with_sources(cfg, refresh)[0]
