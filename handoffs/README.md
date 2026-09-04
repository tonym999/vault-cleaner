# Multi-Agent Handoff Workflow

This directory contains repository implementation plans ("handoffs") and operational templates for the multi-agent development workflow in `tonym999/vault-cleaner`.

## Authorization boundary

This document describes how an authorized handoff operates; it grants no
authority to start or advance one. Before every phase and external mutation,
follow the user-authorization gates in [`AGENTS.md`](../AGENTS.md#user-authorization-gates).
Opening or merging PRs, pushing branches, requesting reviewers, posting issue or
PR comments, and changing issue/PR/project state require authorization from the
encompassing phase or a separate user instruction. If that authority is absent
or unclear, stop and report it.

Product implementation tickets use the two-PR lifecycle below. A documentation-
or maintenance-only ticket may use a direct single PR only when the user
explicitly authorizes that issue-to-PR route; the exception never authorizes a
merge.

## Topology

```text
planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR
```

## Roles

1. **Planner**
   - **Responsibility:** Researches an open issue, measures current code state, resolves any staleness in the issue body, designs the solution, allocates branch names, and authors the implementation handoff document using [handoffs/templates/planner.md](templates/planner.md).
   - **Tier Selection:** Neither the plan nor this workflow selects the planner or orchestrator tier. The plan selects and justifies only the *implementer's* model tier and native reasoning effort, plus the recommended review path; it does not select the adversarial reviewer's model.

2. **Orchestrator**
   - **Responsibility:** Operates from `main` using [handoffs/templates/orchestrator.md](templates/orchestrator.md). Reads the merged plan from `main`, dispatches the implementer at the plan's specified tier and effort, determines the final review path after inspecting the real diff, selects and dispatches an independent reviewer when required, routes findings, and, when authorized, carries out the plan's review-outcome steps (opening the implementation PR, adding coordination comments).
   - **Constraint:** Never writes production code or implements tickets directly.

3. **Implementer**
   - **Responsibility:** Executes the handoff instructions on the allocated branch (`fix/issue-N-...` or `feat/issue-N-...`). Follows the plan's mechanical inclusion test, adds tests, updates [WORKLOG.md](../WORKLOG.md) and documentation, verifies with tests and linters, and reports results back to the orchestrator.
   - **Constraint:** Does not open pull requests or widen implementation scope.

4. **Independent adversarial reviewer (optional, transient)**
   - **Responsibility:** Starts in a fresh session with no planner or implementer conversation history, reads the canonical plan and exact `base_sha...head_sha` diff from a disposable checkout pinned to the head SHA, independently reruns applicable verification, and returns evidence-backed findings through the fixed review-result contract.
   - **Constraint:** Implementation-read-only. It may create ephemeral test artifacts only inside its disposable checkout or assigned temporary directory, but does not edit tracked files, commit, push, post comments, open a pull request, implement fixes, or re-plan the ticket. The orchestrator remains the owner of routing and the final review outcome.

## Document Lifecycle & Two-PR Process

Every product implementation ticket follows this two-PR lifecycle once its
phases and mutations have been authorized under `AGENTS.md`:

1. **Plan Phase (PR 1):**
   - The planner creates `handoffs/issue-N-implementation-plan.md` on a short-lived plan branch (`handoff/issue-N-implementation-plan`).
   - Appends a dated entry to [WORKLOG.md](../WORKLOG.md) recording the planning session.
   - Opens PR 1 targeting `main` only when that action is authorized.
   - Once its merge and the coordination action are authorized, the planner posts a dispatch comment on the issue thread with the plan's path on `main`, the implementer tier & effort, allocated branch name, and likely findings.

2. **Implementation Phase (PR 2):**
   - The orchestrator reads the merged plan from `main` (`handoffs/issue-N-implementation-plan.md`).
   - Dispatches the implementer to work on the allocated implementation branch.
   - Chooses the final review path after inspecting the real diff, conducts the standard review or dispatches an independent adversarial reviewer, and routes any findings back to the implementer.
   - Once reviewed and verified, the orchestrator opens PR 2 targeting `main` and executes any required issue comments only when those external mutations are authorized; the PR includes a dated [WORKLOG.md](../WORKLOG.md) entry.

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

## Review Path: Standard vs. Independent Adversarial Review

The review path adapts review rigor to the risk and complexity of the change:

- **Standard Orchestrator Review:** Default path for self-contained, low-risk, or routine changes. The orchestrator conducts the review directly against the plan's checklist, likely findings, and test suites.
- **Independent Adversarial Review:** Triggered when prescribed by `# Ticket-specific review decision` in the plan, or when the orchestrator determines the real diff touches critical invariants (parsers, ranking rules, delete rails, server lifecycle), presents unexpected complexity, or involved difficult implementer iterations.
- **Reviewer Selection:** The orchestrator owns reviewer selection because it sees the real diff. At dispatch time it re-verifies official model availability, selects and justifies one exact model ID and native effort from the current **Independent Review** mapping below, and records the actual provider/model/effort and any fallback. A different model family from the implementer is preferred when available, but independence requires a separate fresh context and read-only remit rather than a different provider.
- **Execution via Fresh Context:** The orchestrator creates a detached disposable checkout pinned to the recorded head SHA, copies the reusable adversarial-review prompt from [handoffs/templates/orchestrator.md](templates/orchestrator.md), substitutes only its declared fields, and hands both to a fresh agent session with no planner or implementer conversation history. The reviewer may write only ephemeral verification artifacts in that checkout or its assigned temporary directory and never edits tracked implementation or durable repository state. It independently reruns applicable checks, explicitly treats a skipped required browser suite as a failure, and labels any command it could not run rather than silently trusting the orchestrator's output. Findings are returned to the orchestrator, who routes fixes back to the implementer before PR creation and sends the complete updated diff back to an independent reviewer for re-review.

### Finding Severity, Blocking, and Disposition

- **P0 — Critical:** Exploitable security exposure, data loss, or catastrophic safety/correctness failure. Blocks PR creation.
- **P1 — High:** Material correctness, security, contract, or regression defect. Blocks PR creation.
- **P2 — Medium:** Meaningful defect or verification/coverage gap. Normally blocks; deferral requires explicit human-owner approval, recorded rationale, and a follow-up reference when work remains.
- **P3 — Low:** Worthwhile non-blocking improvement. Advisory unless elevated by the orchestrator or owner.

The orchestrator records one disposition for every finding: `accepted/fixed`, `rejected` with contrary evidence, or `deferred` under the rule above. Reviewer conclusions are not automatically authoritative. Unresolved P0/P1 disagreements go to the human owner, and also to the planner when resolution would alter the canonical plan or scope. Accepted fixes on an independent-review path require a new complete-diff independent review at the updated immutable head.

## Manual Cross-Provider Execution (v1)

For every implementer or independent-reviewer dispatch, the orchestrator records the requested provider, exact model ID, and native effort, then checks whether its active runtime can instantiate that target. If it cannot, the orchestrator prepares the exact role prompt and a human operator launches the external agent. An external implementer returns its branch, base and head SHAs, test output, and completion handoff; an external reviewer returns the fixed findings report for the supplied immutable SHAs. The orchestrator treats every external result as untrusted. Any scope deviation follows `implementer → orchestrator → planner`. Automated provider discovery, authentication, launching, and monitoring are deferred to a separate issue.

The dispatch record captures the **actual** provider/model/effort used and any fallback taken. A repository model table is selection guidance; it does not itself make that provider available to the active runtime.

The first complete real-issue pilot of this workflow is tracked in [#124](https://github.com/tonym999/vault-cleaner/issues/124). It runs after this workflow is available from `main`, because the orchestrator contract requires a merged plan rather than an unmerged integration-PR artifact.

## Model Family & Provider-Native Reasoning-Effort Matrix

*(Verified 2026-09-03)*

> [!IMPORTANT]
> **Rule:** Planners MUST re-verify this table against official provider documentation before selecting a model and effort setting for a task. State support per model rather than assuming uniform provider support. Do not assume equivalent effort names (e.g. OpenAI `xhigh`, Anthropic `xhigh`, Gemini `high`) produce identical reasoning behavior.

### Task Classes & Recommended Mappings

| Task Class | Model Selection & Effort Rationale | Recommended Model & Native Effort |
|---|---|---|
| **Routine Implementation** | Code edits with clear specs, simple bug fixes, label/presentation updates. | `claude-sonnet-5` (`high`), `gpt-5.6-terra` (`medium`), or `gemini-3.8-flash` (`high`) |
| **Complex Implementation** | Multi-file architectural refactors, server lifecycle changes, complex DOM transposition / Playwright suites. | `claude-sonnet-5` (`xhigh`), `gpt-5.6-sol` (`high`), or `gemini-3.1-pro-preview` (`high`) |
| **Planning** | Codebase research, measurement, staleness resolution, inclusion test definition. | `claude-sonnet-5` (`xhigh`), `gpt-5.6-sol` (`xhigh`), or `gemini-3.1-pro-preview` (`high`) |
| **Independent Review** | Reviewing implementation diffs against plan checklists and likely findings. | `claude-opus-5` (`high`), `gpt-5.6-sol` (`high`), or `gemini-3.1-pro-preview` (`high`) |

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
| **Google** | Gemini 3.x | `gemini-3.1-pro-preview` | `thinking_level` | `low`, `medium`, `high` | Preview — [Google Gemini 3.1 Pro Preview](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview), [Thinking Controls](https://ai.google.dev/gemini-api/docs/thinking) |
| **Google** | Gemini 3.x | `gemini-3.8-flash` | `thinking_level` | `low`, `medium`, `high`; `minimal` is unsupported and returns an error | Stable — [Google Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/latest-model), [Thinking Controls](https://ai.google.dev/gemini-api/docs/thinking) |
| **Google** | Gemini 3.x | `gemini-3.5-flash-lite` | `thinking_level` | `minimal`, `low`, `medium`, `high` | Stable — [Google Gemini Models](https://ai.google.dev/gemini-api/docs/models), [Thinking Controls](https://ai.google.dev/gemini-api/docs/thinking) |
