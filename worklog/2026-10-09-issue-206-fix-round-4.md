# 2026-10-09 — Fix round 4 for the Svelte frontend spike (#206)

Started on `feat/issue-206-svelte-frontend-spike` at
`81bc130b`, with a clean tree. The approved plan is unchanged and was not
touched; no `src/` or `tests/` file was edited. No push, PR, issue comment or
issue/project state change was authorised or performed. Refs #206.

An owner-requested review found issues; the owner asked for exactly two fixes
(below) plus this record. Everything else the review found is listed under
*Known limits* and is deliberately not fixed.

## What this round changed

1. **`spikes/issue-206/dev.py`, `vite_dev`.** It used to read Vite's output
   until a line containing `ready in` or `Local:`, then yield without ever
   reading the pipe again and without checking that Vite had started.
   - Vite exiting before it is ready now raises `ViteNotReady` (a
     `RuntimeError`) carrying everything Vite printed and its exit status; the
     process is reaped. `main` catches it, prints `error: ...` to stderr and
     returns 1.
   - After readiness a daemon thread reads and discards Vite's output to EOF,
     so a long session cannot block on a full pipe. Nothing is forwarded, so
     what `proof_s10_devloop.py` prints is unchanged.
   - On exit: `terminate()`, `wait(timeout=10)`, then `kill()` and `wait()` on
     `TimeoutExpired`.
   - **Surprise, found while demonstrating the failure path:** the old ready
     test `"ready in" in line` also matches Vite's own error
     `Error: Port 5188 is already in use` ("al**ready in** use"). A first
     attempt that only added the EOF check therefore still yielded for a dead
     server. The match is now the regex `\bready in \d|Local:`, which matches
     the real banner (`ready in 363 ms`) and the `Local:` URL line but not that
     error.
2. **The four sanitised-report screenshots** were 6.6 to 7.4 MiB each (about
   29 MB together), full-page captures 61,000 and 101,000 px tall.
   `proof_s15_scale.py` now clips each to the top `SHOT_HEIGHT = 2400` px
   (`page.screenshot(full_page=True, clip=...)`). Regenerated with the
   proof's own command:

   | File | Before | After |
   | --- | --- | --- |
   | `real-desktop-dark.png` | 7,790,861 B | 279,689 B |
   | `real-desktop-light.png` | 7,017,664 B | 251,953 B |
   | `real-narrow-dark.png` | 7,737,353 B | 178,084 B |
   | `real-narrow-light.png` | 6,955,386 B | 159,386 B |

   The S15 per-group checks are unchanged and still cover all 74 groups;
   only the image description changed. Descriptions were corrected in
   `docs/frontend-framework-decision.md` (the screenshot section and the
   "stacked layout is long" bullet), `docs/evidence/issue-206/README.md`
   (intro, table, S15 prose) and `spikes/issue-206/README.md`. The
   `proof_s15_scale.py` module docstring was updated too.
   The decision record's S15 median table (four figures) was also updated,
   because the S15 transcript had to be recaptured (next section).

The large PNGs **remain in this branch's earlier commits**. The PR should be
squash-merged so they stay out of `main`'s history.

## Transcript recapture and collateral

The S15 fence in `docs/evidence/issue-206/README.md` quoted the screenshot
dimensions, so the whole fence was replaced with the real output of
`proof_s15_scale.py --screenshots` (merged stdout/stderr, exit 0, `RESULT:
PASS`). Nothing was hand-edited. A line diff against the old fence shows only
the four `wrote ...` lines (now `top 1440x2400 of a 1440x60949 page; all 74
groups checked`, and so on) and the timing lines; counts, assertion totals,
focus laps (444/444) and contrast figures are identical. Timings vary on
rerun; the five-run medians are now slice/production: navigation 200.0/150.2
ms, next frame 212.6/156.3 ms, acknowledgement-to-DOM 17.9/10.3 ms, next
frame 24.8/16.7 ms; 13,143/17,138 elements. The same four figures in the
decision record's table were updated to match. The conclusion (slice slower,
recommendation bounded conditional) is unchanged.

The S10 fence was not replaced. S10 exercises `vite_dev` and was rerun: `RESULT:
PASS`, same lines as the fence apart from timings and the `svelte-check`
summary text (`COMPLETED 295 FILES 0 ERRORS ...` against the fence's `found 0
errors and 0 warnings`, which is that tool's own output format on this
install, not something this round touched). No S10 claim depends on either.

## Verification

- `.venv/bin/ruff check src tests scripts spikes`: all checks passed.
- Failure path, with a throwaway listener occupying the dev port (script in
  the session scratchpad, not in the repo):
  `.venv/bin/python spikes/issue-206/dev.py --port 5188` printed
  `error: vite exited with status 1 before it was ready:` followed by Vite's
  own `Error: Port 5188 is already in use` output and exited **1** after
  1.3 s with no Vite process left behind.
- `.venv/bin/python spikes/issue-206/proof_s10_devloop.py`: exit 0, PASS.
- `.venv/bin/python spikes/issue-206/proof_s15_scale.py --screenshots`: exit
  0, PASS; the four sizes above.
- `.venv/bin/pytest -q`: 1342 passed (32.5 s). `git diff --check`: clean.
  `.venv/bin/python scripts/check_worklog.py --base main`: `worklog: ok`
  (run before this entry was committed, so its pull-request rules were
  re-checked only by the tree rules at that point).

## Owner decision, 2026-10-07: the slice's visual design is not accepted

The owner dislikes both the look and the structure of the slice, and in dark
mode sections are hard to tell apart: cards use the same fill as the page,
and the group card and the piece box are visually identical. The plan
delegated visual design to the spike, so this is **not a defect against the
plan**. The redesign is deferred to a later ticket, to be done dark-first
against the prototype named in `docs/review-ui-design-contract.md`. It does not
change the spike's framework recommendation.

## Reviewer note on the test-migration cost

The decision record's "8,653 lines of Node-harness UI tests" is **77 tests**
(46 in `tests/test_review_ui_js.py`, 31 in `tests/test_server_ui_js.py`). They
are long because each embeds a JS harness and DOM stub. The expected migration
cost is a per-test triage (keep / obsolete with a hand-written DOM / covered by
types or the existing Playwright tests), not a line-for-line rewrite. That
triage has **not been done**.

## Known limits, not fixed in this round

Review findings in spike code that a migration would rewrite anyway:

- `App.svelte`: the in-list "Reset filters" button is unreachable with one
  facet, and once reachable it would drop focus to `<body>`.
- `view.ts` `split` throws on a group with no members and compares cell text
  only.
- `session.svelte.ts` `#rejected` tells the user to repeat an action after
  `illegal_state` on a non-frozen state.
- `harness.py` and `contract.py` patch `server_app.tempfile` outside the `try`.
- `check_source.py` `INERT_URL` is a prefix match.
- `spike_app.build_spike_server` duplicates production `build_server`.
- `contract.py` calls `generate()` twice when writing.

## Edit inventory

`spikes/issue-206/dev.py`, `spikes/issue-206/proof_s15_scale.py`,
`spikes/issue-206/README.md`, `docs/frontend-framework-decision.md`,
`docs/evidence/issue-206/README.md`, the four `real-*.png` files, and this
entry. Nothing under `data/`, `src/`, `tests/` or the plan changed; only the
tracked sanitised armor fixture was read, through the proofs.
