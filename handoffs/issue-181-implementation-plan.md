# Issue #181 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#181 — Sanitised real-export test fixtures: script, fail-closed checks, CI guard and AGENTS.md amendment`

**Milestone:** none (the issue has no milestone; label `maintenance`)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Anthropic, Claude Code session; the runtime does not expose a native effort setting for this session)

**Implementation model selected:** `gpt-5.6-luna` (`high`) (Judgement rung; justified below)

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
The snapshot is in the owner's gitignored `data/in/2026-09-01T-current/` in
the main checkout (also held at `~/Downloads/data/`; the bytes are identical).
Only aggregates are recorded here.

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

The prototype predates review-fix rounds 1 and 2. It retained clauses using
the recogniser, copied their numbers, and compared short ids with `<SID>`
only. Round 2 measured the final grammar separately: all 1,050 real clauses
are recognised, and after canonicalisation they are still full clauses to
`strip_trailing_tool_clauses`. Strip behaviour is therefore unchanged, so
the prototype's retention and parity results still hold. Reference
truthfulness (3(d)) was not prototyped. Every real reference is a legacy
full id, which the id map, not `<SID>`, checks.

### Model verification and selection

Rung: **Judgement.** The plan settles every treatment rule, check and file.
The delegated work still needs real judgement at a privacy boundary: exact
regex and segmentation edge cases, a parity comparator that must neither
over- nor under-normalise, and planted-leak and mapping-error tests that must
be shown to fail when their check is bypassed. A vacuous check here is a
silent privacy failure, so the Bounded rung is not chosen.

- Selected the rung's primary, `gpt-5.6-luna` (`high`). OpenAI's model page
  for it
  (<https://developers.openai.com/api/docs/models/gpt-5.6-luna>, checked
  2026-09-27) lists it as available, with `reasoning.effort` values `none`,
  `low`, `medium` (default), `high`, `xhigh` and `max`.
- Permitted alternative on the same rung: `claude-sonnet-5` (`xhigh`).
- The orchestrator may re-select under `handoffs/README.md`.
- Review-fix rounds 1 and 2 widened the specification (a two-form clause
  grammar with canonical re-rendering, reference-truthfulness checks, a
  text-validating CI guard) but settled every design choice. The rung is
  unchanged.

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
     per-section counts). Every short id that parity normalises must also be
     a truthful rendering of its decision's `kept_id`.
  7. "Keep `#vc-` clauses" is narrowed to clauses that match the strict
     clause grammar below, and each kept clause is re-rendered in canonical
     form: every numeric slot becomes `0`, and every reference becomes
     `[id <short_id(fake)>]`. Anything else, including owner text written in
     clause form, becomes a placeholder.

  Deviation 7 comes from PR #183 review, rounds 1 and 2.
  `strip_trailing_tool_clauses` accepts arbitrary text in its free slots,
  for example `#vc-review: armor-similar to <id> (private note)`, so it
  cannot decide what is safe to keep. Numeric slots can carry owner-typed
  numbers that cannot be verified, for example `max stat delta 3141592`.
