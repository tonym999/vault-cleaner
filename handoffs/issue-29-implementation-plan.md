# Ticket

**Repository:** `tonym999/vault-cleaner`
**Issue:** `#29 — Make duplicate survivor references human-readable in notes and reports`
**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → orchestrating Sol reviews → independent Sol high reviews → PR
**Planning base:** `main` at `70746c3000ff1fbf5171a4c205863683af5952c8` (`Fix weapon duplicate identity with measured exact rolls (#100)`)
**Plan branch:** `handoff/issue-29-luna-plan`

## Objective

Replace raw full-instance-id survivor/partner references in duplicate-facing DIM notes and terminal/report presentation with concise, human-readable references that help the user identify the relevant copy in DIM, while retaining full candidate and reference instance IDs in the existing machine-readable report model.

The finished change must cover weapon exact dupes, armour exact dupes, armour-dominated advice, and armour-similar advice consistently. It must explain why the existing selector chose the survivor/partner without changing that selector, preserve the existing searchable `#vc-junk:` / `#vc-review:` reason slugs and stacked-note behaviour, keep dry-run/write behaviour unchanged, and make no changes to duplicate identity, ranking, safety rails, tags, decisions, pass ordering, review verdict semantics, persistence, or server lifecycle.

The implementation is the presentation foundation for M9. `PLAN.md` must record M9's presentation-only boundary and delivery order:

```text
#29 shared survivor/partner presentation and audit model
    ↓
#101 authoritative armour exact-duplicate group report projection
    ↓
#102 Armor duplicates browser view
```

## Why this ticket is ready

- Issue #31, the prerequisite weapon exact-roll correctness work, is complete and merged to `main` through PR #100.
- The current weapon duplicate resolver now has a measured exact-roll fingerprint and deterministic exact-group survivor ranking, so #29 can describe a chosen exact duplicate without reopening identity design.
- Armour exact duplicate and close-duplicate selectors are already established and covered by focused tests.
- `Decision.kept_id` and `ReportDecision.kept_id` already retain the full survivor/partner instance id; `ReportDecision.id` retains the full candidate id. The machine-readable report therefore already has the audit identities required by #29.
- #101 explicitly depends on #29, and #102 depends on #101. Neither downstream ticket should be pulled forward into this implementation.
- Issue #29 currently has no comments. Its timeline cross-references #31 and #34 and records the new M9 dependency on #101.

---

# Review model

## Independent review path

```text
Sol orchestrator
    ↓
Luna xhigh implementation
    ↓
Same/orchestrating Sol plan-conformance + engineering review
    ↓
Independent Sol high final review
    ↓
PR
```

Although #29 is intentionally presentation-only, use **independent review**.

Reason: this ticket changes safety-relevant text that the user will rely on before manually dismantling items, changes the duplicate-facing report payload's note values across several rule passes, and introduces additional untrusted DIM-export text into durable Notes/terminal presentation. A mistaken reference could point the user at the wrong survivor even if the underlying junk decision is technically unchanged. The current review stack also treats the Python-to-review presentation contract as important, and #101 — the immediate consumer of this foundation — is independently reviewed for the same safety-relevant report-contract reason.

The first Sol review should verify strict conformance to this presentation-only plan. The independent Sol high reviewer should then challenge whether the displayed reference and winner explanation are actually derived from the same authoritative selector and whether hostile export text can corrupt the `#vc-` reason contract.

---

# Authoritative context

Before changing code, Luna must read the latest versions of:

- `AGENTS.md`
- `PLAN.md`
- issue #29 and its timeline/dependency relationships
- issue #31 and the merged #31 implementation on current `main`
- issue #101 and issue #102
- issue #34 only to understand the adjacent weapon-value work that is explicitly not part of #29
- recent #31 entries in `WORKLOG.md`
- `src/vault_cleaner/rules/dupes.py`
- `src/vault_cleaner/rules/weapons.py`
- `src/vault_cleaner/rules/armor_dupes.py`
- `src/vault_cleaner/rules/armor_close.py`
- `src/vault_cleaner/rules/rails.py`
- `src/vault_cleaner/pipeline.py`
- `src/vault_cleaner/report.py`
- `src/vault_cleaner/report_run.py`
- `src/vault_cleaner/cli.py`
- the focused duplicate/report tests listed later in this plan

Treat the following as authoritative and do not redesign them:

1. **Weapon exact-roll identity** — `(Hash, exact_roll_fingerprint)` using the measured contiguous named `Perks 0..N` pre-tracker prefix from #31. Unknown/incomplete identity remains ungroupable.
2. **Weapon exact-dupe survivor ranking** — `Tier > Masterwork Tier > Crafted Level > stat total > deterministic opaque Id` within one proven exact-roll group. Wishlist score is no longer part of this ranking.
3. **Armour exact-dupe identity** — the existing `armor_dupes.fingerprint()` contract, including tuning and exotic-class-item Spirit identity.
4. **Armour exact-dupe survivor ranking** — hard-protected > loadout-referenced > locked > Masterwork Tier > Power > lowest instance id.
5. **Armour close-dupe matching/partner selection** — current Hash/Tier/Spirit compatibility, dominated/similar rules, and deterministic partner ordering.
6. **Safety rails** — current hard/soft behaviour in `rules/rails.py`.
7. **Pass ordering / earlier-pass-wins behaviour** — the current `pipeline.py` flow.
8. **Machine audit identity** — full opaque string `ReportDecision.id` and `ReportDecision.kept_id` in `report_run.py`.
9. **Reason parsing** — `report.reason_slug()` parses the **last** generated `#vc-...` match so stacked historical Notes continue to work.
10. **Versioning** — `SNAPSHOT_SCHEMA_VERSION == 1` and `RULESET_VERSION == 3` on the planning base. Presentation-only text changes do not justify a ruleset bump; no snapshot-schema bump is expected because the existing fields are sufficient.
11. **Review/server lifecycle and persisted veto semantics** — unchanged by this ticket.

