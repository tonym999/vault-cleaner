# Issue #31 — Luna xhigh Implementation Plan

**Repository:** `tonym999/vault-cleaner`
**Issue:** `#31 — Stop same-Hash weapon cleanup from junking distinct useful rolls`
**Planning base:** `main` at `0a5460108fcd2a5473147920716b644147d076a8` (2026-08-28)
**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → orchestrating Sol high reviews → independent Sol high reviews → PR
**Implementation PR:** Luna must **not** open one. Sol will review the completed implementation first.

## Objective

Replace the unsafe weapon duplicate identity of “same item `Hash`” with a **measured, documented, fail-safe exact-roll identity** so that different useful rolls of the same weapon release never junk one another merely because they share a hash.

The end state is:

- the weapon dupe pass can automatically remove only copies whose roll identity has been **proven equivalent**;
- different roll fingerprints under the same `Hash` survive independently;
- wishlist-trash remains its own earlier decision path;
- keep-wishlist matches may rank copies only inside a true exact-roll group and can no longer cause a different roll to be junked;
- safety rails from the current repository, including the completed #32 crafted-state correction, remain intact;
- exact-group survivor choice is deterministic and independent of CSV row order;
- uncertain/truncated/unclassifiable roll identity fails safe by **not participating in automatic duplicate junking**;
- the rule semantics change is reflected in the ruleset fingerprint and documentation.

This is a correctness/safety ticket, not a cleanup-volume optimisation ticket. A smaller exact-dupe yield is acceptable if it is the cost of proving identity.

---

# Why this ticket is ready — and the measurement gate that still applies

Issue #31 is open and has no comments containing a completed weapon-fingerprint measurement. The issue itself deliberately requires the real weapon export to be measured before the fingerprint is finalised.

The implementation is therefore ready to start **only as a measurement-gated ticket**:

1. Luna may inspect the real local weapon export without committing it.
2. Luna must record aggregate measurement findings before writing the final production fingerprint.
3. If the export does not let Luna distinguish immutable roll identity from mutable socket/state data with a bounded, robust rule, Luna must stop and return the ticket to Sol rather than guessing.

The armor precedent confirms this workflow: #16 measured real export behaviour first, #17 then implemented only the fingerprint that measurement justified.

Current dependency/readiness notes:

- #32 is complete and merged. Its strict `Crafted=crafted` handling, crafted-level validation, unknown-level hard protection, and ruleset-v2 state are now part of the baseline and must be preserved.
- #29 is open. It owns human-readable survivor/partner presentation. #31 must coordinate with it but must **not** absorb that UX work.
- #16 and #17 are complete and are the precedent for measurement-first exact identity and deterministic survivor selection.
- No parent/umbrella issue is identified in #31, and the issue has no comments of its own at planning time.

---

# Review model

## Review path: **independent review**

Use:

```text
Sol orchestrator/planner
    ↓
Luna xhigh implementation
    ↓
Orchestrating Sol high plan-conformance + engineering review
    ↓
Independent Sol high final review
    ↓
PR
```

### Why independent review is required

Although the code change should remain local to weapon duplicate identity, it changes the rule that decides which weapon instances are safe to mark `junk`. The CSV is subsequently imported into DIM and used to guide manual in-game dismantling, so a false-positive identity decision can result in loss of a valuable roll.

The ticket also changes **decision semantics**, which requires a `RULESET_VERSION` bump and therefore changes the report fingerprint used to reject stale review state. The difficult part is not code volume; it is whether the chosen identity model is actually sound against mutable socket state, multi-option perk cells, selected markers, enhanced/base representation, and incomplete export data.

A fresh reviewer should therefore challenge both the implementation and the measurement-derived design rather than merely confirming that Luna followed the plan.

---

# Authoritative context

Before changing production code, Luna must read:

- `AGENTS.md`;
- `PLAN.md`;
- issue #31 and its comments;
- issue #29 and its comments;
- issue #32;
- issue #16 and its measurement comment;
- issue #17 and its design-delta comment;
- the latest relevant `WORKLOG.md` entries, especially the 2026-08-28 #32 entry;
- `src/vault_cleaner/rules/dupes.py`;
- `src/vault_cleaner/rules/weapons.py`;
- `src/vault_cleaner/rules/rails.py`;
- `src/vault_cleaner/parse.py`;
- `src/vault_cleaner/pipeline.py`;
- `src/vault_cleaner/report_run.py`;
- `tests/test_dupes.py`;
- `tests/test_weapons_rules.py`;
- `tests/test_rails.py` where crafted/safety behaviour is covered;
- `tests/test_report_run.py`;
- `tests/fixtures/weapons_dupes.csv`;
- `tests/fixtures/report_snapshot_v1.json` and `scripts/regenerate_report_snapshot.py`.

Treat these current seams as authoritative unless implementation proves a real defect within #31:

- `pipeline.resolve_weapons()` is the single public ordered weapon pipeline;
- `weapons.run()` owns wishlist-trash + keep-match integration when wishlists are enabled;
- `dupes.resolve()` owns duplicate grouping/ranking/decision creation;
- `rails.protection()` owns hard/soft protection and the #32 crafted behaviour;
- `parse.py` owns DIM schema validation and header-name access;
- `report_run.RULESET_VERSION` owns decision-semantics invalidation;
- Python remains the only authoritative rules engine;
- `dupes --no-wishlists` remains the zero-wishlist/zero-manifest-network fallback;
- `Decision` remains the shared decision model;
- no real vault export, row, or instance id may be committed.

