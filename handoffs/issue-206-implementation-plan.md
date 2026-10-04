# Issue #206 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#206 — M10 spike: evaluate Svelte 5 + TypeScript + Vite as the review frontend`

**Milestone:** none assigned (no M10 milestone exists; `PLAN.md` has no M10 section)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Claude Code desktop session; the session does not report its native effort, so none is recorded)

**Implementation model selected:** `claude-opus-5-5` at `high` (Judgement rung; justified below)

**Plan baseline:** `main` at `c978a5b6d8f6512539810436b743d87bbc3c166c` (2026-10-04)

**Allocated branch:** `feat/issue-206-svelte-frontend-spike` (this plan is its first commit)

The implementer must **not** open a pull request or edit this file. The branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

**Amendment 1 (2026-10-04).** The first plan commit,
`b6a7c467bceba0e509266935bab0ff8fceab0bd8`, treated any CSP change as making
the result conditional. The owner then pre-approved three additions (see
*The security envelope a built frontend must fit*). This amendment changes
only the CSP handling: experiments S7 and S9, gate H7, one stop condition,
likely finding 1 and two checklist lines. `b6a7c46` was never approved.

## Objective

Decide, with measured evidence, whether the review frontend should be rebuilt
in **Svelte 5 + TypeScript + Vite** with a ready-made component library,
keeping Python/Flask as the backend. The answer is GO, NO-GO, or a bounded
conditional recommendation.

The spike builds one vertical slice (the Armor duplicates surface) with a
fresh design, and compares it with the current page and with the Jinja hybrid
that #137 measured. It lands a decision record, reproducible evidence,
screenshots and an isolated proof. It lands **no production change**.

