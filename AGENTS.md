# Agent guide

Read this before touching the repo. [PLAN.md](PLAN.md) is the spec;
[WORKLOG.md](WORKLOG.md) is what has actually happened so far.

## Setup & commands

```bash
python3 -m venv .venv                # if .venv doesn't already exist
.venv/bin/pip install -e ".[dev]"    # dev extra = the exact toolchain CI gates on
.venv/bin/ruff check src tests scripts   # must pass before every commit
.venv/bin/pytest -q                  # must pass before every commit
.venv/bin/vault-cleaner roundtrip --item "NAME"   # dry-run pipeline check
```

CI also rejects tracked files under `data/`, whitespace or line-ending errors
reported by `git diff --check`, and pull requests without a `WORKLOG.md` entry.
The worklog requirement has no escape hatch: every pull request records what
changed, including CI-only changes and reverts.
An intentional whitespace or line-ending fixture exception must use a narrowly
scoped `path -whitespace` rule in `.gitattributes`, documented in the worklog.

Regenerate the fake-data report golden only when an intentional snapshot
schema or fixture change requires it:

```bash
python scripts/regenerate_report_snapshot.py
```

(Any interpreter with the project installed works — `.venv/bin/python` on
POSIX, `.venv\Scripts\python` on Windows. The script writes the file itself
with UTF-8 bytes and LF endings; shell redirection was the old failure mode,
since PowerShell's `>` re-encodes and re-terminates lines — #45.)

Python 3.12, pandas, `tomllib`, pytest. Runtime deps are pandas and (from M8, added by #49) Flask 3.1 — exactly; anything further needs a ticket amending this line. Dev/test tooling (pytest, ruff, Playwright) stays out of the runtime set.

## Hard rules

- **Never commit anything under `data/`** or any real vault export. This repo
  is public; `data/` holds personal Bungie account data. `.gitignore` covers
  it — do not weaken that, and check `git status` before committing.
- **Access CSV columns by header name, never by position.** DIM's export
  format drifts between releases. Schema checks in `parse.py` must fail
  loudly, not silently coerce.
- **Dry-run is the default.** Nothing writes to `data/out/` without an
  explicit `--write`. The tool never deletes user-owned inputs, exports,
  durable overrides, or output. The local review server may remove only
  server-owned temporary staging, candidate, or retired directories that it
  created itself; request content can never provide cleanup paths, and this
  exception authorizes no broader deletion.
- **Every junk decision needs a reason** in `Notes` (e.g.
  `#vc-junk: dupe-lower`), searchable as a hashtag in DIM.

## Gotchas (learned the hard way)

- DIM wraps instance ids in *literal* quotes (`"""6917…"""` raw) to protect
  the 64-bit value from spreadsheets. `parse.py` strips them on load;
  `report.py` re-adds them on write. Preserve this round trip.
- Item names collide across seasonal reissues (same name, different `Hash`).
  Dupe grouping must use `Hash`, never `Name`.
- Ghost exports have no `Type` column — schemas differ per export kind.
- Empty CSV cells are empty strings (`keep_default_na=False`), never NaN.
- **Measure the real export before designing a rule.** Every spec-first
  rule design died on real data; examples below all came from measuring.
- Ghost `Energy Capacity` / `Masterwork Tier` are empty on every shell
  (retired system) — that's why the ghost pass is protection-only, no
  ranking. Don't "fix" the empty columns.
- Armor 3.0 tier-5 pieces all share a fixed 30+25 stat spike (~75 base
  total): spike/total scoring discriminates nothing; only build-alignment
  weights do. Armor scores are normalized to the `Total (Base)` scale.
- Perk name→hash comes from Bungie's public static manifest, cached in
  `data/cache/` and normally re-fetched only when the manifest version
  changes; an explicit `refresh=True` forces a full rebuild.
  Names map to *all* hash variants (base + enhanced share display names).
- DIM exports crafted weapons as `Crafted=crafted`, not boolean `true`;
  ordinary weapons use `false`, and empty `Crafted` is explicitly not crafted.
  An empty `Crafted Level` on a crafted row is unknown and hard-protected;
  non-empty malformed levels must fail schema validation. Use the focused
  crafted-state helper rather than generic `is_true()`; unknown non-empty
  crafted-state tokens must fail schema validation instead of disabling the
  hard rail.
- Weapon exact-dupe identity uses the complete named `Perks N` prefix before
  the first measured tracker boundary (`Kill Tracker` or `Crucible Tracker`,
  casefolded after removing one trailing selected `*`); tracker/current
  socket, mod, masterwork, and memento cells are mutable and excluded.
  Unknown/future names merely ending in `Tracker` remain identity cells until
  a later measured boundary, or make the row ungroupable when no measured
  boundary exists. Selected trailing `*` markers are normalized away, while
  complete perk names (including ordinary names beginning with the literal
  `Enhanced` followed by one separator space) are retained. Missing boundaries
  or prefixes fail safe as ungroupable rather than collapsing same-Hash rolls.
  DIM's `Perks N` header width is
  export-dependent: `Perks 0` is the minimal schema invariant, and any
  contiguous `0..N` range is accepted when the row has a complete prefix and
  tracker boundary. Perk cells stay whole (commas are not guessed as option
  separators); adjacent cells are the measured multi-option representation.
  Comma-bearing cells containing either measured tracker label are ungroupable
  regardless of component order or marker placement. Wishlist matches protect
  trash decisions but do not rank exact duplicates, whose order is Tier >
  Masterwork Tier > Crafted Level >
  stat total > opaque Id.
- DIM round-trips Notes, so `#vc-` hashtags stack across runs — always
  parse the *last* one (`report.reason_slug` does).
- Python's `csv` module writes CRLF by default: generate fixtures with
  `lineterminator="\n"` or `git diff --check` will flag them.
- Review manifests and server payloads are untrusted input. Validate strictly
  at every entry point, at the outermost layer that entry point uses, and when
  a divergence is fixed on one sibling path, fix the sibling paths in the same
  change. Keep review-manifest validation in `review.py` distinct from the
  server's verdict-request validator.
- Scan for invisible characters at the **byte** level. `str.splitlines()` splits
  on U+2028, so a line-based scan cannot see the character it is hunting for.
- `pip install -e .` leaves a `build/` tree (gitignored). Check
  `git status` before committing anyway — that rule saved `data/` once
  and failed on `build/` once.

## Server lifecycle checklist

- Treat close as a terminal transition, never as a reset: revisions stay
  monotonic, and closed sessions cannot allocate uploads or expose reports.
- Structure upload replacement as explicit prepare → commit/adopt → retire
  phases. Rollback owns candidates only through preparation and ends before
  adoption; retirement is post-commit best-effort housekeeping.
- Keep cleanup retryable and retain failed server-owned paths privately for a
  later attempt. Cleanup failure must not prevent the shutdown callback or
  server socket close from running.
- Delete only temporary staging, candidate, or retired directories created and
  owned by the server. Request content must never supply a cleanup path.
- Give server tests explicit test-owned filesystem paths, normally backed by a
  module-local `tmp_path` helper or fixture. Test a default path only when
  forwarding or default-path behaviour is the subject of that test.

## Conventions

- Test fixtures in `tests/fixtures/` are pinned to real export headers but
  contain only fake items. Regenerate the header from a fresh export if DIM's
  format changes; never paste real rows.
- Rule thresholds live in `config.toml`, not in code.
- Add every new rule-consumed config key to `report_run._decision_config` so
  snapshots and fingerprints cover it. The recursive DEFAULTS coverage test
  must fail until the key is projected; `paths`, `wishlists`, and `manifest`
  are explicit exclusions because their external bytes have separate identities.
- Bump `report_run.RULESET_VERSION` whenever rule ordering or decision
  semantics change. Do not bump it for snapshot-only schema or presentation
  changes. It is baked into the fingerprint, so a bump correctly invalidates
  every persisted review manifest.
- "Manifest" means two unrelated things: `manifest.py` is Bungie's static
  manifest (perk name→hash), `review.py` is the *review* manifest handed back
  by the UI. Keep the distinction explicit in names and messages.
- Review manifests and `data/overrides.json` are untrusted input. Validate
  strictly (reject unknown keys, unknown versions, duplicate ids), never read
  a filesystem path out of their content, and keep `Id`/`Hash` opaque strings.
- Rules live in `src/vault_cleaner/rules/`, one module per pass
  (weapons.py, dupes.py, armor.py, armor_dupes.py, armor_close.py,
  ghosts.py — a new pass gets a new module); ordering is defined in
  PLAN.md and earlier rules win.

## Workflow

1. Pick a ticket from the [vault-cleaner project board](https://github.com/users/tonym999/projects/3);
   milestones in PLAN.md are ordered — respect dependencies noted in each issue.
2. Branch from `main`, keep `pytest` green, PR referencing the issue.
3. Append a dated entry to [WORKLOG.md](WORKLOG.md) in the same PR: what was
   done, decisions made, anything surprising the next agent should know.

## Creating issues

When creating a repository issue:

1. Check the [vault-cleaner project board](https://github.com/users/tonym999/projects/3)
   and [PLAN.md](PLAN.md) first. Apply the most specific existing type label:
   `bug`, `enhancement`, `documentation`, or `question`. Use `maintenance`
   for CI, cleanup, dependency, or internal-quality work that does not fit
   those types. Use `icebox` only when the work is explicitly out of scope in
   `PLAN.md`; do not invent a one-off label.
2. Assign an existing relevant milestone when one exists. Do not create a
   one-off milestone. If the issue depends on other work, state the dependency
   in its body (for example, `Depends on #49`) and add the corresponding
   GitHub issue dependency link where the repository/project UI supports it;
   verify both the dependency text and link before treating the issue as ready.
3. Add the new issue to the project board and set its Status to `Todo`.
   Repository auto-add is enabled as a backstop, not a substitute for this
   explicit step.
4. Verify both project membership and the `Todo` status after creation before
   treating the issue as complete. Recheck the type/scope label and milestone
   at the same time.
