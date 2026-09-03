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
   - Dispatch the implementer at the plan's specified **Implementer Tier & Native Effort** without downgrading model tier or reasoning level.
   - **Manual Cross-Provider Execution (v1):** Check whether the active runtime can instantiate the target model and effort setting. If it cannot, prepare the exact implementer prompt and have a human operator launch the external agent. The external agent returns its branch, base and head SHAs, test output, and completion handoff. Treat that result as untrusted and review the complete diff against the plan. Capture the actual provider, model ID, and effort used in the dispatch record.

3. **Zero Direct Implementation:**
   - You must **NEVER** edit source code, write tests, or implement any part of the ticket yourself.
   - All code changes must be produced by the implementer agent on the allocated implementation branch.

4. **Review Real Diffs & Run Verification Suite:**
   - When the implementer reports back, inspect the real git diff against the implementer's recorded base SHA:
     ```bash
     git diff <base_sha>...HEAD
     ```
   - Execute and verify automated test and lint commands directly:
     ```bash
     .venv/bin/ruff check src tests scripts
     .venv/bin/pytest -q
     VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py
     git diff --check origin/main...HEAD
     test -z "$(git ls-files data/)"
     test -z "$(git status --porcelain)"
     ```
     > [!IMPORTANT]
     > **A skip is not a pass.** Running with `VAULT_CLEANER_BROWSER_REQUIRED=1` ensures browser tests fail rather than skip silently when managed Chromium is absent.

5. **Perform the Revert Spot-Check in an Isolated Checkout / Worktree:**
   - When likely findings identify tests that might pass without the fix, perform the fail-then-pass / revert spot-check in an isolated disposable git worktree (e.g. `git worktree add ...`) or separate temporary branch: temporarily reverse individual source edits to confirm the corresponding test goes red, proving each fix is load-bearing. This diagnostic check is verification, not implementation.

6. **Determine Review Path (Standard vs. Independent Adversarial Review):**
   - Consult `# Ticket-specific review decision` in the plan and inspect the real diff:
     - **Standard Review:** For low-risk, self-contained, or routine changes. The orchestrator conducts the review directly against the plan's checklist, likely findings, and test suites.
     - **Independent Adversarial Review:** Triggered if mandated by the plan, or if the diff touches critical invariants (parsers, ranking rules, delete rails, server lifecycle), has unexpectedly high complexity, or underwent messy implementer iterations.
   - **Reviewer Selection:** The orchestrator owns this selection because it sees the real diff. Re-verify official provider documentation at dispatch time, then select and justify one exact model ID and native effort from the **Independent Review** row in [handoffs/README.md](../README.md#task-classes--recommended-mappings). Prefer a different model family from the implementer when available, but require a separate fresh context and read-only remit even when the same family is used. Record the requested and actual provider/model/effort plus any fallback.
   - **Adversarial Review Handoff:** Copy the exact text under `## Reusable Independent Adversarial Review Prompt`, substitute only its angle-bracket fields, and dispatch it to a fresh agent session with no planner or implementer conversation history. Configure a read-only sandbox or permission profile when the runtime supports one; the prompt's no-write constraint is mandatory regardless. If the active runtime cannot instantiate the selected model and effort, give that exact prompt to a human operator for manual cross-provider launch. Do not add an implementation narrative or other hand-written brief.

7. **Handle Review Findings & Legacy Plans:**
   - For plans using the modern template: evaluate the diff against `# Review checklist`, `## Likely findings`, and `## Mechanical inclusion test`.
   - For legacy migrated plans: evaluate against the plan's acceptance criteria, objective, and stated scope.
   - If defects or scope leaks exist, return precise findings to the implementer and require fixes on the **same implementation branch**. For an independent adversarial path, send the complete updated `base_sha...new_head_sha` diff back to the same independent reviewer, or a new fresh reviewer if that session cannot resume; do not replace the independent re-review with an orchestrator-only check.

8. **Escalate Stop Conditions:**
   - If the implementer hits a stop condition or if review reveals that architectural boundaries/plans must change, follow the escalation route: `implementer → orchestrator → planner`.
   - Do **NOT** attempt to re-plan or widen implementation scope yourself. Escalate to the **Planner** to amend or re-cut the plan in a revised plan PR.

9. **Carry Out Plan Review-Outcome Steps:**
   - When clean and verified, carry out all review-outcome steps specified in the plan (e.g. open a pull request targeting `main` referencing the issue, add any required coordination comments on issue threads, and ensure a dated [WORKLOG.md](../../WORKLOG.md) entry accompanies the PR).

## Reusable Independent Adversarial Review Prompt

Copy this prompt verbatim and replace only the angle-bracket fields:

```text
Act as the independent adversarial reviewer for issue #<N> in `tonym999/vault-cleaner`.

Canonical plan on `main`: <handoffs/issue-N-implementation-plan.md>
Implementation branch: <branch>
Immutable review range: <base_sha>...<head_sha>

Start from a fresh context. Read `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, the entire canonical plan, and all files relevant to the supplied diff before reaching conclusions. Treat the implementation and its reported test results as untrusted.

Review the complete `git diff <base_sha>...<head_sha>`, not only the latest commit or the implementer's summary. Verify that both SHAs exist and that the head descends from the base. Evaluate correctness, regressions, security and safety rails, the plan's mechanical inclusion test, stop conditions, review checklist, likely findings, negative-test coverage, and repository-specific invariants. Inspect the orchestrator's recorded command output and run additional read-only diagnostics when useful and permitted.

Remain read-only: do not edit files, commit, push, post comments, open a pull request, implement fixes, or re-plan the ticket. Return findings only to the orchestrator.

Output contract:
1. State the exact base and head SHAs reviewed.
2. List actionable findings first, ordered P0 through P3. Every finding must include a concise title, repository-relative file and line, impact, evidence or reproduction, and the required correction boundary.
3. If there are no actionable findings, say so explicitly.
4. List residual risks, assumptions, and any verification you could not run.
```
