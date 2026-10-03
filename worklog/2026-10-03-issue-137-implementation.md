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
  (Superseded in fix round 1: the filter and global allow-lists are empty.)
- **In-place repaint without a rule in JavaScript.** The server renders the
  three texts a member's verdict can show as `data-*` attributes; the browser
  picks one. The persisted-veto wording therefore lives only in Python.
  (Corrected in fix round 1: the fragment chose the wording from
  `override_status`, which a finalise changes without a revision. It now
  renders both wordings and the browser chooses.)
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
filters; R3's replace fallback; performance on a large report. (The
per-kind facet recount was listed here at first; fix round 1 measured it for
the Class facet.)

## Verification

`ruff check src tests scripts` and `ruff check spikes/issue-137` clean;
`pytest -q` 1342 passed; the browser suite with
`VAULT_CLEANER_BROWSER_REQUIRED=1` passed; `scripts/check_wheel_install.py`
passed; all twelve spike proofs print `RESULT: PASS` and were compared
against the evidence fences; `check_worklog.py --base origin/main` and
`git diff --check origin/main...HEAD` clean; the plan's inclusion-test
command prints nothing. Raw output is in the implementer's completion
handoff.

## Fix round 1 (independent review of `3140247`)

Two P2 and four P3 findings, all accepted by the orchestrator. New commit on
the same branch from head `314024796679c8d728e20f3f3f2bb1bfde316a66`; nothing
amended. The decision is unchanged: **GO, hybrid.** No gate result changed,
but G3 and G8 now rest on different facts, below. No stop condition was
reached: no new envelope field, header or revision was needed.

- **P2-1, fragment depended on state the revision pair does not cover.**
  `POST /api/finalize` changes `state` and `override_status` and bumps
  nothing, and the fragment rendered `disabled` and the persisted-veto
  wording from them. Fixed by making the fragment a function of the
  snapshot, the verdicts and the revisions only: `context.py` no longer
  reads `state` or `override_status`, the templates render no `disabled`
  and both wordings of every verdict text, and `spike.js` paints the frozen
  gate and the wording choice from the adopted envelope. New experiment E11
  (`proof_e11_finalize.py`): fragment bytes and headers are identical
  across a finalise, an installed page reaches production's finalised
  presentation with no fragment request, and reset and a re-upload under an
  active saved veto also match production. Reset does not share the
  property: with a report loaded it bumps `report_revision`. The record's
  section 4 now lists every envelope input and has a section on state that
  changes without a revision; ticket 2's scope rule and stop conditions
  carry the rule. **The wording still lives only in Python.** What moved
  back to the browser is a lookup (is this id in the active persisted
  vetoes), which production already has; the record says so under "What
  stays in JavaScript for the slice".
- **P2-2, E10 parity held only for the chosen combinations.** Production
  recounts facet options for the selected kind and drops a selected value
  the kind lacks; the spike rendered option counts once in Python. Fixed by
  implementing recount-and-drop in both candidates: in JavaScript for (a),
  where Python now renders no options, and in Python for (b). E10 now
  compares the Class options, the selected value and the reconciliation
  message, and includes the diverging sequence (class Hunter, then kind
  exact). New counts: (a) 62 lines of JavaScript and no Python; (b) 27 and
  63. (a) is still chosen, on the offline behaviour. Option counts and
  labels live in JavaScript only under (a); the record says so in one place.
- **P3-1, template rules had gaps.** The environment now has empty
  allow-lists for filters and globals (`tojson`, `urlize`, `xmlattr` and
  `lipsum` return `Markup`; `filesizeformat` and `round` convert to a
  number). The scan rejects any filter, `{% filter %}` blocks, and
  interpolation inside URL-bearing attributes, with new negative cases.
  Section 3 and ticket 1 updated.
- **P3-2, E9 measured a naive whole-page implementation.** The record now
  separates what is inherent to the shape (a new document recreates the live
  regions; the form post is blocked) from what `whole.js` did (an unassisted
  reload). The rejection stands on the first.
- **P3-3, metrics refetch.** No longer the default. Ticket 3 makes it a gate
  the planner must measure and pass, with in-place paint from the envelope
  as the default; the keep/remove map and section 7 follow.
- **P3-4, unfenced claim.** E2 gained a block requesting the fragment route
  with an envelope the builder refuses: HTTP 500, the production handler's
  bare `internal_error` body, security headers present. The record cites it
  and says which refusal cases are measured where.

Also changed, not asked for: `harness.open_production_duplicates` accepts
production's finalised status text as well as "Connected"; `spike.js` gained
a `sync()` entry point for the proofs (adopt, then fetch only on a report
change); `whole_page.html` and `spikes/issue-137/README.md` were updated to
match; every evidence fence was recaptured, since most proofs' output moved.
New slice counts: 93 lines of seam and 62 of filtering in JavaScript, a
474-line builder and 187 lines of templates, against 908 replaced.

Surprises: `tojson` in a double-quoted attribute is an attribute breakout
even with autoescape on, because it returns `Markup`. Production's
reconciliation message persists across later kind changes until the next
adopt, so E10 compares it once, after the dropping case.

Still not measured: screen readers; other browsers; the other regions; the
four remaining filters, including the piece-counted Tuning Mod Slot facet;
R3's fallback; the `closed` state from the browser; a finalise driven by
the page itself (E11 posts it from outside and has the page adopt the
envelope); performance.
