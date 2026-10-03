# Issue #188 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#188 — Fix stale facts in AGENTS.md, PLAN.md and handoffs/README.md`

**Milestone:** none (workflow documentation; no feature milestone fits, as for #141 and #144)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Anthropic, Claude Code session; the runtime does not expose a native effort setting for this session)

**Implementation model selected:** `MAI-Code-1.1-Flash` (`n/a — adaptive`) (Bounded rung; justified below)

**Plan baseline:** `main` at `1ab2eaed9c327e98fa8c8b169f9cc9b39a64f372` (2026-09-27); re-verified at `40c1c91372a8d3fc1b69e85c7089cc6eb705b5b8` (2026-10-02, after #181's PR #198) — see [Re-verification](#re-verification-after-181-merged-and-pr-197-review)

**Allocated implementation branch:** `fix/issue-188-stale-doc-facts`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Correct the facts in `AGENTS.md`, `PLAN.md`, `handoffs/README.md` and one
sibling `.gitignore` comment that no longer match the repository. Every role
reads these files as current truth at session start, so a stale line can
cause a wrong action. The edits are fully specified below as verbatim text;
nothing is left to the implementer's judgement except mechanical application.

No product code, tests, schemas, rules, config or versions change.

## Context & Measurement

All line numbers are at the plan baseline `1ab2eae`, except `AGENTS.md` lines, which are also given at `40c1c91` where #181 moved them.

### Facts listed in the issue, re-measured

| Id | Location | Stale text | Measured reality | Command |
|---|---|---|---|---|
| F1 | `handoffs/README.md:77` | "The 10 dangling remote `handoff/*` branches remain active on GitHub until this workflow PR merges to `main`." | The workflow PR merged long ago. There are 11 remote `handoff/*` branches: 10 belong to closed issues, 1 (`#181`) to an open issue, and none has an open PR. | `git fetch origin && git branch -r \| grep -c 'origin/handoff/'` |
| F2 | `handoffs/README.md:166` | #124's pilot "runs after this workflow is available from `main`". | #124 is `CLOSED`. The pilot ran on subject issue #119; its [outcome comment](https://github.com/tonym999/vault-cleaner/issues/124#issuecomment-5533463758) has sections *Acceptance criteria* and *Usability gaps found*. | `gh issue view 124 --json state` |
| F3 | `handoffs/README.md:184`, `:217`, `:230` | Opus is named `claude-opus-5` in the planner roster, the Independent Review row and the catalog. | The current Opus is `claude-opus-5-5`; `claude-opus-5` is listed under "Legacy models (still available)". See *Model verification* below. | `WebFetch` of the two Anthropic URLs below |
| F4 | `AGENTS.md:189-192` (`208-211` at `40c1c91`) | Rules modules: `weapons.py, dupes.py, armor.py, armor_dupes.py, armor_close.py, ghosts.py`. | `src/vault_cleaner/rules/` also holds `coverage.py` (docstring: "Weapon coverage rule pass (PLAN.md rule 4)"), `rails.py` ("Safety rails (PLAN.md rule 1)") and `id_order.py` ("Deterministic ordering for opaque DIM instance ids"). | `ls src/vault_cleaner/rules/ && head -1 src/vault_cleaner/rules/{coverage,rails,id_order}.py` |
| F5 | `PLAN.md:73` | `wishlists/  # cached downloads (gitignored or committed — TBD)` | `wishlists/` is gitignored (`.gitignore:5`), and no wishlist file is tracked. | `git check-ignore -v wishlists/ && git ls-files wishlists/` |
| F6 | `PLAN.md:62-78` | The repo layout lists 7 modules. | `src/vault_cleaner/` has 17 modules plus `rules/`, `server/` and `ui/`. The issue allows two fixes: a complete list, or a pointer to `src/vault_cleaner/`. E8 uses the pointer, because it cannot drift. Outside the tree, PLAN.md names a module only in the *M7 boundary* paragraph (`PLAN.md:35-40`: `pipeline.py` and `report_run.py`, plus "the CLI and the local review server" as presentation adapters), and that paragraph is unchanged. | `ls src/vault_cleaner/` |

### Sibling found during measurement

| Id | Location | Stale text | Why in scope |
|---|---|---|---|
| F7 | `.gitignore:4` | `# Cached wishlist downloads (committed-or-not still TBD, see PLAN.md)` | Same fact as F5, and it points at the PLAN.md line being corrected. `AGENTS.md` asks for sibling divergences to be fixed in the same change. |

### Added on owner approval (2026-09-27, before PR #197 merged)

| Id | Location | Stale text | Why in scope |
|---|---|---|---|
| F8 | `PLAN.md` *Milestones* (`PLAN.md:82-91`) | The numbered list stops at item 8 (M8). | PLAN.md has an *M9 duplicate presentation and review UX* section (`PLAN.md:103`), and GitHub milestone "M9 — Duplicate Review UX" holds 16 issues (11 closed). M9 is adopted; only the list is behind. M10 is not added: #137 and #138 have no milestone and PLAN.md has no M10 section. |

### Found in review of PR #197 (2026-10-02)

| Id | Location | Stale text | Measured reality | Source |
|---|---|---|---|---|
| F9 | `PLAN.md:174` (*Risks & mitigations*) | "The browser/server boundary still needs a contract … Specify them before implementation and bind mutations to the exact report revision/fingerprint." | The server is implemented. It validates each request strictly (`src/vault_cleaner/server/`). Verdict and finalize requests require `report_revision`, `verdict_revision` and `fingerprint` (`src/vault_cleaner/server/app.py:184-258`). Seven `tests/test_server_*.py` suites pin the schemas. The risk is durable; only "still needs" and "before implementation" are stale. | Owner review on PR #197 |
| F10 | `handoffs/README.md:184`, `:189`, `:204-206`, `:231` | Sonnet is named `claude-sonnet-5` (planner alternatives, all three ladder rungs, catalog). | `claude-sonnet-5-5` is the current Sonnet. It was not listed at this plan's first verification on 2026-09-27; Claude Sonnet 5 is listed under "Legacy models (still available)". See *Model verification*. | CodeRabbit on PR #197 |
| F11 | `PLAN.md:77` | `tests/  # fixture CSVs with fake items` | Since #181 (PR #198), `tests/fixtures/real/` holds sanitised real-export fixtures (`AGENTS.md`, *Hard rules* and *Conventions*). | Planner, found while checking F9 |

### Time-bound sweep

Command, run at the baseline:

```bash
grep -nEi '\buntil\b|\bTBD\b|not yet|will be|\bpending\b|\bcurrently\b|runs after|once (this|the)|this (workflow|PR)\b|for now|temporar|follow-up|\bsoon\b|next (PR|ticket)|remain active|\bstill\b|before implementation' AGENTS.md PLAN.md handoffs/README.md
```

`\bstill\b` and `before implementation` were added after the first version
missed F9. A keyword list is a heuristic, so `PLAN.md` *Non-goals* and *Risks
& mitigations* were also read in full; F9 is the only stale sentence there.
Every hit at `40c1c91` was classified. Only F1, F2, F5 and F9 are stale. The others are
durable and stay unchanged:

| Hit | Classification |
|---|---|
| `PLAN.md:91` "…produced in Python as an M8 follow-up" | Spec for open issue #38; accurate. |
| `PLAN.md:171` "dry-run mode default until `--write` is passed" | Behaviour, not time. |
| `PLAN.md:177` "out of scope for now" | Deliberate spec wording. |
| `AGENTS.md:55`, `:156` (`74`, `175` at `40c1c91`), `README.md:47`, `:147` "temporary" | Filesystem terminology. |
| `AGENTS.md:101` (`120` at `40c1c91`) "remain identity cells until a later measured boundary" | Rule semantics. |
| `AGENTS.md:177` (`196` at `40c1c91`) "must fail until the key is projected" | Test semantics. |
| `README.md:153` "follow-up reference" | Policy wording. |
| `README.md:164` "this workflow" | Durable reference to the current workflow. |
| `README.md:219` "currently `MAI-Code-1.1-Flash`" | Accurate; #191 restructures this table. |
| `PLAN.md:47` "dupes among matched rolls still resolve" | Rule semantics. |
| `PLAN.md:49` "coverage can still name as partner" | Known limitation #185 (open); accurate. |
| `PLAN.md:173` "cleanup of session state and temporary files" | Filesystem terminology. |
| `README.md:208` "may still be tried on work near the High-risk boundary" | Policy wording. |

### Model verification (F3)

Checked on 2026-09-27 against:

- [Anthropic Models overview](https://platform.claude.com/docs/en/models/overview): current Claude API IDs are `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5` and `claude-haiku-4-5-20251001`. "Legacy models (still available)" includes Claude Opus 5. Default effort: Fable 5.1 `high`, Opus 5.5 `medium`, Sonnet 5 `high`, Haiku 4.5 "Not supported".
- [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort): the parameter is `output_config.effort`. "Claude Opus 5.5 supports all five effort levels, and `medium` is the default (Claude Opus 5 and earlier Opus models default to `high` …)". `xhigh` and `max` are listed for Fable 5.1, Opus 5.5, Opus 5 and Sonnet 5.

So the existing Fable 5.1, Sonnet 5 and Haiku 4.5 catalog rows are correct
as written. The Opus 5 row is correct apart from its stability label. A
`claude-opus-5-5` row is missing, and its default differs (`medium`).

The owner's recent tickets already record `claude-opus-5-5` as planner and
orchestrator (#170, #174 and #181 in `WORKLOG.md`), so moving the roster to
`claude-opus-5-5` records actual practice rather than changing it.

**Re-checked on 2026-10-02 (F10).** The same two pages now list Claude Sonnet
5.5 as current: Claude API ID `claude-sonnet-5-5`, default effort `high`,
retirement "Not sooner than September 28, 2027". Claude Sonnet 5 has moved to
"Legacy models (still available)". The effort page lists `claude-sonnet-5-5`
among supported models, with `xhigh` and `max` both available, and says
"Claude Sonnet 5.5 supports all five effort levels, and `high` is the default
… Its levels are recalibrated, so a level doesn't produce the same amount of
thinking as the same level on Claude Sonnet 5." The Fable 5.1, Opus 5.5, Opus 5
and Haiku 4.5 facts above are unchanged.

The owner chose (2026-10-02) to swap the Sonnet IDs in the roster and ladder
and keep their effort levels. Implementer outcome notes will show whether the
recalibrated levels need adjusting; that is #191's or a later ticket's call.

### Re-verification after #181 merged and PR #197 review

#181's implementation (PR #198) merged to `main` at `40c1c91` after this plan
was opened. It changed `AGENTS.md` (+51/−19 lines across setup, hard rules
and conventions) but none of the other files this plan edits. Re-checked at
`40c1c91` on 2026-10-02:

- E7's old text is unchanged and still occurs exactly once; it moved from
  lines 189–192 to 208–211.
- The trial below, rerun against `40c1c91`, gives the same result.
- The time-bound sweep over the new `AGENTS.md` finds only the four durable
  hits already classified, at their new lines. #181 added no time-bound
  wording, but it did make `PLAN.md:77` false (F11).
- PR #197's review then found F9 and F10, which this revision adds as E11–E13
  and in a rewritten E8.

### Trial (planning session, discarded)

E1–E13 were applied mechanically, from this document's own old/new blocks, in
a detached worktree at `40c1c91`, then the worktree was discarded:

- every old text matched exactly once (E12: exactly five occurrences before
  the catalog heading);
- the diff was 4 files, +23/−26, with `git diff --check` clean;
- `git check-ignore wishlists/` still matched.

(The first version's E1–E10 trial ran at `1ab2eae` and at `40c1c91`.)

### Model selection

Rung: **Bounded.** Every edit is given verbatim below, with its exact
location; there is no design choice, no code and no test. Selected the
primary, `MAI-Code-1.1-Flash` (`n/a — adaptive`).

- On #170, MAI looped on context limits in the Copilot Windows app
  (`WORKLOG.md`, #170 implementation entry). This ticket is small, and the
  execution prompt below bounds reading to the newest entries of
  `WORKLOG.md`, which is the fix requested on #144 and used by the #181 plan.
  The run is a fair test of whether bounded reading resolves the loop.
- If the orchestrator re-selects, prefer `claude-sonnet-5-5` (`medium`) or
  `gpt-5.6-terra` (`medium`). Anthropic's guidance for Sonnet 5.5 is to "start
  with `medium` for well-specified tasks" in agentic coding, and this one is
  fully specified. Avoid `gemini-3.8-flash` for this ticket: its
  recorded collateral-edit incident (PR #160) was silently repointing
  Markdown citations, and this ticket consists entirely of Markdown edits
  next to citations.

The orchestrator verifies whether its runtime can instantiate MAI and
otherwise uses manual cross-provider execution from a local Copilot surface
(`handoffs/README.md`, *Manual Cross-Provider Execution (v1)*).

## Dependencies and assumptions

- **No blocking dependency.** #188 has no GitHub `blocked_by` links. It
  blocks #190 (doc-drift tests) and #191 (structured model roster).
- **#181 has merged** (PR #198, `40c1c91`). It edited `AGENTS.md` but did
  not overlap E7; it only shifted E7's lines (see *Re-verification after #181
  merged*). The implementer still locates every edit by its old text, never
  by line number alone, in case another PR lands first.
- **#191 will replace the model tables with a data file.** E3–E6, E12 and
  E13 are the minimum correction until then. Do not restructure the tables here.
- **Issue body divergence:** the issue said "11 remote `handoff/*` branches".
  That is still the count, but one of them is now #181's open plan branch
  rather than a finished one. The issue listed F1–F6; F7 was found during
  measurement and is added as a sibling, F8 was added on owner approval, and
  F9–F11 came from PR #197's review.
- **Out-of-scope observations** (recorded, not changed):
  - `PLAN.md` *Milestones* stopping at M8 was first recorded here as an
    owner decision; the owner approved correcting it, and it is now F8/E10.
  - Deleting the 10 closed-issue `handoff/*` branches is an external mutation
    that needs separate owner authorisation. It is not implementer work.
  - Historical plans and `WORKLOG.md` entries that name `claude-opus-5` or
    `claude-sonnet-5` are point-in-time records and stay unchanged.

## Proposed Plan & Scope

Each edit gives the exact old text and the exact new text. Match the old
text exactly (including backticks and em dashes) and replace it with the new
text exactly. Nothing else in these files changes.

### Workflow README

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L77) — E1 (F1)

Old line:

```text
- The 10 dangling remote `handoff/*` branches remain active on GitHub until this workflow PR merges to `main`. Deleting a `handoff/*` branch is a post-merge cleanup operation.
```

New line:

```text
- Deleting a `handoff/*` branch is a post-merge cleanup operation.
```

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L166) — E2 (F2)

Old paragraph (one line):

```text
The first complete real-issue pilot of this workflow is tracked in [#124](https://github.com/tonym999/vault-cleaner/issues/124). It runs after this workflow is available from `main`, because the orchestrator contract requires a merged plan rather than an unmerged integration-PR artifact.
```

New paragraph (one line):

```text
The first complete real-issue pilot of this workflow ran in [#124](https://github.com/tonym999/vault-cleaner/issues/124), on subject issue #119. Its [outcome comment](https://github.com/tonym999/vault-cleaner/issues/124#issuecomment-5533463758) records which acceptance criteria were met and the usability gaps found.
```

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L170) — E3 (F3)

Old line:

```text
*(Verified 2026-09-03; Microsoft row verified 2026-09-19)*
```

New line:

```text
*(Verified 2026-09-03; Microsoft row verified 2026-09-19; Anthropic rows verified 2026-10-02)*
```

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L184) — E4 (F3)

In the **Planner** roster row, replace exactly this fragment:

```text
Opus (`claude-opus-5`), `xhigh` effort for planning
```

with:

```text
Opus (`claude-opus-5-5`), `xhigh` effort for planning
```

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L217) — E5 (F3)

In the **Independent Review** row, replace exactly this fragment:

```text
`claude-opus-5` (`high`), `gpt-5.6-sol` (`high`)
```

with:

```text
`claude-opus-5-5` (`high`), `gpt-5.6-sol` (`high`)
```

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L230) — E6 (F3)

Replace the single `claude-opus-5` catalog row:

```text
| **Anthropic** | Claude | `claude-opus-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
```

with these two rows, in this order:

```text
| **Anthropic** | Claude | `claude-opus-5-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `medium`) | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
| **Anthropic** | Claude | `claude-opus-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Legacy, still available — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
```

### Agent guide

#### [MODIFY] [AGENTS.md](../AGENTS.md#L208-L211) — E7 (F4)

Old bullet:

```text
- Rules live in `src/vault_cleaner/rules/`, one module per pass
  (weapons.py, dupes.py, armor.py, armor_dupes.py, armor_close.py,
  ghosts.py — a new pass gets a new module); ordering is defined in
  PLAN.md and earlier rules win.
```

New bullet:

```text
- Rules live in `src/vault_cleaner/rules/`, one module per pass
  (weapons.py, dupes.py, coverage.py, armor.py, armor_dupes.py,
  armor_close.py, ghosts.py — a new pass gets a new module); rails.py
  implements rule 1's safety rails and id_order.py is a shared ordering
  helper. Ordering is defined in PLAN.md and earlier rules win.
```

### Spec

#### [MODIFY] [PLAN.md](../PLAN.md#L62-L78) — E8 (F5, F6, F11)

Old fenced block (inside the `## Repo layout` section):

```text
vault-cleaner/
├── src/vault_cleaner/
│   ├── parse.py          # DIM CSV ingestion, header-name mapping
│   ├── wishlist.py       # download, cache, parse wishlist files
│   ├── rules/            # one module per ordered rule pass
│   ├── pipeline.py       # reusable ordered weapons/armor pipelines
│   ├── report_run.py     # all-passes result + versioned snapshot/fingerprint
│   ├── report.py         # output CSV + human-readable summary
│   └── cli.py            # presentation and explicit --write boundary
├── wishlists/            # cached downloads (gitignored or committed — TBD)
├── data/                 # in/ and out/ — gitignored, personal vault data
├── config.toml
├── tests/                # fixture CSVs with fake items
└── PLAN.md               # this file
```

New fenced block:

```text
vault-cleaner/
├── src/vault_cleaner/    # the Python package
├── wishlists/            # cached downloads, gitignored
├── data/                 # in/ and out/ — gitignored, personal vault data
├── config.toml
├── tests/                # synthetic fixtures, plus sanitised real-export fixtures under fixtures/real/
└── PLAN.md               # this file
```

Nothing is inserted after the block; the existing line that begins
`Public repo;` stays where it is.

### Ignore file

#### [MODIFY] [.gitignore](../.gitignore#L4) — E9 (F7)

Old line:

```text
# Cached wishlist downloads (committed-or-not still TBD, see PLAN.md)
```

New line:

```text
# Cached wishlist downloads
```

Do not change any ignore pattern.

### Spec milestones

#### [MODIFY] [PLAN.md](../PLAN.md#L91) — E10 (F8)

Directly after the numbered item that begins
`8. **M8 — Local review server:**` (one long line), insert this line, with no
blank line between the two items:

```text
9. **M9 — Duplicate review UX:** authoritative duplicate comparison data and review UX; see *M9 duplicate presentation and review UX* below.
```

Change nothing in item 8 or the rest of the list.

### Spec risks

#### [MODIFY] [PLAN.md](../PLAN.md#L174) — E11 (F9)

Old bullet (one line):

```text
- **The browser/server boundary still needs a contract** — the server removes the duplicated manifest parser, but upload, report, verdict, session, and download schemas remain cross-runtime boundaries. Specify them before implementation and bind mutations to the exact report revision/fingerprint.
```

New bullet (one line):

```text
- **The browser/server boundary is a cross-runtime contract** — the server removed the duplicated manifest parser, but upload, report, verdict, session, and download schemas remain cross-runtime boundaries. The server validates each request strictly (`src/vault_cleaner/server/`), binds verdict and finalize mutations to the exact report revision and fingerprint, and the `tests/test_server_*.py` suites pin the schemas.
```

### Sonnet model ID

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L184-L206) — E12 (F10)

Above the `### Provider Catalog & Reasoning Controls` heading, the backticked
token below occurs exactly five times: once in the **Planner** roster row
(line 184), once at the start of the paragraph after the roster table
(line 189), and once in each of the three ladder rows (lines 204–206).
Replace all five with the new token, and change nothing else on those lines,
including the effort values in brackets after each token. Do not touch any
occurrence at or below the catalog heading; E13 handles the catalog.

Old token:

```text
`claude-sonnet-5`
```

New token:

```text
`claude-sonnet-5-5`
```

#### [MODIFY] [handoffs/README.md](../handoffs/README.md#L231) — E13 (F10)

Replace the single `claude-sonnet-5` catalog row:

```text
| **Anthropic** | Claude | `claude-sonnet-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
```

with these two rows, in this order:

```text
| **Anthropic** | Claude | `claude-sonnet-5-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`; levels recalibrated from Sonnet 5) | Stable — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
| **Anthropic** | Claude | `claude-sonnet-5` | `output_config.effort` | `low`, `medium`, `high`, `xhigh`, `max` (defaults to `high`) | Legacy, still available — [Anthropic Models](https://platform.claude.com/docs/en/models/overview), [Anthropic Effort](https://platform.claude.com/docs/en/build-with-claude/effort) |
```

### Worklog

#### [MODIFY] [WORKLOG.md](../WORKLOG.md) — W

Add a dated entry at the top, headed
`## YYYY-MM-DD — #188 implementation: stale workflow and plan facts (PR 2)`,
recording: the base SHA; the dispatch record supplied by the orchestrator;
that E1–E13 were applied verbatim (or any deviation and why); and the
verification output summary. Refs #188.

## Mechanical inclusion test

A hunk in `git diff <base_sha>...HEAD` is **in scope** if and only if it is:

- one of edits E1–E13, applied exactly as specified above; or
- the W `WORKLOG.md` entry.

Worked examples:

- **IN SCOPE:** replacing `claude-opus-5` with `claude-opus-5-5` in the Planner roster row (E4).
- **IN SCOPE:** inserting the `claude-opus-5-5` catalog row above the `claude-opus-5` row, and relabelling the latter (E6).
- **IN SCOPE:** replacing the five `claude-sonnet-5` tokens above the catalog heading (E12) and splitting the Sonnet catalog row into a 5.5 row and a legacy row (E13).
- **OUT OF SCOPE:** changing any effort value next to a swapped Sonnet ID, rewording any other roster, ladder or catalog cell, or restructuring the model tables (that is #191).
- **OUT OF SCOPE:** changing `claude-opus-5` in historical plans (`handoffs/issue-*.md`) or older `WORKLOG.md` entries.
- **IN SCOPE:** inserting item 9 (M9) after item 8 in `PLAN.md` *Milestones* (E10).
- **IN SCOPE:** replacing the browser/server risk bullet in `PLAN.md` *Risks & mitigations* (E11).
- **OUT OF SCOPE:** adding M10, rewording other milestone items or risk bullets, or any other PLAN.md spec edit.
- **OUT OF SCOPE:** reflowing, re-wrapping or "tidying" neighbouring lines, links or citations in any touched file.
- **OUT OF SCOPE:** deleting remote `handoff/*` branches or any other GitHub mutation.

### Stop conditions

Stop implementation and return to the orchestrator if:

- an edit's old text is not found exactly once in its file on the branch base (for example, another PR changed it first), or E12's token does not occur exactly five times above the catalog heading;
- applying an edit would require changing any text not shown in that edit;
- `ruff`, `pytest` or `git diff --check` fails for a reason not caused by this change.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Collateral Markdown edits.** Neighbouring lines, table cells or link targets reflowed or "improved" while applying an edit. Check the word diff for every changed line against E1–E13.
2. **Partial Opus replacement.** One of the three F3 locations missed, or the E6 row order or default (`medium` for `claude-opus-5-5`, `high` for `claude-opus-5`) swapped.
3. **Fence, table or list breakage.** E6 or E13 inserted without a leading `|` or with a blank line inside the table, the E8 fence damaged, or E10 separated from item 8 by a blank line. Render-check all three.
4. **Sonnet swap overreach or underreach.** E12 applied as a file-wide replace (which would also hit the catalog row and the new legacy row from E13), fewer than five tokens swapped, or an effort value changed next to a swapped ID.
5. **Worklog missing the dispatch record** that the orchestrator must verify before opening PR 2.

# Reusable implementer execution prompt

Implement issue #188 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-188-implementation-plan.md
```

Read the entire handoff, issue #188, `AGENTS.md`, and only the newest three entries at the top of `WORKLOG.md` (not the whole file) before editing. You do not need to read the rest of `PLAN.md` or any source code.

Rules:
- work on `fix/issue-188-stale-doc-facts`; branch from latest `main` and record the base SHA;
- apply edits E1–E13 exactly as written in the handoff, locating each by its old text, not by line number;
- change nothing else in any file; apply the plan's mechanical inclusion test to every hunk;
- update `WORKLOG.md` with the dated entry described in W, including the dispatch record you were given;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `git diff --check origin/main...HEAD`, `test -z "$(git ls-files data/)"`; the browser suite is not required because no UI file changes;
- commit and push the implementation branch, with `Refs #188` in every commit message; and
- **do not open a pull request.**

If any edit's old text is missing or appears more than once, or any stop condition is reached, stop and return to the orchestrator with the exact conflict; do not improvise replacement text.

When complete, report: branch, base SHA, head SHA, the list of edits applied (E1–E13 and W), any deviation, and the verification output.

# Ticket-specific review decision

**Review path:** `standard orchestrator review`

**Reason:**
Documentation-only change with verbatim text. It touches no parser, rule, rail, schema, server lifecycle or security boundary. The risk is collateral editing of neighbouring Markdown, which the orchestrator's word-diff audit against E1–E13 catches directly.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] `git diff --word-diff=plain <base_sha>...HEAD -- AGENTS.md PLAN.md handoffs/README.md .gitignore` shows exactly E1–E13 and nothing else.
- [ ] `git diff -U0 <base_sha>...HEAD -- WORKLOG.md` has exactly one `@@` hunk with no removed lines, placed after the preamble and before the base's first `## ` heading; inspect that hunk and confirm every added line belongs to the new top W entry.
- [ ] All three F3 locations now read `claude-opus-5-5`; the catalog has both Opus rows in the E6 order and defaults.
- [ ] Above the catalog heading, `claude-sonnet-5` appears only as `claude-sonnet-5-5` (five times) with unchanged effort values; the catalog has both Sonnet rows in the E13 order.
- [ ] The `handoffs/README.md` catalog table and the `PLAN.md` layout fence render correctly on GitHub.
- [ ] `PLAN.md` *Milestones* has item 9 (M9) directly after item 8, with no blank line between them.
- [ ] `grep -n 'TBD' PLAN.md .gitignore` returns nothing; `grep -n 'dangling\|It runs after' handoffs/README.md` returns nothing; `grep -n 'still needs a contract\|fake items' PLAN.md` returns nothing.
- [ ] Every link added in E2 resolves (the #124 issue and the outcome comment anchor).
- [ ] `WORKLOG.md` entry present, dated, with the dispatch record and `Refs #188`.
- [ ] `ruff`, `pytest -q`, `git diff --check` and `test -z "$(git ls-files data/)"` pass.

# Dispatch comment draft

Planned #188 in [handoffs/issue-188-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-188-implementation-plan.md) on `main`.

- **Implementer model & effort:** `MAI-Code-1.1-Flash` (`n/a — adaptive`); re-selection fallback `claude-sonnet-5-5` (`medium`), not Gemini (PR #160).
- **Implementation branch:** `fix/issue-188-stale-doc-facts`
- **Likely findings:** collateral Markdown edits beside E1–E13; a missed Opus location or swapped default; a file-wide or partial Sonnet swap (E12); table or fence breakage in E6/E8/E13, or a blank line before the E10 item; missing dispatch record in `WORKLOG.md`.

# Amendment — OpenAI model refresh (2026-10-03, owner-authorised direct route)

**Finding (F12):** the OpenAI roster, implementer ladder, independent-reviewer
mapping and provider catalog in `handoffs/README.md`, and the example model ID
in `handoffs/templates/planner.md`, named GPT-5.6, while OpenAI's current
lineup is `gpt-6-astra`, `gpt-6.1-sol` and `gpt-6-luna`. It was raised as a P2
on PR #199.

**Route:** the owner authorised applying the fix directly on the
implementation branch, as a documentation-only change, rather than through a
re-cut plan PR.

**Owner decisions (2026-10-03):**

- Map name for name: `gpt-5.6-sol` becomes `gpt-6.1-sol` and `gpt-5.6-luna`
  becomes `gpt-6-luna`, with effort levels unchanged.
- `gpt-5.6-terra` on the Bounded rung is replaced by `gpt-6-luna` (`medium`).
- `gpt-6-astra` is catalog-only; no roster or ladder row uses it.
- The three GPT-5.6 catalog rows stay, relabelled as previous generation.

**Verification (2026-10-03):** the orchestrator checked
https://developers.openai.com/api/docs/guides/latest-model,
https://developers.openai.com/api/docs/models, the per-model pages for
`gpt-6-astra`, `gpt-6.1-sol` and `gpt-6-luna`, and
https://developers.openai.com/api/docs/deprecations. The deprecations page has
no GPT-5.6 entry, the models page no longer lists GPT-5.6 Sol, Terra or Luna,
and the GPT-6 lineup has no Terra.

**Edits:**

- E14: `handoffs/README.md` verification line gains "OpenAI rows verified 2026-10-03".
- E15: `gpt-5.6-sol` becomes `gpt-6.1-sol` in the four roster, ladder and reviewer locations above the catalog heading.
- E16: `gpt-5.6-luna` becomes `gpt-6-luna` in the two ladder primaries above the catalog heading.
- E17: the Bounded ladder fallback `gpt-5.6-terra` (`medium`) becomes `gpt-6-luna` (`medium`).
- E18: the three GPT-5.6 catalog rows become three GPT-6 rows plus the same three GPT-5.6 rows relabelled "Previous generation, no deprecation listed".
- E19: `handoffs/templates/planner.md` example ID `gpt-5.6-luna` becomes `gpt-6-luna`.

The mechanical inclusion test is extended to "E1–E19, P, and the two worklog
entries W and W2", where P is this section. Historical plans and `WORKLOG.md`
entries that name GPT-5.6 are point-in-time records and stay unchanged.

**Supersession (fix round 2, 2026-10-03):** this amendment supersedes the edit
and worklog lists in `# Reusable implementer execution prompt` and
`# Review checklist` above. Those sections are kept as dispatched for the
original E1–E13 round. Wherever they say "E1–E13", read "E1–E19 and P";
wherever they say "W" or expect one worklog entry, read "the worklog entries
W, W2 and W3". W3 is the fix-round-2 worklog entry that records this
paragraph, and the mechanical inclusion test covers both.

# Amendment 2 — roster policy (2026-10-03, owner-directed)

These are policy changes directed by the owner in PR #199. They go beyond
#188's original "do not change workflow policy, roles or authorisation gates"
scope line, and the owner explicitly authorised making them in this PR.

**Owner decisions (2026-10-03):**

1. Planner effort is `high` by default and `xhigh` when the ticket needs it;
   the Sonnet planner alternative is `high`.
2. The Judgement and High-risk implementer rungs follow the planner row:
   primary Sol or Opus at `high` (`xhigh` when needed), alternatives Sonnet
   (`high`) and Gemini Pro (`high`). `gpt-6-luna` stays only as a
   Bounded-rung alternative. The orchestrator's recorded reason: OpenAI
   describes GPT-6 Luna as its most efficient model for focused, high-volume
   tasks, and no ticket in this repository has used it on a higher rung.
3. `claude-fable-5-1` fills no role. It already has a catalog row and appears
   in no roster, ladder or reviewer row, so no edit is needed.

**Edits:**

- E20: `handoffs/README.md` Planner row says `high` effort by default and `xhigh` when needed, with the Sonnet alternative at `high`.
- E21: `handoffs/README.md` paragraph after the roster table gives Sonnet as `high`.
- E22: `handoffs/README.md` Judgement ladder row: primary `gpt-6.1-sol` or `claude-opus-5-5` (`high`; `xhigh` when needed); alternatives Sonnet and Gemini Pro at `high`.
- E23: `handoffs/README.md` High-risk ladder row: same primary and alternatives as E22.
- E24: `AGENTS.md` roster summary sentence names MAI for the Bounded rung, then Sol or Opus for Judgement and High-risk.
- E25: `handoffs/templates/planner.md` example becomes `gpt-6.1-sol` with `high` effort.

The mechanical inclusion test and the supersession note above now read:
edits E1–E25, the plan sections P, S and P2, and the worklog entries W, W2,
W3 and W4. Wherever an earlier section of this plan gives a shorter list,
this one replaces it.
