# Browser and accessibility verification

Use this checklist for changes to the local review server UI. Use only fake
fixtures from `tests/fixtures/`, start with `--no-wishlists`, and never use an
export from `data/`.

## Reusable checklist

Record before testing:

- Date, operating system, and browser/version.
- Desktop viewport and narrow viewport/device width.
- Fixture exports used.
- Whether the browser was headed or headless; retain screenshots when a
  headless browser supplies the visual pass.

Visual and responsive checks:

- [ ] General desktop layout is legible with no overlapping controls or text.
- [ ] Light appearance has readable text, borders, badges, and statuses.
- [ ] Dark appearance has readable text, borders, badges, and statuses.
- [ ] Narrow layout stacks controls and summary tiles; proposal tables remain
      usable through their contained horizontal scroll area.
- [ ] Focus is plainly visible on links, file inputs, filters, row controls,
      lifecycle controls, and verdict buttons.

Workflow and keyboard checks:

- [ ] Bootstrap reaches the authenticated page and upload statuses are clear.
- [ ] Uploads produce a report with counts, filters, and proposal controls.
- [ ] Search, each applicable filter, grouped/flat view, sortable columns, and
      expanded details remain usable.
- [ ] Keyboard-only row review supports <kbd>a</kbd>, <kbd>v</kbd>, and
      <kbd>u</kbd>.
- [ ] Acknowledged row repaint preserves keyboard focus.
- [ ] Finalisation confirmation is understandable when proposals remain
      unreviewed.
- [ ] Finalised state is visibly frozen; uploads and verdict controls are
      disabled.
- [ ] **Download again** returns the finalised CSV without another finalise.
- [ ] **Reset / Start new review** returns to an upload-ready idle state.
- [ ] **Shutdown** ends the local session and leaves clear terminal guidance.

Issue #104 focused check:

- [ ] Ordinary Proposals shows a labelled `Tuning Mod Slot` pair for an armor
      candidate and its selected survivor/partner before expansion or hover;
      equal and `none/unknown` values remain explicitly labelled on both sides.
- [ ] The tuning text is distinct from the six-stat armor-scoring display and
      remains legible in desktop light/dark appearances and at approximately
      390×844; horizontal table scrolling is contained when needed.
- [ ] The field is rendered as text, not only by color, and remains readable
      after acknowledgement and in finalised/read-only state.

Issue #102 focused check:

- [ ] The surface selector offers Proposals and Armor duplicates when an
      authoritative exact group exists; the duplicate option is unavailable
      when no exact groups exist.
- [ ] Every duplicate group shows its complete backend membership, with the
      preferred survivor first, retained/protected copies, and proposed copies
      labelled from their structured dispositions.
- [ ] Group headers always show the archetype, tier-5 30/25/20 role summary
      (or an honest six-stat fallback), and the text-labelled Tuning Mod Slot;
      Spirit, Seasonal Mod, and Holofoil values remain inert text.
- [ ] Name/instance-id search and Class, slot/type, archetype, and tuning
      filters select whole groups and report `Showing N of M groups`.
- [ ] Only proposed members expose Approve/Veto/Unset controls. An
      acknowledged proposal-member verdict is reflected in both surfaces.
- [ ] Survivor and retained members remain explicitly read-only; finalised
      duplicates remain readable while all mutation controls are frozen.
- [ ] Keyboard-only navigation reaches the surface selector, duplicate
      filters, and proposal-member verdict controls with visible focus.
- [ ] Successful replacement/reset reconciliation retains valid duplicate
      state, clears only invalid categorical filters, and a rejected upload
      leaves the current duplicate surface/search/filter state untouched.
- [ ] Desktop light/dark and approximately 390×844 layouts remain readable;
      the complete member matrix stays inside a contained horizontal scroller.
- [ ] Hostile names, locations, archetypes, Spirit/mod/holofoil values remain
      literal inert text with no injected elements.

Issue #110 focused check:

- [ ] Armor duplicates remains available when the report has same-stat groups
      but no exact groups, and the group heading explicitly says
      `Same stats, different tuning` and `review-only`.
- [ ] The segmented All / Exact / Same stats control appears only for mixed
      authoritative group kinds, selects complete groups, and retains valid
      search/facet state while clearing only unavailable categorical values.
