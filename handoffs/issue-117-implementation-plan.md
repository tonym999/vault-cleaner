# Issue #117 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#117 — Copy a duplicate group's instance ids as a DIM search query`

**Milestone:** `None — intentionally unassigned; this is an interop follow-up rather than M9 presentation work`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `gemini-3.8-flash`, native `thinking_level = high` (justified below)

**Plan baseline:** `main` at `3cc6fa32530a0b1cd6366c4ccc109af20b2cf511` (2026-09-05)

**Allocated implementation branch:** `feat/issue-117-dim-search-query`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Add two local, generation-only controls to **each individual rendered armour
duplicate group card**:

1. generate DIM `id:` search text for the **whole group**; or
2. generate DIM `id:` search text for the group's existing **junk candidates**.

“Whole group” is strictly local to the card whose button was activated. For
example, activating it on one Feropotent Bond same-stat card returns every
Feropotent Bond member in that one authoritative same-stat group—not every
same-stat group in the report, not every Feropotent Bond in other groups, and
not the current filtered result set.

Both choices reveal read-only text in the page. They do not copy automatically,
change a review verdict, tag or annotate an item, call a mutation endpoint,
persist state, or perform an action in DIM. The whole-group option deliberately
includes the preferred survivor when the group has one, so its warning must make
clear that it is a locating/comparison query and must not be bulk-tagged as junk.

## Context & Measurement

### Current vault-cleaner authority and UI seams

- The exact-group projection validates member ids as strings, member uniqueness,
  authoritative dispositions, and correlated proposals at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L330). It exposes the
  projected group fields and `preferredSurvivorId` at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L403).
- Same-stat groups intentionally have no preferred survivor. Each member may
  carry a separately correlated `currentProposalAction` from the existing
  Proposals surface at [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L434).
- Exact-group junk candidates are deliberately the exact pass's own members
  whose projected `proposalAction` is `"junk"`. This excludes a preferred
  survivor or retained member even when that row separately says it is also
  proposed junk by a later pass. Same-stat members may carry close-pass
  `proposalAction` metadata, but it is non-authoritative unless correlated to a
  current proposal decision. Their junk candidates therefore use the separately
  correlated `currentProposalAction === "junk"`. The existing predicate at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1091) admits both `junk`
  and `review`, so it is too broad for the junk-candidate query by itself.
- Verdicts are separate server-held review state, read by `verdictOf` at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L129). They are
  deliberately irrelevant to this first pass: “junk candidate” is selected
  from the applicable group-kind proposal field described above, whether that
  proposal is approved, vetoed, or unreviewed.
- Each group is one `article.armor-group` at
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1452). Both responsive
  comparison orientations exist in the DOM and call the same member-cell
  factory. The two generation controls must therefore render once at group
  level, outside both matrices, or they will be doubled and hidden controls may
  enter the tab order.
- All production DOM is created with `el`, which writes strings through
  `textContent` or text nodes at [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L743).
  Group labels and generated query text must retain that inert rendering path.
