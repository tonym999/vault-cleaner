# 2026-10-03 — #195: plans are canonical at an approved SHA, one PR per ticket

Changed the handoff lifecycle from two PRs to one on
`docs/issue-195-plan-first-commit`, from `main` at
`5fd9ca547db6cd505ec068f3ab7336235966127f`. Refs #195.

## Owner decisions (2026-10-03, asked in this session)

1. **Option 3 from the issue:** the plan is the first commit of the ticket's
   one branch and one PR. The owner approves the plan at a commit SHA before
   implementation begins.
2. **Route:** direct single PR under the documentation/maintenance exception,
   explicitly authorised for this issue. No handoff document was written.
3. **Mutations authorised:** push this branch and open its PR. Merging and
   commenting on the issue were not authorised.

## What changed

- `AGENTS.md`, *User authorization gates*: "Plan a ticket" now cuts and pushes
  the allocated branch and opens no PR. "Merge a planning PR" became "Approve
  a plan", which names the plan SHA and does not authorise implementation.
- `AGENTS.md`, *Workflow*: one branch and one PR per ticket; the orchestrator
  reads the plan with `git show <plan_sha>:…`, never from a branch tip.
- `handoffs/README.md`: the lifecycle section is rewritten, with a new
  subsection *Plan SHA, immutability and amendments*. The
  `handoff/issue-N-implementation-plan` branch convention is retired.
- `handoffs/templates/orchestrator.md`: step 1 reads the plan at the approved
  SHA and stops when no approval names one. Step 4 and step 9 check that the
  plan file at the head is identical to the plan SHA. The reviewer prompt
  takes a `<plan_sha>` field.
- `handoffs/templates/planner.md`: the implementer prompt and the dispatch
  comment draft cite the plan by `<plan_sha>`; the implementer works on the
  existing branch and never edits the plan file.

## Decisions

- **Approval by SHA replaces the merge as the gate.** A merge gave both
  immutability and an explicit owner action; a SHA gives only the first, so
  the gate is stated separately.
- **The implementer can write to the branch that holds the plan.** The guard
  is `git diff --quiet <plan_sha> <head_sha> -- handoffs/issue-N-implementation-plan.md`,
  run by the orchestrator before review and before opening the PR, and
  reported on by the independent reviewer.
- **No PR opens at planning time.** The owner reviews the pushed plan commit.
  This keeps "P0/P1 blocks PR creation" and "the implementer never opens a
  PR" true as written. A draft PR for plan review would be a further change.
- **CI is unchanged.** No CI step encoded the two-PR rule; measured with
  `git grep` over `.github/` and `scripts/`.

## For the next agent

- Measured on `main` at the base above: no open pull requests, and no plan
  under `handoffs/` belongs to an open issue, so nothing is mid-flight under
  the old lifecycle.
- The issue's acceptance criterion says "`WORKLOG.md` entry"; since #193 that
  means an entry file under `worklog/`.
- The repository merges with merge commits, so a plan SHA stays reachable
  from `main` after the ticket's PR merges. A squash merge would drop it.
- Issue bodies still describe the old lifecycle and were not edited: #141
  ("requires the canonical plan merged to main", "Preserve the two-PR
  lifecycle"), #144 ("two-PR lifecycle … remain intact") and #192. #192's
  historical marker is simpler now, because a plan reaches `main` only with
  its implementation.
- At the first push the owner's decision was not yet on #195. The owner
  recorded it there on 2026-10-03 (see *Review round 1*), which is the
  issue's first acceptance criterion.

## Review round 1 (PR #204, reviewed head `703bff6`)

Three findings; all accepted.

- **P2, owner: plan ancestry was checked only before dispatch.** The content
  check passes after a rebase drops the approved commit but keeps the plan's
  bytes. `git merge-base --is-ancestor <plan_sha> <head_sha>` now runs beside
  the content check before review and before opening the PR, and is in the
  reviewer prompt. CodeRabbit raised the same finding.
- **P2, owner: the review base moved with each attempt.** A redispatch after
  an amendment recorded a new base, so `base_sha...head_sha` lost the earlier
  implementation. The review base is now fixed at the ticket's first dispatch
  and kept by the orchestrator; the implementer records only its own
  attempt's starting SHA.
- **Minor, CodeRabbit: the worklog treated the decision as recorded.** The
  owner has since commented the decision on #195; the bullet above is
  corrected.

This PR still uses `Refs #195`; whether merging it should close the issue is
the owner's call.
