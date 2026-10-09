# 2026-10-09 — #209 planning: real-scale performance gate for the Svelte slice

Planned #209 on `feat/issue-209-svelte-perf-gate`, cut from `main` at
`d139a05306828c0a4d7e9ded211408b346dd7768`. The plan is
`handoffs/issue-209-implementation-plan.md`. Refs #209.

## Authorization

The owner asked for #209 to be planned. That covers research, this branch,
the plan commit and its push. No PR was opened, no issue was commented on or
changed, and nothing is approved: implementation needs the owner's approval
of the plan SHA and a separate authorization.

- **Planner:** Anthropic `claude-opus-5-5` (Claude Code desktop session; the
  session does not report its native effort setting, so none is recorded).
- **Issue checks:** #209 open, label `enhancement`, on the vault-cleaner
  project with status `Todo`, no milestone, no comments. Tracker #138 open.
  #206 merged through PR #208.

## Measured while planning

All at the plan baseline with the #206 build and harness unmodified, on the
tracked sanitised fixture `tests/fixtures/real/2026-09-01T-current/armor.csv`
only. No `data/` file was read. The scripts were throwaway, in the session
scratchpad, and are not committed; the plan states the method and makes
reproducing the figures the implementer's step 0. Medians, 1440 px, light, one
machine. Slice / production.

- **Navigation (7 runs):** every group laid out 214.0 / 162.3 ms. Chromium's
  own counters over that window: script 71.6 / 24.9 ms, layout 74.3 / 51.1,
  style recalculation 35.0 / 17.6. The report response ends at 35.9 / 39.9 ms.
- **One verdict (7 runs):** acknowledgement to DOM 21.6 / 10.1 ms. Over the
  window from key press to S15's last stamp: script 25.5 / 4.1 ms, **style
  recalculation 161.9 / 3.3 ms**, main-thread task time 320.3 / 43.4 ms.
- **Cause of the style cost (6 repetitions):** flipping `btn-disabled` and
  `aria-disabled` on all 435 verdict buttons costs 92.8 ms of style
  recalculation; either one alone costs about as much; an attribute no rule
  mentions costs 0.0 ms; one button costs 0.6 ms. The slice flips them twice
  per verdict, when the request starts and when it is answered.
- **Projection:** `duplicateGroups` over the 742,979-byte envelope takes
  0.33 ms warm in Node 24.
- **Probe:** with `content-visibility: auto` appended to the built stylesheet
  for group cards, every group laid out 127.7 ms against production's 151.2
  in the same invocation, and verdict style recalculation 8.1 ms.
  Acknowledgement to DOM stayed at 18.4 ms. No correctness check was run with
  it.

## Surprises, for the next agent

- **S15's verdict stamps miss the largest cost.** `repaintFrame` is stamped
  inside a `requestAnimationFrame` callback, which runs before that frame's
  style and layout. #206 reported a 7 ms gap; about 160 ms of style
  recalculation per verdict sat just after the stamp. The decision record's
  section 6 and section 8 do not say this.
- **The issue's proposed first step cannot close the navigation gap.** The
  projection is a third of a millisecond. What re-deriving costs is object
  identity, which only affects verdict adoption.
- The built `app.css` has 43 `:has(` selectors. Which rule makes the button
  flip expensive was not isolated.

## Decisions in the plan

- **New directory `spikes/issue-209/`,** holding a copy of the #206 frontend
  whose first commit is verbatim. `spikes/issue-206/` is frozen: its
  transcripts are reruns of its code. The #206 proofs run against the new
  build through a runner that sets two module globals; no proof is edited.
- **The gate is wider than the issue's.** S15's four stamps stay as gate A.
  Gate B adds settled-frame measures (second of two nested animation frames)
  for navigation, key press to settled and acknowledgement to settled. The
  plan says approving it approves gate B.
- **Steps in order:** baseline; identity-stable projection by value equality,
  never keyed on a revision; the in-flight flip; the load path, where CSS
  rendering containment is allowed with a traversal proof. Paging and
  virtualisation are a stop condition, not built.
- **Passing** means every comparison holds in each of two consecutive
  invocations, with every invocation reported.
- **The slice must look the same** as #206's. The redesign is #210.
- **Implementer:** `gpt-6.1-sol` at `high`, Judgement rung. **Review path:**
  independent adversarial review.

## Not done

- No code was written and no step was tried beyond the one stylesheet probe.
- The runner approach was read from the code, not run.
- `python3 scripts/check_model_roster.py` reports 2 stale rows (both Gemini);
  neither is relied on.
