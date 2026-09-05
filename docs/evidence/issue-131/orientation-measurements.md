# Issue #131 orientation-switch measurements

Measured by uploading the committed fake fixtures into the real
packaged server (`scripts/measure_armor_matrix_orientation.py`) and
reading live geometry in managed Chromium. Every precondition below
(exactly one orientation visible, no document horizontal overflow,
a real flip bracketed on both sides) is asserted by the script
before this file is written; a failing precondition makes the
script exit non-zero instead of reporting a number. `1rem = 16px`.

### armor_duplicates_ui.csv (exact, 3 pieces)

| Viewport | `.armor-group` width | comparison content box | active orientation | rows table `tbody tr` | columns table `tbody tr` | doc scrollWidth |
|---|---|---|---|---|---|---|
| 1440x1000 | 1182.0px | 1156.0px | columns | 3 | 5 | 1440px |
| 1024x900 | 958.0px | 932.0px | columns | 3 | 5 | 1024px |
| 390x844 | 336.8px | 315.6px | rows | 3 | 5 | 390px |

### armor_same_stat_ui.csv (same-stat, 2 pieces)

| Viewport | `.armor-group` width | comparison content box | active orientation | rows table `tbody tr` | columns table `tbody tr` | doc scrollWidth |
|---|---|---|---|---|---|---|
| 1440x1000 | 1182.0px | 1156.0px | columns | 2 | 4 | 1440px |
| 1024x900 | 958.0px | 932.0px | columns | 2 | 4 | 1024px |
| 390x844 | 336.8px | 315.6px | rows | 2 | 4 | 390px |

### armor_same_stat_four_ui.csv (same-stat, 4 pieces)

| Viewport | `.armor-group` width | comparison content box | active orientation | rows table `tbody tr` | columns table `tbody tr` | doc scrollWidth |
|---|---|---|---|---|---|---|
| 1440x1000 | 1182.0px | 1156.0px | columns | 4 | 7 | 1440px |
| 1024x900 | 958.0px | 932.0px | rows | 4 | 7 | 1024px |
| 390x844 | 336.8px | 315.6px | rows | 4 | 7 | 390px |

## Flip points (binary-searched, per member count)

| Members | flip viewport width | just below the flip | comparison content box at the flip | shipped CSS threshold | matches |
|---|---|---|---|---|---|
| 2 | 708px | 707px | 616.0px | 38.5rem (616px) | yes |
| 3 | 908px | 907px | 816.0px | 51.0rem (816px) | yes |
| 4 | 1108px | 1107px | 1016.0px | 63.5rem (1016px) | yes |

Each flip point above was found by bisecting the real browser viewport width until the member-column orientation first became active, then confirming the row fallback is active one pixel below that width and the member-column orientation is active at it -- not asserted from the stylesheet.

## Conditional same-stat axis row-count delta

Measured at 1440x1000 with the member-column orientation active (so `tbody th.armor-matrix-axis-label` enumerates exactly the rendered axis rows, one per differing or always-shown axis plus Verdict). Member count does not change this count by itself -- the delta below comes entirely from which conditional axes actually differ in each committed fixture's real data.

- `armor_same_stat_ui.csv` (2 pieces): 4 rows -- Tuning Mod Slot, Masterwork Tier, Power, Verdict
- `armor_same_stat_four_ui.csv` (4 pieces): 7 rows -- Tuning Mod Slot, Protection, In loadout, Locked, Masterwork Tier, Power, Verdict
- delta: +3 rows

## N=5 / N=6 thresholds are unreachable in practice

Measured at 2560x1200 -- far wider than any supported member count could need -- the comparison content box plateaus at 1156.0px (`.armor-group` width 1182.0px), capped by `.wrap { max-width: 78rem }` (1248px) minus its own 1rem padding on each side and `.armor-group`'s border and .75rem padding on each side. That plateau is below the N=5 threshold (76.0rem = 1216px) and well below the N=6 threshold (88.5rem = 1416px), so neither `@container` rule can ever match in this surface's real layout. They are deliberate defensive rules for a member count the producer cannot emit today, not measured thresholds -- shipped for consistency with N=2..4 and to fail safe (row fallback) rather than assume, should that ever change.
