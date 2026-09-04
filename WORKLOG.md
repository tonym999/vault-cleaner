# Worklog

Newest first. One entry per working session: what happened, decisions made,
surprises the next agent should know about.

## 2026-09-04 — #131: Armor duplicates design-fidelity implementation (PR 2)

Implementation-only session for #131 on `feat/issue-131-armor-duplicates-design-fidelity`
(branched from `main` at `e839e89081cd96c6c9c07788bc538413a05d974a`), following
`handoffs/issue-131-implementation-plan.md`. No Python rule, grouping key,
ranking, snapshot/server schema, or `RULESET_VERSION` change; every hunk is
under `src/vault_cleaner/ui/**`, `tests/test_review_ui_js.py`,
`tests/test_server_ui_js.py`, `tests/test_server_browser.py`,
`scripts/measure_armor_matrix_orientation.py`, `docs/evidence/issue-131/**`,
`docs/browser-verification.md`, and this file.

- **What changed:**
  - `review_ui.js`: `armorGroupHeader` is now a single wrapping headline
    (name, text-labelled `badge.arch` archetype, type/slot, guardian class,
    tier, hash, piece count) instead of a tile row; `armorStatDisplay`'s
    `zeroSummary` now names the zero stats (`grenade · super · melee · 0
    base`) instead of a fixed sentence; a new `armorStatSpike` renders the
    30/25/20 stats as labelled bars with lowercase `primary`/`secondary`/
    `tertiary` role text; `armorTuningBanner` promotes both banners to
    always-visible `.tuneline`/`.tuneline.warn` treatments. The comparison
    (`armorGroupTable`) is rebuilt around `armorComparisonSpecs`, which
    classifies each candidate axis as always-shown, differs (shown), or
    uniform (suppressed and restated in a new `p.armor-identical-axes`
    line) — then renders that same field list as two tables from the same
    `armorMemberCell` factory: `table.armor-matrix-rows` (today's shape,
    the accessible default) and `table.armor-matrix-columns` (the artifact
    orientation, axes as rows/members as columns). `armorGroup` now stamps
    `data-member-count` for the CSS switch.
  - `review.css`: `article.armor-group` is a `container-type: inline-size`
    query container; `.armor-matrix-columns` is `display: none` by default
    and swapped in per member count (2–6) via `@container (min-inline-size:
    …)` rules once its own measured budget (`13.5 + 12.5×N` rem — a 10.5rem
    axis-label column, 12.5rem per member column, 3rem guard) fits; the row
    table keeps its existing 46rem minimum, uninherited. Added `.tabs`
    (with `.tabs button`), `.segbtns` (with `.segbtns button`),
    `.tuneline`/`.tuneline.warn`, `.badge.arch`, the spike bar rules, and
    the section-heading rule.
  - `review_server.js`: the surface selector restyles as `.tabs` with a
    monospace count chip and a count-carrying `aria-label` on each button
    (counts are visible text *and* accessible name, never a live-region
    announcement); the group-kind control restyles as `.segbtns` the same
    way; `renderList`'s armor-duplicates branch now renders filtered groups
    under "Exact duplicates" / "Same stats, different tuning" `h3` sections
    (exact first, a heading only when that kind has a group in the current
    result); a static (non-live) hint sentence was added to the duplicate
    filter panel. `#vc-duplicate-scope`'s id/parent/`role`/`aria-live`/
    in-place update were not touched.
  - New `scripts/measure_armor_matrix_orientation.py` and
    `docs/evidence/issue-131/orientation-measurements.md`: boots the real
    packaged server, uploads the three committed armor-duplicate fixtures,
    and measures the comparison content box and active orientation at
    1440×1000/1024×900/390×844, asserting exactly-one-orientation-visible
    and no document overflow before writing a number.
- **Thresholds actually measured (not asserted):** at 1440×1000 the
  comparison content box is 1156px and member columns are active for 2, 3,
  and 4 members; at 1024×900 it is 932px and member columns are active for
  2–3 but the 4-member group falls back to rows; at 390×844 it is 315.6px
  and every member count uses rows. This matches the plan's stated
  consequences exactly. A follow-up measurement at 680px/760px (588px/668px
  content box) confirmed the two-member 616px (38.5rem) budget flips
  correctly and reversibly — used as the "zoom/reflow" browser test.
- **Decisions made / settled copy:**
  - Stat-spike role labels render lowercase (`primary`/`secondary`/
    `tertiary`) at display time — matching the artifact's own text exactly —
    while `armorStatDisplay`'s underlying `role` field stays capitalized
    (`"Primary"`, etc.) since an existing Node test asserts that API value
    directly; only the render path lowercases it.
  - The same-stat tuning banner moved from `p.hint` to `.tuneline.warn`; the
    settled two-part sentence itself (`Base stats match but tuning differs,
    so this pass selects no survivor.` / `Pieces below that already carry a
    proposal keep their verdict controls.`) is unchanged.
  - The zero-stat sentence changed from a fixed "The other three base stats
    are 0…" to naming the zero stats in stats-object order plus a fixed
    `· 0 base` tail — required by the plan, not optional polish.
  - Identical axes are restated only when genuinely uniform. `Tuning Stat`
    keeps its own stricter "does this carry information beyond the slot"
    gate unchanged, and is *not* restated as identical when it is merely
    hidden by that gate but not actually uniform — restating it there would
    misrepresent the data.
- **Surprises the next agent should know about:**
  - The server's real `/api/report` JSON pipeline does not preserve the
    Python-side stats-dict insertion order (`weapons, health, class,
    grenade, super, melee`) end to end — a live upload of
    `armor_duplicates_ui.csv` renders the zero-stat summary as `grenade ·
    melee · super · 0 base`, not `grenade · super · melee`. The Node-level
    tests (which build their own literal JSON snapshots) keep the literal
    order they author; only the browser tests, which go through the real
    server, were written against the measured real order. Nobody chased
    down *where* the reordering happens (not in scope for #131) — it is a
    factual observation for whoever next touches the stats payload.
  - Doubling the DOM occurrences (row + column orientation) doubles
    everything keyed by member id: button counts, `th[scope=col]` matches
    across the whole article, and `state.duplicateRows[id]` occurrence
    arrays. Every existing test asserting an exact count or indexing `[0]`
    on these needed updating to either assert over the whole occurrence
    list (Node tests) or scope Playwright locators to `:visible` (browser
    tests) — this was the single largest source of test churn, exactly as
    the plan's "likely findings" predicted. `paintArmorMember` itself needed
    no change: its existing "iterate every registered occurrence" design
    already handled two orientations correctly.
  - `armorMemberCell`'s existing `state.duplicateRows[id]` push-per-call
    design is what makes dual-orientation repaint work for free — worth
    keeping in mind as a reusable pattern if a third orientation is ever
    added.
  - Default `pytest-playwright` viewport (1280×720) already exceeds the
    2/3/4-member column budgets, so almost every existing armor-duplicates
    browser test was implicitly exercising the *new* column orientation
    even before any viewport resize in the test body — not just the
    four-member test the plan called out by name.
- **Orchestrator review follow-up (same session, same branch):** the pushed
  head rendered the stat-spike bar width as an inline `style="width:...%"`
  attribute on the bar `span`. `src/vault_cleaner/server/app.py`'s
  `SERVER_CSP` sends `style-src 'self'` with no `unsafe-inline`, so Chromium
  silently drops every inline `style` attribute and logs a CSP violation —
  measured on the pre-fix head at 1440×1000 as all three bars rendering at
  an identical 86.39px regardless of their 30/25/20 values, three CSP
  violation console messages per group render. Fixed by moving the bar
  widths into `review.css` as three role-selector rules
  (`.sv.p .bar { width: 100% }`, `.sv.s .bar { width: 83% }`,
  `.sv.t .bar { width: 67% }`, alongside the existing per-role opacity
  rules) and dropping the `style` attribute and the now-unused `barWidth`
  field from `armorStatDisplay` in `review_ui.js`. Measured after the fix
  (same viewport, same fixture): 86.39px / 71.70px / 57.88px — strictly
  ordered and matching 100%/83%/67% of the column's own width. Lesson for
  future UI work on this surface: never emit an inline `style` attribute
  here — the CSP has no escape hatch for it, so any dynamic sizing/coloring
  belongs in the stylesheet as selector-driven variants, not inline styles.
  Also removed a leftover empty `.armor-matrix { }` rule in `review.css`.
  Added two new browser tests to `tests/test_server_browser.py`
  (`test_armor_stat_spike_bars_render_proportional_widths`,
  `test_armor_duplicates_surface_has_no_csp_violations`); both were
  confirmed failing against the pre-fix code before the fix landed.
- **Independent adversarial review round (same session, same branch,
  `e839e89...930912b` reviewed):** the orchestrator accepted six findings;
  fixed all of them, tests only plus two doc/worklog corrections and one
  dead-class removal, no rule/grouping/ranking/schema change.
  - **P2-1 (blocking, real defect class):** three plan-mandated behaviours
    had zero test coverage, most seriously that deleting the guard
    `if (!section.groups.length) return;` in `review_server.js`'s
    duplicate-list render made an exact-only or same-stat-only report
    render a stray *empty* second section heading — nothing caught it.
    Added `test_single_kind_report_renders_exactly_one_section_heading`
    (`tests/test_server_ui_js.py`), which renders each kind alone and
    asserts exactly one `.armor-section-head` with both rule lines
    (`Same archetype, same stats, same tuning — one copy survives` /
    `Review only — the tool never picks your tuning for you`) verbatim;
    confirmed it fails both when the guard is deleted (heading count goes
    to 2) and when either rule string is mutated. Also added the exact-group
    tuning-banner N=1/N>1 suffix assertions to the existing mega-test in
    `tests/test_review_ui_js.py` (`— identical across all 2 pieces, and
    part of why they are one group.` / `— the only piece in this group.`),
    each confirmed to fail under a one-character mutation of its string.
  - **P2-2 (blocking):** the evidence file
    (`docs/evidence/issue-131/orientation-measurements.md`) recorded
    geometry at three fixed viewports but never the flip point itself,
    even though `review.css` cites it as the source of truth for the
    38.5/51/63.5/76/88.5rem thresholds. Extended
    `scripts/measure_armor_matrix_orientation.py` to binary-search the real
    browser viewport width at which each reachable member count's
    orientation flips (bracketing the search and re-confirming both sides
    of the boundary before trusting it — fail rather than guess), and to
    measure the conditional same-stat axis row-count delta by reading
    `tbody th.armor-matrix-axis-label` text for the two same-stat fixtures.
    Regenerated the evidence file; the measured flip points are **616.0px
    (38.5rem, N=2), 816.0px (51rem, N=3), 1016.0px (63.5rem, N=4)** —
    exact matches to the shipped CSS thresholds — and the axis-row delta
    between the two committed same-stat fixtures is **+3 rows** (4 vs 7),
    driven entirely by which conditional axes actually differ in each
    fixture's real data, not by member count. Also measured, at a
    2560×1200 viewport far past any reachable need, that the comparison
    content box plateaus at 1156.0px — below the N=5 threshold (1216px)
    and well below N=6 (1416px) — confirming in the evidence file that
    those two thresholds are deliberate defensive rules for a member count
    the producer cannot emit today, not measured ones.
  - **P3-4 (accepted, elevated):** no browser test flipped the panel width
    *between* an acknowledgement and its assertion, despite the plan's own
    likely-finding #1 calling this out as the highest-risk gap in the
    dual-orientation registry. Added
    `test_armor_verdict_acknowledgement_reflected_after_orientation_flip`
    to `tests/test_server_browser.py`: approves a same-stat proposal member
    at 680×900 (row fallback active), resizes to 760×900 (member-column
    orientation active) *after* the click, and asserts the pressed/enabled
    state in the newly visible occurrence and directly on the now-hidden
    row occurrence's own attribute — proving the repaint is registry-wide,
    not scoped to whatever was on screen at click time.
  - **P3-2 (accepted):** the section heading (`h3`) and the group name
    (also `h3`) were heading-level siblings under the same `h2`, which the
    plan did not intend. Demoted the group name to `h4` in
    `review_ui.js`'s `armorGroupHeader` and `.armor-group-header h3` to
    `.armor-group-header h4` in `review.css`; updated
    `tests/test_server_browser.py:703`'s `group.locator("h3")` to `"h4"`.
    Re-grepped the whole tree for other `h3`/heading-level assertions —
    none remained (the `.armor-section-head h3` selector and rule are
    correctly untouched, and `review_ui.js`'s unrelated "Armor scoring"
    `h3` is a different section entirely).
  - **P3-1, P3-6, P3-3 (trivial truthfulness/cleanup):** corrected
    `docs/browser-verification.md`'s recorded browser-suite run from a
    stale `10 passed in 7.30s` to the real re-measured `13 passed in
    9.42s` (12 from the prior round plus the new cross-orientation test);
    corrected this file's own prior entry, which claimed CSS classes
    `.tab` and `.segb` that were never added — only `.tabs button` and
    `.segbtns button` exist; and dropped the dead `armor-matrix` class from
    `review_ui.js`'s `armorGroupTable` scroller div (`930912b` had already
    removed the only CSS rule that used it, and nothing else referenced it
    — confirmed by grepping `tests/` before removing it).
  - **Rejected, left as-is (P3-5):** the identical-axes line's restatement
    of `Seasonal Mod none/unknown` / `Holofoil false` on same-stat groups is
    exactly what plan §8a mandates; `Tuning Stat` alone carries
    `skipIdentical` because its show-condition is genuinely stricter than
    plain "differs". No change made.
  - **Surprise for the next agent:** the flip-point binary search converges
    on viewport pixel widths one apart from the CSS threshold in *content*
    pixels (e.g. flip at 708px viewport / 616.0px measured content box for
    N=2) because of the fixed chrome between the viewport and the
    container's own inline size — the script reports both the viewport
    width searched and the resulting content-box width, and only the
    latter is comparable to the rem thresholds in `review.css`.
- **Second independent adversarial review round (same session, same branch,
  `e839e89...98342f7` reviewed):** the orchestrator accepted one blocking
  finding and four advisory ones; fixed all five, tests plus two small
  production hunks (a static-class move and a dead-CSS-class removal), no
  rule/grouping/ranking/schema change.
  - **P2-1 (blocking, real coverage gap):** `armorComparisonSpecs`'s
    same-stat `Tuning Mod Slot` spec carries `always: true` so the
    difference-only suppression rule never drops the group's defining axis
    — but every same-stat fixture in the whole suite already varies
    `Tuning Mod Slot` itself, so the axis always showed as a row from the
    plain "differs" check anyway and the `always: true` rail was never
    actually exercised. The reviewer proved this by deleting `always: true`
    and finding the full 128-Node/13-browser suite still green. The rail is
    reachable, not defensive: `armor_close.py`'s same-stat grouping key
    forms a group whenever *any* of `Tuning Stat`, `Seasonal Mod` or
    `Holofoil` differs, so a group can exist whose members share one
    identical `Tuning Mod Slot` and differ only in `Seasonal Mod` or
    `Holofoil` — and in that exact shape the `Tuning Stat` fallback is also
    dropped, because `rawTuningValues.length > tuningSlots.length`
    evaluates `1 > 1` (both are uninformative-uniform), so nothing else
    would have kept the axis visible. Added
    `test_same_stat_tuning_mod_slot_defining_axis_never_suppressed`
    (`tests/test_review_ui_js.py`) with exactly that shape (one shared
    `tuningModSlot`, `tuningStat` left unset on every member, `seasonalMod`
    and `holofoil` varying) and asserted `Tuning Mod Slot` is a row in both
    `table.armor-matrix-rows` and `table.armor-matrix-columns` and absent
    from `p.armor-identical-axes`. Confirmed load-bearing in a scratch
    edit: deleting `always: true` flips the result to
    `rowsHasTuningModSlot: False` / `columnsHasTuningModSlot: False` and
    `Tuning Mod Slot Weapons` appearing in the identical-axes text — the
    test goes red exactly as expected, then the source was restored from a
    backup copy before committing.
  - **P3-4 (accepted):** `review_server.js`'s `renderViewSelector` did
    `selectorPanel.className = "panel view-selector tabs"` on every render,
    unconditionally overwriting whatever `review_server.html` set on
    `#vc-view-selector` — `review_server.html` was never touched despite
    plan §1 listing it `[MODIFY]`, so the strip was unstyled between first
    paint and the first render. Moved `tabs` into the static class list on
    `#vc-view-selector` in `review_server.html` and dropped the JS
    assignment; the existing static `aria-label="Review surface"` was left
    exactly as-is. Updated the two `tests/test_server_ui_js.py` fake-DOM
    `Document()` constructors that back the tests reading `selector`'s
    `className` / rendering it, so the fake `#vc-view-selector` node starts
    with `"panel view-selector tabs"` the way the real static markup now
    does — mirroring, in the test harness, what the real HTML/JS split
    looks like post-fix.
  - **P3-1 (accepted):** dropped the dead `seg` class from
    `review_server.js`'s `#vc-dup-kind-selector` (`class: "view-selector
    seg"` → `class: "view-selector"`); `.seg` had zero rules in
    `review.css` (only `.segbtns` exists). Grepped tests first — nothing
    asserted `seg`.
  - **P3-3 (accepted):** `review_ui.js`'s `valuesForField` and
    `memberValues` were two near-identical distinct-value collectors in the
    same closure, both already using `Object.create(null)` (via
    `emptyMap()`) for `__proto__`-shaped-value safety. Collapsed to one:
    `memberValues` now delegates to `valuesForField` with a getter closure
    instead of re-implementing the collection loop; `valuesForField`'s own
    `emptyMap()`-based body is unchanged and is now the sole collector. No
    call site or test needed to change — the full suite stayed green
    unmodified, as the finding required.
  - **P3-2 (accepted):** `tests/test_server_browser.py`'s
    `theme_snapshot()` (inside
    `test_armor_same_stat_four_member_badge_wrapping_and_transposition`)
    covered only `.scope-summary` and `.armor-group-pieces`, leaving the
    new #131 elements — which the reviewer confirmed use only
    `--accent`/`--muted`/`--line`/`--review`/`--warn-bg` with no hardcoded
    colors — without a light/dark computed-value assertion. Extended it
    with the archetype badge's `color` (`--accent`), the `.tuneline.warn`
    banner's `backgroundColor`/`borderLeftColor` (`--warn-bg`/`--review`),
    the stat spike's primary bar `backgroundColor` (`--accent`), and the
    section heading's inherited `color` (`--ink`); all four flow through
    the existing generic "changed between light and dark, and never
    transparent" loops with no new assertion code needed. This fixture
    (`armor_same_stat_four_ui.csv`) only produces same-stat groups, so only
    the `.tuneline.warn` variant is exercised here — the plain `.tuneline`
    banner shares the same `--accent`/`--line` tokens already covered by
    the archetype badge and scope-summary assertions, so a second upload
    just to reach it was judged not worth the added test complexity.
  - **Not changed (P3-5, explicitly out of scope for this round):** the
    `N=5`/`N=6` container-query rules remain unreachable-but-documented
    defensive rules, per the orchestrator's instruction to leave them.
  - **Verification after this round:** `ruff check src tests scripts` —
    all checks passed; `pytest -q` — 962 passed (953 baseline + this
    round's one new Node test + prior-round additions already on the
    branch); `VAULT_CLEANER_BROWSER_REQUIRED=1 pytest -q -m browser
    tests/test_server_browser.py` — 13 passed, not skipped; `git diff
    --check origin/main...HEAD` clean; `git ls-files data/` empty;
    `git status --porcelain` clean after commit.
- **Third independent adversarial review round (same session, same branch,
  `e839e89...c9da9ac` reviewed):** the orchestrator accepted one blocking
  finding and two advisory ones; fixed all three, tests plus two small
  presentation-only production hunks, no rule/grouping/ranking/schema change.
  - **P2-1 (blocking, real defect on real data — the headline visual
    rendered inverted):** the orchestrator measured the shipped head live in
    managed Chromium at 1440×1000 against `armor_duplicates_ui.csv` and
    found the spike's `.sv` document order was tertiary (20), secondary
    (25), primary (30) left to right — bars ramping *up*, faintest and
    shortest leading — the exact reverse of the agreed #102 artifact and of
    plan §6's own `30 → 100%, 25 → 83%, 20 → 67%` spec.
    **Root cause, recorded here because it is the single most valuable fact
    in this entry:** `armorStatDisplay` (`review_ui.js`) built its `rows`
    array by iterating `Object.keys(group.stats)` and keeping whatever
    order the payload's `stats` object arrived in, instead of deriving
    order from role. `report_run.py` serializes the entire report snapshot
    with `sort_keys=True` (unchanged, and out of scope for #131 — do not
    touch it), so `stats` always arrives over the wire with its keys
    alphabetical, never in stat-value order. For this stat set that
    alphabetical order (`class, grenade, health, melee, super, weapons`)
    happens to list the tertiary stat (`class`, 20) before the secondary
    (`health`, 25) before the primary (`weapons`, 30) — i.e. exactly
    ascending, exactly backwards. **Any future presentation code on this
    surface that relies on `stats` payload key order for anything
    order-sensitive will silently render wrong in production while looking
    correct in a hand-authored test fixture** — see the test-gap note below.
    **Why the existing suite missed it:** the browser assertion
    (`test_armor_stat_spike_bars_render_proportional_widths`) selected bars
    by role class (`.sv.p .bar`, `.sv.s .bar`, `.sv.t .bar`), which finds
    the right element regardless of where it sits in the document, so it
    passed on the inverted head. The one Node-level assertion of row order
    (in `test_exact_groups_are_authoritative_and_filter_as_whole_groups`)
    built its own snapshot literal with `stats: {weapons: 30, health: 25,
    class: 20, ...}` — already primary-first by how the fixture happened to
    be authored — so it could not have caught a payload-key-order
    dependency either.
    **Fix (presentation only, `review_ui.js`):** `armorStatDisplay`'s tier-5
    branch now builds `rows` by iterating a fixed `[30, 25, 20]` role order
    and looking up which stat name carries each value, rather than mapping
    over `names` (`Object.keys(stats)`) in whatever order they arrived.
    Deterministic regardless of payload key order. `sort_keys=True` in
    `report_run.py` was not touched, and nothing outside `src/vault_cleaner/
    ui/` changed.
    **New tests, both keyed to a payload with alphabetical `stats` keys —
    exactly what the real server emits — so neither could pass by
    coincidence of fixture-authoring order the way the old one did:**
    `test_armor_stat_spike_orders_rows_by_role_not_payload_key_order`
    (`tests/test_review_ui_js.py`) asserts both `armorStatDisplay(group)
    .rows` order and the actual rendered `.sv` DOM node order/class/value/
    role from `armorGroupHeader`, walking the fake-DOM tree in document
    order (not selecting by role class); and
    `test_armor_stat_spike_renders_primary_first_in_document_order`
    (`tests/test_server_browser.py`) asserts the live Chromium `.sv`
    elements' `className`/`.val`/`.role` text in real document order via
    `locator.evaluate_all`, plus strictly increasing `getBoundingClientRect
    ().x`. **Confirmed load-bearing by mutation:** reverted
    `armorStatDisplay`'s row-ordering to the old `names.filter(...).map(...)`
    payload-order logic in a scratch edit — both new tests failed, the Node
    test reporting `domClassOrder: ["sv t", "sv s", "sv p"]` and the browser
    test reporting `classes == ['sv t', 'sv s', 'sv p']`, i.e. the exact
    inverted order the orchestrator measured live — then restored the fix
    from a backup copy before committing.
    **Measured `.sv` document order after the fix** (1440×1000,
    `armor_duplicates_ui.csv`): `x=142.0 sv p 30 primary bar=86.39px`,
    `x=242.78 sv s 25 secondary bar=71.70px`, `x=343.56 sv t 20 tertiary
    bar=57.88px` — strictly ascending x, strictly descending value/width,
    matching the artifact and plan §6 exactly.
  - **P3-1 (accepted):** the zero-stat summary line rendered its stat names
    in raw lowercase payload casing (`grenade · melee · super · 0 base`)
    directly beneath the spike's own stat labels, which CSS uppercases
    (`.armor-stat-summary.spike .sv .lbl { text-transform: uppercase }`) —
    one stat vocabulary in two casings side by side. Fixed with a CSS-only
    change: added a dedicated `armor-stat-zero` class to the zero-summary
    `<p>` in `review_ui.js` and a `.hint.armor-stat-zero` rule in
    `review.css` (mono font, `letter-spacing: .07em`,
    `text-transform: uppercase` — the same treatment as `.sv .lbl`), rather
    than uppercasing the string in `armorStatDisplay`. Chosen over a
    display-casing step in JS because `armorStatDisplay`'s `zeroSummary`
    string is also a data value asserted directly by an existing Node test
    (`"zeroSummary": "grenade · super · melee · 0 base"`), and this way that
    assertion, the ` · 0 base` suffix, and the non-tier-5 fallback all stay
    completely untouched — only the rendered presentation changes.
  - **P3-2 (accepted, checklist-consistency gap):** `tests/
    test_review_ui_js.py` still indexed `state.duplicateRows[id][0]`
    positionally in the `readOnly`, `repaintedInPlace`, `finalizedDisabled`,
    `proposalControls`, and `laterProposalRemainsMutable` assertions —
    always the row-table occurrence, contradicting review checklist item 5
    ("No test asserts `state.duplicateRows[id][0]` positionally"). The
    reviewer confirmed by mutation that the underlying dual-orientation
    repaint/disable behaviour is already covered elsewhere, so this was a
    checklist-consistency gap, not an uncovered behaviour. Converted all
    five to `.every()` over the full occurrence list (capturing `beforeCells
    = proposalRows.map(r => r.cell)` up front for the identity check), while
    keeping a single occurrence as the actual click target for triggering
    state changes — that part is an action, not an assertion, and stays
    positional by necessity (a real click always lands on one visible
    button).
  - **Trivial hardening (accepted):** `armorTuningBanner`'s exact-group
    branch concatenated `group.tuningModSlot` directly instead of through
    the existing `str()` helper. Both current server/adapter projections
    already normalize it to a string, so this was not reachable today, but
    a future hand-built group object could render the literal text
    `undefined`. Wrapped it in `str()`.
  - **Verification after this round:** `ruff check src tests scripts` — all
    checks passed; `pytest -q` — 964 passed (962 prior + 2 new tests this
    round: one Node, one browser); `VAULT_CLEANER_BROWSER_REQUIRED=1 pytest
    -q -m browser tests/test_server_browser.py` — 14 passed, not skipped;
    `git diff --check origin/main...HEAD` clean; `git ls-files data/`
    empty; `git status --porcelain` clean after commit. Diff scope: only
    `src/vault_cleaner/ui/review_ui.js`, `src/vault_cleaner/ui/review.css`,
    `tests/test_review_ui_js.py`, `tests/test_server_browser.py`, and this
    file.

## 2026-09-04 — #131: Armor duplicates design-fidelity planning session (plan PR 1)

Planning-only session for #131. No production code, test, fixture, snapshot,
CSS, or server contract changed.

