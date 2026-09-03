# Issue #32 — Luna xhigh Implementation Plan

**Repository:** `tonym999/vault-cleaner`  
**Issue:** `#32 — Recognize DIM's Crafted=crafted token in crafted-level safety rail`  
**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → Sol high reviews → PR  
**Plan date:** 2026-08-28  
**Planning baseline:** `main` at `88253914724291732536ec5e27c8476a7ea6b983`

## Objective

Repair the crafted-level hard safety rail so it recognises DIM's measured `Crafted=crafted` value and prevents crafted weapons at or above `rails.crafted_level_protect` from producing any wishlist-trash or duplicate output row.

The intended end state is:

- DIM's real `crafted` token means crafted;
- `false` and the explicitly supported empty value mean not crafted;
- unknown non-empty crafted-state values fail before rule decisions are produced;
- crafted weapons at the threshold and above are hard-protected, including when unlocked;
- crafted weapons below the threshold continue through the existing wishlist and duplicate rules;
- the generic boolean parser remains responsible only for genuinely boolean columns such as `Locked` and `Equipped`;
- the ruleset fingerprint changes because decision semantics have changed.

This ticket repairs one safety-critical field contract. It must not redesign weapon identity, ranking, wishlist semantics, the two-tier rail model, or any browser/server workflow.

## Why this ticket is ready

- The foundational safety-rail work from issue #1 landed in PR #11 and remains the established architecture: one shared `rails.protection` classifier, with crafted threshold protection classed as hard.
- Issue #32 is open, has no comments, no parent or sub-issues, and no GitHub blocked-by/blocking relationships. Its timeline contains only milestone/project metadata.
- The separately mentioned same-Hash/different-roll defect is issue #31. It remains open, but it is not a dependency of this token fix; #32 must not absorb its fingerprint/ranking work.
- The current code still reproduces the defect: `rails.protection` applies `is_true()` to `Crafted`, while `is_true()` recognises only `true`.
- The current fake duplicate fixture still models crafted weapons as `true`, so the existing green test suite gives false confidence. No issue #32 implementation or PR is present on the inspected repository.
- Baseline validation on the planning commit passed: Ruff was clean and the full suite reported `676 passed, 2 skipped`.

Important safety note: fixing #32 does **not** make current weapon cleanup generally safe while issue #31 remains open. Do not use this ticket to claim or test that same-Hash weapon duplicate decisions are otherwise trustworthy.

---

# Review model

## Standard review path — Sol high pre-PR review

```text
Sol orchestrator
    ↓
Luna xhigh implementation
    ↓
Sol high review
    ↓
PR
```

This is bounded, mechanical, and localised work: define one field-specific DIM token contract, route the existing hard rail through it, validate that contract at weapon ingestion, update focused fixtures/tests, and record the resulting ruleset-version change. It does not require an architectural, protocol, persistence, concurrency, stale-state, lifecycle, authentication, authorisation, or security-boundary change.

The behaviour is safety-sensitive because a missed hard rail can create a junk recommendation, so Sol high must scrutinise the fail-closed policy and both decision paths before a PR is raised. That risk is still well contained by a standard review because the intended code change is small and its complete input/output matrix can be tested directly.

If implementation starts to require a new architecture, a broader rule rewrite, or acceptance of additional undocumented tokens, stop and return the issue to Sol. That would invalidate this standard-risk classification.

---

# Authoritative context

Before changing code, read:

- `AGENTS.md`
- `PLAN.md`, especially rule ordering and the hard/soft rail definition
- issue #32
- issue #1 and merged PR #11, which established the current safety-rail contract
- issue #31, only to preserve its boundary as separate open work
- the newest relevant `WORKLOG.md` entries and the original 2026-07-18 M2 entry
- `src/vault_cleaner/parse.py`
- `src/vault_cleaner/rules/rails.py`
- `src/vault_cleaner/rules/weapons.py`
- `src/vault_cleaner/rules/dupes.py`
- `src/vault_cleaner/pipeline.py`
- `src/vault_cleaner/report_run.py`
- the focused tests and fixtures listed in the expected footprint below

Treat these current contracts as authoritative:

