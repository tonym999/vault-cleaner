# Ticket

**Repository:** `tonym999/vault-cleaner`  
**Issue:** `#105 — Model current location and Guardian class as distinct fields (Owner is not an owner)`  
**Planning baseline:** `main` at `afbde22bf124a19c97689a3c43dad8578d14f003`  
**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → orchestrating Sol reviews → independent Sol high reviews → PR

Luna must **not** raise the pull request. The implementation branch must be reviewed first.

## Objective

Replace the misleading presentation/model field `owner` with two independent concepts without changing any rule decision:

- `location`: DIM `Owner`, carried verbatim as the item's current physical location;
- `guardian_class`: armour `Equippable`, carried verbatim; empty for weapons and ghosts.

Expose Guardian class as a first-class review facet while retaining location as useful secondary information. Bump only the report **snapshot** schema as required, preserve the ruleset/fingerprint/persisted-veto semantics, relabel existing human-readable duplicate references from `owner` to `location`, and keep every existing duplicate/scoring/review decision invariant unchanged.

## Intended end state

After #105:

- Python decision/evaluation models use `location` and `guardian_class`; they no longer model DIM `Owner` as an owning identity.
- Armour derives `guardian_class` only from `Equippable`; weapons and ghosts store `guardian_class=""`.
- The snapshot exposes `location` and `guardian_class` as separate keys.
- The browser still has the existing Kind facet and adds a Class facet. Class-neutral items display under their kind (`weapons` / `ghosts`) only in the presentation layer; the stored `guardian_class` remains empty.
- Location remains visible in the proposal table but is no longer a primary filter facet.
- Human-readable terminal output uses explicit location/class wording instead of an ambiguous bare owner value.
- Duplicate Notes say `location <value>` inside the existing bounded bracketed reference; class is deliberately not added to those Notes.
- `SNAPSHOT_SCHEMA_VERSION` is exactly one version ahead of the pre-change schema unless another coordinated ticket has already performed that same bump.
- `RULESET_VERSION`, fingerprint inputs, rule order, actions, tags, reason slugs, survivors/partners and persisted veto behaviour are unchanged.

## Why this ticket is ready

- #29 is complete and merged. Its human-readable survivor/partner reference seam and emitter-driven Notes round-trip coverage are present on `main`.
- #105 has no blocking dependency.
- The authoritative class source already exists: `parse.py` requires armour `Equippable`, and the armour score pass already groups on `Equippable` + `Type`.
- The browser already consumes the shared report snapshot and has a local presentation/filter seam in `review_ui.js` / `review_server.js`.
- Snapshot schema and ruleset versions are already deliberately independent.

The implementation must still perform the issue's fresh-export measurement before changing code.

---

# Review model

## Independent review path

```text
Sol orchestrator
    ↓
Luna xhigh implementation
    ↓
Same Sol orchestrator plan-conformance/engineering review
    ↓
Independent Sol high final review
    ↓
PR
```

This ticket is presentation-only from the rules engine's perspective, but it **does** change a versioned cross-runtime snapshot contract from schema v1 to v2 (unless #101 has already made the coordinated bump), deliberately changes saved review-manifest compatibility, and changes the generated Notes presentation grammar that may already exist in live DIM data. Those are protocol/compatibility boundaries, so the higher review path is warranted even though persistence, finalisation, authentication, ranking and decision semantics must remain untouched.

---

# Authoritative context

Before changing code, read on the latest `main`:

- `AGENTS.md`
- `PLAN.md`, especially the M7 snapshot boundary, rule ordering and M9 section
- issue #105 and all comments
- #29 (completed presentation foundation)
- #101 (parallel authoritative armour exact-group snapshot work)
- #104 (parallel tuning presentation work, depends on #101 and blocks #102)
- #102 (downstream Armor duplicates browser view)
- latest `WORKLOG.md` entries, especially the 2026-08-31 #29 emitter-driven Notes coverage
- `README.md` review workflow / duplicate-reference wording
- all production and test files listed below

Treat these as authoritative and do not silently redesign them:

- `pipeline.py` and the existing ordered rule passes determine the decision set.
- Armour `Equippable` is the class source already used by existing rules.
- DIM `Owner` is a volatile location only; never infer class from it.
- `report_run.compute_fingerprint()` plus `_decision_config()` define the review fingerprint. This ticket adds no fingerprint input.
- `RULESET_VERSION` changes only for decision-semantic/rule-order changes; it must remain unchanged here.
- `review.py` deliberately pins a review manifest's nested snapshot schema exactly.
- `server.session` / `review_session` remain authoritative for lifecycle, verdict and persistence semantics.
- `note_history.py` recognises bracketed duplicate references opaquely. Prefer proving compatibility with emitter-driven tests over changing its grammar unnecessarily.

---

# Current repository state relevant to #105

Planning inspected `main` at `afbde22bf124a19c97689a3c43dad8578d14f003`.

