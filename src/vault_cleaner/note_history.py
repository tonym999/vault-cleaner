"""Preserve user Notes while replacing trailing vault-cleaner clauses.

DIM round-trips Notes verbatim.  Rules therefore append their current
``#vc-junk:`` or ``#vc-review:`` clause to the user's existing text, but a
fresh run must not accumulate another copy of a clause that vault-cleaner
previously appended.  Only complete, known tool clauses at the very end of
the cell are removed; ambiguous text and anything following a tool-looking
fragment are preserved.
"""

from __future__ import annotations

import re

_MARKER_RE = re.compile(r"(?i)(?:^|\s)(#vc-(?:junk|review): )")

_EXACT_REASON = (
    r"(?:dupe-(?:lower|tie)|armor-exact-dupe(?:-tie)?|armor-exotic-class-dupe)"
    r"(?: \((?:loadout|locked|exotic)\))?"
)
_WINNER_REASON = (
    r"(?:higher (?:Tier|Masterwork Tier|Crafted Level|stat total|Power)"
    r"|Masterwork Tier|Power"
    r"|hard protection|loadout membership|lock"
    r"|deterministic(?: lowest)? id tie-break)"
)
_ARMOR_SCORE = (
    r"armor-score -?[0-9]+(?:\.[0-9]+)? < floor -?[0-9]+(?:\.[0-9]+)? "
    r"\(best: [^()\r\n]+, rank [0-9]+/[0-9]+ [^()\r\n]+\)"
)
_TUNING_VALUE = r"(?:Weapons|Health|Class|Grenade|Super|Melee|none/unknown)"
_EXACT_TUNING = (
    rf"; Candidate Tuning Mod Slot: {_TUNING_VALUE}"
    rf"; Survivor Tuning Mod Slot: {_TUNING_VALUE}"
)
_CLOSE_TUNING = (
    rf"; Candidate Tuning Mod Slot: {_TUNING_VALUE}"
    rf"; Partner Tuning Mod Slot: {_TUNING_VALUE}"
)

_GENERATED_CLAUSE_RES = tuple(
    re.compile(pattern) for pattern in (
        # Current human-readable exact-dupe notes.
        (
            rf"#vc-(?:junk|review): {_EXACT_REASON}; keep "
            rf"\[[^\]\r\n]*\]; winner {_WINNER_REASON}"
            rf"(?:{_EXACT_TUNING})?"
        ),
        # Legacy exact-dupe notes retained for migration from older exports.
        rf"#vc-(?:junk|review): {_EXACT_REASON}, kept [^\s]+",
        # Current and legacy close-dupe advice.
        (
            r"#vc-review: armor-dominated by; compare \[[^\]\r\n]*\]; "
            r"\+[0-9]+ total; partner "
            r"(?:largest stat surplus|deterministic id tie-break)"
            rf"(?:{_CLOSE_TUNING})?"
        ),
        (
            r"#vc-review: armor-similar to; compare \[[^\]\r\n]*\]; "
            r"[^;\r\n]+; partner "
            r"(?:closest stat distance|deterministic id tie-break)"
            rf"(?:{_CLOSE_TUNING})?"
        ),
        r"#vc-review: armor-dominated by [^\s]+ \(\+[0-9]+ total\)",
        r"#vc-review: armor-similar to [^\s]+ \([^()\r\n]+\)",
        # Other current rule families.  The #vc- namespace is tool-owned only
        # when one of these complete clauses is the trailing Notes suffix.
        (
            r"#vc-(?:junk|review): wishlist-trash (?:whole-item|roll)"
            r"(?: \((?:locked|exotic)\))?"
        ),
        rf"#vc-junk: {_ARMOR_SCORE}",
        rf"#vc-review: {_ARMOR_SCORE} \((?:locked|exotic)\)",
        rf"#vc-review: armor-last-archetype \([^()\r\n]+\), {_ARMOR_SCORE}",
        r"#vc-junk: ghost-unprotected-surplus",
    )
)


def strip_trailing_tool_clauses(notes: object) -> str:
    """Remove complete known vault-cleaner clauses from the Notes tail.

    Repeated clauses are removed one at a time from the end.  A tool-looking
    fragment with user text after it is intentionally left untouched because
    its ownership is ambiguous.
    """
    remaining = str(notes).strip()
    while remaining:
        markers = tuple(_MARKER_RE.finditer(remaining))
        if not markers:
            break
        start = markers[-1].start(1)
        suffix = remaining[start:]
        if not any(pattern.fullmatch(suffix) for pattern in _GENERATED_CLAUSE_RES):
            break
        remaining = remaining[:start].rstrip()
    return remaining


def append_tool_clause(notes: object, clause: str) -> str:
    """Append the current generated clause after replacing trailing history."""
    base = strip_trailing_tool_clauses(notes)
    return f"{base} {clause}".strip()
