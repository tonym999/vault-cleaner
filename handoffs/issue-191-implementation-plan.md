# Issue #191 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#191 — Move the model roster and provider catalog to structured data with per-row verification dates`

**Milestone:** none (workflow maintenance; no feature milestone fits, as for #141, #144 and #188)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Anthropic, Claude Code cloud session; the runtime does not expose a native effort setting for this session)

**Implementation model selected:** `MAI-Code-1.1-Flash` (`n/a — adaptive`) (Bounded rung; justified below)

**Plan baseline:** `main` at `fa98e8ef737bd4f4f228f0859637877f6f0546a2` (2026-10-03, after #188's PR #199)

**Allocated implementation branch:** `feat/issue-191-model-roster-data`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Move the model roster, implementer ladder models, reviewer mapping and
provider catalog out of the prose tables in `handoffs/README.md` into one data
file, `handoffs/models.toml`, where every catalog row carries its own
`verified` date and sources. A stdlib-only checker,
`scripts/check_model_roster.py`, validates the file's schema and
cross-references, and warns (without failing) about rows older than a
threshold. CI runs it. `handoffs/README.md` keeps the selection policy in
prose and points at the data file; the planner and orchestrator templates
and `AGENTS.md` point at it too. The "re-verify the whole table before every
ticket" rule becomes "re-verify a row when it is stale, or when a dispatch to
it fails or is rejected".

No product code (`src/`), rules, config, schemas or runtime dependencies
change.

## Context & Measurement

All line numbers are at the plan baseline `fa98e8e`.

### Where model data lives today

| Location | Content | Command |
|---|---|---|
| `handoffs/README.md:168-244` | `## Model Family & Provider-Native Reasoning-Effort Matrix` to end of file: verification-date line (`:170`), the re-verify-before-every-ticket rule (`:172-173`), Role → Model Roster table (`:182-187`) and paragraph (`:189-192`), Implementer Ladder table (`:202-206`), Independent Review Mapping (`:215-223`), Provider Catalog (`:227-244`, 16 rows). | `sed -n 168,244p handoffs/README.md` |
| `handoffs/README.md:146` | Reviewer selection: "At dispatch time it re-verifies official model availability, selects … from the current **Independent Review** mapping below". | `grep -n 're-verifies official' handoffs/README.md` |
| `handoffs/README.md:162` | "A repository model table is selection guidance; …" | `grep -n 'repository model table' handoffs/README.md` |
| `handoffs/templates/planner.md:29` | "Consult the role roster, implementer ladder, and provider catalog in [handoffs/README.md](…)". | `sed -n 29p handoffs/templates/planner.md` |
| `handoffs/templates/orchestrator.md:19` | Implementer dispatch and re-selection; nothing about re-verification after a failed dispatch. | `sed -n 19p handoffs/templates/orchestrator.md` |
| `handoffs/templates/orchestrator.md:51` | "Re-verify official provider documentation at dispatch time, then select … from the **Independent Review** row in [handoffs/README.md](…)". | `sed -n 51p handoffs/templates/orchestrator.md` |
| `AGENTS.md:291` | Prose copy of the roster: "Sol and Opus are the regular planner/orchestrator choices, Sonnet and Gemini remain permitted planner alternatives, and the primary implementer ladder is MAI-Code-1.1-Flash for the Bounded rung, then Sol or Opus …". | `sed -n 291p AGENTS.md` |

`grep -rnE 'gpt-|claude-|gemini-|MAI-Code' AGENTS.md handoffs/README.md handoffs/templates/`
at the baseline finds model IDs at `AGENTS.md:291` and in the template and
README lines above, plus three that stay (see *Model IDs left in prose*).

### Which catalog rows are used

The roster, ladder and reviewer tables (`handoffs/README.md:184-185`,
`:204-206`, `:217`) use exactly seven model IDs:

| Model ID | Roles that use it |
|---|---|
| `gpt-6.1-sol` | planner (regular), orchestrator, implementer Judgement and High-risk (primary), reviewer |
| `claude-opus-5-5` | planner (regular), orchestrator, implementer Judgement and High-risk (primary), reviewer |
| `claude-sonnet-5-5` | planner (alternative), implementer all three rungs (alternative) |
| `gemini-3.1-pro-preview` | planner (alternative), implementer Judgement and High-risk (alternative), reviewer |
| `gpt-6-luna` | implementer Bounded (alternative) |
| `gemini-3.8-flash` | implementer Bounded (alternative) |
| `MAI-Code-1.1-Flash` | implementer Bounded (primary) |

The other nine catalog rows are used by no role and are removed:
`gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`,
`claude-fable-5-1`, `claude-opus-5`, `claude-sonnet-5`,
`claude-haiku-4-5-20251001` and `gemini-3.5-flash-lite`.

### Per-row verification dates

`handoffs/README.md:170` reads: "*(Verified 2026-09-03; Microsoft row verified
2026-09-19; Anthropic rows verified 2026-10-02; OpenAI rows verified
2026-10-03)*". The data file carries those dates per row, unchanged:
OpenAI 2026-10-03 (#188 fix round 1), Anthropic 2026-10-02 (#188 review-fix
round 1), Microsoft 2026-09-19, Google 2026-09-03.

The planner tried to re-verify the Google rows on 2026-10-03, but
`ai.google.dev` is blocked by this session's egress proxy. The Google rows
therefore keep 2026-09-03. With a 30-day threshold they become stale on
2026-10-04, so the first CI run of the implementation will very likely show
the stale-row warning on real data. That is correct behaviour, not a defect:
nobody has verified those rows since 2026-09-03. The implementer must **not**
change any `verified` date (see *Stop conditions*).

### Trial (planning session, discarded)

1. `handoffs/models.toml` exactly as given in N1 below was parsed with
   `tomllib` (Python 3.11 in this session). It has 7 models and 21
   assignments. Every assignment's model exists, every effort and
   `effort_when_needed` is in its model's `effort_values` (or is
   `n/a — adaptive` for the adaptive model), `rung` is present exactly on
   implementer rows, `effort` is absent only on orchestrator rows, no
   `(role, rung, model)` repeats, every role and rung has a primary, every
   `default_effort` is allowed, every source is `https://`, and the set of
   assigned models equals the set of catalog IDs.
