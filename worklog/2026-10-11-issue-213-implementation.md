# 2026-10-11 — #213 implementation: NO-GO for the redesigned slice as measured

Work on `feat/issue-213-redesigned-slice-timing-gate` only, on top of approved
plan SHA `8aefb1269e639a76b989c20c724495989a928fd3`. The plan is unedited. No
`data/` file was read. `spikes/issue-210/` and `spikes/issue-206/` are
byte-identical to `main`. No PR was opened and no issue was commented on or
changed. Refs #213.

## Dispatch record

- **Authorization:** the owner approved the plan by SHA (`8aefb12`) and
  authorised implementation in one message. Nothing else was authorised: no
  PR, no dispatch comment, no issue or project change.
- **Checks at the start:** #213 open, project status `Todo`; tracker #138
  open; the branch head was the plan commit; `main` at `89ff866`.
- **Review base and starting SHA:** `8aefb1269e639a76b989c20c724495989a928fd3`.
- **Copy commit:** `b2de097523f429572052644fa000e2ca3bf40820`.
- **Implementer:** plan selected `claude-opus-5-5` at `high`. Actual:
  Anthropic `claude-opus-5-5`, Claude Code desktop; the session does not
  report its native effort. It is the session that planned, as in #210.
- **Orchestrator:** the same session. No separate orchestrator ran.
- **Review:** the plan's path is independent adversarial review. **It has
  not been done.** It needs a fresh session and the owner's choice of
  reviewer.

## Result

**NO-GO for the redesigned slice as measured.** Five complete gate
invocations, none incomplete, none discarded.

| | Baseline 1 | Baseline 2 | Change tried | Final 1 | Final 2 |
| --- | --- | --- | --- | --- | --- |
| A1 gap, ms | +85.2 | +92.5 | +87.7 | +91.7 | +84.4 |
| A2 gap | +92.4 | +99.1 | +95.9 | +98.8 | +90.7 |
| A3, A4 | pass | pass | pass | pass | pass |
| B1 gap | +94.3 | +101.7 | +99.0 | +99.6 | +93.4 |
| B2 | +8.2 | +2.0 | pass | pass | pass |
| B3 | +9.1 | +7.5 | pass | pass | +0.6 |

The full tables, the per-run values and the attribution are in
`docs/frontend-framework-decision.md`, "The redesigned slice against #209's
gate (#213)". Transcripts are in `docs/evidence/issue-213/README.md`.

## What was done

- **Copies.** `spikes/issue-213/frontend` from #210's, and `proof_gate.py`
  from #209's blob `a77c21f3`, committed alone first.
- **A runner,** `run_proof.py`, for the twelve #206 and #210 proofs, with a
  check on which build the server sent and a negative control for it.
- **Baseline:** the gate twice, and every proof once. All thirteen proofs
  pass.
- **Attribution,** `proof_attribution.py`: a timeline, a profile, a
  no-framework floor, and seven ablations.
- **One change tried and dropped:** class merging once per distinct input.
- **Two final invocations** on the unchanged source.
- **The record:** the decision record's status note, a new subsection in
  section 6, one bullet in section 8, one note on draft 5 in section 9.

## Decisions

1. **The runner is named `run_proof.py` on purpose.** #210's proofs and
   #209's gate do `from run_proof import configure` and call it bare. With
   `spikes/issue-213` first on the path they import this module, so no proof
   needed editing and the gate proof needed no change to find its build.
   #210's runner is loaded under another name and its own `configure`,
   `merge_tuned_stat` and `one_column_measure` are called, not copied.
2. **The build check reads the server's responses.** Each signed-in browser
   context fetches the two assets and the runner compares their hashes with
   the #213 build on disk. The source scan opens no browser, so it prints
   none.
3. **The floor was added to the plan's attribution list.** The plan asked
   for a timeline, a profile and ablations. The floor answers a question
   none of those can: whether any script change could pass. It serves the
   slice's own markup and stylesheet with no framework.
4. **One real change, not several.** The plan says to make changes largest
   attributed cost first and keep one only if it moves a gated comparison
   past the baseline spread. The ablations bound every allowed candidate
   below that spread. The class-merge change went through the gate because
   it is the cause #210's worklog and the issue name; the others were not
   built, and the record says so.
5. **The final proofs were not rerun.** The final source is the copy
   commit's, the build is the same bytes the baseline proofs were served
   (their transcripts show the hashes), and neither `run_proof.py` nor
   `proof_gate.py` changed after those runs. The two final gate invocations
   were made.
6. **The visual proof was not written.** The plan requires it once the
   slice source differs from the copy commit. It never does in a commit.
7. **`build-check` prints a `RESULT: FAIL` line before its own
   `RESULT: PASS`.** The first is the check firing under the control. It was
   left that way so the runner did not change after the baseline proofs
   ran; the evidence README explains it.

## Surprises, for the next agent

- **The floor fails.** The redesigned document with no client code at all
  reaches `ready` about 25 ms after production. Layout is 74 to 76 ms
  against 45 to 49 and style 30 to 33 against 15 to 16, with fewer elements.
  So the gap is not only Svelte's mount: part of it is the design.
  (Corrected in fix round 1: this bullet first said "21 to 41 ms" and "about
  a third", from runs that intercepted the floor and not production. See
  `2026-10-11-issue-213-fix-round-1.md`.)
- **The grids are most of the extra layout.** With every grid forced to
  blocks the floor's layout falls by 19 ms and it comes within 12 ms
  of production. (Corrected in fix round 1: measured once when this was
  written, twice now; "draws level" was one run.) That destroys the row alignment the owner accepted, so it is
  a measurement, not a candidate.
- **Container queries cost 8 to 10 ms of style,** stable in every run. They
  could in principle become media queries, since a group's width follows
  the viewport's. That was not tried: it does not move a gated comparison
  past the spread, and equal geometry at every width would need proving.
- **A preload hint brings the report 39 ms earlier and `ready` does not
  move.** The slice's main thread is busy from start to finish (task time
  equals time to `ready`), so data arriving sooner just waits.
