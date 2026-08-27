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