- [ ] Every same-stat member has an always-visible text-labelled Tuning Mod
      Slot, including `none/unknown`; Seasonal Mod and Holofoil rows appear
      when those supplied values vary.
- [ ] Same-stat members do not receive survivor, retained, or junk labels.
      Verdict controls appear only for a same-section, same-hash authoritative
      proposal and use the existing single-item acknowledgement path.
- [ ] An item present in both exact and same-stat groups has both DOM
      occurrences registered; one acknowledgement repaints/disables all
      applicable occurrences while read-only occurrences remain read-only.
- [ ] Desktop (approximately 1440×1000) and narrow (approximately 390×844)
      light/dark layouts keep the heading, tuning labels, focus treatment, and
      contained matrix overflow readable; finalised rendering remains frozen.
- [ ] Hostile same-stat strings remain inert text, and opaque ids/hashes are
      preserved as strings.

Issue #131 focused check:

- [ ] Surface tabs and the group-kind segment show unfiltered counts in both
      visible text and `aria-label` (singular/plural correct); the counts are
      not announced by any live region.
- [ ] Exact duplicates and Same stats, different tuning render under their
      own text-labelled section heading, exact first, only for kinds present
      in the current filtered result.
- [ ] The group header line shows name, a text-labelled archetype badge,
      type/slot, guardian class, tier, hash, and a prominent piece count; the
      30/25/20 stat spike shows values and roles as text with the named
      zero-stat summary line.
- [ ] The Tuning Mod Slot banner is always visible and text-labelled in both
      group kinds (identical-copy phrasing for exact, review-only warning
      phrasing for same-stat), never relying on color alone.
- [ ] At a fitting desktop panel width, the member-column matrix orientation
      is active and the row fallback is absent from the accessibility tree
      and the keyboard tab order (a hidden control does not accept focus).
- [ ] At 390×844 and at a deliberately constrained/zoomed panel width, the
      row fallback is active instead, and the orientation flips back when the
      panel widens again.
- [ ] Only axes that actually differ across a group's members appear as
      matrix rows; every axis suppressed because it is identical is restated
      once, correctly labelled, in the muted identical-axes line beneath the
      matrix.
- [ ] Every verdict cell for a given member id is registered in both
      orientations: one Approve/Veto/Unset acknowledgement repaints and
      disables all occurrences, and read-only occurrences stay read-only in
      both.
- [ ] No `▸ decided` marker, no deciding-rank inference, and no Health
      low-value-for-PvE colouring or legend appear anywhere on the surface.
- [ ] Desktop light/dark and 390×844 layouts remain readable with no document
      horizontal overflow at any tested width; hostile names, ids, locations,
      archetypes, and mod/tuning values remain literal inert text in both
      matrix orientations.

Required multi-tab check:

1. Bootstrap and load a fake report in tab A.
2. Open the authenticated root page in tab B.
3. Mutate a verdict in tab A and wait for its acknowledgement.
4. Attempt a mutation from the now-stale tab B.
5. Verify tab B says the attempted action was not applied.
6. Verify tab B reconciles to the authoritative server verdict and revisions.
7. Verify the stale action was not automatically replayed.

Record the pass/fail result, any defects found, corrections made, and remaining
limitations. End every run with **Shutdown** or stop the server from its
terminal.

## 2026-08-31 — issue #104 focused check

- Environment: Linux 7.0.0-30-generic x86_64, Chrome for Testing
  151.0.7922.34 (Playwright Chromium revision 1234), headless.
- Viewports: 1440×1000 desktop and 390×844 narrow; both light and dark
  appearances were captured.
- Fixture: `tests/fixtures/armor_close.csv`; no real vault data and no wishlist
  or manifest network access.
- Visual result: pass. Ordinary Proposals showed the labelled pair before
  expansion or hover, including `Candidate: Melee · Selected: Grenade` and
  `Candidate: none/unknown · Selected: none/unknown`. The text remained
  distinct from armor scoring details and readable in desktop light/dark and
  narrow layouts; the table's horizontal overflow stayed contained.
- Workflow result: upload, flat view, finalised/read-only rendering, frozen
  controls, and shutdown passed. Acknowledgement state remained correct and
  the row stayed in place. The existing mutation gate disables all verdict
  buttons while an acknowledgement is in flight, so a button that was itself
  focused is blurred by the browser; this is pre-existing server UI behavior
  and was not changed by #104. Keyboard `a`/`v`/`u` review from the row control
  remained usable and repainted the row in place.
