# vault-cleaner review UI — count / heading / badge / label inventory (issue #113)

Read-only inventory of every user-facing string in the local review server UI that is a
number, names a category/kind/state, or summarises a set.

Scope of files read in full: `src/vault_cleaner/ui/review_server.html`,
`src/vault_cleaner/ui/review.css`, `src/vault_cleaner/ui/review_server.js`,
`src/vault_cleaner/ui/review_ui.js`, plus the server-side strings that reach these
surfaces (`src/vault_cleaner/server/session.py`, `src/vault_cleaner/server/app.py`,
`src/vault_cleaner/review.py`).

## Key facts established by reading the code (used as denominators below)

- `state.items` (review_server.js:334) = `ui.itemsFromSnapshot(snapshot)`
  (review_ui.js:68-127) = **every decision in every snapshot section** (weapons + armor +
  ghosts), i.e. all proposals in the current report. It is never filtered.
- `state.armorGroups` (review_server.js:335) = `ui.armorGroupsFromSnapshot`
  (review_ui.js:588-592) = `armor.exact_duplicate_groups` **concatenated with**
  `armor.same_stat_groups` across armor sections. Groups, not items. A single item id may
  appear in one exact group *and* one same-stat group (review_ui.js:429-433).
- `selectedArmorGroups` = `armorGroupsForKind(state.armorGroups, state.armorGroupKind)`
  (review_server.js:219-231) — narrowed by the All / Exact / Same stats control **only**,
  not by the search box or the four selects.
- `filteredGroups` = `ui.filterArmorGroups(selectedArmorGroups, state.armorQuery)`
  (review_server.js:992-993) — narrowed by group kind **and** the duplicate filters.
- Proposals list uses `ui.filterItems(state.items, state.query, state.verdicts)`
  (review_ui.js:201-217).
- CSS: `.tile .k { text-transform: uppercase }` (review.css:80-83) — every tile label
  renders in caps. `.hint`, `.sub`, `.tile .k`, `th`, `.armor-member-number`,
  `.detail dt`, `.verdict-presentation` are all `var(--muted)` (de-emphasised).
  `tr.vetoed > td { opacity: .55 }` + line-through on the name (review.css:128-129).

---

## 1. Shared shell (static HTML, status region, report tiles, session actions)