- `rails.protection` is the single shared hard/soft protection classifier.
- Hard protection means no output row at all.
- The order remains protected DIM tag → equipped → crafted threshold → exotic → locked for valid data.
- `Locked` and `Equipped` are boolean fields and continue to use `is_true()`.
- `Crafted` is **not** a boolean field; DIM's measured non-empty values are `crafted` and `false`.
- Empty `Crafted` is an explicitly supported not-crafted value. This preserves current fake/base exports and shared rail calls for item kinds without the field.
- Weapon loaders validate safety-critical source data before rule passes run.
- `rails.crafted_level_protect` remains the only threshold source.
- Earlier rule decisions win; this ticket must not change pass ordering.
- `report_run.RULESET_VERSION` must be bumped whenever decision semantics change.
- Real vault rows and instance IDs must never be committed.

Do not silently redesign any of these contracts.

---

# Algorithmic scope rule

For **every proposed edit**, Luna must apply this mechanical test.

The edit belongs in issue #32 only if both conditions are true:

1. It is necessary for at least one of these four ticket outcomes:
   - interpret the `Crafted` field using the explicit `crafted` / `false` / empty contract;
   - ensure an unlocked crafted weapon at or above the configured threshold emits no wishlist-trash or duplicate decision;
   - make an unknown non-empty crafted-state value fail before any decision output;
   - update the minimum fixture, regression test, ruleset fingerprint/golden, `AGENTS.md`, or `WORKLOG.md` evidence required by the preceding semantic change.
2. It preserves all existing non-crafted behaviour and does not implement work owned by another ticket.

If either condition is false, the edit is out of scope.

### Required stop/escalation conditions

Stop implementation, leave the branch in a reviewable state, and return the finding to Sol rather than expanding scope if any of the following occurs:

- evidence shows DIM currently emits another non-empty crafted-state token besides `crafted` and `false`;
- accepting the legacy fake-fixture token `true` appears necessary for a real external compatibility contract rather than merely keeping old tests green;
- completion appears to require changing generic `is_true()` semantics;
- completion appears to require changing crafted-level numeric parsing/coercion, the configured threshold, rail precedence, hard/soft classifications, or protection reasons;
- completion appears to require changing weapon grouping/fingerprints, survivor ranking, wishlist matching, pass ordering, notes/tags, or output schema;
- the work crosses into issue #31's same-Hash/different-roll defect or issue #34's useful-combination ranking;
- a server, review UI, manifest, persistence, lifecycle, concurrency, network, filesystem, CI architecture, or dependency change appears necessary;
- real vault rows or instance IDs would need to be committed to demonstrate the fix;
- the expected small/localised footprint grows materially without a direct line to one of the four ticket outcomes above.

In particular, do not broaden the accepted crafted token set “just in case”. The default policy for this ticket is deliberately:

| Normalised `Crafted` value | Meaning |
| --- | --- |
| `crafted` | crafted |
| `false` | not crafted |
| empty | not crafted |
| `true` or any other non-empty value | reject as malformed/unknown |

Normalising surrounding whitespace and letter case is acceptable and consistent with the repository's existing scalar helpers. Adding synonyms is not.

---

# Current repository state relevant to #32

## Production behaviour

- `src/vault_cleaner/rules/rails.py` defines `is_true(value)` as a stripped, lower-cased comparison with `true`.
- `rails.protection()` currently calls `is_true(row.get("Crafted", ""))`, so DIM's real `crafted` value evaluates false.
- The crafted check is already in the correct precedence position and already returns `HARD` with a `crafted-lv...` reason. The defect is token interpretation, not rail ordering.
- `src/vault_cleaner/rules/weapons.py` applies protection to wishlist-trash candidates and then invokes the duplicate resolver.
- `src/vault_cleaner/rules/dupes.py` independently applies protection to duplicate losers. Both paths must use the repaired shared classifier; neither should gain a separate crafted check.
- `src/vault_cleaner/parse.py` requires `Type` and `Ammo` for weapon exports but does not currently require `Crafted` or `Crafted Level`, even though the hard rail consumes both. Missing fields can therefore fall through `.get(..., "")` and disable protection silently.
- `src/vault_cleaner/report_run.py` has `RULESET_VERSION = 1`. Correctly recognising `crafted` changes decision semantics and therefore requires version `2` under `AGENTS.md`.

