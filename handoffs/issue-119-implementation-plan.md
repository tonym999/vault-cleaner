# Issue #119 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#119 — Implement the Armor duplicates count and hierarchy treatment`

**Milestone:** `M9 — Duplicate Review UX`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator reviews → PR`

**Implementation model selected:** `Sonnet 5` (`xhigh` native effort) (justified: extensive DOM transposition in `review_ui.js`, CSS grid restyling in `review.css`, live ARIA region integration, and Playwright UI tests; see model matrix in [handoffs/README.md](README.md#model-family--provider-native-reasoning-effort-matrix)).

**Plan baseline:** `main` at `9a14847` (2026-09-03)

**Allocated implementation branch:** `feat/issue-119-armor-duplicates-hierarchy`

The implementer must **not** open a pull request. The implementation branch is reviewed by the orchestrator before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer).

## Objective

Implement the Armor duplicates count and hierarchy treatment decided in #113. This replaces the dual `SHOWN` tile (`review_server.js:838`) and `Showing N of M groups` status text (`review_server.js:997`) on the Armor duplicates surface with one `aria-live="polite"` scoped summary region, transposes the member comparison view from columns to rows (`review_ui.js:1125+`) while preserving conditional stat/tuning attributes, standardises the user-facing noun to `pieces`, and fixes same-stat proposal copy so it never asserts nothing is proposed when members carry proposals.

## Context & Measurement

- Measured on `main` at `9a14847`:
  - `src/vault_cleaner/ui/review_ui.js:1125+` renders `armorGroupTable` with members as columns. At 390px viewport width, only one column fits, forcing horizontal table scrolling.
  - Dual count displays exist at `src/vault_cleaner/ui/review_server.js:838` (the `SHOWN` tile) and `src/vault_cleaner/ui/review_server.js:997` (`"Showing " + filteredGroups.length + " of " + selectedArmorGroups.length + " groups"`).
  - Copy uses mixed nouns (`groups`, `proposals`, `items`, `members`, `copies`) across `.tile-label`, header text, and group summaries.
- Evidence & references:
  - `docs/duplicate-review-count-design.md` records the settled count hierarchy decision.
  - `tests/fixtures/armor_same_stat_four_ui.csv` contains the 4-member same-stat group fixture for UI verification.

## Dependencies and assumptions

- **Depends on #113:** Decision record is settled; transposition and single-scoped aria-live summary are adopted.
- **Independent of #115, #116, #117:** This plan must not implement bulk verdict controls, score badge projections, or DIM query copying.
- **Coordination with #118:** PR #121 merged at `9a14847`, repairing presentation defects (renaming `"Hard protection"` to `"Protection"` in `review_ui.js`, dropping internal enums, and adding `overflow-wrap: anywhere`). Note that #118 satisfied facet noun labeling (scope item 13 / copy change 6); that item is dropped on rebase.

## Proposed Plan & Scope

### UI Presentation & Logic (`src/vault_cleaner/ui/`)

#### [MODIFY] [review_server.js](src/vault_cleaner/ui/review_server.js#L838-L997)
- Remove `SHOWN` tile rendering from `renderTiles()` at line 838 on the Armor duplicates surface.
- Remove inline `"Showing " + filteredGroups.length ...` string at line 997.

#### [MODIFY] [review_ui.js](src/vault_cleaner/ui/review_ui.js#L1125)
- Add scoped summary region above the group list with `aria-live="polite"`:
  - Filtered: `X of Y groups · A of B pieces — filtered to <filter>`
  - Unfiltered: `Y groups · B pieces`
- Transpose `armorGroupTable` at line 1125+ to render members as stacked rows instead of columns:
  - Preserve `memberValues` conditional attribute rendering (only show `Seasonal Mod`, `Holofoil`, `Tuning Stat` when members actually differ).
- Update group header to prepend piece count (e.g. `3 pieces`).
- Standardise all user-facing nouns to `pieces` (retiring `copies`, `items`, `members` from rendered text).
- Update same-stat banner copy:
  - Unconditional sentence: `Base stats match but tuning differs, so this pass selects no survivor.`
  - Conditional sentence (when member has proposal): `Pieces below that already carry a proposal keep their verdict controls.`

#### [MODIFY] [review.css](src/vault_cleaner/ui/review.css)
- Add CSS layout rules for the transposed member rows and the scoped summary `aria-live` container.
- Ensure wide-group labels do not silently truncate at 390px or 1440px viewports.

### Automated Tests (`tests/`)

#### [MODIFY] [test_server_browser.py](tests/test_server_browser.py)
- Add Playwright browser tests covering:
  - Scoped summary ARIA live region announcement on filter changes.
  - Transposed row layout at 390px and 1440px viewports.
  - Four-member same-stat fixture rendering and conditional same-stat banner copy.

#### [MODIFY] [docs/browser-verification.md](docs/browser-verification.md)
- Record Playwright test commands and visual verification logs.

---

## Mechanical inclusion test

A proposed change is **in scope** if and only if:
- It alters user-facing count labels, live region ARIA attributes, member transposition layout, or same-stat banner copy on the Armor duplicates view as specified in Issue #119; or
- It adds required Playwright browser tests or documentation for these presentation changes.

Worked examples:
- **IN SCOPE:** Changing `"Exact duplicate group"` sub-line to add piece count or rendering members as stacked rows.
- **OUT OF SCOPE:** Adding per-group bulk verdict buttons (scope of #115) or copy DIM search query button (scope of #117).

### Stop conditions
Stop implementation and return to orchestrator if:
- Implementation requires changing backend rules, snapshot schemas, or verdict handling;
- Python `report_run.RULESET_VERSION` bump is needed;
- Issue #115 or #117 functionality is requested.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Scope Leakage:** Unintentionally including bulk verdict buttons (#115) or DIM query tools (#117).
2. **Conditional Column Loss:** Losing the `memberValues` logic that hides invariant `Seasonal Mod` / `Tuning Stat` columns when transposing columns to rows.
3. **ARIA Announcement Failure:** Missing `aria-live="polite"` on the scoped summary container or failing to update it dynamically on filter change.

# Reusable implementer execution prompt

Implement issue #119 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-119-implementation-plan.md
```

