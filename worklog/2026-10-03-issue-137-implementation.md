# 2026-10-03 — #137 implementation: Jinja review rendering spike

Implemented #137 on `feat/issue-137-jinja-render-spike`, on top of the plan
commit, following `handoffs/issue-137-implementation-plan.md` at the approved
plan SHA. Attempt starting SHA:
`ae646be8a1cfaf622f8a95d5e3acc3c54c38dbb0`. No pull request opened, no issue
created or commented on. Refs #137.

## Dispatch record

- **Approved plan SHA:** `ae646be8a1cfaf622f8a95d5e3acc3c54c38dbb0` (owner
  approval given in the orchestrator's session, 2026-10-03; dispatch comment
  https://github.com/tonym999/vault-cleaner/issues/137#issuecomment-5974129083).
- **Review base SHA:** `ae646be8a1cfaf622f8a95d5e3acc3c54c38dbb0` (branch
  head at first dispatch).
- **Orchestrator:** Anthropic `claude-opus-5-5` (Claude Code desktop session;
  the session does not report its native effort setting, so none is
  recorded).
- **Plan's implementer selection:** Anthropic `claude-opus-5-5`, effort
  `high`, Judgement rung.
- **Actual implementer:** Anthropic `claude-opus-5-5`, dispatched as a
  subagent of the orchestrator's Claude Code session. The subagent launch
  surface does not expose an effort setting, so the effort is the runtime
  default, not confirmed as `high`.
- **Re-selection:** none.
- **Review path selected by the plan:** independent adversarial review (the
  orchestrator confirms it against the real diff and selects the reviewer).
- **Pre-dispatch checks:** `python3 scripts/check_model_roster.py` reported
  `7 models, 21 assignments, 0 stale`; issue #137 open, status `Todo`; no
  open pull requests; branch head equals the plan SHA.

## Decision

**GO, hybrid.** Jinja renders report-scoped fragments that the browser
installs only when the report changes; a verdict acknowledgement repaints in
place from the JSON envelope (R1); filtering stays in the browser over
server-written `data-*` attributes; the shell stays one persistent document.
The record is `docs/review-rendering-architecture.md`.

Gates: G1 to G8 all pass for that shape. Shell-only fails G8 (the production
shell has nothing to interpolate). Refetch-and-replace fails G4 by the
contract's own sentence (all 225 list elements, including the focused button,
are destroyed). Whole-page fails G4 (focus to `body`, filter text lost,
status region recreated). No stop condition was reached.

## What landed

- `spikes/issue-137/`: the proof. An explicit Jinja environment, a pure
  context builder for the Armor duplicates surface, an app factory that calls
  the unmodified `create_app` and adds two `GET` routes, five templates, a
  browser script, and twelve proof scripts. Nothing under `src/`, `tests/`,
  `scripts/`, `.github/`, `pyproject.toml`, `PLAN.md` or `AGENTS.md` changed.
- `docs/evidence/issue-137/README.md`: a verbatim transcript per experiment.
- `docs/review-rendering-architecture.md`: the decision record, with six
  follow-up ticket drafts. No issue was created.

## Decisions made

- **The spike page is served beside production,** at `/spike/`, by the same
  app and session. That is what makes E1 and E6 a like-for-like comparison:
  both pages read one envelope.
- **Experiment switches are query parameters read in the browser**
  (`?repaint=`, `?filters=`) and checked against fixed lists. They never
  reach the server as a template name.
- **The environment deletes the `safe`, `int` and `float` filters,** so a
  template using one fails to compile. The byte scan stays as well, since it
  also covers `Markup`, inline style and handlers, and unquoted attributes.
- **In-place repaint without a rule in JavaScript.** The server renders the
  three texts a member's verdict can show as `data-*` attributes; the browser
  picks one. The persisted-veto wording therefore lives only in Python.
- **Fragment acceptance is strict equality** of both revision headers with
  the adopted envelope, in either direction, with at most three attempts.
- **Insertion uses `DOMParser` and `importNode`,** never `innerHTML`.
- **E2 overlays a real envelope** and enriches it first, because
  `armor_close.csv` has no protected member, Spirit perk or read-only member
  with a later proposal. Fields that select a code path (`group_kind`,
  `disposition`, `action`, …) are not overlaid; the proof shows they are
  refused instead.
- **E7 reuses helpers from `scripts/check_wheel_install.py`** by loading the
  file, without editing it.
- **Workstream 5 is merged into the Armor duplicates ticket** in the drafts;
  the record says why.

## Measurements

No real export was read. Everything used `tests/fixtures/`; E10 re-classes
two rows of `armor_close.csv` in memory to get a second guardian class.

## Surprises the next agent should know about

- **The in-process snapshot is not in wire order.** `session_metadata`
  returns `dict`s in insertion order; the browser gets them through
  `jsonify`, which sorts keys. A Python renderer that iterates `stats`
  prints the zero-stat line as `health · grenade · super` where production
  prints `grenade · health · super`. E1 caught it; the builder now sorts.
- **`review.css` has no `[hidden]` rule,** and `.armor-section-head` is
  `display: flex`, so the `hidden` attribute does nothing on it.
- **Production writes `class=""`** on cells with no class, because `el()`
  assigns `className`. It is one of the two declared parity differences.
- **A container query measures the content box.** The two-member flip is at
  a 616 px content box, which is a 642 px border box.
- **Chromium restores scroll on reload but not an unsubmitted search value,**
  and `locator.click()` waits forever on a form the CSP blocks; use
  `no_wait_after=True`.
- **`page.unroute()` before `route.fulfill()`** marks a held route handled.
- **Same-stat eligibility comes from the section's `decisions`,** not from
  the member's `proposal_action`. Production does this join in JavaScript
  today; the context builder does the same join.
- **Production filters still work after the server stops.** That decided
  filter ownership.
- **`ruff check spikes/issue-137`** is not run by CI. It passes here.

## Not measured

Screen-reader output; any browser but the pinned Chromium; the Proposals,
metrics, upload and session-action regions; four of the six duplicate
filters and the per-kind facet recount; R3's replace fallback; performance
on a large report.

## Verification

`ruff check src tests scripts` and `ruff check spikes/issue-137` clean;
`pytest -q` 1342 passed; the browser suite with
`VAULT_CLEANER_BROWSER_REQUIRED=1` passed; `scripts/check_wheel_install.py`
passed; all twelve spike proofs print `RESULT: PASS` and were compared
against the evidence fences; `check_worklog.py --base origin/main` and
`git diff --check origin/main...HEAD` clean; the plan's inclusion-test
command prints nothing. Raw output is in the implementer's completion
handoff.