- **What happened:**
  - Confirmed the ticket is startable: #131 is open in M9, and #102, #110, #113
    and #119 are all closed/`Done` reference work rather than open dependencies.
    Found no staleness between the issue body and `main` — every fidelity gap it
    names is real on the baseline, and every delivered fact it leans on is
    present.
  - Read the #102 agreed artifact (`8f1266ab…`, *Armor Duplicates Mockup*) as the
    design source of truth, and recorded which two of its frame elements #131
    excludes: the structured `▸ decided` winner marker and the amber Health
    "low-value for PvE" treatment.
  - Measured the baseline before prescribing anything: `ruff` clean,
    `pytest -q` 953 passed, and the required Chromium suite **8 passed in 6.02s**.
    Chromium launches in this environment, so the browser gate is a real gate
    here.
  - Measured the real layout budget by uploading the committed fake fixtures into
    the packaged server and reading live geometry: the comparison content box is
    **1156px at 1440×1000, 932px at 1024×900 and 316px at 390×844**, against a
    current `.armor-group-table` minimum of 736px (46rem) and 176px (11rem)
    member cells. The temporary measurement test was deleted; the working tree
    was left clean.
  - Authored `handoffs/issue-131-implementation-plan.md`, allocating
    `feat/issue-131-armor-duplicates-design-fidelity`, `claude-sonnet-5` at
    `xhigh`, and an independent adversarial review path.
- **Decisions made:**
  - **Difference-only rows must not lose information.** Suppressing an axis
    because it is identical would silently drop read-only protected context, so
    every suppressed axis is restated once per group in a muted
    `Identical across all pieces: …` line. That is what makes the artifact's
    "rows are the differences" rule safe here.
  - **Style the navigation as tabs; do not adopt `role="tablist"`.** Real tab
    semantics also require `aria-controls`, `role="tabpanel"`, roving `tabindex`
    and arrow-key handling; a partial version is less accessible than the working
    `aria-pressed` toggle group that already exists and is already tested. Counts
    go into the visible text *and* the `aria-label`, because `aria-label`
    otherwise hides them from assistive technology.
  - **Keep the per-group kind sub-line** (`Exact` / `Same stats · review only`)
    even though the artifact's header omits it. It is delivered copy that #110's
    and #118's acceptance checks and the Node tests depend on. Recorded as a
    deliberate deviation rather than a silent one.
  - **Do not move `#vc-duplicate-scope`.** The artifact puts its count note
    inside the filter card, but an existing browser test pins that element to
    parent `#vc-duplicates` and proves it is updated in place, not recreated.
    Style it into position instead; keep one live-region announcement.
  - **Orientation switch is a CSS container query on `.armor-group`**, with the
    row table as the default so an unsupporting browser degrades to today's
    behavior, and `display: none` (not `aria-hidden`) hiding the inactive
    orientation so it leaves both the accessibility tree and the keyboard order.
- **Surprises the next agent should know about:**
  - `#128` and PR #130 are closed wrong-scope history and are explicitly not
    design authority, so **every number in this plan was re-measured** on the
    baseline rather than inherited from that trail. Their probe and runner no
    longer exist in the repository; only the WORKLOG entries remain.
  - Existing tests are coupled to the current layout in ways a redesign trips
    over: `tests/test_review_ui_js.py:1355` asserts a header **child position**
    (`children[0].children[0]`), `:1341` forbids any underscore anywhere in an
    exact group's text, `:1324` counts exactly three buttons per article, and
    `tests/test_server_ui_js.py:1860`/`:2478` index
    `state.duplicateRows[id][0]` positionally. Rendering two orientations
    doubles both the buttons and the registry entries, so `[0]` may become the
    hidden one — those assertions must move to the whole occurrence list, not a
    re-indexed position.
  - `tests/test_server_browser.py:401` currently asserts the **member-row**
    orientation for a four-member group under a docstring that says
    "transposition". That test is not wrong today; #131 inverts what it should
    assert at fitting desktop widths while keeping it for the narrow fallback.
  - `.venv/bin/python` is **3.14.4** while `AGENTS.md` states Python 3.12. The
    entire suite is green on it. Recorded as an observation; changing it is out
    of scope for #131.

## 2026-09-04 — #132 authorization-boundary correction

- Opened #132 to track this workflow-governance correction. Closed
  implementation PR #130 without merge and closed #128 as not planned.
  Both retain explanatory comments and recoverable Git history. The issue was
  scoped from #113's responsive-matrix follow-up, but the owner's intended
  source was #102 and its linked agreed-design artifact.
- Removed the now-obsolete #128 handoff, responsive probe, and probe runner
  added by planning PR #129. The historical planning entry below remains so the
  repository records what happened rather than silently rewriting the audit
  trail.
- Added explicit authorization gates to `AGENTS.md`: issue creation, planning,
  plan merge, implementation, review, PR opening, and PR merge are separate
  permissions. Repository workflow describes how authorized work proceeds; it
  does not grant authority to advance phases.
- Added mandatory source-of-truth and open-issue checks at phase transitions,
  prohibited automatic issue reopening/repurposing, and reserved GitHub closing
  keywords for intentional final implementation PR bodies. The planning commit
  subject `Fix #128 handoff review sentence` had caused GitHub to close #128
  when PR #129 merged; PR #130 was then opened while #128 was closed and the
  issue was reopened afterward. The new guidance addresses both failures.
- Review round 2 extended the gates beyond `AGENTS.md`. `handoffs/README.md`
  gained an authorization-boundary section and conditional lifecycle wording;
  the phase-transition checklist now verifies explicit authorization for the
  next phase and each planned external mutation; and opening PRs, pushing
  branches, posting dispatch/coordination comments, requesting reviewers,
  changing issue/PR/project state, and merging are enumerated as external
  mutations. The closing-keyword rule was widened from "commit subject starts
  with `Fix #N`" to all nine GitHub keywords anywhere in a message, because
  GitHub matches them in bodies and trailers too, not just at subject start.
- **Decision:** product implementation tickets keep the two-PR handoff, but a
  documentation- or maintenance-only ticket may use one direct issue-to-PR
  route when the user explicitly authorizes it. The exception is never inferred
  from a label and never implies permission to merge. #132 itself used it.
- Review round 3 closed the gaps that round 2 left. `handoffs/templates/orchestrator.md`
  is the prompt that actually boots the orchestrator, and its review-outcome
  step still read as an unconditional instruction to open a PR and post
  comments; it now carries the authorization boundary and a pointer to the
  gates. **Surprise for the next agent:** fixing prose in `handoffs/README.md`
  does not fix the templates beside it — the template is the operative
  document, so treat the two as sibling paths and change them together.
- **Decision:** committing and pushing the allocated implementation branch are
  explicitly inside the implementation phase. Classifying pushes as external
  mutations had otherwise deadlocked the normal workflow, since
  `handoffs/templates/planner.md` tells the implementer to push and the
  orchestrator reviews the pushed head. No other branch may be pushed.
- The closing-keyword prohibition is now scoped to commit messages an agent
  authors, so a merge or squash commit GitHub generates from an intentional
  final PR body remains the supported closing path. Orchestrator finding
  routing was also narrowed to accepted, in-scope findings, matching
  `AGENTS.md` and the orchestrator template.
- No production UI, Python rule, report/snapshot contract, runtime dependency,
  or persisted-review behavior changed in this correction.
- Validation: Ruff passed; full suite passed with `953 passed in 23.30s` after
  rerunning with the required loopback/Chromium permissions; `git diff
  --check` passed; no files under `data/` are tracked. The initial sandboxed
  suite failed only at the documented socket and Chromium permission boundary.

## 2026-09-04 — #128: responsive Armor comparison planning session (plan PR 1)

Planning-only session for #128. No production code, test, fixture, snapshot,
or server contract changed.

- **What happened:**
  - Corrected #128 from a design-record-only issue into an implementation ticket
    with a measured planning phase and a required implementation PR.
  - Re-read the #113/#119 decision and implementation trail, current
    `armorGroupTable`, `armorMemberCell`, verdict repaint/disable paths, CSS,
    and the Node/Playwright regression tests. Reproduced the pre-#119
    member-column matrix from `fb9a435` to measure its minimum-width budget.
  - Authored `handoffs/issue-128-implementation-plan.md`, allocating
    `feat/issue-128-responsive-armor-matrix` and an independent adversarial
    review path. It was subsequently rebased onto `main` at
    `37c054a40ecbf2b79e403ab88fcf96f2156ed720` after PR #127. #127 changes
    workflow/worklog documentation only, so the measured production UI remains
    the issue #119 state at `3a9ee98b8489306b47ae56cb7bb80f0b1190325d`.
  - Ran the required browser suite with
    `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`:
    8 passed in 6.24s. The same command cannot launch Chromium inside this
    environment's filesystem sandbox (`sandbox_host_linux.cc:41`), but passed
    in the required unsandboxed verification environment; a later implementation
    must still report the required browser suite, never a skip.
  - Added a committed, isolated rendered measurement specimen at
    `docs/evidence/issue-128/responsive-matrix-probe.html` and its Playwright
    runner `scripts/measure_responsive_matrix.py`. It records the selected
    2/3/4-member transition values in CSS pixels, 390px and 1440px behavior,
    constrained-panel/zoom reflow, and conditional-field row growth.
  - Strengthened that probe so it asserts every documented precondition before
    reporting: exact container width, active orientation, document containment,
    threshold flips, and conditional 7-to-11 row growth. Added a requirement
    for a genuine test-owned three-member server input at the `45rem` boundary;
    the existing 2- and 4-member checks remain required.
- **Decisions made:**
  - Use a CSS inline-size container query on each comparison, not a viewport
    media query. The default is the current member-row table. The member-column
    table activates at `33rem`, `45rem`, or `57rem` for 2, 3, or 4 members,
    respectively: the pre-#119 comparison matrix needs an `8.5rem` comparison
    column plus `12rem` per member (`32.5rem`, `44.5rem`, `56.5rem`), with a
    0.5rem guard. Conditional same-stat fields add rows, not columns.
  - Render both semantic table shapes from one field list and let `display:none`
    hide the inactive one. This gives a no-container-query fallback of member
    rows and removes the hidden table from the accessibility tree/keyboard
    order without a stale static `aria-hidden` state. Both `armorMemberCell`
    occurrences remain registered so a CSS resize cannot surface a stale verdict.
  - Limit columns deliberately to exactly 2/3/4 members. The authoritative
    group producers have no maximum, while a live singleton is producer-
    impossible (though the exact untrusted snapshot adapter accepts non-empty
    arrays). Both a defensive singleton and 5+ groups remain in the row
    fallback at all sizes: that is safer than a growing matrix selecting a
    borrowed 2/3/4 threshold.
  - Preserve all existing copy, field labels, authoritative projections,
    grouping/ranking/rules, verdict API, and lifecycle. The work must not absorb
    #115/#116/#117 or the separate mobile tile-row question.
- **Surprises the next agent should know about:**
  - Existing tests assume one table and, in places, assume registry positions
    correspond only to exact then same-stat occurrences. Dual rendering doubles
    occurrences; tests must select by group kind/orientation and assert updates
    across every occurrence, not just `[0]`.
  - Any visible-control or badge-width assertion must scope itself to the active
    matrix. Hidden `display:none` nodes have no usable geometry and cannot
    demonstrate wrapping or keyboard behavior.
  - The original `46rem` row-table minimum would invalidate the 33rem and 45rem
    column thresholds if inherited. The implementation must override it with
    the selected column minima; the committed probe confirms all transitions
    fit exactly once opaque-id/location/badge text is allowed to wrap.

## 2026-09-03 — #124: workflow pilot outcome (orchestration session)

Ran the committed planner → orchestrator → implementer → independent adversarial
review workflow end to end on #119, its selected subject. Plan PR #125 merged;
implementation PR #126 opened. No vault-cleaner behaviour changed in this
session — the orchestration produced #119's diff, and this entry records the
pilot itself.

- **What happened:**
  - Four independent adversarial review rounds against a disposable checkout
    pinned to each immutable head. Rounds 1–3 each returned a blocking P2;
    round 4 returned no P0/P1/P2 and recommended proceeding.
  - **Every blocking finding was a missing guard, not broken behaviour.** All
    four blocking P2s (F1, F2, G1, H1) were fixed in tests alone. The
    production code from `482a63a` changed only through three accepted
    non-blocking findings: a discarded `filterItems` scan moved inside its
    surface guard (F3), an equality guard before the `aria-live` scope
    region's `textContent` write so an unchanged string is not re-announced
    (G2), and a redundant `reconcileArmorQueryForGroups` call removed from
    `renderList` (H2).
  - Eleven injected defects were confirmed caught by the suite before PR 2
    opened, including a kind-scoped denominator, the `"exact_duplicate"` token
    mix-up, a fixed column set, render-derived banner eligibility, the live
    region rebuilt inside the cleared list host, the same region replaced in
    place with its parent unchanged, and deletion of the badge wrap rule.
  - Posted #119's dispatch card retroactively and recorded the full dispatch
    record and usability gaps on #124.
- **Dispatch record:**
  - Branch `feat/issue-119-duplicate-count-hierarchy`; base
    `b8b297e2a9f0981bcf91334c7e6b16ce85fea0b6`; heads reviewed in order
    `482a63a` → `2acef1b` → `fd9af2a` → `9fdd592` → `535e3ee`.
  - Implementer round 1: Google Gemini, launched by a human operator under
    Manual Cross-Provider Execution v1; exact model ID and effort not recorded
    by the operator. Rounds 2–4: `claude-sonnet-5` in-runtime, matching the
    plan's specified tier.
  - Reviewer rounds 1–4: `claude-opus-5`, fresh context each round, read-only
    remit, requested native effort `high`.
  - **Native effort was not confirmable for either role.** The runtime
    instantiates a model but exposes no effort control, so the plan's `xhigh`
    and the matrix's `high` are unverified rather than met.
- **Decisions made:**
  - Reversed an orchestrator disposition mid-pilot. The redundant
    `reconcileArmorQueryForGroups` call in `renderList` was rejected twice on
    the grounds that it made review Check 3b locally verifiable. Round 3
    measured that removing it left the suite green *and* that no test pinned
    the ordering either way, so the rationale was defending an unchecked
    property. `AGENTS.md`'s sibling-path rule decided it: the two other
    reconcile call sites pass an `invalidated` collector so a dropped filter is
    reported, and this one did not. The call was removed and Check 3b given an
    actual test that goes red when the kind handler's ordering is inverted.
  - Deferred to the planner rather than fixed in-branch: the plan's
    Check 3e/§Tests contradiction over the singular `piece` form, the
    `<th>Member</th>` header against the design record's retired-noun rule, and
    the static panel hint at `review_server.html:71` whose replacement copy the
    design record does not specify.