---

# Current repository state and stale-ticket corrections

Issue #29 predates several important changes now on `main`; implement against the repository, not the older implications of the issue examples.

## 1. #31 has replaced the old same-Hash weapon behaviour

Current `rules/dupes.py` groups only proven exact rolls and selects the best exact copy using Tier, Masterwork Tier, Crafted Level, stat total, then opaque Id. It no longer ranks exact dupes by wishlist match count.

Therefore the issue's broad list of possible "winning reasons" is **not** a licence to report wishlist or hard protection as the reason a weapon survivor won. For weapon exact dupes, the displayed winner reason must describe the selector that actually ran:

```text
Tier
→ Masterwork Tier
→ Crafted Level
→ stat total
→ deterministic Id tie-break
```

Safety rails still determine whether a losing copy can be emitted as junk/review, but they do not select the weapon `best` row. Wishlist-trash remains an earlier separate pass. Do not reintroduce either into exact-dupe ranking merely to make the display match old issue wording.

## 2. The machine-readable full-ID audit model already exists

`Decision` carries `id` and `kept_id`. `ReportDecision` serialises both as full strings into the existing report snapshot. The implementation should **prove and preserve** this rather than creating another audit file, CLI protocol, or schema field.

A focused regression must use fake 19/20-digit IDs and show all of the following at once:

- candidate `ReportDecision.id` remains the complete opaque string;
- `ReportDecision.kept_id` remains the complete opaque string;
- the human-facing note uses only the documented short suffix for the reference;
- the human-facing note does not contain the full reference instance id.

## 3. The report snapshot is now shared infrastructure

The browser/review server consumes the structured report model that was added after #29 was first opened. #29 may change existing Notes/presentation values, but it must not invent the complete armour-group projection owned by #101 or change the browser protocol owned by later M9 work.

## 4. `PLAN.md` does not yet record M9

The current plan ends at M8. #29 now explicitly owns adding M9's boundary/order to `PLAN.md`.

---

# Dependencies and assumptions

- **Completed prerequisite:** #31 / PR #100.
- **Blocked downstream:** #101, then #102.
- **Adjacent but not a dependency:** #34 weapon useful-combination coverage. Do not implement its scoring, wishlist-provenance, recommendation deduplication, or coverage model here.
- No new runtime dependency is needed or allowed for the planned presentation work.
- Fake fixtures and existing synthetic test data are sufficient; no real vault row, path, item id, perk set, or private export may be committed.
- Existing `Owner`, armour state fields, weapon state fields, exact-roll prefix, and Spirit signature are the only allowed source material for display details.
- Missing optional display fields must degrade to a shorter reference, not cause the duplicate decision to disappear and not cause the implementation to invent data.
- Full IDs stay opaque strings. Shortening is string slicing for display only; never parse a DIM instance id as a numeric value merely to render it.

---

# Ticket-specific algorithmic scope rule

For **every proposed code change**, Luna must apply this mechanical test before making it:

> Hold the ordered set of decisions fixed, and for every decision hold `(id, action, tag, reason_slug, kept_id)` fixed. A change belongs to #29 only if it exclusively:
>
> 1. derives or sanitises a human-facing survivor/partner label from fields already present on the candidate/reference rows;
> 2. derives a textual winner/partner-selection explanation from comparison data that the existing authoritative selector already used;
> 3. replaces a raw full-id reference in duplicate-facing Notes/terminal/report presentation with that label while preserving the existing parsed reason slug;
> 4. preserves/proves the existing full `id` + `kept_id` audit values in `ReportDecision`/snapshot output; or
> 5. adds tests/documentation directly proving 1–4 and M9's presentation-only boundary.

A change **fails the #29 scope test** if it can change any of the following:

- weapon or armour fingerprint/group membership;
- the chosen survivor or close-dupe partner;
- rank keys, rank precedence, comparison thresholds, or tie-break ordering;
- hard/soft rail classification or precedence;
- wishlist keep/trash matching or wishlist influence on decisions;
- the number/order of emitted decisions;
- any decision's `id`, `action`, `tag`, parsed `reason_slug`, or full `kept_id`;
- earlier-pass-wins behaviour or pipeline ordering;
- armour score behaviour or cited-partner shielding semantics;
- report fingerprint inputs, `RULESET_VERSION`, review-manifest identity, veto/stale classification, or finalisation semantics;
- persistence, concurrency, authentication, stale-state handling, server lifecycle, browser protocol, or browser UI;
- dependency sets or filesystem/network permissions.

## Mandatory stop/escalation conditions

Luna must stop implementation and return the issue to Sol for replanning if any of these occurs:

1. Human-readable weapon perk detail cannot be produced without changing `exact_roll_fingerprint()`, tracker-boundary logic, or the measured weapon identity contract.
2. Full candidate/reference auditability cannot be met with the existing `ReportDecision.id` / `ReportDecision.kept_id` model and would require a new report/schema/API field or a new machine-readable file format.
3. Preserving `reason_slug()` and stacked Notes appears to require changing the parser contract rather than safely formatting/sanitising new display fragments.
4. A new `SNAPSHOT_SCHEMA_VERSION` or `RULESET_VERSION` seems necessary.
5. Any implementation change is needed in `src/vault_cleaner/server/**`, `src/vault_cleaner/ui/**`, `review.py`, `review_session.py`, or finalisation/persistence code.
6. A test reveals that the current duplicate selector itself chooses a wrong survivor/partner. Record the defect separately and return to Sol; do not fix the selector in #29.
7. #101's complete armour-group projection or #102's browser view becomes necessary to make #29 pass.
8. A new runtime dependency appears useful or necessary.

