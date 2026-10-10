# 2026-10-10 — #210 plan Amendment 1: proofs that test #206's markup and layout

A planner commit on `feat/issue-210-armor-duplicates-redesign` that touches
only `handoffs/issue-210-implementation-plan.md` and this entry. It follows
implementation head `725bc99`. Refs #210.

## Why

The implementation stopped at a plan stop condition
(`worklog/2026-10-10-issue-210-implementation.md`, *Stop*). S7, S13 and S15
cannot pass unedited, and S6 passes vacuously on one measure, because they
test #206's daisyUI class names, its contrast gaps and its stacked layout.

## Owner decisions (2026-10-10, in the session)

- The design is accepted from the captures at `725bc99`.
- shadcn-svelte stays for now.
- Write this amendment.

## What the amendment does

- Keeps `spikes/issue-206/` untouched and puts every adaptation in
  `spikes/issue-210/`.
- Replaces S7 with `proof_csp.py` and S13 with `proof_axe.py`, each with the
  original's pass conditions and its own negative controls.
- Lets the runner make two substitutions in S6 and S15: the member-column
  measure becomes the constant `1`, and S15's axe step becomes `proof_axe`'s.
- Adds `proof_layout.py`, which asserts what replaced "one column": pieces
  side by side with aligned rows where they are columns, one block per piece
  for a group of four at 390 px, everything inside the viewport.
- Lists the allowed adaptations completely; anything else is still a stop.
- **Changes the review path to independent adversarial review.** The first
  plan said to do so if more than one oracle case was adapted. The planning
  session also implemented, so nothing at `725bc99` has been reviewed by
  anyone but its author.
- Adds a fifth likely finding: a replacement proof weaker than its original.
- Leaves first-render time (260.5 ms against #206's 209.5 ms) to the
  follow-up timing gate.

## Not done

- Nothing in the amendment is implemented. It needs the owner's approval by
  SHA first.
- The amendment's proof designs were written from reading the #206 proofs
  and from one diagnostic run; none of the three new proofs exists yet.