1. **#101 has not landed at the planning baseline.** `report_run.SNAPSHOT_SCHEMA_VERSION` is still `1`; `RULESET_VERSION` is `3`.
2. `dupes.Decision`, `report_run.ReportDecision` and `armor.ArmorEvaluation` still expose `owner`.
3. `ReportDecision` snapshots are currently produced with `asdict(decision)` directly inside `snapshot_dict()`. The issue wording mentions `_decision_snapshot`, but **there is no `_decision_snapshot` helper on current `main`**. Do not add an abstraction merely to match stale issue wording; make the smallest truthful change against the code that exists when Luna starts.
4. `_evaluation_snapshot()` also serialises the dataclass, with two derived armour booleans added afterwards.
5. Current construction sites copy DIM `Owner` into decisions/evaluations. In addition to the files named in the issue, **`src/vault_cleaner/rules/armor_dupes.py` also constructs `Decision(owner=...)` on current `main`**. It is therefore legitimately in scope and must not be missed.
6. Armour score grouping already uses `groupby(["Equippable", "Type"])`; exact/close duplicate grouping does not use `Owner`. `armor_dupes.py` explicitly treats Owner as mutable state, not roll identity.
7. `parse.py` requires `Equippable` only for armour. Weapon and ghost schemas do not contain it and must remain that way.
8. `review_ui.js` currently maps `decision.owner` to `item.owner`, filters/sorts on owner, and has `Owner` in both column definitions. `review_server.js` stores `query.owner`, reconciles it, and renders an Owner filter.
9. `review.py` imports `SNAPSHOT_SCHEMA_VERSION` and rejects a review manifest whose nested snapshot version is not exactly the current build's version. Its manifest decision schema has no owner/location/class field, so no production validator expansion is required.
10. The local server's **session envelope** has its own `SESSION_SCHEMA_VERSION = 1`. That is **not** the report snapshot schema and must not be bumped by #105.
11. `duplicate_reference.weapon_reference()` and `armor_reference()` currently emit `owner <value>` inside the bounded bracketed reference.
12. `note_history._GENERATED_CLAUSE_RES` matches the entire bracket body as opaque non-`]` text, and the current emitter-driven round-trip suite covers weapon exact dupes, armour exact dupes and both armour close-dupe emitters.
13. `tests/test_report_run.py` points at `report_snapshot_v1.json`, asserts schema v1, and already proves that changing only `SNAPSHOT_SCHEMA_VERSION` does not change the input fingerprint.
14. `scripts/regenerate_report_snapshot.py` also points at `report_snapshot_v1.json`.
15. The principal fake armour fixture exercises Titan and Warlock but not Hunter. #105 requires a fresh real-export measurement and fake coverage for Hunter plus empty/unrecognised behaviour.
16. `README.md` still documents duplicate references with `owner Vault` and shows a review manifest containing snapshot schema v1.
17. CI runs Ruff and the full pytest suite on Ubuntu/Windows and a separate Ubuntu Chromium job. The browser acceptance file currently has two tests; extend one of them for this ticket rather than adding a gratuitous third browser flow.

---

# Dependencies and assumptions

## Related ticket coordination

- **#29:** closed/landed. Reuse its bounded duplicate-reference and Notes-history seams; do not redesign them.
- **#101:** open at planning time. It also extends the report snapshot. #105 and #101 must result in **one coordinated snapshot schema bump**, not two presentation bumps.
- **#104:** open and downstream of #101. Do not absorb tuning-mod presentation into #105.
- **#102:** downstream Armor duplicates UI. It should consume the class facet introduced here; do not implement its dedicated duplicate-group view in #105.

## Schema coordination gate before implementation

Immediately after branching from the latest `main`, inspect the live value and recent history:

```bash
git log -5 --oneline
python - <<'PY'
from vault_cleaner import report_run
print(report_run.SNAPSHOT_SCHEMA_VERSION)
print(report_run.RULESET_VERSION)
PY
```

Apply this mechanical rule:

- If latest `main` still has `SNAPSHOT_SCHEMA_VERSION == 1`, #105 owns the `1 → 2` bump.
- If #101 has landed first and latest `main` already has snapshot schema `2`, **do not bump to 3**. Consume schema v2 and integrate #105's new fields into that same version/golden.
- If latest `main` has a schema greater than `2`, a partially landed owner/location split, or a #101 snapshot shape that makes the #105 plan materially incompatible, **stop and return to Sol for replanning** rather than guessing at a new version.
- Never change `SESSION_SCHEMA_VERSION` as part of this coordination.

## Fresh-export measurement prerequisite

Before code changes, measure a **fresh private armour export**. Do not commit or paste rows, names, hashes, instance ids or paths into the repository. Aggregate vocabulary/counts only are acceptable.

Set `ARMOR_EXPORT` to the fresh local DIM armour CSV, then run:

```bash
ARMOR_EXPORT=data/in/destiny-armor.csv .venv/bin/python - <<'PY'
import os
from pathlib import Path
from vault_cleaner.parse import load_armor

frame = load_armor(Path(os.environ["ARMOR_EXPORT"]))
print("Equippable values:", sorted(repr(v) for v in frame["Equippable"].unique()))
print("Empty Equippable count:", int(frame["Equippable"].str.strip().eq("").sum()))
exotics = frame[frame["Rarity"].eq("Exotic")]
print(
    "Exotic Equippable counts:",
    exotics["Equippable"].value_counts(dropna=False).sort_index().to_dict(),
)
PY
```

If a fresh real armour export is unavailable, or the measured shape contradicts the ticket's assumptions in a way that would require validation/inference policy, stop and return to Sol. Do not invent class parsing from `Owner`.

---

# Scope

## In scope

- Rename modelled `owner` → `location` on `Decision`, `ReportDecision` and `ArmorEvaluation`.
- Add `guardian_class` to those models.
- Populate `location` from DIM `Owner` verbatim.
- Populate armour `guardian_class` from `Equippable` verbatim.
- Populate weapon/ghost `guardian_class` as `""`.
- Cover every current decision construction site, including `armor_dupes.py`.
- Serialise both fields in report snapshots/evaluations.
- Perform the coordinated snapshot schema bump/golden update if it has not already landed through #101.
- Keep old review-manifest rejection explicit and tested after the snapshot schema change.
- Replace the browser Owner facet with a Class facet while retaining Kind independently.
- Retain location as a secondary sortable/display column; do not make it the primary class-browsing facet.
- Use a presentation-only class fallback (`guardian_class` if non-empty, otherwise item `kind`) so the browser can present Hunter / Warlock / Titan / weapons / ghosts while the stored model stays clean.
- Relabel CLI/report output so location and class are not conflated.
- Relabel `owner` → `location` inside human-readable duplicate references.
- Prove old and new generated Note clauses remain recognisable/replaced correctly.
- Extend fake coverage for Hunter, a location/class mismatch, and empty/unrecognised class values without adding hard-coded class validation.
- Update directly affected documentation and `WORKLOG.md`.

