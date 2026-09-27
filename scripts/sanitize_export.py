"""Turn a real DIM export snapshot into committable, sanitised fixtures (#181).

Reads ``<snapshot_dir>/{weapons,armor,ghosts}.csv`` and writes
``tests/fixtures/real/<snapshot>/`` plus ``provenance.json``. This is a
privacy boundary in a public repository: every real instance id, every
owner-authored Notes segment and every owner-authored loadout name is
replaced before anything is written, and a battery of fail-closed checks
(leakage, behavioural parity against the raw export, and CSV format) must
all pass before any byte reaches disk. Any failure refuses and writes
nothing.

The grammar this script recognises and writes — the fake-id marker, the
Notes clause families, the Loadouts and placeholder formats — is defined
exactly once, in ``scripts/check_real_fixtures.py``, and loaded here by path
so the writer and the CI acceptance guard can never drift apart.

Usage (from the repository root)::

    python scripts/sanitize_export.py <snapshot_dir> [--out-root tests/fixtures/real]
        [--config config.toml] [--no-wishlists] [--run-date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from vault_cleaner.note_history import strip_trailing_tool_clauses
from vault_cleaner.parse import load_armor, load_ghosts, load_weapons
from vault_cleaner.report_run import run_report, snapshot_dict
from vault_cleaner.rules.id_order import instance_id_order

# ---------------------------------------------------------------------------
# Shared grammar, loaded by path so this script and the CI guard never
# redefine (and therefore never drift from) the same constants.
# ---------------------------------------------------------------------------

_GRAMMAR_PATH = Path(__file__).resolve().parent / "check_real_fixtures.py"
if "check_real_fixtures" in sys.modules:
    # Reuse an already-loaded guard module (a caller, such as the test suite,
    # may have loaded it first) rather than executing the file a second time
    # and ending up with a structurally-identical but distinct copy of the
    # grammar objects.
    grammar = sys.modules["check_real_fixtures"]
else:
    _grammar_spec = importlib.util.spec_from_file_location("check_real_fixtures", _GRAMMAR_PATH)
    assert _grammar_spec is not None and _grammar_spec.loader is not None
    grammar = importlib.util.module_from_spec(_grammar_spec)
    sys.modules["check_real_fixtures"] = grammar
    _grammar_spec.loader.exec_module(grammar)

ID_MARKER = grammar.ID_MARKER
FAKE_ID = grammar.FAKE_ID
RAWSID = grammar.RAWSID
RAWSID_PARTS_RE = grammar.RAWSID_PARTS_RE
LOADOUTS_RE = grammar.LOADOUTS_RE
is_retained_or_placeholder = grammar.is_retained_or_placeholder
recognise_and_canonicalise = grammar.recognise_and_canonicalise


class SanitiseError(Exception):
    """A leakage, parity or format check failed: nothing is written."""


KINDS_FILES = {"weapons": "weapons.csv", "armor": "armor.csv", "ghosts": "ghosts.csv"}
TREATED = frozenset({"Id", "Notes", "Loadouts", "Kill Tracker"})
_PERK_HEADER_RE = re.compile(r"^Perks [0-9]+$")

# Measured column allowlists (#181 planning; AGENTS.md: "any column not
# listed ... is a stop-and-ask, not a silent keep"). Any column outside
# TREATED / Perks N / this set refuses rather than silently passing through.
_WEAPON_KEPT = frozenset({
    "Name", "Hash", "Tag", "Rarity", "Tier", "Type", "Source", "Category",
    "Element", "Ammo", "Power", "Archetype", "Masterwork Type",
    "Masterwork Tier", "Owner", "Locked", "Equipped", "Holofoil", "Year",
    "Season", "Event", "Recoil", "AA", "Impact", "Range", "Zoom",
    "Blast Radius", "Velocity", "Persistence", "Stability", "ROF", "Reload",
    "Mag", "Handling", "Charge Time", "Draw Time", "Accuracy",
    "Charge Rate", "Guard Resistance", "Guard Endurance", "Swing Speed",
    "Shield Duration", "Airborne Effectiveness", "Ammo Generation",
    "Heat Generated", "Cooling Efficiency", "Crafted", "Crafted Level",
    "Foundry",
})
_ARMOR_KEPT = frozenset({
    "Name", "Hash", "Tag", "Rarity", "Tier", "Type", "Source", "Equippable",
    "Power", "Energy Capacity", "Archetype", "Tertiary Stat", "Tuning Stat",
    "Masterwork Tier", "Owner", "Locked", "Equipped", "Holofoil", "Year",
    "Season", "Event", "Weapons", "Health", "Class", "Grenade", "Super",
    "Melee", "Total", "Weapons (Base)", "Health (Base)", "Class (Base)",
    "Grenade (Base)", "Super (Base)", "Melee (Base)", "Total (Base)",
    "Seasonal Mod",
})
_GHOST_KEPT = frozenset({
    "Name", "Hash", "Tag", "Rarity", "Tier", "Source", "Energy Capacity",
    "Masterwork Tier", "Owner", "Locked", "Equipped", "Holofoil", "Year",
    "Season", "Event",
})
_KEPT_BY_KIND = {"weapons": _WEAPON_KEPT, "armor": _ARMOR_KEPT, "ghosts": _GHOST_KEPT}

_ID_RUN_RE = re.compile(r"[0-9]{16,}")


def _audit_columns(kind: str, header: list[str]) -> None:
    kept = _KEPT_BY_KIND[kind]
    for name in header:
        if name in TREATED or _PERK_HEADER_RE.fullmatch(name) or name in kept:
            continue
        raise SanitiseError(
            f"unclassified column {name!r} in {kind}.csv — classify it before sanitising (#181)"
        )


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SanitiseError(f"{path.name}: not valid UTF-8") from exc
    text = text.removeprefix("﻿")
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise SanitiseError(f"{path.name}: empty file") from exc
    if len(header) != len(set(header)):
        raise SanitiseError(f"{path.name}: duplicate header names")
    rows: list[dict[str, str]] = []
    for row_number, row in enumerate(reader, start=2):
        if len(row) != len(header):
            raise SanitiseError(f"{path.name} row {row_number}: column count does not match header")
        rows.append(dict(zip(header, row, strict=True)))
    return header, rows


def _collect_ids(rows: dict[str, list[dict[str, str]]]) -> tuple[frozenset[str], frozenset[str]]:
    export_ids: set[str] = set()
    for kind in ("weapons", "armor", "ghosts"):
        for row_number, row in enumerate(rows[kind], start=2):
            raw_id = row["Id"].strip('"')
            if not re.fullmatch(r"[0-9]{16,}", raw_id):
                raise SanitiseError(
                    f"{kind}.csv row {row_number}: Id is not an all-decimal string of length >= 16"
                )
            if raw_id.startswith(ID_MARKER):
                raise SanitiseError(
                    f"{kind}.csv row {row_number}: Id already begins with the fake-id marker"
                )
            if raw_id in export_ids:
                raise SanitiseError(f"{kind}.csv row {row_number}: duplicate Id across the snapshot")
            export_ids.add(raw_id)

    notes_only_ids: set[str] = set()
    for kind in ("weapons", "armor", "ghosts"):
        for row in rows[kind]:
            for m in _ID_RUN_RE.finditer(row["Notes"]):
                run = m.group(0)
                if run not in export_ids:
                    notes_only_ids.add(run)
    for run in notes_only_ids:
        if run.startswith(ID_MARKER):
            raise SanitiseError("a Notes-only id already begins with the fake-id marker")

    return frozenset(export_ids), frozenset(notes_only_ids)


# ---------------------------------------------------------------------------
# Sanitiser state: the id map, and the two "new value on first sight" maps
# for placeholders and loadout names, shared across every row so numbering
# is deterministic and consistent across the whole snapshot.
# ---------------------------------------------------------------------------


@dataclass
class SanitiserState:
    id_map: dict[str, str]
    export_ids: frozenset[str]
    next_fresh_rank: int
    all_fakes: set[str] = field(default_factory=set)
    fresh_token_map: dict[str, str] = field(default_factory=dict)
    placeholder_map: dict[str, int] = field(default_factory=dict)
    next_k: int = 1
    loadout_map: dict[str, int] = field(default_factory=dict)
    next_loadout_n: int = 1
    frozen: bool = False

    def __post_init__(self) -> None:
        self.all_fakes.update(self.id_map.values())

    def _short_id_for_fake(self, fake: str) -> str:
        suffix4 = fake[-4:]
        if any(other != fake and other.endswith(suffix4) for other in self.all_fakes):
            raise SanitiseError(
                "fake-id short-id suffix collision — the marker-rank scheme's "
                "uniqueness invariant no longer holds"
            )
        return f"…{suffix4}"

    def resolve_ref_token(self, token: str) -> str:
        m = RAWSID_PARTS_RE.fullmatch(token)
        if m is None:
            raise SanitiseError("malformed short-id token encountered while rewriting Notes")
        prefix, suffix = m.group("prefix"), m.group("suffix")
        candidates = [
            rid for rid in self.export_ids if rid.startswith(prefix) and rid.endswith(suffix)
        ]
        if len(candidates) == 1:
            fake = self.id_map[candidates[0]]
        else:
            fake = self.fresh_token_map.get(token)
            if fake is None:
                if self.frozen:
                    raise SanitiseError("frozen sanitiser state required a new short-id allocation")
                fake = f"{ID_MARKER}{self.next_fresh_rank:015d}"
                self.next_fresh_rank += 1
                self.fresh_token_map[token] = fake
                self.all_fakes.add(fake)
        return self._short_id_for_fake(fake)

    def render_placeholder(self, body: str) -> str:
        k = self.placeholder_map.get(body)
        if k is None:
            if self.frozen:
                raise SanitiseError("frozen sanitiser state required a new placeholder body")
            k = self.next_k
            self.placeholder_map[body] = k
            self.next_k += 1
        out_lines = []
        for j, line in enumerate(body.split("\n")):
            if line.strip() == "":
                out_lines.append("")
                continue
            piece = f"note {k}.{j}"
            if "," in line:
                piece += ", x"
            if '"' in line:
                piece += ' "q"'
            out_lines.append(piece)
        return "\n".join(out_lines)

    def _map_long_ids(self, text: str) -> str:
        def repl(m: re.Match) -> str:
            real = m.group(0)
            fake = self.id_map.get(real)
            if fake is None:
                raise SanitiseError("Notes contains an unmapped long digit run")
            return fake

        return _ID_RUN_RE.sub(repl, text)

    def sanitize_notes(self, value: object) -> str:
        text = str(value)
        if "\r" in text:
            raise SanitiseError("Notes cell contains an embedded carriage return")
        parts = re.split(r"(?=#vc-)", text)
        out: list[str] = []
        for segment in parts:
            stripped = segment.strip()
            if not stripped:
                out.append(segment)
                continue
            lead = segment[: len(segment) - len(segment.lstrip())]
            trail = segment[len(segment.rstrip()):]
            if stripped.startswith("#vc-"):
                mapped_body = self._map_long_ids(stripped)
                canonical = recognise_and_canonicalise(mapped_body, self.resolve_ref_token)
                if canonical is not None:
                    out.append(lead + canonical + trail)
                    continue
            out.append(lead + self.render_placeholder(stripped) + trail)
        return "".join(out)

    def sanitize_loadouts(self, value: object) -> str:
        text = str(value)
        if text.strip() == "":
            return text
        out = []
        for token in text.split(","):
            n = self.loadout_map.get(token)
            if n is None:
                if self.frozen:
                    raise SanitiseError("frozen sanitiser state required a new loadout mapping")
                n = self.next_loadout_n
                self.loadout_map[token] = n
                self.next_loadout_n += 1
            out.append(f"Loadout {n}")
        return ",".join(out)


def _l9_independent_resolve(
    token: str, export_ids: frozenset[str], id_map: dict[str, str], fresh_token_map: dict[str, str]
) -> str:
    """Re-derive one rewritten reference without calling the writer's helper."""
    m = RAWSID_PARTS_RE.fullmatch(token)
    if m is None:
        raise SanitiseError("L9: malformed short-id token in raw Notes")
    prefix = m.group("prefix") or ""
    suffix = m.group("suffix")
    matches = [
        rid for rid in export_ids
        if rid[: len(prefix)] == prefix and rid[len(rid) - len(suffix):] == suffix
    ]
    if len(matches) == 1:
        fake = id_map[matches[0]]
    else:
        fake = fresh_token_map.get(token)
        if fake is None:
            raise SanitiseError("L9: raw short-id token has no recorded fresh-fake allocation")
    return f"…{fake[-4:]}"