Do not "solve" a stop condition by quietly broadening this ticket.

---

# Scope

## In scope

- A shared, deterministic human-readable reference format for:
  - weapon exact-dupe survivor references;
  - armour exact-dupe survivor references;
  - armour-dominated partner references;
  - armour-similar partner references.
- A consistent short instance-id suffix, using string operations only.
- Reference details drawn from already-loaded export fields:
  - owner/location (`Owner`) where present;
  - armour Masterwork Tier, Power, Tuning Stat, and exotic-class-item Spirit combination where useful;
  - weapon Tier/Masterwork/Crafted Level and a concise deterministic excerpt of the already-authoritative pre-tracker exact-roll prefix where useful.
- A human-readable reason explaining the **existing** selector/partner choice.
- Safe normalisation of untrusted display text so inserting Owner/perk/tuning/Spirit text cannot forge a later `#vc-junk:`/`#vc-review:` marker or break a single-line DIM note.
- Updating duplicate-facing terminal/report summary output so candidate and survivor/partner are visible together with the existing selection reason.
- Preserving full candidate/reference ids in the existing machine report/snapshot.
- Regenerating the fake report snapshot if the expected note payload changes.
- `PLAN.md`, `README.md` where needed for user-visible note/report behaviour, and `WORKLOG.md`.

## Out of scope

- Changing weapon or armour duplicate identity.
- Changing any survivor/partner ranking or tie-break.
- Changing safety rails or tag preservation.
- Changing wishlist matching/scoring; #34 remains separate.
- Adding semantic weapon roles such as DPS/movement/utility.
- Tagging a survivor `keep` or emitting an extra row for the survivor.
- Emitting a complete armour exact-duplicate group model; #101 owns that.
- Browser duplicate-group rendering; #102 owns that.
- Browser/server/review protocol changes.
- New persisted audit files, database/state, or new CLI persistence surfaces when existing `ReportDecision` audit fields suffice.
- New dependencies.
- Refactoring unrelated report/rule architecture.
- Changing unrelated non-duplicate note wording.

---

# Presentation contract to implement

Use one shared presentation seam rather than four independently formatted strings. A small focused module such as `src/vault_cleaner/duplicate_reference.py` is preferred if it keeps rule modules simple; an equivalently narrow existing presentation module is acceptable if current code provides a better home.

The exact punctuation may be refined against fake dry-run output, but the following invariants are mandatory.

## Short id

For a long instance id, show a bounded suffix, e.g.:

```text
[id …0059]
```

Use the final four characters by default. If a synthetic id is four characters or shorter, show it without pretending characters were omitted. The complete id must remain in `kept_id`; this shortening is display-only.

## Untrusted display text

Owner, perk names, tuning values, Spirit names, and other CSV-derived display fragments are untrusted text.

The shared presenter must:

- collapse line breaks/control whitespace to safe single-line spacing;
- prevent a case-insensitive literal `#vc-` sequence from becoming a second parseable tool hashtag in a generated reference;
- keep output bounded/concise so one hostile or pathological field cannot create an enormous DIM note;
- never modify the original row/report values used for audit or rule logic.

The currently generated tool hashtag must remain the last parseable `#vc-` hashtag in the resulting Notes value. Existing historical `#vc-` hashtags earlier in `Notes` remain untouched so stacked-note behaviour continues to work.

Do **not** redesign `reason_slug()` unless implementation proves the formatting-only approach cannot satisfy the contract; that is a stop/escalation condition.

## Reason-slug prefixes

Preserve the current parser-visible prefixes exactly. In particular, tests must first capture the current `reason_slug()` result for each note family and prove it is unchanged after the presentation rewrite.

Recommended grammar:

```text
#vc-junk: dupe-lower; keep <weapon-reference>; winner <reason>
#vc-junk: dupe-tie; keep <weapon-reference>; winner deterministic id tie-break
#vc-review: dupe-lower (<soft-rail>); keep <weapon-reference>; winner <reason>

#vc-junk: armor-exact-dupe; keep <armor-reference>; winner <reason>
#vc-junk: armor-exact-dupe-tie; keep <armor-reference>; winner deterministic id tie-break
#vc-review: armor-exact-dupe (<soft-rail>); keep <armor-reference>; winner <reason>

#vc-review: armor-dominated by; compare <armor-reference>; <existing surplus detail>
#vc-review: armor-similar to; compare <armor-reference>; <existing similarity detail>
```

The `by` / `to` tokens are deliberately retained before a delimiter because the current permissive `reason_slug()` regex includes those lowercase words in the parsed close-dupe slug before it reaches the numeric partner id. Verify this behaviour in tests rather than assuming a simplified slug.

## Weapon reference details

For an exact-dupe survivor, build details from the existing selected `best` row only. Prefer:

- `Owner` when present;
- `Tier` when useful;
- `MW<n>` when present;
- `crafted lv<n>` only when the existing parser says the row is crafted and level is known;
- a concise deterministic perk excerpt from the **same already-proven pre-tracker exact-roll prefix**.

For the perk excerpt, do not create a second roll parser or infer selectable combinations. Reuse the current exact-roll boundary/result. A suitable bounded presentation is the final two non-empty display names from the authoritative pre-tracker prefix, preserving measured order and source-facing casing while removing only DIM's trailing selected `*` marker. This is a label, not identity and not #34's combination model.

If producing this excerpt requires new identity assumptions, omit the perk excerpt and use the remaining safe state fields; if the ticket cannot then meet acceptance, escalate to Sol rather than changing #31's algorithm.

### Weapon winner explanation

Derive the explanation at the existing comparison point; do not rerank a copy in a separate presentation layer.