| Rendered text (or template) | file:line | Noun — what is counted/named | Denominator | Filter scope | Misreadable? |
|---|---|---|---|---|---|
| `vault-cleaner review` (`<title>` and `<h1>`) | review_server.html:6, 12 | App name | n/a | n/a | No — unambiguous |
| `Skip to review content` | review_server.html:10 | Skip link target name | n/a | n/a | No — unambiguous |
| `Connecting to the local review server…` | review_server.html:14; review_server.js:1086 | Connection state | n/a | n/a | No — unambiguous |
| `Exports` (h2) | review_server.html:18 | Section naming the upload panel | n/a | n/a | Marginal — "Exports" names the *inputs*; a first-timer could read it as "exported results" (the output CSV) rather than "DIM CSVs you upload" |
| `Choose DIM CSV exports to build a report. Files stay on this machine.` | review_server.html:19 | Panel hint | n/a | n/a | No — unambiguous |
| `Weapons CSV` / `Armor CSV` / `Ghosts CSV` | review_server.html:22, 29, 36 | Export kind names | n/a | n/a | No — unambiguous |
| `Idle` (initial upload status) | review_server.html:26, 33, 40 | Per-kind upload state | n/a | n/a | Marginal — "Idle" reads as "no file chosen", but it is also the state after a reset that discarded an accepted upload |
| `Idle` / `Uploading` / `Accepted` / `Rejected` (+ `": " + message`) — `phase.charAt(0).toUpperCase() + phase.slice(1)` | review_server.js:1063 | Per-kind upload state | n/a | Unscoped/global | No — unambiguous |
| `Review session actions` (aria-label on `#vc-actions`) | review_server.html:45 | Accessible group name; **no visible equivalent** | n/a | n/a | **Divergence** — accessible-only name; no visible heading for this button row |
| `Report` (h2) | review_server.html:48 | Section naming the summary tiles | n/a | n/a | Yes — "Report" is also the name of the generated CSV artefact and of the server's `/api/report` envelope; here it labels only the five count tiles |
| `Report fingerprint` + `<code>` value | review_server.html:49; review_server.js:814 | Identity of the current report run | n/a | Unscoped/global | No — unambiguous (opaque value) |
| `Decisions are held in this server session, but no reviewed CSV has been produced and this session's new vetoes have not been persisted.` | review_server.html:53; review_server.js:602 | Session lifecycle state | n/a | Unscoped/global | No — unambiguous |
| `Finalisation succeeded. The reviewed CSV was produced; this session is now frozen.` | review_server.js:599 | Session lifecycle state | n/a | Unscoped/global | No — unambiguous |
| `This review session is closed. It cannot accept further uploads or verdicts.` | review_server.js:601 | Session lifecycle state | n/a | Unscoped/global | No — unambiguous |
| `Filters` (h2) | review_server.html:57 | Section name | n/a | n/a | Yes — the panel holds filters *and* the bulk-verdict buttons + the grouped/flat View selector, which are not filters |
| `Review surface` (section aria-label) | review_server.html:61 | Accessible name of the view-selector panel | n/a | n/a | **Divergence** — duplicates the visible `Review surface` span (review_server.js:610); a screen reader hears "Review surface" twice |
| `Review surface` (visible `.view-selector-label` span) | review_server.js:610 | Label for the two surface buttons | n/a | n/a | No — unambiguous |
| `Proposals` (button, `aria-pressed`) | review_server.js:615 | Surface name | n/a | n/a | No — unambiguous |
| `Armor duplicates` (button text) | review_server.js:617 | Surface name | n/a | n/a | Yes — the surface contains exact duplicates *and* "same stats, different tuning" comparison groups, which are not duplicates |
| aria-label `Armor duplicates` / `Armor duplicates (no duplicate groups)` | review_server.js:620 | Accessible name; the "(no duplicate groups)" suffix has **no visible equivalent** | n/a | Reflects `state.armorGroups.length === 0` (all kinds, ignores every filter) | **Divergence** — sighted users see only a greyed button with no reason; the reason is announced to AT only |
| `PROPOSED` tile — value `String(proposed.total)`, sub `proposed.junk + " junk, " + proposed.review + " review"` | review_server.js:835 (counts: review_ui.js:134-141) | Decisions the rules proposed | All items in the report (`state.items`), every kind, every section | **Ignores all filters and the active surface** | Yes — a first-timer on the Armor duplicates surface reads it as "armor pieces"; it counts weapons + armor + ghosts. Competing reading: "items in my vault" |
| `AFTER VETOES` tile — value `String(kept.total)`, sub `kept.junk + " junk, " + kept.review + " review"` | review_server.js:836 (`ui.keptItems`, review_ui.js:160-171) | Proposals surviving persisted-active vetoes **and** current-session vetoes | Same `state.items` universe | **Ignores all filters** | Yes — "after vetoes" does not say *whose* vetoes; it mixes durable `overrides.json` vetoes with this session's unsaved ones. Competing reading: "after I finish vetoing" (i.e. a projection) |
| `REVIEWED` tile — value `String(reviewed.approved + reviewed.vetoed)`, sub `reviewed.approved + " approved, " + reviewed.vetoed + " vetoed"` | review_server.js:837 (review_ui.js:173-185) | Items with a **current-session** verdict | All `state.items` | **Ignores all filters** | Yes — "reviewed" reads as "I have looked at it"; it only counts items with an Approve/Veto verdict recorded this session. Persisted vetoes from a previous session count as *un*reviewed here |
| `SHOWN` tile — value `String(shown)`, sub `"matching duplicate groups"` **or** `"matching the current filters"` | review_server.js:838-839 | **State-dependent noun**: on `armor-duplicates` it counts *groups* (`filterArmorGroups(selectedArmorGroups, armorQuery).length`); otherwise it counts *items* (`filterItems`) | Groups: the current group-kind selection. Items: all `state.items` | Respects the active filters of whichever surface is showing | **Yes — the worst offender.** The tile label stays `SHOWN` while the counted noun silently switches between items and groups; only the small muted sub-line discloses it. Competing reading: "N items are visible" |
| `UNREVIEWED` tile — value `String(reviewed.unreviewed)`, sub `"without a current-session verdict"` | review_server.js:840 | Items with no session verdict = `items.length - approved - vetoed` | All `state.items` | **Ignores all filters** | Yes — sits beside a filtered `SHOWN` tile, so it reads as "unreviewed among what I'm looking at"; the sub-line corrects the "current-session" half but not the scope half |
| `N persisted override status(es), shown separately from session verdicts:` | review_server.js:845 | Entries in `override_status` | All persisted vetoes in `overrides.json` classified against this run | Unscoped/global | Yes — the count includes `active`, `stale`, `orphaned` **and** `unchecked` buckets (session.py:435-470), so it is *not* "N items are being suppressed". Competing reading: "N vetoes are in force" |
| `<status>: <id> — <detail>` list item | review_server.js:846-847 | One persisted veto and its relation to this run | n/a | Unscoped/global | Yes — bare `id` with no item name; a reviewer cannot tell which vault item it is |
| status token `active` + detail `still matches a proposal; it is being suppressed` | server/session.py:442-443 | Persisted-veto state | n/a | Unscoped/global | No — unambiguous |
| status token `stale` + detail `now proposed as <action>/<reason>, vetoed as <action>/<reason> — re-review it` | server/session.py:448-451; review.py:524-525 | Persisted-veto state | n/a | Unscoped/global | No — unambiguous |
| status token `stale` + detail `still in the vault, but no longer proposed for cleanup` | review.py:533 | Persisted-veto state | n/a | Unscoped/global | No — unambiguous |
| status token `orphaned` + detail `no longer in the export` | server/session.py:456-459 | Persisted-veto state | n/a | Unscoped/global | No — unambiguous |
| status token `unchecked` + detail `<kind> export not loaded this run` | server/session.py:462-467 | Persisted-veto state | n/a | Unscoped/global | No — unambiguous |
| `Retained verdict IDs: <ids>. ` | review_server.js:587, 1074 | Session verdicts carried across a new upload | n/a | Unscoped/global | Yes — raw id list, no count and no names; length is undiscoverable at a glance |
| `Discarded verdict IDs: <ids>. ` | review_server.js:590, 1075 | Session verdicts dropped by a new upload | n/a | Unscoped/global | Yes — same as above |
| ` Local view state dropped: <entries>.` where entries are e.g. `filter action junk`, `duplicate filter type Helmet`, `duplicate group kind exact`, `sort field name`, `expanded item <id>`, `view armor-duplicates` | review_server.js:578-580; entries built at 285, 293, 304, 309, 317, 322, 248 | Client-side view state invalidated by a new report | n/a | Unscoped/global | Yes — these are internal state-machine tokens surfaced verbatim ("view armor-duplicates", "duplicate group kind exact") with no user-facing vocabulary |
| `<description> acknowledged for N item(s).` where description ∈ `Approve`, `Veto`, `Clear`, `Approve all`, `Veto all`, `Unset all`, `Verdict` | review_server.js:1109 (descriptions at 1133, 1138, 740) | Number of verdict decisions POSTed | `decisions.length` — for bulk this is `filterItems(...)` at click time, i.e. the *proposals* filtered set | Bulk respects the **proposals** filters even if the user is on the Armor duplicates surface (bulkVerdict, review_server.js:1137) | Yes — after a bulk action the count is the proposals-filtered count, which need not match the `SHOWN` tile the user was looking at on the duplicates surface |
| `Finalised — this review is frozen. The reviewed CSV has been produced.` | review_server.js:1041 | Session state | n/a | Unscoped/global | No — unambiguous |
| ` 1 approved item remains suppressed by an active persisted veto.` / ` N approved items remain suppressed by active persisted vetoes.` | review_server.js:1036-1040; source header `Vault-Cleaner-Approved-Still-Vetoed` (app.py:284-285) = `len(merge.already_vetoed_but_approved)` (app.py:794) | Items approved this session that a durable veto still suppresses | Conflicts inside the merge at finalize time | Unscoped/global; only rendered in the `finalized` state | No — unambiguous, though it appears only once and is easy to miss |
| `Download again` / `Reset / Start new review` / `Shutdown` / `Finalise review` | review_server.js:1042, 1043, 1044, 1048, 1049, 1052 | Session actions | n/a | n/a | No — unambiguous |
| `Connected. Upload one or more DIM CSV exports to begin.` | review_server.js:1055, 1089 | Session state | n/a | n/a | No — unambiguous |
| `Connected — report loaded with server-backed verdict controls.` | review_server.js:1092 | Session state | n/a | n/a | No — unambiguous |
| `This review is finalised and frozen.` | review_server.js:1090 | Session state | n/a | n/a | No — unambiguous |
| `This review session has ended. Start a new vault-cleaner serve session.` | review_server.js:1091, 1300 | Session state | n/a | n/a | No — unambiguous |
| `Unreviewed proposals will remain in the generated import CSV unless an existing active persisted veto suppresses them. Continue?` (confirm, gated on `reviewed.unreviewed > 0`) | review_server.js:1231-1233 | Warning about the unreviewed set | Gate reads `reviewed.unreviewed` over all `state.items` | **Ignores all filters** | Yes — it does not state *how many* are unreviewed, so the user cannot judge the size of what they are about to ship |
| `Reconnect` (button appended to the status region) | review_server.js:551 | Recovery action | n/a | n/a | No — unambiguous |
| `Review reset. Durable overrides were not changed.` | review_server.js:1283 | Session state after reset | n/a | Unscoped/global | No — unambiguous |

