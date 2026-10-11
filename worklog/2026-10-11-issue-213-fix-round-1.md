# 2026-10-11 — #213 fix round 1: an uneven attribution harness and four record defects

Work on `feat/issue-213-redesigned-slice-timing-gate` only, on top of reviewed
head `895c2ec771c96ccdfd271d0d3117006730e3cc93` and approved plan SHA
`8aefb1269e639a76b989c20c724495989a928fd3`. The plan is unedited and needed
no amendment. No `data/` file was read. The slice, `proof_gate.py`,
`spikes/issue-210/` and `spikes/issue-206/` are unchanged. The verdict is
unchanged: NO-GO for the redesigned slice as measured. Refs #213.

## Review record

- **Authorization:** the owner asked for a reviewer subagent to be
  dispatched in the implementing session, then for this fix round and a
  re-review in the same way. No PR, issue comment or issue change was
  authorised or made.
- **Reviewer, requested and actual:** Anthropic `claude-opus-5-5` at `high`,
  a subagent of the implementing session with a fresh context, given the
  orchestrator template's review prompt verbatim. A different model family
  is preferred by policy; only Claude models can be launched from this
  session, so it is the implementer's family.
- **Checkout:** a detached worktree pinned to `895c2ec` in the session
  scratchpad, with the project `.venv` symlinked in. The diff touches no
  `src/` file, so the environment's editable install is equivalent.
- **Range reviewed:** `8aefb12...895c2ec`, the complete implementation.
- **Outcome:** no P0 or P1. Two P2 and three P3, all in the record or the
  diagnostic harness. The reviewer reran the gate twice (navigation failed
  by 85 to 118 ms), all thirteen proofs, both test suites and the frontend
  checks, and found them as recorded.
- **Implementer of this round:** the same session, Anthropic
  `claude-opus-5-5`; it does not report its native effort.

## Dispositions

| Finding | Disposition |
| --- | --- |
| P2-1: the attribution intercepted the slice's files and not production's, and its docstring said every arm was intercepted | Accepted, fixed |
| P2-2: the change was dropped on A1 alone, though B2 and B3 moved past the baseline spread in that invocation; and "none moves a gated comparison" overclaimed | Accepted, fixed in the record |
| P3-1: `build-check` needs the #206 build, which the README did not say, and ended with no `RESULT:` line without it | Accepted, fixed |
| P3-2: the grid cost was called stable across runs after one measurement | Accepted, fixed: it is now measured twice and the record says so |
| P3-3: the record did not say the proofs ran at baseline only; the commit-order check is vacuous | Accepted: the proofs were rerun, and the record states both |

## P2-1: both pages are now intercepted alike

- **The defect.** `proof_attribution.py` swaps variant files in with
  Playwright's request interception. Its route matched `/spike/` only, so
  production's document, stylesheet and scripts went straight to the server.
  The reviewer measured the difference; I had not.
- **The fix.** The route now covers every request. The slice's three files
  and production's page and static files all make the same fetch-and-fulfil
  round trip; API requests are continued on every arm. The docstring says
  so, and says the figures are not the gate's.
- **A new part 0 measures the cost,** each page with and without
  interception: +10.0 ms on the slice's `ready`, +6.7 ms on production's,
  and each page's report request 6 to 8 ms later.
- **Run 4** of the attribution is the result. Runs 1 to 3 stay in the
  evidence, marked as uneven.
- **What changed in the record.** The timeline table is run 4's. "Requested
  21 to 26 ms later" is gone: the report arrives 15 ms later with both
  intercepted, and the request starts 16 ms later with neither. The floor's
  margin is 25 and 27 ms on stamps, stated as an upper estimate because the
  floor also fetches 1 MB of markup through the interception. The claim now
  rests on the counters: the floor's layout and style are 105 to 110 ms and
  production's script, style and layout together are 84 to 88 ms.
- **My figure differs from the reviewer's.** The reviewer's scratch run put
  the unintercepted request gap at 7 to 9 ms; run 4 puts it at 16 ms. Both
  are small samples. The record quotes run 4 and does not claim more.

## P2-2: why the change was dropped, stated against the rule

- The plan's rule is "moved a gated comparison by more than the spread
  between the two baseline invocations". In the invocation with the change,
  B2 and B3 did that and flipped to pass. I had written the reason for A1
  only.
- The record and the evidence now say so, and give the reason the movement
  is not credited: the two final invocations on the unchanged source show
  the same movement.
- "None moves a gated comparison by more than the spread" is replaced. The
  ablations ran in the attribution harness, not the gate; two allowed
  candidates passed 11.6 ms once each and none did in every run. The case
  for building no further candidate now rests on the counters: each is a
  few milliseconds, together well under 20 ms, against gaps of 84 ms and
  more.

## P3 items

- **P3-1.** `run_proof.py build-check` checks for the #206 build first and
  ends with `RESULT: FAIL` when it is missing. The README lists the build.
  Shown in the evidence with the build moved aside for one run.
- **P3-2.** Run 4 measured the grid ablations a second time: layout down 19
  and 20 ms. The record says "both times" and "the last two runs only".
- **P3-3.** All thirteen proofs were rerun in this round and their
  transcripts replace the baseline ones in section 3 of the evidence. The
  record says when they ran, and says history cannot show the attribution
  preceding the change, because no commit changes the slice.

## Corrections to the implementation entry

`2026-10-11-issue-213-implementation.md` was added by this pull request, so
it is corrected in place, in two bullets under "Surprises": the floor's
margin, and the grid figure. Each carries a pointer here. Nothing else in it
is changed; its decision 5 (final proofs not rerun) is superseded by P3-3
above and is left as written.

## What changed

- `spikes/issue-213/proof_attribution.py`: the route, the `routed` option on
  an arm, part 0, the docstring.
- `spikes/issue-213/run_proof.py`: the missing-build path of `build_check`.
- `spikes/issue-213/README.md`: the #206 build.
- `docs/frontend-framework-decision.md`: the #213 subsection from "Where
  first-render time goes" to its end. The gate tables, the verdict and the
  three short notes outside the subsection are unchanged.
- `docs/evidence/issue-213/README.md`: section 3 (rerun transcripts and the
  missing-build run), section 4 (run 4 and the note on runs 1 to 3), the
  closing paragraph of section 5, and section 8 (rerun checks).
- The two worklog entries.

Not changed: `spikes/issue-213/frontend/`, `spikes/issue-213/proof_gate.py`,
the five gate transcripts, and the plan. No gate invocation was made in this
round; the count stays at five.

## Verification

Recorded in section 8 of the evidence, rerun in this round: both `ruff`
checks pass; `pytest -q` 1342 passed; the required browser suite 16 passed,
3 deselected. The thirteen runner proofs pass. `proof_attribution.py` passes
(run 4). The worklog check, `git diff --check` and both inclusion commands
are clean at the new head.

## For the next agent

- **An interception harness must treat every arm alike, and say what it
  costs.** I intercepted the arms I needed to swap files on and compared
  them with one I did not. The docstring claimed symmetry I had not built.
  The counters were what kept the conclusion standing.
- **State a keep-or-drop decision against the rule as written,** for every
  comparison it names, not only the one that decides the verdict.
- **"Stable across runs" needs more than one run.**

## Not done

- The re-review of this round. It is dispatched next and its result is not
  in this entry.
- Everything listed under "Not done" in the implementation entry, apart
  from the review and the proof rerun.
