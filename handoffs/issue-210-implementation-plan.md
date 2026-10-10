# Issue #210 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#210 — M10: redesign the Svelte Armor duplicates slice, dark-first, against the design contract`

**Milestone:** none assigned (tracked under #138)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (the session does not report its native effort, so none is recorded)

**Implementation model selected:** `claude-opus-5-5` at `high` (Judgement rung; justified below)

**Plan baseline:** `main` at `d139a05306828c0a4d7e9ded211408b346dd7768` (2026-10-10)

**Allocated branch:** `feat/issue-210-armor-duplicates-redesign` (this plan is its first commit)

The implementer must **not** open a pull request or edit this file. The branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Rebuild the presentation of the Svelte Armor duplicates slice so that section,
group and piece are plainly separate in dark mode, pieces of a group compare
side by side, and the page stays readable across the full 74-group report at
1440 px and 390 px. The owner rejected #206's daisyUI design and chose
**direction D** from four mockups on 2026-10-10.

The ticket also measures #206's claim that the UI is cheap to change in this
stack: the change is reported as files and lines, split between
components/stylesheet and typed logic.

Nothing ships. No production code, envelope, route or CSP changes.

## Owner decisions this plan carries (2026-10-10)

1. **Design:** direction D, recorded in
   [docs/evidence/issue-210/README.md](../docs/evidence/issue-210/README.md)
   with captures under
   [docs/evidence/issue-210/mockups/](../docs/evidence/issue-210/mockups/).
2. **Component library:** try **shadcn-svelte** (the Svelte port of shadcn/ui;
   shadcn/ui itself is React) and show the owner what it looks like. daisyUI
   is removed.
3. **Starting point (planner's advice, accepted):** start from the #206 slice
   on `main` and carry #209's value-retention change forward as its own
   commit.
4. **Timing gate (planner's advice, accepted):** #209's seven-comparison gate
   is a follow-up, not part of this ticket. This ticket proves only that the
   design does not repeat #209's dominant cost.
5. **#152:** this ticket supersedes it. Closing or commenting on #152 is an
   issue mutation that needs its own authorization.

## Context & Measurement

### The rejected design

`docs/evidence/issue-206/both-kinds-desktop-dark.png` shows the #206 slice.
Page, group card and piece box share one fill; the section headings are plain
text; every value sits under its own label, so two pieces compare by reading
down. The markup is
[GroupCard.svelte](../spikes/issue-206/frontend/src/components/GroupCard.svelte)
(78 lines) and
[MemberRow.svelte](../spikes/issue-206/frontend/src/components/MemberRow.svelte)
(58 lines).

### The slice's size at the baseline

`wc -l` over `spikes/issue-206/frontend/src`:

| Part | Files | Lines |
| --- | --- | --- |
| `App.svelte`, `app.css`, `components/*.svelte` | 9 | 500 |
| `lib/*.ts` without tests | 5 | 870 |
| `lib/*.test.ts` | 3 | 378 |

### The fixture

From the envelope the unmodified server returns for
`tests/fixtures/real/2026-09-01T-current/armor.csv`
(`docs/evidence/issue-210/mockups/dump_envelope.py`):

- 74 groups (9 exact, 65 same-stat), 158 pieces, 435 verdict buttons.
- 66 pairs, 6 triples, 2 groups of four. Every exact group is a pair.
- Every group is tier 5 with the 30/25/20 spike. Stats never differ inside a
  group.
- Same-stat groups differ on 2 to 9 comparison fields. Tuning Mod Slot and
  Tuning Stat differ in all 65, and the two fields agree, ignoring case, for
  all 140 same-stat pieces.

### What the #206 proofs read

The proofs read the page only through `data-*` hooks, so they do not depend
on layout: `READ_SLICE_JS` at
[harness.py:312](../spikes/issue-206/harness.py#L312). Four facts bind the
new markup:

- Groups are `article[data-group]` with `data-kind`; pieces are
  `[data-member]`; every printed value is a `[data-field]`, `[data-shared]` or
  `[data-stat]` node whose `textContent` is the exact value and which is
  visible without sideways scroll.
- Facets are read as `select[data-facet]`
  ([harness.py:342](../spikes/issue-206/harness.py#L342)). The class filter
  must stay a native `<select>`.
- The kind text is asserted verbatim: `Exact duplicates` and
  `Same stats · review only`
  ([expected.py:158](../spikes/issue-206/expected.py#L158)). The scope text
  is `N groups · M pieces`
  ([expected.py:174](../spikes/issue-206/expected.py#L174)).
- Every same-stat piece must show `tuning_stat` as its own visible value
  ([expected.py:58](../spikes/issue-206/expected.py#L58)). Direction D merges
  it into the tuned-stat cell; see *The one proof adaptation*.

### What #209 measured

Recorded on branch `feat/issue-209-svelte-perf-gate` (not merged) and
summarised in the issue body. Two results bind this plan:

- daisyUI's `.btn` transitions five properties over 0.2 s, and every request
  flips `aria-disabled` on all 435 buttons
  ([VerdictControls.svelte:23-27](../spikes/issue-206/frontend/src/components/VerdictControls.svelte#L23-L27)).
  Verdict style recalculation was 138.7 ms against production's 3.1 ms, and
  59.5 ms fell to 5.5 ms with transitions removed.
- The value-retention change in commit
  `a8da54329cc6d198e7702b567267263d2669d9b4` cut acknowledgement-to-DOM from
  27.1 ms to 17.4 ms. It touches three files under
  `spikes/issue-209/frontend/src/lib/`: `view.ts` (+31/-2),
  `session.svelte.ts` (+4/-3) and `session.test.ts` (+47)
  (`git diff --stat 088218b a8da543 -- spikes/issue-209/frontend/src`).

### shadcn-svelte, as #206 measured it

`docs/frontend-framework-decision.md` section 3 probed shadcn-svelte 1.7.0 on
Bits UI 2.19.5: MIT, no CSP violation (styles go through the CSSOM), 203 kB
of page script against daisyUI's 1 kB, and 31 generated files (717 lines) for
button, toggle, select and dialog. Its CLI is interactive and its default
preset adds an OFL-1.1 web font, which the CSP's missing `font-src` would
block. The probe is under
[spikes/issue-206/probes/](../spikes/issue-206/probes/).

## Dependencies and assumptions

- **#206 is merged** (PR #208, `d139a05`). `spikes/issue-206/` is frozen: its
  transcripts are reruns of its code. This ticket edits nothing under it.
- **#209 is not merged and this ticket does not depend on it.** The
  value-retention change is taken by commit SHA from the pushed branch. If
  `a8da543` is not reachable from `origin`, stop.
- **The issue says the plan settles whether the timing gate is in scope.** It
  is not (owner decision 4). #209's proof scripts live only on its branch.
- **The issue names the contract's prototype hierarchy as the target.**
  Direction D follows its three levels and its matrix orientation (axes as
  rows, pieces as columns, contract 5.10). It departs from the contract in
  three places the owner accepted when choosing D:
  - the 30/25/20 spike is a six-cell strip in a fixed stat order, not three
    cards ordered by role (5.8). The role word stays as text;
  - the review-only statement sits once in the sticky section heading, with a
    text pill on each card, not a banner on every card (5.7, 5.9);
  - labels are sentence case, not uppercase monospace eyebrows (4.2).
- **`PLAN.md` has no M10 section** (contract open question 6). Not in scope.
- **Stale roster rows:** `python3 scripts/check_model_roster.py` reports the
  two Gemini rows as stale. Neither is relied on.

## Proposed Plan & Scope

### Step 0 — copy, then carry forward

#### [NEW] `spikes/issue-210/`

1. **Copy commit.** Copy `spikes/issue-206/frontend/` to
   `spikes/issue-210/frontend/`, excluding `node_modules` and `dist`, with no
   other change. Add `spikes/issue-210/.gitignore` matching #206's. This
   commit must be a verbatim copy:
   `diff -r -x node_modules -x dist spikes/issue-206/frontend spikes/issue-210/frontend`
   prints nothing.
2. **Carry-forward commit.** Apply #209's value-retention change to
   `spikes/issue-210/frontend/src/lib/` and nothing else:
   `git diff 088218b a8da543 -- spikes/issue-209/frontend/src/lib` rewritten
   to the new path. `npm run check` and `npm test` pass (35 tests).

Every later commit is the redesign. The files-and-lines report measures from
the carry-forward commit, so the carried logic is not counted as redesign
cost.

### Step 1 — proof runner

#### [NEW] `spikes/issue-210/run_proof.py`

Runs a fixed #206 proof, unedited, against the #210 source and build by
setting the harness's frontend globals
([harness.py:36](../spikes/issue-206/harness.py#L36)) before importing the
proof. It accepts one fixed proof name from a list and forwards no path.
#209's runner on its branch is a worked example; do not import it.

Proofs in scope: S1 parity, S2 hostile values, S3 acknowledged verdicts, S4
lifecycle, S5 focus, S6 layout, S7 CSP, S13 axe and contrast, S15 real scale,
and `check_source.py`. S15's timing comparison is recorded, not gated.

#### The one proof adaptation

Direction D prints one "Tuned stat" value per piece. The runner may wrap the
oracle for exactly this, in `spikes/issue-210/`, without editing #206:

- When a piece's Tuning Stat equals its Tuning Mod Slot ignoring case, the
  page need not carry a separate `tuning_stat` node. The merged cell carries
  `data-field="tuning_mod_slot"` and `data-merged="tuning_stat"`.
- When they differ, the page must show both, each as its own visible
  `data-field`, and the oracle asserts both as before.

Add a unit test for the differing case on a synthetic envelope; the fixture
has none. Any other oracle or proof change is a stop condition.

### Step 2 — the redesign

#### [MODIFY] `spikes/issue-210/frontend/src/App.svelte`, `src/app.css`, `src/components/*.svelte`
#### [NEW] components and generated shadcn-svelte files under `spikes/issue-210/frontend/src/`
#### [MODIFY] `spikes/issue-210/frontend/package.json`, `package-lock.json`

**The target is direction D.** The captures in
`docs/evidence/issue-210/mockups/` and `mock.css` are the reference for
structure, hierarchy and spacing. They are a target, not a pixel
specification: the shadcn-svelte trial will change the look of controls.

What D must keep:

- **Three surface steps.** Page, section, group and piece each have their own
  background, with a visible border on section and group. In dark mode a
  group must be distinguishable from the page without relying on a shadow.
- **Section.** A container with a sticky heading that carries the section
  name, its rule sentence and the group count. Same-stat is marked by more
  than colour (the mockup uses a different marker shape and the words).
- **Group header.** Name; archetype, type, class, tier and hash on one meta
  line; the kind pill and piece count; and a six-cell stat strip in the fixed
  order Health, Melee, Grenade, Super, Class, Weapons. Non-zero cells are
  filled and carry the role word; zero cells are muted but present.
- **Matrix.** A label column, then one column per piece. Rows: the piece
  header (piece number, status, id, location), then only the fields on which
  the pieces differ, then Proposal, then Verdict. For a same-stat group the
  Tuned stat row is always present and comes first.
- **Tuned stat row.** A six-box strip in the same stat order with the tuned
  stat filled, plus the stat name as text. The strip is decoration
  (`aria-hidden`); the name is the value.
- **Kept piece.** In an exact group the preferred survivor's column is
  tinted and its header carries the text `Preferred survivor`. Approved and
  kept must differ by more than hue (contract 4.3).
- **Shared line.** One line beneath the matrix listing every field that is
  the same on all pieces, led by `Same on both` or `Same on all N`.
- **390 px.** No sideways page scroll. Pairs and triples stay as columns
  with each cell carrying its own small label; a group of four becomes one
  block per piece. Verdict buttons are at least 40 px tall.
- **Light scheme.** Follows `prefers-color-scheme`. It must be usable and
  pass the contrast proof; it is not the design focus.

Copy that the proofs fix, verbatim: the kind pill reads `Exact duplicates`
or `Same stats · review only`; the scope reads `N groups · M pieces`; every
string exported from `lib/view.ts` is unchanged. Other new copy is the
implementer's, in plain sentence case.

**Latitude.** The issue's *Latitude and prior art* section applies in full
and this plan does not narrow it. Component breakdown, class names, layout
mechanics and the treatment of any detail not listed above are the
implementer's. The implementer should use its design skills, review the
result with the 74-group fixture loaded, and improve on the mockup where it
is weak, in particular triples at 390 px. Anything tried and dropped is
reported. A change to the typed logic is allowed when it serves the design,
and is reported as logic.

#### The shadcn-svelte trial

The owner asked to see the design on shadcn-svelte.

- **Approved to add,** pinned exactly: `bits-ui`, `tailwind-variants`,
  `clsx`, `tailwind-merge`, and the `shadcn-svelte` CLI as a development
  dependency if it is used to generate files. Record each one's version,
  licence and installed size in the worklog.
- **Remove** `daisyui` from
  [package.json](../spikes/issue-206/frontend/package.json#L17) and the
  `@plugin "daisyui"` block from
  [app.css](../spikes/issue-206/frontend/src/app.css#L6), with the overrides
  that existed only for it.
- **Not approved without asking:** any icon package, `tw-animate-css`, a web
  font, `@internationalized/date`, or any other package. Ask the owner
  through the orchestrator, naming the package, what it adds, its licence and
  size.
- **Use shadcn-svelte where it fits the contract,** and a native element
  styled with the same tokens where it does not. Known constraints:
  - the class filter stays a native `<select>` (the proofs read
    `select[data-facet]`);
  - verdict controls are three `aria-pressed` toggle buttons, never a
    toggle group with radio roles (contract 5.11, 7);
  - verdict controls are switched off with `aria-disabled`, never
    `disabled`, because Chromium drops focus from a disabled button (#206
    S5);
  - shadcn's default button classes include a transition. Verdict controls
    must have none (see Step 3).
- **Tokens are the design's, not the preset's.** Map the shadcn theme
  variables to direction D's palette. Do not ship the preset's web font.
- **Report the trial honestly:** which shadcn-svelte components were used,
  which were replaced by native elements and why, generated files and lines
  added, and built script and stylesheet size against #206's build.

The owner decides from the captures whether the shadcn-svelte look stays. If
it is rejected, the fallback is the same design in plain CSS with no added
package; that is a new attempt on this branch, not part of this dispatch.

### Step 3 — the #209 constraint

- No CSS transition or animation on any verdict control. Add a proof,
  `spikes/issue-210/proof_no_transition.py`, that loads the real fixture and
  asserts every verdict button's computed `transition-duration` and
  `animation-duration` are `0s`, in both schemes.
- The busy treatment must cost about the same for one control as for all.
  How is open. Controls must still refuse input while a request is in
  flight, and the focused control keeps focus and node identity (S5).
- Record one diagnostic, not gated: style recalculation over a single
  verdict on the real fixture, read from Chromium's performance counters
  through CDP, five runs, median. #209 measured 138.7 ms on #206.
- No `content-visibility`, paging or virtualisation. If the design seems to
  need one, stop.

### Step 4 — captures and records

#### [NEW] `docs/evidence/issue-210/` captures and transcripts
#### [MODIFY] `docs/evidence/issue-210/README.md` (append only; sections 1 to 3 stay)
#### [NEW] `spikes/issue-210/README.md`
#### [NEW] `worklog/YYYY-MM-DD-issue-210-implementation.md`

- **Captures for the owner,** from the running slice with the real fixture:
  dark and light, 1440 px and 390 px, each showing the page top, the section
  boundary, a triple and a group of four. Add the two synthetic cases #206
  captured (both kinds, four members) in dark.
- **Transcripts:** every proof run, verbatim, per `AGENTS.md` *Conventions*.
- **The cheap-to-change report:** `git diff --stat` and line counts from the
  carry-forward commit to the head, split into components and stylesheet,
  generated shadcn-svelte files, typed logic, tests, and proof tooling.
- **Tried and dropped:** every approach attempted and abandoned, with the
  reason.
- **The spike README:** how to build, serve and run each proof.
- The prior-art survey is already recorded in section 1 of the evidence
  README; do not rewrite it. Add findings only if the implementer looks at
  further prior art, and say so.

### Out of scope

- `src/`, `tests/`, `spikes/issue-206/`, `PLAN.md`, `AGENTS.md`, the design
  contract, `docs/frontend-framework-decision.md`.
- The seven-comparison timing gate and any GO or NO-GO on the framework.
- Other surfaces (Proposals, uploads, metrics).
- Closing or commenting on #152 or #210.

## Mechanical inclusion test

A proposed change is **in scope** if and only if:

- it is under `spikes/issue-210/`, `docs/evidence/issue-210/` or `worklog/`,
  and
- it is the verbatim copy, the carry-forward, the proof runner with its one
  adaptation, the redesign, the no-transition proof, or a record this plan
  names, and
- it adds no package beyond the approved list.

Worked examples:

- **IN SCOPE:** replacing `GroupCard.svelte` and `MemberRow.svelte` with a
  matrix component and a stat-strip component.
- **IN SCOPE:** adding a `tunedStat` helper to `lib/view.ts` so the merged
  cell has one source, reported as a logic change with its test.
- **IN SCOPE:** dropping a shadcn-svelte component for a native element
  because it cannot take `aria-disabled`, and saying so.
- **OUT OF SCOPE:** editing `spikes/issue-206/expected.py` so S1 accepts the
  merged cell.
- **OUT OF SCOPE:** adding `@lucide/svelte` for icons without asking.
- **OUT OF SCOPE:** changing a string exported from `lib/view.ts` to match
  the mockup's wording.
- **OUT OF SCOPE:** adding `content-visibility: auto` to shorten the first
  render.

### Stop conditions

Stop implementation and return to orchestrator if:

- a #206 proof cannot pass without an oracle or proof change other than the
  one adaptation above;
- direction D cannot meet a behavioural or accessibility requirement of the
  design contract (sections 5.11, 7, 8) without changing its structure;
- shadcn-svelte needs a package outside the approved list, a CSP addition,
  or a web font to work at all;
- commit `a8da543` is unreachable, or the carry-forward does not apply
  cleanly to the #206 copy;
- the design appears to need deferred rendering, paging or virtualisation;
- any change outside `spikes/issue-210/`, `docs/evidence/issue-210/` and
  `worklog/` seems necessary.

Ordinary design and engineering choices inside direction D are not stop
conditions. Decide, continue and report.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Parity loss hidden by the merge.** The tuned-stat cell drops Tuning Stat
   in a case where it differs from the slot, or the adapted oracle is looser
   than specified (for example it skips `tuning_stat` for every piece).
2. **Transitions back in through shadcn classes.** A generated button or
   toggle keeps `transition-*` classes on verdict controls, or the
   no-transition proof checks only one scheme or only pressed buttons.
3. **Semantics traded for the library.** A toggle group with radio roles, a
   non-native select, `disabled` in place of `aria-disabled`, or a pressed
   state shown by colour alone.
4. **The cheap-to-change number is flattering.** Generated shadcn-svelte
   files or carried-forward logic are left out of the split, or the split is
   measured from the wrong commit.

## Implementer selection

`claude-opus-5-5` at `high`, Judgement rung, at the owner's direction. The
plan fixes the structure but delegates the visual design, the fit of a
component library to an accessibility contract, and the busy treatment. Those
are real design choices between alternatives, which is the Judgement rung's
definition. No persistence, concurrency or lifecycle code changes, so the
High-risk rung is not needed. The orchestrator checks whether its runtime can
instantiate the model, and otherwise prepares the prompt for a human operator.

# Reusable implementer execution prompt

Implement issue #210 in `tonym999/vault-cleaner` using the handoff at the approved plan SHA `<plan_sha>` (the orchestrator fills this in at dispatch):

```text
git show <plan_sha>:handoffs/issue-210-implementation-plan.md
```

Read the entire handoff at that SHA, issue #210, `AGENTS.md`, `PLAN.md`, the recent worklog (defined in `AGENTS.md`, *Worklog*), `docs/review-ui-design-contract.md`, `docs/evidence/issue-210/README.md` with its captures and `mock.css`, and the current `spikes/issue-206/` code before editing. Load your frontend design skill before designing.

Rules:
- work on the existing `feat/issue-210-armor-duplicates-redesign`, which already holds the plan commit; do not create another branch, rebase, or force-push, and record the branch head you start from as your attempt's starting SHA (the orchestrator keeps the ticket's review base, which a later attempt does not move);
- never edit `handoffs/issue-210-implementation-plan.md`;
- never edit anything under `spikes/issue-206/`, `src/` or `tests/`;
- make the verbatim copy and the carry-forward as two separate commits before any redesign;
- apply the plan's mechanical inclusion test to every hunk;
- add no package outside the plan's approved list; ask through the orchestrator for any other;
- use only synthetic fixtures and the tracked sanitised fixture; read nothing under `data/`;
- add a dated worklog entry file under `worklog/` (format in `AGENTS.md`, *Worklog*);
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, `git diff --check origin/main...HEAD`, and in `spikes/issue-210/frontend/`: `npm ci`, `npm run check`, `npm test`, `npm run build`; then every proof named in Step 1 through `spikes/issue-210/run_proof.py`, and `spikes/issue-210/proof_no_transition.py`;
- commit and push the implementation branch; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. The visual design inside direction D is yours to decide; if any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, provide the full implementer → orchestrator handoff: starting and head SHAs; the copy and carry-forward commit SHAs; the captures for the owner; every proof's result with its transcript location; the cheap-to-change report; the shadcn-svelte trial report with package versions, licences and sizes; the style-recalculation diagnostic; everything tried and dropped; and anything not done.

# Ticket-specific review decision

**Review path:** `standard orchestrator review`

**Reason:**
The change is confined to a spike directory and evidence. It touches no parser, rule, rail, server lifecycle or shipped code, and the #206 proofs run against it mechanically. The judgement that cannot be automated, whether the design is good, belongs to the owner's acceptance from the captures, not to a second model. The orchestrator should move to independent adversarial review if the real diff adapts more than the one oracle case, changes `lib/` beyond the carry-forward and a small helper, or needed difficult iterations.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] The approved plan SHA is an ancestor of the head and the plan file is unchanged.
- [ ] Nothing outside `spikes/issue-210/`, `docs/evidence/issue-210/` and `worklog/` changed; `spikes/issue-206/` is byte-identical to `main`.
- [ ] The copy commit is verbatim (`diff -r -x node_modules -x dist` prints nothing at that commit) and the carry-forward commit equals #209's `lib/` diff.
- [ ] `package.json` adds only approved packages, pinned exactly; `daisyui` is gone; licences and sizes are recorded.
- [ ] S1, S2, S3, S4, S5, S6, S7, S13, S15 and `check_source.py` pass through the runner, with transcripts. The only oracle change is the tuned-stat merge, and its differing case has a test.
- [ ] `proof_no_transition.py` passes in both schemes over all 435 buttons; the style-recalculation diagnostic is recorded.
- [ ] Verdict controls are `aria-pressed` buttons using `aria-disabled`; the class filter is a native `select`; pressed, kept and same-stat states each have a non-colour cue.
- [ ] No inline `style` attribute, web font, image or CSP addition; no `content-visibility`.
- [ ] Captures exist for dark and light at 1440 px and 390 px on the real fixture, and match direction D's structure.
- [ ] The cheap-to-change report splits components and stylesheet, generated files, logic, tests and tooling, measured from the carry-forward commit.
- [ ] Tried-and-dropped approaches and the shadcn-svelte trial are reported.
- [ ] Likely findings 1 to 4 were each checked against the diff.
- [ ] The owner has accepted the design from the captures before any PR is proposed.

# Review outcome steps (each needs its own authorization)

- Open the ticket's one PR to `main`, with `Refs #210` unless the owner says the PR closes the issue.
- Create the follow-up issue for repeating #209's seven-comparison timing gate on the redesigned slice.
- Comment on and close #152 as superseded by #210.

# Dispatch comment draft

Planned #210 in [handoffs/issue-210-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/<plan_sha>/handoffs/issue-210-implementation-plan.md), approved at plan SHA `<plan_sha>`.

- **Implementer model & effort:** `claude-opus-5-5` at `high`
- **Implementation branch:** `feat/issue-210-armor-duplicates-redesign`
- **Likely findings:** parity loss hidden by the tuned-stat merge; transitions returning through shadcn-svelte classes on verdict controls; accessibility semantics traded for the library; a cheap-to-change figure that leaves out generated files or carried-forward logic
