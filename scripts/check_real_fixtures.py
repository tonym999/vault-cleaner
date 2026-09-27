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


class _T:
    """Builds one family's regex text, in either mode, from its slots.

    Each family is written as a single template *function* (below) that
    calls these slot methods in a fixed order and interleaves literal regex
    text. Calling that one function twice — once with ``mode="input"``, once
    with ``mode="retained"`` — produces the input-recognition pattern and
    the canonical-output pattern from the same source, so they cannot drift
    apart. Only ``n()``/``score()``/``ref()`` differ by mode (a digit
    pattern vs. the literal zeroed/rewritten form); every vocabulary slot
    (``vocab()``, ``id_()``) uses the identical pattern text in both modes.
    """

    def __init__(self, mode: str) -> None:
        assert mode in ("input", "retained")
        self.mode = mode

    def vocab(self, name: str, pattern: str) -> str:
        """A closed-vocabulary slot: identical pattern text in both modes."""
        return f"(?P<{name}>{pattern})"

    def id_(self, name: str = "id") -> str:
        """An already-mapped legacy full id: copied verbatim in both modes."""
        return self.vocab(name, FAKE_ID)

    def n(self, name: str) -> str:
        """A count/rank/delta/total/curated-match number: zeroed when retained."""
        pattern = _N if self.mode == "input" else "0"
        return f"(?P<{name}>{pattern})"

    def score(self, name: str) -> str:
        """An armor score or floor: zeroed when retained."""
        pattern = _SCORE if self.mode == "input" else "0"
        return f"(?P<{name}>{pattern})"

    def ref(self, name: str = "ref") -> str:
        """A ``[id ...]`` reference: any reference part beyond the rewritten
        short id is accepted on input and dropped entirely when retained."""
        if self.mode == "input":
            return r"\[id (?P<" + name + r">" + RAWSID + r")(?:; [^;\]\r\n]*)*\]"
        return r"\[id …(?P<" + name + r">[0-9]{4})\]"

    def opt(self, inner: str) -> str:
        return f"(?:{inner})?"


def _tuning_suffix_template(t: _T, label: str) -> str:
    return t.opt(
        r"; Candidate Tuning Mod Slot: " + t.vocab("tuning1", _TUNING)
        + r"; " + label + r" Tuning Mod Slot: " + t.vocab("tuning2", _TUNING)
    )


def _tuning_suffix(m: re.Match, label: str) -> str:
    if m.group("tuning1") is None:
        return ""
    return (
        f"; Candidate Tuning Mod Slot: {m.group('tuning1')}"
        f"; {label} Tuning Mod Slot: {m.group('tuning2')}"
    )


def _scorec_template(t: _T) -> str:
    return (
        r"armor-score " + t.score("score1") + r" < floor " + t.score("score2") + r" "
        r"\(best: " + t.vocab("profile", _PROFILE) + r", rank " + t.n("n1") + r"/" + t.n("n2")
        + r" " + t.vocab("cls", _CLASS) + r" " + t.vocab("vcslot", _SLOT) + r"\)"
    )


def _render_scorec(m: re.Match) -> str:
    return (
        f"armor-score 0 < floor 0 (best: {m.group('profile')}, "
        f"rank 0/0 {m.group('cls')} {m.group('vcslot')})"
    )


# ---------------------------------------------------------------------------
# The twelve clause families: one template function + one render function
# each. The template function is called with mode="input" to build the
# recognition pattern and with mode="retained" to build the canonical-output
# validation pattern — see _T above.
# ---------------------------------------------------------------------------


class ClauseFamily(NamedTuple):
    name: str
    input_re: re.Pattern[str]
    retained_re: re.Pattern[str]
    render: Callable[[re.Match, Callable[[str], str]], str]


def _template_1(t: _T) -> str:
    return r"#vc-" + t.vocab("kind", r"junk|review") + r": " + t.vocab("exact", _EXACT) + r", kept " + t.id_()


