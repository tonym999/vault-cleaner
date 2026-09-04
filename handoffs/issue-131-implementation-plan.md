# Issue #131 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#131 — M9: implement #102 Armor duplicates visual design fidelity`

**Milestone:** `M9 — Duplicate Review UX`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `claude-sonnet-5` with native effort `xhigh` (justified below)

**Plan baseline:** `main` at `2ea5744253947868e2702e9cb560a12d37341ff9` (2026-09-04)

**Allocated implementation branch:** `feat/issue-131-armor-duplicates-design-fidelity`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Bring the permanent **Armor duplicates** review surface into faithful visual and
organizing alignment with the agreed #102 design, using the payload, counts,
accessibility and verdict semantics already delivered by #101, #102, #104, #110,
#113 and #119.

This is presentation and interaction work only. No Python rule, grouping key,
ranking, survivor selection, close-pass behavior, note, tag, threshold, report or
snapshot schema, `RULESET_VERSION`, server lifecycle, auth, persistence, or
revision/verdict validation changes.

The design source of truth is the #102 agreed artifact
(`https://claude.ai/code/artifact/8f1266ab-46b8-4be4-90af-22f16b9c7d4b`,
titled *Armor Duplicates Mockup*). Its public frame is the complete design
reference; its document notes below the frame are commentary, not specification.
Two elements in that frame are explicitly excluded by #131 and must not be built:
the structured `▸ decided` winner marker (`.mx-c.win::after`) and the amber
"Health tuning, flagged as low-value for PvE" legend/`.mx-c.avoid` treatment.

## Context & Measurement

All measurements below were taken on the plan baseline SHA in this environment
on 2026-09-04. Chromium launches here: the required browser suite runs, it does
not skip.

### Baseline verification state

```text
.venv/bin/ruff check src tests scripts                 -> All checks passed!
.venv/bin/pytest -q                                    -> 953 passed in 26.93s
VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q \
  -m browser tests/test_server_browser.py              -> 8 passed in 6.02s
```

`.venv/bin/python` reports **3.14.4** while [AGENTS.md](../AGENTS.md) states
Python 3.12. The whole suite is green on 3.14.4, so this is a documented
environment observation, not a blocker, and **is not in scope to change**.

### Current surface — what exists today