---

## 2. Proposals surface

### 2a. Panel chrome, filters and bulk controls

| Rendered text (or template) | file:line | Noun — what is counted/named | Denominator | Filter scope | Misreadable? |
|---|---|---|---|---|---|
| `Proposals` (h2, `aria-labelledby`) | review_server.html:65 | Section name | n/a | n/a | No — unambiguous |
| `Verdicts are held by the server and change only after an acknowledgement.` | review_server.html:66 | Panel hint | n/a | n/a | No — unambiguous |
| `Search name or instance id` (field label) | review_server.js:943 | Search scope | n/a | n/a | Marginal — matching is name-substring OR **id-substring** (`matchesText`, review_ui.js:187-192); "name" matching is case-insensitive but id matching is not, and neither is anchored |
| placeholder `e.g. Dupe Rifle or 3001` | review_server.js:945 | Example query | n/a | n/a | No — unambiguous |
| `Action` select label | review_server.js:949 | Facet name | n/a | n/a | No — unambiguous |
| `Kind` select label | review_server.js:949 | Facet name (`weapons` / `armor` / `ghosts` section kind) | n/a | n/a | Yes — "Kind" is Destiny-ambiguous; competing reading is item type (Helmet, Hand Cannon). It is actually the export/section kind |
| `Reason` select label | review_server.js:950 | Facet name (rule reason slug) | n/a | n/a | No — unambiguous |
| `Class` select label | review_server.js:950 | Facet name — bound to `classFacet`, which is `guardian_class` **or**, when empty, the decision/section kind (review_ui.js:96-99) | n/a | n/a | **Yes** — for class-neutral items (weapons, ghosts) the "Class" dropdown lists values like `weapons` and `ghosts` beside `Hunter`/`Titan`/`Warlock`. Competing reading: "Guardian class only" |
| All-option text `any action` / `any kind` / `any reason` / `any class` | review_server.js:949-950 (rendered at review_ui.js:773) | "No constraint" option | n/a | n/a | No — unambiguous |
| Option text `<value> (<count>)` — `entry.value + " (" + entry.count + ")"` | review_ui.js:774-780 (`countBy`, review_ui.js:675-686); wired at review_server.js:951 | Number of **items** having that facet value | **All `state.items`** — `optionsFor` is called with `state.items`, not the filtered set | **Ignores every active filter, including the other selects and the search box** | **Yes** — the parenthesised counts do not co-vary with the other filters, so `Action: junk (12)` + `Kind: armor (30)` can both be shown while the list has far fewer rows. Competing reading: "12 junk items among what is currently filtered" |
| `Protection` select label | review_server.js:953 | Facet name | n/a | n/a | No — unambiguous |
| Protection options `any` / `protected` / `unprotected` / `soft only` / `hard only` | review_server.js:954-956 | Protection state | n/a | n/a | Yes — `protected` means "soft **or** hard" (`item.protectionLevel !== ""`, review_ui.js:196); a first-timer may read `protected` and `hard only` as disjoint categories. These options carry **no counts**, unlike the four selects above — an inconsistency |
| `Session verdict` select label | review_server.js:958 | Facet name | n/a | n/a | No — unambiguous |
| Verdict options `any` / `unreviewed` / `approved` / `vetoed` | review_server.js:959-960 | Current-session verdict state | n/a | n/a | Yes — `unreviewed` here means "no verdict **this session**"; an item suppressed by a persisted veto still filters as `unreviewed`. No counts here either |
| `View` select label | review_server.js:962 | Presentation mode | n/a | n/a | Yes — "View" collides with the `Review surface` selector (Proposals / Armor duplicates), which is also a view choice |
| View options `grouped by action/kind/reason` / `one sortable table` | review_server.js:963 | Presentation mode | n/a | n/a | No — unambiguous |
| `Bulk action on shown items` (field label) | review_server.js:973 | Label over the three bulk buttons | n/a | Describes `filterItems(state.items, state.query, state.verdicts)` (review_server.js:1137) | Yes — "shown items" is the proposals-filtered set even when the user is on the Armor duplicates surface; and it does not match the `SHOWN` tile when that tile is counting groups |
| `Approve all shown` / `Veto all shown` / `Unset all shown` | review_server.js:968-970 | Bulk verdict actions | Acts on the proposals-filtered set | Respects proposals filters only | Yes — "shown" is undefined at the moment of clicking if the reviewer has collapsed/scrolled; nothing states the number that will be affected before the click |
| `Reset filters` | review_server.js:978 | Action; clears every key of `state.query` including the search text | n/a | n/a | Marginal — it also clears the search box, which the label does not say |
| `No items match these filters.` | review_server.js:1010 | Empty state for the proposals list | n/a | Respects the active proposals filters | No — unambiguous |

