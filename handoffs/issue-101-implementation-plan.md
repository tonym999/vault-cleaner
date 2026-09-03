# Ticket

**Repository:** `tonym999/vault-cleaner`  
**Issue:** `#101 — M9 A: expose authoritative armor exact-duplicate groups in the report`  
**Plan base:** `main` at `190e8473fbd8e9c40b0ec486f6fa70305c10bb61`  
**Implementation model:** Sol plans/orchestrates → **Luna xhigh** implements → orchestrating Sol reviews → independent Sol high reviews → PR

Luna must **not** raise the pull request. Sol reviews the completed implementation before any PR is created.

## Objective

Expose the armour exact-duplicate pass's complete, authoritative groups through the reusable Python report model and the server-delivered snapshot. Each group must contain the exact-pass preferred survivor, every provably matching member (including additional hard-protected copies that produce no decision), enough structured display/audit metadata for later browser work, and each member's truthful disposition.

This is a presentation/audit projection only. The ticket is complete when the report/server contract can describe exact groups without any consumer reimplementing the fingerprint, survivor selector, protection logic or proposal semantics, while the existing duplicate decisions remain semantically unchanged.

## Implementation model decision

**Use Luna xhigh.**

The code footprint should remain modest, but correctness depends on preserving several coupled invariants while refactoring an authoritative rule seam: exact fingerprint membership, unknown-Spirit fail-safe behaviour, survivor ranking, hard/soft protection, decision wording, ordered-pipeline filtering, deterministic ordering, 64-bit identifier handling and snapshot compatibility. Luna high could implement a straightforward projection, but xhigh is the better fit for proving that the new projection and the old decisions are two outputs of one pass rather than accidentally creating a second rules implementation.

## Why this ticket is ready

- Dependency `#29` is complete and merged. Its human-readable survivor/partner presentation and full-id audit preservation are already on `main`.
- `PLAN.md` already records the M9 sequence `#29 → #101 → #102` and makes Python the authoritative rules/report layer.
- `#104` depends on this ticket and `#102` depends on `#101`/`#104`; neither downstream ticket needs to be implemented here.
- The exact-dupe fingerprint, ungroupable Spirit policy, survivor ranking and protection rules already exist and are well covered by focused tests.
- There are no issue comments changing the #101 contract at plan time.

## Current repository state relevant to #101

This plan is based on `main` at `190e8473fbd8e9c40b0ec486f6fa70305c10bb61`, after the location/Guardian-class work from `#105`/PR `#106` landed.

### Important stale-ticket reconciliation

The repository has moved since #101 was drafted:

1. `#105` renamed the misleading report/model `owner` concept to `location` and added armour `guardian_class` from DIM `Equippable`. **Do not reintroduce an `owner` field.** Group members should expose `location`; group-level class should use `guardian_class` (or an equivalently explicit current-schema name).
2. `#105` already advanced `report_run.SNAPSHOT_SCHEMA_VERSION` from 1 to **2**, regenerated `tests/fixtures/report_snapshot_v2.json`, and recorded in `WORKLOG.md` that this is the coordinated single v1→v2 bump. `RULESET_VERSION` remains **3**.
3. Therefore #101 must **not mechanically bump the snapshot to v3**. Treat schema v2 as the coordinated M9 snapshot version and add the exact-group projection to v2, updating the v2 golden deliberately. Add regression coverage that schema stays 2, ruleset stays 3, and the decision fingerprint remains unaffected by this presentation-only projection.
4. If implementation reveals an already-shipped strict consumer that makes adding this field to schema v2 unsafe, **stop and return to Sol**. Do not choose a v3 bump unilaterally; the compatibility decision must be replanned because it contradicts the just-landed #105 coordination decision.

### Authoritative exact-dupe seam today

`src/vault_cleaner/rules/armor_dupes.py` currently:

- owns `spirit_signature`, `unknown_spirit_roll`, `fingerprint`, `in_loadout`, `_survivor_rank` and `_winner_reason`;
- groups by `Hash` + six base stats + raw `Tuning Stat` + `Seasonal Mod` + `Holofoil` + Spirit signature;
- skips incomplete/unknown exotic class-item Spirit rolls before grouping;
- chooses the preferred survivor by hard protection → loadout → lock → Masterwork Tier → Power → deterministic lowest-instance-id tie-break;
- emits no decision for the preferred survivor;
- emits no decision for an additional hard-protected losing copy;
- emits `review` for loadout/soft-protected losing copies and `junk` for ordinary losing copies;
- currently returns only `list[Decision]`, so the complete groups disappear after the pass.

`src/vault_cleaner/pipeline.py` calls `armor_dupes.run(...)` once, removes **decision ids only** from the frame passed to later armour passes, then runs close-dupe and scoring logic. That filtering behaviour is decision semantics and must not change merely because complete group membership becomes available.