## Out of scope

- Any new rule that filters, scores, protects, junks or ranks by the new `guardian_class` field.
- Any change to `Equippable`'s existing use in armour scoring/grouping.
- Any change to duplicate fingerprints, exact/close compatibility, group membership, partner/survivor selection, pass order, safety rails, action/tag/reason semantics or finalisation.
- Parsing Guardian class from `Owner` text, including strings such as `Titan(550)`.
- Adding `Equippable` to weapon or ghost required schemas.
- Adding a class config key or `_decision_config()` input.
- Adding class to bounded duplicate Note references.
- #101's authoritative armour exact-group projection.
- #104's Tuning Mod Slot presentation.
- #102's dedicated Armor duplicates view or group-level verdict UX.
- Server authentication, request schemas, verdict payloads, lifecycle, persistence, stale-state protocol, reset/finalise/shutdown behaviour.
- A new runtime dependency or CI architecture change.

---

# Ticket-specific algorithmic scope rule

For **every proposed diff hunk**, Luna must be able to assign it to exactly one allowed category:

1. **MODEL:** rename `owner` to `location` or add/carry `guardian_class` on #105-owned models.
2. **DERIVATION:** copy DIM `Owner` to location, armour `Equippable` to Guardian class, or class-neutral `""` for weapons/ghosts.
3. **SNAPSHOT:** serialise the two fields, coordinate the single snapshot schema bump, regenerate/update its golden and compatibility tests.
4. **PRESENTATION:** label/render/sort/filter the two concepts correctly in CLI/report/browser, including the presentation-only class fallback.
5. **NOTES:** relabel the existing bounded reference fragment from `owner` to `location` and prove old/new Notes-history compatibility.
6. **TEST/FIXTURE:** regression coverage mechanically required to prove categories 1–5 without committing private data.
7. **DOC/WORKLOG:** documentation needed to describe the new field semantics/version/compatibility and record implementation evidence.

A hunk **belongs to #105 only if** it fits one of those categories **and** all of these invariants remain true:

```text
rule inputs used for decisions: unchanged
rule order: unchanged
duplicate/close group membership: unchanged
selected survivor/partner: unchanged
action/tag/reason slug: unchanged
RULESET_VERSION: unchanged
fingerprint inputs: unchanged
server session schema/version: unchanged
verdict/finalisation/persistence semantics: unchanged
Guardian class source for armour: Equippable only
Guardian class source for weapons/ghosts: empty only
```

### Mandatory stop/escalation conditions

Stop implementation and return the ticket to Sol if **any** proposed change would require:

- changing a duplicate fingerprint, close-dupe compatibility bucket, armour score grouping or any other rule grouping;
- changing a winner/partner selector, safety rail, rule ordering, action, tag or reason slug;
- changing `RULESET_VERSION`, `_decision_config()`, or fingerprint construction/inputs;
- using `guardian_class` as a new rule input rather than a presentation copy of existing data;
- parsing or normalising class from DIM `Owner`;
- adding a hard-coded `{Hunter, Warlock, Titan}` validation gate;
- changing weapon/ghost parser schemas to require `Equippable`;
- changing `review.py` manifest decision keys, server verdict payloads or session lifecycle to make the split work;
- changing `SESSION_SCHEMA_VERSION`;
- changing authentication, stale-state, reset, finalisation, shutdown or persistence behaviour;
- introducing a new runtime dependency;
- implementing #101, #104 or #102 work beyond the minimum compatibility needed to consume whatever has already landed on `main`;
- resolving a merge/schema conflict by creating snapshot schema v3 without Sol approval;
- committing real vault rows or identifying private export data.

Incidental defects outside this rule should be reported separately in the Luna → Sol handoff, not fixed inside #105.

---

# Expected change footprint

## Likely production files

```text
src/vault_cleaner/rules/dupes.py
src/vault_cleaner/rules/weapons.py
src/vault_cleaner/rules/armor.py
src/vault_cleaner/rules/armor_dupes.py
src/vault_cleaner/rules/armor_close.py
src/vault_cleaner/rules/ghosts.py
src/vault_cleaner/report_run.py
src/vault_cleaner/report.py
src/vault_cleaner/cli.py
src/vault_cleaner/duplicate_reference.py
src/vault_cleaner/ui/review_ui.js
src/vault_cleaner/ui/review_server.js
```

## Likely tests/fixtures

```text
tests/test_report_run.py
tests/test_review.py
tests/test_duplicate_reference.py
tests/test_note_history.py
tests/test_note_history_roundtrip.py
tests/test_review_ui_js.py
tests/test_server_ui_js.py
tests/test_server_browser.py
tests/test_cli_report.py
# plus focused rule/CLI tests that directly construct/assert Decision objects
tests/fixtures/<new fake class/location armour fixture if useful>
tests/fixtures/report_snapshot_v2.json   # if #105 performs the v1→v2 bump
scripts/regenerate_report_snapshot.py    # golden filename/version alignment
```

Prefer a **dedicated fake fixture** for Hunter/location mismatch/empty/unrecognised class coverage rather than perturbing the widely shared `armor.csv` unless changing that shared fixture is clearly simpler and all dependent assertions are updated intentionally.

## Documentation

```text
README.md
PLAN.md              # concise M9 model wording only; no unrelated rewrite
WORKLOG.md
```

## Files/components that should normally remain unchanged

