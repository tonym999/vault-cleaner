# Issue #150 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#150 — Generate a DIM search query for the weapon proposals shown or selected`

**Milestone:** `None — deliberately unassigned; #117 and #148 are the unmilestoned interop/presentation seams this ticket extends`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** Google `gemini-3.8-flash`, native `thinking_level = high` (justified below)

**Plan baseline:** `main` at `caea7486e5b1ab124ca6576d80dd2063cf5544d5` (2026-09-13)

**Allocated implementation branch:** `feat/issue-150-shown-weapon-dim-query`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Add one local, live read-only subsection to the Proposals workflow that emits
complete DIM `id:` search text for exactly the **weapon proposals matching the
current Proposals filters**.

This plan deliberately settles the issue's “shown set, selected set, or both?”
question as **shown set only**. The current UI has proposal verdicts and filters,
but no independent row-selection model. Users who want an approved-only,
vetoed-only, unreviewed-only, junk-only, review-only, in-loadout, or otherwise
bounded query first apply the existing filters; the live query then updates
from that same result. This uses one authoritative membership definition
instead of introducing checkbox state, selection persistence, or a second
bulk-action boundary.

The live query is a locating aid, not an approved-junk list. It may include
junk and review proposals and approved, vetoed, or unreviewed proposals whenever
the current filters admit them. It also includes a shown item still suppressed
by an active persisted veto, because persisted vetoes affect final output but do
not remove the item from the shown Proposals set. Rendering or selecting query
text changes no verdict, tag, note, item, report, session, or DIM state.

## Context & Measurement

### Current proposal membership and UI seams

- [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L208) owns the pure
  `filterItems(items, query, verdicts)` predicate used by the Proposals view. It
  already applies action, kind, reason, class, protection, loadout, session
  verdict, and text filters. This is the authoritative meaning of “shown”; a
  new selection predicate must not reproduce those facets.
- The adapter's `visibleIds` helper delegates to that predicate at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L428), the summary's
  `shown` tile delegates to it at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L977), and the
  rendered proposal list delegates to it at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L1222).
- The three current bulk verdict buttons say **`Approve all shown`**,
  **`Veto all shown`**, and **`Unset all shown`** at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L1144). Their
  mutation path recomputes the same filtered set at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L1349). The live
  query must use that same proposal membership, then narrow it to
  `item.kind === "weapons"`; it must not read rendered rows, grouped `<details>`,
  the current sort, or the bulk-control DOM.
