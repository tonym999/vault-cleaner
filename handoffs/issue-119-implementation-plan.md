# Issue #119 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#119 — Implement the Armor duplicates count and hierarchy treatment`

**Milestone:** `M9 — Duplicate Review UX`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `claude-sonnet-5` with native `output_config.effort = xhigh` (justified below)

**Plan baseline:** `main` at `91a4e5b1c5059138b231ed915bfdbd8352a15eae` (2026-09-03)

**Allocated implementation branch:** `feat/issue-119-duplicate-count-hierarchy`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Make group count, piece count, and filter scope unambiguous on the Armor
duplicates surface, and make the exact versus same-stat distinction readable
without relying on colour — implementing the treatment decided in
[docs/duplicate-review-count-design.md](../docs/duplicate-review-count-design.md)
§3.

The change is presentation only. No armor grouping key, close-pass behaviour,
ranking, survivor selection, note, tag, threshold, verdict, revision,
finalisation, persistence, lifecycle or authentication behaviour changes, and
`report_run.RULESET_VERSION` is not bumped.

## Implementer model and effort

Selected: **`claude-sonnet-5`** with native `output_config.effort = xhigh`.

This is a **Complex Implementation** under the task-class matrix in
[handoffs/README.md](README.md#model-family--provider-native-reasoning-effort-matrix)
— the row names "complex DOM transposition / Playwright suites" specifically —
whose mapping is `claude-sonnet-5` (`xhigh`), `gpt-5.6-sol` (`high`), or
`gemini-3.1-pro-preview` (`high`). The matrix was re-verified against the
provider tables in that document on 2026-09-03; Anthropic exposes effort through
`output_config.effort` with `xhigh` among its allowed values.

`claude-sonnet-5` is chosen over the two alternatives because the work is a
single-repository rewrite against a precise written spec rather than open-ended
design, and because keeping the implementer inside the orchestrator's likely
native runtime avoids the manual cross-provider launch boundary for the longer
of the two dispatches. `xhigh` rather than `high` because the transposition must
hold several invariants simultaneously — conditional columns, member identity,
verdict registration — where a cheaper pass tends to produce a fixed column set
that renders correctly and quietly loses one of them.

Reserving a different family for the adversarial reviewer is preferred where
available, but that selection belongs to the orchestrator after it sees the real
diff, and independence rests on a fresh context and a read-only remit rather
than on a different provider.

The orchestrator verifies whether its active runtime can instantiate this exact
model and effort. If it cannot, it prepares the reusable implementer execution
prompt below for a human operator to launch, and records the actual
provider/model/effort used together with any fallback.

## Context & Measurement

All line numbers below were measured against the plan baseline
`91a4e5b` on 2026-09-03. Reproduce with `git rev-parse origin/main` followed by
the greps in each subsection.

### File sizes at baseline

```text
src/vault_cleaner/ui/review_server.js   1361 lines
src/vault_cleaner/ui/review_ui.js       1257 lines
src/vault_cleaner/ui/review.css          175 lines
src/vault_cleaner/ui/review_server.html   78 lines
```

### The two displays of one quantity

The `SHOWN` tile is appended for every surface at
[review_server.js:838-839](../src/vault_cleaner/ui/review_server.js#L838-L839),
with its value computed at
[review_server.js:832-834](../src/vault_cleaner/ui/review_server.js#L832-L834).
On the duplicates surface it counts groups; on every other surface it counts
items. Only the sub-caption changes between `"matching duplicate groups"` and
`"matching the current filters"`.

The `Showing N of M groups` hint is built at
[review_server.js:995-998](../src/vault_cleaner/ui/review_server.js#L995-L998)
as `p#vc-duplicate-count.hint`. Its denominator is `selectedArmorGroups.length`
([review_server.js:992](../src/vault_cleaner/ui/review_server.js#L992)), which
is already narrowed by the kind selector via `armorGroupsForKind`, so both
numbers move together and the string can never reveal that groups of another
kind exist. It is also not pluralised.

### Piece totals need no schema change

Both armor group projections carry a non-empty `members` array
([review_ui.js:335-401](../src/vault_cleaner/ui/review_ui.js#L335-L401) for
exact groups, and the same-stat projection below it). A piece count is
`group.members.length`; totals are the sum over the relevant group list. No
snapshot schema field, no golden regeneration, and no `_decision_config` key are
required.

### Group header and kind label

`armorGroupHeader` is
[review_ui.js:1043-1067](../src/vault_cleaner/ui/review_ui.js#L1043-L1067). The
kind sub-line is
[review_ui.js:1050-1052](../src/vault_cleaner/ui/review_ui.js#L1050-L1052) and
currently reads `"Same stats, different tuning · review-only"` or
`"Exact duplicate group"`.

### The comparison table

`armorGroupTable` is
[review_ui.js:1126-1197](../src/vault_cleaner/ui/review_ui.js#L1126-L1197).
Members are **columns**: header cells are built per member at
[review_ui.js:1128-1135](../src/vault_cleaner/ui/review_ui.js#L1128-L1135), and
each comparison field becomes a `tr` whose cells map over `group.members` at
[review_ui.js:1174-1180](../src/vault_cleaner/ui/review_ui.js#L1174-L1180).

The conditional-column behaviour is driven by `memberValues`
([review_ui.js:1034-1042](../src/vault_cleaner/ui/review_ui.js#L1034-L1042)),
called at
[review_ui.js:1141-1156](../src/vault_cleaner/ui/review_ui.js#L1141-L1156):
`Seasonal Mod` and `Holofoil` rows appear only when members differ, and
`Tuning Stat` only when `rawTuningValues.length > tuningSlots.length`.

The verdict row is
[review_ui.js:1182-1186](../src/vault_cleaner/ui/review_ui.js#L1182-L1186); each
cell comes from `armorMemberCell`
([review_ui.js:1069-1124](../src/vault_cleaner/ui/review_ui.js#L1069-L1124)),
which registers a handle in `state.duplicateRows` keyed by member id. That
registry is what repaints a verdict across both surfaces, so it must survive the
rewrite unchanged in behaviour.

The table is wrapped in `div.scroller.armor-matrix` at
[review_ui.js:1189](../src/vault_cleaner/ui/review_ui.js#L1189).

### Why the table needs transposing

`table` carries `min-width: 52rem`
([review.css:119](../src/vault_cleaner/ui/review.css#L119)) and
`.armor-group-table` narrows that to `min-width: 46rem`
([review.css:157](../src/vault_cleaner/ui/review.css#L157)), with
`.armor-member-heading { min-width: 12rem }`
([review.css:159](../src/vault_cleaner/ui/review.css#L159)) and
`.armor-member-cell { min-width: 12rem }`
([review.css:163](../src/vault_cleaner/ui/review.css#L163)). At a 390px viewport
one member column is visible and comparison requires scrolling inside the
table.

### Badge truncation

`.badge` sets `white-space: nowrap`
([review.css:131-134](../src/vault_cleaner/ui/review.css#L131-L134)) and is
rendered inside the member heading at
[review_ui.js:1133](../src/vault_cleaner/ui/review_ui.js#L1133). With
`armorMemberLabel` returning `"Existing Proposals action: review"`
([review_ui.js:1008-1015](../src/vault_cleaner/ui/review_ui.js#L1008-L1015)) the
badge exceeds the 12rem heading and is clipped mid-word inside the horizontal
scroller.

### The facet noun defect

`duplicateOptions`
([review_server.js:915-923](../src/vault_cleaner/ui/review_server.js#L915-L923))
already renders `value (N group)` / `value (N groups)`. The remaining defect is
upstream: `countArmorGroups`
([review_ui.js:626-645](../src/vault_cleaner/ui/review_ui.js#L626-L645)) counts
**one per distinct member tuning slot** when `field === "tuningModSlot"` and the
group is same-stat, but one per group for every other field and kind. The noun
rendered is `group` in both cases, so the tuning facet can sum to more than the
group total while presenting itself in group units.

### Existing tests that assert strings this change removes

| Location | Assertion |
|---|---|
| [tests/test_review_ui_js.py:1267-1268](../tests/test_review_ui_js.py#L1267-L1268) | `labels`: same-stat article contains `Same stats, different tuning` and `review-only` |
| [tests/test_review_ui_js.py:1294](../tests/test_review_ui_js.py#L1294) | `exactSubLine`: exact article contains `Exact duplicate group` |
| [tests/test_review_ui_js.py:1295-1296](../tests/test_review_ui_js.py#L1295-L1296) | `exactNoEnumToken`: exact article text contains **no** `_` at all |
| [tests/test_review_ui_js.py:1297-1298](../tests/test_review_ui_js.py#L1297-L1298) | `sameSubLineUnchanged`: exact literal `Same stats, different tuning · review-only` |
| [tests/test_server_ui_js.py:2272](../tests/test_server_ui_js.py#L2272) | duplicate `groupText` starts with `Showing 1 of 1 groups` |
| [tests/test_server_browser.py:333](../tests/test_server_browser.py#L333) | group contains text `Same stats, different tuning` |

The node harness in `tests/test_review_ui_js.py` also uses `findRow(article,
label)` and `cellTexts(row)` helpers that assume members are columns. Both must
be reworked for the transposed layout rather than deleted; the assertions they
carry (`protectionHeaderPresent`, `noHardProtectionHeader`,
`protectionCellsHonest`) are #118 regression guards and must keep testing the
same facts.

[tests/test_server_ui_js.py:511](../tests/test_server_ui_js.py#L511) asserts the
literal `"shown"` appears in `review_server.js`. The tile is retained on the
proposals surface, so that assertion stays true and must not be weakened.

### Toolchain availability (measured on the plan host)

```text
node v24.20.0                      # tests/test_review_ui_js.py, test_server_ui_js.py
~/.cache/ms-playwright/chromium-1234  # tests/test_server_browser.py
```

The browser suite therefore genuinely runs here; a skip is a failure, not an
absence.

## Dependencies and assumptions

### Resolved staleness — the issue body is stale in four places

1. **Item 11's replacement target no longer exists.** The issue and the design
   record both say the kind label replaces
   `"Exact duplicate group · " + group.groupKind`. That concatenation was
   removed by #118 (PR #121, `9a14847`). The current target is the plain
   sub-line at
   [review_ui.js:1050-1052](../src/vault_cleaner/ui/review_ui.js#L1050-L1052).

2. **Item 13 is partly landed.** #118 added the `group`/`groups` pluralisation
   at
   [review_server.js:916](../src/vault_cleaner/ui/review_server.js#L916), so
   `Melee (1 group)` already renders. What remains is the *wrong* noun on
   member-derived tuning counts, described under "The facet noun defect".

3. **The #118 coordination clause is resolved.** #119 says "whichever lands
   second rebases". #118 landed first (`9a14847`, 2026-09-03), so #119 rebases
   onto it. Its three defects — the `Hard protection` header, the leaked
   `exact_duplicate` enum, and the 390px fingerprint overflow — are already
   fixed on `main` and must not be reintroduced. The fingerprint fix was applied
   as `overflow-wrap: anywhere` on `code, .mono, kbd`
   ([review.css:52-55](../src/vault_cleaner/ui/review.css#L52-L55)).

4. **Cited line numbers have drifted.** `review_server.js:832-839` is now
   831-840; `review_server.js:996` is now 997; `review_ui.js:1125` is 1126; and
   the `memberValues` range cited as `review_ui.js:1133-1159` is its call sites,
   the function itself being at 1034-1042.

### Dependencies

- **#113 is satisfied.** The decision record is committed at
  [docs/duplicate-review-count-design.md](../docs/duplicate-review-count-design.md)
  (PR #120, `95b9706`) and names the direction. Nothing in this plan is
  contingent on further #113 work.
- **The four-member fixture exists.** `tests/fixtures/armor_same_stat_four_ui.csv`
  is committed, with its shape pinned by
  [tests/test_report_run.py:874-912](../tests/test_report_run.py#L874-L912),
  including the fact that all four members carry `proposal_action: review`.
- **#115, #116 and #117 are out of scope** and must not be implemented, in whole
  or in part.

### Assumptions

- Piece totals are group members, counted identically in numerator and
  denominator, per the design record's §3 note. Pieces belonging to no duplicate
  group are counted by neither.
- No new runtime dependency. Runtime deps remain pandas and Flask 3.1.

## Proposed Plan & Scope

### Scoped summary region

#### [MODIFY] [review_server.html](../src/vault_cleaner/ui/review_server.html#L69-L73)

Insert one persistent live region between the static hint and the list host,
so it is never destroyed and recreated by a re-render:

```html
<p id="vc-duplicate-scope" class="scope-summary" role="status" aria-live="polite"></p>
```

It must sit **outside** `#vc-duplicate-list`, because `renderList` calls
`view.clear(host)` on that element
([review_server.js:989](../src/vault_cleaner/ui/review_server.js#L989)) and a
live region removed and re-inserted is not reliably announced.

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L823-L841)

In `renderSummary`, append the `shown` tile only when
`state.surface !== "armor-duplicates"`. The tile and its
`"matching the current filters"` caption stay exactly as they are on the
proposals surface. Delete the duplicates branch of the `shown` computation at
[review_server.js:832-834](../src/vault_cleaner/ui/review_server.js#L832-L834)
once nothing reads it.

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L990-L998)

In `renderList`, delete the `p#vc-duplicate-count` hint entirely and instead set
the text of `#vc-duplicate-scope` in place. Three group lists are needed:

- `state.armorGroups` — every group, every kind. This is the fix for the
  already-filtered denominator.
- `selectedArmorGroups` — after `armorGroupsForKind`.
- `filteredGroups` — after `ui.filterArmorGroups`.

Verbatim copy, where `G`/`GT` are shown/total groups and `P`/`PT` are shown/total
pieces:

- Unfiltered (no kind selection and no active query field):
  `74 groups · 211 pieces`
- Otherwise: `12 of 74 groups · 38 of 211 pieces` followed by the scope suffix.

Pluralise both nouns independently: `1 group`, `2 groups`, `1 piece`,
`2 pieces`.

**Scope suffix.** The decision record specifies only the kind case
(`— filtered to exact duplicates`). This plan extends it deterministically,
because the surface has four facets and a search box in addition to the kind
selector. The suffix is `" — filtered to "` followed by the active parts joined
with `", "`, in this fixed order:

| Source | Part |
|---|---|
| kind selector `exact_duplicate` | `exact duplicates` |
| kind selector `same_stat` | `same-stat groups` |
| `armorQuery.guardianClass` | `class VALUE` |
| `armorQuery.type` | `slot VALUE` |
| `armorQuery.itemArchetype` | `archetype VALUE` |
| `armorQuery.tuningModSlot` | `tuning slot VALUE` |
| `armorQuery.text` | `search "VALUE"` |

Worked example:
`12 of 74 groups · 38 of 211 pieces — filtered to exact duplicates, class Titan, search "Reaver"`.

Values are inserted as text through the existing `view.el` text path; they are
never concatenated into markup. Hostile fixture text must remain inert.

When a filter matches nothing, the region still states the scope, and the
existing empty-state hint
([review_server.js:999-1002](../src/vault_cleaner/ui/review_server.js#L999-L1002))
remains as the only other message.

### Group header

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1043-L1067)

1. **Piece count first.** Prepend to `header.armor-group-header`, before the
   `h3`:
   `el("p", { class: "armor-group-pieces", text: N + (N === 1 ? " piece" : " pieces") })`
   where `N = (group.members || []).length`.

2. **Kind label.** Replace the sub-line text at
   [review_ui.js:1050-1052](../src/vault_cleaner/ui/review_ui.js#L1050-L1052)
   with exactly `Exact` for an exact group and `Same stats · review only` for a
   same-stat group. Note the space-free spelling `review only`, not the current
   hyphenated `review-only`.

3. **Same-stat banner.** For same-stat groups only, add one `p.hint` after the
   kind label carrying two sentences:

   - Unconditional: `Base stats match but tuning differs, so this pass selects no survivor.`
   - Appended, separated by a single space, only when at least one member
     satisfies `armorMemberCanVerdict(group, member)`
     ([review_ui.js:1017-1023](../src/vault_cleaner/ui/review_ui.js#L1017-L1023)):
     `Pieces below that already carry a proposal keep their verdict controls.`

   Eligibility is decided from the projected member data through
   `armorMemberCanVerdict`, never from whether a button was rendered.

### Transposed comparison table

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1126-L1197)

Rewrite `armorGroupTable` so **members are rows and comparison fields are
columns**.

Required carry-overs:

- The conditional-column decision is unchanged. `memberValues` still decides
  whether `Seasonal Mod`, `Holofoil` and `Tuning Stat` appear, with the same
  predicates at
  [review_ui.js:1141-1156](../src/vault_cleaner/ui/review_ui.js#L1141-L1156).
  They are now conditional **columns of the transposed table**; a fixed column
  set is a plan violation.
- `Tuning Mod Slot` remains same-stat-only.
- The fixed fields keep their current order and cell functions verbatim:
  `Protection`, `In loadout`, `Equipped`, `Locked`, `Masterwork Tier`, `Power`.
  `Protection` keeps its `level — reason` / `—` behaviour (a #118 guard).
- Each member row starts with a `th scope="row"` carrying the member identity
  currently in the column heading
  ([review_ui.js:1128-1135](../src/vault_cleaner/ui/review_ui.js#L1128-L1135)):
  the member number, the monospace id, the location, and the
  `armorMemberLabel` badge. Field columns are `th scope="col"`.
- The verdict cell stays `armorMemberCell(member, group)` **unchanged**,
  including its `data-member-id` from `armorMemberDomIdentity` and its
  registration into `state.duplicateRows`. Cross-surface repaint
  ([review_ui.js:1218-1226](../src/vault_cleaner/ui/review_ui.js#L1218-L1226))
  must keep working with no edit.
- The `div.scroller.armor-matrix` wrapper is retained.
- `Member N` numbering, member order, and the `armor-group` article attributes
  are unchanged.

#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css#L131-L175)

- Allow the member badge to wrap in the group table context rather than clip.
  Scope the change so the global `.badge { white-space: nowrap }` used elsewhere
  is untouched.
- Re-tune `.armor-group-table` `min-width`, `.armor-member-heading` and
  `.armor-member-cell` for the transposed layout. `.scroller` overflow handling
  stays.
- Add `.scope-summary` and `.armor-group-pieces` rules using existing custom
  properties only. No new colour literals outside the `:root` blocks
  ([review.css:2-36](../src/vault_cleaner/ui/review.css#L2-L36)).
- Extend the `max-width: 640px` block
  ([review.css:166-175](../src/vault_cleaner/ui/review.css#L166-L175)) as
  required.

### Facet noun

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L626-L645)

`countArmorGroups` returns entries that additionally carry the unit they were
counted in. **Decision:** the `tuningModSlot` facet counts **pieces** for every
group kind — one per member — and every other facet counts **groups**. For an
exact group all members share the group's tuning slot, so contributing
`group.members.length` to that value is consistent with the same-stat branch and
removes the mixed-unit sum.

Entries gain `unit: "group" | "piece"`. Existing `value` and `count` fields and
the `compareText` ordering are unchanged.

**Consequence to state in the PR:** the tuning facet's number stops predicting
how many groups the filter will show. The scoped summary region is the surface
that answers that, and the option now answers "how many pieces have this tuning
slot". The rejected alternative — leaving counts alone and labelling only the
same-stat contribution — was rejected because a single facet value can be fed by
both kinds, which would make one option's unit indeterminate.

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L915-L923)

`duplicateOptions` pluralises from `entry.unit` instead of the hard-coded
`"group"`, producing `Melee (3 pieces)` for the tuning facet and
`Titan (1 group)` elsewhere. If `unit` is absent, fall back to `group` so a
partial deployment degrades to today's behaviour.

### Retire the user-facing nouns

#### [MODIFY] [review_server.html](../src/vault_cleaner/ui/review_server.html#L71), [review_ui.js](../src/vault_cleaner/ui/review_ui.js), [review_server.js](../src/vault_cleaner/ui/review_server.js)

`pieces` is the user-facing word for a piece of armor on this surface.
`copies`, `items` and `members` are retired from user-facing text **on the
duplicates surface only**. `members` stays correct in code, in the snapshot
schema, and in the projection error messages, which are developer-facing.

The proposals surface keeps its existing vocabulary; do not re-word it.

### Tests

#### [MODIFY] [tests/test_review_ui_js.py](../tests/test_review_ui_js.py#L1255-L1305)

- Rework `findRow`/`cellTexts` for the transposed layout, preserving the
  `protectionHeaderPresent`, `noHardProtectionHeader` and
  `protectionCellsHonest` assertions as equivalent facts about the new shape.
- Update `labels`, `exactSubLine` and `sameSubLineUnchanged` to the new copy.
- Keep `exactNoEnumToken` passing: the exact article's text must still contain
  no `_`.
- Add: header piece count and its singular form; the unconditional banner
  sentence on a same-stat group with no proposing member; both sentences when a
  member proposes; conditional `Seasonal Mod` / `Holofoil` / `Tuning Stat`
  columns still appear and disappear on the same predicates after transposition;
  `countArmorGroups` unit values.

#### [MODIFY] [tests/test_server_ui_js.py](../tests/test_server_ui_js.py#L2272)

Replace the `Showing 1 of 1 groups` assertion with the scoped summary text,
including a filtered case whose group and piece numbers differ. Leave
[tests/test_server_ui_js.py:511](../tests/test_server_ui_js.py#L511) alone.

#### [MODIFY] [tests/test_server_browser.py](../tests/test_server_browser.py#L268-L388)

Browser coverage must exercise, using committed fake fixtures only:

- the four-member same-stat group (`armor_same_stat_four_ui.csv`), which is the
  badge-truncation and transposition case;
- an exact group (`armor_duplicates_ui.csv`);
- a mixed report where both kinds are present;
- a filtered state where the group count and the piece count differ, asserting
  the scoped region's text and that it carries `aria-live="polite"`;
- 1440x900 and 390x844 viewports, asserting
  `document.documentElement.scrollWidth` does not exceed the viewport at 390px;
- the member badge is not clipped — assert the badge element's `scrollWidth`
  does not exceed its `clientWidth`;
- light and dark via `page.emulate_media(color_scheme=...)`.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

A dated entry at the top: what changed, the facet-unit decision and its
consequence, the scope-suffix format, and anything surprising.

## Mechanical inclusion test

A proposed change is **in scope** if and only if all of the following hold:

- It changes only `src/vault_cleaner/ui/review_ui.js`,
  `src/vault_cleaner/ui/review_server.js`, `src/vault_cleaner/ui/review.css`,
  `src/vault_cleaner/ui/review_server.html`, files under `tests/`, or
  `WORKLOG.md`.
- It is traceable to a numbered item in #119's Scope, to the copy table in
  [docs/duplicate-review-count-design.md](../docs/duplicate-review-count-design.md)
  §3, or to a section of this plan.
- It alters what the browser **renders or counts for display**, never what the
  server decides, persists, or returns.
- It leaves `report_run.RULESET_VERSION`, the snapshot schema, the fake-data
  golden, `report_run._decision_config`, and every file under
  `src/vault_cleaner/rules/` untouched.

Worked examples:

- **IN SCOPE:** deleting the `SHOWN` tile on the duplicates surface while
  leaving it on the proposals surface.
- **IN SCOPE:** transposing `armorGroupTable` and re-tuning the CSS min-widths
  that existed to support the column layout.
- **IN SCOPE:** adding `unit` to `countArmorGroups` entries and reading it in
  `duplicateOptions`.
- **OUT OF SCOPE:** adding a `score` field to a duplicate member — that is #116.
- **OUT OF SCOPE:** adding an `Approve all` control to a group header — that is
  #115.
- **OUT OF SCOPE:** building a DIM search string from a group's ids — that is
  #117.
- **OUT OF SCOPE:** changing `matchesArmorGroup` so a facet selects members
  rather than groups. Counting pieces for display is in scope; filtering by
  member is a different feature.
- **OUT OF SCOPE:** collapsing the tile row at 390px. The design record lists it
  as an open question "worth its own look during #119" — raise it, do not build
  it.
- **OUT OF SCOPE:** re-wording the proposals surface.

### Stop conditions

Stop implementation and return to the orchestrator if:

- The transposition cannot preserve `memberValues` conditional columns, the
  `state.duplicateRows` registration, or `data-member-id` identity without
  editing `armorMemberCell`.
- A projected field needed for the piece count or the banner turns out not to
  exist, so a snapshot schema change would be required.
- The facet-unit decision cannot be implemented without changing what
  `filterArmorGroups` selects.
- The scoped region cannot be announced by a screen reader without moving
  verdict state, revision handling, or focus management.
- Making the badge wrap requires changing `.badge` globally, affecting the
  proposals surface.
- Any test that guards a #118 fix would have to be deleted rather than adapted.
- `VAULT_CLEANER_BROWSER_REQUIRED=1` cannot be satisfied on the implementation
  host.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **The live region is recreated instead of updated.** The natural edit is to
   append the scoped line inside `#vc-duplicate-list`, which `renderList`
   clears on every keystroke. That renders correctly, passes a text assertion,
   and never announces. Check that `#vc-duplicate-scope` is static markup whose
   `textContent` is set, and that the browser test asserts the element survives
   a filter change rather than only that the text is right.

2. **DOM-derived eligibility in the same-stat banner.** The conditional second
   sentence invites `article.querySelector(".approve")`. #115 records that exact
   prior-art defect. It must call `armorMemberCanVerdict` against projected
   members. Note that in read-only sessions (`readOnly` at
   [review_ui.js:1073](../src/vault_cleaner/ui/review_ui.js#L1073)) no buttons
   render at all, so a DOM check silently drops the sentence — and the banner
   would then claim less than the truth.

3. **Transposition drops the conditional columns.** A fixed column list is
   simpler and passes any test that only checks the fixed six fields. #119 calls
   this out explicitly. Verify with a same-stat group whose members share a
   `Seasonal Mod` — that column must be absent — and one where they differ.

4. **Denominator still kind-scoped.** The whole point of item 4 is that the
   total comes from `state.armorGroups`, not `selectedArmorGroups`. A diff that
   keeps using the kind-filtered list will look correct in every single-kind
   fixture and be wrong only in a mixed report. The mixed-report browser case is
   the guard.

5. **Browser suite skipped.** `tests/test_server_browser.py` skips silently when
   managed Chromium is absent unless `VAULT_CLEANER_BROWSER_REQUIRED=1` is set.
   Chromium is present on the plan host, so a skip in the implementer's report
   means the variable was not set. A skipped browser run is not a pass.

# Reusable implementer execution prompt

Implement issue #119 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-119-implementation-plan.md
```

Read the entire handoff, issue #119, `docs/duplicate-review-count-design.md`, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-119-duplicate-count-hierarchy`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, `git diff --check origin/main...HEAD`;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, report the branch name, base and head SHAs, the full output of every verification command, each stop condition considered, and any deviation from the plan with its justification.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**

The diff is presentation-only but not self-contained. It rewrites the rendering
path that hosts verdict controls: `armorGroupTable` builds the cells that
`armorMemberCell` registers in `state.duplicateRows`, which is the registry
driving cross-surface verdict repaint. A rewrite that renders correctly while
subtly changing member identity or registration order would pass a visual
review and corrupt verdict repaint — the one part of this surface where
presentation touches verdict authority.

Three further properties raise the risk above routine: the change deletes
user-facing counts that existing tests pin, so tests must be adapted rather than
merely extended, and an adapted test is where a silently weakened guard hides;
the banner's conditional sentence is exactly the DOM-versus-data eligibility
defect recorded as prior art in #115; and correctness at 390px, in dark mode,
and under a screen reader is only demonstrable by actually running the browser
suite, which skips silently by default.

The blast radius is nonetheless bounded — no rules, no schema, no persistence,
no `RULESET_VERSION` bump — which makes this a good subject for adversarial
review rather than a dangerous one.

This ticket is also the selected subject of the #124 workflow pilot, but the
path above is chosen on the change's own merits.

The orchestrator confirms the path against the real diff and, when adversarial
review is required, selects and records the reviewer's exact provider, model ID,
and native effort at dispatch time.

# Review checklist

- [ ] Check 1: `#vc-duplicate-scope` is static markup outside `#vc-duplicate-list`, carries `aria-live="polite"`, and is updated by `textContent` rather than recreated. Confirm it survives a filter change in the browser test.
- [ ] Check 2: The group total comes from `state.armorGroups`, not `selectedArmorGroups`. Confirm against a mixed-kind report that a kind-filtered view still shows the unfiltered total.
- [ ] Check 3: Both nouns pluralise independently; the unfiltered form omits "of"; the scope suffix matches the plan's table exactly.
- [ ] Check 4: The `SHOWN` tile is gone from the duplicates surface and unchanged on the proposals surface. `tests/test_server_ui_js.py:511` is untouched.
- [ ] Check 5: The same-stat banner's first sentence is unconditional and its second is gated on `armorMemberCanVerdict` over projected members, with no DOM query. Verify it still appears in a read-only session.
- [ ] Check 6: After transposition, `memberValues` still gates `Seasonal Mod`, `Holofoil` and `Tuning Stat` on the same predicates. Verify both the present and absent case.
- [ ] Check 7: `armorMemberCell` is unedited; `data-member-id`, `armorMemberDomIdentity` and `state.duplicateRows` registration are unchanged; cross-surface verdict repaint still works.
- [ ] Check 8: #118's fixes are intact — `Protection` header with no `Hard protection`, no `exact_duplicate` token or `_` in the exact article's text, `overflow-wrap` on `code, .mono, kbd`.
- [ ] Check 9: No user-facing `copies`, `items` or `members` on the duplicates surface; `members` still used in code and schema.
- [ ] Check 10: `.badge` global rule unchanged; wrapping scoped to the group table. Badge `scrollWidth` does not exceed `clientWidth` in the four-member case.
- [ ] Check 11: Facet units — tuning facet reports pieces for both kinds, other facets report groups, `filterArmorGroups` semantics unchanged.
- [ ] Check 12: `RULESET_VERSION`, snapshot schema, report golden, `_decision_config`, and `src/vault_cleaner/rules/` are untouched. `git diff --stat` shows no file outside the inclusion test.
- [ ] Check 13: Browser suite actually ran with `VAULT_CLEANER_BROWSER_REQUIRED=1` — no skips — covering the four-member, exact, mixed and filtered cases at 1440x900 and 390x844, light and dark. No horizontal document scroll at 390px.
- [ ] Check 14: `ruff`, `pytest`, and `git diff --check origin/main...HEAD` clean; `WORKLOG.md` entry present and accurate.

# Dispatch comment draft

Planned #119 in [handoffs/issue-119-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-119-implementation-plan.md) on `main`.

- **Implementer tier & effort:** `claude-sonnet-5`, native `output_config.effort = xhigh` (Complex Implementation: DOM transposition plus Playwright coverage)
- **Implementation branch:** `feat/issue-119-duplicate-count-hierarchy`
- **Recommended review path:** `independent adversarial review` — the orchestrator confirms against the real diff and selects the reviewer's exact model and effort at dispatch time.
- **Likely findings:** live region recreated inside the cleared list host and never announced; same-stat banner eligibility read from the DOM instead of `armorMemberCanVerdict`; transposition dropping the `memberValues` conditional columns; the group total left kind-scoped, which only a mixed-kind report exposes; browser suite skipped without `VAULT_CLEANER_BROWSER_REQUIRED=1`.

**Staleness resolved during planning:** #118 (PR #121) already removed the `"Exact duplicate group · " + group.groupKind` concatenation that item 11 names as its replacement target, and already added the facet `group`/`groups` pluralisation from item 13; what remains there is the wrong noun on member-derived tuning counts. #119 rebases onto #118 rather than the reverse.
