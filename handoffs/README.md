# Multi-Agent Handoff Workflow

This directory contains repository implementation plans ("handoffs") and operational templates for the multi-agent development workflow in `tonym999/vault-cleaner`.

## Topology

```text
planner → orchestrator → implementer → orchestrator reviews → PR
```

## Roles

1. **Planner**
   - **Responsibility:** Researches an open issue, measures current code state, resolves any staleness in the issue body, designs the solution, allocates branch names, and authors the implementation handoff document using `handoffs/templates/planner.md`.
   - **Tier Selection:** Selected by the caller/user or orchestrator brief. The planner selects and justifies the *implementer's* model tier within the plan.

2. **Orchestrator**
   - **Responsibility:** Operates from `main` using `handoffs/templates/orchestrator.md`. Reads the merged plan from `main`, dispatches the implementer at the plan's specified tier, reviews the resulting diff (`git diff base_sha...HEAD`) and test execution outputs, returns feedback if defects exist, and opens the implementation PR once clean.
   - **Constraint:** Never writes production code or implements tickets directly.

3. **Implementer**
   - **Responsibility:** Executes the handoff instructions on the allocated branch (`fix/issue-N-...` or `feat/...`). Follows the plan's mechanical inclusion test, adds tests, updates `WORKLOG.md` and documentation, verifies with tests and linters, and reports results back to the orchestrator.
   - **Constraint:** Does not open pull requests or widen implementation scope.

## Document Lifecycle & Two-PR Process

Every ticket follows a two-PR lifecycle:

1. **Plan Phase (PR 1):**
   - The planner creates `handoffs/issue-N-implementation-plan.md` on a short-lived plan branch (`handoff/issue-N-implementation-plan`).
   - Appends a dated entry to `WORKLOG.md` recording the planning session.
   - Opens PR 1 targeting `main`.
   - Once merged to `main`, the planner posts a dispatch comment on the issue thread with the plan's path on `main`, the implementer tier, allocated branch name, and likely findings.

2. **Implementation Phase (PR 2):**
   - The orchestrator reads the merged plan from `main`.
   - Dispatches the implementer to work on the allocated implementation branch.
   - Once reviewed and verified, the orchestrator opens PR 2 targeting `main` with a dated `WORKLOG.md` entry.

## Naming Convention

All plan files stored in this directory follow the standard format:

```text
handoffs/issue-N-implementation-plan.md
```

- Filenames must **never** include role names (e.g. `luna`) or model tier suffixes (e.g. `xhigh`).
- Branch names for plans follow `handoff/issue-N-implementation-plan`.
- Implementation branches follow `fix/issue-N-...` or `feat/issue-N-...` as allocated in the plan.

## Stop-Condition Escalation Routing

If an edge case, breaking change, or scope conflict occurs during implementation:

```text
Implementer → Orchestrator → Planner
```

1. **Implementer:** Stops work immediately when a plan stop condition is triggered and reports the exact conflict to the orchestrator without attempting to widen scope.
2. **Orchestrator:** Evaluates whether the issue can be resolved within the existing plan contract. If non-trivial plan changes are required, the orchestrator escalates to the **Planner** rather than re-cutting the plan or broadening implementation scope.
3. **Planner:** Re-evaluates the codebase, amends or re-cuts the plan, and submits a revised plan PR.