`src/vault_cleaner/report_run.py` currently has:

- `SNAPSHOT_SCHEMA_VERSION = 2`;
- `RULESET_VERSION = 3`;
- `ArmorSectionDetails(scored, evaluations, cited_ids, kept_elsewhere)`;
- an armour snapshot object containing score/close-pass metadata but no exact-duplicate groups.

The local server already transports `snapshot_dict(run)` through the session/report API. There is no evidence that server production code needs special handling for a new nested snapshot field; prove pass-through in server tests rather than adding a second server projection.

### Existing test assets

`tests/fixtures/armor_dupes.csv` and `tests/test_armor_dupes.py` already exercise most #101 edge cases with fake data, including:

- an ordinary group;
- a deterministic tie with reversed fixture ordering;
- a group containing hard-protected copies, including an equipped retained copy;
- loadout and locked members;
- power/Masterwork ranking;
- different hashes with the same name;
- different `Tuning Stat` values that must not group;
- exotic Spirit combinations;
- spiritless/truncated exotic class-item rolls that remain ungroupable.

Prefer reusing/mutating these fake rows in tests rather than broad fixture churn unless a genuinely missing case requires a small fake fixture addition.

# Review model

## Review path: **independent**

Use:

```text
Sol orchestrator
    ↓
Luna xhigh implementation
    ↓
Same Sol orchestrator first-pass review
    ↓
Independent Sol high final review
    ↓
PR
```

### Why independent review is required

The feature is read-only, but it changes the reusable Python→browser report/snapshot contract and exposes safety-relevant truth about which exact copy is preferred, which hard-protected copies additionally remain, and which copies are proposed for junk/review. It also requires a refactor at the authoritative exact-dupe rule seam. A projection bug could make the UI display a false survivor or falsely imply that a protected copy is disposable even while the underlying decisions remain safe.

The orchestrating Sol should first verify strict plan conformance and semantic parity. An independent Sol high reviewer should then challenge the contract design, disposition mapping, deterministic ordering, schema-v2 compatibility and the claim that there is still exactly one source of duplicate truth.

# Authoritative context

Before changing code, Luna must read on the **latest `main`**:

- `AGENTS.md`;
- `PLAN.md`, especially the ordered armour rules, M7 report boundary and M9 section;
- issue `#101` and its comments;
- completed predecessor `#29`;
- downstream `#104` and `#102` for the contract they expect, without implementing them;
- completed coordination issue `#105` / merged PR `#106` for the current `location`/`guardian_class` and schema-v2 state;
- the newest relevant `WORKLOG.md` entries;
- `src/vault_cleaner/rules/armor_dupes.py`;
- `src/vault_cleaner/rules/rails.py`;
- `src/vault_cleaner/pipeline.py`;
- `src/vault_cleaner/report_run.py`;
- `src/vault_cleaner/review.py` only to confirm snapshot-version/fingerprint compatibility boundaries;
- `tests/test_armor_dupes.py`;
- `tests/test_report_run.py`;
- `tests/test_server_uploads.py`;
- `tests/fixtures/report_snapshot_v2.json`;
- `scripts/regenerate_report_snapshot.py`;
- `.github/workflows/ci.yml`.

Treat these as authoritative and do not silently redesign them:

- the existing `armor_dupes.fingerprint()` and `unknown_spirit_roll()` policy;
- the existing `_survivor_rank()` and deterministic id tie-break;
- `rails.protection()` as the protection classifier;
- existing exact-dupe `Decision` actions/tags/notes/reasons;
- `pipeline.resolve_armor()` pass ordering and its decision-id filtering semantics;
- current `location` / `guardian_class` model vocabulary from #105;
- `SNAPSHOT_SCHEMA_VERSION == 2` and `RULESET_VERSION == 3`, subject only to the explicit stop/escalation rule above;
- Python as the sole authoritative duplicate/rules engine.

# Scope

## Ticket-specific algorithmic scope rule

For **every proposed production-code change**, Luna must be able to answer **YES** to all four checks below:

1. **Exact-pass provenance:** Is the value/behaviour derived only from a group, row field, protection result, rank result or proposal result already used or selected by the existing armour exact-dupe pass?
2. **Projection necessity:** Is the change mechanically required to construct, classify, deterministically order, serialise, transport or test the authoritative exact-duplicate group projection?
3. **Decision parity:** Can the exact-dupe decision set remain unchanged in group membership, selected survivor, `id`, `kept_id`, action, tag, note/reason and downstream pass ordering?
4. **Boundary preservation:** Does the change avoid altering close-dupe/scoring/weapon rules, verdicts, persistence, stale-state/lifecycle behaviour, authentication/trust boundaries and runtime dependencies?

