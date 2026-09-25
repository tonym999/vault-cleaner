# Issue #170 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#170 — Plain-English reasons for weapon proposals in the review report`

**Milestone:** `None — deliberately unassigned; #170 is a child of umbrella #140, whose children carry no milestone`

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5-5` (Anthropic, Claude Code session; the runtime does not expose a native effort setting for this session)

**Implementation model selected:** `MAI-Code-1.1-Flash` (`n/a — adaptive`) (Bounded rung; justified below)

**Plan baseline:** `main` at `c64f703e35b14ca90e958a6691d6ce4f1a41ac7c` (2026-09-25)

**Allocated implementation branch:** `feat/issue-170-proposal-explanations`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Give every **weapon** proposal a plain-English explanation, built in Python by
the rule that makes the proposal, carried in the report snapshot, and shown in
the current review UI. The explanation has five parts: a short label, why the
copy is suggested, the copy to keep instead (when the reasoning relies on one),
what you give up, and caveats.

The DIM `Notes` clauses, the reason slug, every decision (action, tag, note,
kept id, protection) and `RULESET_VERSION` are unchanged. This is a
presentation and snapshot-schema change only.

The explanation is Python-owned so it survives the M10 rendering decision
(#137 / #138) unchanged: any renderer displays it and never composes it. The
weapons page redesign (#171) consumes this structure; it is not part of this
ticket.

## Context & Measurement

### Where reason text comes from today

- `ReportDecision.reason` is the slug parsed back out of the generated Notes
  clause: `reason=reason_slug(decision.note)[1]`
  ([report_run.py:309](../src/vault_cleaner/report_run.py#L309)), using
  `_REASON_RE` ([report.py:28](../src/vault_cleaner/report.py#L28)).
- The UI copies it verbatim: `reason: str(decision.reason)`
  ([review_ui.js:101](../src/vault_cleaner/ui/review_ui.js#L101)); the
  Proposals table cell is `el("td", { text: item.reason })`
  ([review_ui.js:1078](../src/vault_cleaner/ui/review_ui.js#L1078)); the
  group heading is `ACTION reason (kind) — N item(s)`
  ([review_ui.js:241-244](../src/vault_cleaner/ui/review_ui.js#L241-L244));
  the Reason filter lists raw slugs through the generic `optionsFor`
  ([review_server.js:1329](../src/vault_cleaner/ui/review_server.js#L1329),
  [review_ui.js:909](../src/vault_cleaner/ui/review_ui.js#L909)).
- The expanded detail row shows the raw clause as "note vault-cleaner would
  write" and the survivor as a bare opaque id, "surviving copy"
  ([review_ui.js:988-990](../src/vault_cleaner/ui/review_ui.js#L988-L990)).

### The six weapon reason slugs and where each is emitted

| Slug | Emitter | Actions | Facts available at the emit site |
|---|---|---|---|
| `dupe-lower` | [dupes.py:251-272](../src/vault_cleaner/rules/dupes.py#L251-L272) | junk; review when soft-protected | survivor row `best`, `survivor_group_ids`, `exact_roll_display_prefix(best)`, `_winner_reason(best_key, key)` ([dupes.py:169](../src/vault_cleaner/rules/dupes.py#L169)) |
| `dupe-tie` | same | same | same; the winner reason is `deterministic id tie-break` |
| `wishlist-trash whole-item` | [weapons.py:86-101](../src/vault_cleaner/rules/weapons.py#L86-L101) | junk; review when soft-protected | `wl`, `item_hash`, `perk_hashes`, `kind` |
| `wishlist-trash roll` | same | same | same |
| `coverage-dominated by` | [coverage.py:210-228](../src/vault_cleaner/rules/coverage.py#L210-L228) | review only | `n`, `m`, partner row `best_b["row"]`, `partner_group_ids` |
| `coverage-uncovered vs` | [coverage.py:254-272](../src/vault_cleaner/rules/coverage.py#L254-L272) | review only | `m`, partner row, `partner_group_ids` |

Reason distribution in the committed golden
(`tests/fixtures/report_snapshot_v2.json`, `weapons_dupes.csv`, no
wishlists), measured with a one-off `json.load` count on 2026-09-25:
`dupe-lower` 3 junk + 2 soft review, `dupe-tie` 1 junk + 1 soft review. Armor
(`armor-similar to`, `armor-last-archetype`, `armor-score`) and ghost
(`ghost-unprotected-surplus`) decisions are also present and must serialize
`"explanation": null`.

### Wishlist source data is available but unused for display

`Wishlist.trash_evidence` holds per-entry `source`, `family` and `activities`
([wishlist.py:128-153](../src/vault_cleaner/wishlist.py#L128-L153)). The
production pipeline passes an evidence-bearing merged wishlist to the rules
([pipeline.py:148-153](../src/vault_cleaner/pipeline.py#L148-L153)). Unit
tests often use `parse_wishlist(...)` without `evidence=True`, where
`trash_evidence is None` ([wishlist.py:201-206](../src/vault_cleaner/wishlist.py#L201-L206)).
Source attribution must therefore be optional.

### Snapshot versioning and consumers

- `SNAPSHOT_SCHEMA_VERSION = 2`
  ([report_run.py:39](../src/vault_cleaner/report_run.py#L39)); the comment
  says snapshot schema changes do not change `RULESET_VERSION`, but saved
  review manifests pin and reject mismatched schemas
  ([review.py:272-273](../src/vault_cleaner/review.py#L272-L273)).
- `snapshot_dict` serializes decisions with `asdict`
  ([report_run.py:421](../src/vault_cleaner/report_run.py#L421)), and both
  server paths use it
  ([server/app.py:549](../src/vault_cleaner/server/app.py#L549),
  [server/session.py:484](../src/vault_cleaner/server/session.py#L484)). The
  server session envelope has its own `schema_version: 1`
  ([server/session.py:490](../src/vault_cleaner/server/session.py#L490)),
  which this ticket does not touch.
- Durable vetoes (`data/overrides.json`) are keyed by id with their own schema
  ([review.py:59](../src/vault_cleaner/review.py#L59)); they are unaffected.
- The golden's file name tracks the schema version: #106 renamed
  `report_snapshot_v1.json` → `report_snapshot_v2.json` when it bumped the
  schema (`git log --follow --name-status -- tests/fixtures/report_snapshot_v2.json`).
  Both `scripts/regenerate_report_snapshot.py:25` and
  `tests/test_report_run.py:33` name the file, and
  `tests/test_report_run.py:266` asserts `schema_version == 2`.

### What approving a review proposal does

`select_approved_proposals` includes an approved decision's row as-is
([review.py:546-565](../src/vault_cleaner/review.py#L546-L565)). A review
decision's tag is the row's original tag
([dupes.py:250](../src/vault_cleaner/rules/dupes.py#L250),
[weapons.py:87](../src/vault_cleaner/rules/weapons.py#L87)), so approving a
review proposal writes the Notes clause and leaves the tag unchanged. The
review-only caveat copy below states exactly that.

### Partner-retention measurement

`dupes.resolve` never proposes its survivor. Soft-reviewed wishlist-trash rows
stay in the dupe pool ([weapons.py:103-111](../src/vault_cleaner/rules/weapons.py#L103-L111)),
so a survivor can in principle also carry a wishlist-trash review decision.
Coverage partners are maximal by matched-set cardinality among undecided rows,
so a coverage partner cannot itself be dominated. The "also proposed" caveat
below is therefore defensive for coverage and live for dupes; it is computed
from the report's decided ids, never assumed.

### Model verification and selection

`handoffs/README.md` lists `MAI-Code-1.1-Flash` as the Bounded-rung primary,
with no user-settable effort (`n/a — adaptive`). Re-checked 2026-09-25 against
the GitHub changelog (<https://github.blog/changelog/2026-08-11-mai-code-1-1-flash-available-in-github-copilot/>):
it is rolling out in GitHub Copilot, selectable in Copilot CLI, VS Code and
other surfaces; the page documents no effort control. Launch it from a local
surface on the allocated branch, never the Copilot cloud agent.

Rung: **Bounded.** The plan fixes the data model, module boundaries, every
user-facing string, the ordering rules and the tests. The implementer
delegates no design choice beyond local structure. The code touches rule
modules, but only to attach presentation data beside existing Notes clauses;
the review path, not the rung, carries that risk. Permitted alternative:
`claude-sonnet-5` (`high`).

## Dependencies and assumptions

- **Issue body vs. current code.** The issue's proposed direction holds. Two
  refinements, both within its scope:
  1. It suggested reusing `weapon_reference` for "keep instead". That helper
     renders Notes-oriented text (`[id …1234; location Vault; Tier 4; MW10;
     roll A / B]`, [duplicate_reference.py:174-199](../src/vault_cleaner/duplicate_reference.py#L174-L199)).
     This plan adds a readable sibling built from the same parts and the same
     `short_id` disambiguation, so a copy has one consistent short id in both
     places.
  2. It listed four explanation parts. This plan adds a fifth, a short
     per-slug `label`, because the grouped headings and the Reason filter
     also show raw slugs.
- **Soft-protection caveats and loadout caveats** are computed at the report
  layer from the same row facts `ReportDecision` already carries
  (`protection_level`, `protection_reason`, `in_loadout`), not inside rules.
- **No dependency on #171 or #172.** #172 (Child 5) depends on this ticket and
  adds its own reasons through the builders defined here. #171 designs the
  future page around this structure.
- **Owner decisions already recorded on #172** (locked "unlock and junk", Aegis
  vs Voltron → review) are not implemented here. The locked caveat below is
  worded so Child 5 can reuse it.

## Proposed Plan & Scope

### Explanation model and builders

#### [NEW] [explanation.py](../src/vault_cleaner/explanation.py)

A presentation-only module with no ranking, grouping, eligibility or rail
logic.

```python
@dataclass(frozen=True)
class ProposalExplanation:
    label: str          # short per-slug title
    why: str            # one or two sentences
    keep_instead: str   # "" when the reasoning names no retained copy
    gives_up: str
    caveats: tuple[str, ...] = ()