- There is no row checkbox or independent selected-id registry in `createState`
  ([review_server.js](../src/vault_cleaner/ui/review_server.js#L81)). Approve,
  veto, and unset are durable-in-session review verdicts, not transient
  selection. Adding checkbox selection would require new lifecycle,
  reconciliation, accessibility, and reset semantics and is therefore not a
  small interpretation of this ticket.
- Current fake-browser evidence uploads `weapons_hostile.csv` and measures five
  weapon proposals, including one in-loadout proposal, at
  [test_server_browser.py](../tests/test_server_browser.py#L1182). This is an
  existing synthetic end-to-end fixture seam for the live set; no real
  export, new fixture, or private aggregate is needed.

### Existing DIM query and cross-check seams

- #117 landed through PR #151 before this baseline. Its shared
  `dimIdQueryChunks(ids, maxLength)` helper at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L636) validates every id
  against `^[0-9]{1,20}$` as an opaque string, emits `id:<id> or id:<id>`, and
  splits only on complete terms at the 2048-character DIM saveability boundary.
  It validates the complete input before emitting output, so a malformed id
  fails atomically rather than returning a partial query.
- The helper and `DIM_QUERY_SAVEABLE_MAX` are public exports at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1729). Its deterministic
  tests already prove the 76/77 maximum-width-id boundary, once-only ordering,
  invalid-id rejection, and invalid injected limits at
  [test_review_ui_js.py](../tests/test_review_ui_js.py#L2261). #150 must call
  this helper; it must not fork, wrap, or subtly alter the DIM expression
  builder.
- #117 also supplied contained read-only query output styles at
  [review.css](../src/vault_cleaner/ui/review.css#L403). They are reusable for
  complete query chunks and already have required-browser evidence for
  keyboard reachability and 390px containment in
  [docs/browser-verification.md](../docs/browser-verification.md#L422).
- #148 landed through PR #153 before this baseline. It creates the
  **`Cross-check in DIM`** panel and three static loadout queries at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L35) and
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L627). The dynamic
  shown-weapons subsection belongs inside that existing panel, visibly distinct
  from the three static strings; no second report-level DIM panel is needed.
- #148's adapter harness already owns the cross-check DOM and exact static-query
  assertions at [test_server_ui_js.py](../tests/test_server_ui_js.py#L4116), and
  its browser test owns the live panel at
  [test_server_browser.py](../tests/test_server_browser.py#L1225). Those tests
  must remain green and the three static strings must remain byte-for-byte
  unchanged.

### Model verification and selection

Google's official documentation was rechecked on 2026-09-13:

- [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
  identifies the stable model code as `gemini-3.8-flash` and lists thinking
  support at `low`, `medium`, and `high`; `minimal` is unsupported.
- [What's new in Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/latest-model)
  identifies the model as generally available and intended for long-horizon
  software engineering and agentic workflows.
- [Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking) confirms
  `medium` as the default and `low | medium | high` as the supported native
  levels for `gemini-3.8-flash`.

`gemini-3.8-flash` at `thinking_level = high` is appropriate. The production
change is bounded to existing browser seams and a previously reviewed pure query
builder; it does not require Pro-tier architectural work. High thinking is
warranted because “shown” must remain exactly aligned with eight current filter
axes, mixed-kind reports must never leak armor or ghost ids, active persisted
vetoes must be described honestly, and the result is directly actionable in
DIM.

The orchestrator must still verify that its runtime can instantiate this Google
model and native effort. If it cannot, it must prepare the reusable prompt below
for manual cross-provider execution and record the actual provider/model/effort;
documented availability is not runtime availability.

## Dependencies and assumptions

- Issue #150 is open, labeled `enhancement`, and belongs to project 3 at `Todo`,
  verified on 2026-09-13. It has no milestone. The closely related #117 and #148
  are also deliberately unmilestoned, so implementation must not invent or
  change milestone/project metadata.
- The issue's hard dependency is resolved: #117 is closed and PR #151 merged at
  `649bc30d9c1f2e290ae15e710abc20e5f0806fcb`. The shared query validator/chunker
  and read-only presentation seam are visible on `main`.
- The issue body describes #148 in the future tense. That text is stale: #148 is
  closed and PR #153 merged at baseline commit
  `caea7486e5b1ab124ca6576d80dd2063cf5544d5`. The plan targets its shipped
  cross-check panel, static queries, loadout facet, and synthetic browser test.
- #140's boundary remains authoritative: this explicit weapon extension may
  reuse #117 but must not change armor query semantics, rules, ranking,
  proposal decisions, or DIM/Bungie integration.
- “Shown weapon proposals” means the result of
  `filterItems(state.items, state.query, state.verdicts)`, narrowed to
  `kind === "weapons"`, in existing backend order. Sort/group presentation does
  not change membership and therefore does not change query identity.
- A verdict is not a selection. Default filters include approved, vetoed, and
  unreviewed proposals. The existing Session verdict filter is the supported
  way to request one of those subsets; there is no separate “selected” mode.
- Active persisted vetoes are not a Proposals filter. `filterItems` intentionally
  leaves those proposals shown while `keptItems` separately excludes them from
  final output. The query therefore includes a shown weapon with an active
  persisted veto, and its warning must say so; silently applying `keptItems`
  would make the query disagree with the visible set.
- Output is visible read-only text only. There is no automatic Clipboard API
  write, DIM deep link, server endpoint, or navigation in this ticket. The user
  manually selects and copies a complete chunk.
- Ids remain opaque strings. The selection helper preserves them unchanged; the
  existing #117 builder owns shape validation and chunk construction. No
  `Number`, `parseInt`, numeric ordering, quote reconstruction, or CSV-wide id
  validation is allowed.
- The planning PR records this companion interop boundary in `PLAN.md`; no
  `RULESET_VERSION`, snapshot schema, review/session schema, or dependency
  change is required.

## Proposed Plan & Scope

### Pure shown-weapon selection over the existing filtered result

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L596)

Add and export one pure helper, `weaponProposalIdsForDimQuery(items)`, beside the
existing #117 DIM helpers:

- require `items` to be an array;
- require every supplied entry to be an object, then include only entries whose
  `kind === "weapons"`;
- preserve every included `id` unchanged and in input order;
- reject a weapon entry whose id is not a string matching the existing
  `DIM_ID_PATTERN`;
- ignore id fields on well-formed non-weapon objects rather than validating or
  emitting them; and
- never read verdicts, filters, sort state, DOM nodes, labels, hashes, names,
  tags, notes, or loadout cells.

The adapter supplies the already-filtered items. It then passes the returned id
array directly to existing `dimIdQueryChunks`; do not add another query builder,
another length constant, or another id grammar.

### Live subsection in the existing Cross-check in DIM panel

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L627)

The Cross-check panel is constructed once during boot at
[review_server.js](../src/vault_cleaner/ui/review_server.js#L627), before `state`
and `view` exist at [review_server.js](../src/vault_cleaner/ui/review_server.js#L709).
During that existing construction, create a stable shown-weapons subsection
before the static loadout-query controls. The boot path creates only the DOM
skeleton and stable render targets: heading, explanation, a count node with
`role="status"` and `aria-live="polite"`, and an output container. It must not
read state, filter items, or construct query text at boot. The polite count
region exists before any count text is assigned and is not destroyed/recreated
on each update.

Add one `renderShownWeaponDimQuery()` function after `state` and `view` exist,
and call it from `renderSummary()` at
[review_server.js](../src/vault_cleaner/ui/review_server.js#L977). This is the
single refresh hook: query/search changes and Reset filters already call
`renderSummary()` ([review_server.js](../src/vault_cleaner/ui/review_server.js#L1004),
[review_server.js](../src/vault_cleaner/ui/review_server.js#L1154)); `adopt()`
always reaches it after verdict acknowledgements, server updates, and report
refreshes ([review_server.js](../src/vault_cleaner/ui/review_server.js#L906));
and `setSurface()` reaches it after a view switch
([review_server.js](../src/vault_cleaner/ui/review_server.js#L783)). Do not hook
this into `renderList()`: sort/group-only changes call that function despite
unchanged membership, and its Armor duplicates branch returns early.

`renderShownWeaponDimQuery()` owns the subsection's visibility. It sets the
subsection hidden whenever the report is idle or `state.surface !== "proposals"`
and visible otherwise. Because both `setSurface()` and `adopt()` call
`renderSummary()`, their existing paths must result in that toggle; do not hide
the whole Cross-check panel, whose #148 static controls retain their current
idle-only visibility. Returning to Proposals **must** show the subsection again
with query text recomputed from the current report and filters.

The subsection renders this exact copy:

- Heading: **`Shown weapon proposals`**
- Explanation: **`This DIM search updates from the weapon proposals matching the current Proposals filters. For an approved-only query, set Session verdict to approved first.`**
- Live count: **`N weapon proposal(s) currently shown.`**, with correct singular
  or plural.
- Empty state: **`No weapon proposals match the current filters.`** Render no
  query details or empty textarea.

On every `renderSummary()` refresh while the subsection is visible:

1. recompute `ui.filterItems(state.items, state.query, state.verdicts)` rather
   than trusting the rendered table or a cached count;
2. narrow through `ui.weaponProposalIdsForDimQuery`;
3. call `ui.dimIdQueryChunks(ids, ui.DIM_QUERY_SAVEABLE_MAX)`;
4. update the stable count node only when its text changes; and
5. derive an ephemeral render key from the complete renderer-owned display
   model: empty, atomic error, or the exact non-empty label, warning, and chunks.

The render key is a DOM-reconciliation optimization only. Membership and chunks
are always recomputed before comparing it; the key must never supply ids, bypass
`filterItems`, suppress a renderer call or its recomputation, enter `state` or an
envelope, or persist outside this boot instance. When the key is unchanged,
leave the output subtree untouched so an expanded `<details>`, focused textarea,
and its selection range survive verdict acknowledgements or search keystrokes
that do not change the query. When the key changes, replace the output content
immediately. Before replacement, capture any existing `<details>.open` value in
a renderer-local nullable flag and reuse the latest captured choice across
empty results and surface switches. Only a non-empty render while that flag is
unset is collapsed by default. Render each complete chunk as a labelled
read-only textarea using the #117 classes and `spellcheck="false"`.

There is no Generate button, generated-query membership signature, clear
announcement, activation state, persistence decision, or cached membership.
The query is a pure render of current state, so it cannot remain stale after any
path that reaches `renderSummary()`. Query text and chunk containers are not live
regions; only the short, stable count status is announced as filters change.

Generated output renders this exact copy:

- Label: **`DIM query for N shown weapon proposal(s)`**, with correct singular
  or plural.
- Warning: **`This locating query includes every matching weapon proposal — junk and review, any session verdict, and items still suppressed by an active saved veto unless the current filters exclude them. Do not treat it as an approved-junk list.`**
- Side-effect explanation: **`Rendering or selecting this text changes no vault-cleaner verdict, tag, note, item, or DIM state.`**
- Chunk labels: **`DIM query N of M`**, including `1 of 1`.
- For multiple chunks, reuse #117's split behavior, boundary, and first sentence,
  but scope the second sentence to this shown-only feature:
  **`Split into M complete queries at DIM's current 2048-character saveability boundary. Use every query to cover the shown proposals.`**
- Atomic failure: **`Could not generate a safe DIM query for the shown weapons.`**
  Render no partial textarea and never echo the rejected id.

The live query remains available for an already-loaded finalised or disconnected
frozen report because it uses local data only. It must not call `fetch`,
`mutateVerdicts`, `toggleVerdict`, `bulkVerdict`, Clipboard, navigation, or a
server endpoint; it must not change `state.verdicts`, revisions,
`mutationInFlight`, persisted vetoes, report/session state, or row registries.

Do not refactor #117's group-specific renderer or #148's static-query definitions
to share DOM factories. Reusing the pure selector/chunker and existing CSS is
the intended seam; a cross-cutting UI abstraction is not needed for this ticket.

### Contained presentation

#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css#L403)

Reuse `.dim-query-*` text, warning, chunk, textarea, error, and focus styles.
Add only narrowly scoped `.weapon-dim-query-*` or cross-check-descendant rules
needed to separate the dynamic subsection from the three static fields, lay out
the live count/details summary, and keep output contained at 390px. Do not
broaden shared badge, table, control, or armor-group selectors and add no inline
style (the server CSP remains `style-src 'self'`).

### Automated proof

#### [MODIFY] [test_review_ui_js.py](../tests/test_review_ui_js.py#L2261)

Extend the existing DIM-helper coverage to prove the new pure selector:

- mixed weapons/armor/ghost input emits only weapon ids in supplied order;
- leading-zero and 20-digit ids remain unchanged strings;
- malformed weapon ids, numeric ids, missing weapon ids, non-object entries,
  and non-array input reject atomically;
- malformed id fields on well-formed non-weapon objects are ignored because
  they cannot enter the weapon query; and
- feeding its output to `dimIdQueryChunks` produces the expected complete query.

Do not duplicate #117's full 76/77 boundary matrix in this file; it already
proves the unchanged builder. The adapter integration below must still prove
that the dynamic UI renders multiple complete chunks rather than truncating.

#### [MODIFY] [test_server_ui_js.py](../tests/test_server_ui_js.py#L4116)

Extend the cross-check adapter harness or add a focused sibling harness proving:

- the boot path creates the stable subsection, output container, and empty
  `role="status" aria-live="polite"` count region before any count text is set;
- the live subsection renders before the unchanged three static strings and
  only on the Proposals surface;
- an unfiltered mixed-kind report selects every and only weapon proposal,
  including junk/review and approved/vetoed/unreviewed rows;
- action, kind, reason, class, protection, loadout, verdict, and text filters
  affect membership only through `ui.filterItems`; specifically, setting
  Session verdict to `approved` makes the query approved-only without a second
  mode;
- zero matching weapons shows the exact empty copy and no query details or
  textarea;
- 77 maximum-width synthetic weapon ids render two complete labelled chunks
  with every id once and in order, proving the adapter actually uses #117's
  builder rather than slicing or truncating output;
- a malformed included weapon id fails closed with the exact local error and no
  partial textarea;
- query/search changes, Reset filters, `adopt`, and `setSurface` all reach the
  one `renderSummary` refresh hook; no query rendering is attached to
  `renderList`;
- changing shown membership, verdicts, report identity, or filters immediately
  rerenders exact current output; a sort/group-only change does not invoke the
  query renderer;
- the first non-empty query is collapsed; after the user expands it, an
  unchanged query survives both a verdict acknowledgement under the default
  Session verdict filter and a search keystroke that leaves membership unchanged
  without replacing the `<details>` or textarea node, losing focus/selection, or
  collapsing;
- a changed query is reconciled immediately while preserving the established
  `<details>` open/closed state; the local render key is never used as membership
  input and never prevents the authoritative filter/chunker calls;
- switching away hides the subsection; returning to Proposals must show it with
  query text recomputed from current state;
- finalised and disconnected frozen reports render identical local text;
  and
- live rendering makes zero fetch/clipboard/navigation calls and leaves all adapter
  state, verdicts, revisions, persisted vetoes, `mutationInFlight`, rows, and
  duplicateRows unchanged.

Preserve the exact-equality assertions for all three #148 static queries and
their Clipboard fallback/copy behavior.

#### [MODIFY] [test_server_browser.py](../tests/test_server_browser.py#L1182)

Extend `test_weapon_loadout_visibility_and_crosscheck_panel` with packaged
Chromium coverage. Start with the existing `weapons_hostile.csv` upload only;
do not upload `armor_close.csv` until the weapon-only assertions below have
finished:

1. assert the unfiltered textarea's literal value in authoritative backend
   order: **`id:18446744073709551615 or id:7004 or id:7006 or id:7008 or id:7010`**.
   Do not derive the expected ids from rendered rows, which would compare the
   output against another rendering of the same source;
2. verify the warning does not describe the result as approved junk and the
   query textarea is read-only with `spellcheck="false"`;
3. after the upload has completed, record requests and state, apply the
   in-loadout filter, and assert the live textarea updates to **`id:7004`** with
   zero new network calls and no verdict, revision, or server-state change;
4. reset the loadout filter and, at 390px, prove no document-level horizontal
   overflow and keyboard focus can reach the `<details>` summary and visible
   read-only textarea;
5. set the text search to **`no such weapon`** and assert the exact empty state
   with no `<details>` or textarea. Use this deterministic text filter instead
   of coupling the empty-set assertion to the Kind options available in a
   particular upload;
6. activate **`Reset filters`** and assert the five-id literal query returns;
7. only now upload the existing synthetic `armor_close.csv`, wait for its
   **`Accepted`** status, assert the Armor duplicates control is enabled, and
   switch to it unconditionally. Assert the live subsection is hidden, then
   return to Proposals and assert it is visible with the same five weapon ids;
   and
8. verify the pre-existing three static #148 queries remain unchanged after the
   second upload and both surface switches.

The 77-id integration stays deterministic in Node; do not manufacture a 77-row
CSV or real browser fixture solely to reach the chunk boundary.

#### [MODIFY] [browser-verification.md](../docs/browser-verification.md#L422)

Add an Issue #150 checklist and, after implementation, an execution record for
the exact shown-set membership, live filter refresh, warning/empty/error copy,
zero network/state side effects, read-only keyboard use, narrow containment,
and the actual required-browser result.

#### [MODIFY] [README.md](../README.md#L227)

Extend the browser-review guidance with one short paragraph: from the
Cross-check in DIM panel, use the live complete queries for currently shown weapon
proposals; filters define the set, including Session verdict for approved-only;
the result is a locating query rather than an approved-junk list; rendering or
selecting it changes nothing and the user manually copies every chunk they need.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

Add a newest-first implementation entry recording shown-only semantics, the
rejected independent-selection expansion, exact filter membership, reuse of the
#117 builder, the `renderSummary` live-refresh seam, active persisted-veto copy,
model/effort actually used, review result,
browser evidence, and unchanged rules/schemas/dependencies.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- it is mechanically required to select weapon ids from the existing filtered
  Proposals result, live-render complete chunks in the existing Cross-check in
  DIM panel from `renderSummary`, or test/document that local path;
- membership is exactly `filterItems(...)` narrowed to `kind === "weapons"`,
  with existing verdict filters providing approved/vetoed/unreviewed subsets;
- it calls #117's exported validator/chunker unchanged and preserves ids as
  opaque strings; and
- it changes only the packaged browser assets, focused tests, README/browser
  verification, and WORKLOG—never rules, reports, snapshots, endpoints, or
  persisted state.

Worked examples:

- **IN SCOPE:** with five displayed weapon proposals and two displayed armor
  proposals, the live renderer emits the five weapon ids only.
- **IN SCOPE:** set `Action = junk`, `Session verdict = approved`, and
  `Loadout = in a loadout`; the query includes only weapons matching all three
  existing filters.
- **IN SCOPE:** a filter change from ids `[7004, 7006]` to `[7004]` immediately
  rerenders the live textarea as `id:7004`, without a Generate action or cached
  membership authority.
- **IN SCOPE:** an ephemeral key made only from the freshly computed display
  model prevents needless DOM replacement and preserves open/focus/selection
  state; it never decides membership or suppresses recomputation.
- **IN SCOPE:** 77 20-digit ids become two complete read-only query chunks
  through `dimIdQueryChunks`, with no term lost, duplicated, or truncated.
- **OUT OF SCOPE:** adding selection checkboxes, a selected-id registry, a second
  bulk-action model, or selection persistence/reconciliation semantics.
- **OUT OF SCOPE:** calling all default-filter items “approved”, “junk”, or safe
  to bulk-tag; default membership includes review and vetoed proposals too.
- **OUT OF SCOPE:** deriving ids from visible table rows, DOM text, grouped
  sections, sort order, tags, notes, loadout names, or armor group members.
- **OUT OF SCOPE:** changing `dimIdQueryChunks`, its 2048 boundary, its regex,
  #117's armor-group modes, or #148's static strings/copy behavior.
- **OUT OF SCOPE:** a server endpoint, network call, clipboard write, DIM deep
  link, automatic action, new dependency, Python edit, rule/version/schema
  change, fixture/golden regeneration, or tracked `data/` file.

### Stop conditions

Stop implementation and return to orchestrator if:

- current `main` no longer has #117's exported builder or #148's Cross-check in
  DIM panel and the ticket cannot be delivered through those seams;
- “shown” cannot reuse `filterItems` and would require reimplementing filter
  predicates, parsing DOM state, or adding an independent selection registry;
- query rendering requires any new backend/report/snapshot field, Python
  change, server endpoint, session/review schema, ruleset/schema version bump,
  or runtime dependency;
- safe rendering cannot reject an invalid included weapon id atomically, or
  cannot remain synchronized through the one `renderSummary` hook;
- upstream DIM or current #117 tests show that `id:<id> or id:<id>` or the 2048
  saveability boundary is no longer valid;
- rendering triggers or requires fetch, verdict mutation, persistence,
  Clipboard, navigation, CSP/auth weakening, or any DIM/Bungie integration;
- the static #148 queries or #117 armor-group behavior would need semantic
  changes; or
- required Chromium cannot run. A skipped required browser suite is not a pass.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **The set is not actually the shown weapon set:** The implementation may use
   all `state.items`, include armor/ghost proposals from a mixed report, read
   rendered/sorted rows, or create an “approved” interpretation instead of
   delegating every facet to `filterItems`.
2. **The live refresh is wired to the wrong path:** Attaching query rendering to
   `renderList` misses or duplicates work across armor early returns and
   sort/group changes. `renderSummary` is the single hook reached by query
   changes, reset, `adopt`, and `setSurface`; it must also own subsection
   visibility.
3. **Live reconciliation destroys user context:** Unconditionally replacing the
   output on every `renderSummary` call collapses an expanded query and loses
   textarea focus/selection even when its text is unchanged. Recompute every
   time, skip unchanged DOM, and preserve the established open/closed state when
   changed output is rendered.
4. **#117 is copied rather than reused:** A second regex, length constant, joiner,
   or truncation path may drift from `dimIdQueryChunks`; the 77-id adapter proof
   should fail any locally rebuilt or sliced expression.
5. **A locating aid becomes a hidden action:** Clipboard/network calls, mutation
   coupling, misleading approved-junk copy, or keyboard-inaccessible overflow
   can make the dynamic output unsafe despite correct query syntax.

# Reusable implementer execution prompt

Implement issue #150 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-150-implementation-plan.md
```

Read the entire handoff, issue #150, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`,
the merged #117/#148 handoffs, and current relevant code before editing.

Rules:
- work on `feat/issue-150-shown-weapon-dim-query`; branch from latest `main` and record the base SHA;
- use Google `gemini-3.8-flash` with native `thinking_level = high`; if the runtime cannot instantiate it, stop for the repository's manual cross-provider launch rather than silently substituting;
- implement one live shown-set query only; do not add a Generate button,
  selection checkboxes, selected-id state, cached membership signature, or clear
  lifecycle;
- compute membership through `filterItems(state.items, state.query, state.verdicts)`, then narrow to weapons; the Session verdict filter is how an approved-only subset is requested;
- create stable empty query/count render targets while the Cross-check panel is
  built, then populate them only from a `renderShownWeaponDimQuery` call inside
  `renderSummary`; do not attach query rendering to `renderList`;
- recompute membership and chunks on every call, but use a renderer-local display
  key to leave identical output DOM untouched and preserve node identity,
  focus/selection, and the user's `<details>` open/closed choice; that key is
  never membership input or persisted state;
- include shown weapons with active persisted vetoes and reproduce the plan's
  warning about that intentional membership exactly;
- call the existing exported `dimIdQueryChunks` and `DIM_QUERY_SAVEABLE_MAX` unchanged; do not create another query builder, id grammar, or length constant;
- reproduce every user-facing string in the plan exactly and preserve #148's three static query strings exactly;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, and `git diff --check origin/main...HEAD`;
- verify `test -z "$(git ls-files data/)"`, inspect `git status --short`, and confirm no Python, golden, rule, version, dependency, or fixture file changed;
- commit with `Refs #150` and no closing keyword, then push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, report the branch name, base and head SHAs, changed files, full
verification output, model/provider/effort actually used, shown-set and live-
refresh evidence, all stop conditions considered, and every deviation with
justification.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**

The implementation is presentation-only and does not warrant a larger
implementer, but its output is immediately actionable in DIM. A membership bug
can include a hidden weapon, a vetoed proposal, an armor/ghost item, or an
out-of-date pre-filter set while the page appears to describe the current set.
Independent review should therefore verify membership against all existing
filter axes, atomic use of #117's query-safe builder, the single live-render
hook, non-destructive DOM reconciliation, honest locating-only copy, and zero
mutation/network/clipboard side effects.

The orchestrator confirms the path against the real diff and selects the
reviewer's exact provider, model ID, and native effort only after inspection. A
fresh non-Gemini reviewer is preferred when available, but reviewer selection
does not alter the requested Gemini implementer.

# Review checklist

- [ ] `filterItems(state.items, state.query, state.verdicts)` is the only filter
  authority; the result is narrowed to `kind === "weapons"`, preserves opaque
  ids, and never derives membership from the DOM, sort/group presentation, or
  armor groups.
- [ ] There is exactly one shown-weapons mode. Approved/vetoed/unreviewed subsets
  work through the existing Session verdict filter; no checkbox or selected-id
  state was added.
- [ ] Default-filter output is labelled as a locating query and explicitly says
  it may include junk/review, any session verdict, and items still suppressed
  by an active persisted veto. It never applies `keptItems`, or implies the set
  is approved junk or safe to bulk-tag.
- [ ] The implementation calls exported `dimIdQueryChunks` and
  `DIM_QUERY_SAVEABLE_MAX` unchanged. No duplicate regex, builder, length
  constant, truncation, id parsing, numeric ordering, quoting, or labels enter
  the expression.
- [ ] Invalid included weapon ids fail atomically with exact local error copy;
  non-weapon items never enter the query; 77 maximum-width ids render two
  complete chunks with every source id once and in order.
- [ ] The boot-time Cross-check path creates stable empty render targets and an
  empty `role="status" aria-live="polite"` count node before state/view reads or
  text assignment. Query text is populated only after state/view exist.
- [ ] `renderSummary` is the single live-query refresh hook reached by
  query/search changes, Reset filters, `adopt`, and `setSurface`; `renderList`
  does not render the query. There is no Generate button, membership signature,
  clear status, or activation/persistence state.
- [ ] Membership and chunks are recomputed before every render-key comparison.
  Identical output retains `<details>` and textarea node identity, open state,
  focus, and selection; changed output appears immediately while retaining the
  established open/closed choice. The first non-empty render is collapsed.
- [ ] The query subsection is hidden on idle and Armor duplicates, while #148's
  static panel remains governed by its existing idle-only rule. Returning to
  Proposals must show a query recomputed from current state.
- [ ] Finalised/disconnected frozen reports can render locally. No fetch,
  endpoint, clipboard, navigation, session mutation, verdict/revision,
  persistence, `mutationInFlight`, row-registry, tag, note, or item change occurs.
- [ ] The dynamic subsection is inside the existing Cross-check in DIM panel,
  while the three #148 static strings and their current copy/fallback behavior
  are byte-for-byte unchanged.
- [ ] Read-only textareas have labels and `spellcheck="false"`; exact empty,
  warning, split, and error copy matches the plan; keyboard focus
  and 390px document containment pass in packaged Chromium.
- [ ] No Python, fixture, golden, rule, version, session/schema, dependency, CSP,
  server endpoint, or tracked `data/` change appears in the diff.
- [ ] Ruff, full pytest, required Chromium, diff check, clean status, and
  no-tracked-data checks pass; README, browser verification, and WORKLOG match
  actual behavior and actual provider/model/effort.

# Dispatch comment draft

Planned #150 in [handoffs/issue-150-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-150-implementation-plan.md) on `main`.

- **Scope decision:** one live query for the weapon proposals matching the current Proposals filters; no Generate button or new checkbox/selection state. Use the Session verdict filter for an approved-only subset.
- **Implementer tier & effort:** Google `gemini-3.8-flash`, native `thinking_level = high`
- **Implementation branch:** `feat/issue-150-shown-weapon-dim-query`
- **Recommended review path:** independent adversarial review — the output is local/presentation-only but directly actionable in DIM, so hidden, mixed-kind, or out-of-date membership needs independent proof.
- **Likely findings:** membership bypasses `filterItems`, `keptItems` silently removes saved vetoes, or non-weapons leak in; live rendering is attached to `renderList` instead of `renderSummary` or needlessly replaces unchanged DOM; #117's builder is copied or truncated; locating-only output gains misleading copy or hidden clipboard/network/mutation effects.
