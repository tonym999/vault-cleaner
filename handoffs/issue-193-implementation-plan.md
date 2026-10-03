# Issue #193 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#193 — Restructure WORKLOG.md: define "recent" and stop append conflicts`

**Milestone:** none (workflow maintenance; no feature milestone fits, as for #188 and #191)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Anthropic, Claude Code desktop session; the session does not report its native effort setting, so none is recorded)

**Implementation model selected:** `claude-sonnet-5-5` with `high` effort (Bounded rung; justified below)

**Plan baseline:** `main` at `52739968e7f0fa333fda2a8dfe97ceb6e0e7c544` (2026-10-03, after #191's PR #201)

**Allocated implementation branch:** `feat/issue-193-worklog-entry-files`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Replace the single prepend-only `WORKLOG.md` with one file per entry under
`worklog/`, so concurrent branches stop conflicting, and give "the recent
worklog" one precise definition that the planner, implementer and reviewer
prompts all use. `WORKLOG.md` stays in place, unchanged apart from a pointer
at the top, as a frozen archive. A stdlib-only checker,
`scripts/check_worklog.py`, replaces the inline CI shell step and keeps the
rule that every pull request adds a worklog entry, with no escape hatch.

No product code (`src/`), rules, config, schemas or runtime dependencies
change.

### Owner decisions (2026-10-03)

The issue asked the owner to choose before implementation. The owner chose,
in the planning session:

1. **Option 1, one file per entry:** `worklog/YYYY-MM-DD-issue-N-<slug>.md`;
   `WORKLOG.md` frozen as an archive with a pointer at the top.
2. **"Recent" covers the 10 newest entries**, plus every entry for the
   ticket's own issue.

The implementation's worklog entry must record both (acceptance criterion 1).
Recording them on the issue itself is in the dispatch comment draft.

## Context & Measurement

All line numbers are at the plan baseline `5273996`. The planning PR adds one
entry to `WORKLOG.md` after line 5, so `WORKLOG.md` line numbers above 5
shift; no other file listed here changes.

### Size and shape of the worklog

| Fact | Value | Command |
|---|---|---|
| Lines | 7,893 | `wc -l WORKLOG.md` |
| Entries (`## ` headings) | 142 | `grep -c '^## ' WORKLOG.md` |
| Headings not starting `## YYYY-MM-DD ` | 0 | `grep -n '^## ' WORKLOG.md \| grep -Ev '^[0-9]+:## [0-9]{4}-[0-9]{2}-[0-9]{2} '` |
| Headings naming no issue (`#N`) | 4 (`:2141`, `:2166`, `:7857`, `:7874`) | `grep -n '^## ' WORKLOG.md \| grep -v '#[0-9]'` |
| Most entries on one date | 10 (2026-08-31); 7 on 2026-10-03 | `grep -o '^## [0-9-]*' WORKLOG.md \| sort \| uniq -c \| sort -rn \| head` |

The issue body's 6,874 lines and 132 entries were measured at `66589da`; the
file has grown by 1,019 lines and 10 entries in the six days since.

The newest 10 entries (`WORKLOG.md:6-1344`) cover #174, #181, #188 and #191,
so N = 10 reaches back about three tickets at the current pace.

### Every place that names the worklog

`grep -rn -i 'worklog'` over tracked files, excluding `WORKLOG.md` itself and
the historical `handoffs/issue-*-implementation-plan.md` files:

| Location | Role | Action |
|---|---|---|
| `.github/workflows/ci.yml:35-44` | The CI check: inline shell requiring an added `## YYYY-MM-DD — ` line in `WORKLOG.md`. | Replace (E13) |
| `AGENTS.md:4`, `:19`, `:53`, `:281`, `:286`, `:291` | Agent guide references. | Edit (E1–E6) |
| `AGENTS.md:20`, `:23`, `:230` | Say "the worklog" / "worklog entry" generically. | Unchanged; still correct |
| `handoffs/README.md:42`, `:56`, `:64`, `:126`, `:133` | Workflow README references. | Edit (E8) |
| `handoffs/templates/planner.md:16`, `:132`, `:137` | "recent `WORKLOG.md`" twice; the implementer rule. | Edit (E9) |
| `handoffs/templates/orchestrator.md:20`, `:88`, `:89`, `:105` | Dispatch record; review outcome; "recent `WORKLOG.md`" in the reviewer prompt. | Edit (E10) |
| `README.md:8` | "Session history" link. | Edit (E11) |
| `docs/evidence/issue-142/README.md:534`, `docs/aggressive-clearout-measurement.md:7`, `:724`, `:784`, `:785` | Historical statements that a decision "is recorded in `WORKLOG.md`". | Unchanged: they stay true, because the archive keeps those entries |
| `src/vault_cleaner/rules/ghosts.py:7` | Comment: "see WORKLOG 2026-07-19". | Unchanged, for the same reason |

"Recent" is undefined in exactly three places: `handoffs/templates/planner.md:16`,
`:132` and `handoffs/templates/orchestrator.md:105`
(`grep -rn 'recent' handoffs/templates`).

### Git plumbing trial (planning session, discarded)

A throwaway repository confirmed the diff behaviour the checker relies on:

- `git diff --name-status --no-renames -z BASE...HEAD -- worklog WORKLOG.md`
  reports a renamed entry as `D old` plus `A new`. Without `--no-renames` it
  is one `R100` row. So a rename looks like an added file unless deletions
  are rejected too; rule P2 below does that.
- With `main` moved on after the branch point, the three-dot range still
  lists only the branch's own changes.
- `git diff --unified=0 BASE...HEAD -- WORKLOG.md` exposes a newly added
  `+## YYYY-MM-DD ` heading line (rule P3).

### Model selection

The work is Bounded: the layout, file format, definition text, checker rules
and every edit are fixed below. Run `python3 scripts/check_model_roster.py`
before dispatch; at the baseline it reports `0 stale`.

The Bounded primary is `MAI-Code-1.1-Flash`. This plan selects the Bounded
alternative `claude-sonnet-5-5` (`high`) instead. The two most recent MAI
attempts lost their place to context compaction or looping (#170, noted at
`WORKLOG.md:1354-1355`, and #191, recorded at `WORKLOG.md:17-31`), and both
involved reading the worklog this ticket restructures. Sonnet was the
implementer that then delivered #191. The orchestrator may re-select under
[Implementer Re-selection](README.md#implementer-re-selection).

## Dependencies and assumptions

- **No blocking dependency.** #193 is open, labelled `maintenance`, status
  `Todo`, with no milestone and no comments at planning time. No pull
  request was open at planning time.
- **Staleness against the issue body:** the size figures are out of date
  (above). The three "recent" citations are still exact. Option 1's text is
  followed as written, with these details settled by this plan:
  - Entries with no issue omit the `issue-N-` part. Four archived headings
    name no issue, so the case is real, though rare.
  - "The last N files by name" is deterministic but not chronological within
    one day: names sort by date, then issue number as text, then slug. That
    is accepted. The definition needs every role to read the same set, not a
    strict timeline.
  - While `worklog/` holds fewer than 10 entries, the newest archived entries
    make up the difference. Without this, the first tickets after the change
    would read almost nothing.
  - Entries for an issue that predate the change are found by a heading
    `grep` in the archive.
- **The definition lives in `AGENTS.md`,** in a new `## Worklog` section,
  because every role loads that file. The templates point at it and do not
  restate it. There is no `worklog/README.md`: every file in `worklog/` is an
  entry, which keeps "the last 10 files by name" literal.
- **Existing entries are not migrated** into files. The owner chose a frozen
  archive; splitting 142 entries would rewrite history for no reader benefit.
- **In-flight branches:** a branch cut before this lands that adds a
  `WORKLOG.md` entry will fail the new check after it merges `main`. The
  error message tells its author to move the entry to a file. That is
  intended.
- **Neighbouring issues, none blocking:**
  - #194 (promote-or-discard step) edits `handoffs/templates/orchestrator.md`
    step 9 and builds on this layout. Do not add its step here.
  - #144 edits both templates; #196 slims `AGENTS.md`; #190 adds doc-drift
    tests; #189 single-sources the verification gate. Whichever lands second
    rebases. None of their scope belongs in this change.
  - #192 marks merged plans as historical. This plan leaves the old plans'
    "update `WORKLOG.md`" lines alone for that reason.
- **This planning PR** still adds its entry to `WORKLOG.md`, because the old
  CI check is in force until the implementation merges.

## Proposed Plan & Scope

Three new files (N1–N3), thirteen edits (E1–E13). Text in the fenced blocks
is verbatim. For the phrase replacements, each old phrase occurs exactly once
on the cited line unless stated; if it does not, stop.

### Layout and format (the contract the other parts implement)

- **Entry file name:** `worklog/YYYY-MM-DD-issue-N-<slug>.md`, or
  `worklog/YYYY-MM-DD-<slug>.md` when the work has no issue. Regular
  expression, matched against the whole file name:

  ```text
  ^(\d{4}-\d{2}-\d{2})-(?:issue-[1-9]\d*-)?[a-z0-9]+(?:-[a-z0-9]+)*\.md$
  ```

  The date must be a real calendar date. `worklog/` is flat: no
  subdirectories and no other files.
- **First line:** `# YYYY-MM-DD — <title>` (em dash U+2014 with one space
  each side, non-empty title), with the same date as the file name. Regular
  expression: `^# (\d{4}-\d{2}-\d{2}) — \S.*$`. The rest of the file is free
  Markdown.
- **Archive:** `WORKLOG.md` stays at the repository root.

### Checker

#### [NEW] [scripts/check_worklog.py](../scripts/check_worklog.py) — N1

Stdlib-only, runnable with a bare `python3`, in the style of
[scripts/check_model_roster.py](../scripts/check_model_roster.py): module
docstring, `from __future__ import annotations`, `REPO` constant, pure
validation functions returning a list of error strings, and
`main(argv: list[str] | None = None) -> int`.

```text
python3 scripts/check_worklog.py [--base REV] [--root PATH]
```

`--root` defaults to the repository root and exists for tests. Every error is
reported, not just the first; each is printed to stderr as
`error: <message>`. Exit status is 0 with no errors and 1 otherwise,
including when `git` fails or `REV` does not resolve.

Rules that always run (tree rules):

| Rule | Fails when |
|---|---|
| T1 | `WORKLOG.md` is missing from the root. |
| T2 | `worklog/` is missing, is not a directory, or holds no entry file. |
| T3 | Anything in `worklog/` is not a regular file (a subdirectory or symlink), or its name does not match the name expression, or its date is not a real date. |
| T4 | An entry is not valid UTF-8, or its first line does not match the heading expression, or the heading date differs from the name date. |

Rules that run only with `--base REV` (pull-request rules), over
`git diff --name-status --no-renames -z REV...HEAD -- worklog WORKLOG.md`:

| Rule | Fails when |
|---|---|
| P1 | No path with status `A` under `worklog/` is an entry that passes T3 and T4. The message must say that `WORKLOG.md` is a frozen archive and name `AGENTS.md`, *Worklog*. |
| P2 | Any path under `worklog/` has status `D`, or `WORKLOG.md` has status `D`. (With `--no-renames` this also covers renames.) |
| P3 | `git diff --unified=0 REV...HEAD -- WORKLOG.md` adds a line matching `^\+## \d{4}-\d{2}-\d{2} `. The message says to put the entry in a file under `worklog/`. |

Requirements that are easy to get wrong:

- Read entry files as bytes and decode as UTF-8 explicitly; pass
  `encoding="utf-8"` for `git` output. Never rely on the locale encoding
  (#45).
- Strip one trailing `\r` from the first line before matching, so a Windows
  checkout with `core.autocrlf=true` passes.
- Parse the `-z` output as NUL-separated `status, path` pairs. Git prints
  paths with `/` on every platform.
- Run `git` with `cwd` set to the root. Keep the `git` calls in one or two
  thin functions, so the rules can be tested with supplied change lists.

#### [NEW] [tests/test_worklog_check.py](../tests/test_worklog_check.py) — N2

Load the script with `importlib` as
[tests/test_model_roster.py](../tests/test_model_roster.py#L18-L26) does.
Build every tree under `tmp_path`; write files with explicit UTF-8 bytes and
`\n`. Required cases:

- **Tree, passing:** a root with `WORKLOG.md` and two valid entries (one with
  `issue-N`, one without) has no errors. The real repository passes the tree
  rules.
- **T1, T2:** missing `WORKLOG.md`; missing `worklog/`; empty `worklog/`.
- **T3, parametrized:** `README.md`; `2026-10-04-Issue-193-x.md`;
  `2026-10-04-issue-0-x.md`; `2026-10-04-issue-193-.md`;
  `2026-10-04-issue-193-x.txt`; `2026-10-04--x.md`; `2026-02-30-x.md`;
  `26-10-04-x.md`; a subdirectory.
- **T4, parametrized:** empty file; `## 2026-10-04 — x` (wrong level);
  `# 2026-10-04 - x` (hyphen); `# 2026-10-04 —` (no title);
  heading date different from the name date; invalid UTF-8 bytes. A first
  line ending `\r\n` passes.
- **P1:** no changes; only a modified existing entry; only an added file with
  an invalid name; only an added `WORKLOG.md` heading. Each fails. One added
  valid entry passes.
- **P2:** a deleted entry fails even when another valid entry is added (the
  rename case); a deleted `WORKLOG.md` fails.
- **P3:** an added dated `## ` heading in `WORKLOG.md` fails even when a
  valid entry is also added. An added line that is not a dated heading (the
  archive pointer) passes.
- **End to end with real `git`:** in a `tmp_path` repository
  (`git init -b main`, commits made with
  `-c user.name=… -c user.email=… -c commit.gpgsign=false`), a branch that
  changes only an unrelated file makes `main(["--base", "main", "--root", …])`
  return 1; after committing a valid entry it returns 0. A `--base` that does
  not resolve returns 1. Do not skip this test when `git` is missing; it must
  fail.

#### [NEW] `worklog/<date>-issue-193-implementation.md` — N3

The implementation's own entry and the first file in `worklog/`. `<date>` is
the implementation session's date. First line
`# <date> — #193 implementation: one worklog file per entry (PR 2)`. It
records the two owner decisions above, the dispatch record, what landed, and
anything surprising.

### Agent guide

#### [MODIFY] [AGENTS.md](../AGENTS.md#L3-L4) — E1

Old (`:4`): `[WORKLOG.md](WORKLOG.md) is what has actually happened so far.`

New: `the worklog ([worklog/](worklog/), see *Worklog*) is what has actually happened so far.`

#### [MODIFY] [AGENTS.md](../AGENTS.md#L18-L19) — E2

Old (`:18-19`):

```text
line-ending errors reported by `git diff --check`, and pull requests without
a `WORKLOG.md` entry.
```

New:

```text
line-ending errors reported by `git diff --check`, and pull requests that do
not add a worklog entry file (`scripts/check_worklog.py`; see *Worklog*).
```

#### [MODIFY] [AGENTS.md](../AGENTS.md#L53) — E3

Old: ``record each measurement in `WORKLOG.md`.``
New: `record each measurement in the worklog.`

#### [MODIFY] [AGENTS.md](../AGENTS.md#L281) — E4

Old: `Appends a dated entry to [WORKLOG.md](WORKLOG.md) (recording`
New: `Adds a dated worklog entry file under [worklog/](worklog/) (recording`

#### [MODIFY] [AGENTS.md](../AGENTS.md#L286) — E5

Old: `updates [WORKLOG.md](WORKLOG.md) (recording`
New: `adds a worklog entry file under [worklog/](worklog/) (recording`

#### [MODIFY] [AGENTS.md](../AGENTS.md#L291) — E6

Old: `the next agent should know in [WORKLOG.md](WORKLOG.md).`
New: `the next agent should know in a worklog entry file (see *Worklog*).`

#### [MODIFY] [AGENTS.md](../AGENTS.md#L214) — E7

Insert this section immediately before the `## Workflow` heading (`:214`),
followed by one blank line:

````markdown
## Worklog

The worklog records what each working session did, the decisions made, and
anything surprising the next agent should know. It has two parts:

- **Entry files** under `worklog/`, one per working session, named
  `YYYY-MM-DD-issue-N-<slug>.md`. The slug is lowercase words joined by
  hyphens that name the phase, for example `planning`, `implementation` or
  `fix-round-2`. Leave out `issue-N-` only when the work has no issue. The
  first line is `# YYYY-MM-DD — <title>` with the same date.
- **The archive,** `WORKLOG.md`: every entry from before #193, newest first.
  It is frozen. Never add an entry to it.

Every pull request adds at least one entry file; CI
(`scripts/check_worklog.py`) rejects one that does not. A later session on
the same pull request, such as a fix round, adds another file or extends one
that pull request added. Do not rename or delete an entry that is already on
`main`; put a correction in a new entry.

**The recent worklog** for a ticket on issue #N means exactly these, and
every role reads all of them:

1. The 10 entry files whose names sort last:
   `ls worklog | LC_ALL=C sort | tail -n 10`. While `worklog/` holds fewer
   than 10, make up the difference with the first entries of `WORKLOG.md`.
2. Every entry file for the issue: `ls worklog/*-issue-N-*.md`.
3. Every archived entry whose heading names the issue:
   `grep -nE '^## .*#N([^0-9]|$)' WORKLOG.md`, each read from that heading
   to the next `## ` heading.

Names sort by date, then issue, then slug, so the order within one day is
not chronological.
````

### Workflow README and templates

#### [MODIFY] [handoffs/README.md](README.md) — E8

| Line | Old | New |
|---|---|---|
| `:42` | `updates [WORKLOG.md](../WORKLOG.md) and documentation,` | `adds a worklog entry file under [worklog/](../worklog/), updates documentation,` |
| `:56` | `Appends a dated entry to [WORKLOG.md](../WORKLOG.md) recording` | `Adds a dated worklog entry file under [worklog/](../worklog/) recording` |
| `:64` | `the PR includes a dated [WORKLOG.md](../WORKLOG.md) entry.` | `the PR includes a dated entry file under [worklog/](../worklog/).` |
| `:126` | ``the `WORKLOG.md` entry.`` | `the worklog entry.` |
| `:133` | ``orchestrator's `WORKLOG.md` entry adds`` | `orchestrator's worklog entry adds` |

#### [MODIFY] [handoffs/templates/planner.md](templates/planner.md) — E9

| Line | Old | New |
|---|---|---|
| `:16` | ``recent `WORKLOG.md`,`` | ``the recent worklog (defined in `AGENTS.md`, *Worklog*),`` |
| `:132` | ``recent `WORKLOG.md`,`` | ``the recent worklog (defined in `AGENTS.md`, *Worklog*),`` |
| `:137` | ``update `WORKLOG.md` with a dated entry;`` | ``add a dated worklog entry file under `worklog/` (format in `AGENTS.md`, *Worklog*);`` |

#### [MODIFY] [handoffs/templates/orchestrator.md](templates/orchestrator.md) — E10

| Line | Old | New |
|---|---|---|
| `:20` | ``in its `WORKLOG.md` entry;`` | `in its worklog entry;` |
| `:88` | `ensure a dated [WORKLOG.md](../../WORKLOG.md) entry accompanies the PR` | `ensure a dated entry file under [worklog/](../../worklog/) accompanies the PR` |
| `:89` | ``in its `WORKLOG.md` entry and`` | `in its worklog entry and` |
| `:89` | ``The `WORKLOG.md` entry records`` | `The worklog entry records` |
| `:105` | ``recent `WORKLOG.md`,`` | ``the recent worklog (defined in `AGENTS.md`, *Worklog*),`` |

`:105` is inside the reviewer prompt, which is copied verbatim; change only
that phrase.

### Project README, archive and CI

#### [MODIFY] [README.md](../README.md#L8) — E11

Old: `**Session history:** [WORKLOG.md](WORKLOG.md) ·`
New: `**Session history:** [worklog/](worklog/) (archive: [WORKLOG.md](WORKLOG.md)) ·`

If the new line is longer than its neighbours, leave it; do not re-wrap the
paragraph.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md#L1-L2) — E12

Insert after line 1 (`# Worklog`) and its blank line, before
`Newest first.`; add nothing else and remove nothing:

```markdown
> **Frozen archive (#193).** New entries are one file each under
> [`worklog/`](worklog/); see `AGENTS.md`, *Worklog*. Do not add entries
> here. Everything below is unchanged history.

```

`git diff --numstat origin/main...HEAD -- WORKLOG.md` must show 4 added and 0
deleted lines.

#### [MODIFY] [.github/workflows/ci.yml](../.github/workflows/ci.yml#L35-L44) — E13

Replace the `WORKLOG entry present` step (`:35-44`) with:

```yaml
      - name: Worklog entry files are well formed
        if: github.event_name != 'pull_request'
        run: python3 scripts/check_worklog.py
      - name: Pull request adds a worklog entry file
        if: github.event_name == 'pull_request'
        env:
          BASE: ${{ github.base_ref }}
        run: python3 scripts/check_worklog.py --base "origin/$BASE"
```

The job already checks out with `fetch-depth: 0` (`:17`). No `if:` condition
may depend on labels, titles, paths or authors: there is no escape hatch.

## Mechanical inclusion test

A proposed change is **in scope** if and only if it is one of:

- N1, N2 or N3 as specified;
- one of E1–E13, changing only the stated text;
- a `ruff` or test fix inside N1 or N2 caused by the implementer's own code.

Worked examples:

- **IN SCOPE:** a helper in N1 that parses the `-z` output into pairs.
- **IN SCOPE:** an extra negative test in N2 for a rule in the tables above.
- **OUT OF SCOPE:** splitting `WORKLOG.md` entries into files, or editing,
  re-wrapping or deleting any existing line of it.
- **OUT OF SCOPE:** editing a historical `handoffs/issue-*-implementation-plan.md`,
  anything under `docs/`, or `src/vault_cleaner/rules/ghosts.py:7`.
- **OUT OF SCOPE:** a `worklog/README.md`, an index file, or a script mode
  that lists the recent worklog.
- **OUT OF SCOPE:** #194's promote-or-discard step, or any other wording
  change to the templates beyond E9 and E10.
- **OUT OF SCOPE:** a new rule beyond T1–T4 and P1–P3, such as rejecting
  edits to existing entries.

### Stop conditions

Stop implementation and return to orchestrator if:

- an old phrase in E1–E13 does not occur exactly once where stated, other
  than a pure line-number shift;
- another worklog reference exists in `AGENTS.md`, `README.md`,
  `handoffs/README.md`, `handoffs/templates/` or `.github/` that this plan
  does not list;
- `worklog/` already exists on `main`, or the CI worklog step has changed;
- the checker cannot meet a rule with the standard library and `git` alone;
- the end-to-end `git` test cannot be made to pass on Windows or Linux
  without skipping it;
- any rule or the definition text looks wrong against the real repository.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Leftover instructions to write `WORKLOG.md`:** an edit missed or half
   applied, so a role is still told to append to the archive. After the
   change, `grep -rn 'WORKLOG.md' AGENTS.md README.md handoffs/README.md handoffs/templates .github`
   must match only the `## Worklog` section of `AGENTS.md` and `README.md:8`.
2. **P1 passes for the wrong reason:** a rename, a modified existing entry,
   or an added file with a bad name satisfies the check; or a test passes
   with the rule removed. Spot-check by reverting P1 and P2 in turn.
3. **Platform encoding and line endings:** the checker reads with the locale
   encoding or fails on `\r\n`, so it passes on Linux and fails in the
   Windows test job (#45's class of defect).
4. **Scope leak:** archive entries reformatted or moved, extra documents in
   `worklog/`, or template wording changed beyond the listed phrases.

# Reusable implementer execution prompt

Implement issue #193 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-193-implementation-plan.md
```

Read the entire handoff, issue #193, `AGENTS.md`, `PLAN.md`, the newest 10 entries of `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-193-worklog-entry-files`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every hunk;
- do not add an entry to `WORKLOG.md`; write the worklog entry as the new file N3, including the dispatch record the orchestrator gives you and both owner decisions;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `python3 scripts/check_worklog.py --base origin/main`, `git diff --numstat origin/main...HEAD -- WORKLOG.md`, `git diff --check origin/main...HEAD`;
- commit and push the implementation branch, with `Refs #193` in every commit message; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, provide the implementer → orchestrator handoff: branch, base and head SHAs, the files changed against N1–N3 and E1–E13, the full output of each verification command, notable decisions, and anything surprising.

# Ticket-specific review decision

**Review path:** `standard orchestrator review`

**Reason:**
The change is workflow documentation, one stdlib-only CI script and its
tests. It touches no parser, ranking rule, delete rail, server lifecycle or
product code, and every edit is specified verbatim. The one invariant at
risk, that every pull request must add a worklog entry, is covered by
required negative tests and a revert spot-check in the checklist.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] Every hunk in `git diff base_sha...HEAD` maps to N1–N3 or E1–E13; no
      other file changed.
- [ ] `git diff --numstat base_sha...HEAD -- WORKLOG.md` shows 4 added, 0
      deleted.
- [ ] `worklog/` holds exactly one file, N3, and it records both owner
      decisions and the complete dispatch record.
- [ ] The `## Worklog` section in `AGENTS.md` matches E7 verbatim, and its
      three commands run as written (substituting an issue number).
- [ ] Likely finding 1's `grep` matches only the allowed locations, and
      `grep -rn 'recent' handoffs/templates` shows the new phrase three times.
- [ ] `ruff`, `pytest -q` and `git diff --check` pass;
      `python3 scripts/check_worklog.py --base origin/main` exits 0 on the
      branch.
- [ ] Demonstrated failing case: in a disposable checkout of `main` after
      E13 would apply, or on a scratch branch without N3,
      `python3 scripts/check_worklog.py --base origin/main` exits 1 with the
      P1 message.
- [ ] Revert spot-check: removing P1, then P2, each makes at least one test
      in N2 fail.
- [ ] N1 imports only the standard library, decodes UTF-8 explicitly, and
      tolerates `\r\n`; the end-to-end `git` test is not skipped.
- [ ] The CI steps in E13 have no escape-hatch condition, and the
      pull-request run on PR 2 itself is green on both test platforms.
- [ ] Likely findings 2–4 checked against the real diff.

# Dispatch comment draft

Planned #193 in [handoffs/issue-193-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-193-implementation-plan.md) on `main`.

- **Owner decisions (2026-10-03):** option 1, one file per entry under `worklog/` with `WORKLOG.md` frozen as an archive; "recent" is the 10 newest entries plus every entry for the ticket's issue.
- **Implementer model & effort:** `claude-sonnet-5-5`, `high` (Bounded rung)
- **Implementation branch:** `feat/issue-193-worklog-entry-files`
- **Likely findings:** leftover instructions to write `WORKLOG.md`; the pull-request rule passing on a rename or modified entry; locale encoding or CRLF handling in the checker; scope leak into the archive or templates.