## Existing tests and fixtures

- `tests/test_rails.py` asserts crafted protection using the incorrect `Crafted="true"` representation. It covers above and below threshold but not the exact boundary or malformed-state policy.
- `tests/fixtures/weapons_dupes.csv` contains ordinary `false` rows and two incorrect `true` crafted rows at levels 12 and 2. The level-12 row is an unlocked duplicate loser, so changing it to the real token provides a valuable end-to-end dupe regression.
- `tests/test_dupes.py` already asserts that the level-12 row produces no output and the level-2 row is junked. Keep this behaviour, but drive it with real DIM tokens and add the exact threshold boundary.
- `tests/test_weapons_rules.py` has wishlist-trash and hard-protection coverage, but its hard-protected case is tag-based rather than crafted-state based.
- `tests/test_parse.py` already has a shared path/byte loader rejection-parity table. Extend that pattern for an unknown non-empty `Crafted` value and for newly required safety columns.
- `tests/fixtures/report_snapshot_v1.json` is generated from `weapons_dupes.csv`; fixture bytes, decisions, and `RULESET_VERSION` contribute to the snapshot/fingerprint. Regenerate it with the repository script after the intentional changes.
- `tests/test_report_run.py` currently asserts ruleset version 1 and byte-for-byte golden reproduction.

## Documentation state

- `PLAN.md` already states the correct product rule and does not need a semantic rewrite.
- `AGENTS.md` does not yet record that `Crafted` is a DIM enum-like token rather than a boolean.
- `WORKLOG.md` records the original crafted threshold rule but not the real-export token gotcha.
- `README.md` does not need a user-facing change for this internal field correction.

---

# Dependencies and assumptions

- Issue #1 / PR #11 is complete and supplies the established rail architecture.
- Issue #31 remains separate open work. #32 neither waits for it nor resolves its warning about same-Hash/different-roll cleanup.
- The measured real-export contract stated by issue #32 is authoritative: ordinary weapons use `false`; crafted weapons use `crafted`.
- Empty is retained as an explicit not-crafted value because current fake/base weapon data contains it and the shared rail can be called for rows without a `Crafted` field.
- There is no evidence that `true` is a real DIM export token. Existing support comes only from incorrectly modelled tests, so compatibility with it is not preserved by default.
- The threshold remains an integer supplied by the existing config. Validation of malformed `Crafted Level` text is a separate concern unless Sol explicitly expands this ticket.
- No new dependency is needed.

---

# Scope

## In scope

- Add one focused crafted-state parser/helper with the explicit token policy above.
- Make weapon ingestion require the `Crafted` and `Crafted Level` headers.
- Validate every weapon row's crafted-state token through the shared helper so unknown non-empty values fail before rule output.
- Route `rails.protection` through the helper instead of generic `is_true()`.
- Preserve generic boolean parsing for `Locked` and `Equipped`.
- Update fake weapon fixture rows from `true` to DIM's real `crafted` token.
- Add the missing exact-threshold, above-threshold, below-threshold, ordinary-false, empty, and malformed-state coverage.
- Prove both wishlist-trash and duplicate decision paths emit no row for unlocked crafted weapons at/above the threshold.
- Bump `report_run.RULESET_VERSION` from 1 to 2.
- Update the ruleset-version assertion and regenerate the fake report snapshot.
- Add the DIM token gotcha to `AGENTS.md`.
- Add a dated implementation/validation entry to `WORKLOG.md`.

## Out of scope

- Accepting speculative crafted-state aliases or preserving `true` solely for old fixtures.
- Changing `is_true()` behaviour for actual boolean columns.
- Changing malformed `Crafted Level` handling or numeric ranking coercion.
- Changing the configured threshold or adding config keys.
- Changing hard/soft rail categories, precedence, or reason strings.
- Changing wishlist semantics, duplicate grouping, exact-roll identity, ranking, or deterministic survivor behaviour.
- Implementing any part of #31, #34, or #29.
- Changing report/snapshot schema versions; only the ruleset version changes.
- Changing DIM import columns, notes, tags, dry-run/write behaviour, CLI shape, or paths.
- Changing runtime/dev dependencies, CI, packaging, server, UI, browser tests, review manifests, or persistence.
- Adding real-vault examples, rows, IDs, counts, or exports to the repository.
- Rewriting historical `WORKLOG.md` entries.