def _build_id_map(sorted_ids: list[str]) -> dict[str, str]:
    """Assign each real id its order-preserving fake, by rank (1-based)."""
    return {real: f"{ID_MARKER}{i:015d}" for i, real in enumerate(sorted_ids, start=1)}


def _sanitize_kill_tracker(value: object) -> str:
    """Kill Tracker is play history (a kill count): always zeroed."""
    return "0"


def _transform_row(header: list[str], row: dict[str, str], state: SanitiserState) -> list[str]:
    out = []
    for col in header:
        value = row[col]
        if col == "Id":
            fake = state.id_map[value.strip('"')]
            out.append(f'"{fake}"')
        elif col == "Notes":
            out.append(state.sanitize_notes(value))
        elif col == "Loadouts":
            out.append(state.sanitize_loadouts(value))
        elif col == "Kill Tracker":
            out.append(_sanitize_kill_tracker(value))
        else:
            out.append(value)
    return out


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Leakage and format checks (L1-L9, F)
# ---------------------------------------------------------------------------


def _staged_text(tmp_path: Path, name: str) -> str:
    return (tmp_path / name).read_text(encoding="utf-8")


def _check_l1(tmp_path: Path, all_real_ids: frozenset[str]) -> None:
    for name in KINDS_FILES.values():
        text = _staged_text(tmp_path, name)
        for real in all_real_ids:
            if real in text:
                raise SanitiseError(f"L1: a real id appears verbatim in {name}")