- **The planning note on B2 and B3 was half right.** It said the slice's
  acknowledgement-to-settled was steady near 29 ms and only production's was
  split. Over 25 runs here the slice fell in the lower group 5 times and
  production 13. Both are quantised to a frame; production lands low more
  often. B3 failed the last invocation by 0.6 ms.
- **Ablation medians of five are noisy.** The unchanged arm's own `ready`
  median ranged from 241 to 262 ms across comparisons in one session. The
  counters are steadier than the stamps. Read a difference under about 15 ms
  between two arms as nothing.
- **`first group in document` in the timeline is not independent.** S15's
  observer is registered first and forces layout with a box read, so the
  later observer's stamp equals `ready`. The evidence README says so.
- **The build writes container queries in range syntax,**
  `(width>=760px)`, not the `(min-width: 760px)` of the source. The first
  attribution run stopped on that.
- **A heredoc with an unquoted delimiter eats backslashes** in an inline
  Python patch. Quote the delimiter.
- **`tail -3` is rejected by this machine's `tail`.** Use `tail -n 3`. It
  broke one `&&` chain; nothing was lost.

## Verification

- `.venv/bin/ruff check src tests scripts`: all checks passed.
- `.venv/bin/ruff check spikes/issue-213`: all checks passed.
- `.venv/bin/pytest -q`: 1342 passed (32.35 s), the baseline count.
- The required browser suite: 16 passed, 3 deselected (12.08 s), no skip.
- `spikes/issue-213/frontend`, from a clean `npm ci`: `npm run check` 0
  errors and 0 warnings; `npm test` 43 passed; `npm run build` clean
  (script 144,389 bytes, stylesheet 31,725 bytes, the same hashes as #210's
  build).
- Every proof in `spikes/issue-213/README.md`: the thirteen runner proofs
  pass; the gate fails, as recorded; `proof_attribution.py` passes.
- `python3 scripts/check_worklog.py --base origin/main`, `git diff --check
  origin/main...HEAD` and both inclusion commands are recorded in the
  completion handoff, run after the last commit.

## Not done

- **The independent adversarial review.**
- No candidate beyond class merging was built (decision 4).
- Rendering containment, deferred or chunked mounting, paging and
  virtualisation were excluded by the plan and not measured.
- Other widths, the dark scheme, other browsers and a larger report were not
  timed.
- Svelte's mount was not broken down below "the runtime".
- No issue was created, edited or commented on; the dispatch comment was
  not posted. `feat/issue-209-svelte-perf-gate` was not touched.