### 2b. Group headings and table

| Rendered text (or template) | file:line | Noun — what is counted/named | Denominator | Filter scope | Misreadable? |
|---|---|---|---|---|---|
| `<ACTION> <reason> (<kind>) — N item(s)` — `group.action.toUpperCase() + " " + group.reason + " (" + group.kind + ") — " + group.items.length + " item(s)"` (details `<summary>`) | review_ui.js:232-235; rendered at review_server.js:1019 | Items in one (action, kind, reason) triple | Items in that triple **within the currently filtered+sorted set** (`renderList` passes `sortItems(filterItems(...))`, review_server.js:1008-1018) | **Respects the active filters** | Yes — it respects filters while the `SHOWN`/`PROPOSED` tiles above do not, so the group counts will not sum to `PROPOSED`. Competing reading: "N items exist with this reason" |
| Column header `Name` | review_ui.js:1240, 715 | Column | n/a | n/a | No — unambiguous |
| Column header `Instance id` | review_ui.js:1240, 716 | Column (opaque uint64 string) | n/a | n/a | No — unambiguous |
| Column header `Kind` | review_ui.js:1240, 716 | Column — export/section kind | n/a | n/a | Yes — same ambiguity as the `Kind` filter: reads as item type |
| Column header `Class` | review_ui.js:1241, 717 | Column — `classFacet` (guardian class, or the kind when class-neutral) | n/a | n/a | **Yes** — a weapons row shows `weapons` in the Class column |
| Column header `Location` | review_ui.js:1241, 717 | Column — `decision.location` (DIM `Owner`) | n/a | n/a | Yes — "Location" reads as vault/character position; the value is the owning character/vault name |
| Column header `Action` | review_ui.js:1242, 718 | Column | n/a | n/a | No — unambiguous |
| Column header `Reason` | review_ui.js:1242, 718 | Column — parsed reason slug (`report.reason_slug`, report.py:31-40) | n/a | n/a | No — unambiguous |
| Column header `Tuning Mod Slot` | review_ui.js:1243, 719 | Column — value is `Candidate: X · Selected: Y` or `—` (`tuningComparison`, review_ui.js:62-66) | n/a | n/a | Yes — the header names a single slot but the cell is a two-sided comparison; `—` means "one side unknown", not "no tuning slot" |
| Column header `Protection` | review_ui.js:814 | Column — not sortable, unlike the eight above | n/a | n/a | Marginal — visually identical `th` to the sortable ones but has no button |
| Column header `Verdict` | review_ui.js:815 | Column | n/a | n/a | No — unambiguous |
| Sort button text `<label>` / `<label> ▲` / `<label> ▼` | review_ui.js:797-799 | Column header + sort direction | n/a | n/a | No — unambiguous |
| Sort button aria-label `sort by <label>` | review_ui.js:800 | Accessible name — **omits the ▲/▼ direction** the visible text carries | n/a | n/a | **Divergence** — direction is conveyed to AT only via `aria-sort` on the `th` (review_ui.js:795); the button's own name never changes |
| Name cell button text `▸ <name>` / `▾ <name>` / `▸ (unnamed)` | review_ui.js:910 | Item name + expand state | n/a | n/a | No — unambiguous (`aria-expanded` matches) |
| Action badge `junk` / `review` (`.badge.junk` red, `.badge.review` amber) | review_ui.js:926-929; review.css:134-135 | Proposed action | n/a | n/a | Yes — the badge says `review` and the surface selector says `Proposals`, while the panel `Filters` also has a `Session verdict` facet; "review" the action vs "review" the activity are different things |
| Protection cell `<level>` or `—` | review_ui.js:932 | Protection level (`soft` / `hard` / empty) | n/a | n/a | Marginal — `—` means unprotected; nothing says so |
| Verdict buttons `Approve` / `Veto` / `Unset` | review_ui.js:875, 883, 889 | Verdict actions, `aria-pressed` reflects state | n/a | n/a | No — unambiguous |
| aria-label `approve <name>, id <id>` / `veto <name>, id <id>` / `unset verdict for <name>, id <id>`; `"unnamed item"` when name is empty | review_ui.js:877, 884, 891-892 | Accessible names — **richer than the visible `Approve`/`Veto`/`Unset`** | n/a | n/a | **Divergence** — deliberate and benign, but note that the armor-duplicate equivalents (review_ui.js:1029-1032) use a *different* pattern with **no item name** |
| Verdict presentation text (`.verdict-presentation`, muted) — one of `Unreviewed`, `approved`, `vetoed`, `Approved this session · active persisted veto still suppresses this item`, `Vetoed this session · active persisted veto still suppresses this item`, `Active persisted veto still suppresses this item` | review_server.js:359-370; rendered review_ui.js:896-899 | Combined session-verdict + persisted-veto state | n/a | Unscoped/global | **Yes** — casing is inconsistent (`Unreviewed` capitalised, `approved`/`vetoed` lower-case, straight from the enum), and the "Approved this session · active persisted veto still suppresses this item" string reads as a contradiction with no hint about which wins |
| Detail term `hash` | review_ui.js:845 | Item hash | n/a | n/a | No — unambiguous |
| Detail term `note vault-cleaner would write` | review_ui.js:846 | Prospective `Notes` value | n/a | n/a | No — unambiguous |
| Detail term `DIM tag vault-cleaner would write` | review_ui.js:847 | Prospective `Tag` value | n/a | n/a | No — unambiguous |
| Detail term `surviving copy` (value = `keptId`) | review_ui.js:848 | The winning duplicate's instance id | n/a | n/a | Yes — an opaque id with no name; a reviewer cannot tell which copy survives without cross-referencing |
| Detail term `protection` (value = `<level> — <reason>`) | review_ui.js:849-850 | Protection level and its cause | n/a | n/a | No — unambiguous |
| Detail term `existing DIM tag` / `existing DIM notes` | review_ui.js:851-852 | Current DIM values | n/a | n/a | No — unambiguous |
| Detail term `flags`, values joined from `locked`, `equipped`, `in a loadout` | review_ui.js:853-857 | Boolean item states | n/a | n/a | Marginal — an absent flag renders as an omitted `dt`/`dd` pair entirely (`definition` returns `[]` on empty, review_ui.js:818-821), so "not locked" is invisible rather than stated |
| `Armor scoring` (h3 inside the detail row) | review_ui.js:839 | Sub-section name | n/a | n/a | No — unambiguous |
| Detail term `slot` / `equippable` / `best archetype` | review_ui.js:825-827 | Armor evaluation fields | n/a | n/a | Yes — `best archetype` is vault-cleaner's own `[armor.archetypes.*]` scoring profile (AGENTS.md), **not** the DIM `Archetype` column shown as `Archetype` in the duplicates surface. Two different "archetype" nouns in one UI |
| Detail term `score`, value `<score> (base <base_score>, set bonus <set_bonus>)` | review_ui.js:828-829 | Armor score decomposition | n/a | n/a | Marginal — no scale is given; per AGENTS.md scores are normalised to the `Total (Base)` scale, which the UI never states |
| Detail term `rank`, value `<rank> of <group_size>` | review_ui.js:830-831 | Rank of this piece among scored rows | `group_size` = `len(scored_rows)` for the (class, slot) scoring group (rules/armor.py:150-176) | Unscoped/global — computed server-side, unaffected by any UI filter | **Yes** — "rank 4 of 37" gives no clue what the 37 is. Competing readings: "37 copies of this item", "37 items in this duplicate group", "37 items shown". It is actually every scored armor piece of that equippable class and slot |
| Detail stat badges `<stat name> <value>` | review_ui.js:834-836 | Per-stat values | n/a | n/a | Marginal — nothing says these are *base* stats |