```

Constants and builders (names are binding; bodies are the implementer's):

- `LABELS: dict[str, str]`, keyed by the exact slug `reason_slug` returns:

  | Slug | Label (verbatim) |
  |---|---|
  | `dupe-lower` | `Duplicate roll, ranked lower` |
  | `dupe-tie` | `Duplicate roll, ranked equal` |
  | `wishlist-trash whole-item` | `Wishlist rates this weapon trash` |
  | `wishlist-trash roll` | `Wishlist rates this roll trash` |
  | `coverage-dominated by` | `Another copy covers its wishlist rolls` |
  | `coverage-uncovered vs` | `No wishlist roll; another copy has some` |

- `weapon_keep_reference(row, perk_prefix, *, distinguish_from) -> str`: the
  parts below in this order, each omitted when empty, joined with `", "`.
  Every export value goes through `safe_fragment(value, limit=…,
  escape_structure=False)` with the same limits `weapon_reference` uses; the
  id through `short_id(row["Id"], distinguish_from=distinguish_from)`.
  1. `copy {short_id}`
  2. `in the Vault` when the stripped `Owner` equals `Vault`, otherwise
     `on {Owner}`
  3. `Tier {Tier}`
  4. `masterwork tier {Masterwork Tier}`
  5. `crafted level {Crafted Level}` only when `is_crafted(Crafted)` and the
     level is non-empty
  6. `roll {p1} / {p2}` from the last two non-empty entries of `perk_prefix`
     (as `weapon_reference` does)

  Example: `copy …4321 in the Vault, Tier 4, masterwork tier 10, roll Rampage / Kill Clip`.
- `dupe(*, tie: bool, winner: str, keep_instead: str)`. For `tie=False`,
  `winner` must be one of the four `_winner_reason` dimension labels.
  Anything else raises `ValueError`; do not fall back silently.
- `wishlist_trash(*, whole_item: bool, sources: tuple[str, ...], pve_only: bool)`
- `coverage_dominated(*, n: int, m: int, keep_instead: str)`
- `coverage_uncovered(*, m: int, keep_instead: str)`
- `with_context(explanation, *, action, protection_level, protection_reason,
  in_loadout, partner_also_proposed) -> ProposalExplanation`, which returns a
  copy with the context caveats appended after the rule's own caveats.

**Verbatim copy.** `{…}` marks substituted values; nothing else varies.

`dupe-lower`:
- why: `You own another copy with the same perk roll and {dimension}.` where
  `{dimension}` maps `higher Tier` → `a higher Tier`, `higher Masterwork Tier`
  → `a higher masterwork tier`, `higher Crafted Level` → `a higher crafted
  level`, `higher stat total` → `a higher stat total`.
- keep_instead: `weapon_keep_reference(best, exact_roll_display_prefix(best), distinguish_from=survivor_group_ids)`
- gives_up: `Nothing in the perk roll. Kill trackers, mods and mementos are not compared.`

`dupe-tie`:
- why: `You own another copy with the same perk roll that ranks equal on Tier, masterwork tier, crafted level and stat total. One copy is kept, chosen by a fixed ID order.`
- keep_instead and gives_up: as `dupe-lower`.

`wishlist-trash whole-item` / `wishlist-trash roll`:
- why: `A wishlist you use rates every roll of this weapon as trash.` (whole
  item) or `A wishlist you use rates this perk roll as trash.` (roll). When
  `sources` is non-empty, append ` Source: {s1}, {s2}.` (sorted, unique,
  each through `safe_fragment(..., escape_structure=False)`).
- keep_instead: `""`
- gives_up: `This copy. No other copy is named as a replacement; the suggestion rests on the wishlist rating alone.`
- rule caveat when `pve_only`: `That rating is for PvE only and says nothing about PvP use.`

`coverage-dominated by`:
- why: `Another copy of this weapon matches every curated wishlist roll this one matches, and more ({m} against {n}).`
- keep_instead: `weapon_keep_reference(best_b["row"], exact_roll_display_prefix(best_b["row"]), distinguish_from=partner_group_ids)`
- gives_up: `No wishlist-recommended roll. Perks no wishlist recommends may differ, so compare them if you use this copy for something specific.`

`coverage-uncovered vs`:
- why: `This copy matches no curated wishlist roll, while another copy of the same weapon matches {m} curated roll(s).`
  Write `1 curated roll` when `m == 1`, otherwise `{m} curated rolls`; the
  literal `(s)` never appears.
- keep_instead: as `coverage-dominated by`.
- gives_up: `No wishlist-recommended roll. Not being on a wishlist does not make a roll bad, so check it if you use this copy.`

Context caveats, appended by `with_context` in this order, each only when its
condition holds:
1. `action == "review"`: `Review only: approving adds a note in DIM and leaves its tag unchanged.`
2. `protection_level == "soft"` and `protection_reason == "exotic"`: `Exotic, so never tagged junk automatically.`
3. `protection_level == "soft"` and `protection_reason == "locked"`: `Locked in game: unlock it before dismantling.`
4. `in_loadout`: `In a DIM loadout: dismantling it breaks that loadout.`
5. `partner_also_proposed`: `The copy suggested to keep is also proposed in this report. Decide on both together.`

### Rules attach explanations beside their existing clauses

#### [MODIFY] [dupes.py](../src/vault_cleaner/rules/dupes.py#L183-L197)

Add `explanation: ProposalExplanation | None = None` as the **last** field of
`Decision`, after `effective_protection`, so armor and ghost constructors are
untouched. In `resolve` ([dupes.py:242-272](../src/vault_cleaner/rules/dupes.py#L242-L272))
build the explanation once per loser from `rel == "dupe-tie"`,
`_winner_reason(best_key, key)` and the keep reference, and pass it to
`Decision(...)`. The `hashtag`, `action`, `tag`, `note` and `kept_id`
expressions stay byte-for-byte identical.

#### [MODIFY] [weapons.py](../src/vault_cleaner/rules/weapons.py#L77-L101)

At the existing trash decision, when `wl.trash_evidence is not None`, collect
`entries = [e for e in wl.trash_evidence.get(item_hash, []) if not e.perks or e.perks <= perk_hashes]`.
Then `sources = tuple(sorted({e.source for e in entries}))` and
`pve_only = bool(entries) and all(e.activities == frozenset({"pve"}) for e in entries)`.
Without evidence, `sources = ()` and `pve_only = False`. Pass
`wishlist_trash(whole_item=(kind == "whole-item"), ...)`. Keep `trash_match`,
the keep-conflict handling and every existing expression unchanged.

#### [MODIFY] [coverage.py](../src/vault_cleaner/rules/coverage.py#L203-L272)

In both branches, pass `explanation=coverage_dominated(...)` /
`coverage_uncovered(...)` using the already-computed `n`, `m`, partner row and
`partner_group_ids`. Partner selection, `partner_reason`, clause text and
counts stay unchanged.

### Report projection and snapshot

#### [MODIFY] [report_run.py](../src/vault_cleaner/report_run.py#L39-L104)

- `SNAPSHOT_SCHEMA_VERSION = 3`. Extend the adjacent comment with one sentence:
  schema 3 adds the presentation-only per-decision `explanation`.
  `RULESET_VERSION` stays 5.
- `ReportDecision` gains `explanation: ProposalExplanation | None = None` as
  its last field.
- In `_decision_records` ([report_run.py:259-321](../src/vault_cleaner/report_run.py#L259-L321)),
  compute `decided_ids = {str(d.id) for d in decisions}` once. For each
  decision with `decision.explanation is not None`, set
  `explanation=with_context(decision.explanation, action=decision.action,
  protection_level=level, protection_reason=protection_reason,
  in_loadout=<the same expression used for in_loadout>,
  partner_also_proposed=bool(decision.kept_id) and str(decision.kept_id) != str(decision.id) and str(decision.kept_id) in decided_ids)`.
  Decisions without an explanation keep `None`.
- `snapshot_dict` needs no code change: `asdict` nests the dataclass and
  `json` writes `caveats` as a list. Armor and ghost decisions serialize
  `"explanation": null`.

The review-manifest format ([review.py:56-57](../src/vault_cleaner/review.py#L56-L57))
and its `reason` identity field are **unchanged**. Explanations are never read
back from a manifest or from `Notes`.

#### [MODIFY] Golden rename and regeneration

- `git mv tests/fixtures/report_snapshot_v2.json tests/fixtures/report_snapshot_v3.json`,
  update `GOLDEN` in `scripts/regenerate_report_snapshot.py:25` and
  `tests/test_report_run.py:33`, change `tests/test_report_run.py:266` to
  `== 3`, then run `python scripts/regenerate_report_snapshot.py`.
- The golden diff after the rename must consist only of `schema_version` and
  the added `explanation` members. The `fingerprint` and every other decision
  field stay identical (the fingerprint excludes the schema version:
  `test_snapshot_schema_version_does_not_change_input_fingerprint`,
  [test_report_run.py:796](../tests/test_report_run.py#L796)).

### Review UI (current renderer)

#### [MODIFY] [review_ui.js](../src/vault_cleaner/ui/review_ui.js#L68-L130)

- `itemsFromSnapshot`: add `explanation: explanationOf(decision.explanation, where)`
  and `reasonLabel`. `explanationOf` returns `null` for `null`/`undefined`.
  It throws `new Error(where + ".explanation must be an object or null")`
  for a non-object (use the existing `isObject`) and
  `new Error(where + ".explanation.caveats must be an array")` when
  `caveats` is not an array. Otherwise it returns `{ label, why, keepInstead,
  givesUp, caveats }` with every string passed through `str()`.
  `reasonLabel = explanation && explanation.label ? explanation.label : str(decision.reason)`.
- `groupItems` / `groupLabel` ([review_ui.js:241-272](../src/vault_cleaner/ui/review_ui.js#L241-L272)):
  grouping keys and ordering are unchanged (still `action, kind, reason`).
  Each group records `reasonLabel` from its first item. The heading becomes
  `ACTION {reasonLabel} [{reason}] ({kind}) — N item(s)` when
  `reasonLabel !== reason`, and is **byte-identical to today** otherwise
  (armor and ghost groups).
- New exported helper `reasonOptions(viewItems, allLabel)`: like
  `optionsFor(viewItems, "reason", allLabel)`, but the option text is
  `{reasonLabel} ({count})` while the option value remains the slug. Add it
  to the returned API object ([review_ui.js:1760-1781](../src/vault_cleaner/ui/review_ui.js#L1760-L1781)).
- Reason cell ([review_ui.js:1078](../src/vault_cleaner/ui/review_ui.js#L1078)):
  `el("td", { class: "reason-cell" }, [el("span", { class: "reason-label", text: item.reasonLabel }), item.explanation ? el("span", { class: "sub reason-why", text: item.explanation.why }) : null])`.
  Sorting by the Reason column still sorts by the slug field.
- `detailRow` ([review_ui.js:985-1005](../src/vault_cleaner/ui/review_ui.js#L985-L1005)):
  when `item.explanation` is present, prepend `definition("why suggested", why)`,
  `definition("keep instead", keepInstead)` and
  `definition("what you give up", givesUp)`. Then add, only when there are
  caveats, `dt` "caveats" with a `dd` containing a `ul` of one `li` per caveat,
  all built through `el`/`textContent`. The existing definitions follow
  unchanged.

#### [MODIFY] [review_server.js](../src/vault_cleaner/ui/review_server.js#L1328-L1331)

The Reason select uses `view.reasonOptions(state.items, "any reason")`. The
other three selects keep `optionsFor`. Filtering still compares
`item.reason` to the slug
([review_ui.js:214](../src/vault_cleaner/ui/review_ui.js#L214)).

#### [MODIFY] [review.css](../src/vault_cleaner/ui/review.css)

`.reason-cell .reason-why { display: block; overflow-wrap: anywhere; }` and a
`.detail dd ul` rule with no bullets indent beyond the existing `dl` rhythm.
No inline `style` attributes (CSP `style-src 'self'`).

### Automated proof

#### [NEW] [test_explanation.py](../tests/test_explanation.py)

- Every builder's exact output against the verbatim copy above: all four
  `dupe-lower` dimensions, tie, unknown winner → `ValueError`, wishlist
  whole-item and roll with and without sources, `pve_only`, uncovered `m == 1`
  and `m == 3`, dominated.
- `with_context`: each caveat alone, all five together in the fixed order, and
  none for a junk, unprotected, non-loadout decision without a proposed
  partner.
- `weapon_keep_reference`: Vault vs character owner, empty owner, crafted with
  and without level, non-crafted with a stale level (omitted), and hostile
  values (control characters, a `#vc-` marker, and a 200-character name) that
  stay single-line and bounded.
