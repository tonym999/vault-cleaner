# Issue #51 — Luna xhigh Implementation Plan

**Repository:** `tonym999/vault-cleaner`
**Issue:** `#51 — M8 cleanup: delete the browser-side validator and its parity suite`
**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → Sol high reviews → PR
**Plan date:** 2026-08-28

## Objective

Complete the M8 migration to a single browser review surface by deleting the unreleased static `review-html` workflow and all browser-side manifest parsing/building/import/export code that existed only to support it.

The permanent end state is:

- `vault-cleaner serve` is the browser workflow;
- `review.parse_manifest` remains the only **review-manifest** validator and is reached through `vault-cleaner review --manifest` for CLI/scripting/backup use;
- the server verdict API keeps its own separate strict validator for verdict mutation payloads;
- the shared presentation layer and the permanent server/browser/packaging tests remain intact;
- the repository becomes materially smaller rather than carrying two interactive review implementations.

This is a cleanup/deletion ticket, not a protocol redesign.

## Why this ticket is ready

- Issue #48 chose **Option A — retire** for the static review page. There is no remaining product decision about whether the static workflow survives.
- Issue #51's follow-up decision resolved manifest support as **CLI-only**: no manifest endpoints and no browser manifest code.
- Issue #90, which explicitly blocked #51, is complete. The real-browser parity gate, non-editable wheel proof, and server workflow documentation have landed.
- The permanent presentation split already exists:
  - `src/vault_cleaner/ui/review_ui.js` — shared, manifest-free presentation/view code;
  - `src/vault_cleaner/ui/review_server.js` — permanent server adapter;
  - `src/vault_cleaner/ui/review_static.js` — temporary adapter explicitly marked for deletion by #51.
- The permanent packaging declaration already includes `vault_cleaner.ui` CSS/HTML/JS assets, and the wheel proof checks the server's three allow-listed assets. Do not redesign packaging unless cleanup exposes a concrete defect.

---

# Review model

## Standard review path — with Sol high as the required reviewer

```text
Sol orchestrator
    ↓
Luna xhigh implementation
    ↓
Sol high review
    ↓
PR
```

This ticket is intentionally mechanical and localised. It should remove an unreleased temporary surface without changing the server protocol, persistence model, lifecycle, finalisation semantics, rules engine, CSV writer, or security boundary.

Sol high must still review the completed branch before any PR is raised, because deletion can accidentally remove regression coverage or leave a half-retired workflow behind.

If implementation unexpectedly requires a substantive server protocol, lifecycle, persistence, security, packaging architecture, or shared-view redesign, **stop expanding the diff and hand the finding back to Sol**. That would invalidate this ticket's standard-risk classification rather than silently turning #51 into a higher-risk feature change.

---

# Authoritative context

Before changing code, read:

- `AGENTS.md`
- `PLAN.md`
- issue #51 and both comments
- issue #48, especially the Option A decision
- parent issue #50
- issue #90
- the 2026-08-25 to 2026-08-27 `WORKLOG.md` entries for #87–#90
- the current tests listed below

Treat the following as authoritative:

- **Browser product path:** `vault-cleaner serve`
- **Manifest path:** CLI-only through `review.parse_manifest` / `vault-cleaner review --manifest`
- **Server mutation path:** verdict API payloads; no review-manifest endpoint
- **Shared browser presentation seam:** `src/vault_cleaner/ui/review_ui.js`
- **Permanent browser adapter:** `src/vault_cleaner/ui/review_server.js`
- **Permanent browser page:** `src/vault_cleaner/ui/review_server.html`
- **Permanent package proof:** `scripts/check_wheel_install.py`
- **Permanent browser acceptance:** `tests/test_server_browser.py`
- Python remains authoritative for rules, review-manifest validation, durable veto handling, finalisation, and DIM CSV generation.

Do not reintroduce a browser manifest path in another form.

---

# Algorithmic scope rule

For **every proposed edit**, Luna must apply this two-question test:

1. **Is this change necessary to remove the retired static `review-html` surface or browser-manifest path?**
   Examples: static adapter, Python static renderer, CLI subcommand, static-only tests, stale user documentation, obsolete static/manifest-parser guidance.

