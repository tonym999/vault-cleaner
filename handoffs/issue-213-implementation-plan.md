# Issue #213 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#213 — M10: repeat the real-scale timing gate on the redesigned Svelte slice`

**Milestone:** none assigned (no M10 milestone exists; `PLAN.md` has no M10 section)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Claude Code desktop session; the session does not report its native effort, so none is recorded)

**Implementation model selected:** `claude-opus-5-5` at `high` (Judgement rung; justified below)

**Plan baseline:** `main` at `89ff866ee610816bf9fe28e048e60617fbd66063` (2026-10-11)

**Allocated branch:** `feat/issue-213-redesigned-slice-timing-gate` (this plan is its first commit)

The implementer must **not** open a pull request or edit this file. The branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

#210 redesigned the Svelte Armor duplicates slice and showed only that it does
not repeat #209's dominant cost. #209's full gate, seven comparisons against
the current page on the tracked sanitised report, has not been run on it.

This ticket runs that gate on the redesigned slice, attributes first-render
time before changing anything, makes changes only inside the limits #210 set,
and records **GO** or **NO-GO** for the redesigned slice against #209's bar.

It is a spike. No production code changes, and nothing here ships. **NO-GO
with every figure recorded is a complete outcome of this ticket**, not a
failed attempt.

## Context & Measurement

### What is already recorded