If implementation appears to require an out-of-scope change, apply the stop rule and return it to Sol.

---

# Expected change footprint

## Expected production/documentation modifications

```text
src/vault_cleaner/parse.py
src/vault_cleaner/rules/rails.py
src/vault_cleaner/report_run.py
AGENTS.md
WORKLOG.md
```

## Expected test/fixture modifications

```text
tests/test_parse.py
tests/test_rails.py
tests/test_dupes.py
tests/test_weapons_rules.py
tests/test_report_run.py
tests/fixtures/weapons_dupes.csv
tests/fixtures/report_snapshot_v1.json
```

`tests/test_dupes.py` may need only a fixture expectation/comment adjustment plus a boundary assertion. Keep the test changes behaviour-focused.

## Files/components that should normally remain substantively unchanged

```text
src/vault_cleaner/rules/dupes.py
src/vault_cleaner/rules/weapons.py
src/vault_cleaner/pipeline.py
src/vault_cleaner/config.py
src/vault_cleaner/report.py
src/vault_cleaner/cli.py
config.toml
PLAN.md
README.md
pyproject.toml
.github/workflows/ci.yml
src/vault_cleaner/server/
src/vault_cleaner/ui/
tests/test_server_*.py
tests/test_server_browser.py
```

If a substantive edit to one of these files seems necessary, stop and explain the concrete reason to Sol. A tiny test import adjustment outside the expected list is acceptable only when mechanically required by the selected helper location and should be called out in the handoff.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline

Start from the latest remote `main`, not from the handoff branch.

Suggested implementation branch:

```text
fix/issue-32-crafted-token
```

