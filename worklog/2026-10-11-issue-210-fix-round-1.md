# 2026-10-11 — #210 fix round 1: Amendments 1 and 2 implemented, all proofs pass

Work on `feat/issue-210-armor-duplicates-redesign` only, on top of approved
plan SHA `50560efa8f81b0883a4c5fa52a1ff24a00f2fb5d` (Amendments 1 and 2). The
plan is unedited. No PR, no issue comment or state change. No `data/` file
was read. `spikes/issue-206/` is byte-identical to `main`. Refs #210.

## Dispatch record

- The owner approved `50560ef` and authorised implementation in the session.
- Review base stays `a006920`. This attempt started at `50560ef`.
- Implementer: Anthropic `claude-opus-5-5` (Claude Code desktop; the session
  does not report its native effort). The same session planned, as before.
- **No orchestrator review and no independent adversarial review has
  happened.** The plan requires an independent review of the final head by a
  fresh session. The Codex review of `653adeb` was an input to Amendment 2,
  not that review.
- Issue #210 open.

## Required fixes (Amendment 2)

1. **Focus outline no longer clipped.** `.segments` and `.verdict` lost
   `overflow: hidden`; the end buttons carry the rounded corners.
   `proof_axe.py` checks every focus stop's painted outline against the
   viewport and every clipping ancestor: 0 clipped of 444 on the real
   fixture at both widths and schemes. Its negative control restores the
   clipping and is detected on 435 of 435 verdict buttons.
2. **The Tuned stat row is always present and first** for a same-stat
   group. The row list moved from the component into `lib/view.ts`
   (`comparisonRows`, `sharedFacts`), with four unit tests. When tuning is
   identical the value stays in the shared line too, so the oracle is
   untouched. `proof_layout.py` reproduces the review's case in memory
   through the real server: both pieces lead with a visible tuned stat and
   one marker, at 1440 and 390 px, with 0 differences from the server's
   report.

## Design refinements (Amendment 2)

- **A, phone triples.** In a narrow group an ordinary piece's status is
  plain muted text, not a pill; the kept piece keeps its pill. "Unreviewed"
  is quiet and only a recorded verdict takes weight and colour. The linking
  words in the proposal are for screen readers only in narrow columns, for
  pairs as well as triples. Ids are whole, proof-fixed copy is unchanged,
  verdict buttons are 40 px tall. **This is judged from 390 px captures
  only. The server is loopback-only, so the slice was not opened on a phone,
  and a width check does not show it is comfortable to use.** The verdict
  buttons of a triple still stack.
- **B, administration.** The status line is quiet text beside the title
  while the tone is info or ok, with a dot for ok; a warn or error notice is
  a full-width bordered box in bold. Session and filters are two plain rows,
  not two boxes. The session note's text and `data-field`, and the three
  live regions' nodes and ids, are unchanged (S1, S3, S4 and S5 pass). **The
  first group's top edge at 1440 by 1000 px is 266 px**; the review measured
  about 415 px at `653adeb`. At 390 px it is 587 px, which this refinement
  did not try to reduce.
- **C, small text.** No visible text is under 11 px: `proof_layout.py`
  finds none among 6,278 text nodes at 1440 px and 6,386 at 390 px on the
  real fixture. Getting there changed the layout: at 11 px the six stat
  cells did not fit one row of a phone-width group, so in a group narrower
  than 480 px the strip is two rows of three, in the same reading order.

## What the new proofs found

Each was a defect in the build, not in the proof:

- **The skip link slid in from off-screen.** It carried shadcn's
  `transition-all`, so on focus its position animated from the far left and
  its outline was briefly outside the viewport. It has `transition-none`.
- **Eight groups' stat strips overflowed at 390 px** once text was 11 px;
  axe could not judge the overlapped cells. See refinement C.
- (From the first diagnostic, already fixed at `725bc99`: the role word on a
  filled stat cell was under 4.5:1 in dark.)

## Proof results

One run of each, verbatim, is in `docs/evidence/issue-210/README.md`
section 5.