- **Surprises the next agent should know about:**
  - **A plan can prescribe an assertion that cannot fail.** #119's plan required
    asserting the member badge's `scrollWidth <= clientWidth`. The badge sits in
    an auto-width `<th>` inside `.scroller { overflow-x: auto }`, so a
    non-wrapping badge grows the cell instead of overflowing itself. Deleting
    the CSS rule that fixes the ticket's headline visual defect left the entire
    suite green. Following the plan exactly shipped an unguarded defect.
  - **Three consecutive rounds each found a guard that passed by construction**
    — `emulate_media` calls with no assertion between or after them, a same-id
    re-query blind to a recreated node, and the badge check above. That is a
    pattern, not coincidence. A vacuity audit added by hand in round 3 ("for
    each assertion, name the single production change that would break it")
    found no further instances.
  - **The reviewer's read-only remit forbids mutation testing**, which is
    precisely what exposes guards that pass by construction. Rounds 1–2
    reported they could not run mutants without editing tracked files; round 3
    built its own isolated copy and immediately found the badge gap.
  - **A disposable `git worktree` has no `.venv`.** The orchestrator template's
    verification commands assume one. Falling back to the main repository's
    editable install silently tests the *wrong source tree*; a dedicated venv
    had to be built inside the checkout.
  - **No role owns the dispatch card after the plan merges.** `AGENTS.md` makes
    posting it the planner's step, but the planner's session ends when PR 1
    opens. #119's card was never posted until this pilot noticed, and had to be
    posted retroactively.
  - **Acceptance criterion 3 was not cleanly met and is not ticked.** The
    orchestrator received a supplementary brief alongside the template and
    merged plan — base/head SHAs, the allocation variance, and five targeted
    checks. Those mapped onto the plan's own likely findings and added no
    information, but this was not the "committed template and merged plan only"
    dispatch the criterion describes. A clean re-run needs a second subject
    issue.

## 2026-09-03 — #119: implementation of duplicate count hierarchy and table transposition (PR 2)

Implementation session for issue #119 under the two-PR lifecycle, following the
merged plan at `handoffs/issue-119-implementation-plan.md`.

- **What happened:**
  - Branched `feat/issue-119-duplicate-count-hierarchy` from `main` at base SHA
    `b8b297e2a9f0981bcf91334c7e6b16ce85fea0b6`.
  - Added persistent live region
    `<p id="vc-duplicate-scope" class="scope-summary" role="status" aria-live="polite"></p>`
    in `review_server.html` above `#vc-duplicate-list`.
  - Removed `shown` summary tile on the armor duplicates surface in
    `review_server.js` while retaining it untouched on the proposals surface.
  - Updated `duplicateOptions` in `review_server.js` to pluralise option labels
    using `entry.unit || "group"`.
  - Exported `duplicateScopeText` and `countGroupPieces` from `review_server.js`,
    and updated `renderList` to write the exact scope summary string to
    `#vc-duplicate-scope` (a reconcile call this bullet originally described
    `renderList` as making was removed in the third fix round below, H2 —
    reconciliation is instead guaranteed by the two callers that can change
    the group universe).
  - Updated `countArmorGroups` in `review_ui.js` to return `unit`, counting pieces
    (per member) across both exact and same-stat groups for `tuningModSlot`, and
    groups for other facets.
  - Updated `armorGroupHeader` in `review_ui.js` to prepend `p.armor-group-pieces`,
    render kind sub-line as `"Exact"` or `"Same stats · review only"`, and add the
    conditional same-stat banner based on `armorMemberCanVerdict(group, member)`.
  - Transposed `armorGroupTable` in `review_ui.js` with members as rows and comparison
    fields as columns, keeping conditional column logic intact and preserving
    `armorMemberCell` untouched in the Verdict cell.
  - Scoped badge-wrapping styling `.armor-member-heading .badge` in `review.css`
    so the global `.badge` rule is untouched, styled `.scope-summary` and
    `.armor-group-pieces` with existing custom properties, and adjusted table layout.
  - Adapted `tests/test_review_ui_js.py` to test the column-based layout, pieces counts,
    singular piece count, banner sentences, and facet units.
  - Added table-driven parameterized test in `tests/test_server_ui_js.py` covering
    all 7 selectors individually, combined ordering with all 6 parts, independent
    pluralisation, and mixed-kind filtering.
  - Added browser tests in `tests/test_server_browser.py` for four-member same-stat
    groups (`armor_same_stat_four_ui.csv`), badge wrapping without clipping,
    390x844 and 1440x900 viewport horizontal scroll invariants, light/dark mode,
    and mixed-report filtering (`armor_close.csv`).
- **Decisions made:**
  - Preserved `armorMemberCell` completely untouched, mounting it directly into the
    Verdict cell in transposed member rows, preserving DOM identities and
    `state.duplicateRows` occurrences registration.
  - Placed `#vc-duplicate-scope` outside `#vc-duplicate-list` in `review_server.html`
    so `view.clear(host)` does not destroy the live region across keystrokes.
  - **Facet-unit decision and its consequence:** the `tuningModSlot` facet counts
    pieces (one per member, for both exact and same-stat groups), while every
    other facet counts groups; `duplicateOptions` labels each with `entry.unit`.
    Consequence: the tuning facet's number stops predicting how many groups the
    filter will show — the option now answers "how many pieces have this tuning
    slot", not "how many groups". The scoped summary region
    (`#vc-duplicate-scope`) is the surface that answers the group question
    instead.
  - **Scope-suffix format:** `" — filtered to "` followed by the active parts
    joined with `", "`, in the fixed order kind, class, slot, archetype, tuning
    slot, search — e.g.
    `12 of 74 groups · 38 of 211 pieces — filtered to exact duplicates, class Titan, search "Reaver"`.
- **Surprises the next agent should know about:**
  - `ARMOR_CLOSE_EXPORT` contains 1 exact group (2 members) and 1 same-stat group
    (2 members) for a total of 4 pieces. Filtered exact/same-stat views each show
    `1 of 2 groups · 2 of 4 pieces`, cleanly exercising differing group and piece counts.
  - In Node test environments that mock `Document`, added `vc-duplicate-scope` to the
    element lookup map.

### Fix round: independent adversarial review follow-up

Independent adversarial review of `482a63a` found no P0/P1 defects, two
blocking P2 coverage gaps (F1, F2), and two accepted non-blocking fold-ins
(F3, F4). The production code from `482a63a` was found correct by that
review; F1, F2 and F4 changed tests and this worklog only, and the sole
production change was F3's performance guard in `review_server.js`.

- **F1 (blocking, test-only):** `test_armor_same_stat_four_member_badge_wrapping_and_transposition`
  called `page.emulate_media(color_scheme=...)` for dark then light with no
  assertion between or after either call, so the plan's "light and dark"
  checklist item asserted nothing theme-dependent. Added computed-style
  assertions under each scheme (`.scope-summary` `backgroundColor` /
  `borderLeftColor`, `.armor-group-pieces` `color` / `borderColor`), asserting
  non-transparent values that differ between dark and light, plus re-running
  the scroll-width and badge-clipping checks inside each scheme.
- **F2 (blocking, test-only):** `test_armor_duplicates_mixed_report_scope_summary_and_filtering`
  re-queried `#vc-duplicate-scope` by id after each kind-selector click, so an
  implementation that destroyed and recreated the region inside
  `#vc-duplicate-list` on every render (the plan's Likely Finding #1) would
  still pass. Measured: with the region moved into `renderList`/`host.appendChild`
  and deleted from `review_server.html`, all 8 browser tests and all 123 node
  tests still passed before this fix. Added an assertion that
  `el.parentElement.id === "vc-duplicates"` and that the element node identity
  (`element_handle()` equality) survives a kind-selector click. Proved the
  guard load-bearing with a temporary recreated-region variant (removed the
  `<p id="vc-duplicate-scope">` line from `review_server.html`; in
  `review_server.js` `renderList`, built the element with `view.el` and
  `host.appendChild`ed it instead of `byId` lookup): the new
  `parentElement.id` assertion failed red
  (`AssertionError: assert 'vc-duplicate-list' == 'vc-duplicates'`), then the
  variant was fully reverted with `git checkout --` and the tree confirmed
  clean against the intended change set before re-running green.
- **F3 (accepted, non-blocking):** `renderSummary` in `review_server.js`
  computed the `shown` scan of `state.items` via `ui.filterItems` on every
  render regardless of surface, even though the result is only consumed
  inside the `state.surface !== "armor-duplicates"` branch. Moved the
  computation inside that guard so it no longer runs (and is discarded) on the
  duplicates surface. Pure performance change — the proposals surface tile
  renders identically, and `tests/test_server_ui_js.py:511` (the `"shown"`
  literal assertion) is untouched and passing.
- **F4 (this entry):** the original entry omitted the facet-unit consequence,
  the scope-suffix format, and this fix round; both are now recorded above.

### Second fix round: independent adversarial review of `b8b297e...2acef1b`

A second independent adversarial review of the complete `b8b297e...2acef1b`
range found no P0/P1, one new blocking P2 (G1), and two accepted non-blocking
items (G2, G3). Production code changed only for G2; G1 and G3 are test-only.

- **G1 (blocking, test-only):** no assertion distinguished
  `armorGroupHeader`'s data-derived same-stat banner eligibility
  (`armorMemberCanVerdict(group, member)`, which reads only
  `currentProposalAction`/`isProposalMember` and never `readOnly` or the DOM)
  from a render-derived one gating on whether a verdict button would actually
  render (the #115 prior-art defect). Measured: replacing the eligibility
  check with `!readOnly && (group.members || []).some(function (m) { return
  armorMemberCanVerdict(group, m); })` left all 123 node tests and all 8
  browser tests passing (`950 passed` in the full suite run before this fix,
  since a same-stat proposing member always has a rendered `.approve` button
  under the harness's normal, non-read-only views). Added a read-only-view
  case to `test_same_stat_projection_and_cross_kind_dom_overlap` in
  `tests/test_review_ui_js.py`: a same-stat group with a member whose
  `currentProposalAction` is `"junk"`, rendered through
  `api.createView({..., readOnly: true})`, asserting both that the second
  banner sentence ("Pieces below that already carry a proposal keep their
  verdict controls.") is present and that zero `button.approve` elements
  render in that article (new key `sameBannerPresentWhenReadOnly`). Proved
  the guard load-bearing with the temporary render-derived variant above:
  the new assertion went red —
  `AssertionError: ... Differing items: {'sameBannerPresentWhenReadOnly':
  False} != {'sameBannerPresentWhenReadOnly': True}` — with the rest of the
  suite (950 of 951 tests) still green, then the variant was fully reverted
  with `git checkout -- src/vault_cleaner/ui/review_ui.js` and the tree
  confirmed clean against the intended change set before re-running green.
- **G2 (accepted, non-blocking):** `renderList` in `review_server.js` wrote
  `scopeTarget.textContent` unconditionally on every `#vc-dup-search` input
  event, so the `role="status"`/`aria-live="polite"` `#vc-duplicate-scope`
  region re-announced the whole scope line to screen readers even when the
  computed string had not changed. Guarded the assignment to only write when
  the new string differs from the current `textContent`; behaviour is
  otherwise identical.
- **G3 (accepted, non-blocking, test-only):** the `shown` tile's absence from
  the duplicates surface was pinned only by reading code — a regression that
  re-added the tile there would go undetected, since
  `tests/test_server_ui_js.py:511` (left untouched) only pins the tile's
  presence on the proposals surface via a source-literal check. Added a
  negative assertion in
  `test_armor_duplicates_mixed_report_scope_summary_and_filtering` in
  `tests/test_server_browser.py`: `#vc-summary .tile .k:text-is('shown')`
  has count 1 on the proposals surface (asserted first, before switching) and
  count 0 after switching to the duplicates surface, proving a surface
  distinction rather than the absence of a string anywhere on the page.

### Third fix round: independent adversarial review of `b8b297e...fd9af2a`

A third independent adversarial review of the complete `b8b297e...fd9af2a`
range found no P0/P1, one blocking P2 (H1), and three accepted items (H2,
H3, H4). Production code changed only for H2 (a reversal of a decision this
worklog previously recorded as rejected); H1, H1b, and H3 are test-only.

- **H1 (blocking, test-only):** the three badge non-clipping assertions in
  `test_armor_same_stat_four_member_badge_wrapping_and_transposition`
  (`tests/test_server_browser.py`) read `el.scrollWidth <= el.clientWidth`
  on the badge itself — true by construction, since the badge sits in an
  auto-width `<th>` inside `.scroller { overflow-x: auto }`: a non-wrapping
  badge simply grows the cell rather than overflowing itself, so the check
  cannot fail regardless of whether `.armor-member-heading .badge`'s
  `white-space: normal; overflow-wrap: anywhere` rule (`review.css:180`)
  is present. Measured: deleting that CSS rule left all 8 browser tests and
  all 951 non-browser tests passing before this fix. Replaced all three
  occurrences with `badge_width_and_heading_budget`, comparing the badge's
  `offsetWidth` against its `.armor-member-heading` container's *fixed*
  `min-width` (11rem/176px, from a separate, untouched selector, so it does
  not grow with the badge's content the way the heading's own `offsetWidth`
  does). Proved the new assertion load-bearing by deleting `review.css:180`
  and re-running: it failed red (`AssertionError: badge 0 exceeded its
  heading's 176.0px width budget: 252.0px`), then `review.css` was fully
  reverted with `git checkout --` and confirmed unchanged in the final diff
  before re-running green.
- **H1b (vacuity audit, test-only):** audited every assertion this ticket
  added across `tests/test_server_browser.py`, `tests/test_review_ui_js.py`,
  and `tests/test_server_ui_js.py` in the `b8b297e...HEAD` range for the same
  "passes by construction" class as H1, F1/F2, and G1. Found no further
  vacuous assertion: the remaining checks are string/attribute/count
  equalities tied 1:1 to a specific production value (scope text, piece
  counts, `role`/`aria-live` attributes read from `review_server.html:72`,
  column-header presence after the row-to-column transposition, theme
  computed-value differences from F1, and the region-identity/read-only-view
  checks from F2/G1) — each one requires a distinct, identifiable production
  change to fail. The H2 and H3 fixes below each added a new assertion;
  both were proved load-bearing by an explicit inverted-ordering mutation
  (see their entries).
- **H2 (accepted — reverses this worklog's F3-adjacent prior rejection):**
  `renderList` called `reconcileArmorQueryForGroups(state.armorQuery,
  selectedArmorGroups)` on every duplicates render, with no `invalidated`
  collector — unlike its two sibling call sites (`applySessionEnvelope` and
  the kind-selector click handler), which both report a dropped filter via
  `state.viewInvalidated`. This implementer had rejected the same finding
  twice in earlier rounds; three independent reviews flagging it, plus
  `AGENTS.md`'s sibling-path rule, changed that. Removed the call: the
  kind-selector handler already reconciles `state.armorQuery` for the new
  kind's group universe before it calls `renderList`, and `renderList` is
  the only caller that can change `state.armorGroupKind`'s selected universe
  without a prior reconcile, so the scope suffix `renderList` computes never
  names a facet value the current universe has already dropped. Extended
  the existing `test_local_duplicate_kind_switch_renders_filter_reconciliation`
  in `tests/test_server_ui_js.py` with a `scope` field capturing
  `#vc-duplicate-scope`'s textContent after the kind-selector switches from
  `same_stat` (with `tuningModSlot: Health` set) to `exact` (where `Health`
  no longer exists): asserted it reads `"1 of 2 groups · 1 of 3 pieces —
  filtered to exact duplicates"` with no mention of `Health`. Proved
  load-bearing by temporarily moving
  the click handler's `renderControls(); renderList(); renderSummary();`
  call to before its `reconcileArmorQueryForGroups` call (simulating the
  now-removed `renderList`-side reconcile no longer covering this path): the
  assertion went red (`'0 of 2 groups · 0 of 3 pieces — filtered to exact
  duplicates, tuning slot Health'` instead), then the variant was fully
  reverted with a diff against the pre-mutation copy and confirmed clean
  before re-running green.
- **H3 (accepted, test-only):** `renderList` writes the scope text to
  `#vc-duplicate-scope` before its `if (!filteredGroups.length) { ...;
  return; }` early return, but nothing pinned that ordering — a filter
  matching nothing could regress to leaving the region stale or blank.
  Added `test_duplicate_list_states_scope_before_the_empty_result_hint` in
  `tests/test_server_ui_js.py`: a search matching no groups still leaves
  `#vc-duplicate-scope` reading `"0 of 2 groups · 0 of 3 pieces — filtered to
  search \"no-such-armor-piece\""` alongside the `"No armor duplicate groups
  match these filters."` hint. Also added a "no matches" case to the
  existing `test_duplicate_scope_summary_formats_exact_table` parametrized
  suite pinning `duplicateScopeText`'s zero-match formatting in isolation.
  Proved the DOM-level test load-bearing by temporarily moving the scope
  write in `renderList` to after the early return: it failed red (`'2
  groups · 3 pieces' == '0 of 2 group...-armor-piece"'`, i.e. the write was
  skipped entirely on the empty-result path), then the variant was fully
  reverted and confirmed clean before re-running green.
- **H4 (open question carried forward, not built):** the plan's out-of-scope
  list flagged collapsing the four-member tile row at 390px as worth its own
  look during #119, and instructed raising rather than building it. It was
  correctly not built in the implementation, but the review found it was
  never raised anywhere reaching the PR. Recording it here per that
  instruction: collapsing the tile row layout at the 390px viewport remains
  an open question for a follow-up ticket, out of scope for #119.

## 2026-09-03 — #119: planning session (plan PR 1)

Planning-only session under the new two-PR lifecycle. Authored
`handoffs/issue-119-implementation-plan.md` from
`handoffs/templates/planner.md` against `main` at `91a4e5b`. No production code
changed. #119 was selected as the subject of the #124 workflow pilot because it
is the only one of the four candidate issues (#115, #116, #117, #119) whose
design direction is already settled, so it produces a real implementation diff
for the independent adversarial reviewer rather than a decision record.

- **What happened:**
  - Measured the Armor duplicates surface against the plan baseline and pinned
    every claim to a current file and line: the `SHOWN` tile
    (`review_server.js:838-839`), the `Showing N of M groups` hint
    (`review_server.js:995-998`), `armorGroupHeader` (`review_ui.js:1043-1067`),
    `armorGroupTable` (`review_ui.js:1126-1197`), `memberValues`
    (`review_ui.js:1034-1042`) and `countArmorGroups` (`review_ui.js:626-645`).
  - Confirmed piece counts need no snapshot schema change: both armor group
    projections already carry a non-empty `members` array, so a piece count is
    `group.members.length`. No golden regeneration and no `_decision_config`
    key.
  - Inventoried the six existing assertions that pin strings this work deletes
    (`test_review_ui_js.py:1267,1294,1297`, `test_server_ui_js.py:2272`,
    `test_server_browser.py:333`) so the implementer adapts rather than deletes
    them, and flagged that `test_server_ui_js.py:511` must stay untouched
    because the `shown` tile survives on the proposals surface.
  - Allocated `feat/issue-119-duplicate-count-hierarchy`, selected
    `claude-sonnet-5` at native `xhigh` effort from the Complex Implementation
    row of the model matrix, and recommended the `independent adversarial
    review` path.
- **Decisions made:**
  - **Scope suffix format.** The #113 decision record specifies only the kind
    case (`— filtered to exact duplicates`), but the surface has four facets and
    a search box. The plan fixes a deterministic suffix — `" — filtered to "`
    plus ordered parts `exact duplicates` / `same-stat groups`, `class V`,
    `slot V`, `archetype V`, `tuning slot V`, `search "V"` — so the copy is
    testable for every filter combination rather than only the documented one.
  - **Facet units.** The `tuningModSlot` facet will count pieces for *both*
    group kinds, and every other facet counts groups; entries gain a `unit`
    field that `duplicateOptions` pluralises from. Counting pieces only for
    same-stat groups was rejected because one facet value can be fed by both
    kinds, which leaves that option's unit indeterminate. Consequence recorded
    for the PR: the tuning facet's number stops predicting how many groups the
    filter will show; the scoped summary region is what answers that.
  - **Live region placement.** The scoped summary is static markup
    (`#vc-duplicate-scope`) in `review_server.html`, outside `#vc-duplicate-list`,
    updated by `textContent`. `renderList` clears the list host on every
    keystroke, and a live region removed and re-inserted is not reliably
    announced.
- **Surprises the next agent should know about:**
  - **#119's body is stale in two ways that matter.** Item 11 names
    `"Exact duplicate group · " + group.groupKind` as the string its kind label
    replaces, but #118 (PR #121) already removed that concatenation; the real
    target is the plain sub-line at `review_ui.js:1050-1052`. Item 13 is
    partly landed too — #118 added the `group`/`groups` pluralisation, so
    `Melee (1 group)` already renders. What actually remains is the wrong noun
    on member-derived tuning counts.
  - **The #118 coordination clause resolved itself.** #119 says "whichever
    lands second rebases"; #118 landed first, so #119 rebases onto it, and its
    three fixes (the `Protection` header, the leaked enum, and the 390px
    fingerprint overflow, fixed via `overflow-wrap: anywhere` on
    `code, .mono, kbd`) are regression guards this work must not undo.
  - **The node test harness assumes members are columns.** `findRow` and
    `cellTexts` in `test_review_ui_js.py` walk the current layout, so the
    transposition forces them to be reworked — which is exactly where a #118
    guard could be silently weakened while the suite still passes.
  - Chromium and node are present on the plan host, so
    `VAULT_CLEANER_BROWSER_REQUIRED=1` genuinely runs the browser suite here; a
    skip in an implementer report means the variable was not set.
- **Corrections made during plan review (same session, before merge):**
  - **Baseline reproduction was self-staling.** The plan told the reader to
    reproduce its measurements with `git rev-parse origin/main`, which stops
    reporting `91a4e5b` the moment the plan merges. Now pinned to
    `git show 91a4e5b:<path>` with an explicit instruction that the implementer
    re-measures from its own base and treats the named function or literal, not
    the line number, as authoritative.
  - **The scope-suffix table named the wrong vocabulary.** It listed the kind
    source as `exact_duplicate`, which is a group's `groupKind`. The selector
    stores `"all" | "exact" | "same_stat"`
    (`review_server.js:872-873`), so an implementer following the table
    literally would have compared against a token that never matches and the
    `exact duplicates` clause would have silently never rendered while the rest
    of the line looked right. Only `same_stat` is spelled the same in both
    vocabularies, which is what makes the trap easy to walk into. Added as
    likely finding 5 and checklist item 3a.
  - **Suffix test coverage was one case for seven inputs.** Because the suffix
    format has no source outside this plan, its test is the specification rather
    than a guard; a single filtered case would pass with six parts missing. Now
    a parametrised table, one case per selector plus a combined ordering case.
  - Also recorded: the suffix must be built from the query *after*
    `reconcileArmorQueryForGroups` clears facets that no longer exist, and a
    single-kind report cannot distinguish a correct denominator from a
    kind-scoped one because the kind selector only renders when both kinds are
    present.
  - **Second review round.** The corrected test matrix drew two further
    findings, both accepted in substance. The combined ordering case activated
    only four of the six renderable suffix parts, which leaves the relative
    order of the omitted facets unpinned — an implementation emitting
    `tuning slot` before `archetype` would never be exercised; it now activates
    all six. The cardinality row was `1 group, 1 piece`, which does not prove
    the two nouns pluralise independently.
  - **Partially rejected, with evidence.** The suggested companion cases
    `2 groups · 1 piece` and any `1 piece` state are unreachable: both duplicate
    passes skip groups with fewer than two members
    (`armor_dupes.py:306`, `armor_close.py:131`, `armor_close.py:290`), so
    pieces is always at least twice groups. `1 group · 2 pieces` is therefore
    both the smallest reachable report and the only case that catches a shared
    plural suffix computed from one number, and it is the one the plan now
    requires. The singular `piece` form, if covered at all, belongs in a direct
    unit test of the pluralisation helper rather than a fabricated report state.
    Recorded because it is easy to re-derive the same impossible case later.
  - **Template gaps for #124.** Two of the three corrections generalise beyond
    this plan. `planner.md` requires claims to be pinned to a path and line or
    an empirical command, but does not require that command to be
    baseline-pinned; and it requires exact copy to be stated verbatim, but has
    no clause requiring copy a planner *invents* to carry a matching test
    obligation. A third candidate clause: quote state tokens from the source
    line rather than from prose.

## 2026-09-03 — #122: integrated multi-agent handoff workflow into repository

- **What happened:**
  - Integrated the multi-agent handoff workflow under `handoffs/` on `main`. Created `handoffs/README.md` defining the orchestrator-owned topology (`planner → orchestrator → implementer → orchestrator-managed review → PR`), document lifecycle (two-PR process), naming convention (`handoffs/issue-N-implementation-plan.md`), model tier selection rules, manual cross-provider execution boundary (v1), and stop-condition escalation routing (`implementer → orchestrator → planner`).
  - Added a provider-native model family and reasoning-effort matrix in `handoffs/README.md` documenting task classes and native effort controls (`reasoning.effort` for OpenAI, `output_config.effort` for Anthropic, `thinking_level` for Gemini), with exact current model IDs and per-model support notes. Corrected the Google rows after re-verification: complex work uses preview `gemini-3.1-pro-preview`, stable `gemini-3.8-flash` excludes unsupported `minimal` thinking, and the stable cost-oriented entry is `gemini-3.5-flash-lite`.
  - Committed operational templates: `handoffs/templates/planner.md` (directs planner agents to plan issues, resolve staleness, use relative links, select native model effort, nest markdown examples within four backticks, and emit the named-section contract) and `handoffs/templates/orchestrator.md` (boots orchestrator agents to read merged plans from `main`, dispatch implementers, enforce browser suite execution with `VAULT_CLEANER_BROWSER_REQUIRED=1`, conduct isolated worktree revert spot-checks, and handle findings/escalation).
  - Migrated and normalised 10 historical handoffs onto `main` under `handoffs/issue-N-implementation-plan.md`, retiring `luna` and `xhigh` filename suffixes and correcting #118's self-description. Restored the 10 source `handoff/*` branches on `origin` until PR merge.
  - Narrowed `.gitattributes` whitespace exception rules from a blanket wildcard to the exact 10 migrated historical handoff files.
  - Updated `AGENTS.md` to document the Planning Phase (PR 1) ahead of implementation, formalising the 3-role workflow, template paths, repo-relative links, dispatch comment requirements, worklog entry content contract, and escalation routing.
  - Validated planner-template usability against open Issue #119; split out the #119 plan from this PR so #119 lands via its own planning PR as the new lifecycle requires.
  - Moved the full post-merge, no-hand-written-brief workflow pilot to follow-up Issue #124, which is blocked by #122 and tracked as `Todo` on the project board. This keeps #122's integration PR honest about what has and has not been exercised while preserving the real end-to-end acceptance check.
  - Added review path decision criteria (Standard Orchestrator Review vs. Independent Adversarial Review) across `AGENTS.md`, `handoffs/README.md`, `planner.md`, and `orchestrator.md`. For high-risk, complex, or sensitive changes, the orchestrator now selects and records the reviewer's exact provider/model/native effort after inspecting the real diff, applies the same manual cross-provider fallback as implementer dispatch, and sends a fixed findings-only prompt to a fresh read-only reviewer session. Any repaired head returns to an independent reviewer for a complete-diff re-review.
  - Hardened independent review after PR feedback: the orchestrator now supplies a detached disposable checkout pinned to the reviewed head, the reviewer independently reruns verification while limiting writes to ephemeral test artifacts, and the prompt explicitly treats a skipped required browser suite as a failure. Defined P0-P3 severity and blocking semantics plus auditable `accepted/fixed`, evidence-backed `rejected`, and owner-approved `deferred` dispositions, including escalation for unresolved blocking disagreements.
- **Decisions made:**
  - Standardised on two PRs per issue: Plan PR merged to `main` first, followed by Implementation PR.
  - Established manual cross-provider execution for v1: orchestrators verify runtime support or prepare prompts for operator dispatch without automated multi-provider harnesses.
  - Defined reviewer read-only status as no tracked implementation or durable repository mutations, rather than a filesystem restriction that prevents independent test execution.
  - Retained intentional Markdown hard line breaks in historical handoffs via narrow `.gitattributes` rules rather than stripping trailing spaces.
- **Surprises the next agent should know about:**
  - Browser tests in `test_server_browser.py` skip silently when managed Chromium is absent unless `VAULT_CLEANER_BROWSER_REQUIRED=1` is set; the orchestrator template now specifies this environment variable directly.
  - Relative links in GitHub issue comments resolve relative to the issue URL (`/issues/handoffs/...` -> 404), so the planner's dispatch comment draft must emit an absolute GitHub `blob/main/...` URL rather than a relative path.

## 2026-09-03 — #118: fix mislabelled and overflowing review UI text

Implemented the four presentation defects from #118, per the committed
handoff `handoffs/issue-118-implementation-plan.md` on
`fix/issue-118-review-ui-labels`, branched from `main` at `95b9706` (unchanged
since the plan baseline). Presentation-only: no Python rule, grouping,
ranking, survivor selection, report/server contract, persistence, verdict,
reconciliation, finalisation, lifecycle or authentication change.
`report_run.RULESET_VERSION` is untouched and no snapshot golden was
regenerated.

- **Defect 1 — contradictory protection label.** `review_ui.js`'s
  `armorGroupTable` row list renamed `"Hard protection"` to `"Protection"`;
  the cell function was already correct (level plus `" — " + reason` when a
  reason exists, `"—"` otherwise) and was left untouched.
- **Defect 2 — leaked internal enum.** The exact-group sub-line in
  `armorGroupHeader` now reads the plain literal `"Exact duplicate group"`,
  dropping the appended `group.groupKind`. The `same_stat` branch
  (`"Same stats, different tuning · review-only"`) is byte-identical to
  baseline, and the two non-display `groupKind` uses —
  `data-group-kind`/`data-group-id` and `armorMemberDomIdentity` — were
  confirmed to survive (searched for every `groupKind`/`group_kind`/
  `disposition` concatenation into display text; `dispositionLabel` already
  maps every validated disposition value to human-readable text and was not
  touched).
- **Defect 3 — horizontal overflow at 390px, two independent causes.** Added
  `overflow-wrap: anywhere` to the existing `code, .mono, kbd` rule
  (`review.css:52`, the fingerprint fix) and to the existing
  `.armor-group-header h3` rule (`review.css:151`, the hostile armour-name
  fix). The second cause is **not named in the issue body** — PR #120 and
  `docs/evidence/issue-113/README.md:101-118` record it as tracked under
  #118 without that ever reaching the issue text; it is fixed here per the
  handoff's resolution of that gap. No `#vc-fingerprint` id selector was
  added; `review.css` still has none. `.mono` also reaches the instance-id
  span in armour member headings and the Proposals surface's `code`/`.mono`
  cells — checked manually (see below): no visible regression, since a
  19-digit id does not reach the wrap threshold at the existing min-widths.
- **Defect 4 — facet counts didn't state their noun.** `duplicateOptions` in
  `review_server.js` now renders `entry.value + " (" + entry.count + " " +
  noun + ")"` with `noun` computed once (`"group"`/`"groups"`) for all four
  duplicate facets (`guardianClass`, `type`, `itemArchetype`,
  `tuningModSlot`) — e.g. `Melee (1 group)`, `Chest Armor (2 groups)`. This
  is the copy already decided in `docs/duplicate-review-count-design.md` §3
  change 6 (carried as #119 scope item 13), implemented here per the
  handoff's resolution of the issue's staleness on this point:
  **#119 should drop copy change 6 / scope item 13 on rebase, since it is
  already shipped.** `optionsFor` (the Proposals surface's item-count
  facets, `review_ui.js:767`) is untouched; its pinned
  `"weapons (2)"`-style output (`tests/test_review_ui_js.py:361`) still
  passes, and a live manual check (below) confirmed the Proposals surface
  still renders noun-free counts such as `weapons (5)`.
- **Deliberately not adopted:** #119's paired `Exact` / `Same stats · review
  only` kind-label relabelling. Adopting only the exact half here would
  leave `Exact` beside an unchanged `Same stats, different tuning ·
  review-only`, worse than either endpoint; #119 replaces both together.
- **Measured 390×844 `document.documentElement.scrollWidth`,** own run
  against a packaged local server with `tests/fixtures/armor_same_stat_ui.csv`:
  **550 before, 390 after** — matching the plan's own measurement exactly.
- **Tests.** Extended the existing armour-group DOM harness
  (`test_same_stat_projection_and_cross_kind_dom_overlap`,
  `tests/test_review_ui_js.py`) with six new probes in its exact-JSON-equality
  assertion: the exact sub-line text and the absence of any leaked
  `exact_duplicate`/underscore token; the same-stat sub-line unchanged; a
  `Protection` row header present (and no `Hard protection` header) in both
  the exact and same-stat articles; and the protection cell still rendering
  level+reason together and `"—"` alone, driven by new `protection_level`/
  `protection_reason` fields added to that test's fixture members. Added a
  sibling test `test_duplicate_facet_options_state_the_counted_noun` in
  `tests/test_server_ui_js.py` asserting rendered option text (not just
  counts) across all four duplicate facets, singular and plural, plus the
  unchanged noun-free `allLabel` option. Added
  `test_duplicates_surface_does_not_scroll_horizontally` in
  `tests/test_server_browser.py` — the first test in that file to set a
  viewport — asserting no horizontal document overflow at both 390×844 and
  1440×1000, that the fingerprint still renders its digest, and that
  `article.armor-group h3`'s computed `overflow-wrap` is `anywhere` while
  `article.armor-group .scroller`'s computed `overflow-x` stays `auto`
  (overflow fixed by wrapping, not by removing the contained scroll). Every
  new/extended assertion was observed to fail against the pre-fix source
  (via `git stash` on each production file in turn) and pass after
  reapplying the fix, for all four defects including the browser test.
- **Manual verification**, packaged server with `--no-wishlists`, headless
  Chromium (Chrome for Testing 151.0.7922.34, Playwright Chromium revision
  1234), fake fixtures only (`armor_duplicates_ui.csv`,
  `armor_same_stat_ui.csv`, `weapons_hostile.csv`): confirmed the skip link
  is the first tab stop from a fresh load, the `:focus-visible` ring renders
  (`outline-style: solid`) during interaction, `Protection`/`Exact duplicate
  group`/`(N group(s))` copy renders correctly at 1440×1000 in light and
  dark, no horizontal overflow at 390×844 or 1440×1000 in either theme, the
  Proposals surface's facet options remain noun-free
  (`weapons (5)`/`Hunter (2)`), and finalised state remains readable (the
  `Protection` label and same-stat sub-line still render, both verdict
  buttons on the finalised group are disabled) and Shutdown ends the
  session cleanly.
- Ran the full focused/browser/full/diff/hygiene gate from the handoff:
  `ruff check` clean; `pytest -q tests/test_review_ui_js.py
  tests/test_server_ui_js.py` 112 passed; `node --check` clean on both JS
  files; `pytest -q -m browser tests/test_server_browser.py` 6 passed
  (5 pre-existing + 1 new); full `pytest -q` 938 passed; `git diff --check`
  clean; `git ls-files data/` empty; `git status --short` shows exactly the
   eight files in the plan's expected footprint.

## 2026-09-03 — #113 fifth review round: the narrow comparison was not a comparison

- **The narrow harness compared A without a tile row against B with one.**
  Alternative A deletes only the `SHOWN` tile, so it keeps four; the harness gave
  it none. That is not a mis-measurement, it is two different things being
  measured and the difference reported as a result. It made A look compact by
  omitting a component it actually has, and it reversed the conclusion.
- Rebuilt the harness as a **thin production shell**: it links the real
  `src/vault_cleaner/ui/review.css` and reuses `main.wrap` / `section.panel` /
  `.tiles`, with only treatment-specific rules layered on. Both alternatives now
  carry complete content.
- Added `scripts/measure_narrow_specimens.py`, which **asserts its preconditions
  before reporting**: viewport is really 390px, the document does not scroll
  sideways, panels sit at the production width, both specimens carry four tiles,
  and no remote request is made. The panel-width assertion immediately caught a
  wrong expectation of mine — `review.css:166` drops `.wrap` padding to `.6rem`
  at ≤640px, so a panel is 370.8px, not 358px.
- **True figures: A 652px, B 617px — B is the more compact**, the opposite of the
  previous entry's claim. The difference is A's 62px scope line.
- **The "B's expanded tile row" reasoning was empty all along.** At ≤640px
  `review.css:167` sets `.tile { min-width: 100% }`, so all four tiles stack full
  width and the tile row is **413px in both treatments**. It was never a
  differentiator, and the decision text had been leaning on it.
- Re-evaluated rather than renumbered: the narrow criterion now favours B, so
  measurement *weakens* the recommendation by one criterion of eight rather than
  strengthening it. The hybrid still stands on single-authoritative-scope, one
  live region, and no paired numbers to keep in sync, and now says plainly that
  it buys those for 35px of height.
- New, and larger than either treatment: four stacked tiles occupy 413px of an
  844px viewport before any group is reached, and the live surface has five.
  Recorded as an open question for #119.
- Replaced `aria-pressed` on static `span` chips with `data-selected` in both the
  harness and the comparison document — `aria-pressed` is toggle-button state and
  these have no button semantics.
- **Worth knowing:** four attempts at one number produced four answers. What
  finally worked was not more care, it was a script that refuses to print a
  height until the layout it is measuring is demonstrably the production one.

## 2026-09-03 — #113 fourth review round: measured 390px properly

- **The previous entry's "measurement" was invalid, twice over.** Setting a
  nested `.vc` to `width:390px` inside a 1180px document does not reproduce a
  390px viewport: no narrow media query activates, and the surrounding padding
  changes the content width. Measuring the same page at a genuine 390px viewport
  is also wrong — its own `.wrap` and `.stage` padding take ~67px, leaving the
  specimen 241px.
- Added `docs/evidence/issue-113/narrow-390-specimens.html`, a committed harness
  holding the two treatments with no document chrome, so each gets the full
  width at 390×844. It reuses the artifact's `.vc` token block verbatim so the
  two cannot drift, and drops the 30rem `min-width` the comparison page sets —
  that is an authoring convenience for desktop reading, not a property of either
  treatment, and it was itself forcing a 480px overflow at 390px.
- True figures: neither treatment overflows; **A is 248px, B is 371px**, B's tile
  row stacking to 178px. The earlier 235/358 pair was directionally right by
  luck. The conclusion and the recommendation are unchanged.
- Restored newest-first worklog order, which had drifted as entries were
  prepended against inconsistent anchors. CodeRabbit flagged the ordering but
  proposed moving the newest entry to the end, which is backwards for this file.
- #119's acceptance criterion still described the whole same-stat banner as
  conditional; narrowed to the verdict-controls sentence only.
- **#113 formally amended** to waive the paired-design-skill prerequisite and
  narrow its acceptance criterion, rather than leaving a documented exception
  against an unchanged issue.
- **Worth knowing:** measuring a responsive claim requires the component at the
  width it will really have, with no enclosing chrome and no authoring-only
  constraints. Three attempts here produced three different numbers, all from
  the same markup.

## 2026-09-03 — #113 third review round: measured the narrow claim

- **A comparison row asserted something the specimens could not show, and the
  measurement reversed it.** The table scored "fits 390px" as a win for B on the
  reasoning that tiles and chips stack, while `.vc` carried `min-width:30rem`, so
  no specimen could render below 480px at all. Added specimens constrained to
  exactly 390px and measured: neither treatment overflows, and **A is the more
  compact** — a 235px block against B's 358px, because stacking B's tile row
  costs 178px. The recommendation is unchanged and better supported, since the
  hybrid takes A's line and declines B's expanded tile row.
- Alternative B's "what it costs" prose described a specimen that was never
  built — "the same numbers appear in three places", "two tiles count groups and
  two count proposals" — where the specimen has one Groups, one Pieces, one
  Proposals and one Reviewed tile. Rewritten against what is actually rendered:
  the real duplication is pairs (`12` in tile and chip, `74` in tile and chip).
- #119 was internally contradictory: settled item 5 still carried the original
  conditional-banner rule while item 12 carried the corrected two-part rule.
  Item 5 now defers to item 12.
- **Worth knowing:** the recurring failure across three review rounds was not the
  design, which has not moved. It was claims outrunning evidence — artifacts
  described but not committed, prose describing a specimen that was not built,
  and a responsive claim asserted rather than measured. Where a document argues
  from evidence, every comparison row needs to name whether it was measured.

## 2026-09-02 — #113 second review round: specimen coherence

- **The Exact-filtered specimens listed a same-stat group.** Both alternatives
  were captioned "filtered to Exact", set the Exact chip pressed, and carried a
  scope line reading "filtered to exact duplicates" — while rendering a
  `Same stats · review only` group underneath. A self-contradiction, in a
  document whose subject is filter and count coherence. Exact-filtered specimens
  now list only exact groups, and the kind hierarchy moved to a new unfiltered
  specimen, which is the state where both kinds legitimately appear. Added a
  rendering assertion for it rather than trusting the eye.
- The committed `count-treatments.html` still carried the pre-correction banner
  copy and the superseded denominator wording, so it contradicted the design
  record it illustrates. Synced.
- Made that file a standalone document: it had been authored for a publisher
  that supplies the wrapper, so committing it as-is left no doctype and put it
  in quirks mode. It also pulled fonts from a remote host on open. Now has a
  doctype and head, uses system font stacks, and makes zero network requests —
  verified by asserting no non-`file://` request during render. Stills
  re-rendered so they match.
- **Worth knowing:** an artifact authored for one delivery target is not
  automatically fit to commit. Doctype, wrapper elements, and remote assets are
  all supplied by a publisher and all absent from the repo copy.

## 2026-09-02 — #113 PR review corrections

- **Banner logic error, caught in review.** The specified same-stat banner was
  conditional on a group having *no* proposals, yet its second sentence
  described members that *do* carry one. Those cannot both hold, and the
  committed four-member fixture has proposals on every member — so the banner
  would never have rendered for the canonical evidence case. Split it: the
  no-survivor sentence is unconditional, and the verdict-controls sentence is
  appended only when a member carries a proposal. Also replaced `Members` with
  `Pieces`, which the same decision had already retired.
- Committed the artifacts the record referenced but had left uncommitted: the
  160-entry count and label inventory, the alternatives prototype
  (`count-treatments.html`) and rendered stills of both treatments. The design
  record and #119 previously linked a file that did not exist in the repo.
- Completed the evidence matrix. Both viewports are now captured in both
  appearances, rather than a subset presented as a complete set, and empty-state
  and keyboard/focus results are recorded.
- Recorded the design-skill pairing honestly: `ux-audit` covers audit and copy
  but refuses greenfield work, and the exploration half used `artifact-design`,
  already present in the environment rather than installed for this ticket. That
  is a deviation from #113's user-scoped prerequisite and is now stated as one.
- Defined the piece denominator in the copy: both figures count group members,
  measured identically, and pieces in no duplicate group are counted by neither.
  The open question is narrowed to what happens once member-level filters exist.
- **New, from the empty-state capture:** `Showing 0 of 2 groups` is the one case
  where the already-filtered denominator is genuinely useful, which the
  replacement line should preserve. The empty message also names no filter and
  offers no way to widen — recorded for #119.

## 2026-09-02 — #113 duplicate report count and hierarchy design pass

- Design pass only: no Python rule, report contract, or server contract
  changed. Decision record and handoff in
  [docs/duplicate-review-count-design.md](docs/duplicate-review-count-design.md);
  baseline captures in [docs/evidence/issue-113](docs/evidence/issue-113/README.md).
- Installed the required global design/audit skill at user scope — `ux-audit`
  1.4.0, MIT, commit `f07ff760…` — via the skill-installer workflow. Nothing
  committed to this repo. #113 names `~/.codex/skills`; this work ran in Claude
  Code, so it went to both that path and `~/.claude/skills` from the same pinned
  commit. Rejected candidates recorded, including microsoft/skills
  `frontend-design-review`.
- Added `tests/fixtures/armor_same_stat_four_ui.csv`, the #112 four-member
  evidence shape as fake data (Reaver / Titan chest / tier 5; tunings Melee,
  Class, Super, none-unknown), plus a projection test pinning it. No fixture
  previously had a group larger than three, so nothing could exercise a complete
  multi-member group.
- **Decision:** one authoritative scoped summary line above the list, plus a
  per-group piece count and a conditional review-only banner. `SHOWN` leaves the
  duplicates surface. `pieces` becomes the single user-facing noun; `copies`,
  `items` and `members` are retired from user-facing text. Six exact copy
  changes are specified. Implementation is #119.
- **Decision:** transpose the comparison table so members are rows. At 390px the
  current member-as-column layout shows exactly one member, so comparing needs
  horizontal scrolling inside the table. Any implementation must carry over the
  existing conditional-column behaviour in `memberValues`.
- Split out of #113 as separate issues: #115 per-group bulk verdicts, #116
  exposing an armor score, #117 the DIM query builder, #118 baseline defects.
  All four came from a prototype whose features #113's guardrails exclude.
- **Surprise, worth knowing:** `Showing N of M groups` has an already-filtered
  denominator. `M` is the count *after* the kind selector, so both numbers move
  together and the string can never show that groups of another kind exist. The
  reported `Showing 2 of 74 groups` means "2 of the 74 groups of the currently
  selected kind" — a third reading nobody had proposed.
- **Surprise:** every member of a same-stat group can carry a live proposal and
  render verdict controls, so same-stat groups are not a verdict-free surface.
  Any copy asserting "nothing is proposed" here is wrong in the common case.
- **Surprise:** hostile-text rendering is inert (no dialog fired, no injected
  element reached the DOM), but a 180-character unbroken item name gives the
  page a 2266px scroll width at a 390px viewport. `article.armor-group h3` has
  no `overflow-wrap`, though `review.css` already applies `anywhere` to
  `.armor-member-heading .sub` and `.detail dd`. Tracked in #118.
- Baseline behaviour confirmed good and not to be regressed: `.scroller`
  overflow handling, the `:focus-visible` ring and skip link, light-by-default
  theming, and zero-base-stat suppression. An earlier code-only reading had
  wrongly flagged all four; rendering corrected it.

## 2026-09-01 — #112 second PR review corrections

- Namespaced rendered armor member `data-member-id` attributes by validated
  group kind while keeping the opaque source id unchanged in snapshot,
  verdict, and duplicate-row state. Approve, Veto, and Unset labels now
  distinguish exact-duplicate controls from same-stat controls and retain the
  member id.
- Updated browser selectors and added a renderer regression covering a member
  legitimately present in both group kinds, including unique rendered ids and
  accessible control names.
- A kind switch now replaces invalidation state only when it drops a local
  filter; with no drop, an existing server reconciliation notice remains
  visible and intact. The existing local-drop behavior remains covered, with
  a complementary no-drop regression.
- No grouping, ranking, proposal correlation, verdict semantics, or the older
  proposal-index refactor changed. No browser production test was added.

## 2026-09-01 — #112 PR review corrections

- Made exact duplicate projection strict about the authoritative
  `group_kind: exact_duplicate` value; malformed or missing values now reject
  the complete envelope before presentation adoption.
- Preserved raw Tuning Stat distinctions only when they collapse into fewer
  normalized Tuning Mod Slot values, and namespaced rendered `data-group-id`
  attributes by validated group kind while leaving source ids opaque.
- Added a shared reconciliation renderer and local All / Exact / Same stats
  reconciliation path so dropped duplicate filters are immediately visible,
  stale server invalidations are not carried forward, and selector focus is
  restored.
- Added focused Node-backed regressions for the hostile exact envelope, raw
  tuning rendering, cross-kind DOM ids, and local filter invalidation. No new
  Playwright test was added; no Python rules, report schema, server protocol,
  lifecycle, runtime dependency, or `data/` content changed. GitHub review
  comments could not be fetched because the API was unreachable.
- Validation: Ruff passed; focused UI/adapter tests passed (`110 passed`);
  full suite passed (`934 passed, 1 skipped`); non-editable wheel proof passed;
  focused #110 Chromium passed (`1 passed`); full browser marker passed (`5
  passed, 929 deselected`); diff whitespace and tracked-`data/` checks passed.
  The first full-suite attempt was blocked only by sandbox socket/Chromium
  permissions and was repeated successfully with approved escalation.
- Follow-up review correction aligned the tuning renderer regression with
  Python's projection: empty and future raw values both use
  `tuning_mod_slot: none/unknown`, so the test now requires one raw Tuning Stat
  row and verifies the future raw text appears in that row.

## 2026-09-01 — #110 PR real-export evidence

- Added the vault owner's approved DIM Organizer and vault-cleaner report
  screenshots as durable PR evidence. They independently show the same
  four-piece Titan Luminopotent Plate / Reaver stat group: Class 30, Melee 25,
  Weapons 20, with distinct Class, Melee, Super, and Health tuning slots in the
  report. No CSV export was committed; the owner explicitly approved the
  visible opaque item instance ids for publication.

## 2026-09-01 — #110 same-stat Armor duplicates browser extension

- Extended the #102 Armor duplicates presentation to consume the authoritative
  `same_stat_groups` snapshot projection. Same-stat groups are clearly labelled
  `Same stats, different tuning · review-only`; they show per-member Tuning Mod
  Slot text and supplied Seasonal Mod/Holofoil variation, without deriving a
  survivor, disposition, ranking, or junk decision.
- Added All / Exact / Same stats local presentation selection only when both
  authoritative group kinds exist. Whole-group search/facets and per-group
  Tuning Mod Slot matching/counting are preserved, including any-member tuning
  matches for same-stat groups.
- Changed the local duplicate DOM registry to retain multiple handles for one
  opaque id so legitimate exact/same overlap repaints and disables every
  applicable occurrence while preserving read-only presentation semantics.
- Added fake same-stat fixture, focused Node projection/renderer/overlap
  coverage, and exactly one focused packaged-server browser test. Updated the
  README, narrow M9 ownership sequencing, and browser verification checklist.
- Focused Node/adapter tests pass (`104 passed`). Focused Chromium passed in
  1.34s and the full browser marker passed in 5.62s; no Python rules, report
  schema, server protocol/lifecycle, runtime dependencies, or #109 work
  changed.

## 2026-09-01 — #110 Sol review corrections

- Same-stat projection now rejects missing `group_kind`, one-member groups,
  duplicate group ids, and member ids repeated across same-stat groups. It
  keeps Seasonal Mod/Holofoil strictly member-level, so absent group axes
  cannot render synthetic `none/unknown` header tiles.
- Same-stat current proposal controls now require a same-section, same-hash
  authoritative current proposal decision. Supplied close-pass member
  metadata is displayed/validated when present but never grants authority;
  blank metadata therefore still permits legitimate later-pass proposals,
  while an exact preferred/retained presentation remains read-only even when
  it discloses the current proposal. Wrong-hash and cross-section lookalikes
  remain rejected.
- Added focused Node trust/security coverage for strict shape, duplicate
  identity, hostile same-stat values, prototype-shaped group/member ids, and
  huge/leading-zero/non-digit opaque ids. Added adapter coverage that renders
  exact and same-stat occurrences for one id, acknowledges one verdict through
  the existing seam, repaints both occurrences, and freezes all applicable
  controls at finalisation. The single #110 Playwright test remains the only
  new browser test.
- Performed the packaged-server visual pass with a temporary combined fixture
  containing only committed fake rows: 1440×1000 and 390×844 in light and
  dark, headless screenshots retained and inspected. The mixed selector and
  focused All control, same-stat heading/tuning values, contained narrow
  matrix overflow, and finalised read-only/disabled state were legible in all
  four cases (about 6.2s total). The pre-existing acknowledgement focus blur
  remains the only noted limitation.

## 2026-09-01 — #102 incremental review follow-up

- Replaced the cross-group malformed-envelope adapter regression's fixed
  five-millisecond assertion delay with a test-only completion signal on the
  mocked `vc-status` node. The signal resolves only after the adapter has
  processed the malformed response, entered terminal incompatible state, and
  published its failure status; other harness scenarios are unchanged and no
  production timing/lifecycle hook was added.
- Documented the untrusted `exactDuplicateGroupsFromSnapshot` contract in
  JSDoc: authoritative group/member ordering is preserved, opaque identity,
  uniqueness, dispositions, and section/hash proposal correlation are
  validated before adoption, and browser grouping/ranking/survivor truth is
  never reconstructed. Contract violations throw `Error`/`TypeError` as
  applicable.
- Validation: focused UI/adapter tests `102 passed`; full suite `925 passed in
  19.91s`; Chromium marker gate `4 passed, 921 deselected in 4.45s`, with the
  focused #102 test `1 passed in 1.68s` (0.47s call, 0.37s setup, 0.58s
  teardown); non-editable wheel proof, Ruff, and `git diff --check` passed; no
  tracked `data/` files. The single #102 Playwright test remains the only new
  browser test.
- No behavior or files outside the established #102 presentation,
  test-harness, and documentation scope changed; snapshot/ruleset versions,
  server protocol/lifecycle, runtime dependencies, CI, persistence, auth,
  rules, and #109/#110 boundaries remain unchanged. Committed locally for
  Sol's review; no push or GitHub reply was made.

## 2026-09-01 — #102 PR #111 review follow-up

- Fixed the Armor duplicates Unset bug: a function-scoped DOM button named
  `clearVerdict` shadowed the callback, so clicking Unset attempted to call the
  button node. The DOM handle is now distinct, and Node coverage clicks
  Approve, Veto, and Unset and verifies the exact opaque id/verdict callbacks.
- Exact-group adoption now rejects an opaque member id repeated across any
  authoritative Armor exact groups, using prototype-safe maps before state
  adoption. Adapter coverage proves the incompatible response leaves the
  previous envelope/report state unadopted. Proposal correlation remains
  section-scoped and requires the exact group hash; cross-section and
  wrong-hash lookalikes remain incompatible.
- Later-pass junk/review decisions for preferred or retained members are
  carried as separate current-proposal presentation metadata only when the
  same Armor section and group hash match. The exact disposition remains
  read-only and controls remain absent, while the duplicate cell discloses the
  Proposals action and current authoritative verdict. Exact proposed losers
  retain the existing acknowledged single-member mutation path. The matrix
  now also renders the supplied Equipped boolean as Yes/No.
- Updated the reviewed domain wording to the exact `75 base total` phrase and
  recorded the packaged-server manual check with the fake
  `tests/fixtures/armor_duplicates_ui.csv`: 390×844 and 1440×1000 light/dark
  layouts, focus, Equipped No/Yes/No, real Approve/Unset acknowledgement,
  rejected replacement preservation, finalise/freeze, and reset all passed.
- Validation: focused UI/adapter tests `102 passed`; full suite `925 passed in
  19.36s`; Chromium marker gate `4 passed, 921 deselected in 5.08s`, with the
  focused #102 test `1 passed in 1.59s` (0.44s call, 0.35s setup, 0.56s
  teardown); non-editable wheel proof passed; Ruff and `git diff --check`
  passed; no tracked `data/` files. The sandbox-only baseline failures were
  loopback socket/Chromium permission errors and were rerun with the required
  permissions.
- Snapshot schema v2, ruleset v4, Python rules/report/pipeline, server
  protocol/lifecycle, runtime dependencies, CI, persistence, auth, and #109/
  #110 scope remain unchanged. This correction is committed locally for Sol's
  review; the remote branch remains at `d0710eb` and no PR was opened or
  pushed.

## 2026-09-01 — #102 Armor duplicates browser view

- Added the permanent Armor duplicates surface beside Proposals. It consumes
  #101's authoritative `exact_duplicate_groups` projection, preserves backend
  group/member order and disposition truth, and treats every group as an
  indivisible unit for name/id, Class, slot/type, archetype, and Tuning Mod
  Slot filtering. No JavaScript duplicate identity, ranking, or survivor
  algorithm was added; same-stat groups remain reserved for #110.
- Added a reusable safe DOM group header/matrix seam with archetype-led
  tier-5 Primary/Secondary/Tertiary display and honest six-stat fallback. The
  shared Tuning Mod Slot, Spirit signature, Seasonal Mod, Holofoil, protection
  ladder, and full opaque ids are text-labelled. Survivor and retained
  members are read-only; proposed members alone reuse the existing
  acknowledged single-id verdict path and both views read the same verdict
  map. Presentation state preserves valid duplicate filters/surface and
  clears only values absent from a replacement group set.
- Added hostile/prototype/opaque-id Node coverage, adapter reconciliation
  coverage (including malformed-envelope rejection, same-report repaint,
  shared cross-view verdict state, actual duplicate surface switching,
  rejected-upload preservation, finalized disabling, and view retention), plus
  incompatible-response regressions for cross-section same-ID/action and
  wrong-hash proposal lookalikes. Added a fake three-member tier-5 group
  fixture and exactly one focused Chromium test covering complete membership
  and cross-view acknowledgement.
- Added the reviewed `docs/armor-archetypes.md`, corrected the tier-5 gotcha
  and terminology warning in `AGENTS.md`, updated README and browser
  verification documentation, and recorded the 1440×1000 desktop and 390×844
  narrow light/dark, focus, replacement/rejection, finalise/freeze, and reset
  pass. The pre-existing focused-button blur during in-flight mutation remains
  documented.
- Validation: focused UI/adapter tests `100 passed`; full suite `923 passed in
  19.78s`; Chromium marker gate `4 passed, 919 deselected in 4.46s`, with the focused
  #102 test `1 passed in 1.59s` (0.46s call, 0.54s teardown); non-editable
  wheel proof passed; Ruff and `git diff --check` passed; no tracked `data/`
  files.
  Baseline sandbox runs had only the pre-existing socket/Chromium permission
  failures and were rerun with required loopback/browser permissions.
- Snapshot schema v2, ruleset v4, Python decisions/rules, server protocol and
  lifecycle, runtime dependencies, and CI topology are unchanged. No pull
  request was opened.

## 2026-08-31 — #108 PR review follow-up

- Restored the static armor semantic capture for every unchanged Decision
  field except `note`: id, hash, name, location, guardian class, action, tag,
  selected id, and parsed reason. Removed obsolete pre-#104 Note strings from
  the baseline fixture so the guard remains clear and authoritative.
- Hoisted the shared tuning comparison formatter in the exact, dominated, and
  similar emitters without changing selection, grouping, wording,
  normalization, Note grammar, schema/ruleset versions, fingerprints, or
  decision semantics.
- Strengthened emitter-driven armor round-trip assertions to derive both
  sides from the fake frame and authoritative `kept_id`, then require the
  complete expected winner/partner and tuning tail at Note end. Affected tests
  and Ruff passed (`209 passed`); the elevated full suite passed (`913
  passed`), with diff/privacy checks clean and no tracked `data/` files.

## 2026-08-31 — #104 Tuning Mod Slot presentation

- Extended the existing shared duplicate-reference presenter with the fixed
  six-value Tuning Mod Slot vocabulary and explicit `none/unknown`; exact,
  dominated, and similar armor Notes now label candidate and survivor/partner
  values, including equal values. Existing #29/#101 Notes remain recognized and
  new clauses replace cleanly on repeated emitter-driven runs.
- Added nullable `candidate_tuning_mod_slot` and
  `selected_tuning_mod_slot` fields to pairwise armor report decisions. The
  selected side is projected only by direct lookup of the authoritative
  `kept_id`; weapons, ghosts, and non-comparison armor decisions remain null.
  Snapshot schema 2, ruleset 4, fingerprint inputs, and #101 exact/same-stat
  group projections remain unchanged.
- The ordinary Proposals table maps those structured fields and adds an
  always-visible inert-text `Tuning Mod Slot` column. No Notes parsing, tuning
  preference, server endpoint/lifecycle change, runtime dependency, or #102
  Armor duplicates view was added.
- Focused fake-fixture Python/Node and server pass-through coverage was added;
  the packaged Chromium visual pass covered desktop light/dark and narrow
  layouts, unexpanded Proposals text, finalised/read-only state, and shutdown.
  Golden regeneration was byte-stable twice (see handoff). The pre-existing
  server mutation gate blurs a verdict button that is itself focused while an
  acknowledgement is in flight; this was recorded as a remaining manual
  limitation rather than changing out-of-scope lifecycle behavior.

## 2026-08-31 — #101 PR review follow-up: truthful CLI exact counts

- Replaced the armor command's note-substring summary classification with the
  shared last-marker `reason_slug` parser and explicit exact/close reason
  families. Complete exotic class-item duplicate decisions now contribute to
  the exact-pass count without trusting stale or user-authored earlier markers.
- Added a CLI regression proving the full armor duplicate fixture reports all
  ten exact-pass decisions, including `armor-exotic-class-dupe`, and documented
  the close pass's wider `group_frame` projection contract following review.

## 2026-08-31 — #101 review regression: exact protection reaches reports

- Threaded an optional effective-protection classification through the
  internal `Decision` model from the authoritative armor exact pass. Report
  records consume that classification when present, including explicit
  unprotected complete exotic-class losers; decisions from other passes keep
  the existing global rails projection. The external report/snapshot schema
  is unchanged and no exotic exception was duplicated in `report_run`.
- Added report and server regressions for plain-junk, locked-review, and
  loadout-review complete exotic-class losers, plus ordinary exotic behavior
  remaining soft-protected. Updated the emitter-path coverage fixture setup
  and retained server pass-through checks.
- Validation: the focused implementation subset passed 529 tests with 4
  sandbox-deselected socket checks; the unrestricted full suite passed 891
  tests. Ruff, diff, and privacy checks passed. No browser production code or
  PR was changed/opened.

## 2026-08-31 — #101 review regressions: ordering and identity parity

- Restored exact-group member presentation order: preferred survivor first,
  retained protected members next, then proposed members, with the shared
  opaque-ID order used within each disposition bucket. Close-pass decisions
  now emit in deterministic shared-ID order, independent of CSV row order.
- Made same-stat membership use raw Tier identity, matching the close-pass
  compatibility boundary while retaining the integer display projection.
  Restored Spirit extraction for every armor row so non-class Spirit-looking
  perk data remains part of the established exact fingerprint; exactly-two
  validation remains limited to exotic class items.
- Added regressions for preferred-survivor ordering, complete ordered close
  decision parity, raw-Tier ambiguity, and non-class Spirit fingerprint
  boundaries. The focused gate passed 522 tests with 4 real-socket checks
  deselected by the sandbox; the unrestricted full suite passed 884 tests.
  Ruff and diff checks passed, and the v2 golden regenerated byte-stably twice.
  No browser production code or PR was changed/opened.

## 2026-08-31 — #101 amended replan: opaque ids, exotic class dupes, same-stat groups

- Applied one shared string-only `instance_id_order` helper across armor exact
  survivor selection and group/member projection, armor close partners, armor
  scoring ranks, and weapon exact-dupe ties. Raw ids remain unchanged for
  leading-zero, arbitrarily large, variable-length, and non-digit values;
  rank-first decision emission order remains stable while equal-rank ties are
  row-order independent.
- Bumped `RULESET_VERSION` to 4 while keeping snapshot schema v2. The
  fingerprint change is intentional and invalidates persisted veto identity
  from ruleset v3; review/session schemas and persistence formats are
  unchanged.
- Complete exotic class items now require exactly two distinct visible Spirit
  perks. Matching exact groups retain hard-protected losers, review loadout or
  locked losers, and junk otherwise unprotected losers with the dedicated
  `armor-exotic-class-dupe` reason; ordinary exotic armor rails are unchanged.
  Notes history recognizes every new exact emitter branch.
- Extended the authoritative armor close analysis to return review-only
  `same_stat_groups` alongside its existing pairwise decisions. Groups use
  Hash + Tier + six stats + complete Spirit signature, ignore tuning/seasonal/
  holofoil for membership, suppress exact-only groups, and expose raw and
  presented variation plus each member's truthful proposal/partner and safety
  state. The pipeline supplies the full comparison frame, and report/server
  snapshots pass the projection through without reconstruction.
- Updated PLAN/README, added full behavioral and parity coverage, and
  regenerated `report_snapshot_v2.json` twice for byte-stable output. Focused
  exact/close/armor/weapon/report/review/note-history/server/id-order tests
  passed 457 tests; Ruff passed. The unrestricted full suite passed 880 tests
  including real-socket and Chromium acceptance. The earlier restricted run
  could not start those six environment-gated checks (`Operation not
  permitted`), but no code or test failure remained. No browser production
  code or PR was changed/opened.

## 2026-08-31 — #101 authoritative armor exact-duplicate groups

- Refactored the armor exact-dupe rule into one analysis pass that returns the
  existing decisions together with complete immutable exact-group/member
  projections. Group ids use the lowest member id, groups and members have
  deterministic ordering, and additional hard-protected copies are represented
  as `retained_protected` rather than a second survivor.
- Projected the existing Hash/stats/raw identity fields plus explicit generic
  Tuning Mod Slot labels (`Weapons`, `Health`, `Class`, `Grenade`, `Super`,
  `Melee`, or `none/unknown`) through the armor pipeline and report snapshot.
  Proposed members carry the exact branch action/reason; no decision, ruleset,
  fingerprint, pass ordering, or later-pass filtering semantics changed.
- Kept the coordinated #105 compatibility boundary: snapshot schema remains
  v2, ruleset remains v3, and the decision fingerprint inputs remain unchanged.
  Regenerated `report_snapshot_v2.json` deliberately; its only change is the
  empty `exact_duplicate_groups` projection for the standard report fixture.
  Added report, server pass-through, reversal, disposition, string-id, and
  inert hostile-text regressions. No server production, UI, review, persistence,
  or lifecycle code changed.
- Follow-up review added a static origin/main decision capture covering every
  Decision field and reason slug, plus complete group metadata/state, all
  tuning labels, Spirit/Hash safety boundaries, and 64-bit-ish hash strings.
- Validation: focused armor/report/server/Ruff gate passed (193 tests), and
  golden regeneration was byte-stable (report-run suite: 27 tests). The full
  local suite reached 849 passed and 1 skipped; its 4 socket failures and 2
  Chromium startup errors were environment-only `Operation not permitted`
  restrictions from the sandbox, so Sol should rerun those tests unrestricted.

## 2026-08-31 — #105 location and Guardian class split

- Measured one fresh private armour export using aggregates only: 891 rows;
  Equippable Hunter 186, Titan 429, Warlock 276, empty 0; exotics Hunter 53,
  Titan 115, Warlock 65; class-item types Hunter Cloak 38, Titan Mark 101,
  Warlock Bond 48; exotic class-item rows Hunter 9, Titan 41, Warlock 9.
- Replaced the decision/evaluation `owner` model field with `location` from
  DIM `Owner`, added verbatim armour `guardian_class` from `Equippable`, and
  kept weapon/ghost classes empty. Updated the snapshot to schema v2 (the
  single v1→v2 bump is owned by #105), regenerated the v2 golden, and left the
  ruleset, fingerprint inputs, review-manifest outer schema, override schema,
  and session schema unchanged.
- Added independent browser Kind/Class facets with a presentation-only
  class-neutral fallback, retained Location as a secondary column, relabeled
  duplicate references and terminal output, and covered legacy `owner` plus
  current `location` Notes replacement. Added fake Hunter, mismatched
  location/class, empty, and unrecognised-class coverage; no class validation
  or weapon/ghost schema change was introduced.
- Valid current-schema manifests continue to parse and pre-upgrade nested
  schema-v1 manifests are rejected. The before/after fake semantic capture
  diff is empty (fingerprint, action/tag/reason, membership, and selected
  references unchanged).
- Review follow-up coverage now exercises same-revision Class-control
  resynchronisation through the live no-rebuild path, including invalid-filter
  clearing, list repaint, and preservation of search/focus/local state. The
  fake browser armour input now has deterministic Hunter and Warlock proposal
  rows, proving class filtering removes the other class while locations remain
  visibly independent.
- Validation: baseline before edits passed Ruff and had 819 passing/1 skipped
  with 4 socket and 2 Chromium startup failures under the restricted sandbox;
  the final exact focused gate passed 375 tests, golden/report-run passed 23 tests,
  real-browser acceptance passed 2 tests, and the unrestricted full suite
  passed 837 tests. Final Ruff, diff-check, and no-tracked-`data/` checks
  passed; the full/browser reruns used the permitted socket/browser execution
  environment.

## 2026-08-31 — #29 emitter-driven Notes round-trip coverage

- Added emitter-driven regressions for current Notes clauses from weapon and
  armour exact dupes, armour close dupes, wishlist trash (whole-item and
  roll, junk and soft-review rails), armour scoring (junk, soft review, and
  last-of-archetype), and ghosts. Each case feeds the exact emitted note
  through three further rule runs and asserts the user prefix, action, reason,
  and complete note remain stable with one current vault-cleaner marker.
- Extended the exact-dupe emitter coverage to exercise every current winner
  label: weapon higher Tier, Crafted Level, and stat total, plus armour
  loadout membership, lock, and higher Power. The cases use fixture rows or
  a minimal fixture-derived pair and assert the label in the actual emitted
  note without reconstructing its grammar.
- Kept the literal `note_history` tests for legacy migration formats. Added a
  maintenance obligation to keep emitter tests and recognizer patterns in
  sync whenever a generated clause changes. No production mismatch was found
  and no rule or decision semantics were changed.
- Added emitter-driven partner tie-break coverage for both armor-close
  branches: dominated `6033` selects the lower-id `6031` among equal-surplus
  `6031`/`6032`, and similar Guard Plate `4051` selects `4052` among the
  equally close `4052`/`4053`. Each test checks the actual reason slug and
  structured selected partner plus the exact emitted `; partner deterministic
  id tie-break` tail through the shared round-trip helper; the strict
  recognizer remains unchanged.
- Validation: `.venv/bin/ruff check src tests scripts` passed;
  `.venv/bin/pytest -q tests/test_note_history_roundtrip.py
  tests/test_note_history.py tests/test_dupes.py tests/test_armor_dupes.py
  tests/test_armor_close.py tests/test_weapons_rules.py
  tests/test_armor_rules.py tests/test_ghost_rules.py` passed 170 tests.
  The unrestricted `.venv/bin/pytest -q` suite passed 826 tests, including
  the real-socket and Chromium coverage. Independent renames of the dominated
  and similar armour-close tie-break literals each failed only their targeted
  emitter/recognizer guard; the earlier armour lock and weapon Tier mutations
  remained guarded. Production sources were restored byte-for-byte afterward.

## 2026-08-31 — #29 current-only generated Notes

- Replaced complete, known vault-cleaner clauses at the trailing `Notes`
  boundary before appending the current clause across weapon, armour, armour
  close-duplicate, and ghost rules. User-authored prefixes, ambiguous
  tool-looking fragments, and text following them remain untouched; a
  five-cycle DIM-style round-trip regression confirms generated Notes no
  longer grow across runs.
- Kept last-marker parsing for migrated or manually edited Notes, routed
  crafted-state display through the shared strict parser, and aligned armour
  winner wording with weapon winner wording. Corrected the M9 issue
  reference, so Markdown treats it as prose rather than a heading.
- This is presentation/history handling only: rule order, selection, action,
  tag, reason slug, full audit ids, report schema, fingerprint, and ruleset
  version remain unchanged. Snapshot regeneration was byte-identical.
- Validation: Ruff passed. The focused review-follow-up command was
  `.venv/bin/pytest -q tests/test_note_history.py tests/test_dupes.py
  tests/test_armor_dupes.py tests/test_armor_close.py
  tests/test_duplicate_reference.py tests/test_weapons_rules.py
  tests/test_armor_rules.py tests/test_ghost_rules.py tests/test_report.py
  tests/test_report_run.py tests/test_cli_report.py`; it passed 213 tests.
  The unrestricted `.venv/bin/pytest -q` suite passed 800 tests. `git diff
  --check` and the no-tracked-`data/` privacy check passed.

## 2026-08-30 — #29 five-character suffix boundary correction

- Corrected the bounded collision presenter so prefix-plus-suffix displays
  are used only when at least one source character is genuinely omitted.
  Five-character collisions now use suffix plus the stable bounded
  discriminator, without reintroducing the leading character; naturally
  distinct ids of four characters or fewer remain unchanged.
- Added a direct five-character regression while retaining the 16-character,
  three-copy group-wide, and pathological stability coverage. No selection,
  grouping, ranking, action/tag, audit-id, schema, or fingerprint semantics
  changed.
- Validation: Ruff passed; focused duplicate/reference/report tests passed
  146 tests; full suite passed 772 tests and skipped 1. Four real-socket tests
  failed and two Chromium tests errored only because this sandbox denies
  socket/browser startup (`Operation not permitted`). Snapshot regeneration
  was byte-identical; fake report/roundtrip dry-run checks passed; diff-check
  and no-tracked-`data/` privacy checks passed.

## 2026-08-30 — #29 group-wide suffix collision correction

- Corrected collision context so weapon exact-dupe and armour exact-dupe
  survivors receive every id in their exact group, while armour close-dupe
  partners receive every id in the compatibility group. A referenced row now
  has one stable presentation label across all notes that cite it.
- Kept the final four characters as the normal label and bounded suffix
  expansion strictly below the complete long id. A truthful leading-prefix /
  suffix projection handles group-unique collisions; pathological shared
  projections use a bounded deterministic group-rank plus target digest.
  Short synthetic ids remain intact, and no opaque id is parsed numerically by
  the presenter or emitted in full.
- Added three-copy weapon and armour exact-group regressions, repeated
  armour-close partner stability coverage, 16-character collision protection,
  and pathological-prefix/suffix fallback coverage. Selection, grouping,
  ranking, actions, tags, full audit ids, and all other #29 semantics are
  unchanged.
- Validation: Ruff passed; the focused duplicate/reference/report suite
  passed 145 tests; the full suite passed 771 tests and skipped 1. Four
  real-socket tests failed and two Chromium tests errored only because this
  sandbox denies socket/browser startup (`Operation not permitted`). Snapshot
  regeneration was byte-identical; fake `report` and `roundtrip` dry-run
  checks passed; `git diff --check` passed; no files are tracked under
  `data/`.

## 2026-08-30 — #29 presentation safety corrections

- Corrected exact-roll identity normalization to remove only one selected
  trailing `*` from the original DIM cell. Display casing is derived
  separately, so `Trait*` and `Trait**` remain distinct and `Kill Tracker**`
  cannot become a measured boundary; the regression also confirms the
  fingerprint remains at the established #31 semantics.
- Escaped untrusted reference delimiters (`[`, `]`, `;`) as full-width
  presentation characters while retaining raw audit values. Generated
  Notes grammar remains ASCII and report summaries preserve the generated
  `keep`/`compare` and winner/partner suffix. Added hostile weapon and armor
  exact/close regressions for marker, structural, newline, and forged-clause
  safety.
- Added presentation-only survivor/partner suffix disambiguation: final four
  characters remain the default, colliding candidate/survivor suffixes grow
  by bounded string comparison, and pathological shared suffixes use a
  bounded differing-character fallback. Full `ReportDecision.id` and
  `kept_id` remain unchanged; no identity, grouping, ranking, or action
  semantics changed.
- Validation: Ruff passed; the focused duplicate/reference/report suite
  passed 139 tests; the full suite passed 765 tests and skipped 1. Four
  real-socket tests failed and two Chromium tests errored only because this
  sandbox denies socket/browser startup (`Operation not permitted`).
  `git diff --check` passed, no files are tracked under `data/`, the fake
  report snapshot regeneration was byte-identical, and fake `report` plus
  `roundtrip` dry-run checks completed successfully.

## 2026-08-30 — #29 human-readable duplicate references

- Added one shared presentation seam for weapon exact-dupe survivors, armour
  exact-dupe survivors, and armour dominated/similar partners. Long opaque ids
  render as a final-four-character suffix (`[id …0059]`); short synthetic ids
  remain intact. Weapon references include Owner, Tier, MW, crafted level when
  known, and the final two names from the existing measured pre-tracker roll
  prefix. Armour references include Owner, MW, Power, Tuning Stat, and compact
  Spirit names where present.
- Notes retain the existing `#vc-junk:`/`#vc-review:` reason slugs and append a
  bounded `keep`/`compare` reference plus a selector explanation. Weapon
  explanations follow the current #31 Tier → Masterwork Tier → Crafted Level →
  stat total → opaque-id ranking; wishlist and hard-rail state are not used to
  select a survivor. Armour explanations follow the existing survivor rank,
  and close-dupe explanations retain the current surplus/similarity detail.
- Referenced-row display text collapses control whitespace, bounds each
  fragment/reference, and neutralizes case-insensitive `#vc-` text. Raw row
  values and the existing full `ReportDecision.id`/`kept_id` audit strings stay
  unchanged. No survivor row is emitted merely for discoverability.
- Added fake hostile-text, short-id, selector-reason, report-summary, reverse
  determinism, and long-id snapshot regressions. Regenerated the schema-v1
  fake snapshot; its diff is limited to duplicate presentation Notes. Schema
  version remains 1 and ruleset version remains 3; no runtime dependency or
  browser/server/review code changed. Validation: Ruff and 132 focused tests
  pass; the full suite has 758 passing tests plus 1 skip, with 4 socket tests
  failing and 2 Chromium tests erroring only because this sandbox denies socket
  and browser startup (`Operation not permitted`).

## 2026-08-30 — #31 Enhanced-prefix documentation clarification

- Reconciled every exact-roll description with the literal DIM prefix while
  keeping the Markdown lint-safe: names begin with `Enhanced` followed by one
  separator space, and both the word and that space remain part of the complete
  perk name. This avoids relying on an invisible trailing space inside a code
  span while preserving the measured distinction from the base perk name.
- Updated AGENTS.md, PLAN.md, README.md, WORKLOG.md, and the duplicate-rule
  module docstring only. Decision semantics, fixtures, ruleset version, and
  report snapshots are unchanged.
- Validation passed with Ruff, `git diff --check`, and all 752 tests in the
  full suite.

## 2026-08-29 — #31 final review cleanup

- Corrected the public `dupes` command summary: duplicate resolution keeps the
  best exact copy while preserving distinct and uncertain rolls, rather than
  keeping only one item per Hash.
- Aligned the comma-bearing tracker-candidate scan with the exact measured
  boundary invariant. The boundary cell is necessarily the exact normalized
  `Kill Tracker` or `Crucible Tracker` label, so it cannot contain a comma and
  is no longer included in the pre-boundary scan. The existing adversarial
  tests still cover comma-bearing candidates before a later valid boundary.
- Kept the hostile-Unicode report, renderer, and upload regressions in this PR.
  They restore coverage lost when this ticket changed the hostile weapon
  fixture's roll identity, so they are directly related regression protection
  rather than unrelated feature work.
- Validation passed with Ruff, the top-level CLI help smoke check, and all 752
  tests in the full suite.

## 2026-08-29 — #31 review correction: preserve Enhanced perk names

- Corrected the exact-roll normalizer to remove only DIM's trailing selected
  `*` marker. Names beginning with the literal `Enhanced` followed by one
  separator space are retained as complete gameplay perk names; collapsing
  them to base names could falsely merge distinct rolls under one Hash. The
  regression now proves `Battery` and `Enhanced Battery` remain separate and
  produce no dupe decision.
- Re-measured the private export after the correction: 665 rows remained
  groupable with contiguous named `Perks 0` through `Perks 20`; all 665 rows
  had a measured `Kill Tracker` or `Crucible Tracker` boundary (positions 4
  through 15), and 25 pre-tracker names beginning with the literal `Enhanced`
  followed by one separator space were ordinary gameplay names. Aggregate
  identity results were unchanged: 117 old same-Hash groups (346 rows, 229
  redundant), 1 exact group of 3 rows (2 redundant), and 2 review decisions
  with no automatic junk decisions. No real rows, ids, paths, or hashes are
  recorded here.
- Regenerated the fake-data snapshot with the repository script; it was
  byte-identical because no fake input or decision payload changed. The
  ruleset remains version 3; this correction does not introduce another
  ruleset bump.
- Focused validation passed: Ruff and 243 duplicate, parser, report, weapon,
  review, session, finalize, and UI tests. The full suite passed 721 tests and
  skipped 1; 4 real-socket tests failed and 2 Chromium tests errored because
  this sandbox denies sockets/browser startup (`Operation not permitted`), the
  same environmental limitation recorded for the prior review.

## 2026-08-29 — #31 PR #100 follow-up: dynamic headers, hostile coverage, and wishlist/comma safety

- Made weapon `Perks N` schema width export-dependent. The minimal load-time
  invariant is `Perks 0`; the extractor accepts any contiguous `0..N` header
  range with a complete non-empty pre-tracker prefix and a measured `Kill
  Tracker` or `Crucible Tracker` boundary, so gaps, missing starts/boundaries,
  unknown tracker-looking labels without a measured boundary, or incomplete
  rows remain ungroupable without blocking unrelated commands. Previous
  real-style fixtures measured `Perks 0..19`; the current private export
  measures `Perks 0..20`.
- Restored the hostile fixture's exact prefix on the RTL-name row so its
  decision path carries the RLO/PDF name and U+2028/U+2029 Notes. Added report,
  renderer, and server-upload assertions for those values; no real data is
  involved.
- Removed wishlist score from exact-dupe survivor ranking. Wishlist-trash,
  keep-over-trash conflicts, and exact-group keep protection remain unchanged;
  exact copies now rank Tier > Masterwork Tier > Crafted Level > stat total >
  stable opaque Id. Added a regression proving differing post-tracker
  wishlist-resolvable cells cannot select the survivor.
- Measured 5,302 starred perk cells, each with exactly one trailing selected
  marker. The private export has 13 comma-bearing pre-tracker cells, all
  legitimate full names (`Nail, Meet Hammer` or `Eyes Up, Guardian`), and no
  comma-bearing tracker cells. `row_perk_hashes` now keeps each cell whole;
  comma-bearing names resolve through the perk map without guessed splitting.
  The measured tracker boundaries are exactly `Kill Tracker` (662 rows) and
  `Crucible Tracker` (3 rows). Any comma-bearing cell containing either
  measured tracker label is rejected as an unmeasured combined tracker,
  regardless of component order or marker placement; unknown/future names that
  merely end in `Tracker` stay identity cells until a later measured boundary,
  or make the row ungroupable when no measured boundary exists. These are safe
  aggregate counts only: no rows, IDs, hashes, or paths are recorded.
- Snapshot regeneration via the repository script was byte-identical: the
  changed hostile fixture is not part of the fake golden, no decision payload
  changed, and `RULESET_VERSION` remains 3.
- Final focused validation passed: Ruff and 201 parser, dupe, weapon, rail,
  report, UI, server-upload, and export-discovery tests. Restricted full-suite
  result: 745 passed, 1 skipped, 4 failed, and 2 errors; the failures/errors
  were caused by documented socket/browser startup `Operation not permitted`
  restrictions. An independent elevated full-suite run completed cleanly:
  752 passed. The fake Slammer CLI dry run remained 1 junk / 0 review, and the
  private no-wishlist report remained 0 junk / 2 review with no `--write`.

## 2026-08-29 — #31 weapon exact-roll measurement (pre-code)

- Measured the current private DIM weapon export before finalizing the
  extractor: 665 rows, with contiguous named `Perks 0` through `Perks 20`.
  The first `Kill Tracker` or `Crucible Tracker` perk cell is a stable
  structural boundary in the export: cells before it are the frame and
  randomized roll options; tracker, origin, mod, masterwork, memento, and
  other current-state cells follow it.
- The fingerprint will use `Hash` plus every pre-tracker perk cell by header
  name, stripping only DIM's trailing selected `*` marker. Names beginning
  with the literal `Enhanced` followed by one separator space are retained as
  complete perk names: the measured occurrences were ordinary gameplay perk
  names, not a safe display-only decoration. Perk options are retained in
  their measured socket order: the export represents
  multi-option sockets as adjacent named cells, and no order changes were
  observed. Exotic rows also carry pre-tracker prefixes in this export, so
  their `Hash` alone is not a complete identity.
- Mutable tracker, origin/current socket, mod, masterwork, memento, and later
  cells are excluded. `Hash` remains mandatory, and `Name` is never used.
  Missing or empty pre-tracker identity cells, a missing measured boundary, an
  unknown tracker-looking label without a later measured boundary, an unknown
  rarity, or an otherwise incomplete prefix will be ungroupable and cannot
  enter automatic duplicate cleanup. Cells at and after the measured boundary
  are excluded from identity and may legitimately be empty.
- Aggregate baseline: 117 same-Hash groups of at least two rows (346 rows,
  229 redundant rows). The safe measured candidate has 1 exact group (3
  exotic rows, 2 redundant rows); no legendary exact group was present. The
  candidate therefore bounds automatic cleanup to 2 rows before rails, rather
  than the old 229-row same-Hash pool. No real rows, ids, paths, or hashes are
  recorded here.
- The three same-Hash Exotic groups measured as size/distinct-prefix pairs
  `9/9`, `3/1`, and `2/2`; only the `3/1` group supports exact grouping. The
  two multi-prefix groups are therefore intentionally left untouched.

## 2026-08-29 — #31 weapon exact-roll implementation

- Implemented `exact_roll_fingerprint()` in `rules/dupes.py`: named `Perks N`
  fields are normalized through the first measured `Kill Tracker` or
  `Crucible Tracker` boundary, with only the selected `*` marker removed.
  Unknown tracker-looking labels are not guessed as boundaries. Names beginning
  with the literal `Enhanced` followed by one separator space are retained
  because measurement found them in ordinary gameplay perk names. Socket order
  is preserved; exotic prefixes are included because Hash-only identity was
  not supported by the measurement.
  Blank hashes, unknown rarities, missing boundaries, and incomplete prefixes
  are ungroupable and never enter automatic dupe resolution. Mutable tracker,
  current socket, mod, masterwork, memento, and later state remain excluded.
- `dupes.resolve()` now groups by `(Hash, fingerprint)` and chooses survivors
  by the existing rank order plus an opaque-id tie-break independent of CSV
  order. Wishlist-trash remains the earlier separate pass, and #32 crafted
  validation/protection and all hard/soft rails remain unchanged.
- Added a fake, synthetic Slammer-like export and behavioral coverage for
  distinct and exact same-Hash rolls, row reversal, selected markers,
  multi-option cells, distinct names beginning with the literal `Enhanced`
  followed by one separator space, mutable state, unknown identity,
  wishlist behavior, and same-name/different-Hash safety. The parser then
  required the measured named perk-prefix headers; the later dynamic-width
  follow-up below reduces that to the minimal `Perks 0` invariant while the
  extractor keeps its fail-safe contiguity checks. `RULESET_VERSION` advanced
  from 2 to 3 and the report snapshot was regenerated by the repository
  script.
- Post-change private-export aggregate dry runs: 665 rows remained
  groupable under the measured contract; 1 exact group covered 3 rows (2
  pre-rail redundant copies), and the resolver emitted 2 review decisions
  with no automatic junk decisions. The real Slammer aggregate is six copies
  across two Hashes: the five-copy group has five distinct fingerprints and no
  exact group, while the other Hash is a singleton. The synthetic Slammer dry
  run has one four-copy Hash with three distinct fingerprints and one
  two-copy exact group; it emitted one junk decision from that exact pair and
  kept distinct rolls separate.
- Snapshot inspection found no weapon decision payload changes; only the
  ruleset/global fingerprint and the fake weapon source digest/fingerprint
  metadata changed.
- Focused validation passed: Ruff and 274 exact-dupe/weapon/rail/report,
  parser, review, server-finalize, and UI tests. The full suite result was
  721 passed, 1 skipped, 4 failed, and 2 errors;
  the four real-socket tests and two Chromium tests remain blocked by this
  sandbox's `Operation not permitted` network/browser restrictions, as in the
  baseline.

## 2026-08-28 — #32 crafted token safety-rail correction

- DIM's crafted weapon token is `Crafted=crafted`, but the old rail passed
  `Crafted` through the generic boolean parser, which only recognised
  `true`. The focused helper now accepts `crafted` as crafted, `false` and
  empty as not crafted (with surrounding whitespace/case normalised), and
  rejects `true` plus every other unknown non-empty token. The fixture-only
  `true` representation is deliberately not retained.
- Weapon ingestion now requires and validates `Crafted` and `Crafted Level`
  before any rule decisions. Threshold and above-threshold unlocked crafted
  losers are absent from wishlist and duplicate output; below-threshold
  crafted rows retain normal behaviour.
- Bumped `RULESET_VERSION` from 1 to 2 and regenerated the fake report
  snapshot. Focused validation passed Ruff and 96 tests; the elevated full
  gate passed Ruff and 695 tests. The dry-run reports 4 junk and 3 review
  decisions, with ids 3021 and 3023 absent and below-threshold id 3022
  junked. Browser/server/wheel checks are not required for this local parser
  ticket. No real vault rows or IDs were committed; issue #31 remains
  separate and unresolved.
- Review follow-up: the fingerprint regression now compares all input
  categories at the current ruleset version 2, with only the dedicated
  version-change assertion using version 1. A shared strict level parser now
  trims surrounding whitespace; empty non-crafted/shared levels map to zero,
  while empty crafted levels map to an explicit unknown sentinel and are
  hard-protected; every non-empty level must be ASCII non-negative integer
  text, otherwise SchemaError. Both weapon loaders validate every row before
  rules, and rails.protection validates direct-call data eagerly.
- Empty crafted-level follow-up: crafted rows with empty or whitespace-only
  levels now load as an explicit unknown sentinel and are hard-protected with
  `crafted-lvunknown`; non-crafted empty levels remain zero/unprotected.
  Loader parity, wishlist-trash, duplicate-loser, mixed-export, and eager
  precedence regressions cover the fallback without changing fixtures or the
  ruleset version.
- Final review validation: focused Ruff and 117 focused tests passed; full
  Ruff and 716 tests passed; the fake duplicate dry run parsed 18 weapons and
  produced 4 junk plus 3 review decisions, with crafted ids 3021 and 3023
  absent and below-threshold id 3022 junked. Snapshot regeneration was
  byte-identical (schema 1, ruleset 2); git diff --check passed, and no data
  paths are tracked.

## 2026-08-28 — #51 retired static review surface

- Removed the unreleased `review-html` command and Python renderer, deleted
  `review_static.js`, and deleted the static-only CLI/artifact/browser parity
  test suites. Browser manifest parsing, import/export, autosave, and handoff
  code are gone; CLI `review --manifest` and `review.parse_manifest` remain,
  as does the server's separate strict verdict validator.
- Kept the permanent manifest-free presentation coverage in
  `tests/test_review_ui_js.py` (including 64-bit ids, prototype safety,
  grouping/filtering/sorting, hostile text, and source safety). Its hostile-run
  helper was moved locally from the deleted static test module. The two #90
  Playwright tests and the non-editable wheel proof were left intact.
- Updated README, PLAN, and AGENTS to describe `serve` as the only browser
  workflow, keep review manifests as CLI/scripting/backup input, and remove
  obsolete inline/static browser-parser guidance. A stale server asset guard
  that named deleted browser-parser symbols was removed; allow-listed assets
  and route tests remain.
- Retired-surface baseline before deletion: 2,353 lines
  (`review_html.py` 165, `review_static.js` 745, `test_cli_review_html.py`
  174, `test_review_html.py` 285, `test_review_html_js.py` 984). Final
  `git diff --numstat origin/main...HEAD`: 109 additions, 2,637 deletions,
  for a net reduction of 2,528 lines.
- Validation: Ruff passed; full suite passed (678 tests); focused UI/review/
  CLI/verdict suites passed (22/82/34 tests); both permanent Chromium tests
  passed (2 passed, 676 deselected); the wheel proof passed; both surviving
  packaged JavaScript assets passed `node --check`; CLI help showed `serve`,
  `report`, and `review` with `review-html` rejected; `git diff --check`
  passed; no files under `data/` are tracked; hygiene search found no live
  retired-surface references and `parse_manifest` remains owned by
  `review.py`/CLI/tests. No runtime dependency or server protocol change.

## 2026-08-27 — #94 review follow-up: browser launch and wheel-proof hardening

- Replaced the browser test's `BrowserType.executable_path` preflight with the
  real `launch_browser()` attempt. Only Playwright's exact missing-executable
  diagnostic is translated into the ordinary skip / `VAULT_CLEANER_BROWSER_REQUIRED=1`
  failure policy; unrelated launch failures still propagate. Fixture return
  annotations now use `Iterator[...]`.
- Changed `scripts/check_wheel_install.py` to snapshot current bytes for
  `git ls-files -z` paths into a fresh temporary source tree. Pip builds from
  that tree outside the checkout, so ignored `build/`, `data/`, `.venv/`, and
  other untracked content cannot be reused. The child server's stderr is
  drained concurrently and retained in diagnostics; malformed bootstrap URLs
  now become the intended `RuntimeError`.
- Validation: Ruff passed; all 750 pytest tests passed; browser collection was
  exactly 2; both required Chromium browser tests passed; empty-browser
  ordinary mode skipped 2 and required mode exited nonzero with 2 setup
  failures; the wheel proof passed; a disposable clone containing a stale
  `build/stale.whl` left that artifact untouched while the proof built from a
  `/tmp` source snapshot; all three packaged JavaScript files passed
  `node --check`; `git diff --check` passed; and `git ls-files data/` remained
  empty.
- Intentional non-changes: `Session.expected_origin` remains untouched because
  it is a property; no runtime dependencies, package data, production server,
  protocol, or UI files changed; the reusable browser checklist remains in one
  document as requested by #90.

## 2026-08-27 — #90 browser parity gate, wheel proof, and documentation

- Pinned dev/test-only `playwright==1.62.0` and
  `pytest-playwright==0.9.0` without changing the pandas + Flask runtime set.
  The managed install resolved Chrome for Testing 151.0.7922.34, Playwright
  Chromium browser revision 1234 (plus headless-shell revision 1234 and FFmpeg
  revision 1011).
- Added exactly two `browser`-marked real-browser tests over the existing
  loopback server: hostile uploaded names/notes remain inert live DOM text with
  no injected `img`, `script`, `b`, or dialog, and the one browser smoke covers
  bootstrap → armor upload → approve → unset → veto → finalise → Playwright
  download. The downloaded `dim-import.csv` bytes equal
  `session.finalized_csv_bytes`; #67's CLI/server parity was not duplicated.
- Guarded the managed browser executable before launch. Browser-free runs skip
  both tests, while `VAULT_CLEANER_BROWSER_REQUIRED=1` turns a missing Chromium
  into a failing setup instead of a falsely green job. Collection reports
  exactly 2 browser tests.
- Added a dedicated Ubuntu browser CI job alongside the unchanged
  Windows/Linux core matrix. It installs Chromium with
  `python -m playwright install --with-deps chromium`, runs the isolated wheel
  proof and both browser tests, and uploads retained-on-failure traces and
  failure screenshots from `test-results`; no retries or rerun tooling were
  added.
- Added `scripts/check_wheel_install.py`: it builds a real wheel with
  `python -m pip wheel --no-deps --wheel-dir <temporary-wheelhouse> .`, installs
  only that wheel into a fresh temporary virtual environment, removes inherited
  `PYTHONPATH`, runs outside the checkout, verifies the imported package origin,
  starts the installed `vault-cleaner serve --no-wishlists --port 0`, follows
  bootstrap with a cookie-aware standard-library client, and checks the root
  HTML plus every allow-listed CSS/JavaScript asset for status, content type,
  body, and references. The existing #87 `vault_cleaner.ui` package-data
  declaration was sufficient; no packaging correction was required.
- Completed the reusable manual browser/accessibility checklist on Linux with
  Chrome for Testing 151.0.7922.34 at 1440×1000 and 390×844. Light, dark,
  narrow, keyboard `a`/`v`/`u` focus preservation, report controls,
  finalised/frozen state, Download again, Reset, Shutdown, and the required
  stale second-tab reconciliation all passed. No product browser defect was
  found; one exploratory checklist command selected an option absent from the
  all-review fixture and was corrected before the complete pass.
- Expanded the README from the #88 stub to the complete #89 server workflow
  and privacy model: byte uploads rather than paths, session-held verdicts,
  finalisation and durable vetoes, download/reset/shutdown, loopback and
  bootstrap secrecy, local-only vault data, no Bungie credentials, and the
  separate optional static-content network path with `--no-wishlists`.
- Final validation: Ruff passed; all 750 pytest tests passed; browser collection
  was exactly 2 and both passed in Chromium; all three packaged JavaScript files
  passed `node --check`; the non-editable wheel proof passed; the fake-fixture
  round-trip stayed dry; `git diff --check` passed; and `git ls-files data/`
  remained empty.

## 2026-08-27 — #89 review follow-up: control and finalisation recovery hardening

- Refreshed every mutation control, including bulk buttons, whenever the
  single-tab gate or authoritative session state changes. Finalized adoption
  now leaves verdict controls frozen while retaining a safe Download-again
  recovery action when report refresh is disconnected.
- Treated every successful finalise HTTP response as committed even when CSV
  bytes are missing or unreadable. Added no-retry/no-second-finalise coverage,
  finalized CSV recovery coverage, and preserved committed-success messaging
  when the post-download report refresh fails.
- A stale mutation whose mandatory report refetch fails now enters an explicit
  disconnected recovery state with Reconnect and no enabled mutations; the
  stale envelope remains display-only until authoritative adoption.
- Verdict-filter acknowledgements now compare actual visible row membership,
  so approving an already-approved row (and the vetoed/unreviewed equivalents)
  repaints in place without stealing focus. Finalisation report-refresh errors
  preserve terminal authentication/session/incompatibility outcomes separately
  from recoverable HTTP/transport failures; a successful Download-again
  response restores the connected finalized lifecycle controls.
- Acknowledgement envelopes that invalidate a query now rebuild the filter
  controls along with the rows. Session actions live outside the report panel,
  so Shutdown and the idle upload hint remain reachable after boot and Reset;
  the action group is explicitly labelled for assistive technology.
- The static artifact now opts into the shared non-read-only view and shared
  row painter, keeping Unset aria state and verdict presentation synchronized.
  Finalisation surfaces the protocol's approved-but-still-vetoed count with
  singular/plural wording. A small ``Vault-Cleaner-Serve-Once`` response
  signal lets the page represent intentional post-download shutdown without
  a misleading reconnect prompt; persistent servers retain report recovery.
- Finalisation response metadata is snapshotted before reading CSV bytes and
  carried through committed body-read failures, so even a ``--once`` server
  can show the accurate approved-but-still-vetoed count in its terminal banner.
- Finalisation notes now remain truthful across every committed response and
  report-refresh recovery path; zero suppression counts are omitted, and
  invalidated filters synchronize in place without stealing search focus.
- The committed finalisation note is now rendered synchronously before a
  follow-up report refresh can wait; focused-control tests retain the search
  caret and cover zero and malformed suppression headers.

## 2026-08-27 — server-acknowledged review mutations and finalisation (#89)

- Extended the packaged server review page from read-only presentation to a
  server-acknowledged review workflow. Single-row and filtered bulk approve,
  veto, and unset actions use one revision/fingerprint-bound request and a
  single same-tab mutation gate; displayed verdicts change only after the
  returned envelope is accepted.
- Added keyboard ``a``/``v``/``u`` review controls, in-place acknowledged row
  repainting (including focus-preserving row handles), stale mutation
  reconciliation through ``GET /api/report`` without replay, selective local
  view-state invalidation reporting, and retained/discarded upload verdict
  presentation.
- Added finalise/download/reset/shutdown lifecycle controls. Finalisation
  consumes CSV bytes and protocol headers, revokes temporary download URLs,
  supports ``GET /api/finalized.csv`` recovery, freezes the finalized view,
  sends reset's exact two-key payload, and sends shutdown as a bodyless POST.
- The shared view layer now exposes explicit Unset controls and safe row-paint
  and control-disable seams. Hostile item text remains text-node data, while
  approved-session/active-persisted-veto conflicts remain explicit.

## 2026-08-26 — Linux VM handoff review (#88)

- Recreated the ignored development environment after the repository move and
  revalidated the pushed issue branch: Ruff was clean, all 687 existing tests
  passed, all three packaged JavaScript files passed Node syntax checks,
  `git diff --check` was clean, and no file under `data/` was tracked. The VM
  only provides Python 3.14 rather than the documented Python 3.12 target; the
  declared `>=3.12`
  package contract and full suite still pass there.
- Ran an isolated real-loopback smoke test: bootstrap authentication and all
  three fake fixture uploads returned 200, an invalid weapons replacement
  returned the sanitized 422 response, and the accepted report fingerprint
  and revision remained unchanged after rejection.
- Moved the minimal local-server README section below the static manifest
  workflow. Its earlier placement made the following static-only approve/veto
  and browser-storage paragraphs read as features of the read-only server.
- The SSH-forwarded real-browser pass covered all three accepted fixture
  uploads, rejected replacement preservation, rendering, refresh, and the
  disconnected state. It found that the visible Reconnect button did nothing:
  deferred execution let the outer loader overwrite the global runtime object
  its click handler looked up. The button now retains its retry callback
  directly, with a Node regression that constructs and clicks it. A fresh
  real-browser pass then proved the button sends its retry, a stopped server
  retains the visible disconnected state, and a replacement session produces
  terminal 401 restart guidance without another retry. The manual checklist is
  complete, and the final suite passes all 688 tests.
- Follow-up review fixes keep one stable ``VaultCleanerServerUI`` object while
  exposing live ``start`` and ``state`` handles for both interactive and
  loading-time script execution. Shared response conversion now distinguishes
  transport failures, HTTP/API errors, invalid JSON, and incompatible success
  envelopes; malformed successful responses are terminal with restart guidance,
  while ordinary rejected uploads remain connected. Added focused Node coverage
  for response/error classes, array/numeric-id/duplicate-id envelopes, upload
  rejection, terminal 401, and both DOM timings. Upload statuses are now
  outside the file labels, linked with ``aria-describedby``, and polite live
  regions for all three export kinds. Documented the read-only view contract,
  including null approve/veto row handles. A shared browser failure-state helper
  now handles only common 401, illegal-state, incompatible/invalid-JSON, and
  transport transitions based on client failure kinds; ordinary upload HTTP
  failures remain per-kind while report HTTP failures retain reconnect guidance.
  Session envelope override statuses are validated and copied before state
  adoption, and the browser/Python session-state vocabularies are parity-tested.
  Invalid-JSON guidance is identical in the main and per-kind live regions.
  Focused browser/UI plus session-invariant tests pass (47 tests, including 46
  UI tests); full validation passes Ruff, all 708 tests, packaged JavaScript
  syntax checks, diff whitespace checks, and confirms no tracked files under
  ``data/``. Session metadata now fails loudly if an unknown state would be
  emitted, while upload eligibility remains an explicit allow-list.

## 2026-08-25 — server review UI shell and read-only report (#88)

- Replaced the server placeholder root with fixed packaged HTML, CSS, shared
  presentation JavaScript, and a server-only adapter wired through
  `run_server` → `build_server` → `create_app`; the explicit asset allow-list
  remains the only way browser resources are served.
- Tightened the HTTP CSP to deny all by default while allowing only same-origin
  packaged scripts/styles and same-origin API fetches. The page has no forms,
  inline code, request-derived paths, or mutation/finalization controls.
- Added separate weapons/armor/ghost CSV inputs using `fetch` with explicit
  `text/csv` and browser-owned transport length headers. Each input reports its
  own upload/error status, while one `applySessionEnvelope` seam adopts server
  state, rejects unknown schema versions, keeps valid local
  search/filter/group/sort/detail state, drops only invalidated filter/sort/
  expansion values, and retains upload reconciliation ids privately.
- The read-only report uses the #87 presentation core for counts, filtering,
  grouping, sorting, item details, hostile-text-safe DOM rendering, and armor
  panels. Persisted override statuses and current-session verdicts are shown
  as separate concepts. Added server asset/CSP tests and Node seam/safety tests,
  updated serve docs, and kept the static review adapter unchanged.
- Review found and fixed selective view-state invalidation, exact CSP ordering,
  the five named count displays, disconnected upload disabling, and terminal
  `401` restart guidance before the final verification pass.
- A real browser pass remains: the Linux Playwright driver had no installed
  Chrome and the Windows browser-control bridge could not attach from this WSL
  workspace. Open the printed bootstrap URL, upload each fake fixture kind,
  refresh, reject a replacement, and verify disconnected/terminal messaging.

## 2026-08-25 — shared review UI assets and presentation core (#87)

- Extracted the review stylesheet and the manifest-free presentation/view layer
  into packaged `vault_cleaner.ui` resources. The static HTML adapter now reads
  and inlines those exact resource bytes, while keeping autosave and manifest
  import/export in a clearly temporary adapter for #51.
- Generalized browser `keptItems` to combine active persisted veto ids with
  current-session vetoes; the static adapter passes an empty `Set`.
- Added setuptools package-data configuration and direct Node coverage for the
  packaged presentation resource (64-bit ids, grouping parity, prototype-safe
  maps, and persisted-veto filtering), plus an exact inline-byte proof. The
  static-adapter Node harness retains manifest/parity coverage, while the
  presentation harness directly requires the packaged resource; resource
  loading decodes raw bytes to avoid universal-newline drift.
- Review follow-up adds a small Node DOM-stub contract for the shared view
  layer, precise static-only layering guards, exact snapshot-element coupling,
  and a strict Set-like contract for active persisted veto ids. Safety comments
  now live with the extracted helpers, including the DOM text-node boundary and
  64-bit id ordering rationale.
- Windows review finding: packaged CSS/JS resources now have narrowly scoped
  LF attributes, preserving exact browser bytes under core.autocrlf while the
  existing byte-exact fixture rules remain unchanged.
- Round-two review follow-up: constant leak sentinels now catch ordinary
  SCREAMING_CASE reads, Node harness failures retain captured stderr, and the
  exported `keptItems` Set-like/opaque-id/filter-copy contract is documented
  beside the function.
- No server UI, HTTP client, CSP, or manifest-code deletion was introduced.

## 2026-08-25 — transactional server finalization (#67)

- Implemented serialized `/api/finalize` as prepare → raw-byte override drift
  guard → durable persistence → tiny in-memory commit. The complete DIM CSV is
  rendered before `save_overrides`, deliberately preserving the server/CLI
  ordering distinction, and finalized bytes are cached for idempotent retries
  and `/api/finalized.csv` without another disk read.
- Added strict finalize request and revision validation, exact CSV/disposition
  and revision headers, the approved-still-vetoed conflict count, finalized
  lifecycle invalidation on reset/close, and `serve --once` shutdown on a
  successful response close only.
- Reset now reloads and validates the current override bytes/digest before
  changing session state, so an `overrides_changed` refusal can recover and a
  second review in the same process adopts the new baseline. The digest
  comparison still has the unavoidable small TOCTOU window before
  `save_overrides`' atomic replacement; the next reset establishes a fresh
  exact-byte baseline.
- Added raw-byte parity coverage against all three CLI reference modes
  (proposal report, persisted-veto review, and fixed review-manifest review),
  distinct existing/missing override drift cases, finalized cache/reset
  behavior, post-commit response recovery, `--once` close semantics, and
  route-specific error-path redaction for report, upload, finalize, and reset.
- Review follow-up: derive the approved-still-vetoed header from the merge
  result, make reset's refreshed override store/digest inputs required, give
  closed-session finalize requests a terminal-state error, and cover missing
  and float-spelled revisions plus finalized upload refusal for every export
  kind. The finalize digest remains the pre-persistence review baseline by
  design; reset is the atomic store+digest refresh boundary.
- Review follow-up also gives closed `/api/finalized.csv` requests a terminal
  shutdown error, documents the `create_app(once=True)` response-close
  contract, and clarifies the finalized-response construction seam and
  lifecycle comments.

## 2026-08-25 — verdicts, reset, stale revisions, and terminal shutdown (#66)

- Added the serialized `/api/verdicts` batch mutation with strict shared
  review-input validation, opaque ids, duplicate/unknown-id rejection, both
  batch caps, JSON `null` clearing, no-op semantics, deterministic report-order
  responses, and one revision bump per changed batch.
- Added the reusable session stale-check seam and exact revision headers for
  `stale_report`/`stale_verdicts`; stale checks run inside the same serialized
  critical section as verdict and reset mutations.
- Upload replacement now reconciles verdicts through #63's
  `retain_verdicts()` before adoption, returns retained/discarded ids, and
  bumps `verdict_revision` once only when the stored verdict set changes.
- Added serialized `/api/reset` with monotonic revisions and retryable
  server-owned cleanup while leaving durable overrides untouched. Shutdown now
  synchronously enters terminal `closed` state, clears live metadata, keeps
  revisions monotonic, and returns a coherent idempotent closed envelope;
  physical cleanup and socket stop remain in the response callback boundary.
- Added focused protocol tests for validation, atomicity, stale headers,
  clear/reset, repeated shutdown, and response ordering. No durable review
  writes were introduced. Added a real-loopback overlapping-verdict test with
  events and bounded joins proving one same-revision request wins and the
  other receives stale headers.
- Follow-up hardening requires the `verdict` key explicitly (so omitted and
  JSON `null` remain distinct), snapshots stale revision headers under the
  session lock, deep-copies report-present verdict arrays, and makes reset,
  close, and post-commit retirement resilient to ordinary cleanup exceptions.
  The protocol note in `PLAN.md` records schema-v1's five states, including
  #67's `finalized` and the terminal `closed` state.
- Validation passes: Ruff reports no findings, all 637 tests pass (including
  the real-loopback overlap regressions), `git diff --check` is clean, and no
  file under `data/` is tracked.

## 2026-08-24 — server lifecycle regression contract (#83)

- Audited all nine substantive PR #82 review findings. Post-close upload
  allocation is covered by
  `test_close_before_upload_rejects_without_staging_a_candidate` and the new
  real-socket overlap test; partial live metadata and revision rewind are
  covered by `test_close_invalidates_all_accepted_export_state` plus the shared
  lifecycle expectations; and the over-wide rollback span is covered by
  `test_post_commit_retirement_failure_keeps_new_live_state`.
- The prepare, cleanup-retry, and retirement boundaries remain pinned by
  `test_report_failure_rolls_back_and_removes_candidate`,
  `test_failed_candidate_cleanup_remains_tracked_until_close`,
  `test_close_retries_a_directory_when_deletion_temporarily_fails`, and the
  post-commit retirement regression. Shutdown cleanup cannot gate process
  teardown: `test_shutdown_callback_runs_when_close_raises` and
  `test_run_server_closes_server_when_session_close_fails` cover the callback
  and socket-close boundaries respectively.
- Added `tests/test_server_lifecycle.py` with one extensible expectation table
  for current idle, exports-loaded, and closed state. Its real-loopback test
  blocks inside report construction with events, proves a shutdown request has
  reached Flask but cannot overtake the serialized upload, then proves ordered
  completion, successful server exit, monotonic revisions, and no live,
  candidate, or retired staging residue. It uses bounded waits and joins, not
  sleeps or a lock-only simulation.
- Removed the shared absent override fixture path from server-app tests; every
  constructed session now receives its own `tmp_path` path. The CLI's
  default-path forwarding test stays intentionally path-specific and stubs
  `run_server`, so it performs no filesystem read. This closes both the real or
  cwd-relative override exposure and the later finding that absence of the
  shared fixture was unenforced.
- Two review findings remain explicit contract decisions rather than defects:
  the 96 MiB aggregate guard is defensive because three 32 MiB per-kind caps
  make its rejection side unreachable today, while the coherent terminal
  response for repeated shutdown remains a schema decision for #66. No
  production or schema behaviour changed here.
- Promoted the reusable rules to the `AGENTS.md` server-lifecycle checklist:
  close is terminal, revisions are monotonic, uploads use prepare → adopt →
  retire phases, rollback ends before adoption, cleanup is retryable and cannot
  block shutdown, deletion is server-owned only, and tests use explicit
  test-owned paths.
- Validation passes: Ruff reports no findings, all 603 tests pass (including
  real loopback coverage), `git diff --check` is clean, and no file under
  `data/` is tracked.
- Review follow-up: the overlap regression now spies on
  `server_app.session_metadata` before delegation and only for the shutdown
  request, proving the shutdown view cannot enter before the serialized upload
  finishes. The staging redirect now replaces only the `server_app.tempfile`
  binding with a delegating proxy, leaving process-wide
  `tempfile.mkdtemp` unchanged. `build_client` documents its test-owned
  `tmp_path/overrides.json` contract.
- Mutation proof: removing `@serialized` from either the upload handler or the
  shutdown view makes the overlap regression fail at the pre-delegation view
  assertion: without either side of the serialization boundary, shutdown can
  enter while report construction is still blocked.

## 2026-08-24 — isolate server-app test overrides (#65)

- Replaced every repo-relative `overrides.json` path used by
  `tests/test_server_app.py` sessions with an absolute, deliberately absent
  test-owned fixture path. The `run_server` integration test continues to use
  its own `tmp_path` override path, so a real repository override file cannot
  influence the server-app tests.

## 2026-08-23 — final upload lifecycle review follow-up (#65)

- Lifecycle tests now pass isolated overrides paths under `tmp_path` and never
  read personal `data/` overrides; the one default-path forwarding test remains
  explicit about `DEFAULT_OVERRIDES_PATH`.
- Clarified the narrow deletion exception: the local review server may remove
  only its own temporary staging/candidate/retired directories, and request
  content can never supply cleanup paths.
- `override_digest` remains internal session state for #67 lost-update/finalize
  drift detection and is deliberately absent from schema-version-1
  `/api/report` responses.
- Repeat `/api/shutdown` metadata coherence requires a terminal closed protocol
  state and is deferred to #66/parent state-machine work; #65 API behavior is
  unchanged.
- Ruff and the full test suite pass: 602 tests collected and passed.

## 2026-08-23 — upload lifecycle review follow-up, round 3 (#65)

- Preserved the session's prior state plus monotonic `report_revision` and
  `verdict_revision` counters across close while still invalidating the live
  report, export metadata, verdict data, and staging pointer. Failed cleanup
  paths remain private retry state.
- Authenticated `GET /api/report` now returns the registered 409
  `illegal_state` error after shutdown, rather than exposing a reset-looking
  idle envelope. Shutdown still builds its response metadata before the close
  callback runs.
- Wrapped both shutdown callback and server socket cleanup in `finally` paths;
  regressions prove each cleanup callback runs when session close raises. The
  full suite passes all 602 tests, including the two real loopback checks.

## 2026-08-23 — upload lifecycle review follow-up (#65)

- Made the lock-protected session closed flag authoritative for uploads and
  shutdown: closed sessions return the registered 409 illegal-state error
  before reading or staging a body. Close now invalidates the report, export
  digests/sizes, fingerprint/snapshot, verdicts, revisions, state, and live
  staging pointer before cleanup; failed deletions remain only in private
  retry tracking.
- Encapsulated candidate tracking, adoption, and retirement in `Session`.
  Candidate rollback ends before adoption, while prior-directory retirement is
  post-commit best effort so cleanup failures cannot remove the new live run.
- Kept `MAX_EXPORT_BYTES=32 MiB` and `MAX_TOTAL_EXPORT_BYTES=96 MiB` and
  removed the production-only aggregate-limit seam. With exactly three shipped
  export kinds, each capped at 32 MiB, the reject side is mathematically
  unreachable under those constants; the aggregate guard remains defensive
  for future kinds or limit changes. Integration rejection coverage injects a
  lower module cap instead.
- Converted upload-test client setup to unconditional `Session.close()`
  teardown and added close-before-upload, close-state invalidation, and
  post-commit retirement-failure regressions. The full suite passes all 600
  tests, including the two real loopback checks.

## 2026-08-23 — server uploads and transactional report staging (#65)

- Added strict raw-byte upload handling for weapons, armor, and ghost exports:
  explicit lengths, transfer-encoding rejection, named per-kind/aggregate
  limits, media-type checks, strict UTF-8 decoding, and sanitized schema/error
  responses.
- Uploads now build a complete canonical temporary export set and run the
  existing `run_report` engine before swapping session state. Identical bytes
  are idempotent; changed uploads advance `report_revision`; failed builds and
  invalid replacements leave the live report untouched and remove candidates.
- Sessions now retain the current `ReportRun`, source digests/sizes, exact
  override-store bytes digest (with missing-file distinction), and clean live,
  retired, and candidate directories idempotently on shutdown or startup
  failure. `/api/report` derives its snapshot and override status from the
  committed run.
- Added focused upload, rollback, transport, canonical-path, limit, and
  lifecycle coverage. Full suite passes (597 tests); no ruleset or snapshot
  version changed and no files under `data/` are tracked.
- Follow-up: centralized temporary-directory deletion in `Session`, retaining
  paths when a filesystem removal transiently fails so repeated `close()` calls
  retry them. Candidate rollback now uses the same seam; focused tests cover
  failed deletion and later cleanup. Full suite now collects 597 tests.

## 2026-08-23 — final Project #3 workflow verification (#61)

- Verified live Project #3 workflows through GraphQL: `Auto-add to project`,
  `Item added to project`, and `Auto-archive items` are enabled. The UI-configured
  filters are repository auto-add for `is:issue` with default `Todo`, and
  completed-item archive after 30 days (`is:closed reason:completed
  updated:<@today-1m`); workflow configuration details are not exposed by the
  available GraphQL schema.
- Created temporary maintenance issue #80 and verified it automatically
  appeared in Project #3 with Status `Todo` before closing it with an explanatory
  comment. This proves the repository auto-add and Item added behavior
  end-to-end without leaving test work open.
- Re-audited the four views, exact `Todo`/`In Progress`/`Done` statuses, the
  `enhancement` label on feature #38, `maintenance` on #51/#61, M8 assignments
  (#38/#47/#49/#50/#51), dependency links #49 → #50 → #51, and superseded #25.

## 2026-08-22 — issue and project workflow guidance (#61)

- Updated `AGENTS.md` to link the actual vault-cleaner project board and added
  the complete issue-creation checklist: specific type/maintenance labels,
  `icebox` only for explicitly out-of-scope PLAN work, existing milestones,
  dependency text and project dependency links, explicit `Todo` membership,
  and post-creation verification.
- Audited the public repository state before external changes: the existing
  `M8 — Local review server` milestone is already assigned to #38, #47, #49,
  #50, and #51; feature #38 retains `enhancement`, while #51 and #61 use
  `maintenance`.
- Repository issue metadata is now applied through the authenticated GitHub
  connector: `enhancement` remains on feature issue #38, `maintenance` is on
  #51 and #61 (replacing #61's `enhancement`), #25 is closed as superseded
  with a linking comment, and the M8 milestone assignments remain intact.
- Project v2 views and dependency links are now configured through the
  authenticated GraphQL API: `All items`, `Board`, `Active`, and `Icebox`;
  #50 is blocked by #49 and #51 is blocked by #50. Status remains exactly
  `Todo`, `In Progress`, and `Done`. The Board is still a board layout with
  Status visible; the available schema exposes no explicit grouping mutation,
  so its existing/default Status grouping is preserved for UI verification.
- At the time of this entry, the remaining project steps were the UI-only
  repository auto-add/default `Todo` and 30-day completed-item archive controls;
  the final verification is recorded in the dated entry above.

## 2026-08-22 — shared proposal retention and manifest-free verdict merge (#63)

- Added pure `review_session.py` primitives: `same_proposal` compares only
  `id`, `kind`, `hash`, `action`, and `reason`; `retain_verdicts` keeps only
  unchanged full identities and reports changed or missing ids as discarded.
- Added the manifest-free `merge_verdicts` core. `review.merge_manifest` is a
  thin adapter that preserves additive vetoes, run-owned metadata, unchanged
  timestamps, and the existing CLI diagnostics.
- Promoted the strict review-input helpers/constants (`check_keys`,
  `require_text`, `require_id`, `require_kind`, `MAX_TEXT`, `ID_RE`) while
  retaining their validation behavior. The five-field identity rule remains
  cross-fingerprint retention only; `classify` and merge still compare
  `(action, reason)`.
- No ruleset or snapshot change: `RULESET_VERSION` remains 1 and the report
  golden remains byte-identical. Ruff and the full test suite pass.
- Follow-up: made proposal identity access fail loudly for missing fields,
  unified verdict-entry normalization for retention and merge (including a
  single server entry), and rejected non-string ids without coercion.
- Removed the obsolete private validator aliases, centralized veto ordering
  and UTC timestamp formatting, tightened source-level consumer coverage, and
  kept the adapter's legacy diagnostic payloads at its boundary.
- Final follow-up: verdict mappings now require exactly `approved` or
  `vetoed`, including for retention, and the pure core accepts only mapping
  entries while `merge_manifest` continues to restore legacy diagnostics.
- Final input-shape guard rejects non-mapping iterable entries with a stable
  project-owned `TypeError`.

## 2026-08-22 — in-memory CSV rendering and DIM export byte loaders (#62)

- Added `render_import_csv`, sharing validation, DIM Id quoting, column
  filtering, UTF-8 encoding, and CRLF serialization with `write_import_csv`.
  The writer now renders completely before opening its destination while
  retaining its existing signature and row-count return; a regression pins
  existing outputs byte-identical and fresh nested destinations untouched when
  a later row is invalid.
- Added strict UTF-8 byte loaders for weapons, armor, and ghosts, with a
  separate `ExportDecodeError` and fixed non-path source labels. Shared
  schema and armor-field validation keeps path diagnostics unchanged and
  prevents uploaded-schema errors from exposing staging paths.
- Added renderer byte-parity and parser path/bytes parity coverage for plain
  and BOM exports, schema/duplicate failures, malformed armor fields, and
  undecodable bytes.

## 2026-08-09 — M8 server transport and security envelope (#64)

- Added Flask 3.1 as the second and only other runtime dependency and added
  `vault-cleaner serve`: it pre-warms configured wishlist and Bungie manifest
  caches before binding, listens only on `127.0.0.1` with an OS-selected port
  by default, prints a one-time bootstrap URL, and runs Werkzeug threaded
  behind one session mutation lock.
- Established `server/` primitives for the later M8 children: named request
  limits, one registered JSON error contract, the idle session metadata
  builder, a `@serialized` check-and-apply decorator, and an idempotent
  `Session.close()` lifecycle seam. Upload, verdict, reset, and finalize routes
  are present but remain idle-state placeholders for #65–#67; there is no
  manifest endpoint and no report logic in this ticket.
- The bootstrap credential is separate from the session credential, expires
  after five minutes, is compared in constant time and consumed once, then
  exchanged for a host-only `HttpOnly; SameSite=Strict; Path=/` cookie before
  a 303 redirect to the clean root URL. Every request validates the exact
  bound Host, every POST validates the exact Origin, every response is
  `no-store`/`no-referrer`, and none carries CORS allow headers.
- Assets are registered as exact allowlisted URL rules backed by byte
  providers; the placeholder page is an inline Python constant, so there is
  no catch-all path or filesystem mapping to traverse. A custom Werkzeug
  handler redacts the complete bootstrap query from request logs.
- Coverage includes the Flask client security matrix and error schemas plus a
  real threaded loopback exchange proving actual-port bootstrap, log
  redaction, response-before-shutdown ordering, and clean server exit. Runtime
  dependency and console-script metadata are pinned. `RULESET_VERSION` and
  report snapshots are unchanged because no decision semantics changed.
- Review follow-up made credential comparison safe for arbitrary Unicode,
  rejects a present noncanonical Origin on every method, snapshots session
  metadata under the mutation lock, canonicalizes port 80, reserves server
  routes against asset collisions, and adds `nosniff`, framing, and CSP
  headers. Server imports are lazy for non-server CLI commands and tests now
  cover those boundaries with isolated config paths and deep state snapshots.
  Werkzeug remains Flask's transitive implementation detail, preserving the
  ticket's exact two-dependency runtime contract; no ruleset bump was needed.

## 2026-08-09 — wishlist cache stat errors (#72)

- `wishlist.fetch` now treats `OSError` while reading cache metadata as a
  stale/unavailable cache and continues to the existing download path instead
  of leaking the raw filesystem error.
- Regression tests cover a cache whose `stat()` fails before a successful
  redownload, and the no-cache case still raises the existing clean
  `WishlistError` when the download also fails.
- Review follow-up covers `stat()` failure followed by download failure falling
  back to a readable stale cache, and an unreadable cache raising the clean
  "no usable cached copy" error.

## 2026-08-09 — DIM CSV BOM regression coverage (#47)

- Pinned the existing weapons-loader behaviour for both ordinary UTF-8 DIM
  exports and exports with a leading UTF-8 BOM. The regression uses the same
  fake DIM fixture in both cases and verifies that header parsing, row loading,
  and quoted instance-id normalisation remain identical.
- No runtime behaviour or decision semantics changed; this closes the final
  test-coverage acceptance criterion on the #47 umbrella.

## 2026-08-08 — CI hygiene review follow-up (#60)

- Tightened the worklog gate from “the path changed” to “the PR added a dated
  entry,” so deleting, reformatting, or otherwise touching `WORKLOG.md` no
  longer satisfies the audit-trail requirement. Both PR-diff checks now use
  the event's base branch instead of assuming every PR targets `main`.
- Made the workflow's read-only token permission explicit and stopped both
  checkouts from persisting credentials that neither job uses.
- Documented the narrow `.gitattributes` escape valve for a deliberately
  whitespace-sensitive fixture; exceptions belong on exact paths and in the
  worklog rather than weakening the repository-wide check.

## 2026-08-08 — deterministic zero-age cache bypass (#70)

- Made `max_age_days=0` unconditionally bypass the fresh-cache fast path for
  both the Bungie manifest perk map and wishlist downloads, even when
  filesystem timestamp precision leaves a newly written cache mtime slightly
  ahead of the current clock. Positive limits retain their existing freshness
  behavior, and both contracts are documented at their loader boundaries.
- Pinned the Windows failure with actual future-dated cache mtimes rather than
  a process-wide clock fake. Separate tests retain the ordinary stale-cache
  fallback coverage; failed forced requests still return cached content with
  the existing warning.
- `RULESET_VERSION` is unchanged: this fixes cache refresh control flow and
  does not change rule ordering or decision semantics.

## 2026-08-03 — CI repository hygiene gates (#60)

- Added a platform-independent `hygiene` job that rejects tracked files under
  `data/` on both CI triggers and checks pull-request diffs for whitespace,
  line-ending errors, and a `WORKLOG.md` change.
- The job checks the full PR range from its merge base, so checkout fetches the
  complete history. Each failure identifies the offending path or the missing
  `WORKLOG.md` file without requiring a local reproduction.
- Kept the worklog gate unconditional. CI-only changes and reverts still need
  a short audit-trail entry, so a bypass label would weaken the stated workflow
  without a current use case.
- Proved all three failure paths in scratch commits that did not land: a
  force-added `data/private-vault.csv`, a two-line CRLF fixture, and a clean PR
  with no worklog change each failed with the expected offending path. A
  scratch commit containing this implementation passed all three checks.

## 2026-08-02 — clean write-side filesystem errors (#43)

- Added one CLI write boundary that converts ordinary `OSError` failures into
  the existing `error: <message>` convention and exit code 1. All CSV-writing
  commands now use it, as does `review-html`, so an unwritable destination no
  longer produces a traceback from any `--write` surface.
- Preserved review's deliberate write order: overrides are saved before the
  derived CSV. A failed override save reports that nothing was written; a CSV
  failure after a successful save reports that the overrides are durable and
  only the CSV must be regenerated. A review run without a manifest has no
  override write and reports that nothing was written when its CSV fails.
- Regression coverage injects filesystem failures into every command shape
  and separately pins both review outcomes, including the persisted override
  file in the partial-write case.

## 2026-08-02 — configured-path maintenance follow-up (#58)

- Documented the deliberate path-base split from #55: when the requested
  config is missing, built-in relative paths retain their historical
  current-working-directory meaning; relative paths resolve against the config
  file's parent whenever that file exists — built-in defaults included.
- Both `load_config` and the paths-only `load_paths_config` reject non-string
  `[paths]` values cleanly. The paths-only accessor remains intentional so
  `roundtrip` and `ghosts` are not blocked by unrelated armor validation.
- Combined `report`, `review`, and `review-html` runs now reuse the paths
  configuration already loaded for input discovery when resolving their
  output, avoiding a third read of the same config file.

## 2026-07-26 — deterministic DIM export discovery (#56)

- Added one discovery boundary for all three DIM export kinds. Omitted inputs
  accept the exact filename or either browser-numbered spelling only when it
  is the sole match; multiple matches refuse with every filename and tell the
  user to move/delete stale copies or pass the intended file explicitly.
  Candidates are sorted by filename and timestamps are never inspected.
- Explicit single-command `--input` and combined `--weapons` / `--armor` /
  `--ghosts` paths bypass discovery entirely. For PR #54's later rebase, the
  discovery directory is a separate `run_report` argument: its configured
  `input_dir` must be passed there rather than collapsed into an exact path,
  or the configured default would be mistaken for an explicit input.
- Combined runs resolve every omitted kind before hashing or loading any CSV,
  so an ambiguity in a later kind cannot produce a partial read first. Zero
  matches retain the partial-report contract with an expected-name/pattern
  warning; ambiguity is always fatal, and all-zero errors report every
  expected name and pattern.
- Snapshot warnings keep the full directory in the path field, where snapshot
  sanitisation already reduces it to a basename; their reason text contains
  only the filename/pattern. Fingerprints, the golden snapshot, snapshot
  schema, and ruleset version are unchanged because selected source bytes
  already carry the decision identity.
- Regression tests cover every kind, both numbered spellings, exact-plus-
  numbered ambiguity, stable actionable errors, no newest-wins behaviour,
  explicit bypasses, partial/all-missing reports, clean CLI failures, and
  refusal before any loader or fingerprint read.
- Review follow-up made filename matching ASCII-digit-only and kept it
  deliberately case-sensitive. DIM documents these export names in lowercase,
  and identical matching on case-sensitive and case-insensitive filesystems is
  more predictable than inheriting platform-specific path semantics.
- Empty explicit paths now fail with a clean CLI error instead of resolving to
  the current directory and reaching a loader traceback. Partial-report
  warnings use a readable browser-numbered example rather than exposing the
  regular expression; direct missing/ambiguity diagnostics retain the exact
  pattern for troubleshooting, with command-neutral explicit-path guidance.
- Regression coverage now includes OS-native displayed paths for Windows,
  matching-name directories, directory scan permission failures, Windows/WSL
  `Zone.Identifier` sidecars, Unicode digits, case variants, empty explicit
  paths, and the simplified single-command loader map.

## 2026-07-26 — Windows test suite fixes (#45)

- All four causes confirmed before coding, three of them invisible on Linux:
  - `subprocess.run(text=True)` decodes node's UTF-8 output with the *locale*
    encoding (cp1252 on the reporter's machine) — the `Ãœ`/`ï»¿` mojibake in
    the failure output pins cp1252 specifically. Fixed with
    `encoding="utf-8"` on all three harness calls; a regression from #44 that
    Linux's UTF-8 default masked.
  - `Path.write_text()` translates `\n` → `\r\n` on Windows, so a test
    hashed bytes it never wrote. Both digests reproduced exactly (LF hash =
    asserted, CRLF hash = observed). Fixed with `newline=""` on the one
    digest-sensitive write.
  - Windows temp paths inside TOML *basic* strings hit `\U` as an escape and
    fail to parse. First fixed with TOML *literal* (single-quoted) strings,
    which review caught as correct-but-narrow: a literal string cannot contain
    an apostrophe, so `C:\Users\O'Brien\...` would have broken the same way
    `\U` did. Now encoded with `json.dumps(str(path))` — JSON string escaping
    *is* valid TOML basic-string escaping, and `ensure_ascii` keeps the
    generated config ASCII-safe for non-ASCII profile names. The test's
    directory is named `pri'vate` so the Windows leg exercises apostrophe and
    backslash together, with no extra test.
  - `core.autocrlf=true` checkout translated fixture bytes (`i/lf w/crlf`,
    measured by the maintainer), so every sha256-of-bytes comparison failed.
    Fixed with `.gitattributes` pinning `tests/fixtures/** -text`. Existing
    Windows clones re-materialise with `git checkout HEAD -- tests/fixtures`.
- New meta-test fails a translated checkout with the actual cause and the fix
  command, instead of an opaque hash mismatch; revert-checked by CRLF-ing a
  fixture copy.
- Golden regeneration is now `python scripts/regenerate_report_snapshot.py`.
  The old documented one-liner was POSIX-only twice over: `.venv/bin/python`
  does not exist on Windows, and PowerShell's `>` re-encodes and re-terminates
  redirected output, which would have corrupted the golden's bytes. Review
  caught that this PR *claimed* a portable regen path while shipping a command
  its own target platform cannot run — the same overclaim shape as the #52
  WORKLOG fix. The script writes via `write_bytes` so no platform can
  translate the endings, and deliberately does not import
  `tests.test_report_run`: a maintenance command should not depend on a test
  module. `test_regeneration_script_reproduces_the_committed_golden` pins the
  duplicated recipe against the committed bytes on both CI platforms, so
  byte-stability is a checked invariant rather than a claim.
- `scripts/` is in the ruff scope (AGENTS.md and CI) so the helper is linted
  like everything else.
- CI now runs the suite on `windows-latest` and `ubuntu-latest`
  (`fail-fast: false`). Three of the four causes could recur silently without
  the Windows leg; node is preinstalled on both runner images so the JS tests
  run everywhere.

## 2026-07-26 — M8 adopted: loopback review server (PLAN amendment, #46)

- PLAN.md now plans the localhost bridge instead of listing it as a fallback
  risk. The evidence for the pivot is PR #44: the static artifact makes the
  browser a second implementation of the review-manifest contract, and five
  review rounds were spent closing divergences between it and
  `review.parse_manifest` — object shape, number spelling, UTF-8/BOM decoding,
  then `trim()` on the paste path. A server removes the duplicated manifest
  parser outright; upload/session/verdict/download become explicit,
  Python-owned contracts instead.
- #48 decided **Option A**: the interactive static page retires once the
  server UI proves parity (#50), removed in #51. No deprecation period —
  `review-html` merged after the `v0.2.0` (M6) release and has never shipped
  in a tag. No *known* external usage was identified (public repo, zero
  forks/stars/watchers) — that cannot prove nobody ran it from a clone, so
  the decision rests on the provable fact: it never shipped in a release.
- Framework decided on #49: **Flask 3.1**, the first runtime dependency beyond
  pandas. Recorded with the full cost stated — Flask brings Werkzeug, Jinja2,
  itsdangerous, click, blinker, MarkupSafe (~7 packages, not 2). The
  dependency rule in PLAN.md and AGENTS.md is amended to "pandas and Flask
  3.1, exactly"; `pyproject.toml` changes land with the server code in #49,
  not this docs change. The security-critical work (bootstrap token exchange,
  exact Host/Origin validation, revision checks, atomic finalize) is
  application code under any framework — Flask replaces plumbing, not
  protocol.
- Browser testing decided on #50: **Playwright, dev/test-only**, separate
  Ubuntu CI job, skip-when-absent, no retries to hide flakes. The runtime set
  is untouched by test tooling.
- #38 amended in place: armor what-if variants are **precomputed in Python**;
  the browser switches among bounded server-produced variants. Recomputing
  scores client-side would re-implement `rules/armor.py` in JavaScript — the
  #44 failure mode on far harder logic.
- Measured on real DIM downloads for #47: no save-as dialog; the browser
  writes the expected fixed filename and appends a number when it exists. So
  the ambiguous case (stale exact name beside newer numbered copy) is the
  normal result of exporting twice, which validates refusing ambiguity even
  when the exact name is present.

## 2026-07-26 — configured CLI input/output paths (#47)

- Taught the existing CLI defaults to respect `[paths].input_dir` for known
  DIM export filenames and `[paths].output_dir` for generated import/review
  artifacts. Explicit CLI paths still win, so scripted invocations keep their
  current behaviour.
- Added `--config` to `roundtrip` and `ghosts` so those commands can use the
  same path defaults as the rest of the CLI.
- Configured input directories still go through the existing export discovery
  path, preserving ambiguity refusal for omitted inputs.

## 2026-07-25 — self-contained static HTML review UI (#37)

- New `review_html.py` renders one portable file: inline CSS/JS, the #35
  snapshot embedded as an inert `application/json` data block, and a
  `default-src 'none'` CSP so the page physically cannot fetch or exfiltrate
  anything. No runtime dependency, no asset file (the CSS/JS are Python string
  constants, so packaging needed no `package-data` change).
- Chose a **new `review-html` subcommand** over `review --output x.html`.
  `review --output` already means "the reviewed CSV", and the issue's own
  requirement is that the two write actions stay unambiguous. Each command now
  owns exactly one output, and `report --write` is untouched.
- **A literal `</script>` in the app source truncates its own script element.**
  Found the hard way: an explanatory comment quoted a closing script tag as an
  example of hostile input, which silently cut the shipped script in half — the
  page still parsed, just missing most of its code. Now guarded by a test over
  `APP_JS`/`CSS`/`BODY_HTML`. Snapshot *data* is safe by construction:
  `embed_json` escapes `<`, `>`, `&`, U+2028, and U+2029 to `\uXXXX`, which is
  value-identical JSON but cannot spell a tag or a comment delimiter.
- The page's pure logic is exported under CommonJS when `module` exists and
  only touches the DOM otherwise. That is what lets `test_review_html_js.py`
  extract the script from a *generated artifact* and drive the real filtering,
  grouping, counting, and manifest code under node — skipped when node is
  absent, so nothing new is required to `pip install`.
- Grouping is asserted equal to `report.summarize`'s group headers, string for
  string and in order, so the page and the terminal cannot drift. That works
  because the snapshot's `action`/`reason` are the same pair `reason_slug`
  re-derives from `note`; a test pins that invariant too.
- Ids and hashes never touch a JS number. `compareIds` orders decimal uint64
  strings by length then lexicographically (a test shows `Number()` ties
  2**64-1 and 2**64-2), and `itemsFromSnapshot` *throws* on a non-string id
  rather than coercing one.
- Data-keyed maps are all `Object.create(null)`. An item literally named
  `__proto__` is in the hostile fixture: with a plain `{}` accumulator its
  count assignment is a silent no-op and the whole group vanishes from the
  filter dropdown, which is the failure a test now pins.
- Exported `name` is clipped to 200 **code points** — `review.parse_manifest`
  rejects longer strings, and slicing UTF-16 units could leave half a
  surrogate pair. The 260-character fixture name proves the cap is needed.
- Verified for real, not just in tests: headless Chromium opened the file over
  `file://` with the CSP live, vetoed rows through the actual buttons, approved
  one via the `a` key (focus survives, because a verdict change repaints the
  row in place instead of rebuilding the table), exported, re-imported, and
  `localStorage` worked under `file://`. That exported manifest then went
  through `vault-cleaner review --manifest ... --write` and produced the
  reviewed CSV with exactly the vetoed rows suppressed.
- `SNAPSHOT_SCHEMA_VERSION`/`RULESET_VERSION` deliberately unchanged: no
  decision semantics moved, and bumping the ruleset would invalidate every
  persisted veto for a presentation-only feature.
- Known gap, deliberate: `review-html` does not pre-mark items that already
  have persisted vetoes in `data/overrides.json`, for the same reason `report`
  does not apply them — the page shows what the rules propose. Re-vetoing is
  harmless (merges are additive), but a future `--overrides` flag to seed the
  page's verdicts would be a real ergonomic win.
- Also left out: no browser-side threshold what-if controls. That is #38, and
  every knob a user could turn there is inside the fingerprint, so a what-if
  that changed decisions must not export a manifest against the original run.
- Review follow-up (PR #44), four findings, all accepted:
  - The browser's `readManifest` claimed parity with `parse_manifest` and did
    not have it: **7 of 8** malformed manifests Python refuses, it accepted —
    extra `snapshot.output_path`, extra root and decision keys, a decision of
    only `{id, verdict}`, a 300-character `name`, a numeric `kind`, an empty
    `generated_at`. Import then stored and autosaved the verdicts and reported
    success, so the page said the review was restored and Python rejected the
    same file later. Now mirrors `_check_keys`/`_require_text`/`_require_version`
    in `parse_manifest`'s order, and validates structure *before* comparing
    the fingerprint, so a malformed file says what is malformed.
  - Text length is capped in **code points** (`Array.from(text).length`), not
    UTF-16 units. Python's `len()` counts code points, so a 200-emoji name is
    legal there and naive `.length` would have rejected it — the browser must
    not be stricter than Python either. Both directions are pinned.
  - Parity is now enforced by **one table of ~40 payloads run through both**
    `readManifest` (under node) and `parse_manifest` + `check_manifest_matches`,
    asserting they agree on accept/refuse. Hand-kept case lists on each side
    are exactly how the gap appeared. Both Python calls are needed: a
    well-formed manifest for another run is accepted by `parse_manifest` and
    only refused by `check_manifest_matches`, while the browser does both at
    once. Confirmed non-vacuous by re-running it against the old reader.
  - The `</script>` source guard was case-sensitive. Chromium confirms a
    mixed-case `</SCRIPT >` inside a comment terminates the element and the
    rest of the script never runs — the exact bug the guard exists for, in a
    casing it missed. Now `re.search(r"</script", blob, re.IGNORECASE)`;
    deliberately not `</script\s*>`, since the end tag also terminates on
    whitespace or `/`, so requiring the `>` would weaken it.
  - Two sub-points skipped: making the `_SNAPSHOT_BLOCK`/`_APP_BLOCK`
    *extraction* regexes case-insensitive buys nothing (they match our own
    generated lowercase output), and the ast-grep ReDoS warning on that line
    is a false positive — `APP_ELEMENT_ID` is a module constant, not input.
  - `test_dry_run_does_not_write_to_the_default_path_either` asserted on the
    relative default path, so a leftover artifact from any earlier `--write`
    failed it even though the dry run wrote nothing. Runs from `tmp_path` now.
  - Node subprocesses get `timeout=NODE_TIMEOUT`: an accidental infinite loop
    in the shipped script should fail loudly, not hang the suite silently.
- Review round 2 (PR #44), one more real parity hole:
  - **`JSON.parse` erases number spelling.** `1`, `1.0`, and `1e0` all become
    the same IEEE-754 double, so `Number.isInteger(1.0)` is `true` and no
    post-parse check in JavaScript can tell them apart. Python's `json.loads`
    keeps `1.0`/`1e0` as `float` and `_require_version` refuses non-`int`, so a
    manifest with `"schema_version": 1.0` imported cleanly in the page and was
    then rejected by `parse_manifest` — the same inconsistency round 1 set out
    to close, one level lower down.
  - Fixed on the **raw text**, not the parsed value, because that is the only
    place the distinction still exists. `fractionalNumberError` returns the
    first number token containing `.`, `e`, or `E`. Legitimate because a review
    manifest has *no* fractional field: everything is a string except the three
    integer versions. It is string-aware and escape-aware, so a `name` of
    `"Price: 1.5 (v1.0)"` and the `e` in `true`/`false` are untouched —
    over-rejecting here would break manifests Python accepts, which is a parity
    bug in the other direction and is pinned by accept cases.
  - **Never run that scan over the embedded snapshot.** Armor scores serialise
    as `112.0`, so the snapshot legitimately contains floats; the rule is about
    imported manifests only.
  - New `readManifestText(snapshot, items, text)` is the single entry point —
    bytes in, verdict out, the same contract as `parse_manifest(path)`. The
    parity harness now feeds both sides identical *bytes* rather than a parsed
    object, which is what makes spelling and unparseable text testable at all.
    `importText` lost its duplicated `JSON.parse` branch to it.
  - The deeper miss was the **table**, not the code: it had integer, boolean,
    string, and missing versions but no integral-float *spelling*, so it passed
    while the gap was open. Now 54 cases (8 accept, 46 refuse), including
    `1.0`/`1e0` in all three version positions, `NaN`, `Infinity`, truncated
    JSON, and non-object roots. Lesson: a parity table is only as good as the
    axes it varies — type and presence were covered, spelling was not.
  - Deliberately did **not** loosen Python to accept `1.0`. `_require_version`
    is shared with `load_overrides`, so it guards persisted state too, and
    AGENTS.md's rule for manifests is to validate strictly. Also rejected
    `JSON.parse`'s reviver `context.source`: it gives exact token access and
    works in node 22, but support is recent enough that strictness would vary
    by browser, and an invariant that holds "depending on your browser" is not
    an invariant.
  - Line-length nit skipped as a rule but applied locally: there is no
    `[tool.ruff]` section, `E501` is not in ruff's default rule set, and
    existing tests run to 118 characters, so the 90-character signature was not
    violating anything. Wrapped for consistency with the newer files only.
- Review round 3 (PR #44), the decode boundary — one flagged divergence, two
  more found while verifying it:
  - **`FileReader.readAsText()` substitutes U+FFFD** for malformed UTF-8 rather
    than failing, so a mis-encoded manifest imported and autosaved cleanly while
    Python's `read_text(encoding="utf-8")` refused the same bytes. Confirmed in
    Chromium: `"na\x80me"` came back as `"na�me"`.
  - **`readAsText()` also strips a leading BOM** (checked: `EF BB BF 7B 7D`
    decodes to `{}`), where Python keeps U+FEFF and `json` then refuses it. So
    the naive fix makes things worse — `TextDecoder`'s default strips the BOM
    too. `{ fatal: true, ignoreBOM: true }` is the only combination that agrees
    with Python on all four inputs, and `ignoreBOM` is load-bearing rather than
    decoration. A revert-check pins it: dropping it flips `bad_utf8_bom_prefix`
    to browser-accepts/Python-refuses, trading one divergence for another.
  - **Python was crashing, not refusing.** `_load_json_object` caught `OSError`,
    but `UnicodeDecodeError` is a `ValueError`, so mis-encoded bytes escaped
    `parse_manifest` uncaught and past the CLI's `except ReviewError` — a
    traceback where an `error:` line belongs, and the class of bug #43 tracks.
    Widened to `except (OSError, UnicodeDecodeError)`; `load_overrides` shares
    the helper, so a mis-encoded `data/overrides.json` stopped crashing too.
    Note this is not a reversal of round 2's "leave `review.py` alone": that ask
    was to *loosen* what it accepts, whereas this changes no accept/reject
    decision at all — the same bytes are refused either way — it only makes the
    refusal sayable.
  - The harness now compares **bytes in, verdict out** through the page's own
    `readManifestBytes`, so it cannot model a decode the page does not perform.
    It previously used node's `buffer.toString("utf8")`, which keeps a BOM where
    the browser strips one — meaning the harness had never matched the real
    page. 61 cases now (10 accept, 51 refuse).
  - Follow-up nit, and a fair catch: the new BOM tests embedded **literal**
    U+FEFF characters in Python string literals. Replaced with `\ufeff`
    escapes. Embarrassing repeat — a literal U+2028 typed into `review_html.py`
    earlier in the same work arrived as a NUL byte and made the module
    unimportable, which is exactly why `embed_json` uses escapes. Now guarded:
    `test_no_source_blob_contains_an_invisible_character` scans `APP_JS`/`CSS`/
    `BODY_HTML` for Cf/Cc/Zl/Zp characters. A literal NUL needs no guard —
    Python refuses to import the file at all; the guard is for the ones that
    parse silently and leave no trace in a diff. A scan of `src/` and `tests/`
    found no others.
  - **The recurring lesson, three rounds running:** each time, the two
    implementations were being compared one layer too high — objects, then text,
    now bytes. The parity idea was right from the start; the *boundary* was
    wrong. Compare at the outermost layer the real entry points use, and add
    accept cases at each layer, since every fix here risked over-rejecting
    (a `name` containing `1.5`, a name with emoji, an interior U+FEFF).
- Review round 4 (PR #44), the same divergence on the **sibling path**:
  - The paste handler called `.trim()` on the textarea value *before*
    validating it. **JavaScript's `trim()` is not JSON whitespace:** it removes
    U+FEFF, U+00A0, U+2028, and U+3000, none of which JSON accepts. So all four
    prefixes were laundered into accepted manifests while Python refused the
    same text — including the BOM case fixed on the *file* path one round
    earlier. Passing the value untouched costs nothing, because `JSON.parse`
    already allows ordinary leading and trailing JSON whitespace; `trim()` now
    answers only the question it can, "is the box empty".
  - **Why three rounds of parity work missed it:** the parity harness covered
    `readManifestBytes` (the file input) and the paste path's normalisation sat
    inline in an un-exported click handler inside `boot()`, unreachable by any
    test. The UI had two import entry points and the table covered one. Both are
    now exported and both are columns in the table — 65 cases, the paste column
    covering the 61 whose bytes are valid UTF-8, with an assertion that the skip
    set is exactly the undecodable ones so coverage cannot shrink quietly.
  - Proven by revert: restoring the `trim()` leaves the **file** column green
    and fails only the **paste** column, which is precisely why the old
    single-column table could not have caught it.
  - **The actual lesson, and it is not "check one more layer":** when a
    divergence is found on one path, fix every sibling path in the same change.
    Round 3 had the BOM bug in hand and closed it in one of the two places.
    Normalisation hidden in UI code is where these survive, so anything that
    touches input before validation belongs in the exported, tested layer.
  - Also: typed literal U+00A0/U+2028/U+3000 into the new test cases while
    writing them, one round after being told off for literal U+FEFF. The
    existing guard only covers `APP_JS`/`CSS`/`BODY_HTML`, not test files. Caught
    by scanning at the byte level — `str.splitlines()` splits on U+2028, so a
    line-based scan cannot see the character it is looking for.

## 2026-07-25 — persistent review overrides and reviewed export (#36)

- New `review.py` owns the review manifest schema, `data/overrides.json`, and
  the classification of saved vetoes against a fresh run. `report` is
  unchanged and still shows raw proposals; it only prints a pointer line when
  vetoes exist, so "what the rules propose" stays distinct from "what I
  approved". One `review` command covers both inspection and application:
  without `--manifest` it just reports override status.
- Vetoes never reach the CSV writer as a second implementation — final rows
  go through `write_import_csv()` unchanged, pinned by a test comparing the
  reviewed CSV byte-for-byte against the same filtered rows through the
  Python writer.
- A veto only applies while it still describes the proposal the reviewer saw.
  If the rules now propose something else for that id it goes **stale** and is
  *not* applied. Chosen deliberately: the item resurfacing for review is the
  safe direction to fail, and note-wording drift silently suppressing an
  unreviewed decision is not.
- `orphaned` (id gone from a loaded export) is kept distinct from `unchecked`
  (that export was skipped this run). Collapsing them would make a missing
  `data/in/destiny-ghost.csv` look like a vault full of dismantled ghosts.
- Applying a manifest is additive: an `approved` verdict never removes an
  existing veto. A UI that forgot a previous session must not be able to
  resurrect junk the user already rejected; un-vetoing is an explicit file
  edit, reported on stderr when it comes up.
- Merges take display metadata from the *run*, not the manifest — only
  identity crosses the boundary. Manifest parsing rejects unknown keys
  outright (an `output_path` key is an error, not something ignored), unknown
  schema/ruleset versions, non-string or non-DIM-shaped ids, and any id
  appearing twice, whether the verdicts agree or conflict.
- `ReportSection` gained `item_ids`, deliberately *not* in the snapshot: it is
  run-local bookkeeping needed to tell orphaned from stale, and adding it to
  the shareable snapshot would have churned schema v1 for no consumer.
- `save_overrides` writes via same-directory temp file → fsync → `os.replace`
  → directory fsync, with the temp file removed on any failure. Tested by
  making `os.replace` and `json.dump` fail: the previous file survives
  byte-identical and no `.tmp` is left behind. Directory fsync failure is
  tolerated — the replace already happened by then.
- `RULESET_VERSION` deliberately not bumped: no rule ordering or decision
  semantics changed. The golden snapshot is untouched for the same reason.
- Gap worth knowing: nothing generates a manifest yet — #37 is the producer.
  The schema is documented in README so one can be hand-written meanwhile.
- Review follow-up (PR #42), two findings, both accepted:
  - `os.fsync` failure on the directory handle was tolerated but the `os.open`
    that precedes it was not, and by then `os.replace` has already committed.
    The raise escaped before `write_import_csv()`, so a *successful* write was
    reported as a failure and left persisted vetoes with no reviewed CSV to
    match them. Now one `_fsync_directory` helper where nothing past the
    commit point may propagate. Windows refuses `O_RDONLY` directory handles
    outright; `EMFILE`/`EACCES` reach the same place on Linux.
  - Persisted `kind` was accepted as any non-empty text, but `classify` reads
    it functionally. A hand-edited `"weapon"` could only ever land in
    `unchecked` and be reported forever as "that export was not loaded" — the
    exact lie the unchecked/orphaned split exists to prevent, reachable via
    the README's own advice to edit the file to un-veto. Now validated against
    `report_run.EXPORT_KINDS`, one vocabulary derived from
    `DEFAULT_EXPORT_PATHS`.
- Two non-changes, decided rather than overlooked. Manifest `kind` stays
  unvalidated: `merge_manifest` discards it and re-reads kind from the run, so
  there it is free-text display metadata beside `name`/`hash`/`action`/
  `reason`, none of them enumerated. Overrides `action`/`reason` stay
  unvalidated too — they are functional, but a typo degrades safely to
  `stale`, which is truthful. `kind` is the only field whose bad value
  produces a wrong explanation.
- `OVERRIDES_SCHEMA_VERSION` not bumped: this rejects files that were always
  malformed, it does not change the format.
- Both fixes were confirmed by reverting each and watching the new tests fail.
  The `os.open` fake has to be selective — `review.os` *is* the `os` module,
  so a blanket patch breaks `tempfile.mkstemp`; match on `flags == os.O_RDONLY`
  and delegate otherwise.
- Second review round found the helper did not keep its own promise:
  `os.close(dir_fd)` sat in a bare `finally` and could still propagate,
  recreating the exact persisted-vetoes-without-CSV outcome. Restructured so
  open/fsync share one tolerant block and close is separately swallowed, with
  `dir_fd = None` guarding the case where the open itself failed. Three
  targeted tests now pin open, fsync, and close; each was confirmed by
  reverting the fix and watching it fail.
- Still unresolved, not part of this PR: `save_overrides()` and
  `write_import_csv()` are two files with no transaction between them, so a
  failed CSV write leaves vetoes persisted without an export. The current
  order is deliberate — overrides are the durable record of human decisions,
  the CSV is derived and regenerable by re-running.

## 2026-07-25 — pytest imports the checkout under test (#40)

- `pytest` run from a git worktree was exercising the **main checkout's**
  source. The editable install is setuptools' static flavour: a single
  absolute `src` path in `__editable__.vault_cleaner-0.1.0.pth`, injected
  into every interpreter using the venv regardless of cwd. Nothing competed
  with it — src layout, no `tests/__init__.py`, and `testpaths` was the only
  pytest ini setting, so pytest prepended `tests/` (no importable package)
  and the `.pth` won.
- Surfaced during the #39 review rounds: a fault injected into a worktree
  passed cleanly, and the real result only appeared after pinning
  `PYTHONPATH`. Reproduced here before fixing — a worktree with
  `write_import_csv`'s DIM quote re-wrapping deleted still reported
  `201 passed`. With `pythonpath = ["src"]` the same worktree correctly
  fails the two round-trip tests.
- Branch skew is not required for this to bite. Uncommitted edits in either
  tree, or `main` moving while a worktree review is in flight (#39 merged
  mid-review), are enough. The failure is silent, which is what makes it
  worth config rather than reviewer discipline.
- `tests/conftest.py` now asserts the imported `vault_cleaner` sits under
  pytest's own `rootpath/src`, raising `pytest.UsageError` with both
  resolved paths. `pythonpath` fixes today's mechanism; the guard means any
  future mechanism that reintroduces the skew fails loudly instead of
  passing. Verified it refuses when `pythonpath` is disabled.
- No escape hatch was added: there is no workflow here that deliberately
  tests an out-of-tree install, and an opt-out would reopen the silent path.

## 2026-07-25 — M7 foundation review follow-up (#35 / PR #39)

- Made effective TOML config recursively JSON-safe (date/time values use ISO
  strings) before fingerprinting or snapshotting; this closes an uncaught
  `TypeError` regression without accepting arbitrary object stringification.
- Split snapshot schema v1 from ruleset v1 so presentation-only schema changes
  do not invalidate persisted reviews, while decision-semantic changes do;
  documented the required version bump beside the rule conventions.
- Shareable snapshots reduce source and skipped-export paths to basenames and
  omit configured directories plus unknown TOML sections, while the in-memory
  `ReportRun` and CLI retain truthful full paths and effective config. Warnings
  stay structured in the snapshot; only the CLI renders presentation text.
- Fingerprints and snapshots share one allowlisted decision config, filtered to
  the exact nested `rails` and `armor` keys consumed by rules. External content
  is covered separately by export, wishlist, and manifest identities, so a
  snapshot can reproduce its fingerprint from its own recorded inputs without
  leaking free-form config. A recursive DEFAULTS coverage test makes future
  thresholds fail CI until they are added to the projection.
- Reused one streaming file-digest helper, detected export changes across load,
  and fingerprinted the exact captured wishlist bytes that were parsed. Wishlist
  downloads now accept only HTTP(S), and source/wishlist races become domain
  errors rather than raw filesystem failures.
- Made armor `set_bonus` consistently a JSON float, removed the misleading
  frozen marker from evaluations containing mutable stats, and restored an
  explicit manifest refresh as a forced rebuild while retaining normal
  same-version cache reuse.
- Pinned the CI dev tools after unbounded Ruff drift made local 0.15.22 pass
  while CI's 0.16.0 reported nine findings; updated those findings and added a
  checked-in schema-v1 golden snapshot, a documented regeneration command,
  and focused regression coverage. Schema v1 remained intentionally fluid while
  this PR was unmerged; the final golden pins the pre-merge contract.
- The golden test exposed that `load_config` shallow-copied nested defaults,
  letting one caller contaminate later report runs; defaults are now deep-copied
  and an order-isolation regression test pins that behavior.

## 2026-07-24 — M7 foundation: reusable report snapshot (#35)

- Extracted ordered rule execution from `cli.py` into `pipeline.py`;
  individual commands and the combined report now share the same public
  weapons/armor pipeline results. The CLI remains the dry-run / explicit
  `--write` presentation boundary, and its summary/CSV behaviour is unchanged.
- Added `report_run.py`: available exports become a structured `ReportRun`
  with per-section source metadata, original item state, decisions, conflicts,
  effective config, armor score evaluations, and a deterministic JSON-safe
  snapshot (schema v1). DIM instance ids and hashes stay opaque strings.
- Snapshot fingerprints cover export bytes, the effective config, raw cached
  wishlist files, and both the Bungie manifest version and the semantic perk
  map digest. `manifest.load_perk_map_data` exposes version metadata while the
  existing `load_perk_map` dict API remains compatible.
- Armor scoring now records every scored legendary's raw base stats, base and
  bonus score, class/slot rank, protection state, and source tag/notes for
  the later static review/what-if tickets; rule decisions did not change.
- Ruff clean; 186 tests pass (176 before this ticket).

## 2026-07-20 — v0.2.0 tagged; last-of-kind guard in the score pass (#30)

- v0.2.0 tagged + released (M6). First real post-M6 import run surfaced
  the next design gap: the score pass junked the vault's only
  weapons/grenade/super Gunner Ferropotent Mark at score 40 — no dupe
  reasoning, just build-misfit against the single configured archetype.
  Its four same-archetype set-mates survived only because their identical
  stats earned them close-dupe review notes (accidental shielding).
- **Measured before designing:** 115/175 junk rows were the last kept
  copy of their (Hash, Archetype); 174/175 the last at
  (Hash, Archetype, tertiary) — the dupe passes already remove real
  duplicates, so the score pass mostly sees unique rolls, and a
  full-granularity guard would kill it (rejected). 5 (class, set) combos
  lost 4-piece fieldability; the archetype-level guard fixes all 5 free
  (every slot's pieces share one Hash).
- **Owner-picked policy: (Hash, Archetype).** Score pass now runs two
  phases — classify, then junk — and demotes the best-scoring junk
  candidate of any combo that would otherwise lose its last kept copy
  (`#vc-review: armor-last-archetype (<archetype>), armor-score …`).
  Ties break on id, never CSV order. Review-noted pieces from earlier
  passes count as survivors via `kept_elsewhere` (an exact-dupe junk
  always leaves an identical twin, so those combos were already safe).
  `Archetype` is schema-required (empty = legacy, valid).
- Real vault (fresh export, 884 pieces): 73 junk, 102 last-archetype
  demotions. The original Gunner mark still junks — four better Gunner
  set-mates survive, so the combo isn't foreclosed; lock a specific roll
  in DIM to keep it (soft rail).
- Also: PR #27 had merged into its stacked base branch instead of main
  (GitHub only retargets when the base branch is deleted) — re-landed as
  #28 by cherry-picking the stranded squash. Verify content reached main
  after merging stacked PRs.

## 2026-07-19 (M6, part 2) — armor close-dupe pass (#18)

- `rules/armor_close.py`: review-only — dominated (`armor-dominated by
  <id> (+N total)`) and similar (`armor-similar to <id>`), compared within
  Hash + Tier only. The measured collapse (#16): every vault legendary is
  in a manifest set and every set has exactly one hash per class×slot, so
  class+slot+tier+set-signature ⇔ Hash + Tier — no set table, no manifest,
  no network. A dominated pair is never also "similar" (either direction of
  domination excludes the pair); one note per piece, best partner
  (closest, then lowest id — order-independent, tested by CSV reversal).
- Caps in `[armor.close_dupes]` (`max_stat_delta = 5`, `max_total_delta =
  12`), validated non-negative-int with a named error on partial override.
  Measured bimodality means any cap 1–9/1–19 picks the same pairs today.
- Pipeline: rails → exact dupes → close dupes → score. **Deliberate
  consequence:** junk dropped 227 → 175 on the real vault, because ~52
  near-twin pieces the score pass used to junk now get a close-dupe
  review note instead — earlier passes win, and a near-dupe deserves
  human eyes over a blind score junk.
- Real vault: 124 close-dupe reviews (mostly "identical stats, tuning X
  vs Y" — the tuning-twin cluster measured in #16), 0 dominated (as
  measured: structurally impossible at tier 5's fixed 75 totals).
- Review follow-ups: `Tier` schema-required (the close pass groups on it —
  drift was a KeyError, now a SchemaError). Score pass no longer junks a
  piece cited as a close-pass dominator ("only kept pieces dominate" —
  under a strict-but-valid config the old code reviewed 6002 as "dominated
  by 6001" then junked 6001; similar partners never needed the shield
  because their notes are symmetric, so both sides are already decided or
  hard-protected).
- Round 2 (owner call, follows the #17 spiritless guard): the Spirit
  signature joined the close-pass compatibility bucket — two exotic class
  items with different Spirit combos are functionally different pieces
  (same rule as set bonuses), and a spiritless copy is an unknown roll,
  compared with nothing. Real vault: 124 → 115 close reviews; the 9
  removed notes were cross-spirit "similar" advice, i.e. misleading.
- Round 3: the shared `unknown_spirit_roll` helper now also rejects
  truncated signatures (fewer than the measured two Spirits), closing the
  round-2 gap in both passes — a one-Spirit copy sharing its first Spirit
  with a full roll no longer compares with it. Real vault unchanged.

## 2026-07-19 (M6) — armor measurement spike + exact-dupe pass (#16, #17)

- **Spike first (#16), and it rewrote both designs** — full numbers in the
  issue comments. Highlights: the Perks columns are a masterwork-gated
  socket dump (unupgraded copies export almost nothing), so raw perk
  hashing is unusable; but Hash already implies the set perk — the
  manifest's DestinyEquipableItemSetDefinition has 56 sets × exactly one
  hash per class×slot, covering every legendary in the vault. Tuning Stat
  is roll identity, not socket state (present before anything is socketed;
  a socketed '+X/-Y' always matches it on legendaries; always empty on
  exotics — and one tier-5 legendary quirk-exports it empty). No tuning
  leak into base stats: every tier-5 piece totals exactly 75 base.
  Tertiary Stat/Archetype are derivable from base stats. Exotic class item
  Spirit perks are roll identity and visible on every copy.
- `rules/armor_dupes.py` (#17): fingerprint = Hash + 6 base stats +
  Tuning Stat + Seasonal Mod + Holofoil + Spirit signature. Survivor:
  hard > loadout > locked > masterwork > power, then lowest id — reversing
  the CSV changes nothing (tested). Loadout losers review-only (loadouts
  pin instance ids). Fingerprint + ranking columns are now
  schema-required; PLAN.md rules list amended (exact + close dupes).
- Armor pipeline is now rails → exact dupes → score via `_resolve_armor`
  (shared by `armor` and `report`); earlier passes win, one decision per
  item.
- Real vault: 7 exact-dupe rows — 1 junk, 1 loadout review (the rule fired
  on real data: an identical twin survives but the loser is in a loadout),
  5 exotic reviews. Small by design; the volume lives in the close-dupe
  pass (#18): dominated is structurally impossible within tier 5 (fixed 75
  totals) and "similar" is bimodal — 65 pairs differ only in Tuning Stat,
  then nothing until far-apart archetypes.
- Review follow-ups: Masterwork Tier / Power cells validated
  empty-or-digits at load (to_int would coerce garbage to 0 and silently
  flip a survivor; strict `\d+` would repeat the ghost-pass mistake — the
  measured export is all digits, but empty legitimately means
  unmasterworked). `Perks 0` is schema-required, so the Spirit identity source
  can't vanish silently; and (owner call, round 2) the belt-and-braces
  guard is in too — an exotic class item exporting no Spirit perks is an
  unknown roll and is never grouped. Round 3 closed the guard's own gap:
  a complete roll is exactly two Spirits (measured, 38/38 copies), so a
  one-Spirit signature is a truncated identity — two rolls sharing their
  first Spirit must not merge — and anything shorter than
  `SPIRIT_ROLL_SIZE` is now treated as unknown. The guards only fire on
  data we haven't seen — better silent than wrong. Ordinary exotics (no
  spirits by design) still group normally.

## 2026-07-19 (wrap-up) — v1 chores (#21)

- AGENTS.md gotchas absorbed the durable worklog lessons (empty ghost rank
  columns, fixed Armor 3.0 spikes, manifest name→hash, stacked hashtags,
  csv CRLF, build/ artifacts) so future agents get them up front.
- ruff added to CI (one finding: unused import, autofixed).
- Older fixtures (weapons/ghosts/weapons_dupes) normalized to LF.
- pandas pinned `>=3.0,<4` — the venv and CI actually run pandas 3.0.3;
  the old `>=2.0` floor advertised an untested major version.
- After merge: tag v0.1.0 on main — all five milestones + full board done.

## 2026-07-19 (late) — MIT license (#10, PR #20)

- **Owner decision: MIT.** LICENSE file (copyright Tony M), PEP 639
  metadata in pyproject (`license = "MIT"`, `license-files`, setuptools
  ≥77.0.3), README section. All five PLAN.md milestones plus the board
  are now complete; v1 wrap-up chores tracked in #21.
- Review note: kept the README heading "License" (en-US) — repo prose
  follows ecosystem convention and DIM's own en-US terms; an en-GB sweep
  would belong in #21 if ever wanted.

## 2026-07-19 (evening) — M5: dry-run summary report (#9)

- `vault-cleaner report`: runs weapons (wishlist-aware), armor, and ghost
  passes dry, prints "would junk N item(s) and flag M for review" grouped
  by action + reason with per-item lines beneath (junk groups first,
  largest first). `--write` emits one combined import CSV. Missing exports
  are skipped with a warning; item sets are disjoint across passes so
  concatenation is safe.
- `report.reason_slug` parses the reason out of the `#vc-` hashtags —
  the notes remain the single source of truth for reasons.
- `_resolve_weapons` helper extracted so `dupes` and `report` share the
  wishlist/manifest setup.
- Real vault: 430 junk + 135 review across 1,580 items.
- PLAN.md's `--profile pvp|pve` stretch idea intentionally not done —
  file a ticket if wanted.

## 2026-07-19 (later) — Ghost pass redesigned: protection-only (#8, PR #15)

- **Owner decision during review: no ranking at all.** The ranking design
  below went through two review rounds (empty rank columns → tie-breaks →
  determinism) before the honest conclusion: ghosts carry no quality
  signal, and "top N" was an arbitrary policy wearing a ranking costume.
  Final policy: keep only shells that are equipped, **locked (the lock IS
  the keep signal for ghosts — no #vc-review)**, tagged
  favorite/keep/archive, or **referenced by a saved DIM loadout**
  (`Loadouts` column, now schema-required); junk everything else as
  `#vc-junk: ghost-unprotected-surplus`. Rarity still irrelevant.
  Rationale: mods move freely, Collections reacquires dismantled shells,
  and dry-run + DIM review + in-game dismantle remain the gates.
- Removed: `ghosts.keep_top_n`, rank-column schema/validation, tie-breaks.
  Ghosts take no config — lock/tag shells in DIM to keep them.
- Real vault: 29 shells → 17 junk, 12 protected.

## 2026-07-19 — Ghost cleanup pass (#8) — superseded, see above

- `rules/ghosts.py` + `vault-cleaner ghosts`. **Measured data reshaped the
  ticket sketch:** zero duplicate hashes exist, ghost mods move freely
  between shells (the mod carries the utility), and 28/29 shells are
  Exotic *rarity* — cosmetic for ghosts. So: rank all shells by Energy
  Capacity then Masterwork Tier, keep top `ghosts.keep_top_n` (default 6),
  junk the surplus with rank in the note.
- **Deliberate rails deviation:** exotic rarity is NOT a soft rail for
  ghosts (it would flag everything and clean nothing). Locked still
  reviews — checked directly because `rails.protection` reports exotic
  before locked. Tags/equipped hard-protect as usual.
- Real vault: 29 shells → 15 junk, 5 review, top 6 + 3 protected kept.
- New fixtures now written LF-only (csv module defaults to CRLF).
- Review follow-up + finding: **current DIM exports leave Energy Capacity
  and Masterwork Tier EMPTY on every shell** (retired system) — ranking
  ties at (0,0) and falls back to export order. Rank columns are now
  schema-required, cells validated empty-or-digits (strict `\d+` à la
  armor would reject the real export!), and notes say "no
  energy/masterwork data" instead of fabricating "energy 0" rankings.

## 2026-07-18 (late night) — M4: armor loader + archetype scorer (#6, #7)

- `load_armor` on the shared loader; **`ARMOR_STATS` in parse.py is THE
  stat lookup table** (canonical name → `(Base)` column) — an Armor 3.0
  rename is a one-line fix there. Weapons schema now also requires `Ammo`
  because an armor export otherwise satisfies it silently.
- `rules/armor.py`: score every legendary against each configured
  archetype, take the best; favored-set perks (matched by name in Perks
  columns, e.g. "Erebos Glance") add `set_bonus`. Keep top-N per slot per
  class OR anything ≥ floor; junk only both-outside, with reason
  (`#vc-junk: armor-score 56 < floor 65 (best: melee_primary, rank 26/50
  titan gauntlets)`). Rails as usual; exotics never scored.
- **Design finding (measured, not assumed):** every Armor 3.0 tier-5
  piece has the same fixed 30+25 stat spike and ~75 base total, so the
  planned "generic spike profile" scores everything identically (165) and
  discriminates nothing. Dropped from defaults (mechanism `top_stats = N`
  remains for legacy armor); scoring is entirely build-alignment weights.
  Scores are normalized to the Total (Base) scale.
- Real vault: 872 pieces, 559 legendaries scored → 227 junk, 38 review.

## 2026-07-18 (night) — M3 complete: wishlist matching in the rules (#5)

- **Perk name→hash resolved via the Bungie manifest** (`manifest.py`):
  DestinyInventoryItemDefinition is public static JSON (no key/OAuth — still
  inside the no-API-integration rule, which is about live inventory).
  ~200MB one-time download reduced to a ~1MB name→hashes cache in
  `data/cache/`; on staleness only the small index is re-checked, the big
  file re-fetched only when Bungie's manifest *version* changes. One name
  maps to several hashes (base + enhanced variants) — kept deliberately so
  wishlist entries citing either variant match.
- `rules/weapons.py`: full pipeline rails → wishlist pass → dupes. Trash
  match (whole-item or roll ⊆ item perks) → junk / review-if-soft, unless a
  keep roll also matches. Keep matches feed `dupes.resolve` as the
  top-ranked key (match count). Perk names from `Perks N` columns, trailing
  `*` (DIM's selected marker) stripped.
- `dupes` CLI now runs the wishlist pass by default; `--no-wishlists`
  opts out; wishlist/manifest failures error cleanly with that hint.
- Real vault: 679 weapons → 186 junk, 97 review; 23 wishlist-trash calls.
- Review follow-ups: **PLAN.md amended (user-approved)** — the no-API rule
  now precisely bans authenticated access (keys/OAuth/live inventory)
  while permitting unauthenticated static content like the manifest.
  Keep-over-trash conflicts are counted and reported by the CLI (15 in
  the real vault). Cache validation checks every name→hash entry. The
  unwritable-cache test monkeypatches the write instead of chmod (which
  silently doesn't block writes on Windows-backed mounts — it failed on
  the user's WSL setup while passing in CI).

## 2026-07-18 (evening) — M3 part 1: wishlist download/cache/parse (#3, #4)

- `wishlist.py`: `fetch` (cache in `wishlists/`, re-download after
  `wishlists.max_age_days`, stale-cache fallback with warning when offline,
  `WishlistError` only when there's no copy at all) and `parse_wishlist`
  (defensive: non-`dimwishlist:` lines ignored, malformed entries counted
  in `.skipped`, DIM's `-69420` wildcard entries counted but unsupported).
- Sources in `config.toml`: 48klocs choosy_voltron (keep + trash entries)
  and Nitaraku/dim-wishlists aegis_wishlist.txt (auto-generated from the
  Aegis PvE tierlist, actively updated). Real parse: 252k keep rolls + 53
  trash entries (choosy), 5k keep (aegis).
- **Decision:** `wishlists/` stays gitignored — choosy_voltron alone is
  26MB of refreshable third-party content.
- Review follow-up: added the Aegis **trash** list (Ciceron14/
  dim-extra-wishlists, 291 whole-item entries for D-tier-or-lower; updates
  less often than the keep lists). That list writes whole-item trash as
  `&perks=` (present, empty) — the parser now accepts that deliberately
  while still rejecting separator-only `perks=,` as malformed. Also:
  digit runs bounded to uint32 length (huge numbers can't crash `int()`),
  and malformed URLs fall back to stale cache like any download failure.
- **Open question for #5:** wishlist perks are hashes; the DIM export has
  perk *names*. Matching needs a name→hash bridge (or a hash-bearing
  export) — investigate before building the matcher.

## 2026-07-18 (later) — M2: safety rails + dupe resolver

- **Design change from the plan (user decision):** rails are now two-tier.
  Hard (never touched): favorite/keep/archive tags, equipped, crafted ≥
  `rails.crafted_level_protect` (config, default 10). Soft (never tagged
  junk, `#vc-review` note when outranked as a dupe, existing tag/notes
  preserved): **locked and exotic items** — the user wanted recommendations
  on those rather than blanket protection. PLAN.md rule 1 updated.
- `rules/rails.py` (protection classifier), `rules/dupes.py` (group by
  Hash, rank: gear Tier > masterwork > crafted level > stat total; ranking
  takes a pluggable `wishlist_key` for M3 to prepend), `config.py`
  (tomllib + defaults), `vault-cleaner dupes` CLI (dry-run default).
- Output rows append our hashtag to *existing* DIM notes rather than
  replacing them; review rows carry the item's existing tag so import is a
  tag no-op.
- Real-vault dry run: 684 weapons → 184 junk, 89 review.

## 2026-07-18 — Repo bootstrap, M1, ghosts, published

- Initialized repo from PLAN.md; `data/` gitignored from the first commit.
  Layout: `src/vault_cleaner/` (parse, report, cli, rules/), `tests/`,
  `wishlists/`, `data/in|out/`, `config.toml` stub.
- **M1 done.** `vault-cleaner roundtrip` parses a DIM export by header name
  (loud `SchemaError` on drift), tags one sacrificial item, writes a DIM
  `Id/Hash/Tag/Notes` import CSV. Dry-run default, `--write` to emit.
  Verified against a real export (684 weapons). **Round trip confirmed in
  DIM**: imported CSV set tag=junk + note on the target item (screenshot
  check by user). M1 fully done.
- **Ghost support added** (`--kind ghosts`). Ghost exports lack the `Type`
  column, which forced per-kind schema sets — see AGENTS.md gotchas.
- **Finding:** "A Good Shout" exists under two different item hashes
  (seasonal reissue). Dupe resolution (M2) must group by `Hash`, not name.
- Published to https://github.com/tonym999/vault-cleaner (public). Verified
  no vault data anywhere in git history first.
- Decisions: pandas as the only runtime dep; fixtures pinned to real export
  headers with fake rows; `wishlists/` gitignored for now (PLAN.md marks it
  TBD).
