# 2026-10-09 — #209 presentation performance gate implementation

Refs #209. Work on the existing `feat/issue-209-svelte-perf-gate` only.
Approved plan remains byte-identical and is never edited. No issue mutation or PR.
No `data/` file read; only synthetic fixtures and tracked sanitised armor fixture.
No package added, removed or re-versioned; both lockfile/package files match #206.

## Complete dispatch record

- User explicitly requested implementation and referred to issue dispatch
  https://github.com/tonym999/vault-cleaner/issues/209#issuecomment-6089962949,
  confirming approval at `3be17ac7d39d88cb01439edf328872f48051368e`.
- Immutable review base and this attempt's starting SHA:
  `3be17ac7d39d88cb01439edf328872f48051368e`.
- Issue #209 OPEN, enhancement, project vault-cleaner Status Todo, no milestone;
  tracker #138 OPEN. #206 merged through #208 at
  `d139a05306828c0a4d7e9ded211408b346dd7768`.
- Orchestrator: OpenAI GPT-6 Codex desktop runtime; exact model ID/native effort
  not exposed and not guessed.
- Planned and actual implementer: OpenAI `gpt-6.1-sol`, `high`, native Codex
  `collaboration.spawn_agent`; no re-selection.
- Independent adversarial review required. Orchestrator selected OpenAI
  `gpt-6.1-sol`, `high`, via native `collaboration.spawn_agent`, fresh context
  and detached checkout pinned to final committed head at dispatch. No
  cross-provider reviewer is callable in this session. Actual review results
  follow this implementation handoff; no review pass is claimed here.
- Workspace: `/home/raver/projects/personal/vault-cleaner`.
- Copy-only first implementation commit:
  `088218ba42ee29719ca7eee852e06ce218806ad6`. Recursive diff excluding dist and
  node_modules printed nothing. It contains exactly the 27 baseline frontend files.

## Baseline and measurement tooling

Runner sets #206's call-time frontend globals before importing each fixed proof;
source scanner globals also point at #209. It accepts exactly one fixed name and
cannot forward screenshots or a path. No frozen source is edited.
Gate uses unchanged S15 stamps; extra settled stamps are the second nested rAF.
Both pages use 1440x1000 light, same authenticated report, five alternating fresh
pages. CDP counters are diagnostic. The gate enforces S15's focus invariant on the
slice only; production focus loss is measured baseline behavior.

Gate invocation 1 was incomplete: one baseline slice sample then proof incorrectly
asserted focus identity for production. Captured, counted, corrected; no reroll
or exclusion of a complete comparison. Invocation 2 reproduced M1-M4 direction:
A1 198.1/158.2 ms; A3 27.1/9.6 ms; B3 176.0/19.9 ms; verdict style 138.7/3.1 ms.
All seven comparisons fail on the copy, as expected.
The unchanged S1 proof against the copy passed. Full pre-copy pytest first hit
sandbox socket/Chromium restrictions; escalated run passes 1342 in 32.52s.

## Step 1 and step 2 investigation

Step 1 retains complete presented values by equality, never a revision key, and
retains filters when reconciliation changes no value. Three added unit tests cover
one changed verdict, unchanged-revision state/overrides, and a changed snapshot.
35 frontend tests and the type check pass. Invocation 3 moves A3 from 27.1 to 17.4 ms
and A4 from 33.9 to 22.6 ms; script 29.4 to 16.1 ms. Navigation remains behind.

Eight diagnostic command invocations are accounted for: initial join/:has removal;
expanded disabled/theme families; direct-property replacement; narrowed disabled
rules; per-color/background/simple-selector families; transition removal; an
import-bootstrap failure; final fixed all-family command. Every tried family is
preserved in the final proof. Final baseline diagnostic: unchanged 59.5 ms,
join-scope 61.1, has 55.6, disabled 5.6, join-and-disabled 4.1, root-has 71.6,
direct 58.9, color 73.1, background 71.4, simple-selector 70.0, no-transitions 5.5.

Exact cause: daisyUI `.btn` sets transition-property to color, background-color,
border-color, box-shadow, transform, duration 0.2 s. The disabled selectors change
these on all 435 buttons twice. Changing transitions would change intermediate
presentation, so the orchestrator rejected it as diagnostic-only. No stylesheet
candidate was retained. Step 2 invocation 4 uses unchanged step-1 source and still
fails all seven comparisons. Allowed step 3 rendering containment is next.

Baseline tooling commit `a25e997e8c289e2adaa0ea180097091f4844a95b` keeps the
frontend byte-identical to the copy, making step 0 reproducible in a disposable
checkout. The next kept-step commit contains step 1 and step 2 captures. The gate's
warm Node projection diagnostic was added after invocation 4, outside timed windows;
this adds diagnostic output only, not a changed stamp or sample window.