If **any answer is NO or cannot be proved**, the change does **not** belong in #101. Stop that line of work and return the issue to Sol for replanning rather than expanding scope.

### Mechanical stop/escalation conditions

Return to Sol before proceeding if any of the following becomes necessary:

- changing `fingerprint()` fields, normalisation, `Hash`-based identity or the unknown/truncated Spirit policy;
- changing `_survivor_rank()`, tie-breaking, winner reason semantics, protection precedence or which copy wins;
- changing any existing decision action, tag, generated Note, reason slug, `kept_id`, pass ordering or later-pass filtering;
- implementing a second fingerprint/group builder/survivor selector in `pipeline.py`, `report_run.py`, server code or JavaScript;
- changing close-dupe, scoring, wishlist, weapon, verdict, finalisation, persistence, stale-state, reset, upload transactionality or lifecycle behaviour;
- changing server authentication, loopback/origin/Host protections or any filesystem trust boundary;
- changing `review.py` manifest/override formats or validators to make the projection work;
- adding a runtime dependency;
- touching browser UI/JavaScript to render the groups;
- changing `parse.py` or required export schemas because a desired display field is not already available to the exact-dupe pass;
- needing to bump snapshot schema to 3, or discovering a strict consumer that makes the planned additive schema-v2 change unsafe;
- needing broader cross-surface Tuning Mod Slot behaviour owned by `#104` rather than the exact-group field required here.

Incidental defects outside this rule should be documented separately for Sol; do not fix them in this implementation.

## In scope

- Refactor the armour exact-dupe seam so one authoritative pass yields both the existing decisions and immutable/read-only exact-group presentation data.
- Add a group/member report model containing the required display and audit metadata already available from the pass.
- Truthfully classify each member as preferred survivor, additionally retained/protected, proposed junk or proposed review.
- Include an explicit labelled Tuning Mod Slot value for each group while retaining raw `Tuning Stat` as identity input; never infer tuning from the six-stat vector.
- Add deterministic group identity, group ordering and member ordering independent of CSV row order.
- Thread the authoritative groups through `ArmorPipelineResult` → `ArmorSectionDetails` → `snapshot_dict()`.
- Prove the local server returns the same group projection without browser inference or a server-side duplicate implementation.
- Keep opaque ids and hashes as JSON strings.
- Deliberately update the schema-v2 golden and focused snapshot tests.
- Add focused fake-data regressions for all #101 acceptance cases.
- Append a dated `WORKLOG.md` entry documenting the projection and compatibility decision.

## Out of scope

- Rendering or interacting with an Armor duplicates browser view (`#102`).
- Cross-surface/pairwise Tuning Mod Slot presentation (`#104`) beyond the exact-group field required by #101.
- Weapon duplicate-group projection.
- Close-duplicate clustering or pair graphs.
- New cleanup/scoring/wishlist decisions.
- Any preference between Weapons, Health, Class, Grenade, Super or Melee tuning values.
- DIM Note or terminal wording changes beyond the already-landed #29/#105 work.
- Group-level approve/veto operations.
- Review/finalisation/persistence/stale-state/lifecycle changes.
- New runtime or dev dependencies.
- Browser/Playwright changes.

# Expected change footprint

Likely production files:

```text
src/vault_cleaner/rules/armor_dupes.py
src/vault_cleaner/pipeline.py
src/vault_cleaner/report_run.py
```

Likely tests/artifacts:

```text
tests/test_armor_dupes.py
tests/test_report_run.py
tests/test_server_uploads.py
tests/fixtures/report_snapshot_v2.json
WORKLOG.md
```

A small fake-fixture change under `tests/fixtures/` is acceptable only if existing fake rows cannot express a required case cleanly.

Files/components that should normally remain unchanged:

```text
src/vault_cleaner/parse.py
src/vault_cleaner/rules/rails.py
src/vault_cleaner/rules/armor_close.py
src/vault_cleaner/rules/armor.py
src/vault_cleaner/rules/weapons.py
src/vault_cleaner/rules/dupes.py
src/vault_cleaner/duplicate_reference.py
src/vault_cleaner/note_history.py
src/vault_cleaner/review.py
src/vault_cleaner/review_session.py
src/vault_cleaner/server/app.py
src/vault_cleaner/server/session.py
src/vault_cleaner/ui/
README.md
PLAN.md
AGENTS.md
config.toml
pyproject.toml
.github/workflows/ci.yml
```

If substantive changes to one of these normally-unchanged components appear necessary, apply the stop/escalation rule rather than widening the ticket. A focused **test-only** server change is expected in `tests/test_server_uploads.py`; server production code should remain pass-through.

# Proposed group contract

The exact field names may be refined during implementation, but keep the contract small, explicit and JSON-safe. A target shape is:

