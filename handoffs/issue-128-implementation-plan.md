# Issue #128 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#128 — Implement responsive member-column comparison for desktop Armor duplicates`

**Milestone:** `M9 — Duplicate Review UX`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `gpt-5.6-terra` (`high`) (justified below)

**Plan baseline:** `main` at `3a9ee98b8489306b47ae56cb7bb80f0b1190325d` (2026-09-04)

**Allocated implementation branch:** `feat/issue-128-responsive-armor-matrix`

The implementer must **not** open a pull request. The implementation branch is
reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer,
independent adversarial reviewer).

## Objective

Implement a responsive orientation for each Armor-duplicates comparison: use
member rows when its available inline size cannot safely show the member-column
matrix, and member columns when it can. This preserves #113's measured 390px
comparison benefit while restoring the desktop scan pattern from before issue #119.

The planned switching rule is deliberately based on the **comparison
container's inline size**, rather than a viewport breakpoint. A desktop browser
can still give an individual group a constrained panel (or a zoomed CSS
viewport); defaulting to the row layout there is safer than forcing a clipped
column matrix.

No user-facing copy changes in this ticket: existing headings remain exactly
`"Member"`, `"Comparison"`, `"Verdict"`, `"Protection"`, and the existing
member/disposition labels. The change is orientation and semantics only.

## Context & Measurement

### Shipped baseline

