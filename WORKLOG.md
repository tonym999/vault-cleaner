# Worklog

Newest first. One entry per working session: what happened, decisions made,
surprises the next agent should know about.

## 2026-08-22 — shared proposal retention and manifest-free verdict merge (#63)

- Added pure `review_session.py` primitives: `same_proposal` compares only
  `id`, `kind`, `hash`, `action`, and `reason`; `retain_verdicts` keeps only
  unchanged full identities and reports changed or missing ids as discarded.
- Added the manifest-free `merge_verdicts` core. `review.merge_manifest` is a
  thin adapter that preserves additive vetoes, run-owned metadata, unchanged
  timestamps, and the existing CLI diagnostics.
- Promoted the strict review-input helpers/constants (`check_keys`,
  `require_text`, `require_id`, `require_kind`, `MAX_TEXT`, `ID_RE`) while
  retaining their validation behavior. The five-field identity rule remains
  cross-fingerprint retention only; `classify` and merge still compare
  `(action, reason)`.
- No ruleset or snapshot change: `RULESET_VERSION` remains 1 and the report
  golden remains byte-identical. Ruff and the full test suite pass.
- Follow-up: made proposal identity access fail loudly for missing fields,
  unified verdict-entry normalization for retention and merge (including a
  single server entry), and rejected non-string ids without coercion.
- Removed the obsolete private validator aliases, centralized veto ordering
  and UTC timestamp formatting, tightened source-level consumer coverage, and
  kept the adapter's legacy diagnostic payloads at its boundary.

## 2026-08-22 — in-memory CSV rendering and DIM export byte loaders (#62)

- Added `render_import_csv`, sharing validation, DIM Id quoting, column
  filtering, UTF-8 encoding, and CRLF serialization with `write_import_csv`.
  The writer now renders completely before opening its destination while
  retaining its existing signature and row-count return; a regression pins
  existing outputs byte-identical and fresh nested destinations untouched when
  a later row is invalid.
- Added strict UTF-8 byte loaders for weapons, armor, and ghosts, with a
  separate `ExportDecodeError` and fixed non-path source labels. Shared
  schema and armor-field validation keeps path diagnostics unchanged and
  prevents uploaded-schema errors from exposing staging paths.
- Added renderer byte-parity and parser path/bytes parity coverage for plain
  and BOM exports, schema/duplicate failures, malformed armor fields, and
  undecodable bytes.

## 2026-08-09 — M8 server transport and security envelope (#64)

- Added Flask 3.1 as the second and only other runtime dependency and added
  `vault-cleaner serve`: it pre-warms configured wishlist and Bungie manifest
  caches before binding, listens only on `127.0.0.1` with an OS-selected port
  by default, prints a one-time bootstrap URL, and runs Werkzeug threaded
  behind one session mutation lock.
- Established `server/` primitives for the later M8 children: named request
  limits, one registered JSON error contract, the idle session metadata
  builder, a `@serialized` check-and-apply decorator, and an idempotent
  `Session.close()` lifecycle seam. Upload, verdict, reset, and finalize routes
  are present but remain idle-state placeholders for #65–#67; there is no
  manifest endpoint and no report logic in this ticket.
- The bootstrap credential is separate from the session credential, expires
  after five minutes, is compared in constant time and consumed once, then
  exchanged for a host-only `HttpOnly; SameSite=Strict; Path=/` cookie before
  a 303 redirect to the clean root URL. Every request validates the exact
  bound Host, every POST validates the exact Origin, every response is
  `no-store`/`no-referrer`, and none carries CORS allow headers.
- Assets are registered as exact allowlisted URL rules backed by byte
  providers; the placeholder page is an inline Python constant, so there is
  no catch-all path or filesystem mapping to traverse. A custom Werkzeug
  handler redacts the complete bootstrap query from request logs.
- Coverage includes the Flask client security matrix and error schemas plus a
  real threaded loopback exchange proving actual-port bootstrap, log
  redaction, response-before-shutdown ordering, and clean server exit. Runtime
  dependency and console-script metadata are pinned. `RULESET_VERSION` and
  report snapshots are unchanged because no decision semantics changed.
- Review follow-up made credential comparison safe for arbitrary Unicode,
  rejects a present noncanonical Origin on every method, snapshots session
  metadata under the mutation lock, canonicalizes port 80, reserves server
  routes against asset collisions, and adds `nosniff`, framing, and CSP
  headers. Server imports are lazy for non-server CLI commands and tests now
  cover those boundaries with isolated config paths and deep state snapshots.
  Werkzeug remains Flask's transitive implementation detail, preserving the
  ticket's exact two-dependency runtime contract; no ruleset bump was needed.

## 2026-08-09 — wishlist cache stat errors (#72)

- `wishlist.fetch` now treats `OSError` while reading cache metadata as a
  stale/unavailable cache and continues to the existing download path instead
  of leaking the raw filesystem error.
- Regression tests cover a cache whose `stat()` fails before a successful
  redownload, and the no-cache case still raises the existing clean
  `WishlistError` when the download also fails.
- Review follow-up covers `stat()` failure followed by download failure falling
  back to a readable stale cache, and an unreadable cache raising the clean
  "no usable cached copy" error.

## 2026-08-09 — DIM CSV BOM regression coverage (#47)

- Pinned the existing weapons-loader behaviour for both ordinary UTF-8 DIM
  exports and exports with a leading UTF-8 BOM. The regression uses the same
  fake DIM fixture in both cases and verifies that header parsing, row loading,
  and quoted instance-id normalisation remain identical.
- No runtime behaviour or decision semantics changed; this closes the final
  test-coverage acceptance criterion on the #47 umbrella.

## 2026-08-08 — CI hygiene review follow-up (#60)

- Tightened the worklog gate from “the path changed” to “the PR added a dated
  entry,” so deleting, reformatting, or otherwise touching `WORKLOG.md` no
  longer satisfies the audit-trail requirement. Both PR-diff checks now use
  the event's base branch instead of assuming every PR targets `main`.
- Made the workflow's read-only token permission explicit and stopped both
  checkouts from persisting credentials that neither job uses.
- Documented the narrow `.gitattributes` escape valve for a deliberately
  whitespace-sensitive fixture; exceptions belong on exact paths and in the
  worklog rather than weakening the repository-wide check.

## 2026-08-08 — deterministic zero-age cache bypass (#70)

- Made `max_age_days=0` unconditionally bypass the fresh-cache fast path for
  both the Bungie manifest perk map and wishlist downloads, even when
  filesystem timestamp precision leaves a newly written cache mtime slightly
  ahead of the current clock. Positive limits retain their existing freshness
  behavior, and both contracts are documented at their loader boundaries.
- Pinned the Windows failure with actual future-dated cache mtimes rather than
  a process-wide clock fake. Separate tests retain the ordinary stale-cache
  fallback coverage; failed forced requests still return cached content with
  the existing warning.
- `RULESET_VERSION` is unchanged: this fixes cache refresh control flow and
  does not change rule ordering or decision semantics.

## 2026-08-03 — CI repository hygiene gates (#60)

- Added a platform-independent `hygiene` job that rejects tracked files under
  `data/` on both CI triggers and checks pull-request diffs for whitespace,
  line-ending errors, and a `WORKLOG.md` change.
- The job checks the full PR range from its merge base, so checkout fetches the
  complete history. Each failure identifies the offending path or the missing
  `WORKLOG.md` file without requiring a local reproduction.