```json
{
  "exact_duplicate_groups": [
    {
      "group_id": "<stable opaque string>",
      "hash": "<opaque string>",
      "name": "<export text>",
      "type": "<DIM Type/slot text>",
      "guardian_class": "<Equippable text>",
      "item_archetype": "<export Archetype text>",
      "stats": {
        "weapons": 0,
        "health": 0,
        "class": 0,
        "grenade": 0,
        "super": 0,
        "melee": 0
      },
      "tuning_mod_slot": "Melee",
      "seasonal_mod": "",
      "holofoil": "",
      "spirit_signature": [],
      "preferred_survivor_id": "<opaque string>",
      "members": [
        {
          "id": "<opaque string>",
          "location": "Vault",
          "protection_level": null,
          "protection_reason": "",
          "equipped": false,
          "in_loadout": false,
          "locked": false,
          "masterwork_tier": 0,
          "power": 0,
          "disposition": "preferred_survivor",
          "proposal_action": null,
          "proposal_reason": null
        }
      ]
    }
  ]
}
```

Contract rules:

- `group_id` must be stable under row reversal and must not depend on list position. Prefer a deterministic member-derived opaque string such as the lowest member id, rather than a row index. It should remain stable when mutable ranking fields change but membership does not.
- `hash`, all instance ids and `group_id` remain strings in the report/JSON even if an existing internal tie-break temporarily parses an id numerically.
- `name`, `type`, `guardian_class`, `item_archetype`, seasonal mod, holofoil, Spirit text and locations are inert export-derived text. Do not interpret them as HTML.
- `stats` are the same six base-stat values used by the fingerprint, projected with the established report stat keys.
- `tuning_mod_slot` is a presentation label for the raw `Tuning Stat` already in the fingerprint. The supported labels are `Weapons`, `Health`, `Class`, `Grenade`, `Super`, `Melee`, plus an explicit `none/unknown`. Do **not** normalise the value before fingerprinting or merge groups on the presentation label.
- The preferred survivor is first in `members`.
- Additional hard-protected retained copies follow the survivor and use `retained_protected`.
- Proposed members follow retained copies and use `proposed_junk` / `proposed_review` matching the exact pass's real `Decision.action`.
- `proposal_action`/`proposal_reason` must come from the same exact-pass branch that created the Decision, not from reparsing the generated Note later.
- A hard-protected loser has no proposal action/reason; its protection fields explain why it remains.
- Do not add speculative UI-only fields that #102 can derive trivially from this explicit contract.

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline

Do **not** implement on the handoff-storage branch. Read this plan from `handoff/issue-101-luna-plan`, then branch the implementation from the latest `main`.

Suggested implementation branch:

```text
issue-101-armor-exact-dupe-groups
```

Before editing:

```bash
git fetch origin
git checkout main
git pull --ff-only
git status --short
git rev-parse HEAD
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q tests/test_armor_dupes.py tests/test_report_run.py tests/test_server_uploads.py
git diff --check
test -z "$(git ls-files data/)"
```

Record the base `main` SHA in the Luna→Sol handoff. If baseline focused/full validation is already failing for a repository reason unrelated to #101, report it to Sol before attributing failures to the implementation.

## 2. Introduce one authoritative exact-dupe analysis result

Refactor `rules/armor_dupes.py` so the grouping/ranking loop produces a small result object containing **both**:

- the existing decisions; and
- the exact-group projection model.

Preferred pattern:

- immutable dataclasses/tuples for exact-group/member output;
- an `analyse(...)`/`resolve(...)` function that performs the pass once;
- retain `run(...) -> list[Decision]` as a compatibility wrapper if that keeps existing direct callers/tests stable;
- `pipeline.resolve_armor()` should call the authoritative result-producing function **once**, not call `run()` and then rebuild groups separately.

Do not duplicate `fingerprint()`, `unknown_spirit_roll()`, `_survivor_rank()` or `rails.protection()` logic in another module.

## 3. Build groups from the same loop that selects the survivor

For each exact group of two or more provably matching rows:

1. Reuse the existing fingerprint and unknown-Spirit guard unchanged.
2. Select `best` with the exact existing ranking/tie-break unchanged.
3. Create the group-level metadata from a deterministic group member (prefer the selected survivor) while preserving raw export text as text.
4. Create the preferred-survivor member record.
5. Iterate each non-survivor through the **existing** protection/decision branches.
6. If a non-survivor is hard-protected, keep the existing `continue` decision behaviour but also create a `retained_protected` member record.
7. If the existing code emits a review/junk Decision, create the member record from that same branch with matching proposal action/reason.
8. Append the existing Decision exactly as before.
9. Sort/finalise the member list deterministically without using CSV row position.
10. Emit the group once.

