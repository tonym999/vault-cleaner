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
   - Pin every claim to an exact `file:line` reference or an empirical measurement script/command.

2. **Resolve Staleness:**
   - Treat the issue body as potentially stale relative to current `main`.
   - Explicitly document any divergence between the issue description and current repository state under *Dependencies and assumptions*.

3. **Allocate Names & State Copy Verbatim:**
   - Allocate the implementation branch name (e.g. `fix/issue-N-...` or `feat/issue-N-...`).
   - State exact user-facing copy verbatim where copy is decided.

4. **Construct the Mechanical Inclusion Test:**
   - Define a rule-based inclusion test with worked examples showing what changes are strictly in-scope and what changes are out-of-scope.
   - Specify explicit stop conditions that require the implementer to halt and return to the orchestrator.

5. **Predict Likely Findings:**
   - State 2–4 specific things most likely to be wrong during orchestrator review (e.g. scope leakage from adjacent tickets, tests passing without their fix).

6. **Emit the Named-Section Contract:**
   - You MUST emit all required named sections expected by the orchestrator template.

---

## Handoff Document Structure

Author the handoff document using the following exact structure:

```markdown
# Issue #N — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#N — <Issue Title>`

**Milestone:** `<Milestone>`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator reviews → PR`

**Implementation model selected:** `<Model Tier>` (justified below)

**Plan baseline:** `main` at `<Commit SHA>` (<Date>)

**Allocated implementation branch:** `fix/issue-N-<short-name>`

The implementer must **not** open a pull request. The implementation branch is reviewed by the orchestrator before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer).

## Objective

<Brief description of what the change accomplishes and why.>

## Context & Measurement

<Measured current state, reproducing commands/scripts, and exact file:line references.>

## Dependencies and assumptions

<Staleness resolution, code state relative to issue body, and dependencies on prior tickets.>

## Proposed Plan & Scope

### [Component Name]

#### [MODIFY] [file.py](file:///path/to/file.py#L10-L20)
#### [NEW] [new_file.py](file:///path/to/new_file.py)
#### [DELETE] [old_file.py](file:///path/to/old_file.py)

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

## Likely findings

1. **<Finding 1 Title>:** <Prediction of potential defect or scope leak>
2. **<Finding 2 Title>:** <Prediction of test or coverage gap>

# Reusable implementer execution prompt

Implement issue #N in `tonym999/vault-cleaner` using the committed handoff at:

```text
handoffs/issue-N-implementation-plan.md
```

on the branch `handoff/issue-N-implementation-plan`.

Read the entire handoff, issue #N, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `<allocated-branch-name>`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `git diff --check origin/main...HEAD`;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, provide the full implementer → orchestrator handoff specified in the plan.

# Ticket-specific review decision

**Review path:** `standard orchestrator review`

**Reason:**
<Justification for standard review path vs replanning based on architectural risk and scope scope boundaries.>

# Review checklist

- [ ] Check 1: <Verification item 1>
- [ ] Check 2: <Verification item 2>
- [ ] Check 3: <Likely findings check>

# Dispatch comment draft

```markdown
Planned #N in `handoffs/issue-N-implementation-plan.md` on `main`.

- **Implementer tier:** <Model Tier>
- **Implementation branch:** `<allocated-branch-name>`
- **Likely findings:** <Brief summary of predicted review focus areas>
```
```
