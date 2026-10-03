# 2026-10-03 — #193 implementation: one worklog file per entry (PR 2)

Implemented #193 on `feat/issue-193-worklog-entry-files` from `main` at
`e2b3f8d3233d2983298629505fc84ffb64f8dd91`, following
`handoffs/issue-193-implementation-plan.md`. Refs #193.

This is the first entry file under `worklog/`. It is the new layout's own
entry, so it is not also added to the `WORKLOG.md` archive.

## Owner decisions (2026-10-03, asked in the planning session)

1. **Option 1 from the issue, one file per entry:**
   `worklog/YYYY-MM-DD-issue-N-<slug>.md`, with `WORKLOG.md` frozen as an
   archive behind a pointer at the top.
2. **"Recent" covers the 10 newest entries,** plus every entry for the
   ticket's own issue.

## Dispatch record

- **Orchestrator:** Anthropic `claude-opus-5-5` (Claude Code desktop
  session; the session does not report its native effort setting, so none is
  recorded).
- **Plan's implementer selection:** Anthropic `claude-sonnet-5-5`, effort
  `high`, Bounded rung (alternative; the plan passed over the Bounded primary
  `MAI-Code-1.1-Flash` after its context failures on #170 and #191).
- **Actual implementer:** Anthropic `claude-sonnet-5-5`, dispatched as a
  subagent of the orchestrator's Claude Code session. The subagent launch
  surface does not expose an effort setting, so the effort is the runtime
  default, not confirmed as `high`.
- **Re-selection:** none.
- **Review path selected by the plan:** standard orchestrator review (the
  orchestrator confirms it against the real diff).
- **Pre-dispatch checks:** `python3 scripts/check_model_roster.py` reported
  `7 models, 21 assignments, 0 stale`; issue #193 open, status `Todo`, no
  comments; no open pull requests; `worklog/` absent on `main`; the CI
  `WORKLOG entry present` step unchanged from the plan.

## What landed

- **N1** `scripts/check_worklog.py`: stdlib-only checker. Tree rules T1-T4
  always run (archive hash, `worklog/` is a directory with entries, names and
  dates, UTF-8 and first-line heading). With `--base REV` it also runs the
  pull-request rules P1-P3 over
  `git diff --name-status --no-renames -z REV...HEAD -- worklog`: at least
  one valid added entry, no deletions or renames, no edits to entries
  already on the base.
- **N2** `tests/test_worklog_check.py`: tests for every rule, including
  the negative cases the plan lists and an end-to-end class using real `git`
  in `tmp_path` repositories (not skipped when `git` is missing).
- **N3** this file.
- **E1-E7** `AGENTS.md`: references now point at `worklog/`, and a new
  `## Worklog` section defines the layout and "the recent worklog" once.
- **E8-E10** `handoffs/README.md`, `handoffs/templates/planner.md` and
  `handoffs/templates/orchestrator.md`: only the listed phrases changed; the
  three "recent `WORKLOG.md`" prompts now point at the `AGENTS.md`
  definition.
- **E11** `README.md`: session history link.
- **E12** `WORKLOG.md`: a four-line frozen-archive pointer after the title;
  nothing else touched.
- **E13** `.github/workflows/ci.yml`: the inline shell step is replaced by
  two steps running `scripts/check_worklog.py` (tree rules on pushes to
  `main`, tree plus pull-request rules on pull requests), with no `if:`
  condition that depends on labels, titles, paths or authors.

## Decisions made

- `ARCHIVE_SHA256` was computed from `WORKLOG.md` as it stands after E12
  (which already included the planning PR's entry from `main`), over bytes
  with `\r\n` replaced by `\n`. Any later deliberate change to the archive
  must update the constant in the same pull request.
- The name expression is the plan's, character for character, applied with
  `re.fullmatch` and `re.ASCII` so that `\d` cannot match non-ASCII digits
  and a trailing newline in a name cannot satisfy `$`.
- The first line is split on `\n` only, never `str.splitlines()`, so U+2028
  and similar separators cannot hide a heading problem; one trailing `\r` is
  stripped.
- T2 ("holds no entry file") fires when no regular file with a valid entry
  name exists, so a directory holding only `README.md` reports T2 and T3.
- A `--base` revision beginning with `-` is rejected before `git` is run, so
  a hostile value cannot be read as an option.
- `ruff format` was applied to the two new Python files only; the repository
  does not gate on formatting and existing files were left alone.

## Surprises the next agent should know about

- `git diff --name-status --no-renames` reports a rename as a delete plus an
  add, so P2 is what catches a rename; the P1 "added valid entry" test alone
  would pass it.
- The recent-worklog definition's fallback ("the first entries of
  `WORKLOG.md`" while `worklog/` holds fewer than 10) applies to this and the
  next nine entries.
- The old plans under `handoffs/issue-*-implementation-plan.md` still tell
  the implementer to update `WORKLOG.md`; that is left for #192, as the plan
  says.
