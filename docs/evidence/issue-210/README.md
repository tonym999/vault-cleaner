# Issue #210 evidence: prior-art survey and mockup directions

Recorded while planning [#210](https://github.com/tonym999/vault-cleaner/issues/210)
on 2026-10-10. It holds the prior-art survey the issue asks for and the four
mockup directions the owner chose from. The chosen design, direction D, is the
visual target of [handoffs/issue-210-implementation-plan.md](../../../handoffs/issue-210-implementation-plan.md).

Nothing here ships. The mockups are static pages generated from the tracked
sanitised fixture `tests/fixtures/real/2026-09-01T-current/armor.csv`; no file
under `data/` was read.

## 1. Prior-art survey

### What was looked at, and how

| Tool | How it was examined | Coverage |
| --- | --- | --- |
| Destiny Item Manager (DIM) | Its changelog, wiki and Compare source, then the live app in the owner's signed-in Chrome on 2026-10-10 (inventory, item popup, Compare, Organizer) | Desktop width only |
| D2ArmorPicker | README, then the sign-in page's preview image | Not signed in; the app itself was not seen |
| light.gg | One item page in the owner's signed-in Chrome | Item definition page only; its Armor Playground needs a data download that was not started |
| Braytech | Landing page | Not signed in; no piece comparison was found |
| Ishtar Commander | Not examined | A phone app; no source was reachable |
| The game's inspect and vault screens | Not examined | No source was reachable |

Limits, stated plainly:

- **No tool was seen at phone width.** The Chrome window ignored both resize
  requests and stayed at 1568 by 744 px.
- **The live DIM session showed the owner's real vault.** Only layout
  observations are recorded here. No screenshot of it was saved, and no id,
  note or loadout name appears in this file.
- Fetching light.gg returned HTTP 403, its documentation host did not resolve,
  and Bungie's article page returned an empty shell, so those were read only
  through the browser, or not at all.

Sources read:

- DIM changelog: <https://raw.githubusercontent.com/DestinyItemManager/DIM/master/docs/CHANGELOG.md>
  (entries 8.81.4 to 8.94.0 cover archetypes, tuned stats and tiered armor)
- DIM Compare wiki page: <https://github.com/DestinyItemManager/DIM/wiki/Compare>
- DIM Compare source: `src/app/compare/Compare.m.scss` and `CompareItem.tsx`
  on the `master` branch of <https://github.com/DestinyItemManager/DIM>
- D2ArmorPicker README: <https://github.com/Mijago/D2ArmorPicker> (AGPL-3.0;
  it does not describe the interface)

### Findings for this surface's job

The job: tell near-identical pieces apart inside a group, compare across
pieces, show which piece is kept and why, and stay readable across many groups
in dark mode and at 390 px.

**DIM item tile.** Tier is a column of pips down the left edge, the archetype
icon sits in a corner, power is printed at the bottom, lock and tag are small
icons. Good for scanning hundreds of pieces; it relies on icons, which the
server's CSP (no `img-src`) and the contract's "no icon carries meaning alone"
rule both limit here.

**DIM item popup.** The name sits on a rarity-coloured header. All six stats
are listed in a fixed order with a bar each; the archetype's stats are bold;
the tuned stat carries a small swap marker beside its value. The archetype is
a labelled block ("Primary Stat", "Secondary Stat").

**DIM Compare.** Items are columns and one label column names the rows. The
grid is `max-content` wide inside a horizontal scroller and the stylesheet has
no phone-specific layout. The item the comparison started from has its name in
orange. Stat values are coloured on a scale (blue best, red worst), zeros are
shown in a quiet colour, and the tuned stat again carries the swap marker
beside its value. Filter buttons above the grid include "same archetype" and
"same three non-zero stats"; the second is this project's same-stat group. In
that view the three values are identical across columns, and what differs is
the position of the tuned-stat marker and the archetype name.

**DIM Organizer.** One row per item, about 36 px tall: a small tile, name,
power, energy, lock, tag, archetype, a tuner icon, six stat columns under icon
headers, total, location, notes. Four pieces take about 145 px. Bulk actions
sit in a toolbar above, driven by row checkboxes.

**D2ArmorPicker (preview image only).** Pieces as rows, six stat columns, a
totals row beneath.

**light.gg item page.** Full-width section bars with a disclosure triangle and
a title separate the page's parts clearly. The page describes an item
definition, so it has nothing on comparing owned copies.

### Adopted and rejected

