# Issue #104 — Luna xhigh implementation handoff

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#104 — M9: expose Tuning Mod Slot across armor comparisons`

**Plan baseline:** `main` at `4d0f1ebe6cd55d20a7dc8c6285051bfdc84c979e`

**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → orchestrating Sol reviews → independent Sol high reviews → PR

**Suggested implementation branch:** `codex/issue-104-tuning-mod-slot-presentation`

## Objective

Make the existing DIM `Tuning Stat` value immediately and honestly visible as an explicitly labelled **Tuning Mod Slot** whenever vault-cleaner presents an armour candidate beside the survivor or partner already selected by the current rules.

At completion:

- armour exact-duplicate, dominated and similar DIM Notes identify both the candidate and selected survivor/partner tuning values, even when they are equal;
- dry-run and aggregated terminal comparison lines expose the same labelled pair;
- each pairwise armour `ReportDecision` and server snapshot carries normalised candidate and selected values as structured data;
- the ordinary browser **Proposals** view displays the pair as always-visible text, without hover, row expansion, note parsing or a colour-only cue;
- the authoritative exact-group and same-stat projections landed by #101 retain their existing Tuning Mod Slot contract for the later #102 view; and
- duplicate identity, grouping, selection, actions, tags, reason slugs, decision order, verdicts and lifecycle behaviour do not change.

This is a presentation and report-projection ticket. It must not become a rule, ranking or browser-lifecycle redesign.

## Why this ticket is ready

- #29 is closed and its shared human-readable survivor/partner reference seam is on `main`.
- #105 is closed. `location` and `guardian_class` are distinct, snapshot schema v2 is established, and the browser already consumes the current decision projection.
- #101 is closed through merged PR #107. The baseline commit now contains:
  - one authoritative exact-duplicate group projection;
  - one authoritative same-stat group projection;
  - the complete supported `Tuning Mod Slot` vocabulary;
  - ruleset v4 and snapshot schema v2; and
  - deterministic opaque-ID ordering.
- #102 remains open and textually depends on #101 and #104. Its Armor duplicates browser view must consume the payload prepared here and in #101; it is not implemented in this ticket.

Issue #104 has no comments, no parent issue and no sub-issues. The native GitHub dependency endpoints currently expose no edges even though the issue bodies state the sequence. Treat the written dependency chain and the M9 plan as authoritative:

```text
#29 → #101 → #104 → #102
```

## Model selection

**Use Luna xhigh.**

Although the behaviour is presentation-only, it crosses the Notes emitter/recogniser contract, Python report modelling, a versioned JSON snapshot, server pass-through tests, shared JavaScript presentation code, real-browser coverage and user documentation. The main risk is not algorithmic novelty; it is making one consistent change without duplicating rule truth, stranding old generated Notes, or accidentally altering decision semantics. Luna xhigh is justified by that cross-runtime coordination and the amount of invariant checking required.

## Review model

**Review path: independent.**

```text
Sol orchestrator
    ↓
Luna xhigh implementation
    ↓
Same Sol orchestrator plan-conformance and engineering review
    ↓
Independent Sol high final review
    ↓
PR
```

The issue itself classifies the work this way. The implementation changes a safety-relevant comparison presentation across DIM Notes, terminal text, report/snapshot data and the live browser. An omission or mismatch could cause a user to dismantle the wrong armour copy even though the underlying selector remains correct. A fresh reviewer should therefore challenge both the implementation and the projection design, rather than only checking that Luna followed this plan.

Luna must commit and push the implementation branch but must not open a pull request.

---

# Authoritative context

Before changing code, read all of the following on the then-current `main`:

- `AGENTS.md`;
- `PLAN.md`, especially the ordered armour passes and M9 section;
- issue #104 and its complete timeline;
- closed prerequisite issues #29, #101 and #105;
- dependent issue #102;
- merged PR #107 and its resolved review findings;
- the newest relevant `WORKLOG.md` entries;
- every production and test file listed under the expected footprint below.

Treat these as authoritative:

- Python selects every survivor/partner and remains the only rules engine.
- `Decision.kept_id` is the already-selected full opaque survivor/partner identity.
- `report_run.snapshot_dict()` is the structured browser/report source.
- `Session` and the server return that snapshot without reconstructing comparison truth.
- `review_ui.js` renders export-derived values using DOM text APIs.
- current exact and same-stat group projections from #101 own group membership and group truth.
- complete instance ids and hashes remain strings; do not pass them through JavaScript `Number` or Python integer normalisation.
- Notes replacement is a compatibility contract: old recognised generated clauses and the new format must both remain removable on the next run.

Do not create a second tuning vocabulary, duplicate selector, partner lookup algorithm, snapshot builder or server-side projection path.