2. **Or is this change necessary to preserve an already-valid permanent invariant after those static dependencies are removed?**
   Examples: moving a test helper so permanent Node tests remain self-contained; preserving opaque 64-bit ID handling, prototype-safe maps, terminal grouping parity, hostile-text inertness, or source-safety checks.

If the answer to **both** questions is no, the change is out of scope.

Additional hard stop:

> If a proposed change alters the server API/protocol, verdict semantics, `review.parse_manifest`, finalisation, persistence, session lifecycle, rule/report semantics, permanent shared-view behaviour, Playwright scope, or packaging architecture rather than merely removing/decoupling the retired static surface, do not implement it under #51. Record the finding for Sol.

This rule should keep the diff dominated by deletions and small test/documentation decoupling edits.

---

# Scope

## In scope

- Remove the `review-html` CLI subcommand and all CLI imports/constants/helpers used only by it.
- Delete `src/vault_cleaner/review_html.py`.
- Delete `src/vault_cleaner/ui/review_static.js`.
- Remove all browser manifest reading, validation, building, import, export, handoff, autosave, and static-page-only UI code.
- Delete the static-artifact test suites once their still-relevant presentation assertions are proven to exist in permanent tests:
  - `tests/test_cli_review_html.py`
  - `tests/test_review_html.py`
  - `tests/test_review_html_js.py`
- Decouple `tests/test_review_ui_js.py` from deleted static test/module helpers while preserving its permanent manifest-free presentation coverage.
- Remove review-html-specific cases from mixed-purpose test modules such as:
  - `tests/test_cli_write_errors.py`
  - `tests/test_cli_config_paths.py`
- Update `README.md` so `serve` is the browser workflow and `review --manifest` remains CLI/scripting/backup functionality.
- Update `AGENTS.md` to remove obsolete static/browser-manifest implementation gotchas while retaining the general strict-untrusted-input lesson.
- Update `WORKLOG.md` with a dated #51 entry and auditable line-count reduction.
- Remove stale static-only comments/references discovered by repository search.

## Out of scope

- Adding manifest endpoints to the server.
- Replacing the deleted static page with another browser manifest import/export mechanism.
- Changing `review.parse_manifest` behaviour or review-manifest schema.
- Changing the verdict API contract or loosening its strict validation.
- Changing server session states, revision/fingerprint rules, stale handling, finalisation, reset, shutdown, persistence, or CSV download behaviour.
- Changing rules, scoring, report/snapshot semantics, `RULESET_VERSION`, or snapshot versions.
- Expanding Playwright coverage beyond the two permanent tests from #90.
- Changing runtime dependencies.
- Reworking package-data architecture merely because one `*.js` file is deleted.
- Deleting historical references from old `WORKLOG.md` entries. History is supposed to remain history.

If implementation appears to need any out-of-scope change, document the concrete reason and return it to Sol before expanding the branch.

---

# Expected change footprint

## Expected deletions

```text
src/vault_cleaner/review_html.py
src/vault_cleaner/ui/review_static.js
tests/test_cli_review_html.py
tests/test_review_html.py
tests/test_review_html_js.py
```

Delete these only after checking that no permanent coverage still depends on a helper or assertion living there.

## Expected modifications

```text
src/vault_cleaner/cli.py
tests/test_review_ui_js.py
tests/test_cli_write_errors.py
tests/test_cli_config_paths.py
README.md
AGENTS.md
WORKLOG.md
```

Other files may need tiny stale-reference cleanup if `git grep` finds a genuine live dependency.

## Files/components that should normally remain substantively unchanged

```text
src/vault_cleaner/review.py
src/vault_cleaner/review_session.py
src/vault_cleaner/server/
src/vault_cleaner/ui/review_ui.js
src/vault_cleaner/ui/review_server.js
src/vault_cleaner/ui/review_server.html
src/vault_cleaner/ui/review.css
tests/test_review.py
tests/test_cli_review.py
tests/test_server_*.py
tests/test_server_browser.py
scripts/check_wheel_install.py
.github/workflows/ci.yml
pyproject.toml
PLAN.md
```