- **Wishlist-mode parity needs the owner's caches or network.**
  `run_report` resolves `wishlists/` and `data/cache/` relative to the
  working directory (`config.toml` `[paths]`;
  [pipeline.py:141-159](../src/vault_cleaner/pipeline.py#L141-L159)).
  Without a fresh `data/cache/perk-name-map.json`, the manifest step
  downloads about 200 MB. The owner's main checkout already has
  `data/cache/perk-name-map.json` and the snapshot in `data/in/`, both
  gitignored. If the implementer works in a different checkout or worktree,
  the orchestrator copies `data/` into it first; never commit it. The
  `wishlists/` cache is fetched on demand (3 public files).
- **Neighbouring work.** #174 (implementation pending) changes weapon
  decisions with wishlists. That does not affect this ticket: the fixtures
  are raw-equivalent inputs, and parity compares raw and sanitised under the
  same code. The issue body notes that #174's bug cannot be triggered by
  committed fixtures; adopting these fixtures in rule tests is out of scope.
  #144 (template hardening) is unrelated.
- **Project board.** #181 is `Todo` on the project board (verified
  2026-09-27).

## Proposed Plan & Scope

### Shared grammar (single source: `check_real_fixtures.py`)

`scripts/check_real_fixtures.py` is stdlib-only and must not import
`vault_cleaner`. It is the **only** definition of the constants and grammars
below. `sanitize_export.py` loads it by path, from its own directory, with
`importlib.util.spec_from_file_location`, and never redefines them. The
sanitiser's writing rules and CI's acceptance rules therefore cannot drift.

- `ID_MARKER = "1000"`; `FAKE_ID = r"1000[0-9]{15}"`.
- `PLACEHOLDER_RE`: one owner-text segment,
  `(?:note [0-9]+\.[0-9]+(?:, x)?(?: "q")?)?(?:\n(?:note [0-9]+\.[0-9]+(?:, x)?(?: "q")?)?)*`,
  non-empty.
- `LOADOUTS_RE = r"Loadout [1-9][0-9]*(?:,Loadout [1-9][0-9]*)*"`.
- **Clause grammar: two compiled forms of one set of family templates.**
  - `INPUT_CLAUSE_RES` is permissive in numeric and reference slots. The
    sanitiser uses it only to *recognise* a candidate clause.
  - `RETAINED_CLAUSE_RES` is canonical. The sanitiser *writes* this form,
    and it is the only form L5 and the CI guard accept.

  Both are built from the same templates, one per family, so the two forms
  cannot drift. The slot types:

  | Slot | `INPUT_CLAUSE_RES` | `RETAINED_CLAUSE_RES` |
  |---|---|---|
  | `N` (count, rank, delta, total, surplus, curated matches) | `[0-9]+` | `0` |
  | `SCORE` (armor score, floor) | `-?[0-9]+(?:\.[0-9]+)?` | `0` |
  | `ID` (legacy full id, already mapped) | `FAKE_ID` | `FAKE_ID` |
  | `REF` | `\[id RAWSID(?:; [^;\]\r\n]*)*\]` | `\[id …[0-9]{4}\]` |
  | `STAT` | `(?:weapons\|health\|class\|grenade\|super\|melee)` | same |
  | `TUNING` | `(?:Weapons\|Health\|Class\|Grenade\|Super\|Melee\|none/unknown)` | same |
  | `CLASS` | `(?:hunter\|titan\|warlock)` | same |
  | `SLOT` | `(?:helmet\|gauntlets\|chest armor\|leg armor\|hunter cloak\|titan mark\|warlock bond)` | same |
  | `ARCH` | the twelve Destiny archetypes of [armor-archetypes.md](../docs/armor-archetypes.md#L33-L44), lowercase, or `no archetype` | same |
  | `PROFILE` | `(?:melee_primary)`: an explicit allowlist, not an identifier pattern | same |
  | `EXACT` | `(?:dupe-(?:lower\|tie)\|armor-exact-dupe(?:-tie)?\|armor-exotic-class-dupe)(?: \((?:loadout\|locked\|exotic)\))?` | same |
  | `WINNER` | the closed list at [note_history.py:21-26](../src/vault_cleaner/note_history.py#L21-L26) | same |

  `RAWSID` is the short-id token pattern
  `[0-9]*…[0-9]+(?:~[0-9a-f]+-[0-9a-f]{8})?`. The template
  `SCOREC = armor-score SCORE < floor SCORE \(best: PROFILE, rank N/N CLASS SLOT\)`
  follows [armor.py:187-191](../src/vault_cleaner/rules/armor.py#L187-L191).

  The family templates:

  1. `#vc-(?:junk|review): EXACT, kept ID` (legacy)
  2. `#vc-(?:junk|review): EXACT; keep REF; winner WINNER(?:; Candidate Tuning Mod Slot: TUNING; Survivor Tuning Mod Slot: TUNING)?`
  3. `#vc-review: armor-similar to ID \((?:identical stats(?:, tuning STAT vs STAT)?|max stat delta N, total N)\)` (legacy)
  4. `#vc-review: armor-dominated by ID \(\+N total\)` (legacy)
  5. `#vc-review: armor-dominated by; compare REF; \+N total; partner (?:largest stat surplus|deterministic id tie-break)(?:; Candidate Tuning Mod Slot: TUNING; Partner Tuning Mod Slot: TUNING)?`
  6. `#vc-review: armor-similar to; compare REF; (?:identical stats|max stat delta N, total N); partner (?:closest stat distance|deterministic id tie-break)(?:; Candidate Tuning Mod Slot: TUNING; Partner Tuning Mod Slot: TUNING)?` ([armor_close.py:59-62](../src/vault_cleaner/rules/armor_close.py#L59-L62))
  7. `#vc-review: coverage-(?:dominated by|uncovered vs); compare REF; curated matches N vs N; partner (?:largest coverage gain|most curated matches|most combinations|deterministic id tie-break)`
  8. `#vc-(?:junk|review): wishlist-trash (?:whole-item|roll)(?: \((?:locked|exotic)\))?`
  9. `#vc-junk: SCOREC`
  10. `#vc-review: SCOREC \((?:locked|exotic)\)`
  11. `#vc-review: armor-last-archetype \(ARCH\), SCOREC`
  12. `#vc-junk: ghost-unprotected-surplus`

  **Why canonicalise (PR #183 round 2).** Numeric and reference payloads
  in input Notes reflect historic vault state, so the sanitiser cannot
  verify them as tool-generated. An owner-typed
  `armor-similar to <id> (max stat delta 3141592, total 1)` fits the
  family's shape. So no input number, and no reference part other than the
  rewritten id, is ever written:
  - every numeric slot becomes `0`;
  - every reference becomes `[id <short_id(fake)>]`;
  - the only copied slots are fixed words from the closed vocabularies.

  In a retained clause, the only digits are generated ones: fake ids,
  checked by L3/L4, and their 4-digit short ids, re-derived by L9.
  Residual channel, accepted: which vocabulary word was chosen (e.g. one of
  twelve archetypes), a few bits and not identifying.

  Canonical forms are still full clauses to `strip_trailing_tool_clauses`
  (its patterns take `[0-9]+` numbers and a free `[...]` body), so strip
  behaviour, and therefore parity, is unchanged. A test pins this subset
  relation for every family.

  **Non-numeric short-id tokens** (a CodeRabbit round-2 question). `short_id`
  emits letters only for non-decimal ids, and the sanitiser refuses every
  non-decimal export id before parity runs. So every token that `N` or L9
  meets is decimal. A raw Notes token such as `[id …AB12` does not match
  `RAWSID`, so its clause matches no input form and becomes a placeholder
  (fail-closed).

  **Measured in round 2** on the real snapshot, with ids already mapped:
  - all **1,050** real `#vc-` segments match `INPUT_CLAUSE_RES`;
  - after canonicalisation, all 1,050 match `RETAINED_CLAUSE_RES` and are
    accepted by `strip_trailing_tool_clauses`;
  - only the `#vc-test: …` segment becomes a placeholder.

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
   - fullmatch the result against `INPUT_CLAUSE_RES`. If no family matches,
     replace the **whole** body with a placeholder;
   - if a family matches, **re-render** the clause from that family's
     `RETAINED_CLAUSE_RES` form. Closed-vocabulary words and fake ids are
     copied from the match; every `N` and `SCORE` slot is written as `0`;
     every `REF` is written as `[id <short_id(fake)>]`, with the token
     resolved as in the next step and every other reference part dropped
     (`location`, `Tier`, `MW`, `crafted lv`, `power`, `roll`, `spirits`).
     Never copy a numeric or reference payload from the input;
   - assert that the re-rendered clause fullmatches its
     `RETAINED_CLAUSE_RES` pattern;
   - the recogniser `strip_trailing_tool_clauses`
     ([note_history.py:87-104](../src/vault_cleaner/note_history.py#L87-L104))
     must not be used to decide retention: it accepts free text in its
     slots.
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
  - every output Notes segment body, split as above, fullmatches one of
    `RETAINED_CLAUSE_RES` or `PLACEHOLDER_RE`, and the text between
    segments is whitespace only;
  - no output Notes cell or segment body equals any original owner segment
    body.
- **L9, rewritten references:** re-derive each rewritten short-id token
  independently. Do not call the rewriter's helper: resolve the raw token
  against the raw export ids with a separate implementation. Pair raw and
  output tokens by their order within the segment. Every output token must
  equal `short_id(expected)`, where `expected` is the fake of the uniquely
  resolved id, or the fresh fake allocated for that token text.
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
2. Let `N(s)` replace every short-id token with `<SID>`. Use the pattern
   above without the `id ` look-behind, because explanations render
   `copy …1234`
   ([explanation.py:50-56](../src/vault_cleaner/explanation.py#L50-L56)).
   `N` is applied **only** to a decision's appended clause and its
   `explanation` strings. No other snapshot string carries a short id, so no
   other string is normalised.
3. Notes fields, per decision pair (raw `r`, staged `s`, matched by position
   within the section). `S` is `sanitize_notes` with the maps frozen; any new
   placeholder or fresh-fake allocation is a refusal.
   - (a) `s.original_notes == S(r.original_notes)` exactly.
   - (b) Let `base(x) = strip_trailing_tool_clauses(x.original_notes)`. On
     each side, the note must split as `append_tool_clause(x.original_notes,
     clause(x))`, where `clause(x)` is the text after `base(x)`. Require
     `base(s) == S(base(r))`. This catches a clause that `S` replaced but the
     raw run stripped.
   - (c) `N(clause(r)) == N(clause(s))`, and each `explanation` string is
     equal under `N`.
   - (d) **Reference truthfulness**, on both sides independently: every
     short-id token in `clause(x)` and in `x.explanation` must be a truthful
     rendering of `x.kept_id`:
     - the digits before `…` are a prefix of `kept_id`, and the digits after
       it (before any `~`) are a suffix;
     - a `-hhhhhhhh` digest equals the first 8 hex characters of
       `sha256(kept_id)`;
     - an empty `kept_id` admits no token.

     Every production reference renders the `kept_id` row
     ([dupes.py:266-283](../src/vault_cleaner/rules/dupes.py#L266-L283),
     [armor_dupes.py:375-414](../src/vault_cleaner/rules/armor_dupes.py#L375-L414),
     [armor_close.py:196-250](../src/vault_cleaner/rules/armor_close.py#L196-L250),
     [coverage.py:208-294](../src/vault_cleaner/rules/coverage.py#L208-L294)).
     A raw-side violation means that assumption broke: refuse, and treat it
     as a stop condition.
4. Every other field, recursively: on the raw side, a whole-string member of
   `R` becomes its fake, and otherwise every ≥ 16-digit run becomes its fake.
   The field must then equal the staged field exactly. `kept_id`, `id`,
   `group_id`, `preferred_survivor_id`, `selected_partner_id` and `cited_ids`
   are therefore checked through the map.
5. Refuse unless every comparison holds. On refusal, the message gives only
   per-section decision counts and the number of differing decisions.

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

Stdlib-only (`csv`, `io`, `json`, `pathlib`, `re`, `sys`). It holds the
shared grammar above. Signature: `check(root: Path) -> list[str]` (the
errors) and a `main` that runs it on `tests/fixtures/real` relative to the
repository root. It exits 1 and prints the errors if there are any. If the
root does not exist, it passes.

The guard validates every text field the sanitiser rewrites, not only ids. A
fixture with marked ids but raw owner Notes or loadout names must fail
(PR #183 review): the measured owner text contains 8–11-digit runs, which a
digit-run check alone never sees.

- Every file under the root must be `<snapshot>/{weapons,armor,ghosts}.csv`
  or `<snapshot>/provenance.json`, at exactly that depth. Anything else is
  an error (`unexpected file`).
- For each CSV, decoded as strict UTF-8:
  - `Id`, `Notes` and `Loadouts` headers are required;
  - every `Id` cell, with `"` stripped, must fullmatch `FAKE_ID`;
  - every maximal run of ≥ 16 ASCII digits in the file's bytes must start
    with `1000`. This catches a real id inside Notes, or a raw export
    renamed into place;
  - every `Notes` cell, split before each `#vc-`, has whitespace-only text
    between segments, and every stripped non-empty segment fullmatches
    `RETAINED_CLAUSE_RES` or `PLACEHOLDER_RE`;
  - every `Loadouts` cell is empty after `.strip()` or fullmatches
    `LOADOUTS_RE`;
  - if a `Kill Tracker` header exists, every cell is `0`.
- `provenance.json` must parse. Its key set must be exactly `files`,
  `parity_modes`, `run_date` and `script_version`. `files` must name exactly
  the three CSVs, each with exactly `raw_sha256` (64 lowercase hex
  characters) and `rows` (matching the CSV's data-row count).
- Errors name the file, the row number and the rule, never the value.

#### [MODIFY] [ci.yml](../.github/workflows/ci.yml#L19-L25)

Add a hygiene step after "No tracked files under data/":

```yaml
      - name: Real-export fixtures pass the sanitised-fixture guard
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
- **owner text in clause form becomes a placeholder.** Each of these, with a
  mapped id, is replaced wholesale:
  - `#vc-review: armor-similar to <id> (private note)`;
  - `#vc-junk: dupe-lower, kept secret-text`;
  - `#vc-junk: armor-score 1 < floor 2 (best: my secret, rank 1/2 anything)`;
  - `#vc-review: armor-last-archetype (private words), armor-score …`.

  The planning session confirmed that `strip_trailing_tool_clauses` accepts
  every one of them;
- **owner numbers and reference payloads never survive (round 2).** Each
  clause keeps its family but comes out canonical:
  - `#vc-review: armor-similar to <id> (max stat delta 3141592, total 1)`
    becomes `… (max stat delta 0, total 0)`;
  - `#vc-review: coverage-dominated by; compare [id …NNNN]; curated matches
    123456789 vs 1; partner largest coverage gain` becomes `… curated
    matches 0 vs 0 …`;
  - `#vc-junk: armor-score 64.2857 < floor 65 (best: melee_primary, rank
    7/9 titan helmet)` becomes `armor-score 0 < floor 0 (… rank 0/0 …)`;
  - `#vc-junk: dupe-lower; keep [id …1234; my address]; winner lock`
    becomes `keep [id <short_id(fake)>]` with the address dropped.

  Assert that no input digit other than a mapped id's survives;
- a current-format `keep [id …NNNN; location Vault; Tier 5; MW10; roll A /
  B]` resolves to `[id <short_id(fake)>]`, and every other part is dropped.
  An ambiguous token gets a fresh fake with no digest left. A non-numeric
  token (`[id …AB12]`) makes the whole clause a placeholder;
- **grammar coverage and subset:**
  - every one of the 12 clause families has at least one example produced by
    the production emitter. Run the passes on synthetic 19-digit-id copies of
    the existing fixtures (with `wishlist_coverage.txt` for coverage), feed
    each decision's appended clause through `sanitize_notes` as input Notes,
    and assert it is retained, not replaced. Use a handwritten example only
    for a family that no fixture reaches, and name it in the test;
  - every retained (canonical) example matches `RETAINED_CLAUSE_RES` and is
    also accepted by `strip_trailing_tool_clauses`. Both forms of each family
    come from the same template;
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
- `sanitize_notes` keeps a clause-shaped owner note such as
  `armor-similar to <fake> (private note)` (L5 refuses);
- `sanitize_notes` copies numeric payloads instead of canonicalising, for
  example `max stat delta 3141592, total 1` (L5 refuses);
- `sanitize_loadouts` returns the input (L6 refuses);
- Kill Tracker is left unchanged (L7 refuses);
- the short-id rewriter renders a **wrong** fake, a real but different one
  (L9 refuses).

Each refusal test also calls the corresponding check function directly on a
tampered staged table.

**Parity mapping error** (acceptance criterion 3):

- Build a synthetic snapshot in which an id tie-break decides a survivor,
  for example two identical armor pieces decided by "deterministic id
  tie-break" (compare `tests/fixtures/armor_dupes.csv`).
- Monkeypatch the id map to reverse the order. Assert that parity refuses
  and nothing is written.
- Also assert that the same input with the correct map passes.

**Parity wrong reference** (PR #183 review; unit tests of the comparator on
synthetic snapshot pairs):

- the staged appended clause's `[id …NNNN` is changed to another fake's
  suffix;
- the staged `explanation.keep_instead` names `copy …NNNN` for a different
  fake.

Each must refuse under 3(d), although `N` makes the two sides equal under
3(c). A clause that `S` replaced but the raw run stripped must refuse under
3(b).

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
  - with every id marked, each of these fails:
    - raw multi-line owner text in `Notes`;
    - a clause-shaped owner note (`armor-similar to <fake> (private note)`);
    - an owner number in a numeric slot (`armor-similar to <fake> (max stat
      delta 3141592, total 1)`, `curated matches 123456789 vs 1`, and a
      non-zero `armor-score`);
    - a reference with any part besides `id` (`[id …0001; location Vault]`);
    - a raw loadout name in `Loadouts`;
    - a non-zero `Kill Tracker`;
    - a `provenance.json` with an extra key, or a wrong row count;
  - a stray file fails;
  - a missing root passes;
  - the sanitiser uses the guard's grammar objects: the loaded module's
    `INPUT_CLAUSE_RES`, `RETAINED_CLAUSE_RES` and `ID_MARKER` are the
    guard's own objects, not copies.
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
  prefix. CI (`scripts/check_real_fixtures.py`) rejects any fixture whose ids
  lack it, or whose `Notes`, `Loadouts` or `Kill Tracker` cells fall outside
  the sanitised formats.
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
CI also rejects tracked files under `data/`, any file under
`tests/fixtures/real/` that fails the sanitised-fixture guard, whitespace or
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
  is bypassed;
- a real `#vc-` segment other than the `#vc-test: …` one fails
  `INPUT_CLAUSE_RES`, or a production-emitted clause family cannot be
  retained. Do not widen the grammar with a free-text slot, and never let a
  canonical slot accept anything but `0` or the rewritten id;
- parity check 3(d) fails on the **raw** side, which would mean a reference
  does not render its decision's `kept_id`.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Vacuous checks.** A planted-leak or parity test passes even with its
   check disabled, for example because the synthetic input has no id-decided
   tie, or the monkeypatch misses the path actually used. Every such test
   needs bypass evidence.
2. **Over-normalising parity.** A comparator that maps or `<SID>`-normalises
   more than specified, or skips 3(d)'s reference-truthfulness check, would
   hide a real divergence. Examples: dropping `explanation`, comparing only
   decisions, normalising every digit run. `<SID>` alone equates correct and
   wrong references. The comparator must equal the specification above.
3. **Clause retention decided by the recogniser.** Retaining a segment
   because `strip_trailing_tool_clauses` accepts it, or a grammar slot
   loosened to `[^…]+`, lets clause-shaped owner text through. So does
   copying a numeric or reference payload from the input instead of
   re-rendering it canonically. Recognition must be `INPUT_CLAUSE_RES`, and
   output must be the canonical `RETAINED_CLAUSE_RES` form.
4. **Leak in a side channel.** Real ids, Notes text or loadout names printed
   in refusal messages or exceptions; Notes-only ids left unmapped; a
   short-id digest, a numeric payload or a reference part other than `id`
   kept; or `provenance.json`
   carrying more than specified.
5. **CI guard that cannot see the failure.** A guard that validates only
   ids misses raw owner Notes or loadout names while every id is marked. The
   guard needs the Notes, Loadouts, Kill Tracker and provenance rules, the
   byte-level ≥ 16-digit run check, and the file allowlist, using the same
   grammar objects the sanitiser uses.

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
- for every planted-leak, mapping-error and wrong-reference test, show it fails with its check bypassed, then restore;
- recognise clauses with `INPUT_CLAUSE_RES` and write only their canonical `RETAINED_CLAUSE_RES` form (numeric slots `0`, references `[id …NNNN]`), both from `scripts/check_real_fixtures.py`; never decide retention with `strip_trailing_tool_clauses`, and never copy an input number or reference part;
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
adversarial review. This plan also narrows four of the issue's literal checks
on measured grounds and tightens clause retention beyond the issue's wording;
a fresh reviewer should challenge both. The reviewer works on the owner's
machine, where the raw snapshot is in the gitignored `data/`, and must
regenerate the fixtures from it (see checklist).

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] No file under `src/` changed; `RULESET_VERSION` and `SNAPSHOT_SCHEMA_VERSION` unchanged; `git ls-files data/` empty.
- [ ] **Required, no fallback:** the reviewer regenerates the fixtures from the raw snapshot in the owner's gitignored `data/in/2026-09-01T-current/`, after confirming the plan's SHA-256s, running the reviewed head's sanitiser with the committed `--run-date` and both parity modes. The committed files must be byte-identical to the output. If the snapshot is unavailable, the review is incomplete: report it and do not substitute `check_real_fixtures`.
- [ ] `check_real_fixtures` passes on the committed tree and rejects the planted cases (owner Notes, clause-shaped owner note, loadout name, non-zero Kill Tracker, bad provenance, unmarked id), with every id marked.
- [ ] A byte scan of the committed fixtures finds no ≥ 16-digit run without the `1000` marker, no short-id digest (`~…-xxxxxxxx`), no reference part other than `id`, no non-zero numeric slot in a retained clause, no Notes segment outside `RETAINED_CLAUSE_RES`/`PLACEHOLDER_RE`, and no Loadouts cell outside `LOADOUTS_RE`.
- [ ] Column audit allowlists match the measured headers exactly; an unclassified column refuses.
- [ ] Notes-only ids are in the map; short-id rewriting never keeps a digest; L9 re-derives references independently of the rewriter.
- [ ] Clauses are recognised with `INPUT_CLAUSE_RES` and re-rendered canonically: numeric slots `0`, references `[id …NNNN]` only, no payload copied from the input. Both forms come from one set of templates in `check_real_fixtures.py`; no slot admits free text; the 12 families have emitter-driven coverage; the canonical forms are a subset of `strip_trailing_tool_clauses`. The owner-number planted cases fail in both the sanitiser and the guard.
- [ ] L1–L9, P and F exist as specified, and exemptions are exactly "whole fake id" and "whole raw Hash value".
- [ ] The parity comparator matches the specification: whole snapshot, only the three digest/path drops, `N` only on appended clauses and explanations, 3(a)–3(d) all enforced; the wrong-reference tests fail with 3(d) bypassed.
- [ ] Every planted-leak and mapping-error test has bypass evidence.
- [ ] Refusal messages and exceptions print no real ids, Notes text or loadout names.
- [ ] CI hygiene step added; guard is stdlib-only with byte-level run, text-field, provenance and file allowlist checks.
- [ ] `AGENTS.md` edits verbatim; `WORKLOG.md` entry records the measurement, deviations and the `Crafted Level` decision.
- [ ] `ruff`, `pytest`, `git diff --check` pass.

# Dispatch comment draft

Planned #181 in [handoffs/issue-181-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-181-implementation-plan.md) on `main`.

- **Implementer model & effort:** `gpt-5.6-luna` (`high`), Judgement rung (alternative `claude-sonnet-5` `xhigh`)
- **Implementation branch:** `feat/issue-181-sanitised-real-fixtures`
- **Review path:** independent adversarial review, with required regeneration from the raw snapshot
- **Likely findings:** vacuous planted-leak or mapping-error tests; a parity comparator that over-normalises or skips reference truthfulness; clause retention decided by the loose recogniser; side-channel leaks (refusal messages, Notes-only ids, short-id digests); a CI guard that does not validate Notes and Loadouts.
