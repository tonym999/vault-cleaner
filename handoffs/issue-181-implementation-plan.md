# Issue #181 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#181 — Sanitised real-export test fixtures: script, fail-closed checks, CI guard and AGENTS.md amendment`

**Milestone:** none (the issue has no milestone; label `maintenance`)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Anthropic, Claude Code session; the runtime does not expose a native effort setting for this session)

**Implementation model selected:** `claude-sonnet-5` (`xhigh`) (Judgement rung; justified below)

**Plan baseline:** `main` at `a3f7767909a36948e55c3c7d2ca36c40e1e31783` (2026-09-27)

**Allocated implementation branch:** `feat/issue-181-sanitised-real-fixtures`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Add `scripts/sanitize_export.py`. It turns one real DIM snapshot
(`weapons.csv`, `armor.csv`, `ghosts.csv`) into committable fixtures under
`tests/fixtures/real/<snapshot>/` plus `provenance.json`, and refuses to
write anything unless its leakage, parity and format checks pass. The fixtures
must behave exactly like the real vault. Also add a stdlib-only CI guard
(`scripts/check_real_fixtures.py`) that rejects any unmarked id under
`tests/fixtures/real/`, amend `AGENTS.md` to allow these fixtures and make
real-export measurement authorised by default, and commit the sanitised
`2026-09-01T-current` snapshot.

No product code under `src/` changes. `RULESET_VERSION` and
`SNAPSHOT_SCHEMA_VERSION` do not change.

## Context & Measurement

All measurements were taken in this planning session on the owner's snapshot
`2026-09-01T-current`. The owner's standing permission is recorded in #181.
The snapshot is held outside the repository; on the planning machine it is
at `~/Downloads/data/in/2026-09-01T-current/`. Only aggregates are recorded
here.

Raw SHA-256 (identifies the snapshot; the orchestrator confirms these before
dispatch):

```text
d7b6af183720edf40d37e82ca06da2b683e536029557f9f21ed2040cefd928e6  weapons.csv
104fc23186327257304607342140dd21007ec05a612b3089c4f94c0c20e191bb  armor.csv
8cd3851b0346021719ebf0d16d20d6c5894ce84473b83a8a08e6f860233635f4  ghosts.csv
```

### Shape

| | weapons | armor | ghosts |
|---|---|---|---|
| Rows | 665 | 893 | 28 |
| Columns | 74 (`Perks 0`–`Perks 20`) | 49 (`Perks 0`–`Perks 9`) | 24 (`Perks 0`–`Perks 5`) |
| `Id` | all 19 digits, all literal-quoted, all begin `69` | same | same |
| Non-empty `Notes` | 192 | 360 | 0 |
| Notes with an embedded newline / literal quote | 0 / 0 | 49 / 49 | 0 |
| Non-empty `Loadouts` | 143 | 299 | 4 |

UTF-8, no BOM. The 1,586 export ids are unique across all three files.

### Every column, re-checked (issue: "the planner must re-check every column")

Weapons headers: `Name, Hash, Id, Tag, Rarity, Tier, Type, Source, Category,
Element, Ammo, Power, Archetype, Masterwork Type, Masterwork Tier, Owner,
Locked, Equipped, Holofoil, Year, Season, Event, Recoil, AA, Impact, Range,
Zoom, Blast Radius, Velocity, Persistence, Stability, ROF, Reload, Mag,
Handling, Charge Time, Draw Time, Accuracy, Charge Rate, Guard Resistance,
Guard Endurance, Swing Speed, Shield Duration, Airborne Effectiveness, Ammo
Generation, Heat Generated, Cooling Efficiency, Crafted, Crafted Level, Kill
Tracker, Foundry, Loadouts, Notes, Perks 0..20`.

Armor headers: `Name, Hash, Id, Tag, Rarity, Tier, Type, Source, Equippable,
Power, Energy Capacity, Archetype, Tertiary Stat, Tuning Stat, Masterwork
Tier, Owner, Locked, Equipped, Holofoil, Year, Season, Event, Weapons, Health,
Class, Grenade, Super, Melee, Total, Weapons (Base), Health (Base), Class
(Base), Grenade (Base), Super (Base), Melee (Base), Total (Base), Seasonal
Mod, Loadouts, Notes, Perks 0..9`.

Ghost headers: `Name, Hash, Id, Tag, Rarity, Tier, Source, Energy Capacity,
Masterwork Tier, Owner, Locked, Equipped, Holofoil, Year, Season, Event,
Loadouts, Notes, Perks 0..5`.

Classification:

- **Owner-authored text or play history, treated:** `Id`, `Notes`,
  `Loadouts`, `Kill Tracker` (255 distinct kill counts), as the issue says.