A comment-only correction may be reasonable where it directly names the deleted static surface. Substantive edits to any of the above are a scope warning and must be called out to Sol.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline

Branch from the latest `main`.

Suggested branch:

```text
issue-51-retire-static-review
```

Install the declared dev toolchain if necessary:

```bash
python -m pip install -e ".[dev]"
```

Run the normal baseline gates before editing:

```bash
ruff check src tests scripts
pytest -q
git diff --check
git status --short
git ls-files data/
```

Expected baseline:

- Ruff green.
- Full pytest green.
- `git diff --check` clean.
- `git status --short` clean before the branch work.
- `git ls-files data/` prints nothing.

Record the current `main` commit SHA in the Luna → Sol handoff.

### Capture the deletion baseline

Before deleting files, record line counts for the retired surface so the later `WORKLOG.md` entry can give a real before/after audit rather than repeating old ticket estimates.

Use a small cross-platform Python count:

```bash
python - <<'PY'
from pathlib import Path

paths = [
    Path("src/vault_cleaner/review_html.py"),
    Path("src/vault_cleaner/ui/review_static.js"),
    Path("tests/test_cli_review_html.py"),
    Path("tests/test_review_html.py"),
    Path("tests/test_review_html_js.py"),
]

total = 0
for path in paths:
    count = sum(1 for _ in path.open(encoding="utf-8"))
    total += count
    print(f"{count:6}  {path}")
print(f"{total:6}  TOTAL retired-surface baseline")
PY
```

Also keep `git diff --numstat origin/main...HEAD` for the final net additions/deletions.

Do **not** manufacture a line-count target. Behavioural cleanup is the gate; the ticket only requires that the resulting reduction be materially downward and recorded.

---

## 2. Inventory every live static-surface reference before deleting

Run targeted searches from the clean baseline:

```bash
git grep -n "review-html" -- ':!WORKLOG.md'
git grep -n "review_html" -- ':!WORKLOG.md'
git grep -n "review_static.js" -- ':!WORKLOG.md'
git grep -n -E \
  'readManifest|readManifestText|readManifestBytes|readPastedManifest|decodeManifestBytes|fractionalNumberError|buildManifest|exportManifest|manifestJson|offerDownload|MANIFEST_KEYS|SNAPSHOT_KEYS|DECISION_KEYS' \
  -- ':!WORKLOG.md'
```

Classify every hit as one of:

- delete with retired surface;
- rewrite documentation;
- preserve because it belongs to CLI manifest validation;
- preserve because it belongs to the server verdict API;
- historical `WORKLOG.md` only.

Do not use a broad search-and-delete for generic words such as `manifest`, `VERDICTS`, `MAX_TEXT`, `clip`, or `validate`; those concepts may legitimately exist elsewhere.

Before removing test files, make an explicit survivor map for #51's required presentation invariants:

| Invariant | Permanent owner after #51 |
| --- | --- |
| Opaque 64-bit IDs / `compareIds` without `Number` coercion | `tests/test_review_ui_js.py` |
| `Object.create(null)` / prototype safety / `__proto__` | `tests/test_review_ui_js.py` |
| grouping/sorting/filtering and terminal summary parity | `tests/test_review_ui_js.py` |
| hostile browser text remains inert | `tests/test_review_ui_js.py` plus real-browser hostile test |
| packaged source safety / invisible-character guard where still relevant | `tests/test_review_ui_js.py` |
| live browser hostile DOM proof | `tests/test_server_browser.py` |
| full browser upload → verdict → finalise → downloaded bytes | `tests/test_server_browser.py` |
| non-editable wheel assets | `scripts/check_wheel_install.py` |
| review-manifest parsing/validation | `tests/test_review.py` / `tests/test_cli_review.py` |
| verdict API strictness | existing server verdict/API tests |

If a required survivor is not actually covered, move or recreate the smallest behaviour-level assertion in the permanent owner **before** deleting its old copy.

Do not carry browser-manifest parity tests forward under a new name.

---

## 3. Remove the production static review surface