---

# Current repository state relevant to #31

Planning was performed against `main` SHA:

```text
0a5460108fcd2a5473147920716b644147d076a8
```

Important current-state facts:

1. **The defect still exists.** `rules/dupes.py` groups only by `Hash`:

   ```python
   for _, group in weapons.groupby("Hash", sort=False):
   ```

   Every same-hash copy therefore competes with every other same-hash roll.

2. **Current ties are row-order dependent.** The resolver performs a stable descending sort and lets the earlier CSV row survive when ranking keys tie. That directly contradicts #31’s reversed-row-order acceptance criterion.

3. **Wishlist keep matches are ranking only.** `weapons.run()` calculates a keep-match count and passes it into `dupes.resolve()` as the first rank component. Under the current same-hash grouping, this allows one useful roll to defeat and junk another useful but different roll.

4. **Wishlist-trash is already a separate earlier path.** Ordinary trash-junked rows are removed from the dupe pool; soft-reviewed trash rows remain because they are expected to stay in the vault. Preserve that architecture. The bug is the identity used by the dupe pass, not the existence of wishlist-trash.

5. **#32 has changed the baseline since #31 was written.** Weapon loading now requires `Crafted` and `Crafted Level`, validates them before rules run, recognises DIM’s real `Crafted=crafted` token, treats unknown crafted level as hard-protected, and rejects malformed safety values. `RULESET_VERSION` is currently `2`.

6. **`PLAN.md` is stale for weapon duplicate identity.** Rule 3 still explicitly says “group by item Hash” and still describes export-order-dependent tie behaviour indirectly through the old design. It must be corrected when #31 lands.

7. **The armor exact-dupe implementation is the closest repository precedent.** `armor_dupes.py` documents a measured fingerprint, deliberately excludes mutable state from identity, fails safe for unknown Spirit-roll identity, and uses a stable instance-id tie-break rather than CSV row order.

8. **The weapon parser does not currently require roll-perk headers for duplicate identity.** `REQUIRED_WEAPON_COLUMNS` includes Type/Ammo/Crafted fields but not any `Perks N` field, because weapon duplicate identity has never consumed them. #31 must establish a safe schema/fallback policy rather than silently assuming arbitrary perk columns are present.

9. **Current fake weapon fixtures have the real-style header through `Perks 19` but many existing rows leave all perk cells empty.** Some old tests intentionally model same-hash ranking rather than true roll identity and will need to be rewritten when their premise conflicts with #31.

10. **Report fingerprints and golden snapshots cover decision semantics.** Changing weapon grouping requires a ruleset bump (expected `2 → 3`) and intentional snapshot regeneration/expectation updates.

---

# Ticket-specific algorithmic scope rule

This rule is the mechanical boundary Luna must use for every proposed code or test change.

## A. Per-row automatic-dupe rule

Define a row as **groupable** only when the measurement-approved extractor can produce a complete, proven immutable weapon-roll key.

Conceptually:

```text
Groupable(row) := exact_roll_fingerprint(row) is proven/complete

SameWeaponDupe(a, b) :=
    Groupable(a)
    AND Groupable(b)
    AND a.Hash == b.Hash
    AND exact_roll_fingerprint(a) == exact_roll_fingerprint(b)
```

The weapon dupe pass may automatically emit `dupe-*` junk/review advice comparing `a` with `b` **only if `SameWeaponDupe(a, b)` is true**.

If identity is incomplete, truncated, unknown, ambiguous, or depends on unmeasured mutable state, that row is **not groupable** and must not be automatically junked by the dupe pass.

Wishlist-trash is exempt from this equivalence test because it is a separate earlier explicit rule and must retain its existing behaviour.

## B. Change-scope rule

A proposed change belongs in #31 only if **all** of these are true:

1. it is directly required to:
   - measure/classify weapon roll identity;
   - extract/canonicalise the measured immutable exact-roll fingerprint;
   - fail safe when the fingerprint cannot be proven;
   - restrict the existing weapon dupe pass to true exact-roll groups;
   - make survivor selection within such groups independent of CSV row order;
   - preserve and test existing wishlist/safety-rail behaviour around the narrower grouping; or
   - update tests, ruleset fingerprints, snapshots, or documentation directly invalidated by those changes;
2. it can be tied to a #31 acceptance criterion or a regression caused by implementing one;
3. it does **not** redesign an adjacent subsystem.

## C. Mandatory stop/escalation conditions

Luna must stop and return the issue to Sol for replanning if any of the following becomes true:

- the current real weapon export is unavailable, so the mandatory measurement cannot be performed;
- randomized roll options cannot be reliably separated from mutable mods, trackers, masterworks, origin traits, mementos, selected markers, or other socket state using bounded evidence from the export;
- safe identity would require a new authenticated Bungie API path, a new runtime dependency, or a new network requirement for `dupes --no-wishlists`;
- the proposed solution needs a broad manifest/parser architecture change rather than a local fingerprint seam;
- the necessary identity is not present in the DIM export at all;
- missing/truncated perk data could false-merge different rolls and no local fail-safe “not groupable” policy can prevent it;
- correctness appears to require changing hard/soft rail policy, crafted protection semantics, wishlist source/parsing semantics, output CSV schema, review/server protocol, durable override semantics, armor/ghost rules, or configuration shape;
- implementing human-readable survivor notes from #29 appears necessary — it is not part of #31 and should be returned to Sol instead of absorbed;
- a reason/presentation rewrite grows beyond the minimal truthfulness needed for exact-roll decisions;
- a fixture/snapshot change cannot be explained by #31 decision semantics.