---

## 3. Armor duplicates surface

### 3a. Panel chrome, group-kind selector, filters, counts

| Rendered text (or template) | file:line | Noun — what is counted/named | Denominator | Filter scope | Misreadable? |
|---|---|---|---|---|---|
| `Armor duplicates` (h2, `aria-labelledby`) | review_server.html:70 | Section name | n/a | n/a | Yes — same as the surface button: same-stat groups are not duplicates |
| `Exact groups show authoritative survivor and disposition context. Same stats, different tuning groups are review-only comparisons; verdict controls appear only where the current report already has a proposal.` | review_server.html:71 | Panel hint distinguishing the two group kinds | n/a | n/a | Marginal — it is the only place the two kinds are defined, and it sits above a control (`Show: All / Exact / Same stats`) that uses different words for the same kinds |
| `Armor duplicate group kind` (aria-label on the kind selector `role="group"`) | review_server.js:870 | Accessible group name | n/a | n/a | **Divergence** — visible label is `Show` (review_server.js:871); AT hears "Armor duplicate group kind" |
| `Show` (visible `.view-selector-label` span) | review_server.js:871 | Label for the All/Exact/Same stats buttons | n/a | n/a | Yes — "Show" is a verb with no object; nothing on screen says it selects *group kinds* |
| `All` / `Exact` / `Same stats` buttons (`aria-pressed`) | review_server.js:873 | Group-kind selection. `exact` = `groupKind !== "same_stat"`; `same_stat` = `groupKind === "same_stat"` (review_server.js:219-231) | n/a | This control **defines** the denominator for everything else on this surface | Yes — `Exact` and `Same stats` do not name the same axis (`Exact` what? `Same stats` as what?). Also the whole selector is **only rendered when both kinds exist** (review_server.js:867), so a report with one kind gives no hint the other kind is a concept at all |
| `Search armor name or instance id` (field label) | review_server.js:900 | Search scope | n/a | n/a | Yes — the name match is against the **group** name, the id match is against **any member's** id (`matchesArmorGroup`, review_ui.js:596-603); a matching id keeps the whole group, including non-matching members |
| placeholder `e.g. Dupe Plate or 5002` | review_server.js:902 | Example query | n/a | n/a | No — unambiguous |
| `Class` select label | review_server.js:924 | Facet — group `guardianClass` | n/a | n/a | Yes — same visible label as the Proposals `Class` select but a **different field** (`guardianClass`, never falling back to kind). Two selects, same label, different semantics |
| `Slot / type` select label | review_server.js:925 | Facet — group `type` (DIM `Type`) | n/a | n/a | Marginal — "Slot / type" is two nouns for one column; the Proposals surface calls the same underlying idea `slot` (review_ui.js:825) |
| `Archetype` select label | review_server.js:926 | Facet — group `itemArchetype` (the DIM `Archetype` column) | n/a | n/a | **Yes** — collides with `best archetype` in the Proposals detail row, which is vault-cleaner's own scoring profile. AGENTS.md flags exactly this two-meaning hazard |
| `Tuning Mod Slot` select label | review_server.js:927 | Facet — group-level value for exact groups; **any member's** value for same-stat groups (review_ui.js:607-616) | n/a | n/a | Yes — the same filter silently changes from "the group's slot" to "at least one member has this slot" depending on group kind |
| All-option text `any class` / `any slot / type` / `any archetype` / `any tuning slot` | review_server.js:924-927 | "No constraint" options | n/a | n/a | Marginal — `any tuning slot` is a third wording for the field labelled `Tuning Mod Slot` and rendered as a row header `Tuning Mod Slot` |
| Duplicate option text `<value> (<count>)` — `entry.value + " (" + entry.count + ")"` | review_server.js:918-920 (`countArmorGroups`, review_ui.js:626-645) | Number of **groups** with that value. For `tuningModSlot` on same-stat groups, groups containing ≥1 member with that value — so **one group can be counted under several tuning-slot values** | `selectedArmorGroups` — i.e. the current `All`/`Exact`/`Same stats` selection only | **Ignores the search box and the other three selects**; **does** respect the group-kind selection | **Yes, twice over.** (a) the count is groups, not armor pieces, and nothing on the option says so; (b) for tuning slots on same-stat groups the counts can sum to more than the number of groups. Competing reading: "N armor pieces are Helmets" |
| Value token `none/unknown` (from `normalizeCategoricalValue`) appearing in option text, meta tiles and table cells | review_ui.js:29-32; used at 408-416, 546-548, 564-575, 1139, 1144, 1150, 1157 | Empty categorical value | n/a | n/a | Yes — it conflates "the export had no value" with "the value is genuinely unknown", and it appears as if it were a real Destiny value in a dropdown alongside `Helmet`, `Titan`, etc. |
| `Reset duplicate filters` | review_server.js:932 | Action; clears every key of `state.armorQuery` including the text box — but **not** the `All`/`Exact`/`Same stats` selection | n/a | n/a | Yes — the group-kind selection survives the reset, so "reset" leaves the list still narrowed |
| `Showing <filteredGroups.length> of <selectedArmorGroups.length> groups` (id `vc-duplicate-count`, `.hint` = muted) | review_server.js:994-997 | **Groups**, not armor pieces | `selectedArmorGroups.length` — **the current group-kind selection**, not all armor duplicate groups. With `Show: Exact` active, `of N` silently drops every same-stat group | Numerator respects search + the four selects; denominator respects **only** the group-kind selection | **Yes — the second-worst offender.** (a) "groups" reads as "items" to a first-time reviewer looking at a page of armor pieces; (b) the denominator moves when the `Show` control changes, so "12 of 20" and "12 of 45" can describe an identical list; (c) it is rendered in muted `.hint` grey, so it is visually the *least* prominent number on a surface where it is the only scoped one |
| `No armor duplicate groups match these filters.` | review_server.js:999 | Empty state | n/a | Respects group kind + duplicate filters | Yes — says "these filters" but the empty result may be caused by the `Show` control, which is not presented as a filter and is not cleared by `Reset duplicate filters` |