def _l2_windows(all_real_ids: frozenset[str]) -> frozenset[str]:
    windows: set[str] = set()
    for rid in all_real_ids:
        for i in range(len(rid) - 7):
            windows.add(rid[i:i + 8])
    return frozenset(windows)


def _check_l2(
    tmp_path: Path, windows: frozenset[str], all_fakes: set[str], raw_hash_values: frozenset[str]
) -> None:
    for name in KINDS_FILES.values():
        text = _staged_text(tmp_path, name)
        for m in re.finditer(r"[0-9]{8,}", text):
            run = m.group(0)
            if run in all_fakes or run in raw_hash_values:
                continue
            for i in range(len(run) - 7):
                if run[i:i + 8] in windows:
                    raise SanitiseError(f"L2: an 8-digit window of a real id appears in {name}")


def _check_l3(tmp_path: Path, all_real_ids: frozenset[str]) -> None:
    for name in KINDS_FILES.values():
        text = _staged_text(tmp_path, name)
        reader = csv.reader(io.StringIO(text, newline=""))
        header = next(reader)
        id_idx = header.index("Id")
        seen: set[str] = set()
        for row_number, row in enumerate(reader, start=2):
            raw = row[id_idx].strip('"')
            if not re.fullmatch(FAKE_ID, raw):
                raise SanitiseError(f"L3: {name} row {row_number} Id lacks the fake-id marker")
            if raw in seen:
                raise SanitiseError(f"L3: {name} row {row_number} has a duplicate Id")
            seen.add(raw)
            if raw in all_real_ids:
                raise SanitiseError(f"L3: {name} row {row_number} Id collides with a real id")