## Current repository state relevant to #104

The ticket is not stale, but `main` has moved materially since it was written. Plan from the actual baseline:

1. `src/vault_cleaner/rules/armor_dupes.py`
   - already defines the generic mapping `Weapons`, `Health`, `Class`, `Grenade`, `Super`, `Melee`, otherwise `none/unknown`;
   - already emits one normalised `tuning_mod_slot` per exact group; and
   - must retain the exact fingerprint's raw `Tuning Stat` identity unchanged.
2. `src/vault_cleaner/rules/armor_close.py`
   - already emits raw and normalised tuning per same-stat member;
   - already carries each member's selected partner id where a close proposal exists; and
   - only mentions both raw values in Note detail for identical-stat pairs whose tuning differs. Dominated, near-stat, equal-tuning and unknown-tuning pairs are not uniformly presented.
3. `src/vault_cleaner/duplicate_reference.py`
   - the selected armour reference includes raw tuning only when the source cell is non-blank;
   - it omits an explicit unknown state; and
   - it does not label candidate and selected values side by side.
4. `src/vault_cleaner/report_run.py`
   - `ReportDecision` has no candidate or selected tuning fields;
   - `_decision_records()` has both the full source frame and `kept_id`, so it can project already-selected values without re-running selection; and
   - `snapshot_dict()` serialises decisions with `asdict()` and group projections through dedicated pass-through helpers.
5. `src/vault_cleaner/report.py` and `src/vault_cleaner/cli.py`
   - terminal duplicate lines include the generated Note tail, so a correct Note comparison will naturally reach both focused armour and aggregate dry-run output;
   - direct regression coverage is still required so this is not assumed by inspection.
6. `src/vault_cleaner/ui/review_ui.js`
   - `itemsFromSnapshot()` does not map tuning comparison fields;
   - the ordinary Proposals table has no always-visible tuning column; and
   - the expanded armour-scoring detail is not an acceptable substitute because #104 forbids hidden-details-only presentation.
7. `src/vault_cleaner/ui/review_server.js`
   - consumes `review_ui.js` items and `COLUMNS` and should not need protocol or lifecycle changes for an additive presentation field.
8. `src/vault_cleaner/server/app.py` and `src/vault_cleaner/server/session.py`
   - already pass `snapshot_dict()` through the authenticated session envelope;
   - no server inference or new endpoint is needed.
9. `tests/test_server_browser.py`
   - currently contains two real-browser tests from #90;
   - #104 explicitly requires browser proof, so one focused armour tuning presentation case is authorised in addition to those existing tests.
10. `PLAN.md`
    - its M9 sequence currently omits #104 and goes directly from #101 to #102. Update the documentation to reflect the actual dependency chain without changing rule design.

## Dependencies and assumptions

- Implementation must branch from the latest `main`, not blindly from the SHA above. If `main` has advanced, record the new base and first confirm this plan still matches the live code.
- Snapshot schema v2 is the coordinated M9 contract established by #105 and extended by #101. #104 should complete that contract additively without bumping it.
- Ruleset v4 is authoritative. #104 is presentation-only and must not change the decision fingerprint.
- Existing fake fixtures contain enough equal, different and blank tuning examples. Prefer fixture-derived test frames over adding large new CSV fixtures.
- `Tuning Stat` is read by header name. Missing required armour columns remain a parse/schema concern already handled elsewhere.
- For an armour comparison decision, `kept_id` must resolve to a row in the same loaded armour export. If that invariant is false, stop rather than inventing a fallback selector.
- Non-armour decisions and armour decisions with no selected comparison partner may carry a non-applicable/null structured comparison state. A blank or unrecognised value on an actual armour comparison side must be the explicit string `none/unknown`, not null or omission.
- The browser consumes the normalised report fields. It must not inspect `note`, parse Notes grammar, infer from stat vectors or reconstruct a partner from group data.

---

# Ticket-specific algorithmic scope rule

Apply this rule to every proposed production-code hunk.

## Mechanical inclusion test

A hunk belongs in #104 only if all of the following are true:

1. It performs at least one of these operations:
   - reads the existing raw `Tuning Stat` for an armour candidate or the row already named by that decision's `kept_id`;
   - applies the one shared presentation vocabulary to that existing value;
   - carries candidate/selected/group tuning through an existing Note, report, snapshot, server or UI seam;
   - labels or renders those values as inert text; or
   - tests/documents one of those operations.
2. It does not choose, rank, group, filter or otherwise change which row is the candidate, survivor or partner.
3. For every unchanged fake input, the ordered semantic capture below remains identical before and after the change:

```python
(
    decision.id,
    decision.hash,
    decision.action,
    decision.tag,
    decision.kept_id,
    reason_slug(decision.note),
)
```

The same must hold for exact/same-stat group ids, membership, preferred survivor, member disposition and order. Note wording and new presentation-only report fields are the intended differences.

If a hunk fails any part of this test, it does not belong in #104.

## Stop and return to Sol for replanning if

- the selected row cannot be obtained by a direct lookup of the existing `kept_id` in the already-loaded armour frame;
- #101's exact/same-stat payload is insufficient or contradictory and would need the browser or report layer to reconstruct group truth;
- implementation would change the exact fingerprint, same-stat key, close compatibility, group membership, survivor/partner selection, ordering, dispositions or exotic class-item exception;
- implementation would add any preference among the six supported tuning values;
- implementation would add paired base-stat comparison machinery, a new duplicate/close pass or a group-level verdict;
- a snapshot-schema, ruleset, review-manifest, override, session-envelope or persistence version change appears necessary;
- server endpoint, verdict validation, stale reconciliation, finalisation, reset, shutdown, authentication or lifecycle behaviour would need to change;
- JavaScript would need to parse DIM Notes, infer tuning from stats or convert an opaque id/hash to a number;
- the #102 Armor duplicates view would need to be implemented early;
- a runtime dependency, CI topology change, browser retry, fixed sleep or new cross-browser matrix appears necessary;
- a real vault export or other private data seems necessary for implementation or tests; or
- an incidental defect cannot be isolated from the semantic invariants above.

Report incidental findings separately. Do not fix them on the #104 branch unless Sol replans the ticket.

---

# Scope

## In scope

- One shared Tuning Mod Slot presentation vocabulary for all six recognised values plus `none/unknown`.
- Pairwise armour Note presentation that labels candidate and selected survivor/partner values, including equal values.
- Compatibility recognition for both existing #29-style Notes and the new #104 format.
- Structured candidate and selected Tuning Mod Slot fields on pairwise armour report decisions and snapshots.
- Existing server snapshot pass-through verification.
- An always-visible, text-labelled ordinary Proposals comparison column/cell.
- Preservation tests for #101 exact and same-stat group tuning projections.
- Focused Python, Node/JavaScript and Chromium coverage.
- M9 sequencing/user documentation and a dated `WORKLOG.md` entry.

## Out of scope

- Any tuning preference, recommendation, optimisation or config.
- Any duplicate identity, compatibility, selection, protection, disposition, action, tag, reason-slug or pass-order change.
- New group membership or new group projections.
- Pairwise six-stat payload redesign; only keep tuning visually distinct from existing stat displays.
- Weapon comparison changes.
- The #102 Armor duplicates view, its selector, group filtering, expansion state or group verdict interaction.
- Bulk/group actions.
- Snapshot/ruleset/session/review/override version changes.
- Server protocol, lifecycle, persistence, authentication or filesystem-boundary changes.
- New dependencies, retries, fixed sleeps or browser matrices.

## Expected change footprint

Likely production files:

```text
src/vault_cleaner/duplicate_reference.py
src/vault_cleaner/rules/armor_dupes.py
src/vault_cleaner/rules/armor_close.py
src/vault_cleaner/note_history.py
src/vault_cleaner/report_run.py
src/vault_cleaner/ui/review_ui.js
src/vault_cleaner/ui/review.css                 # only if needed for legible text layout
```

Likely tests/fixtures:

```text
tests/test_duplicate_reference.py
tests/test_armor_dupes.py
tests/test_armor_close.py
tests/test_note_history.py
tests/test_note_history_roundtrip.py
tests/test_report.py
tests/test_report_run.py
tests/test_review_ui_js.py
tests/test_server_uploads.py
tests/test_server_browser.py
tests/fixtures/report_snapshot_v2.json
```

Likely documentation:

```text
PLAN.md
README.md
docs/browser-verification.md
WORKLOG.md
```

`src/vault_cleaner/report.py` and `src/vault_cleaner/cli.py` may remain production-code unchanged if their existing Note-tail presentation correctly exposes the new labelled pair. Their behavioural tests must nevertheless prove the terminal requirement. Change those modules only if the tests demonstrate that the existing seam is insufficient.

## Files/components that should normally remain unchanged

```text
src/vault_cleaner/pipeline.py
src/vault_cleaner/rules/armor.py
src/vault_cleaner/rules/dupes.py
src/vault_cleaner/rules/id_order.py
src/vault_cleaner/rules/weapons.py
src/vault_cleaner/rules/rails.py
src/vault_cleaner/review.py
src/vault_cleaner/review_session.py
src/vault_cleaner/server/app.py
src/vault_cleaner/server/session.py
src/vault_cleaner/ui/review_server.js
src/vault_cleaner/ui/review_server.html
.github/workflows/ci.yml
pyproject.toml
config.toml
```