- #210's diagnostic S15 run, five alternating runs, 1440 px, light, slice /
  production: navigation 235.5 / 147.0 ms; acknowledgement to DOM 7.5 /
  10.0 ms ([docs/evidence/issue-210/README.md, S15 fence](../docs/evidence/issue-210/README.md#L525-L604)).
  Style recalculation over one verdict: 1.2 ms median
  ([spikes/issue-210/proof_no_transition.py:52-76](../spikes/issue-210/proof_no_transition.py#L52-L76)).
- #209's gate and its result on the #206 design live on the unmerged branch
  `feat/issue-209-svelte-perf-gate`, head
  `ee61b0790e4e1a8f8b928d3b452210fa6558f9b8`. The gate proof is
  `spikes/issue-209/proof_gate.py` there, blob
  `a77c21f3f2826c735c49463f6ef4d305604e82da`.

### Planning measurements (2026-10-11)

Made at the plan baseline. Only the tracked sanitised fixture
`tests/fixtures/real/2026-09-01T-current/armor.csv` was read. The scripts were
in the session scratchpad and are not in the repository; the method is stated
so step 0 and step 1 can reproduce each figure.

**Method.** #209's `proof_gate.py`, the blob above, byte for byte, run with
`PYTHONPATH=spikes/issue-210` so that its `from run_proof import FRONTEND,
configure` resolves to #210's runner and build
(`spikes/issue-210/frontend/dist`, rebuilt with `npm run build`: `app.js`
144,389 bytes, `app.css` 31,725 bytes). Two complete invocations, one after
the other. Chromium as pinned, 1440x1000, light, one machine.

**P1. The seven comparisons, slice / production, medians of 5.**

| | Invocation 1 | Invocation 2 |
| --- | --- | --- |
| A1 navigation to every group laid out | 234.5 / 149.1 ms, **+85.4 FAIL** | 247.9 / 146.1 ms, **+101.8 FAIL** |
| A2 navigation to next frame | 246.7 / 156.1 ms, **+90.6 FAIL** | 260.5 / 151.7 ms, **+108.8 FAIL** |
| A3 acknowledgement to DOM | 6.8 / 10.1 ms, pass | 7.8 / 10.0 ms, pass |
| A4 acknowledgement to next frame | 12.1 / 16.5 ms, pass | 12.4 / 17.6 ms, pass |
| B1 navigation to settled | 259.7 / 158.7 ms, **+101.0 FAIL** | 273.7 / 160.6 ms, **+113.1 FAIL** |
| B2 key press to settled | 50.8 / 57.1 ms, pass | 52.2 / 48.7 ms, **+3.5 FAIL** |
| B3 acknowledgement to settled | 29.1 / 30.5 ms, pass | 29.6 / 20.8 ms, **+8.8 FAIL** |

The redesigned slice fails the gate. The three navigation comparisons fail by
85 to 113 ms in both invocations. The verdict comparisons A3 and A4 pass in
both.

**P2. Where navigation time goes (Chromium's counters, medians of 5, both
invocations).** `Performance.getMetrics` deltas from document start to the
settled stamp.

| | Slice | Production | Difference |
| --- | --- | --- | --- |
| Script | 93.6, 95.9 ms | 22.9, 22.1 ms | about +72 |
| Layout | 79.0, 76.0 ms | 47.6, 44.9 ms | about +31 |
| Style recalculation | 31.8, 31.9 ms | 15.3, 15.6 ms | about +16 |
| Main-thread task time | 260.5, 265.4 ms | 152.0, 147.7 ms | about +113 |

The slice has fewer elements (13,019 against 17,138) and is slower in all
three. `/api/report` also finishes later on the slice: response end 46 to
59 ms in nine of ten runs against production's 28 to 41 ms.

**P3. The class-merge guess is small.** #210's worklog named a
`tailwind-merge` call per badge as a candidate. A sampling CPU profile
(`Profiler` over CDP, 100 µs interval, five fresh documents, an unminified
build of the same source made with `vite build --minify false` into the
scratchpad) gives these inclusive medians. Sampling at that rate inflates
every figure, so read them as proportions:

| Inclusive | ms |
| --- | --- |
| Svelte's effect flush that mounts the list | 78.0 |
| `GroupCard` (74 instances) | 65.3 |
| `PieceColumn` (158 instances) | 41.2 |
| `Badge` (232 instances) | 9.7 |
| Class merging under it (`tailwind-variants` and `tailwind-merge`) | 7.0 |
| `Value` | 7.9 |
| `TunedStat` | 7.5 |
| `StatStrip` | 5.9 |
| Garbage collection (self time) | 28.8 |
| `cloneNode` (self time) | 12.5 |

Class merging is about 7 of roughly 80 ms of profiled script: under a tenth.
Removing it entirely would not close an 85 ms gap. The cost is spread across
mounting 13,019 elements through per-instance components and effects, plus
garbage collection, layout and style. `Badge` merges per instance at
[badge.svelte:37](../spikes/issue-210/frontend/src/components/ui/badge.svelte#L37);
the verdict buttons already merge once per module at
[VerdictControls.svelte:9-27](../spikes/issue-210/frontend/src/components/VerdictControls.svelte#L9-L27).

**P4. The verdict path is as #210 said.** Slice / production over one
verdict: script 7.8 / 3.6 ms, style 1.2 / 3.3 ms, layout 5.4 / 8.9 ms, task
time 38.4 / 43.8 ms (invocation 1; invocation 2 within 1 ms). Flipping
`aria-disabled` on all 435 buttons costs 0.0 ms of style.

**P5. B2 and B3 are decided by frame phase, not by the slice.** The settled
stamp is the second of two nested animation frames, so it lands on a frame
boundary. Acknowledgement to settled on the slice was 28.5 to 30.3 ms in all
ten runs. On production it was 19.2 to 21.8 ms in five runs and 29.5 to
33.7 ms in the other five. Which mode production's median falls in decided
B2 and B3: they passed in invocation 1 and failed in invocation 2 with no
change to either page. The gap is smaller than one 16.7 ms frame. Chromium's
own counters for the same window favour the slice (P4).

**P6. Approve and Veto.** The gate inherits S15's alternation
([proof_s15_scale.py:253](../spikes/issue-206/proof_s15_scale.py#L253)): the
slice is timed on Approve, Veto, Approve, Veto, Approve and production on the
opposite sequence. No difference by action above 1 ms shows in the per-run
A3 values of P1 (slice 6.2 to 8.2 ms after the first document; production
9.2 to 11.7 ms).

**What follows.**

- The baseline will fail. The work is attribution, then a bounded attempt,
  then an honest record.
- No single cheap fix is in view. The planner's expectation is NO-GO unless
  attribution finds a large cost the profile above does not show.
- A GO needs B2 and B3 to hold twice running. On the planning evidence that
  is partly luck of frame phase; the record has to say so either way.

### Repository facts that shape the work

- `spikes/issue-210/` is the evidence for a merged ticket: section 5 of
  [docs/evidence/issue-210/README.md](../docs/evidence/issue-210/README.md)
  is reruns of its code. It is frozen, like `spikes/issue-206/`.
- `spikes/issue-210/frontend/src/lib/` already carries #209's value-retention
  change (`duplicateGroups(envelope, previous)`,
  [view.ts:295-326](../spikes/issue-210/frontend/src/lib/view.ts#L295-L326)).
- **#210's runner binds its build at definition time.**
  [run_proof.py:96](../spikes/issue-210/run_proof.py#L96) is
  `def configure(frontend: Path = FRONTEND)`, and S15's child process calls
  `configure()` with no argument
  ([run_proof.py:113-136](../spikes/issue-210/run_proof.py#L113-L136)).
  `proof_axe.py`, `proof_csp.py`, `proof_layout.py`, `proof_no_transition.py`
  and `capture.py` each call `configure()` at import. Setting
  `run_proof.FRONTEND` afterwards does not redirect any of them. A #213
  runner must call `configure(<the #213 frontend>)` itself, first; the
  `_configured` latch at `run_proof.py:78-101` then makes the later calls
  no-ops. `proof_no_transition.py:26` also imports `FRONTEND` by name to read
  the built stylesheet, so that name must be set before the import too.
- The spike server serves exactly `index.html`, `assets/app.js` and
  `assets/app.css` from the build
  ([spike_app.py:50-68](../spikes/issue-206/spike_app.py#L50-L68)). A build
  that emits another file will not have it served.
- The root `.gitignore` ignores `dist/` but not `node_modules/`.
  `spikes/issue-210/.gitignore` adds both for that directory.
- CI lints `src tests scripts` only; nothing in CI runs a spike.
- Baseline at the plan commit: `.venv/bin/pytest -q` reports `1342 passed`;
  `.venv/bin/ruff check src tests scripts spikes/issue-206 spikes/issue-210`
  passes. Python 3.14.4, Node v24.20.0.
- `docs/frontend-framework-decision.md` on `main` is still #206's text
  (last changed by `d139a05`). #209's rewrite of it is on #209's branch only.
- `python3 scripts/check_model_roster.py` reports 2 stale rows, both Gemini.
  The `claude-opus-5-5` and `gpt-6.1-sol` rows are current.

## Dependencies and assumptions

- **#213 is open,** labelled `enhancement`, on the project with status
  `Todo`, tracked under #138 (open). #210 is closed, merged through PR #212
  at `89ff866`.
- **#209 is open and its branch is unmerged.** The issue says "Depends on
  #209". This plan reads that as a dependency on the gate's definition and
  tooling, which are pinned above by commit and blob. It does not need the
  branch merged, and does not merge, rebase onto or edit it. What happens to
  that branch stays the owner's decision.
- **The issue's figures are current.** Planning runs gave the same direction
  and slightly larger navigation gaps (P1).
- **Divergence 1: the candidate cause in the issue is measured and small**
  (P3). The plan does not build around it.
- **Divergence 2: the issue's three open questions are settled here.**
  **Approving this plan approves these three answers.**
  1. *Tooling.* The gate proof is carried from #209's branch as a verbatim
     copy of the pinned blob, then adapted in a separate commit, so every
     difference from #209's gate is one readable diff. #209's branch is not
     merged first.
  2. *The screenshot gate.* Byte-identical captures are not a pass condition
     of the timing gate. They are the test of whether a change needs the
     owner: a change that alters any compared capture or the document's
     height is a stop condition, returned for the owner's acceptance.
  3. *shadcn-svelte.* Not decided here. P3 shows class merging is a small
     part of the cost. Resolving class strings once instead of per instance
     is an allowed change if attribution supports it, and the rendered
     `class` attributes must stay identical. Removing the button and badge
     conventions, or the three packages, is not in scope; the record reports
     what they cost so the owner can decide.
- **Divergence 3: the directory.** The work goes in a new
  `spikes/issue-213/`. `spikes/issue-210/` is not edited.
- **The bar is #209's, unchanged:** each of the seven comparisons holds in
  each of two consecutive complete invocations. P5 shows two of the seven
  can flip on frame phase. The plan keeps the bar, because the issue asks
  for the same one, and requires the record to show the phase effect. It
  adds no gated comparison and removes none.
- **Assumption:** timings come from one machine and one browser, as in #206,
  #209 and #210. The gate compares the two pages under the same conditions
  in the same invocation and claims nothing about absolute speed.
- **Working-tree note.** The planning checkout has an untracked
  `spikes/issue-209/` holding only `node_modules`, `dist` and `__pycache__`
  left from a checkout of #209's branch. It is not part of this ticket.
  Stage paths by name; never `git add -A`.

## Proposed Plan & Scope

### The spike directory

#### [NEW] `spikes/issue-213/frontend/`

A copy of `spikes/issue-210/frontend/` (source, `index.html`, configuration,
`package.json`, `package-lock.json`).

- **The first implementation commit is the two verbatim copies and nothing
  else:** this directory, and `spikes/issue-213/proof_gate.py` as the pinned
  #209 blob. At that commit both of these print nothing, and the second
  prints the blob id above:

  ```bash
  diff -r --exclude=node_modules --exclude=dist spikes/issue-210/frontend spikes/issue-213/frontend
  git rev-parse HEAD:spikes/issue-213/proof_gate.py
  ```

  Record its SHA as the **copy commit**. Every later change to the slice or
  to the gate is then a diff from it.
- No dependency is added or re-versioned. `package-lock.json` stays
  byte-identical to #210's. `package.json` stays byte-identical too.

#### [NEW] `spikes/issue-213/.gitignore`

`node_modules/` and `dist/`, as in `spikes/issue-210/.gitignore`. It may be
part of the copy commit.

#### [NEW] `spikes/issue-213/` Python modules

Names other than `proof_gate.py` are the implementer's. These roles are
required.

- **A runner** that runs each #206 and #210 proof, unedited, against the
  #213 build: S1, S2, S3, S4, S5, S6, S15 and the source scan with the three
  adaptations #210's runner makes, and `proof_csp`, `proof_axe`,
  `proof_layout` and `proof_no_transition`. It takes a proof name from a
  fixed list and no other argument. See *Repository facts* for how the build
  location must be set.
- **Every proof run prints which build it used:** the SHA-256 of the served
  `app.js` and `app.css`, read from the live server's responses, not from
  disk. This is the check that a proof did not quietly run against #210's
  build.
- **The gate proof,** `proof_gate.py` (below).
- **The attribution proof** (step 1).
- **The visual proof** (below), required once the slice source differs from
  the copy commit.

Each proof prints `RESULT: PASS` or `RESULT: FAIL` and exits non-zero on
failure. A browser proof fails when Chromium is missing; it never skips.
Each new check has a negative control that it is shown to detect (#210's
worklog, `2026-10-11-issue-210-fix-round-2.md`, "For the next agent").

#### [NEW] `spikes/issue-213/README.md`

What the directory is, that nothing ships, the build commands, and one
command per proof.

### The gate

Same conditions as #209 and S15: the tracked sanitised fixture uploaded once,
one authenticated session, all groups, no Class selection, 1440x1000, light,
fresh documents, the two pages alternating which goes first, five runs each,
medians. "Slice" is the #213 build; "production" is the current page at `/`.

The slice's median is less than or equal to production's for each of:

- **Gate A,** S15's stamps: (A1) navigation to every group laid out; (A2)
  navigation to the next animation frame; (A3) acknowledgement to DOM; (A4)
  acknowledgement to the next animation frame.
- **Gate B,** settled frames, the second of two nested animation frames:
  (B1) navigation to settled; (B2) key press to settled; (B3) acknowledgement
  to settled.

**Passing.** Every comparison holds in **each of two consecutive complete
invocations**. Every invocation made for the record is reported, with its
count, including incomplete ones; none is discarded or re-rolled. A
comparison that holds in one invocation and fails in the other is a failure
with a measured gap.

**What may differ from #209's `proof_gate.py`.** After the copy commit, the
diff of `proof_gate.py` against the pinned blob may contain only:

- where the runner and build come from;
- output added, not changed: the build hashes, and the action (Approve or
  Veto) on each run's line;
- removal or adjustment of the two diagnostics that name #206's markup, if
  they cannot run: the flip probe's `btn-disabled` class, and the Node
  projection probe's working directory.

`RUNS`, `COMPARISONS`, `TIMING_JS` and `ARM_REPAINT_JS` as imported,
`SETTLED_JS`, `ARM_SETTLED_JS`, the sample window, the alternation and the
pass rule do not change. The reviewer reads every hunk of:

```bash
git diff a77c21f3f2826c735c49463f6ef4d305604e82da HEAD:spikes/issue-213/proof_gate.py
```

**Reporting B2 and B3.** For both pages the record gives every run's value,
not only the medians, and says whether production's values fall in two
groups about a frame apart (P5). The verdict-window counters (script, style,
layout, task time) are printed beside them. These explain a result; they do
not change it.

### The steps, in order

**Step 0: baseline.** With the verbatim copy built, run the gate proof twice
and record both invocations. Run every proof through the runner once and
record the results. This is the "before" column, and the answer to the
issue's first acceptance criterion.

**Step 1: attribution, before any change to the slice.** The attribution
evidence is committed before the first commit that changes a file under
`spikes/issue-213/frontend/`. The record must give, slice beside production
where production has the equivalent:

- script, layout, style recalculation and task time over the navigation
  window, from `Performance.getMetrics` (P2);
- a timeline of the slice's navigation: when `app.js` finished loading, when
  the `/api/report` request started and ended, when the first group was in
  the document, and the `ready` stamp. It splits "before the data arrived"
  from "rendering it";
- where script time goes, by component and by library, from a sampling
  profile of an unminified build of the same source (P3). State the sampling
  interval and that the figures are proportions. Garbage collection is
  reported as its own line;
- for any single cause the record names, an **ablation**: a throwaway build
  or a CSSOM change with that one thing removed, and the navigation figures
  with and without it. A cause is "attributed" when removing it moves the
  number, not when a profile mentions it. Ablation builds are not committed;
  their diffs are quoted in the evidence;
- what layout and style cost beyond production's, to the level the tools
  allow, and a plain statement of what could not be attributed.

Write the unminified and ablation builds outside the repository or under an
ignored `dist/`.

**Step 2: changes, largest attributed cost first.** Make one change at a
time. After each, run the gate proof and record it. **Keep a change only if
it moved a gated comparison** by more than the spread between the two
baseline invocations; take out one that did not, and record it as tried and
dropped. Allowed means:

- script: less work per repeated element with the rendered DOM unchanged.
  Examples: a class string resolved once per variant instead of per
  instance; fewer components, effects or spread attributes on an element
  that appears hundreds of times;
- stylesheet: changes that leave every computed presentation value and all
  geometry unchanged;
- load path: starting the report request earlier, or shrinking what loads
  before it, within the unchanged CSP, routes and the three served files.

Not allowed, whatever they would save:

- `content-visibility`, `contain`, or any other rendering containment;
- deferred, chunked, idle-time or on-scroll mounting; paging;
  virtualisation. Every group is in the document and laid out at the `ready`
  stamp;
- a transition or animation on verdict controls, or a rule selecting on
  `aria-disabled`;
- anything that changes what the slice shows, says to assistive technology,
  or sends.

**Step 3: stop when there is nothing allowed left to try, or the gate
passes.** With the final source, run the gate proof twice more, back to
back; those are the two final invocations. Then run every proof through the
runner, the visual proof, and the frontend checks.

A short measurement of what an excluded means would save may be included,
labelled as not built and not part of the result.

### The visual proof

Required when the slice source differs from the copy commit. In one run, it
captures the top 2,400 px of the sanitised report at 1440 and 390 px, dark
and light, from the #210 build and from the #213 build, and compares the PNG
bytes in memory. It also compares the document's scroll height at each of
the four states.

- **A control comes first:** the #210 build captured twice. A state whose
  two control captures differ is reported as not comparable, and is not
  counted as a pass. (#210's round 2 saw four capture files change bytes
  after regeneration without investigating why.)
- **A negative control:** a one-pixel change made through the CSSOM is
  detected.
- No image is written unless a difference has to be shown. No new Python
  package.

Any difference between the builds, in a comparable capture or in a height,
is a stop condition.

### Decision record

#### [MODIFY] [docs/frontend-framework-decision.md](../docs/frontend-framework-decision.md)

Additions only. #206's text and tables stay as written.

- **Status** (lines 3-8): one sentence naming #213, the date, GO or NO-GO
  for the redesigned slice, and a link to the new subsection.
- **Section 6, after "Real scale beside production"** (ends at line 469): a
  new subsection, "The redesigned slice against #209's gate (#213)". It
  holds the baseline table for both invocations, the attribution, the step
  table (each change, what it moved, kept or dropped), both final
  invocations, the per-run B2 and B3 values with the frame-phase statement,
  and the verdict.
- **GO** requires gates A and B by the passing rule, every proof passing on
  the final source, and the visual proof clean or not required. Otherwise
  the record says **NO-GO for the redesigned slice as measured**, gives the
  gap per comparison, and notes that #209's issue lets the owner accept a
  measured gap explicitly. The implementer never writes GO on a failing
  comparison, including a B2 or B3 failure smaller than a frame.
- The subsection states that #209's own record is on
  `feat/issue-209-svelte-perf-gate` at `ee61b07` and is not on `main`.
- **Section 8** (line 589 on): one bullet. Timings are one machine, one
  browser, 1440 px, light; the settled-frame comparisons are quantised to a
  frame; what was not measured.
- **Section 9, draft 5** (line 705): one note that #209 and #213 carried it
  out, with the outcome. No issue is created or edited.

### Evidence and worklog

#### [NEW] `docs/evidence/issue-213/README.md`

Per `AGENTS.md`, *Conventions*: verbatim command transcripts, plain text,
each fence reproducible on its own. It holds both baseline invocations, the
attribution transcripts and ablation diffs, one gate transcript per change
tried, both final invocations, the runner transcripts, and the visual proof
when required. Only the tracked sanitised fixture is read; every id shown
carries the `1000` marker.

#### [NEW] `worklog/YYYY-MM-DD-issue-213-implementation.md`

What was done, the decisions made, the result, the count of gate
invocations, what was tried and dropped, anything surprising, what was not
measured, and the copy commit's SHA.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- every changed path is under `spikes/issue-213/` or
  `docs/evidence/issue-213/`, or is `docs/frontend-framework-decision.md`,
  or is a new `worklog/*-issue-213-*.md` entry; and
- it measures presentation work on load or on a verdict, or reduces it by an
  allowed means, or records the result; and
- it changes nothing the slice shows, says to assistive technology, or sends
  to the server.

Both commands print nothing (`<base>` is the ticket's review base):

```bash
git diff --name-only <base>...HEAD | grep -vE '^(spikes/issue-213/|docs/evidence/issue-213/|docs/frontend-framework-decision\.md$|worklog/[0-9]{4}-[0-9]{2}-[0-9]{2}-issue-213-[a-z0-9-]+\.md$)'
git ls-files spikes/issue-213 | grep -E '(^|/)(node_modules|dist)/'
```

Worked examples:

- **IN SCOPE:** computing a badge's class string once per variant, with the
  rendered `class` attribute byte-identical and a gate transcript showing
  what it moved.
- **IN SCOPE:** a throwaway build with class merging stubbed out, used only
  to measure its cost, its diff quoted in the evidence and not committed.
- **IN SCOPE:** a runner that points #210's `proof_axe.py` at the #213 build
  without editing it, and prints the hashes of the files served.
- **IN SCOPE:** adding the action name to each run's line in `proof_gate.py`.
- **OUT OF SCOPE:** any edit under `spikes/issue-210/`, `spikes/issue-206/`,
  `spikes/issue-137/`, `src/`, `tests/`, `scripts/`, `.github/`,
  `docs/evidence/issue-210/`, `docs/evidence/issue-206/`, or to
  `pyproject.toml`, `.gitignore`, `PLAN.md` or `AGENTS.md`.
- **OUT OF SCOPE:** `content-visibility: auto` on group cards, or mounting
  groups a few per frame, even with a traversal proof.
- **OUT OF SCOPE:** changing `RUNS`, a stamp, the sample window or the pass
  rule in `proof_gate.py`; dropping a run; adding a warm-up document.
- **OUT OF SCOPE:** a different component library, or removing shadcn's
  button and badge conventions, `tailwind-variants`, `tailwind-merge` or
  `clsx` from the slice.
- **OUT OF SCOPE:** a new npm or Python package; a new route; a server-side
  view-model; a fourth served file.
- **OUT OF SCOPE:** changing colours, spacing, structure or wording, even
  where it would be faster.
- **OUT OF SCOPE:** merging, rebasing onto, or pushing to
  `feat/issue-209-svelte-perf-gate`; creating, editing or commenting on any
  GitHub issue.

### Stop conditions

Stop implementation and return to orchestrator if:

- step 0 does not reproduce the direction of P1 and P4: navigation is not
  slower by tens of milliseconds, or the verdict's style recalculation is
  not a few milliseconds at most;
- a proof fails on the verbatim copy, or cannot be run against the #213
  build without editing a file under `spikes/issue-210/` or
  `spikes/issue-206/`;
- a build hash printed by a proof is not the #213 build's;
- a change the gate needs alters a comparable capture or a document height,
  or would need anything listed as not allowed or out of scope. Report what
  it would save and what it would change; the owner decides;
- the gate would pass only by changing what a stamp measures, or by
  excluding runs;
- `proof_gate.py` cannot be made to run on the redesigned slice within the
  three permitted kinds of difference.

**Not a stop condition:** the gate still failing after the allowed means are
exhausted. That is the result. Finish the record as NO-GO.

Escalation route: `implementer → orchestrator → planner`.

## Implementer model justification

**Judgement rung.** The plan fixes the gate, the order of steps, the allowed
and excluded means, and the scope. It delegates real judgement inside them:
attributing 85 ms that no single cause explains, designing ablations that
isolate one cause, deciding when the allowed means are exhausted, and
reporting comparisons that sit inside one frame of noise without tilting
them. A Bounded implementer could apply a named fix; here there is not one.

`claude-opus-5-5` at `high` is a Judgement primary, built the slice under
test in #210, and runs in the owner's usual Claude runtime with no manual
cross-provider launch. `gpt-6.1-sol` at `high` is the equal alternative and
implemented #209's gate; the orchestrator may re-select.

## Likely findings

1. **A gate passed, or failed, by measuring something else.** A proof that
   ran against #210's build (see *Repository facts*); a hunk in
   `proof_gate.py` outside the three permitted kinds; a run dropped or a
   warm-up added; GO written on one passing invocation; a B2 or B3 result
   reported as a median only, hiding the frame-phase split.
2. **Attribution asserted, not shown.** A cause named from a profile with no
   ablation; a slice change committed before the attribution evidence; the
   `tailwind-merge` guess repeated as a finding; profile figures quoted as
   if they were gate timings.
3. **An excluded means under another name.** `contain` in a stylesheet rule;
   groups mounted after the `ready` stamp; an `{#await}` or timer that
   defers part of a card; a change that passes because fewer elements are in
   the document. The element count must stay 13,019 unless a change removes
   elements the proofs do not read, and then it is stated.
4. **The look changed without the owner.** A visual proof with no control,
   so byte differences are waved through as noise; a height change; a
   `class` attribute that differs after class strings are precomputed.
5. **Scope leakage and an overclaiming record.** An edit under
   `spikes/issue-210/`; tracked `node_modules` or `dist`, or the stray
   `spikes/issue-209/` staged; #206's tables rewritten; a NO-GO written as a
   verdict on Svelte or on the migration when it is a verdict on this slice
   as measured.

# Reusable implementer execution prompt

Implement issue #213 in `tonym999/vault-cleaner` using the handoff at the approved plan SHA `<plan_sha>` (the orchestrator fills this in at dispatch):

```text
git show <plan_sha>:handoffs/issue-213-implementation-plan.md
```

Read the entire handoff at that SHA, issue #213, issues #209 and #210 (including #210's "Performance constraints from #209"), tracker #138, `AGENTS.md`, `PLAN.md`, `docs/frontend-framework-decision.md`, `docs/evidence/issue-210/README.md` section 5, `spikes/issue-210/README.md`, `spikes/issue-210/run_proof.py`, `spikes/issue-206/proof_s15_scale.py`, the #209 plan and gate (`git show ee61b0790e4e1a8f8b928d3b452210fa6558f9b8:handoffs/issue-209-implementation-plan.md` and `...:spikes/issue-209/proof_gate.py`), the #209 worklog entries on that commit, the recent worklog (defined in `AGENTS.md`, *Worklog*), and current relevant code before editing.

Rules:
- work on the existing `feat/issue-213-redesigned-slice-timing-gate`, which already holds the plan commit; do not create another branch, rebase, or force-push, and record the branch head you start from as your attempt's starting SHA (the orchestrator keeps the ticket's review base, which a later attempt does not move);
- never edit `handoffs/issue-213-implementation-plan.md`;
- make the two verbatim copies (`spikes/issue-210/frontend`, and `proof_gate.py` from blob `a77c21f3f2826c735c49463f6ef4d305604e82da`) their own first commit and record its SHA;
- commit the attribution evidence before the first commit that changes a file under `spikes/issue-213/frontend/`;
- apply the plan's mechanical inclusion test to every hunk; this spike changes no file under `src/`, `tests/`, `scripts/`, `.github/`, `spikes/issue-210/`, `spikes/issue-206/`, `spikes/issue-137/`, `docs/evidence/issue-210/`, `docs/evidence/issue-206/`, or `pyproject.toml`, `.gitignore`, `PLAN.md`, `AGENTS.md`;
- add, remove or re-version no npm or Python package; install with `npm ci`; track no `node_modules` or build output; stage paths by name, never `git add -A` (an untracked `spikes/issue-209/` may be present and is not yours);
- use only the tracked fixtures under `tests/fixtures/`, including the sanitised `tests/fixtures/real/2026-09-01T-current/armor.csv`; never read `data/`, and never edit or regenerate anything under `tests/fixtures/real/`;
- follow the steps in order; run the gate proof after each change and keep a change only if it moved a gated comparison;
- report every gate invocation made for the record, complete or not; discard none;
- do not touch `feat/issue-209-svelte-perf-gate`; create, edit or comment on no GitHub issue;
- add a dated worklog entry file under `worklog/` (format in `AGENTS.md`, *Worklog*);
- run all verification commands:
  - `.venv/bin/ruff check src tests scripts`
  - `.venv/bin/ruff check spikes/issue-213`
  - `.venv/bin/pytest -q` (baseline: `1342 passed`; the count must not change)
  - `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`
  - in `spikes/issue-213/frontend`, from a clean `npm ci`: `npm run check`, `npm test`, `npm run build`
  - in `spikes/issue-210/frontend`: `npm ci && npm run build` (the visual proof and the hash comparison need the #210 build)
  - every proof command listed in `spikes/issue-213/README.md`
  - `python3 scripts/check_worklog.py --base origin/main`
  - `git diff --check origin/main...HEAD`
  - both inclusion-test commands, which must print nothing;
- commit and push the implementation branch with `Refs #213`; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. Finding where the time goes, designing the ablations, and deciding that the allowed means are exhausted are the work of this ticket, not an escalation. A NO-GO with the record complete is a finished ticket. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, provide the implementer → orchestrator handoff: starting, copy-commit, attribution-commit and head SHAs; the verdict in one sentence; all seven comparisons, slice beside production, for both baseline and both final invocations, and the total number of invocations made; every run's B2 and B3 values for the final invocations; the attribution, with the ablation behind each named cause; the step table (each change, what it moved, kept or dropped); the diff of `proof_gate.py` against the pinned blob; the build hashes each proof printed; the visual proof's result, or that the source is unchanged from the copy commit; every verification command with its output tail; anything not measured; and notable implementation choices.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
No production code changes, so the immediate blast radius is nil. The output
is the GO or NO-GO on the redesigned slice, which the frontend migration
waits on, and it rests on timings that have been got subtly wrong before:
#206's verdict stamp missed its largest cost, #209's supplemental check
covered two of four states, and each of #210's three review rounds found a
proof that could not see what it claimed to check. Here two of the seven
comparisons sit inside one frame of noise, and the runner has a known way to
test the wrong build. A fresh reviewer who reruns the gate twice on its own
checkout, reads the gate's diff against #209's blob hunk by hunk, and checks
each attribution claim against its ablation is the right check.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] Both inclusion-test commands print nothing; `git diff --stat <base>...HEAD -- src tests scripts .github spikes/issue-210 spikes/issue-206 spikes/issue-137 docs/evidence/issue-210 docs/evidence/issue-206 pyproject.toml .gitignore PLAN.md AGENTS.md` is empty.
- [ ] At the recorded copy commit, `diff -r --exclude=node_modules --exclude=dist spikes/issue-210/frontend spikes/issue-213/frontend` prints nothing and `git rev-parse <copy>:spikes/issue-213/proof_gate.py` is `a77c21f3f2826c735c49463f6ef4d305604e82da`. At the head, `package.json` and `package-lock.json` are byte-identical to #210's.
- [ ] Every hunk of `git diff a77c21f3f2826c735c49463f6ef4d305604e82da HEAD:spikes/issue-213/proof_gate.py` is one of the three permitted kinds; `RUNS`, the comparisons, the stamps, the sample window, the alternation and the pass rule are unchanged.
- [ ] `.venv/bin/pytest -q` still reports `1342 passed`; the browser suite passes unchanged.
- [ ] From a clean `npm ci`, the #213 type check, unit tests and build pass.
- [ ] The reviewer reran the runner for S1, S2, S3, S4, S5, S6, S15, the source scan, `proof_csp`, `proof_axe`, `proof_layout` and `proof_no_transition`. All pass, none skipped, no file under `spikes/issue-210/` or `spikes/issue-206/` differs from the base, and each printed the #213 build's hashes, which differ from #210's whenever the source does.
- [ ] The reviewer reran the gate proof twice. All seven comparisons are printed slice beside production; the record's GO or NO-GO follows the passing rule; the number of invocations reported matches the worklog.
- [ ] The record gives both baseline invocations and both final ones, and every run's B2 and B3 values for both pages, and says whether production's fall in two groups about a frame apart.
- [ ] The attribution commit precedes the first commit that changes `spikes/issue-213/frontend/`. Each named cause has an ablation with figures. Profile figures are labelled as proportions. What could not be attributed is stated.
- [ ] Each kept change has a gate transcript showing a gated comparison moved by more than the baseline spread; each dropped change is listed.
- [ ] No `content-visibility` or `contain` in the built stylesheet beyond what #210's has; every group is in the document and laid out at the `ready` stamp; the element count is 13,019 or the difference is explained; `proof_no_transition` passes.
- [ ] If the source differs from the copy commit: the visual proof ran with its control and its negative control, and every comparable capture and all four heights match. If any differ, the work stopped and the owner's decision is recorded.
- [ ] The decision record keeps #206's text and tables, adds the #213 subsection and the three short notes the plan lists, says NO-GO or GO for the redesigned slice as measured, and creates no issue.
- [ ] No `data/` path or unsanitised value appears in the evidence; every id shown carries the `1000` marker; no file under `tests/fixtures/real/` changed.
- [ ] Likely findings 1 to 5 were each checked.

# Dispatch comment draft

Planned #213 in [handoffs/issue-213-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/<plan_sha>/handoffs/issue-213-implementation-plan.md), approved at plan SHA `<plan_sha>`.

- **Implementer model & effort:** `claude-opus-5-5` at `high` (Judgement rung)
- **Implementation branch:** `feat/issue-213-redesigned-slice-timing-gate`
- **Likely findings:** a proof run against #210's build instead of #213's, or a gate hunk beyond the three permitted kinds; attribution named from a profile with no ablation, or a change made before it; an excluded means (containment, deferred mounting) under another name; a changed look passed off as capture noise; scope leakage into `spikes/issue-210/` and a NO-GO or GO that claims more than the transcripts.