Two things the owner has decided (issue #206, 2026-10-04):

- **Design freedom.** The current CSS, markup, layout and colours are not
  requirements. Visual or DOM parity is not an acceptance criterion. The
  meaning of the information and the review workflow are.
- **This is a hobby project.** Learning value and an enjoyable development
  experience count alongside correctness and maintainability.

## Context & Measurement

Measured on the plan baseline. No real export was read.

### What #137 established, and how to treat it

[docs/review-rendering-architecture.md](../docs/review-rendering-architecture.md)
and [docs/evidence/issue-137/README.md](../docs/evidence/issue-137/README.md)
are comparison material. Assess their claims independently. The facts below
are re-usable because they are about the server and the current page, not
about Jinja:

- The current page is 3,644 lines of JavaScript:
  [review_ui.js](../src/vault_cleaner/ui/review_ui.js) (1,851) and
  [review_server.js](../src/vault_cleaner/ui/review_server.js) (1,793).
- The Armor duplicates slice is 908 of those lines (record, section 5). The
  Jinja hybrid replaced them with 155 lines of JavaScript, a 474-line Python
  builder and 187 lines of templates, with two of six filters written.
- `create_app` can be wrapped without editing it: it takes an `assets`
  mapping, and routes added to the returned app inherit the Host, cookie and
  Origin checks, `no-store` and the CSP
  ([app.py:302-360](../src/vault_cleaner/server/app.py#L302-L360),
  [app.py:427-441](../src/vault_cleaner/server/app.py#L427-L441)).
- **Finalise changes `state` and `override_status` without moving either
  revision** ([app.py:825-828](../src/vault_cleaner/server/app.py#L825-L828)).
  Anything keyed on the revision pair alone goes stale across a finalise.
  This was #137's main review finding.
- Production filters with the server stopped, recounts the Class options for
  the selected group kind, and drops a selected class that kind lacks
  (`review_server.js:263-275`, `:1284-1296`).
- A nested directory under `vault_cleaner.ui` is left out of the wheel:
  `pyproject.toml:31-32` packages only top-level `*.css`, `*.html`, `*.js`.

### The security envelope a built frontend must fit

The CSP ([app.py:85-94](../src/vault_cleaner/server/app.py#L85-L94)) is:

```text
default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self';
object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
```

**Owner decision on the policy (2026-10-04).** Three additions are
pre-approved, because they let a page load its own images and fonts and let
a component set styles, and none of them lets injected content run code:

| Pre-approved addition | Allows |
| --- | --- |
| `img-src 'self' data:` | images and icons from the build, including Vite's inlined assets |
| `font-src 'self'` | fonts bundled in the build |
| `'unsafe-inline'` in `style-src` | `<style>` elements and `style` attributes that a component injects |

Everything else stays as it is: `script-src 'self'`, `connect-src 'self'`,
`object-src 'none'`, `base-uri 'none'`, `frame-ancestors 'none'`,
`form-action 'none'`, and `default-src 'none'`. No remote origin is ever
allowed in any directive. This plan calls the result **the approved
envelope**. The unchanged policy is still preferred: use an addition only
when a measured need exists, and record which component needs it.

Consequences to measure, not assume:

- **No `img-src` or `font-src`,** so both fall back to `'none'`. Under the
  unchanged policy image files, `data:` URIs, icon fonts and web fonts are
  all blocked and icons must be inline SVG elements. Vite inlines small
  assets as `data:` URIs by default. The pre-approved additions lift this
  for same-origin files and `data:` images only.
- **`style-src 'self'`** blocks `<style>` elements and `style="…"`
  attributes in parsed markup. Styles set through the CSSOM
  (`element.style.setProperty`) are not blocked. Which of these Svelte 5 and
  each component library use is the spike's question.
- **`script-src 'self'`** rules out inline scripts and `eval`. This is not
  negotiable in the spike.
- **The spike cannot change the header with `after_request`.** Flask runs
  `after_request` functions in reverse order of registration, so production's
  `secure_response` runs last and overwrites anything the spike sets. To
  serve a spike route under the approved envelope, wrap `app.wsgi_app` in
  the spike's own factory and rewrite the header for spike paths only.
  Production routes must keep the unchanged policy.
- **A `POST` needs `Origin` equal to the server's own origin**
  ([app.py:339-351](../src/vault_cleaner/server/app.py#L339-L351)). A Vite
  development server on another port sends a different `Origin`, so the
  hot-reload development loop is itself a question (experiment S10).

### Toolchain available

```bash
node --version && npm --version
```

gave `v24.20.0` and `12.0.2`; the npm registry is reachable. Current
versions, licences and Svelte peer ranges from `npm view` on 2026-10-04:

| Package | Version | Licence | Svelte peer |
| --- | --- | --- | --- |
| `svelte` | 5.57.1 | MIT | |
| `vite` | 8.3.2 | MIT | |
| `typescript` | 7.0.2 | Apache-2.0 | |
| `@sveltejs/vite-plugin-svelte` | 7.3.1 | MIT | `^5.46.4` |
| `svelte-check` | 4.7.6 | MIT | `^4 \|\| ^5` |
| `vitest` | 5.0.3 | MIT | |
| `tailwindcss` | 4.3.3 | MIT | |
| `bits-ui` | 2.19.5 | MIT | `^5.33.0` |
| `shadcn-svelte` (CLI) | 1.7.0 | MIT | `^5.0.0` |
| `@skeletonlabs/skeleton-svelte` | 5.0.1 | MIT | `^5.40.0` |
| `flowbite-svelte` | 1.33.1 | MIT | `^5.40.0` |
| `daisyui` | 5.7.47 | MIT | none (CSS only) |

All four library candidates declare Svelte 5 support. The shadcn-svelte
documentation has an installation path for plain Vite without SvelteKit.

### Repository facts that shape the proof

- `.gitignore` ignores `dist/` but **not** `node_modules/`. The spike adds
  its own `.gitignore` under `spikes/issue-206/`; the root file is untouched.
- CI lints `src tests scripts` and runs `tests/` only, so `spikes/` is
  outside CI, as `spikes/issue-137/` is.
- `scripts/check_wheel_install.py` copies tracked files into a temporary
  tree and builds from that; #137's `proof_e7_wheel.py` shows how to overlay
  extra files on such a copy without touching `pyproject.toml`.
- Fake fixtures for the slice: `tests/fixtures/armor_close.csv` (an exact
  group with one proposal member and one read-only member, plus a same-stat
  group), `armor_duplicates_ui.csv` (three-member exact),
  `armor_same_stat_ui.csv`, `armor_same_stat_four_ui.csv` (four-member).
- Baseline: `.venv/bin/pytest -q` → `1342 passed`.
  `python3 scripts/check_model_roster.py` → `2 stale` (neither is the
  `claude-opus-5-5` row, verified 2026-10-02).

## Dependencies and assumptions

- **#137 is merged** (PR #205) and its record, evidence and spike are on
  `main`. Merging closed #137; whether it stays closed is the owner's call
  and does not affect this ticket.
- **No M10 milestone exists.** The issue has none.
- **The design contract's behaviour binds; its presentation does not.** The
  implementer must classify
  [docs/review-ui-design-contract.md](../docs/review-ui-design-contract.md)
  and record each presentation choice it changes. Starting classification:

  | Binding (behaviour, accessibility, security) | Free (presentation) |
  | --- | --- |
  | Section 1, levels 2 to 4 | Section 1, level 1 (the prototype as visual target) |
  | Section 5.11: verdict controls only on proposal members; read-only members show status | Section 4: tokens, colours, type, spacing |
  | Section 7: skip link, focusable `h1`, `role="status"` live regions, `aria-pressed` toggles, real labels, visible focus, *a verdict repaint never rebuilds the focused element* | Sections 5.1 to 5.10: anatomy and composition |
  | Section 8: the page never scrolls sideways; ids, hashes and reasons wrap and are never truncated | Section 6: icon choices |
  | Section 9: an empty state says why it is empty | Section 8: breakpoints and the matrix's two-table technique |
  | Section 10 constraints: untrusted values inert, opaque ids, no inline style or script, no request-supplied path | Section 12: open questions 1 to 5 |
  | Section 11: no analytics, telemetry or remote resources | |

- **"No dependency change" means Python and production.** The spike has its
  own `package.json` and lockfile under `spikes/issue-206/`.
- **Follow-up tickets are drafted, never created,** by the implementer.
- **The issue body predates the owner's policy decision.** It says any
  policy change must be recorded as a requirement and not described as
  compatible. Since 2026-10-04 the three pre-approved additions above are
  allowed. The issue's rule still applies in full to every other change, and
  an addition that is used must still be recorded exactly.

Planner decisions the owner approves with this plan:

- **Plain Svelte with Vite, not SvelteKit.** One page behind Flask needs no
  router or server runtime. The record should say so and note what SvelteKit
  would add (its CSP nonce and hash support applies to server-rendered
  markup, which this app does not have).
- **Shortlist: shadcn-svelte (on Bits UI), Skeleton, Flowbite Svelte.** All
  MIT, all Svelte 5. The implementer may swap one for daisyUI with a stated
  reason. Each gets a small CSP probe; **one** is used to build the slice.
- **The proof wraps `create_app`,** as #137 did, and serves the built
  frontend at a spike path beside the production page.
- **Screenshots are committed** as PNG files under
  `docs/evidence/issue-206/`, as `docs/evidence/issue-113/` did.

## Proposed Plan & Scope

### Proof

#### [NEW] `spikes/issue-206/README.md`

What the directory is, that nothing in it ships, the one **try-it command**
that builds and serves the proof for the owner, and one command per
experiment.

#### [NEW] `spikes/issue-206/.gitignore`

Ignores `node_modules/` and the build output directory.

#### [NEW] `spikes/issue-206/frontend/`

A Vite project: `package.json` with **exact** versions, a committed lockfile
installed with `npm ci`, `vite.config.ts`, `tsconfig.json`, and the Svelte 5
source for the slice in TypeScript.

Source rules, each enforced by a spike check over the source files:

- no `{@html}`, `innerHTML`, `outerHTML`, `insertAdjacentHTML` or `eval`;
- `id` and `hash` have a string type everywhere, and no `Number(…)`,
  `parseInt`, `parseFloat` or unary `+` is applied to one;
- no remote URL in source or build output: no CDN, web font or analytics;
- no grouping, ranking, survivor choice or proposal eligibility is computed
  in the browser. Those are read from server data.

#### [NEW] `spikes/issue-206/` Python modules

- **A spike app factory** that wraps the production `create_app`, serves the
  built frontend from a **fixed allow-list** of resources, and, if the chosen
  architecture needs it, adds a spike-only JSON view-model route rendered
  under `session.mutation_lock`. No request value selects a file.
- **A view-model builder,** if used: a pure function from the
  schema-version-1 envelope. The implementer may adapt
  `spikes/issue-137/context.py` by copying it; do not import across spikes.
- **Proof scripts,** one per experiment, each printing `RESULT: PASS` or
  `RESULT: FAIL` and exiting non-zero on failure. Browser proofs use the
  pinned Chromium and **fail, never skip,** when it is missing.

### Architecture questions the implementer settles from evidence

1. **Where the projection lives.** Compare (i) the browser consuming the
   existing envelope and projecting it in typed TypeScript, with (ii) a
   server JSON view-model for report-scoped structure, joined in the browser
   with `verdicts`, `state` and `override_status` from the envelope. Under
   (ii), say how the view-model is kept in step with the envelope, including
   across a finalise.
2. **How TypeScript types follow Python.** Hand-written types with a contract
   check, types generated from Python, or a JSON Schema. Demonstrate what
   happens when a field is renamed on the Python side.
3. **Filter ownership.** Filtering must keep working with the server stopped.
4. **How Flask serves the build.** Stable file names or an allow-list derived
   from Vite's manifest at build or import time; never from a request.
5. **How the wheel gets the build.** Built in CI before packaging, or
   committed build output. Say what a contributor without Node can and
   cannot do.

### Experiments

Each produces a transcript in the evidence file.

| # | Issue question | Experiment | Pass means |
| --- | --- | --- | --- |
| S1 | 4 | **Information parity.** For the four fixtures, with and without verdicts, compare what the slice shows with the server's envelope: group order, every member id, disposition or proposal state, verdict state, which members have verdict controls, and the scope counts. Compare scope text and Class options with the production page for the filter sequences in #137's E10, including the recount-and-drop cases. | Equal, or every difference listed and justified as a presentation choice |
| S2 | 4 | **Hostile content.** Overlay hostile and long values on every string field of the envelope, including ids `18446744073709551615`, `007` and one with `"`, `<`, `'` and a space. Assert no dialog, no injected element, no CSP violation, exact text round-trip, and byte-identical ids in the DOM and in the verdict request body. Run the source-rule scan. | All inert; ids unchanged |
| S3 | 3, 4 | **Acknowledged state only.** Approve, Veto and Unset through the unmodified `POST /api/verdicts`, with the response held: the presentation must not change until it arrives. Force `stale_verdicts` and `stale_report`; the action must not be replayed. | No optimistic state; no replay |
| S4 | 3, 4 | **Finalise, reset, disconnect.** Finalise with a veto in place: the open page must reach the frozen state and the persisted-veto wording with the revision pair unchanged, and match production loaded fresh in meaning. Reset. Stop the server and filter. | Correct in all three |
| S5 | 3 | **Focus and live regions.** After an acknowledgement the focused control is the same node. State and measure the focus policy on a report change. The status, reconciliation and scope regions are the same nodes throughout, and each acknowledgement is one announcement. | Recorded; contract section 7 met |
| S6 | 2 | **Layouts.** At 1440, 1024 and 390 px, light and dark: the page does not scroll sideways; a group's members can be compared without member-by-member horizontal navigation; ids wrap; every control is reachable by keyboard in a sensible order; no hidden duplicate control is in the tab order. Capture the screenshots. | Recorded with screenshots |
| S7 | 2, 5 | **CSP.** First run the whole slice under the **unchanged** policy and record every violation, including every component used and any transition. Then, only if needed, run it under the approved envelope with the fewest additions that give zero violations, and name the component that needs each one. For each shortlisted library, build a minimal probe page (button, toggle, select or equivalent, one overlay if the library has one) and record its violations under the unchanged policy and which additions clear them. Check the build for `data:` URIs, fonts, inline styles and any remote URL. | Zero violations under the unchanged policy or the approved envelope, with each addition used attributed; or the exact further directive a candidate needs |
| S8 | 5 | **Installed wheel.** Modelled on #137's `proof_e7_wheel.py`: overlay the built assets and the `package-data` change on a temporary copy of the tracked source, build a wheel, install it into a fresh environment with no Node on the path, confirm the package origin, and load the slice over HTTP. | Works with Node absent, or a concrete blocker |
| S9 | 5 | **Request envelope.** Every spike route has production's security headers and refuses unauthenticated, wrong-Host and wrong-Origin requests. Production routes served by the spike app keep the unchanged policy byte for byte. | No header differs; the policy on a spike route differs from production's only by pre-approved additions that S7 shows are needed |
| S10 | 1, 6 | **Development loop.** Measure a cold build, a rebuild after a one-line edit, and the output size (raw and gzip). Establish a working edit-and-see loop against the Flask server given the `Origin` rule, and say exactly how it works and what it costs. Record `svelte-check` and the unit-test run. | Recorded |
| S11 | 6 | **Type drift.** Rename one view-model or envelope field on the Python side and show where the mismatch surfaces: type check, build, test, or only at runtime. | Recorded |
| S12 | 3, 6 | **Code comparison.** Line counts for the slice by category: components and markup, application logic (requests, revisions, reconciliation, lifecycle), filtering, types, Python, tests. Set them beside production's 908 and the hybrid's 155 + 474 + 187. Count the installed npm packages and record `npm audit`. | Recorded |
| S13 | 2 | **Automated accessibility check** (for example axe-core) on the slice in both colour schemes. | Violations listed; none left unexplained |

### Decision record

#### [NEW] `docs/frontend-framework-decision.md`

In this order:

1. **Recommendation:** GO, NO-GO, or a bounded conditional recommendation,
   in the first paragraph, with the recommended stack.
2. **Architecture:** the answers to the five architecture questions, with a
   state-ownership table (server, browser, CSS).
3. **Component library comparison:** the shortlist against styling effort,
   keyboard and focus behaviour, accessibility, Svelte 5 compatibility,
   maintenance, licence and the measured CSP result. Cite the official
   documentation used, with the date read.
4. **Design:** the contract classification (binding or free), every
   presentation choice changed, and the screenshots.
5. **Browser responsibility keep/remove map:** one row for each of the ten
   responsibilities #137 listed, with current `file:line` ranges and what
   becomes framework-managed, what stays as application code, and what moves
   to Python.
6. **Comparison** with the current page and the Jinja hybrid, on measured
   figures, plus a short honest account of the development experience.
7. **Costs:** Node in development and CI, the dependency tree, the
   `PLAN.md`/`AGENTS.md` dependency lines that would need amending, what
   happens to the 8,653 lines of Node-harness UI tests, and the exact
   production CSP the stack needs. If any pre-approved addition is used, the
   migration drafts must carry the `SERVER_CSP` change as an explicit,
   separately reviewable item with its tests.
8. **Limits of the evidence.**
9. **Migration ticket drafts** if GO or conditional: bounded, ordered, each
   with a scope rule, stop conditions and dependencies. **Drafts only.**

Decision gates. GO requires H1 to H7; H8 and H9 inform the comparison:

| Gate | Requirement | Evidence |
| --- | --- | --- |
| H1 | The slice shows what the server says | S1 |
| H2 | Untrusted values inert; ids and hashes opaque | S2 |
| H3 | Acknowledged state only; no replay; correct across finalise, reset and disconnect | S3, S4 |
| H4 | Contract section 7 met; focus survives a verdict | S5, S13 |
| H5 | Narrow layout usable; page never scrolls sideways | S6 |
| H6 | Works from an installed wheel without Node | S8 |
| H7 | Auth, Host, Origin and `no-store` unchanged; the CSP unchanged or within the approved envelope | S7, S9 |
| H8 | No rule exists in both Python and the browser; handcrafted browser code for the slice is clearly smaller | S12 |
| H9 | A workable development loop | S10, S11 |

A pre-approved addition does not make the result conditional, but the record
must state the exact policy the recommended stack needs, which component
needs each addition, and what the unchanged policy would have required
instead. If H7 can be met only by going **beyond** the approved envelope
(anything in `script-src`, `connect-src`, `default-src`, `object-src`,
`base-uri`, `frame-ancestors` or `form-action`, or any remote origin), the
result is at most **conditional**: name the exact directive, the alternatives
tried and the trade-off. Never describe such an option as compatible.

### Evidence and worklog

#### [NEW] `docs/evidence/issue-206/README.md` and screenshots

Verbatim transcripts for S1 to S13, each fence reproducible from the
repository root after `npm ci` and a build. Fake data only. Screenshots:
light and dark, desktop and 390 px.

#### [NEW] `worklog/YYYY-MM-DD-issue-206-implementation.md`

What was done, the recommendation, the dispatch record, and surprises.

## Mechanical inclusion test

A hunk is **in scope** if and only if both hold:

- its path is under `spikes/issue-206/`, or under `docs/evidence/issue-206/`,
  or is exactly `docs/frontend-framework-decision.md`, or is a new
  `worklog/*-issue-206-*.md` entry file; and
- it is needed to answer one of the issue's six questions or to build or
  verify the slice.

The first clause is checked by command, which must print nothing:

```bash
git diff --name-only origin/main...HEAD | grep -vE '^(spikes/issue-206/|docs/evidence/issue-206/|docs/frontend-framework-decision\.md$|worklog/[0-9-]+-issue-206-[a-z0-9-]+\.md$|handoffs/issue-206-implementation-plan\.md$)'
```

No `node_modules` and no build output may be tracked:

```bash
git ls-files spikes/issue-206 | grep -E '(^|/)(node_modules|dist|build)/'
```

Worked examples:

- **IN SCOPE:** a Svelte component for a duplicate group under
  `spikes/issue-206/frontend/src/`.
- **IN SCOPE:** `package.json` and `package-lock.json` under
  `spikes/issue-206/frontend/`.
- **IN SCOPE:** a 60-line probe page per shortlisted library for S7.
- **OUT OF SCOPE:** any edit to `pyproject.toml`, the root `.gitignore`,
  `.github/`, `src/`, `tests/` or `scripts/`. The wheel proof works on a
  temporary copy.
- **OUT OF SCOPE:** building the slice in more than one component library.
- **OUT OF SCOPE:** the Proposals surface, uploads, metrics or session
  actions beyond what S4 needs to trigger a finalise and a reset.
- **OUT OF SCOPE:** importing from `spikes/issue-137/`, or editing it.
- **OUT OF SCOPE:** creating, editing or commenting on any GitHub issue.

### Stop conditions

Stop implementation and return to orchestrator if:

- the proof cannot be built without editing a file outside the allowed paths;
- a gate can be met only by changing the snapshot or envelope schema, the
  session lifecycle, the auth/Origin/Host contract, revision or verdict
  validation, persistence, duplicate rules or finalisation semantics;
- plain Svelte 5 output itself, with no component library, cannot run within
  the approved envelope;
- the proof would need a policy on any **production** route to change;
- the toolchain cannot be installed or run here (registry unreachable, an
  install script that needs elevated access, Chromium unavailable);
- a needed package has a licence other than MIT, Apache-2.0, BSD or ISC;
- real vault data would be needed;
- the slice needs a field the envelope does not carry.

A failed gate, or every shortlisted library needing more than the approved
envelope, is **not** a stop. It is a finding and may be the NO-GO or the condition.

Escalation route: `implementer → orchestrator → planner`.

## Implementer model justification

**Judgement rung.** The plan fixes the questions, experiments, gates and
boundaries. It delegates the architecture, the library choice and the visual
design, which are meaningful choices between alternatives. It is not
High-risk: no production code, persistence or lifecycle changes.
`claude-opus-5-5` is a Judgement primary, its roster row is not stale, and
the active runtime can instantiate it.

## Likely findings

1. **A CSP result claimed from a happy path, or wider than needed.** Zero
   violations recorded for a page that never opened an overlay, ran a
   transition, or rendered the component that injects a style; or all three
   pre-approved additions switched on without showing which component needs
   each. Check S7 ran the unchanged policy first, exercised every component
   the slice uses, and that no remote URL is in the build.
2. **The projection quietly reimplemented in TypeScript.** Eligibility,
   survivor or disposition logic re-derived in the browser while H8 is
   passed. Read the slice's TypeScript against the plan's source rules.
3. **Finalise handled only on a fresh load.** S4 passes because the page was
   reloaded, not because the open page reconciled. Check the open-page case.
4. **A development loop that works only with a weakened server.** A dev proxy
   that rewrites `Origin`, or a relaxed check, presented as the normal loop
   without saying so. S10 must state exactly what it does.
5. **Scope and hygiene.** `node_modules` or build output tracked; a root
   `.gitignore` or `pyproject.toml` edit; two libraries fully built; issues
   created instead of drafted.

# Reusable implementer execution prompt

Implement issue #206 in `tonym999/vault-cleaner` using the handoff at the approved plan SHA `<plan_sha>` (the orchestrator fills this in at dispatch):

```text
git show <plan_sha>:handoffs/issue-206-implementation-plan.md
```

Read the entire handoff at that SHA, issue #206, tracker #138, `AGENTS.md`, `PLAN.md`, `docs/review-ui-design-contract.md`, `docs/review-rendering-architecture.md`, `docs/evidence/issue-137/README.md`, `spikes/issue-137/README.md`, `docs/browser-verification.md`, the recent worklog (defined in `AGENTS.md`, *Worklog*), and current relevant code before editing.

Rules:
- work on the existing `feat/issue-206-svelte-frontend-spike`, which already holds the plan commit; do not create another branch, rebase, or force-push, and record the branch head you start from as your attempt's starting SHA (the orchestrator keeps the ticket's review base, which a later attempt does not move);
- never edit `handoffs/issue-206-implementation-plan.md`;
- apply the plan's mechanical inclusion test to every hunk; this spike changes no file under `src/`, `tests/`, `scripts/`, `.github/`, `spikes/issue-137/`, or `pyproject.toml`, `.gitignore`, `PLAN.md`, `AGENTS.md`;
- pin exact npm versions, commit the lockfile, install with `npm ci`, and track no `node_modules` or build output;
- use fake fixtures only; never read `data/`;
- create, edit or comment on no GitHub issue; draft migration tickets in the decision record;
- add a dated worklog entry file under `worklog/` (format in `AGENTS.md`, *Worklog*);
- run all verification commands:
  - `.venv/bin/ruff check src tests scripts`
  - `.venv/bin/ruff check spikes/issue-206`
  - `.venv/bin/pytest -q` (baseline: `1342 passed`; the count must not change)
  - `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`
  - `.venv/bin/python scripts/check_wheel_install.py`
  - the frontend's type check, unit tests and build, from a clean `npm ci`
  - every proof command listed in `spikes/issue-206/README.md`
  - `python3 scripts/check_worklog.py --base origin/main`
  - `git diff --check origin/main...HEAD`
  - both inclusion-test commands above, which must print nothing;
- commit and push the implementation branch with `Refs #206`; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. Choosing the architecture, the component library and the visual design from the evidence is the work of this ticket, not an escalation. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, provide the implementer → orchestrator handoff: starting and head SHAs; the recommendation in one sentence; the result of each gate H1 to H9 with its evidence fence; the CSP result stated exactly (the full policy string the stack needs, and which component needs each addition); every verification command with its output tail; the try-it command; anything not measured; notable implementation choices; and the migration ticket drafts' titles in order.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
No production code changes, so the immediate blast radius is nil. The output
is a recommendation to adopt a frontend framework, a build toolchain and a
dependency tree, and it rests on security claims (CSP compatibility,
inertness of untrusted values, the unchanged auth envelope) and on
stale-state claims that #137's review showed are easy to get subtly wrong. A
fresh reviewer who reruns the proofs and probes the CSP and finalise cases is
the right check.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] Both inclusion-test commands print nothing; `git diff --stat origin/main...HEAD -- src tests scripts spikes/issue-137 pyproject.toml .gitignore .github PLAN.md AGENTS.md` is empty.
- [ ] `.venv/bin/pytest -q` still reports `1342 passed`; the browser suite and `scripts/check_wheel_install.py` pass unchanged.
- [ ] From a clean `npm ci`, the type check, unit tests and build pass, and every proof command was rerun by the reviewer and matches its evidence fence; no browser proof skipped.
- [ ] The recommendation is stated first and is GO, NO-GO or a bounded conditional; each gate H1 to H9 has a result and a linked fence.
- [ ] S1 covers the four fixtures and the recount-and-drop filter cases.
- [ ] S2 overlays every string field including ids and hashes, checks the verdict request body, and the source scan rejects `{@html}`, `innerHTML` and numeric conversion of ids.
- [ ] S3 shows no change before the acknowledgement and no replay; S4 covers the already-open page across a finalise.
- [ ] S5 shows the focused control is the same node after a verdict and states the report-change focus policy.
- [ ] S7 ran the unchanged policy first, exercised every component the slice uses, has a probe result for each shortlisted library, and states the exact policy needed. Every addition used is one of the three pre-approved ones and is attributed to a component; nothing beyond the approved envelope is described as compatible; `script-src` and `connect-src` are `'self'` only.
- [ ] Production routes served by the spike app carry the unchanged policy.
- [ ] S8 ran with Node absent from the fresh environment and checked the package origin.
- [ ] S10 says exactly how the development loop satisfies the `Origin` rule.
- [ ] The decision record classifies the design contract, lists every presentation choice changed, and includes light and dark, desktop and narrow screenshots.
- [ ] The keep/remove map's `file:line` ranges were opened at the head.
- [ ] Library claims cite official documentation with the date read.
- [ ] Migration drafts are bounded and ordered; no issue was created.
- [ ] No real data, real ids or `data/` paths appear in the evidence or screenshots.
- [ ] Likely findings 1 to 5 were each checked.

# Dispatch comment draft

Planned #206 in [handoffs/issue-206-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/<plan_sha>/handoffs/issue-206-implementation-plan.md), approved at plan SHA `<plan_sha>`.

- **Implementer model & effort:** `claude-opus-5-5` at `high` (Judgement rung)
- **Implementation branch:** `feat/issue-206-svelte-frontend-spike`
- **Likely findings:** a CSP result claimed from a happy path or wider than needed; the projection reimplemented in TypeScript; finalise handled only on a fresh load; a development loop that needs a weakened server; tracked `node_modules` or build output, or other scope leakage.
