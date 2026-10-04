# 2026-10-04 — #206 implementation: Svelte 5 + TypeScript + Vite frontend spike

Implemented #206 on `feat/issue-206-svelte-frontend-spike`, on top of the
plan commit, following `handoffs/issue-206-implementation-plan.md` at the
approved plan SHA. No pull request opened, no issue created or commented on,
no production file changed, `data/` never read. Refs #206.

## Dispatch record

- **Issue:** #206
- **Plan SHA (owner-approved 2026-10-04):** `522f2fb228755b7631685649c9d136bd80ebaa53`. It supersedes `732de2286328763d86781b300ae8c00dd56a692e`, approved earlier the same day, on which the first attempt stopped at the licence stop condition with no commits.
- **Dispatch comments:** https://github.com/tonym999/vault-cleaner/issues/206#issuecomment-5979714598 (for `732de22`) and https://github.com/tonym999/vault-cleaner/issues/206#issuecomment-5979875429 (for `522f2fb`)
- **Branch:** `feat/issue-206-svelte-frontend-spike`
- **Review base SHA (fixed at the first dispatch, not moved by the amendment):** `732de2286328763d86781b300ae8c00dd56a692e`
- **This attempt's starting SHA:** `522f2fb228755b7631685649c9d136bd80ebaa53`
- **Orchestrator:** Anthropic `claude-opus-5-5`, Claude Code desktop session; native effort not reported by the session, so none is recorded. The same session wrote Amendment 3 acting as planner at the owner's direction.
- **Implementer, plan's selection:** `claude-opus-5-5` at `high` (Judgement rung)
- **Implementer, actual:** Anthropic `claude-opus-5-5`, a Claude Code subagent launched from the orchestrator session; the second attempt resumes the same subagent session that made the first. The subagent launch has no effort parameter, so `high` could not be set or confirmed. No model re-selection; no fallback.
- **Review path (plan):** independent adversarial review; reviewer to be selected by the orchestrator after the diff exists.

## What was done

- **The slice** (`spikes/issue-206/frontend/`): the Armor duplicates surface
  in Svelte 5 and TypeScript, built by Vite 8, styled with Tailwind 4 and
  daisyUI 5. Typed logic in `src/lib/` with 28 unit tests that run without a
  browser; markup in `src/components/`.
- **Probes** (`spikes/issue-206/probes/`): one page each for plain Svelte 5,
  shadcn-svelte, Skeleton and daisyUI, for the CSP experiment.
- **Python:** `spike_app.py` wraps the unmodified `create_app` and adds
  three built files to its allow-list; `contract.py` writes envelope samples
  the TypeScript types are checked against; `serve.py` and `dev.py` are the
  try-it command and the development loop; one proof script per experiment
  S1 to S14, plus `check_source.py`.
- **Record and evidence:** `docs/frontend-framework-decision.md` and
  `docs/evidence/issue-206/README.md` with six screenshots.

## Recommendation

**GO:** Svelte 5 + TypeScript + Vite 8, Tailwind 4 with daisyUI 5 on native
controls, the browser projecting the existing envelope, three built files
served by Flask under the unchanged CSP, the build committed so the wheel
needs no Node. All nine gates pass for the slice. H8 passes on structure
(no hand-written DOM code, typed, unit-tested) and not on size: the slice is
not smaller than the code it replaces. Six migration tickets are drafted in
the record; none was created.

## Decisions

- **Projection in the browser, no view-model route.** Everything on screen
  derives from the one adopted envelope, so a finalise (which moves neither
  revision) is shown as soon as an envelope carrying it is adopted.
- **Hand-written TypeScript types, checked against samples the Python server
  generates.** A renamed field fails `contract.py --check`, then the type
  check, then a unit test. The build does not type-check.
- **daisyUI for the slice.** All three shortlisted libraries ran under the
  policy (daisyUI after a one-line override); daisyUI adds no script and the
  page needs only native controls. Bits UI is the measured fallback for a
  widget HTML lacks.
- **`aria-disabled` instead of `disabled`** on verdict and session buttons.
  This departs from the wording of contract section 5.11 and is flagged in
  the record for the owner.
- **Flat, stable file names** for the build (`review_app.html/.js/.css` in
  the wheel proof), which today's `package-data` globs already match.
- **`TypeScript` 6.0.3,** as the amended plan says.
- **`spikes/issue-206/exercises/.gitattributes`** has `*.patch -whitespace`:
  a unified diff keeps one space on an empty context line, which
  `git diff --check` would report. The rule covers only that directory's
  patch files.
- **One evidence fence is edited:** the checkout's absolute path printed by
  svelte-check and vitest is replaced with `<repo>`, and the README says so
  above the fence.

## Surprising, for the next agent

- **A focused button that becomes `disabled` loses focus to `<body>`** in
  the pinned Chromium (151). Production's verdict buttons use `disabled`.
- **Plain Svelte 5 needs nothing from the CSP.** `style` attributes and
  `style:` directives go through the CSSOM, transitions through the Web
  Animations API, and scoped styles into the stylesheet. Bits UI and Zag.js
  components had no violation either.
- **daisyUI, the CSS-only library, is the one with a violation:** a `data:`
  noise texture on buttons. `--fx-noise: none` removes the need for
  `img-src`.
- **Tailwind takes class names from any text it scans.** A
  `data-empty="loading"` attribute pulled in daisyUI's `.loading` rule with a
  `data:` image, and the stylesheet changed when unrelated files did, until
  `app.css` restricted the sources.
- **lightningcss (MPL-2.0) writes `--lightningcss-light` and
  `--lightningcss-dark` properties into the stylesheet** under Vite's default
  CSS target. A modern `build.cssTarget` stops it. S12 checks the built
  files for any such trace; with the default target that check fails.
- **axe-core cannot judge contrast on daisyUI's buttons, badges and
  notices,** because they declare `background-image: none`. `proof_s13_axe.py`
  measures those itself. daisyUI's default dark `primary` measured 4.1:1 and
  is overridden.
- **The shadcn-svelte CLI is interactive** (it was driven through `script`),
  and its default preset adds the `@fontsource-variable/inter` web font
  (OFL-1.1), which the probe removes.
- **Playwright passes a route handler one or two arguments by its
  signature,** so a handler with default arguments receives the request in
  the second one.
- **The server's Tuning Mod Slot sentinel is the string `none/unknown`**
  (`duplicate_reference.py:34`); the slice shows it as an absent value.
- **The fixtures have no read-only same-stat member and no exact survivor
  with a later proposal.** Those cases have unit tests only.

## Not measured

No screen reader; Chromium only; one slice; two of six filters; build
reproducibility on one machine only; no large report. The full list is in
the record's section 8.
