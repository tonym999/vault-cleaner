# 2026-10-04 — #206 fix round 1: review findings on the Svelte frontend spike

Fix round on `feat/issue-206-svelte-frontend-spike`, on top of
`cbd89ca2fa1f477addb066433634bbdc9f7d7e63`, under the same plan SHA
`522f2fb228755b7631685649c9d136bd80ebaa53`. Commits appended; no rebase. No
pull request opened, no issue touched, no production file changed. Refs #206.

## Review record

- **Reviewed head:** `cbd89ca2fa1f477addb066433634bbdc9f7d7e63`.
- **Reviewer, requested and actual:** Anthropic `claude-opus-5-5`, a fresh
  read-only Claude Code subagent in a disposable checkout pinned to
  `cbd89ca`. The subagent launch has no effort parameter, so `high` could
  not be set or confirmed.
- **Model family:** the roster prefers a different family for the
  independent reviewer; the runtime cannot instantiate one. No fallback was
  taken.
- **Findings:** no P0 or P1, one P2 and five P3. All six were
  `accepted/fixed` by the orchestrator.

## What changed, by finding

1. **P2, three required values never rendered by S1.** No fixture carries a
   spirit signature, or an exact group with a Seasonal Mod or a Holofoil.
   `proof_s1_parity.py` now has a case that changes the server's real answer
   in memory (as `two_class_fixture` does for a class) to give the groups
   those values; the page must show them, and the oracle in `expected.py`
   computes them independently. `view.test.ts` gained tests for the spirit
   signature and for an exact group's Seasonal Mod and Holofoil, including
   the `false` case. The record's H1 row and section 8 say how they were
   measured.
2. **P3, verdict-control rule looser than production's.** `view.ts` and
   `expected.py` now use production's rule: an exact member needs its
   disposition and `proposal_action` to agree and the section's proposal to
   carry that action; a same-stat member needs the section's proposal to be
   exactly `junk` or `review`. Two unit tests cover the non-agreeing cases.
   `proof_s2_hostile.py` now has two passes, because a hostile disposition
   or action correctly leaves a member without buttons: the first replaces
   everything and asserts there are none; the second keeps those three
   values so a verdict can be pressed on a hostile id.
3. **P3, the dev loop's Host check.** `proof_s10_devloop.py` measures four
   Host names through the proxy and straight to Flask. `dev.py`,
   `vite.config.ts` and the record say that Vite's `server.allowedHosts` is
   the stand-in for Flask's exact-Host check and that it accepts `localhost`
   and `*.localhost`, which Flask refuses.
4. **P3, H8(a) wording.** Record only: H8(a) lists the server values and
   conventions the browser also knows, and H9 says enumerated-value drift is
   caught by the unit tests and the stale-sample check, not by the type
   check.
5. **P3, the stylesheet half of S12's licence scan.** The limit is stated in
   the proof's docstring, the evidence description and section 8. The
   bundler lists only the CSS entry file, so no finer list was available.
6. **P3, absolute paths in `dist/modules.json`.** The Vite plugin now writes
   paths relative to the frontend directory, `proof_s12_code.py` reads them
   that way and asserts none is absolute, and migration draft 1 says the
   file must stay relative or be excluded. The record's citation for
   `armorStatDisplay` is corrected to `review_ui.js:806-844`.

## Other edits

- The four `exercises/*.patch` files that touch `view.ts` or `view.test.ts`
  were regenerated, because their context lines moved. Their content is the
  same change.
- The record's figures follow the code: 32 unit tests (was 28), 298 lines of
  projection (was 285), 816 and 1,410 for the two totals.
- `docs/evidence/issue-206/README.md` was captured again in full. The
  build-reproducibility fence is now part of the same capture.
- The screenshots were not regenerated: nothing a fixture renders changed.

## Result

The recommendation is unchanged (GO), and no gate result changed. H1 now
rests on measurements for all required items. H9's text records one
development-only weakening that the first version did not state.

## Surprising, for the next agent

- **A hostile `disposition` is a useful negative test for the control
  rule.** Under the first, looser rule S2 passed with buttons on members
  whose disposition was markup.
- **Vite's default `allowedHosts` accepts any `*.localhost` name.** A dev
  proxy with `changeOrigin` therefore turns Flask's exact-Host check into
  that allow-list.
- **An unquoted shell heredoc mangles backticks and backslashes** in text
  passed to a script; this cost two retries while editing evidence tooling.
