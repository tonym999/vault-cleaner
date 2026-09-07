# Aggressive weapons-first clear-out — measurement and policy design

## 1. Scope, baseline and reproduction

- **Date:** 2026-09-06 (original measurement and round 1/2 review), corrected 2026-09-07 (round 3 review), corrected again 2026-09-07 (round 4 review)
- **Base SHA:** `9a74192d136242a9820830d4547dd2209db37ca5`
- **Environment:** This document was produced across two machines, and no single "Environment" line covers it honestly. An enumeration mapping sections to machines has now been wrong in three places across two consecutive review rounds (round 3's P3-2, round 4's P3-2), so this document does not attempt one. Nor does every fence state its own machine: the rule instead is **per-capture provenance by materiality** — a fence or its surrounding prose names the producing machine only where the machine materially affects the claim (for example, the C4 `wishlists` capture in §5, whose byte-for-byte reproduction is not required, and the "Measured seam usage" fence in §5, dated 2026-09-06 on both machines). Everywhere else a capture is dated but not machine-labeled; do not infer a machine from a section number or a date alone where the surrounding text does not state one. Session-to-machine provenance for the sessions that produced this document is recorded in `WORKLOG.md`, not repeated per-fence here. Two machines were used:
  - **Windows** (Git Bash, `bash 5.2.26`), Python `3.13.14`, pandas `3.0.5` — the original implementer's session, 2026-09-06.
  - **Linux**, Python `3.14.4`, pandas `3.0.5` — round 2's correction session (2026-09-06), round 3's correction session (2026-09-07), and round 4's correction session (2026-09-07; version re-confirmed with the same `.venv/bin/python -c "import sys, pandas; ..."` command each time).
- **Scope:** This document is an investigative measurement and policy design spike for Issue #142 (part of umbrella Issue #140). It changes no production behaviour: no rule, parser, schema, config, server, UI, `RULESET_VERSION`, or fixture change is introduced by this investigation.
- **Authorized plan deviation (owner directive):** On 2026-09-06, the repository owner explicitly provided a fresh DIM weapon export (`destiny-weapon (12).csv`) and authorized measurement of it within this spike. This supersedes the plan's "specified, not executed" restriction (plan lines 417-419 and 637) and satisfies stop condition S4. What was actually committed from that export is: aggregate counts, and — under a second, explicit owner authorization dated 2026-09-06 — the real item names appearing in two `report` captures in evidence §8. Instance `Id`s, `Hash` values, and raw rows were never authorized for commit and are redacted (see §14 for the full record). Future agents must not reverse either authorization or restore the redacted IDs.

### Evidence rule

> Every **empirical claim** in this document — any statement about the state of this
> repository, its fixtures, or a DIM export — carries one of three citations: the
> exact command run in this session that produced it, a `file:line` reference to the
> source that defines it, or, for an upstream fact, the URL and the date it was
> retrieved. An empirical claim that carries none of those is recorded in section 14
> as `NOT MEASURED`.
>
> This rule does not apply to non-empirical figures: section and issue numbers,
> dates, the 100-space product goal, and other requirements taken from #140 or #142
> cite the issue instead.

### Reproduction commands

All measurements in this document were executed from the repository root on the implementation branch `feat/issue-142-clearout-measurement`. On Windows environments, `export PYTHONUTF8=1` is required to ensure standard I/O streams operate in UTF-8 mode, preventing codepage faults when redirecting characters such as the emoji in `tests/fixtures/weapons_hostile.csv` (see [docs/evidence/issue-142/README.md](evidence/issue-142/README.md)).

```bash
set -euo pipefail
export PYTHONUTF8=1
OUT="$(mktemp -d)"; echo "scratch: $OUT"

.venv/bin/python -c "import sys, pandas; print(sys.version); print(pandas.__version__)" > "$OUT/versions.txt" 2>&1

{ head -1 tests/fixtures/weapons.csv | tr ',' '\n' | nl
  head -1 tests/fixtures/armor.csv   | tr ',' '\n' | nl
  head -1 tests/fixtures/ghosts.csv  | tr ',' '\n' | nl
} > "$OUT/headers.txt" 2>&1

.venv/bin/python - <<'PY' > "$OUT/fixtures.txt" 2>&1
import pandas as pd, glob, os
for path in sorted(glob.glob("tests/fixtures/*.csv")):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    cols = set(df.columns)
    nz = lambda c: int(df[c].str.strip().ne("").sum()) if c in cols else None
    print(os.path.basename(path), "rows=", len(df),
          "| Loadouts nonempty=", nz("Loadouts"),
          "| Equipped=", sorted(set(df["Equipped"])) if "Equipped" in cols else None,
          "| Owner=", sorted(set(df["Owner"])) if "Owner" in cols else None,
          "| Tag=", sorted(set(df["Tag"])) if "Tag" in cols else None)
PY

.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons.csv --armor tests/fixtures/armor.csv --ghosts tests/fixtures/ghosts.csv --no-wishlists > "$OUT/runA.txt" 2>&1
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_dupes.csv --no-wishlists > "$OUT/runB.txt" 2>&1
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_hostile.csv --no-wishlists > "$OUT/runC.txt" 2>&1
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_slammer_like.csv --no-wishlists > "$OUT/runD.txt" 2>&1

.venv/bin/vault-cleaner wishlists > "$OUT/wishlists.txt" 2>&1

ls -1 "$OUT"
```

Verbatim outputs of each capture are archived in [docs/evidence/issue-142/README.md](evidence/issue-142/README.md).

---

## 2. Export schema and completeness by header name

### Required schema sets in `src/vault_cleaner/parse.py`

DIM export validation in `parse.py` enforces four named column sets:

1. **`REQUIRED_BASE_COLUMNS`** ([parse.py:32-34](../src/vault_cleaner/parse.py#L32-L34)):
   `Name`, `Hash`, `Id`, `Tag`, `Rarity`, `Locked`, `Equipped`, `Notes`.
2. **`REQUIRED_WEAPON_COLUMNS`** ([parse.py:42-44](../src/vault_cleaner/parse.py#L42-L44)):
   `REQUIRED_BASE_COLUMNS` + `Type`, `Ammo`, `Crafted`, `Crafted Level`, `Perks 0`.
   **Finding:** `Loadouts` is **not** in `REQUIRED_WEAPON_COLUMNS`.
3. **`REQUIRED_GHOST_COLUMNS`** ([parse.py:47](../src/vault_cleaner/parse.py#L47)):
   `REQUIRED_BASE_COLUMNS` + `Loadouts`.
4. **`REQUIRED_ARMOR_COLUMNS`** ([parse.py:71-76](../src/vault_cleaner/parse.py#L71-L76)):
   `REQUIRED_BASE_COLUMNS` + `Type`, `Equippable`, `Loadouts`, `Tuning Stat`, `Seasonal Mod`, `Holofoil`, `Masterwork Tier`, `Power`, `Tier`, `Perks 0`, `Archetype`, plus the six `ARMOR_STATS` columns (`Weapons (Base)`, `Health (Base)`, `Class (Base)`, `Grenade (Base)`, `Super (Base)`, `Melee (Base)`).

### Measured fixture headers and content

As captured in `headers.txt` and `fixtures.txt` ([docs/evidence/issue-142/README.md](evidence/issue-142/README.md#2-export-headers-by-kind)):

- `tests/fixtures/weapons.csv` has 74 columns, including `Owner` (col 16), `Locked` (17), `Equipped` (18), `Crafted` (48), `Crafted Level` (49), `Kill Tracker` (50), `Loadouts` (52), `Notes` (53), and `Perks 0..20` (54–74).
- `tests/fixtures/armor.csv` has 48 columns, including `Loadouts` (38).
- `tests/fixtures/ghosts.csv` has 24 columns, including `Loadouts` (17), and has no `Type` column.

Cell population across all committed fixtures:

| Fixture | Rows | `Loadouts` non-empty | `Equipped` values | `Owner` values | `Tag` values |
|---|---|---|---|---|---|
| `armor.csv` | 15 | 0 | `['false']` | `['Vault']` | `['', 'keep']` |
| `armor_classes.csv` | 4 | 0 | `['false']` | `['Hunter(550)', 'Titan(550)', 'Vault']` | `['']` |
| `armor_close.csv` | 34 | 0 | `['false', 'true']` | `['Vault']` | `['']` |
| `armor_dupes.csv` | 32 | 2 | `['false', 'true']` | `['Vault']` | `['', 'keep']` |
| `armor_duplicates_ui.csv` | 3 | 0 | `['false', 'true']` | `['Hunter(550)', 'Vault']` | `['', 'keep']` |
| `armor_same_stat_four_ui.csv` | 4 | 1 | `['false']` | `['Titan(415)', 'Vault']` | `['']` |
| `armor_same_stat_ui.csv` | 2 | 0 | `['false']` | `['Vault']` | `['']` |
| `ghosts.csv` | 2 | 0 | `['false', 'true']` | `['Hunter(506)', 'Vault']` | `['', 'favorite']` |
| `ghosts_cleanup.csv` | 7 | 1 | `['false', 'true']` | `['Titan(550)', 'Vault']` | `['', 'favorite', 'keep']` |
| `weapons.csv` | 3 | 0 | `['false', 'true']` | `['Titan', 'Vault']` | `['', 'favorite', 'keep']` |
| `weapons_dupes.csv` | 18 | 0 | `['false', 'true']` | `['Vault']` | `['', 'keep']` |
| `weapons_hostile.csv` | 10 | 0 | `['false']` | `['Vault']` | `['']` |
| `weapons_slammer_like.csv` | 5 | 0 | `['false']` | `['Vault']` | `['']` |

### Core schema findings

1. **Weapon `Loadouts` coverage gap:** Across all 36 weapon rows in all 4 weapon fixtures (`weapons.csv`, `weapons_dupes.csv`, `weapons_hostile.csv`, `weapons_slammer_like.csv`), **zero** non-empty `Loadouts` cells exist. Because `Loadouts` is not in `REQUIRED_WEAPON_COLUMNS`, an export that dropped `Loadouts` entirely would load silently without triggering schema validation.
2. **Three distinct `Loadouts` states:**
   - **Column missing:** Incomplete export schema. The protection input is absent. Must not default to "not in a loadout". Child 2a must add `"Loadouts"` to `REQUIRED_WEAPON_COLUMNS` in `parse.py` so incomplete weapon exports fail loudly.
   - **Cell empty on a row:** The normal measured state for items not saved to any loadout ([ghosts.py:36](../src/vault_cleaner/rules/ghosts.py#L36), [armor_dupes.py:99-100](../src/vault_cleaner/rules/armor_dupes.py#L99-L100)). Treated as unprotected by this dimension.
   - **Column present but empty on every row:** Ambiguous state (either the player has saved no DIM loadouts, or DIM export formatting changed). Must be detected and surfaced in the report summary as an explicit advisory notice.
3. **`Owner` contract and lack of semantic parsing:**
   `Owner` exhibits three observed shapes in DIM exports:
   - The literal `Vault` sentinel: item resides in the vault.
   - Bare class name: e.g. `Titan` (observed in `weapons.csv`).
   - Class with power level: e.g. `Titan(451)`, `Titan(550)`, `Hunter(506)` (observed in armor/ghost fixtures and real exports).

   A comprehensive search for `"Owner"` across `src/vault_cleaner` yields exactly **13 reads** ([docs/evidence/issue-142/README.md](evidence/issue-142/README.md#4-semantic-owner-reads-in-codebase)): 10 `Decision.location` assignments, 2 display reads through `safe_fragment` ([duplicate_reference.py:184,212](../src/vault_cleaner/duplicate_reference.py#L184)), and 1 CLI dry-run print ([cli.py:151](../src/vault_cleaner/cli.py#L151)). **`Owner` is not semantically parsed anywhere**: no function parses `Owner` to derive residency, character class, or power level. Child 6 must define and implement this derivation before capacity accounting can rely on it.
4. **No export column reports vault capacity or free space:** DIM CSV exports do not report total vault capacity (e.g. 700 spaces) or current free spaces (`F`). `F` is inherently an external input.

### Protection dimension comparison

| Dimension | Measured Export Indicator | Current Rail Precedence | Aggressive Policy Treatment |
|---|---|---|---|
| **Equipped state** | `Equipped == 'true'` | HARD rail (`equipped`) | Retained; hard rail preserved |
| **Character location** | `Owner != 'Vault'` | Unprotected (location recorded only) | Does not imply protection; items on characters may be proposed for removal |
| **Saved-loadout membership** | `Loadouts.str.strip() != ''` | Unprotected for weapons; read only for ghosts/armor dupes | **HARD rail** in aggressive policy (settled decision; Child 2a) |
| **DIM protective tags** | `Tag in {'favorite', 'keep', 'archive'}` | HARD rail (`dim-tag:{tag}`, [rails.py:45](../src/vault_cleaner/rules/rails.py#L45)) | Retained; hard rail preserved |
| **Crafted protection** | `Crafted == 'crafted'` | HARD if empty level (`crafted-lvunknown`) or level ≥ 10 (`crafted-lv{level}`, [rails.py:51](../src/vault_cleaner/rules/rails.py#L51)) | Retained; hard rail preserved |
| **Locked state** | `Locked == 'true'` | SOFT rail (`locked` -> review-only) | Retained as soft rail; flagged for review, never auto-junked |
| **Exotic state** | `Rarity == 'Exotic'` | SOFT rail (`exotic` -> review-only) | Retained as soft rail; flagged for review, never auto-junked |
| **Durable veto** | `Id in OverrideStore.vetoes` (`data/overrides.json`) | Excluded from CSV in `apply_vetoes` | Retained; vetoes suppress export unless stale or re-reviewed |

### Identifier handling and types

- **`Id`:** Opaque string end-to-end. Handled as a string in `parse.py`, stored as string in `Decision.id`, formatted with surrounding triple-quotes on export ([report.py:100](../src/vault_cleaner/report.py#L100)), and ordered lexically by `id_order.instance_id_order` without numeric conversion.
- **`Hash`:** String in DataFrame representation, dupe grouping ([dupes.py:100,216](../src/vault_cleaner/rules/dupes.py#L100)), and `Decision.hash`. Converted to `int` specifically at the wishlist boundary ([weapons.py:72](../src/vault_cleaner/rules/weapons.py#L72)) because `Wishlist.keep` and `Wishlist.trash` maps are int-keyed ([wishlist.py:79](../src/vault_cleaner/wishlist.py#L79)). `AGENTS.md`'s rule ("keep Id/Hash opaque strings") governs untrusted input (review manifests and `data/overrides.json`), not internal wishlist lookup.

---

## 3. Current weapon rules, rails and review behaviour

### Rail precedence order in `rules/rails.py`

In `src/vault_cleaner/rules/rails.py:30-56`, `protection(row, crafted_level_protect: int) -> tuple[str | None, str]` evaluates in strict sequence, returning `(HARD|SOFT|None, reason)`:

1. `Tag in HARD_PROTECT_TAGS` (`favorite`, `keep`, `archive`): `(HARD, f"dim-tag:{tag}")` ([rails.py:44-45](../src/vault_cleaner/rules/rails.py#L44-L45))
2. `is_true(Equipped)`: `(HARD, "equipped")` ([rails.py:46-47](../src/vault_cleaner/rules/rails.py#L46-L47))
3. `Crafted == 'crafted'` and `Crafted Level == ''`: `(HARD, "crafted-lvunknown")` ([rails.py:48-49](../src/vault_cleaner/rules/rails.py#L48-L49))
4. `Crafted == 'crafted'` and `int(Crafted Level) >= crafted_level_protect` (default 10): `(HARD, f"crafted-lv{level}")` ([rails.py:50-51](../src/vault_cleaner/rules/rails.py#L50-L51))
5. `Rarity == 'Exotic'`: `(SOFT, "exotic")` ([rails.py:52-53](../src/vault_cleaner/rules/rails.py#L52-L53))
6. `is_true(Locked)`: `(SOFT, "locked")` ([rails.py:54-55](../src/vault_cleaner/rules/rails.py#L54-L55))
7. Default: `(None, "")` ([rails.py:56](../src/vault_cleaner/rules/rails.py#L56))

**Loadouts gap:** There is no weapon loadout rail. Only `ghosts.py:36` and `armor_dupes.py:99-100` check `Loadouts`. `report_run.py:317` records `in_loadout` strictly for UI presentation.

### Weapons pass execution order

In `src/vault_cleaner/rules/weapons.py:59-111`:

1. **Wishlist evaluation and selective rails check:**
   - In `weapons.run` ([weapons.py:71-84](../src/vault_cleaner/rules/weapons.py#L71-L84)), each weapon row is checked against `wishlist.trash` (`whole-item` or `roll` match).
   - If a row does not match trash, `rails.protection` is **not** evaluated in this pass; the row continues to the duplicate candidate pool.
   - If a row matches `wishlist.trash` and also matches `wishlist.keep`, **keep beats trash**: the trash decision is suppressed, and `keep_trash_conflicts` is incremented ([weapons.py:79-81](../src/vault_cleaner/rules/weapons.py#L79-L81)).
   - Only for rows matching unsuppressed trash is `rails.protection(row, crafted_level_protect)` evaluated ([weapons.py:82-90](../src/vault_cleaner/rules/weapons.py#L82-L90)):
     - Hard-protected rows are skipped (`continue`).
     - Soft-protected rows emit `review` with hashtag `#vc-review: wishlist-trash {kind} ({reason})`.
     - Unprotected rows emit `junk` with hashtag `#vc-junk: wishlist-trash {kind}`.
   - Rows junked by wishlist trash are recorded and their IDs are removed from the exact-dupe candidate pool ([weapons.py:102-107](../src/vault_cleaner/rules/weapons.py#L102-L107)).
2. **Exact-duplicate pass:**
   - Remaining candidates are grouped by `Hash` + normalized perks prefix ([dupes.py:100-177](../src/vault_cleaner/rules/dupes.py#L100-L177)).
   - Exact duplicates are ranked by #31's landed guarantees: `Tier` desc, `Masterwork Tier` desc, `Crafted Level` desc, then stat total desc, using `RANK_COLUMNS` plus `STAT_COLUMNS` ([dupes.py:42-51](../src/vault_cleaner/rules/dupes.py#L42-L51)). Among rows sharing the best rank, the survivor is chosen by `min(..., key=instance_id_order)` — the **lowest** opaque instance `Id` wins the tie, not the highest ([dupes.py:225-228](../src/vault_cleaner/rules/dupes.py#L225-L228)).
   - Winner is retained; lower copies are evaluated against `rails.protection` separately in `dupes.resolve`: lower copies marked junk (or review if soft rail applies). Ties use the same lowest-`Id`-wins deterministic tie-break.
   - Any row lacking a measured tracker boundary or complete prefix fails safe as ungroupable ([dupes.py:126-177](../src/vault_cleaner/rules/dupes.py#L126-L177)).

### Verified baseline captures on committed fake fixtures

Run A (`report` on `weapons.csv`, `armor.csv`, `ghosts.csv` with `--no-wishlists`):
```text
would junk 1 item(s) and flag 5 for review

JUNK ghost-unprotected-surplus (ghosts) — 1 item(s)
  Fake Shell (id 2000000000000000001, class ghosts; location Vault)

REVIEW armor-similar to (armor) — 3 item(s)
  Guard Plate A (id 4051, class Titan; location Vault) — review: armor-similar to; compare [id 4052; location Vault]; max stat delta 1, total 2; partner deterministic id tie-break; Candidate Tuning Mod Slot: none/unknown; Partner Tuning Mod Slot: none/unknown
  Guard Plate B (id 4052, class Titan; location Vault) — review: armor-similar to; compare [id 4051; location Vault]; max stat delta 1, total 2; partner deterministic id tie-break; Candidate Tuning Mod Slot: none/unknown; Partner Tuning Mod Slot: none/unknown
  Guard Plate C (id 4053, class Titan; location Vault) — review: armor-similar to; compare [id 4051; location Vault]; max stat delta 1, total 2; partner deterministic id tie-break; Candidate Tuning Mod Slot: none/unknown; Partner Tuning Mod Slot: none/unknown

REVIEW armor-last-archetype (armor) — 1 item(s)
  Bad Plate (id 4005, class Titan; location Vault)

REVIEW armor-score (armor) — 1 item(s)
  Bad Locked Plate (id 4006, class Titan; location Vault)

dry run — pass --write to write the combined import CSV
```

Run B (`report` on `weapons_dupes.csv` with `--no-wishlists`):
```text
skipping armor: data\in\destiny-armor.csv not found; expected destiny-armor.csv or a browser-numbered copy such as destiny-armor (1).csv
skipping ghosts: data\in\destiny-ghost.csv not found; expected destiny-ghost.csv or a browser-numbered copy such as destiny-ghost (1).csv
would junk 4 item(s) and flag 3 for review

JUNK dupe-lower (weapons) — 3 item(s)
  Dupe Rifle (id 3002, class weapons; location Vault) — junk: dupe-lower; keep [id 3001; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  Crafted Pulse (id 3022, class weapons; location Vault) — junk: dupe-lower; keep [id 3020; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  Tiered Sidearm (id 3032, class weapons; location Vault) — junk: dupe-lower; keep [id 3031; location Vault; Tier 5; MW0; roll Mag B / Trait A]; winner higher Tier

JUNK dupe-tie (weapons) — 1 item(s)
  Twin SMG (id 3042, class weapons; location Vault) — junk: dupe-tie; keep [id 3041; location Vault; Tier 5; MW0; roll Mag B / Trait A]; winner deterministic id tie-break

REVIEW dupe-lower (weapons) — 2 item(s)
  Dupe Rifle (id 3003, class weapons; location Vault) — review: dupe-lower (locked); keep [id 3001; location Vault; Tier 5; MW10; roll Mag B / Trait A]; winner higher Masterwork Tier
  Fake Exotic HC (id 3012, class weapons; location Vault) — review: dupe-lower (exotic); keep [id 3011; location Vault; Tier 5; MW8; roll Mag Exotic B / Trait Exotic]; winner higher Masterwork Tier

REVIEW dupe-tie (weapons) — 1 item(s)
  Tied Exotic GL (id 3052, class weapons; location Vault) — review: dupe-tie (exotic); keep [id 3051; location Vault; Tier 5; MW0; roll Mag Exotic B / Trait Exotic]; winner deterministic id tie-break

dry run — pass --write to write the combined import CSV
```

### Current finalization seam

The authoritative finalization seam is `review.apply_vetoes` ([review.py:546](../src/vault_cleaner/review.py#L546)) feeding `report.render_import_csv` ([report.py:83-102](../src/vault_cleaner/report.py#L83-L102)). It has two sibling call sites:
1. Server finalization: [server/app.py:790-792](../src/vault_cleaner/server/app.py#L790-L792)
2. CLI review: [cli.py:484](../src/vault_cleaner/cli.py#L484)

`apply_vetoes` is currently **subtractive**: it subtracts vetoed IDs from the pipeline's proposal set, meaning all unreviewed proposals are included in the generated import CSV.

---

## 4. Proposal-strength taxonomy

To prevent premature automatic dismantling while enabling high-confidence clear-outs, proposals are classified into four mutually exclusive categories:

| Strength Class | Definition | Rules Producing It | Emit Action | Output Inclusion |
|---|---|---|---|---|
| **Automatic junk candidate** | Deterministic evidence of inferiority with zero soft-rail impediment | `wishlist-trash whole-item`, `wishlist-trash roll`, `dupe-lower`, `dupe-tie` on unprotected items | `junk` | Proposed for junk; included in CSV under current subtractive seam, but requires explicit approval under Child 2b approval-only seam |
| **Review-only comparison** | Proposal backed by evidence but restricted by a soft rail (locked/exotic) or pairwise coverage trade-off | `#vc-review: wishlist-trash whole-item (locked)`, `#vc-review: wishlist-trash whole-item (exotic)`, `#vc-review: dupe-lower (locked)`, `#vc-review: dupe-lower (exotic)`, `#vc-review: dupe-tie (exotic)`, future useful-combination dominance (#34) | `review` | Displayed in review UI; excluded from CSV unless user explicitly approves |
| **Protected / retained** | Hard-protected by player directive, system state, or dupe winner | Hard rails (`dim-tag:{tag}`, `equipped`, `crafted-lv{level}`, `crafted-lvunknown`) — current behaviour; plus `loadout-protected`, a **Child 2a settled decision, not yet implemented** (`grep -rn "loadout-protected" src/ tests/` returns nothing today; see §2 and §8) — and dupe survivor / winner | `keep` | Never proposed for junk; excluded from CSV |
| **Unknown or uncovered** | No wishlist match, ungroupable perks, or unique roll without comparable duplicate | Unmatched rolls, ungroupable exact-dupe rows, lone rolls | None | Retained. **Explicit invariant:** absence of wishlist coverage or inability to determine roll identity is **never** evidence of junk. |

---

## 5. Wishlist source and evidence evaluation

### Candidate evaluation matrix

Evaluation conducted on 2026-09-06 (see upstream repository metadata and API query evidence in [docs/evidence/issue-142/README.md](evidence/issue-142/README.md#9-upstream-wishlist-repository-metadata)):

| Candidate | Upstream Curation Family | Activity Scope | Roll / Hash Coverage | Tier & Quality Metadata | Notes & Attribution | Freshness / Check Date | Base/Enhanced Normalization |
|---|---|---|---|---|---|---|---|
| **Choosy Voltron** (configured, `choosy_voltron`) | Multi-curator community — curator names measured present in the cached file (see below) | Broad PvE & PvP across all Destiny history | 255,373 keep rolls across 1,234 items; 53 trash entries across 53 items ([evidence §7](evidence/issue-142/README.md#7-wishlists-command-output-and-local-cache-state), re-verified 2026-09-06) | None (binary keep/trash) | Mixed loss: ~1% of `dimwishlist:` lines carry an inline `#notes:` tail discarded at `LINE_RE` (`wishlist.py:29`); the remainder of its notes are standalone `//notes:` lines discarded at `wishlist.py:73-74`, same as the two Aegis sources — see the measured seam table above | [`2026-08-03T22:53:37Z`](https://github.com/48klocs/dim-wish-list-sources) upstream (retrieved 2026-09-06); local cache `2026-09-06` (evidence §7) | Hash-based; enhanced perk hashes listed explicitly |
| **Ciceron Aegis Lists** (configured, `aegis_trash`; repo also hosts unconfigured sibling files evaluated below) | Aegis PvE Endgame Analysis (mechanical conversion) | PvE Endgame (GM, Master Raids, Dungeons) | Configured `aegis_trash` source: 0 keep rolls; 286 trash entries across 286 items (evidence §7). Sibling repo files (not configured): `dim_aegis_endgame.txt` ("Full", A+S tier) and `dim_aegis_endgame-exclusive.txt` ("Exclusive", S tier only) per the repo README's own quick-start descriptions (measured 2026-09-06, below) | "Full" = A & S tier; "Exclusive" = S tier only, per upstream README wording (not a vault-cleaner-parsed field) | 0 of 286 `dimwishlist:` lines in the configured file carry a `#notes:` tail; 156 are standalone `//notes:` lines discarded at `wishlist.py:73-74`, **not** `LINE_RE` | [`2026-08-27T20:25:09Z`](https://github.com/Ciceron14/dim-extra-wishlists) upstream (retrieved 2026-09-06); local cache `2026-09-06` (evidence §7) | `_major-perks` sibling files filter out Barrels and Mags per the README's "Barrels and Mags" section (measured 2026-09-06, below); the specific sibling filename `dim_aegis_endgame_major-perks.txt` is confirmed to exist in the repository tree by the `gh api .../git/trees` fence following the README excerpt below, not by the README prose itself |
| **MrCharles Configurable Aegis** (evaluated only; **not** a configured source) | Aegis PvE Endgame Analysis (mechanical conversion) | PvE Endgame | Not loaded by `vault-cleaner` — no `[wishlists.sources]` entry. Repository structure measured via `gh api .../git/trees` (below): 28 files = 7 rank codes (`MRA`, `MRB`, `MRC`, `MRD`, `MRE`, `MRF`, `MRS`) × 4 perk-count codes (`PPC0`..`PPC3`); sizes 443,282 to 36,724,539 bytes | Rank encoded in filename only (`MRx`); per-entry tier/rank text inside the files is **NOT MEASURED** — files were never fetched (§14 item 2) | **NOT MEASURED** — content was never fetched in any session, so no discard-seam claim can be made for this unconfigured source | [`2026-08-15T00:45:01Z`](https://github.com/charlesxcaliber/DIMAegisWeaponWishlist) upstream (retrieved 2026-09-06) | **NOT MEASURED** — no file content inspected |
| **Nitaraku Aegis List** (configured, `aegis`) | Aegis PvE Endgame Analysis (mechanical conversion) | PvE Endgame | 5,022 keep rolls across 968 items; 0 trash entries (evidence §7, re-verified 2026-09-06) | Explicit Tier/Rank in standalone `//notes:[Tier: S, Rank: 1]`-style lines | 0 of 5,022 `dimwishlist:` lines carry a `#notes:` tail; 740 are standalone `//notes:` lines discarded at `wishlist.py:73-74`, **not** `LINE_RE` | [`2026-07-04T08:37:05Z`](https://github.com/Nitaraku/dim-wishlists) upstream (retrieved 2026-09-06); local cache `2026-09-06` (evidence §7) | The cached file's own header states "Uses only Trait 1 and Trait 2 columns" (measured directly from the file, below) |

### Measured source detail (2026-09-06)

**Curator names and rail cache freshness** — `wishlists/` is the gitignored local cache; this session's `ls -l wishlists/` (evidence §7) shows all three configured sources with mtime `Sep 6 14:23`, hours before this evidence was committed later the same session. Evidence §7 states the basis precisely, and it is restated here rather than re-derived: had this capture's single `vault-cleaner wishlists` invocation downloaded fresh content for any of the three sources, that source's file would carry a write time at or after the moment the command ran, not an already-hours-old timestamp — and the absence of a `warning: ... download failed` line alone does **not** distinguish a cache hit from a successful download, since `wishlist.py:152` prints that warning only when a download fails. The already-hours-old, unmodified mtime is therefore the basis for concluding all three sources were **served from cache**, not freshly downloaded, in this session — not a separate before/after `ls -la` comparison, which was never run.

```bash
set -euo pipefail
OUT="$(mktemp -d)"
{
  echo "=== curator name mentions in choosy_voltron.txt (case-insensitive) ==="
  grep -o -i "pandapaxxy" wishlists/choosy_voltron.txt | wc -l
  grep -o -i "mercules" wishlists/choosy_voltron.txt | wc -l
} > "$OUT/p2-8_curator_counts.txt" 2>&1
cat "$OUT/p2-8_curator_counts.txt"
```

`$OUT/p2-8_curator_counts.txt`:

```text
=== curator name mentions in choosy_voltron.txt (case-insensitive) ===
3883
253
```

**Nitaraku's own file header** confirms the "traits 1 & 2 only" scope directly, rather than by inference:

```bash
set -euo pipefail
OUT="$(mktemp -d)"
head -2 wishlists/aegis.txt > "$OUT/p2-8_nitaraku_header.txt" 2>&1
cat "$OUT/p2-8_nitaraku_header.txt"
```

`$OUT/p2-8_nitaraku_header.txt`:

```text
title:Aegis PvE Endgame Wishlist: All Tiers | Only Traits v26.7.4.1
description:Automatically generated DIM wishlist based on the Aegis PvE Tierlist for all Tiers. Uses only Trait 1 and Trait 2 columns.
```

**MrCharles repository structure** (evaluated only; this source is not configured):

```bash
set -euo pipefail
OUT="$(mktemp -d)"
gh api "repos/charlesxcaliber/DIMAegisWeaponWishlist/git/trees/main?recursive=1" --jq '.tree[] | select(.type=="blob") | "\(.path) \(.size)"' > "$OUT/mrcharles_tree.txt" 2>&1
cat "$OUT/mrcharles_tree.txt"
```

`$OUT/mrcharles_tree.txt` (28 wishlist files; sizes in bytes; `README.md` excluded from the 28 count):

```text
MrCharlesWishlist_MRA_PPC0.txt 23392051
MrCharlesWishlist_MRA_PPC1.txt 17216708
MrCharlesWishlist_MRA_PPC2.txt 5853045
MrCharlesWishlist_MRA_PPC3.txt 1129700
MrCharlesWishlist_MRB_PPC0.txt 31746899
MrCharlesWishlist_MRB_PPC1.txt 23240534
MrCharlesWishlist_MRB_PPC2.txt 7832479
MrCharlesWishlist_MRB_PPC3.txt 1604394
MrCharlesWishlist_MRC_PPC0.txt 34887457
MrCharlesWishlist_MRC_PPC1.txt 25176633
MrCharlesWishlist_MRC_PPC2.txt 8481476
MrCharlesWishlist_MRC_PPC3.txt 1933831
MrCharlesWishlist_MRD_PPC0.txt 36358170
MrCharlesWishlist_MRD_PPC1.txt 26006846
MrCharlesWishlist_MRD_PPC2.txt 8762065
MrCharlesWishlist_MRD_PPC3.txt 2131892
MrCharlesWishlist_MRE_PPC0.txt 36703022
MrCharlesWishlist_MRE_PPC1.txt 26203770
MrCharlesWishlist_MRE_PPC2.txt 8846983
MrCharlesWishlist_MRE_PPC3.txt 2182960
MrCharlesWishlist_MRF_PPC0.txt 36724539
MrCharlesWishlist_MRF_PPC1.txt 26214742
MrCharlesWishlist_MRF_PPC2.txt 8851303
MrCharlesWishlist_MRF_PPC3.txt 2187280
MrCharlesWishlist_MRS_PPC0.txt 11292682
MrCharlesWishlist_MRS_PPC1.txt 8573418
MrCharlesWishlist_MRS_PPC2.txt 2916327
MrCharlesWishlist_MRS_PPC3.txt 443282
README.md 1799
```

Smallest file `MrCharlesWishlist_MRS_PPC3.txt` is 443,282 bytes (≈443KB decimal); largest `MrCharlesWishlist_MRF_PPC0.txt` is 36,724,539 bytes (≈36.7MB decimal) — 28 files total, confirming the file-count and size-range claim with this session's own query rather than round 1's uncited figure.

**Ciceron's repository README** confirms the Full/Exclusive tier structure and the major-perks Barrels-and-Mags filter directly from upstream documentation:

```bash
set -euo pipefail
OUT="$(mktemp -d)"
gh api "repos/Ciceron14/dim-extra-wishlists/readme" --jq '.content' > "$OUT/raw_b64.txt" 2>&1
base64 -d "$OUT/raw_b64.txt" > "$OUT/ciceron_readme.txt" 2>&1
grep -n -A5 "^### Everything Good\|^### Only The Greats\|^## Barrels and Mags" "$OUT/ciceron_readme.txt" > "$OUT/ciceron_readme_excerpt.txt" 2>&1
cat "$OUT/ciceron_readme_excerpt.txt"
```

`$OUT/ciceron_readme_excerpt.txt`:

```text
20:### Everything Good
21-_A & S Tier Endgame Weapons + Endgame Shopping List_
22-
23-```
24-https://raw.githubusercontent.com/Ciceron14/dim-extra-wishlists/main/Aegis%20Spreadsheets%20Wishlists/Aegis%20Endgame%20Analysis/Shopping%20List/dim_aegis_endgame-shopping_list.txt|https://raw.githubusercontent.com/Ciceron14/dim-extra-wishlists/main/Aegis%20Spreadsheets%20Wishlists/Aegis%20Endgame%20Analysis/dim_aegis_endgame.txt
25-```
--
30:### Only The Greats
31-_S Tier Endgame Weapons + Endgame Shopping List_
32-```
33-https://raw.githubusercontent.com/Ciceron14/dim-extra-wishlists/main/Aegis%20Spreadsheets%20Wishlists/Aegis%20Endgame%20Analysis/Shopping%20List/dim_aegis_endgame-shopping_list.txt|https://raw.githubusercontent.com/Ciceron14/dim-extra-wishlists/main/Aegis%20Spreadsheets%20Wishlists/Aegis%20Endgame%20Analysis/dim_aegis_endgame-exclusive.txt
34-```
35-> Or, ignore Barrels and Mags for less grind:
--
75:## Barrels and Mags
76-If you are looking for less grindy wishlists, you can replace any of them with their "Major Perks" version. You can find them in the folders next to the standard ones.
77-Note that Endgame Shopping List does not list Barrels and Mags in the sheet so this one is always Major Perks only.
```

"Everything Good" bundles `dim_aegis_endgame.txt` (the "Full" list, line 24's raw URL) and is described as A & S tier; "Only The Greats" bundles `dim_aegis_endgame-exclusive.txt` (the "Exclusive" list, line 33's raw URL) and is described as S tier only. Widened from round 2's `-A1` to `-A5` specifically so the excerpt itself carries the raw URLs naming both files, rather than requiring the reader to trust the surrounding prose — this fence is now self-supporting for the claim it backs.

The README excerpt above names the "Major Perks" variant only in prose ("you can replace any of them with their 'Major Perks' version"), never the literal filename this document cites elsewhere (`dim_aegis_endgame_major-perks.txt`). That filename is confirmed directly, not inferred from the prose:

```bash
set -euo pipefail
OUT="$(mktemp -d)"
gh api "repos/Ciceron14/dim-extra-wishlists/git/trees/main?recursive=1" --jq '.tree[] | select(.path=="Aegis Spreadsheets Wishlists/Aegis Endgame Analysis/dim_aegis_endgame_major-perks.txt") | "\(.path) \(.size)"' > "$OUT/p3-5_major_perks_path.txt" 2>&1
cat "$OUT/p3-5_major_perks_path.txt"
```

`$OUT/p3-5_major_perks_path.txt`:

```text
Aegis Spreadsheets Wishlists/Aegis Endgame Analysis/dim_aegis_endgame_major-perks.txt 177699
```

Confirms the exact path and that the file exists in the repository tree (177,699 bytes), sibling to `dim_aegis_endgame.txt` in the same directory — this is the citation for the filename named in §6's recommendation, rather than "§5's widened fence" (the `-A5` README excerpt), which only supports the general "Major Perks" concept, not this specific filename.

### Parser facts and data loss in current code

**Two distinct discard seams exist, and the two Aegis sources actually configured in `config.toml` never reach the one round 1 originally named.**

- **Standalone `//notes:` block lines are discarded before `LINE_RE` is ever reached.** `parse_wishlist` ([wishlist.py:69-74](../src/vault_cleaner/wishlist.py#L69-L74)) skips any line that does not start with `dimwishlist:` — `if not line.startswith("dimwishlist:"): continue  # titles, comments, prose — not ours to police`. Both configured Aegis sources (`aegis` = Nitaraku, `aegis_trash` = Ciceron) carry their tier/attribution text as **standalone `//notes:` comment lines preceding a block of `dimwishlist:` lines**, not as a `#notes:` tail on the `dimwishlist:` line itself. For those two sources, the loss happens at `wishlist.py:73-74`, and `LINE_RE`'s `(?:#.*)?` tail group is never reached.
- **`LINE_RE`'s `(?:#.*)?` tail group discards a `#notes:` suffix when a `dimwishlist:` line carries one.** `LINE_RE = re.compile(r"^dimwishlist:item=(-?\d{1,10})(?:&perks=([\d,]*))?(?:#.*)?$")` ([wishlist.py:29](../src/vault_cleaner/wishlist.py#L29)). This seam is real, but measured against the local cache it applies **only to Choosy Voltron** among the three configured sources — see the measured table below.
- **Source loss at `merge`:** `Wishlist.merge` ([wishlist.py:51-57](../src/vault_cleaner/wishlist.py#L51-L57)) merges all rolls into unified `keep` and `trash` dictionaries. Once merged, the engine cannot determine whether a roll came from Choosy Voltron or Aegis.

**Measured seam usage per configured source** (cached copies in `wishlists/`, measured 2026-09-06 on round 2's Linux correction session — the same calendar date as the original Windows session, but a different machine and a different cache fetch; see §1's per-capture provenance rule):

```bash
set -euo pipefail
OUT="$(mktemp -d)"
{
  for f in aegis.txt aegis_trash.txt choosy_voltron.txt; do
    total=$(grep -c "^dimwishlist:" "wishlists/$f" || true)
    hash_notes=$(grep "^dimwishlist:" "wishlists/$f" | grep -c "#notes:" || true)
    slash_notes=$(grep -c "^//notes:" "wishlists/$f" || true)
    echo "$f: dimwishlist_lines=$total hash_notes_tail=$hash_notes standalone_slash_notes=$slash_notes"
  done
} > "$OUT/p1-1_seam_counts.txt" 2>&1
cat "$OUT/p1-1_seam_counts.txt"
```

`$OUT/p1-1_seam_counts.txt`:

```text
aegis.txt: dimwishlist_lines=5022 hash_notes_tail=0 standalone_slash_notes=740
aegis_trash.txt: dimwishlist_lines=286 hash_notes_tail=0 standalone_slash_notes=156
choosy_voltron.txt: dimwishlist_lines=255426 hash_notes_tail=2726 standalone_slash_notes=8628
```

| Source | `dimwishlist:` lines | `#notes:` tail (`LINE_RE`, `wishlist.py:29`) | standalone `//notes:` lines (`wishlist.py:73-74`) |
|---|---|---|---|
| `aegis.txt` (Nitaraku) | 5,022 | **0** | 740 |
| `aegis_trash.txt` (Ciceron) | 286 | **0** | 156 |
| `choosy_voltron.txt` | 255,426 | 2,726 (~1%) | 8,628 |

Both Aegis sources carry **zero** `#notes:` tails on their `dimwishlist:` lines; their tier/attribution text is entirely in standalone `//notes:` block lines, discarded at `wishlist.py:73-74` before `LINE_RE` ever runs. Only Choosy Voltron's minority `#notes:` tail (~1% of its lines) reaches `LINE_RE`'s discard group. A Child 3 implementer who targets only `LINE_RE` would recover zero notes from either Aegis source. This is the measured justification for #140 Child 3, and Child 3 must address both discard seams, not only `LINE_RE`.

### Malformed/skipped counts, and conflict behaviour (measured 2026-09-07)

`Wishlist.skipped` and `Wishlist.wildcards` ([wishlist.py:44-45](../src/vault_cleaner/wishlist.py#L44-L45)) count, per source, malformed `dimwishlist:` lines and wildcard-item (`69420`) entries respectively. `vault-cleaner wishlists` prints them per source:

```bash
set -euo pipefail
OUT="$(mktemp -d)"
.venv/bin/vault-cleaner wishlists > "$OUT/p2-1_wishlists.txt" 2>&1
cat "$OUT/p2-1_wishlists.txt"
```

`$OUT/p2-1_wishlists.txt`:

```text
choosy_voltron: 255373 keep rolls across 1234 items, 53 trash entries across 53 items
aegis: 5022 keep rolls across 968 items, 0 trash entries across 0 items
aegis_trash: 0 keep rolls across 0 items, 286 trash entries across 286 items
total: 260395 keep rolls, 339 trash entries
```

None of the three lines carries a parenthesized suffix. `cli.py:560-565` appends `"{N} malformed lines skipped"` and `"{N} wildcard entries ignored"` clauses to a source's line **only when the corresponding count is non-zero** (`if wl.skipped: ...` / `if wl.wildcards: ...`); a zero count produces no suffix at all, not a printed `0`. The table below therefore states skipped/wildcard counts of zero as an **inference from the absence of that suffix**, cited to the `cli.py:560-565` derivation — not as a value any command printed directly:

This subsection's own `vault-cleaner wishlists` invocation is the plan's one environment-dependent C4 capture (§1's per-capture provenance rule), and it needs its own cache-state record rather than relying on evidence §7's, which was captured a day earlier. This run also served all three sources from cache: the `wishlists/` mtimes checked immediately afterward are unchanged, byte-for-byte, from evidence §7's `Sep 6 14:23` record —

```bash
set -euo pipefail
OUT="$(mktemp -d)"
ls -l wishlists/ > "$OUT/p3-6_wishlists_ls.txt" 2>&1
cat "$OUT/p3-6_wishlists_ls.txt"
```

`$OUT/p3-6_wishlists_ls.txt`:

```text
total 26472
-rw-rw-r-- 1 raver raver   346965 Sep  6 14:23 aegis.txt
-rw-rw-r-- 1 raver raver    29281 Sep  6 14:23 aegis_trash.txt
-rw-rw-r-- 1 raver raver 26723730 Sep  6 14:23 choosy_voltron.txt
```

— same sizes and the same `Sep 6 14:23` mtime evidence §7 recorded, one day earlier. By evidence §7's own argument (a fresh download would leave a write time at or after the moment the command ran, not an unchanged prior timestamp), this round's invocation also served from cache rather than downloading.

| Source | malformed/skipped (inferred from absent suffix, `cli.py:560-565`) | wildcards (inferred from absent suffix, `cli.py:560-565`) | Conflict behaviour |
|---|---|---|---|
| `choosy_voltron` | 0 | 0 | Additive merge, no dedup/priority (below) |
| `aegis` (Nitaraku) | 0 | 0 | Additive merge, no dedup/priority (below) |
| `aegis_trash` (Ciceron) | 0 | 0 | Additive merge, no dedup/priority (below) |

**Conflict behaviour:** `Wishlist.merge` ([wishlist.py:51-57](../src/vault_cleaner/wishlist.py#L51-L57)) is purely additive — for each item hash it extends the merged map's roll list with the other source's rolls, with **no de-duplication and no source priority**. If two configured sources both have keep or trash rolls for the same item hash, both sets of rolls survive independently in the merged `Wishlist`; the merge step itself never resolves a conflict. A keep-vs-trash conflict on the *same* item (one source's keep against another's trash, or the same source's own keep and trash) is resolved downstream, at the rule layer, by `weapons.py`'s keep-beats-trash check (§3) — not inside `merge`.

---

## 6. Recommended Aegis-derived source strategy

### One curation family

Ciceron, MrCharles, and Nitaraku are **not independent curators**. All three are mechanical scripts converting a single source of truth: Aegis's PvE Endgame spreadsheet ([https://docs.google.com/spreadsheets/d/1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY](https://docs.google.com/spreadsheets/d/1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY); retrieved/confirmed 2026-09-06, cited from the `// Tierlist source:` comment header in the cached `wishlists/aegis.txt` and independently from the Ciceron repository README's "Endgame Analysis Spreadsheet" link, both re-fetched this session). Counting agreement between them as "consensus" is a statistical error. They must be treated as **one curation family** (Aegis PvE Endgame), evaluated against Choosy Voltron as the broad community baseline.

### Strategy recommendation

1. **Broad baseline:** Retain Choosy Voltron as the baseline keep source for general utility and PvP protection.
2. **Endgame keep curation — recommendation: keep Nitaraku's traits-only feed** (the already-configured `aegis` source, `wishlists/aegis.txt`, upstream `aegis_wishlist.txt`), not Ciceron's sibling `dim_aegis_endgame_major-perks.txt`. Reasoning: (a) Nitaraku is already a configured `[wishlists.sources]` entry with a measured, working parse (5,022 keep rolls across 968 items, §5) — adopting Ciceron's major-perks file instead would require adding a **new** `[wishlists.sources]` entry, which is a `config.toml` change out of this ticket's scope (the mechanical inclusion test bars it) and would need to be a Child 3 deliverable, not a §6 recommendation to act on today; (b) Nitaraku's traits-only scope is confirmed directly from the cached file's own `description:` header line ("Uses only Trait 1 and Trait 2 columns", §5) with no inference required, while Ciceron's major-perks filtering behaviour is known only from the upstream README's "Barrels and Mags" prose (§5's widened fence) — the specific filename `dim_aegis_endgame_major-perks.txt` itself is confirmed to exist by §5's `gh api .../git/trees` tree-path fence, not by that prose — one step further from the parsed bytes; (c) Nitaraku's file already carries explicit `Tier`/`Rank` tokens in its standalone `//notes:` lines (§5), which Child 3 can parse directly once it addresses the `wishlist.py:73-74` discard seam. Either file remains a defensible choice — Ciceron's major-perks variant is a candidate migration if Child 3 finds Nitaraku's coverage insufficient — but Nitaraku is the one recommendation this section commits to, since it needs no new source entry to act on. Focus on trait columns rather than full 4-perk combinations to avoid false negative mismatches on barrel/mag rolls.
3. **Endgame trash curation:** Retain Ciceron's whole-item trash list (`dim_aegis_endgame-trashlist.txt`, D-tier and below).
4. **Attribution and tier preservation (Child 3):** Enhance `parse_wishlist` to parse and retain `#notes:` tier tokens (`Tier: S`, `Tier: A`, etc.) and record the originating `source_name`.
5. **Conflict and uncertainty rules:**
   - A weapon lacking Aegis coverage is **not** trash; it represents absence of endgame PvE evaluation (or a dedicated PvP weapon), treated as `unknown or uncovered`.
   - In aggressive mode, a keep match from Choosy Voltron on an item marked trash by Aegis should be flagged for review (`#vc-review: aegis-trash-voltron-keep`) rather than silently suppressed, allowing the player to confirm the dismantle.
   - No permanent third-party wishlist snapshot may be committed to the repository.

---

## 7. #34 reconciliation recommendation

### Staleness analysis of Issue #34

Issue #34 ("Rank weapons by unique useful-combination coverage", milestone `M6 — Armor dupes`) states:
> "The current `keep_match_count` counts every keep-wishlist entry whose perk hashes are a subset of the row's combined perk set. That is a useful first approximation and currently influences same-Hash survivor ranking, but..."

**Measured reality:** This statement is **stale**. `keep_counts` appears at `src/vault_cleaner/rules/weapons.py:65,74,79`; it is used **exclusively** to detect keep-vs-trash conflicts, guarded at `weapons.py:79` by `if keep_counts[row["Id"]] > 0:`. Exact duplicate ranking in `src/vault_cleaner/rules/dupes.py:42-51` uses `RANK_COLUMNS = ["Tier", "Masterwork Tier", "Crafted Level"]` then stat total, then opaque `Id`. Wishlist match counts have **zero** influence on survivor ranking today.

### Authoritative criteria to preserve

1. **Subset combination coverage:** Within the same `Hash`, roll B dominates roll A only if every useful combination on A is covered by B, and B provides at least one additional combination or wins deterministic state ranking.
2. **Review-only initially:** Lower combination count or subset relationship must remain review-only initially and never automatically junk a distinct roll without user approval.
3. **Physical selectable combinations:** Enumerations must evaluate only perk combinations physically selectable on that instance; impossible cross-column combinations must not be formed.
4. **Preserve landed #31 guarantees:** Exact duplicates remain governed by #31's landed deterministic ranking. Useful combinations apply only to non-identical rolls of the same `Hash`.

### Recommendation

**Recommendation: update.** Issue #34 should be revised to remove the stale survivor-ranking claim and repositioned as the specification for Child 4 of the #140 umbrella, rather than split into a new issue or left as-is. This recommendation is **advisory only**. `AGENTS.md` gates every issue operation — creating, editing, labelling, or commenting on an issue — behind explicit user authorization, and no such authorization has been given for this ticket. This document records the recommendation; it does not carry standing permission to act on it. Editing #34 (or any other issue) requires a separately authorized issue operation, requested and granted independently of this report.

Child 4 should be review-only, producing pairwise dominance comparisons in the review UI for owner decision. Per the authoritative criteria above (item 4), Child 4 must stay **separate from both #31's exact-duplicate identity/ranking and from wishlist-trash decisions** (§3, §4): a useful-combination dominance comparison never overrides an exact-dupe ranking or a `wishlist-trash` verdict, and neither of those existing mechanisms substitutes for the dominance evidence Child 4 must independently establish. This keeps the first version narrowly scoped and reviewable rather than entangled with #31's landed guarantees or the wishlist pipeline's existing trash path.

**Measured inputs a useful-combination enumeration would need.** These are already characterized above and in §2/§3; no new measurement is required to state them here:
- The complete named `Perks N` prefix per row up to the measured tracker boundary (§2's identifier-handling section, `AGENTS.md`'s weapon exact-dupe identity rule) — the same cells `dupes.py` already uses for exact-dupe grouping, needed here to enumerate which perk options are physically selectable on a given instance.
- `Hash`, to scope any comparison to rolls of the same weapon (§2's identifier-handling section); cross-`Hash` comparison is explicitly deferred (§8 item 9) and is not an input this enumeration may use.
- The wishlist `keep` match counts already computed at `weapons.py:65,74,79` (this section's own staleness measurement above) — the signal #34 originally proposed reusing for ranking, and which this section has just confirmed has zero influence on survivor ranking today.
- `RANK_COLUMNS` (`dupes.py:45`: `Tier`, `Masterwork Tier`, `Crafted Level`) then stat total (`dupes.py:47-52`'s `STAT_COLUMNS`) — needed so #31's deterministic exact-dupe ranking stays authoritative over, and is never displaced by, a dominance comparison.

Each of these is cited to where it is already measured elsewhere in this document; this list does not introduce a new command.

---

## 8. Aggressive weapons-first policy contract

### Policy specification

1. **Selection:** The aggressive policy is selectable via CLI `--policy aggressive` and review server configuration. Default execution remains the conservative maintenance policy.
2. **Weapons-only proposal scope:** The aggressive policy emits removal proposals **exclusively for weapons**.
3. **Armor handling:** Armor is imported and counted for inventory capacity accounting (measuring character and vault capacity), but all armor removal proposals are suppressed at the pipeline boundary. Hiding a UI tab is insufficient; the engine must emit zero armor junk decisions under this policy.
4. **Hard rails:**
   - `Tag in {'favorite', 'keep', 'archive'}` -> HARD (`dim-tag:{tag}`)
   - `Equipped == 'true'` -> HARD (`equipped`)
   - `Crafted == 'crafted'` with level >= 10 -> HARD (`crafted-lv{level}`)
   - `Crafted == 'crafted'` with empty level -> HARD (`crafted-lvunknown`)
   - **`Loadouts != ''` -> HARD** (`loadout-protected`; settled owner decision; Child 2a)
   - Durable vetoes in `overrides.json` -> HARD exclusion
5. **Aegis tier discrimination and PvP uncertainty:**
   - D-tier whole-item trash with no keep match -> Automatic junk candidate.
   - D-tier whole-item trash with Voltron keep match -> Review-only comparison (`#vc-review: aegis-trash-voltron-keep`).
   - Unrated / no Aegis coverage -> `unknown or uncovered`; retained.
   - **PvP uncertainty, stated at this policy seam** (§5/§6 measure the underlying gap): every configured Aegis-derived source rates PvE endgame performance only ([config.toml:64-71](../config.toml#L64-L71); §5). Absence of Aegis coverage, or a D-tier PvE rating, is never evidence that a weapon is safe to remove for a PvP-oriented loadout — a PvP-relevant roll with no PvE endgame rating stays `unknown or uncovered`, not `automatic junk candidate`.
6. **Personal-use exceptions:** This policy proposes at the Python pipeline/output seam only (§8's boundary statement above); it has no input signal for a player's personal, non-meta attachment to a build that scores low on curated tier lists. The review UI's per-item veto is the only mechanism that can record such an exception, and no rule is permitted to infer one — an aggressive proposal is never suppressed by anything other than a rail, a keep match, or an explicit veto.
7. **Distinct useful coverage:** A roll that offers a perk combination available on no other owned copy of the same `Hash` (per §4's taxonomy and #34's authoritative criteria in §7) is never `automatic junk candidate` on that basis alone; it remains `review-only comparison` at best, pending #34/Child 4's dominance evidence. The aggressive policy does not weaken this — a 100-space shortfall is never grounds to treat unique coverage as junk.
8. **Retained alternatives requirement:** Any outclassed-weapon proposal must name an owned, retained weapon instance covering the same role and element. If the alternative is proposed for removal, the recommendation is invalid.
9. **Stop conditions for unsupported inference:**
   - **Role inference:** the aggressive policy must not infer a weapon's PvE/PvP role, activity fit, or build synergy from any field vault-cleaner currently parses (`Type`, `Ammo`, `Element`, `Archetype` are descriptive, not role metadata; see §2). A rule that would need role inference to justify a proposal is out of scope until a child ticket defines and measures a role-metadata source.
   - **Cross-`Hash` comparison:** comparing two different `Hash` values (as opposed to exact-roll or same-`Hash` dominance) requires explicit role and activity metadata this pipeline does not have today. **Cross-`Hash` recommendations are deferred unless explicit role and activity metadata supports them** — see Child 7 in §12, which is gated on this stop condition, not merely deprioritized.
10. **Ruleset and fingerprint effects:** Adding `policy` settings requires projecting the new configuration in `report_run._decision_config` ([report_run.py:173-224](../src/vault_cleaner/report_run.py#L173-L224)) and bumping `RULESET_VERSION` ([report_run.py:44](../src/vault_cleaner/report_run.py#L44)) from `4` to `5`.
11. **No manufactured proposals:** The 100-space goal is a target, not a quota. If justified proposals fall short of 100, the shortfall is reported honestly; rules must never manufacture junk decisions. The 100-space goal never justifies manufacturing proposals, inferring an unsupported role, or performing a deferred cross-`Hash` comparison.

---

## 9. Approval-only finalization contract

### Authoritative seam and call sites

The authoritative finalization seam is `review.apply_vetoes` ([review.py:546](../src/vault_cleaner/review.py#L546)) feeding `report.render_import_csv` ([report.py:83-102](../src/vault_cleaner/report.py#L83-L102)). Both sibling call sites must be updated together:
1. Server: [src/vault_cleaner/server/app.py:790-792](../src/vault_cleaner/server/app.py#L790-L792)
2. CLI: [src/vault_cleaner/cli.py:484](../src/vault_cleaner/cli.py#L484)

### Approval-only rule

Today, `apply_vetoes` is subtractive:
```python
# Current subtractive behavior (review.py:553-559):
suppressed = frozenset(vetoed_ids)
return [
    decision
    for section in run.sections
    for decision in section.decisions
    if decision.id not in suppressed
]
```

In approval-only finalization (Child 2b):
- An item is included in the output CSV **only if explicitly approved** (`verdict == "approved"`).
- Vetoed proposals (`verdict == "vetoed"`) are excluded.
- Unreviewed proposals (`verdict` unset / unchecked) are **excluded**.
- The canonical verdict *token set* is `VERDICTS = frozenset({"approved", "vetoed"})` ([review_session.py:41](../src/vault_cleaner/review_session.py#L41)). Both untrusted-input boundaries accept exactly that token set for a non-null verdict — [review.py:300-304](../src/vault_cleaner/review.py#L300-L304) (the review-manifest validator) rejects any verdict not in `VERDICTS`, and [server/app.py:221-228](../src/vault_cleaner/server/app.py#L221-L228) (the server's verdict-request validator) rejects any non-null verdict not in the inlined literal `{"approved", "vetoed"}` — but the **enforcement is not identical**: the server additionally accepts `verdict: null` as an explicit clear path (`"{where}: verdict must be approved, vetoed, or null"`, `app.py:227`), which the manifest validator has no equivalent for — a missing or non-string `verdict` there fails as malformed input, not as an accepted clear signal. This distinction matters specifically for the approval-only contract, which turns on distinguishing "vetoed" from "unset/unchecked": the server's `null` path is how a client clears a verdict back to unset, and the review-manifest side was never given the same explicit clear token. `review_ui.js:131` accepts only these two *verdict* tokens (`verdict === "approved" || verdict === "vetoed"`); there is no `"approve"` / `"veto"` **verdict** token anywhere in the codebase. (`"approve"` and `"veto"` do appear elsewhere in `review_ui.js` — e.g. lines 893, 900, 1231, 1233, 1238, 1240 — but only as CSS class names and `aria-label` fragments for the UI buttons, and in `tests/test_review_ui_js.py:1557` asserting that presentation; none of those is a verdict value.)

### Durable veto interaction and semantics

Two unrelated "manifest"-adjacent types must stay distinct here, per `AGENTS.md`:
- **`OverrideStore`** ([review_session.py:64-66](../src/vault_cleaner/review_session.py#L64-L66)) is the **durable** record, persisted to and loaded from `data/overrides.json`. Its `vetoes: tuple[Veto, ...]` field is the only place a veto survives across sessions.
- **`ReviewManifest`** ([review.py:83-97](../src/vault_cleaner/review.py#L83-L97)) is the **transient, untrusted** manifest the UI hands back for one session's fresh verdicts. It has `decisions`, and the derived properties `vetoed` and `approved` (each filtering `decisions` by `verdict`) — it has **no** `vetoes` attribute, and it is never itself the durable store.
- `review.classify` ([review.py:496-543](../src/vault_cleaner/review.py#L496-L543)) sorts the durable `OverrideStore.vetoes` into active / stale / orphaned / unchecked against the current `ReportRun`'s proposals. A veto becomes `stale` when `(action, reason)` no longer matches the current proposal. This is how a fresh session's fresh verdicts and durable state interact without resetting the durable store: a new rule (or a new aggressive profile) that changes what is proposed for an item does not erase its persisted veto — it makes that veto stale so the item resurfaces for re-review, and #114 (not repurposed here) owns any reset behaviour.
- **Definition:** "Removed" means excluded from the CSV. Vault Cleaner never deletes items or issues automated dismantle commands.

---

## 10. Capacity model and input contract

### Mathematical formula validation

Umbrella Issue #140 defines projected free vault space:

```text
projected_free = F + D_v - (C - D_c)
```

Where:
- $F$: Current free vault spaces. **Not derivable from DIM export**; must be entered by the user or confirmed against an external baseline.
- $C$: Unequipped items currently on characters intended to be cleared into the vault.
- $D_v$: Unique approved removals from the vault.
- $D_c$: Unique approved removals from characters.
- $C - D_c$: Net character items that must move into the vault.

### Four distinct capacity states

The capacity model must report four distinct states honestly:

1. **Proposed capacity:** Potential capacity if every proposed item (automatic junk + review proposals) were approved: `F + D_v_prop - (C - D_c_prop)`.
2. **Explicitly accepted capacity:** Capacity based strictly on user-approved verdicts in the review session: `F + D_v_acc - (C - D_c_acc)`.
3. **Finalized-output capacity:** Capacity resulting from the generated DIM import CSV.
4. **Observed / confirmed free space:** Actual empty vault slots verified via a fresh DIM export or user confirmation after in-game dismantling and transfers.

### Input and counting contracts

- **Opaque ID single-counting:** Every removal is counted exactly once by its opaque string instance `Id`. An item cannot be counted twice across different duplicate or review groups. `Id` is handled as an opaque string end to end; `rules/id_order.py`'s module docstring states plainly that ids "are normally decimal uint64 values, but callers must not rely on that being true" ([id_order.py:1-7](../src/vault_cleaner/rules/id_order.py#L1-L7)) — a capacity contract that counts by `Id` must not assume a fixed bit width.
- **Negative projections as shortfalls:** If $F - (C - D_c) < 0$, the display must report a shortfall (e.g. "Over capacity by 90 items; 90 removals required before clearing characters"), never an impossible negative capacity.
- **Incomplete exports and omitted categories as shortfalls:** An incomplete export (a required column missing schema validation) or an omitted item category (weapons measured, armor/ghosts/consumables not) must be surfaced as an explicit shortfall or uncertainty band, never folded silently into $F$, $C$, $D_v$, or $D_c$ as though the omitted category contributed zero. §11's authorized real export is itself this case: it is weapons-only (§14 item 3), and its $F \approx 10$ figure is an owner estimate rather than a measured export field — so §11's capacity arithmetic must be read as a weapons-only, owner-estimated-$F$ scenario carrying that uncertainty, not a validated whole-vault projection.
- **Dismantle vs. transfer proof:** An approval, tag, Notes edit, or CSV download is not proof that in-game dismantling or transfers occurred.

---

## 11. Yield: fake-data evidence and privacy-safe real-export procedure

### Reproducible fake-data yield

From committed fixtures without wishlists ([docs/evidence/issue-142/README.md](evidence/issue-142/README.md#5-baseline-report-runs-on-fake-fixture-data)):
- `weapons.csv`: 3 items -> 0 junk, 0 review.
- `weapons_dupes.csv`: 18 items -> 4 junk, 3 review.
- `weapons_hostile.csv`: 10 items -> 5 junk, 0 review.
- `weapons_slammer_like.csv`: 5 items -> 1 junk, 0 review.

### Privacy-safe real-export measurement procedure

When analyzing a real user export:
1. **Zero committed account data:** Never copy the export into `data/in/` or any tracked folder. Do not run `--write`.
2. **Aggregate-only extraction:** Run measurement scripts outside the working tree (or via temporary scripts) that output only sums, value counts, and aggregate metrics.
3. **No durable identifiers:** Never log, print, or commit `Hash` values, instance `Id`s, or raw CSV rows. **Item names may be published only when the repository owner explicitly authorizes that specific measurement for the ticket** — as happened here on 2026-09-06 (see §1, §14). Absent that authorization, item names are withheld along with `Hash`/`Id`/rows.
4. **Sanitize evidence:** Transcripts committed under `docs/evidence/` must contain aggregate counts (and, only under an owner-authorized item-name exception, item names) — never `Hash`, instance `Id`, or raw rows.

### Aggregate findings on authorized real export (2026-09-06)

Measured on the owner's supplied export of 664 weapons (see self-contained reproduction commands and output in [docs/evidence/issue-142/README.md](evidence/issue-142/README.md#8-aggregate-only-real-export-analysis-authorized-session-data)):

- **Export identity:** `destiny-weapon (12).csv`, size 323,610 bytes, SHA-256 `35c9ee801b73a64c641dfe7a0f556c05d244f96a52902083e7a2fff7e0fb5571`, measured on 2026-09-06. The file contains 664 data rows across 74 header columns, per the `csv.reader` and `pandas` counts quoted in evidence §8's `real_export_summary.txt`. (Round 1 additionally claimed a total line count and a trailing-newline state for this file; neither was ever produced by a command in evidence §8, which only calls `.splitlines()` and never reports a line count or newline state. The file is on another machine and unavailable to this session, so that claim is retracted rather than re-measured — see §14.)
- **Location breakdown:**
  - Owner `Vault`: 555
  - Owner `Titan(451)`: 43 (measured power level 451 at snapshot time)
  - Owner `Warlock(550)`: 35
  - Owner `Hunter(550)`: 31
  - Total on characters: 109
- **Equipped weapons:** 9 (3 characters × 3 equipped slots)
- **Unequipped character weapons ($C$):** 100 ($109 - 9$)
- **Unique hashes:** 440 (`df['Hash'].nunique()`, quoted in evidence §8's `real_export_summary.txt`).
- **Protection breakdown across rule worlds:**
  - **Current-rules world (no loadouts rail):**
    - Hard-protected: 56 (8 tag-protected, 9 equipped, 41 crafted level >= 10 or unknown)
    - Soft-protected (exotic or locked, not hard): 323 (125 exotic, 198 locked legendary)
    - Completely unprotected: 285 (239 in vault, 46 unequipped on characters)
  - **Proposed-rules world (with hard loadouts rail):**
    - Hard-protected: 169 (136 in loadouts; 113 incremental over current rules)
    - Soft-protected (exotic or locked, not hard): 223 (82 exotic, 141 locked legendary)
    - Completely unprotected: 272 (231 in vault, 41 unequipped on characters)
- **Baseline pipeline yield:**
  - With `--no-wishlists`: 0 junk, 2 review (both exotic Praxic Blade duplicates).
  - With wishlists (using the original session's local Bungie manifest cache, version `244213.26.06.29.2000-1-bnet.65864`; this run is environment-dependent, see §14 item 1 for this session's inability to reproduce that exact cache state): 5 junk (`wishlist-trash whole-item`), 6 review (4 `wishlist-trash whole-item` + 2 `dupe-lower`). 21 weapons had trash suppressed by keep matches. **Not stated:** which configured source (Choosy Voltron vs. the Aegis family) contributed each trash match, or which soft rail (`exotic` vs. `locked`) applies to each of the 4 `wishlist-trash whole-item` review items — neither is observable in the quoted capture (evidence §8's `real_wishlists.txt`), and `Wishlist.merge` (§5) destroys per-source attribution before rules run, so the source cannot be recovered after the fact. The round 1 attribution of these to "all Ciceron whole-item trash" and "4 locked trash" was unsourced and is retracted here; see §14.
- **Required removals for 100-space goal:**
  Given estimated $F \approx 10$ and $C = 100$:
  ```text
  projected_free = 10 + D_v - (100 - D_c) >= 100  ==>  D_v + D_c >= 190
  ```
  The owner needs **at least 190 approved removals** across vault and characters ($D_v + D_c \ge 190$). Because only 272 weapons are completely unprotected in the proposed ruleset (and only 285 in current rules), reaching the goal requires evaluating distinct useful-combination coverage (#34) and reviewing locked/outclassed rolls, rather than relying on exact duplicates alone.

---

## 12. Dependency-ordered child map

| Child | Scope | Depends On | Mechanical Seam | Recommended Review Path | Overlap / Boundaries | Early Deliverable? |
|---|---|---|---|---|---|---|
| **2a** | Hard loadout protection rail for weapons; schema enforcement | #142 | `parse.py:42-44`, `rules/rails.py:30-56`, `tests/fixtures/weapons*.csv` | Independent adversarial review | Touches weapon schema and rails; requires adding loadout fixture test cases | **Yes** (independent safety gate) |
| **2b** | Approval-only finalization seam | #142 | `review.py:546`, `server/app.py:790`, `cli.py:484` | Independent adversarial review | Inverts CSV finalization logic; affects both server and CLI | **Yes** (independent output gate) |
| **3** | Wishlist provenance, attribution, and tier/notes parsing — **both** discard seams: `LINE_RE`'s `#notes:` tail (Choosy Voltron) and the standalone `//notes:` block-line skip (both configured Aegis sources) | #142 | `src/vault_cleaner/wishlist.py:29` (`LINE_RE`), `wishlist.py:69-100` (`parse_wishlist`, including the standalone-comment skip at `wishlist.py:73-74`) | Standard review | Parses both tier-token forms and preserves source attribution through `merge`; a fix that only touches `LINE_RE` recovers zero notes from either configured Aegis source (measured, §5) and is an incomplete Child 3; does not change rule logic | Yes |
| **4** | Same-Hash useful-combination coverage (#34) | 2a, 3, #31 | `src/vault_cleaner/rules/` (new module `combinations.py`) | Independent adversarial review | Implements pairwise coverage dominance; review-only initially | No (needs 2a, 3) |
| **5** | Aggressive clear-out policy and weapons-first proposal scope | 2a, 2b, 3, 4 | `src/vault_cleaner/report_run.py`, `config.toml` | Independent adversarial review | Suppresses armor proposals; projects config in `_decision_config`; bumps `RULESET_VERSION` | No (needs 2a, 2b, 4) |
| **6** | Capacity model and progress accounting UI | 2b, 5, #140 | `src/vault_cleaner/ui/`, `duplicate_reference.py` | Standard review | Adds semantic `Owner` parsing for $C$; displays four capacity states | No (needs 2b, 5) |
| **7** | Outclassed / redundant alternative recommendations | 4, 5 | `src/vault_cleaner/rules/` | Independent adversarial review | Recommends replacements across weapons sharing role/element; requires owned retained replacement | No (needs 4, 5) |
| **8** | Validation, real-export dry run, and operating guidance | 2a–7 | `docs/`, `WORKLOG.md` | Standard review | End-to-end dry run verification; operational walkthrough | Final wrap-up |

---

## 13. Open questions requiring an owner decision

1. **Weapon `Loadouts` schema enforcement (Child 2a):**
   Should Child 2a make `Loadouts` strictly required in `REQUIRED_WEAPON_COLUMNS` (failing loudly if a CSV lacks the header, matching armor/ghost behavior), or degrade gracefully with an explicit error/warning?
   *Recommendation:* Make `Loadouts` required in `REQUIRED_WEAPON_COLUMNS`. Incomplete exports should fail loudly rather than silently treating all weapons as unprotected.
2. **Character inventory clear-out workflow (Child 6):**
   Should unequipped character weapons ($C = 100$) be proposed for dismantling in place on characters ($D_c$), or should the policy instruct transferring them to the vault first?
   *Recommendation:* Support in-place dismantling ($D_c$). In DIM, tag and note updates apply regardless of location. Dismantling in-place reduces character clutter without requiring intermediate vault space.
3. **Review treatment of locked weapons:**
   On the real export, 141 legendary weapons are locked without being in any loadout. To reach 190 removals, some locked items must be evaluated. Should aggressive review surface locked duplicate/inferior rolls with an explicit "Unlock & Junk" recommendation?
   *Recommendation:* Yes. Keep locked state as a soft rail: surface in the review UI with a clear `#vc-review: dupe-lower (locked)` or `#vc-review: outclassed (locked)` tag, requiring explicit approval to include in the output.
4. **Choosy Voltron vs. Aegis conflict handling in aggressive mode:**
   When an item is rated D-tier trash by Aegis but matches a broad keep roll in Choosy Voltron (21 items observed on real export), should aggressive mode default to proposing it for review?
   *Recommendation:* Yes. Surface as `#vc-review: aegis-trash-voltron-keep` so the player can decide whether to keep the casual roll or clear the space for endgame optimization.

---

## 14. Limitations and NOT MEASURED register

1. **Live Bungie Manifest download, and the original wishlist-enabled real-export run's exact cache state:** The ~200MB Bungie manifest download was not executed in the original implementer's session; that session used its local cache and recorded manifest version `244213.26.06.29.2000-1-bnet.65864` in a shell comment (not command output) in evidence §8. **This correction round runs on a different machine than that original session and cannot reproduce or independently verify that specific cache state or version string** — the real export itself is also unavailable on this machine. What this session *can* and does state as its own measurement, from a genuine command against this machine's own local cache, is:
   ```bash
   set -euo pipefail
   OUT="$(mktemp -d)"
   .venv/bin/python -c "
   import json
   d = json.load(open('data/cache/perk-name-map.json'))
   print('version:', d['version'])
   print('names_count:', len(d['names']))
   " > "$OUT/manifest_cache_version.txt" 2>&1
   cat "$OUT/manifest_cache_version.txt"
   ```
   `$OUT/manifest_cache_version.txt`:
   ```text
   version: 244213.26.06.29.2000-1-bnet.65583
   names_count: 10627
   ```
   and, for the cache directory's mtime:
   ```bash
   set -euo pipefail
   OUT="$(mktemp -d)"
   ls -l data/cache/ > "$OUT/data_cache_ls.txt" 2>&1
   cat "$OUT/data_cache_ls.txt"
   ```
   `$OUT/data_cache_ls.txt`:
   ```text
   total 404
   -rw-rw-r-- 1 raver raver 410472 Aug 30 10:29 perk-name-map.json
   ```
   This machine's cache (version `...65583`, mtime 2026-08-30) is a **different** cache from the one the original session used (version `...65864`) — the two are not the same measurement and must not be conflated. The original session's specific version/mtime claim is **NOT MEASURED** in this correction round for that reason; it is left in §11 as the original implementer's own recorded claim, not independently re-verified here.
2. **MrCharles full matrix run:** Newly measured this round: the repository structure (28 files, 7 rank codes × 4 `PPC` codes, byte sizes from 443,282 to 36,724,539) via a `gh api .../git/trees` query (§5, cited with retrieval date 2026-09-06). **Still NOT MEASURED:** actual parsed content of those 28 files (keep-roll counts, skipped/malformed counts, per-rank tier semantics beyond the file-name convention) — MrCharles is not a configured `[wishlists.sources]` entry, and importing >200MB of additional wishlist text into `vault-cleaner wishlists` for a source this report does not recommend adopting wholesale is out of this ticket's scope.
3. **Non-weapon vault inventory:** The supplied real export contained weapons only (`destiny-weapon (12).csv`, SHA-256 `35c9ee801b73a64c641dfe7a0f556c05d244f96a52902083e7a2fff7e0fb5571`, 664 true data rows, 323,610 bytes, measured 2026-09-06). Armor, ghost shells, and consumable vault holdings were not measured; total free space $F \approx 10$ is based on owner estimate.
4. **Third-party dates and commits:** External repository commit timestamps (`pushed_at`) and raw file contents are cited to GitHub API queries executed on 2026-09-06 (re-run and re-verified in this correction round; see evidence §9).
5. **Real-export multi-copy hash breakdown (retracted):** Round 1's "115 hashes account for 339 items" claim (§11) was never produced by any recorded command — the real-export script (evidence §8) prints only `Unique weapon Hashes: 440`. No script computing a multi-copy breakdown was run in the original session, and none is re-derivable here (the export is unavailable on this machine). Retracted from §11; **NOT MEASURED**.
6. **Real-export wishlist-trash source and rail-reason attribution (retracted):** Round 1's "(all Ciceron whole-item trash)" and "(4 locked trash + 2 Praxic Blade)" attributions in §11 are not supported by the quoted capture (evidence §8's `real_wishlists.txt` prints item name/id/location for `wishlist-trash whole-item` decisions with no source or rail-reason suffix) and contradict §5's finding that `Wishlist.merge` destroys per-source attribution before rules run. Which configured source contributed each of those 5 junk / 4 review decisions, and which soft rail (if any) applies to each of the 4 review decisions, is **NOT MEASURED** and not recoverable from the existing capture.
7. **Authorized plan deviation and owner privacy decision (real export analysis):** The repository owner explicitly provided `destiny-weapon (12).csv` on 2026-09-06 and authorized measurement of it within this spike, superseding the plan's "specified, not executed" restriction (plan lines 417-419 and 637). Stop condition S4 was satisfied. Two privacy rules apply, and they are distinct:
   - **Aggregate counts** (location breakdown, protection breakdown, capacity arithmetic) were authorized and committed from the start; zero raw rows, `Hash` values, or instance `Id`s were ever authorized for commit.
   - **Item names** in the two `report` captures quoted in evidence §8 were additionally authorized for publication by the repository owner, explicitly, on 2026-09-06. That authorization does **not** extend to instance `Id`s: the eleven 19-digit instance `Id`s that originally appeared alongside those names in evidence §8 have been redacted post-capture to `id <redacted>` (see the note above each capture in evidence §8). This is the owner's 2026-09-06 decision recorded in `WORKLOG.md`; future agents must not reverse it, and must not restore the redacted IDs without a fresh, explicit owner authorization.
   - This decision is recorded today only in `WORKLOG.md` (the 2026-09-06 PR-2 entry and its round 2/3 corrections), not as a durable repository rule. Issue #145 is the ticket that would carry it into `AGENTS.md` as a durable rule — see `WORKLOG.md`'s round 3 entry (`AGENTS.md` was not touched here; issue #145 carries that amendment). This document does not create, edit, or comment on #145 or any other issue; doing so is a separately authorized issue operation.
8. **Real-export total line count and trailing-newline state (retracted, round 3):** Round 1's §11 stated the file "has 665 lines total because it does not end with a trailing newline," citing the 664-data-row count as its basis. No command in evidence §8 ever measured a total line count or a trailing-newline state — the export script only calls `.splitlines()` and prints `Data rows (csv.reader)` / `Data rows (pandas)`, never a line count. The claim was also internally wrong regardless of citation: a file of 1 header line + 664 data lines has 665 lines whether or not it ends with a trailing newline; the absence of a trailing newline would make `wc -l` under-count to 664, not add a 665th line. The file is on another machine and unavailable to this session, so the sentence is retracted from §11 rather than re-measured. **NOT MEASURED.**
9. **Real-export unique-hash coverage against wishlist keep/trash entries (round 4):** §11 measures 440 unique `Hash` values on the real export (`df['Hash'].nunique()`); §5 measures per-source keep/trash counts against the cached wishlist files. §5 never cross-references the two — how many of those 440 hashes have a keep or trash entry in any configured source. Cross-referencing them would require running the export's actual `Hash` column against the cached wishlist maps, which needs the real export CSV; it is on another machine and unavailable to this session (same limitation as items 1, 3, 5, and 6 above). The plan's requirement is "where obtainable" for this row, so its absence from §5 is not itself a defect — this entry records that it was not obtainable this round, rather than leaving the gap unstated. **NOT MEASURED.**