Do not “solve” a stop condition by expanding the ticket.

---

# Scope

## In scope

- Measurement of the current real weapon DIM export using local/private data without committing rows or ids.
- Documenting which exported weapon perk/socket data is immutable roll identity versus mutable/current state.
- Deciding and documenting treatment of:
  - randomized perk options;
  - selected `*` markers;
  - multi-option perk cells;
  - base/enhanced representation;
  - origin/intrinsic traits;
  - weapon mods;
  - masterwork/tracker/memento/current socket state;
  - any other categories actually observed in the real export.
- Measuring old same-hash groups versus candidate exact-roll groups and expected cleanup volume.
- Adding a measured exact-roll fingerprint built by header name / named export fields, never numeric column position.
- A fail-safe “identity unknown → no auto-dupe” path if measurement shows it is required.
- Narrowing `dupes.resolve()` grouping from same-hash to proven exact-roll identity.
- Making exact-group survivor selection deterministic under CSV row reversal.
- Preserving the existing rank priorities **inside a true exact group** unless measurement proves a component is unsafe.
- Preserving existing hard/soft rail semantics, including #32 crafted handling.
- Preserving wishlist-trash as a separate earlier rule.
- Updating stale tests that currently depend on different rolls competing merely because they share a hash.
- Adding the required fake Slammer-like exact-roll fixture.
- Bumping `RULESET_VERSION` because decision semantics change.
- Regenerating the fake report snapshot if required by the ruleset/fixture change.
- Updating `PLAN.md`, `WORKLOG.md`, and narrowly relevant user/agent documentation.

## Out of scope

- #29 survivor/partner presentation overhaul.
- New human-readable audit format or new report artifact.
- Changing `Decision` schema for presentation-only fields.
- Changing wishlist download sources, cache policy, parser format, or network architecture.
- Adding manifest/network dependence to no-wishlist duplicate cleanup.
- Changing wishlist keep/trash policy beyond preventing different exact-roll groups from competing.
- Changing hard/soft safety-rail definitions.
- Adding weapon loadout protection unless separately approved; armor’s loadout-specific survivor rule is not automatically a weapon requirement.
- New config knobs for fingerprint behaviour.
- Armor/ghost rule changes.
- Review UI/server protocol changes.
- Persistent override/review-manifest behaviour changes.
- CI, Playwright, packaging, or wheel work unrelated to the changed rule semantics.
- Runtime dependency changes.
- Broad parser refactors.

Incidental findings outside this boundary should be written into the Luna → Sol handoff as follow-up candidates, not implemented.

---

# Expected change footprint

Likely production files:

```text
src/vault_cleaner/rules/dupes.py
src/vault_cleaner/rules/weapons.py          # only if integration/tests require it
src/vault_cleaner/parse.py                  # only for the measured safe schema boundary
src/vault_cleaner/report_run.py             # RULESET_VERSION bump
PLAN.md
README.md                                    # brief exact-roll wording if useful
AGENTS.md                                    # weapon-export gotcha if measurement is reusable
WORKLOG.md
```

Likely tests/fixtures:

```text
tests/test_dupes.py
tests/test_weapons_rules.py
tests/test_rails.py                          # only if safety/schema boundary needs coverage
tests/test_report_run.py
tests/fixtures/weapons_slammer_like.csv      # preferred dedicated fake fixture name
tests/fixtures/weapons_dupes.csv             # only if old blank-perk rows need realistic identity data
tests/fixtures/report_snapshot_v1.json       # regenerated, never hand-edited
```

Files/components that should normally remain unchanged:

```text
src/vault_cleaner/rules/armor.py
src/vault_cleaner/rules/armor_dupes.py
src/vault_cleaner/rules/armor_close.py
src/vault_cleaner/rules/ghosts.py
src/vault_cleaner/review.py
src/vault_cleaner/review_session.py
src/vault_cleaner/server/
src/vault_cleaner/ui/
src/vault_cleaner/wishlist.py
src/vault_cleaner/manifest.py
config.toml
pyproject.toml
.github/workflows/
scripts/check_wheel_install.py
```

`scripts/regenerate_report_snapshot.py` should be **used**, not redesigned.

If any normally-unchanged component needs substantive edits, Luna must explain why the algorithmic scope rule permits it before proceeding; otherwise stop/escalate.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline

Branch from the latest `main`, not from the handoff branch.

Suggested implementation branch:

```text
issue-31-weapon-exact-roll-dupes
```

Record the actual base SHA in the final Luna handoff.

Before modifying code:

```bash
git switch main
git pull --ff-only
git status --short
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git ls-files data/
```

Expected final command output for `git ls-files data/` is empty.

If baseline Ruff/tests fail on latest `main`, stop and report the baseline failure before mixing unrelated fixes into #31.

## 2. Re-read the current issue/dependency state after branching

Confirm:

- #31 remains open and has not received a later fingerprint decision;
- #32 remains merged and its current safety semantics are present;
- #29 has not landed a change that affects note/reason expectations;
- `RULESET_VERSION` is still the value expected by this plan;
- no newer main commit has already introduced a weapon fingerprint.

If `main` moved legitimately, adapt this plan only where necessary and document the delta. Do not silently restore stale assumptions from this handoff.

## 3. Perform the mandatory real-export measurement **before final fingerprint code**

Use the current private/local DIM weapon export. Do not copy it into `tests/`, `handoffs/`, logs committed verbatim, or any tracked path.

A throwaway script or interactive Python analysis is acceptable. Prefer an untracked temporary path outside the repository or a heredoc command. Do not add a permanent analysis framework unless the ticket genuinely needs one.

Measure at minimum:

1. all present headers matching `Perks N`, by **header name**;
2. representative/aggregate contents of those cells by category, including:
   - randomized weapon perks;
   - selectable/multi-option cells;
   - active/selected `*` markers;
   - weapon mods;
   - origin/intrinsic traits;
   - masterwork-related entries;
   - trackers;
   - mementos;
   - enhancement/crafting state;
   - anything else actually present;
3. whether the same underlying roll changes exported `Perks N` cells when mutable state changes;
4. whether perk cells shift between `Perks N` headers as sockets/masterwork/crafting state changes;
5. how base and enhanced perk variants appear in DIM’s exported text;
6. whether option order within a multi-option cell is stable or should be canonicalised as a set;
7. whether an empty perk cell/header has a defined meaning or could mean truncated/unknown identity;
8. old same-Hash duplicate-group counts;
9. candidate exact-fingerprint group counts and group-size distribution;
10. candidate “would remove `sum(size - 1)`” volume before safety rails;
11. expected actual dupe decision volume after safety rails where practical;
12. a Slammer-specific aggregate sanity check: number of copies per hash, number of distinct measured fingerprints, and exact duplicate group sizes — **no instance ids or row dumps**.

### Measurement output that may be recorded

Record only safe aggregate results, public game/perk terminology where useful, and the resulting structural rule. Examples:

- “`Perks 0..19` present”;
- “selected marker is a trailing `*` and does not alter the option identity”;
- “these structural socket categories were mutable”;
- “candidate fingerprint produced N groups ≥2 / M redundant rows”;
- “Slammer hash X contained N distinct fingerprints and Y exact duplicate groups”.

Do **not** record:

- complete real vault rows;
- real instance ids;
- a copied real CSV subset;
- personal account/location data not needed for the decision.

### Required pre-code record

Before finalising the production extractor, add a provisional dated #31 section to `WORKLOG.md` (or, if the orchestration environment supports it, a GitHub issue comment) containing:

- the measurement date;
- the observed structural categories;
- the chosen immutable components;
- the excluded mutable components;
- base/enhanced decision;
- multi-option/selected-marker decision;
- unknown/truncated-data policy;
- exact-group and expected-cleanup aggregate counts.

If the measurement does not support a bounded rule, invoke the stop/escalation conditions and do not continue.

## 4. Freeze the exact-roll identity contract in code/documentation

Once measurement is recorded, write the fingerprint contract before changing resolver behaviour.

The contract must have this shape:

```text
weapon exact identity = Hash + measurement-approved immutable roll components
```

Requirements:

- `Hash` remains part of identity; never group by `Name`.
- Access named headers / named field patterns only; never numeric dataframe positions.
- Include only data proven to describe the roll the weapon dropped/was shaped with, not its current mutable configuration.
- Strip/canonicalise selection markers only if measurement proves they are mutable presentation state.
- Canonicalise multi-option cells order-insensitively only if measurement proves option order has no gameplay identity.
- Base/enhanced equivalence must follow the measured semantics; do not infer it from wishlists alone.
- Do not make the fingerprint depend on live network access or wishlist availability.
- Do not use a brittle allow/deny list of today’s specific perk names if the export offers no stable structural discriminator. If that is the only possible approach, stop/escalate.
- If a row’s exact identity cannot be proven, return an explicit “unknown/not groupable” result rather than inventing a partial key that might false-merge it.

Prefer a small named helper in `rules/dupes.py` (for example `exact_roll_fingerprint`) over embedding complex parsing inside the grouping loop. A separate production module is justified only if the measured extractor is substantial enough that keeping it in `dupes.py` would materially harm clarity.

Document the fingerprint in the module docstring with the measurement rationale, following `armor_dupes.py`’s style.

## 5. Establish the parser/schema fail-safe boundary

Because current `REQUIRED_WEAPON_COLUMNS` does not require any perk header, decide from measurement which schema condition is necessary to prevent silent false merges.

Acceptable patterns include:

- require one or more specifically measured, invariant named headers; and/or
- dynamically discover named `Perks N` headers but treat missing/insufficient row identity as ungroupable.

The chosen boundary must satisfy both:

1. a DIM format change cannot silently collapse many unrelated weapons into one fingerprint;
2. valid but genuinely empty/optional values are not rejected merely because they are empty.

If a whole-file missing header means identity cannot be trusted, fail loudly with `SchemaError`. If an individual row can legitimately have incomplete identity, fail safe locally by excluding it from auto-dupe grouping.

Do not weaken or bypass #32’s crafted-value validation.

## 6. Narrow duplicate grouping to exact-roll groups