- The Armor duplicates group view was not tested or claimed; it remains #102.

## 2026-09-01 — issue #110 focused check

- Environment: Linux 7.0.0-30-generic x86_64, Chrome for Testing
  151.0.7922.34 (Playwright Chromium revision 1234), headless.
- Fixtures: `tests/fixtures/armor_same_stat_ui.csv` for the focused browser
  test, plus a temporary five-row combined fake fixture made only from the
  committed `armor_duplicates_ui.csv` and `armor_same_stat_ui.csv` fake rows
  for the mixed-kind visual pass. No real vault data, wishlists, or manifest
  network access was used. The focused packaged-server browser test completed
  in 1.34s (`1 passed`); the final full Chromium marker gate completed in
  5.07s (`5 passed`, `923 deselected`).
- Result: pass. Armor duplicates stayed enabled with no exact groups and
  rendered one complete `Same stats, different tuning · review-only` group.
  Both fake member ids and their differing Weapons/Health Tuning Mod Slot
  values were visible as ordinary text before any expansion or hover. The
  same-stat group exposed only controls for existing authoritative current
  proposals and did not imply a survivor or junk disposition.
- Actual visual matrix: the packaged server was exercised headlessly at
  1440×1000 and 390×844 in both light and dark appearances (four cases, about
  6.2s total), with review and finalised screenshots retained and inspected.
  The mixed fixture showed the All / Exact / Same stats selector; `All` was
  focused and its focus ring was visible. Headings, tuning labels, finalised
  read-only text, and disabled controls were legible in all four cases, and
  narrow member matrices remained inside their contained horizontal scrollers.
- Node/adapter coverage passed for mixed group ordering, All/Exact/Same stats
  state and reconciliation, whole-group any-member tuning filters/counts,
  strict malformed same-stat rejection, hostile text, prototype-shaped ids,
  and the one-id-to-many duplicate DOM registry. The existing mutation gate
  can still blur a verdict button focused while acknowledgement is in flight;
  this pre-existing behavior was not changed by #110.
- Remaining limitation: as recorded for #102, the pre-existing mutation gate
  can blur a verdict button focused while acknowledgement is in flight. No
  server lifecycle or mutation semantics were changed by #110.

## 2026-09-01 — issue #102 focused check

- Environment: Linux 7.0.0-30-generic x86_64, Chrome for Testing
  151.0.7922.34 (Playwright Chromium revision 1234), headless.
- Viewports and appearances: 1440×1000 desktop and 390×844 narrow, with both
  light and dark media appearances exercised at each viewport. The contained
  member matrix stayed within the page width in the narrow run. All checks used
  the same packaged server and fake fixture.
- Fixture: `tests/fixtures/armor_duplicates_ui.csv`; no real vault data,
  wishlists, or manifest network access.
- Result: pass. The authenticated server rendered the complete authoritative
  exact group with its preferred survivor, retained protected member, and
  proposed member. The archetype-led Primary/Secondary/Tertiary summary,
  collapsed zero-stat line, always-visible Tuning Mod Slot, and explicit
  Equipped row (No/Yes/No for the fake members) were readable.
  Survivor and retained cells were text-only; only the proposed member exposed
  verdict controls. Approve followed by a real Unset acknowledgement cleared
  the proposed member verdict; an acknowledged proposal verdict was also
  visible after switching to Proposals and back to the same duplicate
  presentation.
- Focus/state result: pass. Surface and duplicate filter controls were
  keyboard-focusable with visible focus, and the duplicate group remained
  complete while searching by member id. The existing acknowledgement gate
  kept controls frozen while a request was in flight and after finalisation.
- Lifecycle/reconciliation result: pass. A deliberately malformed replacement
  was rejected without changing the active duplicate surface or search; a
  successful replacement retained those valid values. Replacing it with an
  empty fake armor export disabled the duplicate option and returned to
  Proposals, while uploading the group again restored the option. Finalise
  left the duplicate matrix readable/frozen and Reset returned to upload-ready
  idle state.
