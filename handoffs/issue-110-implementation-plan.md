# Sol / Luna Ticket Handoff — Issue #110

# Ticket

**Repository:** `tonym999/vault-cleaner`
**Issue:** `#110 — M9 C: add a same-stat / different-tuning comparison to the Armor duplicates view`
**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → Sol high reviews → PR
**Implementation model selected:** **Luna xhigh**
**Plan baseline:** `main` at `fb9a435e50a9a13e8c8afb0c93883296112ff4fa` (2026-09-01; merge commit for #102 / PR #111)

Luna must **not** open a pull request. The implementation branch is reviewed by Sol high before any PR is created.

## Objective

Extend the existing browser **Armor duplicates** surface so it renders the authoritative `same_stat_groups` already present in the report snapshot, alongside the exact-duplicate groups delivered by #102. The end state is one reusable armour-comparison component that clearly distinguishes **Exact duplicate** groups from **Same stats, different tuning** review-only groups, preserves authoritative Python group/member truth, shows every same-stat member’s text-labelled Tuning Mod Slot, and reuses the existing single-item server verdict seam only when that member already has an authoritative proposal.

This is a presentation extension. It must not change armour identity, grouping, close-dupe decisions, survivor/partner selection, server protocol, persisted state, finalisation, authentication, or lifecycle behaviour.

## Why this ticket is ready

- #101 is complete and already supplies authoritative `exact_duplicate_groups` and `same_stat_groups`.
- #104 is complete and already establishes the Tuning Mod Slot vocabulary and structured presentation contract.
- #102 is complete on current `main`; the browser now has the reusable Armor duplicates surface, exact-group projector, group header/matrix renderer, whole-group filters, reconciliation, and shared verdict map that #110 is intended to extend.
- The only comment on #110 says the proposed `docs/armor-archetypes.md` work was superseded by #102. That document now exists on `main`; #110 must not recreate or redesign it.
- The current report/server snapshot already contains all same-stat data required by the ticket. No Python or HTTP contract change is needed.

---

# Current repository state relevant to #110

## Authoritative Python/report state

`src/vault_cleaner/rules/armor_close.py` already owns the same-stat projection:

- `_same_stat_key()` is `Hash + raw Tier + all six base stats + complete Spirit signature`;
- `_same_stat_groups()` emits a group only when at least two members differ in raw `Tuning Stat`, `Seasonal Mod`, or `Holofoil`;
- group/member ordering already uses the shared opaque-id order;
- groups are review-only and do not select a survivor;
- members carry location, protection, equipped/loadout/lock state, masterwork tier, power, raw tuning, presented Tuning Mod Slot, Seasonal Mod, Holofoil, any close-pass proposal action/reason, and selected partner id.

`src/vault_cleaner/report_run.py` already serialises those groups through `_same_stat_group_snapshot()` under `section.armor.same_stat_groups`. `SNAPSHOT_SCHEMA_VERSION` is 2 and `RULESET_VERSION` is 4. These versions must remain unchanged for #110.

## Existing #102 browser seam

`src/vault_cleaner/ui/review_ui.js` currently:

- validates/projects only `exact_duplicate_groups` through `exactDuplicateGroupsFromSnapshot()`;
- preserves exact group/member order and opaque string ids/hashes;
- safely renders untrusted export strings through text APIs;
- renders one reusable `armorGroup()` / `armorGroupHeader()` / `armorGroupTable()` component;
- assumes exact-only semantics in several places: group-level Tuning Mod Slot, exact-disposition badges, preferred/retained/proposed labels, and the exact verdict row;
- filters exact groups by name/member id, class, slot/type, archetype, and a single group-level Tuning Mod Slot.

`src/vault_cleaner/ui/review_server.js` currently:

- stores one `state.armorGroups` list populated only from `exactDuplicateGroupsFromSnapshot()`;
- exposes Proposals / Armor duplicates as the top-level review-surface selector;
- retains/invalidates duplicate query state across authoritative envelope replacement;
- uses the existing report/verdict revisions and `/api/verdicts` acknowledgement path;
- has no group-kind selector yet;
- uses `state.duplicateRows[id]` as one DOM handle per id, which was sufficient for exact groups because exact-group membership is unique across exact groups.

The last point becomes important in #110: the same item may intentionally appear once in an exact subgroup **and** once in a wider same-stat group. Rendering `All` therefore requires a presentation registry that can hold multiple DOM occurrences for one opaque id while still using that id as the single verdict identity.

## Existing tests and browser gate

- `tests/test_review_ui_js.py` already covers exact-group projection, prototype-shaped keys, opaque ids, hostile strings, whole-group filtering, tier-5 stat presentation, read-only exact members, and exact proposal controls.
- `tests/test_server_ui_js.py` already covers exact-group envelope adoption/reconciliation, invalid filter clearing, rejected malformed envelopes, same-report repaint, shared cross-view verdict state, finalised disabling, and surface retention.
- `tests/test_server_browser.py` currently contains four browser tests, including one focused #102 exact-group test.
- CI installs the pinned Chromium and runs all `@pytest.mark.browser` tests in a dedicated Ubuntu job, plus the non-editable wheel proof.
- `docs/browser-verification.md` records the #102 desktop/narrow light/dark pass and the existing in-flight focused-button blur limitation.

## Documentation staleness to correct narrowly

`PLAN.md` currently describes the M9 delivery chain as ending at #102 and says #102 owns browser rendering of the group projections. That wording is now stale: #102 deliberately shipped exact groups only and #110 owns same-stat browser rendering. A minimal sequencing/ownership correction belongs in this ticket; do not otherwise rewrite M9 architecture.

---

# Review model

## Review path: **standard Sol high review**

This is a bounded browser-presentation extension over an already-landed Python snapshot contract and an already-landed authenticated server/reconciliation lifecycle. The allowed implementation must not change architecture, HTTP protocol, persistence, concurrency, stale-state semantics, authentication, finalisation, filesystem trust boundaries, or decision semantics.

The work is still subtle enough to use **Luna xhigh**, because the `All` presentation must safely handle the same opaque item id appearing in both an exact group and a same-stat group, and because the adapter must preserve #102’s hostile-input, proposal-correlation, reconciliation, and focus/state invariants. Those are cross-file presentation concerns, not a reason to escalate to an independent architectural review.

**Escalate to independent review/replanning instead of silently continuing if implementation demonstrates that any server/session/protocol/persistence/lifecycle/security-boundary change is actually required.**

---

# Authoritative context

Before changing code, Luna must read:

- `AGENTS.md`
- `PLAN.md`
- issue #110 and its comment
- issue #102 and its comment
- issue #101
- issue #104
- issue #29 for the M9 presentation boundary
- issue #109 only to recognise it as a separate rule ticket, not as implementation scope
- recent #101/#104/#102 entries in `WORKLOG.md`
- `src/vault_cleaner/rules/armor_close.py`
- `src/vault_cleaner/report_run.py`
- `src/vault_cleaner/ui/review_ui.js`
- `src/vault_cleaner/ui/review_server.js`
- `src/vault_cleaner/ui/review_server.html`
- `src/vault_cleaner/ui/review.css`
- `tests/test_review_ui_js.py`
- `tests/test_server_ui_js.py`
- `tests/test_server_browser.py`
- `tests/fixtures/armor_duplicates_ui.csv`
- `README.md`
- `docs/browser-verification.md`
- `.github/workflows/ci.yml`
- `pyproject.toml`

Treat as authoritative:

1. Python’s `same_stat_groups` membership, ordering, member fields, and proposal/partner metadata.
2. Python’s exact-group dispositions and ordering.
3. Opaque ids/hashes as untouched strings.
4. The existing server session envelope, revision/fingerprint model, `/api/verdicts` mutation seam, finalisation lifecycle, authentication, and same-origin/trust boundary.
5. #104’s Tuning Mod Slot vocabulary: `Weapons`, `Health`, `Class`, `Grenade`, `Super`, `Melee`, plus explicit `none/unknown`.
6. #102’s shared armour group component and whole-group filtering model.

Do not silently redesign any of these.

---

# Dependencies and assumptions

- Implementation branches from the **latest** `main`, not from the handoff-storage branch.
- At plan time, `main` is `fb9a435e50a9a13e8c8afb0c93883296112ff4fa`. If `main` moves before implementation, Luna must first confirm that #101/#104/#102 contracts above still hold.
- `section.armor.same_stat_groups` may be absent or empty and must be treated as “no same-stat groups”, not as an error.
- An exact-group member may also appear in a same-stat group by design. Cross-kind overlap is valid and must not be rejected as duplicate identity.
- Duplicate member ids **within the same authoritative group category where they should be disjoint** remain incompatible input. Existing exact-group uniqueness checks must remain intact; same-stat projection should use equivalent prototype-safe validation for its own category.
- A same-stat group creates no verdict target. A member becomes mutable only through an already-existing authoritative proposal for that same opaque id in the same armour section/hash context.
- Browser display may derive presentation labels such as tier-5 Primary/Secondary/Tertiary from supplied stat values, as #102 already does. Browser code must not derive membership, ranking, survivor, partner, disposition, or action truth.

---

# Ticket-specific algorithmic scope rule

For every proposed code change, Luna must apply this mechanical decision test.

A change is **in scope only if all five statements are true**:

1. **Input rule:** the change consumes or presents fields already present in `section.armor.same_stat_groups`, the existing exact-group projection, or local #102 browser presentation state.
2. **Truth rule:** it does not alter or recreate Python’s group membership, group/member ordering, close-dupe decision, exact disposition, survivor, selected partner, protection, tag, note, reason, or action.
3. **Mutation rule:** any enabled Approve/Veto/Unset control maps an already-correlated current proposal id to the **existing** single-item `/api/verdicts` path; the group itself never becomes a mutation target.
4. **Boundary rule:** the report snapshot bytes/schema, server envelope/API, revisions, fingerprint, persistence, authentication, finalisation, and lifecycle are unchanged.
5. **Footprint rule:** the effect is limited to browser projection/validation, local presentation state, DOM/CSS, fake test fixtures/tests, and ticket-owned documentation/worklog.

If any statement is false, **stop and return the issue to Sol for replanning**.

Luna must also stop immediately if the implementation appears to require any of the following:

- changing `_same_stat_key`, `_same_stat_groups`, close-dupe thresholds, exact-dupe identity, or Python group ordering;
- changing `report_run._same_stat_group_snapshot()` or snapshot/ruleset/session schema versions;
- adding JavaScript grouping, similarity, survivor, partner, disposition, or ranking logic;
- adding a tuning preference, especially a Health/Weapons special case;
- introducing group-level or bulk verdict mutations;
- treating same-stat membership itself as a junk/review decision;
- coercing ids/hashes through `Number`, `parseInt`, numeric JSON, or any other precision-losing path;
- changing server endpoints, stale-reconciliation semantics, finalisation, persistence, authentication, session state, filesystem behaviour, or network permissions;
- adding a runtime dependency;
- solving #109 or any other incidental rule defect.

Incidental findings outside this predicate go into the Luna → Sol handoff as separate observations only.

---

# Scope

## In scope

- Project and validate `same_stat_groups` into the browser’s existing armour-comparison presentation model.
- Reuse the #102 group component with group-kind-specific header/member rows rather than creating a second renderer.
- Render a clearly text-labelled **Same stats, different tuning** review-only group type.
- Show every same-stat member’s Tuning Mod Slot as an always-visible text row.
- Show Seasonal Mod and Holofoil as member comparison rows when those axes vary; show honest empty/unknown text where one side is blank.
- If raw `tuning_stat` variation would otherwise be hidden because multiple raw values present as the same `none/unknown` slot, display the supplied raw tuning value as inert supporting text. Do not use it to re-evaluate membership.
- Reuse the existing mutable-state rows: hard protection, in loadout, equipped, locked, masterwork tier, and power.
- Reuse current single-item verdict controls only for members with an authoritative current proposal; all other same-stat members are explicitly read-only.
- Support `All / Exact / Same stats` group-kind selection only when more than one kind is present.
- Keep search/facets selecting whole groups.
- Extend Tuning Mod Slot filtering so an exact group matches its shared group value and a same-stat group matches when **any member** has the selected slot, while returning the complete group.
- Preserve local duplicate surface/search/facet/kind state across redraw/reconciliation when still valid; clear only state that has become invalid.
- Make the duplicate DOM registry support multiple rendered occurrences of the same id across group kinds and repaint/disable every occurrence from the one shared verdict state.
- Add focused Node/adapter/Playwright coverage and a fake fixture.
- Update README, browser verification documentation, minimal M9 PLAN sequencing/ownership wording, and `WORKLOG.md`.

## Out of scope

- Any Python rule, grouping, snapshot, pipeline, report, decision, note, tag, or ranking change.
- Any new same-stat/near-stat clustering or pair graph.
- Any group-level survivor for same-stat groups.
- Any group-level/bulk verdict.
- Any tuning preference or scoring optimisation.
- Weapon/ghost duplicate group UI.
- #109 legacy armour rule work.
- Server endpoint/session/auth/persistence/stale-state/finalisation/lifecycle changes.
- CI topology or dependency changes.
- Reworking #102’s exact-group semantics merely because the shared renderer is being generalised.

---

# Expected change footprint

Likely files:

```text
src/vault_cleaner/ui/review_ui.js
src/vault_cleaner/ui/review_server.js
src/vault_cleaner/ui/review_server.html
src/vault_cleaner/ui/review.css              # only if the shared/segmented presentation needs it
tests/test_review_ui_js.py
tests/test_server_ui_js.py
tests/test_server_browser.py
tests/fixtures/armor_same_stat_ui.csv        # new fake fixture; name may vary narrowly
README.md
PLAN.md                                      # minimal M9 sequencing/ownership correction only
docs/browser-verification.md
WORKLOG.md
```

Files/components that should normally remain unchanged:

```text
AGENTS.md
docs/armor-archetypes.md
src/vault_cleaner/rules/armor_close.py
src/vault_cleaner/rules/armor_dupes.py
src/vault_cleaner/report_run.py
src/vault_cleaner/pipeline.py
src/vault_cleaner/server/app.py
src/vault_cleaner/server/session.py
src/vault_cleaner/review.py
config.toml
pyproject.toml
.github/workflows/ci.yml
tests/fixtures/report_snapshot_v2.json
scripts/regenerate_report_snapshot.py
```

If a substantive change to any normally-unchanged file seems necessary, Luna must stop and return the ticket to Sol with the exact reason.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean baseline

Fetch the latest default branch and create a fresh implementation branch, for example:

```bash
git fetch origin
git switch main
git pull --ff-only
git switch -c issue-110-same-stat-armor-view
```

Record the base `main` SHA in the handoff.

Before edits:

```bash
ruff check src tests scripts
pytest -q
git diff --check
git status --short
```

Also confirm:

```bash
git ls-files data/
```

must print nothing.

If the current baseline differs materially from the state described above, do not blindly apply this plan. Reconcile only legitimate presentation-layer drift; if the authoritative seams changed, return to Sol.

## 2. Preserve the Python/report/server architecture

Do **not** change Python production code for this ticket.

Use the existing snapshot arrays as authoritative:

```text
section.armor.exact_duplicate_groups
section.armor.same_stat_groups
```

Keep exact and same-stat category order exactly as supplied. For an `All` presentation, concatenate the two authoritative category sequences in a fixed presentation order (Exact first, Same stats second) without sorting or re-keying either category.

Do not invent a combined backend group id. `group_kind + group_id` is sufficient for DOM/presentation disambiguation; opaque member `id` remains the verdict identity.

## 3. Add a same-stat snapshot projector without weakening exact validation

In `review_ui.js`, retain the public behaviour of `exactDuplicateGroupsFromSnapshot()` so #102 tests and exact semantics do not regress.

Add either:

- a thin `sameStatGroupsFromSnapshot()` plus a combined `armorGroupsFromSnapshot()` helper; or
- an equivalent shared internal projector with exact/same wrappers.

Prefer shared internal helpers for proposal indexing/string validation where that reduces duplicated trust-boundary code, but do not turn this into a broad refactor.

For each same-stat group:

- require `group_kind == "same_stat"` when supplied from `same_stat_groups`;
- keep `group_id` and `hash` as required JSON strings;
- preserve group array order and member array order;
- copy `name`, `type`, `guardian_class`, `item_archetype`, `tier`, `stats`, and `spirit_signature` as inert presentation data;
- map each member’s `id`, location/protection/equipped/loadout/lock/masterwork/power, `tuning_stat`, `tuning_mod_slot`, `seasonal_mod`, `holofoil`, `proposal_action`, `proposal_reason`, and `selected_partner_id`;
- normalise blank/null categorical presentation to explicit `none/unknown` where the UI requires an honest visible value;
- use prototype-safe maps for group/member uniqueness;
- allow the same member id to exist once in an exact category and once in a same-stat category;
- reject malformed duplicate same-stat group ids/members within the same category before state adoption.

Reuse #102’s proposal-correlation boundary:

- current mutable proposal truth comes from `section.decisions`;
- correlation must be for the same armour section, same opaque id, and same group hash;
- cross-section or wrong-hash lookalikes must never grant controls;
- a supplied close-pass `proposal_action` may be displayed as same-stat metadata, but it must not manufacture a current proposal if the authoritative current section decision does not exist.

Keep every id/hash/selected-partner value as a string. Do not call `Number()` or `parseInt()`.

## 4. Generalise the existing group renderer, not the architecture

Refactor the current `armorGroupHeader()`, `armorGroupTable()`, `armorMemberCell()`, and related helpers only as much as needed to render both group kinds.

### Exact groups

The current #102 presentation is a regression contract:

- exact subtitle/label remains explicit;
- group-level Tuning Mod Slot remains visible;
- exact preferred survivor/retained/proposed dispositions remain visible;
- survivor and retained members remain read-only under the #102 rules;
- exact proposed members keep the existing verdict behaviour;
- current later-pass proposal disclosure remains truthful;
- current stat/archetype/Spirit/seasonal/holofoil presentation remains intact.

Do not “simplify” exact behaviour while making the component generic.

### Same-stat groups

Render the same article/matrix component with a clearly distinct text identity, e.g.:

```text
Same stats, different tuning · review-only
```

The header should reuse the common Name / Type / Guardian class / Tier / Hash / Archetype / stat-summary / Spirit presentation. It must **not** show an exact survivor, exact disposition, or a group-level tuning value.

Member comparison rows should be:

1. **Tuning Mod Slot** — always present for every member, text-labelled, including `none/unknown`.
2. **Seasonal Mod** — present when this supplied axis varies across members; blank sides display an honest explicit value rather than disappearing.
3. **Holofoil** — present when this supplied axis varies across members; blank sides display an honest explicit value rather than disappearing.
4. If required to avoid hiding a raw tuning variation that collapses to the same presented slot, an inert `Tuning Stat` supporting row may be shown from the supplied member field; it is presentation only.
5. Hard protection.
6. In loadout.
7. Equipped.
8. Locked.
9. Masterwork Tier.
10. Power.
11. Existing proposal/verdict presentation.

Do not call any member “preferred survivor”, “retained”, or “junk” merely because it is in this group. If a member has a current proposal, label that fact as an **existing Proposals action** so the user cannot mistake it for a same-stat group verdict.

A same-stat member without a current proposal must be explicit read-only comparison text and have no Approve/Veto/Unset buttons.

## 5. Make duplicate DOM registration one-id-to-many

Current `state.duplicateRows[id]` assumes one duplicate matrix cell per id. That assumption no longer holds when the `All` view shows an exact group and a same-stat group containing the same item.

Change the presentation registry mechanically so one id can own multiple row/cell handles, for example:

```text
duplicateRows[id] -> [handle, handle, ...]
```

or an equivalent prototype-safe structure.

Requirements:

- rendering registers every occurrence;
- `paintArmorMember(id)` repaints **all** registered occurrences for that verdict id;
- `setVerdictControlsDisabled()` disables/enables controls in **all** occurrences;
- one server verdict acknowledgement remains one opaque id mutation;
- an occurrence that is read-only stays read-only even if another occurrence for the same id has controls;
- rendering `All` must not overwrite one group kind’s DOM handle with the other;
- no DOM key should be derived by numeric coercion.

Update existing Node/adapter tests that directly inspect the old one-handle registry shape. Do not preserve an awkward test-only compatibility shape if a clean one-to-many registry is safer.

## 6. Add group-kind selection and whole-group facet semantics

Keep the current top-level Proposals / Armor duplicates selector.

Within Armor duplicates:

- derive the set of available group kinds from the projected groups;
- render `All / Exact / Same stats` only when **both** kinds are present;
- if only exact groups exist, do not render a redundant kind selector;
- if only same-stat groups exist, do not render a redundant kind selector;
- default to `All`;
- use stable accessible buttons with `aria-pressed` and an appropriate `role="group"` / label;
- preserve keyboard focus on the selected control when its pressed state is redrawn.

Store this as local presentation state only, e.g. `state.armorGroupKind`.

On report replacement:

- retain the selected kind if it still exists;
- if the selected kind disappears, reset to `All`, record a local invalidation, and keep unrelated search/filter state;
- if both exact and same-stat arrays become empty, fall back to Proposals as #102 already does;
- if exact disappears but same-stat remains (or vice versa), Armor duplicates stays available.

For search/facets:

- filter **groups**, never members out of a group;
- name/id search matches if the group name or any member id matches;
- Class, slot/type, and archetype remain group-level;
- Tuning Mod Slot:
  - exact group: compare the existing shared group tuning value;
  - same-stat group: match when any member has the requested Tuning Mod Slot;
  - return the complete group in either case;
- option counts count each matching group at most once per facet value, even if multiple same-stat members share that value;
- derive facet options from the current group-kind universe;
- when a user switches group kind, preserve categorical filters that still exist in that universe and clear only the ones that do not; preserve search text;
- `Showing N of M groups` should use `M` as the number of groups in the selected kind universe before search/facet filtering.

Do not sort authoritative groups in JavaScript.

## 7. Preserve acknowledgement, rejection, reconciliation, and finalised behaviour

No request shape or endpoint changes are permitted.

Extend existing adapter behaviour so:

- a same-stat-only report enables Armor duplicates;
- a malformed same-stat projection is rejected before the new envelope is adopted;
- a rejected upload leaves the previous surface, kind selection, search, facets, and DOM state intact;
- same-report verdict acknowledgement repaints every rendered occurrence of the id without a full view reset;
- a report replacement rebuilds from the new authoritative groups while retaining only valid local state;
- finalised state leaves both group kinds readable and freezes all mutation controls;
- reset/shutdown behaviour remains exactly as #102/#90 established.

Do not add retry/replay logic.

## 8. Update static HTML/CSS narrowly

Update `review_server.html` so the Armor duplicates explanatory text no longer claims that the surface contains exact groups only. It should explain:

- exact groups show authoritative survivor/disposition context;
- same-stat groups are review-only comparisons;
- verdict controls appear only where the current report already has a proposal.

Use existing classes and responsive patterns where possible. Add CSS only for the nested group-kind selector or clear text distinction if the existing `.view-selector`, button, matrix, and narrow-layout rules are insufficient.

Do not change asset routes or the server asset allow-list.

## 9. Add focused fake fixture coverage

Add a fake armour fixture specifically for the same-stat browser path, preferably `tests/fixtures/armor_same_stat_ui.csv`.

Keep it small and deterministic:

- same Hash, Tier, six base stats, and Spirit signature;
- at least two members;
- members differ in Tuning Stat/Tuning Mod Slot (use two supported values such as `Weapons` and `Health`; the pairing is not a preference);
- optionally include one blank/unknown tuning or a Seasonal Mod/Holofoil variant only if needed for a focused acceptance assertion;
- use fake names, hashes, ids, owners, and values only.

Do not copy a real vault row.

The focused Playwright fixture does not need to manufacture both group kinds; mixed exact/same selection can be tested cheaply and deterministically in the Node adapter harness.

## 10. Required automated tests

### `tests/test_review_ui_js.py`

Add/extend tests proving:

1. `same_stat_groups` project with group/member order unchanged and ids/hashes/partner ids preserved as strings.
2. Prototype-shaped `group_id`/member ids do not pollute prototypes.
3. Duplicate same-stat group/member identities in the same category are rejected.
4. Intentional exact/same overlap for one member id is accepted.
5. Same-stat projection rejects cross-section/wrong-hash proposal lookalikes before they can grant mutation controls.
6. Group rendering is clearly labelled “Same stats, different tuning” / review-only.
7. Same-stat rendering never emits exact survivor/retained/junk disposition labels from group membership.
8. Tuning Mod Slot is always visible per member, including explicit `none/unknown`.
9. Seasonal Mod/Holofoil member rows appear when those supplied axes vary and retain inert text.
10. Mutable-state rows are present.
11. No-proposal same-stat members have no verdict buttons.
12. Current-proposal same-stat members reuse the existing single-id callback.
13. Hostile name/location/archetype/tuning/mod/holofoil strings remain text; no injected `IMG`, `SCRIPT`, `B`, or event-driven markup.
14. Tuning filtering matches any member but returns the full group.
15. Facet counting counts a group once per value.
16. Tier-5 stat display remains the existing #102 presentation and no membership logic is reimplemented.

### `tests/test_server_ui_js.py`

Add/extend adapter tests proving:

1. a same-stat-only envelope enables/stores Armor duplicates while exact is empty;
2. mixed exact+same groups expose both kinds in deterministic presentation order;
3. the kind selector appears only when both kinds are present;
4. All/Exact/Same stats selects whole groups and count totals correctly;
5. switching kind preserves valid search/facets and clears only invalid categorical values;
6. selected kind survives report replacement when still available and resets to All when it disappears;
7. rejected/malformed same-stat replacement does not adopt the envelope or erase prior local state;
8. finalised state freezes same-stat proposal controls;
9. one verdict id rendered in both an exact and same-stat group registers multiple DOM handles and every applicable occurrence repaints/disable-gates correctly;
10. read-only and mutable occurrences for the same id retain their own presentation semantics;
11. ids remain opaque strings, including leading-zero, huge, non-digit, and prototype-shaped examples where relevant.

Preserve all existing #102 exact tests; update their registry assertions only where the one-to-many DOM registry intentionally changes.

### `tests/test_server_browser.py`

Add **exactly one** new focused browser test for #110, e.g.:

```text
test_armor_same_stat_group_renders_member_tuning_variation
```

Through the packaged authenticated server:

- upload the fake same-stat armour fixture;
- assert Armor duplicates is enabled even with no exact groups;
- enter Armor duplicates;
- assert one clearly labelled same-stat/review-only group is visible;
- assert both complete member ids are visible;
- assert each member’s Tuning Mod Slot is visible as ordinary text, with the chosen differing values;
- assert the group does not show exact-survivor/junk-disposition wording;
- if the fixture naturally produces a current proposal, assert only the authoritative proposal member(s) have controls and acknowledgement uses the existing state map;
- assert the field is visible without hover/hidden expansion.

Do not add a second new Playwright case. Use Node tests for mixed-kind selector/reconciliation edge cases.

## 11. Manual verification

Using only fake fixture data and `--no-wishlists`, perform a focused packaged-server visual pass and record it in `docs/browser-verification.md` and the Luna handoff:

- desktop approximately 1440×1000, light and dark;
- narrow approximately 390×844, light and dark;
- same-stat heading is visually/textually distinct from exact groups;
- Tuning Mod Slot labels/values are readable without colour, hover, or expansion;
- matrix horizontal overflow stays contained on narrow width;
- keyboard navigation reaches the Armor duplicates surface, group-kind selector when present, filters, and any authorised member verdict controls with visible focus;
- `All / Exact / Same stats` is checked with a synthetic/mixed test state or fake fixture if readily available;
- finalised/read-only rendering remains legible and controls are frozen;
- no same-stat group implies a survivor or junk recommendation;
- hostile values remain inert (automation is the primary proof; visual pass only confirms no presentation regression).

Do not repeat unrelated manual server lifecycle/multi-tab testing unless the implementation unexpectedly touches those paths. If it does, that is a scope-escalation signal first.

Record browser/version and focused test timing as #102 did.

## 12. Documentation and `WORKLOG.md`

### README

Update the existing armour duplicate paragraph to explain that Armor duplicates now includes:

- authoritative exact groups; and
- review-only same-stat/different-tuning groups.

State that same-stat groups do not create a survivor or junk recommendation and that per-member Tuning Mod Slot is visible.

### PLAN.md

Make only the M9 sequencing/ownership correction required by current reality:

```text
#29 → #101 → #104 → #102 exact-group browser view → #110 same-stat browser extension
```

Correct the sentence that currently implies #102 owns all same-stat browser rendering. Do not alter rules/architecture text.

### `docs/browser-verification.md`

Add an Issue #110 focused checklist and a dated execution record covering the manual pass above, including browser timing and any remaining limitation.

### `WORKLOG.md`

Add a dated #110 entry describing:

- same-stat projection/rendering added through the #102 component;
- exact/same distinction;
- one-to-many duplicate DOM registry for legitimate cross-kind overlap;
- group-kind selector/filter/state behaviour;
- tests and the single new Playwright case;
- manual light/dark/narrow results and timing;
- exact validation results;
- confirmation that Python rules/report schema, server protocol/lifecycle, runtime dependencies, and #109 remain unchanged.

Do not update `docs/armor-archetypes.md`; #110’s own comment says that documentation deliverable was superseded and #102 has already landed it.

---

# Failure/recovery behaviour

This ticket adds no new server failure mode.

- **Projection validation fails:** reject the incoming envelope as incompatible before adoption; preserve the last known safe state exactly as the existing adapter does.
- **Upload is rejected:** retain current duplicate surface, selected group kind, search/facets, and rendered report.
- **Verdict request fails:** existing mutation/stale handling remains authoritative; never replay automatically.
- **Report replacement removes one group kind:** retain Armor duplicates if the other kind remains, reset only the now-invalid kind selection, and reconcile invalid facets.
- **Report replacement removes all duplicate groups:** return to Proposals using existing #102 behaviour.
- **Finalisation:** existing frozen/read-only semantics apply; no special same-stat finalisation path.
- **Partial browser rendering error:** do not fall back to deriving group truth or mutating server state.

---

# Local/user presentation state to preserve

Preserve when still valid:

- top-level `surface`;
- same-stat/exact `armorGroupKind`;
- duplicate search text;
- class filter;
- slot/type filter;
- archetype filter;
- Tuning Mod Slot filter;
- current server verdict map;
- focused stable control where a local redraw is required.

Legitimately drop only:

- a selected group kind no longer present in the new authoritative report;
- a categorical filter value absent from the relevant replacement/current kind universe;
- duplicate DOM handles when a report-changing rebuild occurs;
- the Armor duplicates surface when **no exact or same-stat groups remain**.

Never reset Proposals query/sort/expanded state merely because same-stat state changes.

---

# Security and trust boundary

Maintain all existing #102/#90 rules:

- snapshot/server payloads are untrusted input;
- ids/hashes/partner ids remain opaque strings;
- prototype-shaped data keys use prototype-safe maps;
- all export-derived strings reach the DOM as text, never HTML;
- no request-derived filesystem paths;
- no new network/API access;
- no new runtime dependency;
- no authentication, Host/Origin, cookie, no-store, or same-origin changes;
- no server payload accepts a group id as a mutation target.

Ticket-specific trust invariant:

> A same-stat member may show verdict controls only because a current authoritative proposal for the same opaque id is correlated in the same armour section and group hash. Same-stat membership, tuning difference, or browser inference must never grant mutation authority.

---

# Luna completion gate

Before handoff to Sol, Luna must have:

- implemented every in-scope acceptance criterion;
- preserved the exact-group #102 behaviour;
- added the one-to-many duplicate DOM registry needed for valid cross-kind overlap;
- added focused Node/adapter tests and exactly one new Playwright test;
- completed the fake-data manual visual pass;
- updated README, minimal PLAN wording, browser verification docs, and WORKLOG;
- committed and pushed the implementation branch;
- **not opened a PR**.

The handoff must contain:

- implementation branch;
- base `main` SHA;
- commit SHA(s);
- files changed/added;
- implementation summary;
- tests added/changed;
- exact command results;
- focused Chromium result and timing;
- full browser marker result;
- manual light/dark/narrow result;
- wheel proof result;
- known risks/uncertainties;
- any deviation from this plan;
- confirmation that no PR was opened.

---

# Exact validation commands

Use the repository environment/interpreter convention for the machine. The CI-equivalent POSIX commands are:

## Focused non-browser gate

```bash
ruff check src tests scripts
pytest -q tests/test_review_ui_js.py tests/test_server_ui_js.py
git diff --check
```

## Install Chromium if the managed browser is not already present

```bash
python -m playwright install --with-deps chromium
```

## Focused #110 browser test

Use the final test name if Luna chooses an equally clear narrow name:

```bash
VAULT_CLEANER_BROWSER_REQUIRED=1 \
pytest -q \
  tests/test_server_browser.py::test_armor_same_stat_group_renders_member_tuning_variation \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results
```

## Full repository and packaged-browser gate

```bash
ruff check src tests scripts
pytest -q
python scripts/check_wheel_install.py
VAULT_CLEANER_BROWSER_REQUIRED=1 \
pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results
git diff --check
```

## Privacy/hygiene and branch state

```bash
if git ls-files data/ | grep -q .; then
  echo "ERROR: tracked file(s) under data/"
  git ls-files data/
  exit 1
fi

git status --short
git log -1 --oneline
```

Expected final `git status --short`: clean after the implementation commit.

If using PowerShell, set `VAULT_CLEANER_BROWSER_REQUIRED=1` with the shell’s normal environment-variable syntax; do not weaken the required-browser guard.

---

# Orchestrating Sol high review prompt

Review the completed Luna xhigh implementation for issue `#110` in `tonym999/vault-cleaner`.

Do **not** raise a PR yet.

This ticket uses the **standard Sol high review path**. Review both plan conformance and engineering quality against the current GitHub issue and the handoff plan.

## 1. Plan-conformance review

Confirm:

1. The branch started from the latest legitimate `main`.
2. The implementation consumes existing `same_stat_groups`; it does not change Python group generation or report/server schemas.
3. The #102 armour group component was extended rather than a parallel same-stat renderer being created.
4. Same-stat groups are clearly labelled review-only and never imply an exact survivor/disposition or group junk decision.
5. Every same-stat member shows text-labelled Tuning Mod Slot, including `none/unknown`.
6. Seasonal Mod/Holofoil variation is visible from supplied member data.
7. Current proposal controls are granted only through same-section/same-hash correlation to an existing proposal id.
8. No group-level/bulk mutation was added.
9. Exact-group #102 behaviour remains unchanged.
10. `All / Exact / Same stats` appears only when both kinds exist and selects whole groups.
11. A same-stat-only report still enables Armor duplicates.
12. Tuning filtering matches any same-stat member but keeps the complete group; counts do not double-count a group for repeated member values.
13. Cross-kind exact/same overlap is accepted, while malformed within-category duplicate identities are rejected.
14. One opaque id can have multiple rendered DOM occurrences and one verdict acknowledgement repaints/disables every applicable occurrence without changing read-only occurrences.
15. Replacement/rejection/finalisation preserves the existing state/lifecycle semantics.
16. Hostile export strings remain inert and ids never pass through JavaScript Number coercion.
17. Exactly one new focused Playwright case was added.
18. README, browser verification docs, WORKLOG, and the narrow M9 PLAN ownership wording are updated; `docs/armor-archetypes.md` was not needlessly changed.
19. No #109 work or unrelated cleanup leaked into the diff.

## 2. Engineering review

Inspect the actual diff for:

- duplicated exact/same validation or rendering logic that should share a narrow helper;
- over-generalised refactors not justified by #110;
- accidental cross-kind id rejection;
- `duplicateRows` registry overwrite/stale-handle bugs;
- one occurrence repainting while another remains stale;
- control-gating based on group membership rather than current proposal truth;
- wrong-hash/cross-section proposal correlation;
- group/member reordering in JavaScript;
- facet counts that count members instead of groups;
- kind/filter reconciliation that clears unrelated state;
- hidden tuning values, colour-only distinction, or misleading exact/junk labels;
- unsafe `innerHTML`, dynamic HTML parsing, or numeric id conversion;
- exact-group regressions from making the renderer generic;
- insufficient hostile/prototype/leading-zero/overlap tests.

## 3. Independently verify validation

At minimum rerun:

```bash
ruff check src tests scripts
pytest -q tests/test_review_ui_js.py tests/test_server_ui_js.py
pytest -q
python scripts/check_wheel_install.py
VAULT_CLEANER_BROWSER_REQUIRED=1 \
pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results
git diff --check
git ls-files data/
```

Review the #110 manual verification record rather than accepting Luna’s summary alone.

## Review outcome

If findings exist:

- identify each precisely with file/behaviour;
- explain why it violates #110 or an existing invariant;
- return it to Luna for correction on the same branch;
- require a focused regression for behaviour bugs;
- rerun affected focused tests and the full completion gate;
- review again.

Only when the branch is review-clean should Sol high report:

```text
READY FOR PR
```

Do not create the PR unless the owner explicitly asks.

---

# Reusable Luna xhigh execution prompt

Implement issue `#110` in `tonym999/vault-cleaner` using the Sol handoff plan at:

```text
handoffs/issue-110-luna-xhigh-implementation-plan.md
```

You are the implementation agent. Use **Luna xhigh**.

Workflow:

```text
Sol plans/orchestrates → Luna xhigh implements → Sol high reviews → PR
```

Rules:

- read issue #110 and its comment, #102, #101, #104, #29, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and the handoff before editing;
- branch from the latest `main`, **not** from `handoff/issue-110-luna-plan`;
- record the base `main` SHA;
- treat current repository state as authoritative if it has legitimately moved since this plan, but preserve the plan’s ticket-specific scope rule;
- consume the existing authoritative `same_stat_groups`; do not change Python grouping/rules/report schema;
- extend the #102 armour comparison component; do not create a second renderer;
- preserve exact-group behaviour;
- handle legitimate exact/same cross-kind member overlap with a one-id-to-many DOM registry;
- keep ids/hashes opaque strings and hostile strings inert;
- grant same-stat member verdict controls only for an already-correlated current proposal using the existing single-id server path;
- add behavioural Node/adapter tests and exactly one new focused Playwright test;
- use fake fixture data only;
- update README, the narrow M9 PLAN ownership/sequencing wording, `docs/browser-verification.md`, and `WORKLOG.md`;
- do not change `docs/armor-archetypes.md` unless Sol explicitly replans the ticket;
- run the exact focused/full/wheel/browser/diff/privacy validation in the handoff;
- perform and record the requested desktop/narrow light/dark manual check;
- commit and push the implementation branch;
- **do not open a pull request**.

If any work crosses the stop/escalation conditions in the handoff—especially Python group semantics, report/server contracts, lifecycle/auth/persistence, group-level mutations, tuning preferences, or runtime dependencies—stop implementation and return the issue to Sol for replanning rather than broadening scope.

When complete, return a structured handoff with:

- branch name;
- base `main` SHA;
- commit SHA(s);
- files changed/added;
- behaviour implemented;
- tests added/changed;
- exact validation results and timings;
- browser/manual verification results;
- known risks/uncertainties;
- deviations from plan;
- explicit confirmation that no PR was opened.

---

# Ticket-specific review decision

**Review path:** `standard Sol high review`

**Reason:**

Issue #110 is a browser presentation extension over already-authoritative Python group projections and an already-established authenticated server mutation/reconciliation seam. Its allowed change surface is localised to projection, DOM presentation, local UI state, tests, fake fixtures, and documentation. It must not alter architecture, protocol, persistence, concurrency, stale-state handling, lifecycle, authentication, or security boundaries. The cross-kind duplicate-DOM registry is subtle and merits Luna xhigh plus a careful Sol high review, but it remains presentation-local and mechanically testable.

If implementation proves that a forbidden higher-risk boundary must change, the correct response is **replanning**, not silently upgrading the implementation scope.
