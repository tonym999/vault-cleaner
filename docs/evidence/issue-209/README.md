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