def _check_l4(tmp_path: Path, all_fakes: set[str]) -> None:
    for name in KINDS_FILES.values():
        text = _staged_text(tmp_path, name)
        for m in re.finditer(r"[0-9]{16,}", text):
            if m.group(0) not in all_fakes:
                raise SanitiseError(
                    f"L4: {name} contains a long digit run that is not a generated fake id"
                )


def _check_l5(
    headers: dict[str, list[str]],
    staged: dict[str, list[list[str]]],
    state: SanitiserState,
) -> None:
    for kind, name in KINDS_FILES.items():
        notes_idx = headers[kind].index("Notes")
        for row_number, out_row in enumerate(staged[kind], start=2):
            for segment in re.split(r"(?=#vc-)", out_row[notes_idx]):
                stripped = segment.strip()
                if not stripped:
                    continue
                if not is_retained_or_placeholder(stripped):
                    raise SanitiseError(
                        f"L5: {name} row {row_number} Notes segment is outside the sanitised grammar"
                    )
    owner_bodies = {body for body in state.placeholder_map if body}
    all_notes_text = "\n".join(
        out_row[headers[kind].index("Notes")]
        for kind in KINDS_FILES
        for out_row in staged[kind]
    )
    for body in owner_bodies:
        if body in all_notes_text:
            raise SanitiseError("L5: an original owner Notes segment appears verbatim in output")


def _check_l6(
    headers: dict[str, list[str]],
    rows: dict[str, list[dict[str, str]]],
    staged: dict[str, list[list[str]]],
    state: SanitiserState,
) -> None:
    raw_tokens = set(state.loadout_map.keys())
    for kind, name in KINDS_FILES.items():
        lo_idx = headers[kind].index("Loadouts")
        for row_number, (raw_row, out_row) in enumerate(
            zip(rows[kind], staged[kind], strict=True), start=2
        ):
            raw_value = raw_row["Loadouts"]
            out_value = out_row[lo_idx]
            raw_empty = raw_value.strip() == ""
            out_empty = out_value.strip() == ""
            if raw_empty != out_empty:
                raise SanitiseError(f"L6: {name} row {row_number} Loadouts emptiness changed")
            if out_empty:
                continue
            if not LOADOUTS_RE.fullmatch(out_value):
                raise SanitiseError(f"L6: {name} row {row_number} Loadouts is not a sanitised format")
            if len(raw_value.split(",")) != len(out_value.split(",")):
                raise SanitiseError(f"L6: {name} row {row_number} Loadouts token count changed")
            for token in out_value.split(","):
                if token in raw_tokens:
                    raise SanitiseError(f"L6: {name} row {row_number} contains an original loadout token")


def _check_l7(headers: dict[str, list[str]], staged: dict[str, list[list[str]]]) -> None:
    for kind, name in KINDS_FILES.items():
        header = headers[kind]
        if "Kill Tracker" not in header:
            continue
        kt_idx = header.index("Kill Tracker")
        for row_number, out_row in enumerate(staged[kind], start=2):
            if out_row[kt_idx] != "0":
                raise SanitiseError(f"L7: {name} row {row_number} Kill Tracker is not zeroed")


def _check_l8(snapshot_dir: Path, tmp_path: Path, id_map: dict[str, str]) -> None:
    pairs = (
        ("weapons", load_weapons(snapshot_dir / "weapons.csv"), load_weapons(tmp_path / "weapons.csv")),
        ("armor", load_armor(snapshot_dir / "armor.csv"), load_armor(tmp_path / "armor.csv")),
        ("ghosts", load_ghosts(snapshot_dir / "ghosts.csv"), load_ghosts(tmp_path / "ghosts.csv")),
    )
    for name, raw_df, staged_df in pairs:
        if len(raw_df) != len(staged_df):
            raise SanitiseError(f"L8: {name} row count differs after sanitisation")
        expected_ids = raw_df["Id"].map(id_map).reset_index(drop=True)
        if not (expected_ids == staged_df["Id"].reset_index(drop=True)).all():
            raise SanitiseError(f"L8: {name} Id column does not match the id map")
        for col in raw_df.columns:
            if col in TREATED:
                continue
            if not (raw_df[col].reset_index(drop=True) == staged_df[col].reset_index(drop=True)).all():
                raise SanitiseError(f"L8: {name} column {col!r} changed outside the treated set")


_ID_TOKEN_AFTER_ID_RE = re.compile(r"(?<=\bid )" + RAWSID)
_STAGED_ID_TOKEN_RE = re.compile(r"(?<=\bid )…[0-9]{4}")