Run:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c fix/issue-32-crafted-token
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git status --short
git ls-files data/
```

If `.venv` already exists and uses a compatible interpreter, reuse it instead of recreating it.

Expected planning baseline was Ruff clean, `676 passed, 2 skipped`, a clean worktree, and no tracked path under `data/`. Record the actual base SHA and actual current test totals because `main` may advance before Luna starts.

Do not continue on top of unrelated local modifications. Preserve user work and return any overlap to Sol.

## 2. Lock the crafted-state contract in focused tests first

Add direct table-driven coverage for the one authoritative helper before changing the rail:

- `crafted` → true;
- `false` → false;
- empty → false;
- surrounding whitespace/case variants follow the chosen normalisation policy;
- `true` is rejected;
- another arbitrary non-empty value is rejected.

Use one shared implementation/token table. Do not duplicate accepted-token sets between parser and rail modules.

The helper should return a boolean for accepted values and raise a clear domain-appropriate error for unknown non-empty values. Loader entry points must surface malformed exports as `SchemaError`, with path and byte loaders producing equivalent messages under the existing test pattern.

## 3. Validate the safety-critical fields during weapon ingestion

In `src/vault_cleaner/parse.py`:

1. Add `Crafted` and `Crafted Level` to `REQUIRED_WEAPON_COLUMNS` because the weapon rules consume both to decide hard protection.
2. Introduce the single focused crafted-state parser/helper at the parsing boundary.
3. Add a weapon-specific validation step, analogous in purpose to `_validate_armor`, that validates every `Crafted` value before returning the DataFrame.
4. Apply that validation identically to `load_weapons()` and `load_weapons_bytes()` through their shared path.
5. Preserve all existing string/empty-cell/opaque-ID behaviour.

The loader must reject a missing `Crafted` or `Crafted Level` header as schema drift. It must reject an unknown non-empty token even when the affected row would otherwise be unique, tagged, equipped, or absent from a wishlist. This prevents rule-path coverage from deciding whether malformed safety data is noticed.

Do not add crafted fields to armour or ghost schemas.

Do not add numeric validation for `Crafted Level` in this ticket; if that becomes necessary to complete the token fix, stop and ask Sol to reassess scope.

## 4. Route the existing hard rail through the focused helper

In `src/vault_cleaner/rules/rails.py`:

- keep `is_true()` unchanged for `Equipped` and `Locked`;
- replace only the `Crafted` use of `is_true()` with the focused crafted-state helper;
- preserve the existing threshold comparison, `HARD` result, reason format, and precedence for valid data;
- do not create a second crafted check in `weapons.py`, `dupes.py`, or `pipeline.py`.

The classifier should also fail explicitly if called directly with an unknown crafted token, rather than silently treating it as ordinary. For accepted inputs, all non-crafted rail outcomes must remain byte-for-byte/tuple-for-tuple compatible with existing tests.

## 5. Correct and extend the fake fixture

In `tests/fixtures/weapons_dupes.csv`:

- replace the two fake crafted rows' `true` values with `crafted`;
- retain an ordinary `false` row;
- retain a below-threshold crafted row;
- retain an above-threshold crafted row;
- add the smallest fake unlocked row necessary to cover the exact threshold boundary if that boundary is not already represented after editing;
- use fake IDs only and keep LF line endings.

Shape the duplicate group so the at-threshold and above-threshold crafted rows would be output as losers if the rail failed. An at/above row that happens to win ranking is not adequate regression proof because winners emit no row even without protection.

Do not copy a real vault row or instance ID. Do not alter unrelated fixture groups.

## 6. Prove rail, duplicate, and wishlist behaviour

### `tests/test_rails.py`

Cover:

1. `Crafted=crafted` at exactly threshold 10 returns `HARD`.
2. `Crafted=crafted` above threshold returns `HARD`.
3. `Crafted=crafted` below threshold returns no crafted protection.
4. `Crafted=false` does not hard-protect even with a high level value.
5. empty uses the explicit not-crafted policy.
6. unknown non-empty values fail explicitly.
7. tag/equipped/exotic/locked/plain behaviour remains unchanged.

### `tests/test_dupes.py`

Using the corrected real-token fixture, prove:

1. unlocked crafted losers at threshold and above do not appear in decisions;
2. the below-threshold crafted loser continues through normal duplicate logic and is junked;
3. the ordinary `false` copy follows existing ranking/decision rules;
4. unrelated dupe cases remain unchanged.

### `tests/test_weapons_rules.py`

Add a compact wishlist regression using constructed fake rows:

1. unlocked `crafted` rows at threshold and above that match wishlist-trash emit no wishlist-trash decision and no later dupe decision;
2. a below-threshold `crafted` row with the same trash condition retains normal junk behaviour;
3. test data forces the hard-protected row to be a potential loser where duplicate resolution also runs.

Avoid source-string assertions. Assert decision IDs/actions/notes or complete absence from the decision list.

## 7. Prove loader failure policy

Extend `tests/test_parse.py` using its existing CSV rewrite helpers and path/byte parity structure:

- missing `Crafted` header fails as a weapons schema error;
- missing `Crafted Level` header fails as a weapons schema error;
- an unknown non-empty `Crafted` value fails for both path and byte loaders;
- error type and normalised message remain equivalent between path and byte entry points;
- empty and valid real tokens still load;
- armour and ghost loaders remain unaffected.

Do not merely test that `rails.protection()` raises. The ingestion regression is what guarantees malformed unique/non-decided rows cannot pass unnoticed.

## 8. Version the decision-semantic change and regenerate the golden

In `src/vault_cleaner/report_run.py`:

- bump `RULESET_VERSION` from `1` to `2`;
- do not change `SNAPSHOT_SCHEMA_VERSION` because the snapshot shape is unchanged.

In `tests/test_report_run.py`:

- update the explicit ruleset-version assertion to `2`;
- retain the fingerprint, deterministic serialisation, exact-ID, and byte-reproduction tests.

After production, fixture, and version changes are complete, regenerate the committed fake golden with the repository-owned command:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
```

Inspect the golden diff. Expected causes are limited to:

- ruleset version 1 → 2;
- the fake weapons source digest/fingerprint change;
- any fixture decision/source-count change caused deliberately by the new exact-boundary row.

Unexpected schema, armour, ghost, UI, or unrelated decision changes are a stop condition until explained.

## 9. Documentation and worklog

### `AGENTS.md`

Add a concise gotcha stating:

- DIM exports crafted weapons as `Crafted=crafted`, not boolean `true`;
- ordinary weapons use `false` and empty is explicitly treated as not crafted;
- the field must use the focused crafted-state helper, never generic `is_true()`;
- unknown non-empty tokens must fail schema validation rather than disable the hard rail.

Do not rewrite unrelated guidance.

### `WORKLOG.md`

Add a newest-first dated entry for issue #32 containing:

- the real DIM token and the former `is_true()` mismatch;
- the accepted/rejected token policy, including the deliberate rejection of fixture-only `true`;
- the loader/schema hardening for `Crafted` and `Crafted Level`;
- confirmation that threshold/above rows are absent from wishlist and dupe output while below-threshold behaviour remains normal;
- the `RULESET_VERSION` bump and golden regeneration;
- exact focused/full validation results;
- confirmation that no real vault rows or IDs were committed;
- confirmation that #31 remains separate and unresolved.

Do not edit the historical 2026-07-18 entry.

`PLAN.md` and `README.md` should remain unchanged unless Sol separately approves a concrete stale statement discovered during implementation.

## 10. Review the diff for scope and privacy

Before final validation, inspect:

```bash
git diff --stat origin/main...HEAD
git diff -- src/vault_cleaner/parse.py src/vault_cleaner/rules/rails.py
git diff -- tests/test_parse.py tests/test_rails.py tests/test_dupes.py tests/test_weapons_rules.py
git diff -- src/vault_cleaner/report_run.py tests/test_report_run.py tests/fixtures/report_snapshot_v1.json
git diff -- AGENTS.md WORKLOG.md
git grep -n 'Crafted="true"' -- src tests || true
git grep -n ',true,[0-9][0-9]*,' -- tests/fixtures/weapons_dupes.csv || true
```

The searches are guards, not proof by themselves. Generic `true` values for boolean columns will legitimately remain elsewhere.

Check that the diff contains no `data/` path, real item, real account detail, or unexplained large fixture change.

---

# Required automated tests

The completed branch must prove all of the following.

## Crafted-state contract

1. `crafted` parses as crafted.
2. `false` parses as not crafted.
3. empty parses as not crafted by explicit policy.
4. supported case/whitespace normalisation is deterministic.
5. `true` and arbitrary unknown non-empty values are rejected.
6. missing `Crafted` or `Crafted Level` headers fail loudly for weapon exports.
7. path and byte weapon loaders enforce the same contract and expose equivalent schema errors.

## Hard-rail regression

1. Unlocked crafted weapon at threshold is hard-protected.
2. Unlocked crafted weapon above threshold is hard-protected.
3. Such rows produce no wishlist-trash output.
4. Such rows produce no duplicate output even when deliberately ranked as losers.
5. Below-threshold crafted weapons continue through normal wishlist/dupe behaviour.
6. `false` ordinary weapons remain eligible for normal rules.
7. Tag, equipped, exotic, locked, and plain-item outcomes remain unchanged.

## Snapshot/fingerprint regression

1. `RULESET_VERSION == 2`.
2. Snapshot schema remains version 1.
3. Snapshot serialisation remains deterministic.
4. The repository regeneration script reproduces the committed golden byte-for-byte.
5. Existing opaque-ID and fingerprint tests remain green.

## Privacy and hygiene

1. All fixtures use fake rows and IDs.
2. No file under `data/` is tracked.
3. Fixture and golden files remain LF-only.

---

# Manual verification

After automated tests pass, run the fake fixture through the dry-run duplicate command:

```bash
.venv/bin/vault-cleaner dupes \
  --input tests/fixtures/weapons_dupes.csv \
  --config config.toml \
  --no-wishlists
```

Record in the Luna → Sol handoff that:

- the fake at-threshold and above-threshold crafted IDs are absent from printed decisions;
- the fake below-threshold crafted ID retains its expected normal decision;
- the command remains a dry run and writes no output file.

No real vault export is needed or permitted for this verification. Browser, server, and wheel verification add no value for this local rules/parser ticket and are deliberately not required.

---

# Exact validation commands

Run focused validation first:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_parse.py \
  tests/test_rails.py \
  tests/test_dupes.py \
  tests/test_weapons_rules.py \
  tests/test_report_run.py
