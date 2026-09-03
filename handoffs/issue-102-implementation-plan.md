# Ticket

**Repository:** `tonym999/vault-cleaner`  
**Issue:** `#102 — M9 B: add an Armor duplicates view to the local review UI`  
**Implementation model:** Sol plans/orchestrates → Luna xhigh implements → Sol high reviews → PR  
**Plan baseline:** `main` at `c3abe8aab6fd0baabbfa2567b2f6fae0776fdd96` (`Expose armor tuning slots across comparisons (#108)`, 2026-08-31)

## Objective

Add a permanent **Armor duplicates** presentation to the authenticated local review-server UI, alongside the existing **Proposals** presentation. The view must consume the authoritative `section.armor.exact_duplicate_groups` payload already delivered by #101, show the complete group without reconstructing rule truth, and reuse the existing server-acknowledged verdict path only for members that already carry a proposal.

The intended end state is an accessible, narrow-layout-safe, light/dark-compatible comparison surface whose group header explains the shared armour roll and whose member matrix makes the survivor-ranking facts visible. The preferred survivor and retained/protected copies are explicitly read-only; proposal members expose the same Approve/Veto/Unset semantics as Proposals. Switching views and server reconciliation must preserve still-valid local presentation state, while finalised sessions remain readable and frozen.

This ticket also owns the reviewed Armor 3.0 domain reference from the issue comment, the corresponding `AGENTS.md` gotcha correction, the browser-verification documentation, the README description, and a dated `WORKLOG.md` entry.

## Why this ticket is ready

- #101 is closed and its authoritative armour exact-group contract is present on current `main`. `report_run.py` serialises exact groups directly rather than asking browser consumers to reconstruct identity, ordering, survivor selection, or disposition.
- #104 is closed and is the current tip of `main`. Its Tuning Mod Slot presentation work is already present in the ordinary Proposals view.
- #105's `location` / `guardian_class` split is already part of the current report/UI model, so #102 must use `guardian_class` as its Class facet and member `location` only as location metadata.
- The existing dedicated Ubuntu browser job already runs every test marked `browser`, installs pinned Chromium, runs the non-editable wheel proof, and retains Playwright failure artefacts. Adding the one required #102 browser test extends that job automatically; no CI workflow edit is normally needed.
- The project already packages `review.css`, `review_server.html`, `review_ui.js`, and `review_server.js` as `vault_cleaner.ui` package data. #102 can be implemented within those established assets without adding a new server asset or runtime dependency.

## Current repository state relevant to #102

At the plan baseline:

- `src/vault_cleaner/report_run.py` has `SNAPSHOT_SCHEMA_VERSION = 2` and `RULESET_VERSION = 4`.
- `ArmorSectionDetails` contains both `exact_duplicate_groups` and `same_stat_groups`.
- `_exact_duplicate_group_snapshot()` emits, without recomputation:
  - `group_kind` (`exact_duplicate`), `group_id`, `hash`, `name`, `type`, `guardian_class`, `item_archetype`, `tier`;
  - all six base stats in `stats`;
  - shared `tuning_mod_slot`, `seasonal_mod`, `holofoil`, `spirit_signature`;
  - `preferred_survivor_id`;
  - ordered members with `id`, `location`, protection state/reason, equipped/loadout/lock state, masterwork tier, power, disposition, proposal action, and proposal reason.
- `rules/armor_dupes.py` already orders exact members as preferred survivor → retained protected → proposed junk → proposed review, with the shared opaque-id order only as a tie-break inside a disposition bucket. The browser must preserve that order verbatim.
- `src/vault_cleaner/ui/review_ui.js` is the shared pure presentation layer. It already uses `Object.create(null)` for untrusted/data-keyed maps, requires snapshot ids to be JSON strings, and creates DOM with `createElement`/`textContent` rather than HTML injection.
- `itemsFromSnapshot()` currently consumes only proposal decisions. It does **not** consume `exact_duplicate_groups` yet.
- `src/vault_cleaner/ui/review_server.js` owns browser-local state and the server adapter. The existing verdict path is `toggleVerdict()` → `mutateVerdicts()` → `POST /api/verdicts` → authoritative envelope adoption. Acknowledged same-report verdicts repaint rows in place rather than rebuilding them.
- `review_server.html` currently has a single Proposals panel and one Proposals filter panel.
- `review.css` already has light/dark variables, visible focus, contained table scrolling, and a narrow-layout breakpoint.
- `tests/test_review_ui_js.py` is the natural home for pure/DOM presentation tests. `tests/test_server_ui_js.py` is the natural home for adapter/state-reconciliation tests.
- `tests/test_server_browser.py` currently contains three real-browser tests. #102 must add **exactly one** further focused Playwright test.
- `.github/workflows/ci.yml` already runs `pytest -q -m browser` in a dedicated Ubuntu job with Chromium and failure artefacts. Do not add browser execution to the core Ubuntu/Windows test matrix.
- `scripts/check_wheel_install.py` already proves that the root HTML and the three allow-listed UI assets work from a non-editable wheel installation. Because #102 changes existing packaged assets, the proof must be rerun but normally should not be edited.
- `docs/browser-verification.md` has the reusable browser checklist and a #104 execution record which explicitly says the Armor duplicates view remains #102.
- `README.md` still says the later Armor duplicates group view is tracked separately; that sentence becomes stale when #102 lands.
- `docs/armor-archetypes.md` does not exist on current `main`.
- `AGENTS.md` still has the superseded “30+25 stat spike (~75 base total)” gotcha and lacks the Destiny-archetype versus scoring-profile terminology warning. #102's issue comment supplies the reviewed replacement text.
- `PLAN.md` already records the M9 order `#29 → #101 → #104 → #102`, ruleset v4/snapshot v2, authoritative groups, tuning, and `guardian_class`. It does not need another #102-only amendment.

