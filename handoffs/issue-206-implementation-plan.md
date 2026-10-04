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

**Amendment 2 (2026-10-04).** From the owner's review of
`b8a86806ae5a3e86f615bfcdc57f5d481239b87b`, which was not approved. Four
changes: the binding-constraints table now matches the approved CSP envelope;
S1 defines the information a group and a member must show and tests its
values; S8 requires Chromium to render a group and complete an acknowledged
verdict against the installed wheel; and **H8 (lower maintenance effort) and
H9 (a usable development loop) are now required for GO**, with a new
experiment S14.

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
  | Section 10 constraints: untrusted values inert, opaque ids, no inline script, no request-supplied path. Inline styles: none hand-written in the slice's source; component-generated ones only within the approved CSP envelope and attributed in S7 | Section 12: open questions 1 to 5 |
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
that builds and serves the proof for the owner, the one command that starts
the development loop, a short **"make a change yourself" walkthrough** taken
from one S14 exercise, and one command per experiment.

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

### Required information

Layout, styling, wording and grouping of this information are free. What must
be shown is not. The list is what the production page shows today
(`review_ui.js:1201-1288`, `:1319-1422`, `:1489-1557`), read from the
envelope.

**Per group:**

- name (or a clear "unnamed" fallback), item archetype, type or slot,
  guardian class, tier, hash, and the number of pieces;
- which kind it is: an exact duplicate group, or a same-stats group that is
  review-only and selects no survivor;
- the six base stats with their values, and for a tier-5 piece which stat is
  primary, secondary and tertiary;
- for an exact group, the shared Tuning Mod Slot;
- spirit signature, Seasonal Mod and Holofoil, where the group has them.

**Per member:**

- its id (complete, never truncated) and location;
- its disposition: for an exact group the server's `disposition` (survivor,
  proposed junk, proposed review, protected and so on); for a same-stat group
  whether it has an existing proposal, and that proposal's action;
- protection level and reason, in loadout, equipped, locked, masterwork tier
  and power;
- for a same-stat member: Tuning Mod Slot, Seasonal Mod, Holofoil, and Tuning
  Stat where it tells members with the same slot apart;
- for a member with a proposal: the proposed action and its reason, the
  current verdict, and whether an active persisted veto still suppresses it;
- verdict controls if and only if the server makes it a proposal member.

**The rule that keeps the comparison a comparison:** every value that differs
between a group's members must be visible for each member at once, without
hover, expansion or per-member navigation. A value identical across all
members may be shown once for the group, but must be shown. An unknown or
absent value must look different from a real one.

Test hooks such as `data-testid` attributes are allowed so the proof can find
a value without depending on layout.

### Experiments

Each produces a transcript in the evidence file.