| Concern | Current implementation | File |
|---|---|---|
| Surface navigation | `Review surface` label + two `button` elements with `aria-pressed`, ids `vc-view-proposals` / `vc-view-duplicates`, no counts | [review_server.js](../src/vault_cleaner/ui/review_server.js#L639-L663) |
| Group-kind control | `All` / `Exact` / `Same stats` buttons with `aria-pressed`, rendered only for mixed kinds, no counts | [review_server.js](../src/vault_cleaner/ui/review_server.js#L900-L930) |
| Filters | search + `guardianClass`, `type`, `itemArchetype`, `tuningModSlot` selects + reset, in the shared `#vc-controls` host | [review_server.js](../src/vault_cleaner/ui/review_server.js#L933-L971) |
| Scoped summary | single `#vc-duplicate-scope`, `role="status"`, `aria-live="polite"`, updated in place | [review_server.html](../src/vault_cleaner/ui/review_server.html#L72), [review_server.js](../src/vault_cleaner/ui/review_server.js#L262-L288) |
| Sections | none — one flat list of `article.armor-group`, exact groups first then same-stat | [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L588-L592) |
| Group header | piece-count chip, `h3` name, kind sub-line, then a **tile row** of Type/slot, Guardian class, Tier, Hash, Archetype, Tuning Mod Slot | [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1047-L1091) |
| Stats | `armorStatDisplay` tier-5 model, rendered as **tiles** plus the sentence `The other three base stats are 0 on this tier-5 piece.` | [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L653-L677), [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1048-L1051) |
| Tuning presentation | exact: a tile. same-stat: a `p.hint` banner with the settled two-part copy | [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1057-L1069) |
| Comparison | **one table, members as rows, axes as columns**, every axis always rendered, inside `.scroller { overflow-x: auto }` | [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1149-L1220) |
| Verdict cells | `armorMemberCell` registers each cell in `state.duplicateRows[member.id]`; `paintArmorMember` repaints every registered occurrence | [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1093-L1147), [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1233-L1252) |

The current comparison is therefore the **transpose** of the artifact. The
artifact's matrix is axes-as-rows, members-as-columns, and shows a row only for
an axis on which members actually differ.

### Measured layout budget (production server, real fixtures)

Measured by uploading the committed fake fixtures into the packaged server and
reading live geometry. `1rem = 16px` (root font-size 16).

| Fixture | Viewport | `.armor-group` clientWidth | comparison content box | current table scrollWidth | document scrollWidth |
|---|---|---|---|---|---|
| `armor_duplicates_ui.csv` (exact, 3 pieces) | 1440×1000 | 1180px | **1156px (72.25rem)** | 1156px | 1440 |
| `armor_duplicates_ui.csv` | 1024×900 | 956px | **932px (58.25rem)** | 932px | 1024 |
| `armor_duplicates_ui.csv` | 390×844 | 335px | **316px (19.75rem)** | 878px (contained scroll) | 390 |
| `armor_same_stat_four_ui.csv` (same-stat, 4 pieces) | 1440×1000 | 1180px | 1156px | 1156px | 1440 |
| `armor_same_stat_four_ui.csv` | 1024×900 | 956px | 932px | 1010px (contained scroll) | 1024 |
| `armor_same_stat_four_ui.csv` | 390×844 | 335px | 316px | 1010px (contained scroll) | 390 |

Fixed budgets already in CSS: `.armor-group-table { min-width: 46rem }` (measured
736px), `.armor-member-heading { min-width: 11rem }` (measured 176px),
`.armor-member-cell { min-width: 11rem }`
([review.css](../src/vault_cleaner/ui/review.css#L176-L182)). `.armor-group`
padding is `.75rem` (12px) desktop, `.6rem` (9.6px) at ≤640px.

**Consequences the implementation must respect:**

- A member-column matrix fits comfortably at 1440px (72.25rem of content box)
  for realistic member counts, does **not** fit for four members at 1024px, and
  cannot fit at 390px. A width-driven switch is therefore genuinely required —
  it is not a cosmetic preference.
- The switch must be driven by the **comparison's own available inline size**,
  not the viewport, because the panel width is what actually varies (zoom,
  narrow windows, and the ≤640px padding change all move it).
- The existing `min-width: 46rem` on the row table is larger than the 2-member
  column threshold and would invalidate any smaller threshold if inherited by
  the column table. The column table needs its own minima.

### #113 narrow evidence (already in the repository)

`docs/evidence/issue-113/narrow-390-specimens.html` and
`scripts/measure_narrow_specimens.py` establish the repository's method for a
narrow claim: measure the component at the width it will really have, with no
enclosing chrome and no authoring-only constraints, and assert preconditions
before reporting. The 390px production panel width there is **370.8px**
(`390 − 2 × 9.6`), consistent with the 335px/316px figures measured above once
`.armor-group`'s own border and padding are taken. #131 must produce equivalent
measured evidence for its orientation switch.

### Test coupling that will break (measured, not guessed)

- [tests/test_server_browser.py:400-406](../tests/test_server_browser.py#L400-L406)
  asserts the **current** orientation for a four-member same-stat group
  (`tbody tr` count 4, `th[scope='col']` named `Member` / `Tuning Mod Slot` /
  `Protection` / `Verdict`). This assertion must be inverted for the fitting
  desktop case and kept for the narrow fallback.
- [tests/test_review_ui_js.py:1324-1325](../tests/test_review_ui_js.py#L1324-L1325)
  asserts `count(exactArticle, BUTTON) === 3` and `count(sameArticle, BUTTON) === 3`.
  Rendering two orientations doubles button occurrences.
- [tests/test_review_ui_js.py:1355](../tests/test_review_ui_js.py#L1355)
  asserts `exactArticle.children[0].children[0].textContent === "2 pieces"` — a
  **positional** header assertion that any header restructure breaks. Replace it
  with a class-scoped selector, not a re-indexed position.
- [tests/test_review_ui_js.py:1341-1342](../tests/test_review_ui_js.py#L1341-L1342)
  asserts `exactArticle.textContent.indexOf("_") === -1` — no underscore anywhere
  in an exact group's text. All new copy must honour that.
- [tests/test_server_ui_js.py:1860-1864](../tests/test_server_ui_js.py#L1860-L1864)
  and [tests/test_server_ui_js.py:2478](../tests/test_server_ui_js.py#L2478)
  index `state.duplicateRows[id][0]` positionally. With two orientations, `[0]`
  may be the hidden one; these must assert across **every** registered occurrence.
- [tests/test_server_browser.py:517-537](../tests/test_server_browser.py#L517-L537)
  pins `#vc-duplicate-scope` to parent `#vc-duplicates` and proves it is updated
  in place rather than destroyed. **Do not move that element.**

### Settled copy that must not churn

- Same-stat banner (settled by #113/#119 review):
  `Base stats match but tuning differs, so this pass selects no survivor.`
  plus, only when a member carries a proposal,
  ` Pieces below that already carry a proposal keep their verdict controls.`
- Group kind sub-lines: `Exact` and `Same stats · review only`
  (#118 retired `Exact duplicate group`; #119 settled the pair).
- Scope summary strings produced by `duplicateScopeText`
  ([review_server.js](../src/vault_cleaner/ui/review_server.js#L262-L288)).
- Row/facet labels `Protection`, `Tuning Mod Slot`, `Masterwork Tier`, `Power`,
  `In loadout`, `Equipped`, `Locked`, `Verdict`.

## Dependencies and assumptions

- **#102, #110, #113, #119 are delivered references, not open dependencies.**
  Verified: all four are `Done` on the project board and closed. No GitHub
  dependency link is required.
- **#128 / PR #130 are closed wrong-scope history.** They are **not** design
  authority and must not be reopened, cited, or reused. Their handoff, probe and
  probe runner were removed from the repository
  (`docs/evidence/issue-128/`, `scripts/measure_responsive_matrix.py` do not
  exist on the baseline). The [WORKLOG.md](../WORKLOG.md) entries about them
  remain as an audit trail only. Every number in this plan was re-measured on
  the baseline SHA; nothing is inherited from that history.
- **Issue body vs. code state:** no staleness found. Every fidelity gap the issue
  describes is real on the baseline, and every "already delivered" fact it relies
  on (authoritative group payload, #113 scoped summary, #119 counts and banner
  copy, per-piece proposal controls on same-stat groups) is present.
- The artifact is readable and unambiguous; there is no second plausible design
  source. Where its illustrative content conflicts with #131's constraints,
  #131 wins.
- `container-type` / `@container` inline-size queries are used. The required
  verification browser is the managed Chromium already used by
  `tests/test_server_browser.py`, which supports them. The **default** (no
  container query support) must be the row orientation, so an unsupporting
  browser degrades to today's behavior.
- No new runtime dependency. Runtime deps remain pandas and Flask 3.1.

## Proposed Plan & Scope

### 1. Surface navigation — artifact tabs with counts

#### [MODIFY] [review_server.html](../src/vault_cleaner/ui/review_server.html#L61-L62)
#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L639-L663)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css#L88-L90)

- Restyle `#vc-view-selector` as the artifact's compact tab strip
  (`.tabs` / `.tab`: bottom rule on the strip, selected tab raised on
  `var(--panel)` with a matching border and `font-weight: 600`, unselected in
  `var(--muted)`).
- Add a monospace count chip inside each button:
  `Proposals` + total proposal items; `Armor duplicates` + total authoritative
  groups. Both are **unfiltered totals** for the whole report.
- **Keep the existing `button` + `aria-pressed` semantics and the existing ids.**
  Do not introduce `role="tablist"` / `role="tab"` / `aria-selected`: real tab
  semantics additionally require `aria-controls`, `role="tabpanel"`, roving
  `tabindex`, and arrow/Home/End key handling, and a partial implementation is
  less accessible than the working toggle group that exists today. The issue asks
  for the artifact's compact tab **styling** and an accessible selected state;
  `aria-pressed` already provides the latter and is already covered by tests.
- Because a count in visible text is hidden from assistive technology by the
  existing `aria-label`, update those labels to carry it:
  `Proposals (41 proposals)` / `Proposals (1 proposal)`,
  `Armor duplicates (7 groups)` / `Armor duplicates (1 group)`, and retain the
  existing disabled label `Armor duplicates (no duplicate groups)` verbatim.
- The counts must not be announced by any live region. The single live-region
  announcement for this surface stays `#vc-duplicate-scope`.

### 2. Group-kind control — segmented, with counts

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L900-L930)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

- Restyle `#vc-dup-kind-selector` as the artifact's segmented control
  (`.segbtns` / `.segb`: one bordered pill, hairline separators between
  segments, pressed segment on `var(--bg)` with `box-shadow: inset 0 -2px 0
  var(--accent)` and `font-weight: 600`).
- Add per-segment counts from the current report:
  `All <total groups>`, `Exact <exact groups>`, `Same stats <same-stat groups>`,
  rendered in a `span.n`. Extend each button's `aria-label` the same way as the
  tabs so the count is exposed, e.g. `Exact (5 groups)`.
- Keep the `Show` label, the existing button ids, `aria-pressed` state, the
  mixed-kinds-only render condition, and the existing filter reconciliation.
- Keep the existing hint sentence, or add the artifact's
  `Picks which kinds are shown. The filters below pick which groups.` — one
  sentence only, no second count line.

### 3. Filter panel — artifact hierarchy

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L933-L971)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

- Present the duplicate filters as the artifact's `.filters` card: a bordered
  panel with a wrapping `.fgrid` row of labelled controls in the artifact order —
  **Search name or instance id, Class, Slot, Archetype, Tuning Mod Slot** —
  followed by the reset control.
- Keep every existing id, option text (including the `(N groups)` / `(N pieces)`
  suffixes), change handler, and reconciliation behavior.
- **Do not** render the artifact's `Showing 3 of 7 groups …` note. That number
  already exists exactly once as `#vc-duplicate-scope`. Style that existing
  element as the artifact's filter note and add
  ` Filters select whole groups — a group shows in full or not at all.` as
  **static** hint text elsewhere in the panel if desired, never as part of the
  live-region text.
- `#vc-duplicate-scope` keeps its id, parent (`#vc-duplicates`), `role="status"`,
  `aria-live="polite"`, and in-place update. Do not move it into `#vc-filters`.

### 4. Sections — Exact duplicates / Same stats, different tuning

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L1037-L1054) (duplicate list render)
#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1229-L1231) (`armorGroups`)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

- Render the filtered groups under two text-labelled section headings, exact
  first, preserving backend order within each kind:

  | Heading (`h3`) | Rule line (verbatim) |
  |---|---|
  | `Exact duplicates` | `Same archetype, same stats, same tuning — one copy survives` |
  | `Same stats, different tuning` | `Review only — the tool never picks your tuning for you` |

- A section heading renders only when that kind has at least one group in the
  current filtered result. The distinction must be carried by text, never by
  color alone.
- **Keep** the existing per-group kind sub-line (`Exact` / `Same stats · review
  only`). It is delivered copy that #110's and #118's acceptance checks and the
  Node tests depend on; the artifact's header omits it only because its own
  section heading is the sole label. Retaining both is a deliberate, recorded
  deviation from the artifact.
- Empty filtered result keeps whatever the current implementation renders; do not
  invent a new empty state.

### 5. Group header — scan-first hierarchy

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1047-L1091) (`armorGroupHeader`)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css#L151-L185)

Replace the `.armor-group-meta` tile row with the artifact's single wrapping
header line, in this order:

1. item name (`h3`, `overflow-wrap: anywhere` retained);
2. **archetype badge** — `span.badge.arch`, text-labelled, containing the
   `item_archetype` value, or `none/unknown` when absent. Colour is decoration
   only; the value is the text;
3. type / slot;
4. guardian class;
5. tier;
6. hash;
7. **piece count**, kept prominent, keeping the existing
   `p.armor-group-pieces` element, class and `N piece` / `N pieces` copy.

Rules:

- Every value stays inert text via the existing `el()` / `textContent` path.
  Long and hostile values must still wrap (`overflow-wrap: anywhere`) and must
  not force document-level horizontal overflow at any tested width.
- Keep Spirit signature, Seasonal Mod and Holofoil exactly as today
  (same conditions, same labels, same values) — restyled from tiles to labelled
  inline text is allowed; inventing or dropping fields is not.
- Do not add any payload field that does not already exist.

### 6. Stat spike — 30 / 25 / 20

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1048-L1051)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

- Replace the `.armor-stat-summary` tiles with the artifact's spike block: for
  each of the three non-zero tier-5 stats render, in one `.sv` column, the stat
  **name** (uppercase mono label), the **value**, a proportional **bar**
  (`30 → 100%`, `25 → 83%`, `20 → 67%` of the column width, opacity stepping
  `1 / .72 / .46`) and the **role** label (`primary`, `secondary`, `tertiary`).
- The bar is redundant decoration: the value and role are always text.
- Replace the zero-stat sentence with the artifact's muted summary naming the
  zero stats: the three zero stat names joined by ` · `, followed by ` · 0 base`.
  Example: `Health · Class · Grenade · 0 base`.
- The non-tier-5 fallback in `armorStatDisplay`
  ([review_ui.js](../src/vault_cleaner/ui/review_ui.js#L653-L677)) stays honest:
  keep listing all supplied stats with no role labels, no bars and no zero
  summary. Do not "fix" empty or unexpected stat shapes.
- `armorStatDisplay`'s detection logic is not changed by this ticket.

### 7. Tuning banners — always visible, always labelled

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1057-L1084)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

- **Exact groups:** replace the Tuning Mod Slot tile with an always-visible
  banner styled as the artifact's `.tuneline` (accent left rule), containing the
  uppercase label `Tuning Mod Slot`, the value, and the suffix
  ` — identical across all <N> pieces, and part of why they are one group.`
  When `N` is 1, use ` — the only piece in this group.` instead.
- **Same-stat groups:** promote the existing `p.hint` banner to the artifact's
  `.tuneline.warn` treatment (review-coloured left rule on `var(--warn-bg)`),
  with the settled copy unchanged, and prefix it with the same uppercase
  `Tuning Mod Slot` label. It stays always visible; only the second sentence
  remains conditional on a member carrying a proposal.
- Both banners must be readable in light and dark, and must not rely on colour
  alone to distinguish "identical" from "differs".

### 8. Difference-only comparison, two orientations

This is the largest and highest-risk part of the ticket.

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1149-L1231) (`armorGroupTable`, `armorGroup`)
#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css#L175-L196)

**8a. One field list, difference-only rows.**

Build the candidate axis list exactly as today
([review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1149-L1188)), then split it:

- **Always rendered:** for same-stat groups, `Tuning Mod Slot` (the group's
  defining axis, and an explicit acceptance criterion); for every group, the
  `Verdict` row.
- **Conditionally rendered:** every other axis is rendered **iff** its values
  differ across the group's members, using the existing `memberValues` helper
  with the same normalizers already in use. The existing conditional same-stat
  axes (`Seasonal Mod`, `Holofoil`, `Tuning Stat`) keep their current, stricter
  conditions unchanged.
- **No information may be lost.** Every axis suppressed because it is identical
  must be restated once per group, beneath the matrix, in a muted
  `p.armor-identical-axes` line:
  `Identical across all pieces: <Label> <value> · <Label> <value> · …`,
  in the same order the axes would have appeared. This is what makes
  "rows are the differences" safe for the read-only survivor/protected context
  the issue requires be preserved.
- Filters select whole groups, so "the displayed pieces" is always every member
  of the group. Do not add member-level filtering.

**8b. Two semantic orientations, one source of truth.**

Render **both** tables from the same field list and the same
`armorMemberCell(member, group)` factory:

- `table.armor-matrix-columns` — the artifact orientation. `thead`: a corner
  `th[scope="col"]` reading `Differs on`, then one `th[scope="col"]` per member
  carrying the member number, opaque id, location and disposition badge.
  `tbody`: one `tr` per axis with `th[scope="row"]` for the axis label and one
  `td` per member; the final `tr` is the `Verdict` row of member verdict cells.
- `table.armor-matrix-rows` — the accessible fallback, i.e. today's shape:
  `thead` of `Member`, axis labels, `Verdict`; `tbody` one `tr` per member.

Both must:

- register their verdict cell in `state.duplicateRows[member.id]`, so
  `paintArmorMember` repaints **every** occurrence and a CSS-driven resize can
  never surface a stale verdict;
- preserve backend member order, opaque `Id`/`Hash` strings (never through
  `Number`), location, read-only survivor/protected context, and the existing
  Approve / Veto / Unset controls with their existing `aria-label` text;
- keep same-stat verdict controls gated on an existing correlated proposal
  (`armorMemberCanVerdict`), unchanged.

**8c. The switching rule.**

- Put `container-type: inline-size` on `article.armor-group` and set
  `data-member-count="<N>"` on it.
- Default (and any browser without container query support):
  `.armor-matrix-columns { display: none }`, `.armor-matrix-rows` shown.
- Inside `@container (min-inline-size: …)` blocks keyed by
  `[data-member-count="N"]`, swap them with `display: none` on the row table.
  `display: none` — not `visibility`, not `aria-hidden` — so the inactive
  orientation is absent from both the accessibility tree and keyboard order
  with no stale static state.
- Budget: `axis label column + N × member column + guard`. Start from the
  existing measured budgets (`.armor-member-heading` / `.armor-member-cell`
  are 11rem; the row table's `46rem` minimum must **not** be inherited by the
  column table) and derive thresholds for `N = 2..6`. `N = 1` (defensively
  possible from the untrusted adapter, producer-impossible live) and `N ≥ 7`
  always use the row orientation: one piece has nothing to compare, and seven
  columns exceed any panel width this surface gets.
- The column table needs its own `min-width`; the row table keeps `46rem`.
- **The chosen thresholds must be measured, not asserted.** The measured
  anchors this plan established are the acceptance frame: at a 1440px viewport
  the comparison content box is 1156px (72.25rem) and a member-column matrix
  must be active for 2–4 members; at 1024px it is 932px (58.25rem); at 390px it
  is 316px (19.75rem) and the row fallback must be active for every member
  count. Whatever thresholds are chosen, no width may produce document-level
  horizontal overflow, and no width may leave both orientations visible or both
  hidden.

**8d. Explicitly excluded.**

- No `decided here` marker, no `▸ decided` suffix, no deciding-rank row, and no
  browser-derived inference of which axis settled the survivor.
- No Health-tuning "low-value for PvE" colouring, legend, or demotion.
- No group-level verdict actions and no bulk controls.
- No `aria-hidden` toggling, no `tabindex="-1"` sweeping, and no JS resize
  observer: the orientation switch is CSS-only.

### 9. Measured evidence

#### [NEW] [scripts/measure_armor_matrix_orientation.py](../scripts/measure_armor_matrix_orientation.py)
#### [NEW] `docs/evidence/issue-131/orientation-measurements.md`

Following the method in
[scripts/measure_narrow_specimens.py](../scripts/measure_narrow_specimens.py),
add a Playwright script that boots the **real packaged server** (as
`tests/test_server_browser.py` does), uploads the committed fake fixtures, and
records, in CSS pixels:

- the comparison content box at each measured width;
- which orientation is active, asserting exactly one is;
- the flip point for each supported member count;
- document containment (`documentElement.scrollWidth <= viewport width`) at
  1440×1000, 1024×900 and 390×844;
- the row-count change when conditional same-stat axes are present versus absent.

The script must assert every precondition before printing a number, and must
fail rather than report if the layout it measured is not the production one.
It writes the evidence file it documents. Fake fixtures only; never `data/`.

### 10. Tests

#### [MODIFY] [tests/test_review_ui_js.py](../tests/test_review_ui_js.py)
#### [MODIFY] [tests/test_server_ui_js.py](../tests/test_server_ui_js.py)
#### [MODIFY] [tests/test_server_browser.py](../tests/test_server_browser.py)

Tests must prove behavior, not assert static CSS declarations or inline styles.

**Node coverage (adapter/DOM):**

- Difference-only rows: an axis identical across members is absent from the
  matrix **and** present in the identical-axes summary line; an axis that
  differs is present as a row. Prove both directions with one group each.
- Same-stat `Tuning Mod Slot` and the `Verdict` row are present even when the
  suppression rule would otherwise drop them.
- Conditional `Seasonal Mod` / `Holofoil` / `Tuning Stat` behaviour is unchanged.
- Both orientations exist in the DOM, are built from the same field list, and
  register **every** verdict cell: one acknowledgement repaints and disables all
  occurrences of an id, and read-only occurrences stay read-only. Replace the
  positional `state.duplicateRows[id][0]` assertions with assertions over the
  whole occurrence list.
- Hostile strings stay inert in both orientations (no `IMG`/`SCRIPT`/`B` nodes),
  in the archetype badge, the header line, the banners and the stat spike.
- Opaque ids and hashes remain strings; `__proto__`-shaped ids stay safe.
- Header/piece-count assertions move from child positions to class selectors.
- Stat spike: three labelled values with roles, and the named zero-stat summary;
  non-tier-5 fallback unchanged.
- Section headings appear per kind, exact first, and only for kinds present.
- Tab and segment counts match the authoritative totals, including singular and
  plural accessible names.

**Browser coverage (Chromium, `tests/test_server_browser.py`):**

Using `armor_duplicates_ui.csv` (exact, 3), `armor_same_stat_ui.csv`
(same-stat, 2), `armor_same_stat_four_ui.csv` (same-stat, 4) and
`armor_close.csv` (mixed), plus `weapons_hostile.csv` for inert-text coverage:

- fitting desktop panel (1440×1000): member-column orientation active, row
  orientation absent from the accessibility tree and from keyboard order
  (tab order must not reach a hidden control);
- non-fitting desktop panel and 390×844 narrow: row orientation active, no
  document horizontal overflow, all pieces comparable without member-by-member
  horizontal navigation;
- browser zoom / reflow: exercise a constrained panel width and confirm the
  orientation flips and remains contained;
- exactly one orientation visible at every tested width;
- verdict behaviour across orientations: Approve/Veto/Unset on a proposal member,
  acknowledged repaint, focus retention, finalised freeze, read-only members;
- one live-region scope announcement only, `#vc-duplicate-scope` still updated
  in place inside `#vc-duplicates`;
- section headings, archetype badge text, always-visible tuning banners, and the
  stat spike readable in **both light and dark** (assert theme-sensitive computed
  values actually change, as the existing four-member test already does);
- long/hostile strings, proposal and read-only members, and filtered states.

Update the existing four-member test at
[tests/test_server_browser.py:384](../tests/test_server_browser.py#L384) rather
than deleting it: its badge-wrapping and theme assertions stay, scoped to the
**active** orientation, and its orientation assertion is split per width.

### 11. Documentation

#### [MODIFY] [docs/browser-verification.md](../docs/browser-verification.md)
#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

- Add an `Issue #131 focused check` checklist section covering the orientation
  switch, sections, archetype badge, stat spike, tuning banners, difference-only
  rows and the identical-axes line, in both appearances and at 1440×1000,
  a constrained panel width, and 390×844.
- Record a dated run of that check with environment, viewports, fixtures and
  results — a real run, not a restatement of the checklist.
- Add a dated `WORKLOG.md` entry (newest first) recording what changed, the
  decisions made, and anything surprising for the next agent.

### Not changed by this ticket

`src/vault_cleaner/rules/**`, `report_run.py` (including `RULESET_VERSION` and
`_decision_config`), `report.py`, `review.py`, `review_session.py`,
`server/**`, `config.toml`, `PLAN.md`, snapshot schema, fixtures' contents, and
the snapshot golden. Node/adapter *projection* functions
(`exactDuplicateGroupsFromSnapshot`, `sameStatGroupsFromSnapshot`,
`matchesArmorGroup`, `filterArmorGroups`, `countArmorGroups`,
`duplicateScopeText`) are unchanged except where a count is newly **read** for
display.

## Mechanical inclusion test

A proposed change is **in scope** if and only if **all** of these hold:

- it edits only `src/vault_cleaner/ui/**`, `tests/test_review_ui_js.py`,
  `tests/test_server_ui_js.py`, `tests/test_server_browser.py`,
  `scripts/measure_armor_matrix_orientation.py`, `docs/evidence/issue-131/**`,
  `docs/browser-verification.md`, or `WORKLOG.md`; **and**
- it changes how already-authoritative data is presented, laid out, labelled or
  navigated — not what that data is, how it is grouped or ranked, or which
  member may carry a verdict; **and**
- it is traceable to a named element of the #102 artifact frame or to an explicit
  #131 acceptance criterion; **and**
- it preserves every settled copy string listed under *Settled copy that must not
  churn*, the `#vc-duplicate-scope` contract, opaque id/hash strings, and inert
  text rendering.

Worked examples:

- **IN SCOPE:** replacing the group-header tile row with the artifact's wrapping
  header line, moving the archetype into a text-labelled badge.
- **IN SCOPE:** suppressing a `Power` row because all members share a power, and
  restating `Power 2010` in the identical-axes line.
- **IN SCOPE:** adding a second `table.armor-matrix-columns` built from the same
  field list, hidden by default and activated by a container query.
- **IN SCOPE:** updating `tests/test_review_ui_js.py:1355` from a child-position
  assertion to a `.armor-group-pieces` class selector.
- **OUT OF SCOPE:** changing `_same_stat_key` to key on three stats instead of
  six (the artifact's own open question — a rules change, needs its own issue).
- **OUT OF SCOPE:** rendering the artifact's `▸ decided` marker, or deriving
  which axis settled the survivor.
- **OUT OF SCOPE:** demoting or colouring Health tuning as low-value for PvE.
- **OUT OF SCOPE:** adding a `decided_by` (or any) field to the snapshot or
  server payload, bumping `RULESET_VERSION`, or touching `rules/`.
- **OUT OF SCOPE:** group-level or bulk verdict actions; letting a same-stat
  member without an existing correlated proposal expose verdict controls.
- **OUT OF SCOPE:** adding member-level filtering, weapon duplicates, score
  projection, DIM-query copying, or the separate mobile tile-row question.
- **OUT OF SCOPE:** changing the venv's Python version or the browser test
  harness's launch strategy.

### Stop conditions

Stop implementation and return to the orchestrator if:

- a faithful rendering appears to require a new payload field, a new snapshot or
  server contract, or any change under `src/vault_cleaner/rules/`,
  `report_run.py`, `review.py` or `server/`;
- no orientation threshold can satisfy both "member columns at fitting desktop
  panel widths" and "no document overflow at 390px" without either capping
  member counts differently from this plan or changing existing member cell
  minima in a way that regresses the row fallback;
- the container query approach cannot keep the inactive orientation out of the
  accessibility tree and keyboard order in the required Chromium, or the required
  browser suite cannot be run (a skip is not a pass);
- honouring the artifact would require changing a settled copy string, moving
  `#vc-duplicate-scope`, or introducing a second count announcement;
- suppressing identical axes would drop read-only survivor/protected context that
  the identical-axes line cannot carry;
- the diff would need to touch a file outside the inclusion test's file list.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Stale verdict in the hidden orientation.** Two rendered orientations double
   the entries in `state.duplicateRows[id]`. The likeliest defect is a repaint,
   disable, or finalise-freeze path that updates only the first occurrence — and
   tests that still index `[0]` (`tests/test_server_ui_js.py:1860`, `:2478`)
   passing anyway because `[0]` happens to be the visible one at the test width.
   Verify by asserting over every occurrence and by flipping the width between
   an acknowledgement and its assertion.
2. **Tests that assert CSS instead of behavior.** The acceptance criteria
   explicitly forbid this, and an orientation switch is the classic case: a test
   that reads `getComputedStyle(...).display` on both tables proves the stylesheet
   parsed, not that the right matrix is usable. Expect at least one such
   assertion, and expect a badge-width or focus assertion that was not scoped to
   the **active** orientation — a `display: none` node has no usable geometry.
3. **Information lost with the suppressed rows.** Difference-only rows are the
   ticket's headline idea and its easiest regression: a group whose members are
   all hard-protected loses its Protection row, and if the identical-axes line is
   missing, incomplete, or ordered differently from the suppressed axes, the
   read-only protected context the issue requires is simply gone.
4. **Scope leak into the excluded artifact elements.** The artifact frame
   contains the `▸ decided` marker, the `.mx-c.avoid` amber Health treatment and
   its legend. An implementer working from the artifact rather than from #131 is
   likely to render one of them, or to add a "winner" class that infers a
   deciding rank the payload does not provide.

# Reusable implementer execution prompt

Implement issue #131 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-131-implementation-plan.md
```

Read the entire handoff, issue #131, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing. The design source of truth is the #102 agreed artifact at `https://claude.ai/code/artifact/8f1266ab-46b8-4be4-90af-22f16b9c7d4b`; read its public frame before implementing, and treat #131's constraints as overriding it wherever they differ. Do not read, reuse, or cite #128 or PR #130: they are closed wrong-scope history and are not design authority.

Rules:
- work on `feat/issue-131-armor-duplicates-design-fidelity`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, `git diff --check origin/main...HEAD`, `test -z "$(git ls-files data/)"`, `test -z "$(git status --porcelain)"`;
- a skipped browser suite is a failure, not a pass — report the real result;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, report: the branch, base and head SHAs, the full output of every verification command, the thresholds you measured and the evidence file you wrote, every settled copy string you changed (with justification), and every existing test you modified and why.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
The change is presentation-only but its blast radius is not. Rendering two
orientations doubles the verdict-cell registry that `paintArmorMember`,
`setVerdictControlsDisabled` and the finalise freeze all depend on, so a subtle
defect surfaces as a *stale or wrongly-enabled verdict control* — a mutation-path
correctness failure, not a cosmetic one. The difference-only rule deliberately
removes information from the DOM, which is exactly the kind of change whose
regressions pass their own tests. The diff is large, spans three test suites and
the CSS, and the acceptance criteria explicitly require tests that prove behavior
rather than assert static CSS — a claim best checked by a reviewer with no
implementation context who reruns the browser suite independently.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

**Implementer tier justification:** `claude-sonnet-5` at `xhigh`. This is the
matrix's **Complex Implementation** class: multi-file DOM transposition, a
container-query orientation switch, an accessibility-tree contract, a measurement
probe, and coordinated updates across Node and Playwright suites. `high` is
specified for routine label/presentation edits and would under-serve the
dual-orientation registry and difference-only rules; `xhigh` matches the
"complex DOM transposition / Playwright suites" example in the matrix.

# Review checklist

- [ ] Check 1: `git diff <base_sha>...HEAD` touches only the files permitted by the mechanical inclusion test; nothing under `src/vault_cleaner/rules/`, `report_run.py`, `report.py`, `review.py`, `review_session.py`, `server/`, `config.toml`, `PLAN.md`, or the snapshot golden.
- [ ] Check 2: `RULESET_VERSION` is unchanged and no snapshot/server schema field was added or renamed.
- [ ] Check 3: exactly one orientation is active at every measured width; the inactive one is `display: none`, absent from the accessibility tree, and unreachable by keyboard. Verified in the browser, not by reading CSS.
- [ ] Check 4: member columns are active at a fitting desktop panel; the row fallback is active at 390×844 and at a constrained/zoomed panel; `documentElement.scrollWidth <= viewport width` at 1440×1000, 1024×900 and 390×844, in both appearances.
- [ ] Check 5: every verdict cell for an id is registered in both orientations; one acknowledgement repaints and disables **all** occurrences; read-only occurrences stay read-only; finalise freezes both; focus is retained. No test asserts `state.duplicateRows[id][0]` positionally.
- [ ] Check 6: an axis identical across members is absent from the matrix **and** present, correctly labelled and ordered, in the identical-axes line. Same-stat `Tuning Mod Slot` and the `Verdict` row are never suppressed.
- [ ] Check 7: no `decided`/winner marker, no deciding-rank inference, no Health low-value colouring or legend, no group-level or bulk verdict actions, no new payload field.
- [ ] Check 8: settled copy is intact — the same-stat two-part banner, `Exact`, `Same stats · review only`, `duplicateScopeText` outputs, and the existing row/facet labels. `#vc-duplicate-scope` keeps its id, parent, `role`, `aria-live`, and in-place update; there is exactly one live-region scope announcement and no `SHOWN` total on this surface.
- [ ] Check 9: archetype renders as a text-labelled badge; the 30/25/20 spike shows values and roles as text with the named zero-stat summary; the non-tier-5 fallback is unchanged; tuning banners are always visible and text-labelled in both group kinds.
- [ ] Check 10: hostile names, ids, locations, notes, perks, archetypes, mods and state text render inertly in **both** orientations; `Id`/`Hash` stay opaque strings and never pass through `Number`.
- [ ] Check 11: tests prove behavior. Spot-check by reverting individual source hunks in a disposable worktree and confirming the corresponding test goes red — in particular the orientation switch, the row-suppression rule, and the dual-occurrence repaint.
- [ ] Check 12: `ruff check src tests scripts`, `pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 pytest -q -m browser tests/test_server_browser.py` (passed, not skipped), `git diff --check origin/main...HEAD`, `git ls-files data/` empty, `git status --porcelain` empty.
- [ ] Check 13: the measurement script runs, asserts its preconditions, and the committed evidence file matches the thresholds actually shipped in the CSS.
- [ ] Check 14: `docs/browser-verification.md` has an Issue #131 focused check plus a real dated run record, and `WORKLOG.md` has a dated newest-first entry.

# Dispatch comment draft

Planned #131 in [handoffs/issue-131-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-131-implementation-plan.md) on `main`.

- **Implementer tier & effort:** `claude-sonnet-5` (`xhigh`)
- **Implementation branch:** `feat/issue-131-armor-duplicates-design-fidelity`
- **Review path:** independent adversarial review
- **Likely findings:** stale verdict state in the hidden orientation (the duplicate-cell registry doubles); tests that assert computed CSS instead of behavior, or that measure a `display: none` node; read-only protection context lost with the suppressed identical rows; scope leak into the artifact's excluded `decided` marker or Health low-value treatment.