The new model must not change whether a row proceeds into later passes. In `pipeline.resolve_armor()`, compute `remaining` from the ids of **decisions**, as it does today; do not remove all exact-group members just because they appear in the projection.

## 4. Define truthful member dispositions

Use exactly four dispositions:

- `preferred_survivor` — the current selected `best` row;
- `retained_protected` — a non-best row for which the exact pass emits no Decision because protection is hard;
- `proposed_junk` — a non-best row for which the exact pass emits `Decision.action == "junk"`;
- `proposed_review` — a non-best row for which the exact pass emits `Decision.action == "review"`.

Assert in code/tests that every group member lands in exactly one category and every proposed member maps to one exact-pass Decision with the same id/action/reason.

Do not label a hard-protected extra copy as another “survivor”. There is one **preferred survivor**, but there may be multiple retained copies.

## 5. Project display metadata without changing identity

Carry only information already present on exact-group rows or already computed by exact-dupe/protection logic:

- group `Hash` as a string;
- `Name` as display text only, never identity;
- `Type`/slot text;
- current `guardian_class` from `Equippable` (do not parse class from `Owner`/`location`);
- raw `Archetype` display text;
- six base stats;
- a distinct Tuning Mod Slot label;
- `Seasonal Mod`, `Holofoil`, Spirit signature where applicable;
- preferred survivor id;
- each member's id and `location` (`Owner` source, current model name);
- protection level/reason, equipped/loadout/locked state, Masterwork Tier and Power;
- disposition and associated proposal action/reason.

For Tuning Mod Slot, add only a presentation mapping around the raw already-consumed `Tuning Stat`: recognise all six vocabulary values generically and surface blank/unrecognised values honestly as `none/unknown`. Do not add a preference order, infer tuning from stats or normalise the raw identity input before fingerprinting.

## 6. Make ordering deterministic

Define ordering in the Python producer so #102 does not need to infer it.

Required invariants:

- reversing the input DataFrame produces byte/structure-equivalent ordered groups;
- preferred survivor is member 0;
- retained-protected members come next;
- proposed members come last;
- ordering within a disposition bucket is deterministic using an existing-safe id ordering rule, never CSV index;
- group ordering is deterministic, e.g. by `(hash, group_id)` or another documented stable key;
- `group_id` itself is stable and row-order independent.

Do not use `Name` as group identity or primary group key.

## 7. Thread groups through the existing pipeline/report seam

Extend `ArmorPipelineResult` with the authoritative group tuple/list.

In `resolve_armor()`:

- get decisions and groups from the single exact-pass analysis;
- preserve current `remaining` calculation from exact-pass **decision ids**;
- leave close-pass/scoring logic otherwise untouched;
- return exact groups alongside existing armour result fields.

Extend `ArmorSectionDetails` in `report_run.py` to retain those groups and add them under the armour section snapshot, preferably as `exact_duplicate_groups`.

Use dataclass serialisation or an explicit small snapshot helper in `report_run.py`; do not reconstruct grouping/ranking/dispositions there.

## 8. Preserve the schema/fingerprint compatibility decision

For this ticket on the current base:

- keep `SNAPSHOT_SCHEMA_VERSION = 2`;
- keep `RULESET_VERSION = 3`;
- do not add group output to `_decision_config`;
- do not alter `compute_fingerprint()` inputs;
- regenerate `tests/fixtures/report_snapshot_v2.json` in place with the repository script;
- verify the golden's existing fingerprint value does not change solely because the new output field exists;
- run existing review-manifest tests so current schema-v2 manifests remain accepted and pre-v2 manifests remain rejected exactly as #105 established.

Rationale: #105 deliberately owned the coordinated v1→v2 snapshot bump and landed immediately before #101. The new group field is completing the M9 v2 report contract before #102 consumes it. If actual code reveals that this assumption is unsafe, stop for Sol; do not improvise v3.

## 9. Prove server pass-through without changing server semantics

Add a focused `tests/test_server_uploads.py` case that uploads a fake armour exact-dupe fixture, then verifies the `/api/report` or upload response contains the authoritative `exact_duplicate_groups` data from the report snapshot.

The server test should prove:

- survivor + every member arrive in the response;
- retained protected copy is present;
- ids/hashes are strings;
- the server did not transform/recompute the group.

Do not change `server/app.py` or `server/session.py` unless a real pass-through defect is found; such a defect is an escalation point because #101 should not alter lifecycle/protocol mechanics beyond carrying the report snapshot.

## 10. Preserve hostile/untrusted text as inert data

Add a fake-data regression using hostile-looking text in one or more display fields (for example a name/location/archetype containing HTML-like markup). Assert that the Python report/snapshot retains it as an ordinary JSON string and does not reinterpret or pre-render it.

Do not add HTML escaping here. Safe DOM rendering belongs to the browser layer; the producer's responsibility is typed JSON data with strings preserved exactly.

