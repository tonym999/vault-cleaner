# Issue #118 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#118 — Fix mislabelled and overflowing text in the review UI`

**Milestone:** `M9 — Duplicate Review UX`

**Implementation model:** orchestrator plans → implementer implements → orchestrator reviews → PR

**Implementation model selected:** **Claude Sonnet 5, extended thinking enabled**

**Plan baseline:** `main` at `95b9706` (2026-09-03; merge commit for #113 / PR #120)

**Allocated implementation branch:** `fix/issue-118-review-ui-labels`

The implementer must **not** open a pull request. The implementation branch is reviewed by the orchestrator before any PR is created.

This document uses role-neutral names. Earlier handoffs in this repository, stored on the `handoff/issue-*-luna-plan` branches, call the same two roles *Sol* (orchestrator) and *Luna* (implementer); the structure below is theirs.

## Objective

Fix three shipped presentation defects in the local review UI, and close a fourth by adopting copy already decided in #113 / PR #120. All four were found while capturing baseline evidence for #113; none depends on a design decision and none is blocked.

At completion:

- no row label on the Armor duplicates surface contradicts the value its cells render — the row headed `Hard protection`, which renders `member.protectionLevel` and can therefore read `Hard protection: soft — locked`, is headed `Protection`;
- no user-facing string contains a raw internal enum — the exact-group sub-line reads `Exact duplicate group` rather than `Exact duplicate group · exact_duplicate`;
- the page does not scroll horizontally at a 390px viewport, for ordinary **or** hostile item names, both causes being fixed by wrapping rather than by removing any contained scroller;
- every duplicate-surface facet option states the noun it counts — `Melee (1 group)`, `Chest Armor (2 groups)`;
- regression coverage exists for each, at this repository's established verification sizes; and
- grouping, ranking, survivor selection, verdict authority, report/server contracts, persistence, lifecycle and authentication are untouched.

This is a defect-repair and copy ticket. It must not become the count-and-hierarchy treatment scheduled in #119.

## Why this ticket is ready

- #113 is closed, delivered by merged PR #120. Its decision record is on `main` at `docs/duplicate-review-count-design.md`, so the one piece of copy #118 shares with #119 is already decided and reviewed.
- #112 (closing #110) and #111 (closing #102) are both closed. The Armor duplicates surface these defects live on is on `main` and stable.
- The issue explicitly states `Dependencies: None — this issue is not blocked by the #113 design decision and can ship immediately.`
- Issue #118 has no comments, no parent issue and no sub-issues.
- The only coordination edge is #119, which is open and unstarted. The written relationship is:

```text
#113 (closed, PR #120) → #118 (this ticket) → #119
```

  Both touch `review_ui.js` group rendering, so whichever lands second rebases. #119's own body carries the instruction `#118 lands first → Remove any overlapping item; note the rebase`.

## Model selection

**Use Claude Sonnet 5, with extended thinking enabled.**

The production changes are trivial — two string literals, one option-text expression, two CSS declarations. The test work is not. Required regression coverage lands in three bespoke harnesses: a Node `vm.runInNewContext` fake-DOM harness in `tests/test_server_ui_js.py`; a Node module harness in `tests/test_review_ui_js.py` whose assertions are **exact JSON-equality dictionaries**, so a new probe must be added to the emitted object and the expected dictionary in lockstep; and a Playwright suite in `tests/test_server_browser.py` that contains **no viewport-setting test to copy**. Designing assertions into those harnesses is judgement work, not transcription, and that is the whole reason this is not a cheapest-tier ticket.

It does not warrant staying with the orchestrator. Nothing here touches rules, scoring, grouping, schemas, persistence, revisions, lifecycle, authentication or concurrency, and no design space is left open: every string is either specified in the issue or already decided in `docs/duplicate-review-count-design.md`.

Because the tier is mid, this plan states intent, constraints and exact copy, and leaves harness mechanics to the implementer. The scope rule and stop conditions are at full strength regardless of tier.

## Review model

**Review path: standard orchestrator review.**

```text
orchestrator plan
    ↓
implementation
    ↓
same orchestrator plan-conformance and engineering review
    ↓
PR
```

The change is presentation-only. It alters five literals and declarations across `review_ui.js`, `review_server.js` and `review.css`, plus tests and documentation. It changes no architecture, no HTTP contract, no persisted artefact, no stale-state or reconciliation handling, no server lifecycle and no security boundary. `report_run.RULESET_VERSION` is untouched, so no persisted review manifest is invalidated and no snapshot golden is regenerated. Blast radius is the rendered text and wrapping behaviour of one surface.

Two items take extra attention at review without changing the classification: the `code, .mono, kbd` rule is shared with the Proposals surface, so its wrapping change is reviewed for effects there; and the overlap with #119 is reviewed for whether the landed copy matches the decision record verbatim.

**Escalate to independent review or replanning instead of silently continuing if implementation demonstrates that any rules, schema, server, persistence, lifecycle or security-boundary change is actually required.** No such change is expected, and needing one would mean this plan is wrong.

---

# Authoritative context

Before changing code, read all of the following on the then-current `main`:

- `AGENTS.md`, in full — it is the project's operating manual and its rules override defaults;
- `PLAN.md`, especially the M9 section;
- issue #118 and its complete timeline;
- issue #119, closely enough to know what must **not** be built here;
- closed issue #113 and merged PR #120, including the decision record `docs/duplicate-review-count-design.md`;
- `docs/evidence/issue-113/README.md` — the measured baseline these defects come from;
- the newest `WORKLOG.md` entries;
- every production and test file listed under the expected footprint below.

Treat these as authoritative:

- Python selects every survivor, partner and disposition, and remains the only rules engine. Nothing in this ticket may influence one.
- `report_run.snapshot_dict()` is the structured browser/report source; the server returns it without reconstructing truth.
- `review_ui.js` renders export-derived values using DOM text APIs only.
- Instance ids and hashes are opaque strings and never pass through JavaScript `Number`.
- `docs/duplicate-review-count-design.md` §3 is the decided copy for anything this ticket shares with #119.
- `docs/evidence/issue-113/*` is a dated historical record of what the UI looked like on 2026-09-02. Fixing a defect it describes does not make it wrong, and it is not edited by this ticket.

Do not create a second option-label formatter, a second wrapping convention, or a parallel armour group renderer.

## Current repository state relevant to #118

The ticket is **partly stale**, and §*Dependencies and assumptions* below records exactly how. Plan from the actual baseline. Line numbers are from `95b9706` and must be re-confirmed rather than trusted.

1. `src/vault_cleaner/ui/review_ui.js:1162` — the row list built by `armorGroupTable` labels a row `"Hard protection"`, while its cell function renders `member.protectionLevel` plus `" — " + member.protectionReason`. `protectionLevel` is `soft` for a soft-protected member, so the four-member evidence capture shows the literal contradiction `Hard protection: soft — locked`. Per `AGENTS.md`, hard versus soft protection is exactly the distinction governing whether an item can be auto-junked, so this misstates the field a reviewer uses to judge whether a proposal is safe. The cell function is already correct.
2. `src/vault_cleaner/ui/review_ui.js:1050-1052` — the group-kind sub-line is `group.groupKind === "same_stat" ? "Same stats, different tuning · review-only" : "Exact duplicate group · " + group.groupKind`, so the exact branch renders `Exact duplicate group · exact_duplicate`: an internal snake_case identifier appended to prose that already said the same thing. The same-stat branch has no equivalent problem.
3. `src/vault_cleaner/ui/review_server.html:49` — `<code id="vc-fingerprint">` receives a 64-character SHA-256 hex digest from `compute_fingerprint`. `review.css:52-54` gives `code, .mono, kbd` only a `font-family`, with no wrapping guard, so the token cannot break.
4. `src/vault_cleaner/ui/review.css:151` — `.armor-group-header h3` has no wrapping guard either. This is a **second, independent** overflow cause, recorded in PR #120 and `docs/evidence/issue-113/README.md:101-118` as tracked in #118 but never written into the issue body: a 180-character unbroken armour name computes `overflow-wrap: normal` and reports a 2229px scroll width inside a 316px box, propagating through `.armor-group` and `main.wrap` to give the document a 2266px scroll width at 390px.
5. `src/vault_cleaner/ui/review_server.js:913-923` — `duplicateOptions` builds option text as `entry.value + " (" + entry.count + ")"` for all four duplicate facets. `countArmorGroups` (`review_ui.js:626-645`) counts groups, except that for `tuningModSlot` on a `same_stat` group it adds one per distinct **member** tuning, so a group with four tunings matches four options. Every facet uses identical `value (N)` presentation, so nothing distinguishes a partitioning count from an overlapping one.
6. `review.css` contains **no id selectors at all**. It is entirely element- and class-based. Introducing `#vc-fingerprint` as a selector would break the file's only structural convention.
7. `src/vault_cleaner/ui/review_ui.js:767-780` — `optionsFor`, serving the **Proposals** surface, builds the same `value + " (" + count + ")"` string over item counts. It is out of scope, and `tests/test_review_ui_js.py:361` pins its output as `"weapons (2)"`. This is the likeliest way to break the build while doing step 5.

### Measured, not assumed

The orchestrator reproduced defect 3 against a live server on `95b9706` with a temporary Playwright probe, since removed; the working tree was left clean. Uploading `tests/fixtures/armor_same_stat_ui.csv`, switching to the duplicates surface, at a 390×844 viewport:

- **before:** `document.documentElement.scrollWidth === 550`. The issue reports 549; the 1px difference is scrollbar rounding, not a discrepancy.
- **after** adding `overflow-wrap: anywhere` to `code, .mono, kbd` and to `.armor-group-header h3`: `document.documentElement.scrollWidth === 390`.

The prescribed fix is therefore known to work. The implementer is confirming a measured result, not exploring.

### Baseline behaviour that must not regress

Recorded in #119 and the decision record as must-not-regress, having been wrongly flagged as defects by an earlier code-only reading and corrected by rendering the view:

- `.scroller` wrapping with `overflow-x: auto` (`review_ui.js:1189`, `review.css:117,156`). The comparison table's own horizontal scroll is correct, contained behaviour. It must not start propagating to the document, and it must not be removed to "solve" overflow.
- `:focus-visible` at 3px plus the skip link (`review.css:63,105`).
- Light theme as default with a dark override (`review.css:2-19`).
- Zero base stats suppressed in favour of `PRIMARY`/`SECONDARY`/`TERTIARY` tiles plus a caption.
- The `Show: All / Exact / Same stats` kind selector, and whole-group filter semantics.

### Existing coverage that constrains this change

- `tests/test_review_ui_js.py` — Node harness over the packaged `review_ui.js`. The armour-group DOM test at ~600-680 already builds `exactArticle` and `sameArticle` from a projected snapshot and asserts an exact JSON dictionary; a `countArmorGroups` tuning assertion (`countsOnce`) sits at ~1252. Neither `"Hard protection"` nor `"Exact duplicate group"` is asserted anywhere in the suite today — only in `docs/evidence/`.
- `tests/test_server_ui_js.py` — Node fake-DOM harness over `review_server.js`. The test ending at ~2725 boots the adapter, clicks `#vc-view-duplicates`, drives `#vc-dup-kind-*` and reads `document.nodes["vc-dup-f-tuningModSlot"]`. Its `envelope()` supplies one exact group and one same-stat group.
- `tests/test_server_browser.py` — five `@pytest.mark.browser` tests, green in 5.5s locally, with a `live_server` fixture, an `authenticate` helper and armour fixtures wired as module constants. No test sets a viewport.

## Dependencies and assumptions

- **Dependencies: none.** The issue is not blocked. #113 is closed. Nothing waits on #119.
- Implementation must branch from the latest `main`, not blindly from the SHA above. If `main` has advanced, record the new base and first confirm this plan still matches the live code.
- `node` must be on `PATH` — the JavaScript harnesses skip silently without it, which would let this ticket ship with no coverage at all. The managed Playwright Chromium must be installed. Both were verified working on the planning machine.
- `.venv` exists with the `[dev]` extra installed.
- #119 has not landed. If it has, see the stop conditions.
- Existing fake fixtures are sufficient. No new CSV fixture is expected, and adding one is a stop condition.
- `report_run.RULESET_VERSION` and the snapshot golden are unchanged; this is presentation-only and must not touch the decision fingerprint.

### Where the ticket is stale, and what this plan does about it

The issue was written on 2026-09-02, before PR #120 landed. Three points, all resolved here rather than left to the implementer:

1. **Defect 4 is no longer an open question.** The issue says defect 4 "may reasonably be deferred to the #113 implementation if the count treatment changes how facets are labelled". It does: `docs/duplicate-review-count-design.md` §3 copy change 6 specifies `Melee (1 group)`, carried as #119 scope item 13. **The decision for this handoff is to implement it here, with the decided copy verbatim.** It is a one-expression change in `duplicateOptions`, in a function that #119's largest piece — the `armorGroupTable` transposition in `review_ui.js` — does not touch; using already-reviewed copy means #119 inherits it with no churn; and deferring would ship this ticket with one of its own acceptance criteria unmet.
2. **The issue's list of overflow causes is incomplete.** Defect 3 names only the fingerprint. PR #120 and `docs/evidence/issue-113/README.md:101-118` record the `article.armor-group h3` cause and state that **both** are tracked in #118; that never reached the issue body. It is in scope here, because the acceptance criterion "the page does not scroll horizontally at 390px" cannot otherwise hold for hostile names, and because #120 assigned it to this issue. This is the only addition to the issue's stated scope, and it is one CSS declaration.
3. **The paired kind labels are deliberately not adopted.** #119 item 11 will later change the same sub-line to `Exact` / `Same stats · review only`. This plan does **not** take that now: adopting half of a paired copy change would leave `Exact` beside an unchanged `Same stats, different tuning · review-only`, which is worse than either endpoint. The minimal enum removal is used instead, and #119 replaces both labels together.

---

# Ticket-specific algorithmic scope rule

Apply this rule to every proposed production-code hunk.

## Mechanical inclusion test

A hunk belongs in #118 only if **all five** of the following are true:

1. **Site.** It falls inside exactly one of:
   - `review_ui.js` at the group-kind sub-line (~1050-1052) or the comparison row label list (~1160-1170);
   - `review_server.js` inside `duplicateOptions` only;
   - `review.css` in the `code, .mono, kbd` rule or the `.armor-group-header h3` rule only;
   - `tests/test_review_ui_js.py`, `tests/test_server_ui_js.py`, `tests/test_server_browser.py`;
   - `WORKLOG.md` or `docs/browser-verification.md`.
2. **Nature.** It changes a user-visible **string**, or a **wrapping** declaration. It computes no new value, changes no function's return shape, and adds no conditional branch to a rendering decision.
3. **Structure.** It adds, removes, reorders or reparents **no DOM node** on either surface. If the diff introduces an `el(...)` call or deletes one, the work belongs to #119.
4. **Contract.** It touches no snapshot key, no envelope field, no `data-*` attribute, no element `id`, no `aria-label`/`aria-pressed` value, and not `RULESET_VERSION`.
5. **Necessity.** Reverting the hunk alone would leave at least one of the issue's five acceptance criteria unmet.

If a hunk fails any part of this test, it does not belong in #118.

## Worked examples

| Proposed change | Verdict |
|---|---|
| Change `"Hard protection"` to `"Protection"` | Passes all five. **In.** |
| Also add a caption explaining hard versus soft protection | Fails 3 (new node) and 5 (no criterion needs it). **Out.** |
| Add `overflow-wrap: anywhere` to `.badge` | Fails 1 (rule not listed) and 5 — badge truncation is #119 item 6, not this issue's criterion. **Out.** |
| Append `" group"`/`" groups"` in `duplicateOptions` | Passes all five. **In.** |
| Make the same change in `optionsFor` | Fails 1 (wrong call site) and 5, and breaks a pinned test. **Out.** |
| Delete the `Showing N of M groups` line while in `renderList` | Fails 1, 3 and 5. **Out** — #119 copy change 1. |
| Add an `aria-live` region above the group list | Fails 1, 3 and 4. **Out** — #119 copy change 2. |

## Stop and return to the orchestrator for replanning if

- `git log origin/main` shows #119, or any change touching `armorGroupTable`, `duplicateOptions` or the duplicate-surface count lines, has landed since `95b9706` — this plan's line references and its overlap decision both need re-cutting;
- after both wrapping declarations the 390px assertion still fails — report the measured `scrollWidth` and the offending element, and do **not** broaden the CSS, relax the assertion, or touch `.scroller`, `table { min-width }`, `.armor-group-table` or `.armor-member-heading` to force it through;
- an existing test fails because it asserts one of the old strings from a Python rules, report, snapshot or server-contract test rather than a UI test — that would mean a presentation string has become part of a contract, which is above this ticket's pay grade;
- satisfying any acceptance criterion appears to require a new or modified CSV fixture, a snapshot-golden regeneration or a `RULESET_VERSION` bump;
- satisfying any acceptance criterion appears to require adding or removing a DOM node;
- a change would need to touch `src/vault_cleaner/` outside the three UI asset files named above;
- a runtime dependency, CI topology change, browser retry or fixed sleep appears necessary;
- a real vault export or other private data seems necessary for implementation or tests; or
- anything under `data/` appears in `git status`.

Report incidental findings separately. Do not fix them on the #118 branch unless the orchestrator replans the ticket.

---

# Scope

## In scope

- Renaming the comparison row label `Hard protection` to `Protection` (defect 1).
- Removing the raw `group.groupKind` enum from the exact-group sub-line (defect 2).
- A wrapping guard for the report fingerprint (defect 3a).
- A wrapping guard for the armour group heading (defect 3b — the addition recorded above).
- Stating the counted noun, pluralised, on duplicate-surface facet options, using the copy decided in `docs/duplicate-review-count-design.md` §3 change 6 (defect 4).
- Regression coverage for all five, at 1440×1000 desktop and 390×844 narrow.
- A dated `WORKLOG.md` entry and a dated focused-check section in `docs/browser-verification.md`.

## Out of scope

Everything in #119, #115, #116 and #117 — named explicitly, because several are visible from the files being edited:

- the `SHOWN` tile, the `Showing N of M groups` line and its already-filtered denominator, that line's pluralisation, any scoped summary region, any `aria-live` region, any per-group piece count, any same-stat banner, and the `pieces` noun migration — **all #119**;
- transposing `armorGroupTable` from member-as-column to member-as-row — **#119**, and its largest single piece;
- the `Exact` / `Same stats · review only` paired kind labels — **#119**;
- badge truncation of `Existing Proposals action: re`, and the `.badge { white-space: nowrap }` rule causing it — **#119 item 6**;
- per-group bulk verdicts (**#115**), exposing an armour score (**#116**), the DIM query builder (**#117**);
- any change to `optionsFor` on the Proposals surface;
- any change to `countArmorGroups`' computation or return shape;
- any change to Python rules, grouping, ranking, survivor selection, notes, tags, thresholds, report or server contracts, persistence, revisions, finalisation, lifecycle or authentication;
- bumping `RULESET_VERSION` or regenerating the snapshot golden;
- new dependencies, retries, fixed sleeps or browser matrices;
- editing anything under `docs/evidence/` or `docs/duplicate-review-count-design.md`.

## Expected change footprint

Production files:

```text
src/vault_cleaner/ui/review_ui.js        # two string literals
src/vault_cleaner/ui/review_server.js    # one option-text expression in duplicateOptions
src/vault_cleaner/ui/review.css          # two overflow-wrap declarations
```

Tests:

```text
tests/test_review_ui_js.py
tests/test_server_ui_js.py
tests/test_server_browser.py
```

Documentation:

```text
WORKLOG.md
docs/browser-verification.md
```

Eight files. A ninth is a signal to re-read the mechanical inclusion test.

## Files/components that should normally remain unchanged

```text
src/vault_cleaner/ui/review_server.html
src/vault_cleaner/rules/*.py
src/vault_cleaner/report.py
src/vault_cleaner/report_run.py
src/vault_cleaner/review.py
src/vault_cleaner/review_session.py
src/vault_cleaner/parse.py
src/vault_cleaner/pipeline.py
src/vault_cleaner/config.py
src/vault_cleaner/server/*.py
config.toml
tests/fixtures/*
docs/duplicate-review-count-design.md
docs/evidence/*
docs/armor-archetypes.md
AGENTS.md
PLAN.md
README.md
pyproject.toml
.github/workflows/ci.yml
```

If any normally unchanged component needs a substantive edit, stop and explain why to the orchestrator before proceeding.

---

# Implementation plan for the implementer

## 1. Establish a clean baseline

1. Fetch the latest `main` and create `fix/issue-118-review-ui-labels` from it. The branch name is allocated by this plan, not a suggestion — the orchestrator's review prompt names it in advance. Do not branch from the handoff-storage branch, which holds the plan only.
2. Record the base SHA you actually branched from. If `main` has advanced past `95b9706`, re-confirm the line references in *Current repository state* against the live code before editing anything, and apply the first stop condition if the advance touched this surface.
3. Run the full completion gate below **before** changing anything. All of it must be green. If it is not, stop and report — you are not starting from the state this plan was written against.
4. Capture the 390×844 `document.documentElement.scrollWidth` on the duplicates surface before your change, so you can report a real before/after pair rather than quoting this document.

## 2. Correct the contradictory protection row label

In `review_ui.js`, in the row list built by `armorGroupTable` (~1162), change the row label from `"Hard protection"` to `"Protection"`. Leave the cell function alone: it already renders the level plus `" — " + reason` when a reason exists and `"—"` when there is no level, which is exactly the behaviour the new label describes. Do not add a qualifier such as "level" or "status"; `Protection` is the label the issue specifies.

## 3. Remove the leaked group-kind enum

In `review_ui.js` (~1052), make the exact branch of the group-kind sub-line the plain literal `"Exact duplicate group"`. Leave the `same_stat` branch byte-identical — the issue records it as having no equivalent problem, and the paired #119 relabel is deliberately not adopted here.

Then confirm by search that no other user-facing string in `review_ui.js` or `review_server.js` concatenates `groupKind`, `group_kind`, `disposition` or any other snake_case enum into display text. Two non-display uses are correct and must survive: the `data-group-id` / `data-group-kind` attributes (~1199) and `armorMemberDomIdentity` (~1026).

## 4. Add the two wrapping guards

Both declarations go in `review.css`, using the property spelling already used at `:145` and `:160` — `overflow-wrap: anywhere`, not `word-break` or `word-wrap`. `anywhere`, unlike `break-word`, also reduces min-content width, which is what stops the overflow propagating through `.armor-group` and `main.wrap` to the document.

1. Add it to the existing `code, .mono, kbd` rule (~52). This is the fingerprint fix. Note the deliberate side effect: `.mono` also styles the instance-id span in armour member headings, which gains the same guard. That is intended and harmless — a 19-digit id does not reach the wrap threshold at the 12rem `.armor-member-heading` min-width on desktop — but report it so the reviewer can confirm it.
2. Add it to the existing `.armor-group-header h3` rule (~151). This is the hostile-name fix.

Do **not** introduce an `#vc-fingerprint` id selector. `review.css` contains no id selectors, and adding one breaks the file's convention for a fix that does not need it.

## 5. State the counted noun on duplicate facet options

In `review_server.js`, inside `duplicateOptions` (~919), change the option text from `entry.value + " (" + entry.count + ")"` to state the noun, pluralised on the count: `Melee (1 group)`, `Chest Armor (2 groups)`.

The noun is `group`/`groups` for **all four** duplicate facets (`guardianClass`, `type`, `itemArchetype`, `tuningModSlot`). All four genuinely count groups; the tuning facet counts groups containing at least one member with that slot, which is why its options overlap and its column does not sum to the group total. Naming the noun uniformly is what resolves the issue's complaint that identical `value (N)` presentation distinguishes nothing. The `allLabel` option — "any class", "any slot / type" and so on — is unchanged and carries no count.

**Do not touch `optionsFor` in `review_ui.js` (~778).** It serves the Proposals surface, counts items rather than groups, is out of scope, and its output is pinned by `tests/test_review_ui_js.py:361`.

## 6. Failure, recovery and state behaviour

This ticket introduces no operation, mutation, request or retry.

- Upload, replacement, rejection, stale-verdict reconciliation, finalisation, reset and shutdown remain protocol-equivalent and byte-equivalent.
- No local UI state is added, removed or renamed. Surface selection, kind selection, search text, facet values, focus and the duplicate-row registry all behave exactly as before, because no state feeds the changed strings.
- The changed strings are pure functions of data already projected. There is no new failure mode to recover from: a missing `protectionLevel` still renders `"—"`, and an unrecognised tuning value still normalises to `none/unknown` in Python before it reaches the option label.
- Finalised/read-only state remains readable; the changed text is ordinary snapshot-derived text and mutation controls remain governed by existing code.
- Do not add automatic replay, retries or fixed sleeps, in production code or in the browser test.

## 7. Security and trust boundary

Maintain every existing boundary; none of them moves.

- Raw export text is untrusted. The changed strings are rendered through the same DOM text APIs as before — no `innerHTML`, no HTML interpolation, no URL construction, no executable attribute receives an export value.
- Ids and hashes remain opaque strings and never pass through JavaScript `Number`.
- No request-derived filesystem path is introduced, no endpoint is added, no network permission changes, and no dependency is added.
- Only fake fixtures are committed. Nothing under `data/` is tracked, and no real export, account identifier or instance id appears in a test, a document or a screenshot.
- The wrapping guards change **layout only**. They must not be used to make hostile text safe — it is already inert, proven by the existing hostile-text coverage, and that inertness must remain independently asserted rather than becoming a side effect of a CSS rule.
- Facet option values still originate from the fixed Python tuning vocabulary. An unrecognised hostile string remains `none/unknown`; appending a noun to it must not turn it into markup or a new supported value.

## 8. Documentation and worklog

CI rejects a pull request with no `WORKLOG.md` entry, and that requirement has no escape hatch.

Update:

- `WORKLOG.md` — a newest-first dated entry recording: the four defects fixed and the exact copy now rendered; your own measured before/after `scrollWidth` at 390px; that the `article.armor-group h3` overflow cause was **not** in the issue body but was assigned to #118 by PR #120 and the evidence README, and is fixed here; that defect 4 was implemented with the copy decided in `docs/duplicate-review-count-design.md` §3 change 6, so **#119 scope item 13 / copy change 6 is already satisfied** and #119 should drop it on rebase; that the `Exact` / `Same stats · review only` paired relabel was deliberately not adopted, and why; that the `code, .mono, kbd` change also reaches the Proposals surface, and that this was checked; and that `RULESET_VERSION` is unchanged with no snapshot regenerated and no fixture added.
- `docs/browser-verification.md` — a dated `## YYYY-MM-DD — issue #118 focused check` section, placed with the other dated sections and following their structure: environment, viewports, fixture, results per category, overall result.

Do not edit `docs/evidence/issue-113/*` or `docs/duplicate-review-count-design.md`. Both are dated records of what was observed and decided at the time. No `AGENTS.md`, `PLAN.md` or `README.md` change is expected; believing one is needed is an escalation.

Do not describe any part of #119 as delivered.

## 9. Commit and hand off

After every required gate passes:

1. inspect the complete diff against the recorded implementation base;
2. confirm no private, generated or unrelated files are tracked;
3. commit with a focused message such as `Fix mislabelled and overflowing text in the review UI`;
4. push `fix/issue-118-review-ui-labels`;
5. do not open a PR; and
6. return the structured handoff required below.

---

# Required automated tests

Every defect needs coverage that fails before its fix and passes after. Verify that directly — write the assertion, watch it fail, then apply the fix — for at least defects 1, 2 and 4, where a stale assertion is the likeliest way to ship a test that proves nothing.

## Shared presentation module — `tests/test_review_ui_js.py`

Extend the existing armour-group DOM harness (the test building `exactArticle` and `sameArticle` from a projected snapshot, ~600-680) rather than adding a parallel one. It asserts an exact JSON dictionary; add each probe to the emitted object and the expected dictionary in the same edit.

1. The exact group's `.sub` line equals `Exact duplicate group`.
2. The exact article's text contains no `exact_duplicate`, and no other snake_case enum token.
3. The same-stat group's `.sub` line is unchanged.
4. A comparison row header `Protection` exists in both the exact and the same-stat article.
5. No row header `Hard protection` exists in either.
6. The protection cell still renders level and reason together, and still renders `—` when there is no level.

## Server adapter — `tests/test_server_ui_js.py`

Extend the fake-DOM adapter test that boots the adapter, clicks `#vc-view-duplicates`, drives `#vc-dup-kind-*` and reads `document.nodes["vc-dup-f-tuningModSlot"]` (~2640 onwards), or add a sibling test on the same harness. Assert rendered option **text**, not counts:

7. A singular case reads `… (1 group)` — not `(1 groups)`.
8. A plural case reads `… (2 groups)`. Under the `All` kind selection, a facet value shared by both harness groups — for example the unset `type`, which normalises to `none/unknown` for both — yields a count of 2.
9. The "any …" all-label option is unchanged and carries no count.
10. All four duplicate facets carry the noun, not only the tuning facet.

## Real browser — `tests/test_server_browser.py`

One new `@pytest.mark.browser` test using the existing `live_server` fixture and `authenticate` helper, with `page.set_viewport_size(...)`. No existing test in this file sets a viewport, so this is new construction.

11. At **390×844**, after uploading an existing armour duplicates fixture and switching to the duplicates surface, `document.documentElement.scrollWidth` is not greater than the viewport width. The orchestrator measured 550 before and 390 after, using `tests/fixtures/armor_same_stat_ui.csv`.
12. The same assertion at **1440×1000**, this repository's desktop verification size.
13. The computed `overflow-wrap` of `article.armor-group h3` is `anywhere`. This is a deliberate proxy for the hostile-name case: the committed fixtures do not contain a 180-character armour name, and adding one would be a new fixture, which is a stop condition.
14. `#vc-fingerprint` still renders its digest — the wrapping guard did not hide or empty it.
15. `article.armor-group .scroller` still has a computed `overflow-x` of `auto`, proving overflow was fixed by wrapping and not by removing the contained scroll.

Do not add a browser retry or a fixed sleep.

## Non-regression

16. `tests/test_review_ui_js.py:361` (`"weapons (2)"`) still passes. If it fails, the wrong call site was edited in step 5.
17. The existing hostile-input, focus-preservation, reconciliation, filter and opaque-id tests remain green and are updated only as mechanically required.
18. The five existing browser tests remain green.

---

# Manual verification

Use committed fake fixtures only.

1. Start the packaged local server with `--no-wishlists` and an ephemeral port; upload a fake armour export; open the Armor duplicates surface.
2. At approximately 390×844, confirm by eye that nothing overflows sideways, that the fingerprint wraps rather than being clipped, and that the comparison table still scrolls horizontally **inside its own scroller**.
3. At approximately 1440×1000, confirm the `Protection` row, the `Exact duplicate group` sub-line and the `… (N groups)` facet options read correctly and that nothing else moved.
4. Check both desktop and narrow in **light and dark** appearances.
5. Check the **Proposals** surface at both sizes. Its facet options must still read `weapons (2)`-style with no noun, and the `.mono` wrapping change must not have disturbed its tables. This is the one place the CSS change reaches beyond the duplicates surface.
6. Confirm the skip link and the `:focus-visible` ring still behave, and that keyboard traversal of the duplicates surface is unchanged.
7. Confirm finalised state remains readable and frozen.
8. End with Shutdown or stop the server process.

Record environment, browser and version, viewports, fixture, pass/fail, defects corrected and remaining limitations in `docs/browser-verification.md` and in the handoff.

Do not claim any part of #119 was tested; it remains unimplemented.

---

# Exact validation commands

Run from the repository root on the implementation branch.

## Focused Python/Node gate

```bash
.venv/bin/ruff check src tests scripts
```

```bash
.venv/bin/pytest -q tests/test_review_ui_js.py tests/test_server_ui_js.py
```

```bash
node --check src/vault_cleaner/ui/review_ui.js
```

```bash
node --check src/vault_cleaner/ui/review_server.js
```

## Real-browser gate

```bash
.venv/bin/python -m playwright install --with-deps chromium
```

```bash
.venv/bin/pytest -q -m browser tests/test_server_browser.py
```

## Full completion gate

```bash
.venv/bin/ruff check src tests scripts
```

```bash
.venv/bin/pytest -q
```

```bash
git diff --check
```

```bash
test -z "$(git ls-files data/)"
```

```bash
git status --short
```

After committing, also run:

```bash
git log --oneline origin/main..HEAD
```

```bash
git diff --stat origin/main...HEAD
```

```bash
git diff --check origin/main...HEAD
```

`git ls-files data/` must print nothing. `git status --short` must show only the eight files in the expected footprint; a gitignored `build/` tree may exist on disk but must not appear. If the implementation base is newer than this plan's baseline, substitute that recorded base ref for review comparisons.

---

# Implementer completion gate

Hand the branch back only when every item below is true.

- [ ] The branch started from the latest `main`, and its base SHA is recorded.
- [ ] The mechanical inclusion test passes for every production hunk.
- [ ] The comparison row reads `Protection`; the cell still renders level and reason.
- [ ] The exact sub-line reads `Exact duplicate group`; no user-facing string carries a snake_case enum; the `same_stat` branch is byte-identical.
- [ ] Both `overflow-wrap: anywhere` declarations are present, use the existing spelling, and no id selector was introduced.
- [ ] `duplicateOptions` states the noun on all four facets and pluralises correctly; `optionsFor` is untouched.
- [ ] The measured 390px `scrollWidth` before and after the change is recorded from your own run.
- [ ] Each new test was observed to fail before its fix and pass after, for defects 1, 2 and 4 at minimum.
- [ ] Nothing from #119, #115, #116 or #117 was implemented; no DOM node was added, removed, reordered or reparented.
- [ ] `RULESET_VERSION`, the snapshot golden, every fixture, every schema key and every `aria-*`/`data-*`/`id` value are unchanged.
- [ ] No server protocol, persistence, stale-state, lifecycle, authentication or filesystem-boundary change was made.
- [ ] No runtime or dev dependency, CI topology, retry or fixed sleep was added.
- [ ] Focused, browser and full gates pass.
- [ ] Only fake fixtures are committed; nothing under `data/` is tracked.
- [ ] `WORKLOG.md` and `docs/browser-verification.md` are current and cover every point required above.
- [ ] The implementation is committed and pushed to `fix/issue-118-review-ui-labels`.
- [ ] **No pull request has been opened.**

## Required implementer → orchestrator handoff

Return:

- implementation branch and base `main` SHA;
- commit SHA(s);
- files changed;
- concise implementation summary;
- the exact final copy rendered for each of the four defects;
- measured 390px `scrollWidth` before and after;
- tests added or changed, and confirmation of the fail-then-pass observation;
- exact validation commands and results, including test counts;
- browser environment and manual verification result;
- the Proposals-surface check from manual verification step 5;
- unresolved concerns and incidental findings, reported separately and **not** fixed on this branch;
- deviations from this plan and why; and
- explicit confirmation that no PR was raised.

---

# Orchestrating review checklist and prompt

Review the completed implementation for issue #118 in `tonym999/vault-cleaner`.

Do **not** raise a PR until this review is clean. This ticket uses the **standard orchestrator review path**: review both plan conformance and engineering quality against the current issue and this handoff, working from the actual diff against the recorded base.

## 1. Plan-conformance checklist

- [ ] Read issue #118, issue #119, closed #113, merged PR #120, this handoff, and current `AGENTS.md` / `PLAN.md`.
- [ ] Every production hunk passes the mechanical inclusion test.
- [ ] The diff touches at most the eight files in the expected footprint, and nothing in `src/vault_cleaner/` beyond `review_ui.js`, `review_server.js` and `review.css`.
- [ ] No DOM node was added, removed, reordered or reparented.
- [ ] No `data-*`, element `id`, `aria-*`, snapshot key or envelope field changed.
- [ ] `RULESET_VERSION` is unchanged; no snapshot golden regenerated; no fixture added or modified.
- [ ] The comparison row reads `Protection`, the cell is unchanged, and no `Hard protection` string remains outside `docs/evidence/`.
- [ ] The exact sub-line reads `Exact duplicate group`, and the `same_stat` branch is byte-identical to baseline.
- [ ] The two non-display `groupKind` uses — `data-group-kind` and `armorMemberDomIdentity` — survive.
- [ ] Both wrapping declarations are present, correctly spelled, and no id selector was introduced.
- [ ] `duplicateOptions` pluralises correctly across all four facets; `optionsFor` is untouched and `"weapons (2)"` still passes.
- [ ] Nothing from #119 leaked in: no summary region, no `aria-live` addition, no per-group piece count, no banner, no `SHOWN`/`Showing…` change, no `pieces` migration, no `armorGroupTable` transposition, no `.badge` change.
- [ ] `docs/evidence/` and `docs/duplicate-review-count-design.md` are untouched.
- [ ] `WORKLOG.md` has a dated entry covering every required point, especially the #119 item-13 note and the Proposals-surface side effect; `docs/browser-verification.md` has a dated #118 section in house style.
- [ ] No private data, new dependency, retry, fixed sleep or CI topology change.

## 2. Engineering review

- [ ] Would each new test genuinely fail without its fix? Spot-check by reverting one source edit and confirming the corresponding test goes red — do not take the implementer's word for the fail-then-pass observation.
- [ ] Does the browser test assert at **both** 390×844 and 1440×1000?
- [ ] Does it prove overflow was fixed by wrapping rather than by removing a contained scroll — fingerprint still rendered, `.scroller` still `overflow-x: auto`?
- [ ] Does the `code, .mono, kbd` change have any unwanted effect on the Proposals surface, particularly on instance-id columns and table min-widths?
- [ ] Is `Protection` the honest label for what the cell renders in every branch, including the no-level `—` case?
- [ ] Do the facet labels read correctly for a hostile facet value, and is that value still inert text?
- [ ] Is the pluralisation implemented once, rather than duplicated per facet?

## 3. Independent validation to rerun

At minimum rerun:

```bash
.venv/bin/ruff check src tests scripts
```

```bash
.venv/bin/pytest -q
```

```bash
.venv/bin/pytest -q -m browser tests/test_server_browser.py
```

```bash
git diff --check origin/main...HEAD
```

```bash
test -z "$(git ls-files data/)"
```

If findings exist, return precise findings to the implementer, require fixes on the **same branch**, rerun the affected tests plus the complete gate, and review again.

## 4. Review outcome

Because #118 uses the standard orchestrator review path, no independent second review is required. When this review is clean:

1. open the pull request, targeting `main` and referencing issue #118, summarising the four defects, the measured before/after `scrollWidth`, and the deliberate non-adoption of the paired #119 kind labels;
2. add a comment to issue #119 recording that its scope item 13 / copy change 6 is already satisfied and should be dropped on rebase; and
3. add a comment to issue #118 recording the `article.armor-group h3` overflow cause that was missing from its body, so the written record matches what shipped.

---

# Reusable implementer execution prompt

Implement issue #118 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-118-implementation-plan.md
```

Read the entire handoff, issue #118, issue #119 (to know what must **not** be built), closed issue #113 and merged PR #120, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and the current relevant code, tests and docs before editing. Note the handoff's *Dependencies and assumptions* section, which records where the issue is stale relative to the code and how this plan resolves it.

Rules:

- work on `fix/issue-118-review-ui-labels`; the name is allocated by the plan, not yours to choose. Branch it from the latest `main`, not from the handoff-storage branch, and record the base SHA;
- treat current repository state as authoritative if it has legitimately moved since the plan baseline;
- apply the plan's mechanical inclusion test to every production hunk;
- change only user-visible strings and wrapping declarations — no new value, no changed return shape, no added or removed DOM node;
- use the exact copy the plan specifies; do not invent wording, and do not adopt #119's paired kind labels;
- do not touch `optionsFor` on the Proposals surface;
- preserve `.scroller` overflow handling, `:focus-visible` and the skip link, light/dark theming and zero-stat suppression;
- keep ids and hashes opaque strings and all rendering inert;
- do not change Python rules, grouping, ranking, survivor selection, report/server contracts, persistence, verdicts, reconciliation, finalisation, lifecycle or authentication, and do not bump `RULESET_VERSION` or regenerate the snapshot golden;
- do not implement any part of #119, #115, #116 or #117;
- add the required Node and real-Chromium tests, and observe each failing before its fix;
- use fake fixtures only; add none;
- update `WORKLOG.md` and `docs/browser-verification.md`;
- run every focused, browser, full, diff and hygiene command in the handoff;
- write UK English in all prose;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return the issue to the orchestrator with the exact conflict; do not broaden scope.

When complete, provide the full implementer → orchestrator handoff specified in the plan, including branch, base SHA, commits, changed files, the final copy for each defect, measured before/after `scrollWidth`, tests, exact validation results and counts, browser and manual results, risks and deviations, and confirmation that no PR was raised.

---

# Ticket-specific review decision

**Review path:** `standard orchestrator review`

**Reason:**

Issue #118 repairs four presentation defects on an already-landed browser surface, over already-authoritative Python projections and an already-established authenticated server seam. Its allowed change surface is five literals and declarations, plus tests and documentation. It alters no architecture, protocol, persistence, concurrency, stale-state handling, lifecycle, authentication or security boundary, and does not touch the decision fingerprint. The subtlety is concentrated in test-harness design and in not straying into #119's overlapping work — both mechanically checkable against the inclusion test and the pinned `optionsFor` coverage.

The mid implementer tier is justified by that harness work, not by architectural risk, so the standard review path and the tier choice are consistent rather than in tension.

If implementation proves that a forbidden higher-risk boundary must change, the correct response is **replanning**, not silently upgrading the implementation scope.

---

# Observations outside scope

Recorded here rather than folded into the plan. None is actionable by the implementer.

1. **The tuning facet still will not sum to the group total.** Step 5 makes the noun honest, but a reader adding the tuning column up still exceeds the group count, because a same-stat group with four distinct tunings matches four options. A one-line caption under that select would close the gap; it is presentation on the surface #119 is rewriting, so it belongs there — best raised as a comment on #119.
2. **The issue body is missing the `article.armor-group h3` overflow cause.** PR #120 and `docs/evidence/issue-113/README.md` both say it is tracked in #118, but it never reached the issue. Worth a comment on #118 so the record matches whichever way the fix lands.
3. **The empty state names no filter and offers no way to widen.** Recorded as an observation in the evidence README; in no issue the orchestrator could find, including #119. A candidate for a new `enhancement` issue on the M9 milestone.
4. **`docs/evidence/issue-113/count-label-inventory.md` marks 57 of 160 user-facing labels as misreadable.** #118 fixes two and #119 will fix a further set. Nothing tracks the remainder, and nothing states which are intentionally being left. A triage pass over that inventory after #119 lands would close the loop.
5. **`review.css` is 174 lines with no id selectors, styling a surface that has grown considerably.** Not a defect. Noting only that a future ticket adding several component rules may want to reorganise it, and that doing so opportunistically inside a defect fix would be the wrong call.

---

# Template provenance

This document follows the house handoff structure used by the nine earlier handoffs stored on the `handoff/issue-*-luna-plan` branches of this repository, under `handoffs/` — most closely `handoffs/issue-104-luna-xhigh-implementation-plan.md`, the nearest analogue as a presentation-only ticket on the standard review path.

Two deliberate departures. The branch name, file path and commit message for this handoff were set by the orchestration brief and differ from the `*-luna-plan` / `*-luna-xhigh-implementation-plan.md` convention. And the brief requires role-neutral language, so the legacy role names are mapped throughout: *Sol* → the orchestrator, *Luna* → the implementer, with the specific model named only under *Model selection*.