## Step 3 and authorized stop handling

Kept step-1/2 commit: `a8da54329cc6d198e7702b567267263d2669d9b4`.
Navigation attribution still showed script 67.1/23.9 ms, layout 65.4/48.6,
style 32.9/16.4 after step 2. Step 3 uses content-visibility auto with remembered
intrinsic size and an initial 800 px group estimate. All groups remain in the DOM;
off-screen groups render when approaching the viewport. No animation is changed.

Invocation 5 reaches the stop condition: A3 11.2/10.1 ms and B3 26.0/24.9 ms,
both +1.1 ms. A1 118.0/151.4, A2 120.9/157.7, A4 11.8/20.8,
B1 135.9/165.3, B2 46.7/49.2 pass. Style 8.5/3.4 ms and M4 all-both 3.3 ms
show containment also reduces off-screen animation work. Projection is 0.342 ms,
value-stable projection 0.790 ms, JSON.parse 1.297 ms on 743,025 bytes.

The implementer reported the stop immediately. Orchestrator confirmed: make no
further optimization, preserve the measured containment candidate (it moves gated
navigation), finish the second final invocation, C/D/traversal, verification and
NO-GO record, commit/push only the allocated branch. This completes authorized
measurement/reporting; no planner amendment or new implementation is proposed.
Invocation 5 failure precludes GO even if invocation 6 happens to pass. No paging
or virtualization is built. Nothing here ships.

## Final measurements and failures

All six gate invocations are preserved: one incomplete bootstrap and five complete
comparisons. Invocation 6 is the unchanged candidate, recorded regardless of its
outcome: A1 135.5/173.1, A2 137.2/181.2, A3 11.7/11.2 (**FAIL +0.5**),
A4 12.5/21.6, B1 152.4/190.8, B2 43.5/56.9, B3 19.0/26.2 ms. Gate A fails
both final invocations; gate B fails the two-consecutive-invocation bar because
invocation 5 fails B3. Recommendation **NO-GO**, also because gate D fails all five
visual pairs. No final run is discarded and no further optimization is attempted.

All four visual attempts are disclosed in evidence: attempt 1 has differing captures
and held-route cancellation noise; attempt 2 releases held responses before closure
and still differs in every pair. Preserve only one minimal desktop-light pair,
showing blank off-screen group bodies in the 2400 px crop. No #206 image changes.
The candidate is a failed measured spike, never accepted migration code.

The first two traversal attempts are retained. The first stops at Chromium's outside-document BODY
keyboard stop; the second skips it, exactly as S6 does. It focuses the last control
after two Shift+Tabs, but the control is outside the viewport: traversal FAIL.
Second run: slice 61 steps, largest 30.1 ms, total 1593.3 ms + navigation 149.7 ms
= 1743.0 ms, no Long Tasks; production 59 steps, largest 32.2 ms, total 1819.0 ms
+ navigation 173.1 ms = 1992.1 ms, no Long Tasks. Slice height 60392→60949 px
(+557), middle article top 30118.2→29558.0 px (-560.2) at restored scrollY 0;
production height 58059 and middle top 29816.6 stay fixed. Reading the middle
article box may itself affect containment; no stability pass is claimed.

Both themes' accessibility counts match #206: 13137 unique axe targets, 74 groups,
444 native controls, 0 violations, 582 incomplete contrast targets measured. This
equality follows S15's all-box reads and Tab lap; it does not validate untouched
initial off-screen rendering, screen readers or in-page find.

Served source grows 34 non-blank lines (S12 method): view +27 to 325, session +1,
stylesheet +6 to 67; components/types/filtering unchanged, application logic 278,
whole served slice plus unchanged helper 1454. Three new frontend tests give 35.
Timings remain one machine, pinned Chromium, fixture, desktop/light. Other widths'
performance, other browsers, screen readers, in-page find, human navigation and
#210's redesigned presentation are unmeasured. Deferred rendering is accounted for
above rather than treated as free work.


## Verification completed before final commit

- `.venv/bin/ruff check src tests scripts`: All checks passed.
- `.venv/bin/ruff check spikes/issue-209`: All checks passed.
- `.venv/bin/pytest -q`: **1342 passed in 35.83s**, unchanged count.
- `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`:
  **16 passed, 3 deselected in 12.44s**; no browser skip.
- Clean #209 `npm ci`: 76 packages; `npm run check`: 0 errors/warnings;
  `npm test`: 3 files, 35 tests pass; `npm run build`: 121 modules,
  CSS 57.10 kB, JS 64.16 kB, built in 373 ms.
- Clean #206 `npm ci`: 76 packages; `npm run build`: 121 modules,
  CSS 57.02 kB, JS 63.44 kB, built in 420 ms.