| Proof | Result |
| --- | --- |
| S1, S2, S3, S4, S5, source scan (#206, unedited) | PASS |
| S6 (#206; member-column measure replaced by a constant) | PASS |
| S15 (#206; that measure replaced, accessibility step from `proof_axe.py`) | PASS |
| `proof_csp.py` (in place of S7 part 1) | PASS |
| `proof_axe.py` (in place of S13), with three negative controls detected | PASS |
| `proof_layout.py`, with its negative control detected on 74 of 74 groups | PASS |
| `proof_no_transition.py`, negative control detected on 435 of 435 | PASS |

- The adaptations are exactly Amendment 1's: the tuned-stat merge, the
  member-column constant, and S15's accessibility step. `run_proof.py`
  refuses to continue if the member-column measure is not found exactly once.
- `proof_csp.py` is stricter than S7 in one way: an image or a web font
  fails it; S7 only reported them.
- `proof_axe.py` fails a state on the same conditions as S13 and adds the
  clipping check. It differs as the plan lists: nothing unjudged is a pass,
  and the page is scrolled to the top with focus cleared before each axe run.
- S15 parity makes 3,261 assertions per width, with 0 differences.
- Style recalculation over one verdict: median 1.3 ms (#209: 138.7 ms on
  #206, 3.1 ms on production). Recorded, not gated.

Repository checks: `ruff check src tests scripts` clean; `pytest -q` 1342
passed (33.57 s); the required browser suite 16 passed, 3 deselected
(12.21 s); `git diff --check` clean; `npm run check` 0 errors and 0
warnings; `npm test` 43 passed; `npm run build` clean.

## S15 timings (recorded, not gated)

Medians of five alternating runs, 1440 px light, slice / production:
navigation to all groups laid out 248.8 / 159.3 ms; next frame 262.3 /
165.0; acknowledgement to DOM 7.1 / 9.3 ms; next frame 7.9 / 18.2; DOM
elements 13,019 / 17,138. First render is still slower than #206's 209.5 ms
and was not investigated; it belongs to the follow-up timing gate.

## The cheap-to-change report, final

From the carry-forward commit `d46f7bf` to this head (`git diff --numstat`):

| Bucket | Files | Added | Removed |
| --- | --- | --- | --- |
| Components and stylesheet | 12 | 1,127 | 299 |
| shadcn-derived `components/ui/` | 3 | 98 | 0 |
| Typed logic (`lib/view.ts`) | 1 | 41 | 0 |
| Logic tests | 1 | 66 | 1 |
| `package.json` and lockfile | 2 | 40 | 12 |
| Proof tooling (six scripts) | 6 | 992 | 0 |

The logic is four pure helpers appended to `view.ts` (`isKept`,
`tunedStatMerged`, `comparisonRows`, `sharedFacts`). No existing logic line
changed. Built script 144.4 kB and stylesheet 31.7 kB (#206: 64.2 and 57.0).

Page height on the real fixture: 28,312 px at 1440 and 55,274 px at 390.

## Tried and dropped

- Refinement A's status rules in the component layer: the badge's utility
  classes won, and the pills stayed. They are outside the layers.
- One row of six stat cells at 11 px in a phone-width group: see refinement
  C. Shrinking padding would have fitted this machine's font and not others.
- An element screenshot for the triple and four-piece captures: a group
  taller than the viewport came back cut off. They are clipped from the full
  page.
- Deleting the old captures before regenerating: refused by the session's
  safety check on a variable-path removal, and not needed. The capture
  script overwrote the same 20 file names in place.

## Also changed

- The evidence README has the dated correction about direction C, a
  captures section and the proof transcripts. Sections 1 to 3 are otherwise
  as they were.
- `spikes/issue-210/README.md` is written. There is no serve script; it
  says so.
- The captures in `docs/evidence/issue-210/captures/` are replaced. The
  redundant page-top capture is no longer written.

## Not done

- **The owner has not accepted this look.** The acceptance of 2026-10-10
  was for `725bc99`.
- The independent adversarial review the plan requires.
- Phone comfort (see refinement A).
- First-render time.
- The follow-up issues (timing gate, readable proposal reasons) and #152 are
  untouched; each needs its own authorization.
