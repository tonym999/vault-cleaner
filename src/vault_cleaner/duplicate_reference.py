"""Human-readable references used by duplicate-facing presentations.

The duplicate rules keep opaque instance ids as their machine identity.  This
module only renders a compact label for a row that a rule has already selected
and sanitises values copied from a DIM export before they enter a Note or a
terminal summary.  It deliberately contains no grouping, ranking, or rule
selection logic.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from hashlib import sha256

_TOOL_MARKER_RE = re.compile(r"#vc-", re.IGNORECASE)
_STRUCTURAL_CHARS = str.maketrans({"[": "［", "]": "］", ";": "；"})
_MAX_FRAGMENT = 48
_MAX_REFERENCE = 220
_MAX_ID_SUFFIX_WIDTH = 16
_MAX_ID_PREFIX_WIDTH = 8


def safe_fragment(
    value: object,
    *,
    limit: int = _MAX_FRAGMENT,
    escape_structure: bool = True,
) -> str:
    """Return bounded, single-line presentation text for an export value.

    CSV values are untrusted presentation input.  Control/format characters
    become spaces, whitespace collapses, the ASCII ``#vc-`` sequence is
    neutralised, and reference punctuation is full-width escaped so a field
    cannot forge another tool hashtag or structural clause.  The raw value is
    never changed by this helper.
    """
    text = str(value)
    text = "".join(
        " " if unicodedata.category(char).startswith("C") else char
        for char in text
    )
    text = " ".join(text.split())
    text = _TOOL_MARKER_RE.sub("#vc‑", text)
    if escape_structure:
        text = text.translate(_STRUCTURAL_CHARS)
    if len(text) > limit:
        text = text[: max(0, limit - 1)].rstrip() + "…"
    return text


def _raw_id(value: object) -> str:
    return str(value).strip().strip('"')


def _id_suffix(raw: str, width: int) -> str:
    if len(raw) <= width:
        return safe_fragment(raw, limit=24)
    return "…" + safe_fragment(raw[-width:], limit=24)


def _id_prefix_suffix(raw: str, prefix_width: int) -> str:
    suffix = raw[-4:]
    # The caller only asks for this projection when the raw id is longer than
    # the four-character suffix.  Keep the two source slices disjoint so the
    # display can never become the complete long id.
    max_prefix = max(1, len(raw) - len(suffix) - 1)
    prefix = raw[: min(prefix_width, max_prefix)]
    return (
        f"{safe_fragment(prefix, limit=12)}…"
        f"{safe_fragment(suffix, limit=8)}"
    )


def short_id(
    value: object, *, distinguish_from: Iterable[object] = ()
) -> str:
    """Render an opaque DIM id without parsing it as a number.

    The normal form is the final four characters.  When that presentation
    collides within the supplied compatibility group, grow the suffix by
    string comparison only.  Extremely shared suffixes use a truthful
    leading-prefix projection or a bounded group discriminator so the
    reference remains concise and stable.
    """
    raw = _raw_id(value)
    others = tuple(
        other_raw
        for other_raw in (_raw_id(other) for other in distinguish_from)
        if other_raw != raw
    )
    rendered = _id_suffix(raw, 4)
    if not any(rendered == _id_suffix(other, 4) for other in others):
        return rendered

    # Keep every suffix expansion strictly shorter than the source id.  In
    # particular, a 16-character id must not be emitted in full just because
    # its first character is the only distinguishing position.
    for width in range(5, min(_MAX_ID_SUFFIX_WIDTH, len(raw) - 1) + 1):
        rendered = _id_suffix(raw, width)
        if all(rendered != _id_suffix(other, width) for other in others):
            return rendered

    # Prefer a truthful leading prefix plus suffix.  Unlike an unpositioned
    # differing character, this remains meaningful when several group members
    # share the same first character.  Every member must use the same complete
    # comparison set so a referenced row's label is stable across notes.
    if len(raw) >= 6:
        for width in range(1, min(_MAX_ID_PREFIX_WIDTH, len(raw) - 4) + 1):
            rendered = _id_prefix_suffix(raw, width)
            if all(
                rendered != _id_prefix_suffix(other, width)
                for other in others
            ):
                return rendered

    # Pathological ids can still share the bounded prefix and suffix.  A
    # stable group rank is a bounded deterministic discriminator while the
    # visible prefix/suffix remain truthful; the digest makes the target
    # projection explicit without exposing the complete opaque id.
    members = sorted({raw, *others})
    rank = members.index(raw) + 1
    digest = sha256(raw.encode("utf-8")).hexdigest()[:8]
    if len(raw) == 5:
        return f"…{safe_fragment(raw[-4:], limit=8)}~{rank:x}-{digest}"
    return (
        f"{safe_fragment(raw[:1], limit=4)}…"
        f"{safe_fragment(raw[-4:], limit=8)}~{rank:x}-{digest}"
    )


def _reference(parts: Iterable[str]) -> str:
    body = "; ".join(part for part in parts if part)
    # Keep the closing bracket even when a pathological collection of fields
    # would otherwise exceed the note budget.
    if len(body) + 2 > _MAX_REFERENCE:
        body = body[: _MAX_REFERENCE - 3].rstrip() + "…"
    return f"[{body}]"


def weapon_reference(
    row,
    perk_prefix: Iterable[str] = (),
    *,
    distinguish_from: Iterable[object] = (),
) -> str:
    """Render a selected weapon row and its already-measured roll prefix."""
    parts = [
        f"id {short_id(row.get('Id', ''), distinguish_from=distinguish_from)}"
    ]
    owner = safe_fragment(row.get("Owner", ""))
    if owner:
        parts.append(f"owner {owner}")
    tier = safe_fragment(row.get("Tier", ""), limit=12)
    if tier:
        parts.append(f"Tier {tier}")
    masterwork = safe_fragment(row.get("Masterwork Tier", ""), limit=12)
    if masterwork:
        parts.append(f"MW{masterwork}")
    crafted = safe_fragment(row.get("Crafted Level", ""), limit=12)
    if str(row.get("Crafted", "")).strip().casefold() == "crafted" and crafted:
        parts.append(f"crafted lv{crafted}")
    perks = [safe_fragment(perk) for perk in perk_prefix if str(perk).strip()]
    if perks:
        parts.append("roll " + " / ".join(perks[-2:]))
    return _reference(parts)


def armor_reference(
    row,
    spirits: Iterable[str] = (),
    *,
    distinguish_from: Iterable[object] = (),
) -> str:
    """Render a selected armor row and, when available, its Spirit pair."""
    parts = [
        f"id {short_id(row.get('Id', ''), distinguish_from=distinguish_from)}"
    ]
    owner = safe_fragment(row.get("Owner", ""))
    if owner:
        parts.append(f"owner {owner}")
    masterwork = safe_fragment(row.get("Masterwork Tier", ""), limit=12)
    if masterwork:
        parts.append(f"MW{masterwork}")
    power = safe_fragment(row.get("Power", ""), limit=12)
    if power:
        parts.append(f"power {power}")
    tuning = safe_fragment(row.get("Tuning Stat", ""))
    if tuning:
        parts.append(f"tuning {tuning}")
    spirit_names = []
    for spirit in spirits:
        rendered = safe_fragment(spirit)
        if rendered.casefold().startswith("spirit of the "):
            rendered = rendered[len("Spirit of the "):]
        elif rendered.casefold().startswith("spirit of "):
            rendered = rendered[len("Spirit of "):]
        if rendered:
            spirit_names.append(rendered)
    if spirit_names:
        parts.append("spirits " + " + ".join(spirit_names))
    return _reference(parts)


def note_tail(note: object) -> str:
    """Return the current generated hashtag fragment for terminal summaries."""
    return str(note).rsplit("#vc-", 1)[-1]