## 11. Update the golden deliberately

Run:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
```

Review the diff manually. The schema-v2 golden should gain the new armour exact-group key (possibly an empty list if the standard golden fixture contains no exact groups) and nothing should change in decision semantics, schema version, ruleset version or fingerprint because of the projection itself.

Do not rename the golden to v3.

## 12. Update `WORKLOG.md`

Append a dated entry recording:

- one authoritative exact-dupe pass now supplies both decisions and group projection;
- the chosen group/member ordering and stable group-id rule;
- how additional hard-protected copies are represented;
- the explicit Tuning Mod Slot representation, including `none/unknown`;
- the #105 compatibility decision: snapshot remains v2, ruleset remains v3, decision fingerprint unchanged;
- server pass-through result;
- tests/validation run;
- any surprising implementation finding relevant to #104/#102, without implementing those tickets.

`PLAN.md` already records M9 ownership/sequencing and should not need modification for this ticket.

# Required automated tests

Add/update focused behavioural coverage proving at least the following.

## `tests/test_armor_dupes.py`

1. **Ordinary group** — group includes preferred survivor plus all ordinary losers; loser Decisions remain unchanged.
2. **Tie** — selected survivor remains the existing deterministic lowest-id winner; member/group order is deterministic.
3. **Multiple retained/protected copies** — use the existing hard-protected fixture group to prove a non-best hard-protected copy is present as `retained_protected` even though it has no Decision.
4. **Loadout/soft protection** — review members are `proposed_review` and retain existing review Decision content.
5. **Ungroupable Spirit roll** — spiritless/truncated exotic class-item rows produce neither a false group nor false decisions.
6. **Spirit identity** — different complete Spirit signatures remain separate.
7. **Hash identity** — same name/different Hash never groups.
8. **Tuning identity** — otherwise identical rows with two different supported tuning values never collapse into one exact group.
9. **Tuning vocabulary** — multiple supported values project generically; blank/unrecognised maps to explicit `none/unknown` without affecting raw fingerprint behaviour.
10. **Reverse-order determinism** — reverse the DataFrame and compare ordered group structures as well as Decisions.
11. **Disposition bijection** — every proposed member corresponds to exactly one existing exact-pass Decision; every hard-protected retained member corresponds to none.
12. **Semantic parity** — retain all existing exact-dupe assertions for action/tag/note/reason/winner wording and ranking.

## `tests/test_report_run.py`

13. Exact groups appear under the armour report/snapshot section with required metadata.
14. Full 64-bit-ish fake ids/hashes remain JSON strings in group ids, preferred survivor ids and member ids.
15. Hostile export-derived text survives as plain JSON strings.
16. `schema_version == 2` and `ruleset_version == 3` remain unchanged.
17. The projection does not change the report decision fingerprint for the same source/config/ruleset inputs.
18. Snapshot serialisation remains deterministic.
19. Regeneration script still reproduces `report_snapshot_v2.json` byte-for-byte.
20. Golden diff is deliberate and limited to the new v2 projection plus any directly required fake-fixture effects.

## `tests/test_server_uploads.py`

21. Upload a fake armour export containing exact groups and assert the returned server snapshot exposes the same complete group contract, including retained copies and string ids.

## Existing regression suites to rerun unchanged

At minimum also run existing review-manifest/version tests and close/scoring pipeline tests so the new result field cannot mask a pass-order or compatibility regression.

No new Playwright test is required by #101; browser rendering is #102. No CI workflow change is expected.

# Manual verification

No browser/manual UI verification is required because this ticket does not render the groups. Automation should prove the report and server response contract completely.

Useful reviewer inspection only:

- inspect one fake group in `snapshot_json()` or the server test response and verify the labels read truthfully;
- inspect the golden diff to confirm schema/ruleset/fingerprint stability and absence of real data;
- inspect `git diff` to confirm no browser, persistence or lifecycle code was pulled in.

# Exact validation commands

Run from the repository root with the project dev environment installed.

## Focused implementation gate

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_armor_dupes.py \
  tests/test_armor_close.py \
  tests/test_armor_rules.py \
  tests/test_report_run.py \
  tests/test_review.py \
  tests/test_server_uploads.py
```

If the review/version tests live under an additional existing review test module on the current branch, include that module in the focused gate as well rather than weakening coverage.

## Golden reproducibility gate

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
.venv/bin/pytest -q tests/test_report_run.py
```

After the intended golden is committed, rerun the regeneration command and verify it creates no diff:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
git diff --exit-code -- tests/fixtures/report_snapshot_v2.json
```

