# Issue #213 evidence: the timing gate on the redesigned slice

Transcripts behind [docs/frontend-framework-decision.md](../../frontend-framework-decision.md),
"The redesigned slice against #209's gate (#213)". The code is in
[spikes/issue-213/](../../../spikes/issue-213/README.md).

- Every fence is the complete output of the command above it, standard output
  and standard error together, with a last line `exit N` added by the shell
  that ran it. Nothing else is added, removed or reordered.
- Run from the repository root, on one machine, with the pinned Playwright
  Chromium, Python 3.14.4 and Node v24.20.0.
- Only tracked fixtures were read. The real-scale ones use the sanitised
  `tests/fixtures/real/2026-09-01T-current/armor.csv`; every id shown carries
  the `1000` marker. Nothing under `data/` was read.
- Timings vary from run to run. Rerunning a command reproduces the direction,
  not the digits.
- The two `diff` fences (sections 5 and 7) are not verbatim in one respect:
  the single space that `git diff` prints on an empty context line is removed,
  because the repository's whitespace check rejects it.
- Some transcripts carry this checkout's absolute path or a temporary
  directory name. They are left as printed.

Contents: [1 builds](#1-builds) · [2 baseline gate](#2-the-gate-on-the-unchanged-copy-baseline) ·
[3 proofs](#3-every-proof-on-the-unchanged-copy) · [4 attribution](#4-attribution) ·
[5 the change tried](#5-the-one-change-tried-and-dropped) · [6 final gate](#6-the-two-final-gate-invocations) ·
[7 gate diff](#7-the-gate-proof-against-209s) · [8 repository checks](#8-repository-checks)

## 1. Builds

`spikes/issue-213/frontend` is a byte-for-byte copy of
`spikes/issue-210/frontend` at copy commit
`b2de097523f429572052644fa000e2ca3bf40820`, and ends this ticket unchanged.
From `spikes/issue-213/frontend`, after removing `node_modules` and `dist`:

```bash
(cd spikes/issue-213/frontend && npm ci)
```

```text

added 77 packages, and audited 78 packages in 1s

18 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
```

```bash
(cd spikes/issue-213/frontend && npm run check)
```

```text
npm notice run vault-cleaner-spike-206-frontend@0.0.0 check
npm notice run svelte-check --tsconfig ./tsconfig.json --fail-on-warnings
1791736397975 START "/home/raver/projects/personal/vault-cleaner/spikes/issue-213/frontend"
1791736397976 COMPLETED 303 FILES 0 ERRORS 0 WARNINGS 0 FILES_WITH_PROBLEMS
exit 0
```

```bash
(cd spikes/issue-213/frontend && npm test)
```

```text
npm notice run vault-cleaner-spike-206-frontend@0.0.0 test
npm notice run vitest run

 RUN  v5.0.3 /home/raver/projects/personal/vault-cleaner/spikes/issue-213/frontend


 Test Files  3 passed (3)
      Tests  43 passed (43)
   Start at  16:33:19
   Duration  580ms (transform 82%, import 11%, tests 5%, worker 1%)

exit 0
```

```bash
(cd spikes/issue-213/frontend && npm run build)
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

✓ built in 277ms
exit 0
```

The #210 build was made the same way (`npm ci && npm run build` in
`spikes/issue-210/frontend`). The two builds are the same bytes:

```bash
sha256sum spikes/issue-21[03]/frontend/dist/assets/app.*
```

```text
95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0  spikes/issue-210/frontend/dist/assets/app.css
5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981  spikes/issue-210/frontend/dist/assets/app.js
95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0  spikes/issue-213/frontend/dist/assets/app.css
5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981  spikes/issue-213/frontend/dist/assets/app.js
```

## 2. The gate on the unchanged copy (baseline)

Two complete invocations, one after the other. Both fail: navigation (A1, A2,
B1) by 85 to 102 ms, and B2 and B3 by 2 to 9 ms.

Invocation 1 of 5:

```bash
.venv/bin/python spikes/issue-213/proof_gate.py
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=239.0ms; navigationFrame=250.5ms; dom=7.2ms; frame=12.1ms; navigationSettled=262.0ms; keySettled=49.7ms; ackSettled=29.9ms; responseEnd=53.8ms; elements=13019; action=Approve
run 1 production: navigation=148.8ms; navigationFrame=156.3ms; dom=10.1ms; frame=18.9ms; navigationSettled=167.1ms; keySettled=44.2ms; ackSettled=20.8ms; responseEnd=37.9ms; elements=17138; action=Veto
run 2 production: navigation=142.4ms; navigationFrame=147.7ms; dom=8.6ms; frame=17.5ms; navigationSettled=150.4ms; keySettled=42.8ms; ackSettled=18.9ms; responseEnd=35.4ms; elements=17138; action=Approve
run 2 slice: navigation=226.7ms; navigationFrame=239.0ms; dom=6.7ms; frame=12.9ms; navigationSettled=249.3ms; keySettled=53.7ms; ackSettled=30.1ms; responseEnd=53.2ms; elements=13019; action=Veto
run 3 slice: navigation=251.6ms; navigationFrame=263.4ms; dom=5.5ms; frame=12.5ms; navigationSettled=275.1ms; keySettled=54.1ms; ackSettled=29.6ms; responseEnd=47.1ms; elements=13019; action=Approve
run 3 production: navigation=143.7ms; navigationFrame=148.8ms; dom=9.6ms; frame=17.5ms; navigationSettled=158.2ms; keySettled=41.2ms; ackSettled=19.2ms; responseEnd=36.8ms; elements=17138; action=Veto
run 4 production: navigation=145.9ms; navigationFrame=151.8ms; dom=9.9ms; frame=18.8ms; navigationSettled=161.4ms; keySettled=44.1ms; ackSettled=20.5ms; responseEnd=36.3ms; elements=17138; action=Approve
run 4 slice: navigation=228.1ms; navigationFrame=240.1ms; dom=8.9ms; frame=11.4ms; navigationSettled=250.6ms; keySettled=45.6ms; ackSettled=28.0ms; responseEnd=49.1ms; elements=13019; action=Veto
run 5 slice: navigation=229.2ms; navigationFrame=241.9ms; dom=7.9ms; frame=11.5ms; navigationSettled=253.9ms; keySettled=52.3ms; ackSettled=29.0ms; responseEnd=51.8ms; elements=13019; action=Approve
run 5 production: navigation=144.0ms; navigationFrame=149.5ms; dom=11.6ms; frame=22.3ms; navigationSettled=159.6ms; keySettled=50.6ms; ackSettled=24.3ms; responseEnd=34.5ms; elements=17138; action=Veto
A1 navigation to all groups: slice=229.2ms production=144.0ms gap=+85.2ms FAIL
A2 navigation to next frame: slice=241.9ms production=149.5ms gap=+92.4ms FAIL
A3 acknowledgement to DOM: slice=7.2ms production=9.9ms gap=-2.7ms PASS
A4 acknowledgement to next frame: slice=12.1ms production=18.8ms gap=-6.7ms PASS
B1 navigation to settled: slice=253.9ms production=159.6ms gap=+94.3ms FAIL
B2 key press to settled: slice=52.3ms production=44.1ms gap=+8.2ms FAIL
B3 acknowledgement to settled: slice=29.6ms production=20.5ms gap=+9.1ms FAIL
slice navigation CDP medians: ScriptDuration=95.0ms; RecalcStyleDuration=31.8ms; LayoutDuration=76.0ms; TaskDuration=265.4ms
slice verdict CDP medians: ScriptDuration=7.3ms; RecalcStyleDuration=1.0ms; LayoutDuration=4.3ms; TaskDuration=36.1ms
production navigation CDP medians: ScriptDuration=22.3ms; RecalcStyleDuration=15.1ms; LayoutDuration=45.5ms; TaskDuration=149.6ms
production verdict CDP medians: ScriptDuration=3.5ms; RecalcStyleDuration=3.0ms; LayoutDuration=8.9ms; TaskDuration=39.6ms
M4 one-class: buttons=1; style median=0.1ms; samples=[0.2, 0.2, 0.2, 0.1, 0.1, 0.1]
M4 all-class: buttons=435; style median=3.0ms; samples=[2.9, 2.7, 3.0, 3.0, 3.2, 3.7]
M4 all-aria: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M4 all-both: buttons=435; style median=3.1ms; samples=[3.1, 3.2, 3.2, 2.8, 2.7, 3.0]
M4 all-disabled: buttons=435; style median=3.4ms; samples=[4.0, 3.2, 3.4, 3.6, 3.3, 3.3]
M4 all-unused: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M5 warm Node medians (50): bytes=743025; JSON.parse=1.259ms; projection=0.341ms; value-stable projection=0.830ms
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: B1 navigation to settled
FAIL: B2 key press to settled
FAIL: B3 acknowledgement to settled
RESULT: FAIL
exit 1
```

Invocation 2 of 5:

```bash
.venv/bin/python spikes/issue-213/proof_gate.py
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=240.2ms; navigationFrame=252.9ms; dom=7.4ms; frame=7.6ms; navigationSettled=264.0ms; keySettled=36.4ms; ackSettled=20.3ms; responseEnd=54.5ms; elements=13019; action=Approve
run 1 production: navigation=150.8ms; navigationFrame=157.7ms; dom=9.1ms; frame=18.0ms; navigationSettled=160.2ms; keySettled=42.6ms; ackSettled=19.7ms; responseEnd=36.6ms; elements=17138; action=Veto
run 2 production: navigation=148.3ms; navigationFrame=153.8ms; dom=9.7ms; frame=15.5ms; navigationSettled=163.3ms; keySettled=56.4ms; ackSettled=32.2ms; responseEnd=39.7ms; elements=17138; action=Approve
run 2 slice: navigation=242.9ms; navigationFrame=256.3ms; dom=10.6ms; frame=10.8ms; navigationSettled=261.9ms; keySettled=47.0ms; ackSettled=28.4ms; responseEnd=48.8ms; elements=13019; action=Veto
run 3 slice: navigation=253.4ms; navigationFrame=265.3ms; dom=14.4ms; frame=14.6ms; navigationSettled=274.1ms; keySettled=40.9ms; ackSettled=23.4ms; responseEnd=56.3ms; elements=13019; action=Approve
run 3 production: navigation=146.8ms; navigationFrame=152.0ms; dom=10.1ms; frame=18.4ms; navigationSettled=163.4ms; keySettled=45.0ms; ackSettled=19.8ms; responseEnd=40.9ms; elements=17138; action=Veto
run 4 production: navigation=149.1ms; navigationFrame=155.2ms; dom=9.0ms; frame=16.2ms; navigationSettled=157.9ms; keySettled=57.9ms; ackSettled=33.3ms; responseEnd=36.8ms; elements=17138; action=Approve
run 4 slice: navigation=225.4ms; navigationFrame=237.8ms; dom=7.4ms; frame=12.3ms; navigationSettled=249.0ms; keySettled=53.9ms; ackSettled=29.4ms; responseEnd=51.4ms; elements=13019; action=Veto
run 5 slice: navigation=240.8ms; navigationFrame=252.7ms; dom=7.3ms; frame=12.3ms; navigationSettled=258.6ms; keySettled=51.4ms; ackSettled=30.0ms; responseEnd=49.5ms; elements=13019; action=Approve
run 5 production: navigation=137.0ms; navigationFrame=142.4ms; dom=10.2ms; frame=19.1ms; navigationSettled=152.4ms; keySettled=44.1ms; ackSettled=20.9ms; responseEnd=29.3ms; elements=17138; action=Veto
A1 navigation to all groups: slice=240.8ms production=148.3ms gap=+92.5ms FAIL
A2 navigation to next frame: slice=252.9ms production=153.8ms gap=+99.1ms FAIL
A3 acknowledgement to DOM: slice=7.4ms production=9.7ms gap=-2.3ms PASS
A4 acknowledgement to next frame: slice=12.3ms production=18.0ms gap=-5.7ms PASS
B1 navigation to settled: slice=261.9ms production=160.2ms gap=+101.7ms FAIL
B2 key press to settled: slice=47.0ms production=45.0ms gap=+2.0ms FAIL
B3 acknowledgement to settled: slice=28.4ms production=20.9ms gap=+7.5ms FAIL
slice navigation CDP medians: ScriptDuration=97.0ms; RecalcStyleDuration=31.8ms; LayoutDuration=77.8ms; TaskDuration=257.0ms
slice verdict CDP medians: ScriptDuration=8.5ms; RecalcStyleDuration=1.2ms; LayoutDuration=4.9ms; TaskDuration=39.9ms
production navigation CDP medians: ScriptDuration=23.0ms; RecalcStyleDuration=15.7ms; LayoutDuration=46.2ms; TaskDuration=146.6ms
production verdict CDP medians: ScriptDuration=3.3ms; RecalcStyleDuration=3.1ms; LayoutDuration=8.5ms; TaskDuration=38.7ms
M4 one-class: buttons=1; style median=0.1ms; samples=[0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
M4 all-class: buttons=435; style median=2.5ms; samples=[2.1, 2.4, 2.5, 2.6, 4.0, 2.4]
M4 all-aria: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M4 all-both: buttons=435; style median=2.4ms; samples=[2.4, 2.3, 3.0, 2.2, 2.2, 2.4]
M4 all-disabled: buttons=435; style median=3.8ms; samples=[3.4, 3.5, 3.5, 4.1, 4.1, 4.4]
M4 all-unused: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M5 warm Node medians (50): bytes=743025; JSON.parse=1.373ms; projection=0.374ms; value-stable projection=0.801ms
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: B1 navigation to settled
FAIL: B2 key press to settled
FAIL: B3 acknowledgement to settled
RESULT: FAIL
exit 1
```

## 3. Every proof on the unchanged copy

These are the fix-round runs, made after the independent review, each once
through `spikes/issue-213/run_proof.py` as it now is. The same thirteen
passed at the baseline on the same build; those transcripts were in this
file at commit `895c2ec` and are replaced here, because the runner's
`build-check` path changed in the fix round. The `build served`
line in each is the SHA-256 of the two files the live server sent to that
proof's signed-in browser; the runner fails the proof if they are not the
#213 build's. The source scan opens no browser, so it has no such line.

`build-check` is that check's negative control. It serves #206's build on
purpose. The `RESULT: FAIL` line in its transcript is the check firing, which
is what the control requires; the proof's own result is the last line.
It needs `spikes/issue-206/frontend` built. Without that build it now ends
with its own `RESULT: FAIL`; that path is shown after its transcript.

### build-check

```bash
.venv/bin/python spikes/issue-213/run_proof.py build-check
```

```text
build served: app.js sha256=9fca3eaf5580099fbf9856b8ce93ea877606183c63d7c64fd0172cdc8cde4ccf app.css sha256=fd6dfbe3f715a7456e1eaf1330c5d0f044e5f666d77a7393279a611ca945eac1; is the issue-213 build=False; same bytes as the issue-210 build=False
RESULT: FAIL (the server did not send the issue-213 build)
negative control: #206's build was served and refused
RESULT: PASS
exit 0
```

With `spikes/issue-206/frontend/dist` moved aside for one run, then moved back:

```bash
mv spikes/issue-206/frontend/dist spikes/issue-206/frontend/dist.aside; .venv/bin/python spikes/issue-213/run_proof.py build-check; echo "exit $?"; mv spikes/issue-206/frontend/dist.aside spikes/issue-206/frontend/dist
```

```text
FAIL: not built: spikes/issue-206/frontend. Run `npm ci && npm run build` there first.
RESULT: FAIL
exit 1
```

### S1

```bash
.venv/bin/python spikes/issue-213/run_proof.py S1
```

```text
-- every required value, for four fixtures, without and with verdicts --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
armor_close.csv unreviewed at 1440px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv unreviewed at 390px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 1440px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 390px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
armor_duplicates_ui.csv unreviewed at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv unreviewed at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
armor_same_stat_ui.csv unreviewed at 1440px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv unreviewed at 390px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 1440px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 390px: 1 groups, 2 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
armor_same_stat_four_ui.csv unreviewed at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv unreviewed at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
-- group values no fixture has, overlaid in memory on the server's answer --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
exact:6031 shows: {'spirit_signature': 'Spirit of the Fixture · Spirit of the Proof', 'seasonal_mod': 'Fake Seasonal Mod', 'holofoil': 'true'}
same_stat:6081 shows: {'spirit_signature': 'Spirit of the Twin'}
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 1440px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 390px: 2 groups, 4 members, 4 differing member values all visible=True, page scrolls sideways=False, differences=0
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
exit 0
```

### S2

```bash
.venv/bin/python spikes/issue-213/run_proof.py S2
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
exit 0
```

### S3

```bash
.venv/bin/python spikes/issue-213/run_proof.py S3
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
exit 0
```

### S4

```bash
.venv/bin/python spikes/issue-213/run_proof.py S4
```

```text
-- finalise from the open page, with a veto in place --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
finalise posted outside the page: HTTP 200; revisions unchanged=True
open page, before it makes any request: {'verdict': 'Vetoed', 'persisted_veto': False, 'pressed': ['Veto'], 'disabled': [False, False, False]}
status: 'Your approval was not applied: this review is finalised.'
POSTs sent by the page: ['verdicts']; server verdicts=[{'id': '6032', 'verdict': 'vetoed'}]
open page now: {'session': 'Finalised. The reviewed CSV has been produced and this review is frozen.', '6032': {'verdict': 'Vetoed', 'persisted_veto': True, 'pressed': ['Veto'], 'disabled': [True, True, True]}, 'all verdict controls disabled': True, 'download link': 1}
a fresh load shows the same: True
-- the server stops --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
filter with the server stopped: groups=['same_stat:6081']; scope='1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups'
a verdict with the server stopped: status='Your approval was not applied. The review server did not answer. Filters still work; use Reload to reconnect.'
nothing shown as applied, controls off: {'verdict': 'Unreviewed', 'persisted_veto': False, 'pressed': ['Unset'], 'disabled': [True, True, True]}; connection=disconnected
filter again while disconnected: groups=['exact:6031']; scope='1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates'
RESULT: PASS
exit 0
```

### S5

```bash
.venv/bin/python spikes/issue-213/run_proof.py S5
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
exit 0
```

### S6

```bash
.venv/bin/python spikes/issue-213/run_proof.py S6
```

```text
-- armor_close.csv --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
1440px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1440px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
tab order at 390px: ['Skip to review content', 'Reload report', 'Finalise review', 'Reset session', 'All (2)', 'Exact (1)', 'Same stats (1)', 'any classTitan (2 groups)', 'Reset filters', 'Approve item 6032', 'Veto item 6032', 'Unset item 6032', 'Approve item 6081', 'Veto item 6081', 'Unset item 6081', 'Approve item 6082', 'Veto item 6082', 'Unset item 6082']
-- armor_same_stat_four_ui.csv --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
1440px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1440px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
1024px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px light: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
390px dark: page scrolls sideways=False; sideways scrollers inside the page=0; every required value visible=True; ids and hashes inside the viewport=True, clipped=0; members stacked in 1 column; controls=18, reached by Tab in document order=18 (True), tab stops not visible=0, controls outside the viewport=0
RESULT: PASS
exit 0
```

### source

```bash
.venv/bin/python spikes/issue-213/run_proof.py source
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
exit 0
```

### csp

```bash
.venv/bin/python spikes/issue-213/run_proof.py csp
```

```text
production policy: default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
additions the slice is served with: []
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
exercised: ['class facet', 'kind filter, dropping the class (reconciliation notice)', 'verdict buttons (approve, veto, unset)', 'focus ring', 'finalise (frozen controls, persisted-veto notice, download link)', 'reset (the no-report empty state)', 'reload']
requests: {'document GET spike/': 1, 'script GET spike/assets/app.js': 1, 'stylesheet GET spike/assets/app.css': 1, 'fetch GET api/report': 3, 'fetch POST api/verdicts': 4, 'fetch POST api/finalize': 1, 'fetch POST api/reset': 1}
responses checked one by one: 12 for 12 requests; without production's policy: 0 []
violations: []; console errors: []; page errors: []
stylesheet applied: True (read from 3 slice buttons); <style> elements: 0; style attributes: 0; images: 0; web fonts: 0
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
negative control, policy removed from verdict responses after the first: verdict responses=4; responses without production's policy=3 ['api/verdicts']; a one-policy-per-path check would have seen=0
RESULT: PASS
exit 0
```

### layout

```bash
.venv/bin/python spikes/issue-213/run_proof.py layout
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
armor_close.csv, 1440px light: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
armor_close.csv, 1440px dark: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
armor_close.csv, 390px light: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
armor_close.csv, 390px dark: groups by piece count={2: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=162, under 11px=[]
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
armor_same_stat_four_ui.csv, 1440px light: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=156, under 11px=[]
armor_same_stat_four_ui.csv, 1440px dark: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=156, under 11px=[]
armor_same_stat_four_ui.csv, 390px light: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=183, under 11px=[]
armor_same_stat_four_ui.csv, 390px dark: groups by piece count={4: 1}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=183, under 11px=[]
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
real, 1440px light: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6278, under 11px=[]
real, 1440px dark: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6278, under 11px=[]
real, 390px light: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6386, under 11px=[]
real, 390px dark: groups by piece count={2: 66, 3: 6, 4: 2}; not side by side with aligned rows=0; fours not stacked=0; uneven row counts=0; groups with a cell or button outside the viewport=0; page scrolls sideways=False; visible text nodes=6386, under 11px=[]
negative control, matrix forced to block at 1440px: groups failing side by side=74 of 74
-- identical tuning, Holofoil differs (built in memory, uploaded through the server) --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
1440px: same-stat groups=1; pieces=2; every piece leads with a visible tuned stat and one marker=True [('8301', 'Weapons'), ('8302', 'Weapons')]; also in the shared line=[True]; differences from the server's report=0 []
390px: same-stat groups=1; pieces=2; every piece leads with a visible tuned stat and one marker=True [('8301', 'Weapons'), ('8302', 'Weapons')]; also in the shared line=[True]; differences from the server's report=0 []
RESULT: PASS
exit 0
```

### no-transition

```bash
.venv/bin/python spikes/issue-213/run_proof.py no-transition
```

```text
built stylesheet: rules mentioning aria-disabled=0
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
dark: verdict buttons=435, pressed=145, with a transition or animation=0
style recalculation over one acknowledged verdict, ms: 1.3, 1.6, 1.0, 1.3, 1.0; median 1.3 (recorded, not gated; #209 measured 138.7 on #206)
after 5 verdicts: pressed=145, with a transition or animation=0
negative control, a 0.2s transition added: with a transition=435 of 435
light: verdict buttons=435, pressed=145, with a transition or animation=0
RESULT: PASS
exit 0
```

### axe

```bash
.venv/bin/python spikes/issue-213/run_proof.py axe
```

```text
axe-core 4.13.0 (MPL-2.0), development-only
-- S13's seven states, synthetic fixture --
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
exit 0
```

### S15

```bash
.venv/bin/python spikes/issue-213/run_proof.py S15
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
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
timing run 1 slice: all groups=74; navigation=241.2ms, next frame=254.3ms; ack-to-DOM=6.4ms, next frame=6.9ms; DOM elements=13019
timing run 1 production: all groups=74; navigation=139.9ms, next frame=145.2ms; ack-to-DOM=8.9ms, next frame=18.0ms; DOM elements=17138
timing run 2 production: all groups=74; navigation=135.7ms, next frame=141.4ms; ack-to-DOM=9.6ms, next frame=18.2ms; DOM elements=17138
timing run 2 slice: all groups=74; navigation=230.5ms, next frame=243.4ms; ack-to-DOM=6.5ms, next frame=12.2ms; DOM elements=13019
timing run 3 slice: all groups=74; navigation=251.0ms, next frame=264.5ms; ack-to-DOM=8.7ms, next frame=11.7ms; DOM elements=13019
timing run 3 production: all groups=74; navigation=158.8ms, next frame=166.3ms; ack-to-DOM=11.3ms, next frame=21.4ms; DOM elements=17138
timing run 4 production: all groups=74; navigation=145.5ms, next frame=151.6ms; ack-to-DOM=10.5ms, next frame=15.0ms; DOM elements=17138
timing run 4 slice: all groups=74; navigation=234.1ms, next frame=246.8ms; ack-to-DOM=8.0ms, next frame=11.5ms; DOM elements=13019
timing run 5 slice: all groups=74; navigation=244.0ms, next frame=258.7ms; ack-to-DOM=7.7ms, next frame=10.5ms; DOM elements=13019
timing run 5 production: all groups=74; navigation=153.8ms, next frame=159.3ms; ack-to-DOM=9.9ms, next frame=18.2ms; DOM elements=17138
verdict target: group 74/74, chosen from the envelope
slice medians (5 runs): navigation=241.2ms, next frame=254.3ms; ack-to-DOM=7.7ms, next frame=11.5ms; DOM elements=13019
production medians (5 runs): navigation=145.5ms, next frame=151.6ms; ack-to-DOM=9.9ms, next frame=18.2ms; DOM elements=17138
RESULT: PASS
exit 0
```

## 4. Attribution

`proof_attribution.py` ran four times. All four are kept.

- **Run 1** stopped in part 4: the container-rule rewrite looked for
  `(min-width: …)` and the build writes `(width>=…)`. Parts 1 to 3 completed.
- **Run 2** is complete for the script as it then was, without the two
  layout ablations.
- **Run 3** adds the layout ablations to the last comparison.
- **Run 4** was made in the fix round, after the independent review. It
  intercepts production's document and static files the same way as the
  slice's, and adds part 0, which measures what interception costs each
  page.

**Runs 1 to 3 intercepted the slice and the floor but not production.** That
was a defect in the proof, found by the review. In those three runs every
figure that sets the slice or the floor beside production is biased against
the slice, by about the 10 ms that run 4's part 0 measures. Comparisons among
slice arms, and among floor arms, are not affected: both sides were
intercepted alike. Chromium's counters (script, style, layout) are not
affected either. The record takes its slice-against-production timings from
run 4 only.

Runs 1 to 3 were made with earlier versions of the script. Runs 1 and 2 used
versions that were never committed; run 3 used the version at commit
`895c2ec`. Those fences cannot be reproduced exactly from the current file.

Reading the output:

- `ready` is S15's stamp: every group in the document with a laid-out box.
  Each arm's bracketed figures are its difference from the first arm in the
  same comparison.
- `first group in document` is not independent of `ready`. Svelte mounts the
  whole list in one task, and S15's observer, registered first, reads a box
  and so forces style and layout before this stamp is taken.
- In the profile, "browser built-ins called from script" includes that forced
  style and layout, because the box read is called from script.
- The floor fetches its 1 MB of markup through the interception. Production
  has no equivalent request, so the floor's stamps against production's are
  an upper estimate of the floor's cost; its counters are not.
- The run-to-run spread of the unchanged arm's `ready` median across these
  comparisons is 241 to 262 ms. A difference under about 15 ms between two
  arms is not a finding.

### Run 4 (complete; production intercepted like the slice)

```bash
.venv/bin/python spikes/issue-213/proof_attribution.py
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; viewport 1440x1000 light
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
-- 0. what interception adds: each page with and without it --
  unchanged: ready=245.6ms (+0.0); settled=264.6ms (+0.0); script=94.9 style=30.7 layout=79.3 task=248.1ms; report 48.3-62.4ms; first group=245.6ms; elements=13019; report requests=[1]; ready samples=[267.3, 250, 239.3, 245.6, 242.6]
  slice, not intercepted: ready=235.6ms (-10.0); settled=259.3ms (-5.3); script=95.8 style=30.6 layout=75.6 task=255.3ms; report 39.9-51.1ms; first group=235.6ms; elements=13019; report requests=[1]; ready samples=[244.9, 233.1, 229.7, 242.3, 235.6]
  production: ready=151.4ms (-94.2); settled=159.3ms (-105.3); script=22.1 style=15.8 layout=46.7 task=145.5ms; report 29.9-44.3ms; first group=151.5ms; elements=17138; report requests=[1]; ready samples=[162.7, 166.9, 150.3, 148.4, 151.4]
  production, not intercepted: ready=144.7ms (-100.9); settled=161.2ms (-103.4); script=22.3 style=15.7 layout=46.2 task=152.7ms; report 23.7-35.1ms; first group=144.8ms; elements=17138; report requests=[1]; ready samples=[143.2, 144.7, 143.7, 147.9, 145.8]
-- 1. timeline, medians of 5 alternating fresh documents, ms from navigation start --
  slice: document=4.3; /spike/assets/app.css loaded=15.5; /spike/assets/app.js loaded=19.7
  slice: report request 48.1 to 61.9; first group in document=246.3; all groups in document=144.7; ready=246.3; next frame=259.4; settled=265.5
  slice: before the report arrived=61.9; report arrival to ready=184.4; counters to settled: script=96.5 style=30.6 layout=76.3 task=246.1; elements=13019
  production: document=4.0; /assets/review.css loaded=16.0; /assets/review_server.js loaded=18.5; /assets/review_ui.js loaded=17.2
  production: report request 28.9 to 46.5; first group in document=156.8; all groups in document=102.2; ready=156.7; next frame=163.0; settled=165.0
  production: before the report arrived=46.5; report arrival to ready=110.2; counters to settled: script=23.1 style=15.2 layout=47.6 task=147.3; elements=17138
-- 2. profile: unminified build of the same source, sampling every 200 us, medians of 5 fresh documents; proportions, not timings --
  self time by where the function came from:
      125.7 ms  browser built-ins called from script
       57.9 ms  package: svelte
       51.2 ms  browser, outside script
       12.7 ms  garbage collection
        7.5 ms  package: tailwind-variants
        5.3 ms  package: tailwind-merge
        3.8 ms  slice: lib/filters.ts
        3.0 ms  slice: lib/view.ts
        2.3 ms  slice: components/PieceColumn.svelte
        2.0 ms  slice: components/GroupCard.svelte
        1.2 ms  slice: components/ui/badge.svelte
        0.6 ms  slice: lib/session.svelte.ts
        0.6 ms  slice: App.svelte
  inclusive time under each component:
       67.3 ms  GroupCard
       40.4 ms  PieceColumn
       10.3 ms  Badge
        6.9 ms  TunedStat
        5.9 ms  StatStrip
        5.6 ms  Value
        5.1 ms  Filters
        4.9 ms  VerdictControls
        4.9 ms  App
        3.5 ms  Button
        3.4 ms  SessionPanel
-- 3. floor: the slice's own markup and stylesheet, no framework --
  captured markup: 1007504 bytes; assigned once the same report request has answered
  markup equal (comment anchors ignored)=True; every element's box equal=True
  unchanged: ready=243.5ms (+0.0); settled=263.2ms (+0.0); script=94.8 style=30.8 layout=76.0 task=248.7ms; report 46.2-60.4ms; first group=243.5ms; elements=13019; report requests=[1]; ready samples=[246.2, 246.3, 243.5, 242.6, 243]
  floor: ready=180.8ms (-62.7); settled=199.3ms (-63.9); script=1.2 style=30.5 layout=73.8 task=164.6ms; report 19.4-37.1ms; first group=180.9ms; elements=13019; report requests=[1]; ready samples=[180.8, 196.2, 176.4, 181.9, 173.7]
  production: ready=156.2ms (-87.3); settled=164.0ms (-99.2); script=22.7 style=15.4 layout=48.2 task=142.8ms; report 30.4-47.3ms; first group=156.3ms; elements=17138; report requests=[1]; ready samples=[183.2, 150.6, 156.2, 148.8, 162]
-- 4. ablations: one suspected cause removed, against the unchanged build --
  class-merge-once: a badge's class string is merged once per distinct input, not once per badge
  class-merge-once: app.js 144500 bytes sha256=5d8467ea4d01e99d; markup equal (comment anchors ignored)=True
  report-first: the report is requested before the page is mounted, not after
  report-first: app.js 144389 bytes sha256=ff0b1152095fbbc9; markup equal (comment anchors ignored)=True
  value-inline: no Value component
  value-inline: 7 uses of the Value component written out as their one span
  value-inline: app.js 145058 bytes sha256=ab7ef2065cd1ce4f; markup equal (comment anchors ignored)=True
  no-container-queries: 17 container rules and declarations resolved for a 1348 px group; markup equal (comment anchors ignored)=True; every element's box equal=True
  report-preload: a preload hint for /api/report in index.html; markup equal (comment anchors ignored)=True
  unchanged: ready=252.8ms (+0.0); settled=271.1ms (+0.0); script=97.9 style=30.6 layout=76.0 task=244.5ms; report 52.6-66.8ms; first group=252.8ms; elements=13019; report requests=[1]; ready samples=[252.8, 256.5, 240.5, 265.9, 246.6]
  class-merge-once: ready=243.8ms (-9.0); settled=261.3ms (-9.8); script=95.9 style=31.5 layout=74.4 task=243.9ms; report 50.4-64.2ms; first group=244.0ms; elements=13019; report requests=[1]; ready samples=[241.1, 243.8, 243.3, 252.3, 245.8]
  report-first: ready=245.5ms (-7.3); settled=263.3ms (-7.8); script=94.8 style=29.8 layout=77.8 task=243.3ms; report 41.7-61.8ms; first group=245.6ms; elements=13019; report requests=[1]; ready samples=[242.9, 246, 245.5, 240, 250.6]
  value-inline: ready=241.6ms (-11.2); settled=258.0ms (-13.1); script=90.2 style=30.9 layout=76.1 task=244.1ms; report 49.0-61.9ms; first group=241.6ms; elements=13019; report requests=[1]; ready samples=[235, 239.3, 248.1, 241.6, 249.3]
  no-container-queries: ready=239.8ms (-13.0); settled=258.4ms (-12.7); script=97.0 style=22.4 layout=79.2 task=240.7ms; report 50.9-65.8ms; first group=239.9ms; elements=13019; report requests=[1]; ready samples=[254.5, 235.4, 237, 239.8, 242.2]
  report-preload: ready=255.2ms (+2.4); settled=273.5ms (+2.4); script=96.1 style=30.9 layout=77.1 task=250.7ms; report 8.8-24.0ms; first group=255.2ms; elements=13020; report requests=[1]; ready samples=[261.2, 258.8, 255.2, 249.6, 252.6]
  the floor again with stylesheet ablations, beside production. The two layout
  ablations change the page's geometry: they measure the grid, they are not candidates:
  floor: ready=181.0ms (+0.0); settled=200.4ms (+0.0); script=1.1 style=32.0 layout=76.0 task=169.9ms; report 19.7-38.6ms; first group=181.1ms; elements=13019; report requests=[1]; ready samples=[191.1, 176.2, 181, 174.5, 186.4]
  floor + no-container-queries: ready=183.5ms (+2.5); settled=205.2ms (+4.8); script=1.2 style=23.6 layout=77.3 task=167.5ms; report 18.4-37.7ms; first group=183.6ms; elements=13019; report requests=[1]; ready samples=[183.7, 191.1, 180.4, 183.5, 174.2]
  floor + comparison grid as blocks: ready=179.6ms (-1.4); settled=196.0ms (-4.4); script=1.2 style=31.4 layout=70.8 task=163.2ms; report 19.3-39.0ms; first group=179.7ms; elements=13019; report requests=[1]; ready samples=[179.6, 174.3, 193.2, 172.5, 181.4]
  floor + every grid as blocks: ready=166.5ms (-14.5); settled=183.1ms (-17.3); script=1.2 style=31.0 layout=56.4 task=147.8ms; report 19.6-37.9ms; first group=166.5ms; elements=13019; report requests=[1]; ready samples=[159.3, 167.6, 165.5, 169.3, 166.5]
  floor + no-container-queries + every grid as blocks: ready=161.0ms (-20.0); settled=177.9ms (-22.5); script=1.3 style=23.0 layout=57.0 task=139.5ms; report 20.4-37.3ms; first group=161.0ms; elements=13019; report requests=[1]; ready samples=[160.4, 154.9, 167.3, 164.6, 161]
  production: ready=154.2ms (-26.8); settled=162.4ms (-38.0); script=22.2 style=15.5 layout=47.0 task=143.8ms; report 24.3-44.3ms; first group=154.3ms; elements=17138; report requests=[1]; ready samples=[154.2, 148.3, 169.5, 144.9, 161.2]
RESULT: PASS
exit 0
```

### Run 3 (complete; production not intercepted)

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; viewport 1440x1000 light
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
-- 1. timeline, medians of 5 alternating fresh documents, ms from navigation start --
  slice: document=5.0; /spike/assets/app.css loaded=20.0; /spike/assets/app.js loaded=19.6
  slice: report request 48.9 to 61.8; first group in document=245.5; all groups in document=145.8; ready=245.4; next frame=257.3; settled=263.5
  slice: before the report arrived=61.8; report arrival to ready=183.6; counters to settled: script=94.8 style=30.6 layout=77.1 task=244.5; elements=13019
  production: document=4.2; /assets/review.css loaded=12.8; /assets/review_server.js loaded=16.0; /assets/review_ui.js loaded=15.9
  production: report request 23.0 to 35.4; first group in document=148.5; all groups in document=94.8; ready=148.4; next frame=154.5; settled=157.2
  production: before the report arrived=35.4; report arrival to ready=113.0; counters to settled: script=22.9 style=15.2 layout=47.3 task=141.9; elements=17138
-- 2. profile: unminified build of the same source, sampling every 200 us, medians of 5 fresh documents; proportions, not timings --
  self time by where the function came from:
      131.7 ms  browser built-ins called from script
       60.3 ms  browser, outside script
       58.0 ms  package: svelte
       14.9 ms  garbage collection
        6.8 ms  package: tailwind-variants
        6.7 ms  package: tailwind-merge
        3.9 ms  slice: lib/filters.ts
        3.2 ms  slice: lib/view.ts
        3.0 ms  slice: components/GroupCard.svelte
        2.1 ms  slice: components/PieceColumn.svelte
        1.2 ms  slice: components/ui/button.svelte
        1.2 ms  slice: App.svelte
        1.1 ms  slice: components/Value.svelte
        1.0 ms  slice: components/ui/badge.svelte
        0.9 ms  slice: components/VerdictControls.svelte
        0.7 ms  slice: lib/session.svelte.ts
        0.6 ms  slice: components/TunedStat.svelte
  inclusive time under each component:
       70.9 ms  GroupCard
       45.6 ms  PieceColumn
        8.4 ms  Badge
        8.3 ms  Value
        7.5 ms  TunedStat
        6.5 ms  VerdictControls
        6.1 ms  Filters
        5.9 ms  StatStrip
        5.6 ms  App
        4.4 ms  Button
        3.7 ms  SessionPanel
-- 3. floor: the slice's own markup and stylesheet, no framework --
  captured markup: 1007504 bytes; assigned once the same report request has answered
  markup equal (comment anchors ignored)=True; every element's box equal=True
  unchanged: ready=245.5ms (+0.0); settled=264.3ms (+0.0); script=96.1 style=30.9 layout=76.9 task=245.6ms; report 48.8-61.4ms; first group=245.5ms; elements=13019; report requests=[1]; ready samples=[245.5, 242.9, 242.1, 250.8, 262.2]
  floor: ready=185.9ms (-59.6); settled=206.9ms (-57.4); script=1.1 style=32.8 layout=76.0 task=169.2ms; report 19.3-36.0ms; first group=185.9ms; elements=13019; report requests=[1]; ready samples=[181.4, 187.3, 181, 185.9, 210.4]
  production: ready=161.5ms (-84.0); settled=170.4ms (-93.9); script=22.5 style=16.2 layout=48.6 task=153.5ms; report 30.0-46.1ms; first group=161.5ms; elements=17138; report requests=[1]; ready samples=[163.3, 161.5, 139.4, 154.4, 171.9]
-- 4. ablations: one suspected cause removed, against the unchanged build --
  class-merge-once: a badge's class string is merged once per distinct input, not once per badge
  class-merge-once: app.js 144500 bytes sha256=5d8467ea4d01e99d; markup equal (comment anchors ignored)=True
  report-first: the report is requested before the page is mounted, not after
  report-first: app.js 144389 bytes sha256=ff0b1152095fbbc9; markup equal (comment anchors ignored)=True
  value-inline: no Value component
  value-inline: 7 uses of the Value component written out as their one span
  value-inline: app.js 145058 bytes sha256=ab7ef2065cd1ce4f; markup equal (comment anchors ignored)=True
  no-container-queries: 17 container rules and declarations resolved for a 1348 px group; markup equal (comment anchors ignored)=True; every element's box equal=True
  report-preload: a preload hint for /api/report in index.html; markup equal (comment anchors ignored)=True
  unchanged: ready=261.7ms (+0.0); settled=284.8ms (+0.0); script=101.6 style=32.6 layout=83.3 task=264.6ms; report 51.9-66.5ms; first group=261.8ms; elements=13019; report requests=[1]; ready samples=[282.2, 254.4, 264.1, 254.1, 261.7]
  class-merge-once: ready=250.3ms (-11.4); settled=270.2ms (-14.6); script=95.3 style=31.3 layout=82.3 task=251.6ms; report 50.2-62.9ms; first group=250.3ms; elements=13019; report requests=[1]; ready samples=[293.5, 245.6, 250.3, 242, 277]
  report-first: ready=252.4ms (-9.3); settled=271.2ms (-13.6); script=97.7 style=31.2 layout=78.7 task=250.2ms; report 46.1-65.7ms; first group=252.5ms; elements=13019; report requests=[1]; ready samples=[252.4, 246, 256.1, 242.6, 270.3]
  value-inline: ready=246.1ms (-15.6); settled=265.7ms (-19.1); script=95.9 style=30.8 layout=77.1 task=245.6ms; report 50.3-63.9ms; first group=246.1ms; elements=13019; report requests=[1]; ready samples=[252.8, 243.1, 242.5, 246.1, 249.3]
  no-container-queries: ready=256.7ms (-5.0); settled=275.5ms (-9.3); script=99.0 style=22.2 layout=87.2 task=257.5ms; report 49.1-64.8ms; first group=256.7ms; elements=13019; report requests=[1]; ready samples=[256.8, 271, 242.7, 256.7, 246]
  report-preload: ready=266.8ms (+5.1); settled=285.9ms (+1.1); script=98.6 style=31.8 layout=77.2 task=255.3ms; report 9.6-27.2ms; first group=266.8ms; elements=13020; report requests=[1]; ready samples=[280, 258.4, 266.8, 273.3, 252]
  the floor again with stylesheet ablations, beside production. The two layout
  ablations change the page's geometry: they measure the grid, they are not candidates:
  floor: ready=182.7ms (+0.0); settled=200.2ms (+0.0); script=1.2 style=30.6 layout=76.0 task=169.5ms; report 19.5-36.4ms; first group=182.7ms; elements=13019; report requests=[1]; ready samples=[182.8, 182.7, 180.5, 193.6, 175.4]
  floor + no-container-queries: ready=183.3ms (+0.6); settled=200.6ms (+0.4); script=1.1 style=22.8 layout=78.5 task=160.1ms; report 21.5-37.1ms; first group=183.4ms; elements=13019; report requests=[1]; ready samples=[183, 173.9, 193.7, 194.8, 183.3]
  floor + comparison grid as blocks: ready=176.5ms (-6.2); settled=192.2ms (-8.0); script=1.2 style=30.5 layout=70.9 task=162.1ms; report 19.0-35.9ms; first group=176.5ms; elements=13019; report requests=[1]; ready samples=[170.6, 184.4, 176.5, 185.1, 169.6]
  floor + every grid as blocks: ready=161.2ms (-21.5); settled=176.8ms (-23.4); script=1.1 style=31.3 layout=57.4 task=145.7ms; report 18.7-36.2ms; first group=161.2ms; elements=13019; report requests=[1]; ready samples=[165.1, 161.2, 159.8, 160.4, 170.9]
  floor + no-container-queries + every grid as blocks: ready=163.3ms (-19.4); settled=178.4ms (-21.8); script=1.2 style=22.4 layout=58.8 task=141.6ms; report 19.8-35.6ms; first group=163.3ms; elements=13019; report requests=[1]; ready samples=[148.1, 164.9, 163.3, 210.5, 155.2]
  production: ready=161.9ms (-20.8); settled=170.1ms (-30.1); script=23.9 style=16.0 layout=47.7 task=151.7ms; report 28.6-42.8ms; first group=161.9ms; elements=17138; report requests=[1]; ready samples=[148, 152.1, 164.2, 164.2, 161.9]
RESULT: PASS
exit 0
```

### Run 2 (complete, before the layout ablations were added; production not intercepted)

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; viewport 1440x1000 light
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
-- 1. timeline, medians of 5 alternating fresh documents, ms from navigation start --
  slice: document=4.5; /spike/assets/app.css loaded=19.6; /spike/assets/app.js loaded=19.8
  slice: report request 49.8 to 61.5; first group in document=241.1; all groups in document=144.1; ready=241.1; next frame=254.2; settled=261.0
  slice: before the report arrived=61.5; report arrival to ready=179.6; counters to settled: script=92.7 style=30.2 layout=74.1 task=241.5; elements=13019
  production: document=4.3; /assets/review.css loaded=13.6; /assets/review_server.js loaded=16.6; /assets/review_ui.js loaded=16.0
  production: report request 28.5 to 41.6; first group in document=146.0; all groups in document=93.8; ready=146.0; next frame=152.2; settled=155.6
  production: before the report arrived=41.6; report arrival to ready=104.4; counters to settled: script=22.3 style=15.1 layout=45.6 task=141.8; elements=17138
-- 2. profile: unminified build of the same source, sampling every 200 us, medians of 5 fresh documents; proportions, not timings --
  self time by where the function came from:
      124.3 ms  browser built-ins called from script
       53.7 ms  browser, outside script
       52.8 ms  package: svelte
       11.0 ms  garbage collection
        7.5 ms  package: tailwind-variants
        5.6 ms  package: tailwind-merge
        3.9 ms  slice: lib/filters.ts
        2.6 ms  slice: components/PieceColumn.svelte
        2.5 ms  slice: lib/view.ts
        2.1 ms  slice: components/GroupCard.svelte
        1.2 ms  slice: components/ui/badge.svelte
        0.9 ms  slice: App.svelte
        0.8 ms  slice: components/Value.svelte
        0.6 ms  slice: lib/session.svelte.ts
        0.6 ms  slice: components/TunedStat.svelte
  inclusive time under each component:
       66.9 ms  GroupCard
       39.1 ms  PieceColumn
        9.7 ms  Badge
        7.4 ms  Value
        6.0 ms  Filters
        5.8 ms  VerdictControls
        5.1 ms  App
        4.9 ms  StatStrip
        4.3 ms  Button
        4.2 ms  TunedStat
        3.2 ms  SessionPanel
-- 3. floor: the slice's own markup and stylesheet, no framework --
  captured markup: 1007504 bytes; assigned once the same report request has answered
  markup equal (comment anchors ignored)=True; every element's box equal=True
  unchanged: ready=244.8ms (+0.0); settled=262.6ms (+0.0); script=95.0 style=30.4 layout=75.9 task=242.4ms; report 49.2-63.0ms; first group=244.8ms; elements=13019; report requests=[1]; ready samples=[243.1, 247.2, 236.1, 251.3, 244.8]
  floor: ready=179.8ms (-65.0); settled=196.9ms (-65.7); script=1.2 style=30.5 layout=73.6 task=163.4ms; report 20.0-35.7ms; first group=179.8ms; elements=13019; report requests=[1]; ready samples=[179.8, 189.9, 176.8, 186.3, 178.3]
  production: ready=150.9ms (-93.9); settled=164.4ms (-98.2); script=22.5 style=16.4 layout=45.4 task=146.3ms; report 28.4-42.7ms; first group=150.9ms; elements=17138; report requests=[1]; ready samples=[144.5, 155, 149.4, 157.5, 150.9]
-- 4. ablations: one suspected cause removed, against the unchanged build --
  class-merge-once: a badge's class string is merged once per distinct input, not once per badge
  class-merge-once: app.js 144500 bytes sha256=5d8467ea4d01e99d; markup equal (comment anchors ignored)=True
  report-first: the report is requested before the page is mounted, not after
  report-first: app.js 144389 bytes sha256=ff0b1152095fbbc9; markup equal (comment anchors ignored)=True
  value-inline: no Value component
  value-inline: 7 uses of the Value component written out as their one span
  value-inline: app.js 145058 bytes sha256=ab7ef2065cd1ce4f; markup equal (comment anchors ignored)=True
  no-container-queries: 17 container rules and declarations resolved for a 1348 px group; markup equal (comment anchors ignored)=True; every element's box equal=True
  report-preload: a preload hint for /api/report in index.html; markup equal (comment anchors ignored)=True
  unchanged: ready=247.2ms (+0.0); settled=264.6ms (+0.0); script=95.4 style=30.2 layout=78.2 task=243.7ms; report 48.7-62.1ms; first group=247.3ms; elements=13019; report requests=[1]; ready samples=[242.6, 244.5, 247.4, 247.2, 248.9]
  class-merge-once: ready=243.3ms (-3.9); settled=262.7ms (-1.9); script=93.5 style=30.7 layout=76.6 task=244.8ms; report 48.7-61.4ms; first group=243.4ms; elements=13019; report requests=[1]; ready samples=[239.4, 238.1, 248.9, 243.3, 247.8]
  report-first: ready=245.5ms (-1.7); settled=262.8ms (-1.8); script=94.7 style=29.9 layout=76.7 task=244.5ms; report 41.6-59.6ms; first group=245.5ms; elements=13019; report requests=[1]; ready samples=[248.2, 246.3, 242.8, 241.2, 245.5]
  value-inline: ready=246.0ms (-1.2); settled=265.4ms (+0.8); script=94.7 style=30.4 layout=75.9 task=239.6ms; report 50.4-63.6ms; first group=246.0ms; elements=13019; report requests=[1]; ready samples=[241.3, 251.4, 246, 247.6, 240.2]
  no-container-queries: ready=242.8ms (-4.4); settled=261.6ms (-3.0); script=95.7 style=21.9 layout=79.7 task=240.3ms; report 48.7-65.2ms; first group=242.8ms; elements=13019; report requests=[1]; ready samples=[232.5, 239.9, 250.5, 244.8, 242.8]
  report-preload: ready=248.1ms (+0.9); settled=265.8ms (+1.2); script=94.8 style=30.3 layout=75.4 task=240.3ms; report 8.6-23.3ms; first group=248.1ms; elements=13020; report requests=[1]; ready samples=[251.7, 263.4, 248.1, 244.9, 244.9]
  the floor again, with and without container queries, beside production:
  floor: ready=192.8ms (+0.0); settled=210.5ms (+0.0); script=1.1 style=30.4 layout=73.9 task=160.6ms; report 19.1-34.9ms; first group=192.8ms; elements=13019; report requests=[1]; ready samples=[192.8, 178.7, 203.1, 195.6, 179.7]
  floor + no-container-queries: ready=173.3ms (-19.5); settled=189.9ms (-20.6); script=1.1 style=21.8 layout=75.5 task=155.4ms; report 19.0-33.6ms; first group=173.4ms; elements=13019; report requests=[1]; ready samples=[173, 177.3, 173.3, 170.5, 175]
  production: ready=151.8ms (-41.0); settled=160.6ms (-49.9); script=22.5 style=15.3 layout=46.6 task=143.6ms; report 29.6-42.8ms; first group=151.8ms; elements=17138; report requests=[1]; ready samples=[151.8, 149.2, 193.7, 146.3, 155.4]
RESULT: PASS
exit 0
```

### Run 1 (stopped in part 4; production not intercepted)

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; viewport 1440x1000 light
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
-- 1. timeline, medians of 5 alternating fresh documents, ms from navigation start --
  slice: document=5.7; /spike/assets/app.css loaded=22.1; /spike/assets/app.js loaded=21.3
  slice: report request 53.0 to 66.0; first group in document=247.8; all groups in document=149.2; ready=247.7; next frame=258.9; settled=264.3
  slice: before the report arrived=66.0; report arrival to ready=181.7; counters to settled: script=97.4 style=31.3 layout=75.3 task=249.1; elements=13019
  production: document=4.3; /assets/review.css loaded=13.6; /assets/review_server.js loaded=15.5; /assets/review_ui.js loaded=14.4
  production: report request 28.8 to 41.8; first group in document=148.5; all groups in document=95.4; ready=148.5; next frame=153.6; settled=156.3
  production: before the report arrived=41.8; report arrival to ready=106.7; counters to settled: script=23.3 style=14.7 layout=46.4 task=142.1; elements=17138
-- 2. profile: unminified build of the same source, sampling every 200 us, medians of 5 fresh documents; proportions, not timings --
  self time by where the function came from:
      124.0 ms  browser built-ins called from script
       53.5 ms  package: svelte
       48.5 ms  browser, outside script
       12.8 ms  garbage collection
        7.0 ms  package: tailwind-variants
        5.5 ms  package: tailwind-merge
        4.1 ms  slice: lib/filters.ts
        3.3 ms  slice: lib/view.ts
        2.8 ms  slice: components/GroupCard.svelte
        2.0 ms  slice: components/PieceColumn.svelte
        1.2 ms  slice: components/ui/badge.svelte
        1.1 ms  slice: App.svelte
        1.0 ms  slice: components/Value.svelte
        0.9 ms  slice: lib/session.svelte.ts
        0.8 ms  slice: components/ui/button.svelte
        0.6 ms  slice: components/ui/cn.ts
        0.6 ms  slice: components/StatStrip.svelte
  inclusive time under each component:
       65.1 ms  GroupCard
       35.7 ms  PieceColumn
        8.9 ms  Badge
        5.6 ms  TunedStat
        5.5 ms  Filters
        5.4 ms  VerdictControls
        5.1 ms  App
        5.1 ms  Value
        4.8 ms  StatStrip
        3.7 ms  Button
        3.2 ms  SessionPanel
-- 3. floor: the slice's own markup and stylesheet, no framework --
  captured markup: 1007504 bytes; assigned once the same report request has answered
  markup equal (comment anchors ignored)=True; every element's box equal=True
  unchanged: ready=248.4ms (+0.0); settled=265.2ms (+0.0); script=95.8 style=30.1 layout=78.2 task=247.7ms; report 50.4-63.0ms; first group=248.4ms; elements=13019; report requests=[1]; ready samples=[251.5, 244.1, 237.3, 251.8, 248.4]
  floor: ready=180.1ms (-68.3); settled=197.9ms (-67.3); script=1.2 style=30.7 layout=73.6 task=164.7ms; report 19.6-35.4ms; first group=180.2ms; elements=13019; report requests=[1]; ready samples=[178.7, 187, 180.1, 181.3, 180.1]
  production: ready=155.3ms (-93.1); settled=162.8ms (-102.4); script=22.4 style=15.7 layout=47.7 task=147.2ms; report 28.2-40.4ms; first group=155.3ms; elements=17138; report requests=[1]; ready samples=[150.4, 156.2, 147.7, 155.3, 156.6]
-- 4. ablations: one suspected cause removed, against the unchanged build --
  class-merge-once: a badge's class string is merged once per distinct input, not once per badge
  class-merge-once: app.js 144500 bytes sha256=5d8467ea4d01e99d; markup equal (comment anchors ignored)=True
  report-first: the report is requested before the page is mounted, not after
  report-first: app.js 144389 bytes sha256=ff0b1152095fbbc9; markup equal (comment anchors ignored)=True
  value-inline: no Value component
  value-inline: 7 uses of the Value component written out as their one span
  value-inline: app.js 145058 bytes sha256=ab7ef2065cd1ce4f; markup equal (comment anchors ignored)=True
FAIL: a container rule was not resolved
exit 1
```

## 5. The one change tried, and dropped

The `class-merge-once` ablation of section 4, applied to the real source: a
badge's class string is merged once per distinct input instead of once per
badge. The rendered markup is identical (section 4, "markup equal"). The type
check and the 43 unit tests passed with it, and the build was 144,500 bytes.

The change, as `git diff spikes/issue-213/frontend` printed it before it was
reverted. It was never committed:

```diff
diff --git a/spikes/issue-213/frontend/src/components/ui/badge.svelte b/spikes/issue-213/frontend/src/components/ui/badge.svelte
index bd78f5f..4b76254 100644
--- a/spikes/issue-213/frontend/src/components/ui/badge.svelte
+++ b/spikes/issue-213/frontend/src/components/ui/badge.svelte
@@ -4,6 +4,7 @@
   // removed, and the fixed height and nowrap are overridden where it is
   // used, because a status must wrap at 390 px and never be clipped.
   import { type VariantProps, tv } from 'tailwind-variants';
+  import { cn } from './cn';

   export const badgeVariants = tv({
     base: 'h-5 gap-1 rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium transition-all group/badge inline-flex w-fit shrink-0 items-center justify-center overflow-hidden whitespace-nowrap',
@@ -18,12 +19,20 @@
   });

   export type BadgeVariant = VariantProps<typeof badgeVariants>['variant'];
+  const resolved = new Map<string, string>();
+  export const badgeClass = (variant: BadgeVariant, extra: unknown): string => {
+    const key = `${variant}\n${String(extra ?? '')}`;
+    let value = resolved.get(key);
+    if (value === undefined) {
+      value = cn(badgeVariants({ variant }), 'h-auto shrink whitespace-normal transition-none', extra as string);
+      resolved.set(key, value);
+    }
+    return value;
+  };
 </script>

 <script lang="ts">
   import type { HTMLAttributes } from 'svelte/elements';
-  import { cn } from './cn';
-
   let {
     class: className,
     variant = 'default',
@@ -34,7 +43,7 @@

 <span
   data-slot="badge"
-  class={cn(badgeVariants({ variant }), 'h-auto shrink whitespace-normal transition-none', className)}
+  class={badgeClass(variant, className)}
   {...rest}
 >
   {@render children?.()}
```

The gate on that build, invocation 3 of 5. Its `build served` line says
`same bytes as the issue-210 build=False`, as it should:

```bash
.venv/bin/python spikes/issue-213/proof_gate.py
```

```text
build served: app.js sha256=5d8467ea4d01e99db68d0fe69e565fd47f440b01a414d311e868703e6c16f502 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=False
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=236.2ms; navigationFrame=250.0ms; dom=7.3ms; frame=7.6ms; navigationSettled=262.9ms; keySettled=40.0ms; ackSettled=22.8ms; responseEnd=51.0ms; elements=13019; action=Approve
run 1 production: navigation=147.3ms; navigationFrame=153.0ms; dom=10.2ms; frame=14.8ms; navigationSettled=164.0ms; keySettled=55.3ms; ackSettled=31.5ms; responseEnd=38.5ms; elements=17138; action=Veto
run 2 production: navigation=144.6ms; navigationFrame=151.4ms; dom=9.7ms; frame=13.7ms; navigationSettled=161.1ms; keySettled=54.7ms; ackSettled=30.6ms; responseEnd=38.7ms; elements=17138; action=Approve
run 2 slice: navigation=226.4ms; navigationFrame=239.9ms; dom=11.0ms; frame=11.4ms; navigationSettled=252.2ms; keySettled=53.2ms; ackSettled=27.3ms; responseEnd=52.0ms; elements=13019; action=Veto
run 3 slice: navigation=238.5ms; navigationFrame=251.3ms; dom=13.7ms; frame=14.1ms; navigationSettled=264.6ms; keySettled=54.8ms; ackSettled=29.6ms; responseEnd=53.0ms; elements=13019; action=Approve
run 3 production: navigation=153.4ms; navigationFrame=161.6ms; dom=9.8ms; frame=19.5ms; navigationSettled=164.8ms; keySettled=45.3ms; ackSettled=21.1ms; responseEnd=36.9ms; elements=17138; action=Veto
run 4 production: navigation=148.5ms; navigationFrame=154.1ms; dom=9.8ms; frame=20.1ms; navigationSettled=156.8ms; keySettled=45.5ms; ackSettled=22.8ms; responseEnd=38.9ms; elements=17138; action=Approve
run 4 slice: navigation=230.6ms; navigationFrame=244.8ms; dom=6.6ms; frame=12.0ms; navigationSettled=256.3ms; keySettled=52.6ms; ackSettled=29.6ms; responseEnd=49.5ms; elements=13019; action=Veto
run 5 slice: navigation=238.6ms; navigationFrame=254.2ms; dom=6.4ms; frame=12.7ms; navigationSettled=266.0ms; keySettled=53.6ms; ackSettled=29.9ms; responseEnd=52.9ms; elements=13019; action=Approve
run 5 production: navigation=148.8ms; navigationFrame=154.2ms; dom=10.3ms; frame=14.5ms; navigationSettled=163.9ms; keySettled=56.3ms; ackSettled=31.6ms; responseEnd=37.6ms; elements=17138; action=Veto
A1 navigation to all groups: slice=236.2ms production=148.5ms gap=+87.7ms FAIL
A2 navigation to next frame: slice=250.0ms production=154.1ms gap=+95.9ms FAIL
A3 acknowledgement to DOM: slice=7.3ms production=9.8ms gap=-2.5ms PASS
A4 acknowledgement to next frame: slice=12.0ms production=14.8ms gap=-2.8ms PASS
B1 navigation to settled: slice=262.9ms production=163.9ms gap=+99.0ms FAIL
B2 key press to settled: slice=53.2ms production=54.7ms gap=-1.5ms PASS
B3 acknowledgement to settled: slice=29.6ms production=30.6ms gap=-1.0ms PASS
slice navigation CDP medians: ScriptDuration=93.9ms; RecalcStyleDuration=31.4ms; LayoutDuration=76.0ms; TaskDuration=263.8ms
slice verdict CDP medians: ScriptDuration=8.8ms; RecalcStyleDuration=1.1ms; LayoutDuration=3.8ms; TaskDuration=37.7ms
production navigation CDP medians: ScriptDuration=23.9ms; RecalcStyleDuration=15.9ms; LayoutDuration=45.5ms; TaskDuration=152.5ms
production verdict CDP medians: ScriptDuration=3.5ms; RecalcStyleDuration=3.3ms; LayoutDuration=8.9ms; TaskDuration=40.4ms
M4 one-class: buttons=1; style median=0.1ms; samples=[0.2, 0.1, 0.1, 0.1, 0.1, 0.1]
M4 all-class: buttons=435; style median=2.4ms; samples=[2.3, 2.3, 2.5, 2.6, 2.4, 3.7]
M4 all-aria: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M4 all-both: buttons=435; style median=2.5ms; samples=[3.0, 2.5, 2.6, 2.9, 2.3, 2.4]
M4 all-disabled: buttons=435; style median=3.3ms; samples=[4.1, 3.2, 3.2, 3.2, 3.3, 3.3]
M4 all-unused: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M5 warm Node medians (50): bytes=743025; JSON.parse=1.268ms; projection=0.339ms; value-stable projection=0.821ms
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: B1 navigation to settled
RESULT: FAIL
exit 1
```

A1 on the slice is 236.2 ms, between the two baseline invocations (229.2 and
240.8 ms), and A2 and B1 are likewise inside the baseline range. B2 and B3
did move by more than the baseline spread, from fail to pass: B2 from +8.2
and +2.0 to -1.5, B3 from +9.1 and +7.5 to -1.0. That movement is not
credited to the change, because the two final invocations in section 6, on
the unchanged source, show the same movement without it (B2 -6.9 and -2.6;
B3 -2.5 and +0.6). The change was taken out with
`git checkout -- spikes/issue-213/frontend` and the slice rebuilt
(section 1).

## 6. The two final gate invocations

On the unchanged source, back to back. Invocation 4 of 5:

```bash
.venv/bin/python spikes/issue-213/proof_gate.py
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=239.1ms; navigationFrame=251.8ms; dom=6.8ms; frame=7.2ms; navigationSettled=262.8ms; keySettled=39.4ms; ackSettled=23.5ms; responseEnd=53.6ms; elements=13019; action=Approve
run 1 production: navigation=146.5ms; navigationFrame=152.2ms; dom=11.8ms; frame=12.1ms; navigationSettled=154.9ms; keySettled=59.7ms; ackSettled=34.1ms; responseEnd=29.0ms; elements=17138; action=Veto
run 2 production: navigation=146.7ms; navigationFrame=153.0ms; dom=9.4ms; frame=14.9ms; navigationSettled=163.2ms; keySettled=56.1ms; ackSettled=32.0ms; responseEnd=39.1ms; elements=17138; action=Approve
run 2 slice: navigation=231.9ms; navigationFrame=245.3ms; dom=6.5ms; frame=12.2ms; navigationSettled=257.1ms; keySettled=52.9ms; ackSettled=29.5ms; responseEnd=48.7ms; elements=13019; action=Veto
run 3 slice: navigation=238.4ms; navigationFrame=253.4ms; dom=7.1ms; frame=12.4ms; navigationSettled=265.2ms; keySettled=55.1ms; ackSettled=29.8ms; responseEnd=54.1ms; elements=13019; action=Approve
run 3 production: navigation=153.0ms; navigationFrame=159.5ms; dom=9.8ms; frame=11.4ms; navigationSettled=170.0ms; keySettled=55.2ms; ackSettled=28.6ms; responseEnd=41.2ms; elements=17138; action=Veto
run 4 production: navigation=143.5ms; navigationFrame=149.2ms; dom=9.3ms; frame=21.0ms; navigationSettled=151.9ms; keySettled=48.3ms; ackSettled=23.7ms; responseEnd=28.9ms; elements=17138; action=Approve
run 4 slice: navigation=231.5ms; navigationFrame=244.0ms; dom=6.8ms; frame=12.5ms; navigationSettled=254.6ms; keySettled=49.2ms; ackSettled=31.1ms; responseEnd=53.7ms; elements=13019; action=Veto
run 5 slice: navigation=249.2ms; navigationFrame=264.8ms; dom=7.5ms; frame=8.1ms; navigationSettled=270.7ms; keySettled=48.3ms; ackSettled=26.1ms; responseEnd=56.4ms; elements=13019; action=Approve
run 5 production: navigation=152.5ms; navigationFrame=158.2ms; dom=9.8ms; frame=16.6ms; navigationSettled=169.1ms; keySettled=58.0ms; ackSettled=33.7ms; responseEnd=37.5ms; elements=17138; action=Veto
A1 navigation to all groups: slice=238.4ms production=146.7ms gap=+91.7ms FAIL
A2 navigation to next frame: slice=251.8ms production=153.0ms gap=+98.8ms FAIL
A3 acknowledgement to DOM: slice=6.8ms production=9.8ms gap=-3.0ms PASS
A4 acknowledgement to next frame: slice=12.2ms production=14.9ms gap=-2.7ms PASS
B1 navigation to settled: slice=262.8ms production=163.2ms gap=+99.6ms FAIL
B2 key press to settled: slice=49.2ms production=56.1ms gap=-6.9ms PASS
B3 acknowledgement to settled: slice=29.5ms production=32.0ms gap=-2.5ms PASS
slice navigation CDP medians: ScriptDuration=97.2ms; RecalcStyleDuration=32.3ms; LayoutDuration=76.7ms; TaskDuration=259.5ms
slice verdict CDP medians: ScriptDuration=7.4ms; RecalcStyleDuration=1.2ms; LayoutDuration=4.0ms; TaskDuration=34.1ms
production navigation CDP medians: ScriptDuration=23.0ms; RecalcStyleDuration=15.5ms; LayoutDuration=47.1ms; TaskDuration=151.8ms
production verdict CDP medians: ScriptDuration=3.5ms; RecalcStyleDuration=3.3ms; LayoutDuration=9.3ms; TaskDuration=41.9ms
M4 one-class: buttons=1; style median=0.1ms; samples=[0.2, 0.1, 0.0, 0.1, 0.1, 0.1]
M4 all-class: buttons=435; style median=2.7ms; samples=[2.3, 2.2, 2.6, 3.1, 3.4, 2.8]
M4 all-aria: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M4 all-both: buttons=435; style median=2.6ms; samples=[2.5, 2.3, 2.8, 2.6, 2.3, 3.1]
M4 all-disabled: buttons=435; style median=3.3ms; samples=[4.0, 3.3, 3.2, 3.2, 3.4, 3.3]
M4 all-unused: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M5 warm Node medians (50): bytes=743025; JSON.parse=1.287ms; projection=0.386ms; value-stable projection=0.810ms
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: B1 navigation to settled
RESULT: FAIL
exit 1
```

Invocation 5 of 5:

```bash
.venv/bin/python spikes/issue-213/proof_gate.py
```

```text
build served: app.js sha256=5b5c2b87d268f942077e053f0e341db1b32e243dc90d65aa2faa600831fcb981 app.css sha256=95368d83cc4ea710d43b41100ab808ee99315294e0ab81cb74ffe8ce087064e0; is the issue-213 build=True; same bytes as the issue-210 build=True
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=243.3ms; navigationFrame=260.4ms; dom=8.2ms; frame=8.4ms; navigationSettled=267.1ms; keySettled=39.7ms; ackSettled=21.3ms; responseEnd=55.6ms; elements=13019; action=Approve
run 1 production: navigation=148.2ms; navigationFrame=155.1ms; dom=9.0ms; frame=15.3ms; navigationSettled=157.7ms; keySettled=55.9ms; ackSettled=30.5ms; responseEnd=37.9ms; elements=17138; action=Veto
run 2 production: navigation=143.5ms; navigationFrame=150.4ms; dom=10.1ms; frame=19.3ms; navigationSettled=161.4ms; keySettled=43.2ms; ackSettled=21.1ms; responseEnd=36.4ms; elements=17138; action=Approve
run 2 slice: navigation=230.5ms; navigationFrame=243.7ms; dom=6.8ms; frame=12.7ms; navigationSettled=256.0ms; keySettled=53.6ms; ackSettled=29.8ms; responseEnd=48.5ms; elements=13019; action=Veto
run 3 slice: navigation=233.1ms; navigationFrame=247.2ms; dom=8.4ms; frame=12.1ms; navigationSettled=259.7ms; keySettled=46.7ms; ackSettled=29.7ms; responseEnd=55.6ms; elements=13019; action=Approve
run 3 production: navigation=150.7ms; navigationFrame=156.6ms; dom=10.1ms; frame=14.8ms; navigationSettled=166.3ms; keySettled=56.2ms; ackSettled=31.7ms; responseEnd=39.0ms; elements=17138; action=Veto
run 4 production: navigation=161.4ms; navigationFrame=167.2ms; dom=9.9ms; frame=11.7ms; navigationSettled=177.0ms; keySettled=54.6ms; ackSettled=28.8ms; responseEnd=37.5ms; elements=17138; action=Approve
run 4 slice: navigation=235.1ms; navigationFrame=247.3ms; dom=6.8ms; frame=12.4ms; navigationSettled=258.4ms; keySettled=52.3ms; ackSettled=29.0ms; responseEnd=51.3ms; elements=13019; action=Veto
run 5 slice: navigation=241.9ms; navigationFrame=256.3ms; dom=7.4ms; frame=12.0ms; navigationSettled=268.6ms; keySettled=52.0ms; ackSettled=29.4ms; responseEnd=51.7ms; elements=13019; action=Approve
run 5 production: navigation=155.9ms; navigationFrame=161.7ms; dom=11.6ms; frame=21.3ms; navigationSettled=172.5ms; keySettled=50.5ms; ackSettled=23.3ms; responseEnd=37.8ms; elements=17138; action=Veto
A1 navigation to all groups: slice=235.1ms production=150.7ms gap=+84.4ms FAIL
A2 navigation to next frame: slice=247.3ms production=156.6ms gap=+90.7ms FAIL
A3 acknowledgement to DOM: slice=7.4ms production=10.1ms gap=-2.7ms PASS
A4 acknowledgement to next frame: slice=12.1ms production=15.3ms gap=-3.2ms PASS
B1 navigation to settled: slice=259.7ms production=166.3ms gap=+93.4ms FAIL
B2 key press to settled: slice=52.0ms production=54.6ms gap=-2.6ms PASS
B3 acknowledgement to settled: slice=29.4ms production=28.8ms gap=+0.6ms FAIL
slice navigation CDP medians: ScriptDuration=97.6ms; RecalcStyleDuration=32.0ms; LayoutDuration=76.4ms; TaskDuration=267.8ms
slice verdict CDP medians: ScriptDuration=7.6ms; RecalcStyleDuration=1.2ms; LayoutDuration=4.2ms; TaskDuration=35.3ms
production navigation CDP medians: ScriptDuration=23.5ms; RecalcStyleDuration=16.4ms; LayoutDuration=46.9ms; TaskDuration=159.7ms
production verdict CDP medians: ScriptDuration=3.6ms; RecalcStyleDuration=3.3ms; LayoutDuration=9.2ms; TaskDuration=41.7ms
M4 one-class: buttons=1; style median=0.1ms; samples=[0.2, 0.2, 0.1, 0.1, 0.1, 0.1]
M4 all-class: buttons=435; style median=2.4ms; samples=[2.3, 2.3, 2.5, 2.4, 3.5, 2.6]
M4 all-aria: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M4 all-both: buttons=435; style median=2.4ms; samples=[2.5, 2.5, 2.6, 2.3, 2.4, 2.4]
M4 all-disabled: buttons=435; style median=3.4ms; samples=[3.5, 5.0, 3.2, 3.2, 3.8, 3.2]
M4 all-unused: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
M5 warm Node medians (50): bytes=743025; JSON.parse=1.335ms; projection=0.385ms; value-stable projection=0.876ms
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: B1 navigation to settled
FAIL: B3 acknowledgement to settled
RESULT: FAIL
exit 1
```

## 7. The gate proof against #209's

`spikes/issue-213/proof_gate.py` at the copy commit is blob
`a77c21f3f2826c735c49463f6ef4d305604e82da`, #209's file. This is everything
that differs now: the verdict action is added to each run's line.

```bash
git diff a77c21f3f2826c735c49463f6ef4d305604e82da HEAD:spikes/issue-213/proof_gate.py
```

```diff
diff --git a/a77c21f3f2826c735c49463f6ef4d305604e82da b/a70f96cc2d12c5e13ca9e61abea8146018cf3f28
index a77c21f..a70f96c 100644
--- a/a77c21f3f2826c735c49463f6ef4d305604e82da
+++ b/a70f96cc2d12c5e13ca9e61abea8146018cf3f28
@@ -132,6 +132,7 @@ def sample(context: Any, live: Any, name: str, group: dict, member: dict) -> dic
       viewportJump: Math.abs(__scaleButton.getBoundingClientRect().top - __scaleTop),
     })"""))
     result["verdictMetrics"] = delta(before, after)
+    result["action"] = action
     assert result["groups"] == 74
     if name == "slice":
         assert result["same"] and result["viewportJump"] <= 1
@@ -228,7 +229,8 @@ def main() -> int:
                 measured[name].append(result)
                 print(f"run {run + 1} {name}: " + "; ".join(
                     f"{key}={result[key]:.1f}ms" for _, key in COMPARISONS
-                ) + f"; responseEnd={result['responseEnd']:.1f}ms; elements={result['nodes']}")
+                ) + f"; responseEnd={result['responseEnd']:.1f}ms; elements={result['nodes']}"
+                      f"; action={result['action']}")
         for label, key in COMPARISONS:
             mine = median(s[key] for s in measured["slice"])
             theirs = median(s[key] for s in measured["production"])
```

## 8. Repository checks

```bash
.venv/bin/ruff check src tests scripts
```

```text
All checks passed!
exit 0
```

```bash
.venv/bin/ruff check spikes/issue-213
```

```text
All checks passed!
exit 0
```

```bash
.venv/bin/pytest -q
```

```text
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
........................................................................ [ 21%]
........................................................................ [ 26%]
........................................................................ [ 32%]
........................................................................ [ 37%]
........................................................................ [ 42%]
........................................................................ [ 48%]
........................................................................ [ 53%]
........................................................................ [ 59%]
........................................................................ [ 64%]
........................................................................ [ 69%]
........................................................................ [ 75%]
........................................................................ [ 80%]
........................................................................ [ 85%]
........................................................................ [ 91%]
........................................................................ [ 96%]
..............................................                           [100%]
1342 passed in 31.99s
exit 0
```

```bash
VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py
```

```text
................                                                         [100%]
16 passed, 3 deselected in 12.06s
exit 0
```