2. `tomllib` returns `datetime.date` for `verified = 2026-10-03`, and also
   returns a `datetime.datetime` (a **subclass** of `date`) for
   `verified = 2026-10-03T00:00:00`. A plain `isinstance(value, date)` check
   therefore accepts datetimes; the checker must reject them explicitly.
3. E1–E8 below were applied mechanically from this document's old/new blocks
   in a detached worktree at `fa98e8e`; each old text matched exactly once
   (see *Trial results* at the end of *Proposed Plan & Scope*). The worktree
   was discarded.

### Model selection

Rung: **Bounded.** The plan fixes the data file verbatim, every prose edit
verbatim, the checker's schema rules, its message and exit-code contract and
its CI step, and lists every test case. What remains is writing a ~200-line
stdlib validator and its tests to that specification, which is bounded
implementation, not design. Selected the primary, `MAI-Code-1.1-Flash`
(`n/a — adaptive`).

- On #170, MAI looped on context limits in the Copilot Windows app. The
  execution prompt bounds reading to the newest three `WORKLOG.md` entries,
  as #188's did.
- If the orchestrator re-selects, prefer `claude-sonnet-5-5` (`high`), the
  ladder's Bounded alternative at its listed effort; the validator has two
  type traps (`bool` is an `int`, `datetime` is a `date`) where care matters
  more than speed. Avoid `gemini-3.8-flash` for the prose edits (PR #160:
  silently repointed Markdown citations), since E1–E7 are Markdown edits
  next to links.

The orchestrator verifies whether its runtime can instantiate MAI and
otherwise uses manual cross-provider execution from a local Copilot surface
(`handoffs/README.md`, *Manual Cross-Provider Execution (v1)*).

## Dependencies and assumptions

- **#188 is merged** (PR #199, `fa98e8e`), as the issue requires. It
  corrected Opus to `claude-opus-5-5`, added Sonnet 5.5, refreshed OpenAI to
  GPT-6 and set the roster policy (planner `high`/`xhigh`; Judgement and
  High-risk follow the planner row). The data file encodes that state.
- **Issue body staleness:**
  - The issue cites `handoffs/README.md:170` as a single "Verified 2026-09-03"
    date. Since #188 it records four per-provider dates; the problem it
    describes (no per-row date) still holds.
  - The issue says the roster names `claude-opus-5`. #188 fixed that.
  - The issue's unused-row examples were `claude-haiku-4-5-20251001`,
    `gemini-3.5-flash-lite` and `claude-fable-5-1`. After #188 there are nine
    unused rows (listed above); all are removed.
  - The issue cites `handoffs/README.md:173` for the re-verify rule; it is
    still at `:172-173`.
