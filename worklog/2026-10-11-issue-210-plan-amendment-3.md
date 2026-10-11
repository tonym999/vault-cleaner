# 2026-10-11 — #210 plan Amendment 3: raise the minimum Python version to 3.14

A planner commit on `feat/issue-210-armor-duplicates-redesign` that touches
only `handoffs/issue-210-implementation-plan.md` and this entry. It follows
`ef0f599`, which is open as PR #212. Refs #210.

## Why

A third review comment by OpenAI Codex, on the PR at the owner's request,
found one P2:
<https://github.com/tonym999/vault-cleaner/pull/212#issuecomment-6106496939>.
`spikes/issue-210/proof_layout.py:149` uses `Path.read_text(newline="")`,
which exists from Python 3.13; the project declares 3.12. It recommended
raising the baseline to 3.14 in this PR.

## Owner decision (2026-10-11)

Raise the baseline to 3.14 in this PR, and write this amendment.

**The planner advised against doing it here**, and the owner decided
otherwise. Recorded so the next reader knows it was weighed:

- The finding has a one-line fix that stays inside the spike.
- The baseline is a project-wide declaration, unrelated to a UI redesign,
  in a PR that is already 81 files.
- For it: the local environment is already 3.14, all tests pass there, and
  it is one merge, not two.

## Measured while writing it

- `.venv/bin/python` is 3.14.4. Every check and proof in this ticket ran on
  it, so the 3.12 incompatibility could not show. CI does not run the spike
  proofs.
- Four declarations of the baseline: `pyproject.toml:7`, `ci.yml:59` and
  `ci.yml:74`, `AGENTS.md:44`, `PLAN.md:59`. `git grep` finds no other
  current one.
- The `hygiene` job has no `setup-python` step and runs its scripts on the
  runner's own `python3`. The amendment adds the step, which the review
  comment did not ask for.
- `ruff check src tests scripts --target-version py314` reports nothing.
  There is no `[tool.ruff]` section, so ruff will take the new target from
  `requires-python`.

## What the amendment does

- Lists the exact edits to the four files and widens the inclusion test for
  those edits only.
- Leaves `proof_layout.py:149` alone: on 3.14 it is correct.
- Forbids touching the dependency rule that shares a line with the version
  in `AGENTS.md` and `PLAN.md`, any pin, and any historical record.
- **Makes CI on the pushed head the gate**, because whether the pinned
  toolchain installs on 3.14 on Windows was not measured and cannot be from
  here. A failure there is a stop condition, not a reason to change a pin.
- Adds a likely finding and two checklist items.

## Also in this session, outside the amendment

- The PR body was changed to close #210 on merge, at the owner's request.
- **The PR body had linked #152 for closing by accident.** Its follow-ups
  list said to close that issue, and GitHub reads a closing keyword next to
  an issue reference wherever it appears. It was reworded before any merge,
  and GitHub now lists only #210. `AGENTS.md` warns about this for commit
  messages; a to-do list in a PR body is the same trap.
- `gh pr edit` fails in this repository on a Projects-classic GraphQL
  error. The body was changed with `gh api -X PATCH`.

## Correction before approval

The amendment as first committed (`eb74763`) said the `hygiene` job runs
four scripts. It runs three, one of them in two steps. A second planner
commit corrects that wording in the plan and nothing else, so the SHA to
approve is the later one.

## Not done

- Nothing in the amendment is implemented. It needs the owner's approval by
  SHA.
- CI on Python 3.14 has not run.