Within `armor_dupes.py` and `armor_close.py`, fingerprinting, compatibility, ranking, selected ids, group construction and ordering should remain unchanged; only shared presentation calls/imports and their tests should move.

If any normally unchanged component needs a substantive edit, stop and explain why to Sol before proceeding.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline

1. Fetch the latest `main` and create the implementation branch from it.
2. Record the exact base SHA in the Luna → Sol handoff.
3. Read `AGENTS.md`, the issue graph and every file named in this plan.
4. Confirm the current versions are snapshot schema 2 and ruleset 4.
5. Run the baseline focused and full gates before editing. If baseline fails for a code reason, stop and report it; do not mix a repair into #104. Environment-only missing Chromium/socket restrictions must be recorded and rerun in a suitable environment before completion.
6. Capture the current fake-fixture semantic tuples and group projections described in the scope rule so the finished branch can prove parity.

Suggested setup:

```bash
git fetch origin main
git switch -c codex/issue-104-tuning-mod-slot-presentation origin/main
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git status --short
```

## 2. Centralise the presentation vocabulary without moving rule truth

Use the existing shared presentation seam in `duplicate_reference.py` for normalisation and labelled comparison text.

- Move or expose the existing normaliser so Notes, report projection and #101 group projection all call one implementation.
- Preserve the exact mapping:

| Raw recognised value, case/outer whitespace insensitive | Presented value |
| --- | --- |
| `weapons` | `Weapons` |
| `health` | `Health` |
| `class` | `Class` |
| `grenade` | `Grenade` |
| `super` | `Super` |
| `melee` | `Melee` |
| blank or anything else | `none/unknown` |

- Do not rewrite the raw value used by `armor_dupes.fingerprint()` or same-stat variation detection.
- Keep the current import surface stable where practical: `armor_dupes` may import/re-export the shared helper so existing internal consumers do not fork.
- Add a small formatter for pairwise labels rather than hand-building subtly different strings in exact and close emitters.
- Resolve the current raw `tuning <value>` fragment in `armor_reference()` deliberately: either replace it with the explicit normalised Tuning Mod Slot label or let the new pairwise formatter own both sides. Do not emit an omitted/raw selected value beside a normalised comparison, and do not duplicate the selected value in two competing formats.
- Continue to pass export-derived fragments through the existing bounded/single-line safe presentation functions. The normalised vocabulary itself is fixed text.

## 3. Extend DIM Note emitters and preserve Note-history compatibility

Update only the presentation fragments in the existing exact and close branches.

For every exact-duplicate Note:

- show `Candidate Tuning Mod Slot: <value>`;
- show `Survivor Tuning Mod Slot: <value>` or an equivalently unambiguous label tied to the existing `keep` reference;
- show both when equal; and
- retain the existing reason slug, `keep` reference, winning reason and selected id.

For every dominated/similar Note:

- show `Candidate Tuning Mod Slot: <value>`;
- show `Partner Tuning Mod Slot: <value>` or an equivalently unambiguous label tied to the existing `compare` reference;
- show both when equal; and
- retain the existing reason slug, comparison detail, partner reason and selected id.

Do not rely on `_similar_detail()`'s current special case for different tuning; the new labelled pair is required for dominated, near-stat, equal-tuning and unknown-tuning comparisons too. Avoid needlessly repeating contradictory raw wording. The final clause should remain concise enough for the existing bounded reference/summary contracts.

Update `note_history.py` so it recognises:

1. the newly emitted #104 exact, dominated and similar clauses; and
2. the immediately preceding #29/#101 formats already present in users' DIM Notes.

Do not delete legacy recognisers. Prove that repeated runs replace one complete current clause rather than accumulating it, while ambiguous user-authored marker text remains untouched.

## 4. Add pairwise structured report data

Extend `ReportDecision` with two clearly named optional presentation fields, preferably:

```python
candidate_tuning_mod_slot: str | None
selected_tuning_mod_slot: str | None
```

Equivalent names are acceptable only if their meaning is equally clear and the browser does not need to parse another field to identify the two sides.

In `_decision_records()`:

1. build/use the existing `Id` → source row lookup;
2. for an armour decision with a non-empty `kept_id`, look up the already-selected row directly;
3. normalise the candidate row's raw `Tuning Stat` through the shared presenter;
4. normalise the selected row's raw `Tuning Stat` through the same presenter;
5. assign `none/unknown` for blank/unrecognised values on either actual comparison side; and
6. assign null/non-applicable values to weapons, ghosts and armour decisions that do not compare against a selected row.

