# Issue #148 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#148 — Child 2a: hard weapon loadout protection rail and Loadouts schema enforcement`

**Milestone:** none — deliberate. [#140](https://github.com/tonym999/vault-cleaner/issues/140)'s tracking section records that no existing milestone covers this initiative and that a one-off milestone must not be created without a planning decision.

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `claude-sonnet-5` with native effort `xhigh` (justified below)

**Plan baseline:** `main` at `381e8de938f3cd63b20db029376514ab3ac2a998` (2026-09-12)

**Allocated implementation branch:** `feat/issue-148-weapon-loadout-rail`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Give weapons the hard safety rail that armor and ghosts already have in some form: a weapon referenced by a saved DIM loadout is never proposed for removal, and a weapons export that does not carry the `Loadouts` header fails to load instead of silently protecting nothing.

DIM loadouts pin *instance ids*. Removing a loadout member breaks the owner's saved loadout, which is why [PLAN.md:49](../PLAN.md) already spells out that reasoning for armor. The weapon passes never implemented the equivalent. On the owner-authorized real export measured under [#142](https://github.com/tonym999/vault-cleaner/issues/142), the rail moves **113 weapons** from unprotected/soft-protected to hard-protected — the largest single safety improvement identified in that measurement, and the reason Child 2a is scheduled first.

The requirements source of truth is [docs/aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md): §2 (schema and protection-dimension comparison), §3 (rail precedence), §8 item 4 (the settled owner decision that `Loadouts != ''` is a HARD rail), §11 (real-export aggregates), §12 (child map row 2a), §13 question 1 (schema enforcement, recommendation accepted).

## Context & Measurement

All references below were measured on the plan baseline.

### There is no weapon loadout rail today

```bash
grep -rn "loadout-protected" src/ tests/     # no output
```

[`rails.protection`](../src/vault_cleaner/rules/rails.py#L30-L56) evaluates, in strict order: `Tag in HARD_PROTECT_TAGS` → `Equipped` → `crafted-lvunknown` → `crafted-lv{level}` → `exotic` (SOFT) → `locked` (SOFT) → `(None, "")`. It never reads `Loadouts`.

`Loadouts` is read in exactly three places in `src/`:

| Location | Purpose |
|---|---|
| [ghosts.py:36](../src/vault_cleaner/rules/ghosts.py#L36) | ghost protection reason `loadout` |
| [armor_dupes.py:99-100](../src/vault_cleaner/rules/armor_dupes.py#L99-L100) | `in_loadout`, used for survivor ranking ([armor_dupes.py:103-112](../src/vault_cleaner/rules/armor_dupes.py#L103-L112)) and the complete-exotic-class-item carve-out ([armor_dupes.py:194-213](../src/vault_cleaner/rules/armor_dupes.py#L194-L213)) |
| [report_run.py:317](../src/vault_cleaner/report_run.py#L317) | `ReportDecision.in_loadout`, presentation only |

### Both weapon seams call the shared rail

- [weapons.py:82](../src/vault_cleaner/rules/weapons.py#L82) — the wishlist-trash pass. `HARD` → `continue` (no decision at all); `SOFT` → `#vc-review: wishlist-trash {kind} ({reason})`.
- [dupes.py:243](../src/vault_cleaner/rules/dupes.py#L243) — the exact-dupe pass, over `keyed[1:]` (losers only; the survivor is never visited). `HARD` → `continue`; `SOFT` → `#vc-review: {rel} ({reason})`.

Both weapon entry points reach these: [pipeline.py:141](../src/vault_cleaner/pipeline.py#L141) calls `dupes.resolve` directly on the no-wishlists path, and [pipeline.py:151](../src/vault_cleaner/pipeline.py#L151) calls `weapons_rules.run` (which itself calls `dupes.resolve` at [weapons.py:107](../src/vault_cleaner/rules/weapons.py#L107)) on the wishlist path. Changing only one of `weapons.py` / `dupes.py` leaves the dominant path unprotected. This is the `AGENTS.md` sibling-path rule in its most literal form.

### `rails.protection` is shared with armor

```bash
grep -rn "rails.protection" src/
```

Eight call sites, listed here by path and line:

| Call site | Kind |
|---|---|
| [armor.py:155](../src/vault_cleaner/rules/armor.py#L155) | armor |
| [armor_close.py:138](../src/vault_cleaner/rules/armor_close.py#L138) | armor |
| [armor_close.py:302](../src/vault_cleaner/rules/armor_close.py#L302) | armor |
| [armor_dupes.py:107](../src/vault_cleaner/rules/armor_dupes.py#L107) | armor |
| [armor_dupes.py:204](../src/vault_cleaner/rules/armor_dupes.py#L204) | armor |
| [weapons.py:82](../src/vault_cleaner/rules/weapons.py#L82) | weapons |
| [dupes.py:243](../src/vault_cleaner/rules/dupes.py#L243) | weapons |
| [report_run.py:295](../src/vault_cleaner/report_run.py#L295) | all kinds, projection only |

Five of the eight call sites are armor. **Adding the loadout check inside `protection` itself would change armor decisions**, which is out of scope and would regress the deliberate armor design in which loadout membership is a survivor-ranking input and a review-only rail, not a hard rail.

### Schema state

[parse.py:42-44](../src/vault_cleaner/parse.py#L42-L44):

```python
REQUIRED_WEAPON_COLUMNS = REQUIRED_BASE_COLUMNS | {
    "Type", "Ammo", "Crafted", "Crafted Level", "Perks 0",
}
```

`Loadouts` is absent, while [`REQUIRED_GHOST_COLUMNS`](../src/vault_cleaner/parse.py#L47) and [`REQUIRED_ARMOR_COLUMNS`](../src/vault_cleaner/parse.py#L71-L76) both require it. Both weapon entry points — [`load_weapons`](../src/vault_cleaner/parse.py#L192-L203) and [`load_weapons_bytes`](../src/vault_cleaner/parse.py#L206-L215), the latter being the review server's upload path — share the same frozenset, so one edit covers both.

### Fixture state

All four committed weapon fixtures carry a `Loadouts` header, and **every one of their 36 rows has an empty `Loadouts` cell** (measured in §2 of the design document). No existing test exercises weapon loadout membership:

```bash
for f in tests/fixtures/weapons*.csv; do echo -n "$f: "; head -1 "$f" | tr ',' '\n' | grep -c '^Loadouts$'; done
```

```text
tests/fixtures/weapons.csv: 1
tests/fixtures/weapons_dupes.csv: 1
tests/fixtures/weapons_hostile.csv: 1
tests/fixtures/weapons_slammer_like.csv: 1
```

`tests/fixtures/weapons_dupes.csv` has 74 columns and 18 rows over hashes `500` (×5), `600` (×2), `700`, `800` (×4), `900` (×2), `950` (×2), `960` (×2).

### Real-export aggregates (design document §11)

| Rule world | Hard-protected | Soft-protected | Completely unprotected |
|---|---|---|---|
| Current rules | 56 | 323 | 285 |
| With the hard loadout rail | 169 (136 in loadouts) | 223 | 272 |

113 weapons are protected that are not protected today.

### Versioning surfaces

- [`RULESET_VERSION = 4`](../src/vault_cleaner/report_run.py#L44) is baked into [`compute_fingerprint`](../src/vault_cleaner/report_run.py#L241-L257) and into [`snapshot_dict`](../src/vault_cleaner/report_run.py#L415-L468). This change alters decision semantics, so `AGENTS.md` requires the bump; the bump correctly invalidates every persisted review manifest.
- `SNAPSHOT_SCHEMA_VERSION` stays at `2`. No snapshot field is added or removed.
- The golden [tests/fixtures/report_snapshot_v2.json](../tests/fixtures/report_snapshot_v2.json) is built from `weapons_dupes.csv` + `armor.csv` + `ghosts_cleanup.csv` ([scripts/regenerate_report_snapshot.py:36-38](../scripts/regenerate_report_snapshot.py#L36-L38)). Because the loadout fixture is **new** rather than an edit to `weapons_dupes.csv`, the golden's only changes must be `ruleset_version` and `fingerprint`.

## Dependencies and assumptions

1. **#142 is closed and merged.** Its design document is on `main` at the baseline SHA. No open blocker.
2. **No staleness found.** Every line reference in issue #148 was re-measured against the baseline and matches.
3. **#145 (open, in progress at planning time)** governs owner-authorized real-export measurement in committed docs. This ticket does **not** depend on it: all committed evidence here is fake-fixture evidence. If #145 has landed by dispatch, an aggregate-only confirmation that the rail hard-protects the measured 136 loadout weapons is a welcome addition to the implementer's report, but it is optional, must be run outside the working tree, and must never commit real rows, `Hash` values, or instance `Id`s. If #145 has not landed, skip it silently — do not ask for an export.
4. **No armor or ghost behaviour changes.** The armor exact pass's loadout handling and the ghost `loadout` protection reason are deliberate and stay exactly as they are.
5. **Unconditional rail, no config key.** The rail is not gated behind a policy flag or a `config.toml` key. Rationale: (a) it can only ever protect *more* items, so it is safe in the default maintenance policy; (b) the design document's §12 makes Child 2a an early deliverable that Child 5 (policy selection) depends on, not the reverse; (c) it is a rail, not a threshold, so `AGENTS.md`'s "thresholds live in `config.toml`" rule does not apply; (d) adding no config key means `report_run._decision_config` needs no new projection and its recursive DEFAULTS coverage test is unaffected.
6. **Weapons are deliberately stricter than armor here.** Design document §8 item 4 settles `Loadouts != ''` as HARD for weapons, while the armor exact pass treats a loadout-referenced loser as review-only. That divergence is an owner decision, not an inconsistency to "fix".
7. **No emitter-contract change.** A hard rail emits no `Decision` and therefore no `Notes` clause. `AGENTS.md`'s generated-clause / `note_history` recognizer requirement is not triggered. If the implementer finds itself writing a new `#vc-` clause, a stop condition has been hit.
8. **No UI change.** `ReportDecision.in_loadout` is already surfaced. The new reason string `loadout-protected` can never reach a rendered decision, because hard-protected rows produce no decision.

## Proposed Plan & Scope

### Rails

#### [MODIFY] [rails.py](../src/vault_cleaner/rules/rails.py#L30-L56)

Add a weapons-only wrapper beside `protection`. Do **not** modify `protection` itself.

```python
def weapon_protection(row, crafted_level_protect: int) -> tuple[str | None, str]:
    """Weapon rails: the shared rails plus the saved-loadout hard rail.

    DIM loadouts pin instance ids, so proposing a loadout member for removal
    breaks the owner's saved loadout (PLAN.md rule 1). Weapons-only on
    purpose: the armor exact pass deliberately treats loadout membership as
    a ranking input and a review rail, not a hard one.
    """
    level, reason = protection(row, crafted_level_protect)
    if level == HARD:
        return level, reason
    if str(row["Loadouts"]).strip():
        return HARD, "loadout-protected"
    return level, reason
```

Required properties, each of which has a named test below:

- Existing `HARD` reasons are returned unchanged, so no existing decision or note changes.
- A `SOFT` row (`exotic`, `locked`) in a loadout is promoted to `HARD`, not left soft.
- An unprotected row in a loadout becomes `HARD, "loadout-protected"`.
- Whitespace-only `Loadouts` (`"   "`) is *not* membership, matching [ghosts.py:36](../src/vault_cleaner/rules/ghosts.py#L36) and [armor_dupes.py:100](../src/vault_cleaner/rules/armor_dupes.py#L100).
- `row["Loadouts"]` uses **strict** indexing, not `.get(..., "")`. A frame that lost the column must fail loudly rather than silently unprotect every weapon; this matches the existing `armor_dupes.in_loadout` precedent. The loader guarantees the column after the schema change below.
- `protection`'s eager crafted-token validation still propagates `SchemaError` (the wrapper calls it first and unconditionally).

### Weapon rules

#### [MODIFY] [weapons.py:82](../src/vault_cleaner/rules/weapons.py#L82)

`rails.protection(row, crafted_level_protect)` → `rails.weapon_protection(row, crafted_level_protect)`. No other change in this file. The existing `HARD → continue` branch already delivers the required behaviour.

#### [MODIFY] [dupes.py:243](../src/vault_cleaner/rules/dupes.py#L243)

`rails.protection(row, crafted_level_protect)` → `rails.weapon_protection(row, crafted_level_protect)`. No other change in this file.

`rank_key` ([dupes.py:200-203](../src/vault_cleaner/rules/dupes.py#L200-L203)) is **not** touched — see the mechanical inclusion test.

### Report projection

#### [MODIFY] [report_run.py:284-297](../src/vault_cleaner/report_run.py#L284-L297)

Add a weapons branch after the existing `decision.effective_protection` branch so the armor carve-out keeps priority:

```python
elif kind == "weapons":
    level, protection_reason = rails.weapon_protection(
        row, crafted_level_protect
    )
```

This is consistency insurance rather than a behaviour change: a loadout-protected weapon never produces a `Decision`, so the projected value cannot differ today. The invariant is pinned by a test.

### Schema

#### [MODIFY] [parse.py:42-44](../src/vault_cleaner/parse.py#L42-L44)

```python
REQUIRED_WEAPON_COLUMNS = REQUIRED_BASE_COLUMNS | {
    "Type", "Ammo", "Crafted", "Crafted Level", "Perks 0", "Loadouts",
}
```

Extend the adjacent comment to record *why* `Loadouts` is safety-critical for weapons (a missing header would silently disable the hard rail), in the same voice as the existing `Crafted` sentence. Both `load_weapons` and `load_weapons_bytes` inherit this.

### Versioning and golden

#### [MODIFY] [report_run.py:41-44](../src/vault_cleaner/report_run.py#L41-L44)

`RULESET_VERSION = 4` → `5`, and update the adjacent comment so it records what v5 captures (the weapon saved-loadout hard rail) in the same style as the existing v4 sentence.

#### [MODIFY] [tests/fixtures/report_snapshot_v2.json](../tests/fixtures/report_snapshot_v2.json)

Regenerate with:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
```

Never by shell redirection (#45). The resulting diff must contain **only** `ruleset_version` and `fingerprint`. Any change to a decision, note, or section is a stop condition.

### Documentation

#### [MODIFY] [PLAN.md:46](../PLAN.md)

Extend the rails rule so the hard tier names saved-loadout membership for weapons, and say why (DIM loadouts pin instance ids). Keep it one clause; do not restructure the rule.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

One dated entry at the top: what changed, the decisions listed under *Dependencies and assumptions* (weapons-only wrapper rather than editing the shared rail; unconditional rather than policy-gated; strict `Loadouts` indexing), and anything surprising.

### Tests

#### [NEW] [tests/fixtures/weapons_loadouts.csv](../tests/fixtures/weapons_loadouts.csv)

Fake rows only, pinned to the real DIM header. Build it by copying the 74-column header of `tests/fixtures/weapons_dupes.csv` verbatim and writing rows with Python's `csv` module using `lineterminator="\n"` (CRLF is the default and `git diff --check` will flag it). Never paste real rows.

Required scenarios, all on invented hashes and ids that do not collide with `weapons_dupes.csv`:

| Group | Rows | Expectation |
|---|---|---|
| Loser in a loadout | two identical exact rolls, same `Hash`; the lower-ranked copy has `Loadouts` non-empty | no decision for the loadout copy; no decision for the survivor either |
| Winner in a loadout | two identical exact rolls; the higher-ranked copy has `Loadouts` non-empty | loser is still `junk`, and the note names the loadout copy as the retained survivor |
| Locked **and** in a loadout | a losing copy with `Locked=true` and `Loadouts` non-empty | hard-protected: **no** `#vc-review: dupe-lower (locked)` decision |
| Exotic **and** in a loadout | a losing copy with `Rarity=Exotic` and `Loadouts` non-empty | hard-protected: no review decision |
| Whitespace-only `Loadouts` | a losing copy with `Loadouts` = `"   "` | unprotected by this dimension; behaves exactly as today |

#### [MODIFY] [tests/test_rails.py](../tests/test_rails.py)

Add `weapon_protection` unit tests covering every property listed under *Rails*. The module-local `item()` helper ([tests/test_rails.py:8-13](../tests/test_rails.py#L8-L13)) has no `Loadouts` key — add a separate weapon-row helper (or extend `item()`) rather than making the existing `protection` tests depend on the new column. Include a test that `weapon_protection` raises on a row with no `Loadouts` key, pinning the strict-indexing decision.

#### [MODIFY] [tests/test_dupes.py](../tests/test_dupes.py)

Add exact-dupe cases over the new fixture for each scenario in the table above.

#### [MODIFY] [tests/test_weapons_rules.py](../tests/test_weapons_rules.py)

Add `"Loadouts": ""` to the `weapon()` helper's base dict ([tests/test_weapons_rules.py:30-44](../tests/test_weapons_rules.py#L30-L44)), then add cases proving that a wishlist whole-item-trash match and a wishlist roll-trash match on a loadout row produce **no** decision — neither `junk` nor `review`.

#### [MODIFY] [tests/test_parse.py](../tests/test_parse.py)

Add a `_drop_column("Loadouts")` entry to `INVALID_EXPORT_CASES` ([tests/test_parse.py:185-190](../tests/test_parse.py#L185-L190)), which exercises both `load_weapons` and `load_weapons_bytes` through the existing parametrization.

#### [MODIFY] [tests/test_report_run.py](../tests/test_report_run.py)

Two additions:

1. An invariant test: for a run over `weapons_loadouts.csv`, every weapon `ReportDecision` has `in_loadout is False`.
2. A test that armor and ghost decisions are unchanged — the simplest honest form is asserting the regenerated golden's `sections` for `armor` and `ghosts` are byte-identical to the baseline's. If the existing golden test already covers this by construction, say so in the worklog instead of adding a redundant test.

## Mechanical inclusion test

A proposed change is **in scope** if and only if it is one of:

- the new `rails.weapon_protection` function and its docstring;
- switching `weapons.py:82` and `dupes.py:243` to call it;
- the `kind == "weapons"` branch in `report_run._decision_records`;
- adding `"Loadouts"` to `REQUIRED_WEAPON_COLUMNS` and its adjacent comment;
- the `RULESET_VERSION` bump and its adjacent comment;
- the regenerated snapshot golden;
- the new `weapons_loadouts.csv` fixture and the test additions listed above;
- the `PLAN.md:46` rails clause and the `WORKLOG.md` entry.

Worked examples:

- **IN SCOPE:** promoting a `locked` weapon in a loadout from `SOFT` to `HARD` inside `weapon_protection`.
- **IN SCOPE:** adding `"Loadouts": ""` to `tests/test_weapons_rules.py`'s `weapon()` base dict, because the strict indexing requires it.
- **OUT OF SCOPE:** adding the `Loadouts` check to `rails.protection` itself. It is shared with five armor call sites and would change armor decisions.
- **OUT OF SCOPE:** adding loadout membership to `dupes.rank_key`. Under a hard rail the loadout copy is already safe; ranking only changes which copy is *named* as the survivor, which would alter existing notes and the golden's decision content. If this looks worth doing, report it as a finding for a follow-up ticket.
- **OUT OF SCOPE:** the "column present but empty on every row" advisory notice from design document §2 finding 2. It is a report-summary/snapshot presentation change, it is not among Child 2a's seams in §12, and issue #148 defers it explicitly.
- **OUT OF SCOPE:** any `--policy` flag, `config.toml` key, or `_decision_config` projection. Child 5 owns policy selection.
- **OUT OF SCOPE:** editing `weapons_dupes.csv`, `weapons.csv`, `weapons_hostile.csv` or `weapons_slammer_like.csv`. New coverage goes in the new fixture so the golden's decision content stays stable.
- **OUT OF SCOPE:** any change to `review_ui.js`, `review.css`, or `server/app.py`.

### Stop conditions

Stop implementation and return to the orchestrator if:

- the regenerated golden diff contains anything other than `ruleset_version` and `fingerprint`;
- any armor or ghost test changes behaviour, or any armor/ghost assertion needs editing;
- a `#vc-junk:` or `#vc-review:` clause format would have to change, or a `note_history` recognizer would have to learn a new clause;
- making the weapons tests pass appears to require a `config.toml` key, a policy flag, or a `_decision_config` projection;
- `REQUIRED_WEAPON_COLUMNS` gaining `Loadouts` breaks a test that cannot be fixed by adding the column to an in-test row (that would mean a real export path constructs weapon frames without it);
- an existing weapon decision's note text changes.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **The rail lands in the shared `protection` instead of a weapons-only wrapper.** It is the shortest diff and it silently changes five armor call sites. Check `git diff` for any edit inside `protection` itself, and confirm the armor sections of the golden are untouched.
2. **Only one of the two weapon seams is converted.** `weapons.py:82` is the one you notice reading the wishlist pass; `dupes.py:243` is the one that matters most on the real export, where duplicates dominate. Grep the final diff for both.
3. **The fixture regresses whitespace or line endings.** Python's `csv` module writes CRLF by default, and `git diff --check` gates CI. Also verify the new fixture's header is byte-identical to `weapons_dupes.csv`'s.
4. **`RULESET_VERSION` is left at 4, or the golden is regenerated by shell redirection.** Both are silent: the suite can pass with a stale ruleset version if the golden was regenerated from the same stale constant. Verify `report_snapshot_v2.json` contains `"ruleset_version": 5` *and* that the fingerprint changed.
5. **Soft-protected loadout members stay soft.** A `locked` or `exotic` loadout member that still emits `#vc-review: dupe-lower (locked)` means the wrapper returned before checking `Loadouts`. This is the single most likely behavioural bug, and it is exactly the case the real export is full of (198 locked legendaries under current rules).

# Reusable implementer execution prompt

Implement issue #148 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-148-implementation-plan.md
```

Read the entire handoff, issue #148, issue #140, `docs/aggressive-clearout-measurement.md` (§2, §3, §8, §11, §12, §13), `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and the current relevant code before editing.

Rules:
- work on `feat/issue-148-weapon-loadout-rail`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- generate the new CSV fixture with `lineterminator="\n"`, fake rows only, header copied verbatim from `tests/fixtures/weapons_dupes.csv`;
- regenerate the golden with `.venv/bin/python scripts/regenerate_report_snapshot.py`, never by shell redirection;
- update `PLAN.md` and add a dated `WORKLOG.md` entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `git diff --check origin/main...HEAD`, and `git status` plus `git ls-files data/` to confirm nothing under `data/` or `build/` is staged. The Playwright browser suite is **not applicable** — no UI, JavaScript, CSS, or server file is in scope; state that explicitly rather than skipping silently;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, report: base and head SHAs, changed files, the full output of each verification command, the exact golden diff, any deviation from the plan, and confirmation that `grep -rn "rails.protection" src/` still shows the five armor call sites unchanged.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
This change adds a delete rail and alters the weapons export parser's required schema — two of the categories `handoffs/README.md` names explicitly. Its blast radius reaches a shared rails helper used by five armor call sites, both weapon rule passes, the report projection, the ruleset version baked into every persisted review manifest's fingerprint, and the committed golden. The failure modes are quiet ones: a rail that returns soft instead of hard, or one seam converted and the other missed, both leave a green suite while leaving real weapons exposed. The design document also assigns Child 2a `Independent adversarial review` in its §12 child map.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

## Implementer model justification

`claude-sonnet-5` at native effort `xhigh`.

The individual edits are small and fully specified, which argues against the top tier. What argues for `xhigh` rather than `high` is that correctness here is about *placement* rather than volume: the wrapper must sit beside the shared rail rather than inside it, both weapon seams must move together, and the soft-to-hard promotion ordering inside the wrapper is the one line a careful-but-quick implementer gets wrong. The fixture and golden work also demands byte-level discipline.

Model IDs and effort values are taken from the catalog in [handoffs/README.md](README.md#model-family--provider-native-reasoning-effort-matrix) (marked verified 2026-09-03) and are consistent with this session's environment statement of current Claude model IDs. That catalog was **not** independently re-verified against live provider documentation during this planning session; per the template's rule the orchestrator must re-verify availability of `claude-sonnet-5` and `xhigh` at dispatch time and record any fallback.

# Review checklist

- [ ] `git diff` shows **no** edit inside `rails.protection`; the loadout check lives only in a new weapons-only function.
- [ ] Both `weapons.py:82` and `dupes.py:243` call the weapons-only rail; `grep -rn "rails.protection" src/` still shows the five armor call sites and `report_run`'s non-weapon fallback.
- [ ] A loadout member that is also `locked` or `exotic` is `HARD`, not `SOFT` — pinned by a named test, not by inspection.
- [ ] Whitespace-only `Loadouts` is not treated as membership.
- [ ] `weapon_protection` uses strict `row["Loadouts"]` indexing and a test pins the failure on a missing column.
- [ ] `REQUIRED_WEAPON_COLUMNS` includes `Loadouts`, and `tests/test_parse.py`'s `INVALID_EXPORT_CASES` covers dropping it through both `load_weapons` and `load_weapons_bytes`.
- [ ] `RULESET_VERSION` is `5`, its comment is updated, and the golden carries `"ruleset_version": 5` with a changed fingerprint.
- [ ] The golden diff contains **only** `ruleset_version` and `fingerprint`.
- [ ] The new fixture has LF endings, a header byte-identical to `weapons_dupes.csv`, fake rows only, and no `Hash`/`Id` values colliding with existing fixtures.
- [ ] A loadout-protected weapon can still be named as the retained survivor of a duplicate group.
- [ ] No weapon `ReportDecision` has `in_loadout is True`.
- [ ] No `config.toml` key, policy flag, `_decision_config` projection, `rank_key` change, UI change, or advisory-notice work appears in the diff.
- [ ] `PLAN.md:46` names the weapon loadout hard rail; `WORKLOG.md` has a dated entry recording the weapons-only-wrapper and unconditional-rail decisions.
- [ ] `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q` and `git diff --check` pass; `git ls-files data/` is empty; the browser suite is explicitly recorded as not applicable.

# Dispatch comment draft

Planned #148 in [handoffs/issue-148-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-148-implementation-plan.md) on `main`.

- **Implementer tier & effort:** `claude-sonnet-5` (`xhigh`) — re-verify availability at dispatch
- **Implementation branch:** `feat/issue-148-weapon-loadout-rail`
- **Review path:** independent adversarial review (delete rail + export schema)
- **Likely findings:** the rail landing inside the shared `rails.protection` and changing armor; only one of the two weapon seams converted; soft-protected loadout members not promoted to hard; CRLF or a non-identical header in the new fixture; `RULESET_VERSION` left at 4 or the golden regenerated by shell redirection.