### 3b. Group header

| Rendered text (or template) | file:line | Noun — what is counted/named | Denominator | Filter scope | Misreadable? |
|---|---|---|---|---|---|
| `<group.name>` or `(unnamed armor)` (h3) | review_ui.js:1049 | Group name = the shared item name | n/a | n/a | No — unambiguous |
| `Same stats, different tuning · review-only` (`.sub`, muted) | review_ui.js:1050-1051 | Group-kind label for `same_stat` | n/a | n/a | Marginal — "review-only" is a third vocabulary for the same idea ("Read-only comparison" on the badges, "review-only comparisons" in the panel hint) |
| `Exact duplicate group · <group.groupKind>` → renders literally as `Exact duplicate group · exact_duplicate` (`.sub`, muted) | review_ui.js:1052 | Group-kind label for exact groups | n/a | n/a | **Yes — a raw enum token leaks into the UI.** The snake_case `exact_duplicate` is appended to prose that already said the same thing, so the line reads as a redundant machine identifier |
| Tile `TYPE / SLOT` — value `group.type \|\| "unknown"` | review_ui.js:1054 | DIM `Type` | n/a | Unscoped/global (property of the group) | Yes — the `\|\| "unknown"` fallback is unreachable because `normalizeCategoricalValue` (review_ui.js:408) already turned `""` into `"none/unknown"`; the tile therefore shows `none/unknown` where the code intends `unknown`. Two different empty-value words for one field |
| Tile `GUARDIAN CLASS` — value `group.guardianClass \|\| "class-neutral/unknown"` | review_ui.js:1055 | DIM guardian class | n/a | Unscoped/global | Yes — same dead fallback: the value is already `none/unknown`, so the intended `class-neutral/unknown` wording never appears. A third empty-value vocabulary |
| Tile `TIER` — value `group.tier` or `"unknown"` | review_ui.js:1056 | Armor tier (e.g. 5) | n/a | Unscoped/global | Yes — a bare number `5` under a caps label `TIER`; "Tier" is also DIM/Destiny rarity vocabulary (Legendary/Exotic). Competing reading: rarity |
| Tile `HASH` — value `group.hash` | review_ui.js:1057 | Item definition hash | n/a | Unscoped/global | Marginal — opaque; meaningful only to a reviewer who knows why grouping is by `Hash` |
| Tile `ARCHETYPE` — value `group.itemArchetype \|\| "none/unknown"` | review_ui.js:1058 | DIM `Archetype` column | n/a | Unscoped/global | Yes — collides with `best archetype` in Proposals (vault-cleaner's scoring profile) |
| Tile `TUNING MOD SLOT` — exact groups only (`null` for same-stat) | review_ui.js:1059 | Group-level tuning slot | n/a | Unscoped/global | Yes — its **absence** on same-stat groups is the signal that tuning varies per member, but nothing states that; a reviewer sees a missing tile, not a message |
| `Base stat summary` (aria-label on `.armor-stat-summary`) | review_ui.js:1061 | Accessible name of the stat tile row; **no visible equivalent** | n/a | n/a | **Divergence** — sighted users get an unlabelled row of tiles; only AT is told these are base stats |
| Stat tile label `PRIMARY` / `SECONDARY` / `TERTIARY` (tier-5 path) — value `<stat name> <value>` | review_ui.js:665, 1045-1046 | Stat role derived from the value (30/25/20) | n/a | Unscoped/global | Yes — the role is inferred from the *number*, not from an archetype table (review_ui.js:648-673); a reviewer could read `PRIMARY` as an authoritative archetype declaration |
| Stat tile label `BASE STAT` (non-tier-5 path) — value `<stat name> <value>` | review_ui.js:661, 1046 | Stat name and value | n/a | Unscoped/global | Marginal — every tile in the row carries the identical label `BASE STAT`, so the label conveys nothing per-tile |
| `The other three base stats are 0 on this tier-5 piece.` (`.hint`, muted) | review_ui.js:671; rendered 1062 | Explanation for the three suppressed rows | Exactly 3, hard-coded for the tier-5 shape | Unscoped/global | No — unambiguous (and only emitted when the 30/25/20/0/0/0 shape is confirmed) |
| Tile `SPIRIT SIGNATURE` — value `group.spiritSignature.join(" · ")` | review_ui.js:1063 | Exotic-class-item spirit perks | n/a | Unscoped/global; tile omitted when empty | Marginal — omission means "none", which is never stated |
| Tile `SEASONAL MOD` | review_ui.js:1064 | Seasonal mod value | n/a | Unscoped/global; omitted when falsy — same-stat groups always set it to `""` (review_ui.js:573) so this tile **never appears** for same-stat groups, even though members may differ | Yes — a group-level tile that is structurally absent for one group kind, with the per-member value appearing instead as a table row only when members disagree |
| Tile `HOLOFOIL` — shown only when truthy **and** not `"false"` | review_ui.js:1065-1066 | Holofoil flag | n/a | Unscoped/global | Marginal — the `"false"` string guard means a literal `false` from the export is treated as absent; nothing distinguishes "no holofoil" from "not exported" |

### 3c. Transposed group table (`armorGroupTable`)

| Rendered text (or template) | file:line | Noun — what is counted/named | Denominator | Filter scope | Misreadable? |
|---|---|---|---|---|---|
| Column header `Comparison` (the row-label column) | review_ui.js:1127 | Names the axis of the transposed table | n/a | n/a | Yes — it is the header of the *stub* column holding attribute names; it reads as a column of comparisons rather than a label for the rows |
| Member column heading line 1: `Member <index+1>` (`.armor-member-number`, muted, 0.78rem) | review_ui.js:1130 | Positional index within this group | Position in `group.members` — **authoritative snapshot order**, which for exact groups is the ranking order (preferred survivor first) | Unscoped — index is per-group, unaffected by filters | **Yes** — "Member 1" reads as a rank or a preference. For exact groups it *is* effectively rank order; for same-stat groups it is arbitrary. Nothing states which |
| Member column heading line 2: `<member.id>` (`.mono`) | review_ui.js:1131 | Instance id | n/a | n/a | No — unambiguous |
| Member column heading line 3: `<member.location>` or `location unknown` (`.sub`, muted) | review_ui.js:1132 | Owning character / vault | n/a | n/a | Marginal — same "Location means Owner" ambiguity as the Proposals column |
| Member column heading line 4: `.badge` with `armorMemberLabel(group, member)` | review_ui.js:1133 | Per-member disposition or proposal state | n/a | n/a | see the four rows below |
| Badge `Preferred survivor` | review_ui.js:986 (via 1014, 1133) | Exact-group disposition `preferred_survivor` | n/a | Unscoped/global (authoritative snapshot value) | Yes — "Preferred" reads as a suggestion the reviewer may override, but there is **no verdict control on this member** (`isProposalMember` is false, review_ui.js:993-996), so it is not actionable here |
| Badge `Retained protected` | review_ui.js:987 | Exact-group disposition `retained_protected` | n/a | Unscoped/global | Yes — two past-participles with no object; it does not say *what* protected it (that is in the `Hard protection` row further down) |
| Badge `Proposed junk` | review_ui.js:988 | Exact-group disposition `proposed_junk` | n/a | Unscoped/global | No — unambiguous |
| Badge `Proposed review` | review_ui.js:989 | Exact-group disposition `proposed_review` | n/a | Unscoped/global | Yes — "review" as an *action* vs the page's `Review surface` / `review-only` vocabulary |
| Badge `<member.disposition>` or `Unclassified member` (fallback) | review_ui.js:990 | Unrecognised disposition | n/a | Unscoped/global | Marginal — unreachable in practice (dispositions are validated at review_ui.js:351-355), but would emit a raw snake_case enum if reached |
| Badge `Read-only comparison` (same-stat member with no correlated proposal) | review_ui.js:1012 | Same-stat member state | n/a | Unscoped/global | Yes — "Read-only" describes the *control*, not the item; a reviewer may read it as "this item is locked/read-only in DIM" |
| Badge `Existing Proposals action: <junk\|review>` (same-stat member with a correlated proposal) | review_ui.js:1010-1011 | The proposal that the Proposals surface already carries for this member | n/a | Unscoped/global (correlated in the same section, same hash) | Yes — capital-P `Proposals` is a *surface name* used mid-sentence as if it were a noun for a set; a first-timer will not know it is a cross-reference to the other tab |
| `.badge` on member headings has **no colour class**, unlike the `junk`/`review` badges in Proposals | review_ui.js:1133 vs 926-929; review.css:130-135 | — | n/a | n/a | Yes — `Proposed junk` here is a neutral outline badge while `junk` in Proposals is red; the same fact reads as different severity on the two surfaces |
| Row header `Tuning Mod Slot` (same-stat groups only) | review_ui.js:1138 | Per-member tuning slot | n/a | Unscoped | No — unambiguous |
| Row header `Seasonal Mod` (same-stat only, and only when members differ) | review_ui.js:1141-1146 | Per-member seasonal mod | Rendered only when `memberValues(...).length > 1` | Unscoped | Yes — the row's **absence** silently means "all members agree", which is information the reviewer never sees stated |
| Row header `Holofoil` (same-stat only, and only when members differ) | review_ui.js:1147-1152 | Per-member holofoil | Same conditional as above | Unscoped | Yes — same silent-absence problem |
| Row header `Tuning Stat` (same-stat only; rendered only when `rawTuningValues.length > tuningSlots.length`) | review_ui.js:1153-1159 | Per-member tuned stat | Conditional compares distinct raw tuning-stat values against distinct tuning-slot values | Unscoped | **Yes** — the display condition is a cardinality comparison with no user-facing meaning; the row appears and disappears for reasons the reviewer cannot infer. Also `Tuning Stat` vs `Tuning Mod Slot` are two adjacent rows with near-identical names |
| Row header `Hard protection`; cell = `<protectionLevel> — <protectionReason>` or `—` | review_ui.js:1162-1166 | Protection level and cause | n/a | Unscoped | **Yes** — the row is labelled `Hard protection` but the cell renders whatever `protectionLevel` is, which can be `soft` (review_ui.js:384-386, and the Proposals filter offers `soft only`/`hard only`). "Hard protection: soft — locked" is directly contradictory |
| Row header `In loadout`; cells `Yes` / `No` | review_ui.js:1167 | Boolean | n/a | Unscoped | No — unambiguous |
| Row header `Equipped`; cells `Yes` / `No` | review_ui.js:1168 | Boolean | n/a | Unscoped | No — unambiguous |
| Row header `Locked`; cells `Yes` / `No` | review_ui.js:1169 | Boolean | n/a | Unscoped | No — unambiguous |
| Row header `Masterwork Tier`; cells `<value>` or `unknown` | review_ui.js:1170-1173 | Masterwork tier | n/a | Unscoped | Yes — `Tier` here is masterwork tier while the header tile `TIER` is armor tier; two different numeric "tier" nouns on the same screen |
| Row header `Power`; cells `<value>` or `unknown` | review_ui.js:1174-1176 | Power level | n/a | Unscoped | No — unambiguous |
| Row header `Verdict` (the `.armor-verdict-row`) | review_ui.js:1185 | Row holding the verdict controls / read-only text | n/a | Unscoped | No — unambiguous |
| Verdict buttons `Approve` / `Veto` / `Unset` (only where `armorMemberCanVerdict` is true) | review_ui.js:1076, 1084, 1090 | Verdict actions | Exact: `isProposalMember` (disposition + proposalAction agree). Same-stat: a correlated `currentProposalAction` of `junk`/`review` exists | Unscoped/global | Yes — controls appear on **some** member columns and not others with no in-table explanation; the only explanation is the panel hint at review_server.html:71 |
| aria-label `approve exact-duplicate armor member id <id>` / `veto same-stat armor member id <id>` / `unset verdict for <kind> armor member id <id>` | review_ui.js:1029-1032; used at 1078, 1085, 1092 | Accessible names | n/a | n/a | **Divergence, two ways** — (a) visible text is just `Approve`/`Veto`/`Unset`; (b) unlike the Proposals equivalents (review_ui.js:877, 884, 891) these **omit the item name**, and they introduce yet another kind vocabulary (`exact-duplicate`, `same-stat`) distinct from the visible `Exact` / `Same stats` buttons and the `exact_duplicate` enum in the group sub-heading |
| Verdict presentation text on an actionable member = `verdictText(member, verdict)` (same six strings as Proposals) | review_ui.js:1097, 1101 | Session verdict + persisted-veto state | n/a | Unscoped/global | Yes — inherits the casing inconsistency and the "approved but still suppressed" contradiction noted in §2b |
| Read-only text (same-stat, no proposal) `Read-only comparison · Current verdict: <verdictText>` | review_ui.js:1103; repainted at 1223 | Member state + verdict | n/a | Unscoped/global | Yes — it shows a "Current verdict" for an item the reviewer cannot give a verdict to on this surface; the verdict came from the Proposals surface or a prior session |
| Read-only text (exact, non-proposal) `Read-only · <dispositionLabel>` | review_ui.js:999; via 1104, 1224 | Member state | n/a | Unscoped/global | Yes — duplicates the badge already shown in the same column heading (review_ui.js:1133), so the same disposition is stated twice per column |
| Read-only suffix ` · Also proposed <action> in Proposals · Current verdict: <verdictText>` (+ ` — <reason>`) | review_ui.js:1000-1004 | Cross-surface proposal correlation | n/a | Unscoped/global | **Yes** — a four-clause `·`-separated run-on that mixes a disposition, a cross-surface pointer, an action enum (`junk`/`review` lower-case), a verdict state and a reason slug, in muted `.hint` grey |

---

## Summary of accessible-name / visible-text divergences (flagged above)

1. `#vc-actions` aria-label `Review session actions` — no visible heading (review_server.html:45).
2. `#vc-view-selector` section aria-label `Review surface` duplicates the visible span of the same text (review_server.html:61 vs review_server.js:610).
3. Armor-duplicates surface button: visible `Armor duplicates`, aria-label `Armor duplicates (no duplicate groups)` when disabled (review_server.js:617 vs 620).
4. Kind selector: visible label `Show`, aria-label `Armor duplicate group kind` (review_server.js:871 vs 870).
5. Sort buttons: visible `<label> ▲`/`▼`, aria-label `sort by <label>` (no direction) (review_ui.js:799 vs 800).
6. Proposals verdict buttons: visible `Approve`, aria-label `approve <name>, id <id>` (review_ui.js:875 vs 877).
7. Armor member verdict buttons: visible `Approve`, aria-label `approve exact-duplicate armor member id <id>` — **name omitted**, unlike (6) (review_ui.js:1076 vs 1078, 1029-1032).
8. Stat tile row: aria-label `Base stat summary`, no visible equivalent (review_ui.js:1061).

## Undetermined

- Whether the `Reason` slug vocabulary (e.g. `dupe-lower`, `armor-similar to`, `ghost-unprotected-surplus`, `wishlist-trash whole-item`) is ever explained to the user anywhere in this UI: not present in any of the four UI files. **Undetermined — would need the docs/onboarding surface, if any, outside `src/vault_cleaner/ui/`.**
- The exact rendered width/wrapping of the muted `Showing N of M groups` line relative to the tiles: **undetermined — would need a rendered page, which this task forbids.**