- Hostile-text result: pass. The Node duplicate-DOM regression uses hostile
  group name, archetype, tuning-mod slot, Holofoil, Spirit signature, and
  member-location strings such as `</script><img ...>` and
  `</b><script>alert(1)</script>`; all remain text and no IMG, SCRIPT, or B
  nodes are created. The existing Proposals, upload, reset, replacement, and
  rejected-upload reconciliation paths remained unchanged; adapter coverage
  additionally boots the packaged adapter DOM to verify rejected-upload
  duplicate state retention, actual selector/list surface switching,
  same-report in-place verdict repaint, shared cross-view verdict state,
  mutation/finalized disabling, and only-invalid categorical filter clearing.
  Its incompatible-response regressions reject both a weapon-section
  same-ID/action lookalike, an armor-section wrong-hash decision, and a
  cross-group duplicate member id without adopting the malformed envelope.
- Browser timing: the four-test Chromium marker run completed in 5.08s; the
  focused #102 test completed in 1.59s, with a 0.44s call phase, 0.35s setup,
  and 0.56s teardown.
- Remaining limitation: as recorded by #104, the pre-existing mutation gate
  can blur a verdict button that is focused while its acknowledgement is in
  flight; #102 did not alter server lifecycle or mutation semantics.

## 2026-09-03 — issue #118 focused check

- Environment: Linux 7.0.0-30-generic x86_64, Chrome for Testing
  151.0.7922.34 (Playwright Chromium revision 1234), headless.
- Viewports and appearances: 1440×1000 desktop and 390×844 narrow, both
  light and dark media appearances at each viewport.
- Fixtures: `tests/fixtures/armor_duplicates_ui.csv` (exact group, for the
  `Protection` label, `Exact duplicate group` sub-line, and facet-noun
  copy), `tests/fixtures/armor_same_stat_ui.csv` (same-stat group, for the
  overflow/wrapping fix — the same fixture the plan's own before/after
  measurement used), and `tests/fixtures/weapons_hostile.csv` (Proposals
  surface, to confirm the CSS change reaching `.mono` there causes no
  regression). No real vault data, wishlists, or manifest network access.
- Copy result: pass. The exact group rendered `Exact duplicate group` with
  no `exact_duplicate` (or any other underscore token) in the article text,
  and a `Protection` row with no `Hard protection` row, at both viewports
  and both appearances. `Hunter (1 group)` and `Chest Armor (1 group)`
  facet options confirmed the noun/pluralisation. The finalised group still
  rendered the same `Protection` label and same-stat sub-line, and both its
  verdict buttons were disabled (frozen), after finalising via
  `#vc-finalize`.
- Overflow result: pass. `document.documentElement.scrollWidth` matched the
  viewport width exactly (390 and 1440) at both viewports in both light and
  dark appearances on the same-stat fixture — no horizontal document
  overflow. `article.armor-group .scroller`'s computed `overflow-x`
  remained `auto` (the contained comparison-table scroll was not removed to
  fix the document-level overflow), and `#vc-fingerprint` still rendered
  its digest.
- Focus/keyboard result: pass. The skip link (`Skip to review content`) was
  the first tab stop from a fresh, unclicked load; the `:focus-visible`
  ring rendered (`outline-style: solid`) during subsequent interaction.