- Kept the worklog gate unconditional. CI-only changes and reverts still need
  a short audit-trail entry, so a bypass label would weaken the stated workflow
  without a current use case.
- Proved all three failure paths in scratch commits that did not land: a
  force-added `data/private-vault.csv`, a two-line CRLF fixture, and a clean PR
  with no worklog change each failed with the expected offending path. A
  scratch commit containing this implementation passed all three checks.

## 2026-08-02 — clean write-side filesystem errors (#43)

- Added one CLI write boundary that converts ordinary `OSError` failures into
  the existing `error: <message>` convention and exit code 1. All CSV-writing
  commands now use it, as does `review-html`, so an unwritable destination no
  longer produces a traceback from any `--write` surface.
- Preserved review's deliberate write order: overrides are saved before the
  derived CSV. A failed override save reports that nothing was written; a CSV
  failure after a successful save reports that the overrides are durable and
  only the CSV must be regenerated. A review run without a manifest has no
  override write and reports that nothing was written when its CSV fails.
- Regression coverage injects filesystem failures into every command shape
  and separately pins both review outcomes, including the persisted override
  file in the partial-write case.

## 2026-08-02 — configured-path maintenance follow-up (#58)

- Documented the deliberate path-base split from #55: when the requested
  config is missing, built-in relative paths retain their historical
  current-working-directory meaning; relative paths resolve against the config
  file's parent whenever that file exists — built-in defaults included.
- Both `load_config` and the paths-only `load_paths_config` reject non-string
  `[paths]` values cleanly. The paths-only accessor remains intentional so
  `roundtrip` and `ghosts` are not blocked by unrelated armor validation.
- Combined `report`, `review`, and `review-html` runs now reuse the paths
  configuration already loaded for input discovery when resolving their
  output, avoiding a third read of the same config file.

## 2026-07-26 — deterministic DIM export discovery (#56)

- Added one discovery boundary for all three DIM export kinds. Omitted inputs
  accept the exact filename or either browser-numbered spelling only when it
  is the sole match; multiple matches refuse with every filename and tell the
  user to move/delete stale copies or pass the intended file explicitly.
  Candidates are sorted by filename and timestamps are never inspected.
- Explicit single-command `--input` and combined `--weapons` / `--armor` /
  `--ghosts` paths bypass discovery entirely. For PR #54's later rebase, the
  discovery directory is a separate `run_report` argument: its configured
  `input_dir` must be passed there rather than collapsed into an exact path,
  or the configured default would be mistaken for an explicit input.
- Combined runs resolve every omitted kind before hashing or loading any CSV,
  so an ambiguity in a later kind cannot produce a partial read first. Zero
  matches retain the partial-report contract with an expected-name/pattern
  warning; ambiguity is always fatal, and all-zero errors report every
  expected name and pattern.
- Snapshot warnings keep the full directory in the path field, where snapshot
  sanitisation already reduces it to a basename; their reason text contains
  only the filename/pattern. Fingerprints, the golden snapshot, snapshot
  schema, and ruleset version are unchanged because selected source bytes
  already carry the decision identity.
- Regression tests cover every kind, both numbered spellings, exact-plus-
  numbered ambiguity, stable actionable errors, no newest-wins behaviour,
  explicit bypasses, partial/all-missing reports, clean CLI failures, and
  refusal before any loader or fingerprint read.
- Review follow-up made filename matching ASCII-digit-only and kept it
  deliberately case-sensitive. DIM documents these export names in lowercase,
  and identical matching on case-sensitive and case-insensitive filesystems is
  more predictable than inheriting platform-specific path semantics.
- Empty explicit paths now fail with a clean CLI error instead of resolving to
  the current directory and reaching a loader traceback. Partial-report
  warnings use a readable browser-numbered example rather than exposing the
  regular expression; direct missing/ambiguity diagnostics retain the exact
  pattern for troubleshooting, with command-neutral explicit-path guidance.
- Regression coverage now includes OS-native displayed paths for Windows,
  matching-name directories, directory scan permission failures, Windows/WSL
  `Zone.Identifier` sidecars, Unicode digits, case variants, empty explicit
  paths, and the simplified single-command loader map.

## 2026-07-26 — Windows test suite fixes (#45)

