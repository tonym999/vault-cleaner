# 2026-10-04 — #206 planning: Svelte 5 + TypeScript + Vite frontend spike

Created issue #206 and planned it on `feat/issue-206-svelte-frontend-spike`,
cut from `main` at `c978a5b6d8f6512539810436b743d87bbc3c166c`. The plan is
`handoffs/issue-206-implementation-plan.md`. Refs #206.

## Authorization

The owner authorized, in this session: merging PR #205; creating the issue
and adding it to the project; and committing and pushing the plan on its
allocated branch. No PR was opened. Implementation needs the owner's approval
of the plan SHA and a separate authorization.

- **Planner:** Anthropic `claude-opus-5-5` (Claude Code desktop session; the
  session does not report its native effort setting, so none is recorded).
- **Issue checks after creation:** #206 open, label `enhancement`, on the
  vault-cleaner project with status `Todo`, no milestone (no M10 milestone
  exists).

## Owner decisions recorded in the issue

- The current CSS, markup, layout and colours are not requirements. A fresh
  design with ready-made components is welcome. Visual and DOM parity are not
  acceptance criteria; the meaning of the information and the review workflow
  are.
- The Jinja hybrid from #137 is a measured fallback, not an adopted plan.
- This is a hobby project: learning value and development experience count.

## Decisions in the plan

- **Plain Svelte with Vite, not SvelteKit.**
- **Shortlist:** shadcn-svelte (on Bits UI), Skeleton, Flowbite Svelte. Each
  gets a small CSP probe; the slice is built with one.
- **Parity is replaced by information parity:** what the slice shows must
  equal what the server's envelope says.
- **The proof stays under `spikes/issue-206/`,** with its own `package.json`,
  lockfile and `.gitignore`. No production file, and not the root
  `.gitignore` or `pyproject.toml`, is touched.
- **The design contract is split** into binding behaviour and free
  presentation; the plan carries a starting table.
- **Implementer:** `claude-opus-5-5` at `high`, Judgement rung. **Review
  path:** independent adversarial review.

## Measured while planning

- Node `v24.20.0` and npm `12.0.2` are installed and the registry is
  reachable. Versions and licences of the candidate packages are in the plan;
  all are MIT or Apache-2.0 and all four libraries declare Svelte 5 support.
- The CSP has no `img-src` or `font-src`, so both fall back to
  `default-src 'none'`: image files, `data:` URIs and web fonts are blocked.
  Vite inlines small assets as `data:` URIs by default.
- A `POST` must carry the server's own `Origin`, so a Vite development server
  on another port cannot call the API as it stands. The development loop is
  an experiment in the plan.
- The root `.gitignore` ignores `dist/` but not `node_modules/`.
- `python3 scripts/check_model_roster.py` reports `2 stale`; neither is the
  `claude-opus-5-5` row.

## For the next agent

- **Merging PR #205 closed #137.** The PR body said the PR "does not close"
  the issue, and GitHub read the keyword without the negation. The owner had
  not intended that. It was not reopened: `AGENTS.md` forbids reopening an
  issue automatically, so that is the owner's decision. In a non-closing PR
  body, write only `Refs #N`.
- CodeRabbit left three minor comments and one nitpick on PR #205, all in the
  frozen `spikes/issue-137/` code. None was acted on.
- `docs/review-rendering-architecture.md` still reads "GO, hybrid" as #137's
  own conclusion. Only the PR description and issue #206 say the owner has
  not adopted it.

## Amendment 1 (2026-10-04): the owner's CSP policy

The first plan commit, `b6a7c467bceba0e509266935bab0ff8fceab0bd8`, was never
approved. The owner asked what relaxing the CSP would cost and then decided,
in this session:

- **Pre-approved additions:** `img-src 'self' data:`, `font-src 'self'`, and
  `'unsafe-inline'` in `style-src`. None lets injected content run code.
- **Unchanged:** `script-src 'self'`, `connect-src 'self'`,
  `default-src 'none'`, `object-src 'none'`, `base-uri 'none'`,
  `frame-ancestors 'none'`, `form-action 'none'`. No remote origin in any
  directive.

What the amendment changes in the plan, and nothing else: experiments S7 and
S9, gate H7 and the paragraph under the gate table, one stop condition (plus
a new one protecting production routes), likely finding 1, the costs item in
the decision record, and two checklist lines.

- The unchanged policy is still measured first and still preferred. An
  addition is used only when a component needs it, and the record names that
  component.
- A pre-approved addition no longer makes the result conditional. Anything
  beyond those three still does.