Do not use `reason_slug`, Note parsing, stat similarity or group reconstruction to find the selected row. `kept_id` is authoritative.

Keep `SNAPSHOT_SCHEMA_VERSION == 2`, `RULESET_VERSION == 4` and the fingerprint unchanged. This is an additive completion of the coordinated M9 v2 projection, matching #101's precedent. Regenerate `tests/fixtures/report_snapshot_v2.json` deliberately and twice to prove byte-stable output.

If a strict consumer makes a version bump necessary, stop and return to Sol; that crosses this plan's compatibility boundary.

## 5. Preserve the #101 group contracts

Do not add another exact- or same-stat group projection.

- Exact groups continue to expose one always-present shared `tuning_mod_slot` because raw `Tuning Stat` remains part of exact identity.
- Same-stat members continue to expose `tuning_stat` and `tuning_mod_slot` per member.
- The server continues to return both group arrays unchanged from `snapshot_dict()`.
- Add or retain tests that make this explicit so helper relocation cannot regress #101.

The actual Armor duplicates rendering remains #102 work. Document that #102 must use the existing exact-group `tuning_mod_slot` in its always-visible group summary.

## 6. Render structured tuning in the ordinary Proposals view

In `review_ui.js`:

1. map the two new snapshot fields in `itemsFromSnapshot()` without reading `decision.note`;
2. construct a bounded presentation value such as `Candidate: Melee · Selected: Grenade` from those structured fields;
3. add an always-visible `Tuning Mod Slot` table column/cell;
4. keep the candidate and selected labels as actual text even when the values match;
5. show a neutral `—`/not-applicable state for non-comparison rows rather than inventing a tuning value;
6. update sortable-field handling consistently if the column header remains sortable; and
7. continue to build every node with `textContent`/text nodes.

Do not hide this comparison inside the existing expanded detail row. Do not use a tooltip, title attribute, icon alone or colour alone. Do not add a tuning filter unless separately requested; #104 only requires visibility.

`review_server.js` should inherit the new `COLUMNS` contract and normally remain unchanged. Existing view/sort/filter/focus state must continue to survive acknowledged repaint and envelope reconciliation because this ticket introduces no new state.

Adjust CSS only if required for a clear two-label cell at desktop and narrow widths. Keep the existing contained horizontal-scroller pattern rather than redesigning the page.

## 7. Failure, recovery and state behaviour

This ticket introduces no operation, mutation or retry.

- Invalid/missing required armour CSV fields continue to fail at the existing parser boundary.
- A missing selected `kept_id` row is an invariant violation and an escalation, not a cue to guess a partner.
- Upload/replacement failure, stale verdict rejection, finalisation, reset and shutdown remain byte-for-byte/protocol-equivalent.
- The tuning presentation remains readable in finalised state because it is ordinary snapshot text; mutation controls remain governed by existing code.
- Do not add automatic replay/retry or fixed sleeps.

## 8. Security and trust boundary

Maintain all existing boundaries:

- raw export text is untrusted;
- the browser renders structured fields with text APIs only;
- no HTML interpolation, `innerHTML`, URL construction or executable attribute receives an export value;
- ids/hashes remain opaque strings;
- no request-derived filesystem path is introduced;
- no network permission or endpoint is added;
- no dependency is added; and
- fake fixtures only are committed.

The normalised Tuning Mod Slot values presented to the browser must come from the fixed Python vocabulary. An unrecognised hostile string becomes `none/unknown`; it is never treated as markup or a new supported value.

## 9. Documentation and worklog

Update:

- `PLAN.md` — record the actual `#29 → #101 → #104 → #102` M9 sequence and state that #104 owns pairwise cross-surface tuning presentation while #102 owns group rendering.
- `README.md` — explain that armour comparison Notes/terminal/browser output labels both candidate and selected Tuning Mod Slots, with explicit `none/unknown` and no preference implied.
- `docs/browser-verification.md` — add a focused check that pairwise tuning is visible without expansion/hover, in light/dark and narrow layouts, and record the manual execution environment/result if Luna performs the visual pass.
- `WORKLOG.md` — add a newest-first dated entry describing the shared vocabulary, structured report fields, Note compatibility, browser presentation, tests, version decisions and any surprising finding.

Do not describe the #102 Armor duplicates view as delivered.

## 10. Commit and hand off

After every required gate passes:

1. inspect the complete diff against the implementation base;
2. confirm no private/generated/unrelated files are tracked;
3. commit with a focused message such as `Expose armor tuning slots across comparisons`;
4. push the implementation branch;
5. do not open a PR; and
6. return the structured handoff required below.

---

# Required automated tests

Add or update behavioural tests covering all of the following.

## Shared presenter and Notes

