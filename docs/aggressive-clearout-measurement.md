# Aggressive weapons-first clear-out — measurement and policy design

## 1. Scope, baseline and reproduction

- **Date:** 2026-09-06
- **Base SHA:** `9a74192d136242a9820830d4547dd2209db37ca5`
- **Environment:** Python `3.13.14`, pandas `3.0.5`
- **Scope:** This document is an investigative measurement and policy design spike for Issue #142 (part of umbrella Issue #140). It changes no production behaviour: no rule, parser, schema, config, server, UI, `RULESET_VERSION`, or fixture change is introduced by this investigation.

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

1. **`REQUIRED_BASE_COLUMNS`** ([parse.py:32-34](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/parse.py#L32-L34)):
   `Name`, `Hash`, `Id`, `Tag`, `Rarity`, `Locked`, `Equipped`, `Notes`.
2. **`REQUIRED_WEAPONS_COLUMNS`** ([parse.py:42-44](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/parse.py#L42-L44)):
   `REQUIRED_BASE_COLUMNS` + `Type`, `Ammo`, `Crafted`, `Crafted Level`, `Perks 0`.
   **Finding:** `Loadouts` is **not** in `REQUIRED_WEAPONS_COLUMNS`.
3. **`REQUIRED_GHOSTS_COLUMNS`** ([parse.py:47](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/parse.py#L47)):
   `REQUIRED_BASE_COLUMNS` + `Loadouts`.
4. **`REQUIRED_ARMOR_COLUMNS`** ([parse.py:71-76](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/parse.py#L71-L76)):
   `REQUIRED_BASE_COLUMNS` + `Type`, `Equippable`, `Loadouts`, `Tuning Stat`, `Seasonal Mod`, `Holofoil`, `Masterwork Tier`, `Power`, `Tier`, `Perks 0`, `Archetype`, plus the six `ARMOR_STATS` columns (`Weapons`, `Health`, `Class`, `Grenade`, `Super`, `Melee`).

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

1. **Weapon `Loadouts` coverage gap:** Across all 36 weapon rows in all 4 weapon fixtures (`weapons.csv`, `weapons_dupes.csv`, `weapons_hostile.csv`, `weapons_slammer_like.csv`), **zero** non-empty `Loadouts` cells exist. Because `Loadouts` is not in `REQUIRED_WEAPONS_COLUMNS`, an export that dropped `Loadouts` entirely would load silently without triggering schema validation.
2. **Three distinct `Loadouts` states:**
   - **Column missing:** Incomplete export schema. The protection input is absent. Must not default to "not in a loadout". Child 2a must add `"Loadouts"` to `REQUIRED_WEAPONS_COLUMNS` in `parse.py` so incomplete weapon exports fail loudly.
   - **Cell empty on a row:** The normal measured state for items not saved to any loadout ([ghosts.py:36](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/ghosts.py#L36), [armor_dupes.py:99-100](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/armor_dupes.py#L99-L100)). Treated as unprotected by this dimension.
   - **Column present but empty on every row:** Ambiguous state (either the player has saved no DIM loadouts, or DIM export formatting changed). Must be detected and surfaced in the report summary as an explicit advisory notice.
3. **`Owner` contract and lack of semantic parsing:**
   `Owner` exhibits three observed shapes in DIM exports:
   - The literal `Vault` sentinel: item resides in the vault.
   - Bare class name: e.g. `Titan` (observed in `weapons.csv`).
   - Class with power level: e.g. `Titan(451)`, `Titan(550)`, `Hunter(506)` (observed in armor/ghost fixtures and real exports).

   A comprehensive search for `"Owner"` across `src/vault_cleaner` yields exactly **13 reads** ([docs/evidence/issue-142/README.md](evidence/issue-142/README.md#4-semantic-owner-reads-in-codebase)): 10 `Decision.location` assignments, 2 display reads through `safe_fragment` ([duplicate_reference.py:184,212](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/duplicate_reference.py#L184)), and 1 CLI dry-run print ([cli.py:151](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/cli.py#L151)). **`Owner` is not semantically parsed anywhere**: no function parses `Owner` to derive residency, character class, or power level. Child 6 must define and implement this derivation before capacity accounting can rely on it.
4. **No export column reports vault capacity or free space:** DIM CSV exports do not report total vault capacity (e.g. 700 spaces) or current free spaces (`F`). `F` is inherently an external input.

### Protection dimension comparison

| Dimension | Measured Export Indicator | Current Rail Precedence | Aggressive Policy Treatment |
|---|---|---|---|
| **Equipped state** | `Equipped == 'true'` | HARD rail (`equipped`) | Retained; hard rail preserved |
| **Character location** | `Owner != 'Vault'` | Unprotected (location recorded only) | Does not imply protection; items on characters may be proposed for removal |
| **Saved-loadout membership** | `Loadouts.str.strip() != ''` | Unprotected for weapons; read only for ghosts/armor dupes | **HARD rail** in aggressive policy (settled decision; Child 2a) |
| **DIM protective tags** | `Tag in {'favorite', 'keep', 'archive'}` | HARD rail (`tag-protected`) | Retained; hard rail preserved |
| **Crafted protection** | `Crafted == 'crafted'` | HARD if empty level (`crafted-lvunknown`) or level ≥ 10 (`crafted-level`) | Retained; hard rail preserved |
| **Locked state** | `Locked == 'true'` | SOFT rail (`locked` -> review-only) | Retained as soft rail; flagged for review, never auto-junked |
| **Exotic state** | `Rarity == 'Exotic'` | SOFT rail (`exotic` -> review-only) | Retained as soft rail; flagged for review, never auto-junked |
| **Durable veto** | `Id in ReviewManifest.vetoes` | Excluded from CSV in `apply_vetoes` | Retained; vetoes suppress export unless stale or re-reviewed |

### Identifier handling and types

- **`Id`:** Opaque string end-to-end. Handled as a string in `parse.py`, stored as string in `Decision.id`, formatted with surrounding triple-quotes on export ([report.py:73](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/report.py#L73)), and ordered lexically by `id_order.instance_id_order` without numeric conversion.
- **`Hash`:** String in DataFrame representation, dupe grouping ([dupes.py:100,216](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/dupes.py#L100)), and `Decision.hash`. Converted to `int` specifically at the wishlist boundary ([weapons.py:72](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/weapons.py#L72)) because `Wishlist.keep` and `Wishlist.trash` maps are int-keyed ([wishlist.py:79](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/wishlist.py#L79)). `AGENTS.md`'s rule ("keep Id/Hash opaque strings") governs untrusted input (review manifests and `data/overrides.json`), not internal wishlist lookup.

---

## 3. Current weapon rules, rails and review behaviour

### Rail precedence order in `rules/rails.py`

In `src/vault_cleaner/rules/rails.py:30-56`, `protection(row)` evaluates in strict sequence:

1. `Tag in PROTECTED_TAGS` (`favorite`, `keep`, `archive`): `Protection(HARD, "tag-protected")` ([rails.py:33-35](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/rails.py#L33-L35))
2. `Equipped == 'true'`: `Protection(HARD, "equipped")` ([rails.py:37-39](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/rails.py#L37-L39))
3. `Crafted == 'crafted'` and `Crafted Level == ''`: `Protection(HARD, "crafted-lvunknown")` ([rails.py:42-43](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/rails.py#L42-L43))
4. `Crafted == 'crafted'` and `int(Crafted Level) >= crafted_level_protect` (default 10): `Protection(HARD, "crafted-level")` ([rails.py:44-46](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/rails.py#L44-L46))
5. `Rarity == 'Exotic'`: `Protection(SOFT, "exotic")` ([rails.py:48-50](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/rails.py#L48-L50))
6. `Locked == 'true'`: `Protection(SOFT, "locked")` ([rails.py:52-54](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/rails.py#L52-L54))
7. Default: `Protection(NONE, "")` ([rails.py:56](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/rails.py#L56))

**Loadouts gap:** There is no weapon loadout rail. Only `ghosts.py:36` and `armor_dupes.py:99-100` check `Loadouts`. `report_run.py:317` records `in_loadout` strictly for UI presentation.

### Weapons pass execution order

In `src/vault_cleaner/rules/weapons.py:59-111`:

1. **Rails check:** Every row is evaluated against `protection(row)`. Hard-protected rows are skipped immediately.
2. **Wishlist evaluation:**
   - Rows matching `wishlist.trash` are identified (whole-item or perk-set match).
   - If a row also matches `wishlist.keep`, **keep beats trash**: the trash decision is suppressed, and `keep_trash_conflicts` is incremented ([weapons.py:79-80](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/weapons.py#L79-L80)).
   - Rows junked by wishlist trash are recorded and their IDs are removed from the exact-dupe candidate pool ([weapons.py:102-107](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/weapons.py#L102-L107)).
3. **Exact-duplicate pass:**
   - Remaining candidates are grouped by `Hash` + normalized perks prefix ([dupes.py:100-177](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/dupes.py#L100-L177)).
   - Exact duplicates are sorted deterministically using #31's landed guarantees: `Tier` desc, `Masterwork Tier` desc, `Crafted Level` desc, stat total desc, opaque instance `Id` desc ([dupes.py:42-51](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/dupes.py#L42-L51)).
   - Winner is retained; lower copies are marked junk (or review if soft rail applies). Ties use deterministic opaque ID tie-breaks.
   - Any row lacking a measured tracker boundary or complete prefix fails safe as ungroupable ([dupes.py:126-177](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/rules/dupes.py#L126-L177)).

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

The authoritative finalization seam is `review.apply_vetoes` ([review.py:546](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/review.py#L546)) feeding `report.render_import_csv` ([report.py:83](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/report.py#L83)). It has two sibling call sites:
1. Server finalization: [src/vault_cleaner/server/app.py:790-792](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/server/app.py#L790-L792)
2. CLI review: [src/vault_cleaner/cli.py:484](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/cli.py#L484)

`apply_vetoes` is currently **subtractive**: it subtracts vetoed IDs from the pipeline's proposal set, meaning all unreviewed proposals are included in the generated import CSV.

---

## 4. Proposal-strength taxonomy

To prevent premature automatic dismantling while enabling high-confidence clear-outs, proposals are classified into four mutually exclusive categories:

| Strength Class | Definition | Rules Producing It | Emit Action | Output Inclusion |
|---|---|---|---|---|
| **Automatic junk candidate** | Deterministic evidence of inferiority with zero soft-rail impediment | `wishlist-trash whole-item`, `wishlist-trash roll`, `dupe-lower`, `dupe-tie` on unprotected items | `junk` | Proposed for junk; included in CSV under current subtractive seam, but requires explicit approval under Child 2b approval-only seam |
| **Review-only comparison** | Proposal backed by evidence but restricted by a soft rail (locked/exotic) or pairwise coverage trade-off | `#vc-review: wishlist-trash whole-item (locked)`, `#vc-review: wishlist-trash whole-item (exotic)`, `#vc-review: dupe-lower (locked)`, `#vc-review: dupe-lower (exotic)`, `#vc-review: dupe-tie (exotic)`, future useful-combination dominance (#34) | `review` | Displayed in review UI; excluded from CSV unless user explicitly approves |
| **Protected / retained** | Hard-protected by player directive, system state, or dupe winner | Hard rails (`tag-protected`, `equipped`, `crafted-level`, `crafted-lvunknown`, `loadout-protected`), dupe survivor / winner | `keep` | Never proposed for junk; excluded from CSV |
| **Unknown or uncovered** | No wishlist match, ungroupable perks, or unique roll without comparable duplicate | Unmatched rolls, ungroupable exact-dupe rows, lone rolls | None | Retained. **Explicit invariant:** absence of wishlist coverage or inability to determine roll identity is **never** evidence of junk. |

---

## 5. Wishlist source and evidence evaluation

### Candidate evaluation matrix

Evaluation conducted on 2026-09-06:

| Candidate | Upstream Curation Family | Activity Scope | Roll / Hash Coverage | Tier & Quality Metadata | Notes & Attribution | Freshness / Check Date | Base/Enhanced Normalization |
|---|---|---|---|---|---|---|---|
| **Choosy Voltron** | Multi-curator community (PandaPaxxy, Mercules, etc.) | Broad PvE & PvP across all Destiny history | 255,373 keep rolls across 1,234 items; 53 trash entries across 53 items | None (binary keep/trash) | Rich `#notes:` descriptions with curator names in raw file; discarded at `LINE_RE` | `2026-08-03T22:53:37Z` upstream; cached `2026-09-03` | Hash-based; enhanced perk hashes listed explicitly |
| **Ciceron Aegis Lists** | Aegis PvE Endgame Analysis (mechanical conversion) | PvE Endgame (GM, Master Raids, Dungeons) | Full: A+S tiers; Exclusive: S tier; Trashlist: 286 whole-item entries (D-tier and below) | Implicit in filename / tier subfolders (S, A, D-tier trash) | File-level curation; roll notes present in raw text; discarded at `LINE_RE` | `2026-08-27T20:25:09Z` upstream; cached `2026-09-03` | Separate "major-perks" files filter out barrels/mags to focus on traits |
| **MrCharles Configurable Aegis** | Aegis PvE Endgame Analysis (mechanical conversion) | PvE Endgame | 28 split files based on Rank (`MRS`..`MRF`) and perks per column (`PPC0`..`PPC3`); 443KB to 36.7MB | Explicit rank metadata (`S`, `A`, `B`, `C`, `D`, `E`, `F`) in `//notes:` | Detailed notes with Tier, Rank, origin trait, and Aegis quote; discarded at `LINE_RE` | `2026-08-15T00:45:01Z` upstream; evaluated 2026-09-06 | Uses Bungie hash combinations; combinations expand with lower PPC |
| **Nitaraku Aegis List** | Aegis PvE Endgame Analysis (mechanical conversion) | PvE Endgame | 5,022 keep rolls across 968 items; 0 trash entries | Explicit Tier/Rank in `//notes:[Tier: S, Rank: 1]` | Concise notes with Tier, Rank, and reason; discarded at `LINE_RE` | `2026-07-04T08:37:05Z` upstream; cached `2026-09-03` | Focuses strictly on trait columns (traits 1 & 2 only) |

### Parser facts and data loss in current code

In `src/vault_cleaner/wishlist.py`:

- **Note loss at `LINE_RE`:** `LINE_RE = re.compile(r"^dimwishlist:item=(-?\d{1,10})(?:&perks=([\d,]*))?(?:#.*)?$")` ([wishlist.py:29](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/wishlist.py#L29)). The `(?:#.*)?` non-capturing group discards the comment tail. All entry notes, tier ratings (`Tier: S`), and curator attribution are deleted at parse time.
- **Source loss at `merge`:** `Wishlist.merge` ([wishlist.py:51-57](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/wishlist.py#L51-L57)) merges all rolls into unified `keep` and `trash` dictionaries. Once merged, the engine cannot determine whether a roll came from Choosy Voltron or Aegis.

This parser reality is the measured justification for #140 Child 3.

---

## 6. Recommended Aegis-derived source strategy

### One curation family

Ciceron, MrCharles, and Nitaraku are **not independent curators**. All three are mechanical scripts converting a single source of truth: Aegis's PvE Endgame spreadsheet ([https://docs.google.com/spreadsheets/d/1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY](https://docs.google.com/spreadsheets/d/1JM-0SlxVDAi-C6rGVlLxa-J1WGewEeL8Qvq4htWZHhY)). Counting agreement between them as "consensus" is a statistical error. They must be treated as **one curation family** (Aegis PvE Endgame), evaluated against Choosy Voltron as the broad community baseline.

### Strategy recommendation

1. **Broad baseline:** Retain Choosy Voltron as the baseline keep source for general utility and PvP protection.
2. **Endgame keep curation:** Adopt Nitaraku's traits-only feed (`aegis_wishlist.txt`) or Ciceron's `dim_aegis_endgame_major-perks.txt` for endgame keep rolls. Focus on trait columns rather than full 4-perk combinations to avoid false negative mismatches on barrel/mag rolls.
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

**Measured reality:** This statement is **stale**. In `src/vault_cleaner/rules/weapons.py:76-80`, `keep_counts` is used **exclusively** to detect keep-vs-trash conflicts (`keep_counts.get(idx, 0) > 0`). Exact duplicate ranking in `src/vault_cleaner/rules/dupes.py:42-51` uses `RANK_COLUMNS = ["Tier", "Masterwork Tier", "Crafted Level"]` then stat total, then opaque `Id`. Wishlist match counts have **zero** influence on survivor ranking today.

### Authoritative criteria to preserve

1. **Subset combination coverage:** Within the same `Hash`, roll B dominates roll A only if every useful combination on A is covered by B, and B provides at least one additional combination or wins deterministic state ranking.
2. **Review-only initially:** Lower combination count or subset relationship must remain review-only initially and never automatically junk a distinct roll without user approval.
3. **Physical selectable combinations:** Enumerations must evaluate only perk combinations physically selectable on that instance; impossible cross-column combinations must not be formed.
4. **Preserve landed #31 guarantees:** Exact duplicates remain governed by #31's landed deterministic ranking. Useful combinations apply only to non-identical rolls of the same `Hash`.

### Recommendation

**Update Issue #34** to reflect current code state (removing the stale survivor-ranking claim) and position it as the specification for Child 4 of the #140 umbrella. Child 4 should be review-only, producing pairwise dominance comparisons in the review UI for owner decision.

---

## 8. Aggressive weapons-first policy contract

### Policy specification

1. **Selection:** The aggressive policy is selectable via CLI `--policy aggressive` and review server configuration. Default execution remains the conservative maintenance policy.
2. **Weapons-only proposal scope:** The aggressive policy emits removal proposals **exclusively for weapons**.
3. **Armor handling:** Armor is imported and counted for inventory capacity accounting (measuring character and vault capacity), but all armor removal proposals are suppressed at the pipeline boundary. Hiding a UI tab is insufficient; the engine must emit zero armor junk decisions under this policy.
4. **Hard rails:**
   - `Tag in {'favorite', 'keep', 'archive'}` -> HARD
   - `Equipped == 'true'` -> HARD
   - `Crafted == 'crafted'` with level ≥ 10 -> HARD
   - `Crafted == 'crafted'` with empty level -> HARD
   - **`Loadouts != ''` -> HARD** (settled owner decision; Child 2a)
   - Durable vetoes in `overrides.json` -> HARD exclusion
5. **Aegis tier discrimination:**
   - D-tier whole-item trash with no keep match -> Automatic junk candidate.
   - D-tier whole-item trash with Voltron keep match -> Review-only comparison (`#vc-review: aegis-trash-voltron-keep`).
   - Unrated / no Aegis coverage -> `unknown or uncovered`; retained.
6. **Retained alternatives requirement:** Any outclassed-weapon proposal must name an owned, retained weapon instance covering the same role and element. If the alternative is proposed for removal, the recommendation is invalid.
7. **Ruleset and fingerprint effects:** Adding `policy` settings requires projecting the new configuration in `report_run._decision_config` ([report_run.py:173-224](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/report_run.py#L173-L224)) and bumping `RULESET_VERSION` ([report_run.py:44](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/report_run.py#L44)) from `4` to `5`.
8. **No manufactured proposals:** The 100-space goal is a target, not a quota. If justified proposals fall short of 100, the shortfall is reported honestly; rules must never manufacture junk decisions.

---

## 9. Approval-only finalization contract

### Authoritative seam and call sites

The authoritative finalization seam is `review.apply_vetoes` ([review.py:546](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/review.py#L546)) feeding `report.render_import_csv` ([report.py:83](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/report.py#L83)). Both sibling call sites must be updated together:
1. Server: `src/vault_cleaner/server/app.py:790-792`
2. CLI: `src/vault_cleaner/cli.py:484`

### Approval-only rule

Today, `apply_vetoes` is subtractive:
```python
# Current subtractive behavior (review.py:557):
surviving = [d for d in decisions if d.id not in vetoed_ids]
```

In approval-only finalization (Child 2b):
- An item is included in the output CSV **only if explicitly approved** (`verdict == "approve"`).
- Vetoed proposals (`verdict == "veto"`) are excluded.
- Unreviewed proposals (`verdict` unset / unchecked) are **excluded**.

### Durable veto interaction and semantics

- `ReviewManifest.vetoes` and `data/overrides.json` store durable vetoes.
- `review.classify` ([review.py:496-543](file:///c:/Users/raver/Documents/Projects/Personal/vault-cleaner/vault-cleaner/src/vault_cleaner/review.py#L496-L543)) classifies stored vetoes against current proposals. A veto becomes `stale` when `(action, reason)` no longer matches the current proposal. This allows new rules to surface previously vetoed items for fresh review without resetting durable state.
- **Definition:** "Removed" means excluded from the CSV. Vault Cleaner never deletes items or issues automated dismantle commands.

---

## 10. Capacity model and input contract

### Mathematical formula validation

Umbrella Issue #140 defines projected free vault space:

$$\text{projected\_free} = F + D_v - (C - D_c)$$

Where:
- $F$: Current free vault spaces. **Not derivable from DIM export**; must be entered by the user or confirmed against an external baseline.
- $C$: Unequipped items currently on characters intended to be cleared into the vault.
- $D_v$: Unique approved removals from the vault.
- $D_c$: Unique approved removals from characters.
- $C - D_c$: Net character items that must move into the vault.

### Four distinct capacity states

The capacity model must report four distinct states honestly:

1. **Proposed capacity:** Potential capacity if every proposed item (automatic junk + review proposals) were approved: $F + D_{v,\text{prop}} - (C - D_{c,\text{prop}})$.
2. **Explicitly accepted capacity:** Capacity based strictly on user-approved verdicts in the review session: $F + D_{v,\text{acc}} - (C - D_{c,\text{acc}})$.
3. **Finalized-output capacity:** Capacity resulting from the generated DIM import CSV.
4. **Observed / confirmed free space:** Actual empty vault slots verified via a fresh DIM export or user confirmation after in-game dismantling and transfers.

### Input and counting contracts

- **Opaque ID single-counting:** Every removal is counted exactly once by its 64-bit opaque instance `Id`. An item cannot be counted twice across different duplicate or review groups.
- **Negative projections as shortfalls:** If $F - (C - D_c) < 0$, the display must report a shortfall (e.g. "Over capacity by 90 items; 90 removals required before clearing characters"), never an impossible negative capacity.
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
3. **No identifiers:** Never log, print, or commit item names, hashes, instance IDs, or raw CSV rows.
4. **Sanitize evidence:** Transcripts committed under `docs/evidence/` must contain aggregate counts only.

### Aggregate findings on authorized real export (2026-09-06)

Measured on the owner's supplied export of 664 weapons ([docs/evidence/issue-142/README.md](evidence/issue-142/README.md#8-aggregate-only-real-export-analysis-authorized-session-data)):

- **Total weapons:** 664 (555 in Vault, 109 on characters)
- **Equipped weapons:** 9 (3 characters × 3 equipped slots)
- **Unequipped character weapons ($C$):** 100
- **Unique hashes:** 440; **Multi-copy hashes:** 115 hashes account for 339 items.
- **Protection breakdown:**
  - Hard-protected under current rules: 56
  - **Hard-protected with loadouts rail:** 169 (136 weapons in DIM loadouts; 113 incremental)
  - Soft-protected (exotic or locked, not hard-protected): 223 (82 exotic, 141 locked legendary)
  - **Completely unprotected:** 272 (231 in vault, 41 on characters)
- **Baseline yield:**
  - With `--no-wishlists`: 0 junk, 2 review (both exotic Praxic Blade duplicates).
  - With current wishlists: 5 junk (all Ciceron whole-item trash), 6 review (4 locked trash + 2 Praxic Blade). 21 weapons had trash suppressed by keep matches.
- **Required removals for 100-space goal:**
  Given estimated $F \approx 10$ and $C = 100$:
  $$\text{projected\_free} = 10 + D_v - (100 - D_c) \ge 100 \implies D_v + D_c \ge 190$$
  The owner needs **at least 190 approved removals** across vault and characters. Because only 272 weapons are completely unprotected, reaching the goal requires evaluating distinct useful-combination coverage (#34) and reviewing locked/outclassed rolls, rather than relying on exact duplicates alone.

---

## 12. Dependency-ordered child map

| Child | Scope | Depends On | Mechanical Seam | Recommended Review Path | Overlap / Boundaries | Early Deliverable? |
|---|---|---|---|---|---|---|
| **2a** | Hard loadout protection rail for weapons; schema enforcement | #142 | `parse.py:42-44`, `rules/rails.py:30-56`, `tests/fixtures/weapons*.csv` | Independent adversarial review | Touches weapon schema and rails; requires adding loadout fixture test cases | **Yes** (independent safety gate) |
| **2b** | Approval-only finalization seam | #142 | `review.py:546`, `server/app.py:790`, `cli.py:484` | Independent adversarial review | Inverts CSV finalization logic; affects both server and CLI | **Yes** (independent output gate) |
| **3** | Wishlist provenance, attribution, and `#notes:` parsing | #142 | `src/vault_cleaner/wishlist.py:29-100` | Standard review | Parses tier tokens and preserves source attribution; does not change rule logic | Yes |
| **4** | Same-Hash useful-combination coverage (#34) | 2a, 3, #31 | `src/vault_cleaner/rules/` (new module `combinations.py`) | Independent adversarial review | Implements pairwise coverage dominance; review-only initially | No (needs 2a, 3) |
| **5** | Aggressive clear-out policy and weapons-first proposal scope | 2a, 2b, 3, 4 | `src/vault_cleaner/report_run.py`, `config.toml` | Independent adversarial review | Suppresses armor proposals; projects config in `_decision_config`; bumps `RULESET_VERSION` | No (needs 2a, 2b, 4) |
| **6** | Capacity model and progress accounting UI | 2b, 5, #140 | `src/vault_cleaner/ui/`, `duplicate_reference.py` | Standard review | Adds semantic `Owner` parsing for $C$; displays four capacity states | No (needs 2b, 5) |
| **7** | Outclassed / redundant alternative recommendations | 4, 5 | `src/vault_cleaner/rules/` | Independent adversarial review | Recommends replacements across weapons sharing role/element; requires owned retained replacement | No (needs 4, 5) |
| **8** | Validation, real-export dry run, and operating guidance | 2a–7 | `docs/`, `WORKLOG.md` | Standard review | End-to-end dry run verification; operational walkthrough | Final wrap-up |

---

## 13. Open questions requiring an owner decision

1. **Weapon `Loadouts` schema enforcement (Child 2a):**
   Should Child 2a make `Loadouts` strictly required in `REQUIRED_WEAPONS_COLUMNS` (failing loudly if a CSV lacks the header, matching armor/ghost behavior), or degrade gracefully with an explicit error/warning?
   *Recommendation:* Make `Loadouts` required in `REQUIRED_WEAPONS_COLUMNS`. Incomplete exports should fail loudly rather than silently treating all weapons as unprotected.
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

1. **Live Bungie Manifest download:** The ~200MB Bungie manifest download was not executed in this session; measurements utilized the valid local cache at `data/cache/perk-name-map.json` (mtime verified).
2. **MrCharles full matrix run:** The complete 28-file MrCharles wishlist matrix (totaling >200MB) was evaluated via upstream repository inspection, Git tree analysis, and file head samples, but was not imported into `vault-cleaner wishlists` due to memory/cache constraints.
3. **Non-weapon vault inventory:** The supplied real export contained weapons only (`destiny-weapon (12).csv`). Armor, ghost shells, and consumable vault holdings were not measured; total free space $F \approx 10$ is based on owner estimate.
4. **Third-party dates and commits:** External repository commit timestamps (`pushed_at`) and raw file contents are cited to GitHub API queries executed on 2026-09-06.