- Current [`armorGroupTable`](../src/vault_cleaner/ui/review_ui.js#L1149-L1219)
  makes one table whose header is `Member`, then comparison fields, then
  `Verdict`; each member becomes one body row. Conditional same-stat fields are
  built in lines 1151–1173 and six always-present fields in lines 1175–1191.
- [`armorMemberCell`](../src/vault_cleaner/ui/review_ui.js#L1093-L1146) is the
  single registration point for `state.duplicateRows`; it registers one handle
  per rendered control cell. [`paintArmorMember`](../src/vault_cleaner/ui/review_ui.js#L1233-L1251)
  and [`setVerdictControlsDisabled`](../src/vault_cleaner/ui/review_ui.js#L973-L987)
  iterate every registered occurrence, so a dual-orientation render must retain
  all occurrences rather than pick one layout's handle.
- Current CSS gives the row table a `46rem` minimum width and member headings
  and verdict cells an `11rem` minimum
  ([`review.css`](../src/vault_cleaner/ui/review.css#L175-L185)). Its `.scroller`
  intentionally retains horizontal scrolling
  ([`review.css`](../src/vault_cleaner/ui/review.css#L118-L124)); #113's concern
  was specifically having to horizontally scroll **between members**, not every
  possible field cell.
- The original member-column table is reproducible from
  `git show fb9a435:src/vault_cleaner/ui/review_ui.js` lines 891–932. It has a
  `Comparison` row-header column, one `12rem` member-heading column per member,
  and a `Verdict` row. Its companion CSS had an `8.5rem` row-header minimum and
  `12rem` member columns. Therefore the minimum content widths are
  `8.5rem + 12rem × N`: **32.5rem** (2 members), **44.5rem** (3), and
  **56.5rem** (4). Conditional same-stat fields add rows in this orientation,
  not columns, so they do not change that horizontal calculation.
- The implementation thresholds add a 0.5rem guard for table borders/padding
  and wrapping: **33rem** (2), **45rem** (3), and **57rem** (4). At exactly or
  above its matching threshold the member-column table is active; below it,
  member rows are active. A browser without container-query support keeps the
  default row matrix, which is the safe fallback.
- The historical `46rem` `.armor-group-table` minimum must **not** leak into
  the column representation: its deliberately scoped minima are exactly
  `32.5rem`, `44.5rem`, and `56.5rem` for 2/3/4 members. Otherwise a two- or
  three-member column matrix would incorrectly overflow at its selected
  threshold.
- #113's committed decision record says the prior matrix at 390px showed one
  member and required an internal horizontal scroll to compare. It chose member
  rows ([`duplicate-review-count-design.md`](../docs/duplicate-review-count-design.md#L141-L150)).
  This plan keeps that result: a normal 390px group panel is below even the
  2-member 33rem threshold.
- Baseline verification on this checkout:

  ```text
  VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py
  8 passed in 6.24s
  ```

  The same command first failed only under the execution sandbox because its
  Chromium host process cannot create its sandbox host; it passed when run in
  the required unsandboxed verification environment. That operational detail is
  not a product failure and must not be hidden by a skipped browser run.

### Reproducible rendered probe (planning evidence)

`docs/evidence/issue-128/responsive-matrix-probe.html` is a faithful, isolated
specimen of the selected DOM/CSS budgets: the current row fallback (`46rem` /
`11rem`), the restored column budget (`8.5rem + 12rem × N`), realistic opaque
IDs, long location/badge text, both matrix shapes, and the proposed container
queries. It is intentionally planning evidence, not production UI. Reproduce
the measurements with:

```text
.venv/bin/python scripts/measure_responsive_matrix.py
```

Observed in managed Chromium on 2026-09-04 (all widths are CSS pixels):

| Probe | container | active orientation | table/document result |
| --- | ---: | --- | --- |
| 390px viewport, 4 members | 316px | rows | row scroll 786px; document 390px |
| 1440px viewport, 4 members | 1156px | columns | column scroll 1156px; document 1440px |
| 2 members, 527px / 528px container | 527 / 528px | rows / columns | boundary flips exactly; 528px column scroll is 528px |
| 3 members, 719px / 720px container | 719 / 720px | rows / columns | boundary flips exactly; 720px column scroll is 720px |
| 4 members, 911px / 912px container | 911 / 912px | rows / columns | boundary flips exactly; 912px column scroll is 912px |
| 1440px viewport, 1 or 5 members | 1156px | rows | no column matrix selected |
| 4 members at 912px, conditional absent/present | 912px | columns | 7 / 11 comparison rows; both scroll 912px |
| 720px CSS viewport, 4 members | 628px | rows | row scroll 786px; document 720px |

The final row is the zoom/reflow probe: browser zoom changes the CSS viewport
and therefore the available container inline size, rather than a separate
physical-pixel layout. A 1440px display at approximately 200% browser zoom
has the same relevant 720-CSS-pixel reflow constraint; no device-scale-factor
claim is being made. The selected container query therefore returns to rows
before the four-member `57rem` floor. The conditional-state probe verifies
that those fields add comparison **rows** (7 to 11), never inline width.

### Design selected for implementation

Render both valid table shapes from the same authoritative group and field
list, enclosed by one `.armor-matrix` container with
`container-type: inline-size` and a `data-member-count` value. CSS defaults to
the row matrix and `display: none` for the column matrix. Container queries
activate only the matching 2/3/4-member column table at `33rem`, `45rem`, or
`57rem` and hide the row matrix. A one-member group and every group with five
or more members deliberately stay in the proven row fallback at every width.

`display: none`, rather than a static `aria-hidden` attribute, is intentional:
the hidden matrix is removed from both the accessibility tree and sequential
keyboard navigation, while CSS can swap it correctly on resize without a
JavaScript aria-state race. There are no duplicated HTML `id` attributes. The
two control cells for a member are two registered presentation occurrences of
one authoritative member/verdict; `paintArmorMember` must keep both in sync.

Within the column matrix, member headings and member cells retain `12rem`
minimums, comparison row headers retain `8.5rem`, and long member metadata,
badges, and data cells use `overflow-wrap: anywhere`. This makes the stated
thresholds a layout floor rather than relying on unbounded text. The existing
scroller remains for both matrices; the row fallback therefore still allows
wide field sets to be read without making members disappear sideways.

## Dependencies and assumptions

- #113, issue #119, PR #120, and PR #126 have landed. The issue correctly refers to
  them as prior evidence/baseline, not open dependencies. The issue was amended
  on 2026-09-04 to make PR 2 implementation explicit; its initial version
  incorrectly ended at a design record.
- Current `main` is exactly the issue #119 merge `3a9ee98`; there is no later
  production change to rebase around. Re-measure from the implementer's actual
  base if `main` advances, but retain the container-size rule unless a measured
  repository change invalidates its `8.5rem + 12rem × N` inputs.
- No schema, snapshot, Python rule, server API, HTML-template, or fixture
  change is needed. Both existing group projections already supply the members,
  dispositions, conditional values, and verdict state needed by both layouts.
- The trusted group producers have no maximum cardinality. Exact grouping skips
  fewer than two members (`armor_dupes.py` lines 284–307), and same-stat
  grouping likewise skips fewer than two (`armor_close.py` lines 275–295), so
  a live 1-member group is producer-impossible. The exact untrusted snapshot
  adapter currently accepts any non-empty `members` array, while same-stat
  rejects a singleton, so a defensive singleton still must render as rows.
  There is no hard maximum: five or more members must remain rows even in a
  wide panel. That intentional bounded column design avoids inventing a
  mismatched static threshold for an unbounded group and preserves #128's
  primary comparison guarantee; a 5+ group has all members vertically visible
  instead of forcing a 68.5rem-and-growing horizontal matrix.
- The existing Node tests have layout-shaped helpers that assume a single
  table and registry indices that assume one occurrence per group. For example,
  [`test_review_ui_js.py`](../tests/test_review_ui_js.py#L1218-L1325) expects
  two cross-kind occurrences and extracts one table's column headers;
  [`test_server_ui_js.py`](../tests/test_server_ui_js.py#L2470-L2510) treats
  occurrences 0/1 as exact/same. They need deliberate adaptation, not deletion.
- `gpt-5.6-terra` with `high` effort is selected because the work is a bounded
  two-file presentation refactor plus test adaptation, but has meaningful
  semantic, responsive, and state-synchronisation edges. The repository matrix
  permits Terra at this effort, and official OpenAI documentation confirms that
  Terra supports `high` (as well as other GPT-5.6 reasoning levels):
  <https://developers.openai.com/api/docs/models/gpt-5.6-terra>. The
  orchestrator must verify its runtime can instantiate that exact model/effort
  or prepare this plan's prompt for a human-operated dispatch.

## Proposed Plan & Scope

### Shared responsive table construction

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1038-L1260)

1. Extract the current conditional-plus-always comparison-field construction
   from `armorGroupTable` into one local helper. Both orientations must consume
   the same ordered field array, preserving the exact current conditional rules
   for `Tuning Mod Slot`, `Seasonal Mod`, `Holofoil`, and `Tuning Stat`, and
   the exact user-facing labels, including `Protection`.
2. Extract/reuse one member-heading builder so the member number, opaque id,
   location, and `armorMemberLabel(group, member)` are identical in the row
   and column tables. Give it `scope="row"` in the row table and
   `scope="col"` in the column table.
3. Keep the current row-oriented table intact as the default representation:
   header row `Member` + field labels + `Verdict`; one member body row; one
   `armorMemberCell(member, group)` in that member row.
4. Add the column-oriented table: header row `Comparison` + one member heading
   per group member; one body row per shared field with its field label as a
   row header; then a `Verdict` row containing one
   `armorMemberCell(member, group)` per member. This is the prior #102 shape,
   restored with issue #119's current `Protection` wording and conditional fields.
5. Return one outer `.armor-matrix` container with `data-member-count` set to
   the actual member count and two named `.scroller` children, one for each
   orientation. Call `armorMemberCell` separately in both tables. Do not change
   `armorMemberDomIdentity`, `armorMemberCanVerdict`, verdict payloads,
   server calls, snapshot adapters, or data projection.
6. Confirm every registered occurrence is updated/disabled by the existing
   `paintArmorMember` and `setVerdictControlsDisabled` loops after a click,
   server acknowledgement, and finalization. Do not optimise by registering
   only the visible matrix: CSS resize must not make a visible table stale.

### Container-query layout and accessibility

#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css#L118-L196)

1. Make `.armor-matrix` an inline-size query container. The row matrix displays
   by default and the column matrix has `display: none` by default.
2. Add three container-query rules keyed by the outer `data-member-count`:
   `min-width: 33rem` for 2 members, `45rem` for 3, and `57rem` for 4. Each
   rule hides the row scroller and displays the matching column scroller. Do
   not substitute a `min-width` viewport media query. Do not add a generic
   `>=5` selector: 1 and 5+ remain row fallback at all container sizes.
3. Scope the column matrix's `8.5rem` comparison-header and `12rem`
   member-heading/member-cell width budgets, including their `32.5rem` /
   `44.5rem` / `56.5rem` table minima, to the column representation. Override
   rather than inherit the current `46rem` row-table floor. Keep the current
   row matrix's `46rem` table and `11rem` member budgets.
4. Ensure long text in both table shapes can break within its cell; retain
   existing badge/location wrapping and add a narrowly scoped matrix-cell
   `overflow-wrap: anywhere` rule if the current one does not cover every
   field value. Do not remove `.scroller { overflow-x: auto; }` or use
   `overflow: hidden` as a visual fix.
5. Do not add `aria-hidden` manually. The inactive matrix must be CSS
   `display: none`; tests will prove it is neither visible nor keyboard
   focusable. If the implementation requires an ARIA state beyond this, stop
   and escalate because that changes the selected design.

### Contract, Node, and live-browser regression coverage

#### [MODIFY] [test_review_ui_js.py](../tests/test_review_ui_js.py#L825-L925)

Extend the fake-DOM presentation tests to inspect both table shapes, rather
than silently taking the first table. Assert, for exact and same-stat groups:

- row semantics: `Member`/field/`Verdict` column headers and one member per
  body row;
- column semantics: `Comparison` plus member column headers, field row headers,
  and a `Verdict` row;
- same ordered member values, `Protection` wording, conditional-field presence
  and absence, hostile-text inertness, and no change in labels;
- each proposed member has two registered control occurrences **per group**;
  a toggle/paint/disable operation updates both orientations, while read-only
  members remain button-free in both.

Update existing `duplicateRows` expectation/index logic to select occurrences
by both group kind and matrix representation instead of relying on array order.

#### [MODIFY] [test_server_ui_js.py](../tests/test_server_ui_js.py#L1842-L1872)

Keep the adapter contract tests, but make their duplicate-control scenarios
assert every matching duplicate occurrence is disabled and receives the
acknowledged `aria-pressed` state after the server response/finalization. The
cross-kind test near lines 2470–2510 must distinguish group-kind occurrences
from the second orientation rather than assuming only two handles exist.

#### [MODIFY] [test_server_browser.py](../tests/test_server_browser.py#L364-L591)

Replace the existing one-layout assertions with load-bearing live-server tests:

1. **390px × 844px:** assert the row matrix alone is visible, it contains all
   group members as rows, the column matrix is `display: none`, the document
   has no horizontal overflow, and a visible member control can be reached and
   used. Do not count hidden duplicate controls as visible controls.
2. **Fitting desktop:** at 1440px, assert a four-member same-stat group exposes
   only the column matrix, with `Comparison`, all member headings, conditional
   fields, and a `Verdict` row. Toggle a visible verdict then assert its active
   counterpart and the Proposals surface show the acknowledged state.
3. **Constrained desktop fallback and boundaries:** keep a desktop viewport,
   constrain the `.armor-matrix` inline size just below `57rem`, assert the
   row matrix is active, then make it at least `57rem` and assert the column
   matrix is active. This proves the rule follows available panel width rather
   than viewport width. Add a 2-member check around `33rem` when using the
   existing two-member fixture; do not fake a four-member group's
   `data-member-count` to claim the 2-member threshold. Add a genuine
   three-member group around `45rem`: build test-owned temporary fake input by
   retaining exactly three members from the existing fake four-member group,
   run it through the real review server, and assert rows at `719px` then
   columns at `720px`. Do not set or mutate `data-member-count` to simulate
   either transition.
4. Exercise exact and same-stat projections, 2-, 3-, and 4-member inputs,
   conditional present/absent fields, a long badge/id/location case, and both
   light/dark themes. Scope badge-width checks to the visible orientation; a
   hidden node with a zero layout width is not evidence of wrapping.
5. Assert a hidden matrix's controls are not visible or focusable and only
   one orientation's controls are in the visible keyboard scan. Preserve the
   existing singleton `#vc-duplicate-scope` node/identity assertion so the
   layout work does not duplicate live-region announcements.
6. Add a direct Node rendering test for the defensive exact singleton and a
   five-member group. Assert both expose `data-member-count` but neither can
   match a column-query selector. Add a live browser case by building a
   test-owned temporary five-member fake CSV from existing fake data (new fake
   opaque id only; do not add a tracked fixture or use `data/`) and assert a
   wide container still exposes rows alone. This prevents a future `>=5`
   selector from activating a 2/3/4 threshold by mistake.

The planning PR adds only the reproducible evidence specimen/measurement
script above. The implementation PR adds no files or fixtures unless a
test-owned temporary fixture is needed at runtime. In particular, do not
change report snapshots, tracked fixtures, server HTML/JS, Python code,
config, dependencies, or documentation outside the mandatory `WORKLOG.md`
entry.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- it changes only the Armor-duplicates presentation or its browser/Node tests;
- it renders or styles one of the two specified semantic table orientations,
  their container-size switch, their existing field/member/control values, or
  verification of those behaviors; and
- it preserves the existing snapshot/server contracts, verdict semantics,
  opaque identifiers, conditional fields, and review-session lifecycle.

Worked examples:

- **IN SCOPE:** extract the field list so rows and columns cannot diverge;
  add a `57rem` four-member container query; change a Playwright locator from
  all `button.approve` nodes to visible active-matrix controls; assert both
  registered control cells repaint after a verdict.
- **IN SCOPE:** add narrowly scoped `overflow-wrap: anywhere` to a matrix data
  cell so a long protection reason cannot invalidate a measured threshold.
- **OUT OF SCOPE:** change duplicate grouping/ranking, member dispositions,
  verdict endpoint payloads, snapshot versions, or `RULESET_VERSION`.
- **OUT OF SCOPE:** collapse mobile summary tiles, add group bulk controls,
  expose scores, add a DIM query, change user-facing copy, or refactor
  unrelated CSS.

### Stop conditions

Stop implementation and return to orchestrator if:

- a correct implementation requires a snapshot/server/HTML contract change,
  a new runtime dependency, a verdict lifecycle change, or any Python rule
  modification;
- the measured `33rem`/`45rem`/`57rem` rules do not fit with the current
  `8.5rem`/`12rem` budgets after the specified wrapping rules, or need a
  per-content JavaScript measurement/ARIA-state mechanism rather than the
  selected CSS container-query design;
- a 5+ member group cannot safely retain the explicit row fallback, or the
  authoritative producers acquire a cardinality constraint that makes this
  plan's singleton/5+ assumptions stale;
- browser support for the required container query is unavailable in the
  repository's managed Chromium, or the required browser command is skipped or
  cannot be made to run; or
- an existing cross-kind/control test reveals that dual rendering would merge
  distinct authoritative members or submit a layout-derived verdict.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Hidden-orientation controls create false-positive tests:** rendering both
   tables doubles `armorMemberCell` occurrences. Existing count/index locators
   can silently test a hidden node or the wrong group. Review must require
   visible-matrix locators and prove all registered occurrences repaint.
2. **A viewport breakpoint masquerades as responsive fit:** a 1440px page with
   a constrained group would pass a desktop-only test while still clipping a
   four-member matrix. Review must exercise just-below/at `57rem` container
   sizes within the same desktop viewport.
3. **Field parity drifts between the two builders:** duplicating the old table
   can lose issue #119's conditional `Seasonal Mod`/`Holofoil`/`Tuning Stat` logic or
   restore the stale `Hard protection` label. Review must compare row and
   column field lists for present and absent conditional states.
4. **Badge/focus accessibility assertions pass by construction:** a hidden
   element has zero rendered width and a `display:none` control cannot prove
   active keyboard order. Review must scope width checks to the visible matrix
   and use actual active/visible controls for focus and interaction.
5. **An unbounded group activates a borrowed threshold:** a broad selector
   such as `[data-member-count]`, `:not([data-member-count="1"])`, or an
   accidental `>=5` rule can show five members at the four-member `57rem`
   threshold. Review must inspect all selectors and run the Node plus live
   five-member fallback checks; singleton input must also remain rows.

# Reusable implementer execution prompt

Implement issue #128 in `tonym999/vault-cleaner` using the committed handoff on
`main` at:

```text
handoffs/issue-128-implementation-plan.md
```

Read the entire handoff, issue #128, `AGENTS.md`, `PLAN.md`, recent
`WORKLOG.md`, and current relevant code before editing.

Rules:

- work on `feat/issue-128-responsive-armor-matrix`; branch from latest `main`
  and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- preserve the selected default-row/container-query column design and its
  `33rem`/`45rem`/`57rem` thresholds for exactly 2/3/4 members (1 and 5+ stay
  rows) unless a stated stop condition occurs;
- update `WORKLOG.md` with a dated entry;
- run all verification commands:

  ```text
  .venv/bin/ruff check src tests scripts
  .venv/bin/pytest -q
  VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py
  git diff --check origin/main...HEAD
  test -z "$(git ls-files data/)"
  git status --short
  ```

- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the
orchestrator with the exact conflict; do not broaden scope.

When complete, provide the full implementer → orchestrator handoff: branch,
base/head SHAs, every changed file and purpose, exact command outputs, the
implemented container thresholds/orientations, test evidence for each likely
finding, and any residual risks.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**

The change is presentation-only, but it introduces two simultaneous semantic
table/control trees for every group and relies on CSS container queries for the
correct accessibility and interaction surface. A regression can leave visible
controls stale, accidentally expose duplicate controls to assistive technology,
or pass layout tests against hidden zero-width nodes. This is comparable to the
DOM transposition/review history of issue #119 and merits a fresh complete-diff
review.

The orchestrator confirms the path against the real diff and, when adversarial
review is required, selects and records the reviewer's exact provider, model
ID, and native effort at dispatch time.

# Review checklist

- [ ] Diff stays within `review_ui.js`, `review.css`, the named Node/browser
  tests, and the required `WORKLOG.md` entry; no server/Python/snapshot/config
  contract or runtime dependency changes.
- [ ] Both tables draw from one ordered field helper and preserve every current
  conditional field, `Protection` label, member order, opaque id, disposition,
  read-only behavior, and verdict payload.
- [ ] Row is the no-container-query/narrow fallback; the exact 2/3/4-member
  `33rem`/`45rem`/`57rem` rules activate columns only where the corresponding
  `8.5rem + 12rem × N` matrix fits, override the old 46rem column floor, and
  never activate columns for a defensive singleton or 5+ group.
- [ ] Browser tests prove 390px rows, fitting desktop columns, constrained
  desktop rows, genuine 2/3/4 threshold transitions, 5+ wide-container rows,
  no document overflow, both color schemes, and actual visible/focusable
  controls—not hidden-node geometry.
- [ ] Node and adapter tests prove every duplicate occurrence (both
  orientations and both group kinds) repaints/disables on acknowledgement and
  finalization; existing cross-kind identities remain distinct.
- [ ] The browser command runs with `VAULT_CLEANER_BROWSER_REQUIRED=1` and is
  not skipped; the adversarial reviewer independently reruns it and every
  repository gate from a disposable checkout.

# Dispatch comment draft

Planned #128 in [handoffs/issue-128-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-128-implementation-plan.md) on `main`.

- **Implementer tier & effort:** `gpt-5.6-terra` (`high`)
- **Implementation branch:** `feat/issue-128-responsive-armor-matrix`
- **Likely findings:** hidden duplicate control occurrences, panel-size versus viewport breakpoint behavior, row/column conditional-field parity, non-load-bearing hidden-node accessibility assertions, and an unbounded group accidentally borrowing a 2/3/4-member threshold.