1. All six supported values normalise generically; use parameterisation and do not encode a preference.
2. Leading/trailing whitespace and case do not create a seventh value.
3. Blank and unrecognised values render exactly `none/unknown`.
4. Exact Notes show candidate and survivor values when equal.
5. Dominated Notes show candidate and partner values when equal, including `none/unknown`.
6. Similar Notes show different candidate and partner values in the correct orientation.
7. Reverse-direction similar decisions reverse only the labels appropriate to each candidate; selected ids remain the existing ids.
8. Hostile/unrecognised tuning input cannot forge a marker, structural clause, newline or supported value.
9. Exact, dominated and similar new-format clauses round-trip through the actual emitters repeatedly with one trailing tool marker.
10. Existing #29-style exact/dominated/similar clauses are still stripped and replaced.
11. Reason slugs, candidate ids and `kept_id` values are unchanged.

## Report and server snapshot

12. Exact decisions expose equal candidate/selected fields.
13. Dominated and similar decisions expose the already-selected row's value, including different and equal pairs.
14. Every supported label is exercised across candidate/selected positions without a preferred ordering assertion.
15. Blank/unrecognised comparison sides expose `none/unknown` rather than null/omission.
16. Non-armour and non-comparison decisions use the documented null/not-applicable state.
17. Snapshot schema remains 2, ruleset remains 4 and the run fingerprint is unchanged by presentation-only projection.
18. Exact and same-stat group payloads remain identical in membership/order/disposition and retain their #101 tuning fields.
19. A real server upload response equals `snapshot_dict()` for the new decision fields; no server reconstruction is added.
20. Full candidate and selected ids remain JSON strings.
21. Golden regeneration is byte-stable on a second run.

## Terminal output

22. `vault-cleaner armor` dry-run output contains the candidate and selected labels for exact, dominated and similar decisions.
23. `vault-cleaner report`/`summarize()` exposes the same information and still preserves the winner/partner reason inside its length bound.
24. No terminal test depends on a real vault row.

## JavaScript and browser

25. `itemsFromSnapshot()` maps candidate/selected tuning from structured fields and does not derive them from Note text.
26. The Proposals header contains `Tuning Mod Slot`, and an unexpanded row contains both explicit side labels.
27. Equal values remain displayed twice with their labels.
28. Different values appear in the correct candidate/selected orientation.
29. Non-comparison items display the neutral state without breaking sorting/grouping.
30. The column remains inert under prototype-shaped keys and hostile snapshot text; no `<img>`, `<script>` or other report-content element is created.
31. Existing class/location, focus-preserving repaint, filter reconciliation and opaque-ID tests remain green after the column count changes.
32. Add one focused `@pytest.mark.browser` case through the real packaged server UI using fake armour data. It must:
    - authenticate and upload a fake armour export;
    - locate one different-tuning pair and one equal/unknown pair in ordinary Proposals;
    - prove both labelled values are visible before clicking, hovering or expanding;
    - prove the field is text, not a colour-only badge; and
    - leave existing verdict and lifecycle behaviour untouched.

Do not add a browser retry or fixed sleep.

---

# Manual verification

Use only `tests/fixtures/armor_close.csv` or another deliberately fake fixture.

1. Start the packaged local server with `--no-wishlists` and an ephemeral port.
2. Upload the fake armour export.
3. In ordinary Proposals, verify an exact/equal or blank pair and a different-tuning similar pair show both sides before expansion.
4. Verify the Tuning Mod Slot text is distinct from the six-stat armour-scoring display.
5. Check desktop light and dark appearances.
6. Check approximately `390 × 844` narrow layout; the table may scroll horizontally but labels must remain legible and contained.
7. Use keyboard navigation to focus a row verdict control, acknowledge a verdict and confirm focus/state are preserved.
8. Confirm finalised state remains readable and frozen.
9. End with Shutdown or stop the server process.

Record environment, browser/version, viewport, fixture, pass/fail, defects corrected and remaining limitations in `docs/browser-verification.md` and the Luna handoff.

Do not claim that the Armor duplicates view was tested; it remains #102.

---

# Exact validation commands

Run from the repository root using the current branch.

## Focused Python/Node gate

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_duplicate_reference.py \
  tests/test_armor_dupes.py \
  tests/test_armor_close.py \
  tests/test_note_history.py \
  tests/test_note_history_roundtrip.py \
  tests/test_report.py \
  tests/test_report_run.py \
  tests/test_cli_report.py \
  tests/test_review_ui_js.py \
  tests/test_server_ui_js.py \
  tests/test_server_uploads.py
