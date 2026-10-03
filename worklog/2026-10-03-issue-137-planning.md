# 2026-10-03 — #137 planning: Jinja review rendering spike

Planned #137 on `feat/issue-137-jinja-render-spike`, cut from `main` at
`eff10dfdb7dd5df6e0bf37d01a8ffeb32bf2c823`. The plan is
`handoffs/issue-137-implementation-plan.md`. Refs #137.

## Authorization

The owner authorized the planning phase only (asked in this session). No PR
was opened, no issue was commented on or created, and the plan is not
approved until the owner names its SHA.

- **Planner:** Anthropic `claude-opus-5-5` (Claude Code desktop session; the
  session does not report its native effort setting, so none is recorded).
- **Pre-planning checks:** #137 open, status `Todo`, no comments; #136 closed
  (PR #169 merged); #131 closed; no branch, plan or worklog entry for #137
  existed; `python3 scripts/check_model_roster.py` reported
  `7 models, 21 assignments, 0 stale`; `.venv/bin/pytest -q` reported
  `1342 passed`.

## Decisions in the plan

- **The spike lands no production change.** Every hunk goes under
  `spikes/issue-137/`, `docs/evidence/issue-137/`,
  `docs/review-rendering-architecture.md` or the worklog. The inclusion test
  is one `git diff --name-only | grep -v` command.
- **The proof is committed, not thrown away,** because evidence fences must
  be reproducible. `spikes/` is a new top-level directory, outside the wheel
  and outside CI.
- **The proof wraps `create_app` and does not edit it,** so the real auth,
  Host, Origin, CSP and `no-store` handling cover every spike route.
- **The fragment shape is the one implemented,** for the Armor duplicates
  surface; the other shapes are compared against it by cheaper experiments.
- **Follow-up tickets are drafted, not created.** Issue creation needs its own
  authorization.
- **Implementer:** `claude-opus-5-5` at `high`, Judgement rung. **Review
  path:** independent adversarial review.

## Measured while planning

No real export was read; all of this used fake fixtures.

- The comparison orientation switch is already CSS container queries
  (`review.css:364-388`). No JavaScript measures layout. The issue's question
  5 presumed it might be browser-measured.
- Flask picks autoescape by file extension: on for `.html`, off for `.j2` and
  `.html.j2`. Its default `Undefined` is silent. `|int` turns an id string
  into a number inside a template.
- A wheel built from the tracked source with a probe at
  `ui/templates/probe.html` omitted it; `pyproject.toml` packages only
  top-level `*.css`, `*.html`, `*.js`. The contract's section 10 said so; this
  confirms it by building one.
- The CSP has `form-action 'none'`, so a script-free form post is not
  available to a whole-page design.
- Armor verdict buttons carry no `id`, and rebuild-path focus restoration
  works by id only (`review_server.js:945`, `:1009-1012`). Only the in-place
  repaint keeps focus on them today.
- `tests/fixtures/armor_close.csv` alone yields an exact group with one
  proposal member and one read-only member, plus a same-stat group. No armor
  fixture carries hostile text.

## For the next agent

- The issue body is stale in places: `WORKLOG.md` is frozen (#193), "Sol"
  means the planner, and the lifecycle is one branch and one PR (#195).
- There is no M10 milestone on GitHub and no M10 section in `PLAN.md`. The
  plan leaves both alone.
- M9 still has open tickets (#152, #177, #178, #116, #115). They do not block
  the spike, but the Proposals design in the contract's section 5.13 depends
  on #178, which matters for the order of any follow-up tickets.
