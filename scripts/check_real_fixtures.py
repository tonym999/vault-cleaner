"""Shared grammar and CI guard for sanitised real-export fixtures (#181).

This module is the **single source of definition** for the constants and
regex grammars that separate a sanitised fixture from a raw export or an
owner-authored note. ``scripts/sanitize_export.py`` loads this module by
path (``importlib.util.spec_from_file_location``) and never redefines any of
these names, so the writer and the CI acceptance guard cannot drift apart.

Stdlib-only: no import of ``vault_cleaner`` or any third-party package. This
lets CI run the guard with a bare ``python3``, with no project install and no
network access.

Run directly to check ``tests/fixtures/real`` relative to the repository
root:

    python3 scripts/check_real_fixtures.py
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Fake-id marker
# ---------------------------------------------------------------------------

# Every generated fake instance id starts with this fixed prefix. No real DIM
# instance id observed in the export (or in its Notes history) starts with
# it, so any occurrence of it in a fixture is unambiguous evidence of
# sanitisation rather than an accident of a real 19-digit id.
ID_MARKER = "1000"
# Real ids are 19-digit decimal strings; the fake scheme keeps that width so
# instance_id_order's magnitude comparisons never behave differently for a
# fake id than they would for a real one.
FAKE_ID = r"1000[0-9]{15}"
_FAKE_ID_RE = re.compile(FAKE_ID)

# ---------------------------------------------------------------------------
# Placeholder text (replaces owner-authored Notes bodies wholesale)
# ---------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(
    r'(?:note [0-9]+\.[0-9]+(?:, x)?(?: "q")?)?'
    r'(?:\n(?:note [0-9]+\.[0-9]+(?:, x)?(?: "q")?)?)*'
)

# ---------------------------------------------------------------------------
# Loadouts
# ---------------------------------------------------------------------------

LOADOUTS_RE = re.compile(r"Loadout [1-9][0-9]*(?:,Loadout [1-9][0-9]*)*")

# ---------------------------------------------------------------------------
# The short-id token grammar (duplicate_reference.short_id's long-id forms)
# ---------------------------------------------------------------------------

# The forms short_id() emits for a long (non-tiny) opaque id: a plain
# suffix, an optional truthful leading prefix, or a bounded rank+digest
# discriminator. No lookbehind here — callers add their own context (a
# `(?<=\bid )` lookbehind when scanning raw Notes for a reference token, none
# at all when scanning free-form explanation text such as "copy …1234").
RAWSID = r"[0-9]*…[0-9]+(?:~[0-9a-f]+-[0-9a-f]{8})?"
RAWSID_PARTS_RE = re.compile(
    r"(?P<prefix>[0-9]*)…(?P<suffix>[0-9]+)"
    r"(?:~(?P<rank>[0-9a-f]+)-(?P<digest>[0-9a-f]{8}))?"
)

_REF_INPUT = r"\[id (?P<ref>" + RAWSID + r")(?:; [^;\]\r\n]*)*\]"
# The only form the sanitiser ever writes: no reference part survives beyond
# the rewritten id, and the fake-id scheme (see sanitize_export.py) makes the
# plain 4-digit suffix the only short-id form that can ever occur.
_REF_RETAINED = r"\[id …[0-9]{4}\]"

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

_N = r"[0-9]+"
_SCORE = r"-?[0-9]+(?:\.[0-9]+)?"
_STAT = r"(?:weapons|health|class|grenade|super|melee)"
_TUNING = r"(?:Weapons|Health|Class|Grenade|Super|Melee|none/unknown)"
_CLASS = r"(?:hunter|titan|warlock)"
_SLOT = r"(?:helmet|gauntlets|chest armor|leg armor|hunter cloak|titan mark|warlock bond)"
# docs/armor-archetypes.md#L33-L44, lowercase.
_ARCHETYPES = (
    "siegebreaker", "bulwark", "brawler", "skirmisher", "grenadier",
    "demolitionist", "colossus", "paragon", "reaver", "specialist",
    "gunner", "powerhouse",
)
_ARCH = r"(?:" + "|".join(_ARCHETYPES) + r"|no archetype)"
_PROFILE = r"(?:melee_primary)"
_EXACT = (
    r"(?:dupe-(?:lower|tie)|armor-exact-dupe(?:-tie)?|armor-exotic-class-dupe)"
    r"(?: \((?:loadout|locked|exotic)\))?"
)
# note_history.py:21-26 verbatim.
_WINNER = (
    r"(?:higher (?:Tier|Masterwork Tier|Crafted Level|stat total|Power)"
    r"|Masterwork Tier|Power"
    r"|hard protection|loadout membership|lock"
    r"|deterministic(?: lowest)? id tie-break)"
)


def _tuning_opt_input(label: str) -> str:
    return (
        r"(?:; Candidate Tuning Mod Slot: (?P<tuning1>" + _TUNING + r")"
        r"; " + label + r" Tuning Mod Slot: (?P<tuning2>" + _TUNING + r"))?"
    )


def _tuning_opt_retained(label: str) -> str:
    return (
        r"(?:; Candidate Tuning Mod Slot: " + _TUNING
        + r"; " + label + r" Tuning Mod Slot: " + _TUNING + r")?"
    )


def _tuning_suffix(m: re.Match, label: str) -> str:
    if m.group("tuning1") is None:
        return ""
    return (
        f"; Candidate Tuning Mod Slot: {m.group('tuning1')}"
        f"; {label} Tuning Mod Slot: {m.group('tuning2')}"
    )


_SCOREC_INPUT = (
    r"armor-score (?P<score1>" + _SCORE + r") < floor (?P<score2>" + _SCORE + r") "
    r"\(best: (?P<profile>" + _PROFILE + r"), rank (?P<n1>" + _N + r")/(?P<n2>" + _N + r") "
    r"(?P<cls>" + _CLASS + r") (?P<vcslot>" + _SLOT + r")\)"
)
_SCOREC_RETAINED = (
    r"armor-score 0 < floor 0 \(best: " + _PROFILE + r", rank 0/0 "
    + _CLASS + r" " + _SLOT + r"\)"
)


def _render_scorec(m: re.Match) -> str:
    return (
        f"armor-score 0 < floor 0 (best: {m.group('profile')}, "
        f"rank 0/0 {m.group('cls')} {m.group('vcslot')})"
    )


# ---------------------------------------------------------------------------
# The twelve clause families
# ---------------------------------------------------------------------------


class ClauseFamily(NamedTuple):
    name: str
    input_re: re.Pattern[str]
    render: Callable[[re.Match, Callable[[str], str]], str]


def _render_1(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-{m.group('kind')}: {m.group('exact')}, kept {m.group('id')}"


def _render_2(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    base = (
        f"#vc-{m.group('kind')}: {m.group('exact')}; "
        f"keep [id {resolve_ref(m.group('ref'))}]; winner {m.group('winner')}"
    )
    return base + _tuning_suffix(m, "Survivor")


def _render_3(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    if m.group("n1") is not None:
        detail = "max stat delta 0, total 0"
    elif m.group("stat1") is not None:
        detail = f"identical stats, tuning {m.group('stat1')} vs {m.group('stat2')}"
    else:
        detail = "identical stats"
    return f"#vc-review: armor-similar to {m.group('id')} ({detail})"


def _render_4(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-review: armor-dominated by {m.group('id')} (+0 total)"


def _render_5(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    base = (
        f"#vc-review: armor-dominated by; compare [id {resolve_ref(m.group('ref'))}]; "
        f"+0 total; partner {m.group('partner')}"
    )
    return base + _tuning_suffix(m, "Partner")


def _render_6(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    detail = "identical stats" if m.group("detail") == "identical stats" else "max stat delta 0, total 0"
    base = (
        f"#vc-review: armor-similar to; compare [id {resolve_ref(m.group('ref'))}]; "
        f"{detail}; partner {m.group('partner')}"
    )
    return base + _tuning_suffix(m, "Partner")


def _render_7(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return (
        f"#vc-review: coverage-{m.group('dir')}; "
        f"compare [id {resolve_ref(m.group('ref'))}]; curated matches 0 vs 0; "
        f"partner {m.group('partner')}"
    )


def _render_8(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    base = f"#vc-{m.group('kind')}: wishlist-trash {m.group('w')}"
    if m.group("paren") is not None:
        base += f" ({m.group('paren')})"
    return base


def _render_9(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-junk: {_render_scorec(m)}"


def _render_10(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-review: {_render_scorec(m)} ({m.group('paren')})"


def _render_11(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-review: armor-last-archetype ({m.group('arch')}), {_render_scorec(m)}"


def _render_12(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return "#vc-junk: ghost-unprotected-surplus"


CLAUSE_FAMILIES: tuple[ClauseFamily, ...] = (
    ClauseFamily(
        "exact-legacy-kept",
        re.compile(
            r"#vc-(?P<kind>junk|review): (?P<exact>" + _EXACT + r"), kept (?P<id>" + FAKE_ID + r")"
        ),
        _render_1,
    ),
    ClauseFamily(
        "exact-current",
        re.compile(
            r"#vc-(?P<kind>junk|review): (?P<exact>" + _EXACT + r"); keep " + _REF_INPUT
            + r"; winner (?P<winner>" + _WINNER + r")" + _tuning_opt_input("Survivor")
        ),
        _render_2,
    ),
    ClauseFamily(
        "close-similar-legacy",
        re.compile(
            r"#vc-review: armor-similar to (?P<id>" + FAKE_ID + r") \("
            r"(?:identical stats(?:, tuning (?P<stat1>" + _STAT + r") vs (?P<stat2>" + _STAT + r"))?"
            r"|max stat delta (?P<n1>" + _N + r"), total (?P<n2>" + _N + r"))\)"
        ),
        _render_3,
    ),
    ClauseFamily(
        "close-dominated-legacy",
        re.compile(
            r"#vc-review: armor-dominated by (?P<id>" + FAKE_ID + r") \(\+(?P<n>" + _N + r") total\)"
        ),
        _render_4,
    ),
    ClauseFamily(
        "close-dominated-current",
        re.compile(
            r"#vc-review: armor-dominated by; compare " + _REF_INPUT + r"; \+(?P<n>" + _N + r") total; "
            r"partner (?P<partner>largest stat surplus|deterministic id tie-break)"
            + _tuning_opt_input("Partner")
        ),
        _render_5,
    ),
    ClauseFamily(
        "close-similar-current",
        re.compile(
            r"#vc-review: armor-similar to; compare " + _REF_INPUT + r"; "
            r"(?P<detail>identical stats|max stat delta " + _N + r", total " + _N + r"); "
            r"partner (?P<partner>closest stat distance|deterministic id tie-break)"
            + _tuning_opt_input("Partner")
        ),
        _render_6,
    ),
    ClauseFamily(
        "coverage",
        re.compile(
            r"#vc-review: coverage-(?P<dir>dominated by|uncovered vs); compare " + _REF_INPUT
            + r"; curated matches (?P<n1>" + _N + r") vs (?P<n2>" + _N + r"); "
            r"partner (?P<partner>largest coverage gain|most curated matches|most combinations|deterministic id tie-break)"
        ),
        _render_7,
    ),
    ClauseFamily(
        "wishlist-trash",
        re.compile(
            r"#vc-(?P<kind>junk|review): wishlist-trash (?P<w>whole-item|roll)"
            r"(?: \((?P<paren>locked|exotic)\))?"
        ),
        _render_8,
    ),
    ClauseFamily(
        "armor-score-junk",
        re.compile(r"#vc-junk: " + _SCOREC_INPUT),
        _render_9,
    ),
    ClauseFamily(
        "armor-score-review",
        re.compile(r"#vc-review: " + _SCOREC_INPUT + r" \((?P<paren>locked|exotic)\)"),
        _render_10,
    ),
    ClauseFamily(
        "armor-last-archetype",
        re.compile(
            r"#vc-review: armor-last-archetype \((?P<arch>" + _ARCH + r")\), " + _SCOREC_INPUT
        ),
        _render_11,
    ),
    ClauseFamily(
        "ghost-unprotected-surplus",
        re.compile(r"#vc-junk: ghost-unprotected-surplus"),
        _render_12,
    ),
)

INPUT_CLAUSE_RES: tuple[re.Pattern[str], ...] = tuple(
    family.input_re for family in CLAUSE_FAMILIES
)

RETAINED_CLAUSE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"#vc-(?:junk|review): " + _EXACT + r", kept " + FAKE_ID),
    re.compile(
        r"#vc-(?:junk|review): " + _EXACT + r"; keep " + _REF_RETAINED
        + r"; winner " + _WINNER + _tuning_opt_retained("Survivor")
    ),
    re.compile(
        r"#vc-review: armor-similar to " + FAKE_ID + r" \("
        r"(?:identical stats(?:, tuning " + _STAT + r" vs " + _STAT + r")?"
        r"|max stat delta 0, total 0)\)"
    ),
    re.compile(r"#vc-review: armor-dominated by " + FAKE_ID + r" \(\+0 total\)"),
    re.compile(
        r"#vc-review: armor-dominated by; compare " + _REF_RETAINED + r"; \+0 total; "
        r"partner (?:largest stat surplus|deterministic id tie-break)"
        + _tuning_opt_retained("Partner")
    ),
    re.compile(
        r"#vc-review: armor-similar to; compare " + _REF_RETAINED + r"; "
        r"(?:identical stats|max stat delta 0, total 0); "
        r"partner (?:closest stat distance|deterministic id tie-break)"
        + _tuning_opt_retained("Partner")
    ),
    re.compile(
        r"#vc-review: coverage-(?:dominated by|uncovered vs); compare " + _REF_RETAINED
        + r"; curated matches 0 vs 0; "
        r"partner (?:largest coverage gain|most curated matches|most combinations|deterministic id tie-break)"
    ),
    re.compile(
        r"#vc-(?:junk|review): wishlist-trash (?:whole-item|roll)(?: \((?:locked|exotic)\))?"
    ),
    re.compile(r"#vc-junk: " + _SCOREC_RETAINED),
    re.compile(r"#vc-review: " + _SCOREC_RETAINED + r" \((?:locked|exotic)\)"),
    re.compile(r"#vc-review: armor-last-archetype \(" + _ARCH + r"\), " + _SCOREC_RETAINED),
    re.compile(r"#vc-junk: ghost-unprotected-surplus"),
)


def is_retained_or_placeholder(stripped_body: str) -> bool:
    """True if a stripped Notes segment body is an accepted sanitised form."""
    if any(pattern.fullmatch(stripped_body) for pattern in RETAINED_CLAUSE_RES):
        return True
    return PLACEHOLDER_RE.fullmatch(stripped_body) is not None


def recognise_and_canonicalise(
    body: str, resolve_ref: Callable[[str], str]
) -> str | None:
    """Recognise one ``#vc-``-prefixed candidate body and re-render it.

    ``body`` must already have had every maximal ``>= 16``-digit run
    replaced by its fake id. Returns the canonical (``RETAINED_CLAUSE_RES``)
    text, or ``None`` if no family recognises it — the caller must then
    replace the whole original body with a placeholder. The canonicalised
    result always fullmatches one of ``RETAINED_CLAUSE_RES`` (asserted here
    as a self-check, since a rendering bug must fail loudly rather than emit
    an unrecognised clause shape).
    """
    for family in CLAUSE_FAMILIES:
        m = family.input_re.fullmatch(body)
        if m is None:
            continue
        rendered = family.render(m, resolve_ref)
        if not any(pattern.fullmatch(rendered) for pattern in RETAINED_CLAUSE_RES):
            raise AssertionError(
                f"internal error: family {family.name!r} rendered a clause "
                "that does not match RETAINED_CLAUSE_RES"
            )
        return rendered
    return None


# ---------------------------------------------------------------------------
# CI guard
# ---------------------------------------------------------------------------

_REQUIRED_HEADERS = {"Id", "Notes", "Loadouts"}
_KNOWN_NAMES = {"weapons.csv", "armor.csv", "ghosts.csv", "provenance.json"}
_PROVENANCE_KEYS = {"files", "parity_modes", "run_date", "script_version"}
_PROVENANCE_FILE_KEYS = {"raw_sha256", "rows"}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


def _validate_notes_cell(value: str) -> str | None:
    for segment in re.split(r"(?=#vc-)", value):
        stripped = segment.strip()
        if not stripped:
            continue
        if not is_retained_or_placeholder(stripped):
            return "contains text outside the sanitised clause/placeholder grammar"
    return None


def _validate_csv_file(path: Path, label: str, errors: list[str]) -> int:
    raw = path.read_bytes()
    for m in re.finditer(rb"[0-9]{16,}", raw):
        if not m.group(0).startswith(ID_MARKER.encode("ascii")):
            errors.append(f"{label}: unmarked long digit run at byte offset {m.start()}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        errors.append(f"{label}: not valid UTF-8")
        return 0

    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration:
        errors.append(f"{label}: empty file")
        return 0

    missing = _REQUIRED_HEADERS - set(header)
    if missing:
        errors.append(f"{label}: missing required headers {sorted(missing)}")
        return 0

    has_kill_tracker = "Kill Tracker" in header
    row_count = 0
    for row_number, row in enumerate(reader, start=2):
        row_count += 1
        if len(row) != len(header):
            errors.append(f"{label} row {row_number}: column count does not match header")
            continue
        record = dict(zip(header, row, strict=True))

        raw_id = record["Id"].strip('"')
        if not _FAKE_ID_RE.fullmatch(raw_id):
            errors.append(f"{label} row {row_number}: Id lacks the {ID_MARKER!r} marker")

        notes_error = _validate_notes_cell(record["Notes"])
        if notes_error is not None:
            errors.append(f"{label} row {row_number}: Notes {notes_error}")

        loadouts_value = record["Loadouts"]
        if loadouts_value.strip() and not LOADOUTS_RE.fullmatch(loadouts_value):
            errors.append(f"{label} row {row_number}: Loadouts is not a sanitised format")

        if has_kill_tracker and record["Kill Tracker"] != "0":
            errors.append(f"{label} row {row_number}: Kill Tracker is not zeroed")

    return row_count


def _validate_provenance(
    path: Path, expected_rows: dict[str, int], errors: list[str]
) -> None:
    label = path.as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{label}: not valid UTF-8")
        return
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        errors.append(f"{label}: not valid JSON")
        return
    if not isinstance(doc, dict) or set(doc) != _PROVENANCE_KEYS:
        errors.append(f"{label}: must have exactly the keys {sorted(_PROVENANCE_KEYS)}")
        return
    files = doc.get("files")
    if not isinstance(files, dict) or set(files) != {"weapons.csv", "armor.csv", "ghosts.csv"}:
        errors.append(f"{label}: 'files' must name exactly the three CSVs")
        return
    for name, meta in files.items():
        if not isinstance(meta, dict) or set(meta) != _PROVENANCE_FILE_KEYS:
            errors.append(f"{label}: files[{name!r}] must have exactly {sorted(_PROVENANCE_FILE_KEYS)}")
            continue
        sha = meta.get("raw_sha256")
        if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
            errors.append(f"{label}: files[{name!r}].raw_sha256 is not 64 lowercase hex characters")
        rows = meta.get("rows")
        expected = expected_rows.get(name)
        if not isinstance(rows, int) or isinstance(rows, bool):
            errors.append(f"{label}: files[{name!r}].rows is not an integer")
        elif expected is not None and rows != expected:
            errors.append(
                f"{label}: files[{name!r}].rows ({rows}) does not match the CSV's data-row count ({expected})"
            )


def check(root: Path) -> list[str]:
    """Validate every sanitised real-export fixture under ``root``.

    Returns the list of error strings (empty means the tree is clean). A
    missing root passes. Errors name the file, the row number and the rule —
    never the offending value, so a CI log never leaks fixture content.
    """
    errors: list[str] = []
    if not root.exists():
        return errors

    row_counts: dict[str, dict[str, int]] = {}
    provenance_paths: dict[str, Path] = {}

    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        parts = rel.parts
        if len(parts) != 2 or parts[1] not in _KNOWN_NAMES:
            errors.append(f"unexpected file: {rel.as_posix()}")
            continue
        snapshot, name = parts
        label = rel.as_posix()
        if name == "provenance.json":
            provenance_paths[snapshot] = path
            continue
        rows = _validate_csv_file(path, label, errors)
        row_counts.setdefault(snapshot, {})[name] = rows

    for snapshot, path in provenance_paths.items():
        _validate_provenance(path, row_counts.get(snapshot, {}), errors)

    return errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "real"
    errors = check(root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