```text
src/vault_cleaner/parse.py
src/vault_cleaner/pipeline.py
src/vault_cleaner/config.py
src/vault_cleaner/review.py
src/vault_cleaner/review_session.py
src/vault_cleaner/server/app.py
src/vault_cleaner/server/session.py
src/vault_cleaner/note_history.py       # expected to remain unchanged if opaque bracket recognition proves sufficient
src/vault_cleaner/ui/review_server.html
src/vault_cleaner/ui/review.css
pyproject.toml
config.toml
.github/workflows/ci.yml
```

If a substantive change is needed in any server lifecycle/persistence/authentication file, `parse.py` weapon/ghost schema, `review.py` validation contract, `note_history.py` recogniser, or config/fingerprint code, explain why and apply the stop rule before proceeding.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline on latest `main`

Create an implementation branch from latest `main`, not from the handoff branch.

Suggested branch:

```text
issue-105-location-guardian-class
```

Record the base SHA and run:

```bash
git status --short
git rev-parse HEAD
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git ls-files data/
```

`git status --short` must be clean and `git ls-files data/` must print nothing.

Before editing, save a fake-data **decision-semantics baseline** outside the repo:

```bash
.venv/bin/python - <<'PY' > /tmp/issue105-before.json
import json
from pathlib import Path
from vault_cleaner.report_run import run_report

f = Path("tests/fixtures")
run = run_report(
    config_path="nonexistent.toml",
    weapons_path=f / "weapons_dupes.csv",
    armor_path=f / "armor.csv",
    ghosts_path=f / "ghosts_cleanup.csv",
    no_wishlists=True,
)
signature = [
    {
        "id": d.id,
        "kind": d.kind,
        "hash": d.hash,
        "action": d.action,
        "tag": d.tag,
        "reason": d.reason,
        "kept_id": d.kept_id,
        "protection_level": d.protection_level,
        "protection_reason": d.protection_reason,
    }
    for section in run.sections
    for d in section.decisions
]
print(json.dumps({"fingerprint": run.fingerprint, "decisions": signature}, indent=2, sort_keys=True))
PY
```

Do **not** include `note`, location, Guardian class or other presentation-only fields in this parity signature; those are expected to change.

Then execute the schema coordination gate and the fresh-export measurement described above.

## 2. Split the shared decision model without changing rule behaviour

In `rules/dupes.py`:

- rename `Decision.owner` to `Decision.location`;
- add `Decision.guardian_class`;
- keep all action/tag/note/kept-id fields and ranking helpers unchanged;
- weapon exact-dupe `Decision` objects get `location=row.get("Owner", "")` and `guardian_class=""`.

Update every constructor against the current code, not only the ticket's original list:

- `rules/weapons.py`: location from Owner; class empty;
- `rules/dupes.py`: location from Owner; class empty;
- `rules/armor_dupes.py`: location from Owner; class from `Equippable`;
- `rules/armor_close.py`: location from Owner; class from `Equippable`;
- `rules/armor.py`: every scoring/last-archetype decision gets location from Owner and class from `Equippable`;
- `rules/ghosts.py`: location from Owner; class empty.

Use the raw string values already supplied by pandas. Do not parse, title-case, strip power suffixes, validate against a class enum or derive class from `Owner`.

Search after the model edit for stale field accesses:

```bash
git grep -nE '\.owner\b|owner=' -- src tests ':!tests/fixtures/*'
```

Remaining `Owner` mentions are legitimate only when explicitly reading DIM's raw input column, describing migration/history, or testing that location is sourced from Owner. There should be no surviving model-level `decision.owner` use.

## 3. Update armour evaluation/report models

In `rules/armor.py`:

- rename `ArmorEvaluation.owner` → `location`;
- add `guardian_class` populated from the same row's `Equippable` verbatim;
- retain the existing `equippable` field because it is already part of the score/evaluation presentation contract and may be consumed by #101; do not refactor it away in #105.

In `report_run.py`:

- rename `ReportDecision.owner` → `location`;
- add `guardian_class`;
- have `_decision_records()` copy both fields from the rule `Decision` object;
- do not derive class again from location or create a second rule path.

The model should now carry an armour row such as `Equippable=Warlock, Owner=Titan(550)` as two distinct truths:

```text
guardian_class = "Warlock"
location       = "Titan(550)"
```

## 4. Update snapshot schema and compatibility deliberately

Work from the **current** snapshot implementation:

- If decisions are still serialised via `asdict(decision)`, let the dataclass change produce `location` and `guardian_class`; do not add `_decision_snapshot()` solely because the issue mentioned a helper that does not exist.
- `_evaluation_snapshot()` should emit the renamed/new dataclass fields naturally while preserving its current `cited_by_close_pass` and `combo_kept_elsewhere` additions.
- The old `owner` key must disappear from new decision/evaluation snapshot objects.

Versioning:

- If starting from snapshot schema 1, set `SNAPSHOT_SCHEMA_VERSION = 2`.
- If #101 has already landed schema 2, keep it at 2.
- Leave `RULESET_VERSION = 3` (or whatever unchanged current value exists on latest main) exactly unchanged.
- Leave `_decision_config()` unchanged.
- Leave `SESSION_SCHEMA_VERSION` unchanged.

If #105 performs the v1→v2 bump, rename the golden truthfully rather than leaving schema-v2 content in a `*_v1.json` file:

```bash
git mv tests/fixtures/report_snapshot_v1.json tests/fixtures/report_snapshot_v2.json
```