## Full completion gate

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
test -z "$(git ls-files data/)"
git status --short
```

The repository CI also runs the full suite on Ubuntu/Windows plus its existing separate browser/wheel job. #101 should not modify those jobs. If local sandbox restrictions prevent existing socket/Chromium tests from starting, record the exact environmental failure and have Sol independently rerun the required unrestricted validation before declaring the branch review-clean; do not add retries/skips to make #101 pass.

# Luna completion gate

Luna may hand back the branch only when all of the following are true:

- one authoritative exact-dupe pass produces both existing Decisions and exact-group data;
- no second fingerprint, survivor selector, protection classifier or disposition inference exists elsewhere;
- every provably matching member is present, including hard-protected retained copies;
- preferred survivor and proposal dispositions match the existing rule output exactly;
- unknown/truncated exotic class-item Spirit rolls remain absent;
- differently tuned rows remain separate exact groups;
- group/member ordering is stable under row reversal;
- all ids/hashes/group ids are serialized as strings;
- hostile text remains ordinary JSON string data;
- `SNAPSHOT_SCHEMA_VERSION` remains 2 and `RULESET_VERSION` remains 3;
- current report fingerprint semantics remain unchanged;
- server pass-through is proven without production server/lifecycle changes;
- `report_snapshot_v2.json` is deliberately regenerated and reproducible;
- `WORKLOG.md` has a dated #101 entry;
- no real vault rows/data or files under `data/` are tracked;
- focused, golden and full validation gates pass (or any environment-only restriction is explicitly handed to Sol for unrestricted rerun);
- implementation branch is committed and pushed;
- **no pull request has been opened**.

Luna's handoff to Sol must include:

- implementation branch;
- base `main` SHA;
- commit SHA(s);
- files changed;
- concise implementation summary;
- exact group contract chosen if it differs from the target shape above;
- tests added/changed;
- exact focused/full validation results;
- golden regeneration result;
- confirmation of schema/ruleset/fingerprint compatibility;
- confirmation no production server/UI/review/persistence code changed, or a precise approved deviation;
- unresolved risks/uncertainties;
- any deviation from this plan.

# Orchestrating Sol review prompt

Review the completed Luna xhigh implementation for issue `#101` in `tonym999/vault-cleaner`.

**Do not raise a PR yet.** This ticket uses the independent review path.

Read issue #101, its linked/dependency context (#29, #104, #102), completed #105/PR #106, `AGENTS.md`, `PLAN.md`, this handoff plan and the actual branch diff against its recorded base `main` SHA. Do not rely on Luna's summary alone.

## 1. Plan-conformance review

Confirm every acceptance criterion and specifically verify:

1. one and only one authoritative exact-dupe pass supplies decisions and groups;
2. the original fingerprint and unknown-Spirit behaviour are untouched;
3. the original survivor ranking/tie-break are untouched;
4. the preferred survivor in each group is the same `kept_id` selected by existing Decisions;
5. additional hard-protected losing copies appear as retained/protected even though they emit no Decision;
6. proposed group members map exactly to existing junk/review Decisions and reasons;
7. pipeline `remaining` still excludes decision ids only and pass ordering is unchanged;
8. `Hash`, never `Name`, owns group identity;
9. Tuning Mod Slot is explicit and differently tuned rows cannot collapse;
10. group/member ordering is deterministic under reversed input;
11. ids/hashes remain strings and hostile text stays inert data;
12. current `location`/`guardian_class` vocabulary from #105 is used; no `owner` model is reintroduced;
13. snapshot remains schema v2, ruleset v3, and decision fingerprint inputs are unchanged;
14. `report_snapshot_v2.json` was regenerated deliberately and its fingerprint did not change merely because projection output was added;
15. server tests prove pass-through without duplicate logic in server code;
16. no #102 browser rendering, #104 pairwise tuning work, review/persistence/lifecycle/auth changes or unrelated refactors leaked in;
17. `WORKLOG.md` records the projection and compatibility decision.

## 2. Engineering review

Review the actual implementation for:

- correctness and maintainability;
- accidental duplicate sources of truth;
- mutable-row references escaping the rule pass instead of stable projected values;
- disposition states that can become contradictory;
- unstable group ids/order;
- accidental `Number`/numeric JSON conversion of opaque ids;
- silent coercion of unknown tuning/Spirit data;
- overly broad schema churn;
- accidental changes to Notes/reason slugs or later-pass eligibility;
- insufficient regression coverage around retained protected copies and row reversal.

Independently rerun at least:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_armor_dupes.py \
  tests/test_armor_close.py \
  tests/test_armor_rules.py \
  tests/test_report_run.py \
  tests/test_review.py \
  tests/test_server_uploads.py