- **Label/slug agreement:** for every emitting branch, run the real rule on
  fixture rows and assert `LABELS[reason_slug(d.note)[1]] == d.explanation.label`.
  This is the drift guard between Notes and labels.

#### [MODIFY] [test_weapons_rules.py](../tests/test_weapons_rules.py), [test_dupes.py](../tests/test_dupes.py), [test_coverage.py](../tests/test_coverage.py)

Add explanation assertions beside existing decision assertions: the
dupe junk and soft-review paths, wishlist trash with an evidence-bearing
wishlist (`parse_wishlist(..., evidence=True)`, `source` and PvE activity
present) and without evidence, and both coverage branches using the committed
coverage fixtures. **No existing assertion on `action`, `tag`, `note`,
`kept_id` or counts may be edited or deleted.**

#### [MODIFY] [test_report_run.py](../tests/test_report_run.py)

Schema 3 and the golden rename. Add: every weapons-section decision in the
golden has a non-null explanation, and every armor or ghost decision has
`null`. Add a `_decision_records` test in which a decision's `kept_id` is
itself decided, asserting the "also proposed" caveat, and a
soft-locked, in-loadout review decision asserting caveats 1, 3 and 4 in order.

#### [MODIFY] [test_review_ui_js.py](../tests/test_review_ui_js.py) and [test_server_ui_js.py](../tests/test_server_ui_js.py)