| # | Issue question | Experiment | Pass means |
| --- | --- | --- | --- |
| S1 | 4 | **Information parity.** For the four fixtures, with and without verdicts, compute the expected values for every item under *Required information* from the server's envelope in the proof script, independently of the frontend, and assert each one is shown for the right group or member: group order, the group facts, the stats, every member id, disposition, protection, loadout, equipped, locked, masterwork tier, power, the same-stat tuning values, proposal action and reason, verdict state, which members have verdict controls, and the scope counts. Assert the differing-values rule: for each field whose values differ within a group, every member's value is visible at 1440 px and at 390 px with no interaction. Compare scope text and Class options with the production page for the filter sequences in #137's E10, including the recount-and-drop cases. Include one negative control: remove one required value from the rendered page and show the proof fails. | Every required value present and correct; the negative control fails; any difference from production's information listed and justified |
| S2 | 4 | **Hostile content.** Overlay hostile and long values on every string field of the envelope, including ids `18446744073709551615`, `007` and one with `"`, `<`, `'` and a space. Assert no dialog, no injected element, no CSP violation, exact text round-trip, and byte-identical ids in the DOM and in the verdict request body. Run the source-rule scan. | All inert; ids unchanged |
| S3 | 3, 4 | **Acknowledged state only.** Approve, Veto and Unset through the unmodified `POST /api/verdicts`, with the response held: the presentation must not change until it arrives. Force `stale_verdicts` and `stale_report`; the action must not be replayed. | No optimistic state; no replay |
| S4 | 3, 4 | **Finalise, reset, disconnect.** Finalise with a veto in place: the open page must reach the frozen state and the persisted-veto wording with the revision pair unchanged, and match production loaded fresh in meaning. Reset. Stop the server and filter. | Correct in all three |
| S5 | 3 | **Focus and live regions.** After an acknowledgement the focused control is the same node. State and measure the focus policy on a report change. The status, reconciliation and scope regions are the same nodes throughout, and each acknowledgement is one announcement. | Recorded; contract section 7 met |
| S6 | 2 | **Layouts.** At 1440, 1024 and 390 px, light and dark: the page does not scroll sideways; a group's members can be compared without member-by-member horizontal navigation; ids wrap; every control is reachable by keyboard in a sensible order; no hidden duplicate control is in the tab order. Capture the screenshots. | Recorded with screenshots |
| S7 | 2, 5 | **CSP.** First run the whole slice under the **unchanged** policy and record every violation, including every component used and any transition. Then, only if needed, run it under the approved envelope with the fewest additions that give zero violations, and name the component that needs each one. For each shortlisted library, build a minimal probe page (button, toggle, select or equivalent, one overlay if the library has one) and record its violations under the unchanged policy and which additions clear them. Check the build for `data:` URIs, fonts, inline styles and any remote URL. | Zero violations under the unchanged policy or the approved envelope, with each addition used attributed; or the exact further directive a candidate needs |
| S8 | 5 | **Installed wheel, in a browser.** Modelled on #137's `proof_e7_wheel.py`: overlay the built assets and the `package-data` change on a temporary copy of the tracked source, build a wheel, and install it into a fresh environment. Start the server from that environment with **Node absent from its `PATH`** (assert `shutil.which("node")` is `None` there) and confirm the package origin is the installed wheel. Then drive it with Chromium: bootstrap, upload a fake fixture, wait for a duplicate group to render from the installed JavaScript and CSS, complete one acknowledged verdict, and confirm the server's verdict revision moved. Record every network response for the page's assets (status and content type) and any console error or CSP violation. Playwright's own bundled driver is test tooling and does not count as Node on the product's path; say so in the transcript. | A group renders and a verdict is acknowledged from the wheel with Node absent, every asset 200 with the right type, no console error; or a concrete blocker |
| S9 | 5 | **Request envelope.** Every spike route has production's security headers and refuses unauthenticated, wrong-Host and wrong-Origin requests. Production routes served by the spike app keep the unchanged policy byte for byte. | No header differs; the policy on a spike route differs from production's only by pre-approved additions that S7 shows are needed |
| S10 | 1, 6 | **Development loop.** Measure a cold build, a rebuild after a one-line edit, the time from saving a component edit to seeing it against real server data, and the output size (raw and gzip). Establish an edit-and-see loop against the Flask server given the `Origin` rule, started by one command, and say exactly how it works. If it relies on anything that relaxes a server check (a proxy rewriting `Origin`, a development-only flag), show that it exists only in the development path and is absent from the built wheel. Record `svelte-check` and the unit-test run. | Recorded, with the mechanism stated exactly |
| S11 | 6 | **Type drift.** Rename one view-model or envelope field on the Python side and show where the mismatch surfaces: type check, build, test, or only at runtime. | Recorded |
| S12 | 3, 6 | **Code comparison.** Line counts for the slice by category: components and markup, application logic (requests, revisions, reconciliation, lifecycle), filtering, types, Python, tests. Set them beside production's 908 and the hybrid's 155 + 474 + 187. Count the installed npm packages and record `npm audit`. | Recorded |
| S13 | 2 | **Automated accessibility check** (for example axe-core) on the slice in both colour schemes. | Violations listed; none left unexplained |
| S14 | 3, 6 | **Change exercises.** Make three small changes to the finished slice, each saved as a patch file under `spikes/issue-206/` that applies cleanly to the committed slice, and not left applied: (1) show one more per-member comparison value; (2) add one more filter facet; (3) change the wording of one verdict state. For each, record the files and places touched in the Svelte slice, and identify by `file:line` every place the same change would touch in the current page and in #137's Jinja hybrid. Record whether the type check or a test caught a deliberately incomplete version of the change. | Recorded for all three, for all three codebases |

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
   figures: the S12 counts, the three S14 exercises side by side, and the
   S10 loop. Then a plain verdict on H8 and on H9, and a short honest account
   of the development experience, including what was awkward.
7. **Costs:** Node in development and CI, the dependency tree, the
   `PLAN.md`/`AGENTS.md` dependency lines that would need amending, what
   happens to the 8,653 lines of Node-harness UI tests, and the exact
   production CSP the stack needs. If any pre-approved addition is used, the
   migration drafts must carry the `SERVER_CSP` change as an explicit,
   separately reviewable item with its tests.
8. **Limits of the evidence.**
9. **Migration ticket drafts** if GO or conditional: bounded, ordered, each
   with a scope rule, stop conditions and dependencies. **Drafts only.**

Decision gates. **GO requires all nine.** H1 to H7 are about correctness and
safety. H8 and H9 are the reason for doing this at all: a slice that is
correct but no easier to maintain or to work on is not a GO.

