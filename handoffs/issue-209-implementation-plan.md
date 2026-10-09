# Issue #209 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#209 — M10: real-scale presentation performance gate for the Svelte slice`

**Milestone:** none assigned (no M10 milestone exists; `PLAN.md` has no M10 section)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Claude Code desktop session; the session does not report its native effort, so none is recorded)

**Implementation model selected:** `gpt-6.1-sol` at `high` (Judgement rung; justified below)

**Plan baseline:** `main` at `d139a05306828c0a4d7e9ded211408b346dd7768` (2026-10-09)

**Allocated branch:** `feat/issue-209-svelte-perf-gate` (this plan is its first commit)

The implementer must **not** open a pull request or edit this file. The branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Spike #206 recommended Svelte 5 + TypeScript + Vite as a **bounded
conditional**: on the tracked sanitised armor report the Svelte slice rendered
and repainted slower than the current page. This ticket is the gate that
decides it. Make a focused presentation-performance change to a copy of the
slice, re-run the whole-report comparison against the current page, and update
[docs/frontend-framework-decision.md](../docs/frontend-framework-decision.md)
to **GO** or **NO-GO** with the new evidence.

It is a spike. No production code changes, and nothing here ships.

## Context & Measurement

### What #206 recorded

[docs/frontend-framework-decision.md, "Real scale beside production"](../docs/frontend-framework-decision.md#real-scale-beside-production)
(lines 425-469) and
[spikes/issue-206/proof_s15_scale.py](../spikes/issue-206/proof_s15_scale.py).
Sanitised fixture `tests/fixtures/real/2026-09-01T-current/armor.csv`: 9 exact
and 65 same-stat groups, 158 member occurrences, 13,143 document elements in
the slice. Five-run medians at 1440 px, light, slice / production: navigation
to every group laid out 200.0 / 150.2 ms; acknowledgement to DOM repaint
17.9 / 10.3 ms.

### Planning measurements (2026-10-09)

Made at the plan baseline with the #206 build and harness unmodified, the same
fixture, Chromium as pinned, 1440 px, light, alternating fresh documents, one
machine. Only the tracked sanitised fixture was read. The scripts were
throwaway and are not in the repository; the method is stated so the
implementer's first step can reproduce each figure (see *Step 0*).

**Method.** S15's own `TIMING_JS` and `ARM_REPAINT_JS` stamps
([proof_s15_scale.py:62-116](../spikes/issue-206/proof_s15_scale.py#L62-L116)),
plus the DevTools protocol's `Performance.getMetrics` read through
`context.new_cdp_session(page)`. Deltas of `ScriptDuration`,
`RecalcStyleDuration`, `LayoutDuration` and `TaskDuration` were taken over two
windows: navigation (document start to S15's `frame` stamp) and verdict (just
before the key press to S15's `repaintFrame` stamp, then one more protocol
round trip).

**M1. Navigation, medians of 7 runs.**

| | Slice | Production |
| --- | --- | --- |
| S15 `ready` (every group laid out) | 214.0 ms | 162.3 ms |
| `/api/report` response end | 35.9 ms | 39.9 ms |
| Script | 71.6 ms | 24.9 ms |
| Layout | 74.3 ms | 51.1 ms |
| Style recalculation | 35.0 ms | 17.6 ms |
| Main-thread task time | 224.9 ms | 162.5 ms |

The gap is about 50 ms and has three parts: script (+47), layout (+23) and
style (+17). The report arrives at the same time on both pages.

**M2. One verdict, medians of 7 runs.**

| | Slice | Production |
| --- | --- | --- |
| S15 acknowledgement to DOM | 21.6 ms | 10.1 ms |
| S15 acknowledgement to next animation frame | 27.2 ms | 17.8 ms |
| Script | 25.5 ms | 4.1 ms |
| Layout | 14.1 ms | 9.4 ms |
| **Style recalculation** | **161.9 ms** | **3.3 ms** |
| Main-thread task time | 320.3 ms | 43.4 ms |

**M3. S15's verdict stamps do not see the largest cost.** A
`requestAnimationFrame` callback runs before that frame's style and layout.
S15 stamps `repaintFrame` inside one
([proof_s15_scale.py:112](../spikes/issue-206/proof_s15_scale.py#L112)), so
the style recalculation the acknowledged change causes falls after the stamp.
The 7 ms gap #206 reported is real; the 160 ms beside it was not measured.

**M4. Where the style cost comes from.** One DOM change at a time on the
loaded slice, then a forced style flush and two animation frames; medians of 6.

| Change | Style recalculation |
| --- | --- |
| One verdict button: `btn-disabled` class, `aria-disabled`, `aria-pressed`, or the pressed classes | 0.6 ms each |
| All 435 verdict buttons: `btn-disabled` class only | 87.3 ms |
| All 435 verdict buttons: `aria-disabled` only | 106.1 ms |
| All 435 verdict buttons: both, as the slice does | 92.8 ms |
| All 435 verdict buttons: the `disabled` property | 164.2 ms |
| All 435 verdict buttons: an attribute no rule mentions | 0.0 ms |
| One attribute on the list `<section>`, or on all 74 group articles | 0.0 ms |
| Status text; one member's verdict text and `data-verdict` | 1.7 ms; 1.6 ms |

[VerdictControls.svelte:24-27](../spikes/issue-206/frontend/src/components/VerdictControls.svelte#L24-L27)
binds `btn-disabled` and `aria-disabled` to `session.canMutate` on every
button. `canMutate` turns false when a request starts and true when it is
answered
([session.svelte.ts:51-53](../spikes/issue-206/frontend/src/lib/session.svelte.ts#L51-L53),
`:80`, `:88`), so each verdict flips all 435 buttons twice: about 90 ms each
time. Production disables its buttons too and pays 3.3 ms in total, so the
cost is in how the built stylesheet reacts to the change, not in the change
itself. The built `app.css` has 43 `:has(` selectors; which rule is
responsible was not isolated.

**M5. The projection is not where the time goes.** `duplicateGroups`
([view.ts:295-314](../spikes/issue-206/frontend/src/lib/view.ts#L295-L314))
over the real envelope (742,979 bytes) takes 0.33 ms warm in Node 24;
`JSON.parse` of the body takes 1.5 ms. What re-deriving costs is identity:
every adoption makes 74 new group objects and 158 new member objects
([session.svelte.ts:42](../spikes/issue-206/frontend/src/lib/session.svelte.ts#L42)),
so every binding in every card is re-evaluated. `#adopt` also replaces
`filters` with a new object on every adoption
([session.svelte.ts:140-150](../spikes/issue-206/frontend/src/lib/session.svelte.ts#L140-L150)).

**M6. Feasibility probe, not a fix.** The built stylesheet was served with one
rule appended:
`article[data-group]{content-visibility:auto;contain-intrinsic-size:auto 800px}`.
Medians of 5: `ready` 127.7 ms against production's 151.2 ms in the same
invocation; navigation script 64.5, layout 29.2, style 6.3 ms; verdict style
8.1 ms, main-thread task time 47.8 ms; acknowledgement to DOM 18.4 ms, still
behind production. No S15 correctness, focus, layout or accessibility check
was run with the rule, and scrolling cost was not measured.

**What follows.**

- The issue's starting point, a report-scoped projection with updates only to
  verdict-dependent presentation, addresses the acknowledgement-to-DOM gap
  (script) and nothing else. It is necessary and not sufficient.
- The in-flight flip of 435 buttons is the largest single cost and has its
  own fix.
- The navigation gap is mount, layout and style of 13,143 elements. No
  projection change reaches it.
- The gate has to measure settled frames, or it can pass with the 160 ms
  still there.

### Repository facts that shape the work

- `spikes/issue-206/` is the evidence for a merged ticket: the transcripts in
  [docs/evidence/issue-206/README.md](../docs/evidence/issue-206/README.md)
  are reruns of its code, and S12 and S14 count and patch its source. Editing
  it would invalidate them.
- The #206 proofs find the build through two module globals read at call
  time: `spike_app.FRONTEND_DIST`
  ([spike_app.py:50](../spikes/issue-206/spike_app.py#L50), used at `:181`)
  and `harness.FRONTEND_DIST` / `harness.FRONTEND`
  ([harness.py:24-37](../spikes/issue-206/harness.py#L24-L37), used by
  `require_build` at `:91-100`). A runner that sets them before importing a
  proof can run that proof unchanged against another build.
- `proof_s6_layout.py --screenshots` and `proof_s15_scale.py --screenshots`
  write into `docs/evidence/issue-206/`.
- The root `.gitignore` ignores `dist/` but not `node_modules/`.
- CI lints `src tests scripts` only; nothing in CI runs a spike.
- Baseline at the plan commit: `.venv/bin/pytest -q` reports `1342 passed`;
  `.venv/bin/ruff check src tests scripts spikes/issue-206` passes.
- Node `v24.20.0` is installed; `spikes/issue-206/frontend` builds from its
  committed lockfile.
- `python3 scripts/check_model_roster.py` reports 2 stale rows (both Gemini).
  The `gpt-6.1-sol` and `claude-opus-5-5` rows are current.

## Dependencies and assumptions

- **#206 is merged** (PR #208, `d139a05`). #209 is open, labelled
  `enhancement`, on the project with status `Todo`, tracked under #138 (open).
- **The issue's figures are current.** Its table matches the decision record
  at the baseline. Planning runs on the same machine gave 214 / 162 ms and
  21.6 / 10.1 ms: the same direction, a little slower in absolute terms.
- **Divergence 1: the issue's starting point is not enough.** The issue says
  to start with a report-scoped projection and selective verdict updates, and
  to measure paging or virtualisation "only if that is not enough". M5 and M1
  show the projection cannot close the navigation gap. This plan keeps the
  issue's order, then allows two further focused steps (the in-flight flip,
  and CSS rendering containment) before paging or virtualisation. All DOM
  stays in the document under both, so offline filtering, scope counts,
  keyboard order and every per-member value are untouched. Paging and
  virtualisation remain the issue's last resort and are a stop condition
  here, because neither can pass S15's all-group checks unchanged.
- **Divergence 2: the gate is wider than the issue's acceptance criterion.**
  The issue asks that "the same five-run comparison" no longer show the slice
  slower. Per M3 that comparison cannot see style and layout after the
  acknowledged change. This plan keeps S15's four stamps as gate A, unchanged,
  and adds settled-frame measures as gate B. **Approving this plan approves
  gate B as part of the acceptance bar.** If the owner wants the issue's bar
  only, that is an amendment before dispatch.
- **Divergence 3: the issue leaves the directory to the plan.** The work goes
  in a new `spikes/issue-209/`; `spikes/issue-206/` is frozen.
- **#210 (redesign the slice, dark-first) is open and not a dependency.** The
  owner has not accepted the slice's visual design (worklog,
  `2026-10-09-issue-206-fix-round-4.md`). This ticket does not redesign
  anything: the optimised slice must look the same as #206's. A redesign will
  change markup and CSS, so the gate proof must stay rerunnable for it; the
  record says so.
- **#211 (test triage)** is unrelated.
- **Assumption:** timings come from one machine and one browser, as in #206.
  The gate compares the two pages under the same conditions in the same
  invocation; it claims nothing about absolute speed.

## Proposed Plan & Scope

### The spike directory

#### [NEW] `spikes/issue-209/frontend/`

A copy of `spikes/issue-206/frontend/` (source, `index.html`, configuration,
`package.json`, `package-lock.json`), then changed.

- **The first implementation commit is the verbatim copy and nothing else.**
  At that commit
  `diff -r --exclude=node_modules --exclude=dist spikes/issue-206/frontend spikes/issue-209/frontend`
  prints nothing. Record its SHA. Every later change to the slice is then
  readable as a diff from that commit.
- No dependency is added, removed or re-versioned. `package.json` and
  `package-lock.json` stay byte-identical to #206's.

#### [NEW] `spikes/issue-209/.gitignore`

`node_modules/` and `dist/`, as in `spikes/issue-206/.gitignore`.

#### [NEW] `spikes/issue-209/` Python modules

Names are the implementer's; these roles are required.

- **A runner for the #206 proofs.** It sets the build location (*Repository
  facts*) to `spikes/issue-209/frontend` and runs one #206 proof module
  unchanged. It accepts a proof name from a fixed list and no other argument,
  so `--screenshots` cannot be passed and no path can be supplied. No file
  under `spikes/issue-206/` is edited.
- **The gate proof** (below).
- **The traversal proof** (below), required when step 3 uses rendering
  containment.

Each proof prints `RESULT: PASS` or `RESULT: FAIL` and exits non-zero on
failure, like #206's. A browser proof fails when Chromium is missing; it never
skips.

#### [NEW] `spikes/issue-209/README.md`

What the directory is, that nothing ships, the build commands, and one command
per proof.

### The gate

Same conditions as S15: the tracked sanitised fixture uploaded once, one
authenticated session, All groups, no Class selection, 1440 px, light, fresh
documents, the two pages alternating which goes first, five runs each, medians.
"Slice" is the #209 build; "production" is the current page at `/`.

**Gate A: S15's stamps, unchanged.** Run `proof_s15_scale.py` through the
runner. The slice's median is less than or equal to production's for each of:

1. navigation to every group laid out;
2. navigation to the next animation frame;
3. acknowledgement to DOM repaint;
4. acknowledgement to the next animation frame.

**Gate B: settled frames.** Measured by the gate proof, with production beside
the slice. A frame is *settled* at the second of two nested
`requestAnimationFrame` callbacks: the first frame's style, layout and paint
work on the main thread has finished by then. The slice's median is less than
or equal to production's for each of:

5. navigation to settled, taken from S15's `ready` condition;
6. key press to settled, taken from the acknowledged `aria-pressed` change;
7. acknowledgement to settled.

The gate proof also prints, for both pages and both windows, the
`Performance.getMetrics` deltas used in M1 and M2. Those are diagnostic: they
explain a result and are not themselves gated.

**Passing.** A gate passes when every one of its comparisons holds in **each
of two consecutive complete invocations**. Every invocation made for the
record is reported, with its count; none is discarded. A comparison that holds
in one invocation and fails in the other is a failure with a measured gap.

**Gate C: correctness is unchanged.** Through the runner, against the #209
build, all pass with no proof file edited: S1, S2, S3, S4, S5, S6, S13 and
S15, plus `check_source.py`'s rules applied to the #209 source. From
`spikes/issue-209/frontend`, after a clean `npm ci`: the type check, the unit
tests and the build. The slice still has no hand-written DOM construction or
repaint outside component markup; the two focus effects in `App.svelte` remain
the only direct DOM access.

**Gate D: it looks the same.** Captures of the top 2,400 px of the sanitised
report at 1440 and 390 px, light and dark, from the #206 build and the #209
build in the same run, are identical. Any difference is listed in the record
with its cause. No new image is committed unless one is needed to show a
difference. Use no new Python dependency for the comparison.

### The steps, in order

Run the gate proof after every step and record the result, so the evidence
shows what each change bought. Keep a change only if it moved a gated
comparison; take out one that did not.

**Step 0: baseline.** With the verbatim copy, reproduce M1 to M4 with the gate
proof and record them. This is the "before" column.

**Step 1: identity-stable projection (the issue's starting point).** After an
adoption, a group or member whose presented values did not change is the
**same object** it was before, so Svelte re-evaluates only what depends on the
changed member.

- Reuse is by **value equality** between the old and the new view. Do not key
  a cache on `report_revision`, `verdict_revision`, `fingerprint` or
  `reportKey`. #206's H3 depends on this: a finalise changes `state` and
  `override_status` and moves neither revision
  ([session.svelte.ts:4-9](../spikes/issue-206/frontend/src/lib/session.svelte.ts#L4-L9)).
- The whole envelope is still adopted on every answer and is still the only
  source of what is shown.
- `filters` keeps its identity when reconciliation changes nothing.
- Whether Svelte's keyed `{#each}` actually skips an unchanged item is to be
  measured, not assumed. If stable identity alone does not cut the script
  time, find out what still re-runs before adding machinery.
- Unit tests, in the #209 frontend: after adopting an envelope that differs
  in one verdict, every other member view and every unaffected group view is
  the identical object, and the affected member shows the new verdict; a
  changed `override_status` or `state` with both revisions unchanged is fully
  reflected; a changed snapshot under an unchanged revision pair is fully
  reflected.

**Step 2: the in-flight flip.** Bring the cost of switching the verdict
buttons off and on down to production's order of magnitude (M4).

- What stays, because the design contract binds it
  ([docs/review-ui-design-contract.md, section 5.11](../docs/review-ui-design-contract.md)):
  while a request is in flight, when the session is frozen and when the
  server is not connected, every verdict button is off and says so to
  assistive technology, and the focused button is the same node before,
  during and after. S3, S4 and S5 assert this and must pass unchanged, so each
  button still carries `aria-disabled="true"` when off.
- First isolate which stylesheet rule makes the flip expensive, and record
  it. Then choose the smallest change that removes the cost.
- The off state must look as it does now (gate D covers the idle state; add a
  capture of the in-flight state from both builds to the same comparison).

**Step 3: the load path.** Attribute the remaining navigation gap to script,
layout and style with the diagnostic metrics, then reduce it. Allowed means:

- stylesheet changes that leave computed presentation unchanged;
- component and markup changes that leave unchanged everything the #206
  proofs read (`data-*` hooks, text, roles, names, tab order) and gate D;
- CSS rendering containment of whole groups (`content-visibility` with
  `contain-intrinsic-size`, or `contain`), with every group still in the
  document.

If rendering containment is used, the record must say plainly that
off-screen groups are then rendered when they approach the viewport, not at
load, and the **traversal proof** is required. It reports, slice beside
production:

- scrolling from top to bottom in viewport-height steps, waiting for a
  settled frame at each: the largest step, the total, and the number of steps
  with a main-thread task over 50 ms (the Long Tasks threshold). The slice
  must have none;
- navigation-to-settled plus the traversal total, for both pages, so the
  record shows the deferred work and not only the first screen;
- document height before and after the traversal, and the viewport position
  of a mid-page element across it;
- a jump to the last control by keyboard: it is focused, visible, and its
  group fully rendered;
- that the axe run and the contrast check in S13 and S15 examined as many
  elements as they do on the #206 build.

**Step 4 is not built.** If gates A and B do not pass after steps 1 to 3,
stop (see *Stop conditions*).

### Decision record

#### [MODIFY] [docs/frontend-framework-decision.md](../docs/frontend-framework-decision.md)

- **Status and section 1:** the recommendation becomes **GO** or **NO-GO**,
  stated first, with the date and a link to #209's evidence. H5's row gets its
  result. GO requires gates A, B, C and D. With a measured gap remaining the
  record says **NO-GO**, states the gap, and notes that the issue lets the
  owner accept a gap explicitly; the implementer does not write GO on a
  failing gate.
- **Section 6, "Real scale beside production":** keep #206's table as the
  record of what was found. Add what #209 found (M3 to M5 as re-measured),
  the step-by-step table, the final gate tables from both invocations, and
  what each change was.
- **Section 6, lines and H8:** state how many non-blank lines the optimisation
  added to the slice, counted the way S12 counts, and whether the H8 verdict
  still holds.
- **Section 8:** S15's verdict stamps exclude post-acknowledgement style and
  layout; timings are still one machine, one browser, one width and scheme;
  the result is for the #206 visual design and must be re-measured after #210;
  with rendering containment, what is deferred and what was not measured (for
  example in-page find, other browsers).
- **Section 9:** draft 5 is marked as carried out by #209, with its outcome.
  Draft 2 gains the patterns the migration must carry (whatever steps 1 to 3
  kept) and draft 7 names the gate and traversal proofs as the ones to repeat.
  No issue is created or edited.

### Evidence and worklog

#### [NEW] `docs/evidence/issue-209/README.md`

Per `AGENTS.md`, *Conventions*: verbatim command transcripts, plain text, each
fence reproducible on its own. It holds the step 0 baseline, one gate-proof
transcript per kept step, both final invocations, the runner transcripts for
gate C, the gate D result, and the traversal proof when required. Only the
tracked sanitised fixture is read; every id shown carries the `1000` marker.

#### [NEW] `worklog/YYYY-MM-DD-issue-209-implementation.md`

What was done, the decisions made, the gate result, anything surprising, what
was not measured, and the copy commit's SHA.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- every changed path is under `spikes/issue-209/` or `docs/evidence/issue-209/`,
  or is `docs/frontend-framework-decision.md`, or is a new
  `worklog/*-issue-209-*.md` entry; and
- it reduces presentation work on load or on verdict adoption, or measures
  it, or records the result; and
- it changes nothing the slice shows, says to assistive technology, or sends
  to the server.

Both commands print nothing (`<base>` is the ticket's review base):

```bash
git diff --name-only <base>...HEAD | grep -vE '^(spikes/issue-209/|docs/evidence/issue-209/|docs/frontend-framework-decision\.md$|worklog/[0-9]{4}-[0-9]{2}-[0-9]{2}-issue-209-[a-z0-9-]+\.md$)'
git ls-files spikes/issue-209 | grep -E '(^|/)(node_modules|dist)/'
```

Worked examples:

- **IN SCOPE:** reusing an unchanged member view object across adoptions, with
  a unit test for identity.
- **IN SCOPE:** a stylesheet override in the #209 `app.css` that makes the
  `aria-disabled` flip cheap and leaves the buttons looking the same.
- **IN SCOPE:** `content-visibility: auto` on group cards, with the traversal
  proof and the record saying what is deferred.
- **IN SCOPE:** a runner that points #206's `proof_s15_scale.py` at the #209
  build without editing it.
- **OUT OF SCOPE:** any edit under `spikes/issue-206/`, `spikes/issue-137/`,
  `src/`, `tests/`, `scripts/`, `.github/`, or to `pyproject.toml`,
  `.gitignore`, `PLAN.md`, `AGENTS.md` or `docs/evidence/issue-206/`.
- **OUT OF SCOPE:** changing colours, spacing, card structure or wording to
  improve the design (#210), even where it would also be faster.
- **OUT OF SCOPE:** dropping `aria-disabled` from the buttons while a request
  is in flight, or removing a per-member value, a filter or a count.
- **OUT OF SCOPE:** a new route, a server-side view-model, a changed request,
  or a cache keyed on a revision.
- **OUT OF SCOPE:** a new npm or Python package, including a virtualisation
  library.
- **OUT OF SCOPE:** fixing the "known limits" listed in
  `worklog/2026-10-09-issue-206-fix-round-4.md`, unless one blocks a gate.
- **OUT OF SCOPE:** creating, editing or commenting on any GitHub issue.

### Stop conditions

Stop implementation and return to orchestrator if:

- step 0 does not reproduce the direction of M1 to M4 (in particular, the
  style recalculation on a verdict is not tens of milliseconds);
- gates A and B do not both pass after steps 1 to 3. Report the measured gap
  per comparison. Do not build paging or virtualisation; a short measurement
  of what either would save may be included, labelled as not built;
- a change that would pass a gate needs anything listed as out of scope, or
  would sacrifice comparison information, focus, offline filtering, scope
  counts or the unchanged CSP;
- a #206 proof cannot be run against the #209 build without editing a file
  under `spikes/issue-206/`;
- a #206 proof fails on the verbatim copy;
- gate D cannot hold for a change the gates need;
- the gate would pass only by changing what a stamp measures, by excluding
  runs, or by a comparison that is within run-to-run noise in one invocation
  and fails in the other.

Escalation route: `implementer → orchestrator → planner`.

## Implementer model justification

**Judgement rung.** The plan fixes the gate, the order of steps, the
invariants and the scope. It delegates real judgement inside them: isolating
which stylesheet rule makes the flip expensive, deciding whether stable
identity is enough for Svelte's keyed blocks or what still re-runs, choosing
among the allowed load-path means from attribution, and reporting timings
honestly when they are near the line. A Bounded implementer could apply a
named fix; here the fix has to be found from measurement.

`gpt-6.1-sol` at `high` is a Judgement primary and implemented S15, which
this work extends. The owner ran the last #206 round on it to save Claude
usage (worklog, `2026-10-04-issue-206-planning.md`). `claude-opus-5-5` at
`high` is the equal alternative; the orchestrator may re-select. In a Claude
runtime `gpt-6.1-sol` is a manual cross-provider launch.

## Likely findings

1. **A gate passed by measuring less.** A stamp moved earlier; a
   `requestAnimationFrame` stamp presented as a settled frame; rendering
   containment making "every group laid out" cheap with no traversal figures;
   an axe or contrast pass that covered fewer elements; runs dropped or
   re-rolled until the medians agreed.
2. **Stale state through the new reuse.** Identity reuse or a cache keyed on a
   revision, so a finalise elsewhere, a changed `override_status`, or a
   changed snapshot is not shown. S4 through the runner and the three unit
   tests in step 1 are the check.
3. **A weakened in-flight state.** The buttons no longer `aria-disabled`
   while a request is in flight or when frozen, or focus moving to `<body>`,
   to make the flip cheap.
4. **Scope leakage.** An edit under `spikes/issue-206/`; a visual change that
   belongs to #210; a dependency change; `--screenshots` overwriting #206's
   images; tracked `node_modules` or `dist`; a first commit that is not a
   verbatim copy.
5. **A record that says more than the transcripts.** GO written with a
   comparison failing in one invocation; the deferred rendering not stated;
   the added lines and the H8 verdict not restated; #206's original table
   overwritten instead of kept.

# Reusable implementer execution prompt

Implement issue #209 in `tonym999/vault-cleaner` using the handoff at the approved plan SHA `<plan_sha>` (the orchestrator fills this in at dispatch):

```text
git show <plan_sha>:handoffs/issue-209-implementation-plan.md
```

Read the entire handoff at that SHA, issue #209, tracker #138, `AGENTS.md`, `PLAN.md`, `docs/frontend-framework-decision.md`, `docs/evidence/issue-206/README.md`, `spikes/issue-206/README.md`, `spikes/issue-206/proof_s15_scale.py`, `docs/review-ui-design-contract.md` section 5.11 and section 7, the recent worklog (defined in `AGENTS.md`, *Worklog*), and current relevant code before editing.

Rules:
- work on the existing `feat/issue-209-svelte-perf-gate`, which already holds the plan commit; do not create another branch, rebase, or force-push, and record the branch head you start from as your attempt's starting SHA (the orchestrator keeps the ticket's review base, which a later attempt does not move);
- never edit `handoffs/issue-209-implementation-plan.md`;
- make the verbatim copy of `spikes/issue-206/frontend` its own first commit and record its SHA;
- apply the plan's mechanical inclusion test to every hunk; this spike changes no file under `src/`, `tests/`, `scripts/`, `.github/`, `spikes/issue-206/`, `spikes/issue-137/`, `docs/evidence/issue-206/`, or `pyproject.toml`, `.gitignore`, `PLAN.md`, `AGENTS.md`;
- add, remove or re-version no npm or Python package; install with `npm ci`; track no `node_modules` or build output;
- use only the tracked fixtures under `tests/fixtures/`, including the sanitised `tests/fixtures/real/2026-09-01T-current/armor.csv`; never read `data/`, and never edit or regenerate anything under `tests/fixtures/real/`;
- follow the steps in order, run the gate proof after each, and keep a change only if it moved a gated comparison;
- report every gate invocation made for the record; discard none;
- create, edit or comment on no GitHub issue;
- add a dated worklog entry file under `worklog/` (format in `AGENTS.md`, *Worklog*);
- run all verification commands:
  - `.venv/bin/ruff check src tests scripts`
  - `.venv/bin/ruff check spikes/issue-209`
  - `.venv/bin/pytest -q` (baseline: `1342 passed`; the count must not change)
  - `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`
  - in `spikes/issue-209/frontend`, from a clean `npm ci`: `npm run check`, `npm test`, `npm run build`
  - in `spikes/issue-206/frontend`: `npm ci && npm run build` (gate D and the baseline need the #206 build)
  - every proof command listed in `spikes/issue-209/README.md`, including the runner for S1, S2, S3, S4, S5, S6, S13, S15 and the source rules
  - `python3 scripts/check_worklog.py --base origin/main`
  - `git diff --check origin/main...HEAD`
  - both inclusion-test commands, which must print nothing;
- commit and push the implementation branch with `Refs #209`; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. Finding the cause of each cost and choosing the smallest change inside the allowed means is the work of this ticket, not an escalation. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, provide the implementer → orchestrator handoff: starting, copy-commit and head SHAs; the recommendation in one sentence; gates A to D each with its result and evidence fence; all seven comparisons, slice beside production, for both final invocations, and the total number of invocations made; the step table (what each step changed and what it moved, including changes tried and taken out); the stylesheet rule found in step 2; whether rendering containment is used and, if so, the traversal figures; lines added to the slice; every verification command with its output tail; anything not measured; and notable implementation choices.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
No production code changes, so the immediate blast radius is nil. The output
is the GO or NO-GO that releases a frontend migration, and it rests on
timings that are easy to get subtly wrong: #206's own verdict stamp missed the
largest cost (M3), and the most effective load-path change defers work
instead of removing it. A fresh reviewer who reruns the gate on its own
checkout, reads what each stamp measures, and probes the finalise and
in-flight cases is the right check. The identity reuse also touches the
stale-state behaviour #137's and #206's reviews both found defects in.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] Both inclusion-test commands print nothing; `git diff --stat <base>...HEAD -- src tests scripts .github spikes/issue-206 spikes/issue-137 docs/evidence/issue-206 pyproject.toml .gitignore PLAN.md AGENTS.md` is empty.
- [ ] At the recorded copy commit, `diff -r --exclude=node_modules --exclude=dist spikes/issue-206/frontend spikes/issue-209/frontend` prints nothing; at the head, `package.json` and `package-lock.json` are byte-identical to #206's.
- [ ] `.venv/bin/pytest -q` still reports `1342 passed`; the browser suite passes unchanged.
- [ ] From a clean `npm ci`, the #209 type check, unit tests and build pass.
- [ ] The reviewer reran the runner for S1, S2, S3, S4, S5, S6, S13 and S15 and the source rules against the #209 build; all pass, no #206 proof file differs from the base, and no browser proof skipped.
- [ ] The reviewer reran the gate proof twice. Each of the seven comparisons is printed slice beside production; the record's GO or NO-GO follows the passing rule; the number of invocations reported matches what the worklog says was run.
- [ ] Gate B's stamps are taken at the second of two nested animation frames, from the same start points the plan names; S15's stamps are unchanged. The diagnostic metrics show the verdict style recalculation is no longer tens of milliseconds.
- [ ] Step 0's transcript reproduces the direction of M1 to M4, and the step table shows a gate-proof result after every kept step.
- [ ] Identity reuse is by value equality; no cache is keyed on a revision, fingerprint or `reportKey`. The three step 1 unit tests exist and fail when the reuse is made unconditional.
- [ ] While a request is in flight and when frozen, every verdict button has `aria-disabled="true"`, and the focused button is the same node throughout (S3, S4, S5 through the runner).
- [ ] The slice's direct DOM access is still only the two focus effects in `App.svelte`.
- [ ] Gate D: the eight idle captures and the in-flight capture match between the two builds, or each difference is listed with its cause.
- [ ] If rendering containment is used: the record states that off-screen groups render on approach; the traversal proof ran with production beside the slice, shows no step over 50 ms, reports navigation-plus-traversal totals, document height and position stability and the keyboard jump; and the axe and contrast element counts match the #206 build's.
- [ ] The decision record keeps #206's original real-scale table, adds #209's, restates lines added and the H8 verdict, updates sections 1, 8 and 9 as the plan lists, and creates no issue.
- [ ] No `data/` path or unsanitised value appears in the evidence; every id shown carries the `1000` marker; no file under `tests/fixtures/real/` changed.
- [ ] Likely findings 1 to 5 were each checked.

# Dispatch comment draft

Planned #209 in [handoffs/issue-209-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/<plan_sha>/handoffs/issue-209-implementation-plan.md), approved at plan SHA `<plan_sha>`.

- **Implementer model & effort:** `gpt-6.1-sol` at `high` (Judgement rung), manual cross-provider launch from a Claude runtime
- **Implementation branch:** `feat/issue-209-svelte-perf-gate`
- **Likely findings:** a gate passed by measuring less (an early stamp, deferred rendering with no traversal figures, dropped runs); stale state through identity reuse or a revision-keyed cache; a weakened in-flight disabled state; scope leakage into `spikes/issue-206/`, the visual design or the dependency tree; a record that claims more than its transcripts.
