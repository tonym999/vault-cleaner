# 2026-10-10 — #210 implementation: direction D built, stopped on four proof conflicts

Work on `feat/issue-210-armor-duplicates-redesign` only. The approved plan
(`a0069201bb3adf25a1e6ff451b39c9579118ef52`) is unedited. No PR, no issue
comment or state change. No `data/` file was read: synthetic fixtures and the
tracked sanitised armor fixture only. Refs #210.

**Status: stopped at a plan stop condition.** The design is built and most
proofs pass, but four #206 proofs cannot pass unedited for reasons that are
about #206's daisyUI markup and layout, not about this slice's behaviour. The
plan allows one oracle adaptation and makes any other a stop. See *Stop*.

## Dispatch record

- The owner approved plan SHA `a006920` and authorised implementation in the
  planning session. The dispatch comment on the issue was not authorised and
  was not posted.
- Review base and this attempt's starting SHA: `a006920`.
- Implementer, planned and actual: Anthropic `claude-opus-5-5` (Claude Code
  desktop; the session does not report its native effort). No re-selection.
- **The planning session implemented.** The owner named Claude as implementer
  and no separate orchestrator session was started, so this session did not
  review its own work and no orchestrator review has happened.
- Issue #210 open, project status `Todo`.

## Commits

- `e6ffc11` verbatim copy of `spikes/issue-206/frontend` (28 files with the
  `.gitignore`; `diff -r -x node_modules -x dist` printed nothing).
- `d46f7bf` #209's value-retention change, `git diff 088218b a8da543` on
  `lib/`, applied unchanged: 3 files, +82/-5. Type check clean, 35 tests pass.
- The redesign commit that carries this entry.

## What was built

Direction D, on the full report: a container per kind with a sticky heading;
a group card with a six-cell stat strip in fixed order; pieces as columns with
only the differing fields as rows; one "Tuned stat" row with a six-box marker;
the kept piece as a tinted column; a "Same on both" line. Layout switches by
the group's own width (container queries), per piece count: columns for pairs
and triples at 390 px, one block per piece for four or more.

