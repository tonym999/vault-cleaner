# 2026-10-04 — #206 fix round 3: effective keyboard focus floor

Started on `feat/issue-206-svelte-frontend-spike` at
`d892298e74bfdd01c6e8efc3e2de6bd726631b2a`. Approved plan remains
`4edb4f5cdea7ba78c8a5e7239bdf83d4816fd006`, unchanged; fixed ticket review
base remains `732de2286328763d86781b300ae8c00dd56a692e`. No PR, issue comment
or issue/project state mutation was authorised or performed. Refs #206.

## Independent review and disposition

The initial independent adversarial review at `d892298` found **one P2** and
no other finding. Requested and actual reviewer: fresh OpenAI
`gpt-6.1-sol` at `high`, native Codex collaboration, read-only detached
checkout `/tmp/vault-cleaner-206-review-KvU7V1/checkout`. Same family because
no listed cross-provider model is callable; no fallback. It reviewed the
complete fixed-base range `732de228...d892298` and incremental range
`870b171...d892298`. The orchestrator independently reproduced the finding
and accepted it for this bounded repair.

The reviewer independently passed S1 to S15, repository lint/full pytest
(1342), required browser tests (16), wheel, frontend/probe builds, build
repeat and real-fixture guards. Screenshot-writing modes and the historical
`npm view` licence fence were not rerun; screenshot dimensions/top-bottom
and installed licences/audit were checked. This records the completed
initial review, not a review of this future fix head. Final re-review of the
committed correction is reported by the orchestrator in chat.

P2: dark primary controls (active All and Finalise review) used daisyUI's 2px
outline in `oklch(0.5 0.233 277.117)`, RGB `[77,65,227]`, against adjacent
`[29,35,42]`: **2.3986977:1**. The library's component rule outranked the
global `@layer base` floor. Existing S5/S13/S15 passed without measuring
focus-indicator contrast. The contract's section 7 requires clearly visible
focus in every theme; [WCAG non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
(read 2026-10-04) requires at least 3:1 for authored focus indicators.

**Accepted and repaired.** Move the global rule outside layers and use the
theme's base-content colour, retaining 3px outline and 2px offset. Dark/light
primary rings now measure 14.75:1/17.72:1. The proof temporarily restores the
old layered rule through the built stylesheet's CSSOM: All, Finalise and the
skip link measure 2.40:1/2px and are rejected. No style tag or CSP addition.

Implementer requested and actual: OpenAI `gpt-6.1-sol` at `high`, native
Codex collaboration subagent; no re-selection/fallback. Orchestrator: OpenAI
GPT-6, Codex desktop primary session; exact model ID/native effort are not
exposed. The notable outcome is that passing axe did not establish this
authored focus property; the reusable actual-keyboard check now does.

## Complete incremental edit inventory

- `frontend/src/app.css`: effective unlayered focus floor, base-content
  colour. No fill, text, markup, layout or protocol change.
- New `focus_contrast.py`: actual Tab lap over every control; computed
  outline geometry and composited adjacent background/opacity, WCAG ratio;
  fail on missing focus, insufficient geometry/contrast or unmeasured image.
  Old-cascade negative control restores its stylesheet mutation in `finally`.
- `proof_s13_axe.py`: reuse that check after every unchanged strict axe/text
  contrast check. Extend states to initial unreviewed, held approval and
  acknowledged approval alongside veto, filtered, finalised and no report.
  Reuse S5's held-response helper. Move the pointer away before waiting for
  colour transitions; no axe outcome is ignored. S15 code unchanged: its
  existing shared S13 call consumes the keyboard check for the full report.
- Spike README: explain reusable focus measurement and states.
- Decision record: correct focus description, independent finding/fix and
  measured ratios; affected line counts, timings and size figures only.
  Recommendation remains bounded conditional on comparative performance.
- Evidence README: recapture affected command fences with stated merged
  stdout/stderr order, including new negative control and keyboard results.
  Every synthetic and sanitised screenshot regenerated from corrected CSS;
  six synthetic PNGs changed, four sanitised PNGs are byte-identical because
  those captures blur focus.
- This new entry; previous worklogs and the approved plan untouched.

During helper development, `background-image: none, none` on the no-report
link's parent was initially treated as an unmeasured image. Computed-style
inspection confirmed its ring already passed (3px/2px, 16.68:1 light); parsing
the list correctly removed that false failure. No extra product defect.

## Verification

Final clean frontend `npm ci`, check (zero errors/warnings), 32 unit tests
and build pass. Both repository/spike lints, full pytest **1342 passed**
(34.29 s), required browser **16 passed, 3 deselected** (12.24 s), and
installed-wheel check pass. Source/contract and every S1 to S15 proof pass;
S6 screenshot-writing and exact README modes pass. Build reproducibility
and unchanged #137 keep/remove map pass. All required worklog, inclusion,
plan identity/ancestry and diff checks run before commit.

S13 passes all 28 width/theme/state cases; S15 passes all four full-report
focus laps, each **444/444** controls with no problem. Axe remains strict;
no unexplained result, CSP violation, console error or dialog. Its five-run
medians slice/production: navigation 202.4/152.4 ms, next frame 215.0/158.7 ms;
acknowledgement-to-DOM 20.2/10.5 ms, next frame 26.4/18.0 ms; 13,143/17,138
elements. The slowdown persists and the recommendation/H5 condition remain
bounded conditional. Heavy checks finished before these measurements.

Affected evidence fences recaptured: frontend, source, S9 (CSS bytes),
S10 (CSS bytes/timings), S12 (stylesheet/tooling lines), S13 (new checks and
states), S15 (focus checks/timings). S1 to S8, S11 and S14 transcripts are
unchanged; S6 screenshot mode has only its expected capture messages.
Decision record collateral figures: served total 1420 lines (+2), S10 type
check/unit/first-render 2.2/1.3/1.3 s; S15 medians updated. Existing production
and #137 source citations stay unchanged and their proofs pass.

All changes remain under the mechanical inclusion test; no production/frozen path or fixture
was edited. Only synthetic fixtures and the single tracked sanitised armor
fixture were read; no `data/` access. Limits remain those of S15: DOM/frame
opportunities, one machine/report, no physical scanout or human navigation
study, screen reader or other-browser measurement.

## Orchestrator accounting follow-up

After committing/pushing the focus repair at
`3e47b7478dfe73e67ec5a560a7c5d18162a37760`, the orchestrator's incremental
audit found one bounded **P3**: S12's explicit proof/tooling file list omitted
the new `focus_contrast.py`, so its 3593/21 count included only the S13 edits.
**Accepted and repaired** in an appended commit on the same branch, starting
at that SHA; no amend, rebase or force-push.

Exact extra hunk inventory: add `focus_contrast.py` to S12's existing count
list; replace only that count line in its evidence fence; extend this entry
with the finding/disposition and verification. The new count is 3708 lines in 22 files.
No CSS, proof behavior, decision-record/source citations, S15 figure, other
transcript or screenshot changed.

S12 rerun passes, with the full output compared against its evidence fence.
Mandatory repository/spike lint passes and full pytest reports **1342 passed**
(32.45 s) before this appended commit; hygiene and approved-plan identity
checks also pass. The browser,
frontend and S1–S15 runs already recorded above validate unchanged inputs;
no claim is made that they were rerun for this count-only follow-up.
