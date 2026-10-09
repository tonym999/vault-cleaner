# Issue #209 — presentation performance evidence

Only the tracked sanitised armor fixture and synthetic tracked fixtures are read.
No personal export is read; neither baseline source nor fixture is edited.
These are complete stdout/stderr captures in process emission order; timings vary.
Gate invocations are numbered in order, including the incomplete first invocation.
Baseline and kept step states are preserved in commits (listed in the worklog).
Run a historical step command in a disposable checkout at its recorded step SHA,
after the build commands in the spike README. Nothing here ships.

## Invocation 1 — incomplete instrument bootstrap

The first attempted gate invocation ran on the verbatim copy, printed one slice
sample, then incorrectly applied the slice's focus invariant to production.
Production loses focus when disabled; unchanged S15 applies that invariant only to
the slice. The proof was corrected before invocation 2. This invocation is counted,
not a complete passing/failing comparison. Its original output is retained below;
the corrected proof intentionally cannot reproduce this instrumentation error.

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=199.7ms; navigationFrame=211.1ms; dom=29.1ms; frame=34.5ms; navigationSettled=221.6ms; keySettled=617.6ms; ackSettled=423.8ms; responseEnd=40.4ms; elements=13143
Traceback (most recent call last):
  File "/home/raver/projects/personal/vault-cleaner/spikes/issue-209/proof_gate.py", line 220, in <module>
    sys.exit(main())
             ~~~~^^
  File "/home/raver/projects/personal/vault-cleaner/spikes/issue-209/proof_gate.py", line 195, in main
    result = sample(context, live, name, group, member)
  File "/home/raver/projects/personal/vault-cleaner/spikes/issue-209/proof_gate.py", line 133, in sample
    assert result["groups"] == 74 and result["same"] and result["viewportJump"] <= 1
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError
```

## Step 0 — invocation 2, verbatim copy baseline

```bash
.venv/bin/python spikes/issue-209/proof_gate.py
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=201.3ms; navigationFrame=212.6ms; dom=39.0ms; frame=44.8ms; navigationSettled=216.3ms; keySettled=588.3ms; ackSettled=478.8ms; responseEnd=36.6ms; elements=13143
run 1 production: navigation=176.0ms; navigationFrame=181.7ms; dom=9.6ms; frame=16.3ms; navigationSettled=184.2ms; keySettled=57.2ms; ackSettled=32.8ms; responseEnd=63.1ms; elements=17138
run 2 production: navigation=140.5ms; navigationFrame=145.7ms; dom=9.8ms; frame=18.3ms; navigationSettled=155.1ms; keySettled=42.3ms; ackSettled=19.9ms; responseEnd=35.1ms; elements=17138
run 2 slice: navigation=193.0ms; navigationFrame=205.2ms; dom=28.8ms; frame=34.7ms; navigationSettled=208.6ms; keySettled=265.6ms; ackSettled=140.2ms; responseEnd=31.4ms; elements=13143
run 3 slice: navigation=203.2ms; navigationFrame=222.5ms; dom=26.8ms; frame=33.0ms; navigationSettled=229.2ms; keySettled=421.4ms; ackSettled=329.3ms; responseEnd=32.8ms; elements=13143
run 3 production: navigation=154.1ms; navigationFrame=160.0ms; dom=9.2ms; frame=18.3ms; navigationSettled=169.9ms; keySettled=42.6ms; ackSettled=19.8ms; responseEnd=40.5ms; elements=17138
run 4 production: navigation=158.2ms; navigationFrame=164.8ms; dom=8.8ms; frame=17.7ms; navigationSettled=168.6ms; keySettled=44.1ms; ackSettled=19.2ms; responseEnd=39.0ms; elements=17138
run 4 slice: navigation=198.1ms; navigationFrame=210.3ms; dom=27.1ms; frame=33.9ms; navigationSettled=213.7ms; keySettled=259.8ms; ackSettled=176.0ms; responseEnd=32.0ms; elements=13143
run 5 slice: navigation=194.1ms; navigationFrame=205.3ms; dom=22.0ms; frame=27.7ms; navigationSettled=209.0ms; keySettled=235.7ms; ackSettled=114.8ms; responseEnd=32.5ms; elements=13143
run 5 production: navigation=158.2ms; navigationFrame=163.5ms; dom=10.0ms; frame=12.6ms; navigationSettled=166.5ms; keySettled=56.0ms; ackSettled=30.9ms; responseEnd=40.9ms; elements=17138
A1 navigation to all groups: slice=198.1ms production=158.2ms gap=+39.9ms FAIL
A2 navigation to next frame: slice=210.3ms production=163.5ms gap=+46.8ms FAIL
A3 acknowledgement to DOM: slice=27.1ms production=9.6ms gap=+17.5ms FAIL
A4 acknowledgement to next frame: slice=33.9ms production=17.7ms gap=+16.2ms FAIL
B1 navigation to settled: slice=213.7ms production=168.6ms gap=+45.1ms FAIL
B2 key press to settled: slice=265.6ms production=44.1ms gap=+221.5ms FAIL
B3 acknowledgement to settled: slice=176.0ms production=19.9ms gap=+156.1ms FAIL
slice navigation CDP medians: ScriptDuration=62.5ms; RecalcStyleDuration=32.3ms; LayoutDuration=67.7ms; TaskDuration=207.4ms
slice verdict CDP medians: ScriptDuration=29.4ms; RecalcStyleDuration=138.7ms; LayoutDuration=12.2ms; TaskDuration=283.8ms
production navigation CDP medians: ScriptDuration=23.4ms; RecalcStyleDuration=17.4ms; LayoutDuration=48.3ms; TaskDuration=153.3ms
production verdict CDP medians: ScriptDuration=3.4ms; RecalcStyleDuration=3.1ms; LayoutDuration=9.4ms; TaskDuration=45.0ms
M4 one-class: buttons=1; style median=0.4ms; samples=[0.6, 0.5, 0.5, 0.3, 0.3, 0.3]
M4 all-class: buttons=435; style median=213.0ms; samples=[53.4, 238.8, 158.1, 265.0, 187.2, 276.7]
M4 all-aria: buttons=435; style median=91.9ms; samples=[59.6, 96.4, 87.5, 168.3, 139.0, 37.8]
M4 all-both: buttons=435; style median=61.5ms; samples=[57.1, 67.7, 54.2, 65.9, 50.2, 106.3]
M4 all-disabled: buttons=435; style median=124.4ms; samples=[94.3, 78.4, 83.1, 154.4, 275.6, 277.9]
M4 all-unused: buttons=435; style median=0.0ms; samples=[52.0, 0.0, 0.0, 0.0, 0.0, 0.0]
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: A3 acknowledgement to DOM
FAIL: A4 acknowledgement to next frame
FAIL: B1 navigation to settled
FAIL: B2 key press to settled
FAIL: B3 acknowledgement to settled
RESULT: FAIL
```

## Stylesheet isolation — all tried families, baseline assets

The earlier six developmental diagnostic invocations narrowed the cause. Invocation
7 failed before importing the harness after import sorting; invocation 8 below is
the final fixed diagnostic, preserving every probe in one reproducible command.
Removing transitions is a rejected diagnostic: it changes intermediate presentation.
None of the CSSOM diagnostic alterations is retained in the frontend.

```bash
.venv/bin/python spikes/issue-209/proof_styles.py
```

```text
baseline #206 assets; diagnostic CSSOM changes only; six flips per fixed family
unchanged: removed=0; style median=59.5ms; samples=[50.3, 52.1, 67.0, 70.0, 41.8, 67.0]
join-scope: removed=1; style median=61.1ms; samples=[51.5, 71.2, 49.4, 53.1, 69.7, 69.1]
isolated rule: @scope (.join) {
  :scope > :where(:focus, :has(:focus)) { z-index: 2; }
  @media (hover: hover) {
  :scope > :where(.btn:hover, :has(.btn:hover)) { z-index: 1; }
}
  :scope :where(:scope > :first-child) { --join-ss: var(--radius-field); --join-se: calc(var(--radius-field) * var(--join-v)); --join-es: calc(var(--radius-field) * var(--join-h)); --join-ee: 0; }
  :scope :where(:scope > :last-child) { --join-ss: 0; --join-se: calc(var(--radius-field) * var(--join-h)); --join-es: calc(var(--radius-field) * var(--join-v)); --join-ee: var(--radius-field); }
  :scope :where(:scope > :only-child) { --join-ss: var(--radius-field); --join-se: var(--radius-field); --join-es: var(--radius-field); --join-ee: var(--radius-field); }
  :scope :where(:scope > :not(:first-child)) { --join-ml: calc(var(--border,1px) * -1 * var(--join-h)); --join-mt: calc(var(--border,1px) * -1 * var(--join-v)); }
}
has: removed=38; style median=55.6ms; samples=[54.1, 71.6, 49.0, 57.2, 70.5, 43.8]
disabled: removed=7; style median=5.6ms; samples=[5.3, 5.5, 5.3, 5.9, 5.7, 5.7]
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]):not(.btn-link, .btn-ghost) { background-color: color-mix(in oklab, var(--color-base-content) 10%, transparent); }
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]):not(.btn-link, .btn-ghost) { background-color: var(--color-base-content); }
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]) { --btn-bg: #0000; --btn-border: #0000; --btn-inset: 0 0 0 0 oklch(0% 0 0/0); --btn-shadow: 0 0 0 0 oklch(0% 0 0/0); background-image: none; }
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]) { color: color-mix(in oklch, var(--color-base-content) 20%, #0000); }
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]) { pointer-events: none; color: var(--color-base-content); }
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]):not(.btn-link, .btn-ghost) { background-color: color-mix(in oklab, var(--color-base-content) 10%, transparent); }
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]) { color: color-mix(in oklch, var(--color-base-content) 20%, #0000); }
join-and-disabled: removed=8; style median=4.1ms; samples=[4.7, 4.2, 3.9, 4.2, 4.0, 3.9]
root-has: removed=3; style median=71.6ms; samples=[54.4, 69.1, 74.1, 63.3, 84.4, 78.2]
disabled-direct: removed=1; style median=58.9ms; samples=[54.6, 63.1, 42.1, 53.2, 74.7, 81.3]
isolated rule: .btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"]) { --btn-bg: #0000; --btn-border: #0000; --btn-inset: 0 0 0 0 oklch(0% 0 0/0); --btn-shadow: 0 0 0 0 oklch(0% 0 0/0); background-image: none; }
disabled-color: removed=3; style median=73.1ms; samples=[53.7, 73.2, 54.9, 75.9, 91.0, 73.0]
disabled-background: removed=3; style median=71.4ms; samples=[55.6, 39.7, 68.4, 95.6, 74.3, 75.8]
simple-selector: removed=7; style median=70.0ms; samples=[53.8, 40.6, 76.1, 100.6, 63.9, 78.7]
no-transitions: removed=0; style median=5.5ms; samples=[5.2, 6.3, 5.4, 6.0, 5.3, 5.6]
RESULT: PASS
```

## Step 1 — invocation 3, value-stable projection

```bash
.venv/bin/python spikes/issue-209/proof_gate.py
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=208.9ms; navigationFrame=223.2ms; dom=7.7ms; frame=13.1ms; navigationSettled=228.0ms; keySettled=210.4ms; ackSettled=120.3ms; responseEnd=34.3ms; elements=13143
run 1 production: navigation=173.8ms; navigationFrame=181.8ms; dom=10.1ms; frame=14.4ms; navigationSettled=194.0ms; keySettled=55.4ms; ackSettled=31.1ms; responseEnd=37.2ms; elements=17138
run 2 production: navigation=142.9ms; navigationFrame=149.1ms; dom=9.7ms; frame=18.0ms; navigationSettled=161.2ms; keySettled=42.8ms; ackSettled=19.8ms; responseEnd=31.0ms; elements=17138
run 2 slice: navigation=197.9ms; navigationFrame=210.5ms; dom=14.2ms; frame=20.4ms; navigationSettled=213.9ms; keySettled=252.6ms; ackSettled=163.0ms; responseEnd=34.1ms; elements=13143
run 3 slice: navigation=193.8ms; navigationFrame=204.7ms; dom=17.4ms; frame=22.6ms; navigationSettled=208.0ms; keySettled=227.5ms; ackSettled=130.0ms; responseEnd=33.2ms; elements=13143
run 3 production: navigation=148.2ms; navigationFrame=153.3ms; dom=10.3ms; frame=15.2ms; navigationSettled=162.1ms; keySettled=57.2ms; ackSettled=31.8ms; responseEnd=41.8ms; elements=17138
run 4 production: navigation=150.6ms; navigationFrame=157.4ms; dom=10.4ms; frame=16.6ms; navigationSettled=160.2ms; keySettled=56.6ms; ackSettled=32.4ms; responseEnd=33.5ms; elements=17138
run 4 slice: navigation=210.1ms; navigationFrame=225.1ms; dom=18.8ms; frame=23.9ms; navigationSettled=228.9ms; keySettled=251.9ms; ackSettled=101.4ms; responseEnd=41.6ms; elements=13143
run 5 slice: navigation=193.2ms; navigationFrame=205.1ms; dom=21.3ms; frame=25.7ms; navigationSettled=208.9ms; keySettled=223.2ms; ackSettled=111.4ms; responseEnd=33.3ms; elements=13143
run 5 production: navigation=146.8ms; navigationFrame=152.4ms; dom=10.3ms; frame=19.2ms; navigationSettled=162.4ms; keySettled=43.9ms; ackSettled=21.0ms; responseEnd=39.5ms; elements=17138
A1 navigation to all groups: slice=197.9ms production=148.2ms gap=+49.7ms FAIL
A2 navigation to next frame: slice=210.5ms production=153.3ms gap=+57.2ms FAIL
A3 acknowledgement to DOM: slice=17.4ms production=10.3ms gap=+7.1ms FAIL
A4 acknowledgement to next frame: slice=22.6ms production=16.6ms gap=+6.0ms FAIL
B1 navigation to settled: slice=213.9ms production=162.1ms gap=+51.8ms FAIL
B2 key press to settled: slice=227.5ms production=55.4ms gap=+172.1ms FAIL
B3 acknowledgement to settled: slice=120.3ms production=31.1ms gap=+89.2ms FAIL
slice navigation CDP medians: ScriptDuration=63.5ms; RecalcStyleDuration=32.9ms; LayoutDuration=67.3ms; TaskDuration=204.9ms
slice verdict CDP medians: ScriptDuration=16.1ms; RecalcStyleDuration=115.7ms; LayoutDuration=11.0ms; TaskDuration=246.5ms
production navigation CDP medians: ScriptDuration=22.6ms; RecalcStyleDuration=15.1ms; LayoutDuration=47.0ms; TaskDuration=152.5ms
production verdict CDP medians: ScriptDuration=3.3ms; RecalcStyleDuration=3.2ms; LayoutDuration=8.6ms; TaskDuration=39.3ms
M4 one-class: buttons=1; style median=0.6ms; samples=[0.7, 0.8, 0.9, 0.5, 0.3, 0.6]
M4 all-class: buttons=435; style median=54.9ms; samples=[55.9, 60.9, 51.7, 79.9, 51.5, 54.0]
M4 all-aria: buttons=435; style median=89.3ms; samples=[85.8, 80.9, 87.5, 91.2, 93.2, 94.4]
M4 all-both: buttons=435; style median=82.5ms; samples=[100.1, 42.1, 57.6, 128.3, 82.1, 83.0]
M4 all-disabled: buttons=435; style median=98.2ms; samples=[94.1, 108.6, 107.5, 102.4, 73.1, 71.7]
M4 all-unused: buttons=435; style median=0.0ms; samples=[42.8, 0.0, 0.0, 0.0, 0.0, 0.0]
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: A3 acknowledgement to DOM
FAIL: A4 acknowledgement to next frame
FAIL: B1 navigation to settled
FAIL: B2 key press to settled
FAIL: B3 acknowledgement to settled
RESULT: FAIL
```

## Step 2 — invocation 4, no retained stylesheet change

```bash
.venv/bin/python spikes/issue-209/proof_gate.py
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=212.7ms; navigationFrame=225.0ms; dom=11.6ms; frame=18.3ms; navigationSettled=228.6ms; keySettled=256.1ms; ackSettled=165.5ms; responseEnd=35.9ms; elements=13143
run 1 production: navigation=158.4ms; navigationFrame=164.5ms; dom=9.8ms; frame=18.5ms; navigationSettled=174.6ms; keySettled=42.7ms; ackSettled=20.3ms; responseEnd=43.6ms; elements=17138
run 2 production: navigation=149.4ms; navigationFrame=155.0ms; dom=10.3ms; frame=18.8ms; navigationSettled=164.9ms; keySettled=43.4ms; ackSettled=20.6ms; responseEnd=37.5ms; elements=17138
run 2 slice: navigation=217.1ms; navigationFrame=230.0ms; dom=7.6ms; frame=13.8ms; navigationSettled=240.5ms; keySettled=217.6ms; ackSettled=131.0ms; responseEnd=36.9ms; elements=13143
run 3 slice: navigation=196.0ms; navigationFrame=208.4ms; dom=14.9ms; frame=20.4ms; navigationSettled=212.1ms; keySettled=262.8ms; ackSettled=167.2ms; responseEnd=32.9ms; elements=13143
run 3 production: navigation=169.3ms; navigationFrame=178.2ms; dom=10.2ms; frame=21.5ms; navigationSettled=181.6ms; keySettled=51.2ms; ackSettled=24.4ms; responseEnd=47.3ms; elements=17138
run 4 production: navigation=153.2ms; navigationFrame=161.2ms; dom=10.1ms; frame=14.0ms; navigationSettled=173.4ms; keySettled=55.2ms; ackSettled=30.4ms; responseEnd=30.1ms; elements=17138
run 4 slice: navigation=196.0ms; navigationFrame=208.8ms; dom=16.4ms; frame=22.1ms; navigationSettled=212.9ms; keySettled=253.9ms; ackSettled=117.1ms; responseEnd=31.4ms; elements=13143
run 5 slice: navigation=204.1ms; navigationFrame=215.4ms; dom=15.4ms; frame=21.3ms; navigationSettled=218.9ms; keySettled=287.6ms; ackSettled=175.3ms; responseEnd=33.7ms; elements=13143
run 5 production: navigation=152.0ms; navigationFrame=158.3ms; dom=8.7ms; frame=15.4ms; navigationSettled=161.3ms; keySettled=56.3ms; ackSettled=32.8ms; responseEnd=39.7ms; elements=17138
A1 navigation to all groups: slice=204.1ms production=153.2ms gap=+50.9ms FAIL
A2 navigation to next frame: slice=215.4ms production=161.2ms gap=+54.2ms FAIL
A3 acknowledgement to DOM: slice=14.9ms production=10.1ms gap=+4.8ms FAIL
A4 acknowledgement to next frame: slice=20.4ms production=18.5ms gap=+1.9ms FAIL
B1 navigation to settled: slice=218.9ms production=173.4ms gap=+45.5ms FAIL
B2 key press to settled: slice=256.1ms production=51.2ms gap=+204.9ms FAIL
B3 acknowledgement to settled: slice=165.5ms production=24.4ms gap=+141.1ms FAIL
slice navigation CDP medians: ScriptDuration=67.1ms; RecalcStyleDuration=32.9ms; LayoutDuration=65.4ms; TaskDuration=209.8ms
slice verdict CDP medians: ScriptDuration=11.3ms; RecalcStyleDuration=140.5ms; LayoutDuration=13.4ms; TaskDuration=265.4ms
production navigation CDP medians: ScriptDuration=23.9ms; RecalcStyleDuration=16.4ms; LayoutDuration=48.6ms; TaskDuration=157.8ms
production verdict CDP medians: ScriptDuration=3.4ms; RecalcStyleDuration=3.2ms; LayoutDuration=8.3ms; TaskDuration=39.5ms
M4 one-class: buttons=1; style median=0.5ms; samples=[0.6, 0.7, 0.7, 0.4, 0.4, 0.3]
M4 all-class: buttons=435; style median=57.0ms; samples=[51.7, 64.8, 47.9, 61.3, 63.7, 52.8]
M4 all-aria: buttons=435; style median=88.6ms; samples=[77.0, 70.6, 109.0, 82.1, 95.1, 107.5]
M4 all-both: buttons=435; style median=111.0ms; samples=[124.5, 117.0, 116.0, 100.5, 96.8, 105.9]
M4 all-disabled: buttons=435; style median=285.7ms; samples=[112.0, 179.2, 279.6, 291.8, 292.4, 295.1]
M4 all-unused: buttons=435; style median=0.0ms; samples=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
FAIL: A1 navigation to all groups
FAIL: A2 navigation to next frame
FAIL: A3 acknowledgement to DOM
FAIL: A4 acknowledgement to next frame
FAIL: B1 navigation to settled
FAIL: B2 key press to settled
FAIL: B3 acknowledgement to settled
RESULT: FAIL
```

## Step 3 and final invocation 5 — containment

```bash
.venv/bin/python spikes/issue-209/proof_gate.py
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=114.9ms; navigationFrame=120.9ms; dom=12.1ms; frame=12.5ms; navigationSettled=135.9ms; keySettled=41.5ms; ackSettled=19.6ms; responseEnd=36.3ms; elements=13143
run 1 production: navigation=151.4ms; navigationFrame=157.2ms; dom=10.1ms; frame=12.4ms; navigationSettled=168.6ms; keySettled=54.7ms; ackSettled=29.6ms; responseEnd=37.4ms; elements=17138
run 2 production: navigation=156.9ms; navigationFrame=162.5ms; dom=9.9ms; frame=20.8ms; navigationSettled=165.2ms; keySettled=49.2ms; ackSettled=24.1ms; responseEnd=38.6ms; elements=17138
run 2 slice: navigation=111.8ms; navigationFrame=112.2ms; dom=11.5ms; frame=12.3ms; navigationSettled=125.4ms; keySettled=48.6ms; ackSettled=26.0ms; responseEnd=31.5ms; elements=13143
run 3 slice: navigation=123.2ms; navigationFrame=124.5ms; dom=9.9ms; frame=10.6ms; navigationSettled=138.3ms; keySettled=46.7ms; ackSettled=25.4ms; responseEnd=32.3ms; elements=13143
run 3 production: navigation=148.0ms; navigationFrame=154.4ms; dom=13.3ms; frame=23.3ms; navigationSettled=165.3ms; keySettled=48.6ms; ackSettled=24.9ms; responseEnd=38.4ms; elements=17138
run 4 production: navigation=151.4ms; navigationFrame=157.7ms; dom=9.7ms; frame=21.6ms; navigationSettled=160.3ms; keySettled=48.0ms; ackSettled=23.4ms; responseEnd=44.0ms; elements=17138
run 4 slice: navigation=121.8ms; navigationFrame=123.0ms; dom=11.2ms; frame=11.8ms; navigationSettled=137.0ms; keySettled=47.4ms; ackSettled=27.1ms; responseEnd=30.9ms; elements=13143
run 5 slice: navigation=118.0ms; navigationFrame=119.1ms; dom=9.6ms; frame=10.3ms; navigationSettled=132.5ms; keySettled=45.8ms; ackSettled=26.5ms; responseEnd=31.0ms; elements=13143
run 5 production: navigation=158.0ms; navigationFrame=164.5ms; dom=12.0ms; frame=13.7ms; navigationSettled=175.1ms; keySettled=54.4ms; ackSettled=30.4ms; responseEnd=35.6ms; elements=17138
A1 navigation to all groups: slice=118.0ms production=151.4ms gap=-33.4ms PASS
A2 navigation to next frame: slice=120.9ms production=157.7ms gap=-36.8ms PASS
A3 acknowledgement to DOM: slice=11.2ms production=10.1ms gap=+1.1ms FAIL
A4 acknowledgement to next frame: slice=11.8ms production=20.8ms gap=-9.0ms PASS
B1 navigation to settled: slice=135.9ms production=165.3ms gap=-29.4ms PASS
B2 key press to settled: slice=46.7ms production=49.2ms gap=-2.5ms PASS
B3 acknowledgement to settled: slice=26.0ms production=24.9ms gap=+1.1ms FAIL
slice navigation CDP medians: ScriptDuration=64.0ms; RecalcStyleDuration=6.8ms; LayoutDuration=26.8ms; TaskDuration=133.8ms
slice verdict CDP medians: ScriptDuration=10.3ms; RecalcStyleDuration=8.5ms; LayoutDuration=1.0ms; TaskDuration=40.3ms
production navigation CDP medians: ScriptDuration=22.8ms; RecalcStyleDuration=15.7ms; LayoutDuration=48.5ms; TaskDuration=151.5ms
production verdict CDP medians: ScriptDuration=3.8ms; RecalcStyleDuration=3.4ms; LayoutDuration=9.3ms; TaskDuration=44.3ms
M4 one-class: buttons=1; style median=0.6ms; samples=[0.8, 0.6, 0.7, 0.4, 0.6, 0.5]
M4 all-class: buttons=435; style median=2.7ms; samples=[2.0, 2.3, 2.7, 2.7, 3.8, 2.8]
M4 all-aria: buttons=435; style median=3.0ms; samples=[2.9, 2.6, 3.1, 3.0, 3.3, 3.9]
M4 all-both: buttons=435; style median=3.3ms; samples=[3.2, 2.9, 3.0, 3.5, 3.4, 3.5]
M4 all-disabled: buttons=435; style median=5.3ms; samples=[5.1, 5.7, 6.0, 5.1, 5.5, 5.1]
M4 all-unused: buttons=435; style median=0.0ms; samples=[1.4, 1.3, 0.0, 0.0, 0.0, 0.0]
M5 warm Node medians (50): bytes=743025; JSON.parse=1.297ms; projection=0.342ms; value-stable projection=0.790ms
FAIL: A3 acknowledgement to DOM
FAIL: B3 acknowledgement to settled
RESULT: FAIL
```

## Final invocation 6 — unchanged stopped candidate

```bash
.venv/bin/python spikes/issue-209/proof_gate.py
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
target: group 74/74; viewport 1440x1000 light; five alternating fresh documents
run 1 slice: navigation=142.3ms; navigationFrame=143.5ms; dom=8.8ms; frame=9.2ms; navigationSettled=160.7ms; keySettled=41.0ms; ackSettled=17.6ms; responseEnd=42.0ms; elements=13143
run 1 production: navigation=173.1ms; navigationFrame=181.2ms; dom=10.1ms; frame=21.6ms; navigationSettled=184.4ms; keySettled=49.2ms; ackSettled=23.1ms; responseEnd=37.9ms; elements=17138
run 2 production: navigation=167.4ms; navigationFrame=174.6ms; dom=11.2ms; frame=11.6ms; navigationSettled=186.1ms; keySettled=51.1ms; ackSettled=25.1ms; responseEnd=43.9ms; elements=17138
run 2 slice: navigation=130.7ms; navigationFrame=137.2ms; dom=12.4ms; frame=12.8ms; navigationSettled=152.1ms; keySettled=43.5ms; ackSettled=19.0ms; responseEnd=39.5ms; elements=13143
run 3 slice: navigation=137.7ms; navigationFrame=139.2ms; dom=9.2ms; frame=10.0ms; navigationSettled=155.5ms; keySettled=43.3ms; ackSettled=18.7ms; responseEnd=40.3ms; elements=13143
run 3 production: navigation=185.2ms; navigationFrame=193.8ms; dom=14.3ms; frame=14.3ms; navigationSettled=197.3ms; keySettled=62.6ms; ackSettled=28.2ms; responseEnd=49.1ms; elements=17138
run 4 production: navigation=180.3ms; navigationFrame=189.0ms; dom=11.1ms; frame=24.9ms; navigationSettled=193.0ms; keySettled=57.7ms; ackSettled=28.4ms; responseEnd=44.9ms; elements=17138
run 4 slice: navigation=135.5ms; navigationFrame=136.5ms; dom=11.9ms; frame=12.5ms; navigationSettled=152.4ms; keySettled=45.2ms; ackSettled=24.0ms; responseEnd=35.0ms; elements=13143
run 5 slice: navigation=123.6ms; navigationFrame=124.6ms; dom=11.7ms; frame=12.5ms; navigationSettled=137.7ms; keySettled=45.5ms; ackSettled=24.7ms; responseEnd=35.5ms; elements=13143
run 5 production: navigation=170.7ms; navigationFrame=177.0ms; dom=13.3ms; frame=24.4ms; navigationSettled=190.8ms; keySettled=56.9ms; ackSettled=26.2ms; responseEnd=39.4ms; elements=17138
A1 navigation to all groups: slice=135.5ms production=173.1ms gap=-37.6ms PASS
A2 navigation to next frame: slice=137.2ms production=181.2ms gap=-44.0ms PASS
A3 acknowledgement to DOM: slice=11.7ms production=11.2ms gap=+0.5ms FAIL
A4 acknowledgement to next frame: slice=12.5ms production=21.6ms gap=-9.1ms PASS
B1 navigation to settled: slice=152.4ms production=190.8ms gap=-38.4ms PASS
B2 key press to settled: slice=43.5ms production=56.9ms gap=-13.4ms PASS
B3 acknowledgement to settled: slice=19.0ms production=26.2ms gap=-7.2ms PASS
slice navigation CDP medians: ScriptDuration=72.7ms; RecalcStyleDuration=7.5ms; LayoutDuration=27.6ms; TaskDuration=148.4ms
slice verdict CDP medians: ScriptDuration=11.6ms; RecalcStyleDuration=8.6ms; LayoutDuration=1.0ms; TaskDuration=48.9ms
production navigation CDP medians: ScriptDuration=25.8ms; RecalcStyleDuration=18.4ms; LayoutDuration=52.9ms; TaskDuration=173.3ms
production verdict CDP medians: ScriptDuration=4.7ms; RecalcStyleDuration=4.1ms; LayoutDuration=10.7ms; TaskDuration=52.4ms
M4 one-class: buttons=1; style median=0.6ms; samples=[0.8, 0.7, 0.9, 0.5, 0.4, 0.4]
M4 all-class: buttons=435; style median=3.3ms; samples=[2.2, 3.5, 2.7, 4.2, 3.9, 3.2]
M4 all-aria: buttons=435; style median=3.5ms; samples=[3.2, 3.6, 3.8, 4.3, 3.5, 3.4]
M4 all-both: buttons=435; style median=4.0ms; samples=[3.9, 4.8, 3.7, 4.0, 4.5, 3.7]
M4 all-disabled: buttons=435; style median=6.7ms; samples=[6.8, 6.6, 6.0, 7.0, 6.1, 7.9]
M4 all-unused: buttons=435; style median=0.0ms; samples=[1.5, 0.8, 0.0, 0.0, 0.0, 0.0]
M5 warm Node medians (50): bytes=743025; JSON.parse=1.518ms; projection=0.421ms; value-stable projection=0.921ms
FAIL: A3 acknowledgement to DOM
RESULT: FAIL
```

## Gate D — visual comparison

All four attempts fail all five comparisons. The first also cancelled held routes on
close, causing callback noise; the second fixes only proof cleanup and still fails.
Attempt 3 makes image writing explicit via the fixed flag; attempt 4 compares
in memory and confirms both evidence hashes stay unchanged. No passing reroll.
Only one image pair is committed because it shows an actual difference:
[baseline](baseline-desktop-light.png), [containment](containment-desktop-light.png).
Skipped off-screen group bodies are blank within the 2400 px crop; bytes can vary
with deferred rendering. The candidate is a failed measured spike.

```bash
.venv/bin/python spikes/issue-209/proof_visual.py
```

```text
idle 1440px light: #206=249939 bytes #209=189179 bytes; top 2400px PNG identical=False
wrote docs/evidence/issue-209/baseline-desktop-light.png: difference evidence
wrote docs/evidence/issue-209/containment-desktop-light.png: difference evidence
idle 1440px dark: #206=277725 bytes #209=141312 bytes; top 2400px PNG identical=False
idle 390px light: #206=157954 bytes #209=116736 bytes; top 2400px PNG identical=False
idle 390px dark: #206=176754 bytes #209=130920 bytes; top 2400px PNG identical=False
in-flight 1440px light: #206=245432 bytes #209=125306 bytes; all 435 verdict controls aria-disabled; top 2400px PNG identical=False
FAIL: idle 1440px light differs
FAIL: idle 1440px dark differs
FAIL: idle 390px light differs
FAIL: idle 390px dark differs
FAIL: in-flight state differs
RESULT: FAIL
```

## Traversal attempt 1 — geometry drift and keyboard instrumentation failure

This attempt reports no scrolling Long Task but does not establish stability:
height grows 557 px and the mid-page article moves -560.2 px at restored scrollY 0.
Reading its own article box can itself affect containment; no measurement is
presented as an untouched-layout guarantee. One Shift+Tab hit Chromium's
outside-document BODY stop; the unchanged S6 proof skips that stop. Attempt 2 fixes
only that keyboard instrumentation. The initial result is retained:

```text
slice traversal: steps=61; largest=46.1ms; total=1589.9ms; steps with Long Task >50ms=[]; navigation=160.0ms; navigation+traversal=1749.9ms
slice geometry: height before=60392 after=60949; mid-page element viewport top before=30118.2px after=29558.0px; scroll before=0 after=0
production traversal: steps=59; largest=36.1ms; total=1809.8ms; steps with Long Task >50ms=[]; navigation=197.5ms; navigation+traversal=2007.3ms
production geometry: height before=58059 after=58059; mid-page element viewport top before=29816.6px after=29816.6px; scroll before=0 after=0
keyboard jump to last control: focused=False; visible=False; group fully rendered=True; group controls=6
#206 axe light: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#206 axe dark: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#209 axe light: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#209 axe dark: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
S15 axe/contrast coverage identical to #206=True
FAIL: keyboard jump did not render/focus last group
RESULT: FAIL
```

## Traversal attempt 2 — focused control outside viewport

The browser's BODY stop is now skipped, without changing the candidate. The last
control is focused after two Shift+Tabs, but remains outside the visible viewport;
this is a traversal **FAIL**. Both attempts report the same +557 px height change
and -560.2 px middle-article drift, while production geometry stays stable. No
Long Tasks and equal accessibility counts do not establish layout stability.
Reading the middle article's box can itself affect containment.

```bash
.venv/bin/python spikes/issue-209/proof_traversal.py
```

```text
slice traversal: steps=61; largest=30.1ms; total=1593.3ms; steps with Long Task >50ms=[]; navigation=149.7ms; navigation+traversal=1743.0ms
slice geometry: height before=60392 after=60949; mid-page element viewport top before=30118.2px after=29558.0px; scroll before=0 after=0
production traversal: steps=59; largest=32.2ms; total=1819.0ms; steps with Long Task >50ms=[]; navigation=173.1ms; navigation+traversal=1992.1ms
production geometry: height before=58059 after=58059; mid-page element viewport top before=29816.6px after=29816.6px; scroll before=0 after=0
keyboard jump to last control: Shift+Tab presses=2; focused=True; visible=False; group fully rendered=True; group controls=6
#206 axe light: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#206 axe dark: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#209 axe light: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#209 axe dark: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
S15 axe/contrast coverage identical to #206=True
FAIL: keyboard jump did not render/focus last group
RESULT: FAIL
```

## Visual attempt 1 — differing captures and held-route cleanup noise

This is the complete initial capture, retained despite its cleanup exception.
The current command releases held responses and reproduces the comparison, not
this historical cleanup error; attempt 2 above is that correction.

```text
Exception in callback Connection.dispatch.<locals>._done_callback() at /home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py:539
handle: <Handle Connection.dispatch.<locals>._done_callback() at /home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py:539>
Traceback (most recent call last):
  File "/usr/lib/python3.14/asyncio/events.py", line 94, in _run
    self._context.run(self._callback, *self._args)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py", line 540, in _done_callback
    exc = future.exception()
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_page.py", line 308, in _on_route
    handled = await route_handler.handle(route)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_helper.py", line 442, in handle
    return await self._handle_internal(route)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_helper.py", line 484, in _handle_internal
    return await handled_future
           ^^^^^^^^^^^^^^^^^^^^
asyncio.exceptions.CancelledError
Exception in callback Connection.dispatch.<locals>._done_callback() at /home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py:539
handle: <Handle Connection.dispatch.<locals>._done_callback() at /home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py:539>
Traceback (most recent call last):
  File "/usr/lib/python3.14/asyncio/events.py", line 94, in _run
    self._context.run(self._callback, *self._args)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py", line 540, in _done_callback
    exc = future.exception()
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_page.py", line 308, in _on_route
    handled = await route_handler.handle(route)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_helper.py", line 442, in handle
    return await self._handle_internal(route)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_helper.py", line 484, in _handle_internal
    return await handled_future
           ^^^^^^^^^^^^^^^^^^^^
asyncio.exceptions.CancelledError
idle 1440px light: #206=249939 bytes #209=128286 bytes; top 2400px PNG identical=False
idle 1440px dark: #206=277725 bytes #209=210445 bytes; top 2400px PNG identical=False
idle 390px light: #206=157954 bytes #209=116736 bytes; top 2400px PNG identical=False
idle 390px dark: #206=176754 bytes #209=130920 bytes; top 2400px PNG identical=False
in-flight 1440px light: #206=245432 bytes #209=125306 bytes; all 435 verdict controls aria-disabled; top 2400px PNG identical=False
FAIL: idle 1440px light differs
FAIL: idle 1440px dark differs
FAIL: idle 390px light differs
FAIL: idle 390px dark differs
FAIL: in-flight state differs
RESULT: FAIL
```

## Gate C — S1

The unchanged #206 proof runs against the final #209 candidate.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S1
```

```text
-- every required value, for four fixtures, without and with verdicts --
armor_close.csv unreviewed at 1440px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv unreviewed at 390px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 1440px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with 3 verdicts at 390px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv unreviewed at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv unreviewed at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 1440px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_duplicates_ui.csv with 1 verdicts at 390px: 1 groups, 3 members, 12 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv unreviewed at 1440px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv unreviewed at 390px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 1440px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_ui.csv with 2 verdicts at 390px: 1 groups, 2 members, 8 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv unreviewed at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv unreviewed at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 1440px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_same_stat_four_ui.csv with 4 verdicts at 390px: 1 groups, 4 members, 28 differing member values all visible=True, page scrolls sideways=False, differences=0
-- group values no fixture has, overlaid in memory on the server's answer --
exact:6031 shows: {'spirit_signature': 'Spirit of the Fixture · Spirit of the Proof', 'seasonal_mod': 'Fake Seasonal Mod', 'holofoil': 'true'}
same_stat:6081 shows: {'spirit_signature': 'Spirit of the Twin'}
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 1440px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
armor_close.csv with spirit signatures, Seasonal Mod and Holofoil at 390px: 2 groups, 4 members, 6 differing member values all visible=True, page scrolls sideways=False, differences=0
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

## Gate C — S2

The unchanged #206 proof runs against the final #209 candidate.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S2
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

## Gate C — S3

The unchanged #206 proof runs against the final #209 candidate.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S3
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

## Gate C — S4

The unchanged #206 proof runs against the final #209 candidate.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S4
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

## Gate C — S5

The unchanged #206 proof runs against the final #209 candidate.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S5
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

## Gate C — S6

The unchanged #206 proof runs against the final #209 candidate.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S6
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

## Gate C — S13

The unchanged #206 proof runs against the final #209 candidate.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S13
```

```text
axe-core 4.13.0 (MPL-2.0), development-only
pre-fix cascade negative control: Skip to review content=2.40:1/2px; Finalise review=2.40:1/2px; All (2)=2.40:1/2px; rejected=True
reviewing, unreviewed, 1440px light: rules passed=39, violations=[]; contrast axe could not judge: 20 nodes, measured here 20, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, unreviewed, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, unreviewed, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
approval in flight, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
approval in flight, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
approval in flight, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
approval in flight, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 8 nodes, measured here 8, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
approval in flight, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one approval, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one approval, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 1440px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 1440px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 390px light: keyboard focus=18/18; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (2)', 17.72)]; outline floor=3px/2px; problems=[]
reviewing, one veto, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 19 nodes, measured here 19, lowest 4.88:1 (.btn-error), below 4.5:1: []; with a real background image: ['select']; not measured: []
reviewing, one veto, 390px dark: keyboard focus=18/18; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (2)', 14.75)]; outline floor=3px/2px; problems=[]
filtered, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 1440px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
filtered, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 1440px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
filtered, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 390px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
filtered, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 15 nodes, measured here 15, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
filtered, 390px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
finalised, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 1440px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Download reviewed CSV', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
finalised, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 1440px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Download reviewed CSV', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
finalised, 390px light: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 390px light: keyboard focus=15/15; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Download reviewed CSV', 17.72), ('Same stats (1)', 17.72)]; outline floor=3px/2px; problems=[]
finalised, 390px dark: rules passed=40, violations=[]; contrast axe could not judge: 9 nodes, measured here 9, lowest 5.24:1 (.badge-warning), below 4.5:1: []; with a real background image: ['select']; not measured: []
finalised, 390px dark: keyboard focus=15/15; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Download reviewed CSV', 14.75), ('Same stats (1)', 14.75)]; outline floor=3px/2px; problems=[]
no report, 1440px light: rules passed=32, violations=[]; contrast axe could not judge: 5 nodes, measured here 5, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 1440px light: keyboard focus=5/5; lowest 16.68:1 (main review page); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72)]; outline floor=3px/2px; problems=[]
no report, 1440px dark: rules passed=32, violations=[]; contrast axe could not judge: 5 nodes, measured here 5, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 1440px dark: keyboard focus=5/5; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75)]; outline floor=3px/2px; problems=[]
no report, 390px light: rules passed=31, violations=[]; contrast axe could not judge: 6 nodes, measured here 6, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 390px light: keyboard focus=5/5; lowest 16.68:1 (main review page); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72)]; outline floor=3px/2px; problems=[]
no report, 390px dark: rules passed=32, violations=[]; contrast axe could not judge: 5 nodes, measured here 5, lowest 5.24:1 (#vc-reconciliation), below 4.5:1: []; with a real background image: []; not measured: []
no report, 390px dark: keyboard focus=5/5; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75)]; outline floor=3px/2px; problems=[]
RESULT: PASS
```

## Served-source line count

This uses S12's non-blank-line method against the copy commit.

```bash
python3 - <<'PYCOUNT'
import subprocess
from pathlib import Path
base = '088218ba42ee29719ca7eee852e06ce218806ad6'
for name in ('app.css', 'lib/view.ts', 'lib/session.svelte.ts'):
    path = 'spikes/issue-209/frontend/src/' + name
    before = subprocess.check_output(['git', 'show', base + ':' + path], text=True)
    after = Path(path).read_text()
    count = lambda text: sum(bool(line.strip()) for line in text.splitlines())
    print(f'{name}: copy={count(before)} final={count(after)} added={count(after)-count(before)} non-blank lines')
PYCOUNT
```

```text
app.css: copy=61 final=67 added=6 non-blank lines
lib/view.ts: copy=298 final=325 added=27 non-blank lines
lib/session.svelte.ts: copy=194 final=195 added=1 non-blank lines
```

## Repository and frontend verification — output tails

The following are verbatim tails from required commands; routine progress lines
are omitted. Local sockets and Chromium ran outside the restricted sandbox.

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/ruff check spikes/issue-209
.venv/bin/pytest -q
VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py
```

```text
All checks passed!
All checks passed!
1342 passed in 35.83s
16 passed, 3 deselected in 12.44s
```

```bash
(cd spikes/issue-209/frontend && npm ci && npm run check && npm test && npm run build)
```

```text
added 76 packages in 1s
svelte-check found 0 errors and 0 warnings
 Test Files  3 passed (3)
      Tests  35 passed (35)
✓ 121 modules transformed.
dist/index.html       0.43 kB │ gzip:  0.28 kB
dist/modules.json     3.59 kB │ gzip:  0.57 kB
dist/assets/app.css  57.10 kB │ gzip:  9.93 kB
dist/assets/app.js   64.16 kB │ gzip: 23.33 kB
✓ built in 373ms
```

```bash
(cd spikes/issue-206/frontend && npm ci && npm run build)
```

```text
added 76 packages in 1s
✓ 121 modules transformed.
dist/index.html       0.43 kB │ gzip:  0.28 kB
dist/modules.json     3.59 kB │ gzip:  0.57 kB
dist/assets/app.css  57.02 kB │ gzip:  9.90 kB
dist/assets/app.js   63.44 kB │ gzip: 23.09 kB
✓ built in 420ms
```

## Visual attempt 3 — explicit fixed evidence capture

```bash
.venv/bin/python spikes/issue-209/proof_visual.py --write-difference
```

```text
idle 1440px light: #206=249939 bytes #209=189179 bytes; top 2400px PNG identical=False
wrote docs/evidence/issue-209/baseline-desktop-light.png: difference evidence
wrote docs/evidence/issue-209/containment-desktop-light.png: difference evidence
idle 1440px dark: #206=277725 bytes #209=141312 bytes; top 2400px PNG identical=False
idle 390px light: #206=157954 bytes #209=116736 bytes; top 2400px PNG identical=False
idle 390px dark: #206=176754 bytes #209=130920 bytes; top 2400px PNG identical=False
in-flight 1440px light: #206=245432 bytes #209=125306 bytes; all 435 verdict controls aria-disabled; top 2400px PNG identical=False
FAIL: idle 1440px light differs
FAIL: idle 1440px dark differs
FAIL: idle 390px light differs
FAIL: idle 390px dark differs
FAIL: in-flight state differs
RESULT: FAIL
```

## Visual attempt 4 — default read-only comparison

```bash
.venv/bin/python spikes/issue-209/proof_visual.py
```

```text
idle 1440px light: #206=249939 bytes #209=128286 bytes; top 2400px PNG identical=False
idle 1440px dark: #206=277725 bytes #209=141312 bytes; top 2400px PNG identical=False
idle 390px light: #206=157954 bytes #209=116736 bytes; top 2400px PNG identical=False
idle 390px dark: #206=176754 bytes #209=130920 bytes; top 2400px PNG identical=False
in-flight 1440px light: #206=245432 bytes #209=245496 bytes; all 435 verdict controls aria-disabled; top 2400px PNG identical=False
FAIL: idle 1440px light differs
FAIL: idle 1440px dark differs
FAIL: idle 390px light differs
FAIL: idle 390px dark differs
FAIL: in-flight state differs
RESULT: FAIL
```

Attempt 4 was also wrapped with SHA-256 hashes before and after: both evidence
PNG hashes stayed unchanged; visual exit status was 1.

## Gate C — S15 incomplete at 900s

Gate C FAIL. This is the original unchanged S15 invocation's captured output,
released by closing only its Chromium root at the 15-minute verification bound.
One whitespace-only traceback source-context line (four spaces) is omitted to
meet `git diff --check`; all other captured lines are verbatim. This fence is
therefore a disclosed excerpt, not a byte-identical complete capture.
It completed all six parity/layout/Tab checks and the 1440px light/dark axe/focus
laps, then stayed in S13's unchanged `page.evaluate(SETTLE_JS)` before 390px light.
Cause is unproven. The traceback reflects the historical runner's line offsets.
All owned Python/driver/Chromium processes exited; exit status 1, not a skip.
No S15 timing phase completed and no original S15 rerun was made.

The current command now runs the same unchanged proof in an isolated child with
unbuffered output, a fixed 900s limit and owned-descendant cleanup; proof/stamps
are unchanged. Independent review will exercise this bounded command.

```bash
.venv/bin/python spikes/issue-209/run_proof.py S15
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
report: exact=9, same-stat=65; same-stat sizes={2: 57, 3: 6, 4: 2}; members=158; wire bytes=690503
unreviewed 1440px: groups=74, members=158, value/role assertions=3401, differences=0
unreviewed 390px: groups=74, members=158, value/role assertions=3401, differences=0
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
far-down acknowledged verdict: group=74/74; scroll before=62615px; same focused node=True; scroll change=20px; control viewport change=0px
acknowledged 1440px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 1440px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1440px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 1440px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1024px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 1024px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1024px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 1024px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 390px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 390px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 390px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 390px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
sanitised report, acknowledged verdict, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
sanitised report, acknowledged verdict, 1440px light: keyboard focus=444/444; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (74)', 17.72)]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
sanitised report, acknowledged verdict, 1440px dark: keyboard focus=444/444; lowest 14.75:1 (Skip to review content); primary=[('Skip to review content', 14.75), ('Finalise review', 14.75), ('All (74)', 14.75)]; outline floor=3px/2px; problems=[]
Traceback (most recent call last):
  File "/home/raver/projects/personal/vault-cleaner/spikes/issue-209/run_proof.py", line 51, in <module>
    try:

  File "/home/raver/projects/personal/vault-cleaner/spikes/issue-209/run_proof.py", line 47, in main
    return proof.main()
           ~~~~~~~~~~^^
  File "/home/raver/projects/personal/vault-cleaner/spikes/issue-206/proof_s15_scale.py", line 373, in main
    axe_check(page, "sanitised report, acknowledged verdict", failures)
    ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/spikes/issue-206/proof_s13_axe.py", line 121, in run
    page.evaluate(SETTLE_JS)
    ~~~~~~~~~~~~~^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/sync_api/_generated.py", line 9385, in evaluate
    self._sync(
    ~~~~~~~~~~^
        self._impl_obj.evaluate(expression=expression, arg=mapping.to_impl(arg))
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_sync_base.py", line 115, in _sync
    return task.result()
           ~~~~~~~~~~~^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_page.py", line 472, in evaluate
    return await self._main_frame.evaluate(expression, arg)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_frame.py", line 345, in evaluate
    await self._channel.send(
    ...<6 lines>...
    )
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py", line 76, in send
    return await self._connection.wrap_api_call(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    ...<3 lines>...
    )
    ^
  File "/home/raver/projects/personal/vault-cleaner/.venv/lib/python3.14/site-packages/playwright/_impl/_connection.py", line 632, in wrap_api_call
    raise rewrite_error(error, f"{parsed_st['apiName']}: {error}") from None
playwright._impl._errors.TargetClosedError: Page.evaluate: Target page, context or browser has been closed
```

## Gate C — source rules

```bash
.venv/bin/python spikes/issue-209/run_proof.py source
```

```text
shipped source files scanned: 15; test and contract files: 4
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
App.svelte:78 bind:this: focus policy: the list, and its heading to focus
App.svelte:81 bind:this: focus policy: the list, and its heading to focus
main.ts:8 document.getElementById: the mount point, once at start-up
-- ordering computed in the browser --
lib/filters.ts:60 .sort(([left], [right]) => left.localeCompare(right, 'en', { sensitivity: 'base' }))
-- build output --
assets/app.css: 57100 bytes; URL strings 2 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: ['--fx-noise:url("data:image/svg+xml']; @import/@font-face/remote url(): []
  the one data: URI is daisyUI's --fx-noise definition; the same file overrides it with --fx-noise:none: True
assets/app.js: 64161 bytes; URL strings 15 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: []; @import/@font-face/remote url(): []
index.html: 439 bytes; URL strings 0 (XML namespaces, Svelte error-message links, a Tailwind banner); URLs the page would load: []; data: URIs: []; @import/@font-face/remote url(): []
index.html inline scripts, style elements, style or event attributes: []
RESULT: PASS
```

## Animation diagnostics — separate from correctness and gate timings

Two temporary probes tested the same settle expression. Minimal dark-theme change
settled in 2s for both builds, but lacked S15's complete preconditions. The exact
S15 sequence reached >800 successful settle calls; it was deliberately stopped as
redundant, first its own browser, then Python after SIGINT did not stop it. The
partial capture is retained, with no claim that it completed S15 or explains the
original blocked wait. The command below reproduces the probe method; its stop is
bounded at 800 calls for reproducibility, whereas the original was stopped by
owned-process cleanup after that observed prefix. No frozen source file is edited.

```bash
.venv/bin/python -u - <<'PYDIAG'
import sys
sys.path.insert(0, 'spikes/issue-209')
from run_proof import configure
configure()
import proof_s15_scale as proof
from focus_contrast import SETTLE_JS
original_axe = proof.axe_check
checks = 0
def diagnostic(page, label, failures):
    print('DIAGNOSTIC: exact S15 pre-axe state reached', flush=True)
    evaluate = page.evaluate
    def bounded(*args, **kwargs):
        global checks
        if args[0] == SETTLE_JS:
            checks += 1
            state = evaluate('''async () => {
              const animations = document.getAnimations();
              const resolved = await Promise.race([
                Promise.all(animations.map(a => a.finished.catch(() => undefined))).then(() => true),
                new Promise(resolve => setTimeout(() => resolve(false), 2000))]);
              return {animations: animations.length, finishedWithin2s: resolved,
                unfinished: animations.filter(a => a.playState !== 'finished').map(a => ({
                  state: a.playState, pending: a.pending, time: a.currentTime,
                  property: a.transitionProperty, tag: a.effect.target.tagName,
                  inGroup: !!a.effect.target.closest('article[data-group]')})).slice(0, 8)};
            }''')
            if checks == 1 or checks % 100 == 0 or not state['finishedWithin2s']:
                print(f'DIAGNOSTIC settle {checks}: {state}', flush=True)
            if not state['finishedWithin2s'] or checks >= 800:
                raise RuntimeError('diagnostic bound reached; no correctness result')
            return None
        return evaluate(*args, **kwargs)
    page.evaluate = bounded
    original_axe(page, label, failures)
    raise RuntimeError('diagnostic completed axe; stop before repeated timings')
proof.axe_check = diagnostic
try:
    proof.main()
except Exception as error:
    print('DIAGNOSTIC bounded stop: ' + str(error), flush=True)
PYDIAG
```

```text
fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay
report: exact=9, same-stat=65; same-stat sizes={2: 57, 3: 6, 4: 2}; members=158; wire bytes=690503
unreviewed 1440px: groups=74, members=158, value/role assertions=3401, differences=0
unreviewed 390px: groups=74, members=158, value/role assertions=3401, differences=0
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
far-down acknowledged verdict: group=74/74; scroll before=62615px; same focused node=True; scroll change=20px; control viewport change=0px
acknowledged 1440px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 1440px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1440px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 1440px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1024px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 1024px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 1024px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 1024px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 390px light: groups=74, members=158, value/role assertions=3401, differences=0
layout 390px light: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
acknowledged 390px dark: groups=74, members=158, value/role assertions=3401, differences=0
layout 390px dark: sideways=False; internal sideways scrollers=0; opaque values inside=True, clipped=0; member columns=1; Tab=444/444, document order=True, all visible=True
DIAGNOSTIC: exact S15 pre-axe state reached
DIAGNOSTIC settle 1: {'animations': 94, 'finishedWithin2s': True, 'unfinished': []}
sanitised report, acknowledged verdict, 1440px light: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
DIAGNOSTIC settle 100: {'animations': 6, 'finishedWithin2s': True, 'unfinished': []}
DIAGNOSTIC settle 200: {'animations': 0, 'finishedWithin2s': True, 'unfinished': []}
DIAGNOSTIC settle 300: {'animations': 6, 'finishedWithin2s': True, 'unfinished': []}
DIAGNOSTIC settle 400: {'animations': 6, 'finishedWithin2s': True, 'unfinished': []}
sanitised report, acknowledged verdict, 1440px light: keyboard focus=444/444; lowest 17.72:1 (Skip to review content); primary=[('Skip to review content', 17.72), ('Finalise review', 17.72), ('All (74)', 17.72)]; outline floor=3px/2px; problems=[]
sanitised report, acknowledged verdict, 1440px dark: rules passed=40, violations=[]; contrast axe could not judge: 581 nodes, measured here 581, lowest 5.24:1 (article[aria-labelledby="c839-name"] > .sm\:p-6.card-body.gap-4 > .items-start > .items-center > .badge-warning.badge[data-field="kind"]), below 4.5:1: []; with a real background image: ['select']; not measured: []
DIAGNOSTIC settle 500: {'animations': 6, 'finishedWithin2s': True, 'unfinished': []}
DIAGNOSTIC settle 600: {'animations': 6, 'finishedWithin2s': True, 'unfinished': []}
DIAGNOSTIC settle 700: {'animations': 0, 'finishedWithin2s': True, 'unfinished': []}
DIAGNOSTIC settle 800: {'animations': 6, 'finishedWithin2s': True, 'unfinished': []}
```

The earlier minimal probe used fresh #206/#209 pages, read every box, made one
Tab lap, changed to dark, and raced that same promise for 2s. Its output:

```bash
.venv/bin/python -u - <<'PYMINIMAL'
import sys
sys.path.insert(0, 'spikes/issue-209')
from run_proof import configure
configure()
from dev import preload
from harness import live_spike, chromium, authenticated_context, read_slice
from proof_visual import baseline_assets
from proof_s6_layout import tab_through
with live_spike() as live, chromium() as browser:
    preload(live, 'real')
    context = authenticated_context(browser, live)
    for baseline in (True, False):
        page = context.new_page()
        if baseline:
            baseline_assets(page)
        page.goto(live.origin + '/spike/', wait_until='domcontentloaded')
        page.wait_for_selector('article[data-group]')
        read_slice(page)
        tab_through(page)
        page.emulate_media(color_scheme='dark')
        state = page.evaluate('''async () => {
          const animations = document.getAnimations();
          const resolved = await Promise.race([
            Promise.all(animations.map(a => a.finished.catch(() => undefined))).then(() => true),
            new Promise(resolve => setTimeout(() => resolve(false), 2000))]);
          return {animations: animations.length, finishedWithin2s: resolved,
            unfinished: animations.filter(a => a.playState !== 'finished').map(a => ({
              state: a.playState, pending: a.pending, time: a.currentTime,
              property: a.transitionProperty, tag: a.effect.target.tagName,
              inGroup: !!a.effect.target.closest('article[data-group]')})).slice(0, 8)};
        }''')
        print(('#206' if baseline else '#209') + ': ' + str(state), flush=True)
        page.close()
    context.close()
PYMINIMAL
```

```text
#206: {'animations': 2222, 'finishedWithin2s': True, 'unfinished': []}
#209: {'animations': 107, 'finishedWithin2s': True, 'unfinished': []}
```

## Timeout-helper probe — disposable root and owned child

This is an ephemeral standard-library probe; it never runs S15 or touches fixtures.

```bash
.venv/bin/python - <<'PYTIMEOUT'
import contextlib
import io
import subprocess
import sys
sys.path.insert(0, 'spikes/issue-209')
from run_proof import wait_bounded
code = 'import subprocess,time; child=subprocess.Popen(["sleep","60"]); print(child.pid,flush=True); time.sleep(60)'
process = subprocess.Popen([sys.executable, '-u', '-c', code], stdout=subprocess.PIPE,
                           text=True, start_new_session=True)
child = int(process.stdout.readline())
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = wait_bounded(process, 0.2)
state = subprocess.run(['ps', '-p', str(child), '-o', 'stat='], capture_output=True,
                       text=True).stdout.strip()
assert result == 1 and process.poll() is not None and (not state or state.startswith('Z'))
assert 'RESULT: FAIL' in output.getvalue()
print(output.getvalue(), end='')
print('Synthetic root exited=True; owned child absent or non-running zombie=True')
PYTIMEOUT
```

```text
FAIL: unchanged S15 did not finish within 0.2s
RESULT: FAIL (S15 verification timeout; owned processes closed)
Synthetic root exited=True; owned child absent or non-running zombie=True
```

## Final pre-commit checks — output tails

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/ruff check spikes/issue-209
.venv/bin/pytest -q
```

```text
All checks passed!
All checks passed!
1342 passed in 34.08s
```

## Traversal attempt 3 — independent geometry guard

Same failed candidate, now with an independent >1px height/middle-element/scroll
failure assertion. Both geometry and keyboard visibility fail. Counts/no Long
Tasks do not establish stability; all earlier traversal results remain above.

```bash
.venv/bin/python spikes/issue-209/proof_traversal.py
```

```text
slice traversal: steps=61; largest=46.6ms; total=1613.7ms; steps with Long Task >50ms=[]; navigation=159.1ms; navigation+traversal=1772.8ms
slice geometry: height before=60392 after=60949; mid-page element viewport top before=30118.2px after=29558.0px; scroll before=0 after=0
production traversal: steps=59; largest=31.3ms; total=1811.9ms; steps with Long Task >50ms=[]; navigation=177.5ms; navigation+traversal=1989.4ms
production geometry: height before=58059 after=58059; mid-page element viewport top before=29816.6px after=29816.6px; scroll before=0 after=0
keyboard jump to last control: Shift+Tab presses=2; focused=True; visible=False; group fully rendered=True; group controls=6
#206 axe light: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#206 axe dark: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#209 axe light: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
#209 axe dark: unique targets=13137; groups examined=74; violations=0; contrast incomplete=582, measured=582; controls reached=444
S15 axe/contrast coverage identical to #206=True
FAIL: slice document geometry changed across traversal (>1px)
FAIL: keyboard jump did not render/focus last group
RESULT: FAIL
```

## Timeout-helper probe — detached owned child

This extends the previous ephemeral probe to a child with its own process group,
like Chromium. Stable Linux pidfd handles retire it even if it becomes an orphan.

```bash
.venv/bin/python - <<'PYDETACHED'
import contextlib
import io
import subprocess
import sys
sys.path.insert(0, 'spikes/issue-209')
from run_proof import wait_bounded
code = 'import subprocess,time; child=subprocess.Popen(["sleep","60"],start_new_session=True); print(child.pid,flush=True); time.sleep(60)'
process = subprocess.Popen([sys.executable, '-u', '-c', code], stdout=subprocess.PIPE,
                           text=True, start_new_session=True)
child = int(process.stdout.readline())
output = io.StringIO()
with contextlib.redirect_stdout(output):
    result = wait_bounded(process, 0.2)
state = subprocess.run(['ps', '-p', str(child), '-o', 'stat='], capture_output=True,
                       text=True).stdout.strip()
assert result == 1 and process.poll() is not None and (not state or state.startswith('Z'))
assert 'RESULT: FAIL' in output.getvalue()
print(output.getvalue(), end='')
print('Synthetic root exited=True; detached owned child absent or non-running zombie=True')
PYDETACHED
```

```text
FAIL: unchanged S15 did not finish within 0.2s
RESULT: FAIL (S15 verification timeout; owned processes closed)
Synthetic root exited=True; detached owned child absent or non-running zombie=True
```

Final code-state pre-commit repeat (after timeout/geometry guard completion):

```bash
.venv/bin/pytest -q
```

```text
1342 passed in 33.88s
```
