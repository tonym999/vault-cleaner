# Orchestrator Template

This template boots an **Orchestrator Agent** to manage the execution of a ticket whose plan has merged to `main`.

---

## Orchestrator Operating Instructions

When acting as the **Orchestrator**:

1. **Read Plan from `main`:**
   - Read the merged handoff file at `handoffs/issue-N-implementation-plan.md` on `main`.
   - Do **NOT** read from an unmerged branch; the plan is canonical on `main`.

2. **Dispatch Implementer:**
   - Launch an implementer agent using the exact text under `# Reusable implementer execution prompt` in the handoff document.
   - Dispatch the implementer at the plan's specified **Implementer Tier & Effort** without downgrading model tier or reasoning level.

3. **Zero Direct Implementation:**
   - You must **NEVER** edit source code, write tests, or implement any part of the ticket yourself.
   - All code changes must be produced by the implementer agent on the allocated implementation branch.

4. **Review Real Diffs & Output:**
   - When the implementer reports back, inspect the real git diff against the implementer's recorded base SHA:
     ```bash
     git diff <base_sha>...HEAD
     ```
   - Execute and verify automated test and lint commands directly:
     ```bash
     .venv/bin/ruff check src tests scripts
     .venv/bin/pytest -q
     git diff --check origin/main...HEAD
     ```
   - Evaluate the diff against the plan's `# Review checklist`, `## Likely findings`, and `## Mechanical inclusion test`.

5. **Handle Review Findings:**
   - If defects or scope leaks exist, return precise findings to the implementer and require fixes on the **same implementation branch**.
   - Re-review the updated diff once the implementer completes repairs.

6. **Escalate Stop Conditions:**
   - If the implementer hits a stop condition or if review reveals that architectural boundaries/plans must change, follow the escalation route: `implementer → orchestrator → planner`.
   - Do **NOT** attempt to re-plan or widen implementation scope yourself. Escalate to the **Planner** to amend or re-cut the plan in a revised plan PR.

7. **Finalise & Open PR:**
   - When the implementation is clean and verified, open a pull request targeting `main` referencing the issue number.
   - Ensure a dated [WORKLOG.md](../WORKLOG.md) entry is included in the implementation PR.