- **Decisions made in this plan** (the issue left them to the planner):
  - **Format and location:** TOML at `handoffs/models.toml`, read with the
    stdlib `tomllib`. TOML has native dates, so `verified` is typed, not a
    string.
  - **Shape:** a `[[models]]` catalog plus a role-centric `[[assignments]]`
    list. Each assignment names one role, an implementer rung when the role
    is `implementer`, a standing (`primary` = regular choice, `alternative`
    = permitted), the model, and its effort. This answers "which roles and
    rungs does a model serve" without duplicating the model's facts.
  - **Orchestrator effort is optional.** `handoffs/README.md:185` names no
    orchestrator effort; inventing one would change policy.
  - **Stale-row signal:** the checker prints a warning per stale row and
    still exits 0. In GitHub Actions it emits a `::warning` workflow command,
    which shows as an annotation on the PR. Threshold: **30 days**, stored in
    the data file as `stale_after_days`. Thirty days is the issue's example
    and matches the observed drift rate (#188 found Sonnet 5.5 one day after
    a verification, and the whole OpenAI lineup changed within a month).
  - **Unused rows are an error.** The checker rejects a catalog row that no
    assignment uses, which keeps "only models used by some role remain"
    true mechanically.
  - **Re-verified rows are in scope** for whichever plan or implementation
    change relies on them (E3's *Re-verification* text). Without this, a
    plan's mechanical inclusion test would exclude the `verified` update the
    new rule requires.
  - **The checker lives in `scripts/`, not `src/`.** It is workflow
    tooling, not product code. It follows `scripts/check_real_fixtures.py`:
    stdlib-only, runnable with a bare `python3` in the CI hygiene job, and
    loaded by tests through `importlib`.
- **Model IDs left in prose.** After this change, model IDs remain in prose
  only where they are an example or a rule about that specific model, never
  as roster data:
  - `handoffs/templates/planner.md:30` — "e.g. `gpt-6.1-sol` with `high`
    effort" and "such as `MAI-Code-1.1-Flash`": examples.
  - `handoffs/templates/orchestrator.md:21` and `handoffs/README.md:164` —
    the MAI-specific launch-surface rule (local Copilot surface, never the
    Copilot cloud agent). It applies to that model, not to a role.
  - `handoffs/templates/orchestrator.md:77` — the PR #160 incident record
    naming `gemini-3.8-flash`.
  If the owner reads the acceptance criterion more strictly, generalising the
  MAI launch rule is a separate policy change; it is not done here.
- **Neighbouring issues:**
  - #190 (doc-drift tests) candidate check 3 says: if #191 lands first,
    validate the data file instead. This plan's checker does that, so #190
    can drop check 3 or call this checker. Prose-wide model-ID scanning is
    left to #190.
  - #141 (workflow skills) should read `handoffs/models.toml` rather than
    copy model tables.
  - #189 (`scripts/verify.py`) may later fold this checker into its gate
    list; not done here.
  - #196 (slim `AGENTS.md`) may move the paragraph at `AGENTS.md:291`. E7 is
    one sentence; whichever lands second rebases it.
- **CI interpreter:** the hygiene job runs `python3` without
  `actions/setup-python` (`.github/workflows/ci.yml:13-32`). `tomllib` needs
  Python 3.11 or later; `ubuntu-latest` (Ubuntu 24.04) ships 3.12. If the
  hygiene step fails with `ModuleNotFoundError: tomllib`, that is a stop
  condition, not a reason to add `setup-python` unasked.
- **Historical records stay unchanged:** plans under `handoffs/issue-*.md`
  and older `WORKLOG.md` entries name removed models; they are point-in-time
  records.

## Proposed Plan & Scope

Locate every MODIFY edit by its old text, never by line number alone. Match
the old text exactly (including backticks, arrows and em dashes) and replace
it with the new text exactly. Nothing else in these files changes.

### Data file

#### [NEW] [handoffs/models.toml](models.toml) — N1

Create the file with exactly this content (UTF-8, LF line endings, one
trailing newline):

```toml
# Model roster and provider catalog for the multi-agent handoff workflow.
#
# handoffs/README.md holds the selection policy (rung definitions, reviewer
# independence, re-verification); this file holds which models fill each
# role. scripts/check_model_roster.py validates it and warns about stale rows.
#
# Re-verify a [[models]] row against its sources when it is older than
# stale_after_days, or when a dispatch to it fails or is rejected, and update
# its `verified` date in the same change.

schema_version = 1
stale_after_days = 30

# --- Catalog -------------------------------------------------------------
# effort_control = "adaptive" means the model has no user-settable effort:
# effort_values is empty and every assignment records "n/a — adaptive".

[[models]]
id = "gpt-6.1-sol"
provider = "OpenAI"
family = "GPT-6"
effort_control = "reasoning.effort"
effort_values = ["low", "medium", "high", "xhigh", "max"]
default_effort = "medium"
notes = "`none` and `minimal` are unsupported."
stability = "Stable"
verified = 2026-10-03
sources = [
  "https://developers.openai.com/api/docs/guides/latest-model",
  "https://developers.openai.com/api/docs/models/gpt-6.1-sol",
]

[[models]]
id = "gpt-6-luna"
provider = "OpenAI"
family = "GPT-6"
effort_control = "reasoning.effort"
effort_values = ["none", "low", "medium", "high", "xhigh", "max"]
default_effort = "medium"
stability = "Stable"
verified = 2026-10-03
sources = [
  "https://developers.openai.com/api/docs/guides/latest-model",
  "https://developers.openai.com/api/docs/models/gpt-6-luna",
]

[[models]]
id = "claude-opus-5-5"
provider = "Anthropic"
family = "Claude"
effort_control = "output_config.effort"
effort_values = ["low", "medium", "high", "xhigh", "max"]
default_effort = "medium"
stability = "Stable"
verified = 2026-10-02
sources = [
  "https://platform.claude.com/docs/en/models/overview",
  "https://platform.claude.com/docs/en/build-with-claude/effort",
]

[[models]]
id = "claude-sonnet-5-5"
provider = "Anthropic"
family = "Claude"
effort_control = "output_config.effort"
effort_values = ["low", "medium", "high", "xhigh", "max"]
default_effort = "high"
notes = "Levels recalibrated from Sonnet 5."
stability = "Stable"
verified = 2026-10-02
sources = [
  "https://platform.claude.com/docs/en/models/overview",
  "https://platform.claude.com/docs/en/build-with-claude/effort",
]

[[models]]
id = "gemini-3.1-pro-preview"
provider = "Google"
family = "Gemini 3.x"
effort_control = "thinking_level"
effort_values = ["low", "medium", "high"]
stability = "Preview"
verified = 2026-09-03
sources = [
  "https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview",
  "https://ai.google.dev/gemini-api/docs/thinking",
]

[[models]]
id = "gemini-3.8-flash"
provider = "Google"
family = "Gemini 3.x"
effort_control = "thinking_level"
effort_values = ["low", "medium", "high"]
notes = "`minimal` is unsupported and returns an error."
stability = "Stable"
verified = 2026-09-03
sources = [
  "https://ai.google.dev/gemini-api/docs/latest-model",
  "https://ai.google.dev/gemini-api/docs/thinking",
]

[[models]]
id = "MAI-Code-1.1-Flash"
provider = "Microsoft"
family = "MAI"
effort_control = "adaptive"
effort_values = []
notes = "The model sets its own reasoning budget. 256K context. Launched through GitHub Copilot; see handoffs/README.md, Manual Cross-Provider Execution."
stability = "GitHub Copilot GA; Azure Foundry Preview"
verified = 2026-09-19
sources = [
  "https://microsoft.ai/pdf/MAI-Code-1.1-Flash-Model-Card.PDF",
  "https://github.blog/changelog/2026-08-11-mai-code-1-1-flash-available-in-github-copilot/",
  "https://ai.azure.com/catalog/models/MAI-Code-1.1-Flash",
]

# --- Roster --------------------------------------------------------------
# standing = "primary": a regular choice for the role or rung.
# standing = "alternative": permitted, not in regular use.
# effort_when_needed: the higher level the policy allows when the ticket
# needs it.

# Planner
[[assignments]]
role = "planner"
standing = "primary"
model = "gpt-6.1-sol"
effort = "high"
effort_when_needed = "xhigh"

[[assignments]]
role = "planner"
standing = "primary"
model = "claude-opus-5-5"
effort = "high"
effort_when_needed = "xhigh"

[[assignments]]
role = "planner"
standing = "alternative"
model = "claude-sonnet-5-5"
effort = "high"

[[assignments]]
role = "planner"
standing = "alternative"
model = "gemini-3.1-pro-preview"
effort = "high"

# Orchestrator (no effort is set by policy)
[[assignments]]
role = "orchestrator"
standing = "primary"
model = "gpt-6.1-sol"

[[assignments]]
role = "orchestrator"
standing = "primary"
model = "claude-opus-5-5"

# Implementer, Bounded rung
[[assignments]]
role = "implementer"
rung = "bounded"
standing = "primary"
model = "MAI-Code-1.1-Flash"
effort = "n/a — adaptive"

[[assignments]]
role = "implementer"
rung = "bounded"
standing = "alternative"
model = "claude-sonnet-5-5"
effort = "high"

[[assignments]]
role = "implementer"
rung = "bounded"
standing = "alternative"
model = "gpt-6-luna"
effort = "medium"

[[assignments]]
role = "implementer"
rung = "bounded"
standing = "alternative"
model = "gemini-3.8-flash"
effort = "high"

# Implementer, Judgement rung
[[assignments]]
role = "implementer"
rung = "judgement"
standing = "primary"
model = "gpt-6.1-sol"
effort = "high"
effort_when_needed = "xhigh"

[[assignments]]
role = "implementer"
rung = "judgement"
standing = "primary"
model = "claude-opus-5-5"
effort = "high"
effort_when_needed = "xhigh"

[[assignments]]
role = "implementer"
rung = "judgement"
standing = "alternative"
model = "claude-sonnet-5-5"
effort = "high"

[[assignments]]
role = "implementer"
rung = "judgement"
standing = "alternative"
model = "gemini-3.1-pro-preview"
effort = "high"

# Implementer, High-risk rung
[[assignments]]
role = "implementer"
rung = "high-risk"
standing = "primary"
model = "gpt-6.1-sol"
effort = "high"
effort_when_needed = "xhigh"

[[assignments]]
role = "implementer"
rung = "high-risk"
standing = "primary"
model = "claude-opus-5-5"
effort = "high"
effort_when_needed = "xhigh"

[[assignments]]
role = "implementer"
rung = "high-risk"
standing = "alternative"
model = "claude-sonnet-5-5"
effort = "high"

[[assignments]]
role = "implementer"
rung = "high-risk"
standing = "alternative"
model = "gemini-3.1-pro-preview"
effort = "high"

# Independent reviewer
[[assignments]]
role = "reviewer"
standing = "primary"
model = "claude-opus-5-5"
effort = "high"

[[assignments]]
role = "reviewer"
standing = "primary"
model = "gpt-6.1-sol"
effort = "high"

[[assignments]]
role = "reviewer"
standing = "primary"
model = "gemini-3.1-pro-preview"
effort = "high"
```

Every value above is transcribed from `handoffs/README.md` at `fa98e8e`
(catalog `:230`, `:231`, `:236`, `:238`, `:241`, `:242`, `:244`; roster
`:184-185`; ladder `:204-206`; reviewer `:217`; dates `:170`). Notes keep the
catalog's support notes, minus the default (now `default_effort`) and minus
links (now `sources`).

### Checker

#### [NEW] [scripts/check_model_roster.py](../scripts/check_model_roster.py) — N2

Stdlib-only (`tomllib`, `datetime`, `argparse`, `os`, `sys`, `pathlib`,
`dataclasses`/`typing` as needed): no import of `vault_cleaner` or any
third-party package, so the CI hygiene job can run it with a bare `python3`.
Module docstring states the purpose, refs #191, and the run command
`python3 scripts/check_model_roster.py`, in the style of
`scripts/check_real_fixtures.py:1-17`.

**Public functions** (tests import these; names are fixed):

- `load_roster(path: Path) -> dict` — reads bytes, `tomllib.loads` (via
  `tomllib.load` on a binary file). A `tomllib.TOMLDecodeError` or
  `OSError` is re-raised as `RosterError` (a `ValueError` subclass defined in
  the module) whose message names the path.
- `validate(data: dict, *, today: date) -> list[str]` — returns **every**
  error found (not just the first), each a one-line message naming the
  offending model `id` or the assignment's 1-based index and its
  `role`/`model`. Empty list means valid.
- `stale_rows(data: dict, *, today: date) -> list[str]` — one warning
  message per `[[models]]` row whose age `(today - verified).days` is
  **strictly greater than** `stale_after_days`. Called only on valid data.
- `main(argv: list[str] | None = None) -> int` — CLI.

**Schema rules enforced by `validate`** (strict: unknown keys are errors,
as for review manifests in `AGENTS.md` *Conventions*):

Top level:
- Keys exactly `schema_version`, `stale_after_days`, `models`,
  `assignments`; any missing or extra key is an error.
- `schema_version` is the integer `1`.
- `stale_after_days` is an `int`, not a `bool`, and `> 0`.
- `models` and `assignments` are non-empty lists of tables (dicts).

Each `[[models]]` row:
- Required keys: `id`, `provider`, `family`, `effort_control`,
  `effort_values`, `stability`, `verified`, `sources`. Optional:
  `default_effort`, `notes`. Any other key is an error.
- `id`, `provider`, `family`, `effort_control`, `stability`, and `notes` when
  present, are non-empty strings with no leading or trailing whitespace.
- `id` is unique across rows (exact string comparison; ids stay opaque).
- `effort_values` is a list of unique non-empty strings. It is empty **if
  and only if** `effort_control == "adaptive"`.
- `default_effort`, when present, is a member of `effort_values`; it is not
  allowed when `effort_control == "adaptive"`.
- `verified` is a `datetime.date` and **not** a `datetime.datetime` (check
  `type(value) is date` or reject `isinstance(value, datetime)` first), and
  not later than `today + 1 day` (one day's tolerance for time zones).
- `sources` is a non-empty list of unique strings, each starting with
  `https://`.

Each `[[assignments]]` row:
- Required keys: `role`, `standing`, `model`. Optional: `rung`, `effort`,
  `effort_when_needed`. Any other key is an error.
- `role` is one of `planner`, `orchestrator`, `implementer`, `reviewer`.
- `standing` is one of `primary`, `alternative`.
- `rung` is present if and only if `role == "implementer"`, and is one of
  `bounded`, `judgement`, `high-risk`.
- `model` names an existing `[[models]]` `id`.
- `effort` is required unless `role == "orchestrator"`, where it is optional.
- `effort_when_needed` is allowed only when `effort` is present, and must
  differ from `effort`.
- For a model with `effort_control == "adaptive"`: `effort`, when present,
  must be exactly `n/a — adaptive` (U+2014 em dash, single spaces), and
  `effort_when_needed` is not allowed. For any other model: `effort` and
  `effort_when_needed` must each be in that model's `effort_values`.
- No two assignments share the same `(role, rung, model)`.

Cross-file coverage:
- Every `[[models]]` `id` is used by at least one assignment (an unused
  catalog row is an error).
- Each of `planner`, `orchestrator` and `reviewer`, and each implementer rung
  (`bounded`, `judgement`, `high-risk`), has at least one `primary`
  assignment.

When a row's structure is broken (for example a missing `id`), skip only the
checks that depend on the broken field for that row; never raise
`KeyError`/`TypeError` out of `validate`. Wrong-typed values are errors, not
exceptions.

**Stale-row message** (exact format; `<line>` is described below):

```text
model row "<id>" was verified <YYYY-MM-DD>, <N> days ago (threshold <T> days); re-verify it against its sources and update "verified" (handoffs/README.md, Re-verification)
```

**CLI contract (`main`):**

- `python3 scripts/check_model_roster.py [PATH] [--today YYYY-MM-DD]`.
  `PATH` defaults to `handoffs/models.toml` resolved from the repository
  root (`Path(__file__).resolve().parent.parent`), so the command works from
  any working directory. `--today` defaults to the current UTC date
  (`datetime.now(timezone.utc).date()`); it exists so the stale signal can be
  demonstrated deterministically.
- On a `RosterError`, or when `validate` returns errors: print each as
  `error: <path>: <message>` and return `1`. Stale rows are not reported in
  this case.
- Otherwise print each stale-row message as `warning: <path>: <message>`,
  then one summary line
  `<path>: <M> models, <A> assignments, <S> stale` and return `0`. **Stale
  rows never change the exit code.**
- When the environment variable `GITHUB_ACTIONS` equals `true`, print errors
  as `::error file=<relpath>::<message>` and stale warnings as
  `::warning file=<relpath>,line=<line>,title=Stale model row::<message>`
  instead of the `error:`/`warning:` prefixes. `<relpath>` is the path
  relative to the repository root, with `/` separators. `<line>` is the
  1-based number of the first line of the file whose stripped text equals
  `id = "<id>"`; if none matches, omit `,line=<line>`. The summary line is
  printed unchanged.
- Messages go to standard output; the script never writes files.

### Tests

#### [NEW] [tests/test_model_roster.py](../tests/test_model_roster.py) — N3

Load the script with `importlib.util.spec_from_file_location`, as
`tests/test_real_fixtures.py:15-28` does. Call `main()` in-process with
`capsys` (no subprocess; #45 showed subprocess output encoding differs on
Windows). Use `tmp_path` for every written file. Inject `today` everywhere;
no test depends on the wall clock except the real-file test, which only
asserts validity.

Build a **synthetic** valid baseline in the test module (fake ids such as
`fake-reasoner` and `fake-adaptive`, a `fake-adaptive` model with
`effort_control = "adaptive"`, and assignments that give every role and rung
a primary). Do not derive the baseline from the real file, so roster edits
never break the negative tests. Each negative case deep-copies the baseline,
applies one mutation, and asserts that `validate` returns a non-empty list
**containing a case-specific substring** (for example the offending key or
id). Asserting only "some error" is not enough, because a mutation can trip
an unrelated check.

Required tests:

1. `test_baseline_is_valid` — `validate(baseline, today=...) == []`.
2. `test_real_roster_is_valid` — `validate(load_roster(REPO / "handoffs" / "models.toml"), today=date.today()) == []`.
3. Negative cases, one parametrized test, at least one case per rule:
   - unknown top-level key; missing `assignments`;
   - `schema_version = 2`;
   - `stale_after_days` of `0`, of `True`, and of `"30"`;
   - duplicate model `id`;
   - unknown model key; missing `sources`;
   - `verified` as a string `"2026-10-01"`; as a `datetime.datetime`; and
     two days after `today`;
   - non-empty `effort_values` on the adaptive model; empty `effort_values`
     on a non-adaptive model; duplicate effort value;
   - `default_effort` not in `effort_values`; `default_effort` on the
     adaptive model;
   - a source starting with `http://`; empty `sources`;
   - assignment with unknown `role`, unknown `standing`, unknown `rung`;
   - implementer without `rung`; planner with `rung`;
   - planner without `effort`;
   - assignment naming a model that does not exist;
   - `effort` not in the model's `effort_values`;
   - adaptive model assigned `effort = "high"`; adaptive model assigned
     `effort = "n/a - adaptive"` (hyphen, not em dash);
   - `effort_when_needed` not allowed by the model; equal to `effort`;
     present without `effort`;
   - duplicate `(role, rung, model)`;
   - catalog row used by no assignment;
   - no `primary` reviewer; no `primary` for the `high-risk` rung;
   - unknown assignment key.
4. `test_validate_reports_every_error` — two independent mutations produce
   at least two messages.
5. `test_broken_row_does_not_raise` — a model row with no `id` and an
   assignment that is a string, not a table, return errors without raising.
6. Stale-row signal, against a synthetic baseline with
   `stale_after_days = 30` and a row `verified = date(2026, 9, 1)`:
   - `today = date(2026, 10, 1)` (30 days): `stale_rows` is empty;
   - `today = date(2026, 10, 2)` (31 days): exactly one message, equal to the
     exact stale-row format above with `31 days ago (threshold 30 days)`.
7. `test_main_stale_row_warns_and_exits_zero` — write the synthetic TOML
   with an expired row to `tmp_path`, run
   `main([str(path), "--today", "2026-10-02"])` with `GITHUB_ACTIONS` unset
   (`monkeypatch.delenv(..., raising=False)`): returns `0`, output contains
   `warning:` and `1 stale`.
8. `test_main_github_annotation` — same file, `GITHUB_ACTIONS=true`: returns
   `0` and output contains `::warning file=` and `,line=` with the line
   number of that row's `id = "..."` line, and `title=Stale model row::`.
9. `test_main_invalid_exits_one` — a schema error file returns `1` and prints
   `error:`; a file that is not valid TOML returns `1` and names the path.

Write synthetic TOML files with `Path.write_text(..., encoding="utf-8",
newline="\n")` (or bytes) so Windows writes LF.

### CI

#### [MODIFY] [.github/workflows/ci.yml](../.github/workflows/ci.yml#L25-L26) — E8

Old text:

```text
      - name: Real-export fixtures pass the sanitised-fixture guard
        run: python3 scripts/check_real_fixtures.py
```

New text:

```text
      - name: Real-export fixtures pass the sanitised-fixture guard
        run: python3 scripts/check_real_fixtures.py
      - name: Model roster schema and stale-row warnings
        run: python3 scripts/check_model_roster.py
```

### Workflow README

#### [MODIFY] [handoffs/README.md](README.md#L146) — E1

Old text:

```text
At dispatch time it re-verifies official model availability, selects and justifies one exact model ID and native effort from the current **Independent Review** mapping below, and records the actual provider/model/effort and any fallback.
```

New text:

```text
At dispatch time it selects and justifies one exact model ID and native effort from the `reviewer` assignments in [`handoffs/models.toml`](models.toml) under the [Independent Review Mapping](#independent-review-mapping), re-verifying that model's row first when it is stale (see [Re-verification](#re-verification)), and records the actual provider/model/effort and any fallback.
```

#### [MODIFY] [handoffs/README.md](README.md#L162) — E2

Old text:

```text
A repository model table is selection guidance; it does not itself make that provider available to the active runtime.
```

New text:

```text
The model data file, [`handoffs/models.toml`](models.toml), is selection guidance; it does not itself make that provider available to the active runtime.
```

#### [MODIFY] [handoffs/README.md](README.md#L168-L244) — E3

Replace everything from the line `## Model Family & Provider-Native
Reasoning-Effort Matrix` through the end of the file with the text below.
The four existing headings are kept, so the anchors
`#model-family--provider-native-reasoning-effort-matrix`,
`#role--model-roster`, `#implementer-ladder`, `#independent-review-mapping`
and `#provider-catalog--reasoning-controls` keep working; one heading,
*Re-verification*, is new.

Old text: lines 168–244 (from the heading above to end of file).

New text:

```text
## Model Family & Provider-Native Reasoning-Effort Matrix

Which models fill each role, and each model's provider, exact ID, native
effort control, allowed effort values, verification date and sources, live in
one data file: [`handoffs/models.toml`](models.toml). This section holds the
selection policy. Name a model in prose only as an example or in a rule about
that specific model; never copy the roster or catalog into another document.

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

The orchestrator reviews implementation diffs against plan checklists and
likely findings with one `role = "reviewer"` assignment from
[`handoffs/models.toml`](models.toml), at that assignment's effort.

Prefer a model from a different family than the implementer; any listed model
is allowed in a fresh read-only session.

A model with no `reviewer` assignment, such as an implementer-only model, is
not an independent review option.

### Provider Catalog & Reasoning Controls

The `[[models]]` rows in [`handoffs/models.toml`](models.toml) are the
catalog: provider, family, exact model ID, native reasoning control, allowed
effort values and default, support notes, stability, `verified` date and
sources. A row exists only while some assignment uses it; the checker rejects
an unused row. For a model whose `effort_control` is `adaptive`, record the
effort as `n/a — adaptive` rather than guessing a level.
```

### Templates

#### [MODIFY] [handoffs/templates/planner.md](templates/planner.md#L29) — E4

Old text:

```text
   - Consult the role roster, implementer ladder, and provider catalog in [handoffs/README.md](../README.md#model-family--provider-native-reasoning-effort-matrix).
```

New text:

```text
   - Read the selection policy in [handoffs/README.md](../README.md#model-family--provider-native-reasoning-effort-matrix), then select from the assignments and catalog rows in [handoffs/models.toml](../models.toml). If `python3 scripts/check_model_roster.py` reports the selected model's row as stale, re-verify it under [Re-verification](../README.md#re-verification) before relying on it.
```

#### [MODIFY] [handoffs/templates/orchestrator.md](templates/orchestrator.md#L19) — E5

Old text:

```text
record the plan's selection, the actual choice, and a one-line reason. Re-selection never changes scope.
```

New text:

```text
record the plan's selection, the actual choice, and a one-line reason. Re-selection never changes scope. If a dispatch to the selected model fails or is rejected, re-verify that model's row in [handoffs/models.toml](../models.toml) under [Re-verification](../README.md#re-verification).
```

#### [MODIFY] [handoffs/templates/orchestrator.md](templates/orchestrator.md#L51) — E6

Old text:

```text
Re-verify official provider documentation at dispatch time, then select and justify one exact model ID and native effort from the **Independent Review** row in [handoffs/README.md](../README.md#independent-review-mapping).
```

New text:

```text
Select and justify one exact model ID and native effort from the `reviewer` assignments in [handoffs/models.toml](../models.toml), under the policy in [handoffs/README.md](../README.md#independent-review-mapping); if `python3 scripts/check_model_roster.py` reports that model's row as stale, re-verify it under [Re-verification](../README.md#re-verification) first.
```

### Agent guide

#### [MODIFY] [AGENTS.md](../AGENTS.md#L291) — E7

Old text:

```text
and for the role → model roster: Sol and Opus are the regular planner/orchestrator choices, Sonnet and Gemini remain permitted planner alternatives, and the primary implementer ladder is MAI-Code-1.1-Flash for the Bounded rung, then Sol or Opus (the planner row) for the Judgement and High-risk rungs.
```

New text:

```text
and for the model-selection policy; [handoffs/models.toml](handoffs/models.toml) records which models fill each role.
```

### Worklog

#### [MODIFY] [WORKLOG.md](../WORKLOG.md) — W

Add a dated entry at the top, headed
`## YYYY-MM-DD — #191 implementation: structured model roster (PR 2)`,
recording: the base SHA; the dispatch record supplied by the orchestrator;
that N1 and E1–E8 were applied verbatim (or any deviation and why); notable
implementation choices in N2/N3; the checker's output on the real file
(including any stale-row warnings, which are expected for the Google rows);
and the verification output summary. Refs #191.

### Trial results

Applied mechanically from this document's own blocks in a detached worktree
at `fa98e8e`, then discarded:

- E1, E2 and E4–E8 each matched exactly once; E3's heading occurred once and
  the replacement ran from line 168 to end of file;
- N1 extracted from this plan was byte-identical to the file trialled with
  `tomllib` (see *Context & Measurement*, *Trial*);
- the diff was 6 files, +330/−50 (`handoffs/models.toml` +270), with
  `git diff --check` clean;
- the retained headings sat at lines 168, 194, 211, 233 and 245, with
  *Re-verification* at 180, so every existing anchor survives; and
- `grep -nE 'gpt-|claude-|gemini-|MAI-Code'` over `AGENTS.md`,
  `handoffs/README.md` and `handoffs/templates/*.md` matched only
  `handoffs/README.md:164`, `handoffs/templates/orchestrator.md:21`,
  `handoffs/templates/orchestrator.md:77` and
  `handoffs/templates/planner.md:30`, the four classified locations.

## Mechanical inclusion test

A hunk in `git diff <base_sha>...HEAD` is **in scope** if and only if it is:

- N1 (`handoffs/models.toml`), byte-identical to the block above;
- N2 (`scripts/check_model_roster.py`) or N3 (`tests/test_model_roster.py`),
  implementing the specification above;
- one of E1–E8, applied exactly as specified; or
- the W `WORKLOG.md` entry.

Worked examples:

- **IN SCOPE:** a private helper in N2 that finds the `id = "..."` line for
  the annotation, or a test fixture builder in N3.
- **IN SCOPE:** an extra negative case in N3 beyond the required list, if it
  tests a rule in this plan.
- **OUT OF SCOPE:** changing any `verified` date, effort value, default,
  stability label, note or source in N1, even if the implementer believes a
  provider page has changed. Report it instead.
- **OUT OF SCOPE:** adding a model, an assignment or a field to N1, or
  re-adding a removed catalog row.
- **OUT OF SCOPE:** generalising the MAI launch-surface rule, editing the PR
  #160 incident line, or rewording any other `handoffs/README.md` section.
- **OUT OF SCOPE:** a prose-wide model-ID scan test, link checking, or other
  doc-drift tests (#190); folding the checker into a `verify.py` (#189).
- **OUT OF SCOPE:** adding `actions/setup-python` or any other step to the
  hygiene job, or changing the `test` or `browser` jobs.
- **OUT OF SCOPE:** editing historical plans (`handoffs/issue-*.md`) or older
  `WORKLOG.md` entries.
- **OUT OF SCOPE:** importing anything from `vault_cleaner` or a third-party
  package in N2, or adding a dependency to `pyproject.toml`.

### Stop conditions

Stop implementation and return to the orchestrator if:

- an E-edit's old text is not found exactly once in its file on the branch
  base (another PR changed it first), or `handoffs/README.md` no longer ends
  with the Provider Catalog table;
- `main` has changed a model, effort, date or role in `handoffs/README.md`
  since `fa98e8e`, so N1 no longer transcribes the current tables;
- N1 as written fails the N2 rules (the plan's data and rules disagree);
- the CI hygiene job's `python3` cannot import `tomllib`;
- `ruff`, `pytest` or `git diff --check` fails for a reason not caused by
  this change.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Type traps in the validator.** `verified = 2026-10-03T00:00:00` accepted
   because `datetime` is a `date` subclass; `stale_after_days = true`
   accepted because `bool` is an `int`. The required negative cases cover
   both; check they assert the specific message.
2. **Negative tests that pass without their check.** Cases that assert only
   "errors is non-empty", a baseline that is itself invalid, or a mutation
   that trips an earlier rule. Revert spot-check: delete one rule from N2 in
   a disposable worktree and confirm its case goes red.
3. **The stale signal fails CI or depends on the clock.** A stale row
   changing the exit code, the real-file test calling `stale_rows` and
   asserting none, or a boundary off by one (30 days must not be stale; 31
   must be).
4. **Transcription or prose drift.** An effort value, default, date or
   source in N1 differing from the plan block; collateral edits beside E1–E7;
   a broken relative link (`models.toml` from `handoffs/`, `../models.toml`
   from `handoffs/templates/`, `handoffs/models.toml` from the root); or a
   model ID left in prose outside the four classified locations.
5. **Worklog missing the dispatch record** that the orchestrator must verify
   before opening PR 2.

# Reusable implementer execution prompt

Implement issue #191 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-191-implementation-plan.md
```

Read the entire handoff, issue #191, `AGENTS.md`, only the newest three entries at the top of `WORKLOG.md` (not the whole file), `handoffs/README.md`, both files in `handoffs/templates/`, `scripts/check_real_fixtures.py` (style reference) and `tests/test_real_fixtures.py:1-30` (loader reference) before editing. You do not need to read `PLAN.md` or product source code.

Rules:
- work on `feat/issue-191-model-roster-data`; branch from latest `main` and record the base SHA;
- create `handoffs/models.toml` byte-identical to block N1, and apply E1–E8 exactly as written, locating each by its old text, not by line number;
- implement `scripts/check_model_roster.py` (N2) and `tests/test_model_roster.py` (N3) to the plan's specification, including every required test case;
- apply the plan's mechanical inclusion test to every hunk; never change a `verified` date or any other N1 value;
- update `WORKLOG.md` with the dated entry described in W, including the dispatch record you were given;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `python3 scripts/check_model_roster.py`, `git diff --check origin/main...HEAD`, `test -z "$(git ls-files data/)"`; the browser suite is not required because no UI file changes;
- commit and push the implementation branch, with `Refs #191` in every commit message; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming of private helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, report: branch, base SHA, head SHA, the list of items applied (N1–N3, E1–E8 and W), any deviation, the output of `python3 scripts/check_model_roster.py`, and the verification output.

# Ticket-specific review decision

**Review path:** `standard orchestrator review`

**Reason:**
The change touches workflow documentation, CI's hygiene job and a new
stdlib-only script with its tests. It touches no parser, rule, rail, schema,
server lifecycle or product security boundary, and the checker cannot break a
build on stale data by design. The main risks (validator type traps,
negative tests that pass without their check, collateral Markdown edits) are
caught directly by the checklist below, the revert spot-check and a word-diff
audit. The orchestrator should escalate to independent adversarial review if
the implementer deviates from N1 or the E-edits, or if the validator grows
beyond the specified rules.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] `git show <head>:handoffs/models.toml` is byte-identical to block N1 (extract the block from this plan and `diff` it).
- [ ] `git diff --word-diff=plain <base_sha>...HEAD -- AGENTS.md handoffs/README.md handoffs/templates .github/workflows/ci.yml` shows exactly E1–E8 and nothing else.
- [ ] `python3 scripts/check_model_roster.py` exits 0 on the real file and prints the summary line; any warnings are stale-row warnings only. With `--today` set 40 days after the newest `verified` date it warns for all seven rows and still exits 0.
- [ ] `GITHUB_ACTIONS=true python3 scripts/check_model_roster.py --today <date>` prints `::warning file=handoffs/models.toml,line=<n>,title=Stale model row::…`, and `<n>` is the row's `id = "..."` line.
- [ ] Revert spot-check in a disposable worktree: remove the `datetime` rejection, the unused-row check, and the stale comparison (`>` to `>=`) one at a time; each must turn a specific N3 test red.
- [ ] Every required N3 case exists and asserts a case-specific substring; the baseline is synthetic, not the real file.
- [ ] N2 imports only the standard library; no `vault_cleaner` or third-party import.
- [ ] `grep -nE 'gpt-|claude-|gemini-|MAI-Code' AGENTS.md handoffs/README.md handoffs/templates/*.md` lists only `handoffs/templates/planner.md:30`, `handoffs/templates/orchestrator.md:21`, `handoffs/templates/orchestrator.md:77` and the MAI launch rule in `handoffs/README.md` (*Manual Cross-Provider Execution*).
- [ ] Every new link resolves on GitHub: `models.toml` and `#re-verification` from `handoffs/README.md`; `../models.toml` and `../README.md#re-verification` from both templates; `handoffs/models.toml` from `AGENTS.md`. The README tables render.
- [ ] The CI hygiene job runs the new step and passes on the PR.
- [ ] `git diff -U0 <base_sha>...HEAD -- WORKLOG.md` has exactly one `@@` hunk with no removed lines, placed before the base's first `## ` heading, and the entry has the dispatch record and `Refs #191`.
- [ ] `ruff`, `pytest -q`, `git diff --check` and `test -z "$(git ls-files data/)"` pass.

# Dispatch comment draft

Planned #191 in [handoffs/issue-191-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-191-implementation-plan.md) on `main`.

- **Implementer model & effort:** `MAI-Code-1.1-Flash` (`n/a — adaptive`); re-selection fallback `claude-sonnet-5-5` (`high`), not Gemini (PR #160).
- **Implementation branch:** `feat/issue-191-model-roster-data`
- **Likely findings:** validator type traps (`datetime` as `date`, `bool` as `int`); negative tests that pass without their check; a stale row failing CI or an off-by-one at the threshold; transcription drift in `handoffs/models.toml` or collateral prose edits beside E1–E7; missing dispatch record in `WORKLOG.md`.