Page height on the real fixture: 28,423 px at 1440 and 56,050 px at 390
(#206: about 61,000 and 101,000).

Captures: `docs/evidence/issue-210/captures/`, real fixture in dark and light
at 1440 and 390 px (viewport, section boundary, a triple, a group of four),
plus the two synthetic cases in dark. Written by `spikes/issue-210/capture.py`.

## The shadcn-svelte trial

- **Added, pinned:** `tailwind-variants` 3.3.1 (MIT, 420 kB installed),
  `tailwind-merge` 3.7.0 (MIT, 1,128 kB), `clsx` 2.1.1 (MIT, 48 kB).
  **Removed:** `daisyui`.
- **Not added:** `bits-ui` and the `shadcn-svelte` CLI. Nothing here needed a
  headless widget, so the approved `bits-ui` was left out. The CLI was run
  once, from #206's existing probe install in a scratch copy, to generate
  badge, card and toggle for reading.
- **Used:** shadcn's button and badge, as `components/ui/button.svelte` and
  `badge.svelte` (98 lines with `cn.ts`). Their variant tables are as
  generated. Three edits, each forced: the `ref` binding is removed because
  the source scan allows `bind:this` only in named places; `disabled` is
  removed because it drops focus (S5); the badge's fixed height and nowrap
  are overridden because a status must wrap at 390 px.
- **Dropped, with reasons:**
  - **Toggle.** Bits UI's toggle sets the native `disabled` attribute
    (`toggle.svelte.js:32`), owns its pressed state, and would be 435
    component instances. Verdict buttons are native buttons carrying shadcn's
    ghost-button classes, computed once per module.
  - **Card.** Its padding and gap model fights rows that run edge to edge.
  - **Select.** The proofs read `select[data-facet]`; it stays native.
  - **The CLI's `cn` package** (shadcn-svelte 1.7 generates `import from
    "cn"`). It is not on the approved list; `cn.ts` uses `clsx` and
    `tailwind-merge`, which are.
  - **The preset's theme, web font and `tw-animate-css`.** The palette is
    direction D's, under shadcn's variable names.
- **Every generated component carries a transition** (`transition-all` on
  button and badge). Verdict controls and kind filters override it with
  `transition-none`.
- **Size:** built script 144.1 kB (#206: 64.2 kB), stylesheet 30.5 kB (#206:
  57.0 kB). The script growth is `tailwind-merge` and `tailwind-variants`.
- **Honest summary:** on this surface shadcn-svelte contributed class
  conventions for buttons and badges and nothing else. It cost 80 kB of
  script for that.

## The cheap-to-change report

From the carry-forward commit `d46f7bf` to the redesign commit
(`git diff --numstat`):

| Bucket | Files | Added | Removed |
| --- | --- | --- | --- |
| Components and stylesheet | 12 | 1,020 | 288 |
| shadcn-derived `components/ui/` | 3 | 98 | 0 |
| Typed logic (`lib/view.ts`) | 1 | 18 | 0 |
| Logic tests | 1 | 31 | 1 |
| `package.json` and lockfile | 2 | 40 | 12 |
| Proof tooling (`run_proof.py`, `proof_no_transition.py`, `capture.py`) | 3 | 359 | 0 |

The logic change is two pure helpers, `isKept` and `tunedStatMerged`, with
four tests (39 pass). No existing logic line changed. The claim under test
holds: the redesign was components and stylesheet.

## Proof results

Through `spikes/issue-210/run_proof.py`, #206's proofs unedited:

| Proof | Result |
| --- | --- |
| S1 parity | PASS |
| S2 hostile values | PASS |
| S3 acknowledged verdicts | PASS |
| S4 lifecycle | PASS |
| S5 focus | PASS |
| S6 layout | PASS, but see *Stop* item 4 |
| `check_source.py` | PASS |
| S7 CSP | **Does not run**: see *Stop* item 1 |
| S13 axe and contrast | **Does not run**: see *Stop* item 2 |
| S15 real scale | **FAIL**: see *Stop* items 2 and 4 |
| `proof_no_transition.py` (new) | PASS |

- **The one allowed adaptation** is `merge_tuned_stat` in `run_proof.py`. It
  drops the separate `tuning_stat` requirement only for a same-stat group
  whose every piece agrees, and leaves the oracle untouched otherwise. S15's
  parity then makes 3,261 assertions per width against #206's 3,401: the
  difference is the 140 merged values.
- **No transition:** 435 verdict buttons, none with a transition or
  animation, in both schemes; no rule in the built stylesheet mentions
  `aria-disabled`; the negative control (a 0.2 s transition added through the
  CSSOM) is detected on 435 of 435.
- **Style recalculation over one verdict:** median 1.4 ms over five runs
  (#209 measured 138.7 ms on #206, 3.1 ms on production). Recorded, not gated.

Repository checks on the redesign: `ruff check src tests scripts` clean;
`pytest -q` 1342 passed (34.92 s); the required browser suite 16 passed, 3
deselected (12.27 s); `git diff --check origin/main...HEAD` clean; in
`frontend/`, `npm run check` 0 errors and 0 warnings, `npm test` 39 passed,
`npm run build` clean.

## Stop: four proofs that cannot pass unedited

1. **S7 looks for daisyUI's `.btn`.** `proof_s7_csp.py:144` reads
   `getComputedStyle(document.querySelector(".btn"))` to show the stylesheet
   applied. The slice has no `.btn`, so the proof throws.
2. **S13 assumes daisyUI's contrast gaps and cascade.** It prints the lowest
   ratio among nodes axe could not judge and crashes when there are none
   (`proof_s13_axe.py:129`); here axe judges every node. Its negative control
   (`focus_contrast.py:102`) finds primary controls by `btn-primary` and
   expects daisyUI's layered rule to shrink the outline to 2 px. S15 calls
   the same code and crashes at the same line.
3. **Run as a diagnostic, outside the committed proofs,** S13's own axe
   script and focus lap report: no violation in any state, width or scheme on
   the synthetic and real fixtures; 444 of 444 focus stops with the 3 px
   outline; lowest focus contrast 4.00:1 (frozen controls, light). The run
   found one real defect, fixed: the role word on a filled stat cell was under
   4.5:1 in dark, on 74 nodes. Twice axe returned one "incomplete" node right
   after a scheme switch; it did not reproduce in isolation.
4. **S6 and S15 assert that pieces sit in one column at every width**
   (`proof_s6_layout.py:140`, `proof_s15_scale.py:353`). That is #206's
   layout; the issue and direction D put pieces side by side. S6 passes only
   because a piece is `display: contents` and has no box to measure, so its
   pass on that one measure says nothing. S15 fails at 390 px, where groups
   of four have boxes and pairs do not. With S15's axe step skipped as a
   diagnostic, those two layout lines were its only failures.

What is needed is a plan amendment, approved by SHA, that says which of these
may be adapted and how. A proposal is in the completion handoff.

## S15 timings (diagnostic run, axe step skipped; recorded, not gated)

Medians of five alternating runs, 1440 px light, slice / production:
navigation to all groups laid out 260.5 / 162.3 ms; next frame 274.3 / 168.7;
acknowledgement to DOM 7.4 / 12.4 ms; next frame 8.8 / 25.0; DOM elements
13,018 / 17,138.

- **A verdict is now faster than production.** #206 was 17.5 / 10.8.
- **First render is slower than #206** (209.5 ms there). Not investigated.
  The likely cost is a `tailwind-merge` call per badge instance; the verdict
  buttons already avoid it. The timing gate is a follow-up by owner decision.

## Decisions worth knowing

- **Busy treatment.** A request in flight changes nothing visible on verdict
  controls. `aria-disabled` still flips for assistive technology and no rule
  selects on it. A `frozen` class on the list dims the controls only in the
  long-lived states (finalised, closed, disconnected).
- **Review-only per card** is the kind pill plus a screen-reader sentence
  carrying `data-field="review_only"`. The visible statement is in the sticky
  section heading, as the owner accepted with direction D.
- **Fact labels.** Archetype, type and class print without a visible label
  unless the value is absent, when "none" alone would not say what is missing.
- **Triples at 390 px.** The linking words "Proposed" and "because" are kept
  for screen readers only at that width, which takes the proposal from five
  lines to two. The verdict buttons still stack.
- **Stat order** is sorted in the component. The source scan lists it under
  "ordering computed in the browser"; it orders six stat names, not groups or
  pieces.
- `html` has `scroll-padding-top`, so the sticky heading does not cover a
  control that takes focus.

## Tried and dropped

- Equal-width grid columns for the stat strip at every width: "Weapons"
  overran its cell at 390 px. A `max-content` grid fixed that and failed S2,
  because a 300-character stat name widened the page. The strip is a flex row
  with `overflow-wrap: break-word`, equal cells only when the group is wide.
- A `<b>` around the proposed action: S2 counts `b` elements as markup
  created from values. It is a `<strong>`.
- An injected style element to pin sticky headings for tall captures: the
  server's policy refused it, as it should. The capture script uses the CSSOM.
- A component-layer rule for joined-button borders and sizes: shadcn's
  utility classes won. Those few rules sit outside the layers.
- A badge class named `kind-exact` collided with the section class of the
  same name and turned a whole section blue. The badge uses utilities.

## Not done

- S7, S13 and S15 do not pass; see *Stop*.
- No verbatim proof transcripts are in the evidence README yet, and
  `spikes/issue-210/README.md` is not written. Both wait for the amendment,
  so the transcripts are of the final proof set.
- Light was captured and passes axe, but was not otherwise design-reviewed.
- First-render time was not investigated.