def _check_l9(
    headers: dict[str, list[str]],
    rows: dict[str, list[dict[str, str]]],
    staged: dict[str, list[list[str]]],
    state: SanitiserState,
) -> None:
    for kind, name in KINDS_FILES.items():
        notes_idx = headers[kind].index("Notes")
        for row_number, (raw_row, out_row) in enumerate(
            zip(rows[kind], staged[kind], strict=True), start=2
        ):
            raw_tokens = [m.group(0) for m in _ID_TOKEN_AFTER_ID_RE.finditer(raw_row["Notes"])]
            out_tokens = [m.group(0) for m in _STAGED_ID_TOKEN_RE.finditer(out_row[notes_idx])]
            if len(raw_tokens) != len(out_tokens):
                raise SanitiseError(f"L9: {name} row {row_number} reference token count changed")
            for raw_token, out_token in zip(raw_tokens, out_tokens, strict=True):
                expected = _l9_independent_resolve(
                    raw_token, state.export_ids, state.id_map, state.fresh_token_map
                )
                if expected != out_token:
                    raise SanitiseError(
                        f"L9: {name} row {row_number} rewritten reference does not match "
                        "independent resolution"
                    )


def _check_format(path: Path) -> None:
    data = path.read_bytes()
    if b"\r" in data:
        raise SanitiseError(f"F: {path.name} contains CR bytes")
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise SanitiseError(f"F: {path.name} does not end with exactly one trailing newline")
    text = data.decode("utf-8")
    lines = text.split("\n")[:-1]
    for i, line in enumerate(lines, start=1):
        if line.endswith((" ", "\t")):
            raise SanitiseError(f"F: {path.name} line {i} ends in whitespace")
        leading = line[: len(line) - len(line.lstrip(" \t"))]
        if " \t" in leading:
            raise SanitiseError(f"F: {path.name} line {i} has a space before a tab in leading whitespace")
        if re.match(r"^(?:<{7}|={7}|>{7})(?: |$)", line):
            raise SanitiseError(f"F: {path.name} line {i} starts with a conflict marker")


# ---------------------------------------------------------------------------
# Parity comparator (P)
# ---------------------------------------------------------------------------

_SID_NO_LOOKBEHIND_RE = re.compile(RAWSID)
_SKIP_DECISION_KEYS = {"note", "original_notes", "explanation"}

# Exact key sets this comparator knows how to handle at each snapshot_dict
# level (report_run.py:438-498). A key outside these sets — added or
# removed on either side — refuses rather than being silently skipped, so a
# future snapshot_dict field cannot slip past parity unchecked (#181 review
# finding F). These mirror report_run.py's current shape; src/ is untouched
# by this ticket, so they are asserted here rather than imported.
_TOP_KEYS = {
    "schema_version", "ruleset_version", "fingerprint", "inputs",
    "keep_trash_conflicts", "warnings", "sections",
}
_INPUTS_KEYS = {"sources", "effective_config", "wishlists_used", "wishlist_sources", "manifest"}
_SECTION_KEYS_BASE = {"kind", "source", "decisions"}
_SECTION_KEYS_ARMOR = _SECTION_KEYS_BASE | {"armor"}
_DECISION_KEYS = {
    "id", "kind", "hash", "name", "location", "guardian_class", "action", "tag",
    "note", "kept_id", "reason", "original_tag", "original_notes",
    "protection_level", "protection_reason", "locked", "equipped", "in_loadout",
    "candidate_tuning_mod_slot", "selected_tuning_mod_slot", "explanation",
}
_EXPLANATION_KEYS = {"label", "why", "keep_instead", "gives_up", "caveats"}
_ARMOR_BLOCK_KEYS = {
    "scored", "evaluations", "cited_ids", "kept_elsewhere",
    "exact_duplicate_groups", "same_stat_groups",
}


def _require_exact_keys(raw: dict, staged: dict, expected: set[str], context: str) -> None:
    raw_keys, staged_keys = set(raw), set(staged)
    if raw_keys != expected or staged_keys != expected:
        raise SanitiseError(
            f"parity: {context} has a key this comparator does not handle "
            f"(raw-extra={sorted(raw_keys - expected)}, staged-extra={sorted(staged_keys - expected)}, "
            f"missing={sorted(expected - (raw_keys & staged_keys))})"
        )


def _map_value(value: object, state: SanitiserState) -> object:
    if isinstance(value, str):
        if value in state.id_map:
            return state.id_map[value]

        def repl(m: re.Match) -> str:
            real = m.group(0)
            fake = state.id_map.get(real)
            if fake is None:
                raise SanitiseError("parity: raw snapshot contains an unmapped id-length digit run")
            return fake

        return _ID_RUN_RE.sub(repl, value)
    if isinstance(value, dict):
        # ArmorEvaluation carries its own `original_notes` (armor.py:51),
        # outside the decisions this module otherwise handles through the
        # dedicated 3(a)-3(d) Notes comparison. It needs the same full
        # sanitize_notes() transform, not the generic id-digit-run mapper,
        # or an owner-text body would never be recognised as equal.
        return {
            k: (state.sanitize_notes(v) if k == "original_notes" and isinstance(v, str) else _map_value(v, state))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_map_value(v, state) for v in value]
    return value


def _normalize_shortid(text: str) -> str:
    return _SID_NO_LOOKBEHIND_RE.sub("<SID>", text)