- All four causes confirmed before coding, three of them invisible on Linux:
  - `subprocess.run(text=True)` decodes node's UTF-8 output with the *locale*
    encoding (cp1252 on the reporter's machine) — the `Ãœ`/`ï»¿` mojibake in
    the failure output pins cp1252 specifically. Fixed with
    `encoding="utf-8"` on all three harness calls; a regression from #44 that
    Linux's UTF-8 default masked.
  - `Path.write_text()` translates `\n` → `\r\n` on Windows, so a test
    hashed bytes it never wrote. Both digests reproduced exactly (LF hash =
    asserted, CRLF hash = observed). Fixed with `newline=""` on the one
    digest-sensitive write.
  - Windows temp paths inside TOML *basic* strings hit `\U` as an escape and
    fail to parse. First fixed with TOML *literal* (single-quoted) strings,
    which review caught as correct-but-narrow: a literal string cannot contain
    an apostrophe, so `C:\Users\O'Brien\...` would have broken the same way
    `\U` did. Now encoded with `json.dumps(str(path))` — JSON string escaping
    *is* valid TOML basic-string escaping, and `ensure_ascii` keeps the
    generated config ASCII-safe for non-ASCII profile names. The test's
    directory is named `pri'vate` so the Windows leg exercises apostrophe and
    backslash together, with no extra test.
  - `core.autocrlf=true` checkout translated fixture bytes (`i/lf w/crlf`,
    measured by the maintainer), so every sha256-of-bytes comparison failed.
    Fixed with `.gitattributes` pinning `tests/fixtures/** -text`. Existing
    Windows clones re-materialise with `git checkout HEAD -- tests/fixtures`.
- New meta-test fails a translated checkout with the actual cause and the fix
  command, instead of an opaque hash mismatch; revert-checked by CRLF-ing a
  fixture copy.
- Golden regeneration is now `python scripts/regenerate_report_snapshot.py`.
  The old documented one-liner was POSIX-only twice over: `.venv/bin/python`
  does not exist on Windows, and PowerShell's `>` re-encodes and re-terminates
  redirected output, which would have corrupted the golden's bytes. Review
  caught that this PR *claimed* a portable regen path while shipping a command
  its own target platform cannot run — the same overclaim shape as the #52
  WORKLOG fix. The script writes via `write_bytes` so no platform can
  translate the endings, and deliberately does not import
  `tests.test_report_run`: a maintenance command should not depend on a test
  module. `test_regeneration_script_reproduces_the_committed_golden` pins the
  duplicated recipe against the committed bytes on both CI platforms, so
  byte-stability is a checked invariant rather than a claim.
- `scripts/` is in the ruff scope (AGENTS.md and CI) so the helper is linted
  like everything else.
- CI now runs the suite on `windows-latest` and `ubuntu-latest`
  (`fail-fast: false`). Three of the four causes could recur silently without
  the Windows leg; node is preinstalled on both runner images so the JS tests
  run everywhere.

## 2026-07-26 — M8 adopted: loopback review server (PLAN amendment, #46)

- PLAN.md now plans the localhost bridge instead of listing it as a fallback
  risk. The evidence for the pivot is PR #44: the static artifact makes the
  browser a second implementation of the review-manifest contract, and five
  review rounds were spent closing divergences between it and
  `review.parse_manifest` — object shape, number spelling, UTF-8/BOM decoding,
  then `trim()` on the paste path. A server removes the duplicated manifest
  parser outright; upload/session/verdict/download become explicit,
  Python-owned contracts instead.
- #48 decided **Option A**: the interactive static page retires once the
  server UI proves parity (#50), removed in #51. No deprecation period —
  `review-html` merged after the `v0.2.0` (M6) release and has never shipped
  in a tag. No *known* external usage was identified (public repo, zero
  forks/stars/watchers) — that cannot prove nobody ran it from a clone, so
  the decision rests on the provable fact: it never shipped in a release.
- Framework decided on #49: **Flask 3.1**, the first runtime dependency beyond
  pandas. Recorded with the full cost stated — Flask brings Werkzeug, Jinja2,
  itsdangerous, click, blinker, MarkupSafe (~7 packages, not 2). The
  dependency rule in PLAN.md and AGENTS.md is amended to "pandas and Flask
  3.1, exactly"; `pyproject.toml` changes land with the server code in #49,
  not this docs change. The security-critical work (bootstrap token exchange,
  exact Host/Origin validation, revision checks, atomic finalize) is
  application code under any framework — Flask replaces plumbing, not
  protocol.
- Browser testing decided on #50: **Playwright, dev/test-only**, separate
  Ubuntu CI job, skip-when-absent, no retries to hide flakes. The runtime set
  is untouched by test tooling.
- #38 amended in place: armor what-if variants are **precomputed in Python**;
  the browser switches among bounded server-produced variants. Recomputing
  scores client-side would re-implement `rules/armor.py` in JavaScript — the
  #44 failure mode on far harder logic.
- Measured on real DIM downloads for #47: no save-as dialog; the browser
  writes the expected fixed filename and appends a number when it exists. So
  the ambiguous case (stale exact name beside newer numbered copy) is the
  normal result of exporting twice, which validates refusing ambiguity even
  when the exact name is present.

## 2026-07-26 — configured CLI input/output paths (#47)

- Taught the existing CLI defaults to respect `[paths].input_dir` for known
  DIM export filenames and `[paths].output_dir` for generated import/review
  artifacts. Explicit CLI paths still win, so scripted invocations keep their
  current behaviour.
- Added `--config` to `roundtrip` and `ghosts` so those commands can use the
  same path defaults as the rest of the CLI.
- Configured input directories still go through the existing export discovery
  path, preserving ambiguity refusal for omitted inputs.

## 2026-07-25 — self-contained static HTML review UI (#37)

- New `review_html.py` renders one portable file: inline CSS/JS, the #35
  snapshot embedded as an inert `application/json` data block, and a
  `default-src 'none'` CSP so the page physically cannot fetch or exfiltrate
  anything. No runtime dependency, no asset file (the CSS/JS are Python string
  constants, so packaging needed no `package-data` change).
- Chose a **new `review-html` subcommand** over `review --output x.html`.
  `review --output` already means "the reviewed CSV", and the issue's own
  requirement is that the two write actions stay unambiguous. Each command now
  owns exactly one output, and `report --write` is untouched.
- **A literal `</script>` in the app source truncates its own script element.**
  Found the hard way: an explanatory comment quoted a closing script tag as an
  example of hostile input, which silently cut the shipped script in half — the
  page still parsed, just missing most of its code. Now guarded by a test over
  `APP_JS`/`CSS`/`BODY_HTML`. Snapshot *data* is safe by construction:
  `embed_json` escapes `<`, `>`, `&`, U+2028, and U+2029 to `\uXXXX`, which is
  value-identical JSON but cannot spell a tag or a comment delimiter.
- The page's pure logic is exported under CommonJS when `module` exists and
  only touches the DOM otherwise. That is what lets `test_review_html_js.py`
  extract the script from a *generated artifact* and drive the real filtering,
  grouping, counting, and manifest code under node — skipped when node is
  absent, so nothing new is required to `pip install`.
- Grouping is asserted equal to `report.summarize`'s group headers, string for
  string and in order, so the page and the terminal cannot drift. That works
  because the snapshot's `action`/`reason` are the same pair `reason_slug`
  re-derives from `note`; a test pins that invariant too.
- Ids and hashes never touch a JS number. `compareIds` orders decimal uint64
  strings by length then lexicographically (a test shows `Number()` ties
  2**64-1 and 2**64-2), and `itemsFromSnapshot` *throws* on a non-string id
  rather than coercing one.
- Data-keyed maps are all `Object.create(null)`. An item literally named
  `__proto__` is in the hostile fixture: with a plain `{}` accumulator its
  count assignment is a silent no-op and the whole group vanishes from the
  filter dropdown, which is the failure a test now pins.
- Exported `name` is clipped to 200 **code points** — `review.parse_manifest`
  rejects longer strings, and slicing UTF-16 units could leave half a
  surrogate pair. The 260-character fixture name proves the cap is needed.
- Verified for real, not just in tests: headless Chromium opened the file over
  `file://` with the CSP live, vetoed rows through the actual buttons, approved
  one via the `a` key (focus survives, because a verdict change repaints the
  row in place instead of rebuilding the table), exported, re-imported, and
  `localStorage` worked under `file://`. That exported manifest then went
  through `vault-cleaner review --manifest ... --write` and produced the
  reviewed CSV with exactly the vetoed rows suppressed.
- `SNAPSHOT_SCHEMA_VERSION`/`RULESET_VERSION` deliberately unchanged: no
  decision semantics moved, and bumping the ruleset would invalidate every
  persisted veto for a presentation-only feature.
- Known gap, deliberate: `review-html` does not pre-mark items that already
  have persisted vetoes in `data/overrides.json`, for the same reason `report`
  does not apply them — the page shows what the rules propose. Re-vetoing is
  harmless (merges are additive), but a future `--overrides` flag to seed the
  page's verdicts would be a real ergonomic win.
- Also left out: no browser-side threshold what-if controls. That is #38, and
  every knob a user could turn there is inside the fingerprint, so a what-if
  that changed decisions must not export a manifest against the original run.
- Review follow-up (PR #44), four findings, all accepted:
  - The browser's `readManifest` claimed parity with `parse_manifest` and did
    not have it: **7 of 8** malformed manifests Python refuses, it accepted —
    extra `snapshot.output_path`, extra root and decision keys, a decision of
    only `{id, verdict}`, a 300-character `name`, a numeric `kind`, an empty
    `generated_at`. Import then stored and autosaved the verdicts and reported
    success, so the page said the review was restored and Python rejected the
    same file later. Now mirrors `_check_keys`/`_require_text`/`_require_version`
    in `parse_manifest`'s order, and validates structure *before* comparing
    the fingerprint, so a malformed file says what is malformed.
  - Text length is capped in **code points** (`Array.from(text).length`), not
    UTF-16 units. Python's `len()` counts code points, so a 200-emoji name is
    legal there and naive `.length` would have rejected it — the browser must
    not be stricter than Python either. Both directions are pinned.
  - Parity is now enforced by **one table of ~40 payloads run through both**
    `readManifest` (under node) and `parse_manifest` + `check_manifest_matches`,
    asserting they agree on accept/refuse. Hand-kept case lists on each side
    are exactly how the gap appeared. Both Python calls are needed: a
    well-formed manifest for another run is accepted by `parse_manifest` and
    only refused by `check_manifest_matches`, while the browser does both at
    once. Confirmed non-vacuous by re-running it against the old reader.
  - The `</script>` source guard was case-sensitive. Chromium confirms a
    mixed-case `</SCRIPT >` inside a comment terminates the element and the
    rest of the script never runs — the exact bug the guard exists for, in a
    casing it missed. Now `re.search(r"</script", blob, re.IGNORECASE)`;
    deliberately not `</script\s*>`, since the end tag also terminates on
    whitespace or `/`, so requiring the `>` would weaken it.
  - Two sub-points skipped: making the `_SNAPSHOT_BLOCK`/`_APP_BLOCK`
    *extraction* regexes case-insensitive buys nothing (they match our own
    generated lowercase output), and the ast-grep ReDoS warning on that line
    is a false positive — `APP_ELEMENT_ID` is a module constant, not input.
  - `test_dry_run_does_not_write_to_the_default_path_either` asserted on the
    relative default path, so a leftover artifact from any earlier `--write`
    failed it even though the dry run wrote nothing. Runs from `tmp_path` now.
  - Node subprocesses get `timeout=NODE_TIMEOUT`: an accidental infinite loop
    in the shipped script should fail loudly, not hang the suite silently.
- Review round 2 (PR #44), one more real parity hole:
  - **`JSON.parse` erases number spelling.** `1`, `1.0`, and `1e0` all become
    the same IEEE-754 double, so `Number.isInteger(1.0)` is `true` and no
    post-parse check in JavaScript can tell them apart. Python's `json.loads`
    keeps `1.0`/`1e0` as `float` and `_require_version` refuses non-`int`, so a
    manifest with `"schema_version": 1.0` imported cleanly in the page and was
    then rejected by `parse_manifest` — the same inconsistency round 1 set out
    to close, one level lower down.
  - Fixed on the **raw text**, not the parsed value, because that is the only
    place the distinction still exists. `fractionalNumberError` returns the
    first number token containing `.`, `e`, or `E`. Legitimate because a review
    manifest has *no* fractional field: everything is a string except the three
    integer versions. It is string-aware and escape-aware, so a `name` of
    `"Price: 1.5 (v1.0)"` and the `e` in `true`/`false` are untouched —
    over-rejecting here would break manifests Python accepts, which is a parity
    bug in the other direction and is pinned by accept cases.
  - **Never run that scan over the embedded snapshot.** Armor scores serialise
    as `112.0`, so the snapshot legitimately contains floats; the rule is about
    imported manifests only.
  - New `readManifestText(snapshot, items, text)` is the single entry point —
    bytes in, verdict out, the same contract as `parse_manifest(path)`. The
    parity harness now feeds both sides identical *bytes* rather than a parsed
    object, which is what makes spelling and unparseable text testable at all.
    `importText` lost its duplicated `JSON.parse` branch to it.
  - The deeper miss was the **table**, not the code: it had integer, boolean,
    string, and missing versions but no integral-float *spelling*, so it passed
    while the gap was open. Now 54 cases (8 accept, 46 refuse), including
    `1.0`/`1e0` in all three version positions, `NaN`, `Infinity`, truncated
    JSON, and non-object roots. Lesson: a parity table is only as good as the
    axes it varies — type and presence were covered, spelling was not.
  - Deliberately did **not** loosen Python to accept `1.0`. `_require_version`
    is shared with `load_overrides`, so it guards persisted state too, and
    AGENTS.md's rule for manifests is to validate strictly. Also rejected
    `JSON.parse`'s reviver `context.source`: it gives exact token access and
    works in node 22, but support is recent enough that strictness would vary
    by browser, and an invariant that holds "depending on your browser" is not
    an invariant.
  - Line-length nit skipped as a rule but applied locally: there is no
    `[tool.ruff]` section, `E501` is not in ruff's default rule set, and
    existing tests run to 118 characters, so the 90-character signature was not
    violating anything. Wrapped for consistency with the newer files only.
- Review round 3 (PR #44), the decode boundary — one flagged divergence, two
  more found while verifying it:
  - **`FileReader.readAsText()` substitutes U+FFFD** for malformed UTF-8 rather
    than failing, so a mis-encoded manifest imported and autosaved cleanly while
    Python's `read_text(encoding="utf-8")` refused the same bytes. Confirmed in
    Chromium: `"na\x80me"` came back as `"na�me"`.
  - **`readAsText()` also strips a leading BOM** (checked: `EF BB BF 7B 7D`
    decodes to `{}`), where Python keeps U+FEFF and `json` then refuses it. So
    the naive fix makes things worse — `TextDecoder`'s default strips the BOM
    too. `{ fatal: true, ignoreBOM: true }` is the only combination that agrees
    with Python on all four inputs, and `ignoreBOM` is load-bearing rather than
    decoration. A revert-check pins it: dropping it flips `bad_utf8_bom_prefix`
    to browser-accepts/Python-refuses, trading one divergence for another.
  - **Python was crashing, not refusing.** `_load_json_object` caught `OSError`,
    but `UnicodeDecodeError` is a `ValueError`, so mis-encoded bytes escaped
    `parse_manifest` uncaught and past the CLI's `except ReviewError` — a
    traceback where an `error:` line belongs, and the class of bug #43 tracks.
    Widened to `except (OSError, UnicodeDecodeError)`; `load_overrides` shares
    the helper, so a mis-encoded `data/overrides.json` stopped crashing too.
    Note this is not a reversal of round 2's "leave `review.py` alone": that ask
    was to *loosen* what it accepts, whereas this changes no accept/reject
    decision at all — the same bytes are refused either way — it only makes the
    refusal sayable.
  - The harness now compares **bytes in, verdict out** through the page's own
    `readManifestBytes`, so it cannot model a decode the page does not perform.
    It previously used node's `buffer.toString("utf8")`, which keeps a BOM where
    the browser strips one — meaning the harness had never matched the real
    page. 61 cases now (10 accept, 51 refuse).
  - Follow-up nit, and a fair catch: the new BOM tests embedded **literal**
    U+FEFF characters in Python string literals. Replaced with `\ufeff`
    escapes. Embarrassing repeat — a literal U+2028 typed into `review_html.py`
    earlier in the same work arrived as a NUL byte and made the module
    unimportable, which is exactly why `embed_json` uses escapes. Now guarded:
    `test_no_source_blob_contains_an_invisible_character` scans `APP_JS`/`CSS`/
    `BODY_HTML` for Cf/Cc/Zl/Zp characters. A literal NUL needs no guard —
    Python refuses to import the file at all; the guard is for the ones that
    parse silently and leave no trace in a diff. A scan of `src/` and `tests/`
    found no others.
  - **The recurring lesson, three rounds running:** each time, the two
    implementations were being compared one layer too high — objects, then text,
    now bytes. The parity idea was right from the start; the *boundary* was
    wrong. Compare at the outermost layer the real entry points use, and add
    accept cases at each layer, since every fix here risked over-rejecting
    (a `name` containing `1.5`, a name with emoji, an interior U+FEFF).
- Review round 4 (PR #44), the same divergence on the **sibling path**:
  - The paste handler called `.trim()` on the textarea value *before*
    validating it. **JavaScript's `trim()` is not JSON whitespace:** it removes
    U+FEFF, U+00A0, U+2028, and U+3000, none of which JSON accepts. So all four
    prefixes were laundered into accepted manifests while Python refused the
    same text — including the BOM case fixed on the *file* path one round
    earlier. Passing the value untouched costs nothing, because `JSON.parse`
    already allows ordinary leading and trailing JSON whitespace; `trim()` now
    answers only the question it can, "is the box empty".
  - **Why three rounds of parity work missed it:** the parity harness covered
    `readManifestBytes` (the file input) and the paste path's normalisation sat
    inline in an un-exported click handler inside `boot()`, unreachable by any
    test. The UI had two import entry points and the table covered one. Both are
    now exported and both are columns in the table — 65 cases, the paste column
    covering the 61 whose bytes are valid UTF-8, with an assertion that the skip
    set is exactly the undecodable ones so coverage cannot shrink quietly.
  - Proven by revert: restoring the `trim()` leaves the **file** column green
    and fails only the **paste** column, which is precisely why the old
    single-column table could not have caught it.
  - **The actual lesson, and it is not "check one more layer":** when a
    divergence is found on one path, fix every sibling path in the same change.
    Round 3 had the BOM bug in hand and closed it in one of the two places.
    Normalisation hidden in UI code is where these survive, so anything that
    touches input before validation belongs in the exported, tested layer.
  - Also: typed literal U+00A0/U+2028/U+3000 into the new test cases while
    writing them, one round after being told off for literal U+FEFF. The
    existing guard only covers `APP_JS`/`CSS`/`BODY_HTML`, not test files. Caught
    by scanning at the byte level — `str.splitlines()` splits on U+2028, so a
    line-based scan cannot see the character it is looking for.

## 2026-07-25 — persistent review overrides and reviewed export (#36)

- New `review.py` owns the review manifest schema, `data/overrides.json`, and
  the classification of saved vetoes against a fresh run. `report` is
  unchanged and still shows raw proposals; it only prints a pointer line when
  vetoes exist, so "what the rules propose" stays distinct from "what I
  approved". One `review` command covers both inspection and application:
  without `--manifest` it just reports override status.
- Vetoes never reach the CSV writer as a second implementation — final rows
  go through `write_import_csv()` unchanged, pinned by a test comparing the
  reviewed CSV byte-for-byte against the same filtered rows through the
  Python writer.
- A veto only applies while it still describes the proposal the reviewer saw.
  If the rules now propose something else for that id it goes **stale** and is
  *not* applied. Chosen deliberately: the item resurfacing for review is the
  safe direction to fail, and note-wording drift silently suppressing an
  unreviewed decision is not.
- `orphaned` (id gone from a loaded export) is kept distinct from `unchecked`
  (that export was skipped this run). Collapsing them would make a missing
  `data/in/destiny-ghost.csv` look like a vault full of dismantled ghosts.
- Applying a manifest is additive: an `approved` verdict never removes an
  existing veto. A UI that forgot a previous session must not be able to
  resurrect junk the user already rejected; un-vetoing is an explicit file
  edit, reported on stderr when it comes up.
- Merges take display metadata from the *run*, not the manifest — only
  identity crosses the boundary. Manifest parsing rejects unknown keys
  outright (an `output_path` key is an error, not something ignored), unknown
  schema/ruleset versions, non-string or non-DIM-shaped ids, and any id
  appearing twice, whether the verdicts agree or conflict.
- `ReportSection` gained `item_ids`, deliberately *not* in the snapshot: it is
  run-local bookkeeping needed to tell orphaned from stale, and adding it to
  the shareable snapshot would have churned schema v1 for no consumer.
- `save_overrides` writes via same-directory temp file → fsync → `os.replace`
  → directory fsync, with the temp file removed on any failure. Tested by
  making `os.replace` and `json.dump` fail: the previous file survives
  byte-identical and no `.tmp` is left behind. Directory fsync failure is
  tolerated — the replace already happened by then.
- `RULESET_VERSION` deliberately not bumped: no rule ordering or decision
  semantics changed. The golden snapshot is untouched for the same reason.
- Gap worth knowing: nothing generates a manifest yet — #37 is the producer.
  The schema is documented in README so one can be hand-written meanwhile.
- Review follow-up (PR #42), two findings, both accepted:
  - `os.fsync` failure on the directory handle was tolerated but the `os.open`
    that precedes it was not, and by then `os.replace` has already committed.
    The raise escaped before `write_import_csv()`, so a *successful* write was
    reported as a failure and left persisted vetoes with no reviewed CSV to
    match them. Now one `_fsync_directory` helper where nothing past the
    commit point may propagate. Windows refuses `O_RDONLY` directory handles
    outright; `EMFILE`/`EACCES` reach the same place on Linux.
  - Persisted `kind` was accepted as any non-empty text, but `classify` reads
    it functionally. A hand-edited `"weapon"` could only ever land in
    `unchecked` and be reported forever as "that export was not loaded" — the
    exact lie the unchecked/orphaned split exists to prevent, reachable via
    the README's own advice to edit the file to un-veto. Now validated against
    `report_run.EXPORT_KINDS`, one vocabulary derived from
    `DEFAULT_EXPORT_PATHS`.
- Two non-changes, decided rather than overlooked. Manifest `kind` stays
  unvalidated: `merge_manifest` discards it and re-reads kind from the run, so
  there it is free-text display metadata beside `name`/`hash`/`action`/
  `reason`, none of them enumerated. Overrides `action`/`reason` stay
  unvalidated too — they are functional, but a typo degrades safely to
  `stale`, which is truthful. `kind` is the only field whose bad value
  produces a wrong explanation.
- `OVERRIDES_SCHEMA_VERSION` not bumped: this rejects files that were always
  malformed, it does not change the format.
- Both fixes were confirmed by reverting each and watching the new tests fail.
  The `os.open` fake has to be selective — `review.os` *is* the `os` module,
  so a blanket patch breaks `tempfile.mkstemp`; match on `flags == os.O_RDONLY`
  and delegate otherwise.
- Second review round found the helper did not keep its own promise:
  `os.close(dir_fd)` sat in a bare `finally` and could still propagate,
  recreating the exact persisted-vetoes-without-CSV outcome. Restructured so
  open/fsync share one tolerant block and close is separately swallowed, with
  `dir_fd = None` guarding the case where the open itself failed. Three
  targeted tests now pin open, fsync, and close; each was confirmed by
  reverting the fix and watching it fail.
- Still unresolved, not part of this PR: `save_overrides()` and
  `write_import_csv()` are two files with no transaction between them, so a
  failed CSV write leaves vetoes persisted without an export. The current
  order is deliberate — overrides are the durable record of human decisions,
  the CSV is derived and regenerable by re-running.

## 2026-07-25 — pytest imports the checkout under test (#40)

- `pytest` run from a git worktree was exercising the **main checkout's**
  source. The editable install is setuptools' static flavour: a single
  absolute `src` path in `__editable__.vault_cleaner-0.1.0.pth`, injected
  into every interpreter using the venv regardless of cwd. Nothing competed
  with it — src layout, no `tests/__init__.py`, and `testpaths` was the only
  pytest ini setting, so pytest prepended `tests/` (no importable package)
  and the `.pth` won.
- Surfaced during the #39 review rounds: a fault injected into a worktree
  passed cleanly, and the real result only appeared after pinning
  `PYTHONPATH`. Reproduced here before fixing — a worktree with
  `write_import_csv`'s DIM quote re-wrapping deleted still reported
  `201 passed`. With `pythonpath = ["src"]` the same worktree correctly
  fails the two round-trip tests.
- Branch skew is not required for this to bite. Uncommitted edits in either
  tree, or `main` moving while a worktree review is in flight (#39 merged
  mid-review), are enough. The failure is silent, which is what makes it
  worth config rather than reviewer discipline.
- `tests/conftest.py` now asserts the imported `vault_cleaner` sits under
  pytest's own `rootpath/src`, raising `pytest.UsageError` with both
  resolved paths. `pythonpath` fixes today's mechanism; the guard means any
  future mechanism that reintroduces the skew fails loudly instead of
  passing. Verified it refuses when `pythonpath` is disabled.
- No escape hatch was added: there is no workflow here that deliberately
  tests an out-of-tree install, and an opt-out would reopen the silent path.

## 2026-07-25 — M7 foundation review follow-up (#35 / PR #39)

- Made effective TOML config recursively JSON-safe (date/time values use ISO
  strings) before fingerprinting or snapshotting; this closes an uncaught
  `TypeError` regression without accepting arbitrary object stringification.
- Split snapshot schema v1 from ruleset v1 so presentation-only schema changes
  do not invalidate persisted reviews, while decision-semantic changes do;
  documented the required version bump beside the rule conventions.
- Shareable snapshots reduce source and skipped-export paths to basenames and
  omit configured directories plus unknown TOML sections, while the in-memory
  `ReportRun` and CLI retain truthful full paths and effective config. Warnings
  stay structured in the snapshot; only the CLI renders presentation text.
- Fingerprints and snapshots share one allowlisted decision config, filtered to
  the exact nested `rails` and `armor` keys consumed by rules. External content
  is covered separately by export, wishlist, and manifest identities, so a
  snapshot can reproduce its fingerprint from its own recorded inputs without
  leaking free-form config. A recursive DEFAULTS coverage test makes future
  thresholds fail CI until they are added to the projection.
- Reused one streaming file-digest helper, detected export changes across load,
  and fingerprinted the exact captured wishlist bytes that were parsed. Wishlist
  downloads now accept only HTTP(S), and source/wishlist races become domain
  errors rather than raw filesystem failures.
- Made armor `set_bonus` consistently a JSON float, removed the misleading
  frozen marker from evaluations containing mutable stats, and restored an
  explicit manifest refresh as a forced rebuild while retaining normal
  same-version cache reuse.
- Pinned the CI dev tools after unbounded Ruff drift made local 0.15.22 pass
  while CI's 0.16.0 reported nine findings; updated those findings and added a
  checked-in schema-v1 golden snapshot, a documented regeneration command,
  and focused regression coverage. Schema v1 remained intentionally fluid while
  this PR was unmerged; the final golden pins the pre-merge contract.
- The golden test exposed that `load_config` shallow-copied nested defaults,
  letting one caller contaminate later report runs; defaults are now deep-copied
  and an order-isolation regression test pins that behavior.

## 2026-07-24 — M7 foundation: reusable report snapshot (#35)

- Extracted ordered rule execution from `cli.py` into `pipeline.py`;
  individual commands and the combined report now share the same public
  weapons/armor pipeline results. The CLI remains the dry-run / explicit
  `--write` presentation boundary, and its summary/CSV behaviour is unchanged.
- Added `report_run.py`: available exports become a structured `ReportRun`
  with per-section source metadata, original item state, decisions, conflicts,
  effective config, armor score evaluations, and a deterministic JSON-safe
  snapshot (schema v1). DIM instance ids and hashes stay opaque strings.
- Snapshot fingerprints cover export bytes, the effective config, raw cached
  wishlist files, and both the Bungie manifest version and the semantic perk
  map digest. `manifest.load_perk_map_data` exposes version metadata while the
  existing `load_perk_map` dict API remains compatible.
- Armor scoring now records every scored legendary's raw base stats, base and
  bonus score, class/slot rank, protection state, and source tag/notes for
  the later static review/what-if tickets; rule decisions did not change.
- Ruff clean; 186 tests pass (176 before this ticket).

## 2026-07-20 — v0.2.0 tagged; last-of-kind guard in the score pass (#30)

- v0.2.0 tagged + released (M6). First real post-M6 import run surfaced
  the next design gap: the score pass junked the vault's only
  weapons/grenade/super Gunner Ferropotent Mark at score 40 — no dupe
  reasoning, just build-misfit against the single configured archetype.
  Its four same-archetype set-mates survived only because their identical
  stats earned them close-dupe review notes (accidental shielding).
- **Measured before designing:** 115/175 junk rows were the last kept
  copy of their (Hash, Archetype); 174/175 the last at
  (Hash, Archetype, tertiary) — the dupe passes already remove real
  duplicates, so the score pass mostly sees unique rolls, and a
  full-granularity guard would kill it (rejected). 5 (class, set) combos
  lost 4-piece fieldability; the archetype-level guard fixes all 5 free
  (every slot's pieces share one Hash).
- **Owner-picked policy: (Hash, Archetype).** Score pass now runs two
  phases — classify, then junk — and demotes the best-scoring junk
  candidate of any combo that would otherwise lose its last kept copy
  (`#vc-review: armor-last-archetype (<archetype>), armor-score …`).
  Ties break on id, never CSV order. Review-noted pieces from earlier
  passes count as survivors via `kept_elsewhere` (an exact-dupe junk
  always leaves an identical twin, so those combos were already safe).
  `Archetype` is schema-required (empty = legacy, valid).
- Real vault (fresh export, 884 pieces): 73 junk, 102 last-archetype
  demotions. The original Gunner mark still junks — four better Gunner
  set-mates survive, so the combo isn't foreclosed; lock a specific roll
  in DIM to keep it (soft rail).
- Also: PR #27 had merged into its stacked base branch instead of main
  (GitHub only retargets when the base branch is deleted) — re-landed as
  #28 by cherry-picking the stranded squash. Verify content reached main
  after merging stacked PRs.

## 2026-07-19 (M6, part 2) — armor close-dupe pass (#18)

- `rules/armor_close.py`: review-only — dominated (`armor-dominated by
  <id> (+N total)`) and similar (`armor-similar to <id>`), compared within
  Hash + Tier only. The measured collapse (#16): every vault legendary is
  in a manifest set and every set has exactly one hash per class×slot, so
  class+slot+tier+set-signature ⇔ Hash + Tier — no set table, no manifest,
  no network. A dominated pair is never also "similar" (either direction of
  domination excludes the pair); one note per piece, best partner
  (closest, then lowest id — order-independent, tested by CSV reversal).
- Caps in `[armor.close_dupes]` (`max_stat_delta = 5`, `max_total_delta =
  12`), validated non-negative-int with a named error on partial override.
  Measured bimodality means any cap 1–9/1–19 picks the same pairs today.
- Pipeline: rails → exact dupes → close dupes → score. **Deliberate
  consequence:** junk dropped 227 → 175 on the real vault, because ~52
  near-twin pieces the score pass used to junk now get a close-dupe
  review note instead — earlier passes win, and a near-dupe deserves
  human eyes over a blind score junk.
- Real vault: 124 close-dupe reviews (mostly "identical stats, tuning X
  vs Y" — the tuning-twin cluster measured in #16), 0 dominated (as
  measured: structurally impossible at tier 5's fixed 75 totals).
- Review follow-ups: `Tier` schema-required (the close pass groups on it —
  drift was a KeyError, now a SchemaError). Score pass no longer junks a
  piece cited as a close-pass dominator ("only kept pieces dominate" —
  under a strict-but-valid config the old code reviewed 6002 as "dominated
  by 6001" then junked 6001; similar partners never needed the shield
  because their notes are symmetric, so both sides are already decided or
  hard-protected).
- Round 2 (owner call, follows the #17 spiritless guard): the Spirit
  signature joined the close-pass compatibility bucket — two exotic class
  items with different Spirit combos are functionally different pieces
  (same rule as set bonuses), and a spiritless copy is an unknown roll,
  compared with nothing. Real vault: 124 → 115 close reviews; the 9
  removed notes were cross-spirit "similar" advice, i.e. misleading.
- Round 3: the shared `unknown_spirit_roll` helper now also rejects
  truncated signatures (fewer than the measured two Spirits), closing the
  round-2 gap in both passes — a one-Spirit copy sharing its first Spirit
  with a full roll no longer compares with it. Real vault unchanged.

## 2026-07-19 (M6) — armor measurement spike + exact-dupe pass (#16, #17)

- **Spike first (#16), and it rewrote both designs** — full numbers in the
  issue comments. Highlights: the Perks columns are a masterwork-gated
  socket dump (unupgraded copies export almost nothing), so raw perk
  hashing is unusable; but Hash already implies the set perk — the
  manifest's DestinyEquipableItemSetDefinition has 56 sets × exactly one
  hash per class×slot, covering every legendary in the vault. Tuning Stat
  is roll identity, not socket state (present before anything is socketed;
  a socketed '+X/-Y' always matches it on legendaries; always empty on
  exotics — and one tier-5 legendary quirk-exports it empty). No tuning
  leak into base stats: every tier-5 piece totals exactly 75 base.
  Tertiary Stat/Archetype are derivable from base stats. Exotic class item
  Spirit perks are roll identity and visible on every copy.
- `rules/armor_dupes.py` (#17): fingerprint = Hash + 6 base stats +
  Tuning Stat + Seasonal Mod + Holofoil + Spirit signature. Survivor:
  hard > loadout > locked > masterwork > power, then lowest id — reversing
  the CSV changes nothing (tested). Loadout losers review-only (loadouts
  pin instance ids). Fingerprint + ranking columns are now
  schema-required; PLAN.md rules list amended (exact + close dupes).
- Armor pipeline is now rails → exact dupes → score via `_resolve_armor`
  (shared by `armor` and `report`); earlier passes win, one decision per
  item.
- Real vault: 7 exact-dupe rows — 1 junk, 1 loadout review (the rule fired
  on real data: an identical twin survives but the loser is in a loadout),
  5 exotic reviews. Small by design; the volume lives in the close-dupe
  pass (#18): dominated is structurally impossible within tier 5 (fixed 75
  totals) and "similar" is bimodal — 65 pairs differ only in Tuning Stat,
  then nothing until far-apart archetypes.
- Review follow-ups: Masterwork Tier / Power cells validated
  empty-or-digits at load (to_int would coerce garbage to 0 and silently
  flip a survivor; strict `\d+` would repeat the ghost-pass mistake — the
  measured export is all digits, but empty legitimately means
  unmasterworked). `Perks 0` is schema-required, so the Spirit identity source
  can't vanish silently; and (owner call, round 2) the belt-and-braces
  guard is in too — an exotic class item exporting no Spirit perks is an
  unknown roll and is never grouped. Round 3 closed the guard's own gap:
  a complete roll is exactly two Spirits (measured, 38/38 copies), so a
  one-Spirit signature is a truncated identity — two rolls sharing their
  first Spirit must not merge — and anything shorter than
  `SPIRIT_ROLL_SIZE` is now treated as unknown. The guards only fire on
  data we haven't seen — better silent than wrong. Ordinary exotics (no
  spirits by design) still group normally.

## 2026-07-19 (wrap-up) — v1 chores (#21)

- AGENTS.md gotchas absorbed the durable worklog lessons (empty ghost rank
  columns, fixed Armor 3.0 spikes, manifest name→hash, stacked hashtags,
  csv CRLF, build/ artifacts) so future agents get them up front.
- ruff added to CI (one finding: unused import, autofixed).
- Older fixtures (weapons/ghosts/weapons_dupes) normalized to LF.
- pandas pinned `>=3.0,<4` — the venv and CI actually run pandas 3.0.3;
  the old `>=2.0` floor advertised an untested major version.
- After merge: tag v0.1.0 on main — all five milestones + full board done.

## 2026-07-19 (late) — MIT license (#10, PR #20)

- **Owner decision: MIT.** LICENSE file (copyright Tony M), PEP 639
  metadata in pyproject (`license = "MIT"`, `license-files`, setuptools
  ≥77.0.3), README section. All five PLAN.md milestones plus the board
  are now complete; v1 wrap-up chores tracked in #21.
- Review note: kept the README heading "License" (en-US) — repo prose
  follows ecosystem convention and DIM's own en-US terms; an en-GB sweep
  would belong in #21 if ever wanted.

## 2026-07-19 (evening) — M5: dry-run summary report (#9)

- `vault-cleaner report`: runs weapons (wishlist-aware), armor, and ghost
  passes dry, prints "would junk N item(s) and flag M for review" grouped
  by action + reason with per-item lines beneath (junk groups first,
  largest first). `--write` emits one combined import CSV. Missing exports
  are skipped with a warning; item sets are disjoint across passes so
  concatenation is safe.
- `report.reason_slug` parses the reason out of the `#vc-` hashtags —
  the notes remain the single source of truth for reasons.
- `_resolve_weapons` helper extracted so `dupes` and `report` share the
  wishlist/manifest setup.
- Real vault: 430 junk + 135 review across 1,580 items.
- PLAN.md's `--profile pvp|pve` stretch idea intentionally not done —
  file a ticket if wanted.

## 2026-07-19 (later) — Ghost pass redesigned: protection-only (#8, PR #15)

- **Owner decision during review: no ranking at all.** The ranking design
  below went through two review rounds (empty rank columns → tie-breaks →
  determinism) before the honest conclusion: ghosts carry no quality
  signal, and "top N" was an arbitrary policy wearing a ranking costume.
  Final policy: keep only shells that are equipped, **locked (the lock IS
  the keep signal for ghosts — no #vc-review)**, tagged
  favorite/keep/archive, or **referenced by a saved DIM loadout**
  (`Loadouts` column, now schema-required); junk everything else as
  `#vc-junk: ghost-unprotected-surplus`. Rarity still irrelevant.
  Rationale: mods move freely, Collections reacquires dismantled shells,
  and dry-run + DIM review + in-game dismantle remain the gates.
- Removed: `ghosts.keep_top_n`, rank-column schema/validation, tie-breaks.
  Ghosts take no config — lock/tag shells in DIM to keep them.
- Real vault: 29 shells → 17 junk, 12 protected.

## 2026-07-19 — Ghost cleanup pass (#8) — superseded, see above

- `rules/ghosts.py` + `vault-cleaner ghosts`. **Measured data reshaped the
  ticket sketch:** zero duplicate hashes exist, ghost mods move freely
  between shells (the mod carries the utility), and 28/29 shells are
  Exotic *rarity* — cosmetic for ghosts. So: rank all shells by Energy
  Capacity then Masterwork Tier, keep top `ghosts.keep_top_n` (default 6),
  junk the surplus with rank in the note.
- **Deliberate rails deviation:** exotic rarity is NOT a soft rail for
  ghosts (it would flag everything and clean nothing). Locked still
  reviews — checked directly because `rails.protection` reports exotic
  before locked. Tags/equipped hard-protect as usual.
- Real vault: 29 shells → 15 junk, 5 review, top 6 + 3 protected kept.
- New fixtures now written LF-only (csv module defaults to CRLF).
- Review follow-up + finding: **current DIM exports leave Energy Capacity
  and Masterwork Tier EMPTY on every shell** (retired system) — ranking
  ties at (0,0) and falls back to export order. Rank columns are now
  schema-required, cells validated empty-or-digits (strict `\d+` à la
  armor would reject the real export!), and notes say "no
  energy/masterwork data" instead of fabricating "energy 0" rankings.

## 2026-07-18 (late night) — M4: armor loader + archetype scorer (#6, #7)

- `load_armor` on the shared loader; **`ARMOR_STATS` in parse.py is THE
  stat lookup table** (canonical name → `(Base)` column) — an Armor 3.0
  rename is a one-line fix there. Weapons schema now also requires `Ammo`
  because an armor export otherwise satisfies it silently.
- `rules/armor.py`: score every legendary against each configured
  archetype, take the best; favored-set perks (matched by name in Perks
  columns, e.g. "Erebos Glance") add `set_bonus`. Keep top-N per slot per
  class OR anything ≥ floor; junk only both-outside, with reason
  (`#vc-junk: armor-score 56 < floor 65 (best: melee_primary, rank 26/50
  titan gauntlets)`). Rails as usual; exotics never scored.
- **Design finding (measured, not assumed):** every Armor 3.0 tier-5
  piece has the same fixed 30+25 stat spike and ~75 base total, so the
  planned "generic spike profile" scores everything identically (165) and
  discriminates nothing. Dropped from defaults (mechanism `top_stats = N`
  remains for legacy armor); scoring is entirely build-alignment weights.
  Scores are normalized to the Total (Base) scale.
- Real vault: 872 pieces, 559 legendaries scored → 227 junk, 38 review.

## 2026-07-18 (night) — M3 complete: wishlist matching in the rules (#5)

- **Perk name→hash resolved via the Bungie manifest** (`manifest.py`):
  DestinyInventoryItemDefinition is public static JSON (no key/OAuth — still
  inside the no-API-integration rule, which is about live inventory).
  ~200MB one-time download reduced to a ~1MB name→hashes cache in
  `data/cache/`; on staleness only the small index is re-checked, the big
  file re-fetched only when Bungie's manifest *version* changes. One name
  maps to several hashes (base + enhanced variants) — kept deliberately so
  wishlist entries citing either variant match.
- `rules/weapons.py`: full pipeline rails → wishlist pass → dupes. Trash
  match (whole-item or roll ⊆ item perks) → junk / review-if-soft, unless a
  keep roll also matches. Keep matches feed `dupes.resolve` as the
  top-ranked key (match count). Perk names from `Perks N` columns, trailing
  `*` (DIM's selected marker) stripped.
- `dupes` CLI now runs the wishlist pass by default; `--no-wishlists`
  opts out; wishlist/manifest failures error cleanly with that hint.
- Real vault: 679 weapons → 186 junk, 97 review; 23 wishlist-trash calls.
- Review follow-ups: **PLAN.md amended (user-approved)** — the no-API rule
  now precisely bans authenticated access (keys/OAuth/live inventory)
  while permitting unauthenticated static content like the manifest.
  Keep-over-trash conflicts are counted and reported by the CLI (15 in
  the real vault). Cache validation checks every name→hash entry. The
  unwritable-cache test monkeypatches the write instead of chmod (which
  silently doesn't block writes on Windows-backed mounts — it failed on
  the user's WSL setup while passing in CI).

## 2026-07-18 (evening) — M3 part 1: wishlist download/cache/parse (#3, #4)

- `wishlist.py`: `fetch` (cache in `wishlists/`, re-download after
  `wishlists.max_age_days`, stale-cache fallback with warning when offline,
  `WishlistError` only when there's no copy at all) and `parse_wishlist`
  (defensive: non-`dimwishlist:` lines ignored, malformed entries counted
  in `.skipped`, DIM's `-69420` wildcard entries counted but unsupported).
- Sources in `config.toml`: 48klocs choosy_voltron (keep + trash entries)
  and Nitaraku/dim-wishlists aegis_wishlist.txt (auto-generated from the
  Aegis PvE tierlist, actively updated). Real parse: 252k keep rolls + 53
  trash entries (choosy), 5k keep (aegis).
- **Decision:** `wishlists/` stays gitignored — choosy_voltron alone is
  26MB of refreshable third-party content.
- Review follow-up: added the Aegis **trash** list (Ciceron14/
  dim-extra-wishlists, 291 whole-item entries for D-tier-or-lower; updates
  less often than the keep lists). That list writes whole-item trash as
  `&perks=` (present, empty) — the parser now accepts that deliberately
  while still rejecting separator-only `perks=,` as malformed. Also:
  digit runs bounded to uint32 length (huge numbers can't crash `int()`),
  and malformed URLs fall back to stale cache like any download failure.
- **Open question for #5:** wishlist perks are hashes; the DIM export has
  perk *names*. Matching needs a name→hash bridge (or a hash-bearing
  export) — investigate before building the matcher.

## 2026-07-18 (later) — M2: safety rails + dupe resolver

- **Design change from the plan (user decision):** rails are now two-tier.
  Hard (never touched): favorite/keep/archive tags, equipped, crafted ≥
  `rails.crafted_level_protect` (config, default 10). Soft (never tagged
  junk, `#vc-review` note when outranked as a dupe, existing tag/notes
  preserved): **locked and exotic items** — the user wanted recommendations
  on those rather than blanket protection. PLAN.md rule 1 updated.
- `rules/rails.py` (protection classifier), `rules/dupes.py` (group by
  Hash, rank: gear Tier > masterwork > crafted level > stat total; ranking
  takes a pluggable `wishlist_key` for M3 to prepend), `config.py`
  (tomllib + defaults), `vault-cleaner dupes` CLI (dry-run default).
- Output rows append our hashtag to *existing* DIM notes rather than
  replacing them; review rows carry the item's existing tag so import is a
  tag no-op.
- Real-vault dry run: 684 weapons → 184 junk, 89 review.

## 2026-07-18 — Repo bootstrap, M1, ghosts, published

- Initialized repo from PLAN.md; `data/` gitignored from the first commit.
  Layout: `src/vault_cleaner/` (parse, report, cli, rules/), `tests/`,
  `wishlists/`, `data/in|out/`, `config.toml` stub.
- **M1 done.** `vault-cleaner roundtrip` parses a DIM export by header name
  (loud `SchemaError` on drift), tags one sacrificial item, writes a DIM
  `Id/Hash/Tag/Notes` import CSV. Dry-run default, `--write` to emit.
  Verified against a real export (684 weapons). **Round trip confirmed in
  DIM**: imported CSV set tag=junk + note on the target item (screenshot
  check by user). M1 fully done.
- **Ghost support added** (`--kind ghosts`). Ghost exports lack the `Type`
  column, which forced per-kind schema sets — see AGENTS.md gotchas.
- **Finding:** "A Good Shout" exists under two different item hashes
  (seasonal reissue). Dupe resolution (M2) must group by `Hash`, not name.
- Published to https://github.com/tonym999/vault-cleaner (public). Verified
  no vault data anywhere in git history first.
- Decisions: pandas as the only runtime dep; fixtures pinned to real export
  headers with fake rows; `wishlists/` gitignored for now (PLAN.md marks it
  TBD).