def _render_1(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-{m.group('kind')}: {m.group('exact')}, kept {m.group('id')}"


def _template_2(t: _T) -> str:
    base = (
        r"#vc-" + t.vocab("kind", r"junk|review") + r": " + t.vocab("exact", _EXACT)
        + r"; keep " + t.ref() + r"; winner " + t.vocab("winner", _WINNER)
    )
    return base + _tuning_suffix_template(t, "Survivor")


def _render_2(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    base = (
        f"#vc-{m.group('kind')}: {m.group('exact')}; "
        f"keep [id {resolve_ref(m.group('ref'))}]; winner {m.group('winner')}"
    )
    return base + _tuning_suffix(m, "Survivor")


def _template_3(t: _T) -> str:
    alt_identical = r"identical stats" + t.opt(
        r", tuning " + t.vocab("stat1", _STAT) + r" vs " + t.vocab("stat2", _STAT)
    )
    alt_delta = r"max stat delta " + t.n("n1") + r", total " + t.n("n2")
    return (
        r"#vc-review: armor-similar to " + t.id_() + r" \("
        + f"(?:{alt_identical}|{alt_delta})" + r"\)"
    )


def _render_3(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    if m.group("n1") is not None:
        detail = "max stat delta 0, total 0"
    elif m.group("stat1") is not None:
        detail = f"identical stats, tuning {m.group('stat1')} vs {m.group('stat2')}"
    else:
        detail = "identical stats"
    return f"#vc-review: armor-similar to {m.group('id')} ({detail})"


def _template_4(t: _T) -> str:
    return r"#vc-review: armor-dominated by " + t.id_() + r" \(\+" + t.n("n") + r" total\)"


def _render_4(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-review: armor-dominated by {m.group('id')} (+0 total)"


def _template_5(t: _T) -> str:
    base = (
        r"#vc-review: armor-dominated by; compare " + t.ref() + r"; \+" + t.n("n")
        + r" total; partner " + t.vocab("partner", r"largest stat surplus|deterministic id tie-break")
    )
    return base + _tuning_suffix_template(t, "Partner")


def _render_5(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    base = (
        f"#vc-review: armor-dominated by; compare [id {resolve_ref(m.group('ref'))}]; "
        f"+0 total; partner {m.group('partner')}"
    )
    return base + _tuning_suffix(m, "Partner")


def _template_6(t: _T) -> str:
    detail_pattern = "identical stats|max stat delta " + t.n("n1") + ", total " + t.n("n2")
    base = (
        r"#vc-review: armor-similar to; compare " + t.ref() + r"; "
        + t.vocab("detail", detail_pattern) + r"; partner "
        + t.vocab("partner", r"closest stat distance|deterministic id tie-break")
    )
    return base + _tuning_suffix_template(t, "Partner")


def _render_6(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    detail = "identical stats" if m.group("detail") == "identical stats" else "max stat delta 0, total 0"
    base = (
        f"#vc-review: armor-similar to; compare [id {resolve_ref(m.group('ref'))}]; "
        f"{detail}; partner {m.group('partner')}"
    )
    return base + _tuning_suffix(m, "Partner")


def _template_7(t: _T) -> str:
    return (
        r"#vc-review: coverage-" + t.vocab("dir", r"dominated by|uncovered vs") + r"; compare "
        + t.ref() + r"; curated matches " + t.n("n1") + r" vs " + t.n("n2") + r"; partner "
        + t.vocab(
            "partner",
            r"largest coverage gain|most curated matches|most combinations|deterministic id tie-break",
        )
    )


def _render_7(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return (
        f"#vc-review: coverage-{m.group('dir')}; "
        f"compare [id {resolve_ref(m.group('ref'))}]; curated matches 0 vs 0; "
        f"partner {m.group('partner')}"
    )


def _template_8(t: _T) -> str:
    base = r"#vc-" + t.vocab("kind", r"junk|review") + r": wishlist-trash " + t.vocab("w", r"whole-item|roll")
    return base + t.opt(r" \(" + t.vocab("paren", r"locked|exotic") + r"\)")


def _render_8(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    base = f"#vc-{m.group('kind')}: wishlist-trash {m.group('w')}"
    if m.group("paren") is not None:
        base += f" ({m.group('paren')})"
    return base


def _template_9(t: _T) -> str:
    return r"#vc-junk: " + _scorec_template(t)


def _render_9(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-junk: {_render_scorec(m)}"


def _template_10(t: _T) -> str:
    return r"#vc-review: " + _scorec_template(t) + r" \(" + t.vocab("paren", r"locked|exotic") + r"\)"


def _render_10(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-review: {_render_scorec(m)} ({m.group('paren')})"


def _template_11(t: _T) -> str:
    return r"#vc-review: armor-last-archetype \(" + t.vocab("arch", _ARCH) + r"\), " + _scorec_template(t)


def _render_11(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return f"#vc-review: armor-last-archetype ({m.group('arch')}), {_render_scorec(m)}"


def _template_12(t: _T) -> str:
    return "#vc-junk: ghost-unprotected-surplus"


def _render_12(m: re.Match, resolve_ref: Callable[[str], str]) -> str:
    return "#vc-junk: ghost-unprotected-surplus"


_TEMPLATES: tuple[tuple[str, Callable[[_T], str], Callable[[re.Match, Callable[[str], str]], str]], ...] = (
    ("exact-legacy-kept", _template_1, _render_1),
    ("exact-current", _template_2, _render_2),
    ("close-similar-legacy", _template_3, _render_3),
    ("close-dominated-legacy", _template_4, _render_4),
    ("close-dominated-current", _template_5, _render_5),
    ("close-similar-current", _template_6, _render_6),
    ("coverage", _template_7, _render_7),
    ("wishlist-trash", _template_8, _render_8),
    ("armor-score-junk", _template_9, _render_9),
    ("armor-score-review", _template_10, _render_10),
    ("armor-last-archetype", _template_11, _render_11),
    ("ghost-unprotected-surplus", _template_12, _render_12),
)

CLAUSE_FAMILIES: tuple[ClauseFamily, ...] = tuple(
    ClauseFamily(
        name,
        re.compile(template_fn(_T("input"))),
        re.compile(template_fn(_T("retained"))),
        render_fn,
    )
    for name, template_fn, render_fn in _TEMPLATES
)

INPUT_CLAUSE_RES: tuple[re.Pattern[str], ...] = tuple(family.input_re for family in CLAUSE_FAMILIES)
RETAINED_CLAUSE_RES: tuple[re.Pattern[str], ...] = tuple(family.retained_re for family in CLAUSE_FAMILIES)


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
    result must fullmatch the *same family's own* retained pattern (asserted
    here as a self-check, since a rendering bug must fail loudly rather than
    emit a clause shape a different family's pattern merely happens to also
    accept).
    """
    for family in CLAUSE_FAMILIES:
        m = family.input_re.fullmatch(body)
        if m is None:
            continue
        rendered = family.render(m, resolve_ref)
        if not family.retained_re.fullmatch(rendered):
            raise AssertionError(
                f"internal error: family {family.name!r} rendered a clause "
                "that does not match its own retained pattern"
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
