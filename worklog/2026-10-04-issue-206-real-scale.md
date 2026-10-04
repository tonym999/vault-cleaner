# 2026-10-04 — #206 Amendment 4: sanitised report at real scale

Implemented Amendment 4 on `feat/issue-206-svelte-frontend-spike`, starting
at `4edb4f5cdea7ba78c8a5e7239bdf83d4816fd006`, on top of reviewed
implementation `870b1714770cdaa5751ba7dc574ee20d7e7ec159`.
The approved plan was never edited. No issue comment/state mutation or PR
was authorised or performed. Refs #206.

## Dispatch record

- User approved plan `4edb4f5` in this chat and separately authorised
  implementation. Issue #206 verified OPEN, project Status Todo, no milestone;
  tracker #138 is OPEN.
- Approved plan SHA and attempt starting SHA:
  `4edb4f5cdea7ba78c8a5e7239bdf83d4816fd006`.
- Fixed ticket review base: `732de2286328763d86781b300ae8c00dd56a692e`.
- Previous reviewed head: `870b1714770cdaa5751ba7dc574ee20d7e7ec159`.
- Orchestrator: OpenAI GPT-6, Codex desktop primary session; exact model ID
  and native effort are not exposed, so neither is invented.
- Implementer requested and actual: OpenAI `gpt-6.1-sol` at `high`, native
  Codex collaboration subagent. No re-selection or fallback.
- Review path: independent adversarial. Selected reviewer requested and actual:
  fresh OpenAI `gpt-6.1-sol` at `high`, native Codex collaboration. Same family
  because no listed cross-provider model is callable in this runtime; no
  fallback. The orchestrator will pin the independent read-only checkout to
  the committed head and record the result after dispatch.
- Workspace: `/home/raver/projects/personal/vault-cleaner`.

## Measurements and recommendation

Only the tracked sanitised fixture
`tests/fixtures/real/2026-09-01T-current/armor.csv` was used for S15, without
editing or regenerating it. No `data/` file or unsanitised export was read.
Synthetic fixtures remain the inputs for S1 to S14.

S15 checks all 9 exact groups, 65 same-stat groups, 158 member occurrences,
3401 required text/value/role assertions per width. Same-stat sizes: 57 pairs,
6 triples, 2 groups of four. All five exact spirit signatures appear without
an overlay. All nine E10 filter sequences match production at 1440 and 390 px,
including the real Hunter-to-Exact class drop. All six width/scheme cases
have no sideways scroll or clipped opaque value; Tab reaches all 444 controls
in order. A verdict on group 74/74 keeps the focused node and viewport
position: scroll anchoring adjusts scrollY 20 px while the target moves 0 px.
Whole-document axe and independent contrast checks pass in both schemes.
Four full-page screenshots cover all groups: approximately 61,000 px high at
desktop and 101,000 px at 390 px.

**Bounded conditional**, replacing GO: H1 to H4 and H6 to H9 pass. H5's
layout tests pass, but its S15 performance condition does not. Five alternating
runs on the same report/session/machine produced slice/production medians:
209.5/151.9 ms navigation to all groups laid out, 222.3/158.1 ms to the next
animation frame; acknowledgement-to-DOM 17.5/10.8 ms, next frame 23.6/15.8 ms;
13,143/17,138 document elements. An isolated repeat confirmed the slowdown.
Production also builds Proposals and both matrix orientations; fewer slice
elements did not make it faster. These measure DOM completion and frame
opportunity, not display scanout. Migration drafts now include a focused
presentation-performance gate before switch-over: selective verdict-dependent
updates first, whole-group paging/virtualisation only if needed. None was
implemented or filed as an issue.

## Every edit outside S15

- `harness.py`: fixed `real` fixture path/resolver and command choices;
  synthetic choices retained, arbitrary filesystem paths refused.
- `serve.py`, `dev.py`: `--fixture real`, shared preload using the resolver,
  corrected docstrings. Synthetic defaults preserved.
- `frontend/src/app.css`: two narrow fixes for S15 contrast findings: approved
  success text at 4.46:1 and dark outlined tier-5 stat-role badges at 2.39:1.
  Darken success text; lighten only outlined primary badge text. No layout or
  component-markup restyling.
- `proof_s6_layout.py`: derive the keyboard-loop bound from actual controls,
  replacing the 120-stop cap (S15 has 444).
- `proof_s11_typedrift.py`: required rerun found a baseline proof parsing
  machine output while requesting prose. Orchestrator authorised the single
  invocation repair `-- --output machine`; experiment/assertions/parser stay.
- `proof_s13_axe.py`: wait for colour transitions to settle before measuring,
  replacing the 100 ms delay that could sample an intermediate theme colour.
  No violation or incomplete result is ignored.
- Spike README: sanitised try-it/dev commands, S15 commands and duration,
  conditional result.
- Decision record: recommendation/gates, real-scale figures, contrast fixes,
  screenshots, remaining overlay limits, performance migration gate. H8/H9
  structural/dev verdicts stand.
- Evidence README: fixture/capture wording, S15 transcript and screenshot
  links, affected recaptured fences/figures (frontend and S9, S10, S12, S13,
  S14; S1 to S8 and S11 transcripts unchanged). S14's informational machine
  ERROR lines disappear with prose check output; exercise checks still pass
  and S14 code is untouched. All six synthetic screenshots
  were regenerated from the changed CSS too.
- This new worklog. Earlier entries, including historical GO, unchanged.

## Verification and surprises

Required repository checks and all proofs pass. Full pytest remains
`1342 passed` (35.56 s), required browser suite `16 passed, 3 deselected`
(12.42 s); both lints and installed-wheel check pass. Clean npm install,
type check (zero errors/warnings), 32 unit tests and build pass; probe clean
install/build pass; licence/audit/source/contract checks pass; two builds are
byte-identical. Command tails are handed to the orchestrator; inclusion,
worklog and diff checks run before commit. No production/frozen #137 changes
or tracked modules/build output.

Normal escalation was needed for sockets/Chromium/package indexes, not a
toolchain stop. Automatic approval review timed out once on the final proof
rerun without a safety finding; its permitted retry ran. An npm install briefly
overlapped S13 and removed axe-core; S13 passed after the install finished.
Final S15 timings ran after those checks. Test instrumentation ending in an
assigned fetch function made Playwright invoke it with null and request
`/spike/null`; terminal `undefined` fixes the proof, preserving strict console
checks.

Not measured: screen readers, other browsers/machines, performance at other
widths or reports beyond this fixture, human navigation/task completion on
the long stacked page, paging/virtualisation, other product surfaces. Exact
Seasonal Mod and positive Holofoil still rest on S1's overlay. CSP unchanged;
no component needs an addition.