## Dependencies, related work, and assumptions

### Completed prerequisites

- #29 — shared human-readable survivor/partner references and audit-id preservation.
- #101 — authoritative exact-duplicate and same-stat projections, deterministic opaque-id order, exotic class-item duplicate semantics.
- #104 — cross-surface Tuning Mod Slot presentation, including ordinary Proposals.
- #105 — split `location` from `guardian_class`.

### Follow-on/related tickets

- #110 depends on #102 and will add same-stat/different-tuning groups by **reusing** the group component built here. #102 should therefore avoid an exact-only renderer architecture, but it must not render `same_stat_groups` yet.
- #109 changes legacy exotic protection rules and is unrelated to this presentation ticket. Do not absorb it.

### Assumptions that are authoritative for this ticket

- Python/#101 owns exact-group identity, membership, ordering, survivor selection and dispositions.
- The server session/revision/verdict/finalisation/reset/upload/stale-state protocol is already established and is not redesigned here.
- `Tuning Stat` is exact-roll identity. Differently tuned pieces are not exact duplicates.
- Tier-5 Armor 3.0 base distribution is 30 primary + 25 secondary + 20 tertiary + three zero base stats. The archetype fixes primary/secondary; the tertiary is independent.
- The snapshot does not expose a structured “winner decided here” rank field. #102 ships without that marker rather than parsing `proposal_reason` or recomputing survivor logic.
- The snapshot does not expose `Tertiary Stat` by name. #102 may derive the tertiary **for display only** from the six group stats when the tier-5 30/25/20 shape is unambiguous. It must not add a schema field or use that derivation for identity/filtering/ordering.

---

# Review model

## Standard Sol high review

Use the standard path:

```text
Sol orchestrator
    ↓
Luna xhigh implementation
    ↓
Sol high review
    ↓
PR
```

**Why:** #102 is deliberately bounded presentation work. The safety-sensitive exact-group truth, opaque-id ordering, report schema, and decision semantics were independently established in #101; the cross-surface tuning contract is already established in #104. A correct #102 implementation consumes those contracts and reuses existing acknowledged verdict mutations without changing protocol, persistence, stale-state semantics, lifecycle, security boundaries, or Python decision code.

Luna **xhigh** is preferred over Luna high because the ticket spans shared JavaScript presentation code, adapter state reconciliation, accessible DOM structure, responsive CSS, hostile-input safety, cross-view verdict repainting, one real-browser acceptance test, packaging proof, and several documentation updates. The work is still standard-review risk because those changes must remain within established UI seams.

If implementation crosses one of the stop/escalation boundaries below, this review classification is no longer valid: stop and return the ticket to Sol for replanning rather than silently upgrading the implementation scope.

---

# Authoritative context

Before changing code, Luna must read:

- `AGENTS.md`;
- `PLAN.md`, especially the M9 section and server lifecycle/security boundaries;
- issue #102 and its full comment containing the reviewed `docs/armor-archetypes.md` draft and `AGENTS.md` diff;
- completed dependencies #101 and #104;
- the relevant #29/#105 context needed to understand survivor references and Class/Location presentation;
- follow-on #110 so the component seam remains reusable without implementing #110;
- recent #101/#104/#108 entries at the top of `WORKLOG.md`;
- `src/vault_cleaner/report_run.py` exact-group projection;
- `src/vault_cleaner/rules/armor_dupes.py` **for contract understanding only**, not modification;
- `src/vault_cleaner/ui/review_ui.js`;
- `src/vault_cleaner/ui/review_server.js`;
- `src/vault_cleaner/ui/review_server.html`;
- `src/vault_cleaner/ui/review.css`;
- `tests/test_review_ui_js.py`;
- `tests/test_server_ui_js.py`;
- `tests/test_server_browser.py`;
- `.github/workflows/ci.yml`;
- `scripts/check_wheel_install.py`;
- `docs/browser-verification.md`;
- the relevant README browser/tuning sections.

Treat as authoritative:

1. `section.armor.exact_duplicate_groups` as emitted by `snapshot_dict()`;
2. backend group/member array order;
3. each member's `disposition`, `proposal_action`, and `proposal_reason`;
4. the existing `/api/verdicts` acknowledged mutation path and revision/fingerprint checks;
5. current server finalisation/reset/upload/stale-state/lifecycle semantics;
6. ids/hashes as opaque JSON strings;
7. export strings as untrusted inert text;
8. runtime dependencies limited to pandas and Flask.

Do not silently redesign any of these.

---

# Ticket-specific algorithmic scope rule

For **every proposed code change**, Luna must apply this mechanical test before making it.

A change belongs in #102 **only if all of the following are true**:

1. It is required to **read, project, filter, render, style, reconcile, or test** the already-authoritative `exact_duplicate_groups` payload in the local browser UI; **or** it is one of the documentation/fixture changes explicitly required by #102.
2. It preserves each backend group as an indivisible ordered unit:
   - no member is added/removed by browser filtering;
   - `group_id`, `preferred_survivor_id`, member `id`, `disposition`, proposal fields, and backend member order are consumed, not recomputed;
   - ids/hashes remain strings and never pass through `Number`/`parseInt`/numeric coercion.
3. Any mutation triggered from the duplicate view targets **one existing proposal member id** and goes through the current `mutateVerdicts`/`/api/verdicts` acknowledgement seam. The browser does not invent a group verdict or optimistic state.
4. Any new local state is presentation-only: selected surface, exact-group filter values, DOM handles, and/or focus/presentation bookkeeping. It must not alter server/session/revision/fingerprint semantics.
5. Any tier-5 stat-role derivation is display-only. It may identify 30/25/20 from `group.stats` when unambiguous; it must fall back honestly to the six supplied values if the shape is not the settled tier-5 shape. It must never affect group identity, ordering, disposition, filtering, or verdicts.