- Unchanged runner S1, S2, S3, S4, S5, S6 and S13: RESULT PASS.
- Stylesheet diagnostic final invocation: RESULT PASS (diagnostic reduction only).
- Both final gate invocations: RESULT FAIL; visual and traversal: RESULT FAIL.
- `python3 scripts/check_worklog.py --base origin/main`: worklog: ok.
- Package and lockfile `cmp` against #206 print nothing; frozen-path diff empty.

Proof entry points now emit `RESULT: FAIL` before re-raising an unexpected exception
or nonzero SystemExit (including missing Chromium/build), without changing proof functions, samples or stamps.
The fixed-name runner rejects screenshot/path arguments; no #206 proof is modified.

An ephemeral AST execution of all five entry blocks verifies SystemExit(1) prints
RESULT FAIL and preserves status 1; no test file or dependency was added.

Visual attempts 3/4 fix measurement hygiene only: the fixed --write-difference
flag is the sole way to write the minimal pair; no path input is accepted. Default
runs compare in memory and leave both evidence SHA-256 hashes unchanged. Both
still fail all five comparisons; no capture or comparison is discarded.

## Gate C: unchanged S15 incomplete at the verification limit

S1–S6, S13 and source rules PASS, but **Gate C FAIL**: unchanged S15 did not
complete in 900 s. Final successful stage: all six layout/Tab checks, then
1440 px light/dark axe and 444-control focus laps. It remained in
proof_s13_axe.py:121 `page.evaluate(SETTLE_JS)` before 390 px light. At the
15-minute bound only its Chromium root was sent SIGTERM, releasing evaluation
with TargetClosedError. Exit 1; full buffered stdout and traceback are preserved;
its Python, Playwright driver and Chromium processes were confirmed gone.
No complete S15 timing phase, no skip, no original S15 rerun. Cause is unproven.

Two separate animation diagnostics are disclosed: minimal dark-theme settle
completed within 2 s (#206 2222 animations, #209 107); exact S15 preconditions
completed six layouts and >800 settle calls, each under 2 s. The redundant exact
diagnostic was then stopped deliberately: SIGINT did not stop Python; its own
browser was closed with SIGTERM, then its own Python was terminated. It is not
Gate C evidence of a pass and does not establish the original wait's cause.

The #209 runner now gives unchanged S15 an isolated child, unbuffered output,
and a fixed 900 s bound. Timeout closes only descendants recorded under that
child, preserves nonzero failure and prints RESULT FAIL; no frozen function,
stamp, proof source or candidate is changed. Parent prints FAIL on every nonzero
child result, including missing Chromium/build; duplicates on a completed failing
proof are acceptable. An ephemeral sleeping-process/child probe verifies timeout
and owned cleanup. Independent reviewer will exercise this bounded exact command.

Final pre-commit checks: both lints PASS; **1342 passed in 34.08s**. The strengthened
0.2 s timeout-helper probe asserts root exited and owned sleep child absent or
non-running; RESULT FAIL/status 1 as expected. S15 evidence discloses omission of
one four-space-only traceback source-context line for whitespace validation; the
raw original stays in `/tmp/issue-209-final-S15.txt`. All substantive lines verbatim.

Phase recheck by orchestrator: #209 still OPEN, project status now In Progress
(Todo at dispatch), no milestone; no issue/project mutation by this implementation.
Timeout cleanup uses Linux pidfd handles, including detached owned orphans; exited
snapshot PIDs without handles are skipped, and handles close in finally. A third
synthetic probe checks a detached sleep child. Traversal now independently fails
when slice height, middle-element top or restored scroll changes by >1 px, rather
than relying on its concurrent keyboard failure. No candidate tuning.

Orchestrator independent verification before review dispatch: both lints PASS;
1342 passed in 34.74 s; required browser 16 passed, 3 deselected in 13.08 s.
Its disposable frontend negative control made retain() unconditionally reuse
previous values: all three value-stable adoption tests failed, as required. The
copy was removed. This is orchestrator verification, not independent review.

Third/final traversal FAIL: independent >1 px geometry assertion and keyboard
visibility both fail. Slice 61 steps, largest 46.6 ms, total 1613.7 + navigation
159.1 = 1772.8 ms; production 59 steps, largest 31.3, total 1811.9 + navigation
177.5 = 1989.4 ms. Geometry and accessibility counts match earlier attempts; no
Long Tasks. All three attempts kept, no candidate tuned. Detached timeout-helper
probe PASS: owned child absent/non-running after the 0.2 s timeout, status 1 and
RESULT FAIL as expected. Linux pidfd handles address orphan/PID reuse and exited
snapshot races; no measurement window changed.

Final code-state pre-commit pytest: **1342 passed in 33.88 s**. Both lints pass;
worklog checker and working diff-check pass. Final inclusion, ancestor, frozen-path
and committed diff checks are recorded immediately after the scoped commit.