### 3.1 Delete the temporary browser adapter

Delete:

```text
src/vault_cleaner/ui/review_static.js
```

Do not move its manifest builder/parser/import/export logic into `review_server.js` or `review_ui.js`.

The server UI already posts verdict mutations; that is the permanent design.

### 3.2 Delete the Python static renderer

Delete:

```text
src/vault_cleaner/review_html.py
```

This removes the self-contained HTML renderer, its inline CSP/static chrome, embedded snapshot wrapper, and its loading of `review_static.js`.

Do not preserve a read-only static renderer: #48 chose Option A, not Option C.

### 3.3 Remove the CLI surface

In `src/vault_cleaner/cli.py` remove only the static-page path:

- imports from `vault_cleaner.review_html`;
- `REVIEW_HTML_OUTPUT_HELP`;
- `_cmd_review_html`;
- the `review-html` subparser and its arguments;
- static-page-only terminal/privacy strings whose only consumer disappears.

Preserve:

- `report`;
- `review`;
- `review --manifest`;
- `serve`;
- normal output path helpers used by surviving commands.

Add a small behavioural regression only if it fits an existing CLI test naturally: the top-level CLI help should no longer advertise `review-html`, or invoking it should be rejected as an unknown command. Do not create a large “absence suite”.

---

## 4. Remove the static-only test stack without losing permanent coverage

### 4.1 `tests/test_cli_review_html.py`

Delete the file. Its subject is the retired command.

Before deletion, confirm any generic assertion it happened to contain is already owned elsewhere. Do not preserve “report still writes CSV, not HTML” as a special concept after HTML output no longer exists.

### 4.2 `tests/test_review_html.py`

Delete the static artifact renderer/embedding/containment suite.

Important dependency:

- `tests/test_review_ui_js.py` currently imports `hostile_report` from this file.

Replace that dependency with a small local manifest-free test helper in `test_review_ui_js.py` (or an existing neutral fixture/helper if one already exists). Prefer direct `run_report(...)` construction over creating a new production abstraction solely for tests.

Do **not** move static-only assertions such as:

- self-contained file construction;
- inline CSP for `file://`;
- embedded snapshot escaping;
- static HTML write/replace behaviour;
- static script element coupling.

Those requirements die with the retired product surface.

### 4.3 `tests/test_review_html_js.py`

Treat this file as the static-adapter suite.

Delete it once the survivor map proves the required rendering invariants already live in `tests/test_review_ui_js.py` and the real-browser server tests.

Do **not** preserve or rename:

- the Python-vs-JavaScript manifest parity table;
- raw-number spelling checks;
- BOM/UTF-8 decoder parity;
- paste-path whitespace checks;
- manifest import/export round trips;
- static browser-storage handoff behaviour.

Those tests existed to keep a duplicate browser manifest implementation aligned with Python; the implementation is now intentionally gone.

### 4.4 Clean `tests/test_review_ui_js.py`

This file is the permanent manifest-free Node presentation suite and should survive.

Make the minimum decoupling changes:

- stop importing `hostile_report` from `test_review_html.py`;
- stop importing/using `render_review_html`;
- remove the static-only “artifact inlines exact packaged resource bytes” test;
- keep direct tests against packaged `review_ui.js`;
- keep 64-bit ID, prototype safety, filtering/grouping/sorting, hostile-text, DOM text-node, and source-character safeguards.

Avoid touching `review_ui.js` unless a test decoupling exposes a genuine existing defect unrelated to the deleted static layer. If that happens, report it to Sol rather than folding an opportunistic redesign into #51.

### 4.5 Clean mixed-purpose CLI tests

In:

```text
tests/test_cli_write_errors.py
tests/test_cli_config_paths.py
```

remove only cases parameterised around `review-html` and any monkeypatch of `write_review_html`.

Keep all surviving `report`, `review`, path-resolution, and clean-write-error coverage.

---

## 5. Preserve manifest and verdict validation as distinct responsibilities

This is a critical non-regression boundary.

### Review manifests

Keep:

```text
src/vault_cleaner/review.py
vault-cleaner review --manifest ...
```

