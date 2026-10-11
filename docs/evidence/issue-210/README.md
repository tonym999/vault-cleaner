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

**Correction, 2026-10-11.** The row above says direction C was dropped
because the #206 proofs could not pass. That states a constraint of this
ticket, not a finding about C. C was incompatible with proofs that require
every value of every group to be visible at once; nothing here shows it is
worse to use. It is the only direction that shortens the page by an order of
magnitude, and it remains a candidate for later task testing (review of
`653adeb`, issue #210).

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

## 4. The built slice: captures

`captures/` holds the built #210 slice, written by
`spikes/issue-210/capture.py` from the running review server. They replace
the captures committed at `725bc99`, which predate Amendment 2's fixes and
refinements.

- Real fixture, dark and light, 1440 px and 390 px: `real-<width>-<scheme>-viewport.png`
  (the first screen), `-boundary.png` (the section boundary), `-three.png`
  (a triple) and `-four.png` (a group of four).
- Synthetic, dark: `both-kinds-<width>-dark.png` and
  `four-members-<width>-dark.png`.

The capture run, verbatim:

```bash
.venv/bin/python spikes/issue-210/capture.py docs/evidence/issue-210/captures real && .venv/bin/python spikes/issue-210/capture.py docs/evidence/issue-210/captures synthetic
```

```text
real-desktop-dark: page 1440 x 28312 px, 74 groups
real-desktop-dark: first group's top edge at 266 px
real-narrow-dark: page 390 x 55274 px, 74 groups
real-narrow-dark: first group's top edge at 587 px
real-desktop-light: page 1440 x 28312 px, 74 groups
real-narrow-light: page 390 x 55274 px, 74 groups
```

## 5. Proof transcripts

Each fence is the whole output of the command above it, unedited, from one
run on 2026-10-11 against the build recorded under *Build*. These are the
runs of fix round 2; they replace the transcripts recorded at `61d9410`. The
frontend needs `npm ci` in `spikes/issue-210/frontend/` first. Commands run
from the repository root unless they say otherwise.

### Type check

```bash
cd spikes/issue-210/frontend && npm run check
```

```text
npm notice run vault-cleaner-spike-206-frontend@0.0.0 check
npm notice run svelte-check --tsconfig ./tsconfig.json --fail-on-warnings
1791700909612 START "/home/raver/projects/personal/vault-cleaner/spikes/issue-210/frontend"
1791700909614 COMPLETED 303 FILES 0 ERRORS 0 WARNINGS 0 FILES_WITH_PROBLEMS
```

### Unit tests

```bash
cd spikes/issue-210/frontend && npm test
```

```text
npm notice run vault-cleaner-spike-206-frontend@0.0.0 test
npm notice run vitest run

 RUN  v5.0.3 /home/raver/projects/personal/vault-cleaner/spikes/issue-210/frontend


 Test Files  3 passed (3)
      Tests  43 passed (43)
   Start at  06:41:50
   Duration  827ms (transform 87%, import 8%, tests 4%, worker 1%)
```

### Build

```bash
cd spikes/issue-210/frontend && npm run build
```

```text
npm notice run vault-cleaner-spike-206-frontend@0.0.0 build
npm notice run vite build
vite v8.3.2 building client environment for production...
transforming...
✓ 129 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html        0.44 kB │ gzip:  0.28 kB
dist/modules.json      4.41 kB │ gzip:  0.71 kB
dist/assets/app.css   31.72 kB │ gzip:  6.83 kB
dist/assets/app.js   144.38 kB │ gzip: 42.81 kB

✓ built in 530ms
```

### S1 parity (#206 proof, unedited, tuned-stat merge applied)

```bash
.venv/bin/python spikes/issue-210/run_proof.py S1
```

```text
-- every required value, for four fixtures, without and with verdicts --
armor_close.csv unreviewed at 1440px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv unreviewed at 390px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 1440px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 390px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv unreviewed at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv unreviewed at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv unreviewed at 1440px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv unreviewed at 390px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 1440px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 390px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv unreviewed at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv unreviewed at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
-- group values no fixture has, overlaid in memory on the server's answer --
exact:6031 shows: {'spirit_signature': 'Spirit of the Fixture · Spirit of the Proof', 'seasonal_mod': 'Fake Seasonal Mod', 'holofoil': 'true'}
same_stat:6081 shows: {'spirit_signature': 'Spirit of the Twin'}
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 1440px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 390px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
-- filters: the slice beside the production page, same session --
no filter: equal to production=True; groups=['exact_duplicate:6031', 'same_stat:6081']
  scope: 2 groups · 4 pieces
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected=''
kind=exact: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected=''
kind=same_stat: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected=''
class=Titan: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to class Titan
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected='Titan'
kind=exact, then class=Titan: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates, class Titan
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected='Titan'
class=Hunter: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to class Hunter
  Class options: ['=any class', 'Hunter=Hunter (1 group)', 'Titan=Titan (1 group)']; selected='Hunter'
kind=same_stat, then class=Hunter: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups, class Hunter
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected='Hunter'
class=Titan, then kind=same_stat: equal to production=True; groups=['same_stat:6081']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups
  Class options: ['=any class', 'Hunter=Hunter (1 group)']; selected=''
class=Hunter, then kind=exact: equal to production=True; groups=['exact_duplicate:6031']
  scope: 1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates
  Class options: ['=any class', 'Titan=Titan (1 group)']; selected=''
after the dropped class, the slice says: 'Filter no longer applies and was cleared: class Hunter.'
after the dropped class, production says: 'Local view state dropped: duplicate filter guardianClass Hunter.'
-- negative control: remove one required value from the rendered page --
differences before removal: 0; after removal: ['exact:6031 member 6032 masterwork_tier: not shown']
after a verdict text was changed in the page: ["same_stat:6081 member 6081 verdict: shows ('Approved', False), server says ('Unreviewed', False)"]
RESULT: PASS
```

### S2 hostile values (#206 proof, unedited)

```bash
.venv/bin/python spikes/issue-210/run_proof.py S2
```

```text
-- 1440px: every string in the envelope replaced --
string values replaced: 602; distinct ids: 32; distinct hashes: 15
differences from the hostile envelope, value by value: 0
ids in the DOM (attribute and text, untrimmed) byte-identical: True: ['18446744073709551615', '007', '9"<\'> x']
hashes in the DOM identical: True: ['005<script>alert(4)</script>', '0014<script>alert(4)</script>']
names shown as exact text, internal double spaces kept: True; length 404
elements created from values (img, script, i, b, u): 0; script elements in the document: 1 (the bundle)
page scrolls sideways with 300-character unbroken values: False
verdict buttons with every disposition and action hostile: 0 (no member's disposition and action agree, so none is a proposal member)
second pass, disposition and action values kept: strings replaced 574; verdict buttons 9; differences from the envelope 0
verdict request body: {"report_revision":1,"verdict_revision":0,"fingerprint":"b212ae6e8f2fc0a7ee7977227f78d32f431149e14af3d81c60698ffec47b9397","decisions":[{"id":"007","verdict":"vetoed"}]}
id in the request equals the envelope's id: True; is a JSON string: True
status after the acknowledgement names the id as text: True
dialogs: []; CSP violations: []; console errors: []; page errors: []
-- 390px: every string in the envelope replaced --
string values replaced: 602; distinct ids: 32; distinct hashes: 15
differences from the hostile envelope, value by value: 0
ids in the DOM (attribute and text, untrimmed) byte-identical: True: ['18446744073709551615', '007', '9"<\'> x']
hashes in the DOM identical: True: ['005<script>alert(4)</script>', '0014<script>alert(4)</script>']
names shown as exact text, internal double spaces kept: True; length 404
elements created from values (img, script, i, b, u): 0; script elements in the document: 1 (the bundle)
page scrolls sideways with 300-character unbroken values: False
verdict buttons with every disposition and action hostile: 0 (no member's disposition and action agree, so none is a proposal member)
second pass, disposition and action values kept: strings replaced 574; verdict buttons 9; differences from the envelope 0
verdict request body: {"report_revision":1,"verdict_revision":0,"fingerprint":"b212ae6e8f2fc0a7ee7977227f78d32f431149e14af3d81c60698ffec47b9397","decisions":[{"id":"9\"<'> x","verdict":"vetoed"}]}
id in the request equals the envelope's id: True; is a JSON string: True
status after the acknowledgement names the id as text: True
dialogs: []; CSP violations: []; console errors: []; page errors: []
RESULT: PASS
```

### S3 acknowledged verdicts (#206 proof, unedited)

```bash
.venv/bin/python spikes/issue-210/run_proof.py S3
```

```text
-- the response is held after the server has committed --
before: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [False, False, False]}
server while held: verdict_revision=1, verdicts=[{'id': '6032', 'verdict': 'approved'}]
page while held:   {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [True, True, True]}
status unchanged while held: True
after release:     {'verdict': 'Approved', 'persisted_veto': False, 'pressed': ['Approve'], 'disabled': [False, False, False]}; status='The server recorded your approval for item 6032.'
after Veto: {'verdict': 'Vetoed', 'persisted_veto': False, 'pressed': ['Veto'], 'disabled': [False, False, False]}; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
after Unset: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [False, False, False]}; server verdicts=[]
-- stale_verdicts: another client changes a verdict --
status: 'Your veto was not applied because the review changed. Repeat it if you still want it.'
the page's own action is not shown: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [False, False, False]}
the other client's verdict is shown:  {'verdict': 'Approved', 'persisted_veto': False, 'pressed': ['Approve'], 'disabled': [False, False, False]}
verdict POSTs sent by the page: ['verdicts']; server verdict_revision before=4 after=4; verdicts=[{'id': '6081', 'verdict': 'approved'}]
-- stale_report: a new export is uploaded elsewhere --
status: 'Your approval was not applied because the review changed. Repeat it if you still want it.'
groups now shown: ['exact:8201']; scope: 1 group · 3 pieces
verdict POSTs sent by the page: ['verdicts']; server verdict_revision before=5 after=5; verdicts=[]
differences from the server's new report: 0
RESULT: PASS
```

### S4 lifecycle (#206 proof, unedited)

```bash
.venv/bin/python spikes/issue-210/run_proof.py S4
```

```text
-- finalise from the open page, with a veto in place --
before: state=reviewing, revisions=(1, 1), override_status=[]
page before: {'verdict': 'Vetoed', 'persisted_veto': False, 'pressed': ['Veto'], 'disabled': [False, False, False]}
after:  state=finalized, revisions=(1, 1), active persisted vetoes=['6032']
revision pair and fingerprint unchanged by the finalise: True
requests the page made: ['POST api/finalize', 'GET api/report']; page navigations or reloads: 0
open page now: {'session': 'Finalised. The reviewed CSV has been produced and this review is frozen.', '6032': {'verdict': 'Vetoed', 'persisted_veto': True, 'pressed': ['Veto'], 'disabled': [True, True, True]}, 'all verdict controls disabled': True, 'download link': 1}
differences between the open page and the finalised envelope: 0
production, loaded fresh: {'verdict': 'Vetoed this session · active persisted veto still suppresses this item', 'disabled': [True, True, True], 'note': 'Finalisation succeeded. The reviewed CSV was produced; this session is now frozen.'}
same meaning as production (vetoed, a persisted veto still suppresses it, controls off, frozen): True
-- reset, then a new upload --
after reset: server state=idle, report_revision=2; page groups=0, empty state=['no-report'], session note='No report is loaded. Upload a DIM armor export on the main review page, then reload here.'
after a new upload and Reload: state=exports-loaded, {'verdict': 'Unreviewed', 'persisted_veto': True, 'pressed': ['Unset'], 'disabled': [False, False, False]}
the veto saved by the finalise is still reported and shown: True; differences from the envelope: 0
-- finalise from outside the already-open page --
finalise posted outside the page: HTTP 200; revisions unchanged=True
open page, before it makes any request: {'verdict': 'Vetoed', 'persisted_veto': False, 'pressed': ['Veto'], 'disabled': [False, False, False]}
status: 'Your approval was not applied: this review is finalised.'
POSTs sent by the page: ['verdicts']; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
open page now: {'session': 'Finalised. The reviewed CSV has been produced and this review is frozen.', '6032': {'verdict': 'Vetoed', 'persisted_veto': True, 'pressed': ['Veto'], 'disabled': [True, True, True]}, 'all verdict controls disabled': True, 'download link': 1}
a fresh load shows the same: True
-- the server stops --
filter with the server stopped: groups=['same_stat:6081']; scope='1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups'
a verdict with the server stopped: status='Your approval was not applied. The review server did not answer. Filters still work; use Reload to reconnect.'
nothing shown as applied, controls off: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [True, True, True]}; connection=disconnected
filter again while disconnected: groups=['exact:6031']; scope='1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates'
RESULT: PASS
```

### S5 focus (#206 proof, unedited)

```bash
.venv/bin/python spikes/issue-210/run_proof.py S5
```

```text
-- static semantics (contract section 7) --
{'skipLink': 'Skip to review content', 'h1Focusable': True, 'regions': ['vc-status: role=status, aria-live=polite', 'vc-reconciliation: role=status, aria-live=polite', 'vc-scope: role=status, aria-live=polite'], 'toggles': 12, 'tabRoles': 0, 'unnamed': 0, 'labelledSelects': True}
first Tab stop: 'Skip to review content'; activating it moves focus to: #vc-title
-- why the slice uses aria-disabled: what native `disabled` does to focus here --
a focused button set to disabled: focus is then on <BODY>
-- a verdict by keyboard --
while the request is in flight: {'focus': 'Approve item 6032', 'ariaDisabled': 'true'}
Unset (Enter): focused control is the same node=True (Unset item 6032); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 0}; controls rebuilt=0; tab stops=18; natively disabled buttons=0
Veto (Space): focused control is the same node=True (Veto item 6032); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 0}; controls rebuilt=0; tab stops=18; natively disabled buttons=0
-- a filter change --
kind filter: focused control is the same node=True; writes={'vc-status': 0, 'vc-reconciliation': 0, 'vc-scope': 1}; live regions are the same nodes=True
-- report change, the focused member is still in the new report --
stale_report, member 6032 still present: focused control is the same node=True (Approve item 6032); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 0}; controls rebuilt=0; tab stops=18; natively disabled buttons=0
-- report change, the focused member is gone --
stale_report, member 6032 gone: focused control is the same node=False (vc-list-title); live regions are the same nodes=True; writes to them={'vc-status': 1, 'vc-reconciliation': 0, 'vc-scope': 1}; controls rebuilt=3; tab stops=9; natively disabled buttons=0
RESULT: PASS
```

### S6 layout (#206 proof; the member-column measure replaced by a constant)

```bash
.venv/bin/python spikes/issue-210/run_proof.py S6
```

```text
-- armor_close.csv --
1440px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1440px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
tab order at 390px: ['Skip to review content', 'Reload report', 'Finalise review', 'Reset session', 'All (2)', 'Exact (1)', 'Same stats (1)', 'any classTitan (2 groups)', 'Reset filters', 'Approve item 6032', 'Veto item 6032', 'Unset item 6032', 'Approve item 6081', 'Veto item 6081', 'Unset item 6081', 'Approve item 6082', 'Veto item 6082', 'Unset item 6082']
-- armor_same_stat_four_ui.csv --
1440px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1440px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
RESULT: PASS
```

### Source scan (#206 `check_source.py`, unedited)

```bash
.venv/bin/python spikes/issue-210/run_proof.py source
```

```text
shipped source files scanned: 19; test and contract files: 4
raw HTML: 0
code from strings: 0
numeric conversion: 0
hand-written inline style: 0
remote URL: 0
id and hash fields declared in envelope.ts: 9, all string: True
-- direct DOM access and effects in shipped source --
App.svelte:28 $effect: focus policy on a report change (the slice's only effects: one before, one after the DOM change)
App.svelte:30 document.activeElement: focus policy: has focus fallen to <body>?
App.svelte:32 $effect: focus policy on a report change (the slice's only effects: one before, one after the DOM change)
App.svelte:34 document.activeElement: focus policy: has focus fallen to <body>?
App.svelte:34 document.body: focus policy: has focus fallen to <body>?
App.svelte:34 .focus(: focus policy: move focus to the list heading
App.svelte:84 bind:this: focus policy: the list, and its heading to focus
App.svelte:87 bind:this: focus policy: the list, and its heading to focus
main.ts:8 document.getElementById: the mount point, once at start-up
-- ordering computed in the browser --
components/StatStrip.svelte:10 return [...stats].sort((a, b) => rank(a.name) - rank(b.name));
lib/filters.ts:60 .sort(([left], [right]) => left.localeCompare(right, 'en', { sensitivity: 'base' }))
-- build output --
assets/app.css: 31725 bytes; URL strings 1 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: []; @import/@font-face/remote url(): []
assets/app.js: 144389 bytes; URL strings 16 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: []; @import/@font-face/remote url(): []
index.html: 442 bytes; URL strings 0 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: []; @import/@font-face/remote url(): []
index.html inline scripts, style elements, style or event attributes: []
RESULT: PASS
```

### S15 real scale (#206 proof; the member-column measure replaced, accessibility step from `proof_axe.py`)

```bash
.venv/bin/python spikes/issue-210/run_proof.py S15
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
report: exact=9, same-stat=65; same-stat sizes={2: 57, 3: 6, 4: 2}; members=158; wire bytes=690503
unreviewed 1440px: groups=74, members=158, value/role assertions=3261, differences=0
unreviewed 390px: groups=74, members=158, value/role assertions=3261, differences=0
spirit signatures from unmodified upload: 5/5 exact groups correct
1440px no filter: equal=True; groups=74; scope='74 groups · 158 pieces'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected=''
1440px kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
1440px kind=same_stat: equal=True; groups=65; scope='65 of 74 groups · 140 of 158 pieces — filtered to same-stat groups'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected=''
1440px class=Titan: equal=True; groups=40; scope='40 of 74 groups · 88 of 158 pieces — filtered to class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Titan'
1440px kind=exact, then class=Titan: equal=True; groups=6; scope='6 of 74 groups · 12 of 158 pieces — filtered to exact duplicates, class Titan'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected='Titan'
1440px class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Hunter'
1440px kind=same_stat, then class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to same-stat groups, class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Hunter'
1440px class=Titan, then kind=same_stat: equal=True; groups=34; scope='34 of 74 groups · 76 of 158 pieces — filtered to same-stat groups, class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Titan'
1440px class=Hunter, then kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
  dropped-class notices: slice='Filter no longer applies and was cleared: class Hunter.'; production='Local view state dropped: duplicate filter guardianClass Hunter.'
1440px E10 sequences: executed=9, unsupported=0; real-upload Hunter-to-Exact drops=1
390px no filter: equal=True; groups=74; scope='74 groups · 158 pieces'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected=''
390px kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
390px kind=same_stat: equal=True; groups=65; scope='65 of 74 groups · 140 of 158 pieces — filtered to same-stat groups'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected=''
390px class=Titan: equal=True; groups=40; scope='40 of 74 groups · 88 of 158 pieces — filtered to class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Titan'
390px kind=exact, then class=Titan: equal=True; groups=6; scope='6 of 74 groups · 12 of 158 pieces — filtered to exact duplicates, class Titan'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected='Titan'
390px class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (40 groups)', 'Warlock=Warlock (22 groups)']; selected='Hunter'
390px kind=same_stat, then class=Hunter: equal=True; groups=12; scope='12 of 74 groups · 24 of 158 pieces — filtered to same-stat groups, class Hunter'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Hunter'
390px class=Titan, then kind=same_stat: equal=True; groups=34; scope='34 of 74 groups · 76 of 158 pieces — filtered to same-stat groups, class Titan'; Class=['=any class', 'Hunter=Hunter (12 groups)', 'Titan=Titan (34 groups)', 'Warlock=Warlock (19 groups)']; selected='Titan'
390px class=Hunter, then kind=exact: equal=True; groups=9; scope='9 of 74 groups · 18 of 158 pieces — filtered to exact duplicates'; Class=['=any class', 'Titan=Titan (6 groups)', 'Warlock=Warlock (3 groups)']; selected=''
  dropped-class notices: slice='Filter no longer applies and was cleared: class Hunter.'; production='Local view state dropped: duplicate filter guardianClass Hunter.'
390px E10 sequences: executed=9, unsupported=0; real-upload Hunter-to-Exact drops=1
far-down acknowledged verdict: group=74/74; scroll before=54374px; same focused node=True; scroll change=20px; control viewport change=0px
acknowledged 1440px light: groups=74, members=158, value/role assertions=3261, differences=0
layout 1440px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1440px dark: groups=74, members=158, value/role assertions=3261, differences=0
layout 1440px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1024px light: groups=74, members=158, value/role assertions=3261, differences=0
layout 1024px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1024px dark: groups=74, members=158, value/role assertions=3261, differences=0
layout 1024px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 390px light: groups=74, members=158, value/role assertions=3261, differences=0
layout 390px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 390px dark: groups=74, members=158, value/role assertions=3261, differences=0
layout 390px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
sanitised report, acknowledged verdict, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, acknowledged verdict, 1440px light: keyboard focus=444/444; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 1440px light, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, acknowledged verdict, 1440px light, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, acknowledged verdict, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, acknowledged verdict, 1440px dark: keyboard focus=444/444; lowest 15.96:1 (Approve item 1000000000000000296); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 1440px dark, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, acknowledged verdict, 1440px dark, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, acknowledged verdict, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, acknowledged verdict, 390px light: keyboard focus=444/444; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 390px light, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, acknowledged verdict, 390px light, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, acknowledged verdict, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, acknowledged verdict, 390px dark: keyboard focus=444/444; lowest 15.96:1 (Approve item 1000000000000000296); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 390px dark, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, acknowledged verdict, 390px dark, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
slice CSP violations: []; console/errors/dialogs: {'dialogs': [], 'console': [], 'errors': []}
timing run 1 slice: all groups=74; navigation=245.5ms, next frame=257.9ms; ack-to-DOM=7.4ms, next frame=12.3ms; DOM elements=13019
timing run 1 production: all groups=74; navigation=150.2ms, next frame=156.5ms; ack-to-DOM=10.0ms, next frame=18.1ms; DOM elements=17138
timing run 2 production: all groups=74; navigation=147.0ms, next frame=153.6ms; ack-to-DOM=11.3ms, next frame=19.8ms; DOM elements=17138
timing run 2 slice: all groups=74; navigation=235.5ms, next frame=247.3ms; ack-to-DOM=7.5ms, next frame=7.8ms; DOM elements=13019
timing run 3 slice: all groups=74; navigation=227.1ms, next frame=241.1ms; ack-to-DOM=7.6ms, next frame=12.1ms; DOM elements=13019
timing run 3 production: all groups=74; navigation=151.2ms, next frame=157.0ms; ack-to-DOM=11.4ms, next frame=19.6ms; DOM elements=17138
timing run 4 production: all groups=74; navigation=143.9ms, next frame=148.8ms; ack-to-DOM=9.4ms, next frame=17.7ms; DOM elements=17138
timing run 4 slice: all groups=74; navigation=236.7ms, next frame=249.4ms; ack-to-DOM=6.6ms, next frame=7.1ms; DOM elements=13019
timing run 5 slice: all groups=74; navigation=228.8ms, next frame=241.9ms; ack-to-DOM=8.3ms, next frame=8.5ms; DOM elements=13019
timing run 5 production: all groups=74; navigation=141.1ms, next frame=148.4ms; ack-to-DOM=9.8ms, next frame=9.9ms; DOM elements=17138
verdict target: group 74/74, chosen from the envelope
slice medians (5 runs): navigation=235.5ms, next frame=247.3ms; ack-to-DOM=7.5ms, next frame=8.5ms; DOM elements=13019
production medians (5 runs): navigation=147.0ms, next frame=153.6ms; ack-to-DOM=10.0ms, next frame=18.1ms; DOM elements=17138
RESULT: PASS
```

### CSP (`proof_csp.py`, in place of S7 part 1)

```bash
.venv/bin/python spikes/issue-210/proof_csp.py
```

```text
production policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
additions the slice is served with: []
exercised: ['class facet', 'kind filter, dropping the class (reconciliation notice)', 'verdict buttons (approve, veto, unset)', 'focus ring', 'finalise (frozen controls, persisted-veto notice, download link)', 'reset (the no-report empty state)', 'reload']
requests: {'document GET spike/': 1, 'script GET spike/assets/app.js': 1, 'stylesheet GET spike/assets/app.css': 1, 'fetch GET api/report': 3, 'fetch POST api/verdicts': 4, 'fetch POST api/finalize': 1, 'fetch POST api/reset': 1}
responses checked one by one: 12 for 12 requests; without production's policy: 0 []
violations: []; console errors: []; page errors: []
stylesheet applied: True (read from 3 slice buttons); <style> elements: 0; style attributes: 0; images: 0; web fonts: 0
negative control, policy removed from verdict responses after the first: verdict responses=4; responses without production's policy=3 ['api/verdicts']; a one-policy-per-path check would have seen=0
RESULT: PASS
```

### Accessibility and focus (`proof_axe.py`, in place of S13)

```bash
.venv/bin/python spikes/issue-210/proof_axe.py
```

```text
axe-core 4.13.0 (MPL-2.0), development-only
-- S13's seven states, synthetic fixture --
reviewing, unreviewed, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, unreviewed, 1440px light: keyboard focus=18/18; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 1440px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, unreviewed, 1440px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, unreviewed, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, unreviewed, 1440px dark: keyboard focus=18/18; lowest 15.96:1 (Approve item 6032); primary=[]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 1440px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, unreviewed, 1440px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, unreviewed, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, unreviewed, 390px light: keyboard focus=18/18; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 390px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, unreviewed, 390px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, unreviewed, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, unreviewed, 390px dark: keyboard focus=18/18; lowest 15.96:1 (Approve item 6032); primary=[]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 390px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, unreviewed, 390px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
approval in flight, 1440px light: keyboard focus=18/18; lowest 3.27:1 (Reload report); primary=[]; outline floor=3px/2px; problems=[]
approval in flight, 1440px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 1440px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
approval in flight, 1440px dark: keyboard focus=18/18; lowest 4.86:1 (Reload report); primary=[]; outline floor=3px/2px; problems=[]
approval in flight, 1440px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 1440px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
approval in flight, 390px light: keyboard focus=18/18; lowest 3.27:1 (Reload report); primary=[]; outline floor=3px/2px; problems=[]
approval in flight, 390px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 390px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
approval in flight, 390px dark: keyboard focus=18/18; lowest 4.86:1 (Reload report); primary=[]; outline floor=3px/2px; problems=[]
approval in flight, 390px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
approval in flight, 390px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one approval, 1440px light: keyboard focus=18/18; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one approval, 1440px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 1440px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one approval, 1440px dark: keyboard focus=18/18; lowest 15.96:1 (Approve item 6032); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one approval, 1440px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 1440px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one approval, 390px light: keyboard focus=18/18; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one approval, 390px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 390px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one approval, 390px dark: keyboard focus=18/18; lowest 15.96:1 (Approve item 6032); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one approval, 390px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one approval, 390px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one veto, 1440px light: keyboard focus=18/18; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one veto, 1440px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 1440px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one veto, 1440px dark: keyboard focus=18/18; lowest 15.96:1 (Approve item 6032); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one veto, 1440px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 1440px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one veto, 390px light: keyboard focus=18/18; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one veto, 390px light, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 390px light, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
reviewing, one veto, 390px dark: keyboard focus=18/18; lowest 15.96:1 (Approve item 6032); primary=[]; outline floor=3px/2px; problems=[]
reviewing, one veto, 390px dark, Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
reviewing, one veto, 390px dark, Shift+Tab: focus stops=18, reached=18, with a visible focus indicator=18, outline clipped or covered=0 []
filtered, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
filtered, 1440px light: keyboard focus=15/15; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
filtered, 1440px light, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
filtered, 1440px light, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
filtered, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
filtered, 1440px dark: keyboard focus=15/15; lowest 15.96:1 (Approve item 6081); primary=[]; outline floor=3px/2px; problems=[]
filtered, 1440px dark, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
filtered, 1440px dark, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
filtered, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
filtered, 390px light: keyboard focus=15/15; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
filtered, 390px light, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
filtered, 390px light, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
filtered, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
filtered, 390px dark: keyboard focus=15/15; lowest 15.96:1 (Approve item 6081); primary=[]; outline floor=3px/2px; problems=[]
filtered, 390px dark, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
filtered, 390px dark, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
finalised, 1440px light: keyboard focus=15/15; lowest 4.00:1 (Approve item 6081); primary=[]; outline floor=3px/2px; problems=[]
finalised, 1440px light, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 1440px light, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
finalised, 1440px dark: keyboard focus=15/15; lowest 5.56:1 (Approve item 6081); primary=[]; outline floor=3px/2px; problems=[]
finalised, 1440px dark, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 1440px dark, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
finalised, 390px light: keyboard focus=15/15; lowest 4.00:1 (Approve item 6081); primary=[]; outline floor=3px/2px; problems=[]
finalised, 390px light, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 390px light, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
finalised, 390px dark: keyboard focus=15/15; lowest 5.56:1 (Approve item 6081); primary=[]; outline floor=3px/2px; problems=[]
finalised, 390px dark, Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
finalised, 390px dark, Shift+Tab: focus stops=15, reached=15, with a visible focus indicator=15, outline clipped or covered=0 []
no report, 1440px light: rules passed=33, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
no report, 1440px light: keyboard focus=5/5; lowest 3.27:1 (Finalise review); primary=[]; outline floor=3px/2px; problems=[]
no report, 1440px light, Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
no report, 1440px light, Shift+Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
no report, 1440px dark: rules passed=33, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
no report, 1440px dark: keyboard focus=5/5; lowest 4.86:1 (Finalise review); primary=[]; outline floor=3px/2px; problems=[]
no report, 1440px dark, Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
no report, 1440px dark, Shift+Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
no report, 390px light: rules passed=33, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
no report, 390px light: keyboard focus=5/5; lowest 3.27:1 (Finalise review); primary=[]; outline floor=3px/2px; problems=[]
no report, 390px light, Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
no report, 390px light, Shift+Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
no report, 390px dark: rules passed=33, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
no report, 390px dark: keyboard focus=5/5; lowest 4.86:1 (Finalise review); primary=[]; outline floor=3px/2px; problems=[]
no report, 390px dark, Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
no report, 390px dark, Shift+Tab: focus stops=5, reached=5, with a visible focus indicator=5, outline clipped or covered=0 []
-- the sanitised report --
sanitised report, unreviewed, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, unreviewed, 1440px light: keyboard focus=444/444; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, unreviewed, 1440px light, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, unreviewed, 1440px light, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, unreviewed, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, unreviewed, 1440px dark: keyboard focus=444/444; lowest 15.96:1 (Approve item 1000000000000000296); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, unreviewed, 1440px dark, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, unreviewed, 1440px dark, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, unreviewed, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, unreviewed, 390px light: keyboard focus=444/444; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, unreviewed, 390px light, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, unreviewed, 390px light, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, unreviewed, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, unreviewed, 390px dark: keyboard focus=444/444; lowest 15.96:1 (Approve item 1000000000000000296); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, unreviewed, 390px dark, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, unreviewed, 390px dark, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, one approval, 1440px light: keyboard focus=444/444; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, one approval, 1440px light, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 1440px light, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, one approval, 1440px dark: keyboard focus=444/444; lowest 15.96:1 (Approve item 1000000000000000296); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, one approval, 1440px dark, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 1440px dark, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, one approval, 390px light: keyboard focus=444/444; lowest 14.68:1 (Skip to review content); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, one approval, 390px light, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 390px light, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 0 nodes, measured here 0, lowest none to measure; unexplained: []
sanitised report, one approval, 390px dark: keyboard focus=444/444; lowest 15.96:1 (Approve item 1000000000000000296); primary=[]; outline floor=3px/2px; problems=[]
sanitised report, one approval, 390px dark, Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
sanitised report, one approval, 390px dark, Shift+Tab: focus stops=444, reached=444, with a visible focus indicator=444, outline clipped or covered=0 []
negative control, muted role word on a filled stat cell (390px dark): detected=True ['violation {\'id\': \'color-contrast\', \'impact\': \'serious\', \'nodes\': 74, \'first\': \'article[aria-labelledby="c2-name"] > .group-head > ul > .stat[data-stat="class"][data-role="primary"] > .stat-role[data-field="stat_role"]\'}']
negative control, focus outline in the card colour: controls failing=444
negative control, overflow hidden on the verdict wrapper: outlines clipped by it=435 of 435 verdict buttons
negative control, no scroll padding below (1440px): outlines past the viewport's bottom=75
negative control, no scroll padding below (390px): outlines past the viewport's bottom=6
negative control, no scroll padding above (390px, Shift+Tab): outlines under the sticky heading=6
RESULT: PASS
```

### Layout (`proof_layout.py`)

```bash
.venv/bin/python spikes/issue-210/proof_layout.py
```

```text
armor_close.csv, 1440px light: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
armor_close.csv, 1440px dark: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
armor_close.csv, 390px light: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
armor_close.csv, 390px dark: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
armor_same_stat_four_ui.csv, 1440px light: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=156, under 11px=[]
armor_same_stat_four_ui.csv, 1440px dark: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=156, under 11px=[]
armor_same_stat_four_ui.csv, 390px light: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=183, under 11px=[]
armor_same_stat_four_ui.csv, 390px dark: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=183, under 11px=[]
real, 1440px light: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6278, under 11px=[]
real, 1440px dark: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6278, under 11px=[]
real, 390px light: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6386, under 11px=[]
real, 390px dark: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6386, under 11px=[]
negative control, matrix forced to block at 1440px: groups failing side by side=74 of 74
-- identical tuning, Holofoil differs (built in memory, uploaded through the server) --
1440px: same-stat groups=1; pieces=2; every piece leads with a visible tuned stat and one marker=True [('8301', 'Weapons'), ('8302', 'Weapons')]; also in the shared line=[True]; differences from the server's report=0 []
390px: same-stat groups=1; pieces=2; every piece leads with a visible tuned stat and one marker=True [('8301', 'Weapons'), ('8302', 'Weapons')]; also in the shared line=[True]; differences from the server's report=0 []
RESULT: PASS
```

### No transition (`proof_no_transition.py`)

```bash
.venv/bin/python spikes/issue-210/proof_no_transition.py
```

```text
built stylesheet: rules mentioning aria-disabled=0
dark: verdict buttons=435, pressed=145, with a transition or animation=0
style recalculation over one acknowledged verdict, ms: 1.2, 1.8, 1.0, 1.5, 1.1; median 1.2 (recorded, not gated; #209 measured 138.7 on #206)
after 5 verdicts: pressed=145, with a transition or animation=0
negative control, a 0.2s transition added: with a transition=435 of 435
light: verdict buttons=435, pressed=145, with a transition or animation=0
RESULT: PASS
```