Update `tests/test_report_run.py` and `scripts/regenerate_report_snapshot.py` to use the current golden filename, then regenerate with:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
```

If #101 has already created/renamed a schema-v2 golden, reuse it and do not create a competing one.

Make the existing fingerprint-version regression future-proof: test `current_schema + 1`, not a hard-coded monkeypatch to `2`, so it continues proving that snapshot-only version movement does not affect the decision fingerprint.

## 5. Preserve review compatibility boundaries

`review.py` production code should normally require no change because it already compares the manifest's nested snapshot schema against imported `SNAPSHOT_SCHEMA_VERSION`.

Update test helpers that hard-code nested snapshot schema `1` to use the current `SNAPSHOT_SCHEMA_VERSION` for valid manifests, then add/retain an explicit regression proving a pre-upgrade snapshot-schema-1 review manifest is rejected by a schema-v2 build.

Also prove:

- `MANIFEST_SCHEMA_VERSION` itself remains unchanged;
- `OVERRIDES_SCHEMA_VERSION` remains unchanged;
- existing persisted vetoes still classify/apply based on the unchanged fingerprint/decision identity;
- no `location` or `guardian_class` field is added to `review._DECISION_KEYS` or verdict payloads.

## 6. Implement the browser presentation split

### `review_ui.js`

In `itemsFromSnapshot()` map the clean snapshot fields into the local presentation item, for example:

```text
location      ← decision.location
guardianClass ← decision.guardian_class
classFacet    ← guardianClass when non-empty, otherwise item.kind
```

`classFacet` is a browser-only derived value. It must never be written back into the snapshot/session or used by Python rules.

Update filtering/sorting/columns so:

- existing **Kind** remains independent (`weapons`, `armor`, `ghosts`);
- new **Class** facet uses the presentation value `Hunter`, `Warlock`, `Titan`, any unrecognised non-empty `Equippable` verbatim, or kind fallback for empty values;
- **Location** is visible as a secondary column and sortable if columns are sortable;
- **Owner** no longer appears as a table heading, sort field or primary filter;
- the raw `guardianClass` remains available for tests/details if useful, but the fallback is presentation-only.

Keep both `COLUMNS` definitions and `SORT_FIELDS` consistent. A sensible column order is:

```text
Name | Instance id | Kind | Class | Location | Action | Reason | Protection | Verdict
```

Do not change the safe DOM construction model: all export-derived strings still go through `textContent`/text nodes.

### `review_server.js`

Replace local `query.owner` with the class-facet query field, keep `query.kind`, and update the reconciliation/invalidation list accordingly.

Replace the rendered Owner select with a Class select sourced from the derived class facet. Location stays a table column, not a primary facet.

Preserve all current local-state behaviour:

- a still-valid class filter survives a same/new authoritative envelope;
- an invalid class filter is cleared and reported in `viewInvalidated`;
- unrelated text/kind/reason/protection/verdict filters, grouping, sort direction and expanded rows remain intact;
- verdict acknowledgements still repaint in place where applicable.

Do not touch fetch endpoints, revision checks, mutation gating, finalisation, reset, shutdown or session schema.

## 7. Correct terminal/report wording

Update the four current CLI locations that expose the raw/decision owner concept:

- `roundtrip`: label DIM Owner explicitly as `location` (this command handles class-neutral weapon/ghost inputs only);
- `dupes`: use `d.location`; do not manufacture a Guardian class for weapons;
- `armor`: use `d.location` and expose `d.guardian_class` as the class value; if a measured/synthetic armour class is empty, present the honest fallback under the armour kind rather than inventing Hunter/Warlock/Titan;
- `ghosts`: use `d.location`; class remains neutral/empty.

In the combined `report.summarize()` per-item line, show both axes explicitly because the output mixes kinds. Use `d.guardian_class or d.kind` only as the **display facet** and label location separately. Preserve bounded/safe fragments and reason-tail presentation.

Do not alter action counts, ordering, dry-run behaviour or CSV output rows.

## 8. Relabel duplicate references without adding class

In `duplicate_reference.weapon_reference()` and `armor_reference()`:

- continue reading DIM `Owner` directly from the referenced source row because it is the location source;
- change only the human label from `owner <value>` to `location <value>`;
- keep bounded escaping, id shortening/collision behaviour, roll/tuning/spirit details and winner/partner semantics unchanged;
- do **not** add Guardian class to the bracketed reference.

`note_history.py` is expected to remain unchanged because its current exact/close patterns treat the bracket body opaquely. Prove this rather than weakening/expanding the recogniser.

Add an explicit migration regression: a previously generated current-format duplicate clause containing `owner ...` at the Notes tail must still be stripped and replaced by the new `location ...` clause, without duplicating markers or losing a human-authored prefix.

Keep the existing emitter-driven round-trip coverage for:

- weapon exact duplicate notes;
- armour exact duplicate notes;
- armour dominated notes;
- armour similar notes.

Those tests must consume the emitter's actual output rather than reconstructing the grammar.

## 9. Add focused model/presentation regressions

Use fake data only. At minimum prove:

1. **Source split:** an armour item with `Equippable=Warlock` and `Owner=Titan(550)` produces `guardian_class="Warlock"` and `location="Titan(550)"` in decisions/evaluations/snapshot.
2. **Class-neutral kinds:** weapon and ghost decisions/snapshot rows store `guardian_class=""` while retaining their location.
3. **Hunter:** a fake Hunter armour row reaches model/snapshot/UI coverage.
4. **Verbatim unknown:** an unrecognised fake `Equippable` token is carried unchanged and appears as an ordinary facet value; it is not rejected/coerced.
5. **Empty:** empty `Equippable` remains empty in the stored model and receives only the presentation-layer kind fallback.
6. **No old key:** new decision/evaluation snapshot objects contain `location` and `guardian_class`, not `owner`.
7. **UI axes:** Kind filtering remains independent from Class filtering; selecting a class does not mean current character location.
8. **Location column:** location remains visible/sortable but no Owner primary filter exists.
9. **State reconciliation:** valid class filter survives; stale class filter clears without resetting unrelated query/sort/expanded state.
10. **Opaque ids/hostile text:** existing uint64-string and inert-DOM guarantees remain intact.
11. **Schema compatibility:** nested snapshot schema 1 manifest is rejected after schema 2; valid current-schema manifest still parses.
12. **Fingerprint stability:** snapshot schema/field presentation changes do not change the report fingerprint.
13. **Notes migration:** legacy/current `owner`-labelled bracket clauses are still recognised and replaced; new `location`-labelled clauses round-trip stably.
14. **Decision semantics:** existing rule tests remain unchanged in their expected decision membership, action, tag, reason and survivor/partner ids.

Where current tests manually construct `Decision`, `ReportDecision`, `ArmorEvaluation` or JS items, update them to the new model rather than adding compatibility aliases that perpetuate `owner`.

## 10. Extend existing browser smoke coverage, do not redesign browser tests

Extend the existing armour browser smoke flow in `tests/test_server_browser.py` so the real DOM proves the new presentation while preserving the current upload → verdict → finalise → download purpose.

Before finalisation, assert at least:

- Kind filter remains present;
- Class filter is present and offers the values provided by the fake armour input (including Hunter when that fixture is used);
- there is no Owner primary filter;
- table headers include Class and Location;
- a row whose location differs from its armour class shows the two values in the correct columns;
- selecting Class filters by Guardian class, not by location;
- reset the filter before continuing the existing verdict/finalisation/download assertions.

Do not create a new browser protocol or a third end-to-end lifecycle scenario merely for these checks.

## 11. Re-run the semantic parity capture

After implementation and before committing, produce the same signature:

```bash
.venv/bin/python - <<'PY' > /tmp/issue105-after.json
import json
from pathlib import Path
from vault_cleaner.report_run import run_report