`review.parse_manifest` remains the only review-manifest validator.

Do not simplify it merely because the browser parser is gone. The CLI/scripting/backup manifest path still accepts untrusted input.

### Server verdict API

Keep the server's separate strict verdict request validation.

The cleanup must not imply “Python manifest validation covers the API”. These are different payloads and different trust boundaries.

After implementation, existing tests must still demonstrate that the verdict API rejects malformed/untrusted payloads according to its established contract.

No manifest endpoint should be added.

---

## 6. Rewrite live documentation to describe the final architecture

### README.md

The current README still advertises the static page extensively. Rewrite the live documentation rather than leaving a “deprecated” workflow for something never released.

Required outcome:

1. **How it works**
   - browser review points to `vault-cleaner serve`, not a static HTML page.

2. **Review workflow**
   - retain terminal `report` and `review`;
   - retain `review --manifest` for CLI/scripting/backup;
   - remove `review-html` commands and the “each command owns exactly one output” description that includes it.

3. **Browser review**
   - remove the static HTML section;
   - make the local review server section the sole browser workflow.

4. **Manifest format**
   - keep the CLI manifest format because it still exists;
   - remove wording saying `review-html` generates the manifest;
   - make clear the server UI does **not** use manifest import/export.

5. **Shared presentation wording**
   - replace phrases such as “reuses ... from `review-html`” with neutral wording such as “uses the shared review presentation layer”.

6. **Status**
   - update M7/M8 status wording so it no longer presents `review-html` as an active feature;
   - state that the static prototype has been retired after server parity, if a status note is useful.

Do not remove the server privacy documentation landed by #90.

### AGENTS.md

Remove standing guidance that exists only because the static browser manifest implementation existed, including obsolete `review_html.py` / inline-script coupling and manifest-parser-specific notes such as:

- JavaScript `trim()` vs JSON whitespace;
- `TextDecoder` / `ignoreBOM` parity with Python manifest reads;
- `Number.isInteger` / raw number-spelling workarounds;
- browser manifest import-entry-point parity details that no longer have a browser consumer.

Preserve or state clearly the general lesson:

> Validate untrusted input strictly at every entry point, at the outermost layer that entry point uses, and when a divergence is fixed on one sibling path, fix the sibling paths in the same change.

Also preserve the existing general rules that:

- review manifests are untrusted;
- unknown keys/versions/duplicate IDs are rejected;
- IDs/hashes remain opaque strings;
- no request-derived filesystem path is trusted;
- the server's lifecycle and filesystem cleanup boundaries remain unchanged.

Do not indiscriminately delete source-safety guidance that still applies to the surviving packaged JavaScript/CSS tests.

---

## 7. Preserve packaging and browser acceptance

The package-data rule is currently broad:

```toml
"vault_cleaner.ui" = ["*.css", "*.html", "*.js"]
```

Deleting `review_static.js` should naturally remove it from future wheels. Do not replace the wildcard with a new bespoke packaging scheme unless an actual packaging failure proves it necessary.

The wheel proof already checks only the permanent server assets:

```text
/
review.css
review_ui.js
review_server.js
```

Keep `scripts/check_wheel_install.py` substantively unchanged.

Keep the dedicated Chromium CI job and its two browser tests unchanged unless a stale static-name comment needs a trivial wording correction.

Do not weaken the happy-path browser test's assertion that the downloaded `dim-import.csv` bytes equal the server's finalised bytes.

---

## 8. Run a post-deletion repository hygiene search

After implementation, rerun:

```bash
git grep -n "review-html" -- ':!WORKLOG.md' || true
git grep -n "review_html" -- ':!WORKLOG.md' || true
git grep -n "review_static.js" -- ':!WORKLOG.md' || true
git grep -n -E \
  'readManifest|readManifestText|readManifestBytes|readPastedManifest|decodeManifestBytes|fractionalNumberError|buildManifest|exportManifest|manifestJson|offerDownload|MANIFEST_KEYS|SNAPSHOT_KEYS|DECISION_KEYS' \
  -- ':!WORKLOG.md' || true
```

Expected result:

- no live production/browser/test/documentation reference to the retired static surface;
- historical references in `WORKLOG.md` are allowed and should remain;
- generic CLI manifest support still exists in `review.py`, `cli.py`, tests, and README.

Then explicitly inspect:

```bash
git grep -n "parse_manifest" src tests
```

Confirm it still has the expected CLI/test ownership and has not migrated into browser/server endpoint code.

---

## 9. Documentation/worklog

Add a dated `WORKLOG.md` entry for #51 containing:

- the static `review-html` command and renderer were removed;
- `review_static.js` and the browser manifest parity/import/export stack were removed;
- CLI `review --manifest` remains;
- the server verdict validator remains separate;
- where the permanent Node presentation tests now live;
- confirmation that Playwright and wheel proof remained intact;
- README/AGENTS cleanup performed;
- exact validation results;
- the pre-change retired-surface line count;
- final `git diff --numstat origin/main...HEAD` additions/deletions and net reduction;
- any surprising dependency that had to be decoupled.

Do not rewrite old worklog entries to erase the history of the static implementation.

---

# Required automated tests

The post-#51 suite must prove at least the following.

## Permanent presentation tests

In `tests/test_review_ui_js.py`:

1. IDs and hashes remain strings.
2. `compareIds` correctly orders values wider than JavaScript's safe integer range without `Number` coercion.
3. prototype-shaped data such as `__proto__` cannot pollute `Object.prototype`.
4. grouping matches Python/terminal `report.summarize`.
5. sorting and filtering remain correct.
6. hostile item names render as inert text nodes rather than executable markup.
7. surviving packaged source files retain the invisible/control-character safety guard where applicable.

## Manifest tests

Existing Python tests must continue to prove:

1. `review.parse_manifest` rejects malformed/untrusted manifests;
2. manifest fingerprint/version/ID rules remain unchanged;
3. `vault-cleaner review --manifest` still works.

Do not add a new JavaScript equivalent.

## Server verdict tests

Existing server tests must remain green for:

- strict payload keys/types;
- unknown/duplicate IDs where applicable;
- opaque string IDs;
- revision/fingerprint/state constraints;
- bounded input.

Do not alter those semantics as part of cleanup.

## Permanent browser tests

Keep exactly the two #90 browser tests:

1. hostile uploaded content remains inert in the live DOM;
2. bootstrap → upload → verdict → unset → final verdict → finalise → download works and verifies downloaded bytes.

Do not add replacement browser tests for the deleted static workflow.

## Packaging proof

`python scripts/check_wheel_install.py` must still prove a non-editable wheel serves the permanent root page and all three allow-listed assets.

---

# Focused verification sequence

Run focused checks as the deletion progresses:

```bash
ruff check src tests scripts
pytest -q tests/test_review_ui_js.py
pytest -q tests/test_review.py tests/test_cli_review.py
pytest -q tests/test_server_verdicts.py
```

If file names differ on the latest `main`, use the current permanent equivalents rather than inventing new suites.

Check JavaScript syntax for every surviving packaged JS asset:

```bash
python - <<'PY'
import shutil
import subprocess
from pathlib import Path

node = shutil.which("node")
if not node:
    raise SystemExit("node is required for this focused check")
for path in sorted(Path("src/vault_cleaner/ui").glob("*.js")):
    subprocess.run([node, "--check", str(path)], check=True)
PY
```

Verify the retired JS file is no longer among them.

---

# Manual verification

This ticket should not need a new exploratory browser design pass; #90 already owns and completed that acceptance layer.

Perform these lightweight checks:

1. `vault-cleaner --help`
   - `serve`, `report`, and `review` remain;
   - `review-html` is absent.

2. `vault-cleaner review --help`
   - `--manifest` remains documented.

3. `vault-cleaner serve --help`
   - server workflow remains available.

4. README
   - a user following the browser instructions reaches `serve`, not a removed command;
   - manifest documentation does not imply a browser/server manifest endpoint.

5. Package asset inventory
   - `review_static.js` is gone;
   - `review.css`, `review_ui.js`, `review_server.html`, `review_server.js` remain.

