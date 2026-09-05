# Issue #117 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#117 — Copy a duplicate group's instance ids as a DIM search query`

**Milestone:** `None — intentionally unassigned; the issue is an interop follow-up rather than M9 presentation work`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `gemini-3.8-flash`, native `thinking_level = high` (justified below)

**Plan baseline:** `main` at `3cc6fa32530a0b1cd6366c4ccc109af20b2cf511` (2026-09-05)

**Allocated implementation branch:** `feat/issue-117-dim-search-query`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Ship a deliberately staged, local-only aid that turns the **currently approved
junk proposals in one rendered armour duplicate group** into one or more DIM
`id:` search queries. The user first prepares and inspects the query text, then
chooses whether to copy an individual complete chunk. The preferred survivor,
retained/read-only members, unreviewed proposals, and vetoed proposals never
enter the result.

This records the issue's requested product decision as **ship, in the bounded
form above**. It rejects the prototype's whole-group action and its automatic
copy-on-first-click interaction.

## Context & Measurement

### Current vault-cleaner authority and UI seams

- The browser projection validates exact-group member identity and dispositions,
  preserves each `id` as a string, and correlates proposals against the same
  section and hash at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L330). Exact groups expose
  the authoritative `preferredSurvivorId` and projected name/type/class/archetype
  at [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L403).
- Same-stat groups deliberately have no selected survivor. Their members carry
  only separately correlated current proposal data at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L434). The shared predicate
  `armorMemberCanVerdict` is the existing seam for deciding whether a member has
  a real current proposal, including same-stat members, at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1091).
- The current verdict is read from the server-adopted `state.verdicts` by
  `verdictOf`; it recognizes only `approved` and `vetoed` at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L129). A query selection
  must combine `armorMemberCanVerdict(group, member)` with
  `verdictOf(state.verdicts, member.id) === "approved"`; DOM labels and button
  state are not authority.
- Each group is currently one `article.armor-group`, constructed from projected
  data by `armorGroup` at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1452). Both responsive
  matrix orientations call the same `armorMemberCell` factory and register two
  DOM occurrences per member at current desktop widths; the group-level search
  control must therefore be rendered **once outside both matrices**, never once
  per orientation.
- Server acknowledgements call `adopt`, then repaint existing registered member
  cells when the report identity is unchanged at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L797). A prepared
  query is derived presentation state: it must be cleared or regenerated after
  an acknowledged verdict/report adoption so stale approved ids cannot remain
  copyable.