f = Path("tests/fixtures")
run = run_report(
    config_path="nonexistent.toml",
    weapons_path=f / "weapons_dupes.csv",
    armor_path=f / "armor.csv",
    ghosts_path=f / "ghosts_cleanup.csv",
    no_wishlists=True,
)
signature = [
    {
        "id": d.id,
        "kind": d.kind,
        "hash": d.hash,
        "action": d.action,
        "tag": d.tag,
        "reason": d.reason,
        "kept_id": d.kept_id,
        "protection_level": d.protection_level,
        "protection_reason": d.protection_reason,
    }
    for section in run.sections
    for d in section.decisions
]
print(json.dumps({"fingerprint": run.fingerprint, "decisions": signature}, indent=2, sort_keys=True))
PY

diff -u /tmp/issue105-before.json /tmp/issue105-after.json
```

The diff must be empty. If it is not, stop and investigate; do not rationalise a decision change as part of this presentation ticket.

If the shared `armor.csv` fixture was intentionally changed for class coverage, use a pristine baseline copy/commit or a dedicated untouched parity fixture so this test still compares identical inputs before/after implementation. This is one reason a dedicated new class fixture is preferred.

## 12. Documentation and worklog

Update `README.md` where it is now misleading:

- duplicate-reference example: `owner Vault` → `location Vault`;
- browser workflow: mention separate Kind and Class facets and location display;
- review manifest example: show the current snapshot schema version after the coordinated bump; do **not** change manifest schema version or pretend the server imports manifests;
- keep ruleset/fingerprint language truthful.

Add one concise M9 sentence/paragraph to `PLAN.md` documenting the two presentation axes (`location` from Owner, `guardian_class` from armour Equippable, class-neutral weapons/ghosts) without changing M9 delivery ownership.

Add a newest-first dated `WORKLOG.md` entry recording:

- the aggregate fresh-export Equippable measurement only (no private rows/ids/names/paths);
- model/UI/Notes changes;
- whether #105 or #101 owned the single schema-v2 bump;
- old manifest schema-v1 rejection after upgrade;
- unchanged `RULESET_VERSION` and fingerprint;
- decision-parity diff result;
- Notes old-owner/new-location migration result;
- focused/full/browser validation results;
- any environmental limitation or deviation.

---

# Required automated tests

The implementation should add/update behavioural coverage, not source-string checks where a behavioural seam exists.

## Python/model/snapshot

- `tests/test_report_run.py`
  - schema current value and golden;
  - `location`/`guardian_class` present, `owner` absent;
  - armour class/location mismatch preserved separately;
  - weapon/ghost class empty;
  - Hunter and noncanonical/empty class cases where appropriate;
  - schema-version-only change leaves fingerprint stable.
- Rule tests (`test_dupes.py`, `test_weapons_rules.py`, `test_armor_rules.py`, `test_armor_dupes.py`, `test_armor_close.py`, `test_ghost_rules.py` as affected)
  - new dataclass fields populated correctly;
  - existing decision membership/ranking assertions remain authoritative.
- `tests/test_review.py`
  - valid manifest helper uses current snapshot schema;
  - old snapshot schema 1 manifest rejected after schema 2;
  - override/persisted veto semantics unaffected.

## Notes/presentation

- `tests/test_duplicate_reference.py`
  - `location` label for weapon and armour references;
  - hostile location content remains bounded/inert/marker-safe;
  - class is not added to bounded references.
- `tests/test_note_history_roundtrip.py` and/or `tests/test_note_history.py`
  - actual new emitters round-trip;
  - pre-upgrade `owner` bracket clauses are still recognised/replaced.
- `tests/test_cli_report.py` and directly relevant CLI tests
  - combined report distinguishes Class from Location;
  - specialised output no longer calls location an owner.

## JavaScript/server UI

- `tests/test_review_ui_js.py`
  - snapshot mapping for `guardian_class`/`location`;
  - Kind and Class filters are independent;
  - class-neutral fallback is presentation-only;
  - unknown/empty values are honest;
  - Class/Location columns and sort semantics;
  - Owner filtering removed;
  - existing hostile-text/precision/persisted-veto behaviour preserved.
- `tests/test_server_ui_js.py`
  - class facet local state reconciliation replaces owner-filter reconciliation;
  - unrelated local state is preserved;
  - session envelope schema remains 1 and lifecycle tests remain unchanged.
- `tests/test_server_browser.py`
  - extend existing armour smoke test with real-DOM Class/Kind/Location assertions, then continue existing finalisation/download proof.

## Golden

Regenerate with the repository script and require `test_regeneration_script_reproduces_the_committed_golden` to pass. If #105 owns schema v2, the golden filename/test names should no longer claim v1.

---

# Manual verification

After automated tests, inspect a fake browser review session and confirm:

- armour parked on a character different from its `Equippable` class shows the class under **Class** and holder/vault under **Location**;
- Kind and Class can be browsed independently;
- weapons/ghosts remain stored class-neutral but appear under their kind in the Class browsing facet;
- no Owner filter remains;
- moving/filtering by Location is not silently reintroduced as class behaviour;
- hostile text remains plain text;
- finalisation/download still works through the unchanged server flow.

Also inspect a fake duplicate Note for one weapon and one armour comparison and confirm it says `location`, does not add class, remains bounded, and retains the existing reason/winner/partner structure.

Do not use or record identifiable real-vault items for screenshots or committed verification artefacts.

---

# Luna completion gate

Before handing back to Sol, all of the following must be true:

- latest-main schema coordination was rechecked;
- fresh real-export aggregate measurement was completed and safely recorded;
- no decision model exposes `owner` as the semantic field;
- armour class comes only from `Equippable`;
- weapon/ghost class is empty in stored model;
- no class parsing from Owner exists;
- no new hard-coded class validation exists;
- no weapon/ghost schema gained `Equippable`;
- snapshot contains both new fields and no old decision/evaluation `owner` key;
- exactly one coordinated snapshot schema bump exists;
- `SESSION_SCHEMA_VERSION`, ruleset, fingerprint inputs and review semantics are unchanged;
- pre-upgrade review manifest rejection is tested/documented;
- persisted veto semantics remain intact;
- Kind and Class are independent in UI;
- location is visible but not the primary class facet;
- old `owner` Notes and new `location` Notes round-trip safely;
- decision semantic parity diff is empty;
- required documentation/worklog is present;
- no private `data/` files are tracked;
- implementation branch is committed and pushed;
- **no PR has been raised**.

Provide Sol with:

- implementation branch name;
- base `main` SHA;
- commit SHA(s);
- files changed/deleted/renamed;
- schema coordination outcome (#105-owned v2 or consumed #101 v2);
- aggregate Equippable measurement result;
- implementation summary;
- tests added/changed;
- exact validation results;
- browser/manual verification results;
- decision-parity diff result;
- known risks/uncertainties;
- any intentional deviation from this plan;
- incidental out-of-scope findings reported separately.

---

# Exact validation commands

Run the focused gate first:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_report_run.py \
  tests/test_review.py \
  tests/test_duplicate_reference.py \
  tests/test_note_history.py \
  tests/test_note_history_roundtrip.py \
  tests/test_dupes.py \
  tests/test_weapons_rules.py \
  tests/test_armor_rules.py \
  tests/test_armor_dupes.py \
  tests/test_armor_close.py \
  tests/test_ghost_rules.py \
  tests/test_cli_report.py \
  tests/test_review_ui_js.py \
  tests/test_server_ui_js.py
```

