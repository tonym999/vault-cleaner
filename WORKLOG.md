# Worklog

Newest first. One entry per working session: what happened, decisions made,
surprises the next agent should know about.

## 2026-08-31 — #105 location and Guardian class split

- Measured one fresh private armour export using aggregates only: 891 rows;
  Equippable Hunter 186, Titan 429, Warlock 276, empty 0; exotics Hunter 53,
  Titan 115, Warlock 65; class-item types Hunter Cloak 38, Titan Mark 101,
  Warlock Bond 48; exotic class-item rows Hunter 9, Titan 41, Warlock 9.
- Replaced the decision/evaluation `owner` model field with `location` from
  DIM `Owner`, added verbatim armour `guardian_class` from `Equippable`, and
  kept weapon/ghost classes empty. Updated the snapshot to schema v2 (the
  single v1→v2 bump is owned by #105), regenerated the v2 golden, and left the
  ruleset, fingerprint inputs, review-manifest outer schema, override schema,
  and session schema unchanged.
- Added independent browser Kind/Class facets with a presentation-only
  class-neutral fallback, retained Location as a secondary column, relabeled
  duplicate references and terminal output, and covered legacy `owner` plus
  current `location` Notes replacement. Added fake Hunter, mismatched
  location/class, empty, and unrecognised-class coverage; no class validation
  or weapon/ghost schema change was introduced.
- Valid current-schema manifests continue to parse and pre-upgrade nested
  schema-v1 manifests are rejected. The before/after fake semantic capture
  diff is empty (fingerprint, action/tag/reason, membership, and selected
  references unchanged).
- Review follow-up coverage now exercises same-revision Class-control
  resynchronisation through the live no-rebuild path, including invalid-filter
  clearing, list repaint, and preservation of search/focus/local state. The
  fake browser armour input now has deterministic Hunter and Warlock proposal
  rows, proving class filtering removes the other class while locations remain
  visibly independent.
- Validation: baseline before edits passed Ruff and had 819 passing/1 skipped
  with 4 socket and 2 Chromium startup failures under the restricted sandbox;
  the final exact focused gate passed 375 tests, golden/report-run passed 23 tests,
  real-browser acceptance passed 2 tests, and the unrestricted full suite
  passed 837 tests. Final Ruff, diff-check, and no-tracked-`data/` checks
  passed; the full/browser reruns used the permitted socket/browser execution
  environment.

## 2026-08-31 — #29 emitter-driven Notes round-trip coverage

- Added emitter-driven regressions for current Notes clauses from weapon and
  armour exact dupes, armour close dupes, wishlist trash (whole-item and
  roll, junk and soft-review rails), armour scoring (junk, soft review, and
  last-of-archetype), and ghosts. Each case feeds the exact emitted note
  through three further rule runs and asserts the user prefix, action, reason,
  and complete note remain stable with one current vault-cleaner marker.
- Extended the exact-dupe emitter coverage to exercise every current winner
  label: weapon higher Tier, Crafted Level, and stat total, plus armour
  loadout membership, lock, and higher Power. The cases use fixture rows or
  a minimal fixture-derived pair and assert the label in the actual emitted
  note without reconstructing its grammar.
- Kept the literal `note_history` tests for legacy migration formats. Added a
  maintenance obligation to keep emitter tests and recognizer patterns in
  sync whenever a generated clause changes. No production mismatch was found
  and no rule or decision semantics were changed.
- Added emitter-driven partner tie-break coverage for both armor-close
  branches: dominated `6033` selects the lower-id `6031` among equal-surplus
  `6031`/`6032`, and similar Guard Plate `4051` selects `4052` among the
  equally close `4052`/`4053`. Each test checks the actual reason slug and
  structured selected partner plus the exact emitted `; partner deterministic
  id tie-break` tail through the shared round-trip helper; the strict
  recognizer remains unchanged.
- Validation: `.venv/bin/ruff check src tests scripts` passed;
  `.venv/bin/pytest -q tests/test_note_history_roundtrip.py
  tests/test_note_history.py tests/test_dupes.py tests/test_armor_dupes.py
  tests/test_armor_close.py tests/test_weapons_rules.py
  tests/test_armor_rules.py tests/test_ghost_rules.py` passed 170 tests.
  The unrestricted `.venv/bin/pytest -q` suite passed 826 tests, including
  the real-socket and Chromium coverage. Independent renames of the dominated
  and similar armour-close tie-break literals each failed only their targeted
  emitter/recognizer guard; the earlier armour lock and weapon Tier mutations
  remained guarded. Production sources were restored byte-for-byte afterward.

## 2026-08-31 — #29 current-only generated Notes

- Replaced complete, known vault-cleaner clauses at the trailing `Notes`
  boundary before appending the current clause across weapon, armour, armour
  close-duplicate, and ghost rules. User-authored prefixes, ambiguous
  tool-looking fragments, and text following them remain untouched; a
  five-cycle DIM-style round-trip regression confirms generated Notes no
  longer grow across runs.
- Kept last-marker parsing for migrated or manually edited Notes, routed
  crafted-state display through the shared strict parser, and aligned armour
  winner wording with weapon winner wording. Corrected the M9 issue
  reference, so Markdown treats it as prose rather than a heading.
- This is presentation/history handling only: rule order, selection, action,
  tag, reason slug, full audit ids, report schema, fingerprint, and ruleset
  version remain unchanged. Snapshot regeneration was byte-identical.
- Validation: Ruff passed. The focused review-follow-up command was
  `.venv/bin/pytest -q tests/test_note_history.py tests/test_dupes.py
  tests/test_armor_dupes.py tests/test_armor_close.py
  tests/test_duplicate_reference.py tests/test_weapons_rules.py
  tests/test_armor_rules.py tests/test_ghost_rules.py tests/test_report.py
  tests/test_report_run.py tests/test_cli_report.py`; it passed 213 tests.
  The unrestricted `.venv/bin/pytest -q` suite passed 800 tests. `git diff
  --check` and the no-tracked-`data/` privacy check passed.

## 2026-08-30 — #29 five-character suffix boundary correction

- Corrected the bounded collision presenter so prefix-plus-suffix displays
  are used only when at least one source character is genuinely omitted.
  Five-character collisions now use suffix plus the stable bounded
  discriminator, without reintroducing the leading character; naturally
  distinct ids of four characters or fewer remain unchanged.
- Added a direct five-character regression while retaining the 16-character,
  three-copy group-wide, and pathological stability coverage. No selection,
  grouping, ranking, action/tag, audit-id, schema, or fingerprint semantics
  changed.
- Validation: Ruff passed; focused duplicate/reference/report tests passed
  146 tests; full suite passed 772 tests and skipped 1. Four real-socket tests
  failed and two Chromium tests errored only because this sandbox denies
  socket/browser startup (`Operation not permitted`). Snapshot regeneration
  was byte-identical; fake report/roundtrip dry-run checks passed; diff-check
  and no-tracked-`data/` privacy checks passed.

## 2026-08-30 — #29 group-wide suffix collision correction

- Corrected collision context so weapon exact-dupe and armour exact-dupe
  survivors receive every id in their exact group, while armour close-dupe
  partners receive every id in the compatibility group. A referenced row now
  has one stable presentation label across all notes that cite it.
- Kept the final four characters as the normal label and bounded suffix
  expansion strictly below the complete long id. A truthful leading-prefix /
  suffix projection handles group-unique collisions; pathological shared
  projections use a bounded deterministic group-rank plus target digest.
  Short synthetic ids remain intact, and no opaque id is parsed numerically by
  the presenter or emitted in full.
- Added three-copy weapon and armour exact-group regressions, repeated
  armour-close partner stability coverage, 16-character collision protection,
  and pathological-prefix/suffix fallback coverage. Selection, grouping,
  ranking, actions, tags, full audit ids, and all other #29 semantics are
  unchanged.
- Validation: Ruff passed; the focused duplicate/reference/report suite
  passed 145 tests; the full suite passed 771 tests and skipped 1. Four
  real-socket tests failed and two Chromium tests errored only because this
  sandbox denies socket/browser startup (`Operation not permitted`). Snapshot
  regeneration was byte-identical; fake `report` and `roundtrip` dry-run
  checks passed; `git diff --check` passed; no files are tracked under
  `data/`.

## 2026-08-30 — #29 presentation safety corrections

- Corrected exact-roll identity normalization to remove only one selected
  trailing `*` from the original DIM cell. Display casing is derived
  separately, so `Trait*` and `Trait**` remain distinct and `Kill Tracker**`
  cannot become a measured boundary; the regression also confirms the
  fingerprint remains at the established #31 semantics.
- Escaped untrusted reference delimiters (`[`, `]`, `;`) as full-width
  presentation characters while retaining raw audit values. Generated
  Notes grammar remains ASCII and report summaries preserve the generated
  `keep`/`compare` and winner/partner suffix. Added hostile weapon and armor
  exact/close regressions for marker, structural, newline, and forged-clause
  safety.
- Added presentation-only survivor/partner suffix disambiguation: final four
  characters remain the default, colliding candidate/survivor suffixes grow
  by bounded string comparison, and pathological shared suffixes use a
  bounded differing-character fallback. Full `ReportDecision.id` and
  `kept_id` remain unchanged; no identity, grouping, ranking, or action
  semantics changed.
- Validation: Ruff passed; the focused duplicate/reference/report suite
  passed 139 tests; the full suite passed 765 tests and skipped 1. Four
  real-socket tests failed and two Chromium tests errored only because this
  sandbox denies socket/browser startup (`Operation not permitted`).
  `git diff --check` passed, no files are tracked under `data/`, the fake
  report snapshot regeneration was byte-identical, and fake `report` plus
  `roundtrip` dry-run checks completed successfully.

## 2026-08-30 — #29 human-readable duplicate references

- Added one shared presentation seam for weapon exact-dupe survivors, armour
  exact-dupe survivors, and armour dominated/similar partners. Long opaque ids
  render as a final-four-character suffix (`[id …0059]`); short synthetic ids
  remain intact. Weapon references include Owner, Tier, MW, crafted level when
  known, and the final two names from the existing measured pre-tracker roll
  prefix. Armour references include Owner, MW, Power, Tuning Stat, and compact
  Spirit names where present.
- Notes retain the existing `#vc-junk:`/`#vc-review:` reason slugs and append a
  bounded `keep`/`compare` reference plus a selector explanation. Weapon
  explanations follow the current #31 Tier → Masterwork Tier → Crafted Level →
  stat total → opaque-id ranking; wishlist and hard-rail state are not used to
  select a survivor. Armour explanations follow the existing survivor rank,
  and close-dupe explanations retain the current surplus/similarity detail.
- Referenced-row display text collapses control whitespace, bounds each
  fragment/reference, and neutralizes case-insensitive `#vc-` text. Raw row
  values and the existing full `ReportDecision.id`/`kept_id` audit strings stay
  unchanged. No survivor row is emitted merely for discoverability.
- Added fake hostile-text, short-id, selector-reason, report-summary, reverse
  determinism, and long-id snapshot regressions. Regenerated the schema-v1
  fake snapshot; its diff is limited to duplicate presentation Notes. Schema
  version remains 1 and ruleset version remains 3; no runtime dependency or
  browser/server/review code changed. Validation: Ruff and 132 focused tests
  pass; the full suite has 758 passing tests plus 1 skip, with 4 socket tests
  failing and 2 Chromium tests erroring only because this sandbox denies socket
  and browser startup (`Operation not permitted`).

## 2026-08-30 — #31 Enhanced-prefix documentation clarification

- Reconciled every exact-roll description with the literal DIM prefix while
  keeping the Markdown lint-safe: names begin with `Enhanced` followed by one
  separator space, and both the word and that space remain part of the complete
  perk name. This avoids relying on an invisible trailing space inside a code
  span while preserving the measured distinction from the base perk name.
- Updated AGENTS.md, PLAN.md, README.md, WORKLOG.md, and the duplicate-rule
  module docstring only. Decision semantics, fixtures, ruleset version, and
  report snapshots are unchanged.
- Validation passed with Ruff, `git diff --check`, and all 752 tests in the
  full suite.

## 2026-08-29 — #31 final review cleanup

- Corrected the public `dupes` command summary: duplicate resolution keeps the
  best exact copy while preserving distinct and uncertain rolls, rather than
  keeping only one item per Hash.
- Aligned the comma-bearing tracker-candidate scan with the exact measured
  boundary invariant. The boundary cell is necessarily the exact normalized
  `Kill Tracker` or `Crucible Tracker` label, so it cannot contain a comma and
  is no longer included in the pre-boundary scan. The existing adversarial
  tests still cover comma-bearing candidates before a later valid boundary.
- Kept the hostile-Unicode report, renderer, and upload regressions in this PR.
  They restore coverage lost when this ticket changed the hostile weapon
  fixture's roll identity, so they are directly related regression protection
  rather than unrelated feature work.
- Validation passed with Ruff, the top-level CLI help smoke check, and all 752
  tests in the full suite.

## 2026-08-29 — #31 review correction: preserve Enhanced perk names

- Corrected the exact-roll normalizer to remove only DIM's trailing selected
  `*` marker. Names beginning with the literal `Enhanced` followed by one
  separator space are retained as complete gameplay perk names; collapsing
  them to base names could falsely merge distinct rolls under one Hash. The
  regression now proves `Battery` and `Enhanced Battery` remain separate and
  produce no dupe decision.
- Re-measured the private export after the correction: 665 rows remained
  groupable with contiguous named `Perks 0` through `Perks 20`; all 665 rows
  had a measured `Kill Tracker` or `Crucible Tracker` boundary (positions 4
  through 15), and 25 pre-tracker names beginning with the literal `Enhanced`
  followed by one separator space were ordinary gameplay names. Aggregate
  identity results were unchanged: 117 old same-Hash groups (346 rows, 229
  redundant), 1 exact group of 3 rows (2 redundant), and 2 review decisions
  with no automatic junk decisions. No real rows, ids, paths, or hashes are
  recorded here.
- Regenerated the fake-data snapshot with the repository script; it was
  byte-identical because no fake input or decision payload changed. The
  ruleset remains version 3; this correction does not introduce another
  ruleset bump.
- Focused validation passed: Ruff and 243 duplicate, parser, report, weapon,
  review, session, finalize, and UI tests. The full suite passed 721 tests and
  skipped 1; 4 real-socket tests failed and 2 Chromium tests errored because
  this sandbox denies sockets/browser startup (`Operation not permitted`), the
  same environmental limitation recorded for the prior review.

## 2026-08-29 — #31 PR #100 follow-up: dynamic headers, hostile coverage, and wishlist/comma safety

- Made weapon `Perks N` schema width export-dependent. The minimal load-time
  invariant is `Perks 0`; the extractor accepts any contiguous `0..N` header
  range with a complete non-empty pre-tracker prefix and a measured `Kill
  Tracker` or `Crucible Tracker` boundary, so gaps, missing starts/boundaries,
  unknown tracker-looking labels without a measured boundary, or incomplete
  rows remain ungroupable without blocking unrelated commands. Previous
  real-style fixtures measured `Perks 0..19`; the current private export
  measures `Perks 0..20`.
- Restored the hostile fixture's exact prefix on the RTL-name row so its
  decision path carries the RLO/PDF name and U+2028/U+2029 Notes. Added report,
  renderer, and server-upload assertions for those values; no real data is
  involved.
- Removed wishlist score from exact-dupe survivor ranking. Wishlist-trash,
  keep-over-trash conflicts, and exact-group keep protection remain unchanged;
  exact copies now rank Tier > Masterwork Tier > Crafted Level > stat total >
  stable opaque Id. Added a regression proving differing post-tracker
  wishlist-resolvable cells cannot select the survivor.
- Measured 5,302 starred perk cells, each with exactly one trailing selected
  marker. The private export has 13 comma-bearing pre-tracker cells, all
  legitimate full names (`Nail, Meet Hammer` or `Eyes Up, Guardian`), and no
  comma-bearing tracker cells. `row_perk_hashes` now keeps each cell whole;
  comma-bearing names resolve through the perk map without guessed splitting.
  The measured tracker boundaries are exactly `Kill Tracker` (662 rows) and
  `Crucible Tracker` (3 rows). Any comma-bearing cell containing either
  measured tracker label is rejected as an unmeasured combined tracker,
  regardless of component order or marker placement; unknown/future names that
  merely end in `Tracker` stay identity cells until a later measured boundary,
  or make the row ungroupable when no measured boundary exists. These are safe
  aggregate counts only: no rows, IDs, hashes, or paths are recorded.
- Snapshot regeneration via the repository script was byte-identical: the
  changed hostile fixture is not part of the fake golden, no decision payload
  changed, and `RULESET_VERSION` remains 3.
- Final focused validation passed: Ruff and 201 parser, dupe, weapon, rail,
  report, UI, server-upload, and export-discovery tests. Restricted full-suite
  result: 745 passed, 1 skipped, 4 failed, and 2 errors; the failures/errors
  were caused by documented socket/browser startup `Operation not permitted`
  restrictions. An independent elevated full-suite run completed cleanly:
  752 passed. The fake Slammer CLI dry run remained 1 junk / 0 review, and the
  private no-wishlist report remained 0 junk / 2 review with no `--write`.

## 2026-08-29 — #31 weapon exact-roll measurement (pre-code)

- Measured the current private DIM weapon export before finalizing the
  extractor: 665 rows, with contiguous named `Perks 0` through `Perks 20`.
  The first `Kill Tracker` or `Crucible Tracker` perk cell is a stable
  structural boundary in the export: cells before it are the frame and
  randomized roll options; tracker, origin, mod, masterwork, memento, and
  other current-state cells follow it.
- The fingerprint will use `Hash` plus every pre-tracker perk cell by header
  name, stripping only DIM's trailing selected `*` marker. Names beginning
  with the literal `Enhanced` followed by one separator space are retained as
  complete perk names: the measured occurrences were ordinary gameplay perk
  names, not a safe display-only decoration. Perk options are retained in
  their measured socket order: the export represents
  multi-option sockets as adjacent named cells, and no order changes were
  observed. Exotic rows also carry pre-tracker prefixes in this export, so
  their `Hash` alone is not a complete identity.
- Mutable tracker, origin/current socket, mod, masterwork, memento, and later
  cells are excluded. `Hash` remains mandatory, and `Name` is never used.
  Missing or empty pre-tracker identity cells, a missing measured boundary, an
  unknown tracker-looking label without a later measured boundary, an unknown
  rarity, or an otherwise incomplete prefix will be ungroupable and cannot
  enter automatic duplicate cleanup. Cells at and after the measured boundary
  are excluded from identity and may legitimately be empty.
- Aggregate baseline: 117 same-Hash groups of at least two rows (346 rows,
  229 redundant rows). The safe measured candidate has 1 exact group (3
  exotic rows, 2 redundant rows); no legendary exact group was present. The
  candidate therefore bounds automatic cleanup to 2 rows before rails, rather
  than the old 229-row same-Hash pool. No real rows, ids, paths, or hashes are
  recorded here.
- The three same-Hash Exotic groups measured as size/distinct-prefix pairs
  `9/9`, `3/1`, and `2/2`; only the `3/1` group supports exact grouping. The
  two multi-prefix groups are therefore intentionally left untouched.

## 2026-08-29 — #31 weapon exact-roll implementation

- Implemented `exact_roll_fingerprint()` in `rules/dupes.py`: named `Perks N`
  fields are normalized through the first measured `Kill Tracker` or
  `Crucible Tracker` boundary, with only the selected `*` marker removed.
  Unknown tracker-looking labels are not guessed as boundaries. Names beginning
  with the literal `Enhanced` followed by one separator space are retained
  because measurement found them in ordinary gameplay perk names. Socket order
  is preserved; exotic prefixes are included because Hash-only identity was
  not supported by the measurement.
  Blank hashes, unknown rarities, missing boundaries, and incomplete prefixes
  are ungroupable and never enter automatic dupe resolution. Mutable tracker,
  current socket, mod, masterwork, memento, and later state remain excluded.
- `dupes.resolve()` now groups by `(Hash, fingerprint)` and chooses survivors
  by the existing rank order plus an opaque-id tie-break independent of CSV
  order. Wishlist-trash remains the earlier separate pass, and #32 crafted
  validation/protection and all hard/soft rails remain unchanged.
- Added a fake, synthetic Slammer-like export and behavioral coverage for
  distinct and exact same-Hash rolls, row reversal, selected markers,
  multi-option cells, distinct names beginning with the literal `Enhanced`
  followed by one separator space, mutable state, unknown identity,
  wishlist behavior, and same-name/different-Hash safety. The parser then
  required the measured named perk-prefix headers; the later dynamic-width
  follow-up below reduces that to the minimal `Perks 0` invariant while the
  extractor keeps its fail-safe contiguity checks. `RULESET_VERSION` advanced
  from 2 to 3 and the report snapshot was regenerated by the repository
  script.
- Post-change private-export aggregate dry runs: 665 rows remained
  groupable under the measured contract; 1 exact group covered 3 rows (2
  pre-rail redundant copies), and the resolver emitted 2 review decisions
  with no automatic junk decisions. The real Slammer aggregate is six copies
  across two Hashes: the five-copy group has five distinct fingerprints and no
  exact group, while the other Hash is a singleton. The synthetic Slammer dry
  run has one four-copy Hash with three distinct fingerprints and one
  two-copy exact group; it emitted one junk decision from that exact pair and
  kept distinct rolls separate.
- Snapshot inspection found no weapon decision payload changes; only the
  ruleset/global fingerprint and the fake weapon source digest/fingerprint
  metadata changed.
- Focused validation passed: Ruff and 274 exact-dupe/weapon/rail/report,
  parser, review, server-finalize, and UI tests. The full suite result was
  721 passed, 1 skipped, 4 failed, and 2 errors;
  the four real-socket tests and two Chromium tests remain blocked by this
  sandbox's `Operation not permitted` network/browser restrictions, as in the
  baseline.

## 2026-08-28 — #32 crafted token safety-rail correction

- DIM's crafted weapon token is `Crafted=crafted`, but the old rail passed
  `Crafted` through the generic boolean parser, which only recognised
  `true`. The focused helper now accepts `crafted` as crafted, `false` and
  empty as not crafted (with surrounding whitespace/case normalised), and
  rejects `true` plus every other unknown non-empty token. The fixture-only
  `true` representation is deliberately not retained.
- Weapon ingestion now requires and validates `Crafted` and `Crafted Level`
  before any rule decisions. Threshold and above-threshold unlocked crafted
  losers are absent from wishlist and duplicate output; below-threshold
  crafted rows retain normal behaviour.
- Bumped `RULESET_VERSION` from 1 to 2 and regenerated the fake report
  snapshot. Focused validation passed Ruff and 96 tests; the elevated full
  gate passed Ruff and 695 tests. The dry-run reports 4 junk and 3 review
  decisions, with ids 3021 and 3023 absent and below-threshold id 3022
  junked. Browser/server/wheel checks are not required for this local parser
  ticket. No real vault rows or IDs were committed; issue #31 remains
  separate and unresolved.
- Review follow-up: the fingerprint regression now compares all input
  categories at the current ruleset version 2, with only the dedicated
  version-change assertion using version 1. A shared strict level parser now
  trims surrounding whitespace; empty non-crafted/shared levels map to zero,
  while empty crafted levels map to an explicit unknown sentinel and are
  hard-protected; every non-empty level must be ASCII non-negative integer
  text, otherwise SchemaError. Both weapon loaders validate every row before
  rules, and rails.protection validates direct-call data eagerly.
- Empty crafted-level follow-up: crafted rows with empty or whitespace-only
  levels now load as an explicit unknown sentinel and are hard-protected with
  `crafted-lvunknown`; non-crafted empty levels remain zero/unprotected.
  Loader parity, wishlist-trash, duplicate-loser, mixed-export, and eager
  precedence regressions cover the fallback without changing fixtures or the
  ruleset version.
- Final review validation: focused Ruff and 117 focused tests passed; full
  Ruff and 716 tests passed; the fake duplicate dry run parsed 18 weapons and
  produced 4 junk plus 3 review decisions, with crafted ids 3021 and 3023
  absent and below-threshold id 3022 junked. Snapshot regeneration was
  byte-identical (schema 1, ruleset 2); git diff --check passed, and no data
  paths are tracked.

## 2026-08-28 — #51 retired static review surface

- Removed the unreleased `review-html` command and Python renderer, deleted
  `review_static.js`, and deleted the static-only CLI/artifact/browser parity
  test suites. Browser manifest parsing, import/export, autosave, and handoff
  code are gone; CLI `review --manifest` and `review.parse_manifest` remain,
  as does the server's separate strict verdict validator.
- Kept the permanent manifest-free presentation coverage in
  `tests/test_review_ui_js.py` (including 64-bit ids, prototype safety,
  grouping/filtering/sorting, hostile text, and source safety). Its hostile-run
  helper was moved locally from the deleted static test module. The two #90
  Playwright tests and the non-editable wheel proof were left intact.
- Updated README, PLAN, and AGENTS to describe `serve` as the only browser
  workflow, keep review manifests as CLI/scripting/backup input, and remove
  obsolete inline/static browser-parser guidance. A stale server asset guard
  that named deleted browser-parser symbols was removed; allow-listed assets
  and route tests remain.
- Retired-surface baseline before deletion: 2,353 lines
  (`review_html.py` 165, `review_static.js` 745, `test_cli_review_html.py`
  174, `test_review_html.py` 285, `test_review_html_js.py` 984). Final
  `git diff --numstat origin/main...HEAD`: 109 additions, 2,637 deletions,
  for a net reduction of 2,528 lines.
- Validation: Ruff passed; full suite passed (678 tests); focused UI/review/
  CLI/verdict suites passed (22/82/34 tests); both permanent Chromium tests
  passed (2 passed, 676 deselected); the wheel proof passed; both surviving
  packaged JavaScript assets passed `node --check`; CLI help showed `serve`,
  `report`, and `review` with `review-html` rejected; `git diff --check`
  passed; no files under `data/` are tracked; hygiene search found no live
  retired-surface references and `parse_manifest` remains owned by
  `review.py`/CLI/tests. No runtime dependency or server protocol change.

## 2026-08-27 — #94 review follow-up: browser launch and wheel-proof hardening

- Replaced the browser test's `BrowserType.executable_path` preflight with the
  real `launch_browser()` attempt. Only Playwright's exact missing-executable
  diagnostic is translated into the ordinary skip / `VAULT_CLEANER_BROWSER_REQUIRED=1`
  failure policy; unrelated launch failures still propagate. Fixture return
  annotations now use `Iterator[...]`.
- Changed `scripts/check_wheel_install.py` to snapshot current bytes for
  `git ls-files -z` paths into a fresh temporary source tree. Pip builds from
  that tree outside the checkout, so ignored `build/`, `data/`, `.venv/`, and
  other untracked content cannot be reused. The child server's stderr is
  drained concurrently and retained in diagnostics; malformed bootstrap URLs
  now become the intended `RuntimeError`.
- Validation: Ruff passed; all 750 pytest tests passed; browser collection was
  exactly 2; both required Chromium browser tests passed; empty-browser
  ordinary mode skipped 2 and required mode exited nonzero with 2 setup
  failures; the wheel proof passed; a disposable clone containing a stale
  `build/stale.whl` left that artifact untouched while the proof built from a
  `/tmp` source snapshot; all three packaged JavaScript files passed
  `node --check`; `git diff --check` passed; and `git ls-files data/` remained
  empty.
- Intentional non-changes: `Session.expected_origin` remains untouched because
  it is a property; no runtime dependencies, package data, production server,
  protocol, or UI files changed; the reusable browser checklist remains in one
  document as requested by #90.

## 2026-08-27 — #90 browser parity gate, wheel proof, and documentation

- Pinned dev/test-only `playwright==1.62.0` and
  `pytest-playwright==0.9.0` without changing the pandas + Flask runtime set.
  The managed install resolved Chrome for Testing 151.0.7922.34, Playwright
  Chromium browser revision 1234 (plus headless-shell revision 1234 and FFmpeg
  revision 1011).
- Added exactly two `browser`-marked real-browser tests over the existing
  loopback server: hostile uploaded names/notes remain inert live DOM text with
  no injected `img`, `script`, `b`, or dialog, and the one browser smoke covers
  bootstrap → armor upload → approve → unset → veto → finalise → Playwright
  download. The downloaded `dim-import.csv` bytes equal
  `session.finalized_csv_bytes`; #67's CLI/server parity was not duplicated.
- Guarded the managed browser executable before launch. Browser-free runs skip
  both tests, while `VAULT_CLEANER_BROWSER_REQUIRED=1` turns a missing Chromium
  into a failing setup instead of a falsely green job. Collection reports
  exactly 2 browser tests.
- Added a dedicated Ubuntu browser CI job alongside the unchanged
  Windows/Linux core matrix. It installs Chromium with
  `python -m playwright install --with-deps chromium`, runs the isolated wheel
  proof and both browser tests, and uploads retained-on-failure traces and
  failure screenshots from `test-results`; no retries or rerun tooling were
  added.
- Added `scripts/check_wheel_install.py`: it builds a real wheel with
  `python -m pip wheel --no-deps --wheel-dir <temporary-wheelhouse> .`, installs
  only that wheel into a fresh temporary virtual environment, removes inherited
  `PYTHONPATH`, runs outside the checkout, verifies the imported package origin,
  starts the installed `vault-cleaner serve --no-wishlists --port 0`, follows
  bootstrap with a cookie-aware standard-library client, and checks the root
  HTML plus every allow-listed CSS/JavaScript asset for status, content type,
  body, and references. The existing #87 `vault_cleaner.ui` package-data
  declaration was sufficient; no packaging correction was required.
- Completed the reusable manual browser/accessibility checklist on Linux with
  Chrome for Testing 151.0.7922.34 at 1440×1000 and 390×844. Light, dark,
  narrow, keyboard `a`/`v`/`u` focus preservation, report controls,
  finalised/frozen state, Download again, Reset, Shutdown, and the required
  stale second-tab reconciliation all passed. No product browser defect was
  found; one exploratory checklist command selected an option absent from the
  all-review fixture and was corrected before the complete pass.
- Expanded the README from the #88 stub to the complete #89 server workflow
  and privacy model: byte uploads rather than paths, session-held verdicts,
  finalisation and durable vetoes, download/reset/shutdown, loopback and
  bootstrap secrecy, local-only vault data, no Bungie credentials, and the
  separate optional static-content network path with `--no-wishlists`.
- Final validation: Ruff passed; all 750 pytest tests passed; browser collection
  was exactly 2 and both passed in Chromium; all three packaged JavaScript files
  passed `node --check`; the non-editable wheel proof passed; the fake-fixture
  round-trip stayed dry; `git diff --check` passed; and `git ls-files data/`
  remained empty.

## 2026-08-27 — #89 review follow-up: control and finalisation recovery hardening

- Refreshed every mutation control, including bulk buttons, whenever the
  single-tab gate or authoritative session state changes. Finalized adoption
  now leaves verdict controls frozen while retaining a safe Download-again
  recovery action when report refresh is disconnected.
- Treated every successful finalise HTTP response as committed even when CSV
  bytes are missing or unreadable. Added no-retry/no-second-finalise coverage,
  finalized CSV recovery coverage, and preserved committed-success messaging
  when the post-download report refresh fails.
- A stale mutation whose mandatory report refetch fails now enters an explicit
  disconnected recovery state with Reconnect and no enabled mutations; the
  stale envelope remains display-only until authoritative adoption.
- Verdict-filter acknowledgements now compare actual visible row membership,
  so approving an already-approved row (and the vetoed/unreviewed equivalents)
  repaints in place without stealing focus. Finalisation report-refresh errors
  preserve terminal authentication/session/incompatibility outcomes separately
  from recoverable HTTP/transport failures; a successful Download-again
  response restores the connected finalized lifecycle controls.
- Acknowledgement envelopes that invalidate a query now rebuild the filter
  controls along with the rows. Session actions live outside the report panel,
  so Shutdown and the idle upload hint remain reachable after boot and Reset;
  the action group is explicitly labelled for assistive technology.
- The static artifact now opts into the shared non-read-only view and shared
  row painter, keeping Unset aria state and verdict presentation synchronized.
  Finalisation surfaces the protocol's approved-but-still-vetoed count with
  singular/plural wording. A small ``Vault-Cleaner-Serve-Once`` response
  signal lets the page represent intentional post-download shutdown without
  a misleading reconnect prompt; persistent servers retain report recovery.
- Finalisation response metadata is snapshotted before reading CSV bytes and
  carried through committed body-read failures, so even a ``--once`` server
  can show the accurate approved-but-still-vetoed count in its terminal banner.
- Finalisation notes now remain truthful across every committed response and
  report-refresh recovery path; zero suppression counts are omitted, and
  invalidated filters synchronize in place without stealing search focus.
- The committed finalisation note is now rendered synchronously before a
  follow-up report refresh can wait; focused-control tests retain the search
  caret and cover zero and malformed suppression headers.

## 2026-08-27 — server-acknowledged review mutations and finalisation (#89)

- Extended the packaged server review page from read-only presentation to a
  server-acknowledged review workflow. Single-row and filtered bulk approve,
  veto, and unset actions use one revision/fingerprint-bound request and a
  single same-tab mutation gate; displayed verdicts change only after the
  returned envelope is accepted.
- Added keyboard ``a``/``v``/``u`` review controls, in-place acknowledged row
  repainting (including focus-preserving row handles), stale mutation
  reconciliation through ``GET /api/report`` without replay, selective local
  view-state invalidation reporting, and retained/discarded upload verdict
  presentation.
- Added finalise/download/reset/shutdown lifecycle controls. Finalisation
  consumes CSV bytes and protocol headers, revokes temporary download URLs,
  supports ``GET /api/finalized.csv`` recovery, freezes the finalized view,
  sends reset's exact two-key payload, and sends shutdown as a bodyless POST.
- The shared view layer now exposes explicit Unset controls and safe row-paint
  and control-disable seams. Hostile item text remains text-node data, while
  approved-session/active-persisted-veto conflicts remain explicit.

## 2026-08-26 — Linux VM handoff review (#88)

- Recreated the ignored development environment after the repository move and
  revalidated the pushed issue branch: Ruff was clean, all 687 existing tests
  passed, all three packaged JavaScript files passed Node syntax checks,
  `git diff --check` was clean, and no file under `data/` was tracked. The VM
  only provides Python 3.14 rather than the documented Python 3.12 target; the
  declared `>=3.12`
  package contract and full suite still pass there.
- Ran an isolated real-loopback smoke test: bootstrap authentication and all
  three fake fixture uploads returned 200, an invalid weapons replacement
  returned the sanitized 422 response, and the accepted report fingerprint
  and revision remained unchanged after rejection.
- Moved the minimal local-server README section below the static manifest
  workflow. Its earlier placement made the following static-only approve/veto
  and browser-storage paragraphs read as features of the read-only server.
- The SSH-forwarded real-browser pass covered all three accepted fixture
  uploads, rejected replacement preservation, rendering, refresh, and the
  disconnected state. It found that the visible Reconnect button did nothing:
  deferred execution let the outer loader overwrite the global runtime object
  its click handler looked up. The button now retains its retry callback
  directly, with a Node regression that constructs and clicks it. A fresh
  real-browser pass then proved the button sends its retry, a stopped server
  retains the visible disconnected state, and a replacement session produces
  terminal 401 restart guidance without another retry. The manual checklist is
  complete, and the final suite passes all 688 tests.
- Follow-up review fixes keep one stable ``VaultCleanerServerUI`` object while
  exposing live ``start`` and ``state`` handles for both interactive and
  loading-time script execution. Shared response conversion now distinguishes
  transport failures, HTTP/API errors, invalid JSON, and incompatible success
  envelopes; malformed successful responses are terminal with restart guidance,
  while ordinary rejected uploads remain connected. Added focused Node coverage
  for response/error classes, array/numeric-id/duplicate-id envelopes, upload
  rejection, terminal 401, and both DOM timings. Upload statuses are now
  outside the file labels, linked with ``aria-describedby``, and polite live
  regions for all three export kinds. Documented the read-only view contract,
  including null approve/veto row handles. A shared browser failure-state helper
  now handles only common 401, illegal-state, incompatible/invalid-JSON, and
  transport transitions based on client failure kinds; ordinary upload HTTP
  failures remain per-kind while report HTTP failures retain reconnect guidance.
  Session envelope override statuses are validated and copied before state
  adoption, and the browser/Python session-state vocabularies are parity-tested.
  Invalid-JSON guidance is identical in the main and per-kind live regions.
  Focused browser/UI plus session-invariant tests pass (47 tests, including 46
  UI tests); full validation passes Ruff, all 708 tests, packaged JavaScript
  syntax checks, diff whitespace checks, and confirms no tracked files under
  ``data/``. Session metadata now fails loudly if an unknown state would be
  emitted, while upload eligibility remains an explicit allow-list.

## 2026-08-25 — server review UI shell and read-only report (#88)

- Replaced the server placeholder root with fixed packaged HTML, CSS, shared
  presentation JavaScript, and a server-only adapter wired through
  `run_server` → `build_server` → `create_app`; the explicit asset allow-list
  remains the only way browser resources are served.
- Tightened the HTTP CSP to deny all by default while allowing only same-origin
  packaged scripts/styles and same-origin API fetches. The page has no forms,
  inline code, request-derived paths, or mutation/finalization controls.
- Added separate weapons/armor/ghost CSV inputs using `fetch` with explicit
  `text/csv` and browser-owned transport length headers. Each input reports its
  own upload/error status, while one `applySessionEnvelope` seam adopts server
  state, rejects unknown schema versions, keeps valid local
  search/filter/group/sort/detail state, drops only invalidated filter/sort/
  expansion values, and retains upload reconciliation ids privately.
- The read-only report uses the #87 presentation core for counts, filtering,
  grouping, sorting, item details, hostile-text-safe DOM rendering, and armor
  panels. Persisted override statuses and current-session verdicts are shown
  as separate concepts. Added server asset/CSP tests and Node seam/safety tests,
  updated serve docs, and kept the static review adapter unchanged.
- Review found and fixed selective view-state invalidation, exact CSP ordering,
  the five named count displays, disconnected upload disabling, and terminal
  `401` restart guidance before the final verification pass.
- A real browser pass remains: the Linux Playwright driver had no installed
  Chrome and the Windows browser-control bridge could not attach from this WSL
  workspace. Open the printed bootstrap URL, upload each fake fixture kind,
  refresh, reject a replacement, and verify disconnected/terminal messaging.

## 2026-08-25 — shared review UI assets and presentation core (#87)

- Extracted the review stylesheet and the manifest-free presentation/view layer
  into packaged `vault_cleaner.ui` resources. The static HTML adapter now reads
  and inlines those exact resource bytes, while keeping autosave and manifest
  import/export in a clearly temporary adapter for #51.
- Generalized browser `keptItems` to combine active persisted veto ids with
  current-session vetoes; the static adapter passes an empty `Set`.
- Added setuptools package-data configuration and direct Node coverage for the
  packaged presentation resource (64-bit ids, grouping parity, prototype-safe
  maps, and persisted-veto filtering), plus an exact inline-byte proof. The
  static-adapter Node harness retains manifest/parity coverage, while the
  presentation harness directly requires the packaged resource; resource
  loading decodes raw bytes to avoid universal-newline drift.
- Review follow-up adds a small Node DOM-stub contract for the shared view
  layer, precise static-only layering guards, exact snapshot-element coupling,
  and a strict Set-like contract for active persisted veto ids. Safety comments
  now live with the extracted helpers, including the DOM text-node boundary and
  64-bit id ordering rationale.
- Windows review finding: packaged CSS/JS resources now have narrowly scoped
  LF attributes, preserving exact browser bytes under core.autocrlf while the
  existing byte-exact fixture rules remain unchanged.
- Round-two review follow-up: constant leak sentinels now catch ordinary
  SCREAMING_CASE reads, Node harness failures retain captured stderr, and the
  exported `keptItems` Set-like/opaque-id/filter-copy contract is documented
  beside the function.
- No server UI, HTTP client, CSP, or manifest-code deletion was introduced.

## 2026-08-25 — transactional server finalization (#67)

- Implemented serialized `/api/finalize` as prepare → raw-byte override drift
  guard → durable persistence → tiny in-memory commit. The complete DIM CSV is
  rendered before `save_overrides`, deliberately preserving the server/CLI
  ordering distinction, and finalized bytes are cached for idempotent retries
  and `/api/finalized.csv` without another disk read.
- Added strict finalize request and revision validation, exact CSV/disposition
  and revision headers, the approved-still-vetoed conflict count, finalized
  lifecycle invalidation on reset/close, and `serve --once` shutdown on a
  successful response close only.
- Reset now reloads and validates the current override bytes/digest before
  changing session state, so an `overrides_changed` refusal can recover and a
  second review in the same process adopts the new baseline. The digest
  comparison still has the unavoidable small TOCTOU window before
  `save_overrides`' atomic replacement; the next reset establishes a fresh
  exact-byte baseline.
- Added raw-byte parity coverage against all three CLI reference modes
  (proposal report, persisted-veto review, and fixed review-manifest review),
  distinct existing/missing override drift cases, finalized cache/reset
  behavior, post-commit response recovery, `--once` close semantics, and
  route-specific error-path redaction for report, upload, finalize, and reset.
- Review follow-up: derive the approved-still-vetoed header from the merge
  result, make reset's refreshed override store/digest inputs required, give
  closed-session finalize requests a terminal-state error, and cover missing
  and float-spelled revisions plus finalized upload refusal for every export
  kind. The finalize digest remains the pre-persistence review baseline by
  design; reset is the atomic store+digest refresh boundary.
- Review follow-up also gives closed `/api/finalized.csv` requests a terminal
  shutdown error, documents the `create_app(once=True)` response-close
  contract, and clarifies the finalized-response construction seam and
  lifecycle comments.

## 2026-08-25 — verdicts, reset, stale revisions, and terminal shutdown (#66)

- Added the serialized `/api/verdicts` batch mutation with strict shared
  review-input validation, opaque ids, duplicate/unknown-id rejection, both
  batch caps, JSON `null` clearing, no-op semantics, deterministic report-order
  responses, and one revision bump per changed batch.
- Added the reusable session stale-check seam and exact revision headers for
  `stale_report`/`stale_verdicts`; stale checks run inside the same serialized
  critical section as verdict and reset mutations.
- Upload replacement now reconciles verdicts through #63's
  `retain_verdicts()` before adoption, returns retained/discarded ids, and
  bumps `verdict_revision` once only when the stored verdict set changes.
- Added serialized `/api/reset` with monotonic revisions and retryable
  server-owned cleanup while leaving durable overrides untouched. Shutdown now
  synchronously enters terminal `closed` state, clears live metadata, keeps
  revisions monotonic, and returns a coherent idempotent closed envelope;
  physical cleanup and socket stop remain in the response callback boundary.
- Added focused protocol tests for validation, atomicity, stale headers,
  clear/reset, repeated shutdown, and response ordering. No durable review
  writes were introduced. Added a real-loopback overlapping-verdict test with
  events and bounded joins proving one same-revision request wins and the
  other receives stale headers.
- Follow-up hardening requires the `verdict` key explicitly (so omitted and
  JSON `null` remain distinct), snapshots stale revision headers under the
  session lock, deep-copies report-present verdict arrays, and makes reset,
  close, and post-commit retirement resilient to ordinary cleanup exceptions.
  The protocol note in `PLAN.md` records schema-v1's five states, including
  #67's `finalized` and the terminal `closed` state.
- Validation passes: Ruff reports no findings, all 637 tests pass (including
  the real-loopback overlap regressions), `git diff --check` is clean, and no
  file under `data/` is tracked.

## 2026-08-24 — server lifecycle regression contract (#83)

- Audited all nine substantive PR #82 review findings. Post-close upload
  allocation is covered by
  `test_close_before_upload_rejects_without_staging_a_candidate` and the new
  real-socket overlap test; partial live metadata and revision rewind are
  covered by `test_close_invalidates_all_accepted_export_state` plus the shared
  lifecycle expectations; and the over-wide rollback span is covered by
  `test_post_commit_retirement_failure_keeps_new_live_state`.
- The prepare, cleanup-retry, and retirement boundaries remain pinned by
  `test_report_failure_rolls_back_and_removes_candidate`,
  `test_failed_candidate_cleanup_remains_tracked_until_close`,
  `test_close_retries_a_directory_when_deletion_temporarily_fails`, and the
  post-commit retirement regression. Shutdown cleanup cannot gate process
  teardown: `test_shutdown_callback_runs_when_close_raises` and
  `test_run_server_closes_server_when_session_close_fails` cover the callback
  and socket-close boundaries respectively.
- Added `tests/test_server_lifecycle.py` with one extensible expectation table
  for current idle, exports-loaded, and closed state. Its real-loopback test
  blocks inside report construction with events, proves a shutdown request has
  reached Flask but cannot overtake the serialized upload, then proves ordered
  completion, successful server exit, monotonic revisions, and no live,
  candidate, or retired staging residue. It uses bounded waits and joins, not
  sleeps or a lock-only simulation.
- Removed the shared absent override fixture path from server-app tests; every
  constructed session now receives its own `tmp_path` path. The CLI's
  default-path forwarding test stays intentionally path-specific and stubs
  `run_server`, so it performs no filesystem read. This closes both the real or
  cwd-relative override exposure and the later finding that absence of the
  shared fixture was unenforced.
- Two review findings remain explicit contract decisions rather than defects:
  the 96 MiB aggregate guard is defensive because three 32 MiB per-kind caps
  make its rejection side unreachable today, while the coherent terminal
  response for repeated shutdown remains a schema decision for #66. No
  production or schema behaviour changed here.
- Promoted the reusable rules to the `AGENTS.md` server-lifecycle checklist:
  close is terminal, revisions are monotonic, uploads use prepare → adopt →
  retire phases, rollback ends before adoption, cleanup is retryable and cannot
  block shutdown, deletion is server-owned only, and tests use explicit
  test-owned paths.
- Validation passes: Ruff reports no findings, all 603 tests pass (including
  real loopback coverage), `git diff --check` is clean, and no file under
  `data/` is tracked.
- Review follow-up: the overlap regression now spies on
  `server_app.session_metadata` before delegation and only for the shutdown
  request, proving the shutdown view cannot enter before the serialized upload
  finishes. The staging redirect now replaces only the `server_app.tempfile`
  binding with a delegating proxy, leaving process-wide
  `tempfile.mkdtemp` unchanged. `build_client` documents its test-owned
  `tmp_path/overrides.json` contract.
- Mutation proof: removing `@serialized` from either the upload handler or the
  shutdown view makes the overlap regression fail at the pre-delegation view
  assertion: without either side of the serialization boundary, shutdown can
  enter while report construction is still blocked.

## 2026-08-24 — isolate server-app test overrides (#65)

- Replaced every repo-relative `overrides.json` path used by
  `tests/test_server_app.py` sessions with an absolute, deliberately absent
  test-owned fixture path. The `run_server` integration test continues to use
  its own `tmp_path` override path, so a real repository override file cannot
  influence the server-app tests.

## 2026-08-23 — final upload lifecycle review follow-up (#65)

- Lifecycle tests now pass isolated overrides paths under `tmp_path` and never
  read personal `data/` overrides; the one default-path forwarding test remains
  explicit about `DEFAULT_OVERRIDES_PATH`.
- Clarified the narrow deletion exception: the local review server may remove
  only its own temporary staging/candidate/retired directories, and request
  content can never supply cleanup paths.
- `override_digest` remains internal session state for #67 lost-update/finalize
  drift detection and is deliberately absent from schema-version-1
  `/api/report` responses.
- Repeat `/api/shutdown` metadata coherence requires a terminal closed protocol
  state and is deferred to #66/parent state-machine work; #65 API behavior is
  unchanged.
- Ruff and the full test suite pass: 602 tests collected and passed.

## 2026-08-23 — upload lifecycle review follow-up, round 3 (#65)

- Preserved the session's prior state plus monotonic `report_revision` and
  `verdict_revision` counters across close while still invalidating the live
  report, export metadata, verdict data, and staging pointer. Failed cleanup
  paths remain private retry state.
- Authenticated `GET /api/report` now returns the registered 409
  `illegal_state` error after shutdown, rather than exposing a reset-looking
  idle envelope. Shutdown still builds its response metadata before the close
  callback runs.
- Wrapped both shutdown callback and server socket cleanup in `finally` paths;
  regressions prove each cleanup callback runs when session close raises. The
  full suite passes all 602 tests, including the two real loopback checks.

## 2026-08-23 — upload lifecycle review follow-up (#65)

- Made the lock-protected session closed flag authoritative for uploads and
  shutdown: closed sessions return the registered 409 illegal-state error
  before reading or staging a body. Close now invalidates the report, export
  digests/sizes, fingerprint/snapshot, verdicts, revisions, state, and live
  staging pointer before cleanup; failed deletions remain only in private
  retry tracking.
- Encapsulated candidate tracking, adoption, and retirement in `Session`.
  Candidate rollback ends before adoption, while prior-directory retirement is
  post-commit best effort so cleanup failures cannot remove the new live run.
- Kept `MAX_EXPORT_BYTES=32 MiB` and `MAX_TOTAL_EXPORT_BYTES=96 MiB` and
  removed the production-only aggregate-limit seam. With exactly three shipped
  export kinds, each capped at 32 MiB, the reject side is mathematically
  unreachable under those constants; the aggregate guard remains defensive
  for future kinds or limit changes. Integration rejection coverage injects a
  lower module cap instead.
- Converted upload-test client setup to unconditional `Session.close()`
  teardown and added close-before-upload, close-state invalidation, and
  post-commit retirement-failure regressions. The full suite passes all 600
  tests, including the two real loopback checks.

## 2026-08-23 — server uploads and transactional report staging (#65)

- Added strict raw-byte upload handling for weapons, armor, and ghost exports:
  explicit lengths, transfer-encoding rejection, named per-kind/aggregate
  limits, media-type checks, strict UTF-8 decoding, and sanitized schema/error
  responses.
- Uploads now build a complete canonical temporary export set and run the
  existing `run_report` engine before swapping session state. Identical bytes
  are idempotent; changed uploads advance `report_revision`; failed builds and
  invalid replacements leave the live report untouched and remove candidates.
- Sessions now retain the current `ReportRun`, source digests/sizes, exact
  override-store bytes digest (with missing-file distinction), and clean live,
  retired, and candidate directories idempotently on shutdown or startup
  failure. `/api/report` derives its snapshot and override status from the
  committed run.
- Added focused upload, rollback, transport, canonical-path, limit, and
  lifecycle coverage. Full suite passes (597 tests); no ruleset or snapshot
  version changed and no files under `data/` are tracked.
- Follow-up: centralized temporary-directory deletion in `Session`, retaining
  paths when a filesystem removal transiently fails so repeated `close()` calls
  retry them. Candidate rollback now uses the same seam; focused tests cover
  failed deletion and later cleanup. Full suite now collects 597 tests.

## 2026-08-23 — final Project #3 workflow verification (#61)

- Verified live Project #3 workflows through GraphQL: `Auto-add to project`,
  `Item added to project`, and `Auto-archive items` are enabled. The UI-configured
  filters are repository auto-add for `is:issue` with default `Todo`, and
  completed-item archive after 30 days (`is:closed reason:completed
  updated:<@today-1m`); workflow configuration details are not exposed by the
  available GraphQL schema.
- Created temporary maintenance issue #80 and verified it automatically
  appeared in Project #3 with Status `Todo` before closing it with an explanatory
  comment. This proves the repository auto-add and Item added behavior
  end-to-end without leaving test work open.
- Re-audited the four views, exact `Todo`/`In Progress`/`Done` statuses, the
  `enhancement` label on feature #38, `maintenance` on #51/#61, M8 assignments
  (#38/#47/#49/#50/#51), dependency links #49 → #50 → #51, and superseded #25.

## 2026-08-22 — issue and project workflow guidance (#61)

- Updated `AGENTS.md` to link the actual vault-cleaner project board and added
  the complete issue-creation checklist: specific type/maintenance labels,
  `icebox` only for explicitly out-of-scope PLAN work, existing milestones,
  dependency text and project dependency links, explicit `Todo` membership,
  and post-creation verification.
- Audited the public repository state before external changes: the existing
  `M8 — Local review server` milestone is already assigned to #38, #47, #49,
  #50, and #51; feature #38 retains `enhancement`, while #51 and #61 use
  `maintenance`.
- Repository issue metadata is now applied through the authenticated GitHub
  connector: `enhancement` remains on feature issue #38, `maintenance` is on
  #51 and #61 (replacing #61's `enhancement`), #25 is closed as superseded
  with a linking comment, and the M8 milestone assignments remain intact.
- Project v2 views and dependency links are now configured through the
  authenticated GraphQL API: `All items`, `Board`, `Active`, and `Icebox`;
  #50 is blocked by #49 and #51 is blocked by #50. Status remains exactly
  `Todo`, `In Progress`, and `Done`. The Board is still a board layout with
  Status visible; the available schema exposes no explicit grouping mutation,
  so its existing/default Status grouping is preserved for UI verification.
- At the time of this entry, the remaining project steps were the UI-only
  repository auto-add/default `Todo` and 30-day completed-item archive controls;
  the final verification is recorded in the dated entry above.

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
- Final follow-up: verdict mappings now require exactly `approved` or
  `vetoed`, including for retention, and the pure core accepts only mapping
  entries while `merge_manifest` continues to restore legacy diagnostics.
- Final input-shape guard rejects non-mapping iterable entries with a stable
  project-owned `TypeError`.

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
