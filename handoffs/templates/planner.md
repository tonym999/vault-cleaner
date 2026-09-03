# Planner Template

This template directs a **Planner Agent** to plan the work for an issue and generate a canonical implementation handoff document at:

```text
handoffs/issue-N-implementation-plan.md
```

---

## Planner Instructions

When acting as the **Planner**:

1. **Read and Measure First:**
   - Read the target issue body, neighbouring/overlapping issues, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and relevant source files.
   - Measure real system state before prescribing changes (e.g. run layout measurements, inspect schemas, check exact line counts).
   - Pin every claim to an exact repository-relative path and line number relative to the repository root (e.g. `src/vault_cleaner/ui/review_ui.js:1125`) or an empirical measurement script/command. In markdown links within the handoff file itself, use paths relative to the `handoffs/` directory (e.g. `[review_ui.js](../src/vault_cleaner/ui/review_ui.js#L1125)`). Do NOT use non-portable machine-local `file:///` URIs.

2. **Resolve Staleness:**
   - Treat the issue body as potentially stale relative to current `main`.
   - Explicitly document any divergence between the issue description and current repository state under *Dependencies and assumptions*.

3. **Allocate Names & State Copy Verbatim:**
   - Allocate the implementation branch name (e.g. `fix/issue-N-...` or `feat/issue-N-...`).
   - State exact user-facing copy verbatim where copy is decided.

4. **Select Model & Native Reasoning Effort:**
   - Consult the model family and reasoning-effort matrix in [handoffs/README.md](../README.md#model-family--provider-native-reasoning-effort-matrix).
   - Select and justify the implementer's exact model ID and native reasoning effort setting (e.g. `claude-sonnet-5` with `xhigh` effort) based on task complexity. Note that neither the plan nor this workflow selects the planner or orchestrator tier, and the orchestrator selects any adversarial reviewer's exact model and effort only after inspecting the real diff.
   - Note the manual cross-provider boundary: the orchestrator will verify whether its active runtime supports the target model, or prepare the prompt for a human operator.

5. **Construct the Mechanical Inclusion Test & Escalation Routing:**
   - Define a rule-based inclusion test with worked examples showing what changes are strictly in-scope and what changes are out-of-scope.
   - Specify explicit stop conditions that require the implementer to halt and return to the orchestrator.
   - Note the escalation route: `implementer → orchestrator → planner`.

6. **Predict Likely Findings:**
   - State 2–4 specific things most likely to be wrong during orchestrator review (e.g. scope leakage from adjacent tickets, tests passing without their fix, missing browser coverage).

7. **Determine Recommended Review Path:**
   - Designate `standard orchestrator review` for self-contained, low-risk, or routine changes.
   - Designate `independent adversarial review` for changes touching core parsers, ranking rules, delete rails, server lifecycle, security, or cross-cutting abstractions. Note that the orchestrator will confirm or adapt this path upon inspecting the real diff.

8. **Emit the Named-Section Contract:**
   - You MUST emit all required named sections expected by the orchestrator template.

---

## Handoff Document Structure

Author the handoff document using the following exact structure:

````markdown
# Issue #N — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#N — <Issue Title>`

**Milestone:** `<Milestone>`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `<Exact Model ID & Native Effort>` (justified below)

**Plan baseline:** `main` at `<Commit SHA>` (<Date>)

**Allocated implementation branch:** `fix/issue-N-<short-name>`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

<Brief description of what the change accomplishes and why.>

## Context & Measurement

<Measured current state, reproducing commands/scripts, and exact file:line references.>

## Dependencies and assumptions

<Staleness resolution, code state relative to issue body, and dependencies on prior tickets.>

## Proposed Plan & Scope

### [Component Name]

#### [MODIFY] [file.py](../src/vault_cleaner/file.py#L10-L20)
#### [NEW] [new_file.py](../src/vault_cleaner/new_file.py)
#### [DELETE] [old_file.py](../src/vault_cleaner/old_file.py)

<Detailed breakdown of changes per file.>

## Mechanical inclusion test

A proposed change is **in scope** if and only if:
- <Criterion 1>
- <Criterion 2>

Worked examples:
- **IN SCOPE:** <Example of valid change>
- **OUT OF SCOPE:** <Example of invalid change>

### Stop conditions
Stop implementation and return to orchestrator if:
- <Stop condition 1>
- <Stop condition 2>

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **<Finding 1 Title>:** <Prediction of potential defect or scope leak>
2. **<Finding 2 Title>:** <Prediction of test or coverage gap>

# Reusable implementer execution prompt

Implement issue #N in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-N-implementation-plan.md
```

Read the entire handoff, issue #N, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `<allocated-branch-name>`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py` (if touching UI), `git diff --check origin/main...HEAD`;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, provide the full implementer → orchestrator handoff specified in the plan.

# Ticket-specific review decision

**Review path:** <Choose exactly one: `standard orchestrator review` or `independent adversarial review`>

**Reason:**
<Justification for standard orchestrator review vs independent adversarial review based on architectural risk, invariant sensitivity, and blast radius.>

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] Check 1: <Verification item 1>
- [ ] Check 2: <Verification item 2>
- [ ] Check 3: <Likely findings check>

# Dispatch comment draft

Planned #N in [handoffs/issue-N-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-N-implementation-plan.md) on `main`.

- **Implementer tier & effort:** <Exact Model ID & Native Effort>
- **Implementation branch:** `<allocated-branch-name>`
- **Likely findings:** <Brief summary of predicted review focus areas>
````