**Stop and return #102 to Sol for replanning** before proceeding if any implementation step would require one or more of:

- changing `src/vault_cleaner/rules/**`, `pipeline.py`, `report_run.py`, snapshot schema/ruleset versions, a snapshot golden, or any Python duplicate decision/ranking/note/tag/report semantics;
- changing `server/app.py`, `server/session.py`, `review.py`, verdict validation, revision checks, stale handling, finalisation, reset transactionality, upload transactionality, authentication, persistence, shutdown/lifecycle behaviour, or trust boundaries;
- reconstructing exact membership/fingerprint/survivor/disposition/order in JavaScript;
- sorting exact-group members client-side instead of preserving backend order;
- parsing human-readable Notes or `proposal_reason` to infer structured facts;
- adding a “winner decided here” marker without a structured backend field;
- adding `Tertiary Stat` to the report/snapshot payload;
- rendering `same_stat_groups` (#110), clustering close duplicates, or adding weapon duplicate groups;
- adding group-level/bulk verdict actions to the duplicate view;
- adding any stat/tuning preference, scoring or survivor nomination;
- adding a new runtime dependency or a new UI asset that forces the server asset allow-list/protocol to change;
- changing `.github/workflows/ci.yml` merely to “include” the new Playwright test, because the current `-m browser` job already includes it.

If the current #101 payload proves genuinely insufficient or contradictory, record the exact missing/contradictory field and return to Sol. Do not patch around the contract in JavaScript.

Incidental defects discovered outside this rule must be reported separately, not fixed in #102.

---

# Scope

## In scope

- Accessible top-level selection between **Proposals** and **Armor duplicates**.
- Duplicate view availability only when at least one authoritative exact group exists.
- A reusable armour-group presentation seam in the shared UI module that #110 can extend later without implementing same-stat rendering now.
- Exact-group projection from the snapshot without semantic reconstruction.
- Group-level search/filtering by:
  - item name or any member instance id;
  - `guardian_class`;
  - `type`/slot;
  - `item_archetype`;
  - shared `tuning_mod_slot`.
- Whole-group filtering and `showing N of M groups` feedback.
- Group header with name, type/slot, Guardian class, tier, hash, archetype badge, stat presentation, Tuning Mod Slot, Spirit signature, Seasonal Mod and Holofoil where useful/applicable.
- Tier-5 stat display that leads with archetype and role-labelled 30/25/20 values while collapsing the three zero base stats; safe six-stat fallback for non-conforming data.
- Member matrix with backend members as columns and comparison/state rows including member id/location plus the settled rank ladder: hard protection, loadout, lock, Masterwork Tier, and Power.
- Clear preferred-survivor, retained-protected and proposed-member labels derived only from `disposition`/proposal fields.
- Read-only text for survivor/retained cells instead of disabled verdict widgets.
- Existing server-authoritative Approve/Veto/Unset controls for proposal members only.
- Repainting duplicate-member verdict state after an acknowledgement without rebuilding the report when the authoritative report has not changed.
- Preservation/reconciliation of still-valid view selection, duplicate search/filter values, existing Proposals expansion/search state, and focus conventions across view switches/acknowledgements/refresh/stale reconciliation/rejected upload; successful replacement clears only now-invalid group-specific categorical state.
- Finalised duplicate view stays readable with mutation controls frozen by the existing lifecycle gate.
- Hostile/prototype-shaped data safety and opaque-id precision tests.
- Exactly one new focused Playwright test.
- A fake focused armour fixture if the existing fixtures do not provide a concise browser group with meaningful archetype/stats and survivor/retained/proposal states.
- `docs/armor-archetypes.md` copied from the reviewed issue comment.
- Required `AGENTS.md`, README, browser-verification and `WORKLOG.md` updates.

## Out of scope

- Same-stat/different-tuning rendering (#110).
- Weapon duplicate groups.
- Near-stat clustering/pair graphs.
- New duplicate/scoring/safety-rail rules.
- Tuning or stat preference/ranking.
- Survivor nomination or tie-break switching in the browser.
- “Decided here” winner-rank marker until Python exposes it structurally.
- Group/bulk verdict mutations in Armor duplicates.
- Snapshot/report/server protocol changes.
- Session/review persistence, stale-state, finalisation, upload, reset, auth or lifecycle redesign.
- New browser families, retries, fixed sleeps, screenshot-baseline testing or desktop GUI work.
- New runtime dependencies.
- Health-led armour demotion/preference; the new domain doc records this as owner context only.

---

# Expected change footprint

Likely production files:

```text
src/vault_cleaner/ui/review_ui.js
src/vault_cleaner/ui/review_server.js
src/vault_cleaner/ui/review_server.html
src/vault_cleaner/ui/review.css
```

Likely tests/fixtures:

```text
tests/test_review_ui_js.py
tests/test_server_ui_js.py
tests/test_server_browser.py
tests/fixtures/armor_duplicates_ui.csv   # only if a dedicated concise fake fixture is useful
```

Required documentation/history:

```text
docs/armor-archetypes.md
docs/browser-verification.md
README.md
AGENTS.md
WORKLOG.md
```

Files/components that should normally remain unchanged:

```text
src/vault_cleaner/rules/**
src/vault_cleaner/pipeline.py
src/vault_cleaner/report_run.py
src/vault_cleaner/review.py
src/vault_cleaner/report.py
src/vault_cleaner/server/app.py
src/vault_cleaner/server/session.py
src/vault_cleaner/parse.py
PLAN.md
pyproject.toml
.github/workflows/ci.yml
scripts/check_wheel_install.py
tests/fixtures/report_snapshot_v2.json
```

A substantive need to change any of those normally-unchanged semantic/protocol files is a stop/escalation event, not licence to expand the ticket.

---

# Implementation plan for Luna xhigh

## 1. Establish a clean implementation baseline

Do **not** implement on the handoff branch. The handoff branch stores the plan only.

From the latest `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git switch -c issue-102-armor-duplicates-view
```

Record the base `main` SHA in the Luna → Sol handoff. Re-read the issue and this plan after updating `main`; if code has moved materially, adapt only within the scope rule.

Before editing:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git status --short
git ls-files data/
```

The last command must print nothing. If baseline validation fails for an unrelated environmental reason, record the exact failure before changing code rather than hiding it.

## 2. Add a pure exact-group projection in the shared presentation layer

Extend `review_ui.js` with a small pure seam such as `exactDuplicateGroupsFromSnapshot(snapshot)` (name may vary) that:

1. walks only armour sections;
2. reads `section.armor.exact_duplicate_groups`;
3. requires `group_id`, group `hash`, `preferred_survivor_id` and every member `id` to be strings where present/required;
4. copies/presents fields without mutating the snapshot;
5. preserves group array order and **member array order exactly**;
6. uses `Object.create(null)` for any data-keyed registries;
7. never reads `same_stat_groups` for rendering in this ticket;
8. never calls `Number`, `parseInt`, numeric subtraction, or a client-side survivor sort on ids.

Keep export strings as strings. Do not parse Notes. Do not derive group identity from name/type/stats.

Prefer a reusable group-view model whose shape can later accept #110's group kind without a second renderer, but do not introduce speculative same-stat behaviour.

## 3. Implement whole-group filtering as a pure function

Add a pure group filter/helper that accepts the authoritative group list and presentation query, then returns **whole original groups**.

Required matching:

- text: case-insensitive item name OR exact substring match against any member id;
- class: `guardian_class`;
- slot: `type`;
- archetype: `item_archetype`;
- tuning: `tuning_mod_slot`.

Rules:

- never filter `group.members`;
- do not search Notes/proposal reasons to broaden membership;
- build filter option counts from groups, not members;
- preserve backend group ordering in the filtered result;
- use prototype-safe maps for values such as `__proto__`, `constructor`, or `toString`;
- keep free-text search valid even when it currently yields zero groups;
- clear a categorical value during report replacement only when that value no longer exists in the new authoritative group set.

Expose `showing N of M groups` from filtered count versus total exact-group count.

## 4. Implement the settled group-header stat presentation without changing schema

Create a pure display helper for the six supplied base stats.

For a tier-5 group, only when the supplied values unambiguously contain one 30, one 25 and one 20 with the other three equal to 0:

- display the item archetype prominently as text-labelled content/badge;
- label the 30 stat **Primary**, the 25 stat **Secondary**, and the 20 stat **Tertiary**;
- collapse the three zero base stats to one muted explanatory line rather than three empty-looking columns.

This is a presentation projection only. Do **not** maintain a second twelve-archetype mapping table in JavaScript and do not derive membership from these labels.

If the group is not tier 5 or the 30/25/20/0/0/0 shape is not unambiguous, fall back to an honest six-stat display. Never guess a tertiary name.

Always render `tuning_mod_slot` from the backend as a distinct text-labelled field next to the stat summary, including `none/unknown`. Seasonal Mod, Holofoil and Spirit signature must be shown as inert text where applicable. Do not use colour as the only distinction.

## 5. Build one reusable group component and exact-member matrix

Within `review_ui.js`, implement the duplicate-group DOM through the existing safe `el()`/`textContent` style rather than `innerHTML`.

### Group header

Show at least:

- Name;
- type/slot;
- Guardian class;
- tier;
- hash as an opaque string;
- item archetype;
- stat summary from step 4;
- always-visible Tuning Mod Slot;
- Spirit signature when non-empty;
- Seasonal Mod/Holofoil when non-empty/meaningful.

### Member matrix

Use members as columns, preserving backend order. Make the member heading identify:

- the full opaque instance id (as text, never numeric);
- location;
- role/status from backend disposition: Preferred survivor, Retained protected, Proposed junk, or Proposed review.

Rows should expose the settled comparison ladder without recomputation:

- hard protection/state (from structured `protection_level`/reason; do not infer survivor outcome from it);
- In loadout;
- Locked;
- Masterwork Tier;
- Power;
- Verdict/read-only status.

The preferred survivor must be first because the backend already put it first; do not move it. Additional retained members remain after it; proposed members remain in backend order.

Do not manufacture a “winner decided here” marker. The group lacks a structured deciding-rank field.

## 6. Reuse the existing verdict-control presentation seam

Proposal members are the only duplicate members that may show verdict controls.

Refactor/extract the **presentation-only** verdict button builder from the existing proposal table if needed so both Proposals rows and duplicate proposal cells share:

- Approve;
- Veto;
- Unset;
- `aria-pressed` state;
- disabled/frozen handling;
- acknowledged repaint semantics;
- keyboard/focus conventions where applicable.

Survivor and retained members render explicit read-only text, not disabled fake verdict buttons.

The duplicate component must receive callbacks from `review_server.js`; it must not call `fetch` itself. A duplicate member control must invoke the existing single-id `toggleVerdict()` / `mutateVerdicts()` path. Do not add a group mutation payload or optimistic local verdict.

Add a duplicate-member DOM registry keyed safely by member id if needed so an authoritative acknowledgement can repaint the duplicate cell **in place**. Existing Proposals row repaint must continue to work. When one view records a verdict, switching to the other must show the same `state.verdicts` truth.

## 7. Add presentation-only Armor duplicates state to the server adapter

Extend `createState()` only with presentation fields needed by the new surface, for example:

- current review surface: `proposals` or `armor-duplicates`;
- current authoritative exact-group presentation list;
- duplicate query `{text, guardianClass, type, itemArchetype, tuningModSlot}`;
- duplicate member/control registry if required.

Do not add anything to the server envelope or request payload.

During `applySessionEnvelope()`:

1. continue building Proposals items exactly as today;
2. build the exact-group presentation list through the shared pure helper;
3. calculate the new set of valid exact group ids and categorical values;
4. preserve the duplicate surface if groups still exist; if the active duplicate surface loses all exact groups, fall back to Proposals and record a presentation invalidation;
5. preserve duplicate search text;
6. preserve categorical duplicate filters only while their value still exists, otherwise clear just that filter and record it as invalidated;
7. preserve existing Proposals expanded/search/sort state under its current rules;
8. do not treat survivor/retained member ids as proposal decision ids when reconciling existing row expansion.

A rejected replacement upload must not call `adopt()` and therefore must not alter the current surface/filter/DOM state. A successful replacement may clear only state that is no longer meaningful against the new exact-group set.

## 8. Add the accessible view selector and separate duplicate filters

Update `review_server.html`/`review_server.js` so the user can select:

- **Proposals**;
- **Armor duplicates**.

Use semantic buttons/radio-style controls with an accessible group label and explicit selected state (`aria-pressed` or an equally clear established pattern). Do not overload the existing grouped/flat proposal selector.

When no authoritative exact groups exist, the Armor duplicates option must not be selectable (hide it or render it explicitly disabled). If groups disappear on reconciliation while that surface is active, return to Proposals truthfully.

Keep Proposals filters/bulk actions scoped to Proposals. The duplicate surface gets only its own narrowing controls (search, class, slot, archetype, tuning). **Do not expose the existing “Approve/Veto/Unset all shown” controls as duplicate-group actions.**

Do not add the #110 **All / Exact / Same stats** group-kind segmented control yet. The agreed design says that control appears only when more than one group kind is present; #102 renders exact groups only.

## 9. Render duplicate surface and preserve focus/state through acknowledgements

Add a dedicated duplicate host/panel and rendering function.

Required behaviour:

- duplicate filters show whole groups only;
- the “showing N of M groups” count updates with filtering;
- switching Proposals ↔ Armor duplicates does not destroy either surface's still-valid query/expansion state;
- an acknowledged verdict from a duplicate member repaints both the duplicate member and any existing Proposals representation from `state.verdicts` without optimistic state;
- an acknowledged verdict from Proposals is visible when returning to duplicates;
- same-report/stale-verdict reconciliation should repaint in place where possible rather than rebuild focused controls;
- a report rebuild should restore focus to the same static view/filter control when that control still exists; otherwise allow normal focus fallback rather than inventing a stale target;
- finalised state leaves the duplicate data readable and routes control disabling through the existing mutation gate;
- reset returns to upload-ready/Proposals presentation with no stale group controls;
- closed session behaviour is unchanged.

Do not modify the HTTP failure/retry/finalisation/reset/shutdown algorithms to achieve presentation state preservation.

## 10. Add responsive/accessibility styling using the existing CSS system

Extend `review.css` rather than adding an asset.

Requirements:

- use existing colour variables and visible-focus treatment;
- text labels remain meaningful without colour;
- group header hierarchy is readable in light and dark modes;
- matrix is wrapped in contained horizontal scrolling rather than overflowing the page;
- at the existing narrow breakpoint, controls stack and the group summary remains readable;
- do not add fixed pixel assumptions that make member columns inaccessible on a ~390 px viewport;
- respect current font/system conventions.

No screenshot baseline or additional CSS framework.

## 11. Add focused fake fixture data only if needed

Prefer a dedicated small `tests/fixtures/armor_duplicates_ui.csv` over mutating broad rule fixtures if that keeps the browser scenario precise.

A useful fixture shape is one exact Legendary tier-5 group with:

- populated `Archetype` and a real 30/25/20/0/0/0 fake stat distribution;
- one shared recognised Tuning Stat;
- one preferred hard-protected survivor;
- one additional hard-protected/retained member;
- one otherwise-unprotected losing member that receives the existing junk proposal;
- fake ids/hashes/names only.

This proves survivor, retained and proposal states in one complete group. It must not contain any real vault row/name/hash/id.

Do not change a rule merely to make the fixture produce the desired group; shape the fake fixture to the existing rule contract.

## 12. Add Node/pure presentation coverage

Extend `tests/test_review_ui_js.py` with focused behavioural assertions proving at least:

1. exact groups are read from the snapshot and group/member order is preserved;
2. group id/hash/member ids remain strings, including a 64-bit-sized id and leading-zero/non-digit/prototype-shaped ids where practical;
3. preferred survivor, additional retained and proposal statuses render truthfully;
4. only proposal members receive interactive verdict controls;
5. shared Tuning Mod Slot is visible in the always-visible group summary, including `none/unknown` coverage;
6. tier-5 30/25/20 roles render correctly and the three zero base stats are collapsed;
7. a non-conforming/non-tier-5 shape falls back to all six values rather than guessing;
8. search by name and member id works;
9. Class/slot/archetype/tuning filters select a whole group and never remove members;
10. `showing N of M groups` inputs/counts remain correct;
11. hostile names/archetypes/locations/Spirit/mod/holofoil values remain text nodes with no injected `img`, `script`, `b`, event handler or HTML node;
12. prototype-shaped group ids/filter values cannot pollute `Object.prototype`;
13. no duplicate-group helper converts/sorts opaque ids numerically;
14. the renderer seam remains generic enough for #110 without actually reading/rendering `same_stat_groups`.

Prefer behavioural DOM assertions over source-string checks.

## 13. Add server-adapter/state-reconciliation coverage

Extend `tests/test_server_ui_js.py` to prove:

- exact groups are adopted from an authoritative envelope without changing server/session fields;
- active Armor duplicates surface survives a same-group envelope refresh;
- duplicate search and valid categorical filters survive refresh/reconciliation;
- a categorical filter clears only when its value is absent from the replacement group set;
- active duplicate surface falls back to Proposals only when no exact groups remain;
- existing Proposals expanded/search/sort state survives view switching and remains governed by existing reconciliation;
- duplicate verdict controls are disabled by the same mutation/finalised gate as Proposals;
- same-report acknowledged verdict repaint updates duplicate controls without rebuilding the group DOM;
- proposal and duplicate views read the same authoritative verdict map;
- rejected-upload logic does not adopt/reconcile away local presentation state;
- prototype-shaped group/member ids remain safe.

Do not create a fake HTTP protocol in the test; test the adapter seam that already exists.

## 14. Add exactly one focused Playwright test

Add **one and only one** new `@pytest.mark.browser` test in `tests/test_server_browser.py`, for example:

```text
test_armor_duplicates_view_uses_authoritative_group_and_verdicts
```

Through the real packaged server UI it must, in one scenario:

1. authenticate through the bootstrap URL;
2. upload the fake armour export;
3. wait for the existing Accepted/report conditions — no fixed sleeps;
4. open **Armor duplicates**;
5. assert the group header shows expected name/type/class/archetype/stat-role summary and the always-visible Tuning Mod Slot;
6. assert preferred survivor plus **every** matching member is visible, including the retained-protected member;
7. assert survivor/retained members are read-only and the proposal member has verdict controls;
8. record one loser verdict and wait for server acknowledgement;
9. assert the duplicate member reflects the authoritative verdict;
10. switch to **Proposals** and assert the same member reflects the same authoritative verdict there;
11. optionally switch back to confirm the duplicate view/search state remains intact, keeping all assertions within this single test.

Use Playwright locators/`expect` waits only. No `sleep`, retry plugin, screenshot baseline, or second #102 browser test.

The existing browser job already discovers it via `-m browser`, so `.github/workflows/ci.yml` should remain unchanged.

## 15. Add the required domain/reference documentation

Create `docs/armor-archetypes.md` from the **reviewed draft in issue #102's comment**. Treat that draft as the source of truth. Preserve its distinction between:

- Destiny armour archetypes from DIM's `Archetype` column; and
- vault-cleaner's configurable `[armor.archetypes.*]` scoring profiles.

Preserve the explicit note that the owner's Health-led PvE preference is context, not a rule.

Update `AGENTS.md` using the issue comment's reviewed gotcha change:

- 30+25+20 = 75 base;
- only three base stats carry information on tier-5 armour;
- link to `docs/armor-archetypes.md`;
- add the `Archetype` terminology-collision warning.

Do not turn that domain documentation into new behaviour.

## 16. Update README and browser verification docs

### README

Update the browser-review section so it describes the two views and the exact-group purpose. Remove/replace the now-stale sentence saying the Armor duplicates view is merely tracked separately. State that:

- Proposals remains the action-oriented list;
- Armor duplicates presents complete authoritative exact armour groups;
- only proposal members can receive verdicts;
- tuning is always visible and exact groups do not combine differently tuned pieces.

Do not document #110 as already shipped.

### `docs/browser-verification.md`

Add a #102 focused checklist covering:

- view selector availability/no-group behaviour;
- complete group membership and labels;
- always-visible archetype/stat/tuning summary;
- whole-group search/class/slot/archetype/tuning filters and N/M count;
- proposal-member verdict acknowledgement reflected in both views;
- read-only survivor/retained members;
- keyboard/focus behaviour;
- finalised readable/frozen behaviour;
- successful replacement/reset reconciliation and rejected replacement preservation;
- light/dark and ~390 px narrow layout;
- hostile text remains inert.

Record the actual manual run environment/results after verification. Keep the existing #104 and #90 records.

## 17. Update `WORKLOG.md`

Add a dated #102 entry recording:

- the new Armor duplicates view and its component/state seam;
- that it consumes #101 exact groups without reconstructing rule truth;
- whole-group filter behaviour;
- proposal-only acknowledged verdict reuse;
- stat-role display and honest fallback;
- docs/AGENTS correction;
- tests and manual verification performed;
- non-editable wheel proof result;
- browser-suite timing impact (record the new test duration and/or total marked browser run using pytest durations/output);
- explicit confirmation that schema v2/ruleset v4, Python decisions, server protocol/lifecycle, runtime dependencies and CI topology were unchanged;
- any remaining limitation (for example the pre-existing focus blur noted under #104, if still observed rather than fixed outside scope).

---

# Required automated tests

The completed implementation must prove:

1. **Happy path:** an exact group renders with survivor, retained and proposed members, metadata/stat/tuning header and member matrix.
2. **Authoritative contract:** client preserves backend group/member order and does not reconstruct membership/survivor/disposition.
3. **Whole-group filtering:** every supported filter shows/hides complete groups only.
4. **No-group state:** duplicate view is unavailable and an obsolete active duplicate surface reconciles back to Proposals.
5. **Verdict acknowledgement:** only proposal members can mutate; existing single-id server path is used; both views reflect acknowledged state.
6. **Rejected/stale/replacement reconciliation:** still-valid presentation state survives and invalid state alone is cleared.
7. **Finalised state:** duplicate data remains readable while controls are frozen by existing lifecycle state.
8. **Opaque ids:** large, leading-zero, non-digit and prototype-shaped strings remain strings; no numeric conversion.
9. **Hostile input:** export-derived strings render as text only.
10. **Tier-5 display:** 30/25/20 roles and zero collapse; non-conforming fallback is honest.
11. **Tuning:** all text presentation comes from structured `tuning_mod_slot`; at least recognised and `none/unknown` states are covered.
12. **Regression:** ordinary Proposals filtering/sorting/grouping/details/verdict controls and #104 Tuning Mod Slot presentation continue to pass.
13. **Real browser:** exactly one new #102 Playwright test covers the complete group and cross-view acknowledged verdict scenario.
14. **Packaging:** wheel-installed root/assets still load from the installed package with no checkout fallback.

No snapshot golden/schema test should change as a consequence of #102.

---

# Manual verification

Use fake fixture data only and `--no-wishlists`.

At minimum, record in `docs/browser-verification.md` and Luna's handoff:

- desktop light mode;
- desktop dark mode;
- narrow viewport around 390×844;
- keyboard-only navigation/focus through view selector, filters and a proposal member's verdict controls;
- complete member matrix remains horizontally contained on narrow layout;
- view switch preserves search/filter/proposal expansion state where still valid;
- acknowledged verdict is reflected in both views;
- finalise leaves Armor duplicates readable/frozen;
- Reset returns to upload-ready Proposals;
- a successful replacement that retains a group keeps valid duplicate state, while a removed group invalidates only its categorical/group surface state;
- a deliberately rejected replacement upload leaves current duplicate view/search/filter state untouched;
- hostile text is visibly literal/inert.

Do not use real vault exports for screenshots or manual checks.

---

# Exact validation commands

Run focused presentation/adapter tests first:

```bash
.venv/bin/pytest -q tests/test_review_ui_js.py tests/test_server_ui_js.py
```

Run the new focused browser test explicitly (replace the test name if the final name differs):

```bash
VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q \
  tests/test_server_browser.py::test_armor_duplicates_view_uses_authoritative_group_and_verdicts \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results
```

Run the complete dedicated browser gate exactly as CI does, with durations for the worklog timing note:

```bash
VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results \
  --durations=10
```

Run the non-editable wheel proof because packaged UI assets changed:

```bash
.venv/bin/python scripts/check_wheel_install.py
```

Run the repository gates:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git status --short
git ls-files data/
```

`git ls-files data/` must print nothing.

Before handoff, inspect the implementation diff and confirm the forbidden semantic files are untouched:

```bash
git diff --name-only origin/main...HEAD
git diff --stat origin/main...HEAD
```

Do **not** regenerate `tests/fixtures/report_snapshot_v2.json` for this presentation ticket. If the implementation appears to require a snapshot change, stop/escalate.

---

# Luna completion gate

Luna may hand the branch to Sol only when all of the following are true:

- implementation branch started from the latest `main` and the base SHA is recorded;
- every in-scope #102 acceptance criterion is satisfied;
- exact groups and members are consumed in backend order with no JS duplicate algorithm;
- no rule/report/schema/version/server-protocol/lifecycle/persistence/auth changes were made;
- no same-stat rendering from #110 was added;
- only proposal members have verdict controls and the existing acknowledged mutation path is used;
- both views reflect the same authoritative verdict map;
- group filters never create a partial group;
- ids/hashes remain opaque strings and hostile values remain inert text;
- exactly one new #102 Playwright test was added;
- the existing Ubuntu browser job needs no topology/retry change;
- wheel proof passes;
- `docs/armor-archetypes.md`, `AGENTS.md`, README, browser verification and `WORKLOG.md` are updated;
- `WORKLOG.md` records browser timing impact and any remaining limitation;
- Ruff, full pytest, full Chromium marker run, diff check and privacy/hygiene checks pass;
- implementation branch is committed and pushed;
- **no pull request has been opened**.

Luna's handoff to Sol must contain:

- implementation branch name;
- base `main` SHA;
- commit SHA(s);
- files added/changed;
- concise behaviour summary;
- tests added/changed;
- exact focused/full/browser/wheel validation results;
- manual verification results and environment;
- browser timing impact;
- known risks/limitations;
- any deviation from this plan, with reason;
- confirmation that no PR was raised.

---

# Orchestrating Sol high review prompt

Review the completed Luna xhigh implementation for issue `#102` in `tonym999/vault-cleaner`.

The authoritative implementation plan is stored on branch `handoff/issue-102-luna-plan` at:

```text
handoffs/issue-102-luna-xhigh-implementation-plan.md
```

Do **not** raise a PR yet.

## 1. Plan-conformance review

Compare the actual implementation diff against issue #102, its reviewed comment/design, and the handoff plan. Verify every in-scope requirement, especially:

- accessible Proposals / Armor duplicates selection;
- duplicate view unavailable when no exact groups exist;
- exclusive consumption of `section.armor.exact_duplicate_groups`;
- backend group/member order preserved without browser sorting/reconstruction;
- complete group rendering: preferred survivor, all retained copies, all proposed copies;
- group header: name/type/class/tier/hash/archetype, 30/25/20 tier-5 display with honest fallback, always-visible Tuning Mod Slot, Spirit/mod/holofoil as applicable;
- member matrix and truthful disposition labels;
- only proposal members get verdict controls;
- duplicate verdicts use the existing acknowledged single-id server path with no optimistic or group mutation;
- Proposals and Armor duplicates read the same authoritative verdict state after acknowledgement;
- whole-group filters and N/M count;
- still-valid view/search/filter/Proposals expansion/focus conventions survive acknowledgement/reconciliation/rejected replacement, with only invalid state discarded;
- finalised session remains readable/frozen;
- hostile/prototype-shaped input safety and opaque string ids;
- exactly one new #102 Playwright test;
- existing dedicated browser job remains separate from the core OS matrix, with no retries/fixed sleeps;
- required docs and `WORKLOG.md` updates;
- no accidental #110 same-stat implementation.

Apply the ticket's algorithmic scope rule mechanically to every changed file. A change in a normally-unchanged Python rule/report/server semantic file, snapshot golden/version, protocol/lifecycle/persistence/auth path, runtime dependency, or CI topology requires a specific justified finding or replan — not silent acceptance.

## 2. Engineering review

Review the implementation itself for:

1. correctness and complete-group truthfulness;
2. maintainability and whether #110 can reuse the group component without a fork;
3. unnecessary complexity or duplicated DOM/verdict logic;
4. unsafe data-keyed plain objects/prototype pollution;
5. any `Number`/`parseInt`/numeric coercion of ids/hashes;
6. any browser reconstruction of rule truth or member ordering;
7. partial-group filtering;
8. optimistic verdict state or hidden second mutation path;
9. focus/state loss on acknowledged same-report updates or stale reconciliation;
10. finalised controls accidentally remaining mutable;
11. unsafe HTML/attribute/selector construction from export strings;
12. tier-5 display misrepresenting non-conforming/legacy data;
13. CSS overflow/accessibility problems in narrow/light/dark modes;
14. missing regression coverage;
15. stale README/browser docs/AGENTS/WORKLOG text;
16. scope creep into #109/#110 or architecture/protocol work.

Be willing to challenge the plan if implementation proves an assumption false, but do not fix an out-of-scope contract problem inside #102.

## 3. Independent validation

Do not rely only on Luna's summary. Re-run or independently verify at least:

```bash
.venv/bin/pytest -q tests/test_review_ui_js.py tests/test_server_ui_js.py
VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser \
  --browser chromium \
  --tracing=retain-on-failure \
  --screenshot=only-on-failure \
  --output=test-results \
  --durations=10
.venv/bin/python scripts/check_wheel_install.py
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
git diff --check
git ls-files data/
```

Confirm the marked browser suite includes exactly one newly-added #102 browser test and that no real vault data is tracked.

## Review outcome

If findings exist:

- identify each precisely with file/behaviour;
- explain why it violates the issue/plan or engineering safety;
- specify the required correction;
- require a focused regression where appropriate;
- have Luna fix the **same implementation branch**;
- rerun affected tests plus the full completion gate;
- review again.

Because #102 uses the **standard Sol high review path**, mark the branch `READY FOR PR` only when this review is clean. Do not open the PR unless the owner explicitly asks.

---

# Reusable Luna xhigh execution prompt

Implement issue `#102` in `tonym999/vault-cleaner` using the Sol implementation plan stored on branch `handoff/issue-102-luna-plan` at:

```text
handoffs/issue-102-luna-xhigh-implementation-plan.md
```

Read the plan from that handoff branch, but create your **implementation branch from the latest `main`**, not from the handoff branch. Suggested implementation branch:

```text
issue-102-armor-duplicates-view
```

Before changing code, read issue #102 and its full comment/design, `AGENTS.md`, `PLAN.md`, the relevant recent `WORKLOG.md` entries, completed dependencies #101/#104, follow-on #110, and the current relevant UI/tests/docs. Confirm the current `main` still matches the handoff assumptions.

Follow the plan as the primary execution contract. In particular:

- consume #101's authoritative `exact_duplicate_groups`; do not reconstruct group truth in JavaScript;
- preserve backend group/member order;
- keep ids/hashes opaque strings;
- render all export text with safe DOM text APIs;
- use the existing acknowledged single-member verdict path only for members that already have proposals;
- preserve still-valid local presentation/focus state without changing server stale/finalisation/reset/upload/lifecycle semantics;
- keep same-stat groups for #110 out of scope;
- do not alter rules/report/schema/version/server protocol/persistence/auth/runtime dependencies;
- add behavioural Node/adapter tests and exactly one new focused Playwright test;
- create the reviewed armour-archetypes domain doc and required AGENTS/README/browser-verification/WORKLOG updates;
- run the exact focused, Chromium, wheel, Ruff, full pytest, diff and privacy gates in the plan;
- use fake fixtures only;
- commit and push the implementation branch;
- **do not open a pull request**.

If any proposed change fails the ticket-specific algorithmic scope rule or requires a stop/escalation file/behaviour, stop and return the issue to Sol with the concrete contract problem rather than expanding scope.

When complete, provide a concise structured handoff containing:

- branch;
- base `main` SHA;
- commit SHA(s);
- files changed/added;
- implementation summary;
- tests added/changed;
- exact validation results;
- browser/wheel results and browser timing impact;
- manual verification results;
- unresolved concerns/limitations;
- deviations from plan;
- confirmation that no PR was raised.

---

# Ticket-specific review decision

**Review path:** `standard Sol high review`

**Reason:** #102 consumes already-landed authoritative exact-group and tuning contracts and is constrained to the permanent browser presentation layer plus tests/documentation. It must not change architecture, protocol, persistence, concurrency, stale-state semantics, lifecycle, security boundaries, rule decisions, or schema versions. Luna xhigh is warranted for the breadth and state-sensitive UI/test work, but a clean implementation remains bounded/mechanical enough for the standard Sol high review path.