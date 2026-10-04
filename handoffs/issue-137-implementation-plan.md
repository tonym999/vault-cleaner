# Issue #137 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#137 — M10 spike: prove a Jinja server-rendered review seam before migrating the UI`

**Milestone:** none assigned (the issue is titled M10; no M10 milestone exists on GitHub and `PLAN.md` has no M10 section)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Claude Code desktop session; the session does not report its native effort, so none is recorded)

**Implementation model selected:** `claude-opus-5-5` at `high` (Judgement rung; justified below)

**Plan baseline:** `main` at `eff10dfdb7dd5df6e0bf37d01a8ffeb32bf2c823` (2026-10-03)

**Allocated branch:** `feat/issue-137-jinja-render-spike` (this plan is its first commit)

The implementer must **not** open a pull request or edit this file. The branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Decide, with measured evidence, whether the permanent review presentation
should move from imperative browser DOM construction to Flask/Jinja
server-rendered HTML, and in which shape (shell only, fragments, whole page,
or a hybrid). The spike must be free to conclude **NO-GO**.

The spike lands a decision record, reproducible evidence, and an isolated
proof. It lands **no production change**: nothing under `src/`, `tests/`,
`pyproject.toml`, `.github/`, `PLAN.md` or `AGENTS.md` is touched.

## Context & Measurement

All measurements were taken on the plan baseline with fake fixtures only.

### The current rendering seam

