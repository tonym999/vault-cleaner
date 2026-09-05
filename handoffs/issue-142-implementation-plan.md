# Issue #142 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#142 — Spike: measure and design the aggressive weapons-first clear-out policy`

**Milestone:** `none` (deliberately unassigned — see *Dependencies and assumptions*)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (independent adversarial) → PR`

**Implementation model selected:** `gemini-3.8-flash` with native `thinking_level = high` (justified below)

**Plan baseline:** `main` at `66b121aee1247d9823e783646f73d470359bb79d` (5 September 2026)

**Allocated implementation branch:** `docs/issue-142-clearout-measurement`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

#142 is the first child of the #140 umbrella: **measurement and policy design**. Its
deliverable is a **document**, not a behaviour change. The implementer measures the
current export schemas, weapon rules, rails, wishlist inputs, finalization seam and
capacity inputs from this baseline, then writes a dated report that fixes the
aggressive weapons-first policy contract and a dependency-ordered map of the
bounded children (#140 items 2a–8) that follow.

Every conclusion in that report becomes the specification other tickets implement.
The report's job is therefore to be **honest and reproducible**, not complete: an
explicit `NOT MEASURED` entry is a correct deliverable, an unsourced number is a
defect.

**No production behaviour changes in this ticket.** No rule, parser, schema,
server, UI, config, `RULESET_VERSION` or fixture change. No issue, project, PR or
branch state outside the allocated branch. No third-party wishlist content is
committed.

## Context & Measurement

Every claim below was measured on the plan baseline
`66b121aee1247d9823e783646f73d470359bb79d`. The implementer must re-run the pinned
commands and record any divergence rather than copying these numbers forward.

### C1 — This ticket ships a document

Precedent for a measurement spike landing as repository documentation rather than
code: the M6 armor spike (#16) produced
[docs/armor-archetypes.md](../docs/armor-archetypes.md), recorded in
[WORKLOG.md](../WORKLOG.md) under `2026-07-19 (M6) — armor measurement spike +
exact-dupe pass (#16, #17)`. The #113 design pass produced
[docs/duplicate-review-count-design.md](../docs/duplicate-review-count-design.md)
with raw captures under [docs/evidence/issue-113](../docs/evidence/issue-113).
This ticket follows the same shape.

### C2 — Export schema reality (measured by header name)

`REQUIRED_*_COLUMNS` in [parse.py](../src/vault_cleaner/parse.py#L36-L75):

| Kind | Required set | `Loadouts` required? |
|---|---|---|
| base (all kinds) | `Name, Hash, Id, Tag, Rarity, Locked, Equipped, Notes` ([parse.py:36-38](../src/vault_cleaner/parse.py#L36-L38)) | — |
| weapons | base + `Type, Ammo, Crafted, Crafted Level, Perks 0` ([parse.py:45-49](../src/vault_cleaner/parse.py#L45-L49)) | **no** |
| ghosts | base + `Loadouts` ([parse.py:47](../src/vault_cleaner/parse.py#L47)) | yes |
| armor | base + `Type, Equippable, Loadouts, Tuning Stat, Seasonal Mod, Holofoil, Masterwork Tier, Power, Tier, Perks 0, Archetype` + the six `ARMOR_STATS` columns ([parse.py:70-76](../src/vault_cleaner/parse.py#L70-L76)) | yes |

Measured fixture headers (`head -1 tests/fixtures/<file>.csv | tr ',' '\n' | nl`):

- `tests/fixtures/weapons.csv` has 74 columns and **does** carry `Owner` (16),
  `Locked` (17), `Equipped` (18), `Crafted` (48), `Crafted Level` (49),
  `Kill Tracker` (50), `Loadouts` (52), `Notes` (53), `Perks 0..20` (54–74).
- `tests/fixtures/armor.csv` carries `Loadouts` (38); `tests/fixtures/ghosts.csv`
  carries `Loadouts` (17) and has no `Type` column.

Measured cell content across every fixture:

```text
armor.csv                  rows=15 | Loadouts nonempty=0 | Equipped=['false']          | Owner=['Vault']
armor_classes.csv          rows= 4 | Loadouts nonempty=0 | Equipped=['false']          | Owner=['Hunter(550)','Titan(550)','Vault']
armor_close.csv            rows=34 | Loadouts nonempty=0 | Equipped=['false','true']   | Owner=['Vault']
armor_dupes.csv            rows=32 | Loadouts nonempty=2 | Equipped=['false','true']   | Owner=['Vault']
armor_duplicates_ui.csv    rows= 3 | Loadouts nonempty=0 | Equipped=['false','true']   | Owner=['Hunter(550)','Vault']
armor_same_stat_four_ui.csv rows=4 | Loadouts nonempty=1 | Equipped=['false']          | Owner=['Titan(415)','Vault']
armor_same_stat_ui.csv     rows= 2 | Loadouts nonempty=0 | Equipped=['false']          | Owner=['Vault']
ghosts.csv                 rows= 2 | Loadouts nonempty=0 | Equipped=['false','true']   | Owner=['Hunter(506)','Vault']
ghosts_cleanup.csv         rows= 7 | Loadouts nonempty=1 | Equipped=['false','true']   | Owner=['Titan(550)','Vault']
weapons.csv                rows= 3 | Loadouts nonempty=0 | Equipped=['false','true']   | Owner=['Titan','Vault']
weapons_dupes.csv          rows=18 | Loadouts nonempty=0 | Equipped=['false','true']   | Owner=['Vault']
weapons_hostile.csv        rows=10 | Loadouts nonempty=0 | Equipped=['false']          | Owner=['Vault']
weapons_slammer_like.csv   rows= 5 | Loadouts nonempty=0 | Equipped=['false']          | Owner=['Vault']
```

Three consequences the report must state explicitly:

1. **No weapon fixture carries a single non-empty `Loadouts` cell** (0 of 36 weapon
   rows across four fixtures). Loadout protection for weapons has **zero** committed
   behavioural coverage today, and `Loadouts` is not weapon-schema-required, so a
   DIM export that dropped the column would load silently. That is the measured
   basis for #140 child 2a and for a fail-safe requirement.
2. `Owner` is not a stable identifier. Weapons use bare `Titan`; armor and ghosts use
   `Titan(550)` / `Hunter(506)`. Nothing in `src/` parses `Owner` beyond copying it
   into `Decision.location`. Character-vs-vault accounting therefore has **no**
   current implementation and no measured format contract.
3. No export column reports vault capacity or free spaces. `F` in the #140 capacity
   formula is not derivable from any export.

### C3 — Weapon rule, rail and review reality

Rails ([rails.py:30-56](../src/vault_cleaner/rules/rails.py#L30-L56)), in precedence
order: `Tag ∈ {favorite, keep, archive}` → HARD; `Equipped` true → HARD; crafted with
empty level → HARD `crafted-lvunknown`; crafted level ≥ `crafted_level_protect`
(config `rails.crafted_level_protect = 10`) → HARD; `Rarity == "Exotic"` → SOFT;
`Locked` true → SOFT; otherwise unprotected. **There is no loadout rail.** Only
[ghosts.py:36](../src/vault_cleaner/rules/ghosts.py#L36) and
[armor_dupes.py:100](../src/vault_cleaner/rules/armor_dupes.py#L100) read `Loadouts`;
`report_run.py:317` records `in_loadout` for presentation only.

Weapons pass ([weapons.py:58-111](../src/vault_cleaner/rules/weapons.py#L58-L111)):
rails → wishlist trash → exact-roll dupes. A keep match suppresses a trash decision
and increments `keep_trash_conflicts`
([weapons.py:79-80](../src/vault_cleaner/rules/weapons.py#L79-L80)). `keep_counts`
is computed for every row but is now **only** used for that conflict test — it no
longer ranks dupe survivors, confirming that #34's "wishlist counts influence
survivor ranking" statement is stale. Trash-junked ids are removed from the dupe
pool ([weapons.py:100-104](../src/vault_cleaner/rules/weapons.py#L100-L104)).

Exact-dupe identity and ranking live in
[dupes.py](../src/vault_cleaner/rules/dupes.py) — `RANK_COLUMNS = ["Tier",
"Masterwork Tier", "Crafted Level"]` then stat total then opaque id
([dupes.py:44-52](../src/vault_cleaner/rules/dupes.py#L44-L52)). These are #31's
landed guarantees and are **out of scope to change**.

Measured baseline yield on committed fake data:

```bash
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons.csv --armor tests/fixtures/armor.csv --ghosts tests/fixtures/ghosts.csv --no-wishlists
```

```text
would junk 1 item(s) and flag 5 for review
JUNK ghost-unprotected-surplus (ghosts) — 1 item(s)
REVIEW armor-similar to (armor) — 3 item(s)
REVIEW armor-last-archetype (armor) — 1 item(s)
REVIEW armor-score (armor) — 1 item(s)
```

The weapons section contributes **zero** decisions there. The weapon volume lives in
the dupe fixture:

```bash
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_dupes.csv --no-wishlists
```

```text
would junk 4 item(s) and flag 3 for review
JUNK dupe-lower (weapons) — 3 item(s)      ids 3002, 3022, 3032
JUNK dupe-tie (weapons) — 1 item(s)        id 3042
REVIEW dupe-lower (weapons) — 2 item(s)    ids 3003 (locked), 3012 (exotic)
REVIEW dupe-tie (weapons) — 1 item(s)      id 3052 (exotic)
```

(That invocation also prints two `skipping armor/ghosts: … not found` warnings; they
are expected and belong in the recorded output.)

### C4 — Wishlist reality

Configured sources ([config.toml](../config.toml) `[wishlists.sources]`):
`choosy_voltron` (48klocs), `aegis` (Nitaraku), `aegis_trash` (Ciceron). Measured
against the locally cached copies on the baseline:

```bash
.venv/bin/vault-cleaner wishlists
```

```text
choosy_voltron: 255373 keep rolls across 1234 items, 53 trash entries across 53 items
aegis: 5022 keep rolls across 968 items, 0 trash entries across 0 items
aegis_trash: 0 keep rolls across 0 items, 286 trash entries across 286 items
total: 260395 keep rolls, 339 trash entries
```

These numbers came from a **stale local cache** on the planner's machine
(`wishlists/` is gitignored, [.gitignore:5](../.gitignore#L5)) and are a shape
reference, not a freshness claim. The implementer must re-derive them and record the
actual fetch/check dates.

Parser facts the report must carry
([wishlist.py](../src/vault_cleaner/wishlist.py)):

- `LINE_RE` ([wishlist.py:27](../src/vault_cleaner/wishlist.py#L27)) discards the
  `#notes:` tail entirely. **Entry notes, tier text and source attribution are lost
  at parse time**, before any merge.
- `Wishlist.merge` ([wishlist.py:56-63](../src/vault_cleaner/wishlist.py#L56-L63))
  folds every source into one `keep`/`trash` map keyed by item hash. After
  `load_all_with_sources` ([wishlist.py:160-189](../src/vault_cleaner/wishlist.py#L160-L189))
  the merged `Wishlist` cannot say which source contributed a roll — only the exact
  bytes per source survive, as `WishlistSourceData`.
- Wildcard item `69420` entries are counted and skipped
  ([wishlist.py:20](../src/vault_cleaner/wishlist.py#L20)); malformed
  `dimwishlist:` lines increment `skipped`.
- A trash entry with an empty perk set means whole-item trash
  ([weapons.py:51-56](../src/vault_cleaner/rules/weapons.py#L51-L56)).

Perk name→hash resolution needs the Bungie manifest cache
(`data/cache/perk-name-map.json`, ~410 KB on the planner's machine, rebuilt from a
~200 MB download). **The plan does not require the implementer to download it** —
see the measurement contract in *Proposed Plan & Scope*.

### C5 — Finalization and veto reality

The authoritative "what reaches the import CSV" seam is
[review.apply_vetoes](../src/vault_cleaner/review.py#L546) feeding
[report.render_import_csv](../src/vault_cleaner/report.py#L83). It has exactly two
call sites, and they must be treated as siblings:

- server: [app.py:790-792](../src/vault_cleaner/server/app.py#L790-L792)
- CLI: [cli.py:484](../src/vault_cleaner/cli.py#L484)

`apply_vetoes` currently **subtracts** vetoed ids from every section's decisions —
so today an unreviewed proposal is included. #140 child 2b inverts that to
approval-only. The report must name both call sites, not just the server one.

`classify` ([review.py:496-545](../src/vault_cleaner/review.py#L496-L545)) sorts
persisted vetoes into active / stale / orphaned / unchecked, and a veto goes stale
when `(action, reason)` no longer matches the current proposal. That is the exact
mechanism by which a new aggressive profile would resurface previously vetoed items
for re-review — the report must state this rather than proposing a veto reset (#114
owns that).

`RULESET_VERSION = 4` ([report_run.py:44](../src/vault_cleaner/report_run.py#L44))
is baked into `compute_fingerprint`
([report_run.py:241-258](../src/vault_cleaner/report_run.py#L241-L258)); any new
rule-consumed config key must also be projected in `_decision_config`
([report_run.py:173-224](../src/vault_cleaner/report_run.py#L173-L224)), which today
projects only `rails.crafted_level_protect` and the `armor.*` keys.

### C6 — Model verification and selection

Re-verified against the provider's own thinking-controls documentation on
**5 September 2026**: `gemini-3.8-flash` supports `thinking_level` values `low`,
`medium`, `high`; `minimal` is **not** supported on this model (it is available on
`gemini-3.5-flash` / `gemini-3.5-flash-lite` and other older flash variants). This
matches the repository matrix in
[handoffs/README.md](../handoffs/README.md#model-family--provider-native-reasoning-effort-matrix)
(verified 2026-09-03). `high` is therefore the maximum native effort available for
the selected model.

**Selection:** `gemini-3.8-flash` at `thinking_level = high`, at the vault owner's
explicit direction for this ticket. Stated plainly: the repository matrix maps
*Planning*-class work (codebase research, measurement, staleness resolution) to a
higher tier, and this ticket is investigative. The owner's selection stands; this
plan compensates for the tier gap rather than arguing with it, by:

- fixing the deliverable's **exact section skeleton** so no document architecture
  has to be invented;
- pinning every measurement to a **verbatim command** with an expected result, so
  measurement is reproduction rather than design;
- forbidding any source edit at all, so the blast radius of a mistake is a document;
- requiring **independent adversarial review** with a re-run of every quoted command.

`gemini-3.8-flash` has recent precedent in this repository as the implementer tier
for #117 (see [WORKLOG.md](../WORKLOG.md) `2026-09-05 — #117 planning`).

## Dependencies and assumptions

- **#142 is open**, labelled `question`, unassigned to a milestone, and `Todo` on
  [project 3](https://github.com/users/tonym999/projects/3) — all verified on
  5 September 2026. Leave the milestone unassigned; no existing milestone covers a
  cross-cutting weapons/wishlist/capacity investigation, and `AGENTS.md` forbids
  creating a one-off.
- **Parent #140 is open** and is the requirements authority together with its
  dependency-ordered tracking comment of 2026-09-05. #142 is item **1** of that
  list. The settled owner decisions in the #142 body (loadout hard protection,
  review-only useful-combination dominance, approval-only CSV, "removed" = excluded
  from CSV, four capacity states, one Aegis strategy) are **inputs**, not open
  questions.
- **#31 is closed** (M6). Its exact-roll identity and ranking guarantees are
  authoritative and untouchable here.
- **#34 is open** (M6 — Armor dupes, despite being a weapons ticket) and overlaps
  section 7 of the report. This ticket may **recommend** a reconciliation; it must
  not create, edit, relabel, re-milestone or comment on #34. Confirmed stale in #34:
  "[the count] currently influences same-Hash survivor ranking" — measured false at
  this baseline (C3).
- **#114 is open** and owns veto reset. **#117 is open** and owns per-group DIM
  search generation for armor groups. **#136 / #137 / #138 are open** and own the
  Jinja/design work. None of them may be extended, repurposed or depended on here.
- No fresh real vault export accompanies this ticket. All committed evidence comes
  from `tests/fixtures/`. The report specifies the private real-export procedure but
  does not execute it.
- Network access for wishlist fetching may or may not be available to the
  implementer's runtime. Both outcomes are acceptable; a fabricated one is not. See
  stop condition S5.
- `wishlists/` and `data/` are gitignored ([.gitignore:2](../.gitignore#L2),
  [.gitignore:5](../.gitignore#L5)). Do not weaken either.
- Divergence from the issue body: the #142 body says "Baseline checked for issue
  creation: `main` at `66b121ae…`". That is still `main`'s head at planning time, so
  the issue body is **not** stale. If `main` has advanced when the implementer
  starts, branch from the new `main`, record the new base SHA, and re-run every
  pinned command before quoting a number.

## Proposed Plan & Scope

Exactly three tracked paths change. Nothing else.

### The measurement report

#### [NEW] [docs/aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md)

The report. Its **required top-level section skeleton is fixed by this plan** — use
these fourteen `##` headings, in this order, with these numbers. Sections may gain
sub-headings and tables; they may not be renamed, reordered, merged or omitted. A
section with nothing measurable in it says so and lists what would be needed.

```text
# Aggressive weapons-first clear-out — measurement and policy design

## 1. Scope, baseline and reproduction
## 2. Export schema and completeness by header name
## 3. Current weapon rules, rails and review behaviour
## 4. Proposal-strength taxonomy
## 5. Wishlist source and evidence evaluation
## 6. Recommended Aegis-derived source strategy
## 7. #34 reconciliation recommendation
## 8. Aggressive weapons-first policy contract
## 9. Approval-only finalization contract
## 10. Capacity model and input contract
## 11. Yield: fake-data evidence and privacy-safe real-export procedure
## 12. Dependency-ordered child map
## 13. Open questions requiring an owner decision
## 14. Limitations and NOT MEASURED register
```

Required content, per section:

**1. Scope, baseline and reproduction.** Dated (ISO `YYYY-MM-DD`). Records the base
SHA the implementer branched from, the Python and pandas versions
(`.venv/bin/python -c "import sys, pandas; print(sys.version); print(pandas.__version__)"`),
and the statement that this document changes no production behaviour. Opens with the
**evidence rule**, verbatim:

> Every number in this document is followed by the exact command that produced it.
> A claim without a command, or with a command that was not run in this session, is
> recorded in section 14 as `NOT MEASURED`.

**2. Export schema and completeness by header name.** The three `REQUIRED_*_COLUMNS`
sets with `parse.py` line citations; the measured fixture header lists; the
fixture-content table from C2 (re-derived). Must state, as findings:
(a) `Loadouts` is present in weapon exports but **not** weapon-schema-required and
carries **no** non-empty cell in any committed weapon fixture; (b) `Owner` has two
observed formats (`Titan` vs `Titan(550)`) and is parsed nowhere; (c) no export
column reports vault capacity or free space; (d) the required fail-safe behaviour
when `Loadouts` is absent or empty — a *missing* protection input must not silently
read as "not in a loadout". Distinguish, one row each: equipped state, character
location, saved-loadout membership, DIM protective tags, crafted protection, locked,
exotic, durable veto. State that opaque `Id`/`Hash` remain strings throughout.

**3. Current weapon rules, rails and review behaviour.** The rail precedence table
from C3 with line citations; the weapons pass order; the keep-beats-trash conflict
path and its counter; the trash-junk pool exclusion; the exact-dupe identity and
ranking summary with a pointer to #31 rather than a restatement; the ungroupable
fail-safe. Includes the two measured `report` runs from C3 verbatim (command +
output). Names the finalization seam and both call sites from C5.

**4. Proposal-strength taxonomy.** Defines exactly four classes — `automatic junk
candidate`, `review-only comparison`, `protected / retained`, `unknown or
uncovered` — and maps every reason slug the current weapon pipeline can emit
(`wishlist-trash whole-item`, `wishlist-trash roll`, `dupe-lower`, `dupe-tie`, and
their `#vc-review` variants) into exactly one class. States that "no wishlist
coverage" and "unknown roll identity" land in `unknown or uncovered` and are never
trash evidence.

**5. Wishlist source and evidence evaluation.** One row per candidate — Choosy
Voltron, Ciceron Aegis lists, MrCharles configurable Aegis lists, Nitaraku Aegis
list — with, where obtainable: upstream curation family; activity scope and role
semantics; weapon and current-`Hash` coverage; tier/quality metadata; entry notes and
attribution; source-content revision, generated-file date, successful check date;
fetch/cache behaviour; parsing confidence and malformed/skipped counts; conflict
behaviour; whether base/enhanced variants normalize without guessing. Must record the
parser facts from C4 — notes discarded at `LINE_RE`, attribution lost at `merge` —
as the measured reason child 3 exists. Anything not obtained is `NOT MEASURED`, not
estimated.

**6. Recommended Aegis-derived source strategy.** One recommendation with its
evidence, treating all Aegis conversions as **one curation family** (never as
independent consensus votes) and Choosy Voltron separately as the broad baseline.
States the uncertainty rules: missing coverage, stale or failed sources, unknown
tiers and absent PvP evidence remain explicit uncertainty. States that no third-party
wishlist snapshot is committed.

**7. #34 reconciliation recommendation.** Lists which #34 statements are stale
against this baseline (at minimum the survivor-ranking claim measured false in C3),
which acceptance criteria remain authoritative, and a single recommendation —
update / split / use as-is — with reasoning. Records that the recommendation is
**advisory**: acting on it needs a separately authorized issue operation. States the
measured inputs a useful-combination enumeration would need and why the first version
stays review-only and separate from exact duplicates and wishlist-trash.

**8. Aggressive weapons-first policy contract.** How the profile is selected; the
weapons-only removal-proposal boundary expressed at the Python pipeline/output seam
(explicitly: not a hidden UI tab); armor still imported and counted while armor
removal proposals are suppressed; treatment of broad keep matches, Aegis tiers,
explicit trash evidence, PvP uncertainty, personal-use exceptions, distinct useful
coverage and owned-and-retained alternatives; the fingerprint / `_decision_config` /
`RULESET_VERSION` consequences from C5; and stop conditions for unsupported role
inference and cross-`Hash` comparison. Must state that the 100-space goal never
justifies manufacturing proposals, and that cross-`Hash` recommendations are deferred
unless explicit role and activity metadata supports them.

**9. Approval-only finalization contract.** The current subtractive behaviour of
`apply_vetoes` and both call sites; the exact seam that changes; the resulting rule
(approved included; vetoed and unreviewed excluded); how fresh session verdicts and
durable vetoes interact without resetting durable state (#114 not repurposed); and
that "removed" means excluded from the CSV — vault-cleaner never deletes.

**10. Capacity model and input contract.** Validates `projected_free = F + Dv - (C - Dc)`
against the measured inputs. Defines input and display contracts for `F`, `C`, `Dv`,
`Dc`; the four distinct states (proposed removals / explicitly accepted removals /
finalized-output removals / observed or user-confirmed free space); counting each
item **once** by opaque instance `Id`; incomplete exports, omitted categories and
negative projections labelled as shortfalls; and the fresh-export-or-user-confirmation
requirement. Must state, from C2, that `F` is not derivable from any export and that
`Owner` parsing does not exist yet — so `C` needs a defined, measured derivation
before child 6. Must state that an approval, tag, Notes update or CSV download is
never evidence of a dismantle or transfer.

**11. Yield: fake-data evidence and privacy-safe real-export procedure.** The
reproducible fake-data measurement (commands + outputs) as the committed evidence.
Then the procedure for estimating real cleanup yield from a private export:
aggregate-only outputs, no rows, names, hashes or instance ids recorded, nothing
under `data/` committed, and where the aggregates would be written when a fresh
export is later authorized. The procedure is **specified, not executed**.

**12. Dependency-ordered child map.** A table over #140 items 2a–8 with, per child:
scope in one sentence; depends-on; mechanical boundary (the seam it may touch);
recommended review path; overlap with other children; and whether it is
independently deliverable early. Loadout protection (2a) and approval-only
finalization (2b) must be shown as independently deliverable. No child issue is
created by this ticket.

**13. Open questions requiring an owner decision.** Anything the measurement could
not settle, phrased as a decision the owner can make.

**14. Limitations and NOT MEASURED register.** Every command that could not be run
and why; every claim carried from an external source rather than measured; the stale
or absent inputs.

#### [NEW] [docs/evidence/issue-142/README.md](../docs/evidence/issue-142/README.md)

Verbatim command transcripts backing section 11 and any quoted output too long for
the report body. Plain text only — no images, no binaries, no third-party wishlist
content, no real export rows, names, hashes or instance ids. Follows the shape of
[docs/evidence/issue-113/README.md](../docs/evidence/issue-113/README.md).

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

One dated entry at the top (newest first), following the existing heading style:
`## 2026-MM-DD — #142: aggressive weapons-first measurement and policy design (PR 2)`.
Record what was measured, what was decided, what could not be measured and why, and
anything surprising for the next agent — at minimum the weapon-`Loadouts` coverage
gap and the wishlist attribution/notes loss, if they reproduce.

### Measurement contract

These commands are the measurement. Run them from the repository root on the
implementation branch, and paste **actual** output — never edited, never predicted.

```bash
.venv/bin/python -c "import sys, pandas; print(sys.version); print(pandas.__version__)"
```

```bash
head -1 tests/fixtures/weapons.csv | tr ',' '\n' | nl
head -1 tests/fixtures/armor.csv | tr ',' '\n' | nl
head -1 tests/fixtures/ghosts.csv | tr ',' '\n' | nl
```

```bash
.venv/bin/python - <<'PY'
import pandas as pd, glob, os
for p in sorted(glob.glob("tests/fixtures/*.csv")):
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    cols = set(df.columns)
    nz = lambda c: int(df[c].str.strip().ne("").sum()) if c in cols else None
    print(os.path.basename(p), "rows=", len(df),
          "| Loadouts nonempty=", nz("Loadouts"),
          "| Equipped=", sorted(set(df["Equipped"])) if "Equipped" in cols else None,
          "| Owner=", sorted(set(df["Owner"])) if "Owner" in cols else None,
          "| Tag=", sorted(set(df["Tag"])) if "Tag" in cols else None)
PY
```

```bash
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons.csv --armor tests/fixtures/armor.csv --ghosts tests/fixtures/ghosts.csv --no-wishlists
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_dupes.csv --no-wishlists
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_hostile.csv --no-wishlists
.venv/bin/vault-cleaner report --weapons tests/fixtures/weapons_slammer_like.csv --no-wishlists
```

```bash
.venv/bin/vault-cleaner wishlists
```

Rules for this contract:

- `--no-wishlists` is **mandatory** for the `report` runs. The wishlist-matched path
  needs the Bungie perk-name manifest (a ~200 MB download cached under the gitignored
  `data/cache/`), and this ticket must not require it. If the manifest cache already
  exists locally, an additional wishlist-enabled run may be recorded as
  supplementary, clearly labelled with the manifest version and the fact that it is
  environment-dependent.
- Every `report` run is a dry run. **Never** pass `--write`.
- Any additional analysis is an inline `.venv/bin/python - <<'PY' … PY` heredoc
  quoted into the report or evidence file. **Do not add a file under `scripts/`** —
  that is production surface and out of scope.
- Wishlist source evaluation may fetch candidate lists (`.venv/bin/vault-cleaner
  wishlists --refresh`, or reading the upstream repositories) into the gitignored
  `wishlists/` cache or the session scratch directory only. Quote **counts and
  metadata**; never paste wishlist entry lines or item hashes into a tracked file,
  and never commit a snapshot.
- If a command fails or is blocked, record the command, the failure, and a section-14
  `NOT MEASURED` entry. Do not substitute a plausible number, and do not copy the
  numbers quoted in this handoff as if they were freshly measured.

### Verification

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check origin/main...HEAD
git status --porcelain
git ls-files data/
git ls-files wishlists/
```

`ruff` and `pytest` must pass unchanged — this ticket alters no Python, so a failure
means something outside the intended scope moved. The last two commands must print
nothing. The Playwright browser suite is **not** required and must not be claimed: no
UI, JS, CSS or server file changes here. If a change would touch one, that is stop
condition S1.

## Mechanical inclusion test

A proposed change is **in scope** if and only if all of the following hold:

- it adds or edits lines in exactly one of: `docs/aggressive-clearout-measurement.md`,
  `docs/evidence/issue-142/**`, `WORKLOG.md`; and
- it records a measurement, a policy definition, a recommendation, a child-ticket
  boundary, or an explicit limitation for #142; and
- every number it states is accompanied by a command that was actually run in this
  session; and
- it contains no real vault row, item name, `Hash`, instance `Id`, or third-party
  wishlist entry line.

Worked examples:

- **IN SCOPE:** recording that all four committed weapon fixtures have a `Loadouts`
  header with zero non-empty cells, quoting the command and its output, and
  concluding that #140 child 2a needs both a schema decision and new fixture rows.
- **IN SCOPE:** a section-5 table row stating that Nitaraku's list parses to
  N keep rolls across M items with 0 trash entries, with the `vault-cleaner
  wishlists` output quoted and the cache date recorded.
- **IN SCOPE:** specifying in section 9 that approval-only finalization must change
  `review.apply_vetoes` behaviour at **both** `cli.py:484` and `app.py:790` and
  citing them.
- **IN SCOPE:** a section-14 entry: "MrCharles list coverage — NOT MEASURED; the
  runtime had no network access; the fetch command attempted was …".
- **OUT OF SCOPE:** adding `"Loadouts"` to `REQUIRED_WEAPON_COLUMNS` in `parse.py`,
  or a loadout branch in `rails.protection` — that is child 2a.
- **OUT OF SCOPE:** changing `apply_vetoes` to include only approvals — that is
  child 2b.
- **OUT OF SCOPE:** adding an `[aggressive]` table to `config.toml`, projecting a new
  key in `_decision_config`, or bumping `RULESET_VERSION`.
- **OUT OF SCOPE:** adding rows to `tests/fixtures/weapons*.csv` to demonstrate
  loadout membership, or adding a new test file. This ticket measures the gap; it
  does not close it.
- **OUT OF SCOPE:** adding a source or trash list to `[wishlists.sources]`, or
  committing any file under `wishlists/`.
- **OUT OF SCOPE:** creating, editing, labelling, re-milestoning, closing or
  commenting on #34 or any other issue; creating the child issues; opening a PR;
  pushing any branch other than the allocated one.
- **OUT OF SCOPE:** a new file under `scripts/`, a new runtime dependency, or a
  `pyproject.toml` edit.

### Stop conditions

Stop implementation and return to the orchestrator if:

- **S1.** Any change would be needed outside the three allowed paths — including a
  "trivial" typo fix in `src/`, a fixture row, or a config key.
- **S2.** A measurement contradicts one of the settled owner decisions in the #142
  body (loadout hard protection, review-only useful-combination dominance,
  approval-only CSV output, four capacity states, one Aegis curation family), or
  shows one cannot be implemented safely.
- **S3.** Reaching a defensible conclusion would require weakening an existing hard
  or soft rail, #31's exact-roll guarantees, or a durable veto.
- **S4.** A real vault export is required to settle a question the report must
  answer, and none is available.
- **S5.** Network access is unavailable **and** the report cannot honestly complete
  sections 5 and 6 from cached or documented evidence. Record what was attempted;
  do not invent source metadata. (A partial section 5 with explicit section-14
  entries is a valid deliverable, not a stop condition — S5 fires only if the whole
  source comparison is impossible.)
- **S6.** `main` has advanced such that a pinned command's output diverges from this
  handoff in a way that changes a conclusion.
- **S7.** The child map cannot be made dependency-ordered without either overlapping
  an existing open ticket's ownership (#34, #114, #117, #136, #137, #138) or
  weakening a rail to reach the 100-space target.
- **S8.** `.venv/bin/ruff check src tests scripts` or `.venv/bin/pytest -q` fails on
  a branch that changes no Python.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Unsourced or carried-over numbers.** The highest-probability defect by far: the
   report quotes a fixture count, a wishlist total or a coverage percentage that was
   copied from this handoff, invented, or produced by a command that was never run.
   Every number in the report must be re-derivable by re-running the quoted command;
   the reviewer should re-run all of them and diff.
2. **Scope leak into production files.** A "helpful" one-line fix — adding
   `Loadouts` to `REQUIRED_WEAPON_COLUMNS`, a loadout branch in `rails.protection`,
   a fixture row with a populated `Loadouts` cell, or a `scripts/` measurement
   helper. All are children 2a/3, not this ticket.
3. **Leaked untrusted or private content.** Third-party wishlist entry lines, item
   hashes or tier text pasted into `docs/`, a committed file under `wishlists/`, or
   real export rows/ids. `git ls-files data/` and `git ls-files wishlists/` must both
   be empty, and the diff must contain no `dimwishlist:` line.
4. **Aegis conversions double-counted, or freshness overstated.** Section 6 treating
   Ciceron / MrCharles / Nitaraku as three independent curators rather than one
   curation family, or presenting locally cached list statistics as current upstream
   coverage without recording the fetch/check date.
5. **A hollow section.** One or more of sections 7, 10 and 12 reduced to a
   restatement of the issue body — no measured input, no seam citation, no decision
   — while still reading as complete. Section 14 empty is itself a signal: a spike
   this broad, run without a real export, has limitations.

# Reusable implementer execution prompt

Implement issue #142 in `tonym999/vault-cleaner` using the committed handoff on
`main` at:

```text
handoffs/issue-142-implementation-plan.md
```

Read the entire handoff, issue #142, its parent issue #140 and #140's
dependency-ordered tracking comment, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and
the current source files it cites before writing anything.

This ticket produces **documentation only**. It changes no Python, no config, no
fixture, no test, and no issue or project state.

Rules:
- work on `docs/issue-142-clearout-measurement`; branch from latest `main` and record
  the base SHA;
- change only `docs/aggressive-clearout-measurement.md`,
  `docs/evidence/issue-142/**`, and `WORKLOG.md`; apply the plan's mechanical
  inclusion test to every hunk;
- use the plan's fixed fourteen-section skeleton for the report, in order, unrenamed;
- run every command in the plan's measurement contract and quote the **actual**
  output; where a command cannot be run, record it in section 14 as `NOT MEASURED`
  with the reason. Never copy a number from the handoff as if you measured it;
- never pass `--write`; never commit anything under `data/` or `wishlists/`; never
  paste a real export row, item name, `Hash`, instance `Id`, or a `dimwishlist:`
  entry line into a tracked file;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`,
  `.venv/bin/pytest -q`, `git diff --check origin/main...HEAD`,
  `git status --porcelain`, `git ls-files data/`, `git ls-files wishlists/`. The
  browser suite is not applicable to this ticket and must not be claimed as run;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition (S1–S8) is reached, stop implementation and return to the
orchestrator with the exact conflict; do not broaden scope.

When complete, provide the full implementer → orchestrator handoff: branch, base and
head SHAs, changed files, every command run with its result, every `NOT MEASURED`
entry, and any deviation from the plan.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
The diff is documentation-only and touches no runtime code, which understates the
risk. This report is the **specification** for #140 children 2a–8: a wrong measured
claim here (for example, asserting that weapon exports carry usable `Loadouts` data,
or naming only one of the two `apply_vetoes` call sites) propagates directly into a
protection rail and a finalization change, which are exactly the categories #140
requires adversarial review for. The dominant failure mode of a document deliverable
is unverifiable assertion, and that failure is invisible to a checklist read — it is
only caught by an independent session re-running the commands and diffing the
outputs. The implementer tier selected for this ticket is below the repository
matrix's Planning-class recommendation, which raises that same risk rather than
lowering it.

The reviewer's remit is unusual for this repository and should be stated at dispatch:
**re-run every command quoted in the report and in `docs/evidence/issue-142/`, and
compare the recorded output to the actual output.** A quoted output that does not
reproduce is a P1 finding. A number with no command is a P1 finding. The reviewer
must also read the report for hollow sections, not only for false ones.

The orchestrator confirms the path against the real diff and, when adversarial review
is required, selects and records the reviewer's exact provider, model ID, and native
effort at dispatch time.

# Review checklist

- [ ] **Check 1 — scope.** `git diff --name-only <base_sha>...HEAD` lists only
      `docs/aggressive-clearout-measurement.md`, paths under
      `docs/evidence/issue-142/`, and `WORKLOG.md`. No `src/`, `tests/`, `scripts/`,
      `config.toml`, `pyproject.toml`, or `.gitignore` change. `RULESET_VERSION` is
      still `4`.
- [ ] **Check 2 — reproduction.** Every command quoted in the report and evidence
      file was re-run independently and its output matches what the report records.
      Divergences are either explained in the report or raised as findings.
- [ ] **Check 3 — no unsourced numbers (likely finding 1).** Every numeric claim has
      an adjacent command. Spot-check that the fixture counts, the two `report` run
      summaries and the wishlist statistics are the implementer's own measurements
      and not the handoff's values carried over verbatim without a re-run.
- [ ] **Check 4 — skeleton.** All fourteen `##` sections are present, in order, with
      the specified names. None is a restatement of the issue body without measured
      input, seam citation or a decision (likely finding 5). Section 14 exists and is
      non-empty, or its emptiness is justified.
- [ ] **Check 5 — schema findings.** Section 2 states the weapon `Loadouts` gap
      (header present, not schema-required, zero non-empty cells across all committed
      weapon fixtures), the two `Owner` formats, the absence of any vault-capacity
      column, and the required fail-safe when the protection input is missing.
- [ ] **Check 6 — seams.** Section 9 names **both** `apply_vetoes` call sites
      (`src/vault_cleaner/cli.py:484` and `src/vault_cleaner/server/app.py:790`) and
      describes today's subtractive behaviour correctly. Section 8 names
      `report_run._decision_config` and `RULESET_VERSION` as consequences of adding a
      rule-consumed config key.
- [ ] **Check 7 — sources (likely finding 4).** Section 6 recommends exactly one
      Aegis-derived strategy, treats Ciceron / MrCharles / Nitaraku as one curation
      family, keeps Choosy Voltron separate as the broad baseline, and records
      fetch/check dates rather than presenting cached statistics as current.
- [ ] **Check 8 — privacy and untrusted content (likely finding 3).**
      `git ls-files data/` and `git ls-files wishlists/` are both empty. The diff
      contains no `dimwishlist:` line, no real item name, `Hash` or instance `Id`,
      and no committed third-party snapshot.
- [ ] **Check 9 — ownership.** #34, #114, #117, #136, #137 and #138 are only
      referenced and reconciled in prose. No issue, label, milestone, project field,
      comment or PR changed. No child issue was created.
- [ ] **Check 10 — capacity honesty.** Section 10 counts by opaque `Id` once, defines
      all four capacity states distinctly, treats a negative projection as a
      shortfall, states that `F` is not derivable from any export, and states that an
      approval, tag, Notes edit or CSV download is not evidence of a dismantle or
      transfer.
- [ ] **Check 11 — verification.** `.venv/bin/ruff check src tests scripts`,
      `.venv/bin/pytest -q` and `git diff --check <base_sha>...HEAD` were re-run by
      the reviewer and pass. The browser suite is correctly recorded as not
      applicable rather than as passed or skipped-without-comment.
- [ ] **Check 12 — worklog.** `WORKLOG.md` has one new dated entry at the top,
      newest-first, recording what was measured, what was decided, what could not be
      measured, and the surprises worth carrying forward.

# Dispatch comment draft

Planned #142 in [handoffs/issue-142-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-142-implementation-plan.md) on `main`.

- **Implementer tier & effort:** `gemini-3.8-flash`, native `thinking_level = high`
  (owner-selected; `high` is the maximum effort this model supports, re-verified
  2026-09-05)
- **Implementation branch:** `docs/issue-142-clearout-measurement`
- **Deliverable:** documentation only — `docs/aggressive-clearout-measurement.md`
  (fixed fourteen-section skeleton), `docs/evidence/issue-142/README.md`, and a
  `WORKLOG.md` entry. No rule, parser, schema, config, fixture, server, UI or
  `RULESET_VERSION` change; no child issue created.
- **Likely findings:** unsourced or carried-over numbers; scope leak into `src/` or
  `tests/fixtures/` (especially a premature `Loadouts` schema or rail change); leaked
  third-party wishlist entries or private export content; Aegis conversions
  double-counted as independent curators or cached statistics presented as current;
  hollow sections 7/10/12.
- **Review path:** `independent adversarial review` — the reviewer must re-run every
  command quoted in the report and diff the outputs.