Node coverage for:
- `itemsFromSnapshot` accepting `null` and a valid explanation, and throwing
  on a non-object explanation and on non-array caveats;
- `groupLabel` byte-identical output for items without an explanation, and the
  `label [slug]` form with one;
- `reasonOptions` text and values;
- the Reason cell and detail rows rendered with a hostile explanation
  (`<img src=x onerror=alert(1)>` in every string field and in a caveat) that
  stays inert text.

Update existing assertions that read the Reason cell's text only where the
cell now contains the label and the why line.

#### [MODIFY] [test_server_browser.py](../tests/test_server_browser.py)

One Chromium assertion on the existing weapons-dupes flow: a weapon row's
Reason cell shows `Duplicate roll, ranked lower` and its why sentence, and
expanding the row shows "why suggested", "keep instead" and "what you give up".

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

A dated implementation entry, including the golden diff summary and any Reason
cell assertions updated.

## Mechanical inclusion test

A proposed change is **in scope** if and only if it does one of these:
- adds the explanation model, builders, labels or keep reference in
  `src/vault_cleaner/explanation.py`;
- attaches an explanation to a weapon `Decision` at one of the six emit sites,
  computed from values those sites already compute;
- carries the explanation through `ReportDecision` / `snapshot_dict` and bumps
  `SNAPSHOT_SCHEMA_VERSION` with the golden rename and regeneration;