Read the entire handoff, issue #119, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-119-armor-duplicates-hierarchy`; branch from latest `main` and record base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `git diff --check origin/main...HEAD`;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to orchestrator with exact conflict; do not broaden scope.

When complete, provide the full implementer → orchestrator handoff specified in the plan.

# Ticket-specific review decision

**Review path:** `standard orchestrator review`

**Reason:**
Issue #119 is presentation-only on the local review server UI. It alters no rules, ranking, persistence, security boundaries, or snapshot schemas. `Sonnet 5` (`xhigh` effort) is required for the complex UI layout transposition and Playwright test harness.

# Review checklist

- [ ] Is `pieces` used consistently as the sole user-facing noun for armor items?
- [ ] Is the `aria-live="polite"` scoped summary region rendered above the group list?
- [ ] Are `SHOWN` tile (`review_server.js:838`) and duplicate `Showing...` strings (`review_server.js:997`) removed?
- [ ] Is `memberValues` conditional attribute hiding preserved in transposed row layout?
- [ ] Does same-stat banner render unconditional no-survivor sentence and conditional verdict controls sentence?
- [ ] Are Playwright tests passing at 390px and 1440px viewports?

# Dispatch comment draft

Planned #119 in [handoffs/issue-119-implementation-plan.md](handoffs/issue-119-implementation-plan.md) on `main`.

- **Implementer tier & effort:** `Sonnet 5` (`xhigh` native effort)
- **Implementation branch:** `feat/issue-119-armor-duplicates-hierarchy`
- **Likely findings:** Scope leakage into #115/#117, loss of conditional attribute hiding during row transposition, ARIA live region dynamic update gaps.
