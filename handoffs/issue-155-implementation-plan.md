# Issue #155 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#155 — Child 2b: include only explicitly approved proposals in finalized CSVs`

**Milestone:** `None — deliberately unassigned; this is a cross-cutting child of #140 rather than M8 or M9 work`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** Google `gemini-3.8-flash`, native `thinking_level = high` (justified below)

**Plan baseline:** `main` at `f75175dac66072a662d7129b49921a757af6aafd` (2026-09-13)

**Allocated implementation branch:** `feat/issue-155-approval-only-finalization`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Make the two reviewed/finalized DIM import paths emit only proposals carrying a
fresh explicit `approved` verdict. A current `vetoed` verdict or no verdict means
the proposal is absent. An active durable veto remains an independent exclusion,
so approving an already-vetoed proposal does not resurrect it.

The exact inclusion predicate is:

```text
current proposal AND explicit fresh approval AND NOT active persisted veto
```

Preserve report order among included rows. If nothing qualifies, finalization is
still successful and produces the valid header-only bytes
`Id,Hash,Tag,Notes\r\n`. “Removed” means omitted from this CSV; the program never
deletes or dismantles an item.

This ticket changes reviewed output selection only. It does not change the raw
proposal exports, proposal identity, rule results, ranking, rails, tags, Notes,
fingerprints, or review/session schemas.

## Context & Measurement

### Settled contract and present defect

