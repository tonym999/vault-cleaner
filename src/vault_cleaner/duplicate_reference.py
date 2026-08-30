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

_TOOL_MARKER_RE = re.compile(r"#vc-", re.IGNORECASE)
_STRUCTURAL_CHARS = str.maketrans({"[": "［", "]": "］", ";": "；"})
_MAX_FRAGMENT = 48
_MAX_REFERENCE = 220


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


def short_id(
    value: object, *, distinguish_from: Iterable[object] = ()
) -> str:
    """Render an opaque DIM id without parsing it as a number.

    The normal form is the final four characters.  When that presentation
    collides with the current candidate's suffix, grow the suffix by string
    comparison only.  Extremely shared suffixes use one differing character
    (or a bounded length marker) so the reference remains concise.
    """
    raw = _raw_id(value)
    others = tuple(_raw_id(other) for other in distinguish_from)
    rendered = _id_suffix(raw, 4)
    if not any(rendered == _id_suffix(other, 4) for other in others):
        return rendered

    for width in range(5, min(len(raw), 16) + 1):
        rendered = _id_suffix(raw, width)
        if all(rendered != _id_suffix(other, width) for other in others):
            return rendered

    # If the ids share every bounded suffix, expose a single differing source
    # character rather than leaking an unbounded/full instance id.
    for other in others:
        for index, (left, right) in enumerate(zip(raw, other)):
            if left != right:
                return (
                    f"{safe_fragment(left, limit=4)}…"
                    f"{safe_fragment(raw[-4:], limit=8)}"
                )
    return (
        f"{safe_fragment(raw[:1], limit=4)}…"
        f"{safe_fragment(raw[-4:], limit=8)}~{len(raw)}"
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