- If an addition is used, the migration drafts must carry the `SERVER_CSP`
  change as its own reviewable item.

Measured for the amendment: Flask runs `after_request` functions in reverse
order of registration (a two-function probe printed `['second', 'first']`),
so production's `secure_response` runs last and a spike cannot override the
header that way. The plan tells the implementer to wrap `app.wsgi_app` for
spike paths only.

Issue #206's body still carries the stricter wording. It was not edited; the
plan records the divergence under *Dependencies and assumptions*.

## Amendment 2 (2026-10-04): the owner's review of `b8a8680`

The owner reviewed plan SHA `b8a86806ae5a3e86f615bfcdc57f5d481239b87b`, did
not approve it, and raised three P2 findings and one main recommendation.
All four are accepted.

- **P2, conflicting inline-style requirements.** Amendment 1 allowed
  component-generated inline styles, but the binding-constraints table still
  said "no inline style or script". The row now keeps the inline-script
  prohibition, forbids hand-written inline styles in the slice's source, and
  allows component-generated ones only inside the approved envelope.
- **P2, information parity missed the comparison content.** S1 checked
  membership, dispositions, verdicts and counts, so a simplified page could
  drop tuning slots or protection and still pass. The plan gains a *Required
  information* section, taken from what production shows
  (`review_ui.js:1201-1288`, `:1319-1422`, `:1489-1557`), and S1 now tests
  those values from the envelope, asserts that every value differing within
  a group is visible for each member with no interaction, and carries a
  negative control. Layout, styling and wording stay free.
- **P2, the installed-wheel proof needed a browser.** A 200 for the HTML does
  not show the JavaScript and CSS load. S8 now has Chromium render a group
  and complete an acknowledged verdict against the installed wheel, with Node
  absent from the server environment's `PATH`.
- **Main recommendation: maintenance effort and the development loop decide
  the outcome.** H8 and H9 only informed the comparison, so a correct slice
  could get a GO without delivering the benefit the owner wants. GO now
  requires all nine gates. H8 and H9 have criteria but no numeric threshold;
  an unclear H8 or H9 makes the result conditional. A new experiment, S14,
  makes three small changes to the slice and sets them beside the same
  changes in the current page and the Jinja hybrid, and the README gains a
  "make a change yourself" walkthrough for the owner.

Likely findings gained a sixth (H8 or H9 passed on a number), and the review
checklist follows each change. The amendment touches only the plan and this
entry.

## Amendment 3 (2026-10-04): licences, after the first dispatch stopped

The owner approved `732de2286328763d86781b300ae8c00dd56a692e`. The dispatch
comment was posted
(<https://github.com/tonym999/vault-cleaner/issues/206#issuecomment-5979714598>)
and a `claude-opus-5-5` implementer was dispatched as a Claude Code subagent.
It stopped at the licence stop condition before writing any code: the branch
stayed at `732de22` and nothing was committed. The review base stays
`732de22`.

- **What stopped it.** `vite@8.3.2` depends on `lightningcss ^1.33.0` and
  `@tailwindcss/node@4.3.3` on `lightningcss 1.32.0`; `lightningcss` is
  MPL-2.0. The plan's toolchain table had checked only each direct package's
  licence. The orchestrator confirmed these with `npm view`, and also that
  `axe-core` is MPL-2.0 and that `flowbite-svelte@1.33.1` depends on
  `apexcharts`, whose licence field is `SEE LICENSE IN LICENSE`.
- **Reported by the implementer, not re-checked:** every shortlisted library
  and daisyUI needs Tailwind 4; a tree with Vite 7.3.6 and plugin-svelte
  6.2.4 has nothing outside the original list; `apexcharts` is dual-licensed
  with a revenue threshold.
- **Owner decisions.** MPL-2.0 is accepted for build-time-only development
  dependencies that contribute no code to the built output. Flowbite Svelte
  is dropped from the shortlist and daisyUI replaces it.
- **Plan changes.** A *Licences* section; the shortlist; the licence stop
  condition; a licence scan in S12 covering the installed tree and the
  packages that contribute to the built output; S13's note on axe-core;
  likely finding 7 and one checklist line.
- **TypeScript pinned to 6.0.3,** not 7.0.2: `svelte-check@4.7.6` peers
  `typescript ^5.0.0 || ^6.0.0`.
- **Role note.** The amendment was written in the orchestrator's session
  acting as planner (`claude-opus-5-5`), at the owner's direction. It
  touches only the plan and this entry.

The amended plan needs a new approval by SHA before the implementer is
dispatched again. The dispatch comment on the issue names `732de22` and has
not been updated.