Refactor `dupes.resolve()` so same `Hash` is only the first partition, not the final duplicate identity.

Mechanically:

1. obtain the fingerprint for each row;
2. skip rows whose fingerprint is not proven/groupable;
3. group by `(Hash, fingerprint)` or by a fingerprint that already contains `Hash`;
4. ignore groups of size 1;
5. run the existing survivor ranking only inside each exact group.

After this step, a higher wishlist score/masterwork/crafted level must never defeat a row with a different exact-roll fingerprint.

Do not create a broader “similar weapon roll” auto-junk path in this ticket. If broader advice is ever desired, it belongs in a separate review-only design.

## 7. Make survivor selection deterministic and row-order independent

Preserve the current ranking priorities inside an exact group unless the measured fingerprint makes one irrelevant:

```text
wishlist keep-match count (when wishlists enabled)
> Tier
> Masterwork Tier
> Crafted Level
> stat-total ranking
```

Safety-rail handling must remain as defined by `rails.protection()`.

Remove export-order as the final tie-break. For equal ranking keys, choose a stable survivor by `Id` using a deterministic comparison that does not depend on dataframe row order.

Prefer treating `Id` as an opaque string for tie-breaking rather than introducing new numeric schema assumptions solely for this ticket. The important invariant is that reversing the input rows produces the same survivor id and the same decisions.

Do not opportunistically change weapon hard/soft rail precedence or add armor’s loadout-specific rule.

## 8. Preserve wishlist semantics while removing cross-roll competition

`weapons.run()` should retain its current high-level ordering:

```text
wishlist-trash evaluation
→ exclude ordinary trash-junked rows from dupe pool
→ keep soft-reviewed trash rows in the pool because they remain in the vault
→ exact-roll dupe resolution
```

Required semantics:

- explicit whole-item/roll-specific wishlist trash behaviour stays unchanged;
- keep + trash conflict still lets keep win over trash and still increments the conflict count;
- a keep match is **not** a blanket keep within an exact group;
- a keep match can no longer be used to junk a different exact roll;
- a soft-reviewed trash row with a **different** fingerprint cannot cause a clean roll to become `dupe-lower`;
- ordinary trash-junked rows must still not survive as the “best” duplicate while leaving the vault.

Review and rewrite existing tests whose old premise was “same hash means duplicate”. In particular, current tests where one copy has different perks but is expected to beat/junk the other are stale under #31 and should be replaced with exact-group and distinct-group assertions rather than mechanically preserved.

## 9. Keep safety rails unchanged and pin them with regressions

The new grouping must not weaken:

- `favorite` / `keep` / `archive` hard protection;
- equipped hard protection;
- `Crafted=crafted` recognition;
- crafted threshold and above-threshold hard protection;
- crafted empty/unknown-level hard protection;
- malformed crafted-state/level refusal;
- exotic soft protection;
- locked soft protection;
- existing tag preservation on review rows.

A protected row may cause fewer items to be removed; safety wins over cleanup volume.

Do not change #32 helpers or validation policy merely to simplify fingerprint code.

## 10. Add the fake Slammer-like fixture

Add a dedicated LF-only fake weapon fixture pinned to the real weapon header, preferably:

```text
tests/fixtures/weapons_slammer_like.csv
```

It must contain fake ids/data only and model at least:

- one weapon `Hash` with several distinct useful roll identities, representing different plausible roles;
- one true exact duplicate pair inside that hash;
- ranking differences inside the exact pair so one deterministic survivor is meaningful;
- enough mutable-state variation to prove excluded state does not incorrectly split an exact pair, if the measurement supports such a case;
- relevant multi-option/selected-marker/base-enhanced examples required by the measured contract.

Do not copy real Slammer rows or ids. Public perk names are acceptable if needed, but synthetic names are preferable where they prove the same contract.

## 11. Add focused exact-identity tests

At minimum prove:

1. same `Hash` + different measured roll fingerprints → no `dupe-lower`/`dupe-tie` decision between them;
2. same `Hash` + same exact fingerprint → one deterministic survivor, remaining ordinary exact copies receive the appropriate existing exact/lower/tie decision wording;
3. same weapon name + different `Hash` still never groups;
4. row reversal produces identical decided ids, survivor `kept_id`s, actions, tags, and reason slugs;
5. selected-marker treatment follows the measurement decision;
6. multi-option treatment follows the measurement decision;
7. base/enhanced treatment follows the measurement decision;
8. mutable state excluded from identity does not incorrectly split exact copies;
9. a randomized roll difference does split copies;
10. missing/unknown/truncated identity follows the fail-safe policy and never produces a false auto-junk group.

Prefer behavioural assertions over source-string tests.

## 12. Add explicit wishlist regressions

Cover both directions required by #31:

### Keep wishlist

- one same-hash roll matches a keep recommendation;
- another same-hash **different** roll has fewer/no keep matches;
- the second roll survives independently rather than becoming `dupe-lower`;
- exact duplicates of one roll can still resolve within that roll’s group.

### Trash wishlist

- explicit wishlist-trash still creates the same junk/review outcome it did before #31;
- a trash-junked row remains excluded from dupe survivor selection;
- a soft-reviewed trash row remains in the vault but only competes with rows sharing its exact fingerprint;
- keep+trash conflict count and keep-over-trash semantics are unchanged.

