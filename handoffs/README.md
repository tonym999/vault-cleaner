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

Roles are defined by function, not by model. Which model fills each role is
recorded per ticket (see [Role → Model Roster](#role--model-roster)); the
responsibilities and constraints below are the same whichever model fills the
role.

1. **Planner**
   - **Responsibility:** Researches an open issue, measures current code state, resolves any staleness in the issue body, designs the solution, allocates branch names, and authors the implementation handoff document using [handoffs/templates/planner.md](templates/planner.md).
   - **Model Selection:** The owner chooses the planner and orchestrator models per ticket from the roster; the plan records the planner model. The plan selects and justifies the *implementer's* model and native reasoning effort, plus the recommended review path; it does not select the adversarial reviewer's model.

2. **Orchestrator**
   - **Responsibility:** Operates from `main` using [handoffs/templates/orchestrator.md](templates/orchestrator.md). Reads the merged plan from `main`, dispatches the implementer at the plan's selected model and effort (or re-selects it under [Implementer Re-selection](#implementer-re-selection)), resolves discrepancies that stay within the existing plan contract, determines the final review path after inspecting the real diff, selects and dispatches an independent reviewer when required, routes findings, and, when authorized, carries out the plan's review-outcome steps (opening the implementation PR, adding coordination comments).
   - **Constraint:** Never writes production code or implements tickets directly. Does not change scope, the mechanical inclusion test, or stop conditions; those go back to the planner.

3. **Implementer**
   - **Responsibility:** Executes the handoff instructions on the allocated branch (`fix/issue-N-...` or `feat/issue-N-...`). Follows the plan's mechanical inclusion test, adds tests, updates [WORKLOG.md](../WORKLOG.md) and documentation, verifies with tests and linters, and reports results back to the orchestrator.
   - **Constraint:** Does not open pull requests, widen implementation scope, or approve its own work. Approval belongs to the orchestrator's review and, on an independent path, the independent reviewer.

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
   - Once its merge and the coordination action are authorized, the planner posts a dispatch comment on the issue thread with the plan's path on `main`, the implementer model & effort, allocated branch name, and likely findings.

2. **Implementation Phase (PR 2):**
   - The orchestrator reads the merged plan from `main` (`handoffs/issue-N-implementation-plan.md`).
   - Dispatches the implementer to work on the allocated implementation branch.
   - Chooses the final review path after inspecting the real diff, conducts the standard review or dispatches an independent adversarial reviewer, and routes accepted, in-scope findings back to the implementer.
   - Once reviewed and verified, the orchestrator opens PR 2 targeting `main` and executes any required issue comments only when those external mutations are authorized; the PR includes a dated [WORKLOG.md](../WORKLOG.md) entry.

## Naming Convention

All plan files stored in this directory follow the standard format:

```text
handoffs/issue-N-implementation-plan.md
```

- Filenames must **never** include role names (e.g. `luna`) or model/effort labels (e.g. `xhigh`).
- Branch names for plans follow `handoff/issue-N-implementation-plan`.
- Implementation branches follow `fix/issue-N-...` or `feat/issue-N-...` as allocated in the plan.
- Deleting a `handoff/*` branch is a post-merge cleanup operation.

## Stop-Condition Escalation Routing

If an edge case, breaking change, or scope conflict occurs during implementation:

```text
implementer → orchestrator → planner
```

1. **Implementer:** Stops work immediately when a plan stop condition is triggered and reports the exact conflict to the orchestrator without attempting to widen scope.
2. **Orchestrator:** Evaluates whether the issue can be resolved within the existing plan contract. If non-trivial plan changes or scope alterations are required, the orchestrator escalates to the **Planner** rather than re-cutting the plan or broadening implementation scope.
3. **Planner:** Re-evaluates the codebase, amends or re-cuts the plan, and submits a revised plan PR.

Escalation always goes to the orchestrator for this ticket, whichever model
fills that role, never to a named model.

### Implementation judgement vs. material uncertainty

Every implementer is expected to exercise ordinary engineering judgement.
Stop conditions are for material uncertainty, not for every decision.

- **Decide and continue:** local structure, naming, helper extraction, test
  shape, following an established pattern to a new location, fixing ordinary
  failures the implementer's own change caused, and choosing between
  equivalent approaches that keep the plan's invariants and scope intact.
  Explain notable choices in the completion handoff.
- **Stop and return to the orchestrator:** the change fails the mechanical
  inclusion test; a plan stop condition triggers; the plan's stated invariants
  or approach look wrong against the actual code; a meaningful design choice
  the plan did not settle; or materially more design reasoning is needed than
  the plan anticipated. Do not silently redesign the solution because the work
  proved harder than expected.

Within the existing plan contract, the orchestrator may clarify instructions,
let the same implementer continue, reassign the work to another implementer
(see [Implementer Re-selection](#implementer-re-selection)), or propose
splitting work into a new issue. Reassignment is not a re-plan. Changes to
scope, the inclusion test, or stop conditions go to the planner; architectural
questions go to the owner.

## Implementer Re-selection

The plan's implementer selection is a recommendation, not a fixed floor. The
orchestrator may change the implementer model or effort in either direction on
the [implementer ladder](#implementer-ladder), before dispatch or after a
stopped or failed attempt, when inspection or the attempt shows materially
different complexity, judgement, or risk than the plan expected. It records the
plan's selection, the actual model and effort, and a one-line reason in the
dispatch record and the `WORKLOG.md` entry. Re-selection never changes scope.

## Implementer Outcome Notes

The normal plan → implement → review loop is how the project learns each
implementer's capability boundary; no separate benchmark is required before a
roster model is used on real tickets. When the outcome is notable, the
orchestrator's `WORKLOG.md` entry adds one line saying so, for example: clean
completion; misread the plan; expanded scope; needed substantial reviewer
correction; stopped at a stop condition; reassigned to another implementer;
handled work previously assumed to need a higher rung. Changes to the roster or
ladder should cite these notes, as the Gemini fix-prompt guardrail cites PR
#160.

## Review Path: Standard vs. Independent Adversarial Review

The review path adapts review rigor to the risk and complexity of the change:

- **Standard Orchestrator Review:** Default path for self-contained, low-risk, or routine changes. The orchestrator conducts the review directly against the plan's checklist, likely findings, and test suites.
- **Independent Adversarial Review:** Triggered when prescribed by `# Ticket-specific review decision` in the plan, or when the orchestrator determines the real diff touches critical invariants (parsers, ranking rules, delete rails, server lifecycle), presents unexpected complexity, or involved difficult implementer iterations.
- **Reviewer Selection:** The orchestrator owns reviewer selection because it sees the real diff. At dispatch time it selects and justifies one exact model ID and native effort from the `reviewer` assignments in [`handoffs/models.toml`](models.toml) under the [Independent Review Mapping](#independent-review-mapping), re-verifying that model's row first when it is stale (see [Re-verification](#re-verification)), and records the actual provider/model/effort and any fallback. A different model family from the implementer is preferred when available, but independence requires a separate fresh context and read-only remit rather than a different provider. The same rule holds when the reviewer model matches the orchestrator's (for example, Opus orchestrating and Opus reviewing): a fresh session with a read-only remit is sufficient. The implementer's own session never reviews or approves its work.
- **Execution via Fresh Context:** The orchestrator creates a detached disposable checkout pinned to the recorded head SHA, copies the reusable adversarial-review prompt from [handoffs/templates/orchestrator.md](templates/orchestrator.md), substitutes only its declared fields, and hands both to a fresh agent session with no planner or implementer conversation history. The reviewer may write only ephemeral verification artifacts in that checkout or its assigned temporary directory and never edits tracked implementation or durable repository state. It independently reruns applicable checks, explicitly treats a skipped required browser suite as a failure, and labels any command it could not run rather than silently trusting the orchestrator's output. Findings are returned to the orchestrator, who routes fixes back to the implementer before PR creation and sends the complete updated diff back to an independent reviewer for re-review.

### Finding Severity, Blocking, and Disposition

- **P0 — Critical:** Exploitable security exposure, data loss, or catastrophic safety/correctness failure. Blocks PR creation.
- **P1 — High:** Material correctness, security, contract, or regression defect. Blocks PR creation.
- **P2 — Medium:** Meaningful defect or verification/coverage gap. Normally blocks; deferral requires explicit human-owner approval, recorded rationale, and a follow-up reference when work remains.
- **P3 — Low:** Worthwhile non-blocking improvement. Advisory unless elevated by the orchestrator or owner.

The orchestrator records one disposition for every finding: `accepted/fixed`, `rejected` with contrary evidence, or `deferred` under the rule above. Reviewer conclusions are not automatically authoritative. Unresolved P0/P1 disagreements go to the human owner, and also to the planner when resolution would alter the canonical plan or scope. Accepted fixes on an independent-review path require a new complete-diff independent review at the updated immutable head.

## Manual Cross-Provider Execution (v1)

For every implementer or independent-reviewer dispatch, the orchestrator records the requested provider, exact model ID, and native effort, then checks whether its active runtime can instantiate that target. If it cannot, the orchestrator prepares the exact role prompt and a human operator launches the external agent. An external implementer returns its branch, base and head SHAs, test output, and completion handoff; an external reviewer returns the fixed findings report for the supplied immutable SHAs. The orchestrator treats every external result as untrusted. Any scope deviation follows `implementer → orchestrator → planner`. Automated provider discovery, authentication, launching, and monitoring are deferred to a separate issue.

The dispatch record captures the orchestrator's own exact model ID and native effort, the **actual** implementer provider/model/effort used, the launch surface for externally launched agents (for example GitHub Copilot in VS Code, or Copilot CLI), and any fallback or re-selection taken. When a model has no user-settable effort, record `n/a — adaptive` rather than guessing a level. The model data file, [`handoffs/models.toml`](models.toml), is selection guidance; it does not itself make that provider available to the active runtime.

For implementation dispatch specifically, when the selected target's row in [`handoffs/models.toml`](models.toml) lists `launch_surfaces`, use manual cross-provider execution only if the active runtime cannot instantiate it. Launch it from one of those local agent surfaces, working on the allocated branch, so it commits and pushes only that branch. Do not dispatch implementation to the Copilot cloud agent in this workflow: entry points differ, but the repository policy is absolute and the implementer must never open a pull request.

The first complete real-issue pilot of this workflow ran in [#124](https://github.com/tonym999/vault-cleaner/issues/124), on subject issue #119. Its [outcome comment](https://github.com/tonym999/vault-cleaner/issues/124#issuecomment-5533463758) records which acceptance criteria were met and the usability gaps found.

## Model Family & Provider-Native Reasoning-Effort Matrix

Which models fill each role, and each model's provider, exact ID, native
effort control, allowed effort values, verification date and sources, live in
one data file: [`handoffs/models.toml`](models.toml). So do per-model
operational facts, such as the surfaces a model must be launched from. This
section holds the selection policy. Name a model ID in prose only as an
example; never copy the roster or catalog into another document.

`python3 scripts/check_model_roster.py` validates the file's schema and
cross-references and warns about stale rows. CI runs it on every push and
pull request; a stale row is a warning, not a failure.

### Re-verification

Each `[[models]]` row carries its own `verified` date and `sources`.
Re-verify a row against its sources when it is past the file's
`stale_after_days` threshold, or when a dispatch to that model fails or is
rejected, and update its `verified` date (and any fact that changed) in the
same change. A re-verified row is in scope for whichever plan or
implementation change relies on it. Do not rely on a stale row without
re-verifying it.

State support per model rather than assuming uniform provider support. Do
not assume equivalent effort names (for example OpenAI `xhigh`, Anthropic
`xhigh`, Gemini `high`) produce identical reasoning behavior.

### Role → Model Roster

One set of templates serves every combination in the data file. Record the
model filling each role in the plan (planner, implementer) and the dispatch
record (orchestrator, actual implementer, reviewer); do not create
model-specific workflows.

| Role | Models | Chosen by |
|---|---|---|
| **Planner** | `role = "planner"` assignments. `primary` models are the regular choices, and either may plan any ticket; neither is assumed. `alternative` models remain permitted. Use the assignment's `effort` by default and its `effort_when_needed` when the ticket needs it. | Owner, per ticket and availability |
| **Orchestrator** | `role = "orchestrator"` assignments. The same model, and often the same session driver, may plan and orchestrate one ticket; the roles stay separate. | Owner, per ticket and availability |
| **Implementer** | `role = "implementer"` assignments for the selected [implementer ladder](#implementer-ladder) rung. | Plan selects; orchestrator may re-select |
| **Independent reviewer** | `role = "reviewer"` assignments; see [Independent Review Mapping](#independent-review-mapping). | Orchestrator, at dispatch, after seeing the real diff |

The primary planner models are first-class for planning and orchestration;
this does not claim they are interchangeable for every task.

### Implementer Ladder

Choose the rung by how much ambiguity, engineering judgement, and risk the
plan delegates to the implementer, not by file count or change size. A
multi-file change is not by itself a reason to climb. The orchestrator may
deliberately assign work near a rung's perceived upper edge to learn where it
lies; the review gate makes that acceptable.

Each rung's primary and alternative models are the `role = "implementer"`
assignments with that `rung` value in [`handoffs/models.toml`](models.toml).

| Rung | `rung` value | The plan delegates… | Typical work (examples, not limits) |
|---|---|---|---|
| **Bounded** | `bounded` | a well-defined outcome and scope; architecture and important invariants are already decided in the plan | small and medium well-specified bug fixes; bounded features; localized multi-file changes; mechanical refactors following an established pattern; tests for defined behaviour; lint/type/test fixes; presentation work with clear acceptance criteria; repetitive edits across known locations; bounded exploration followed by bounded implementation |
| **Judgement** | `judgement` | substantial engineering judgement or resolution of real ambiguity | meaningful choices between alternative designs; inferring intended behaviour across several components; significant but bounded refactoring decisions; ambiguity the plan could not settle; work a Bounded attempt showed to exceed that rung |
| **High-risk** | `high-risk` | substantial reasoning responsibility or risk inside the implementation itself | persistence and data integrity; concurrency and races; stale-state reconciliation; lifecycle and state machines (e.g. server lifecycle); transactional or destructive operations; complex cross-file invariants; debugging with no established cause; potentially architectural refactors; several interacting failure modes at once |

The Bounded rung may still be tried on work near the High-risk boundary when
the plan has made the implementation effectively mechanical. When a Bounded
attempt stops or fails, the orchestrator may re-select a higher rung under
[Implementer Re-selection](#implementer-re-selection).

### Independent Review Mapping

When the independent-review path is used, the orchestrator selects one
`role = "reviewer"` assignment from [`handoffs/models.toml`](models.toml) for
a fresh reviewer session, at that assignment's effort, to review the
implementation diff against the plan's checklist and likely findings.
Standard review is conducted by the orchestrator itself and uses no reviewer
assignment.

Prefer a model from a different family than the implementer; any listed model
is allowed in a fresh read-only session.

A model with no `reviewer` assignment, such as an implementer-only model, is
not an independent review option.

### Provider Catalog & Reasoning Controls

The `[[models]]` rows in [`handoffs/models.toml`](models.toml) are the
catalog: provider, family, exact model ID, native reasoning control, allowed
effort values and default, support notes, launch surfaces where they are
restricted, stability, `verified` date and sources. A row exists only while
some assignment uses it; the checker rejects
an unused row. For a model whose `effort_control` is `adaptive`, record the
effort as `n/a — adaptive` rather than guessing a level.