node --check src/vault_cleaner/ui/review_ui.js
node --check src/vault_cleaner/ui/review_server.js
```

If focused terminal tests land in another existing CLI test module, include that module in the focused command and record the exact final command.

## Golden reproducibility

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
sha256sum tests/fixtures/report_snapshot_v2.json
.venv/bin/python scripts/regenerate_report_snapshot.py
sha256sum tests/fixtures/report_snapshot_v2.json
git diff -- tests/fixtures/report_snapshot_v2.json
```

The two hashes must match. Inspect the diff and confirm it contains only the intended additive presentation fields and no semantic decision/group drift.

## Real-browser and packaged-wheel gate

```bash
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python scripts/check_wheel_install.py
VAULT_CLEANER_BROWSER_REQUIRED=1 \
  .venv/bin/pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results \
  tests/test_server_browser.py
```

## Full completion gate

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git diff --check origin/main...HEAD
test -z "$(git ls-files data/)"
git status --short
```

After committing, also run:

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff --check origin/main...HEAD
git status --short --branch
```

If the implementation base is newer than this plan's baseline, substitute that recorded base ref/SHA for review comparisons where appropriate.

---

# Luna completion gate

Luna may hand the branch back only when every item below is true:

- [ ] The branch started from the latest `main`, and its base SHA is recorded.
- [ ] The ticket-specific mechanical scope test passes for every production hunk.
- [ ] All six tuning values and `none/unknown` use one shared normaliser.
- [ ] Exact, dominated and similar Notes show candidate and selected values, including equal values.
- [ ] Old and new generated Notes both round-trip without accumulation.
- [ ] Report/server data supplies both sides structurally; JavaScript does not parse Notes.
- [ ] The ordinary Proposals view shows both values without expansion, hover or colour dependence.
- [ ] #101 exact/same-stat group truth is unchanged and still exposes tuning.
- [ ] Decision semantic capture and group membership/order/disposition match baseline.
- [ ] Snapshot schema remains 2, ruleset remains 4, and fingerprint inputs/values are unchanged for identical inputs.
- [ ] No server protocol, persistence, stale-state, lifecycle, authentication or filesystem-boundary change was made.
- [ ] No runtime/dev dependency or CI topology change was made.
- [ ] Focused, golden, wheel, Chromium and full gates pass.
- [ ] Only fake fixtures are committed; nothing under `data/` is tracked.
- [ ] `PLAN.md`, `README.md`, `docs/browser-verification.md` and `WORKLOG.md` are current.
- [ ] The implementation is committed and pushed.
- [ ] No pull request has been opened.

## Required Luna → Sol handoff

Return:

- implementation branch;
- base `main` SHA;
- commit SHA(s);
- files changed/deleted;
- concise implementation summary;
- exact Notes/report/browser payload shape chosen;
- tests added/changed;
- exact validation commands and results, including test counts;
- both golden hashes;
- browser environment and manual verification result;
- wheel proof result;
- semantic parity result;
- unresolved concerns;
- deviations from this plan and why; and
- explicit confirmation that no PR was raised.

---

# Orchestrating Sol review checklist and prompt

Review the completed Luna xhigh implementation for issue #104 in `tonym999/vault-cleaner`.

Do **not** raise a PR. Perform both plan-conformance and engineering review against the actual diff from Luna's recorded `main` base.

## Plan-conformance checklist

- [ ] Read issue #104, #29, #101, #105, #102, PR #107, this handoff and current `AGENTS.md`/`PLAN.md`.
- [ ] Confirm every production hunk passes the ticket-specific inclusion test.
- [ ] Confirm no change to fingerprints, compatibility, ranking, selected ids, actions, tags, reason slugs, pass order, group membership/disposition/order or verdict semantics.
- [ ] Compare the before/after semantic capture; do not rely only on Luna's summary.
- [ ] Confirm one normaliser handles all six values and `none/unknown` generically.
- [ ] Confirm candidate/selected orientation is correct for exact, dominated and both directions of similar pairs.
- [ ] Confirm equal values are still displayed on both sides.
- [ ] Confirm old and new Note formats are both recognised and emitter-driven round-trip tests cover every changed rule family.
- [ ] Confirm `ReportDecision` derives the selected value only by direct `kept_id` lookup in the loaded armour frame.
- [ ] Confirm non-comparison/null semantics are explicit and do not turn blank comparison values into omission.
- [ ] Confirm snapshot schema 2, ruleset 4 and the decision fingerprint remain unchanged.
- [ ] Confirm exact/same-stat group projections remain authoritative and unchanged except for any mechanical helper import.
- [ ] Confirm the server is still a pass-through and no endpoint/session/review validator changed.
- [ ] Search JavaScript for Note parsing, `innerHTML`, numeric id conversion and duplicate tuning normalisation.
- [ ] Inspect the live DOM/browser test: tuning must be visible in an unexpanded row as text, not inferred by colour.
- [ ] Confirm existing focus/reconciliation/class/location tests were updated only as mechanically required by the new column.
- [ ] Confirm #102 UI work was not pulled into this branch.
- [ ] Confirm docs do not overclaim and `WORKLOG.md` has a dated entry.
- [ ] Confirm no private data, new dependency, retry, fixed sleep or CI topology change.