- The permanent shell has one page-level polite status region at
  [review_server.html](../src/vault_cleaner/ui/review_server.html#L13), while the
  duplicate list itself is repainted beneath a persistent scope status at
  [review_server.html](../src/vault_cleaner/ui/review_server.html#L69). Clipboard
  success/failure may use the existing `announce` path; it must not create a
  competing assertive live region per group.
- Clipboard transport does not exist in production today. The analogous
  browser-owned byte/download boundary is kept in the adapter in
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L1239), not in the
  snapshot/report/server schema. Clipboard access belongs at the same browser
  adapter boundary.
- The current Node suites already exercise hostile group strings and opaque ids
  in [test_review_ui_js.py](../tests/test_review_ui_js.py#L1111), and exercise
  duplicate rendering, server-acknowledged verdict repaint, and mixed group
  kinds in [test_server_ui_js.py](../tests/test_server_ui_js.py#L2400). The
  packaged Chromium suite covers the real duplicate surface and responsive
  orientations in [test_server_browser.py](../tests/test_server_browser.py#L853).

### DIM query evidence and the length decision

The planner inspected upstream `DestinyItemManager/DIM` at commit
[`964adf6ce554fdaac57381b2f1b35abc25ec0a97`](https://github.com/DestinyItemManager/DIM/commit/964adf6ce554fdaac57381b2f1b35abc25ec0a97)
(2026-09-01):

- DIM's advanced search definition declares `id` as a free-form filter at
  [`src/app/search/items/search-filters/advanced.ts`](https://github.com/DestinyItemManager/DIM/blob/964adf6ce554fdaac57381b2f1b35abc25ec0a97/src/app/search/items/search-filters/advanced.ts#L5-L13).
- DIM itself emits multi-item searches as ``id:${i.id}`` joined by ` or ` at
  [`src/app/item-triage/ItemTriage.tsx`](https://github.com/DestinyItemManager/DIM/blob/964adf6ce554fdaac57381b2f1b35abc25ec0a97/src/app/item-triage/ItemTriage.tsx#L343-L357).
- DIM recognizes the all-`id` OR form specially in its search parser at
  [`src/app/search/search-filter.ts`](https://github.com/DestinyItemManager/DIM/blob/964adf6ce554fdaac57381b2f1b35abc25ec0a97/src/app/search/search-filter.ts#L255-L268).
- A byte/text scan of current DIM source and docs found **no 2048-character
  input contract**. Therefore this plan must not claim that 2048 is DIM's
  documented maximum. `2048` remains a conservative vault-cleaner per-chunk
  safety budget inherited from the audited prototype. It is enforced exactly
  and described as vault-cleaner's limit.

For a maximum-width decimal uint64 id, one term is 23 characters (`id:` plus
20 digits) and each later term costs another 27 (` or ` plus the term). Exactly
76 such ids consume 2048 characters; 77 require a second chunk. The builder
must measure JavaScript string `.length`, append whole terms only, and never
truncate a term or id.

### Model verification and selection

Google's official Gemini documentation was rechecked on 2026-09-05. It names
the exact stable model id `gemini-3.8-flash`, supports the native
`thinking_level` values `low`, `medium`, and `high`, and explicitly does not
support `minimal`. This ticket is a bounded browser feature, but its
destructive-adjacent selection semantics, asynchronous clipboard failure path,
dual-orientation renderer, and Playwright proof justify the repository matrix's
routine-implementation model at its highest native reasoning setting:
`gemini-3.8-flash` with `thinking_level = high`.

The orchestrator must verify that its active runtime can instantiate this
Google model. If it cannot, it prepares the reusable prompt below for a human
operator under the repository's manual cross-provider boundary; it must not
silently substitute a different model without recording the actual provider,
model, effort, and fallback.

## Dependencies and assumptions

- Issue #117 is open, labeled `enhancement`, and in project 3 with status
  `Todo`, verified 2026-09-05. It intentionally has no milestone. Do not invent
  one or move its project status during implementation.
- The issue said #113 would be beneficial but was not a hard dependency. That
  staleness is resolved: #113 is closed; PR #120 and the follow-up #119/#131
  implementation are merged into this plan's `main` baseline. The group
  hierarchy and dual responsive matrices now differ materially from the old
  prototype, so this plan targets the current `armorGroup` seam rather than
  porting prototype DOM code.
- The implementation uses the existing projected group fields and current
  server-adopted verdict map. No report/snapshot/server API field is missing;
  a schema change is neither needed nor permitted.
- The feature applies to both authoritative group kinds only when a member has
  an existing proposal that `armorMemberCanVerdict` recognizes and its current
  verdict is `approved`. A same-stat group remains review-only as a grouping
  operation; this feature does not manufacture a proposal, survivor, or group
  verdict.
- Instance ids remain opaque strings. The query builder prefixes and joins
  them; it does not parse, normalize, sort numerically, deduplicate across
  groups, or reconstruct them.
- Query labels are display text built directly from projected `group.name`,
  `group.type`, and `group.guardianClass`. They are not recovered from rendered
  text and are not embedded as DIM comments. Keeping comments out makes every
  character in the enforced budget part of the actual filter.

## Proposed Plan & Scope

### Pure selection and query construction

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L129)

Add small pure helpers, exported for direct Node tests:

1. `approvedJunkIdsForArmorGroup(group, verdicts)` returns projected member ids
   in authoritative backend member order if and only if:
   - `armorMemberCanVerdict(group, member)` is true;
   - the applicable current proposal action is `junk`, not merely `review`;
   - `verdictOf(verdicts, member.id) === "approved"`; and
   - for defensive exact-group protection, `member.id !== group.preferredSurvivorId`.

   The proposal-action check must use the same exact/same-stat projection seams
   already used by `armorMemberCanVerdict`: exact members use `proposalAction`,
   same-stat members use `currentProposalAction`. Approval of a proposed-review
   member is **not** approval to junk it and must never emit an id.

2. `dimIdQueryChunks(ids, maxLength)` validates string ids and produces ordered
   chunks of `id:<opaque-id> or id:<opaque-id>`. Default `maxLength` is the
   named constant `DIM_QUERY_CHUNK_MAX = 2048`. A whole single term longer than
   the budget is an error; no partial output is returned. Every chunk is
   non-empty and `chunk.length <= maxLength`.

Do not parse ids, sort them, add labels/comments, URL-encode them, or call a
clipboard API in these helpers.

### One staged control per rendered group

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1452)

Extend `createView` with adapter callbacks for preparing presentation state and
copying one string. Render one group-level query panel between the shared group
header and comparison matrix. It must not be created inside
`armorMatrixRowsTable`, `armorMatrixColumnsTable`, or `armorMemberCell`.

Settled interaction and exact copy:

- Initial secondary button: **`Prepare approved junk DIM search`**.
- With no approved junk candidates it is disabled, with adjacent text:
  **`Approve at least one proposed junk piece to prepare a DIM search.`**
- The initial button's accessible description states:
  **`Builds a local DIM search from approved junk in this group. Nothing is changed in DIM.`**
- Activating Prepare reveals, but does not copy, a labelled read-only query
  area. Its heading is constructed as:
  **`DIM search for <group.name> · <group.type> · <group.guardianClass>`**,
  with each placeholder inserted as an inert text node from the projected group
  object. Do not parse `.textContent` or embed this display label in the query.
- The explanatory copy is:
  **`Approved junk only. Preferred, retained, review-only, vetoed, and unreviewed pieces are excluded.`**
- For one chunk, button text is **`Copy query`**. For multiple chunks, each
  button is **`Copy query N of M`** and the panel says
  **`Split into M complete queries to stay within vault-cleaner's 2048-character per-query limit. Run every query to cover all approved junk in this group.`**
- Each chunk is visibly selectable/read-only before its copy button. Copying is
  a second, explicit user action. The first Prepare click must make zero calls
  to the clipboard API.
- On success announce **`DIM search query N of M copied. Nothing was changed in DIM.`**
  (use `1 of 1` for one chunk). On failure keep the text visible and announce
  **`Could not copy the DIM search query. Select the visible text and copy it manually.`**
- Do not offer a whole-group/survivor-inclusive mode. Do not use destructive
  styling or place this before the ordinary verdict controls in keyboard order.

Prepared text is a cache of current presentation state, not authority. The
adapter must close/clear all prepared panels whenever an envelope is adopted
after a report or verdict response, including same-revision verdict repaint.
The user can immediately prepare again from the acknowledged verdict map.
Filters may hide/destroy a group normally; no prepared query state is restored
across `renderList` rebuilds. Finalised/disconnected reports may still prepare
and copy from their frozen visible data because this is a local browser action,
not a server mutation.

### Browser-owned clipboard boundary

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L775)

Provide the view with a `copyText(text)` callback implemented through
`navigator.clipboard.writeText`. It returns a promise and handles absence,
rejection, or synchronous failure without removing the visible fallback text.
The callback must receive only the already-built query string; it must not read
the DOM to recover ids or labels.

Add a small adapter-owned prepared-panel reset token/callback and invoke it from
`adopt` before/while the current verdict/report state is repainted. Do not send
a request, add an endpoint, persist clipboard state, modify the session
envelope, or treat clipboard activity as `mutationInFlight`.

### Styling and packaged resource behavior

#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

Add narrowly scoped `.dim-query-*` rules for a quiet secondary action, visible
read-only text/chunks, wrapping of long queries, keyboard focus, and narrow/dark
layouts. Use no inline styles: the server CSP permits only `style-src 'self'`.
The query text must wrap or scroll within its own container without causing
document-level horizontal overflow at 390px.

No change is expected in `review_server.html`, Python application code, CSP,
asset routing, dependencies, or packaging metadata because the three edited UI
assets are already packaged.

### Focused automated and manual proof

#### [MODIFY] [test_review_ui_js.py](../tests/test_review_ui_js.py#L1111)

Add direct tests for selection and chunk construction:

- exact group: preferred survivor excluded even if defensively marked approved;
- retained/read-only, vetoed, unreviewed, and approved-review members excluded;
- only approved proposed-junk members included in backend order;
- same-stat existing `review` proposal excluded and existing `junk` proposal
  included only when approved;
- hostile/prototype-shaped strings remain strings and do not influence ids;
- 76 maximum-width ids fit exactly in one 2048-character chunk; the 77th starts
  a second complete chunk; concatenated chunk terms reproduce all input ids in
  order with none lost or duplicated;
- a term larger than an injected tiny test budget fails instead of truncating.

#### [MODIFY] [test_server_ui_js.py](../tests/test_server_ui_js.py#L2400)

Extend the fake-DOM adapter coverage to prove:

- exactly one Prepare control exists per group despite two matrix orientations;
- empty approved selection disables Prepare and renders the settled empty copy;
- Prepare reveals projected-data label and visible query but does not call the
  clipboard mock;
- the second click calls the mock with exactly one complete chunk and announces
  success;
- mocked rejection preserves visible text and announces the manual-copy fallback;
- an oversized synthetic approved set renders all chunks, each within budget,
  and copies only the specifically clicked chunk;
- a server-acknowledged approval invalidates any prepared panel; preparing again
  includes the newly approved id, while veto/unset removes it;
- hostile group names render inert and cannot alter the query or create nodes.

#### [MODIFY] [test_server_browser.py](../tests/test_server_browser.py#L853)

Add one focused packaged-Chromium test using committed fake armour data. Grant
clipboard permission in the Playwright context or stub only the clipboard write
at the browser boundary while retaining the real packaged DOM. Approve a junk
proposal, prepare its group query, assert the preferred survivor id is absent,
assert no clipboard write happened on Prepare, then copy and assert exact text.
Also exercise the approved-set-empty state before approval and verify at 390px
that visible query text causes no document horizontal overflow and the control
is keyboard reachable with visible focus.

The oversized 77-id case belongs in deterministic Node tests because current
producers need not emit a real group that large. Browser coverage must not
manufacture a new backend grouping shape merely to reach the length boundary.

#### [MODIFY] [browser-verification.md](../docs/browser-verification.md#L105)

Add an Issue #117 focused checklist and append the implementer's measured result:
approved-only selection, survivor exclusion, no first-click clipboard write,
manual-copy fallback, frozen/finalised behavior, narrow layout, keyboard focus,
and actual required-browser command result.

#### [MODIFY] [README.md](../README.md#L196)

After the verdict workflow paragraph, document the optional local bridge in one
short paragraph: prepare a per-group approved-junk DIM search, inspect it, then
copy each complete chunk; nothing is sent to or changed in DIM by vault-cleaner.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

Add a newest-first dated implementation entry recording the shipped interaction,
selection exclusions, 2048-as-vault-cleaner-budget decision, chunk boundary
measurements/tests, browser result, and that rules/schema/dependencies remain
unchanged.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- it is mechanically necessary to select current approved **junk** proposals
  from one already-authoritative projected armour group, build/display/copy
  complete bounded DIM `id:` OR queries, or verify/document that path;
- it derives membership from the projected group plus `state.verdicts`, never
  rendered text or an invented grouping/decision rule;
- it preserves opaque string ids and excludes the preferred survivor plus every
  member that is not both a current junk proposal and approved; and
- it stays within the existing packaged browser assets/tests/docs/worklog, with
  no backend, schema, rule, dependency, persistence, or lifecycle change.

Worked examples:

- **IN SCOPE:** a pure helper returns `['id:8301 or id:8302']` for two projected
  proposed-junk members whose current verdicts are approved.
- **IN SCOPE:** 77 twenty-digit ids become two visible chunks, each at most 2048
  characters, with every term present exactly once and each copy button copying
  only its labelled chunk.
- **IN SCOPE:** clearing prepared text after `adopt` so an acknowledged veto
  cannot leave that id in copyable stale text.
- **OUT OF SCOPE:** a `Copy whole group` button, even behind a secondary menu;
  survivor-inclusive output is the prototype's highest-consequence defect.
- **OUT OF SCOPE:** treating `approved` on a `review` proposal as permission to
  bulk-tag junk in DIM.
- **OUT OF SCOPE:** deriving a label with `article.textContent`, adding labels as
  DIM comments, or parsing/sorting ids numerically.
- **OUT OF SCOPE:** a server endpoint, report/snapshot field, persisted prepared
  query, verdict/group bulk mutation, DIM deep link, or runtime dependency.

### Stop conditions

Stop implementation and return to orchestrator if:

- current `main` changes the projected group/verdict contracts or renderer so
  the cited authoritative seams no longer exist;
- a safe selection requires new backend/report/snapshot data, a schema version,
  `RULESET_VERSION`, or any Python rule/ranking/grouping change;
- DIM no longer accepts the upstream-proven `id:<opaque> or id:<opaque>` form,
  or authoritative evidence establishes a different hard limit/syntax;
- clipboard support would require weakening CSP, server auth/origin/Host rules,
  persistence/lifecycle semantics, or a new dependency;
- a survivor, retained member, approved review proposal, vetoed proposal, or
  unreviewed proposal cannot be mechanically excluded from every chunk;
- current UI architecture cannot invalidate prepared text after acknowledged
  verdict/report adoption without broad repaint or session-state changes; or
- required Chromium cannot run. A skipped browser suite is not a pass.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Approved review leaks into junk output:** Reusing
   `armorMemberCanVerdict` without separately requiring the current proposal
   action to be `junk` includes an approved review-only recommendation.
2. **Prepared query goes stale after acknowledgement:** Updating only the two
   matrix verdict occurrences leaves already-rendered text containing an id
   that was just vetoed or unset.
3. **Control is doubled by responsive rendering:** Adding the action to
   `armorMemberCell` or either matrix factory creates duplicate clipboard
   controls and hidden focus targets because both orientations exist in DOM.
4. **Length test proves display, not completeness:** A test may assert every
   chunk is under 2048 while failing to prove that all source ids appear once,
   in order, with no truncated boundary term.

# Reusable implementer execution prompt

Implement issue #117 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-117-implementation-plan.md
```

Read the entire handoff, issue #117, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-117-dim-search-query`; branch from latest `main` and record the base SHA;
- use Google `gemini-3.8-flash` with native `thinking_level = high`; if the runtime cannot instantiate it, stop for the repository's manual cross-provider launch rather than silently substituting;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, `git diff --check origin/main...HEAD`;
- verify no tracked file exists under `data/` and inspect `git status --short` before committing;
- commit with `Refs #117` and no closing keyword, then push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, report the branch name, base and head SHAs, complete output of every verification command, clipboard/browser setup used, every stop condition considered, and any deviation from the plan with its justification.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**

The code is presentation-only, but the output is destructive-adjacent: it is
designed to select items immediately before a user bulk-tags them as junk in
DIM. A single selection error can include the survivor or reinterpret an
approved review recommendation as junk. The feature also crosses projected
group authority, current server-acknowledged verdict state, dual-orientation
DOM, an asynchronous browser API, and a completeness-sensitive chunking
boundary. Those are compact changes with a disproportionately high consequence,
well suited to an independent complete-diff review.

The orchestrator confirms the path against the real diff and selects the
reviewer's exact provider, model ID, and native effort only after inspecting the
implementation. A different model family from Gemini is preferred when the
runtime allows it.

# Review checklist

- [ ] Check 1: The selection requires both a current approved verdict and a
  current `junk` proposal. Preferred survivor, retained/read-only, review,
  vetoed, and unreviewed members are absent in exact and same-stat cases.
- [ ] Check 2: Ids stay strings end to end; there is no `Number`, `parseInt`,
  numeric sort, normalization, or DOM-text parsing in the feature diff.
- [ ] Check 3: `id:<id> or ...` matches current upstream DIM syntax. `2048` is
  described only as vault-cleaner's conservative chunk budget, not a verified
  DIM maximum.
- [ ] Check 4: The 76/77 maximum-width-id boundary test proves every output
  chunk is complete and at most 2048 characters **and** all input ids occur
  exactly once in original order.
- [ ] Check 5: Exactly one Prepare control is rendered per group, outside both
  responsive matrices. The hidden orientation adds no clipboard focus target.
- [ ] Check 6: Prepare reveals text and performs no clipboard write. Only the
  separate Copy button writes; rejection retains a visible manual-copy fallback.
- [ ] Check 7: Every `adopt` path invalidates prepared text, including
  same-revision verdict repaint, stale reconciliation, replacement, reset, and
  finalised refresh. Preparing again reflects only the acknowledged verdict map.
- [ ] Check 8: Labels use projected fields and inert text nodes; hostile names
  cannot alter markup or query text. No label/comment consumes query budget.
- [ ] Check 9: Finalised/disconnected frozen data remains locally preparable and
  copyable without entering `mutationInFlight` or making a server request.
- [ ] Check 10: At 390px query text stays contained, keyboard focus is visible,
  and the required Chromium test actually runs rather than skips.
- [ ] Check 11: No backend endpoint/schema/snapshot/rules/version/dependency/CSP
  change; no whole-group control; no bulk verdict semantics; no tracked `data/`.
- [ ] Check 12: `ruff`, full `pytest`, required browser suite, and
  `git diff --check origin/main...HEAD` pass; README, browser verification, and
  newest-first WORKLOG entry accurately record the behavior.

# Dispatch comment draft

Planned #117 in [handoffs/issue-117-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-117-implementation-plan.md) on `main`.

- **Implementer tier & effort:** Google `gemini-3.8-flash`, native `thinking_level = high`
- **Implementation branch:** `feat/issue-117-dim-search-query`
- **Recommended review path:** `independent adversarial review` — the orchestrator confirms against the real diff and selects the reviewer's exact model and effort at dispatch time.
- **Likely findings:** approved review proposals leaking into junk queries; prepared text surviving a verdict acknowledgement; duplicate controls from the two responsive matrix DOMs; chunk tests enforcing length without proving complete, once-only id coverage.

**Staleness resolved during planning:** #113 is closed and its #119/#131 follow-up presentation is merged. The old prototype's DOM parsing and two side-by-side whole-group/approved controls are not portable to the current dual-orientation renderer. This plan ships one staged approved-junk-only action, builds labels from projected data, and splits complete queries at vault-cleaner's enforced 2048-character budget.