For each losing exact copy, identify the first current ranking dimension on which the selected `best` row beats that loser:

1. Tier;
2. Masterwork Tier;
3. Crafted Level;
4. stat total;
5. otherwise deterministic opaque-id tie-break.

Do not report wishlist or hard protection as the weapon selection reason unless the authoritative selector is separately changed by another approved ticket. #29 must not make such a change.

## Armour exact reference details

Build from the existing selected `best` row. Prefer:

- `Owner`;
- `MW<n>`;
- `power <n>`;
- `tuning <value>` when present;
- for exotic class items, the existing complete `spirit_signature()` rendered compactly, e.g. `Contact + Scars` rather than repeating `Spirit of` for every entry;
- short id suffix.

Do not change the fingerprint or Spirit completeness rules.

### Armour exact winner explanation

Use the existing `_survivor_rank` comparison, in its current order:

1. hard protection (when selected row is hard and loser is not; the existing trusted rail reason may be displayed);
2. loadout membership;
3. lock;
4. Masterwork Tier;
5. Power;
6. deterministic lowest-id tie-break.

The explanation is descriptive only. It must not feed back into `_survivor_rank`.

## Armour dominated/similar partner details

Use the already selected `other`/partner row and existing comparison metrics.

- Dominated: retain the current `+N total` information and describe the selected partner as the best existing dominator under the current surplus/id key.
- Similar: retain `_similar_detail()`'s current distance/tuning explanation and show the selected closest partner.
- If selection among otherwise equal partner metrics falls to the current id tie-break, the text may say `deterministic id tie-break`; do not alter the key.
- Continue to set `Decision.kept_id` to the complete selected partner id because `pipeline.py` uses it to shield cited partners from the later score pass.

---

# Expected change footprint

## Likely files

```text
src/vault_cleaner/duplicate_reference.py        # preferred new shared presentation helper
src/vault_cleaner/rules/dupes.py
src/vault_cleaner/rules/armor_dupes.py
src/vault_cleaner/rules/armor_close.py
src/vault_cleaner/report.py
src/vault_cleaner/cli.py                        # only if explicit side-by-side output needs adapter work

tests/test_duplicate_reference.py               # if a new shared helper is introduced
tests/test_dupes.py
tests/test_armor_dupes.py
tests/test_armor_close.py
tests/test_report.py
tests/test_report_run.py
tests/test_cli_report.py                         # and existing focused CLI tests if current layout suggests them
tests/fixtures/report_snapshot_v1.json           # regenerate from fake fixtures if Notes change

PLAN.md
README.md                                        # concise user-facing format/status update where useful
WORKLOG.md
```

It is acceptable for Luna to discover that `cli.py` needs no substantive change because the current commands already print the enhanced note fragment, provided automated/manual tests prove the required candidate/reference side-by-side output. Do not change a file merely because it is listed here.

## Files/components that should normally remain unchanged

```text
src/vault_cleaner/pipeline.py
src/vault_cleaner/report_run.py                  # shape/version should remain unchanged
src/vault_cleaner/rules/rails.py
src/vault_cleaner/rules/weapons.py
src/vault_cleaner/rules/armor.py
src/vault_cleaner/parse.py
src/vault_cleaner/config.py
src/vault_cleaner/wishlist.py
src/vault_cleaner/manifest.py
src/vault_cleaner/review.py
src/vault_cleaner/review_session.py
src/vault_cleaner/server/
src/vault_cleaner/ui/
.github/workflows/
pyproject.toml
config.toml
data/
```

A tiny import/type-only change to `pipeline.py` or `report_run.py` may be acceptable only if mechanically necessary and provably schema/behaviour neutral. Any substantive change to these components — especially report schema/versioning, cited-partner shielding, review/server code, or lifecycle — crosses the escalation boundary.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline from latest `main`

Do not implement on the handoff branch. Create a fresh implementation branch from the latest `origin/main`, for example:

```text
issue-29-human-readable-duplicate-refs
```

Record the base SHA in the Luna → Sol handoff.

Run:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --short

python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git ls-files data/
```

If `.venv` already exists and is current, reuse it rather than recreating it.

Baseline requirements:

- Ruff clean.
- Full pytest clean or any environment-only limitation explicitly identified before implementation.
- `git diff --check` clean.
- `git ls-files data/` empty.
- working tree clean.

If the latest `main` has materially moved from planning base `70746c3000ff1fbf5171a4c205863683af5952c8`, compare the moved code to this plan. Adapt only presentation details that remain inside the algorithmic scope rule; otherwise return to Sol.

## 2. Lock in pre-change behavioural invariants with focused tests

Before rewriting strings, make tests state what may **not** change.

Capture representative decision tuples for all four presentation families:

```text
(id, action, tag, reason_slug(note), kept_id)
```

Cover at least:

- weapon lower exact dupe;
- weapon exact tie;
- armour exact lower dupe;
- armour exact tie;
- armour dominated;
- armour similar.

Where existing tests already prove survivor ids and reverse-order determinism, extend rather than duplicate them.

Add/adjust a `reason_slug` regression that records the current parsed values for close-dupe prefixes before changing note grammar. Preserve those exact outputs after implementation.

This gives Sol a direct proof that #29 did not alter decisions while changing display text.

## 3. Introduce one shared duplicate-reference presentation seam

Create a narrow shared helper (preferred location `src/vault_cleaner/duplicate_reference.py`) containing presentation-only utilities. Keep it independent of report/server state.

The helper should own, as appropriate:

- short opaque-id suffix rendering;
- safe single-line untrusted-text normalisation;
- reserved `#vc-` neutralisation for display fragments;
- bounded joining/truncation of human-readable details;
- common reference punctuation/shape;
- small item-family-specific label builders if keeping those builders here avoids duplicating format rules in rule modules.