```

Then run the complete gate:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git status --short
git ls-files data/
git diff --stat origin/main...HEAD
```

The two browser tests may skip in an environment without managed Chromium, as they did on the planning baseline. Do not install a browser or change browser tests for #32. The normal full suite must otherwise pass.

---

# Luna completion gate

Do not hand the branch to Sol high until all of the following are true:

- `Crafted=crafted` is recognised by the shared hard rail.
- The generic boolean helper is unchanged and no longer used for `Crafted`.
- `Crafted` and `Crafted Level` are required weapon headers.
- Unknown non-empty crafted-state values fail during weapon ingestion and on direct helper/classifier use.
- Fixture-only `true` is rejected rather than preserved without evidence.
- At-threshold and above-threshold unlocked crafted losers emit no duplicate decision.
- At-threshold and above-threshold crafted trash matches emit no wishlist decision.
- Below-threshold crafted rows retain normal behaviour.
- No duplicate crafted interpretation was added to downstream passes.
- `RULESET_VERSION` is 2 and snapshot schema remains 1.
- The fake golden was regenerated with the repository script and its diff is fully explained.
- `AGENTS.md` contains the real-token gotcha.
- `WORKLOG.md` contains a dated #32 entry and exact validation totals.
- Ruff and focused/full pytest pass.
- `git diff --check` is clean.
- `git ls-files data/` prints nothing.
- the branch contains no real vault row or ID.
- the implementation is committed and pushed.
- **no pull request has been raised**.

Provide Sol high with:

- implementation branch name;
- base `main` SHA and implementation commit SHA(s);
- concise implementation summary;
- files changed;
- exact accepted/rejected crafted-state policy;
- tests added/changed;
- focused and full validation output;
- manual fake-fixture result;
- snapshot/golden diff explanation;
- privacy/hygiene confirmation;
- known risks or uncertainties;
- any intentional deviation from this plan;
- explicit confirmation that no PR was opened.

---

# Sol high review prompt

Review the completed Luna xhigh implementation for issue #32 in `tonym999/vault-cleaner`.

**Do not raise a PR yet.**

This ticket repairs a safety-critical DIM field contract, but it is intentionally a small parser/rail/test/documentation change. Perform both plan-conformance and engineering review.

## 1. Plan-conformance review

Confirm:

1. one focused helper owns crafted-state parsing;
2. the accepted policy is `crafted` → true, `false`/empty → false;
3. `true` and other unknown non-empty values reject unless the branch contains concrete external compatibility evidence approved by Sol;
4. weapon path and byte loaders require/validate `Crafted` and `Crafted Level` before decisions;
5. `rails.protection` uses the focused helper and keeps `is_true()` unchanged for `Locked`/`Equipped`;
6. rail precedence, hard/soft classifications, reason strings, threshold config, and below-threshold behaviour are unchanged;
7. at-threshold and above-threshold unlocked crafted losers emit no duplicate row;
8. at-threshold and above-threshold crafted trash matches emit no wishlist row;
9. malformed-state coverage cannot be bypassed merely because a row is unique or already protected;
10. fixture rows use real DIM tokens and fake IDs only;
11. `RULESET_VERSION` is bumped to 2, snapshot schema remains 1, and the regenerated golden changes only for explained reasons;
12. `AGENTS.md` and `WORKLOG.md` meet the ticket requirements;
13. #31/#34 work has not leaked into this diff;
14. Luna did not open a PR.

## 2. Engineering review

Review specifically for:

- duplicated accepted-token sets or multiple crafted parsers;
- permissive fallback that silently converts an unknown value to false;
- validation that only happens on duplicate/wishlist candidates instead of every loaded weapon row;
- accidental use of generic boolean parsing for `Crafted`;
- hard-protected rows that appear safe only because they win duplicate ranking;
- tests that cover the direct classifier but not wishlist and duplicate integration paths;
- boundary mistakes (`>` instead of `>=`);
- accidental changes to `Crafted Level` coercion, ranking, wishlist semantics, or rail ordering;
- missing ruleset-version/fingerprint invalidation;
- unexplained golden churn;
- real vault content or IDs;
- unnecessary changes outside the expected footprint.

