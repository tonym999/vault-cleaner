# 2026-10-11 — #210 fix round 2: two proof defects from the second review

Work on `feat/issue-210-armor-duplicates-redesign` only, on top of approved
plan SHA `50560efa8f81b0883a4c5fa52a1ff24a00f2fb5d`. The plan is unedited and
needed no amendment: both findings are failures against conditions it
already states. No `data/` file was read. `spikes/issue-206/` is
byte-identical to `main`. Refs #210.

## Review record

- **Review of `61d9410`** by OpenAI Codex, posted at the owner's request:
  <https://github.com/tonym999/vault-cleaner/issues/210#issuecomment-6106125423>.
  The comment names no exact model or effort, and describes itself as a
  continuation of the earlier standalone review, not the fresh session the
  plan asks for.
- **Owner decision, 2026-10-11:** that review is treated as the plan's
  independent adversarial review. The owner also accepted the refined look
  at `61d9410`, asked for the two findings to be fixed, and authorised
  opening the PR.
- **What that leaves unreviewed:** this round's changes. The plan says
  accepted fixes on an independent-review path get a new complete-diff
  review; by the owner's decision they go to the PR without one.
- Implementer: Anthropic `claude-opus-5-5` (Claude Code desktop; the session
  does not report its native effort), the session that planned.

## Dispositions

| Finding | Disposition |
| --- | --- |
| REV-01, P2: a focus outline can run off the viewport's bottom, and the proof compared only its sides | Accepted, fixed |
| REV-02, P2: the CSP proof keeps one policy per path and has no negative control | Accepted, fixed |
| VIS-01: phone triples remain a usability question; the phone header is 587 px | Accepted as stated: a follow-up, not a defect of this ticket |

## REV-01: the whole outline stays on screen

- **The page.** `html` gains `scroll-padding-bottom: 0.75rem`, so a control
  brought into view by Tab keeps its 5 px of outline inside the viewport.
- **The check.** `proof_axe.py` no longer focuses stops from script. It
  walks a real keyboard lap in each direction, Tab and Shift+Tab, and
  measures each stop as it takes focus: the painted outline must be inside
  the viewport on all four sides, clear of any sticky or fixed element that
  is not its ancestor, and inside every clipping ancestor. 72 laps across
  the nine states, two widths and two schemes; every stop reached, none
  clipped or covered.
- **It found a second defect the review had not:** at 390 px, walking
  backward, six verdict buttons came to rest under the sticky section
  heading. The heading wraps to 109 px there and the page reserved 88 px.
  Narrow viewports now reserve `8.5rem` (136 px).
- **Negative controls,** each through the CSSOM and each detected:
  no padding below gives 75 outlines past the bottom at 1440 px and 6 at
  390 px, the review's own counts; no padding above gives 6 under the sticky
  heading at 390 px walking backward; the earlier wrapper-clipping control
  now catches 435 of 435.
- **A flaw in my first lap, found while writing it:** a lap does not start
  at a known stop, because the browser keeps its place after a blur, and it
  passes the document's edge once with nothing focused. Counting presses
  reported one stop short on every lap. The lap now counts distinct stops.

## REV-02: every response's policy is checked

- `proof_csp.py` records every response in order and fails on any whose
  policy is not production's; it also requires one response per request.
  The mapping by path came unchanged from #206's S7, whose output says
  "every response" and checks the first per path.
- **Negative control:** a fresh server, with the policy removed from every
  verdict response after the first. 3 of 4 are reported, and the proof
  prints that a one-policy-per-path check would have reported 0.
- No policy defect was found in the unmodified server: 12 responses for 12
  requests, all with production's policy.

## Results

All in `docs/evidence/issue-210/README.md` section 5, regenerated from this
round's runs.

| Proof | Result |
| --- | --- |
| S1, S2, S3, S4, S5, source scan (#206, unedited) | PASS |
| S6, S15 (#206, with the two approved substitutions) | PASS |
| `proof_csp.py`, negative control detected | PASS |
| `proof_axe.py`, five negative controls detected | PASS |
| `proof_layout.py`, negative control detected | PASS |
| `proof_no_transition.py`, negative control detected | PASS |

Repository checks: `ruff check src tests scripts` clean; `pytest -q` 1342
passed (31.53 s); the required browser suite 16 passed, 3 deselected
(11.91 s); `git diff --check` clean; `npm run check` 0 errors and 0
warnings; `npm test` 43 passed; `npm run build` clean (script 144.4 kB,
stylesheet 31.7 kB).

Recorded, not gated: style recalculation over one verdict, median 1.2 ms.
S15 medians, slice / production: navigation 235.5 / 147.0 ms; acknowledgement
to DOM 7.5 / 10.0 ms.

`proof_axe.py` now takes about four minutes; the keyboard laps are most of
it.

## What changed

- `frontend/src/app.css`: the two scroll-padding rules. Nothing else in the
  slice. The look the owner accepted is unchanged; four capture files differ
  in bytes after regeneration and were not compared pixel by pixel.
- `proof_axe.py`, `proof_csp.py`: as above.
- The evidence README's captures and transcripts sections, regenerated.

## For the next agent

- **Three review rounds each found a gap in a proof written in this
  ticket,** not in the slice's behaviour: a clipping check that read
  computed style, then one that compared two sides of four, and a policy
  check that deduplicated by path. Each gap was a check with no negative
  control for the case it missed. Treat a new check as unproven until
  something it should catch has been shown to fail it.
- Copying a pattern from a passing #206 proof carried its flaw with it
  (REV-02). #206's S7 still has it.

## Not done

- An independent review of this round's changes (see *Review record*).
- Phone comfort, first-render time, and the follow-ups (the timing gate,
  readable proposal reasons, #152). Each follow-up needs its own
  authorization.