def _explanation_texts(expl: dict) -> list[str]:
    return [expl["label"], expl["why"], expl["keep_instead"], expl["gives_up"], *expl["caveats"]]


def _normalize_explanation(expl: dict) -> tuple:
    return (
        _normalize_shortid(expl["label"]),
        _normalize_shortid(expl["why"]),
        _normalize_shortid(expl["keep_instead"]),
        _normalize_shortid(expl["gives_up"]),
        tuple(_normalize_shortid(c) for c in expl["caveats"]),
    )


def _check_reference_truthfulness(texts: list[str], kept_id: str, *, side: str) -> None:
    tokens: list[str] = []
    for text in texts:
        tokens.extend(m.group(0) for m in _SID_NO_LOOKBEHIND_RE.finditer(text))
    if not kept_id:
        if tokens:
            raise SanitiseError(f"parity 3(d) [{side}]: a reference token exists with an empty kept_id")
        return
    for token in tokens:
        m = RAWSID_PARTS_RE.fullmatch(token)
        if m is None:
            raise SanitiseError(f"parity 3(d) [{side}]: malformed reference token")
        prefix, suffix = m.group("prefix"), m.group("suffix")
        if not kept_id.startswith(prefix):
            raise SanitiseError(f"parity 3(d) [{side}]: reference prefix is not truthful")
        if not kept_id.endswith(suffix):
            raise SanitiseError(f"parity 3(d) [{side}]: reference suffix is not truthful")
        digest = m.group("digest")
        if digest is not None:
            expected = hashlib.sha256(kept_id.encode("utf-8")).hexdigest()[:8]
            if digest != expected:
                raise SanitiseError(f"parity 3(d) [{side}]: reference digest is not truthful")


def _compare_notes(raw_d: dict, staged_d: dict, state: SanitiserState) -> bool:
    mismatch = False
    r_notes, s_notes = raw_d["original_notes"], staged_d["original_notes"]
    if s_notes != state.sanitize_notes(r_notes):
        mismatch = True

    base_r = strip_trailing_tool_clauses(r_notes)
    base_s = strip_trailing_tool_clauses(s_notes)
    if base_s != state.sanitize_notes(base_r):
        mismatch = True

    clause_r = raw_d["note"][len(base_r):].strip() if raw_d["note"].startswith(base_r) else raw_d["note"]
    clause_s = (
        staged_d["note"][len(base_s):].strip() if staged_d["note"].startswith(base_s) else staged_d["note"]
    )
    if _normalize_shortid(clause_r) != _normalize_shortid(clause_s):
        mismatch = True

    r_expl, s_expl = raw_d["explanation"], staged_d["explanation"]
    if (r_expl is None) != (s_expl is None):
        mismatch = True
    elif r_expl is not None:
        _require_exact_keys(r_expl, s_expl, _EXPLANATION_KEYS, "explanation")
        if _normalize_explanation(r_expl) != _normalize_explanation(s_expl):
            mismatch = True

    r_texts = [clause_r] + (_explanation_texts(r_expl) if r_expl else [])
    s_texts = [clause_s] + (_explanation_texts(s_expl) if s_expl else [])
    # A raw-side violation means a production reference no longer renders its
    # own decision's kept_id — the plan treats that as a stop condition, so
    # it propagates immediately rather than being counted.
    _check_reference_truthfulness(r_texts, raw_d["kept_id"], side="raw")
    try:
        _check_reference_truthfulness(s_texts, staged_d["kept_id"], side="staged")
    except SanitiseError:
        mismatch = True
    return mismatch


def _compare_decision(raw_d: dict, staged_d: dict, state: SanitiserState) -> bool:
    _require_exact_keys(raw_d, staged_d, _DECISION_KEYS, "decision")
    mismatch = False
    for key, raw_val in raw_d.items():
        if key in _SKIP_DECISION_KEYS:
            continue
        if _map_value(raw_val, state) != staged_d.get(key):
            mismatch = True
    if _compare_notes(raw_d, staged_d, state):
        mismatch = True
    return mismatch


def _compare_sections(
    raw_sections: list[dict], staged_sections: list[dict], state: SanitiserState
) -> dict[str, int]:
    if len(raw_sections) != len(staged_sections):
        raise SanitiseError("parity: section count differs")
    counts: dict[str, int] = {}
    for r_sec, s_sec in zip(raw_sections, staged_sections, strict=True):
        kind = r_sec["kind"]
        if kind != s_sec["kind"]:
            raise SanitiseError("parity: section kind order differs")
        expected_section_keys = _SECTION_KEYS_ARMOR if "armor" in r_sec or "armor" in s_sec else _SECTION_KEYS_BASE
        _require_exact_keys(r_sec, s_sec, expected_section_keys, f"section {kind}")
        r_decisions, s_decisions = r_sec["decisions"], s_sec["decisions"]
        if len(r_decisions) != len(s_decisions):
            raise SanitiseError(f"parity: {kind} decision count differs")
        mismatched = sum(
            1
            for r_d, s_d in zip(r_decisions, s_decisions, strict=True)
            if _compare_decision(r_d, s_d, state)
        )
        counts[kind] = mismatched
        r_armor, s_armor = r_sec.get("armor"), s_sec.get("armor")
        if r_armor is not None:
            _require_exact_keys(r_armor, s_armor, _ARMOR_BLOCK_KEYS, f"section {kind} armor block")
            if _map_value(r_armor, state) != s_armor:
                counts[f"{kind}:armor"] = 1
    return counts


