# Multi-Agent Handoff Workflow

This directory contains repository implementation plans ("handoffs") and operational templates for the multi-agent development workflow in `tonym999/vault-cleaner`.

## Topology

```text
planner → orchestrator → implementer → orchestrator reviews → PR
```

## Roles

1. **Planner**
   - **Responsibility:** Researches an open issue, measures current code state, resolves any staleness in the issue body, designs the solution, allocates branch names, and authors the implementation handoff document using [handoffs/templates/planner.md](templates/planner.md).
   - **Tier Selection:** Neither the plan nor this workflow selects the planner or orchestrator tier. The plan itself selects and justifies only the *implementer's* model tier and native reasoning effort.

2. **Orchestrator**
   - **Responsibility:** Operates from `main` using [handoffs/templates/orchestrator.md](templates/orchestrator.md). Reads the merged plan from `main`, dispatches the implementer at the plan's specified tier and effort, reviews the resulting diff (`git diff base_sha...HEAD`) and test execution outputs, returns feedback if defects exist, and carries out the plan's review-outcome steps (opening the implementation PR, adding coordination comments).
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
   - Once reviewed and verified, the orchestrator opens PR 2 targeting `main` with a dated [WORKLOG.md](../WORKLOG.md) entry and executes any required issue comments.

## Naming Convention

All plan files stored in this directory follow the standard format:

```text
handoffs/issue-N-implementation-plan.md
```

- Filenames must **never** include role names (e.g. `luna`) or model tier suffixes (e.g. `xhigh`).
- Branch names for plans follow `handoff/issue-N-implementation-plan`.
- Implementation branches follow `fix/issue-N-...` or `feat/issue-N-...` as allocated in the plan.
- The 10 dangling remote `handoff/*` branches remain active on GitHub until this workflow PR merges to `main`. Deleting a `handoff/*` branch is a post-merge cleanup operation.

## Stop-Condition Escalation Routing

If an edge case, breaking change, or scope conflict occurs during implementation:

```text
implementer → orchestrator → planner
```

1. **Implementer:** Stops work immediately when a plan stop condition is triggered and reports the exact conflict to the orchestrator without attempting to widen scope.
2. **Orchestrator:** Evaluates whether the issue can be resolved within the existing plan contract. If non-trivial plan changes or scope alterations are required, the orchestrator escalates to the **Planner** rather than re-cutting the plan or broadening implementation scope.
3. **Planner:** Re-evaluates the codebase, amends or re-cuts the plan, and submits a revised plan PR.

## Manual Cross-Provider Execution (v1)

The orchestrator records the requested provider, exact model ID, and native effort, then checks whether its active runtime can instantiate that target. If it cannot, the orchestrator prepares the exact implementer prompt and a human operator launches the external agent. The external agent returns its branch, base and head SHAs, test output, and completion handoff. The orchestrator treats that result as untrusted and reviews the complete diff against the plan. Any scope deviation follows `implementer → orchestrator → planner`. Automated provider discovery, authentication, launching, and monitoring are deferred to a separate issue.

The dispatch record captures the **actual** provider/model/effort used and any fallback taken. A repository model table is selection guidance; it does not itself make that provider available to the active runtime.

## Model Family & Provider-Native Reasoning-Effort Matrix

*(Verified 2026-09-03)*

> [!IMPORTANT]
> **Rule:** Planners MUST re-verify this table against official provider documentation before selecting a model and effort setting for a task. State support per model rather than assuming uniform provider support. Do not assume equivalent effort names (e.g. OpenAI `xhigh`, Anthropic `xhigh`, Gemini `high`) produce identical reasoning behavior.

### Task Classes & Recommended Mappings

| Task Class | Model Selection & Effort Rationale | Recommended Model & Native Effort |
|---|---|---|
| **Routine Implementation** | Code edits with clear specs, simple bug fixes, label/presentation updates. | `claude-sonnet-5` (`high`), `gpt-5.6-terra` (`medium`), or `gemini-3.8-flash` (`high`) |
| **Complex Implementation** | Multi-file architectural refactors, server lifecycle changes, complex DOM transposition / Playwright suites. | `claude-sonnet-5` (`xhigh`), `gpt-5.6-sol` (`high`), or `gemini-3.5-pro` (`high`) |
| **Planning** | Codebase research, measurement, staleness resolution, inclusion test definition. | `claude-sonnet-5` (`xhigh`), `gpt-5.6-sol` (`xhigh`), or `gemini-3.5-pro` (`high`) |
| **Independent Review** | Reviewing implementation diffs against plan checklists and likely findings. | `claude-opus-5` (`high`), `gpt-5.6-sol` (`high`), or `gemini-3.5-pro` (`high`) |

### Provider Catalog & Reasoning Controls

| Provider | Model Family | Exact Model ID | Native Reasoning Control | Allowed Effort Values / Support Notes | Stability / Source |
|---|---|---|---|---|---|
| **OpenAI** | GPT-5.6 | `gpt-5.6-sol` | `reasoning.effort` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | Stable — [OpenAI Models Guidance](https://developers.openai.com/api/docs/guides/latest-model) |
| **OpenAI** | GPT-5.6 | `gpt-5.6-terra` | `reasoning.effort` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | Stable — [OpenAI Models Guidance](https://developers.openai.com/api/docs/guides/latest-model) |
| **OpenAI** | GPT-5.6 | `gpt-5.6-luna` | `reasoning.effort` | `none`, `low`, `medium`, `high`, `xhigh`, `max` | Stable — [OpenAI Models Guidance](https://developers.openai.com/api/docs/guides/latest-model) |
| **Anthropic** | Claude | `claude-fable-5-1` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
| **Anthropic** | Claude | `claude-opus-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
| **Anthropic** | Claude | `claude-sonnet-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
| **Anthropic** | Claude | `claude-haiku-4-5-20251001` | None | Effort control not supported on Haiku 4.5 | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview) |
| **Google** | Gemini 3.x | `gemini-3.8-flash` | `thinking_level` | `minimal`, `low`, `medium`, `high` | Stable — [Google Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/latest-model), [Thinking Controls](https://ai.google.dev/gemini-api/docs/thinking) |
| **Google** | Gemini 3.x | `gemini-3.5-pro` | `thinking_level` | `minimal`, `low`, `medium`, `high` | Stable — [Google Gemini Models](https://ai.google.dev/gemini-api/docs/models), [Thinking Controls](https://ai.google.dev/gemini-api/docs/thinking) |
| **Google** | Gemini 3.x | `gemini-3.5-flash` | `thinking_level` | `minimal`, `low`, `medium`, `high` | Stable — [Google Gemini Models](https://ai.google.dev/gemini-api/docs/models), [Thinking Controls](https://ai.google.dev/gemini-api/docs/thinking) |