Regenerate and prove the golden:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
.venv/bin/pytest -q tests/test_report_run.py
```

Run the real-browser acceptance with skipping disabled:

```bash
VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results
```

If the managed Chromium executable is genuinely absent, install the repository-pinned browser before retrying:

```bash
.venv/bin/python -m playwright install chromium
```

Do not mark the browser portion complete on a silent skip. If the execution environment cannot run browsers/sockets, record the exact environmental failure and return that limitation to Sol for independent verification.

Then run the unrestricted repository gate:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git ls-files data/
git status --short
```

`git ls-files data/` must print nothing. `git status --short` should show only the intended committed branch state at final handoff.

Also rerun the `/tmp/issue105-before.json` vs `/tmp/issue105-after.json` semantic parity diff from implementation step 11 and require an empty diff.

---

# Orchestrating Sol high review prompt

Review the completed Luna xhigh implementation for issue **#105** in `tonym999/vault-cleaner`.

Do **not** raise a PR yet.

Read issue #105, this handoff, related #29/#101/#104/#102 state, `AGENTS.md`, and the actual implementation diff from its latest-main base.

## 1. Plan-conformance review

Confirm every in-scope requirement and specifically verify:

1. `Decision`, `ReportDecision`, and `ArmorEvaluation` model `location` and `guardian_class`; no compatibility alias perpetuates semantic `owner`.
2. `rules/armor_dupes.py` was not missed even though the original issue construction-site list omitted it.
3. Armour class comes verbatim only from `Equippable`; weapons/ghosts store empty class; no class is parsed from Owner.
4. No hard-coded class enum has become a parser/schema rejection.
5. Weapon/ghost parser schemas remain class-neutral and unchanged.
6. Existing `ArmorEvaluation.equippable` remains intact unless current-main #101 legitimately changed that contract first.
7. Snapshot decisions/evaluations contain `location` and `guardian_class`, not `owner`.
8. Snapshot schema coordination produced one bump only: v1→v2 if #105 owned it, or reuse of #101's v2 if #101 landed first.
9. `SESSION_SCHEMA_VERSION` is unchanged.
10. `RULESET_VERSION`, `_decision_config()` and fingerprint construction are unchanged; the recorded before/after semantic parity diff is empty.
11. Valid current-schema manifests parse; a pre-upgrade schema-v1 snapshot manifest is rejected; overrides/persisted veto behaviour is unchanged.
12. Browser Kind and Class facets are independent; class-neutral fallback exists only in presentation; Location is retained as a secondary column; no Owner primary filter remains.
13. Class filtering is by `guardian_class`/derived class facet, never current location.
14. CLI/report wording no longer conflates location and Guardian class.
15. Duplicate references say `location` and deliberately do not add class.
16. Existing and pre-upgrade `owner`-labelled generated Notes remain recognisable/replaced; new notes are emitter-round-trip safe.
17. #101 authoritative group projection, #104 tuning UX and #102 dedicated duplicate view were not pulled into scope.
18. Fresh-export measurement used aggregates only and no private vault data is tracked.
19. README/PLAN/WORKLOG are truthful about schema and compatibility.