If Chromium is installed in the implementation environment, run the permanent browser gate:

```bash
VAULT_CLEANER_BROWSER_REQUIRED=1 \
pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results
```

If Chromium is not installed, do not weaken/skew the tests to avoid the dependency. Record the local skip and rely on the unchanged required CI browser job; Sol may choose to run the full browser gate during review.

Run the wheel proof locally if the environment supports building the isolated environment:

```bash
python scripts/check_wheel_install.py
```

---

# Luna completion gate

Before handing the branch to Sol high, run:

```bash
ruff check src tests scripts
pytest -q
python scripts/check_wheel_install.py
git diff --check
git status --short
git ls-files data/
git diff --numstat origin/main...HEAD
```

Also run the repository hygiene searches from step 8.

If a managed Chromium is available, also run the required browser test command shown above.

Confirm all of the following:

- `review-html` no longer exists as a CLI command.
- `src/vault_cleaner/review_html.py` is deleted.
- `src/vault_cleaner/ui/review_static.js` is deleted.
- there is no browser manifest reader/writer/import/export/handoff implementation.
- `review.parse_manifest` and CLI `review --manifest` remain.
- verdict API validation remains separate and strict.
- permanent Node tests still cover 64-bit IDs, prototype safety, grouping/filter/sort parity, and hostile text.
- exactly the permanent #90 browser tests remain; their download assertion is unchanged.
- the non-editable wheel proof still targets the three permanent server assets.
- no runtime dependency was added.
- no file under `data/` is tracked.
- `WORKLOG.md` has a dated #51 entry including the line-count audit.
- README no longer directs users to the static review page.
- AGENTS no longer carries obsolete browser-manifest-specific implementation gotchas.
- the branch is committed and pushed.
- **no PR has been raised**.

Provide Sol high with:

- branch name;
- base `main` SHA;
- commit SHA(s);
- implementation summary;
- files deleted;
- files modified;
- permanent tests preserved/moved;
- exact focused/full validation results;
- browser test result or explicit environment skip;
- wheel-proof result;
- `git diff --numstat` totals and net line reduction;
- hygiene-search results;
- known risks/uncertainties;
- any deviation from this plan.

---

# Sol high review prompt

Review the completed Luna xhigh implementation for issue #51 in `tonym999/vault-cleaner`.

**Do not raise a PR yet.**

This ticket is supposed to be a mechanical retirement of the unreleased static review surface after the M8 server parity gate. Review both deletion completeness and preservation of permanent behaviour.

## 1. Plan-conformance review

Confirm:

1. `review-html` is gone from the CLI.
2. `src/vault_cleaner/review_html.py` is gone.
3. `src/vault_cleaner/ui/review_static.js` is gone.
4. browser manifest parsing/building/import/export/handoff code is gone rather than moved elsewhere.
5. static-only tests are gone.
6. required presentation invariants remain covered in the permanent Node suite.
7. `review.parse_manifest` / `review --manifest` survive.
8. verdict API validation remains separate and strict.
9. README now points browser users to `serve`.
10. obsolete manifest-JS gotchas are removed from AGENTS while the general untrusted-input rule survives.
11. #90's Playwright tests, wheel proof, and CI browser job are not weakened.
12. the WORKLOG records the before/after line-count audit.
13. historical WORKLOG entries were not rewritten to make the old design disappear.

## 2. Engineering review

Look specifically for:

- dead imports/constants/parser branches left by `review-html`;
- hidden references to the deleted static adapter;
- browser manifest code quietly copied into `review_server.js` or `review_ui.js`;
- over-deletion of shared rendering behaviour;
- accidental loss of 64-bit ID or prototype-safety regression tests;
- hostile text rendered through unsafe HTML APIs;
- deletion of useful Python manifest tests merely because browser parity disappeared;
- any weakening of the server verdict validator;
- accidental package-data or wheel-proof regressions;
- README links/anchors that now point to removed sections;
- unnecessary churn in server/protocol/shared UI code;
- changes that violate the algorithmic scope rule.

## 3. Reviewer validation

At minimum rerun:

```bash
ruff check src tests scripts
pytest -q
python scripts/check_wheel_install.py
git diff --check
git ls-files data/
```

Inspect:

```bash
git diff --stat origin/main...HEAD
git diff --numstat origin/main...HEAD
git grep -n "review-html" -- ':!WORKLOG.md' || true
git grep -n "review_static.js" -- ':!WORKLOG.md' || true
git grep -n -E \
  'readManifest|readManifestText|readManifestBytes|readPastedManifest|decodeManifestBytes|fractionalNumberError|buildManifest|exportManifest|manifestJson|offerDownload|MANIFEST_KEYS|SNAPSHOT_KEYS|DECISION_KEYS' \
  -- ':!WORKLOG.md' || true
```

Run the required browser job locally if the review environment has managed Chromium; otherwise verify that CI still contains the unchanged required browser job and that the browser tests themselves were not weakened.

## Review outcome

If you find issues:

- identify each finding precisely;
- explain whether it is incomplete deletion, lost coverage, stale documentation, or scope expansion;
- specify the expected fix;
- require regression coverage where appropriate;
- keep fixes on the same branch;
- rerun focused and full validation;
- review again after fixes.

Mark the branch **ready for PR** only when the cleanup is complete, permanent coverage remains intact, and the diff stays within the intended mechanical scope.

Do not create the PR as part of the review unless Tony separately asks for it.

---

# Reusable Luna xhigh execution prompt

Implement issue #51 in `tonym999/vault-cleaner` using the attached Sol implementation plan.

The intended end state is one browser review surface (`vault-cleaner serve`) and one Python review-manifest validator (`review.parse_manifest`, reachable through `vault-cleaner review --manifest`). The temporary static `review-html` workflow and its browser manifest implementation/parity suite must be removed.

Follow the plan as the primary guide, but inspect the latest `main` before editing because the repository may have moved since the plan was written.

Apply the plan's **algorithmic scope rule** to every edit. This should be a deletion-dominated cleanup. Do not redesign server protocol, finalisation, lifecycle, persistence, the verdict API, review-manifest semantics, rules/report semantics, shared browser behaviour, Playwright scope, or packaging architecture.

Rules:

- branch from the latest `main`;
- read `AGENTS.md`, `PLAN.md`, #51 and its comments, #48, #50, #90, and recent #87–#90 worklog entries;
- inventory all static-surface references before deleting;
- map #51's required surviving invariants to permanent tests before removing old suites;
- remove `review-html`, `review_html.py`, `review_static.js`, and static/browser-manifest-only tests;
- preserve `review --manifest` and `review.parse_manifest`;
- preserve the separate strict verdict API validator;
- preserve the shared manifest-free presentation layer;
- preserve #90's two Playwright tests and non-editable wheel proof;
- update README, AGENTS, and WORKLOG;
- record the actual line-count reduction;
- run focused and full validation;
- commit and push the implementation branch;
- **do not raise a pull request**.

When complete, provide a concise handoff containing:

- branch name and base `main` SHA;
- commits;
- deleted/modified files;
- behaviour removed;
- permanent coverage preserved or relocated;
- exact validation results;
- browser result/skip;
- wheel-proof result;
- line-count audit;
- hygiene-search results;
- unresolved concerns or deviations.

The branch will be reviewed by Sol high before any PR is opened.

---

# Ticket-specific review decision

**Review path:** `standard — Sol high pre-PR review`

**Reason:**

Issue #51 is deliberately a mechanical retirement of an unreleased temporary surface after #90 established the permanent server UI, Playwright parity gate, and wheel-install proof. The intended implementation deletes duplicate browser-manifest code and static-only tests without changing protocol, persistence, lifecycle, security semantics, or shared rendering behaviour.

The main risk is **over-deletion**: losing permanent 64-bit ID, prototype-safety, grouping/filtering/sorting, hostile-input, browser-download, or packaging coverage. That risk is well suited to a careful Sol high plan-conformance and engineering review.

If Luna discovers that completion actually requires a substantive protocol, persistence, lifecycle, security, or shared-architecture change, the branch should return to Sol for replanning rather than silently escalating the ticket.