- The current browser adapter owns server transport and every mutation path;
  `mutateVerdicts` starts at
  [review_server.js](../src/vault_cleaner/ui/review_server.js#L1200). This
  feature needs no adapter callback or server transport. Keeping all generation
  inside the group view makes “no underlying record changes” mechanically
  reviewable.
- The Node suites already exercise hostile strings, opaque ids, exact/same-stat
  group projections, dual-orientation rendering, and verdict repaint in
  [test_review_ui_js.py](../tests/test_review_ui_js.py#L1111) and
  [test_server_ui_js.py](../tests/test_server_ui_js.py#L144). The packaged
  Chromium suite covers real group rendering and narrow layout at
  [test_server_browser.py](../tests/test_server_browser.py#L853).

### DIM query evidence and measured boundary

The planner inspected upstream `DestinyItemManager/DIM` at commit
[`964adf6ce554fdaac57381b2f1b35abc25ec0a97`](https://github.com/DestinyItemManager/DIM/commit/964adf6ce554fdaac57381b2f1b35abc25ec0a97)
(2026-09-01):

- DIM declares `id` as a free-form exact-string filter at
  [`advanced.ts`](https://github.com/DestinyItemManager/DIM/blob/964adf6ce554fdaac57381b2f1b35abc25ec0a97/src/app/search/items/search-filters/advanced.ts#L5-L14).
- DIM itself emits multi-item searches as ``id:${i.id}`` joined by ` or ` at
  [`ItemTriage.tsx`](https://github.com/DestinyItemManager/DIM/blob/964adf6ce554fdaac57381b2f1b35abc25ec0a97/src/app/item-triage/ItemTriage.tsx#L343-L357).
- DIM's all-`id` OR special case disables automatic history saving. Separately,
  DIM canonicalizes every valid query and marks it saveable only when that
  canonical string is non-empty and at most 2048 characters at
  [`search-filter.ts`](https://github.com/DestinyItemManager/DIM/blob/964adf6ce554fdaac57381b2f1b35abc25ec0a97/src/app/search/search-filter.ts#L245-L274).
  The 2048 figure is therefore a current **saveability boundary**, not a claim
  that longer query text is syntactically invalid. For the plan's flat,
  top-level OR of bare decimal `id:` filters, DIM's canonical form equals the
  emitted string: no parentheses or quoting are added. That equality is a
  load-bearing constraint. Query comments or embedded display labels are
  forbidden because DIM prepends canonicalized comments and their characters
  would also consume the saveability budget.

Vault-cleaner already defines a DIM instance-id shape as 1–20 decimal digits,
kept as a string and never parsed, at [review.py](../src/vault_cleaner/review.py#L52).
The CSV parser strips DIM's protective quotes but currently does not enforce
that grammar at [parse.py](../src/vault_cleaner/parse.py#L79). Because uploaded
CSV is untrusted and a generated expression must not be alterable by whitespace
or operators inside an id, the query helper must independently require
`^[0-9]{1,20}$` before interpolation. This is shape validation only: ids remain
opaque strings and are never numerically parsed or ordered.

For a 20-digit id, the first `id:` term is 23 characters and each later
` or id:` term adds 27. Exactly 76 maximum-width ids consume 2048 characters;
the 77th must begin a second complete query. Because emitted and canonical
forms are equal under the constraints above, the builder can enforce the same
boundary with JavaScript string `.length`; it appends only whole terms and
never truncates.

### Model verification and selection

Google's official Gemini documentation was rechecked on 2026-09-05. It names
the exact stable model id `gemini-3.8-flash`, supports native
`thinking_level = low | medium | high`, and does not support `minimal`. The
requested model is a good fit for this bounded browser implementation. Use
`thinking_level = high` because the whole-group query intentionally contains a
survivor, hostile CSV values must not alter syntax, and boundary completeness
needs careful negative coverage.

The orchestrator must verify its runtime can instantiate the Google model. If
not, it prepares the reusable prompt below for a human operator under the
manual cross-provider boundary and records any actual fallback.

## Dependencies and assumptions

- Issue #117 is open, labeled `enhancement`, and in project 3 at `Todo`, verified
  2026-09-05. It intentionally has no milestone. Implementation must not move
  its project state or invent a milestone.
- #117 named #113 as beneficial, not hard. That dependency is resolved: #113 is
  closed and the #119/#131 presentation work is merged on this baseline. The
  implementation targets the current dual-orientation group renderer, not the
  old prototype DOM.
- No report, snapshot, or server field is missing. The feature consumes the
  current projected group object only. No schema, Python, API, lifecycle,
  verdict, persistence, or dependency change is permitted.
- “Whole group” means every projected member in authoritative backend order.
  For an exact group this includes the preferred survivor, retained/protected
  members, junk candidates, and review candidates. For a same-stat group it
  means every comparison member; that pass has no survivor. In both cases the
  boundary is that one group object's `members` list—never `state.armorGroups`,
  the selected kind, the visible/filtered groups, or another card.
- “Junk candidates” is deliberately group-kind-specific. An exact card uses
  only that exact pass's `proposalAction === "junk"` members, structurally
  excluding the preferred survivor and retained/protected members even if a
  later pass separately proposes junk. A same-stat card uses only its members'
  correlated `currentProposalAction === "junk"` from the current report because
  uncorrelated source `proposalAction` is non-authoritative close-pass metadata.
  It does not mean all non-survivors, all editable members, all approved members,
  or all members with any proposal. Verdict state has no effect.
- Ids remain opaque strings. Generation validates the decimal DIM shape for
  query safety, then prefixes and joins the unchanged strings in group order.
  It does not parse, sort, normalize, infer, or reconstruct them.
- Output is visible read-only text only. There is no Clipboard API, DIM deep
  link, automatic copy, or hidden side effect in this first pass. The user may
  select and copy the displayed text manually.

### Acceptance-criteria disposition after owner clarification

The issue body predates the 2026-09-05 owner clarification and says browser
coverage must include an empty **approved** set and a query exceeding the length
budget. This plan records two deliberate replacements rather than silently
claiming those original words are met:

- Approval is no longer an input. The empty-approved-set criterion is
  superseded by direct DOM, adapter, and packaged-browser coverage of an
  individual group with **no junk candidates**, including the disabled button
  and exact empty-state copy.
- The 2048/2049 construction and completeness proof remain deterministic Node
  coverage. Producing 77 identical 20-digit-id armor rows through a live CSV is
  not representative browser behavior and would test backend fixture synthesis
  rather than the UI boundary. The packaged-browser test instead proves that
  the real group control renders and contains its generated textarea at 390px.
  This is an explicit test-layer substitution for the issue's browser wording,
  authorized by the owner's request for a simpler first pass; it is not a claim
  that browser overflow coverage exists.

The product scope itself is now recorded in [PLAN.md](../PLAN.md#L149). The
issue may remain unmilestoned; no project metadata change is needed merely
because the product boundary is now explicit.

## Proposed Plan & Scope

### Pure mode selection and complete query construction

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L588)

Add two exported pure helpers:

1. `armorGroupIdsForDimQuery(group, mode)`:
   - accepts only `"whole_group"` or `"junk_candidates"`;
   - accepts only `group.groupKind === "exact_duplicate"` or `"same_stat"` and
     rejects any other group kind atomically;
   - validates every selected member id against `^[0-9]{1,20}$` without numeric
     conversion;
   - returns ids in the group's existing member order;
   - for `whole_group`, includes every member;
   - for `junk_candidates`, branches explicitly on `group.groupKind`: an
     `exact_duplicate` group includes only `member.proposalAction === "junk"`,
     while a `same_stat` group includes only
     `member.currentProposalAction === "junk"`;
   - never reads verdicts, DOM text, labels, or CSS state; and
   - never accepts or traverses a report-level group collection; its only
     membership input is the one supplied `group.members` list; and
   - fails the whole generation atomically on any invalid selected id rather
     than returning a partial query.

2. `dimIdQueryChunks(ids, maxLength)`:
   - defaults to named constant `DIM_QUERY_SAVEABLE_MAX = 2048`;
   - requires `maxLength` to be a finite positive safe integer at least 4 (the
     length of the shortest complete `id:0` term), rejecting zero, negative,
     `NaN`, infinities, fractions, unsafe integers, and smaller values before
     producing output;
   - emits `id:<opaque-id> or id:<opaque-id>` chunks in input order;
   - validates ids defensively even when called directly;
   - never emits an empty chunk, partial term, label, comment, or URL encoding;
   - guarantees every chunk length is at most the chosen boundary; and
   - fails atomically if one complete term exceeds an injected test boundary.

Do not change `_validate_dim_csv` in this ticket. The query helper validates at
the outermost layer that interpolates untrusted ids into DIM syntax; broadening
CSV schema behavior would affect every pipeline and requires separate planning.

### Two inert, group-level generation controls

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1452)

Render one query-generation block between `armorGroupHeader` and
`armorGroupTable`. It contains two ordinary secondary buttons:

- **`Generate whole-group query`**
- **`Generate junk-candidates query`**

They must be separate explicit choices, not a defaulted toggle or a single
ambiguous “DIM query” action. The junk button is disabled when its selection is
empty and carries adjacent copy **`This group has no junk candidates.`**

Shared static explanation, rendered once:

> **These queries only find items in DIM. Generating or selecting the text changes no vault-cleaner verdict, tag, note, or item.**

On activation, replace any prior output for that same group with a labelled
read-only result built entirely from the projected group and pure helpers. The
label uses inert projected data:

> **DIM query for `<group.name>` · `<group.type>` · `<group.guardianClass>`**

Mode-specific text:

- Whole exact group:
  **`Whole group selected — includes the preferred survivor and every retained or protected piece. Use this to locate or compare the group; do not bulk-tag the result as junk.`**
- Whole same-stat group:
  **`Whole group selected — includes every piece in this same-stat comparison. This group has no preferred survivor.`**
- Exact-group junk candidates:
  **`Junk candidates selected — includes only pieces this exact-duplicate pass proposes as junk, regardless of review verdict.`**
- Same-stat junk candidates:
  **`Junk candidates selected — includes only pieces with an authoritative current junk proposal in this report, regardless of review verdict.`**

Render each complete chunk as a labelled read-only `<textarea>` so it remains
keyboard reachable, selectable, wrap/scroll contained, and visible without a
clipboard integration. Labels are **`DIM query N of M`**, including `1 of 1`.
When more than one chunk exists, add:

> **Split into M complete queries at DIM's current 2048-character saveability boundary. Use every query to cover this selection.**

The controls do not call `context.toggleVerdict`, `mutateVerdicts`, `fetch`, a
server endpoint, `navigator.clipboard`, or any other external API. Generated DOM
is naturally destroyed when its group is re-rendered; it is not restored or
persisted. Finalised or disconnected frozen reports may still generate text
because generation depends only on already-rendered local group data.

An invalid id is fail-closed: render no query and render a group-local
`role="status"` error with exact copy
**`Could not generate a safe DIM query for this group.`** Do not expose an
adapter callback and do not echo the rejected id into the error.

### Contained presentation

#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

Add narrowly scoped `.dim-query-*` styles for the secondary button row,
explanation/warning, labels, and read-only textareas. Preserve light/dark
contrast and visible `:focus-visible`. At 390px, query text stays inside its own
textarea without document-level horizontal overflow. Add no inline style; the
server CSP is `style-src 'self'`.

No change is expected in `review_server.js`, `review_server.html`, Python code,
CSP, packaging metadata, runtime dependencies, or server tests. The existing UI
assets are already packaged.

### Automated proof

#### [MODIFY] [test_review_ui_js.py](../tests/test_review_ui_js.py#L1111)

Add direct pure-helper and DOM tests proving:

- whole exact-group mode includes every id in backend order, including the
  preferred survivor and retained/protected members;
- whole same-stat mode includes every comparison member and invents no survivor;
- junk mode branches on both supported `groupKind` values: exact uses only
  `proposalAction === "junk"`, while same-stat uses only
  `currentProposalAction === "junk"`; a retained exact member with an external
  later junk proposal is excluded from the exact card, the same-stat card may
  include a correlated current junk proposal, and approved/vetoed/unreviewed
  state cannot influence either selection;
- an unknown group kind or query mode rejects atomically;
- ids are unchanged strings, never parsed or numerically ordered;
- whitespace, operators, punctuation, empty ids, over-20-digit ids, and
  prototype-shaped non-DIM ids cause atomic rejection with no partial query;
- 76 maximum-width ids produce exactly one 2048-character chunk and the 77th
  starts a second; all source ids occur once, in order, with no truncation;
- one complete term larger than an injected tiny boundary rejects atomically;
- zero, negative, `NaN`, positive/negative infinity, fractional, unsafe-integer,
  and 1–3-character `maxLength` values all reject before output;
- hostile group name/type/class values render inert and do not enter query text;
- two neighboring cards with overlapping names and different group ids remain
  isolated: activating either card emits only that card's member ids;
- exactly two generation buttons and one output block exist per group despite
  the two comparison orientations; and
- a group with no junk candidates has a disabled junk button and renders
  **`This group has no junk candidates.`** without producing an empty query; and
- clicking either button changes no verdict, calls no toggle/clear callback,
  emits no fetch/clipboard effect, and replaces only that group's prior output.

#### [MODIFY] [test_server_ui_js.py](../tests/test_server_ui_js.py#L3269)

Extend the adapter fake-DOM integration only enough to prove the controls survive
the permanent renderer boundary without becoming mutations:

- mixed exact/same-stat rendering gets two buttons per group, never per member
  orientation;
- activating a same-stat Feropotent Bond-shaped card does not collect ids from
  a neighboring same-stat or exact card, even when their names match;
- whole-group output contains the exact preferred survivor id while
  junk-candidate output excludes it and review candidates;
- an empty-candidate exact group renders the disabled button and exact empty
  copy without changing adapter state;
- generating text leaves `state.verdicts`, revisions, `mutationInFlight`, fetch
  call count, and `state.duplicateRows` unchanged; and
- finalised and disconnected frozen reports can still generate the same text
  without a server request.

#### [MODIFY] [test_server_browser.py](../tests/test_server_browser.py#L853)

Add focused packaged-Chromium coverage with committed fake armour data:

1. open an exact group and generate the whole-group query;
2. assert the preferred survivor and every projected member occur once;
3. assert the warning says not to bulk-tag the result as junk;
4. generate junk candidates and assert only the existing junk proposal ids
   remain, regardless of current verdict;
5. prove no verdict button state, report/verdict revision, network request count,
   or server state changes from either generation action;
6. exercise an individual group with no junk candidates and assert the button
   is disabled with **`This group has no junk candidates.`**;
7. open a same-stat group, generate its whole-group query, and assert its warning
   says this group has no preferred survivor rather than reusing exact-group copy;
8. finalise or simulate the supported disconnected frozen state and confirm
   generation remains local; and
9. at 390px, assert no document horizontal overflow and keyboard focus reaches
   both buttons and the visible read-only textarea.

The 77-id boundary remains a deterministic Node test; do not manufacture a
77-row backend group in browser fixtures solely to reach it. This deliberate
substitution for the original issue wording is recorded under acceptance-
criteria disposition above.

#### [MODIFY] [browser-verification.md](../docs/browser-verification.md#L105)

Add an Issue #117 checklist and append measured implementation evidence for both
modes, whole-group warning, unchanged server/verdict state, frozen local use,
narrow layout, keyboard selection, and the actual required-browser result.

#### [MODIFY] [README.md](../README.md#L196)

Add one short paragraph after the verdict workflow: each duplicate group can
generate visible DIM search text for the whole group or existing junk candidates;
whole-group text includes the survivor; generation changes nothing in
vault-cleaner or DIM; the user manually selects/copies any chunks they want.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

Add a newest-first implementation entry recording both modes, exact selection
semantics, the query-safe id check, 2048 saveability chunks, the no-side-effect
proof, browser result, and unchanged rules/schema/dependencies.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- it is mechanically required to select `whole_group` or `junk_candidates`
  from the one existing projected armour group whose local button was activated,
  render complete bounded DIM `id:` query text, or verify/document that
  generation-only path;
- membership comes only from projected members and their current proposal-action
  fields, never DOM text, verdicts, inferred rank, or a new cleanup rule;
- it preserves ids as strings, validates their safe DIM decimal shape before
  interpolation, and emits each selected id unchanged and exactly once in group
  order; and
- it changes only the packaged browser assets, focused tests, README/browser
  verification, and WORKLOG—never backend records or contracts.

Worked examples:

- **IN SCOPE:** whole-group mode for `[survivor, proposed junk, retained]`
  visibly emits all three ids and the survivor warning.
- **IN SCOPE:** junk-candidate mode emits a vetoed `proposed_junk` member because
  exact-group candidacy comes from that pass's disposition, while excluding an
  approved `proposed_review` member and a retained member carrying only a later
  external junk proposal. The same-stat mode may include a correlated current
  junk proposal because correlation makes that current decision authoritative;
  uncorrelated close-pass `proposalAction` metadata alone remains excluded.
- **IN SCOPE:** 77 twenty-digit ids become two read-only complete queries, each
  at most 2048 characters, with all ids present exactly once in order.
- **OUT OF SCOPE:** approving, vetoing, unsetting, tagging, annotating, deleting,
  persisting, auto-copying, or opening DIM from either generation button.
- **OUT OF SCOPE:** naming whole-group output “junk”, omitting its survivor
  warning, or silently excluding retained/protected members from “whole group”.
- **OUT OF SCOPE:** using rendered text to find ids or labels, treating every
  editable/review member as junk, or filtering candidates by verdict.
- **OUT OF SCOPE:** generating one query for all exact groups, all same-stat
  groups, all groups matching the current filters, or all groups sharing an
  item name.
- **OUT OF SCOPE:** a server endpoint, snapshot field, schema/rules/version
  change, CSV-wide validation change, dependency, or Clipboard API integration.

### Stop conditions

Stop implementation and return to orchestrator if:

- current `main` changes the projected group/proposal contracts or renderer so
  the cited selection seams no longer exist;
- either mode requires new backend/report/snapshot data, a Python rule change,
  schema version, or `RULESET_VERSION` bump;
- upstream DIM no longer accepts the exact `id:<id> or id:<id>` form or changes
  the measured 2048 saveability boundary;
- safe query generation cannot reject non-decimal/unbounded ids atomically
  without broadening CSV parsing behavior;
- generation triggers or requires any server mutation, verdict/revision change,
  persistence, clipboard, navigation, auth/CSP weakening, or dependency;
- one group-level block cannot be rendered without duplicating controls across
  the responsive matrices; or
- required Chromium cannot run. A skipped required browser suite is not a pass.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Candidate semantics accidentally use verdicts:** Filtering to approved or
   unreviewed rows violates the owner's request. A second risk is erasing the
   deliberate kind distinction: exact uses its own `proposalAction`, while the
   same-stat card uses authoritative correlated `currentProposalAction` rather
   than uncorrelated close-pass metadata.
2. **Whole group is not actually whole:** A safety-minded implementation may
   silently exclude the survivor or retained/protected members instead of
   including them with the required warning.
3. **Group scope leaks across cards:** A helper may consume the filtered report
   collection and combine multiple groups—especially groups sharing a name—instead
   of using only the activated card's projected `members` list.
4. **Generation becomes a hidden mutation:** Reusing verdict button helpers or
   adapter state may alter `mutationInFlight`, revisions, fetch calls, or
   verdicts despite the feature needing only local text generation.
5. **Chunk test proves length but loses ids:** Every chunk can be below 2048
   while a boundary term is duplicated, omitted, reordered, or truncated.

# Reusable implementer execution prompt

Implement issue #117 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-117-implementation-plan.md
```

Read the entire handoff, issue #117, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-117-dim-search-query`; branch from latest `main` and record the base SHA;
- use Google `gemini-3.8-flash` with native `thinking_level = high`; if the runtime cannot instantiate it, stop for the repository's manual cross-provider launch rather than silently substituting;
- implement the two generation-only modes exactly: whole group and existing junk candidates; do not use review verdicts to select candidates and do not add Clipboard or mutation behavior;
- preserve the deliberate candidate distinction: exact groups use their own `proposalAction === "junk"`; same-stat groups use correlated `currentProposalAction === "junk"`;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, and `git diff --check origin/main...HEAD`;
- verify no tracked file exists under `data/` and inspect `git status --short` before committing;
- commit with `Refs #117` and no closing keyword, then push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, report the branch name, base and head SHAs, complete verification output, the no-side-effect evidence, every stop condition considered, and any deviation with justification.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**

The implementation is intentionally small and local, but its whole-group output
contains the preferred survivor and may be pasted immediately before a DIM bulk
action. Independent review should prove that both modes are labelled honestly,
that junk candidacy is not conflated with verdict state or review proposals,
that hostile ids cannot alter query syntax, and that “generation only” has no
hidden mutation or transport side effect.

The orchestrator confirms the path against the real diff and selects the
reviewer's exact provider, model ID, and native effort only after inspection. A
different family from Gemini is preferred when available.

# Review checklist

- [ ] Check 1: There are exactly two explicit group-level modes. Whole group
  includes every projected member, including survivor and retained/protected;
  exact junk candidates use only `proposalAction === "junk"`, while same-stat
  junk candidates use only correlated `currentProposalAction === "junk"`.
- [ ] Check 1a: Each control is scoped to its own card's `group.members` only.
  Same-named neighboring exact/same-stat groups and the current filtered group
  collection cannot contribute ids.
- [ ] Check 2: Verdicts do not influence either mode. Search the feature diff
  for `verdictOf`, `state.verdicts`, approve/veto/unset coupling, and reject any
  selection dependency.
- [ ] Check 3: Whole exact-group output carries the verbatim preferred-survivor
  warning and is never described as a junk query or bulk-tag instruction. The
  same-stat whole-group warning separately says that pass selects no survivor.
- [ ] Check 4: Ids stay unchanged strings, pass `^[0-9]{1,20}$` before
  interpolation, and never reach `Number`, `parseInt`, numeric sorting, DOM-text
  parsing, or partial output.
- [ ] Check 5: Syntax matches current upstream DIM; 2048 is described as the
  current canonical saveability boundary; raw length equals canonical length
  only under the enforced no-comment/no-label/bare-decimal contract. The 76/77
  test proves complete once-only ordered coverage in addition to chunk length,
  and invalid injected boundaries fail atomically.
- [ ] Check 6: Controls/output render once per group outside both matrices;
  hidden orientations add no duplicate/focusable generation controls.
- [ ] Check 7: Both buttons only replace visible local read-only text. No fetch,
  endpoint, clipboard, navigation, session mutation, `mutationInFlight`, verdict,
  revision, server state, tag, note, or persistence change occurs.
- [ ] Check 8: Labels come from projected data through text nodes; hostile group
  fields remain inert and never enter the query expression.
- [ ] Check 9: Finalised/disconnected frozen reports still generate identical
  text without a server request; output is not persisted across rerender.
- [ ] Check 10: At 390px text stays contained and both buttons plus the read-only
  textarea are keyboard reachable with visible focus. Packaged Chromium also
  covers the empty-junk state and both exact/same-stat whole-group warnings.
- [ ] Check 11: No `review_server.js`, server/API/schema/snapshot/rules/version,
  parse-wide validation, dependency, CSP, or tracked `data/` change. `PLAN.md`
  contains the presentation-only product boundary added by the planning PR.
- [ ] Check 12: Ruff, full pytest, required Chromium, and diff-check gates pass;
  README, browser verification, and WORKLOG accurately describe both modes.

# Dispatch comment draft

Planned #117 in [handoffs/issue-117-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-117-implementation-plan.md) on `main`.

**Acceptance-criteria note:** Issue criterion 6's approved-empty and browser-
overflow wording is superseded by the owner clarification; see
[Acceptance-criteria disposition](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-117-implementation-plan.md#acceptance-criteria-disposition-after-owner-clarification).

- **Implementer tier & effort:** Google `gemini-3.8-flash`, native `thinking_level = high`
- **Implementation branch:** `feat/issue-117-dim-search-query`
- **Recommended review path:** `independent adversarial review` — the orchestrator confirms against the real diff and selects the reviewer's exact model and effort at dispatch time.
- **Likely findings:** verdict state accidentally filters junk candidates; exact/same-stat candidate fields are conflated; “whole group” silently excludes survivor/protected pieces; same-named neighboring groups leak into one query; local generation touches adapter mutation state; chunk boundaries lose or duplicate an id.

**Owner clarification applied:** this first pass has two generation-only choices on each individual group card—whole group or that group's existing junk candidates. “Whole group” means only the activated card (for example, one Feropotent Bond same-stat group), never all exact groups, all same-stat groups, or all filtered groups. Both reveal read-only query text and change no underlying record. Whole exact-group output intentionally includes the survivor and carries an explicit do-not-bulk-tag-as-junk warning. Clipboard integration and approved-only filtering are out of scope.