- The owner-approved #140 tracking comment settles Child 2b as: only explicitly
  approved proposals appear in the generated reviewed import; vetoed and
  unreviewed proposals do not. The measured source of truth is
  [section 9 of the #142 report](../docs/aggressive-clearout-measurement.md#9-approval-only-finalization-contract).
- The current shared selector
  [`apply_vetoes`](../src/vault_cleaner/review.py#L546) accepts only vetoed ids
  and returns every other proposal. Its list comprehension at lines 553–559 is
  therefore subtractive and cannot distinguish approval from missing review.
- The server uses that selector at
  [`server/app.py:783`](../src/vault_cleaner/server/app.py#L783) after merging
  session verdicts into the durable veto store, classifying active vetoes, and
  before rendering/caching the finalized bytes at lines 790–821.
- The CLI reviewed-export path uses the same selector at
  [`cli.py:481`](../src/vault_cleaner/cli.py#L481), then writes its result at
  lines 519–527. Its current **`after vetoes`** output at line 485 describes the
  subtractive model rather than explicit approval.
- [`report.render_import_csv`](../src/vault_cleaner/report.py#L83) always writes
  the four-column header before iterating rows. Empty input already renders the
  required header-only CSV, so no writer change or special empty-file format is
  needed.

### Fresh verdict and durable-veto state are separate

- The canonical non-null verdict tokens are
  [`VERDICTS = {"approved", "vetoed"}`](../src/vault_cleaner/review_session.py#L41).
  `ReviewManifest.approved` and `.vetoed` expose the validated CLI manifest
  partitions at [review.py:83](../src/vault_cleaner/review.py#L83).
- The server validator accepts those same two non-null tokens and additionally
  accepts `null` as the explicit clear-to-unreviewed mutation at
  [server/app.py:193](../src/vault_cleaner/server/app.py#L193). The verdict
  endpoint deletes cleared entries rather than storing null at
  [server/app.py:671](../src/vault_cleaner/server/app.py#L671); therefore
  `session.verdicts` at finalization contains only acknowledged `approved` or
  `vetoed` entries.
- [`merge_verdicts`](../src/vault_cleaner/review_session.py#L243) persists only
  fresh vetoes. An approval does not remove a pre-existing veto, and
  `already_vetoed_but_approved` records that conflict at lines 298–315.
  [`classify`](../src/vault_cleaner/review.py#L496) is still the authority for
  whether a durable veto is active against this exact current proposal.
- Consequently the selector must receive both fresh approvals and the
  post-merge `status.active_ids`. Absence from the active-veto set is never an
  approval, and durable vetoes must not be inferred from fresh verdicts.

### Browser-derived output count and finalization copy

- [`review_ui.verdictOf`](../src/vault_cleaner/ui/review_ui.js#L129) already
  normalizes only `approved` and `vetoed`; missing or unknown values become the
  unreviewed empty string.
- [`keptItems`](../src/vault_cleaner/ui/review_ui.js#L147) currently mirrors the
  Python subtractive selector: it removes active persisted vetoes and fresh
  vetoes but retains unreviewed proposals. The name and behavior become false
  under approval-only output and must be replaced with approval-oriented naming
  and semantics.
- [`renderSummary`](../src/vault_cleaner/ui/review_server.js#L977) labels that
  derived set **`after vetoes`**. It must instead expose the count and
  junk/review split of the actual approval-only output set.
- [`finalizeSession`](../src/vault_cleaner/ui/review_server.js#L1442) currently
  warns, verbatim, **`Unreviewed proposals will remain in the generated import
  CSV unless an existing active persisted veto suppresses them. Continue?`**
  That becomes dangerously false and must be removed.

### Existing regression seams that must be inverted, not discarded

- Pure Python selection tests live at
  [`tests/test_review.py:516`](../tests/test_review.py#L516). They currently prove
  veto subtraction, unknown-id tolerance, order, and no reranking.
- CLI tests at
  [`tests/test_cli_review.py:43`](../tests/test_cli_review.py#L43) assume every
  manifest decision not vetoed is written, and the no-manifest path at line 95
  assumes persisted vetoes alone define reviewed output.
- Server finalization coverage in
  [`tests/test_server_finalize.py`](../tests/test_server_finalize.py) exercises
  cached bytes, idempotent retries, stale revisions, override drift, durable-veto
  conflicts, reset, shutdown, failure privacy, and server/CLI parity. The test at
  line 321 equating server finalization with raw `report --write` encodes the old
  model and must be replaced with approval-only server/CLI-review parity.
- The browser smoke test at
  [`tests/test_server_browser.py:264`](../tests/test_server_browser.py#L264)
  approves, clears, then vetoes a row before finalizing. It currently proves a
  non-empty download only because unrelated unreviewed rows leak through; the
  test must explicitly approve the intended emitted row and prove the other
  visible rows are absent.
- JavaScript unit and adapter tests at
  [`tests/test_review_ui_js.py:1278`](../tests/test_review_ui_js.py#L1278) and
  [`tests/test_server_ui_js.py:1925`](../tests/test_server_ui_js.py#L1925)
  encode `keptItems`, the **after vetoes** summary, and the old conditional
  confirmation. They must prove approval-only counts and the new copy without
  weakening mutation/finalized-state assertions.

### Model verification and selection

Google's official documentation was rechecked on 2026-09-13:

- [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
  identifies stable model code `gemini-3.8-flash`, describes it as designed for
  long-horizon software engineering and autonomous agents, and lists native
  thinking levels `low`, `medium`, and `high`; `minimal` is unsupported.
- [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking)
  confirms `medium` as the default and `high` as supported for this exact model.

`gemini-3.8-flash` with `thinking_level = high` is suitable. The code change is
cross-cutting and safety-sensitive, but the policy is fully settled, the two
backend call sites and one browser mirror are measured, the input tokens already
exist, and the required truth table is mechanical. High thinking is warranted
for durable-veto conflicts, partial manifests, empty output, transactional
server retries, and test-parity changes; Pro-tier open-ended design is not
required.

The orchestrator must still verify that its runtime can instantiate this Google
model and effort. If not, it prepares the reusable prompt below for manual
cross-provider execution and records the actual provider/model/effort. Official
availability does not prove availability in the orchestration runtime.

## Dependencies and assumptions

- #142 is closed and its measurement/report is merged. Its section 9 is the
  authoritative design source and is not stale on this baseline.
- Child 2a #148 is closed and merged through PR #153. It now exposes loadout
  membership and requires the weapon `Loadouts` header. Approval-only selection
  is behaviorally independent and must not alter that work.
- #150 has a merged planning handoff on this baseline but no open implementation
  PR at planning time. Its future implementation is expected to touch
  `review_server.js`, `review_ui.js`, the same JavaScript/browser tests, README,
  and WORKLOG. It does not block #155 semantically, but the implementer must
  branch from latest `main` and re-measure line positions/behavior if #150 lands
  first. Merge conflicts are not permission to drop either ticket's assertions.
- Fresh approvals are session/manifest state, not durable overrides. Running
  `vault-cleaner review --write` without `--manifest` therefore has zero explicit
  approvals and writes a header-only reviewed CSV after the user's existing
  explicit `--write` action. It still reports durable override status. It must
  not treat “not actively vetoed” as approved or silently reuse approvals from a
  prior run.
- A fresh approval conflicting with an active durable veto remains excluded and
  retains the current diagnostic/header. Only #114 may introduce reset behavior.
- The raw proposal commands (`report --write`, `dupes --write`, `armor --write`,
  and `ghosts --write`) remain deliberately separate from reviewed finalization.
  This plan does not convert, remove, or relabel them.
- The change occurs after rule execution and does not alter proposal identity,
  so `RULESET_VERSION = 4`, `SNAPSHOT_SCHEMA_VERSION = 2`, the report fingerprint,
  and `report_snapshot_v2.json` remain unchanged.

## Proposed Plan & Scope

### Shared approval-only output selector

#### [MODIFY] [review.py](../src/vault_cleaner/review.py#L546)

- Replace the subtractively named/behaving `apply_vetoes` seam with one pure,
  approval-oriented selector over a `ReportRun`, explicit approved ids, and
  active persisted-veto ids. A narrow compatibility alias is unnecessary unless
  the implementer finds an actual supported public consumer.
- Materialize ids as opaque strings without numeric coercion. Return decisions
  in section/report order only when their id is explicitly approved and not in
  the active-veto set.
- Do not rerun rules, mutate a `ReportDecision`, choose a new duplicate survivor,
  validate untrusted manifests, or persist state in this helper.

#### [MODIFY] [test_review.py](../tests/test_review.py#L516)

- Replace subtractive tests with the full four-row truth table: approved/no
  active veto is included; approved/active veto, vetoed, and unreviewed are not.
- Prove partial approval sets, unknown approved ids, duplicate ids as harmless
  set membership, stable report order independent of approval input order, and
  no reranking/mutation of the returned `ReportDecision` objects.

### CLI reviewed export

#### [MODIFY] [cli.py](../src/vault_cleaner/cli.py#L422)

- Derive explicit approved ids only from `manifest.approved`; when no manifest
  is supplied, the set is empty.
- After the existing merge/classification flow, pass approvals and
  `status.active_ids` to the shared selector. Preserve the current ordering in
  which an authorized `--write` persists merged vetoes before writing the CSV,
  plus existing failure reporting.
- Replace the CLI's **`after vetoes:`** line with the exact label
  **`approved output:`**, followed by the existing `_action_counts` format.
- Update the command docstring and parser copy to say that `review` applies
  explicit manifest verdicts and writes an approval-only reviewed CSV. Make it
  clear that no manifest means no approval rows; do not make durable-veto absence
  sound like approval.

#### [MODIFY] [test_cli_review.py](../tests/test_cli_review.py#L43)

- Use partial manifests with intentional approved, vetoed, and omitted ids.
  Assert exact emitted ids/row counts, exact **`approved output:`** copy, durable
  veto persistence, active-veto conflict suppression, dry-run non-mutation, and
  a header-only `--write` result without a manifest.
- Retain malformed/stale manifest, invalid overrides, already-imported junk tag,
  opaque 64-bit id, and raw-report-separation coverage.

### Server finalization and transactional parity

#### [MODIFY] [server/app.py](../src/vault_cleaner/server/app.py#L744)

- Derive approved ids from the already validated and acknowledged
  `session.verdicts` at finalization; do not infer them from merge output,
  persisted veto state, report actions, or browser filters.
- Feed those ids and post-merge `status.active_ids` through the same shared
  selector as the CLI before `render_import_csv`.
- Preserve the current transaction sequence and commit boundary: render bytes,
  verify override digest, atomically save overrides, assign the store/cache/
  conflict count, then expose `state = "finalized"`. Do not add an endpoint,
  request field, response schema, output-count header, or second writer.
- Preserve `Vault-Cleaner-Approved-Still-Vetoed`, cached byte retries,
  `/api/finalized.csv`, `--once`, reset, external-drift refusal, and sanitized
  failures exactly.

#### [MODIFY] [test_server_finalize.py](../tests/test_server_finalize.py#L149)

- Add direct response-byte tests for all truth-table states and mixed sections,
  including exact id membership/order, approval cleared back to unreviewed,
  approval plus active durable veto, and zero approvals producing exactly the
  header-only bytes.
- Replace raw `report --write` parity with equivalent server and CLI `review`
  inputs carrying the same explicit partial verdicts and overrides. A test where
  both sides happen to emit zero rows is insufficient parity evidence.
- Keep lifecycle/transaction tests focused on their established concern. They
  may finalize with zero approvals where row content is irrelevant, but at least
  one cache/retry, one `--once`, and the end-to-end parity path must use a
  non-empty approved output so a broken selector cannot hide behind valid empty
  bytes.

#### [MODIFY] [test_cli_serve.py](../tests/test_cli_serve.py#L69)

- Before the real loopback `--once` finalization, submit one explicit approval
  through `/api/verdicts`; continue proving the returned bytes are complete,
  non-empty, and the server exits only after the response closes.

### Browser mirror, count, and copy

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L147)

- Replace `keptItems` with approval-oriented naming and the exact same predicate
  as Python: `verdictOf(...) === "approved"` and no active persisted veto.
- Preserve strict Set-like validation for active veto ids and keep ids opaque.
  Export the renamed helper for the existing Node/Python adapter tests.

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L977)

- In `renderSummary`, replace the **`after vetoes`** tile with
  **`approved output`**, using the approval-only helper for its total and
  junk/review split.
- Replace the old conditional unreviewed-leak warning with an always-accurate
  confirmation based on approval-only output rows. Exact copy:
  - zero rows: **`No proposals are approved for output. Finalise a header-only CSV with no item rows?`**
  - one row: **`Finalise 1 approved proposal into the CSV? Vetoed and unreviewed proposals, plus approvals blocked by active saved vetoes, will be excluded.`**
  - plural: **`Finalise N approved proposals into the CSV? Vetoed and unreviewed proposals, plus approvals blocked by active saved vetoes, will be excluded.`**
- The `N` value is the approval-only output count after active persisted vetoes,
  not merely the raw approved-verdict count. Keep **`Finalise review`** as the
  button label and preserve its mutation gate.
- Change finalized-state success copy to
  **`Finalised — this review is frozen. The CSV contains only explicitly approved proposals not blocked by an active saved veto.`**
  Append the existing approved-still-vetoed conflict sentence unchanged when
  its response header is a valid positive count.

#### [MODIFY] [test_review_ui_js.py](../tests/test_review_ui_js.py#L1271)

- Invert the helper tests to prove only eligible approvals are returned, active
  persisted vetoes override approval, unreviewed/garbage tokens are excluded,
  action splits mirror the Python selector, and report order is preserved.

#### [MODIFY] [test_server_ui_js.py](../tests/test_server_ui_js.py#L1925)

- Assert the exact `approved output` tile and each singular/plural/zero
  confirmation string, including the post-veto output count rather than raw
  approval count.
- Preserve acknowledged-state, refetch failure, committed-finalize recovery,
  `--once`, final freeze, and approved-still-vetoed header coverage.

#### [MODIFY] [test_server_browser.py](../tests/test_server_browser.py#L264)

- Adjust the full browser flow so one selected row is left explicitly approved
  before finalization, at least one visible proposal remains unreviewed, and one
  is vetoed or cleared. Accept the exact approval-only confirmation, inspect the
  downloaded CSV, and prove only the approved eligible id appears.
- Preserve download-again, frozen controls, keyboard/accessibility, 390px, and
  other existing browser responsibilities. No screenshot golden is required.

### User documentation and worklog

#### [MODIFY] [README.md](../README.md#L108)

- Explain that `review --write` and server finalization emit only current
  explicit approvals not blocked by active durable vetoes; partial or omitted
  manifest decisions are unreviewed and excluded.
- State that `review --write` without `--manifest` has no fresh approvals and
  therefore writes a header-only reviewed CSV, while still reporting durable
  override status. Preserve the separate raw `report --write` proposal-export
  explanation.
- Update the server finalization paragraph at lines 220–223 with the same rule.

#### [MODIFY] [aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md#9-approval-only-finalization-contract)

- Preserve the historical measurement. Add a concise Child 2b landed-status
  note when implemented so “Today” and “current” are not mistaken for the new
  behavior; do not rewrite evidence or reproduce private-export findings.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

- Add the required dated implementation entry: base/head and branch, selector
  contract, CLI/server/browser behavior, durable-veto conflict handling,
  zero-row behavior, version invariants, actual model/provider/effort, review
  findings/dispositions, and exact verification results.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- it changes reviewed/finalized row selection, directly mirrors that selection
  in browser counts/copy, tests the changed contract, or documents it;
- every emitted row satisfies explicit fresh approval **and** absence of an
  active durable veto, with no other source of implicit approval;
- raw proposal generation and every `ReportDecision` remain unchanged; and
- it preserves the existing server transaction/lifecycle/API boundary and uses
  the one existing DIM CSV writer.

Worked examples:

- **IN SCOPE:** a pure selector returns proposal ids `A, C` in report order when
  approvals arrive as `C, A`, neither has an active veto, and other proposals are
  unreviewed or vetoed.
- **IN SCOPE:** a server session with one approved proposal and two unreviewed
  proposals downloads a one-row CSV; retry returns identical cached bytes.
- **IN SCOPE:** `review --write` with a partial manifest emits only its approved
  entries; without a manifest it explicitly reports zero approved output rows
  and writes the normal header only.
- **IN SCOPE:** an approved id with an active persisted veto is absent while the
  existing conflict diagnostic remains visible.
- **OUT OF SCOPE:** include every `junk` action, every non-vetoed proposal, every
  currently filtered row, or a prior-session approval.
- **OUT OF SCOPE:** clear an active durable veto when a fresh approval arrives,
  alter stale-veto classification, or implement #114 reset behavior.
- **OUT OF SCOPE:** change `report --write`, a single-pass export, rule ordering,
  ranking, rails, Notes, tags, config, fingerprints, schemas, or versions.
- **OUT OF SCOPE:** add capacity accounting, armor suppression, aggressive-mode
  policy, wishlist evidence, useful-combination logic, or #150 query behavior.

### Stop conditions

Stop implementation and return to orchestrator if:

- any proposal/rule/ranking/protection/Notes behavior must change to implement
  approval-only output;
- fresh approvals cannot be obtained from the existing server verdicts or
  validated CLI manifest without changing an untrusted-input schema;
- satisfying the ticket would require removing or implicitly clearing durable
  vetoes, changing `classify`, or absorbing #114;
- a new server endpoint, request/response field, session state, persistence
  format, output writer, transaction order, lifecycle cleanup, or auth/origin
  behavior appears necessary;
- `RULESET_VERSION`, snapshot schema, fingerprint inputs, config, a fixture
  schema, runtime dependency, or report golden appears to require change;
- #150 or another landed change invalidates the measured selector/count seams in
  a way that needs architectural re-planning rather than a mechanical rebase; or
- browser verification cannot run with a real Chromium process. A skipped
  required-browser suite is not a pass.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **One sibling path remains subtractive:** server, CLI, or the browser
   `approved output` count still treats “not vetoed” as approval, especially the
   no-manifest CLI path or an approved-but-persistently-vetoed row.
2. **Parity passes only because both outputs are empty:** old raw-report parity is
   deleted without a mixed partial-verdict CLI/server test proving the same
   non-empty ids and bytes.
3. **Lifecycle tests accidentally lose their payload proof:** tests finalize with
   zero approvals and continue passing while cache/retry/`--once` behavior never
   exercises an approved row, or transaction order changes while adding ids.
4. **Browser copy/count drift:** confirmation uses raw approved count instead of
   post-active-veto output count, old “unreviewed will remain” wording survives a
   sibling harness, or #150's shared summary refresh path is broken after rebase.

# Reusable implementer execution prompt

Implement issue #155 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-155-implementation-plan.md
```

Read the entire handoff, issue #155, #140's settled tracking comment, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-155-approval-only-finalization`; branch from latest `main` and record the base SHA;
- use Google `gemini-3.8-flash` with native `thinking_level = high`; if the orchestration runtime cannot instantiate it, stop for the documented manual cross-provider handoff rather than silently substituting a model;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run focused tests for review selection, CLI review, server finalization, UI helpers/adapter, and the real browser flow before the full gates;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, `git diff --check origin/main...HEAD`, `test -z "$(git ls-files data/)"`, and `git status --short`;
- commit with `Refs #155`, push only the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, provide the orchestrator: requested and actual provider/model/native effort; branch; base and head SHAs; changed files; exact truth-table, partial-manifest, persistent-veto conflict, header-only, server/CLI parity, cache/retry/`--once`, and browser evidence; complete command outputs including skipped/deselected counts; version/golden/data-hygiene proof; stop conditions considered; and all deviations.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**

This change inverts a final-output safety gate across a shared Python selector,
CLI, authenticated server transaction, browser-derived count, and browser copy.
A single omitted predicate can ship unreviewed proposals; a misplaced active-veto
check can resurrect an explicitly suppressed item; an apparently green parity
test can compare two empty files. The server lifecycle is not to be redesigned,
but its cache/retry/atomic-persistence guarantees must survive the changed row
selection. The orchestrator should therefore require a fresh complete-diff
review and independent rerun of all browser and backend gates.

The orchestrator confirms the path against the real diff and selects the
reviewer's exact provider, model ID, and native effort only after inspection. A
fresh non-Gemini reviewer is preferred when available, but reviewer selection
does not alter the requested Gemini implementer.

# Review checklist

- [ ] One shared pure selector implements exactly `approved AND NOT active
  persisted veto`, preserves report order and object identity, and never treats
  veto absence, `junk`, filters, current tags/Notes, or prior state as approval.
- [ ] CLI approvals come only from the validated current manifest; no manifest
  produces zero rows/header-only bytes and honest **`approved output:`** copy.
- [ ] Server approvals come only from acknowledged `session.verdicts`; cleared,
  vetoed, and unreviewed ids are absent, while approved/active-veto conflicts
  remain excluded and diagnosed.
- [ ] The server's render → digest check → atomic override save → in-memory cache
  → finalized-state order, cached retries, `/api/finalized.csv`, reset, external
  drift refusal, `--once`, response privacy, and auth/origin gates are unchanged.
- [ ] Header-only output is valid and intentional, but non-empty mixed-verdict
  tests prove exact ids/order and prevent false green empty-output parity.
- [ ] Raw `report --write` and single-pass proposal exports remain unchanged and
  clearly distinct from approval-only reviewed/finalized output.
- [ ] Browser helper/count matches Python for approved, vetoed, unreviewed,
  garbage, and active persisted veto states. The tile says **`approved output`**.
- [ ] Zero/singular/plural confirmation and finalized success strings match this
  plan exactly; `N` counts emitted rows after active-veto suppression. No old
  “unreviewed proposals will remain” text survives source, tests, or docs.
- [ ] The real browser test leaves one explicit approval, at least one
  unreviewed row, and one vetoed/cleared row, then proves downloaded membership
  and the frozen/retry lifecycle rather than only file existence.
- [ ] #148 loadout visibility and any landed #150 summary/query refresh behavior
  remain intact after rebase; no unrelated UI or DIM-query semantics move.
- [ ] `RULESET_VERSION`, snapshot schema/fingerprint inputs, report golden,
  config, fixtures, dependencies, Notes grammar, and tracked `data/` remain
  unchanged.
- [ ] README, the #142 status note, and WORKLOG accurately match the implemented
  CLI/server/browser behavior and actual provider/model/effort.
- [ ] Ruff, full pytest, required Chromium with no skips, diff check, branch-only
  push, clean worktree, and no-tracked-data checks all pass.

# Dispatch comment draft

Planned #155 in [handoffs/issue-155-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-155-implementation-plan.md) on `main`.

- **Scope decision:** reviewed/finalized rows satisfy `explicit fresh approval AND NOT active persisted veto`; vetoed and unreviewed rows are absent. Zero approvals deliberately produce a valid header-only CSV. Raw proposal exports remain unchanged.
- **Implementer tier & effort:** Google `gemini-3.8-flash`, native `thinking_level = high`
- **Implementation branch:** `feat/issue-155-approval-only-finalization`
- **Recommended review path:** independent adversarial review — this inverts a final-output decision gate across CLI, server, and browser-derived counts while preserving durable vetoes and lifecycle transactionality.
- **Likely findings:** one sibling still treats “not vetoed” as approval; parity passes on two empty files; cache/retry/`--once` tests stop exercising a real row; confirmation counts raw approvals rather than post-veto output or retains the old unreviewed-leak warning.