| Gate | Requirement | Evidence |
| --- | --- | --- |
| H1 | The slice shows what the server says | S1 |
| H2 | Untrusted values inert; ids and hashes opaque | S2 |
| H3 | Acknowledged state only; no replay; correct across finalise, reset and disconnect | S3, S4 |
| H4 | Contract section 7 met; focus survives a verdict | S5, S13 |
| H5 | Narrow layout usable; page never scrolls sideways | S6 |
| H6 | Works from an installed wheel without Node | S8 |
| H7 | Auth, Host, Origin and `no-store` unchanged; the CSP unchanged or within the approved envelope | S7, S9 |
| H8 | **Maintenance effort is clearly lower.** All of: (a) no rule exists in both Python and the browser; (b) the slice has no hand-written DOM construction, repaint or node bookkeeping outside declarative component markup, apart from listed and justified exceptions such as a `focus()` call; (c) in each S14 exercise the change touches fewer places than in the current page, or the record says why not; (d) the application logic that remains (requests, revisions, reconciliation, lifecycle) is typed and unit-tested without a browser | S12, S14 |
| H9 | **A usable development loop.** One command starts it; a component edit is visible against real server data within a few seconds; a Python-to-browser type mismatch is caught before runtime; and nothing in the loop weakens a check in the built product | S10, S11 |

H8 and H9 have no numeric threshold on purpose: line counts and timings are
evidence, not targets. The implementer must give a plain verdict on each
with its reasons, and say so if the answer is "not clearly". If H1 to H7 pass
but H8 or H9 does not clearly pass, the result is at most **conditional**,
and the record names what would have to be true for a GO. The development
experience is finally the owner's to judge: the README's try-it command and
a short "make a change yourself" walkthrough, built from one S14 exercise,
exist for that.

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
5. **H8 or H9 passed on a number, or on enthusiasm.** A smaller line count
   offered as proof of lower maintenance while imperative DOM code survives
   inside `$effect` blocks or actions; S14 exercises chosen to flatter the
   slice; a development loop that was described but not timed, or that only
   works with a relaxed server check.
6. **Scope and hygiene.** `node_modules` or build output tracked; a root
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

When complete, provide the implementer → orchestrator handoff: starting and head SHAs; the recommendation in one sentence; the result of each gate H1 to H9 with its evidence fence, with a plain verdict and reasons for H8 and H9; the CSP result stated exactly (the full policy string the stack needs, and which component needs each addition); every verification command with its output tail; the try-it command; anything not measured; notable implementation choices; and the migration ticket drafts' titles in order.

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
- [ ] S1 computes its expected values from the envelope independently of the frontend, covers every item under *Required information* for the four fixtures, asserts the differing-values rule at 1440 and 390 px, includes the recount-and-drop filter cases, and its negative control fails.
- [ ] S2 overlays every string field including ids and hashes, checks the verdict request body, and the source scan rejects `{@html}`, `innerHTML` and numeric conversion of ids.
- [ ] S3 shows no change before the acknowledgement and no replay; S4 covers the already-open page across a finalise.
- [ ] S5 shows the focused control is the same node after a verdict and states the report-change focus policy.
- [ ] S7 ran the unchanged policy first, exercised every component the slice uses, has a probe result for each shortlisted library, and states the exact policy needed. Every addition used is one of the three pre-approved ones and is attributed to a component; nothing beyond the approved envelope is described as compatible; `script-src` and `connect-src` are `'self'` only.
- [ ] Production routes served by the spike app carry the unchanged policy.
- [ ] S8 drove the installed wheel with Chromium: a group rendered, a verdict was acknowledged, every asset returned 200 with the right content type, no console error, Node absent from the server environment's `PATH`, package origin checked.
- [ ] S10 says exactly how the development loop satisfies the `Origin` rule, times it, and shows any relaxation is absent from the built wheel.
- [ ] S14 has all three exercises as real diffs, with the corresponding `file:line` places in the current page and the Jinja hybrid opened at the head; the exercises were not chosen to avoid the slice's weak spots.
- [ ] H8 and H9 each have a plain verdict with reasons; a GO has all nine gates passing, and an unclear H8 or H9 is reported as conditional.
- [ ] The slice has no hand-written DOM construction or repaint outside component markup beyond the listed exceptions (check `$effect` blocks, actions and any `document.` or `querySelector` use).
- [ ] The decision record classifies the design contract, lists every presentation choice changed, and includes light and dark, desktop and narrow screenshots.
- [ ] The keep/remove map's `file:line` ranges were opened at the head.
- [ ] Library claims cite official documentation with the date read.
- [ ] Migration drafts are bounded and ordered; no issue was created.
- [ ] No real data, real ids or `data/` paths appear in the evidence or screenshots.
- [ ] Likely findings 1 to 6 were each checked.

# Dispatch comment draft

Planned #206 in [handoffs/issue-206-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/<plan_sha>/handoffs/issue-206-implementation-plan.md), approved at plan SHA `<plan_sha>`.

- **Implementer model & effort:** `claude-opus-5-5` at `high` (Judgement rung)
- **Implementation branch:** `feat/issue-206-svelte-frontend-spike`
- **Likely findings:** a CSP result claimed from a happy path or wider than needed; the projection reimplemented in TypeScript; finalise handled only on a fresh load; a development loop that needs a weakened server; H8 or H9 passed on a line count alone; tracked `node_modules` or build output, or other scope leakage.