## 2. Engineering review

Review the actual implementation for:

- correctness and maintainability;
- duplicated class/location derivation;
- hidden rule-semantic changes;
- accidental sort/filter mismatch between displayed class and stored empty class;
- stale-state/local-query regressions in the UI;
- accidental session-protocol changes;
- manifest/version confusion between snapshot schema and session envelope schema;
- Notes-history migration gaps;
- hostile-text/opaque-id regressions;
- unnecessary abstractions added only to mirror stale ticket wording;
- missing regression coverage.

Independently run the important focused tests, browser check where available, full suite, diff/privacy checks, and inspect the regenerated golden rather than trusting Luna's summary.

## Review outcome

If findings exist, return precise findings to Luna on the **same implementation branch**, require regression coverage where appropriate, rerun focused/full validation, and review again.

When the branch is clean, do **not** open a PR. Hand the clean branch to an independent Sol high reviewer using the prompt below.

---

# Independent Sol high review prompt

Perform a fresh independent final review of issue **#105** in `tonym999/vault-cleaner` after the orchestrating Sol has marked the implementation review-clean.

Do **not** assume the plan is correct merely because Luna followed it, and do **not** raise a PR.

Focus especially on the protocol/compatibility boundary:

1. Is splitting volatile DIM `Owner` into `location` plus armour `Equippable`-derived `guardian_class` the sound model everywhere it crosses Python → snapshot → JavaScript?
2. Is the snapshot version change exactly sufficient, with no accidental session-envelope/ruleset/fingerprint version change?
3. Does rejecting old review manifests while preserving persisted vetoes follow from the actual code/tests, not just documentation?
4. Can any browser path still confuse location with class, especially sorting/filter reconciliation after a new envelope?
5. Are empty/unrecognised `Equippable` values honest and non-fatal without silently becoming a recognised class?
6. Did any model rename accidentally alter rule grouping, ranking, safety rails, selected survivor/partner, actions, tags or reason slugs?
7. Can old generated Notes containing `owner` still be recognised and safely replaced by new `location` wording?
8. Are export-derived strings still inert and opaque ids still strings?
9. Did schema coordination with #101 remain one coherent bump rather than create a v2/v3 race?
10. Did the implementation accidentally absorb #101, #104 or #102 work?
11. Do the fake tests and before/after semantic signature genuinely prove the important invariants?
12. Is any real vault data exposed in fixtures, logs or docs?

If any concern remains, return it to the implementation branch for correction and another review cycle. Only after this independent review is clean should the branch be considered ready for a PR.

---

# Reusable Luna xhigh execution prompt

Implement issue **#105** in `tonym999/vault-cleaner` using `handoffs/issue-105-luna-xhigh-implementation-plan.md` as the primary execution contract.

Workflow:

```text
Sol orchestrates → Luna xhigh implements → orchestrating Sol reviews → independent Sol high reviews → PR
```

Rules:

- read issue #105 and related #29/#101/#104/#102 plus `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, current relevant code/tests/docs;
- branch from the **latest `main`**, not from the handoff branch;
- record the base `main` SHA;
- before editing, run the baseline validation, schema-coordination gate, fresh real-export aggregate measurement, and fake decision-semantics capture in the plan;
- treat the current repository as authoritative if it has legitimately moved since planning;
- preserve the ticket-specific algorithmic scope rule and stop/escalation conditions exactly;
- model DIM Owner as `location`, never as class;
- derive armour `guardian_class` only from `Equippable`; weapons/ghosts remain empty/class-neutral;
- do not change rule semantics, `RULESET_VERSION`, fingerprint inputs, server session schema, review persistence/finalisation/lifecycle or parser requirements for weapons/ghosts;
- coordinate with any already-landed #101 snapshot schema work so there is one schema-v2 bump, never an unapproved second bump;
- do not absorb #101, #104 or #102;
- preserve safe text rendering and opaque string ids;
- add/update behavioural tests alongside implementation, including old/new Notes round-trip and manifest compatibility;
- update README/PLAN only where #105 makes current wording stale and add a dated `WORKLOG.md` entry;
- run the exact focused, browser, full, diff, privacy and semantic-parity gates from the plan;
- commit and push the implementation branch;
- **do not open a pull request**.

When complete, return a structured handoff containing:

- implementation branch;
- base `main` SHA;
- commit SHA(s);
- files changed/deleted/renamed;
- schema coordination outcome;
- safe aggregate measurement result;
- implementation summary;
- tests added/changed;
- exact validation results;
- browser/manual verification results;
- before/after semantic parity result;
- unresolved concerns;
- deviations from the plan;
- incidental out-of-scope findings.

If any stop condition is reached, stop expanding scope and return the issue to Sol with the exact reason.

---

# Ticket-specific review decision

**Review path:** `independent`

**Reason:** #105 is bounded and must not alter rules, but it changes the versioned report snapshot contract consumed across Python/JavaScript, intentionally changes compatibility for saved review manifests, and changes generated Note presentation that may exist in live DIM exports. Those are protocol/migration boundaries. The orchestrating Sol should first check strict plan conformance and semantic non-change; an independent Sol high reviewer should then challenge the schema/migration/UI assumptions before a PR is opened.