- **`Crafted Level` (play history, not in the issue's table): stop-and-ask
  raised in planning. Owner decision 2026-09-27: keep unchanged.** It feeds
  the crafted hard rail (`config.toml` `crafted_level_protect = 10`) and
  exact-dupe ranking, so any change breaks parity.
- **`Owner`:** kept (issue owner decision).
- **Everything else** is item state or public item definition. That covers
  fixed vocabularies (`Tag` is `favorite`/`junk`/`keep` only, plus `Rarity`,
  `Category`, `Element`, `Ammo`, `Event`, `Seasonal Mod`, the `Tertiary`/
  `Tuning Stat` names), manifest data (`Name`, `Hash`, `Type`, `Source`,
  `Archetype`, `Foundry`, `Masterwork Type`, perks, stats, `Year`, `Season`)
  and item state (`Power`, `Masterwork Tier`, `Energy Capacity`, `Tier`,
  `Locked`, `Equipped`, `Holofoil`, `Equippable`, `Crafted`). All of it is kept.
- Perk cells contain no counters. The only digit-bearing perk cells are
  `Tier N: <stat>*`-style names (286 on weapons, 0 elsewhere).

### Notes: stale assumptions in the issue body

The issue expects *short-id* references inside `#vc-` clauses. Measured,
there are **none**: 0 cells contain `[id `. Instead the real Notes carry
**legacy clauses with full 19-digit ids**, the forms that
[note_history.py:50](../src/vault_cleaner/note_history.py#L50) and
[:64-65](../src/vault_cleaner/note_history.py#L64-L65) still recognise:

| Clause shape (ids and numbers masked) | weapons | armor |
|---|---|---|
| `#vc-(junk\|review): dupe-(lower\|tie)[ (locked\|exotic)], kept <ID>` | 395 | — |
| `#vc-(junk\|review): wishlist-trash whole-item[ (locked)]` | 32 | — |
| `#vc-(junk\|review): armor-exact-dupe[ (…)], kept <ID>` | — | 6 |
| `#vc-review: armor-similar to <ID> (…)` | — | 220 |
| `#vc-*: armor-score …` / `armor-last-archetype …` | — | 397 |
| `#vc-test: m3 round trip` (not a known clause) | 1 | — |
| Non-`#vc-` segments (owner text) | 0 | 49 |

Notes hold 1–4 accumulated clauses each.

- **19-digit runs in Notes:** 395 on weapons (346 are current export ids,
  49 are not), 226 on armor (224 current, 2 not). Deduplicated, 240 distinct
  ids appear in Notes, and **28 of them are not in any current export**:
  items since dismantled, but still real instance ids. The issue's id map
  covers only export ids, so those 28 would leak. This plan maps them too.
- **Owner text:** 49 armor segments, each 16–18 lines and 328 or more
  characters, containing `#` hashtags, quotes, parentheses and 8–11-digit
  runs. One armor note is owner text followed by two clauses. The issue's
  "48 contain the owner's own text" is 49 by this segmentation; the
  difference is immaterial because every non-clause segment is replaced.
- The one weapons `#vc-test: …` segment is not a vault-cleaner clause
  (`strip_trailing_tool_clauses` stops at it). It is treated as owner text.

### Loadouts: stale assumption in the issue body

Every non-empty cell starts with an undocumented 5-digit `NNNNN:` prefix
(13 distinct values on weapons, 10 on armor). Names are separated by a bare
`,`. Some names contain `", "`, for example date-stamped auto names. A naive
`,` split gives 227 / 339 / 110 distinct tokens (439 across the files), which
matches the issue's counts. A `", "` split gives 127 / 231 / 7 with at most 2
per cell, so it is wrong. No name matches `^Loadout \d+$`. Five names equal
some cell value in another column (for example a loadout named like a weapon
or an element). **So the issue's literal "no loadout name appears as a cell
value" cannot hold over all columns.** It is scoped to the `Loadouts` column
below. The code reads only emptiness:
[report_run.py:303](../src/vault_cleaner/report_run.py#L303),
[armor_dupes.py:100](../src/vault_cleaner/rules/armor_dupes.py#L100),
[armor_close.py:310](../src/vault_cleaner/rules/armor_close.py#L310),
[ghosts.py:36](../src/vault_cleaner/rules/ghosts.py#L36).

### The issue's 8-digit leakage check, literally, cannot pass

- **2 weapon `Hash` values** share an 8-digit window with a real id. Hashes
  are public manifest values and stay unchanged, so a literal byte scan
  would always refuse.
- With the fake-id scheme below, **1** 8-digit window of a generated fake id
  equals a window of a real id. Fake ids are marker plus zero-padded rank, so
  their windows are mostly zeros. One real id contains `0000`.

The check below exempts digit runs that are *exactly* a generated fake id or
*exactly* a raw-export `Hash` value. It still applies the 8-digit window rule
to every other digit run in the output bytes. Neither exempted value can
carry information about a real id: a fake id is derived from a rank and is
verified disjoint from the real set, and a Hash is copied public item data.

### Id ordering

[id_order.py:13-24](../src/vault_cleaner/rules/id_order.py#L13-L24):
decimal ids compare by `(0, len(magnitude), magnitude, raw)`. All real ids
are 19-digit decimals. Fake ids of one fixed length, assigned by rank in
`instance_id_order`, therefore preserve every pairwise order. That includes
armor `group_id = min(...)`
([armor_dupes.py:249](../src/vault_cleaner/rules/armor_dupes.py#L249)) and
the string-sorted `cited_ids`
([report_run.py:463](../src/vault_cleaner/report_run.py#L463)). No real id
begins with `1000`.

### Prototype (planning session, throwaway, outside the repository)

A ~130-line prototype of the design below ran on the snapshot. Its outputs
went to the session's scratch directory, and no output was committed.

| Check | Result |
|---|---|
| Whole-id leaks (1,614 real ids: 1,586 export + 28 Notes-only) | 0 |
| 8-digit window leaks after the two exemptions | 0 |
| Owner segments replaced / loadout tokens replaced | 50 / 439 |
| Lines ending in whitespace; `git diff --no-index --check` | 0; clean |
| Parity, `no_wishlists=True` (`config.toml`): whole `snapshot_dict` equal under normalisation | **equal** — decisions 2 / 394 / 16 |
| Parity, wishlists on (production `config.toml` sources, cached manifest) | **equal** — decisions 100 / 394 / 16 |
| Parity with the id map deliberately **reversed** | **refused** — 378 differing decisions plus armor details |
| Two runs, same input | byte-identical |
| Output size | 648 KB (weapons 342,792 B; armor 309,432 B; ghosts 5,365 B) |

The whole sanitised export is committed; 648 KB is not a size problem (the
repository pack is 6.0 MiB).

### Model verification and selection

Rung: **Judgement.** The plan settles every treatment rule, check and file.
The delegated work still needs real judgement at a privacy boundary: exact
regex and segmentation edge cases, a parity comparator that must neither
over- nor under-normalise, and planted-leak and mapping-error tests that must
be shown to fail when their check is bypassed. A vacuous check here is a
silent privacy failure, so the Bounded rung is not chosen.

- The rung's primary, `gpt-5.6-luna` (`high`), could not be confirmed. On
  2026-09-27 OpenAI's models page lists `gpt-6-astra`, `gpt-6-sol` and
  `gpt-6-luna`, and of GPT-5.6 only `gpt-5.6-cyber`.
  `handoffs/README.md`'s roster (verified 2026-09-03) may be stale. That is
  for the owner or a follow-up to confirm; this plan does not edit it.
- Selected `claude-sonnet-5` (`xhigh`), a listed Judgement-rung permitted
  alternative whose availability is not in doubt. Anthropic
  `output_config.effort` supports `xhigh`.
- The orchestrator may re-select under `handoffs/README.md`, for example to
  `gpt-6-luna` once the roster is confirmed.

## Dependencies and assumptions

- **Authorisation source.** The owner's standing permission (#181 body,
  decisions of 2026-09-26) covers measuring the real exports and committing
  sanitised fixtures. No per-ticket authorisation is needed. The implementer
  records the measurement in `WORKLOG.md`, as the amended rule requires.
- **Owner decision, 2026-09-27 (this planning session): `Crafted Level` is
  kept unchanged.**
- **Deviations from the issue text, each forced by measurement:**
  1. The id map also covers every 16-or-more-digit run found in raw Notes
     (28 real ids of dismantled items), not only export ids.
  2. Short-id rewriting is implemented, because future exports will carry
     current-format clauses. The current snapshot has none; it has legacy
     full ids, which are rewritten.
  3. The 8-digit window scan exempts runs that are exactly a generated fake
     id or exactly a raw `Hash` value.
  4. "No loadout name / owner text appears as a cell value" is enforced on
     the `Loadouts` and `Notes` columns, backed by a positive grammar for
     both. Five loadout names legitimately equal other columns' values.
  5. Loadouts are split on a bare `,` (DIM's separator), as the issue's
     naive count did. The `NNNNN:` prefix is part of the first token and is
     replaced with it.
  6. Parity compares the **whole** `snapshot_dict` under an explicit
     normalisation. This is stricter than the issue's field list and
     subsumes it (decisions, armor exact and same-stat groups, evaluations,
     per-section counts).
- **Wishlist-mode parity needs the owner's caches or network.**
  `run_report` resolves `wishlists/` and `data/cache/` relative to the
  working directory (`config.toml` `[paths]`;
  [pipeline.py:141-159](../src/vault_cleaner/pipeline.py#L141-L159)).
  Without a fresh `data/cache/perk-name-map.json`, the manifest step
  downloads about 200 MB. The orchestrator makes sure the implementer's
  checkout has the snapshot and, ideally, the owner's cached perk map. On the
  planning machine that is `~/Downloads/data/cache/perk-name-map.json`; it
  goes into the checkout's gitignored `data/cache/`. The `wishlists/` cache
  is fetched on demand (3 public files).
- **Neighbouring work.** #174 (implementation pending) changes weapon
  decisions with wishlists. That does not affect this ticket: the fixtures
  are raw-equivalent inputs, and parity compares raw and sanitised under the
  same code. The issue body notes that #174's bug cannot be triggered by
  committed fixtures; adopting these fixtures in rule tests is out of scope.
  #144 (template hardening) is unrelated.
- **Project board.** The planning session's `gh` token lacks `read:project`,
  so #181's board status was not verified. The owner or orchestrator checks it.

## Proposed Plan & Scope

### Shared constants

Both scripts define `ID_MARKER = "1000"` and the fake-id shape
`^1000[0-9]{15}$`. `check_real_fixtures.py` is stdlib-only and must not
import `vault_cleaner` or the sanitiser, so the constant is duplicated. A test
asserts the two scripts agree.

### Sanitiser

#### [NEW] [sanitize_export.py](../scripts/sanitize_export.py)

Usage:

```text
python scripts/sanitize_export.py <snapshot_dir> [--out-root tests/fixtures/real]
    [--config config.toml] [--no-wishlists] [--run-date YYYY-MM-DD]
```

Module docstring: purpose, the privacy boundary, and "writes nothing unless
every check passes". Keep the logic in importable functions, so tests can load
the script by path as
[test_report_run.py:299-303](../tests/test_report_run.py#L299-L303) does and
call the checks directly. Define `SanitiseError(Exception)`. On any refusal,
`main` prints `refused: <reason>` to stderr and returns 1. Reasons name the
check, the file and, where safe, a row number; **never print real ids, Notes
text or loadout names in errors**. It returns 0 after writing.

**Input.**

- `<snapshot_dir>` must contain `weapons.csv`, `armor.csv` and `ghosts.csv`;
  a missing file is a refusal.
- The snapshot name is the directory's basename and must fullmatch
  `[0-9A-Za-z._-]+`.
- Decode strict UTF-8 and drop one leading BOM if present.
- Parse with `csv.reader` over `io.StringIO(text, newline="")`. Refuse
  duplicate header names and any row whose width differs from the header's.
- Access every cell by header name (rows become `dict(zip(header, row))`).

**Column audit (fail-closed).** A per-kind allowlist holds exactly the
headers measured above: `TREATED = {"Id", "Notes", "Loadouts", "Kill Tracker"}`
plus an explicit `KEPT` set per kind. Any header matching `Perks [0-9]+` is
kept. Any other header is a refusal:
`unclassified column <name> in <kind>.csv — classify it before sanitising
(#181)`. This carries the issue's "stop-and-ask, not a silent keep" into
future DIM drift.

**Id map.**

- Real id set `R` = every export `Id` with DIM quotes stripped
  ([parse.py:82-85](../src/vault_cleaner/parse.py#L82-L85)), across all
  three files, ∪ every maximal ASCII digit run of length ≥ 16 in any raw
  `Notes` cell.
- Refuse unless every export id fullmatches `[0-9]{16,}` and no member of
  `R` starts with `ID_MARKER`.
- Sort `R` by `instance_id_order`. The member at rank *i* (1-based) maps to
  `ID_MARKER + f"{i:015d}"`.
- Output `Id` cells are `'"' + fake + '"'`. The csv writer then emits DIM's
  `"""…"""` wrapping.

**Notes transform `sanitize_notes(value)`.**

1. Split the cell before every `#vc-` (`re.split(r"(?=#vc-)", value)`).
2. For each segment, keep its leading and trailing whitespace verbatim and
   work on the stripped body. Empty bodies pass through.
3. A body that starts with `#vc-` is a clause candidate:
   - replace every maximal digit run of length ≥ 16 with its fake;
   - rewrite short-id tokens (next step);
   - keep the result if
     `note_history.strip_trailing_tool_clauses(result) == ""`, i.e. it is
     wholly known vault-cleaner clauses
     ([note_history.py:87-104](../src/vault_cleaner/note_history.py#L87-L104));
   - otherwise replace the whole body with a placeholder.
4. Every other body is replaced with a placeholder.

**Short-id tokens.**

- A token is `(?<=\bid )[0-9]*…[0-9]+(?:~[0-9a-f]+-[0-9a-f]{8})?`, the forms
  `short_id` emits for long ids
  ([duplicate_reference.py:108-162](../src/vault_cleaner/duplicate_reference.py#L108-L162)).
- Resolve it against the export ids: the visible prefix (digits before `…`)
  and suffix (digits after `…`, before any `~`) must match exactly one id.
  That id's token becomes `short_id(fake)`.
- An unresolvable or ambiguous token becomes `short_id` of a fresh fake id,
  allocated after the ranks in order of first appearance and keyed by the
  token text. The clause stays well-formed and the digest is never kept (its
  8 hex digits of a real id's SHA-256 are brute-forceable given the
  prefix/suffix).

**Placeholder.**

- Distinct stripped bodies are numbered *k* = 1, 2, … by first appearance:
  weapons, then armor, then ghosts, in row order.
- The body is split on `"\n"`. Each line *j* (0-based) becomes `""` if it is
  blank; otherwise `f"note {k}.{j}"`, then `", x"` if the line contained
  `,`, then `' "q"'` if it contained `"`. Lines are rejoined with `"\n"`.
- This keeps embedded newlines, commas and quotes, so the parser paths stay
  exercised, and copies no characters of the text.
- A `"\r"` anywhere in raw Notes is a refusal (0 measured). This keeps line
  handling unambiguous.

**Loadouts `sanitize_loadouts(value)`.**

- A cell that is empty after `.strip()` passes through unchanged. Emptiness
  is the only thing the code reads.
- Otherwise split on `","`. Each exact token maps to `Loadout N`, numbered by
  first appearance in the same file/row/token order. Join with `","`. The
  token count per cell is preserved.

**Kill Tracker.** If the column exists, every cell becomes `"0"`.

**Everything else** is copied cell-for-cell.

**Output.** Header and row order are exactly the raw order.
`csv.writer(lineterminator="\n")` with default minimal quoting, encoded
UTF-8 without BOM. Files are staged in a `tempfile.TemporaryDirectory`. Every
check below runs on the staged bytes.

**Checks.** All run on the staged bytes. The first failure refuses and
nothing is written.

- **L1, whole id:** no member of `R` occurs as a substring of any staged
  CSV's bytes.
- **L2, 8-digit windows:** let `W` be every 8-digit window of every member
  of `R`. For each maximal digit run of length ≥ 8 in the staged bytes: skip
  it if it is exactly a generated fake id or exactly a raw `Hash` cell value;
  otherwise refuse if any of its 8-digit windows is in `W`.
- **L3, Id cells:** every output `Id` (quotes stripped) fullmatches
  `^1000[0-9]{15}$` and is unique within its file, and
  `{fakes} ∩ R = ∅`.
- **L4, long runs:** every maximal digit run of length ≥ 16 in the staged
  bytes is a generated fake id.
- **L5, Notes:**
  - every output Notes segment, split as above, is either wholly known
    clauses (`strip_trailing_tool_clauses(body) == ""`) or matches the
    placeholder grammar
    `^(note [0-9]+\.[0-9]+(, x)?( "q")?|)(\n(note [0-9]+\.[0-9]+(, x)?( "q")?|))*$`;
  - no output Notes cell or segment body equals any original owner segment
    body.
- **L6, Loadouts:**
  - raw empty ⇔ output empty;
  - non-empty output fullmatches `Loadout [1-9][0-9]*(,Loadout [1-9][0-9]*)*`
    with the same token count as raw;
  - no output cell or token equals an original loadout token.
- **L7:** every `Kill Tracker` cell is `"0"`.
- **L8, untouched columns:**
  - load raw and staged through `parse.load_weapons` / `load_armor` /
    `load_ghosts`;
  - every column outside `TREATED` is equal;
  - the staged `Id` column equals the raw `Id` column mapped through the id
    map.

  This also proves that the committed files load through the normal parsers.
- **P, parity:** see the parity comparator below. It runs with
  `no_wishlists=True`, and again with wishlists on unless `--no-wishlists`
  was given.
- **F, format** (`git diff --check` equivalent), per staged file:
  - no `"\r"`;
  - ends with exactly one `"\n"`;
  - no line ends in a space or tab;
  - no line's leading whitespace has a space before a tab;
  - no line starts with a conflict marker (`<<<<<<<`, `=======` or `>>>>>>>`
    followed by a space or end of line).

**Parity comparator.** Run
`run_report(config_path=--config, weapons_path=…, armor_path=…,
ghosts_path=…, no_wishlists=mode)` on the raw and on the staged directory,
and take `snapshot_dict` of each
([report_run.py:435-495](../src/vault_cleaner/report_run.py#L435-L495),
[:508](../src/vault_cleaner/report_run.py#L508)).

1. From both, drop `fingerprint`, `inputs.sources`, and each section's
   `source`. These hold file digests and paths, which must differ.
2. Let `N(s)` replace every short-id token (the pattern above, without the
   `id ` look-behind, because explanations render `copy …1234`;
   [explanation.py:50-56](../src/vault_cleaner/explanation.py#L50-L56))
   with `<SID>`.
3. Transform the raw snapshot recursively:
   - for keys `note` and `original_notes`, the value becomes
     `sanitize_notes(N(value))`, using the same placeholder numbering, no new
     allocations, and no short-id resolution (step 2 already removed the
     tokens);
   - for every other string, a whole-string member of `R` becomes its fake;
     otherwise every ≥ 16-digit run becomes its fake, and then `N` is applied.
4. Transform the staged snapshot by applying `N` to every string.
5. Refuse unless the two structures are equal.
6. On refusal, the message gives per-section decision counts and the number
   of differing decisions only.

If step 3 would allocate a new placeholder or fresh fake, that is itself a
parity refusal.

**Write.**

- Refuse if `<out-root>/<snapshot>/` contains any file other than the four
  names below.
- Create the directory if it is missing. Replace each file by writing
  `<name>.tmp` and then `os.replace`. Never delete anything.
- Files: `weapons.csv`, `armor.csv`, `ghosts.csv`, `provenance.json`.

`provenance.json` is `json.dumps(obj, indent=2, sort_keys=True) + "\n"`,
UTF-8, LF, with:

```json
{
  "files": {
    "armor.csv": {"raw_sha256": "<hex>", "rows": 893},
    "ghosts.csv": {"raw_sha256": "<hex>", "rows": 28},
    "weapons.csv": {"raw_sha256": "<hex>", "rows": 665}
  },
  "parity_modes": ["no-wishlists", "wishlists"],
  "run_date": "YYYY-MM-DD",
  "script_version": 1
}
```

Nothing else about the raw files. `run_date` defaults to today's UTC date.
`parity_modes` records which parity runs passed (`["no-wishlists"]` with
`--no-wishlists`).

### CI guard

#### [NEW] [check_real_fixtures.py](../scripts/check_real_fixtures.py)

Stdlib-only (`csv`, `io`, `pathlib`, `re`, `sys`). Signature:
`check(root: Path) -> list[str]` (the errors) and a `main` that runs it on
`tests/fixtures/real` relative to the repository root. It exits 1 and prints
the errors if there are any. If the root does not exist, it passes.

- Every file under the root must be `<snapshot>/{weapons,armor,ghosts}.csv`
  or `<snapshot>/provenance.json`, at exactly that depth. Anything else is
  an error (`unexpected file`).
- For each CSV, decoded as strict UTF-8:
  - an `Id` header is required;
  - every `Id` cell, with `"` stripped, must fullmatch `^1000[0-9]{15}$`;
  - every maximal run of ≥ 16 ASCII digits in the file's bytes must start
    with `1000`. This catches a real id inside Notes, or a raw export
    renamed into place.
- Errors name the file and row number, not the value.

#### [MODIFY] [ci.yml](../.github/workflows/ci.yml#L19-L25)

Add a hygiene step after "No tracked files under data/":

```yaml
      - name: Real-export fixtures carry only marked ids
        run: python3 scripts/check_real_fixtures.py
```

### Committed fixtures

#### [NEW] `tests/fixtures/real/2026-09-01T-current/{weapons,armor,ghosts}.csv`, `provenance.json`

Produced only by running the sanitiser from the repository root on the
snapshot, with both parity modes and the production `config.toml`. Never
edited by hand. `.gitattributes` already applies `tests/fixtures/** -text`
([.gitattributes:5](../.gitattributes#L5)); no change there.

### Tests

#### [NEW] [test_sanitize_export.py](../tests/test_sanitize_export.py)

Load the script by path. All inputs are synthetic and built in `tmp_path`,
giving explicit test-owned paths. Synthetic ids are 19-digit strings
beginning `69`; they are invented. Parity runs in tests use
`--no-wishlists`, so they stay offline.

**Transform units:**

- legacy `kept <id>` and `armor-similar to <id> (…)` clauses are rewritten
  to the fake and kept;
- a Notes-only id (not in any export) is mapped;
- owner text with newline, comma and quote becomes the exact placeholder;
  identical owner texts share *k*;
- `#vc-test: …` becomes a placeholder;
- owner text followed by clauses keeps the clauses;
- a current-format `keep [id …NNNN; …]` resolves to `short_id(fake)`, and an
  ambiguous one gets a fresh fake with no digest left;
- loadouts keep token count, including the `NNNNN:` prefix token, and empty
  stays empty;
- Kill Tracker becomes `0`;
- the fake map preserves `instance_id_order`.

**Refusals (each asserts exit 1 and that `<out-root>/<snapshot>` does not
exist afterwards):**

- an unclassified column;
- an id starting with `1000`;
- a non-decimal id;
- `"\r"` in Notes;
- a missing export file;
- an unexpected file already present in the destination.

**Planted leaks, one test each** (acceptance criterion 2). Monkeypatch one
transform so the leak survives:

- `sanitize_notes` leaves one id unmapped (L1/L2/L4 refuse);
- the Id map returns a raw id for one row (L3 refuses);
- `sanitize_notes` returns owner text (L5 refuses);
- `sanitize_loadouts` returns the input (L6 refuses);
- Kill Tracker is left unchanged (L7 refuses).

Each refusal test also calls the corresponding check function directly on a
tampered staged table.

**Parity mapping error** (acceptance criterion 3):

- Build a synthetic snapshot in which an id tie-break decides a survivor,
  for example two identical armor pieces decided by "deterministic id
  tie-break" (compare `tests/fixtures/armor_dupes.csv`).
- Monkeypatch the id map to reverse the order. Assert that parity refuses
  and nothing is written.
- Also assert that the same input with the correct map passes.

**F:** a staged line with trailing whitespace refuses.

**Byte stability:** two runs with the same `--run-date` produce identical
bytes, and `provenance.json` has exactly the keys above with the correct
row counts and SHA-256s.

#### [NEW] [test_real_fixtures.py](../tests/test_real_fixtures.py)

- **Smoke test.** For the committed `tests/fixtures/real/2026-09-01T-current/`:
  - `parse.load_weapons`, `load_armor` and `load_ghosts` load 665, 893 and
    28 rows;
  - every `Id` matches `^1000[0-9]{15}$`;
  - `provenance.json` row counts match;
  - `check_real_fixtures.check(<repo>/tests/fixtures/real)` returns `[]`.
- **CI guard tests** (acceptance criterion 4), each on a `tmp_path` tree:
  - a valid tree passes;
  - an unmarked `Id` fails;
  - an unmarked 19-digit run in `Notes` fails;
  - a stray file fails;
  - a missing root passes;
  - both scripts' `ID_MARKER` values are equal.
- No rule-decision assertions on the real fixtures (out of scope).

### Documentation

#### [MODIFY] [AGENTS.md](../AGENTS.md#L38-L48)

Replace the first hard-rule bullet (lines 38–48) with, verbatim:

```markdown
- **Never commit anything under `data/`**, any raw vault export, or anything
  reconstructed from one. This repo is public; `data/` holds personal Bungie
  account data. `.gitignore` covers it — do not weaken that, and check
  `git status` before committing. Measuring a real export is authorised by
  default (owner's standing permission, #181; see *Measure the real export
  before designing a rule*): record each measurement in `WORKLOG.md`.
  **Findings derived from a real export may be committed** to `docs/`:
  aggregate counts, distributions, and item names are permitted; verbatim
  raw CSV rows, real instance `Id` values, the owner's own `Notes` text and
  loadout names are not.
- **Sanitised real-export fixtures** are the one exception. They live only in
  `tests/fixtures/real/<snapshot>/` and are produced only by
  `scripts/sanitize_export.py`, which writes nothing unless its leakage,
  parity and format checks pass. Never hand-edit, trim or copy files into that
  directory; regenerate instead. Every `Id` there carries the `1000` marker
  prefix, and CI (`scripts/check_real_fixtures.py`) rejects any that does not.
  If the sanitiser refuses a new export's unclassified column, classify it
  with the owner before sanitising.
```

Replace the first Conventions bullet (lines 164–168) with, verbatim:

```markdown
- Test fixtures in `tests/fixtures/` are pinned to real export headers but
  contain only fake items, except the sanitised real-export fixtures under
  `tests/fixtures/real/` (see *Hard rules*). Regenerate the header from a
  fresh export if DIM's format changes; never paste real rows. Hand-written
  fixtures stay synthetic.
```

In *Setup & commands*, extend the CI sentence (lines 16–17) so it begins,
verbatim:

```markdown
CI also rejects tracked files under `data/`, any `Id` under
`tests/fixtures/real/` without the sanitiser's marker prefix, whitespace or
line-ending errors
```

The rest of the sentence is unchanged. After the golden-regeneration block,
add:

````markdown
Regenerate the sanitised real-export fixtures from a snapshot directory
(from the repo root; the wishlist parity run uses the normal caches):

```bash
python scripts/sanitize_export.py data/in/<snapshot>
```
````

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

A dated entry covering:

- the real-export measurement (aggregates only, recorded under the new
  default authorisation);
- the six deviations above and the `Crafted Level` owner decision;
- the sanitiser run's check summary: counts, parity modes, output sizes;
- the evidence that each planted-leak and mapping-error test fails with its
  check bypassed.

## Mechanical inclusion test

A proposed change is **in scope** if and only if it:

- adds or changes `scripts/sanitize_export.py` or
  `scripts/check_real_fixtures.py` as specified;
- adds the CI hygiene step;
- adds the sanitiser's output under `tests/fixtures/real/2026-09-01T-current/`
  exactly as written by the script;
- adds `tests/test_sanitize_export.py` or `tests/test_real_fixtures.py`;
- makes the verbatim `AGENTS.md` edits, or adds the `WORKLOG.md` entry.

Worked examples:

- **IN SCOPE:** a private helper in `sanitize_export.py` that walks the
  snapshot dict for the parity comparator.
- **IN SCOPE:** building synthetic 19-digit-id CSVs in `tmp_path` inside
  the tests.
- **OUT OF SCOPE:** any change under `src/vault_cleaner/`, including making
  `note_history._GENERATED_CLAUSE_RES` public. Use
  `strip_trailing_tool_clauses`.
- **OUT OF SCOPE:** editing, filtering or subsetting committed fixture files
  by hand; adding a second snapshot (`2026-08-29T013321Z`).
- **OUT OF SCOPE:** changing existing fixtures or goldens, or using the real
  fixtures in rule tests.
- **OUT OF SCOPE:** editing `handoffs/README.md`'s model roster, `.gitignore`,
  `.gitattributes`, or any issue.

### Stop conditions

Stop implementation and return to the orchestrator if:

- the sanitiser refuses on the real snapshot and the fix would change a
  treatment rule, relax or remove a check, or widen an exemption;
- parity cannot run in wishlist mode (no network and no caches). Do not
  commit a fixture whose provenance lacks `"wishlists"` without orchestrator
  approval;
- the raw SHA-256s differ from the plan's (a different snapshot);
- any change under `src/` appears necessary;
- the committed output exceeds 2 MB, or `git diff --check` flags it;
- a planted-leak or mapping-error test cannot be made to fail when its check
  is bypassed.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Vacuous checks.** A planted-leak or parity test passes even with its
   check disabled, for example because the synthetic input has no id-decided
   tie, or the monkeypatch misses the path actually used. Every such test
   needs bypass evidence.
2. **Over-normalising parity.** A comparator that maps or `<SID>`-normalises
   more than specified, such as dropping `explanation`, comparing only
   decisions, or normalising every digit run, would hide a real divergence.
   The comparator must equal the specification above.
3. **Leak in a side channel.** Real ids, Notes text or loadout names printed
   in refusal messages or exceptions; Notes-only ids left unmapped; a
   short-id digest kept; or `provenance.json` carrying more than specified.
4. **CI guard that cannot see the failure.** A guard that parses only the
   `Id` column misses a raw id in Notes or a renamed raw file. The guard also
   needs the byte-level ≥ 16-digit run check and the file allowlist.

# Reusable implementer execution prompt

Implement issue #181 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-181-implementation-plan.md
```

Read the entire handoff, issue #181, `AGENTS.md`, `PLAN.md`, the newest few entries at the top of `WORKLOG.md` (not the whole file), and the code the handoff cites before editing.

Rules:
- work on `feat/issue-181-sanitised-real-fixtures`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every hunk;
- copy the `AGENTS.md` text in the plan verbatim;
- confirm the raw snapshot's SHA-256s match the plan before running the sanitiser; never print or commit raw rows, real ids, Notes text or loadout names, and never commit anything under `data/`;
- generate the committed fixtures only by running `python scripts/sanitize_export.py <snapshot_dir>` from the repository root, with both parity modes;
- for every planted-leak and mapping-error test, show it fails with its check bypassed, then restore;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `python3 scripts/check_real_fixtures.py`, `git diff --check origin/main...HEAD`, and `git ls-files data/` (must print nothing);
- commit and push the implementation branch; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, return to the orchestrator:

- the base and head SHAs and the changed-file list;
- the full output of each verification command;
- the sanitiser's stdout for the committed run and the committed `provenance.json`;
- the bypass evidence for each planted-leak and mapping-error test;
- the committed fixture sizes;
- any deviations from the plan.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
This is a privacy boundary in a public repository. Its failure modes are
silent: a check that cannot fail, an over-normalising parity comparator, or a
side-channel leak would all pass CI. The committed fixture is
hard to retract once published. The issue itself recommends independent
adversarial review, and this plan narrows four of the issue's literal checks
on measured grounds, which a fresh reviewer should challenge.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] No file under `src/` changed; `RULESET_VERSION` and `SNAPSHOT_SCHEMA_VERSION` unchanged; `git ls-files data/` empty.
- [ ] Committed fixtures are byte-identical to a fresh sanitiser run by the reviewer on the same snapshot with the same `--run-date` (reviewer has the snapshot) or, failing access, `check_real_fixtures` passes and the committed `provenance.json` records both parity modes and the plan's SHA-256s.
- [ ] A byte scan of the committed fixtures finds no ≥ 16-digit run without the `1000` marker, no `[id ` digest (`~…-xxxxxxxx`), no non-placeholder Notes text, and no Loadouts cell outside the `Loadout N` grammar.
- [ ] Column audit allowlists match the measured headers exactly; an unclassified column refuses.
- [ ] Notes-only ids are in the map; short-id rewriting never keeps a digest.
- [ ] L1–L8, P and F exist as specified, and exemptions are exactly "whole fake id" and "whole raw Hash value".
- [ ] The parity comparator matches the specification: whole snapshot, only the three digest/path drops, and the specified normalisation.
- [ ] Every planted-leak and mapping-error test has bypass evidence.
- [ ] Refusal messages and exceptions print no real ids, Notes text or loadout names.
- [ ] CI hygiene step added; guard is stdlib-only with byte-level run and file allowlist checks; markers agree.
- [ ] `AGENTS.md` edits verbatim; `WORKLOG.md` entry records the measurement, deviations and the `Crafted Level` decision.
- [ ] `ruff`, `pytest`, `git diff --check` pass.

# Dispatch comment draft

Planned #181 in [handoffs/issue-181-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-181-implementation-plan.md) on `main`.

- **Implementer model & effort:** `claude-sonnet-5` (`xhigh`), Judgement rung
- **Implementation branch:** `feat/issue-181-sanitised-real-fixtures`
- **Review path:** independent adversarial review
- **Likely findings:** vacuous planted-leak or mapping-error tests; a parity comparator that over-normalises; side-channel leaks (refusal messages, Notes-only ids, short-id digests); a CI guard that only reads the `Id` column.