def _compare_snapshots(raw: dict, staged: dict, state: SanitiserState) -> dict[str, int]:
    _require_exact_keys(raw, staged, _TOP_KEYS, "top level")
    _require_exact_keys(raw["inputs"], staged["inputs"], _INPUTS_KEYS, "inputs")
    if raw["schema_version"] != staged["schema_version"]:
        raise SanitiseError("parity: schema_version differs")
    if raw["ruleset_version"] != staged["ruleset_version"]:
        raise SanitiseError("parity: ruleset_version differs")
    # fingerprint and inputs.sources/each section.source are file digests and
    # paths, which must differ between raw and staged, so their VALUES are
    # dropped by never being compared here (their presence is still required
    # by the key-set checks above/in _compare_sections).
    if raw["inputs"]["effective_config"] != staged["inputs"]["effective_config"]:
        raise SanitiseError("parity: effective_config differs")
    if raw["inputs"]["wishlists_used"] != staged["inputs"]["wishlists_used"]:
        raise SanitiseError("parity: wishlists_used differs")
    if raw["inputs"]["wishlist_sources"] != staged["inputs"]["wishlist_sources"]:
        raise SanitiseError("parity: wishlist_sources differ")
    if raw["inputs"]["manifest"] != staged["inputs"]["manifest"]:
        raise SanitiseError("parity: manifest differs")
    if raw["keep_trash_conflicts"] != staged["keep_trash_conflicts"]:
        raise SanitiseError("parity: keep_trash_conflicts differs")
    if raw["warnings"] != staged["warnings"]:
        raise SanitiseError("parity: warnings differ")
    return _compare_sections(raw["sections"], staged["sections"], state)


def _run_parity(
    raw_dir: Path, staged_dir: Path, config_path: Path, no_wishlists: bool, state: SanitiserState
) -> None:
    raw_run = run_report(
        config_path=config_path,
        weapons_path=raw_dir / "weapons.csv",
        armor_path=raw_dir / "armor.csv",
        ghosts_path=raw_dir / "ghosts.csv",
        no_wishlists=no_wishlists,
    )
    staged_run = run_report(
        config_path=config_path,
        weapons_path=staged_dir / "weapons.csv",
        armor_path=staged_dir / "armor.csv",
        ghosts_path=staged_dir / "ghosts.csv",
        no_wishlists=no_wishlists,
    )
    counts = _compare_snapshots(snapshot_dict(raw_run), snapshot_dict(staged_run), state)
    total = sum(counts.values())
    if total:
        mode = "no-wishlists" if no_wishlists else "wishlists"
        raise SanitiseError(f"parity ({mode}): {total} differing decisions across sections {counts}")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _check_destination(dest: Path) -> None:
    if not dest.exists():
        return
    allowed = {"weapons.csv", "armor.csv", "ghosts.csv", "provenance.json"}
    for child in dest.iterdir():
        if not child.is_file() or child.name not in allowed:
            raise SanitiseError(f"destination {dest} already contains an unexpected entry")


def _check_destination_is_not_snapshot(dest: Path, snapshot_dir: Path) -> None:
    """Refuse before writing anything if the destination would ever touch the
    raw snapshot: AGENTS.md bars deleting or overwriting user-owned inputs,
    and ``os.replace`` inside ``_atomic_write`` would silently do exactly
    that if ``--out-root`` resolved the destination onto the snapshot
    directory (for example, passing the snapshot's own parent)."""
    dest_r = dest.resolve()
    snap_r = snapshot_dir.resolve()
    if dest_r == snap_r:
        raise SanitiseError(
            "destination equals the raw snapshot directory — refusing to overwrite user-owned input"
        )
    if snap_r in dest_r.parents:
        raise SanitiseError(
            "destination is inside the raw snapshot directory — refusing to overwrite user-owned input"
        )
    if dest_r in snap_r.parents:
        raise SanitiseError(
            "destination contains the raw snapshot directory — refusing to overwrite user-owned input"
        )


def _atomic_write(dest_path: Path, data: bytes) -> None:
    tmp_path = dest_path.parent / (dest_path.name + ".tmp")
    tmp_path.write_bytes(data)
    os.replace(tmp_path, dest_path)


def _run_stage(stage: str, func: Callable[..., None], *args: object) -> None:
    """Run one stage, converting any non-``SanitiseError`` exception into a
    ``SanitiseError`` that names only the stage and the exception's type.

    A malformed raw export can make ``vault_cleaner.parse`` (via L8's
    loaders, or ``run_report`` during parity) raise ``SchemaError`` or a
    decode/``ValueError`` whose message embeds real item names and ids.
    Only the stage and the exception type are ever propagated — never
    ``str(exc)`` — so a refusal here can never leak fixture content.
    """
    try:
        func(*args)
    except SanitiseError:
        raise
    except Exception as exc:
        raise SanitiseError(
            f"{stage}: refused — {type(exc).__name__} (value suppressed)"
        ) from exc


