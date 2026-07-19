# Agent guide

Read this before touching the repo. [PLAN.md](PLAN.md) is the spec;
[WORKLOG.md](WORKLOG.md) is what has actually happened so far.

## Setup & commands

```bash
python3 -m venv .venv                # if .venv doesn't already exist
.venv/bin/pip install -e ".[dev]"    # dev extra = the exact toolchain CI gates on
.venv/bin/ruff check src tests       # must pass before every commit
.venv/bin/pytest -q                  # must pass before every commit
.venv/bin/vault-cleaner roundtrip --item "NAME"   # dry-run pipeline check
```

Python 3.12, pandas, `tomllib`, pytest. No other runtime deps for v1 — don't
add any without a ticket saying so.

## Hard rules

- **Never commit anything under `data/`** or any real vault export. This repo
  is public; `data/` holds personal Bungie account data. `.gitignore` covers
  it — do not weaken that, and check `git status` before committing.
- **Access CSV columns by header name, never by position.** DIM's export
  format drifts between releases. Schema checks in `parse.py` must fail
  loudly, not silently coerce.
- **Dry-run is the default.** Nothing writes to `data/out/` without an
  explicit `--write`. The tool never deletes anything, anywhere.
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
  `data/cache/` and re-fetched only when the manifest version changes.
  Names map to *all* hash variants (base + enhanced share display names).
- DIM round-trips Notes, so `#vc-` hashtags stack across runs — always
  parse the *last* one (`report.reason_slug` does).
- Python's `csv` module writes CRLF by default: generate fixtures with
  `lineterminator="\n"` or `git diff --check` will flag them.
- `pip install -e .` leaves a `build/` tree (gitignored). Check
  `git status` before committing anyway — that rule saved `data/` once
  and failed on `build/` once.

## Conventions

- Test fixtures in `tests/fixtures/` are pinned to real export headers but
  contain only fake items. Regenerate the header from a fresh export if DIM's
  format changes; never paste real rows.
- Rule thresholds live in `config.toml`, not in code.
- Rules live in `src/vault_cleaner/rules/`, one module per pass
  (weapons.py, dupes.py, armor.py, armor_dupes.py, armor_close.py,
  ghosts.py — a new pass gets a new module); ordering is defined in
  PLAN.md and earlier rules win.

## Workflow

1. Pick a ticket from the [issue board](https://github.com/tonym999/vault-cleaner/issues);
   milestones M2–M5 are ordered — respect dependencies noted in each issue.
2. Branch from `main`, keep `pytest` green, PR referencing the issue.
3. Append a dated entry to [WORKLOG.md](WORKLOG.md) in the same PR: what was
   done, decisions made, anything surprising the next agent should know.