- Proposals-surface result: pass. This is the one place the `code, .mono,
  kbd` change reaches beyond the duplicates surface (it also styles the
  Proposals table's instance-id cells). Facet options remained noun-free —
  `weapons (5)`, `Hunter (2)` — with no visible regression to table
  layout or instance-id columns at either viewport.
- Shutdown result: pass. The server thread stopped cleanly after the
  headless session ended.
- Overall result: pass. No part of #119 (the paired `Exact`/`Same stats ·
  review only` kind labels, the `armorGroupTable` transposition, or any
  count/hierarchy treatment) was implemented or tested.

## 2026-09-04 — issue #131 focused check

- Environment: Linux 7.0.0-30-generic x86_64, Chrome for Testing
  151.0.7922.34 (managed Playwright Chromium), headless.
- Method: the automated `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q
  -m browser tests/test_server_browser.py` run (10 passed in 7.30s) plus a
  direct run of `scripts/measure_armor_matrix_orientation.py`, which itself
  asserts its own preconditions (exactly one orientation visible, no document
  horizontal overflow) before writing
  `docs/evidence/issue-131/orientation-measurements.md` — a real dated run,
  not a restatement of the checklist above.
- Viewports and appearances: 1440×1000 and 1024×900 desktop, 390×844 narrow,
  plus 680×900/760×900 (a deliberately constrained "zoom/reflow" pair
  straddling the two-member 616px column budget) and light/dark media
  appearances on the four-member fixture.
- Fixtures: `tests/fixtures/armor_duplicates_ui.csv` (exact, 3 pieces),
  `tests/fixtures/armor_same_stat_ui.csv` (same-stat, 2 pieces),
  `tests/fixtures/armor_same_stat_four_ui.csv` (same-stat, 4 pieces), and
  `tests/fixtures/weapons_hostile.csv` (hostile-string inertness). No real
  vault data, wishlists, or manifest network access.
- Orientation result: pass. Exactly one of `table.armor-matrix-columns` /
  `table.armor-matrix-rows` is visible at every measured width; member
  columns are active for 2, 3, and 4 members at 1440×1000 and for 2–3 members
  at 1024×900, and the row fallback is active for the 4-member group at
  1024×900 and for every member count at 390×844 — matching the plan's
  measured budget exactly (see the evidence file). The 680/760px pair proved
  the flip is genuinely width-driven and reversible, not a fixed
  desktop/mobile breakpoint.
- Keyboard result: pass. A button inside the `display: none` orientation
  never accepted `.focus()` (`document.activeElement` stayed elsewhere); the
  same button in the active orientation focused normally.
- Difference-only result: pass. A group with a uniform Masterwork
  Tier/Power/In loadout/Equipped alongside a differing Protection and Locked
  rendered only the differing axes as rows in both orientations, and restated
  every suppressed axis, correctly labelled, in
  `p.armor-identical-axes` beneath the matrix.
- Copy/labelling result: pass. Tabs and the group-kind segment showed correct
  singular/plural counts in both visible text and `aria-label`; section
  headings ("Exact duplicates" / "Same stats, different tuning") appeared
  only for kinds present; the stat spike showed lowercase `primary` /
  `secondary` / `tertiary` role text with the named zero-stat line; the
  same-stat banner used `.tuneline.warn`, not the generic `.hint` class.
- Overflow/theme result: pass (existing four-member test, extended rather
  than replaced): `document.documentElement.scrollWidth` matched the
  viewport width at 1440, 1000, and 390 in both appearances; badge widths
  stayed within their *active* heading's fixed budget in both light and dark
  (scoped to `:visible`, since a hidden heading has no usable geometry).
- Hostile-string result: pass. No part of this ticket introduced `innerHTML`
  or template-string DOM construction; existing hostile-export coverage
  (`test_hostile_export_remains_inert_in_live_dom`) and the archetype-badge/
  header/banner/stat-spike text paths all go through the same `el()`
  `textContent` helper as before.
- Shutdown result: pass (implicit in the automated suite's server teardown).
- Overall result: pass. `RULESET_VERSION`, snapshot/server schema, grouping,
  ranking, and verdict validation were not touched; this run covered
  presentation and interaction only.

## 2026-08-27 — issue #90 execution record

- Environment: Linux 7.0.0-30-generic x86_64, Chrome for Testing
  151.0.7922.34 (Playwright Chromium revision 1234), headless.
- Viewports: 1440×1000 desktop and 390×844 narrow.
- Fixture: `tests/fixtures/armor.csv`; no real vault data and no wishlist or
  Bungie manifest network access.
- Visual result: pass. Desktop light and dark captures had readable hierarchy,
  controls, statuses, tables, badges, and focus treatment. At 390 px, controls
  and summary tiles stacked cleanly and proposal tables stayed contained with
  horizontal access to later columns.
- Keyboard result: pass. Row <kbd>a</kbd>, <kbd>v</kbd>, and <kbd>u</kbd>
  were server-acknowledged and focus stayed in the same row across each repaint.
- Controls result: pass. Upload statuses, report counts, search, kind filtering,
  grouped/flat switching, column sorting, expanded details, finalisation,
  finalised/frozen controls, Download again, Reset, and Shutdown were exercised.
  The first download and Download again returned identical bytes.
- Multi-tab result: pass. Tab A recorded an acknowledged approval; stale tab B's
  veto received a visible “was not applied” message, reconciled to the approved
  server state, and did not replay the veto.
- Defects found and corrected: no product defects. The first exploratory pass
  attempted to select a `junk` action absent from this all-review fixture; the
  checklist driver was corrected to use the available `armor` kind filter and
  the complete pass was rerun successfully.
- Overall result: pass.
