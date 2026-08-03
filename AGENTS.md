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
  `data/cache/` and normally re-fetched only when the manifest version
  changes; an explicit `refresh=True` forces a full rebuild.
  Names map to *all* hash variants (base + enhanced share display names).
- DIM round-trips Notes, so `#vc-` hashtags stack across runs — always
  parse the *last* one (`report.reason_slug` does).
- Python's `csv` module writes CRLF by default: generate fixtures with
  `lineterminator="\n"` or `git diff --check` will flag them.
- In `review_html.py`, a literal `</script>` anywhere in `APP_JS`, `CSS`, or
  `BODY_HTML` silently truncates its own script element — even inside a JS
  comment, and **in any casing** (`</SCRIPT >` and `</script/` both end it,
  because HTML matches the end tag case-insensitively and terminates on
  whitespace or `/` too). Snapshot *data* is safe (`embed_json` escapes it);
  source text is not. A case-insensitive test guards all three constants; don't
  quote closing tags in comments.
- The review page validates manifests **and** so does `review.parse_manifest`.
  They must refuse exactly the same things, enforced by one payload table run
  through both in `test_review_html_js.py` — add cases there, not to a
  one-sided list, and vary *spelling* as well as type and presence. Note the
  browser must not be *stricter* either: cap text at 200 **code points**
  (`Array.from(text).length`), since Python's `len()` counts code points and
  UTF-16 units would reject names Python accepts.
- `JSON.parse` collapses `1`, `1.0`, and `1e0` into one double, so no
  post-parse JavaScript check can tell a float-spelled version from an int —
  but `json.loads` keeps `1.0` as a `float` and `_require_version` refuses it.
  Manifests are therefore checked on the **raw text** (`readManifestText` →
  `fractionalNumberError`), which is sound because a manifest has no fractional
  field. Never run that scan over the embedded snapshot: armor scores really are
  floats (`112.0`).
- Manifests are compared **bytes in, verdict out** (`readManifestBytes` vs
  `parse_manifest(path)`) because the decode itself diverged:
  `FileReader.readAsText` substitutes U+FFFD for malformed UTF-8 *and* strips a
  leading BOM, while `Path.read_text` does neither. Only
  `TextDecoder("utf-8", {fatal: true, ignoreBOM: true})` agrees with Python —
  `ignoreBOM: true` (meaning "keep the U+FEFF") is required, or the BOM
  divergence simply replaces the U+FFFD one.
- **Every** import entry point must be exported and in the parity table, not
  just the deepest validator: the file input (`readManifestBytes`) and the paste
  box (`readPastedManifest`). A divergence hid in the paste path for three rounds
  purely because its normalisation sat in an un-exported click handler. Anything
  that touches input before validation belongs in the exported layer.
- **JS `trim()` is not JSON whitespace** — it removes U+FEFF, U+00A0, U+2028,
  and U+3000, all of which `JSON.parse` and `json.loads` refuse. Never trim
  before validating; trim only to test for emptiness.
- Four rounds of review found the same bug at four places, because the two
  validators were compared one layer too high (object, then text, then bytes)
  and then on only one of two paths. Compare at the outermost layer the real
  entry points use, cover *every* entry point, add *accept* cases at each layer
  (each tightening risked over-rejecting names Python accepts), and when you fix
  a divergence on one path, fix its siblings in the same change.
- Scan for invisible characters at the **byte** level. `str.splitlines()` splits
  on U+2028, so a line-based scan cannot see the character it is hunting for.
- `pip install -e .` leaves a `build/` tree (gitignored). Check
  `git status` before committing anyway — that rule saved `data/` once
  and failed on `build/` once.

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

1. Pick a ticket from the [issue board](https://github.com/tonym999/vault-cleaner/issues);
   milestones M2–M5 are ordered — respect dependencies noted in each issue.
2. Branch from `main`, keep `pytest` green, PR referencing the issue.
3. Append a dated entry to [WORKLOG.md](WORKLOG.md) in the same PR: what was
   done, decisions made, anything surprising the next agent should know.