- The server serves a fixed allow-list of four resources read lazily through
  `importlib.resources`: [app.py:96-120](../src/vault_cleaner/server/app.py#L96-L120).
  The Flask app is created with `static_folder=None`
  ([app.py:313](../src/vault_cleaner/server/app.py#L313)); no template is
  rendered anywhere in `src/`.
- Every response gets `no-store` and the CSP from `secure_response`
  ([app.py:353-360](../src/vault_cleaner/server/app.py#L353-L360)). The CSP
  ([app.py:85-94](../src/vault_cleaner/server/app.py#L85-L94)) includes
  `script-src 'self'`, `style-src 'self'` and **`form-action 'none'`**.
- Host, cookie and Origin are enforced for every route in one
  `before_request` ([app.py:318-351](../src/vault_cleaner/server/app.py#L318-L351));
  a `POST` without an `Origin` header is rejected.
- `create_app` accepts an `assets` mapping
  ([app.py:302-316](../src/vault_cleaner/server/app.py#L302-L316)), and
  `add_asset` rejects only `/bootstrap` and `/api` prefixes
  ([app.py:427-441](../src/vault_cleaner/server/app.py#L427-L441)). A caller can
  therefore add resources, and register further routes on the returned app,
  without editing `app.py`.
- The one authoritative envelope is `session_metadata`
  ([session.py:473-498](../src/vault_cleaner/server/session.py#L473-L498)),
  built under `session.mutation_lock`. `revision_headers`
  ([session.py:106-113](../src/vault_cleaner/server/session.py#L106-L113))
  already snapshots both revisions as a header pair.
- `POST /api/verdicts` validates revisions and fingerprint, then returns that
  envelope as JSON ([app.py:655-693](../src/vault_cleaner/server/app.py#L655-L693)).

### What the browser does today

| File | Lines | Role |
| --- | --- | --- |
| [review_ui.js](../src/vault_cleaner/ui/review_ui.js) | 1851 | snapshot projections, filter/sort, and all DOM builders |
| [review_server.js](../src/vault_cleaner/ui/review_server.js) | 1793 | session state, fetch, adopt/reconcile, lifecycle |
| [review_server.html](../src/vault_cleaner/ui/review_server.html) | 79 | static shell with the persistent live regions |
| [review.css](../src/vault_cleaner/ui/review.css) | 509 | styles, including the orientation switch |

- **Armor duplicate projection is re-derived in JavaScript** from the snapshot:
  `exactDuplicateGroupsFromSnapshot` (`review_ui.js:318`) and
  `sameStatGroupsFromSnapshot` (`review_ui.js:472`). Presentation derivation
  follows: `armorMemberStatus` (`:1218`), `armorMemberCanVerdict` (`:1289`),
  `armorStatSpike` (`:1319`), `armorComparisonSpecs` (`:1489`), the two matrix
  tables (`:1570`, `:1605`) and `armorGroup` (`:1773`).
- **Filtering is client-side over the whole snapshot:** `filterItems`
  (`review_ui.js:232`), `matchesArmorGroup`/`filterArmorGroups`
  (`review_ui.js:747-777`). The duplicates scope sentence is computed in
  `duplicateScopeText` (`review_server.js:283`) and written into a live region
  only when its text changes (`review_server.js:1390-1398`).
- **A verdict acknowledgement repaints in place.** `mutateVerdicts`
  (`review_server.js:1526`) posts, then `adopt` (`review_server.js:944`)
  rebuilds only when the report revision or fingerprint changed; otherwise it
  calls `repaintRows` (`:935`), which flips `aria-pressed`, `disabled` and one
  text node on existing elements (`review_ui.js:1168`, `:1790`).
- **Focus restoration on a rebuild works by element id only**
  (`review_server.js:945`, `:1009-1012`). The armor verdict buttons carry no
  `id` (`review_ui.js:1427-1447`), so a rebuild while one is focused already
  loses focus today. The in-place path is what protects them.
- **Three persistent live regions live in the static shell:** `#vc-status`
  (`review_server.html:13`), `#vc-reconciliation` (`:52`) and
  `#vc-duplicate-scope` (`:72`). `announce` (`review_server.js:755`) only sets
  `textContent`.
- **The comparison orientation is already owned by CSS, not by JavaScript.**
  `.armor-group` is a size container (`review.css:188`); both tables are always
  in the DOM, and container queries keyed on `data-member-count` switch them
  (`review.css:364-388`). Measured:

  ```bash
  grep -rnE 'ResizeObserver|matchMedia|clientWidth|getBoundingClientRect' src/vault_cleaner/ui/*.js
  ```

  prints nothing. Each member's verdict cell is therefore built twice, once per
  orientation, and registered under one id in `state.duplicateRows`
  (`review_ui.js:1465-1470`).

### Jinja facts measured in the project venv (Flask 3.1.3, Jinja2 3.1.6)

```bash
.venv/bin/python - <<'EOF'
from flask import Flask, render_template_string
app = Flask("x")
for name in ["a.html", "a.svg", "a.j2", "a.html.j2", "a.txt", None]:
    print(repr(name), app.select_jinja_autoescape(name))
with app.app_context():
    print(render_template_string('<td data-id="{{ i }}">{{ n }}</td>',
          i='"><script>x</script>', n='<img src=x onerror=1>'))
    print(render_template_string('{{ i }} {{ i|int }}', i="18446744073709551615"))
print(app.jinja_env.undefined.__name__)
EOF
```

- Flask's autoescape is **chosen by file extension**: on for `.html`, `.svg`
  and string templates; **off for `.j2`, `.html.j2` and `.txt`**.
- Hostile values in text and in a quoted attribute came out escaped.
- `|int` accepts an id string and returns a number: a template can break the
  opaque-id rule without any Python change.
- Flask's default `Undefined` is silent: a misspelt context key renders as
  nothing.

### Packaging

`pyproject.toml:31-32` packages `["*.css", "*.html", "*.js"]` for
`vault_cleaner.ui`. A wheel built from a copy of the tracked source with one
probe at `ui/probe_top.html` and one at `ui/templates/probe.html` contained
the first and **omitted the second**. `scripts/check_wheel_install.py`
requests only `/` and three hard-coded assets
([check_wheel_install.py:19-24](../scripts/check_wheel_install.py#L19-L24)),
so it would not notice.

### Fake fixtures available for the slice

| Fixture | Exact groups (members, proposals) | Same-stat groups (members, proposals) |
| --- | --- | --- |
| `tests/fixtures/armor_close.csv` | (2, 1) | (2, 2) |
| `tests/fixtures/armor_duplicates_ui.csv` | (3, 1) | none |
| `tests/fixtures/armor_same_stat_ui.csv` | none | (2, 2) |
| `tests/fixtures/armor_same_stat_four_ui.csv` | none | (4, 4) |

`armor_close.csv` alone gives an exact group with one proposal-controlled and
one read-only member, plus a same-stat group. No armor fixture carries hostile
text; `tests/fixtures/weapons_hostile.csv` is weapons only.

### Baseline verification

`.venv/bin/pytest -q` → `1342 passed`. `python3 scripts/check_model_roster.py`
→ `7 models, 21 assignments, 0 stale`.

## Dependencies and assumptions

Divergences between the issue body and the baseline:

1. **`WORKLOG.md` is frozen** (#193). The acceptance criterion "`WORKLOG.md`
   records the findings" means an entry file under `worklog/`.
2. **"Return to Sol for replanning"** means the escalation route
   `implementer → orchestrator → planner`.
3. **#136 is closed** (PR #169). Its contract is
   [docs/review-ui-design-contract.md](../docs/review-ui-design-contract.md),
   later extended by #171 with the Proposals surface (section 5.13). The spike
   uses that file and never the prototype archive.
4. **#131 is closed, but M9 is not finished.** #152, #177, #178, #116 and #115
   are open. That does not block this spike. It does constrain the order of
   any follow-up tickets: the Proposals design in section 5.13 needs snapshot
   fields that only #178 adds.
5. **Question 5 assumes the orientation switch may be browser-measured. It is
   not.** It is CSS container queries today (see above). The question becomes
   whether server-rendered markup keeps those queries working unchanged.
6. **The issue was written under the two-PR lifecycle.** This ticket uses one
   branch and one PR (#195).
7. **Creating follow-up issues is an external mutation** that needs the
   owner's explicit authorization (`AGENTS.md`, *User authorization gates*).
   The implementer drafts the tickets in the decision record and creates
   nothing. The issue's follow-up gate is met when the owner authorizes
   creation from those drafts.
8. **There is no M10 milestone.** `AGENTS.md` forbids one-off milestones, so
   the drafts leave the milestone for the owner.
9. **`PLAN.md` is not edited here.** Recording the settled M10 architecture in
   `PLAN.md` is a milestone-level criterion on tracker #138; the decision
   record names it as work for the first follow-up ticket.

Planner decisions the owner approves with this plan:

- **The proof is committed, under a new top-level `spikes/issue-137/`.** The
  issue allows throwaway code, but the evidence convention requires every
  transcript to be reproducible, which needs the code at a committed path.
  `spikes/` is outside `src/`, so it is not packaged, and outside `tests/`, so
  CI does not run it. It is frozen evidence, not maintained code.
- **The proof wraps the production app and does not modify it.** It calls
  `create_app` with extra `assets` and registers its own routes on the
  returned app, so the real auth, Host, Origin, CSP and `no-store` handling
  apply to every spike route.
- **The proof implements the fragment shape for the Armor duplicates
  surface,** because that shape carries the lifecycle and focus risk. The
  other shapes are assessed against it with the cheaper experiments listed
  below.

## Proposed Plan & Scope

### Proof code

#### [NEW] `spikes/issue-137/README.md`

What the directory is, that it is frozen evidence for #137, and one command
per proof. State plainly that nothing here ships.

#### [NEW] `spikes/issue-137/` Python modules (names are the implementer's choice)

1. **A template environment** built explicitly: `jinja2.Environment` with
   `autoescape=True` unconditionally, `undefined=StrictUndefined`, and a loader
   over a **fixed allow-list of template names**. No request value reaches the
   loader. Record a comparison against Flask's own `render_template` with a
   `template_folder` (extension-driven autoescape, silent `Undefined`, a
   filesystem search path) and choose one for production with reasons.
2. **A context builder:** a pure function from the schema-version-1 envelope
   (the `dict` that `session_metadata` returns) to the template context for
   the Armor duplicates surface. It ports only *presentation* derivation from
   the JavaScript named above. It must not re-derive grouping, membership
   order, survivor choice or proposal eligibility: those come from
   `exact_duplicate_groups`, `same_stat_groups`, `preferred_survivor_id`,
   `disposition`, `proposal_action` and the envelope's `verdicts`. `id` and
   `hash` stay `str` end to end.
3. **A spike app factory** that calls the production `create_app`, adds the
   spike's page, script and stylesheet through `assets`, and registers
   `GET` routes for the rendered fragment. The fragment is rendered from
   `session_metadata(session)` under `session.mutation_lock` and carries
   `revision_headers(session)`, so the browser can discard a fragment that
   does not match the envelope it has adopted.

#### [NEW] `spikes/issue-137/templates/`

Templates for the slice: section headings, exact group, same-stat group, stat
spike, banners, both matrix orientations, verdict controls, read-only member
status, empty state. Reuse the production class names and `data-*` attributes
so [review.css](../src/vault_cleaner/ui/review.css) applies unchanged (link
the production stylesheet; do not copy it).

Template rules, each enforced by a spike check that scans the template bytes:
every interpolation in an attribute is quoted; no `|safe`, `Markup`,
`{% autoescape false %}`, `|int`, `|float`, `style=`, `on…=` handler or inline
`<script>`; no `{% include %}`/`{% extends %}`/`{% import %}` with a
non-literal name.

#### [NEW] `spikes/issue-137/` browser script

The smallest script that installs fragments and keeps the browser-owned state.
It may load the production `review_ui.js`/`review_server.js` read-only for
comparison, but must not depend on their DOM builders for the slice.

### Experiments the proof must run

Each produces a transcript in the evidence file. Browser proofs use the pinned
Chromium and must **fail, not skip,** when it is missing.

| # | Question | Experiment | Pass means |
| --- | --- | --- | --- |
| E1 | 2 | Render `armor_close.csv`, `armor_duplicates_ui.csv`, `armor_same_stat_ui.csv` and `armor_same_stat_four_ui.csv` through the real upload route. Compare a normalised projection of the Jinja DOM with the production JavaScript DOM for the same session (group order, headings, member ids, every cell's text, button names, `aria-pressed`, `disabled`, `data-*`). | Equal for all four, or every difference listed and explained |
| E2 | 6 | Overlay hostile and long values on **every string field** of an envelope (names, owners/locations, notes, perks, archetypes, state text, ids, hashes), including ids `18446744073709551615`, `007` and one containing `"`, `<`, `'` and a space. Render, insert with the chosen mechanism, and assert in a real browser: no dialog, no added `script`/`img`/`b`, no CSP violation, text round-trips exactly, ids are byte-identical strings. | All inert; ids unchanged |
| E3 | 3 | Approve, Veto and Unset a proposal member through the unmodified `POST /api/verdicts`. Show the rendered state after the acknowledgement with no optimistic update: delay the response and assert the DOM is unchanged until it arrives. | Correct state only after the ack |
| E4 | 3 | Force `stale_verdicts` and `stale_report` (a second client mutates, or re-uploads, between render and click). Show reconciliation refreshes the rendered content, and that a fragment whose revision headers trail the adopted envelope is discarded. | No stale fragment is ever installed |
| E5 | 4 | Measure, for each candidate repaint mechanism in *Mutation and repaint candidates*: is the focused control the same node after the ack; if not, is focus restored to the equivalent control; are `#vc-status`, `#vc-reconciliation` and `#vc-duplicate-scope` the same nodes; is tab order unchanged. | Recorded per mechanism |
| E6 | 4, 5 | Repeat the checks of `test_armor_matrix_inactive_orientation_is_unreachable_by_keyboard` and `test_armor_matrix_orientation_flips_at_its_measured_threshold` ([test_server_browser.py:929-1018](../tests/test_server_browser.py#L929-L1018)) against the Jinja markup at 1440, 1024 and 390 px, plus the page-does-not-scroll-sideways check (`:884`). | Same thresholds as `review.css:364-388`; inactive table out of the tab order and accessibility tree; no member-by-member horizontal navigation |
| E7 | 7 | A script modelled on `scripts/check_wheel_install.py`: copy the tracked source to a temporary tree, overlay the templates at the proposed production location with the proposed `package-data` change, build a wheel, install it into a fresh venv with source-path escapes removed, confirm the package origin, and render and serve a template from the installed package. Try at least the nested `ui/templates/` layout. | Renders from the wheel, or a concrete blocker is recorded |
| E8 | 7 | For every spike route: the response headers equal the production ones (`Cache-Control`, CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`); unauthenticated, wrong-Host and wrong-Origin requests are refused; Chromium reports zero CSP violations for the whole slice. | No header or CSP directive differs |
| E9 | 1 | Whole-page shape: measure what a full-document response after a mutation does to focus, scroll position, the live regions and unsent filter text. Record that `form-action 'none'` rules out a script-free form post. | Recorded |
| E10 | 1, 8 | Filter ownership: for the group-kind selector and one facet filter, compare (a) the server renders every group and the browser hides non-matching ones from `data-*` attributes, with (b) the server filters from validated query parameters. Count what each leaves in JavaScript and what each would add to Python, including where `duplicateScopeText` would live. | Recorded with line counts |

### Mutation and repaint candidates

The verdict response stays JSON. The candidates differ in what happens next:

- **R1, in-place:** the server renders structure; after an ack the browser
  flips `aria-pressed`, `disabled` and the status text on existing nodes from
  the envelope, as today. Fragments are fetched only when the report changes.
- **R2, refetch and replace:** after an ack the browser fetches the fragment
  for the acknowledged revisions and replaces the group or the list, restoring
  focus by a stable control id (unique per orientation).
- **R3, refetch and patch:** as R2, but the browser applies only attribute and
  text differences to existing nodes.

The contract's rule is that *a verdict repaint never rebuilds the focused
element* (design contract, section 7). Measure all three with E3 to E5 and
choose one. State which announcements each preserves by construction, and say
plainly that real screen-reader output was not measured.

### Decision record

#### [NEW] `docs/review-rendering-architecture.md`

Sections, in this order:

1. **Decision:** one of Jinja whole-page, Jinja fragments, hybrid, or NO-GO,
   in the first paragraph, with the go/no-go recommendation.
2. **Shapes compared** (the issue's four), each against the gates below.
3. **Template and resource layout,** and the template-context contract for the
   slice (keys, types, which envelope field each comes from).
4. **State and repaint flow,** including stale reconciliation and which
   presentation state stays browser-owned.
5. **JavaScript keep/remove map:** one row for each of the ten
   responsibilities the issue lists, with current `file:line` ranges, the
   verdict (keep, remove, move to Python, move to template) and line counts.
6. **Findings:** security, packaging, CSP, accessibility, focus and live
   regions, responsive ownership. Link each claim to an evidence fence.
7. **Limits of the evidence:** what was not measured.
8. **Follow-up ticket drafts.** If GO: bounded tickets in dependency order,
   accounting for each of the seven workstreams in the issue's follow-up gate
   or justifying a merge or omission; each with a title, type label, an
   algorithmic scope rule, stop conditions, and `Depends on #N` lines
   (including the open M9 tickets where relevant). If NO-GO: one draft for the
   recommended alternative. **Drafts only; create no issue.**

Decision gates. GO requires G1 to G7; G8 decides between shapes:

| Gate | Requirement | Evidence |
| --- | --- | --- |
| G1 | Rendered parity with production for the slice | E1 |
| G2 | Every untrusted value inert; ids and hashes opaque | E2 |
| G3 | Server-acknowledged state only; stale fragments never installed | E3, E4 |
| G4 | Focus kept or restored; persistent live regions never recreated | E5 |
| G5 | Orientation switch and inactive-table accessibility unchanged | E6 |
| G6 | Templates work from an installed wheel | E7 |
| G7 | Auth, Host, Origin, `no-store` and the CSP unchanged | E8 |
| G8 | The authority split is cleaner: no rule (filter semantics, counts, eligibility) has to exist in both Python and JavaScript, and the JavaScript removed outweighs what is added | E10, keep/remove map |

If a gate can be met only by a change listed under *Stop conditions*, that is
a stop, not a GO with a caveat.

### Evidence and worklog

#### [NEW] `docs/evidence/issue-137/README.md`

Verbatim transcripts for E1 to E10, plain text, each fence reproducible on its
own from the repository root. Fake data only.

#### [NEW] `worklog/YYYY-MM-DD-issue-137-implementation.md`

What was done, the decision, the dispatch record's notable outcome, and
surprises for the next agent.

## Mechanical inclusion test

A hunk is **in scope** if and only if both hold:

- its path is under `spikes/issue-137/`, or under `docs/evidence/issue-137/`,
  or is exactly `docs/review-rendering-architecture.md`, or is a new
  `worklog/*-issue-137-*.md` entry file; and
- it is needed to answer one of the issue's eight questions or to build or
  verify the proof slice.

The first clause is checkable by command and must print nothing:

```bash
git diff --name-only origin/main...HEAD | grep -vE '^(spikes/issue-137/|docs/evidence/issue-137/|docs/review-rendering-architecture\.md$|worklog/[0-9-]+-issue-137-[a-z0-9-]+\.md$|handoffs/issue-137-implementation-plan\.md$)'
```

Worked examples:

- **IN SCOPE:** a Jinja macro for the verdict controls under
  `spikes/issue-137/templates/`.
- **IN SCOPE:** a Python port of `armorComparisonSpecs` in the spike's context
  builder.
- **IN SCOPE:** a spike script that overlays templates onto a temporary copy
  of the source and builds a wheel from that copy.
- **OUT OF SCOPE:** adding `templates/*.html` to `pyproject.toml` on this
  branch. The spike proves the change on a temporary copy and recommends it.
- **OUT OF SCOPE:** a new `tests/test_*.py`, or any edit to
  `scripts/check_wheel_install.py`, `review.css` or `review_ui.js`.
- **OUT OF SCOPE:** templates for the Proposals surface, uploads, metrics or
  session actions. One slice answers the questions.
- **OUT OF SCOPE:** creating, editing or commenting on any GitHub issue.

### Stop conditions

Stop implementation and return to orchestrator if:

- the proof cannot be built without editing a file outside the allowed paths
  (for example, `create_app` cannot be wrapped as measured);
- any gate can be met only by changing the report, snapshot or envelope
  schema, the session lifecycle, the auth/Origin/Host contract, revision or
  verdict validation, persistence, duplicate rules, group membership or
  ranking, or finalisation semantics;
- any CSP directive would have to change, in either direction;
- a runtime dependency beyond pandas and Flask (with Flask's own
  dependencies) would be needed;
- the slice needs a field the envelope does not carry;
- real vault data would be needed;
- the evidence leaves two shapes tied and the choice turns on owner
  preference rather than a gate;
- the design contract and delivered behaviour conflict in a way section 1 of
  the contract does not settle.

A gate that fails is **not** a stop condition. It is a finding, and it may be
the NO-GO.

Escalation route: `implementer → orchestrator → planner`.

## Implementer model justification

**Judgement rung.** A spike delegates the choice between designs: the plan
fixes the questions, experiments, gates and boundaries, but not the rendering
shape, the repaint mechanism, the filter ownership or the ticket split. That
is "meaningful choices between alternative designs" in the ladder's terms. It
is not High-risk: no production code, persistence or lifecycle changes.
`claude-opus-5-5` is a Judgement primary, its roster row was verified
2026-10-02, and the active runtime can instantiate it, so no manual
cross-provider launch is needed.

## Likely findings

1. **A verdict that asserts rather than measures.** The decision record claims
   focus, live-region or parity behaviour that no evidence fence shows, or a
   fence that cannot be rerun as written. Open every cited fence.
2. **Logic duplicated, not moved.** The Python context builder ports
   presentation derivation while the proposed design still needs the same
   logic in JavaScript for filtering or in-place repaint, and G8 is passed
   anyway. Check the keep/remove map against E10.
3. **An escaping proof that tests the easy contexts.** Hostile values checked
   in element text but not in attributes, `id`/`aria-controls` values, or the
   insertion step; or the overlay skips ids and hashes. An unquoted attribute
   or a `|int` in a template is a defect even if E2 passes.
4. **Scope leakage.** A "small" edit to `pyproject.toml`, `review.css`,
   `app.py` or `tests/`; a browser proof that skips without Chromium; or
   follow-up issues created rather than drafted.

# Reusable implementer execution prompt

Implement issue #137 in `tonym999/vault-cleaner` using the handoff at the approved plan SHA `<plan_sha>` (the orchestrator fills this in at dispatch):

```text
git show <plan_sha>:handoffs/issue-137-implementation-plan.md
```

Read the entire handoff at that SHA, issue #137, tracker #138, `AGENTS.md`, `PLAN.md`, `docs/review-ui-design-contract.md`, `docs/browser-verification.md`, the recent worklog (defined in `AGENTS.md`, *Worklog*), and current relevant code before editing.

Rules:
- work on the existing `feat/issue-137-jinja-render-spike`, which already holds the plan commit; do not create another branch, rebase, or force-push, and record the branch head you start from as your attempt's starting SHA (the orchestrator keeps the ticket's review base, which a later attempt does not move);
- never edit `handoffs/issue-137-implementation-plan.md`;
- apply the plan's mechanical inclusion test to every hunk; this spike changes no file under `src/`, `tests/`, `scripts/`, `.github/`, or `pyproject.toml`, `PLAN.md`, `AGENTS.md`;
- use fake fixtures only; never read `data/`;
- create, edit or comment on no GitHub issue; draft follow-up tickets in the decision record;
- add a dated worklog entry file under `worklog/` (format in `AGENTS.md`, *Worklog*);
- run all verification commands:
  - `.venv/bin/ruff check src tests scripts`
  - `.venv/bin/ruff check spikes/issue-137`
  - `.venv/bin/pytest -q` (baseline: `1342 passed`; the count must not change)
  - `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`
  - `.venv/bin/python scripts/check_wheel_install.py`
  - every spike proof command listed in `spikes/issue-137/README.md`
  - `python3 scripts/check_worklog.py --base origin/main`
  - `git diff --check origin/main...HEAD`
  - the inclusion-test command above, which must print nothing;
- commit and push the implementation branch with `Refs #137`; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. Choosing the rendering shape, repaint mechanism and filter ownership from the evidence is the work of this ticket, not an escalation. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, provide the implementer → orchestrator handoff: starting and head SHAs; the decision in one sentence; the result of each gate G1 to G8 with its evidence fence; every verification command with its output tail; anything not measured; notable implementation choices; and the follow-up ticket drafts' titles in order.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
The diff touches no production code, so its blast radius today is nil. Its
output, though, is an architecture decision that sets the scope of a whole
milestone, and it rests on security claims (escaping, the insertion mechanism,
the unchanged CSP and auth envelope) and on cross-cutting claims about focus
and stale-state handling. A wrong GO is expensive and slow to discover. A
fresh reviewer who reruns the proofs and tries to break the hostile-content
and stale-fragment experiments is the right check.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] The inclusion-test command prints nothing; `git diff --stat origin/main...HEAD -- src tests scripts pyproject.toml .github PLAN.md AGENTS.md` is empty.
- [ ] `.venv/bin/pytest -q` still reports `1342 passed`; the browser suite and `scripts/check_wheel_install.py` pass unchanged.
- [ ] Every proof command in `spikes/issue-137/README.md` was rerun by the reviewer and matches its evidence fence; no browser proof skipped.
- [ ] The decision is stated first and is one of the four allowed outcomes; each gate G1 to G8 has a result and a linked fence.
- [ ] E1 parity covers all four fixtures; differences, if any, are listed.
- [ ] E2 overlays every string field including ids and hashes, checks attribute contexts and the insertion step, and the template scan rejects `|safe`, `Markup`, `|int`, `|float`, unquoted attribute interpolation, inline `style`/handlers/scripts and non-literal template names.
- [ ] E3 shows no DOM change before the acknowledgement; E4 shows a trailing fragment discarded.
- [ ] E5 results exist for R1, R2 and R3, and the chosen mechanism satisfies section 7 of the design contract.
- [ ] E6 thresholds equal `review.css:364-388`; the inactive orientation is out of the tab order and accessibility tree.
- [ ] E7 renders from an installed wheel with the package origin checked, or records a concrete blocker.
- [ ] E8 header comparison and refusal cases cover every spike route; zero CSP violations.
- [ ] The keep/remove map has a row for each of the issue's ten responsibilities with current `file:line` ranges, each opened at the head.
- [ ] Follow-up drafts account for all seven workstreams (or one alternative for NO-GO), each with a scope rule, stop conditions and dependencies; no issue was created.
- [ ] No real data, real ids or `data/` paths appear in the evidence.
- [ ] Likely findings 1 to 4 were each checked.

# Dispatch comment draft

Planned #137 in [handoffs/issue-137-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/<plan_sha>/handoffs/issue-137-implementation-plan.md), approved at plan SHA `<plan_sha>`.

- **Implementer model & effort:** `claude-opus-5-5` at `high` (Judgement rung)
- **Implementation branch:** `feat/issue-137-jinja-render-spike`
- **Likely findings:** a verdict asserted without a rerunnable fence; logic duplicated across Python and JavaScript while G8 is passed; an escaping proof that skips attributes, ids or the insertion step; scope leakage into production files or issue creation.