.venv/bin/python scripts/regenerate_report_snapshot.py
git diff --exit-code -- tests/fixtures/report_snapshot_v2.json
.venv/bin/pytest -q
git diff --check
test -z "$(git ls-files data/)"
```

If you find issues, return precise findings to Luna, require fixes on the same implementation branch, rerun affected tests plus the full completion gate, and review again.

When the orchestrating review is clean, **do not raise the PR**. Hand the branch to an independent Sol high reviewer using the prompt below.

# Independent Sol high review prompt

Perform an independent final review of the completed implementation for issue `#101` in `tonym999/vault-cleaner`.

The branch has already been implemented by Luna xhigh and checked against the implementation plan by the orchestrating Sol. **Do not assume the design is correct merely because it follows the plan, and do not raise a PR.**

Approach the diff fresh, with special focus on:

1. **Single-source-of-truth design** — Are grouping, survivor selection, protection and member dispositions genuinely produced from one authoritative exact pass, or is any rule logic duplicated in pipeline/report/server code?
2. **Safety truth** — Can the projection ever call a hard-protected retained copy junk/review, omit a protected exact copy, or report a different survivor from the Decision model?
3. **Identity validity** — Are Hash, six stats, raw Tuning Stat, Seasonal Mod, Holofoil and Spirit signature still exactly the existing identity? Are unknown/truncated Spirit rolls still fail-safe?
4. **Ordering/stability** — Are group id, group order and member order deterministic under reversed rows and independent of CSV index?
5. **Pipeline semantics** — Did exposing complete group membership accidentally alter which rows reach close-dupe/scoring passes?
6. **Contract/versioning** — Is keeping snapshot schema v2 sound given #105's coordinated bump? Do current review manifests/fingerprint semantics remain valid? If not, stop for replanning rather than casually introducing v3.
7. **Data types/trust boundary** — Are 64-bit ids/hashes strings throughout JSON? Is export-derived text still inert and free of HTML interpretation?
8. **Scope** — Did the ticket absorb #104/#102 UI/tuning work or unrelated server/review/lifecycle changes?
9. **Tests** — Do tests prove behaviour, not merely source structure, for ordinary/tie/protected/Spirit/tuning/reversal/server/golden cases?
10. **Maintainability** — Is the group model minimal enough for downstream consumers without leaking pandas rows or creating a second long-lived representation of rule state?

Require fixes/regressions on the same branch for any finding. Only after this independent review is clean should the implementation be reported as **READY FOR PR**. A PR must still wait for explicit user instruction.

# Reusable Luna xhigh execution prompt

Implement issue `#101` in `tonym999/vault-cleaner` using the Sol handoff plan stored on branch `handoff/issue-101-luna-plan` at:

```text
handoffs/issue-101-luna-xhigh-implementation-plan.md
```

Use **Luna xhigh**.

Workflow:

```text
Sol plans/orchestrates → Luna xhigh implements → orchestrating Sol reviews → independent Sol high reviews → PR
```

Rules:

- read issue #101 and all comments, #29, #104, #102, completed #105/PR #106, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and the current relevant code/tests before editing;
- read the handoff from its handoff branch, but create the **implementation branch from the latest `main`**, not from the handoff branch;
- record the base `main` SHA;
- treat the handoff's ticket-specific algorithmic scope rule and stop/escalation conditions as mandatory;
- produce decisions and groups from one authoritative armour exact-dupe pass;
- preserve fingerprint, unknown-Spirit policy, survivor ranking, action/tag/note/reason semantics and ordered-pipeline behaviour;
- use current `location` / `guardian_class` vocabulary from #105 and do not reintroduce `owner`;
- keep snapshot schema at v2 and ruleset at v3 unless implementation proves that unsafe, in which case stop and return to Sol rather than bumping unilaterally;
- add behavioural tests alongside implementation;
- regenerate the schema-v2 golden deliberately;
- update `WORKLOG.md`;
- run the exact focused, golden and full validation gates from the plan;
- commit and push the implementation branch;
- **do not open a pull request**.

When complete, return a structured handoff containing:

- implementation branch;
- base `main` SHA;
- commit SHA(s);
- files changed;
- implementation summary;
- exact group contract implemented;
- tests added/changed;
- exact validation results;
- golden regeneration/schema/ruleset/fingerprint results;
- any environment-only validation limitations;
- unresolved risks/uncertainties;
- deviations from the plan;
- explicit confirmation that no PR was raised.

# Ticket-specific review decision

**Review path:** `independent`

**Reason:** #101 is a presentation-only feature in terms of decisions, but it refactors the authoritative armour exact-dupe seam and extends the Python→browser report/snapshot contract with safety-relevant survivor and retained/proposed disposition data. A wrong projection can mislead the reviewer even if the underlying junk decisions remain safe. Orchestrating Sol should first prove plan conformance and semantic parity; a fresh Sol high reviewer should then challenge the contract/versioning and single-source-of-truth assumptions before the branch can be considered ready for PR.