## 13. Add/retain rail regressions

Make the acceptance criteria explicit in tests for exact groups containing, as applicable:

- crafted threshold / above threshold;
- equipped;
- hard tagged;
- locked;
- exotic.

Where existing tests already prove the same case with rows that remain valid exact duplicates under the new fingerprint, retain them. Rewrite only when their old blank/different-roll fixture makes the assertion no longer meaningful.

## 14. Update ruleset version and report snapshot

This ticket changes which decisions are produced for the same input bytes. Therefore bump:

```python
report_run.RULESET_VERSION
```

Expected from the planning baseline:

```text
2 → 3
```

If `main` has moved and the current version differs, increment from the current value exactly once for #31.

Update any explicit version assertions in `tests/test_report_run.py` and related review tests that are intended to track the current ruleset.

Regenerate the fake report snapshot only through:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
```

Do not hand-edit `tests/fixtures/report_snapshot_v1.json`.

Inspect the snapshot diff and account for every changed weapon decision. A ruleset-version-only change is acceptable if the existing golden weapon fixture happens to remain semantically equivalent; larger changes must be explained by fixture/fingerprint semantics.

## 15. Update documentation

### `PLAN.md`

Rule 3 is stale and must be corrected to describe:

- `Hash` + measured exact-roll fingerprint grouping;
- different fingerprints surviving independently;
- uncertain identity failing safe;
- survivor ranking occurring only within exact groups;
- deterministic stable-id tie-breaking rather than CSV order.

Keep wishlist-trash as rule 2 and do not fold #29 presentation requirements into the rule definition.

### `WORKLOG.md`

The dated #31 entry must include:

- the real-export measurement result in aggregate form;
- the exact fingerprint and what is deliberately excluded;
- base/enhanced, selected-marker, and multi-option decisions;
- unknown/truncated identity policy;
- before/after exact-group and expected cleanup counts;
- implementation files/behaviour;
- the #32 safety semantics explicitly preserved;
- ruleset bump and snapshot effect;
- focused/full validation results;
- manual real-export dry-run result;
- confirmation that no real rows/ids were committed.

### `AGENTS.md`

Add a concise weapon-export gotcha if the measurement reveals a stable fact future agents must know, analogous to the existing armor perk-column and crafted-token notes. Do not turn AGENTS into a full design document.

### `README.md`

If retained wording could lead a user to think all same-hash weapons are duplicates, clarify that weapon cleanup now removes only proven exact-roll duplicates. No new workflow documentation is required.

## 16. Manual real-export verification — dry run only

After all focused tests pass, run against the same current private export used for measurement.

Use a shell variable so no private path is committed:

```bash
WEAPONS_EXPORT=/absolute/path/to/current/destiny-weapon.csv
.venv/bin/vault-cleaner dupes --input "$WEAPONS_EXPORT" --no-wishlists
```

If normal wishlist caches/network are available, also run:

```bash
.venv/bin/vault-cleaner dupes --input "$WEAPONS_EXPORT"
```

Do **not** pass `--write` during this verification.

Check specifically:

- The Slammer-like real case no longer collapses to one survivor per hash when rolls differ.
- Only proven exact groups receive duplicate decisions.
- Wishlist-trash decisions remain present where expected.
- No crafted/equipped/hard-tagged item appears because of the dupe pass.
- Locked/exotic duplicate losers remain review-only.
- The measured aggregate exact-group volume matches the implemented dry-run closely enough to explain any differences from safety rails/wishlists.

Record counts and structural conclusions only; do not paste real rows or instance ids into `WORKLOG.md`.

## 17. Reversal/manual determinism verification

The automated reversal test is authoritative. As a secondary check, run the fake Slammer fixture through the resolver in original and reversed order and compare decisions after sorting by id.

Do not create or retain a reversed real-vault export in the repository.

## 18. Full completion gate

Run the focused gate first:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q tests/test_dupes.py tests/test_weapons_rules.py tests/test_rails.py tests/test_report_run.py
```

Run snapshot regeneration/check after the ruleset/fixture work:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
.venv/bin/pytest -q tests/test_report_run.py
```

Run the full repository gate:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git status --short
git ls-files data/
```

Also run the fake rule-level CLI smoke using the new fixture:

```bash
.venv/bin/vault-cleaner dupes --input tests/fixtures/weapons_slammer_like.csv --no-wishlists
```

The implementation does not require Playwright, browser, wheel, or CI-specific manual validation unless the actual diff unexpectedly touches those areas; such a touch should normally trigger the scope stop instead.

## 19. Commit and push — no PR

Before committing:

- confirm no files under `data/` are tracked;
- confirm no real export fragments or ids appear in the diff/worklog;
- inspect the complete diff for #29/server/armor/wishlist-scope creep;
- confirm the measurement record is present;
- confirm the ruleset bump is intentional and exactly once.

Commit and push the implementation branch.

Luna must **not** open a pull request.

---

# Required automated tests — consolidated acceptance matrix

The implementation is not complete until tests prove all of the following:

