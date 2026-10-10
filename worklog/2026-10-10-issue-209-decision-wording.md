# 2026-10-10 — Issue #209 decision record wording

Refs #209. Owner-requested wording change to
`docs/frontend-framework-decision.md` on `feat/issue-209-svelte-perf-gate`,
on top of `7aa70f8c34b3b1adbc954c8c74a829d8e64b95eb`. Done by Claude Opus 5.5
in a Claude Code session, outside the orchestrator/implementer handoff. No
code, proof, evidence, frontend or plan file changes; no measurement was run.

## What changed

The record said **NO-GO** without saying what the verdict covers, so it read
as a verdict on the migration and the framework. It now says, in the status
line, section 1, the H5 row, and the two section 9 notes:

- NO-GO applies to the #209 candidate, measured with the #206 design held
  fixed; the framework decision is deferred until after #210's redesign.
- The plan's "changes nothing the slice shows" rule kept the largest measured
  cost (daisyUI's `.btn` transition on all 435 verdict buttons) in place, and
  the visual, geometry and keyboard failures come from the rendering
  containment used instead.
- No gate invocation was run with that transition removed, so the slice's
  score without it is unmeasured. The record does not claim it would pass.
- Owner direction, 2026-10-10: do #210 first, with latitude over structure,
  component library and packages, then repeat the timing gate and decide.
- "The proposed architecture remains" became "The architecture #206 proposed
  was", since the styling layer is now open to change in #210.

Every measured figure, gate result and "keep the current page" is unchanged.
The owner has not accepted the recorded gaps, and the record still says so.

## For the next agent

- Issue #210 was edited the same day (by the owner's direction, in the same
  session) to carry #209's findings as design inputs, to give the implementer
  latitude over the earlier approach and packages, and to require a prior-art
  survey. It cites this branch by name because the evidence is not on `main`.
- A standalone review of `cc29041` in the same session raised eight findings
  that this entry does not address. Two concern the measurements: the gate
  times the slice on Approve, Veto, Approve, Veto, Approve and production on
  the opposite sequence (`proof_gate.py`, the `action =` line in `sample`),
  and the traversal step stamps its end in the second animation-frame
  callback, possibly before deferred group rendering (`proof_traversal.py`,
  `STEP_JS`). Neither was confirmed by running a browser proof. The A3 and B3
  margins are 0.5 to 1.1 ms, so the first matters when the gate is repeated.
- Commits `80b2685` and `7aa70f8` landed after that review and were not
  reviewed in this session.