def sanitise(
    snapshot_dir: Path,
    out_root: Path,
    config_path: Path,
    no_wishlists_only: bool,
    run_date: str,
) -> None:
    """Sanitise one snapshot directory, writing only if every check passes."""
    for name in KINDS_FILES.values():
        if not (snapshot_dir / name).exists():
            raise SanitiseError(f"missing {name} in {snapshot_dir}")

    snapshot_name = snapshot_dir.name
    if not re.fullmatch(r"[0-9A-Za-z._-]+", snapshot_name):
        raise SanitiseError("snapshot directory name has invalid characters")

    dest = out_root / snapshot_name
    _check_destination_is_not_snapshot(dest, snapshot_dir)

    headers: dict[str, list[str]] = {}
    rows: dict[str, list[dict[str, str]]] = {}
    for kind, name in KINDS_FILES.items():
        header, data_rows = _read_csv(snapshot_dir / name)
        _audit_columns(kind, header)
        headers[kind] = header
        rows[kind] = data_rows

    export_ids, notes_only_ids = _collect_ids(rows)
    all_real_ids = frozenset(export_ids | notes_only_ids)
    sorted_ids = sorted(all_real_ids, key=instance_id_order)
    id_map = _build_id_map(sorted_ids)

    state = SanitiserState(
        id_map=id_map, export_ids=export_ids, next_fresh_rank=len(sorted_ids) + 1
    )

    staged: dict[str, list[list[str]]] = {}
    for kind in ("weapons", "armor", "ghosts"):
        staged[kind] = [_transform_row(headers[kind], row, state) for row in rows[kind]]

    raw_hash_values = frozenset(
        row["Hash"] for kind_rows in rows.values() for row in kind_rows
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for kind, name in KINDS_FILES.items():
            _write_csv(tmp_path / name, headers[kind], staged[kind])

        _check_l1(tmp_path, all_real_ids)
        windows = _l2_windows(all_real_ids)
        _check_l2(tmp_path, windows, state.all_fakes, raw_hash_values)
        _check_l3(tmp_path, all_real_ids)
        _check_l4(tmp_path, state.all_fakes)
        _check_l5(headers, staged, state)
        _check_l6(headers, rows, staged, state)
        _check_l7(headers, staged)
        _run_stage("L8", _check_l8, snapshot_dir, tmp_path, id_map)
        _check_l9(headers, rows, staged, state)
        for name in KINDS_FILES.values():
            _check_format(tmp_path / name)

        # Parity uses the sanitiser's maps frozen: every body it needs was
        # already registered while staging the rows above, so a new
        # registration attempt here signals a real bug, not a legitimate case.
        state.frozen = True
        _run_stage(
            "parity (no-wishlists)", _run_parity, snapshot_dir, tmp_path, config_path, True, state
        )
        parity_modes = ["no-wishlists"]
        if not no_wishlists_only:
            _run_stage(
                "parity (wishlists)", _run_parity, snapshot_dir, tmp_path, config_path, False, state
            )
            parity_modes.append("wishlists")

        _check_destination(dest)
        dest.mkdir(parents=True, exist_ok=True)

        raw_sha: dict[str, str] = {}
        for kind, name in KINDS_FILES.items():
            raw_sha[name] = hashlib.sha256((snapshot_dir / name).read_bytes()).hexdigest()
            _atomic_write(dest / name, (tmp_path / name).read_bytes())

        provenance = {
            "files": {
                name: {"raw_sha256": raw_sha[name], "rows": len(rows[kind])}
                for kind, name in KINDS_FILES.items()
            },
            "parity_modes": parity_modes,
            "run_date": run_date,
            "script_version": 1,
        }
        prov_text = json.dumps(provenance, indent=2, sort_keys=True) + "\n"
        _atomic_write(dest / "provenance.json", prov_text.encode("utf-8"))

    print(f"weapons: {len(rows['weapons'])} rows")
    print(f"armor: {len(rows['armor'])} rows")
    print(f"ghosts: {len(rows['ghosts'])} rows")
    print(
        f"ids mapped: {len(id_map)} (export {len(export_ids)}, notes-only {len(notes_only_ids)})"
    )
    print(f"parity modes passed: {', '.join(parity_modes)}")
    print(f"wrote fixtures to {dest}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot_dir", type=Path)
    parser.add_argument("--out-root", type=Path, default=Path("tests/fixtures/real"))
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--no-wishlists", action="store_true")
    parser.add_argument("--run-date", default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run_date = args.run_date or datetime.now(UTC).date().isoformat()
    try:
        sanitise(args.snapshot_dir, args.out_root, args.config, args.no_wishlists, run_date)
    except SanitiseError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - never let raw exception text leak real content
        # Last-resort safety net: every exception type this script knows how
        # to trigger deliberately is already wrapped as a SanitiseError by
        # _run_stage before it reaches here (see its docstring). Anything
        # still uncaught is unanticipated, so print only its type, never
        # str(exc) — a raw traceback here could otherwise print real item
        # names or ids straight from a malformed export.
        print(f"refused: unexpected {type(exc).__name__} during sanitisation", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