1. fake Slammer-like same-hash distinct rolls survive independently;
2. one true exact duplicate resolves to a deterministic survivor;
3. exact-group decisions are invariant under reversed CSV row order;
4. Hash remains part of identity and same-name different-hash items never group;
5. mutable-state differences excluded by measurement do not split exact identity;
6. randomized roll differences do split identity;
7. selected-marker semantics match the measured contract;
8. multi-option semantics match the measured contract;
9. base/enhanced semantics match the measured contract;
10. incomplete/unknown identity fails safe and cannot false-junk;
11. keep-wishlist matching cannot junk a different fingerprint;
12. exact duplicates still resolve normally when keep-wishlist data is present;
13. explicit wishlist-trash remains unchanged;
14. trash-junked rows cannot become dupe survivors;
15. soft-reviewed trash rows only compete inside their exact fingerprint;
16. keep+trash conflicts retain current count/precedence behaviour;
17. favorite/keep/archive tagged rows retain hard protection;
18. equipped rows retain hard protection;
19. crafted threshold and above-threshold rows retain #32 hard protection;
20. crafted unknown/empty level retains #32 hard protection;
21. malformed crafted state/level still fails explicitly;
22. locked rows remain review-only duplicate losers;
23. exotic rows remain review-only duplicate losers;
24. existing tags/notes are preserved according to current decision rules;
25. current ruleset-version tests reflect the bump;
26. regenerated fake snapshot matches exactly;
27. full pytest and Ruff pass.

---

# Manual verification

Manual verification is useful here because the fingerprint is explicitly derived from real DIM export behaviour.

Required manual checks:

- real-export measurement completed before fingerprint finalisation;
- dry-run on the measured real weapon export with `--no-wishlists`;
- dry-run with normal wishlists if available;
- confirm the original Slammer failure mode is gone;
- compare measured exact-group counts with runtime output and explain rail/wishlist differences;
- no `--write` for these acceptance checks;
- record only aggregate findings.

If the real export is not available to the implementation agent, this ticket hits a mandatory stop condition and returns to Sol/user for the measurement rather than shipping an unmeasured fingerprint.

---

# Luna completion gate

Luna may hand the branch to Sol only when all of these are true:

- real weapon export measurement completed;
- measurement result recorded safely before final fingerprint finalisation;
- fingerprint is documented and bounded;
- unknown/unprovable identity has a fail-safe no-auto-dupe policy;
- different same-hash rolls survive independently;
- true exact duplicates still resolve;
- survivor choice is row-order independent;
- wishlist keep/trash regressions pass;
- #32 crafted and all other safety rails remain intact;
- `RULESET_VERSION` bumped exactly once from the then-current value;
- fake report snapshot regenerated through the repository script if needed;
- `PLAN.md` is no longer stale;
- `WORKLOG.md` contains measurement + implementation + validation results;
- no real export rows or ids are in tracked content;
- no `data/` paths are tracked;
- Ruff passes;
- focused tests pass;
- full pytest passes;
- `git diff --check` passes;
- implementation branch is committed and pushed;
- **no PR has been opened**.

Provide Sol with this structured handoff:

```text
Implementation branch:
Base main SHA:
Commit SHA(s):
Files changed/added:
Measurement summary:
Final exact-roll fingerprint:
Unknown/truncated identity policy:
Implementation summary:
Tests added/changed:
Focused validation results:
Full validation results:
Real-export dry-run results (aggregates only):
Snapshot/ruleset result:
Known risks/uncertainties:
Deviations from plan:
Stop/escalation conditions encountered: none / details
PR opened: no
```

---

# Orchestrating Sol high review checklist / prompt

Review the completed Luna xhigh implementation for issue #31 in `tonym999/vault-cleaner`.

**Do not raise a PR yet.** This ticket is classified for independent final review after your first-pass review is clean.

## 1. Plan-conformance review

Verify against issue #31 and this handoff:

1. Was the real weapon export actually measured before the final fingerprint was chosen?
2. Does `WORKLOG.md` contain only safe aggregate findings — no real rows/ids?
3. Does the measurement justify every identity component and every excluded mutable component?
4. Are selected `*`, multi-option cells, base/enhanced variants, mutable mods/state, and incomplete data explicitly handled?
5. Does unprovable identity fail safe rather than collapse into a partial duplicate key?
6. Is grouping mechanically `Hash + proven exact fingerprint`, with no different-roll same-hash competition?
7. Does keep-wishlist ranking operate only within exact groups?
8. Is wishlist-trash behaviour still a separate earlier rule?
9. Are hard/soft rails unchanged, especially the just-landed #32 crafted behaviour?
10. Is exact-group survivor selection deterministic under reversed input order?
11. Was `RULESET_VERSION` bumped because decision semantics changed?
12. Was the golden regenerated only through the supplied script?
13. Is `PLAN.md` corrected?
14. Was #29 presentation work kept out of scope?
15. Were armor/ghost/server/review/config/dependency surfaces left alone unless directly justified?

## 2. Engineering review

Inspect the actual diff, not Luna’s summary.

Focus on:

- false-merge risk in the fingerprint;
- brittle name allow/deny lists;
- assumptions about perk-column numbering/ordering;
- mutable state accidentally included as identity;
- gameplay identity accidentally excluded;
- malformed/truncated export behaviour;
- accidental network/manifest dependence in `--no-wishlists` mode;
- row-order dependence hidden in sorting/grouping;
- hard-protected copies accidentally receiving output rows;
- soft-protected copies accidentally becoming junk;
- wishlist-trash/keep conflicts changing semantics;
- duplicate decision reason truthfulness;
- snapshot/ruleset stale-review invalidation;
- tests that merely mirror implementation rather than proving behaviour;
- scope creep into #29 or other rules.

