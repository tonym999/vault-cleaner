# 2026-10-11 — #210 plan Amendment 2: review findings and design refinements

A planner commit on `feat/issue-210-armor-duplicates-redesign` that touches
only `handoffs/issue-210-implementation-plan.md` and this entry. It follows
`653adeb` (Amendment 1, never approved). Refs #210.

## Why

A standalone review of `653adeb` by OpenAI Codex was posted on the issue at
the owner's request before Amendment 1 was approved:
<https://github.com/tonym999/vault-cleaner/issues/210#issuecomment-6103418695>.
The owner asked for its findings and three design refinements to be written
into the plan.

## The review's findings, checked against the source

- **Clipped focus outline: correct.** `.segments` and `.verdict` clip with
  `overflow: hidden`. The planner's earlier diagnostic read the computed
  outline and reported 444 of 444 focus stops as carrying it. That figure
  was true of the computed style and wrong about what is painted.
- **Tuned stat row can disappear: correct.** The first plan required the row
  always; the implementation built rows from `group.differing` only, which is
  #206's rule and what the oracle expects, and did not report the departure.
  The fixture has no identical-tuning group, so no proof caught it.
- Neither reproduction was rerun here; both follow directly from the source.

## What the amendment does

- Records a disposition for every finding in the review.
- **Required fix 1:** no clipped outline, with a check on painted bounds
  against clipping ancestors and a negative control.
- **Required fix 2:** the Tuned stat row always, first. The value stays in
  the shared line too when identical, so no further oracle adaptation is
  needed. The reviewer's case is reproduced in memory through the real
  server; no fixture file changes.
- **Refinements A, B, C:** flatter status framing on phone triples; a quiet
  connected state with the session note and actions brought together; no
  visible text under 11 px, with an assertion.
- **A new owner acceptance is required**, because the refinements change the
  look the owner accepted at `725bc99`.
- Corrects the record on direction C: incompatible with this ticket's
  proofs, not shown to be worse to use.
- Defers human-readable proposal reasons to a follow-up issue; creating it
  needs its own authorization.
- Adds two likely findings and two stop conditions.
- Approving the SHA that holds this amendment approves Amendment 1 as well.

## Decisions

- **Duplicate the tuning value in the rare identical case** and leave the
  oracle alone. One more adapted proof would cost more trust than one
  repeated value costs space.
- **11 px as the text floor.** The design contract names 10 to 11 px
  captions as the sizes whose contrast must be checked; the review flagged
  0.56rem (about 9 px). 11 px is the smallest size the contract mentions.
- **The Codex review is an input, not the plan's independent review.** It
  was of a head that is not final, and the plan still requires a fresh
  independent review of the final head.

## Not done

- Nothing in either amendment is implemented.
- The slice cannot be opened on a real phone, because the review server is
  loopback-only. Refinement A will be judged from 390 px captures and a
  narrow desktop window, and the plan says that does not establish comfort.