- displays the explanation or label in the current Proposals UI as specified;
- tests or documents any of the above, including updating a test that asserted
  the old Reason cell text, the golden's name, or schema version 2.

Worked examples:
- **IN SCOPE:** passing `explanation=dupe(tie=False, winner="higher Masterwork Tier", keep_instead=ref)`
  into the existing `Decision(...)` call in `dupes.resolve`.
- **IN SCOPE:** changing `tests/test_report_run.py:266` from `== 2` to `== 3`.
- **IN SCOPE:** updating a Node assertion that expected the Reason cell's text
  to be exactly `dupe-lower`.
- **OUT OF SCOPE:** changing any `#vc-` clause text, `note_history`
  recognizer, `reason_slug`, or `_REASON_RE`.
- **OUT OF SCOPE:** changing which copy survives, which partner is chosen, any
  action or tag, or `RULESET_VERSION`.
- **OUT OF SCOPE:** explanations for armor or ghost decisions; changing the
  armor duplicates view's "Proposal reason:" line.
- **OUT OF SCOPE:** changing the CLI `report` / `summarize` output, the review
  manifest format, the server session envelope, or durable overrides.
- **OUT OF SCOPE:** visual redesign beyond the specified cell, detail rows and
  two CSS rules (#171), or a Jinja template (#137 / #138).
- **OUT OF SCOPE:** Child 5 reasons such as "unlock and junk" or
  `aegis-trash-voltron-keep` (#172).

### Stop conditions

Stop implementation and return to the orchestrator if:
- producing an explanation requires a value the emit site does not already
  compute, or requires changing an existing expression there;
- the regenerated golden differs in anything other than `schema_version` and
  added `explanation` members;
- any existing rule-test assertion on `action`, `tag`, `note`, `kept_id` or
  counts would need to change;
- `_winner_reason` returns a value for a `dupe-lower` loser outside the four
  mapped dimensions on any fixture;
- a verbatim string above reads as untrue for a real case you encounter (for
  example, a soft-protected reason other than `exotic` or `locked`). Report
  the case; do not reword the copy.
- the server or a test consumes the snapshot `decisions` shape strictly
  enough that adding a key fails outside the files listed above.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Decision drift hidden by the schema bump.** A regenerated golden is easy
   to accept wholesale. Review the rename-aware diff
   (`git diff -M base...head -- tests/fixtures/`) and confirm that only
   `schema_version` and `explanation` members change.
2. **Copy drift.** Strings paraphrased rather than copied, an `(s)` left in,
   or caveats out of order. `test_explanation.py` must pin exact strings, not
   substrings.
3. **Hostile text reaching markup.** A caveat list or keep reference built
   with `innerHTML` or string concatenation into markup, or a keep reference
   that skips `safe_fragment`.
4. **Heading and filter regressions for armor and ghosts.** `groupLabel` must
   be byte-identical for groups without an explanation. The Reason filter's
   values must stay slugs, or URL/query state and existing filter tests
   break silently.

# Reusable implementer execution prompt

Implement issue #170 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-170-implementation-plan.md
```

Read the entire handoff, issue #170, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-170-proposal-explanations`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- copy every user-facing string in the plan verbatim;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `VAULT_CLEANER_BROWSER_REQUIRED=1 .venv/bin/pytest -q -m browser tests/test_server_browser.py`, `git diff --check origin/main...HEAD`, and `git ls-files data/` (must print nothing);
- commit and push the implementation branch; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, return to the orchestrator: the base and head SHAs, the changed-file list, the full output of each verification command, a summary of the renamed golden's diff, every pre-existing test assertion you edited with its reason, and any deviations from the plan.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
The change is additive and presentation-only in intent, but it edits all three
weapon rule modules at their decision-emit sites. It also changes the
snapshot schema every consumer reads, and adds new untrusted-text rendering
paths in the browser. The failure modes are quiet: an accidentally altered
decision hidden inside a regenerated golden, or hostile export text reaching
markup. That matches the #140 guidance to use independent adversarial review
for ranking, decision-state and parser-adjacent changes.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

# Review checklist

- [ ] Every production hunk passes the mechanical inclusion test; no `#vc-` clause, recognizer, `reason_slug`, rail, ranking or partner-selection line changed.
- [ ] The rename-aware golden diff shows only `schema_version: 3` and added `explanation` members; the fingerprint is unchanged, and `RULESET_VERSION` is still 5.
- [ ] Every string in `explanation.py` matches the plan verbatim, pinned by exact-equality tests. The label/slug agreement test runs real rules for all six slugs.
- [ ] Caveat order and conditions match the plan; the "also proposed" test uses a real decided `kept_id`.
- [ ] Wishlist attribution works with and without evidence, and `pve_only` is false when any matching entry is not exactly PvE.
- [ ] UI builds every explanation node via `el`/`textContent`; the hostile explanation test covers every field and a caveat.
- [ ] `groupLabel` is byte-identical for armor and ghost groups; Reason filter values are still slugs.
- [ ] No existing assertion on decision fields was edited; edited UI assertions are limited to the Reason cell text, the golden name and schema 2.
- [ ] Review manifest, server session envelope, overrides and CLI output are unchanged.
- [ ] `ruff`, `pytest`, the required Chromium suite (a skip is a failure), `git diff --check`, empty `git ls-files data/`, and a `WORKLOG.md` entry all pass.

# Dispatch comment draft

Planned #170 in [handoffs/issue-170-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-170-implementation-plan.md) on `main`.

- **Implementer model & effort:** `MAI-Code-1.1-Flash` (`n/a — adaptive`), Bounded rung; permitted alternative `claude-sonnet-5` (`high`)
- **Implementation branch:** `feat/issue-170-proposal-explanations`
- **Likely findings:** decision drift hidden by the schema-3 golden regeneration; paraphrased or misordered copy; hostile text reaching markup in new cells, detail rows or caveat lists; armor/ghost heading or Reason-filter value regressions.