| Finding | Decision | Where it shows in direction D |
| --- | --- | --- |
| Compare: items as columns, one label column | Adopted | The comparison matrix |
| Compare: sideways scroller, no phone layout | Rejected. The issue rules out member-by-member sideways navigation at narrow widths | Pairs and triples stay as columns at 390 px; four pieces become one block per piece |
| All six stats in a fixed order, zeros kept and quiet | Adopted | The six-cell stat strip in each group header |
| Tuned stat marked on the stat, not as a separate field | Adopted | The "Tuned stat" row: a six-box strip in the same order, plus the stat name as text |
| Starting item marked by its name colour | Adopted in spirit, with more weight | The kept piece's column is tinted and carries the text "Preferred survivor" |
| Red-to-green colour scale on stat values | Rejected. Stats are identical inside every group here, and the contract bars colour as the only cue | Not used |
| Organizer density (one line per piece) | Partly adopted | The piece header puts id and location on one line. A full one-line row was direction A and was not chosen |
| Icons for archetype, stat and tier | Rejected for this ticket. The CSP has no `img-src`, and every icon would need a text label anyway | Text labels throughout |
| light.gg section bars | Adopted in spirit | A sticky section heading, so the kind of group stays on screen |

## 2. What the fixture shows

Measured from the envelope the unmodified server returns for the sanitised
fixture (`mockups/dump_envelope.py`):

- 74 groups: 9 exact, 65 same-stat. 158 pieces. 435 verdict buttons.
- Group sizes: 66 pairs, 6 triples, 2 groups of four. Every exact group is a
  pair.
- Every group is tier 5 with the 30/25/20 spike, so base stats never differ
  inside a group.
- Exact groups differ on 0 to 2 comparison fields (4 on none, 1 on one, 4 on
  two).
- Same-stat groups differ on 2 to 9 fields. Tuning Mod Slot and Tuning Stat
  differ in all 65.
- Tuning Stat equals Tuning Mod Slot, ignoring case, for all 140 same-stat
  pieces.

## 3. Mockup directions

Four static directions were built on all 74 groups and captured in dark at
1440 px and 390 px. They share one palette derived from the contract's dark
tokens, system fonts only (the CSP has no `font-src`), a sticky section
heading, no inline `style` attribute, and verdict buttons with no transition.

| | A: ledger | B: side by side | C: index and inspector | D: B revised |
| --- | --- | --- | --- | --- |
| Structure | Pieces as rows, differing fields as columns | Pieces as columns, fields as rows | List of groups, one open at a time | B with the fixed six-stat strip and the tuned-stat row |
| Page height at 1440 px | 25,036 | 35,562 | 6,455 | 28,360 |
| Page height at 390 px | 64,571 | 61,331 | 8,198 | 56,209 |
| Outcome | Dropped: comparison reads down, not across | Superseded by D | Dropped: only one group is in the DOM, so the #206 parity and tab-order proofs could not pass | **Chosen by the owner, 2026-10-10** |

For scale, the #206 slice measured about 61,000 px at desktop and 101,000 px
at 390 px (`worklog/2026-10-04-issue-206-real-scale.md`).

Captures in `mockups/`:

- Direction D: `d-desktop-top.png`, `d-desktop-boundary.png` (the section
  boundary), `d-desktop-four.png` (a group of four), `d-390-boundary.png`,
  `d-390-three.png`, `d-390-four.png`.
- Dropped directions, one each: `a-desktop-boundary.png`,
  `b-desktop-boundary.png`, `c-desktop-top.png`.

Known flaws in the D mockup, left for the implementation:

- At 390 px the word "Weapons" slightly overruns the last cell of the stat
  strip.
- At 390 px a triple is cramped: the verdict buttons stack and the proposal
  text wraps to five lines.
- Three verdicts are overlaid (one vetoed, two approved) so pressed states
  are visible. The real envelope has none.
- The light palette in `mock.css` was written but never captured or checked.
- The mockup's kind pill reads "Exact" and "Review only" and its scope line
  uses a comma. The #206 proofs assert different wording; the plan fixes the
  real copy.

### Regenerating the mockups

The #206 frontend must be built first (`npm ci && npm run build` in
`spikes/issue-206/frontend/`). From the repository root:

```bash
cd spikes/issue-206 && ../../.venv/bin/python ../../docs/evidence/issue-210/mockups/dump_envelope.py ../../docs/evidence/issue-210/mockups/envelope.json
```

```bash
.venv/bin/python docs/evidence/issue-210/mockups/build.py
```

```bash
.venv/bin/python docs/evidence/issue-210/mockups/shoot.py
```

The first writes the envelope, the second writes `a.html` to `d.html`, the
third writes captures to `mockups/shots/`. All three outputs are ignored by
`mockups/.gitignore`; only the nine captures listed above are tracked.
