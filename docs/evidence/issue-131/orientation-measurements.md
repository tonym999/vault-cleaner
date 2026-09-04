# Issue #131 orientation-switch measurements

Measured by uploading the committed fake fixtures into the real
packaged server (`scripts/measure_armor_matrix_orientation.py`) and
reading live geometry in managed Chromium. Every precondition below
(exactly one orientation visible, no document horizontal overflow) is
asserted by the script before this file is written; a failing
precondition makes the script exit non-zero instead of reporting a
number. `1rem = 16px`.

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