Do **not** put duplicate identity, rank comparison, rule selection, or report schema logic into this helper.

Prefer explicit small functions and immutable strings over a new class hierarchy. No new dependency.

## 4. Add weapon exact-dupe presentation without touching identity/ranking

In `rules/dupes.py`:

1. Leave `exact_roll_fingerprint()` behaviour unchanged.
2. Leave `rank_key()` behaviour and `RANK_COLUMNS` ordering unchanged.
3. Leave `(Hash, fingerprint)` grouping unchanged.
4. Leave the existing stable sorting/tie-break unchanged.
5. Once `best` has already been selected, derive a presentation-only winner reason by comparing the already-computed `best_key` with the current losing `key` in the established rank order.
6. Build the human reference from `best` using the shared helper and existing exact-roll prefix.
7. Replace `kept <full id>` in the newly appended tool note with the human reference + winner explanation.
8. Continue setting `Decision.kept_id=best["Id"]` with the complete id.
9. Preserve the same `dupe-lower` / `dupe-tie` action/reason semantics and soft-rail qualifier.

Important #31 guard: no wishlist input may enter this winner explanation. Do not add wishlist score back to `rank_key` or use `keep_match_count` to choose/present a weapon winner.

## 5. Add armour exact-dupe presentation without touching fingerprint/ranking

In `rules/armor_dupes.py`:

1. Leave `fingerprint()`, `unknown_spirit_roll()`, `spirit_signature()`, and grouping unchanged.
2. Leave `_survivor_rank()` tuple and `max(..., -int(Id))` survivor selection unchanged.
3. Once `best` is selected, derive the winner explanation from the first dimension of the existing rank tuple on which it beats the current loser; use current rail output only to name a hard-protection reason when hard protection really is the decisive dimension.
4. Build the human reference from `best` using Owner/state/Tuning/Spirit details already present.
5. Replace only the raw full-id portion of the appended note.
6. Keep `Decision.kept_id` full and unchanged.
7. Keep hard losers omitted, loadout loser review behaviour, soft-review behaviour, tag preservation, and action selection unchanged.

## 6. Add armour close-dupe partner presentation without touching partner selection

In `rules/armor_close.py`:

1. Preserve compatibility grouping and known-Spirit filtering.
2. Preserve the dominated `key = (sum(delta), -int(oid))` selection.
3. Preserve the similar `key = (mx, sm, int(oid))` selection.
4. Preserve hard-protected candidate handling and all pairwise/non-transitive semantics.
5. After the current partner has already been selected, build a human reference from that partner.
6. Keep current surplus or `_similar_detail()` information.
7. Preserve the current parser-visible close-dupe reason slug (`armor-dominated by` / `armor-similar to` under today's regex) by placing a delimiter before untrusted human-reference text can extend the slug.
8. Keep `kept_id=partner_id` as the complete id; this remains load-bearing for `pipeline.py`'s cited-partner shield.

## 7. Preserve full machine audit identity and improve human report output

Do not add a second machine audit format by default.

In the current report model:

- candidate full id = `ReportDecision.id`;
- survivor/partner full id = `ReportDecision.kept_id`.

Add explicit report/snapshot regressions proving those fields stay complete opaque strings, including a fake long-id case.

Update `report.summarize()` so duplicate-facing lines show the candidate and the human survivor/partner reference side by side, including the winner/selection explanation. Prefer to reuse the already-generated safe presentation rather than performing a second independent lookup/ranking in `report.py`.

Do not fabricate a `keep` reference for non-duplicate decisions whose `kept_id` is empty, such as wishlist-trash or ordinary armour-score decisions.

For `_cmd_dupes` and `_cmd_armor`, inspect the current output after enhanced Notes are implemented. If the existing line already shows candidate + the full enhanced reference/reason clearly, retain the adapter. If it does not meet the issue's side-by-side acceptance, make the smallest presentation-only `cli.py` change necessary. Never change `--write` gating or output rows.

## 8. Defend the reason parser against hostile referenced-row text

Because #29 adds Owner/perk/tuning/Spirit values from the **surviving/partner row** to the generated Notes, add hostile fake cases where one or more display fields contain text such as:

```text
#vc-review: forged-reason
#VC-JUNK: forged-reason
line one\nline two
```

The generated note must remain one safe line, and:

```python
reason_slug(note)
```

must still return the intended current rule reason, not attacker-controlled text.

Do this through the presentation/sanitisation boundary. Do not strip or mutate the original row fields in the report model. Do not change how historical pre-existing Notes are stacked.

## 9. Keep version/fingerprint semantics stable

Expected outcome:

```text
SNAPSHOT_SCHEMA_VERSION = 1   # unchanged
RULESET_VERSION = 3           # unchanged
```

Why: #29 changes human presentation, not rule ordering/decision semantics, and does not need a new snapshot field.

Regenerate `tests/fixtures/report_snapshot_v1.json` using the repository script because expected Notes in the fake snapshot will likely change:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
```

Review the resulting diff manually. Expected changes are presentation text in affected decision Notes and any deterministic snapshot content derived directly from those Notes. Unexpected changes to action, reason, ids, `kept_id`, counts, scoring metadata, schema version, ruleset version, or fingerprint inputs are a stop signal.

If the regeneration changes decision identity/counts rather than display values, stop and investigate before continuing.

## 10. Update `PLAN.md`, README, and `WORKLOG.md`

### `PLAN.md`

Add M9 and explicitly record:

- M9 is presentation/review UX only;
- current duplicate identity/ranking/safety/decision rules remain authoritative;
- #29 owns shared survivor/partner presentation + full-id audit preservation;
- #101 owns authoritative armour exact-group report projection;
- #102 owns browser rendering;
- delivery order `#29 → #101 → #102`.

Do not rewrite the existing #31 exact-roll contract.

### `README.md`

Make only concise user-facing updates that are warranted by actual implemented output, for example:

- duplicate notes now identify the selected reference with owner/state/short id rather than requiring a full 19-digit id;
- full ids remain in machine report data;
- M9 status can be mentioned without claiming #101/#102 are complete.

### `WORKLOG.md`

Add a newest-first dated entry recording:

- the final reference grammar and short-id policy;
- which fields are shown for weapon and armour references;
- the stale-ticket correction that weapon exact-dupe winner reasons follow current #31 ranking and do **not** use wishlist/hard protection as selector reasons;
- how hostile `#vc-` text from referenced rows is neutralised while original audit values remain intact;
- that full `id`/`kept_id` stay in the existing report snapshot;
- snapshot/ruleset version decision;
- snapshot regeneration result;
- focused/full validation results;
- any surprising DIM formatting constraint.

Record no real vault rows, ids, hashes, or paths.

## 11. Keep failure behaviour presentation-only and fail safe

Presentation helpers must not cause an otherwise valid duplicate decision to vanish merely because an optional display field is blank.

Use graceful omission:

- no Owner → omit owner rather than guessing;
- no tuning → omit tuning;
- non-exotic/no Spirit signature → omit Spirits;
- non-crafted weapon → omit crafted-level label;
- missing optional weapon display detail → fall back to other safe fields + short id.

The full `kept_id` remains available even if all descriptive fields are absent.

Do not catch/convert errors that currently indicate malformed safety/identity data. #29 does not weaken parser/schema failures or rule safety.

## 12. Check deterministic behaviour explicitly

For passes that already promise row-order independence, reverse the relevant fake DataFrame/fixture and compare at least:

```text
id
kept_id
action
tag
reason_slug(note)
full generated note/reference text
```

The human reference must be deterministic as well as the chosen reference.

---

# Required automated tests

At minimum, add/update focused behavioural tests proving all of the following.

1. **Shared short-id format** — long id becomes the documented suffix, full id never leaks into the human reference, short synthetic ids remain intelligible.
2. **Weapon lower dupe** — same survivor as baseline; note uses human survivor reference; winner explanation identifies the actual first differing current rank dimension.
3. **Weapon tie** — same deterministic survivor; winner explanation says deterministic id tie-break.
4. **Weapon #31 safety** — distinct same-Hash roll fingerprints still do not compete; presentation work cannot create a dupe decision.
5. **Weapon wishlist separation** — existing wishlist keep/trash regressions remain green; no winner text claims wishlist selected an exact-dupe survivor.
6. **Weapon rails** — crafted/equipped/tagged/locked/exotic behaviours remain as currently defined.
7. **Armour exact lower** — same survivor and action; human reference includes appropriate state fields.
8. **Armour loadout/hard/lock/MW/power cases** — same survivors; displayed winner reason matches the existing decisive rank dimension.
9. **Armour exact tie** — same lowest-id deterministic survivor and tie-break explanation.
10. **Exotic class item** — human reference renders the existing Spirit combination without changing Spirit fingerprint semantics.
11. **Armour dominated** — same partner id, same `+N total` meaning, human partner reference, unchanged parsed reason slug.
12. **Armour similar** — same closest partner id, same similarity detail, human partner reference, unchanged parsed reason slug.
13. **Cited-partner shield regression** — close-dupe partner remains protected from later score junking exactly as before.
14. **Machine audit long IDs** — snapshot/report retains complete candidate `id` and complete `kept_id` strings while Notes show only short reference id.
15. **No survivor mutation** — no extra Decision/import row is emitted for a chosen survivor merely to make it discoverable.
16. **Reason-slug stability** — all existing reason families used by #29 parse to exactly the same slug as pre-change.
17. **Stacked Notes** — an old `#vc-` hashtag before the new current hashtag still results in the current last reason winning.
18. **Hostile survivor text** — Owner/perk/tuning/Spirit containing `#vc-`, mixed-case variants, line separators or control whitespace cannot forge a new parsed reason or create unsafe multiline output.
19. **Non-duplicate summaries** — wishlist-trash/armour-score/ghost decisions do not get a fake survivor reference.
20. **Dry-run/write contract** — dry-run remains default; `--write` still controls CSV creation; enhanced Notes are the only relevant CSV-content change.
21. **Reverse-row determinism** — generated reference text and decision fields are identical when the source ordering is reversed where current passes guarantee it.
22. **Golden snapshot** — regenerated fake snapshot matches committed fixture with schema 1 / ruleset 3 and expected presentation-only differences.

Prefer behavioural assertions over source-string inspection.

---

# Focused validation commands

Run after implementation and again after any review fixes:

```bash
.venv/bin/ruff check src tests scripts

.venv/bin/pytest -q \
  tests/test_dupes.py \
  tests/test_armor_dupes.py \
  tests/test_armor_close.py \
  tests/test_report.py \
  tests/test_report_run.py \
  tests/test_cli_report.py
```

If `tests/test_duplicate_reference.py` or another dedicated focused file is added, include it explicitly:

```bash
.venv/bin/pytest -q tests/test_duplicate_reference.py
```

Regenerate and verify the fake snapshot:

```bash
.venv/bin/python scripts/regenerate_report_snapshot.py
.venv/bin/pytest -q tests/test_report_run.py
git diff -- tests/fixtures/report_snapshot_v1.json
```

The snapshot diff must be reviewed, not merely regenerated and accepted.

---

# Manual verification

Use **fake repository fixtures only**.

## Weapon duplicate dry run

```bash
.venv/bin/vault-cleaner dupes \
  --input tests/fixtures/weapons_slammer_like.csv \
  --no-wishlists \
  --config nonexistent.toml
```

Confirm visually:

- candidate line identifies candidate id/name;
- exact survivor is human-readable;
- only short survivor-id suffix appears in the human note;
- winner reason matches current ranking;
- distinct Slammer-like rolls remain untouched;
- command stays dry-run unless `--write` is passed.

## Armour dry run

```bash
.venv/bin/vault-cleaner armor \
  --input tests/fixtures/armor_dupes.csv \
  --config nonexistent.toml
```

If this fixture does not exercise close-dupe presentation through the CLI, use the existing armour-close fake fixture through the narrowest current test/helper path rather than creating a new user workflow solely for manual inspection.

Confirm human references are concise and consistent for exact and relevant close-dupe advice.

## Combined report dry run

```bash
.venv/bin/vault-cleaner report \
  --weapons tests/fixtures/weapons_dupes.csv \
  --armor tests/fixtures/armor.csv \
  --ghosts tests/fixtures/ghosts_cleanup.csv \
  --no-wishlists \
  --config nonexistent.toml
```

Confirm:

- duplicate candidate/reference are understandable side by side;
- selection reason is visible;
- ordinary non-duplicate rows still render normally;
- output remains a dry run.

Optional explicit-write smoke to a temporary location is acceptable, but never write into or commit `data/` for validation. If performed, confirm the CSV still contains exactly `Id,Hash,Tag,Notes` and no survivor-only row has appeared.

No browser, wheel-install, Playwright, or server lifecycle manual check is required for #29 unless Luna unexpectedly touches those components — which should trigger escalation first.

---

# Luna completion gate

Before handing back to Sol, Luna must run the complete repository gate:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git ls-files data/
git status --short
```

Expected:

- Ruff passes.
- Full pytest suite passes.
- `git diff --check` produces no output.
- `git ls-files data/` produces no output.
- `SNAPSHOT_SCHEMA_VERSION` remains 1.
- `RULESET_VERSION` remains 3.
- no runtime dependency added.
- no server/UI/review lifecycle change.
- `PLAN.md` contains M9 boundary/order.
- `WORKLOG.md` has the #29 entry.
- fake snapshot was regenerated and reviewed if affected.
- all four duplicate presentation families are covered.
- full candidate/reference IDs remain in the report model.
- no full long survivor id is required in the human-facing generated duplicate note.
- branch is committed and pushed.
- **no pull request has been opened**.

Suggested implementation branch:

```text
issue-29-human-readable-duplicate-refs
```

Suggested implementation commit message:

```text
Make duplicate survivor references human-readable
```

Multiple focused commits are acceptable if they aid review; do not create cosmetic churn.

## Luna → Sol handoff contents

Provide:

- implementation branch;
- base `main` SHA;
- commit SHA(s);
- files changed/deleted;
- exact final note/reference grammar;
- implementation summary;
- explicit statement that decision/grouping/ranking semantics were unchanged;
- tests added/changed;
- focused validation results;
- full-suite result;
- snapshot regeneration/diff summary;
- manual fake-fixture output checks;
- confirmation that schema/ruleset versions are unchanged;
- confirmation that no `data/` file is tracked;
- unresolved concerns;
- any deviation from this plan and why.

---

# Orchestrating Sol review prompt

Review the completed Luna xhigh implementation for issue `#29` in `tonym999/vault-cleaner`.

Do **not** raise a PR yet.

The ticket is presentation-only and is the foundation for M9. Review the actual diff and rerun important validation; do not accept Luna's summary on trust.

## 1. Plan-conformance review

Check every in-scope requirement and explicitly confirm:

1. weapon exact duplicate identity remains `(Hash, exact_roll_fingerprint)` with #31 semantics unchanged;
2. weapon winner ranking remains Tier > Masterwork Tier > Crafted Level > stat total > opaque Id;
3. no wishlist score/hard rail was reintroduced as a weapon winner selector;
4. armour exact fingerprint and survivor ranking are unchanged;
5. armour close compatibility, dominated/similar comparison, and partner keys are unchanged;
6. safety rails/tags/actions/pass order are unchanged;
7. `Decision.kept_id` remains the full reference id;
8. `ReportDecision.id` and `.kept_id` remain complete opaque strings;
9. no extra survivor Decision/import row is emitted;
10. all four presentation families use one consistent reference contract;
11. the human note uses a short id suffix and actionable fields;
12. displayed winner/partner reason is derived from the selector that already ran, not recomputed by a competing ranking path;
13. `reason_slug()` outputs are stable, including current close-dupe `by`/`to` behaviour;
14. stacked historical Notes still use the last current tool hashtag;
15. hostile referenced-row text cannot inject a parseable later `#vc-` hashtag or unsafe line breaks;
16. dry-run/`--write` behaviour is unchanged;
17. snapshot schema remains 1 and ruleset remains 3;
18. fake snapshot changes are presentation-only and were produced by the regeneration script;
19. `PLAN.md` records M9 `#29 → #101 → #102` and its presentation boundary;
20. `WORKLOG.md` accurately records decisions/validation without private data;
21. #101/#102/#34 work has not leaked into this ticket.

A useful mechanical diff check is to compare representative baseline and final decision tuples:

```text
(id, action, tag, reason_slug(note), kept_id)
```

They must remain equal; only human presentation surrounding the stable reason is allowed to differ.

## 2. Engineering review

Review for:

- duplicated formatting logic across rule modules;
- a second hidden ranking implementation that can drift from the actual selector;
- unsafe parsing of opaque ids;
- misleading winner reasons on tied/multi-factor cases;
- unbounded/unescaped Owner/perk/tuning/Spirit text;
- reason parser injection through `#vc-` text;
- accidental report/schema/version/fingerprint changes;
- accidental changes to close-dupe cited-partner shielding;
- brittle assumptions about optional export fields;
- insufficient fake-fixture regression coverage;
- unrelated refactors.

## 3. Re-run at least

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q \
  tests/test_dupes.py \
  tests/test_armor_dupes.py \
  tests/test_armor_close.py \
  tests/test_report.py \
  tests/test_report_run.py \
  tests/test_cli_report.py
.venv/bin/pytest -q
git diff --check
git ls-files data/
```

Also inspect the regenerated snapshot diff and run the fake weapon/combined report dry-runs if the textual output is not obvious from tests.

## Review outcome

If issues are found:

- identify each finding precisely;
- explain why it matters;
- return fixes to Luna on the **same implementation branch**;
- require focused regression coverage;
- rerun affected tests and the complete gate;
- review again.

When the orchestrating review is clean, do **not** raise a PR. Hand the branch to an independent Sol high reviewer using the prompt below.

---

# Independent Sol high review prompt

Perform an independent final review of issue `#29 — Make duplicate survivor references human-readable in notes and reports` in `tonym999/vault-cleaner`.

The branch has been implemented by Luna xhigh and already reviewed against the Sol handoff plan. Do **not** assume either the plan or implementation is correct merely because they agree.

Do **not** raise a PR.

Focus especially on the safety question: **Could the new human-readable note/report point the user at the wrong survivor/partner, misstate why it was chosen, or allow untrusted DIM text to corrupt the rule reason, while the underlying decision tests still appear green?**

Independently verify:

1. the displayed reference row is exactly the row selected by the authoritative existing weapon/armour/close-dupe algorithm;
2. selection reason text is descriptive and cannot influence the selector;
3. weapon display reflects post-#31 ranking, not stale wishlist/same-Hash assumptions from the old ticket wording;
4. full candidate/reference identities remain machine-readable strings even though Notes show suffixes;
5. `reason_slug()` and stacked-note semantics cannot be spoofed by referenced-row fields;
6. no survivor is tagged/emitted solely for discoverability;
7. no report fingerprint/ruleset/schema or review-verdict behaviour changed unintentionally;
8. downstream #101/#102 responsibilities were not pre-implemented;
9. deterministic row-reversal coverage includes the generated presentation text;
10. the full test gate and repository privacy/hygiene rules pass.

If a design assumption is unsound, return findings to the same branch for correction and require another orchestrating + independent review cycle. Only mark the branch ready for PR when both implementation and design are review-clean.

---

# Reusable Luna xhigh execution prompt

Implement issue `#29` in `tonym999/vault-cleaner` using `handoffs/issue-29-luna-xhigh-implementation-plan.md` as the primary execution contract.

Workflow:

```text
Sol orchestrates → Luna xhigh implements → orchestrating Sol reviews → independent Sol high reviews → PR
```

You are the implementation stage. **Do not raise a pull request.**

Before changing code:

- read issue #29 and its current timeline/dependencies;
- read `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md` entries, and the handoff;
- inspect latest `main` because it may have moved since planning;
- confirm #31's current weapon exact-roll implementation remains authoritative;
- branch from the latest `main` and record its SHA;
- run the baseline validation gate.

Core scope rule:

> Hold `(id, action, tag, reason_slug, kept_id)` and the ordered decision set fixed. You may change only human survivor/partner presentation, explanations derived from comparison data already used by the existing selector, preservation/tests of full IDs in the current report model, and directly related docs/tests. If a change could alter grouping, survivor/partner selection, ranking, safety rails, wishlists, tags, decisions, pass order, report version/fingerprint, review/server lifecycle, persistence, or browser protocol, stop and return the issue to Sol.

Implementation requirements:

- one shared deterministic duplicate-reference presentation seam;
- short opaque-id suffix in human Notes, full ids retained in `ReportDecision.id`/`kept_id`;
- actionable Owner/state/roll detail from existing export fields only;
- weapon winner reasons follow current #31 rank order, not wishlist or hard-protection selection;
- armour exact winner reasons follow current `_survivor_rank` order;
- armour close partner reasons use current dominated/similar metrics and keys;
- preserve parser-visible reason slugs and last-hashtag stacked Notes;
- sanitise referenced-row display text so hostile `#vc-` content cannot forge the current reason;
- do not mutate/tag the survivor;
- do not implement #101 group projection or #102 browser view;
- keep snapshot schema 1 and ruleset 3 unless you hit a stop condition;
- update `PLAN.md` with M9 and `#29 → #101 → #102`;
- update `WORKLOG.md` and concise README user documentation;
- fake fixtures only; never commit `data/`.

Run focused validation, regenerate/review the fake snapshot if Notes changed, perform the fake-fixture dry-runs, then run:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git ls-files data/
git status --short
```

Commit and push the implementation branch. Do **not** open a PR.

When complete, return a structured handoff with:

- branch;
- base `main` SHA;
- commits;
- files changed/deleted;
- final reference/note format;
- behaviour implemented;
- proof that decision/grouping/ranking semantics are unchanged;
- tests added/changed;
- exact focused/full validation results;
- snapshot regeneration/diff result;
- manual fake-fixture checks;
- schema/ruleset values;
- unresolved concerns/deviations.

---

# Ticket-specific review decision

**Review path:** `independent`

**Reason:**

#29 is bounded to presentation and must not change duplicate decisions, but the new text is safety-relevant guidance used to identify the copy that should survive. It also places additional untrusted DIM-export values into generated durable Notes and shared report presentation. A first Sol review should enforce the strict no-semantic-change contract; an independent Sol high review should then verify that the reference really points to the authoritative selected row, the explanation cannot drift from ranking, full audit identities remain intact, and hostile export text cannot corrupt the searchable reason contract before a PR is raised.
