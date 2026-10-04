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
