# Issue #174 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#174 — Dupe survivor can be a copy that is itself proposed as wishlist trash`

**Milestone:** `M2 — Weapon dupes`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Anthropic, Claude Code session; the runtime does not expose a native effort setting for this session)

**Implementation model selected:** `gemini-3.8-flash` (`high`) (Bounded rung; justified below)

**Plan baseline:** `main` at `dfe9113934b3761c29ba7e7556c511ebbc733116` (2026-09-26)

**Allocated implementation branch:** `fix/issue-174-trash-survivor`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Make it impossible for a weapon decision's `kept_id` to name a copy that is
itself proposed in the same run. The fix: every copy that receives a
wishlist-trash decision, junk **or review**, is kept out of exact-duplicate
resolution, so it can never be chosen as the survivor. This changes decisions,
so `RULESET_VERSION` goes from 5 to 6.

## Context & Measurement

### The defect

`rules/weapons.run` removes only **junked** trash copies from the duplicate
pool; soft-protected (review) trash copies deliberately stay in:

- [weapons.py:123-127](../src/vault_cleaner/rules/weapons.py#L123-L127):
  "Soft-reviewed trash stays in the pool: it's only flagged, and probably
  staying." followed by `pool = weapons[~weapons["Id"].isin(trash_junk_ids)]`.
- [weapons.py:131](../src/vault_cleaner/rules/weapons.py#L131) then drops
  dupe decisions for trash ids, so a trash copy's *own* dupe decision never
  appears. But when that copy is the survivor, the other copies' decisions
  still name it in `kept_id`.

A losing copy escapes the trash rule when its keep/trash matches differ from
the survivor's. That is possible because `row_perk_hashes` reads every
`Perks N` cell ([weapons.py:31-45](../src/vault_cleaner/rules/weapons.py#L31-L45)),
while exact-roll identity uses only the pre-tracker prefix
([dupes.py:152](../src/vault_cleaner/rules/dupes.py#L152)).

### Reproduced on this baseline

With the `tests/test_weapons_rules.py` helpers
(`wl = parse_wishlist("dimwishlist:item=-300&perks=3\ndimwishlist:item=300&perks=1")`;
`11` locked with MW10 and `Bad Perk`; `22` with `Bad Perk` and `Perk A` in
`Perks 7`):

```text
11 review '' | #vc-review: wishlist-trash roll (locked)
22 junk '11' | #vc-junk: dupe-lower; keep [id 11; location Vault; Tier 5; MW10; roll Roll 4 / Roll 5]; winner higher Masterwork Tier
```

### An existing test pins the defect

[test_weapons_rules.py:340-352](../tests/test_weapons_rules.py#L340-L352),
`test_soft_reviewed_trash_copy_still_competes_in_dupes`, dates from M3 (#13,
commit `f5a8804`). It asserts `U` is junked with `kept_id == "T"` while `T` is
a review proposal. That is exactly #174's failure. This ticket rewrites that
test's expectations. The issue permits this: "Every changed expected decision
is justified in `WORKLOG.md`".

### Trial of the fix (planning session, reverted)

Changing `trash_junk_ids` to `trash_ids` on line 127 alone, on this baseline:

| Case (`WISHLIST` from `test_weapons_rules.py` unless noted) | Result | `kept_id` violations |
|---|---|---|
| The reproduction above | `11` review; `22` no decision | 0 |
| `T` locked trash MW10, `U` clean MW0 | `T` review; `U` no decision | 0 |
| `T` locked trash MW10, `U` MW5, `V` MW0 | `T` review; `V` junk `dupe-lower`, `kept_id U` | 0 |
| `T` Exotic trash MW10, `U` MW5, `V` MW5 | `T` review (exotic); `V` junk `dupe-tie`, `kept_id U` | 0 |
| `T` locked trash, `H` tagged `favorite` | `T` review; `H` no decision (hard) | 0 |

Full suite with the trial change: `1 failed, 1089 passed`. The only failure
was `test_soft_reviewed_trash_copy_still_competes_in_dupes`. The golden test
passed (its weapons run uses no wishlists).

### Fixture sweep on this baseline

`weapons.run` over every `tests/fixtures/weapons*.csv` × {no wishlist,
`test_weapons_rules.WISHLIST`, the coverage fixture wishlist with and without
evidence} yields **0** `kept_id`-in-decided violations on `main`. No committed
fixture exercises the defect, so the regression tests below must build the
case directly.

### Real-export incidence (measured)

**Authorised by the owner on 2026-09-26**, recorded on #174
(<https://github.com/tonym999/vault-cleaner/issues/174#issuecomment-5848899447>).
Measured in planning on `data/in/2026-09-01T-current/weapons.csv` with the
production config and wishlists, at this baseline and with the one-line fix
applied temporarily (then reverted). Aggregate counts only:

| | Before | After fix |
|---|---|---|
| Weapons | 665 | 665 |
| Decisions | 101 | 101 |
| `kept_id` names a decided copy | 0 | 0 |
| Keep/trash conflicts | 13 | 13 |
| Decisions changed | — | 0 |

By action and reason, identical before and after: junk `wishlist-trash
whole-item` 11; review `wishlist-trash whole-item` 8; review `dupe-lower` 2;
review `coverage-dominated by` 30; review `coverage-uncovered vs` 50.

The defect does not occur on the current real export. The fix is preventive,
and the two-copy yield trade-off below costs nothing on this vault today.

### Model verification and selection

Rung: **Bounded.** The fix is one production expression plus comments,
docstrings, a version bump, a golden regeneration and tests, all specified
here. No design choice is delegated. Selected `gemini-3.8-flash` (`high`), a
Bounded-rung permitted alternative in `handoffs/README.md`. It completed #170
cleanly in this repository on 2026-09-26. The primary, `MAI-Code-1.1-Flash`,
looped on context limits in the Copilot Windows app on #170 (128K window,
`WORKLOG.md`), and #144's prompt-template fix has not landed. The orchestrator
may re-select per `handoffs/README.md`.

## Dependencies and assumptions

- **Fix choice (the issue left it to the planner).** The issue offered two
  shapes: a trash-reviewed copy stays in the pool but cannot be survivor, or
  survivor selection skips proposed copies. Both reduce to "trash-decided
  copies do not take part", because a trash copy's own dupe decision is
  already discarded at line 131. Keeping it in the pool only lets it distort
  `best_key` and the `dupe-tie`/`dupe-lower` relation for the others. Pool
  exclusion is the simplest correct form, and it holds regardless of how
  perk matching is scoped.
- **Matching-scope question (issue scope item 2): deliberately out of
  scope.** Restricting wishlist matching to the pre-tracker prefix would
  change wishlist semantics for every weapon, and would not be needed for the
  invariant once the pool is fixed. #34's measurement found no keep-match
  difference on the real export, and the planning measurement above found
  no `kept_id` violation. Revisit only if a later export shows one.
- **Trade-off, stated plainly.** In the two-copy case, the clean lower copy
  (`U`, or `22`) now gets **no** decision. If the owner later vetoes the trash
  review and keeps `T`, `U` remains an unproposed duplicate, which is a small
  yield loss. The alternative, proposing `U` against a copy that may itself
  leave, can destroy both copies, which is what #140's invariant forbids. The
  #170 "also proposed" caveat remains as a presentation safeguard.
- **Versioning and sequencing.** `RULESET_VERSION` 5 → 6. The #140 tracking
  comment puts #174 before step 5, so #172 (Child 5) takes 7. #172's body
  still says "5 to 6", and its planner re-baselines. This plan does not edit
  #172. The bump invalidates saved review manifests (fingerprint change).
  Durable vetoes are unaffected. `SNAPSHOT_SCHEMA_VERSION` stays 3, and the
  golden file name stays `report_snapshot_v3.json`.
- **Coverage interplay.** Rows that previously got a dupe decision may now be
  undecided and enter `coverage.analyse`
  ([weapons.py:132-135](../src/vault_cleaner/rules/weapons.py#L132-L135)).
  Coverage partners are always undecided rows, so the invariant still holds.
  The invariant test below covers the whole `run` output, coverage included.

## Proposed Plan & Scope

### Rule change

#### [MODIFY] [weapons.py](../src/vault_cleaner/rules/weapons.py#L1-L8)

- Line 127: `pool = weapons[~weapons["Id"].isin(trash_ids)]`.
- Replace the comment at lines 123-126 with:
  ```python
  # Every wishlist-trash copy, junked or soft-reviewed, stays out of dupe
  # resolution: a proposed copy must never be the survivor other copies are
  # told to keep (#174). A trash copy's own dupe decision would be dropped
  # below anyway, so excluding it changes only who survives.
  ```
- Keep line 131's `d.id not in trash_ids` filter unchanged (now defensive).
- Nothing reads `trash_junk_ids` after this change. Remove its declaration
  (line 71) and `trash_junk_ids.add(row["Id"])` (line 111). Ruff will not
  flag it, because `.add` counts as a use.
- Module docstring: append to the `trash match` bullet:
  `Every trash-matched copy (junk or review) is excluded from exact-dupe
  resolution, so a proposed copy is never the kept survivor.`

#### [MODIFY] [report_run.py](../src/vault_cleaner/report_run.py#L41-L45)

`RULESET_VERSION = 6`, and extend the comment: `Ruleset v6 excludes every
wishlist-trash copy from exact-duplicate survivor selection (#174).`

#### [MODIFY] [PLAN.md](../PLAN.md)

Rule 2 (line 47): append `Every trash-matched copy, junk or review, is
excluded from exact-dupe resolution, so a copy proposed for removal is never
the one kept.`

### Tests

#### [MODIFY] [test_weapons_rules.py](../tests/test_weapons_rules.py#L340-L352)

- Rename `test_soft_reviewed_trash_copy_still_competes_in_dupes` to
  `test_soft_reviewed_trash_copy_is_not_a_dupe_survivor`. Assert `T` is the
  only decision (review, `wishlist-trash roll (locked)`) and `U` has none.
  Its comment says why (#174).
- Add `test_trash_survivor_reproduction_174`: the exact reproduction above.
  `11` is review and `22` has no decision.
- Add `test_survivor_chosen_among_non_trash_copies`: `T`/`U`/`V` from the trial
  table. `V` is junk `dupe-lower` with `kept_id == "U"` and winner `higher
  Masterwork Tier`. Also add the Exotic tie variant: `V` is `dupe-tie`,
  `kept_id == "U"`.
- Add `test_no_kept_id_is_itself_decided`: parametrize over every
  `tests/fixtures/weapons*.csv` × the four wishlists in the sweep above, plus
  the synthetic cases. Assert that no decision's non-empty `kept_id` is in the
  decided id set.
- No other existing assertion may change.

#### [MODIFY] [test_report_run.py](../tests/test_report_run.py#L270)

`== 5` → `== 6`. Regenerate the golden with
`python scripts/regenerate_report_snapshot.py`. The diff must be exactly
`ruleset_version` and `fingerprint`.

### Real-export confirmation at the implementation head

Authorisation is recorded on #174. Re-run the same aggregate measurement at
the implementation head: `resolve_weapons` with `config.toml` on
`data/in/2026-09-01T-current/weapons.csv`, printing only counts. Confirm
0 `kept_id` violations and the same 101 decisions by action and reason as
the table above. Record the counts in `WORKLOG.md`: no ids, rows or Notes.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

A dated entry justifying the rewritten test's changed expectation, the
version bump and its manifest effect, and the real-export confirmation
counts.

## Mechanical inclusion test

A proposed change is **in scope** if and only if it:
- changes the dupe-pool expression, its comment, the module docstring, or
  removes the now-unused `trash_junk_ids`;
- bumps `RULESET_VERSION` with its comment, updates the `== 5` assertion, and
  regenerates the golden;
- updates PLAN.md rule 2 as specified;
- adds or rewrites the tests listed above, or records the `WORKLOG.md`
  real-export confirmation.

Worked examples:
- **IN SCOPE:** rewriting `test_soft_reviewed_trash_copy_still_competes_in_dupes`
  to expect no decision for `U`.
- **IN SCOPE:** deleting the now-unread `trash_junk_ids` set and its `.add` call.
- **OUT OF SCOPE:** restricting `row_perk_hashes`, `trash_match` or
  `keep_match_count` to the pre-tracker prefix.
- **OUT OF SCOPE:** any change to `dupes.resolve`, ranking, `_winner_reason`,
  rails, coverage, Notes clause text, or the #170 explanation/caveat code.
- **OUT OF SCOPE:** armor or ghost passes; `SNAPSHOT_SCHEMA_VERSION`; editing
  #172 or any issue.

### Stop conditions

Stop implementation and return to the orchestrator if:
- any test other than the rewritten one changes outcome, or the golden diff
  has anything beyond `ruleset_version` and `fingerprint`;
- a weapon decision's `kept_id` is still decided in any case after the fix;
- the fix appears to need a change in `dupes.py` or `coverage.py`;
- the real-export confirmation differs from the planning table (any
  decision changed, or any `kept_id` violation).

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Pinned-behaviour test weakened rather than rewritten.** The old test
   might be deleted or loosened instead of asserting the new outcome
   exactly. The rename and exact expectations are required.
2. **Invariant test that cannot fail.** A sweep over fixtures alone is
   vacuous: the fixtures never trigger the defect. The parametrized test
   must include the synthetic cases, and the orchestrator should confirm it
   fails when line 127 is reverted.
3. **Stale comments or docs.** The old "Soft-reviewed trash stays in the
   pool" rationale left in the module docstring, PLAN.md or elsewhere.
   `grep -rn "stays in the pool\|Soft-reviewed" src PLAN.md docs` should
   return nothing stale.
4. **Version bump without a golden regeneration, or a hand-edited golden.**

# Reusable implementer execution prompt

Implement issue #174 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-174-implementation-plan.md
```

Read the entire handoff, issue #174, `AGENTS.md`, `PLAN.md`, the newest few entries at the top of `WORKLOG.md` (not the whole file), and the code the handoff cites before editing.

Rules:
- work on `fix/issue-174-trash-survivor`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- copy every comment, docstring and PLAN.md sentence in the plan verbatim;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `git diff --check origin/main...HEAD`, and `git ls-files data/` (must print nothing);
- confirm the new invariant test fails with the one-line fix reverted, then restore it;
- commit and push the implementation branch; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, return to the orchestrator: the base and head SHAs, the changed-file list, the full output of each verification command, the golden diff, the output of the reverted-fix run of the invariant test, the real-export confirmation counts, and any deviations from the plan.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
This changes which copy survives exact-duplicate resolution and which copies
are proposed at all: a ranking and decision-state change that bumps
`RULESET_VERSION` and invalidates saved manifests. Its failure modes are
quiet. A vacuous invariant test would pass, and a loosened pinned test would
hide a regression. #140 and #174 both call for independent adversarial review
on this class of change.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] The only production logic change is the pool expression (plus removal of unused `trash_junk_ids`); comments, docstring and PLAN.md text match the plan verbatim.
- [ ] `RULESET_VERSION` is 6; the golden diff is exactly `ruleset_version` and `fingerprint`; `SNAPSHOT_SCHEMA_VERSION` is still 3.
- [ ] The rewritten pinned test asserts `T` review and no decision for `U`; the reproduction and `T`/`U`/`V` tests assert exact actions, slugs and `kept_id`s.
- [ ] The invariant test covers the synthetic cases and fails with line 127 reverted (evidence in the handoff).
- [ ] No other existing assertion changed; no change in `dupes.py`, `coverage.py`, rails, explanation or Notes code.
- [ ] No stale "stays in the pool" rationale remains.
- [ ] The real-export confirmation matches the planning table (0 violations, 101 unchanged decisions) and is aggregate-only.
- [ ] `ruff`, `pytest`, `git diff --check`, empty `git ls-files data/`, and a `WORKLOG.md` entry all pass.

# Dispatch comment draft

Planned #174 in [handoffs/issue-174-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-174-implementation-plan.md) on `main`.

- **Implementer model & effort:** `gemini-3.8-flash` (`high`), Bounded rung
- **Implementation branch:** `fix/issue-174-trash-survivor`
- **Review path:** independent adversarial review
- **Likely findings:** the pinned M3 test loosened instead of rewritten; an invariant test that cannot fail (fixtures never trigger the defect); stale "stays in the pool" rationale; version bump without a clean golden regeneration.