Challenge the plan if implementation reveals its token or empty-value assumptions are unsupported, but do not silently approve speculative aliases.

## 3. Reviewer validation

Run:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_parse.py \
  tests/test_rails.py \
  tests/test_dupes.py \
  tests/test_weapons_rules.py \
  tests/test_report_run.py
.venv/bin/pytest -q
.venv/bin/vault-cleaner dupes \
  --input tests/fixtures/weapons_dupes.csv \
  --config config.toml \
  --no-wishlists
git diff --check
git status --short
git ls-files data/
git diff --stat origin/main...HEAD
```

Also inspect the golden and semantic-version changes directly:

```bash
git diff origin/main...HEAD -- \
  src/vault_cleaner/report_run.py \
  tests/test_report_run.py \
  tests/fixtures/report_snapshot_v1.json
```

## Review outcome

If you find issues:

- identify each finding precisely;
- explain the safety or correctness consequence;
- specify the smallest expected fix;
- require regression coverage where appropriate;
- keep fixes on the same implementation branch;
- rerun focused and full validation;
- review again after fixes.

Mark the implementation **ready for PR** only after the branch is review-clean. Do not create the PR unless Tony separately asks for it.

Because this ticket uses the standard path, no additional independent reviewer is required unless the implementation has crossed one of the stop conditions and Sol explicitly reclassifies it.

---

# Reusable Luna xhigh execution prompt

Implement issue #32 in `tonym999/vault-cleaner` using the attached Sol implementation plan.

The goal is to recognise DIM's real `Crafted=crafted` token in the existing crafted-level hard rail, reject unknown non-empty crafted-state values before decisions, and prove that unlocked crafted weapons at/above the configured threshold produce neither wishlist-trash nor duplicate output.

Follow the plan as the primary guide, but inspect the latest `main` before editing because the repository may have advanced since planning baseline `88253914724291732536ec5e27c8476a7ea6b983`.

Apply the ticket's **algorithmic scope rule to every edit**. The default token policy is:

- `crafted` → crafted;
- `false` or empty → not crafted;
- `true` or any other non-empty token → reject.

Do not preserve `true` merely because old fake fixtures used it. If real compatibility evidence requires another token, or if the change needs broader rule/architecture work, stop and return the finding to Sol.

Rules:

- branch from the latest `main`;
- read `AGENTS.md`, `PLAN.md`, issue #32, issue #1/PR #11, issue #31, current relevant code/tests, and relevant `WORKLOG.md` entries;
- create one focused crafted-state helper and use it at weapon ingestion and in `rails.protection`;
- require `Crafted` and `Crafted Level` weapon headers;
- leave generic `is_true()`, rail ordering, threshold config, hard/soft semantics, ranking, wishlist logic, and output format unchanged;
- correct fake crafted fixture tokens and add exact boundary/above/below/malformed coverage;
- prove both wishlist and duplicate paths;
- bump `RULESET_VERSION` to 2, keep snapshot schema at 1, and regenerate the golden with the repository script;
- update `AGENTS.md` and add a dated `WORKLOG.md` entry;
- use fake data only and commit nothing under `data/`;
- run the exact focused/full validation and dry-run fixture command from the plan;
- commit and push the implementation branch;
- **do not raise a pull request**.

When complete, provide Sol high with the branch/base/commit SHAs, changed files, token policy, implementation summary, test changes and exact results, manual fake-fixture result, golden-diff explanation, privacy checks, risks/deviations, and confirmation that no PR was opened.

The branch will receive a standard Sol high review before any PR is created.

---

# Ticket-specific review decision

**Review path:** `standard — Sol high pre-PR review`

**Reason:** issue #32 changes a safety decision, but the implementation is a complete, deterministic, local token matrix at an existing parser/rail seam. It does not materially change architecture, protocol, persistence, concurrency, stale-state handling, lifecycle, security boundaries, transactional behaviour, or an externally consumed API. Focused loader/rail/wishlist/dupe tests plus ruleset-fingerprint invalidation make the risk reviewable within the normal Sol high gate.

If Luna crosses any stop condition—especially adding undocumented token compatibility or altering broader rule semantics—the work must return to Sol for replanning and possible independent-review reclassification.