## Independent validation to rerun

At minimum rerun:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_duplicate_reference.py \
  tests/test_armor_dupes.py \
  tests/test_armor_close.py \
  tests/test_note_history.py \
  tests/test_note_history_roundtrip.py \
  tests/test_report.py \
  tests/test_report_run.py \
  tests/test_review_ui_js.py \
  tests/test_server_ui_js.py \
  tests/test_server_uploads.py
.venv/bin/python scripts/check_wheel_install.py
VAULT_CLEANER_BROWSER_REQUIRED=1 \
  .venv/bin/pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results \
  tests/test_server_browser.py
.venv/bin/pytest -q
git diff --check origin/main...HEAD
test -z "$(git ls-files data/)"
```

If findings exist, return precise findings to Luna, require fixes on the same branch, rerun affected tests plus the complete gate, and review again.

When the orchestrating review is clean, hand the exact branch and commit to an **independent Sol high** reviewer. Do not mark it ready for PR yet.

---

# Independent Sol high review prompt

Independently review the completed implementation for issue #104 in `tonym999/vault-cleaner`.

The branch has been implemented by Luna xhigh and passed the orchestrating Sol's plan-conformance review. Do not assume the plan or implementation is correct merely because tests pass. Do not open a PR.

Focus especially on:

1. whether the report shape gives the browser enough explicit truth without Note parsing or selection reconstruction;
2. whether candidate and survivor/partner values can ever be swapped, omitted or mislabelled;
3. whether blank/unrecognised values are represented honestly on both sides;
4. whether helper relocation accidentally changes the raw exact fingerprint or same-stat grouping;
5. whether new Notes remain bounded, inert, replaceable and backwards-compatible with already-exported #29-style Notes;
6. whether schema v2/ruleset v4/fingerprint preservation is sound for this coordinated M9 additive field;
7. whether any strict consumer or lifecycle path was silently affected;
8. whether always-visible browser text is genuinely accessible at narrow widths and under finalised/read-only state;
9. whether opaque ids/hashes and hostile input remain safe; and
10. whether #102 group rendering or another incidental improvement slipped into scope.

Independently inspect the diff and rerun the important focused, Chromium, wheel and full gates. Return actionable findings with file/behaviour detail and required regression coverage. Only after all findings are fixed and the independent review is clean may the branch be reported as `READY FOR PR`.

---

# Reusable Luna xhigh execution prompt

Implement issue #104 in `tonym999/vault-cleaner` using the committed handoff at:

```text
handoffs/issue-104-luna-xhigh-implementation-plan.md
```

Use Luna xhigh. Read the entire handoff, issue #104 and its linked/dependency context (#29, #101, #105, #102 and merged PR #107), `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and the current relevant code/tests/docs before editing.

Rules:

- branch from the latest `main` and record its SHA;
- treat current repository state as authoritative if it has legitimately moved since the plan baseline;
- follow the plan's ticket-specific mechanical scope rule for every production hunk;
- carry only the existing candidate and already-selected survivor/partner Tuning Stat values;
- keep one shared six-value plus `none/unknown` presenter;
- preserve all decision/group semantics and the #101 group contract;
- keep snapshot schema v2, ruleset v4 and the fingerprint unchanged;
- make the browser consume structured report fields, never DIM Note text;
- preserve inert-text rendering and opaque string ids/hashes;
- do not change server protocol, verdicts, persistence, stale reconciliation, finalisation, reset, shutdown, authentication or lifecycle;
- do not implement #102's Armor duplicates view;
- add the required Python, Note-history, Node, server pass-through and real-Chromium tests;
- use fake fixtures only;
- update `PLAN.md`, `README.md`, `docs/browser-verification.md` and `WORKLOG.md`;
- run every focused, golden, wheel, browser, full, diff and hygiene command in the handoff;
- commit and push the implementation branch; and
- **do not open a pull request**.

If any stop condition is reached, stop implementation and return the issue to Sol with the exact conflict; do not broaden scope.

When complete, provide the full Luna → Sol handoff specified in the plan, including branch, base SHA, commits, changed files, payload/Note shape, tests, exact validation results and counts, both golden hashes, browser/manual result, semantic parity evidence, risks/deviations and confirmation that no PR was raised.