## 3. Independently run/verify

At minimum:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q tests/test_dupes.py tests/test_weapons_rules.py tests/test_rails.py tests/test_report_run.py
.venv/bin/pytest -q
git diff --check
git ls-files data/
.venv/bin/vault-cleaner dupes --input tests/fixtures/weapons_slammer_like.csv --no-wishlists
```

Inspect the regenerated snapshot diff and confirm it is explained.

If you have access to the same private export, independently reproduce the aggregate measurement/dry-run outcome without recording real ids.

## 4. Review outcome

If findings exist:

- state each finding precisely;
- explain the safety/correctness impact;
- return it to Luna on the same implementation branch;
- require a regression test where appropriate;
- rerun affected focused tests plus the full completion gate;
- review the fix again.

When the orchestrating review is clean, do **not** mark it ready for PR yet. Hand the branch to an independent Sol high reviewer.

---

# Independent Sol high final review prompt

Perform a fresh independent review of issue #31 in `tonym999/vault-cleaner` after Luna implementation and orchestrating Sol high review are complete.

Do not assume the measurement-derived design is correct merely because the implementation follows it.

Challenge the design from first principles:

1. Could two gameplay-distinct same-hash rolls still produce the same fingerprint?
2. Could mutable current-state differences split one true roll into multiple fingerprints and make the pass useless or misleading?
3. Is the classification based on stable export structure, or on a brittle list of current perk names?
4. Does the design still work with selected markers and multi-option cells?
5. Is the base/enhanced decision justified by measured DIM representation and actual mutability?
6. Could missing/truncated/new `Perks N` data false-merge rows?
7. Does every uncertain case become ungroupable rather than auto-junkable?
8. Is same-name/different-hash separation preserved?
9. Is the survivor truly invariant under CSV reversal?
10. Can wishlist keep/trash data change grouping identity, or only decisions/ranking where intended?
11. Has `--no-wishlists` acquired any hidden manifest/network dependence?
12. Are #32 crafted protections still enforced before junk output?
13. Did the ruleset bump correctly invalidate stale reviews without changing snapshot schema unnecessarily?
14. Are the tests adversarial enough to prove false-merge resistance rather than only the happy path?
15. Did the implementation stay out of #29 presentation work and unrelated architecture?

Re-run the key validation commands independently. If any design assumption is unsupported, return the branch for correction/replanning. Only after this independent review is clean is the implementation eligible to be reported `READY FOR PR`.

---

# Reusable Luna xhigh execution prompt

Implement issue #31 in `tonym999/vault-cleaner` using `handoffs/issue-31-luna-xhigh-implementation-plan.md` as the primary execution contract.

Workflow:

```text
Sol plans/orchestrates → Luna xhigh implements → Sol high reviews → independent Sol high reviews → PR
```

Rules:

- branch from the latest `main`, not the handoff branch;
- read issue #31, #29, #32, #16, #17, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and the current relevant code/tests before changing anything;
- verify the plan still matches current `main`;
- perform the mandatory real weapon export measurement **before finalising the production fingerprint**;
- commit no real vault row, instance id, or file under `data/`;
- mechanically enforce: auto-dupe only when `Hash` and a proven exact-roll fingerprint both match;
- when exact identity is unknown/ambiguous/truncated, do not auto-junk it as a duplicate;
- preserve #32 crafted validation/protection and all existing hard/soft rails;
- preserve wishlist-trash as a separate earlier rule;
- do not let keep-wishlist ranking cause different fingerprints to compete;
- make survivor selection independent of CSV order;
- do not add new runtime/network dependencies or change `dupes --no-wishlists` into a manifest/network path;
- keep #29 survivor-presentation work out of scope;
- add the fake Slammer-like fixture and behavioural regressions;
- bump the current `RULESET_VERSION` exactly once for the changed decision semantics;
- regenerate the golden through `scripts/regenerate_report_snapshot.py`, never by hand;
- update `PLAN.md` and `WORKLOG.md`, plus narrowly relevant README/AGENTS wording;
- follow every stop/escalation condition in the plan instead of broadening scope;
- run focused and full validation exactly as specified;
- perform real-export dry-run verification without `--write`;
- commit and push the implementation branch;
- **do not open a pull request**.

When complete, return:

- implementation branch;
- base `main` SHA;
- commit SHA(s);
- files changed/added;
- safe aggregate measurement summary;
- final fingerprint and unknown-data policy;
- implementation summary;
- tests added/changed;
- exact focused/full validation results;
- real-export dry-run aggregate result;
- ruleset/snapshot result;
- unresolved risks;
- deviations from plan;
- confirmation that no PR was opened.

If the real export is unavailable or the fingerprint cannot be proven safely from the exported data, stop and return the issue to Sol for replanning rather than implementing a guess.

---

# Ticket-specific review decision

**Review path:** `independent`

**Reason:**

#31 changes the semantic boundary for automatically marking weapon instances as junk. The central design choice — what constitutes an immutable exact weapon roll in DIM’s export — is measurement-dependent and safety-critical. A false equivalence can guide destructive in-game action, while the ruleset change also invalidates persisted review fingerprints. The implementation can remain local, but the design assumptions deserve a second Sol high reviewer who was not relying on the original planning model.
