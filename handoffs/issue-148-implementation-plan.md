# Issue #148 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#148 — Child 2a: make weapon loadout membership clear in review, and require the Loadouts column`

**Milestone:** none — deliberate. [#140](https://github.com/tonym999/vault-cleaner/issues/140)'s tracking section records that no existing milestone covers this initiative and that a one-off milestone must not be created without a planning decision.

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Implementation model selected:** `claude-sonnet-5` with native effort `high` (justified below)

**Plan baseline:** `main` at `381e8de938f3cd63b20db029376514ab3ac2a998` (2026-09-12)

**Allocated implementation branch:** `feat/issue-148-loadout-visibility`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

> **Premise reversal, 2026-09-12.** This plan originally specified a HARD rail suppressing every weapon in a saved DIM loadout, per [docs/aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md) §8 item 4. The owner reversed that decision during planning: **a weapon in a loadout may be recommended**; the requirement is that membership is *clear*. §8 item 4 is superseded. The superseded analysis is preserved at the end of this document so the next agent does not re-derive it.

## Objective

Two things, neither of which changes a single decision:

1. **Tell the truth loudly.** `Loadouts` is not in the weapons required schema, and the one place that reads it for weapons uses `.get("Loadouts", "")`. An export missing the header therefore loads cleanly and renders *every* weapon as not-in-a-loadout. That is the actual defect.
2. **Put the fact where the decision is made.** The in-loadout flag already exists end to end, but it renders only inside a per-item detail row you must expand, as one comma-joined entry in a `flags` line. Promote it to a row badge and a filter facet, and hand the owner DIM's own cross-check queries as copyable text.

## Context & Measurement

All references measured on the plan baseline.

### The flag is already plumbed end to end

| Stage | Location | State |
|---|---|---|
| Field | [report_run.py:101](../src/vault_cleaner/report_run.py#L101) | `in_loadout: bool` on `ReportDecision` |
| Populate | [report_run.py:317](../src/vault_cleaner/report_run.py#L317) | `bool(str(row.get("Loadouts", "")).strip())` |
| Snapshot | [report_run.py:422](../src/vault_cleaner/report_run.py#L422) | `[asdict(decision) for decision in section.decisions]` — carried automatically |
| Read | [review_ui.js:111](../src/vault_cleaner/ui/review_ui.js#L111) | `inLoadout: decision.in_loadout === true` |
| Render | [review_ui.js:874](../src/vault_cleaner/ui/review_ui.js#L874) | `item.inLoadout ? "in a loadout" : null`, joined into the detail row's `flags` line |

So no new field, no snapshot schema change, and no `SNAPSHOT_SCHEMA_VERSION` bump. The work is presentation plus one schema constant.

### The schema gap

[parse.py:42-44](../src/vault_cleaner/parse.py#L42-L44) omits `Loadouts`, while [`REQUIRED_GHOST_COLUMNS`](../src/vault_cleaner/parse.py#L47) and [`REQUIRED_ARMOR_COLUMNS`](../src/vault_cleaner/parse.py#L71-L76) both require it. Weapons are the outlier. Both weapon entry points — [`load_weapons`](../src/vault_cleaner/parse.py#L192-L203) and [`load_weapons_bytes`](../src/vault_cleaner/parse.py#L206-L215), the latter being the review server's upload path — share the frozenset, so one edit covers both.

### The UI surface is two modules, one page

[review_server.html:76-77](../src/vault_cleaner/ui/review_server.html#L76-L77) loads both scripts; [review_ui.js:1-12](../src/vault_cleaner/ui/review_ui.js#L1-L12) is the shared pure-presentation module and [review_server.js:1-12](../src/vault_cleaner/ui/review_server.js#L1-L12) the server shell that consumes it. This is one surface split by responsibility, not two surfaces to keep in sync.

Filter facets are an established pattern, and the new one slots into it exactly:

| Concern | Location |
|---|---|
| Predicate | [review_ui.js:201-217](../src/vault_cleaner/ui/review_ui.js#L201-L217) (`filterItems`) |
| Helper precedent | [review_ui.js:194-199](../src/vault_cleaner/ui/review_ui.js#L194-L199) (`matchesProtection`) |
| Query defaults | [review_server.js:76-77](../src/vault_cleaner/ui/review_server.js#L76-L77) |
| Refresh reconciliation | [review_server.js:324](../src/vault_cleaner/ui/review_server.js#L324), inside `applySessionEnvelope` ([review_server.js:291](../src/vault_cleaner/ui/review_server.js#L291)) |
| Staleness predicate | [review_server.js:193-198](../src/vault_cleaner/ui/review_server.js#L193-L198) (`valueStillExists`) |
| Control construction | [review_server.js:1011-1018](../src/vault_cleaner/ui/review_server.js#L1011-L1018), inside `renderControls` ([review_server.js:901](../src/vault_cleaner/ui/review_server.js#L901)) |
| Reset | [review_server.js:1039-1042](../src/vault_cleaner/ui/review_server.js#L1039-L1042) — clears **every** `state.query` key generically; needs no per-facet edit |

There is **no** clipboard helper anywhere in `src/vault_cleaner/ui/` (`grep -rn "clipboard\|execCommand" src/vault_cleaner/ui/*.js` returns nothing), so copy support is new code — see the decision under *Static DIM query panel*.

### DIM's filters, verified from source

Not from the wiki, which fails to render. From [loadouts.ts](https://github.com/DestinyItemManager/DIM/blob/master/src/app/search/items/search-filters/loadouts.ts), [item-infos.ts](https://github.com/DestinyItemManager/DIM/blob/master/src/app/search/items/search-filters/item-infos.ts) and [freeform.ts](https://github.com/DestinyItemManager/DIM/blob/master/src/app/search/items/search-filters/freeform.ts):

- `is:inloadout` / `not:inloadout` — boolean membership.
- `inloadout:>=2` — range over how many loadouts contain the item.
- `inloadout:"raid"` — substring match on loadout name; a `#tag` value also matches hashtags in the loadout's notes.
- `is:indimloadout` / `is:iningameloadout` — DIM versus in-game loadouts.
- `tag:junk` — `format: 'query'`, suggestions drawn from `itemTagSelectorList`.
- `notes:` — freeform substring over item notes, with autocomplete fed by known notes-hashtags, so vault-cleaner's `#vc-` markers already appear there.

### Why the flag matters (cited from #142, qualitatively)

[#142](https://github.com/tonym999/vault-cleaner/issues/142)'s owner-authorized real-export measurement ([docs/aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md) §11) found that a substantial share of the owner's weapons sit in saved DIM loadouts, and that many of those are otherwise unprotected. Those are exactly the proposals this ticket makes legible rather than suppresses.

This plan deliberately does **not** reproduce §11's exact figures. Under the per-ticket rule in [AGENTS.md](../AGENTS.md) (amended by #145), real-export findings are committed under an authorization recorded for a specific ticket; that authorization was recorded for #142, not for #148. Read §11 for the numbers.

## Dependencies and assumptions

1. **#142 is closed and merged**; its §8 item 4 is superseded by the owner reversal recorded above. The implementer must not restore a rail on the strength of that section.
2. **No staleness otherwise.** Every reference above was re-measured against the baseline.
3. **#145 (merged via PR #147)** amended `AGENTS.md`: measuring a real export is expected, and aggregate findings may be committed to `docs/` under per-ticket owner authorization. It does not change this ticket's scope. No real-export measurement is authorized for #148, none is needed, and this plan republishes no real-export figure: every measurement in it was taken on the repository or on synthetic fixtures, and #142's findings are cited qualitatively with a pointer to §11. Fixtures stay synthetic under the same amendment. Loadout names remain deferred; a later pass that carries them would be the natural ticket to seek that authorization and measure the `Loadouts` cell format.
4. **Boolean only.** Loadout *names* are deliberately excluded. The real export's `Loadouts` cell format is unmeasured and the fixtures disagree — `PvE Build` and `Raid` in `armor_dupes.csv`, `Raid Titan` in `armor_same_stat_four_ui.csv`, but `00001:PvP Build` in `ghosts_cleanup.csv`. `AGENTS.md` requires measuring the real export before designing a rule, so name parsing waits for a measured format.
5. **No generated queries.** Per-selection `id:` generation belongs to [#117](https://github.com/tonym999/vault-cleaner/issues/117), and #140 forbids repurposing it for weapons. Static strings only.
6. **Decisions must not move.** This ticket changes no rule. Every committed fixture's decisions, notes, tags and golden bytes stay identical, and `RULESET_VERSION` stays `4`.

## Proposed Plan & Scope

### Schema

#### [MODIFY] [parse.py:42-44](../src/vault_cleaner/parse.py#L42-L44)

```python
REQUIRED_WEAPON_COLUMNS = REQUIRED_BASE_COLUMNS | {
    "Type", "Ammo", "Crafted", "Crafted Level", "Perks 0", "Loadouts",
}
```

Extend the adjacent comment in the existing voice: `Loadouts` is required because the review surface presents loadout membership as fact, and a missing column would render every weapon as not-in-a-loadout rather than as unknown.

Known consequence, stated in the issue: a weapons export predating DIM's `Loadouts` column is now rejected. Intended — `AGENTS.md` requires schema checks to fail loudly — and already true of the ghost and armor schemas.

### Review UI — row badge

#### [MODIFY] [review_ui.js:940-950](../src/vault_cleaner/ui/review_ui.js#L940-L950)

Add a badge to the proposal row when `item.inLoadout` is true, **inside the existing action cell** beside the `junk` / `review` badge ([review_ui.js:944-947](../src/vault_cleaner/ui/review_ui.js#L944-L947)).

Verbatim copy: **`in loadout`**.

Deliberately *not* a new column. The proposal row is a fixed cell sequence (name, id, kind, class, location, action, reason, tuning slot, protection), and `detailRow(item, detailId, columns)` spans the detail row with `colspan: String(columns)` ([review_ui.js:876-879](../src/vault_cleaner/ui/review_ui.js#L876-L879)). Adding a column means updating the header, every row, and that count in step — disproportionate for one flag, and an easy way to produce a misaligned detail row.

Leave the detail-row `flags` line at [review_ui.js:874](../src/vault_cleaner/ui/review_ui.js#L874) exactly as it is. It is not wrong, it is just insufficient, and removing it would lose the grouping with `locked` / `equipped`.

#### [MODIFY] [review.css:163-168](../src/vault_cleaner/ui/review.css#L163-L168)

Add a modifier class beside `.badge.junk` / `.badge.review` ([review.css:163-168](../src/vault_cleaner/ui/review.css#L163-L168)). The bare `.badge` rule is already a neutral outline, so the new class should stay close to it. Do **not** reuse `.badge.junk`'s `--junk` colour: loadout membership is context, not severity. Note that [docs/evidence/issue-113/count-label-inventory.md](../docs/evidence/issue-113/count-label-inventory.md) already records "same fact reads as different severity on the two surfaces" as a known UI defect class — do not add another instance of it.

### Review UI — filter facet

#### [MODIFY] [review_ui.js:194-217](../src/vault_cleaner/ui/review_ui.js#L194-L217)

Add a `matchesLoadout(item, mode)` helper modelled on `matchesProtection`, and one clause in `filterItems`:

```javascript
if (!matchesLoadout(item, q.loadout)) return false;
```

Modes: `""` (no filter), `"in"` (`item.inLoadout === true`), `"out"` (`item.inLoadout !== true`).

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L76-L77)

Three coordinated edits:

- add `loadout: ""` to the query defaults at [review_server.js:76-77](../src/vault_cleaner/ui/review_server.js#L76-L77);
- add `"loadout"` to the **report-refresh invalidation list** at [review_server.js:324](../src/vault_cleaner/ui/review_server.js#L324);
- add the select control next to the existing protection select at [review_server.js:1014-1018](../src/vault_cleaner/ui/review_server.js#L1014-L1018), inside `renderControls`.

Verbatim control copy — label **`Loadout`**, options **`any loadout state`** (default), **`in a loadout`**, **`not in a loadout`**.

**What the invalidation list actually does.** [review_server.js:324](../src/vault_cleaner/ui/review_server.js#L324) is not a facet registry and has nothing to do with the reset button. It lives inside `applySessionEnvelope` ([review_server.js:291](../src/vault_cleaner/ui/review_server.js#L291)): when a refreshed report arrives, each listed facet whose selected value no longer matches any item is cleared and recorded in `invalidated`, and `adopt` ([review_server.js:797-805](../src/vault_cleaner/ui/review_server.js#L797-L805)) then resynchronises the live control. Omitting `loadout` leaves a stale selection filtering against items that no longer exist.

The staleness check needs no special-casing: `valueStillExists` ([review_server.js:193-198](../src/vault_cleaner/ui/review_server.js#L193-L198)) builds a single-facet query and delegates to `ui.filterItems`, so it works for any facet `filterItems` understands — exactly as it already does for `protection`, whose `"protected"` / `"unprotected"` modes are no more item-field-shaped than `loadout`'s.

**Reset needs no edit.** The `Reset filters` handler ([review_server.js:1039-1042](../src/vault_cleaner/ui/review_server.js#L1039-L1042)) clears every key in `state.query` generically, so `loadout` is reset for free once the default exists.

Missing the query default leaves a control whose value never initialises; missing the invalidation entry leaves a filter that silently survives a report refresh it should not. Check all four edits in review, and cover the refresh case with the test named below — it is the one behaviour here that no other test would catch.

### Review UI — static DIM query panel

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js) and [review.css](../src/vault_cleaner/ui/review.css)

Render these three queries verbatim, as literal constants — no interpolation, no per-item generation:

```text
tag:junk is:inloadout
notes:#vc-junk is:inloadout
notes:#vc-review is:inloadout
```

Verbatim labels, in this order:

- **`Cross-check in DIM`** — panel heading.
- **`Junk-tagged items in a loadout (after importing the CSV)`** → `tag:junk is:inloadout`
- **`Proposed junk in a loadout (before accepting tags)`** → `notes:#vc-junk is:inloadout`
- **`Review-only proposals in a loadout`** → `notes:#vc-review is:inloadout`

Each query goes in a **read-only `<input>`** (or an equivalent natively selectable control), so select-all-and-copy works with no scripting. A copy button is optional; if one is added it must use `navigator.clipboard.writeText` guarded by a feature check and fall back to selecting the input's text, never failing silently. A button that silently does nothing is worse than no button — this is a stop condition if it cannot be done cleanly.

Rationale to preserve in a comment: these are DIM's own filters, so DIM stays the source of truth for loadout state. Vault-cleaner deliberately does not write loadout membership into generated `Notes` — the CSV is a snapshot and would assert stale membership after a loadout is edited.

### Documentation

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

One dated entry: the premise reversal and why, the "no rail / no note / no version bump" boundary, the DIM-query approach, and the deferral of loadout names and generated queries.

`PLAN.md` needs **no** change: no rail is added, so its rails rule at line 46 remains accurate.

### Tests

#### [MODIFY] [tests/test_parse.py:185-190](../tests/test_parse.py#L185-L190)

Add a `_drop_column("Loadouts")` entry to `INVALID_EXPORT_CASES`, which exercises both `load_weapons` and `load_weapons_bytes` through the existing parametrization.

#### [MODIFY] [tests/test_review_ui_js.py](../tests/test_review_ui_js.py)

- `filterItems` with `loadout: "in"` returns only in-loadout items; with `"out"`, only the rest; with `""`, everything.
- The proposal row renders the `in loadout` badge when `inLoadout` is true and omits it otherwise.
- The detail-row `flags` line is unchanged.

#### [MODIFY] [tests/test_server_ui_js.py](../tests/test_server_ui_js.py)

- The `Loadout` select exists with the three verbatim option labels.
- Its value round-trips into `state.query.loadout`.
- **Refresh reconciliation** through `applySessionEnvelope`: with `loadout` selected, applying an envelope whose items still include a matching item **preserves** the selection; applying one whose items no longer include any matching item **clears** it to `""` and records it in `invalidated`. Both directions — a test that only asserts clearing would pass against a facet that always clears.
- The three DIM query strings render **verbatim**, asserted as exact string equality — a stray space or a smart quote makes them silently wrong in DIM.

#### [MODIFY] [tests/test_server_browser.py](../tests/test_server_browser.py)

One Playwright case: load a report containing at least one in-loadout weapon proposal, assert the badge is visible without expanding the row, set the `Loadout` filter to `in a loadout`, assert the shown count drops to the in-loadout subset, and assert a DIM query input's value equals the expected string.

#### [MODIFY] test fixture for the browser/UI case

No weapon fixture has a non-empty `Loadouts` cell (all 36 rows across four fixtures are empty), so the UI cases need one. **Set `Loadouts` on the row whose `Id` is `7004` in [tests/fixtures/weapons_hostile.csv](../tests/fixtures/weapons_hostile.csv) (stored DIM-quoted as `"""7004"""` in the raw CSV). Do not create a new fixture, and do not choose a different row.**

That file is already the weapons export driving every module that needs this coverage — `test_report_run.py`, `test_review_ui_js.py`, `test_server_browser.py` and `test_server_uploads.py` are its only consumers — and it is **not** the golden's weapons fixture. It holds 10 rows in five same-`Hash` pairs, every `Loadouts` cell empty.

**The row must be a proposal, which is why it is named.** Each pair yields exactly **one** proposal — the exact-dupe loser — and the survivor produces no decision at all. Measured on the plan baseline with `run_report(weapons_path=weapons_hostile.csv, no_wishlists=True)`: 5 weapon decisions, for `7004`, `7006`, `7008`, `7010` and `18446744073709551615`; survivors `7001`, `7003`, `7005`, `7007` and `7009` produce none. A cell on a survivor would put no proposal in a loadout, leaving the badge and filter with nothing to show. With the cell on `7004`, the `in a loadout` filter selects exactly `7004` and `not in a loadout` selects the other four proposals. `18446744073709551615` is avoided because the id-precision tests already use it.

**This placement is also what covers the omitted-`loadout`-key case.** `valueStillExists` issues single-facet queries with no `loadout` key, so `matchesLoadout` must treat a missing or empty mode as no filter. Existing coverage already enforces that once an in-loadout proposal exists: the harness runs `filterItems(items, {})` and `filterItems(items, { action: "junk" })` ([test_review_ui_js.py:96](../tests/test_review_ui_js.py#L96), [test_review_ui_js.py:109](../tests/test_review_ui_js.py#L109)) and asserts them against sets computed independently from the Python run ([test_review_ui_js.py:1186](../tests/test_review_ui_js.py#L1186), [test_review_ui_js.py:1202](../tests/test_review_ui_js.py#L1202)). An implementation that treated a missing key as an active filter would drop `7004` and fail those assertions, so no duplicate test is required — but only because `7004` is a proposal.

Because this ticket adds no rail, a `Loadouts` cell is **decision-neutral by construction**: it can move `in_loadout` and nothing else. No decision, note, tag or golden byte can change as a result, which is why editing a shared fixture in place is safe here and would not be in the rail version of this plan.

**Do not edit `weapons_dupes.csv`** — it builds the golden ([scripts/regenerate_report_snapshot.py:36-38](../scripts/regenerate_report_snapshot.py#L36-L38)), and while a `Loadouts` cell there would not move a decision, it would move the golden's `in_loadout` value in a ticket whose contract is an empty golden diff.

## Mechanical inclusion test

A proposed change is **in scope** if and only if it is one of:

- adding `"Loadouts"` to `REQUIRED_WEAPON_COLUMNS` and its adjacent comment;
- the `in loadout` row badge and its CSS;
- the `matchesLoadout` helper, its `filterItems` clause, and the three coordinated `review_server.js` facet edits;
- the static DIM query panel and its CSS;
- the test additions listed above, plus the single `Loadouts` cell set in `weapons_hostile.csv`;
- the `WORKLOG.md` entry.

Worked examples:

- **IN SCOPE:** a `matchesLoadout` helper beside `matchesProtection`.
- **IN SCOPE:** a read-only input holding `tag:junk is:inloadout`.
- **OUT OF SCOPE:** any rail. `rails.py`, `weapons.py` and `dupes.py` must not appear in the diff at all. If a rail seems necessary, the premise reversal has been misread.
- **OUT OF SCOPE:** appending loadout state to a `#vc-junk:` or `#vc-review:` clause. Deliberately rejected: DIM already knows, and a CSV snapshot would assert stale membership forever.
- **OUT OF SCOPE:** carrying loadout *names* anywhere. The cell format is unmeasured.
- **OUT OF SCOPE:** generating `id:`-based queries from the current selection — that is #117's mechanism.
- **OUT OF SCOPE:** `RULESET_VERSION`, `SNAPSHOT_SCHEMA_VERSION`, or regenerating `report_snapshot_v2.json`.
- **OUT OF SCOPE:** creating a new fixture file, editing `weapons_dupes.csv`, or touching any armor/ghost rule or fixture.

### Stop conditions

Stop implementation and return to the orchestrator if:

- any committed fixture's decisions, notes, tags, or the golden's bytes change;
- `rails.py`, `weapons.py`, `dupes.py`, `report_run.py`'s decision logic, or any armor/ghost module needs editing;
- the badge or facet appears to need a new field on `ReportDecision` or in the snapshot;
- a copy button cannot be made to degrade gracefully without the clipboard API;
- the browser suite cannot be run in the implementer's environment — report it rather than skipping it silently.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **A rail creeps back in.** #142 §8 item 4 still says `Loadouts != '' -> HARD` in the repository, and an implementer reading the design document rather than this plan will implement it. Any hunk in `rails.py` / `weapons.py` / `dupes.py` is a finding.
2. **The facet is wired in three places out of four.** The predicate, the query default, the refresh-invalidation entry and the control are four edits across two files. The invalidation entry is the one that gets missed, because everything looks correct until a report is refreshed — and no existing test refreshes a report with a filter set. Check for the `"loadout"` string at [review_server.js:324](../src/vault_cleaner/ui/review_server.js#L324) specifically, and for the paired preserve/clear test.
3. **The DIM query strings drift.** A trailing space, a curly quote from an editor, or a helpfully "corrected" `is:inLoadout` makes the string useless in DIM while every test that merely checks for a substring still passes. Assert exact equality.
4. **The `Loadouts` cell lands in the wrong place.** Most likely on a survivor row, which looks harmless and is the worst case: no proposal is in a loadout, the badge and filter tests have nothing to exercise, and the existing coverage of the omitted-`loadout`-key case silently stops applying. Also watch for a new fixture file (scope leakage, with a CRLF risk this ticket no longer carries) or an edit to `weapons_dupes.csv` (which moves the golden in a ticket whose contract is an empty golden diff). Confirm the cell is on `7004` and nowhere else.

# Reusable implementer execution prompt

Implement issue #148 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-148-implementation-plan.md
```

Read the entire handoff, issue #148, and `AGENTS.md`, `PLAN.md` and recent `WORKLOG.md` before editing.

**Read the premise-reversal note at the top of the handoff first.** `docs/aggressive-clearout-measurement.md` §8 item 4 specifies a hard loadout rail; that decision was reversed by the owner and this ticket adds **no rail**. If you find yourself editing `rails.py`, `weapons.py` or `dupes.py`, stop.

Rules:
- work on `feat/issue-148-loadout-visibility`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- reproduce every verbatim string in the plan exactly — the three DIM queries especially, which must be asserted by exact equality;
- set `Loadouts` on row `7004` of `tests/fixtures/weapons_hostile.csv` — that exact row, because it is a proposal — rather than creating any new fixture, and do not edit `weapons_dupes.csv`;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, `git diff --check origin/main...HEAD`, and `git status` plus `git ls-files data/`;
- confirm `git diff origin/main...HEAD -- tests/fixtures/report_snapshot_v2.json` is **empty**;
- commit and push the implementation branch; and
- **do not open a pull request.**

If any stop condition is reached, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope.

When complete, report base and head SHAs, changed files, the full output of each verification command, and confirmation that `rails.py`, `weapons.py`, `dupes.py` and the golden are untouched.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
This plan's required implementation modifies `parse.py` and deliberately changes accepted-input behaviour: a weapons export that loads today is rejected afterwards. Parser changes are a categorical trigger, not a judgement call weighed against diff size — step 7 of [handoffs/templates/planner.md](templates/planner.md) names "core parsers", [handoffs/README.md](README.md#review-path-standard-vs-independent-adversarial-review) names parsers among the critical invariants, and [#140](https://github.com/tonym999/vault-cleaner/issues/140) instructs recommending adversarial review for parser changes, reserving standard review for "demonstrably bounded low-risk slices". An input-contract change that rejects previously-valid exports is not such a slice.

An earlier revision of this plan selected standard review, reasoning that the schema edit is one line with a parametrized test. That argued from implementation effort, which is the wrong axis: the category is set by what the change can break, not by how much code it takes. Corrected here after review.

The presentation half of the diff is genuinely low-risk, and the reviewer should spend its attention on the parser boundary, on the "no decision moved" claim (an empty golden diff plus untouched `rails.py` / `weapons.py` / `dupes.py`), and on the refresh-reconciliation behaviour.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

## Implementer model justification

`claude-sonnet-5` at native effort `high` — deliberately lower than the `xhigh` the rail version of this plan specified, because the risk profile changed rather than the volume. There is no rail, no ranking, no versioning and no golden: the remaining work is a badge, a four-edit filter facet across two modules, three literal strings, and tests.

What still needs care is breadth rather than depth — the facet's four coordinated edits and the exact-string discipline on the DIM queries — which is well within `high`, and the plan names both as review checks rather than relying on the model to notice them.

**The tier stays `high` even though the review path was raised to adversarial.** The two track different things: review rigour follows what the change can break (a parser boundary), while the tier follows how hard the change is to write correctly, and that did not change.

**Provider verification (performed 2026-09-13).** Re-verified against Anthropic's official documentation at [platform.claude.com/docs/en/build-with-claude/effort](https://platform.claude.com/docs/en/build-with-claude/effort), as step 4 of the planner template and the rule in [handoffs/README.md](README.md#model-family--provider-native-reasoning-effort-matrix) require:

- `claude-sonnet-5` appears in that page's supported-models list for `output_config.effort`.
- The documented effort levels are `low`, `medium`, `high`, `xhigh` and `max`; Claude Sonnet 5 is listed under both `xhigh` and `max`, so all five are available to it.
- The API default is `high`, and `"Setting effort to \"high\" produces exactly the same behavior as omitting the effort parameter entirely."`
- The page's Sonnet 5 guidance for this level reads: `"High effort (default): Suitable for complex reasoning, coding, and agentic tasks where quality matters more than speed or cost."`

The selection therefore stands as documented. An earlier revision of this plan recorded that this verification had **not** been done, which was a process defect against the template's explicit MUST; it is closed here.

Incidental, and deliberately **not** actioned in this PR: the repository catalog is accurate for the models it lists but is not exhaustive — the official supported-models list also includes `claude-mythos-5-1`, `claude-fable-5`, `claude-mythos-5`, `claude-opus-4-8`, `claude-opus-4-7`, `claude-opus-4-6`, `claude-opus-4-5-20251101` and `claude-sonnet-4-6`. Amending that table belongs to [#144](https://github.com/tonym999/vault-cleaner/issues/144), not to this ticket.

The orchestrator must still re-verify availability in its own runtime at dispatch and record any fallback; documented support is not the same as an instantiable target.

# Review checklist

- [ ] `rails.py`, `weapons.py`, `dupes.py` do not appear in the diff.
- [ ] `git diff origin/main...HEAD -- tests/fixtures/report_snapshot_v2.json` is empty; `RULESET_VERSION` is still `4` and `SNAPSHOT_SCHEMA_VERSION` still `2`.
- [ ] No generated `Notes` clause changed, and no `note_history` recognizer was touched.
- [ ] `REQUIRED_WEAPON_COLUMNS` includes `Loadouts`, with `INVALID_EXPORT_CASES` covering its removal through both `load_weapons` and `load_weapons_bytes`.
- [ ] The `in loadout` badge renders on the proposal row without expanding the detail row, and does not reuse the red `junk` badge colour.
- [ ] The detail-row `flags` line at `review_ui.js:874` is unchanged.
- [ ] All four facet edits are present: `matchesLoadout`, the `filterItems` clause, the `loadout: ""` query default, the `"loadout"` entry in the refresh-invalidation list at `review_server.js:324`, and the select control in `renderControls`.
- [ ] A paired test covers refresh reconciliation: the loadout selection is **preserved** when a refreshed envelope still has matching items and **cleared** when it does not. A clear-only test is insufficient.
- [ ] The three DIM query strings are asserted by **exact equality**, not substring, and read `tag:junk is:inloadout`, `notes:#vc-junk is:inloadout`, `notes:#vc-review is:inloadout`.
- [ ] Each query sits in a natively selectable control; any copy button feature-checks `navigator.clipboard` and falls back to selecting the text.
- [ ] No loadout name is parsed or displayed anywhere.
- [ ] No new fixture file was created; `weapons_hostile.csv` gained a `Loadouts` value on row `7004` only — a proposal, not a survivor; `weapons_dupes.csv` is unedited.
- [ ] Lint, `pytest`, the Playwright browser suite and `git diff --check` all pass; `git ls-files data/` is empty. The browser suite is **required** here, not optional — a skipped run is not a pass.

# Dispatch comment draft

Planned #148 in [handoffs/issue-148-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-148-implementation-plan.md) on `main`.

- **Implementer tier & effort:** `claude-sonnet-5` (`high`) — re-verify availability at dispatch
- **Implementation branch:** `feat/issue-148-loadout-visibility`
- **Review path:** independent adversarial review — the implementation changes `parse.py`'s accepted-input contract, which is a categorical trigger
- **Likely findings:** a hard rail creeping back in from the superseded #142 §8 item 4; the filter facet wired in three of four places, missing the refresh-invalidation entry; the DIM query strings drifting from verbatim; the `Loadouts` cell placed on a survivor row instead of proposal `7004`, or on a new or golden fixture.

---

# Superseded design — hard loadout rail

Retained so the next agent does not re-derive it. **Do not implement.**

The original plan added `rails.weapon_protection` — a weapons-only wrapper around `rails.protection` returning `(HARD, "loadout-protected")` for a non-empty `Loadouts` cell — called from `weapons.py:82` and `dupes.py:243`, with `Loadouts` added to the weapons schema, `RULESET_VERSION` bumped 4 → 5, and the golden regenerated.

Two findings from that analysis remain useful:

1. **The rail's real effect was hiding, not protecting.** Comparing #142's current-rules and loadout-rail protection breakdowns (design document §11) shows that most of the weapons the rail would have newly hard-protected were already soft-protected — exotic or locked — and therefore already review-only. Only a small minority were automatic-junk candidates. The rail would mainly have removed items from the review surface rather than prevented automatic decisions. Exact figures are in §11 and are deliberately not reproduced here.
2. **Any future weapon rail must be a weapons-only wrapper.** `grep -rn "rails.protection" src/` finds eight call sites and five are armor (`armor.py:155`, `armor_close.py:138`, `armor_close.py:302`, `armor_dupes.py:107`, `armor_dupes.py:204`). Editing the shared helper would silently change armor decisions, where loadout membership is deliberately a survivor-ranking input and a review-only rail ([armor_dupes.py:103-112](../src/vault_cleaner/rules/armor_dupes.py#L103-L112), [armor_dupes.py:194-213](../src/vault_cleaner/rules/armor_dupes.py#L194-L213)).

The reversal rationale: a hard rail suppresses the proposal entirely — hard-protected rows `continue` before a `Decision` is constructed ([weapons.py:83-84](../src/vault_cleaner/rules/weapons.py#L83-L84), [dupes.py:244-245](../src/vault_cleaner/rules/dupes.py#L244-L245)) — so a weapon pinned by a throwaway test loadout would vanish from review with no signal, recoverable only by editing the loadout in DIM and re-exporting. #142 found that its removal target cannot be reached from exact duplicates alone and depends on reviewing locked and outclassed rolls (§11). Against that, hiding a large block of reviewable items to prevent a handful of automatic decisions was the wrong trade.
