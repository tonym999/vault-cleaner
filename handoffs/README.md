# Multi-Agent Handoff Workflow

This directory contains repository implementation plans ("handoffs") and operational templates for the multi-agent development workflow in `tonym999/vault-cleaner`.

## Topology

```text
planner → orchestrator → implementer → orchestrator reviews → PR
```

## Roles

1. **Planner**
   - **Responsibility:** Researches an open issue, measures current code state, resolves any staleness in the issue body, designs the solution, allocates branch names, and authors the implementation handoff document using [handoffs/templates/planner.md](templates/planner.md).
   - **Tier Selection:** Selected by the caller/user or orchestrator brief. The plan itself selects and justifies the *implementer's* model tier and native reasoning effort.

2. **Orchestrator**
   - **Responsibility:** Operates from `main` using [handoffs/templates/orchestrator.md](templates/orchestrator.md). Reads the merged plan from `main`, dispatches the implementer at the plan's specified tier and effort, reviews the resulting diff (`git diff base_sha...HEAD`) and test execution outputs, returns feedback if defects exist, and opens the implementation PR once clean.
   - **Constraint:** Never writes production code or implements tickets directly.

3. **Implementer**
   - **Responsibility:** Executes the handoff instructions on the allocated branch (`fix/issue-N-...` or `feat/issue-N-...`). Follows the plan's mechanical inclusion test, adds tests, updates [WORKLOG.md](../WORKLOG.md) and documentation, verifies with tests and linters, and reports results back to the orchestrator.
   - **Constraint:** Does not open pull requests or widen implementation scope.

## Document Lifecycle & Two-PR Process

Every ticket follows a two-PR lifecycle:

1. **Plan Phase (PR 1):**
   - The planner creates `handoffs/issue-N-implementation-plan.md` on a short-lived plan branch (`handoff/issue-N-implementation-plan`).
   - Appends a dated entry to [WORKLOG.md](../WORKLOG.md) recording the planning session.
   - Opens PR 1 targeting `main`.
   - Once merged to `main`, the planner posts a dispatch comment on the issue thread with the plan's path on `main`, the implementer tier & effort, allocated branch name, and likely findings.

2. **Implementation Phase (PR 2):**
   - The orchestrator reads the merged plan from `main` (`handoffs/issue-N-implementation-plan.md`).
   - Dispatches the implementer to work on the allocated implementation branch.
   - Once reviewed and verified, the orchestrator opens PR 2 targeting `main` with a dated [WORKLOG.md](../WORKLOG.md) entry.

## Naming Convention

All plan files stored in this directory follow the standard format:

```text
handoffs/issue-N-implementation-plan.md
```

- Filenames must **never** include role names (e.g. `luna`) or model tier suffixes (e.g. `xhigh`).
- Branch names for plans follow `handoff/issue-N-implementation-plan`.
- Implementation branches follow `fix/issue-N-...` or `feat/issue-N-...` as allocated in the plan.
- The dangling remote `handoff/*` branches remain active on GitHub until PR 1 (the plan PR) merges to `main`. Deleting a `handoff/*` branch is a post-merge cleanup operation.

## Stop-Condition Escalation Routing

If an edge case, breaking change, or scope conflict occurs during implementation:

```text
implementer → orchestrator → planner
```

1. **Implementer:** Stops work immediately when a plan stop condition is triggered and reports the exact conflict to the orchestrator without attempting to widen scope.
2. **Orchestrator:** Evaluates whether the issue can be resolved within the existing plan contract. If non-trivial plan changes or scope alterations are required, the orchestrator escalates to the **Planner** rather than re-cutting the plan or broadening implementation scope.
3. **Planner:** Re-evaluates the codebase, amends or re-cuts the plan, and submits a revised plan PR.

## Model Family & Provider-Native Reasoning-Effort Matrix

*(Verified 2026-09-03)*

> [!IMPORTANT]
> **Rule:** Planners MUST re-verify this table against official provider documentation before selecting a model and effort setting for a task. Do not assume equivalent effort names (e.g. OpenAI `xhigh`, Anthropic `xhigh`, Gemini `high`) produce identical reasoning behavior.

### Task Classes & Recommended Mappings

| Task Class | Model Selection & Effort Rationale | Recommended Model & Native Effort |
|---|---|---|
| **Routine Implementation** | Code edits with clear specs, simple bug fixes, label/presentation updates. | `Sonnet 5` (`high`), `gpt-5.6-terra` (`medium`), or `Gemini 3.6 Flash` (`high`) |
| **Complex Implementation** | Multi-file architectural refactors, server lifecycle changes, complex DOM transposition / Playwright suites. | `Sonnet 5` (`xhigh`), `gpt-5.6-sol` (`high`), or `Gemini 3.6 Pro` (`high`) |
| **Planning** | Codebase research, measurement, staleness resolution, inclusion test definition. | `Sonnet 5` (`xhigh`), `gpt-5.6-sol` (`xhigh`), or `Gemini 3.6 Pro` (`high`) |
| **Independent Review** | Reviewing implementation diffs against plan checklists and likely findings. | `Opus 5` (`high`), `gpt-5.6-sol` (`high`), or `Gemini 3.6 Pro` (`high`) |

### Provider Catalog & Reasoning Controls

| Provider | Model Family | Exact Model ID / Alias | Native Reasoning Control | Allowed Effort Values | Stability / Source |
|---|---|---|---|---|---|
| **OpenAI** | GPT-5.6 | `gpt-5.6-sol` (flagship)<br>`gpt-5.6-terra` (balanced)<br>`gpt-5.6-luna` (efficient) | `reasoning.effort` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | Stable — [OpenAI GPT-5.6 Model Guidance](https://developers.openai.com/api/docs/guides/latest-model) |
| **Anthropic** | Claude | Fable 5.1 (horizon)<br>Opus 5<br>Sonnet 5<br>Haiku 4.5 | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Stable — [Anthropic Model Deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations), [Anthropic Effort Controls](https://platform.claude.com/docs/en/build-with-claude/effort) |
| **Google** | Gemini 3.x | Gemini 3.6 Pro<br>Gemini 3.6 Flash<br>Gemini 3.6 Flash-Lite | `thinking_level` | `minimal`, `low`, `medium`, `high` (model-specific) | Stable — [Google Gemini Model Catalog](https://ai.google.dev/gemini-api/docs/models), [Google Gemini Thinking Controls](https://ai.google.dev/gemini-api/docs/thinking) |
