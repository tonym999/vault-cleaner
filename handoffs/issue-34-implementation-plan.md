# Issue #34 — implementation handoff

# Ticket

**Repository:** `tonym999/vault-cleaner`

**Issue:** `#34 — Child 4: same-Hash useful-combination coverage for weapons (review-only)`

**Milestone:** `none` (cleared on 2026-09-20; this is a weapons ticket and its landed siblings #148, #155 and #158 carry none)

**Implementation topology:** `planner → orchestrator → implementer → orchestrator-managed review (standard or independent adversarial) → PR`

**Planner model:** `claude-opus-5` (`xhigh`)

**Implementation model selected:** `gpt-5.6-luna` (`high`) (Judgement rung; justified below)

**Plan baseline:** `main` at `775f662377803dcff2e58dd401ed9e723877b19b` (2026-09-20)

**Allocated implementation branch:** `feat/issue-34-coverage-review`

The implementer must **not** open a pull request. The implementation branch is reviewed under orchestrator ownership before any PR is created.

This document uses role-neutral names (planner, orchestrator, implementer, independent adversarial reviewer).

## Objective

Add a review-only weapons pass that compares copies of the same item `Hash` by the **useful perk combinations each copy can actually provide**, and flags — for manual review, never as junk — copies whose useful coverage is wholly contained in another copy's.

This is Child 4 of [#140](https://github.com/tonym999/vault-cleaner/issues/140). The exact-dupe pass from #31 is effectively exhausted on the owner's real vault (one group with more than one member, §"Measured yield"), so coverage is the next lever toward the umbrella's ~190-removal requirement. The pass must deliver that lever **without ever discarding a roll that provides coverage no other copy does** — the invariant #31 was filed to protect.

## Context & Measurement

All figures below come from [docs/evidence/issue-34/README.md](../docs/evidence/issue-34/README.md), measured on 2026-09-20 against `main` at `775f662` using the real export `data/in/2026-09-01T-current/weapons.csv` (665 weapons, 438 hashes), the configured wishlists, and cached manifest `244213.26.06.29.2000-1-bnet.65583`. The owner authorised real-export measurement for this ticket on 2026-09-20 (aggregate counts, distributions and item names only).

### Combinations are read from the wishlists, never enumerated

The original #34 body proposed enumerating "combinations the weapon can actually select". **That is not measurable from the export.** #31 established the `Perks N` prefix as an ordered tuple of available options and deliberately did *not* establish which cells belong to which socket ([rules/dupes.py:1-31](../src/vault_cleaner/rules/dupes.py#L1-L28)). Without a measured socket partition, enumerating selectable combinations is guesswork, and guessing would violate #34's own "do not form impossible cross-column combinations" criterion.

It is also unnecessary. A curated keep roll **is** an author-asserted valid combination, and the existing subset test already answers "can this copy provide it?":

- `matched(X)` = every curated keep roll for the item's `Hash` whose perk hashes are a subset of copy `X`'s perk hashes — today's keep-match semantics from [rules/weapons.py:46-48](../src/vault_cleaner/rules/weapons.py#L46-L47).
- Perk hashes are canonicalised so base and enhanced variants sharing a display name collapse onto one token. [manifest.py:36](../src/vault_cleaner/manifest.py#L36)'s `PerkMapData.names` already maps one display name to *all* its hash variants, so inverting it yields the canonical token map.
- **Displayed** counts collapse recommendations subsumed by a more specific matched one (a traits-only Aegis roll inside a four-perk Voltron roll is one combination, not two). Measured: collapsing changes 46 of 301 matched rows.

### Comparisons use the uncollapsed matched sets

`matched` is downward closed: if copy `B` matches a roll `r`, and `r' ⊆ r` is also curated for that `Hash`, then `B` matches `r'` too. So `matched(A) ⊆ matched(B)` is exactly "B provides everything A does".

Comparing the *collapsed* sets instead is wrong and measurably lossy. Evidence §1 block `[7]` classifies the same ordered pairs both ways: collapsed comparison yields 27 dominance candidates against the uncollapsed test's 30, missing three (Gizmo Weft, Reghusk's Pledge, Stars in Shadow) and claiming none the uncollapsed test does not. The cause is that a copy matching a four-perk Voltron roll semantically covers a two-perk Aegis roll whose collapsed element is a different set. **Compare uncollapsed; display collapsed.** This is the single easiest thing to get backwards in this ticket, and because the error is strictly a loss of relations it cannot be caught by asserting that no false advice appears.

### Perk scope

The pass reuses [`rules.weapons.row_perk_hashes`](../src/vault_cleaner/rules/weapons.py#L29-L43), which reads every `Perks N` cell, rather than restricting to #31's immutable pre-tracker prefix. Measured, the two scopes are equivalent on the real export: **0 rows** differ and both yield 929 matched rolls (evidence §2). Reusing the existing helper keeps one definition of "matches a keep roll" across the wishlist-trash path and this pass.

### Measured yield

Among 116 hashes holding 339 undecided, groupable instances with at least two distinct rolls:

| Relation among distinct rolls of one `Hash` | Instances |
|---|---|
| Mutual trade-off — each copy covers something the other cannot → keep both | 148 |
| `coverage-dominated by` candidates | 30 (21 unprotected, 9 soft, 0 hard, 4 in a loadout) |
| `coverage-uncovered vs` candidates | 53, of which 50 are not hard-protected (28 unprotected, 22 soft) |
| Equal coverage, different roll | 13 |
| Neither copy covered — no evidence either way | 114 |

The two advice sets do not overlap. Expect **80 new review-only proposals** on the owner's current export.

### Consensus is degenerate unless it is subsumption-aware

[`wishlist_evidence.item_evidence`](../src/vault_cleaner/wishlist_evidence.py#L40) counts supporting **families**, never sources, so Aegis conversions cannot pose as independent experts. Measured on this export, exact-identity agreement is degenerate: all 823 matched combinations have exactly one family, because the Aegis feed is traits-only while Voltron rolls carry four perks. Counting a family as supporting a combination when one of its *matched* rolls is a subset of it makes the signal real: 724 combinations at one family, 99 at two.

### Pipeline position

The pass runs last in the weapons pipeline, on copies the earlier passes left undecided — mirroring armor's exact → close ordering in [pipeline.py:161-205](../src/vault_cleaner/pipeline.py#L161-L205). Measured pipeline position on the real export (evidence §1 block `[4]`, taken from the decisions `weapons.run` actually emits): 21 prior decisions remove their rows — 11 `wishlist-trash` junk, **8 soft-protected `wishlist-trash` review**, and 2 `dupe-lower` review — leaving **644** groupable copies for the coverage pass.

The soft-protected trash reviews are the easy ones to miss: they deliberately stay in the *dupes* pool ([rules/weapons.py:101-106](../src/vault_cleaner/rules/weapons.py#L101-L106)) but they do carry a decision, so the coverage filter must exclude them. Take the pool from the emitted decision ids rather than recomputing which rows the earlier passes would have decided.

## Dependencies and assumptions

- **#31 (closed)** is authoritative. `exact_roll_fingerprint` ([rules/dupes.py:151](../src/vault_cleaner/rules/dupes.py#L151)) decides which copies are the *same* roll; this pass only ever compares copies with **different** fingerprints, and never compares a copy whose fingerprint is `None`.
- **#148 (closed) added no safety rail.** [#140](https://github.com/tonym999/vault-cleaner/issues/140)'s tracking comment and §8 item 4 of [docs/aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md) both say weapons in a DIM loadout are hard-protected. **That premise was reversed by the owner before #148 was implemented** (see the #148 entry in [WORKLOG.md](../WORKLOG.md)): `rails.protection` ([rules/rails.py:30-56](../src/vault_cleaner/rules/rails.py#L30-L56)) has no loadout clause, and 4 of the 30 dominance candidates are in a loadout. Loadout membership is presentation here, not protection. Do not add a rail.
- **#158 (closed)** supplies the evidence model. Its `family`/`activity`/`tier_format` fields are deliberately outside `WishlistSourceIdentity` and the fingerprint, with that inclusion handed to Child 5 "when a rule first consumes them" ([docs/wishlist-evidence.md](../docs/wishlist-evidence.md) §1). **This plan keeps that handoff intact by keeping `family` out of every decision input and out of the generated `Notes` clause.** Consensus is dry-run output only.
- **Stale in the spike's child map:** [docs/aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md) §12 names the new module `combinations.py`. This plan names it `coverage.py`, because the pass deliberately does not enumerate combinations. §8 item 10 also assigns the `RULESET_VERSION` 4 → 5 bump to Child 5; this ticket takes 4 → 5 and Child 5 will take 5 → 6.
- **Owner decisions recorded on #34 (2026-09-20):** both advice kinds are in scope; the pass runs by default rather than behind a config gate.
- `--no-wishlists` reaches the early return in [pipeline.py:139-144](../src/vault_cleaner/pipeline.py#L139-L144), so the coverage pass is unreachable without wishlists and the zero-network fallback is unchanged.

## Proposed Plan & Scope

### Rule pass

#### [NEW] [rules/coverage.py](../src/vault_cleaner/rules/coverage.py)

Module docstring states the measured basis: combinations come from curated wishlist rolls, comparison is on uncollapsed matched sets, display counts are collapsed, and absence of coverage is uncertainty rather than trash evidence.

```python
@dataclass(frozen=True)
class CoverageSummary:
    compared_instances: int
    dominated: int
    uncovered: int
    combination_counts: tuple[tuple[int, int], ...]        # (combinations, rows), ascending
    consensus_counts: tuple[tuple[int, int], ...] | None   # (families, combinations); None without evidence


@dataclass(frozen=True)
class CoverageAnalysis:
    decisions: tuple[Decision, ...]
    summary: CoverageSummary


def canonical_perk_tokens(perk_map: dict[str, frozenset[int]]) -> dict[int, int]: ...
def matched_rolls(item_hash, perk_hashes, wl, tokens) -> frozenset[frozenset[int]]: ...
def collapse(rolls: frozenset[frozenset[int]]) -> frozenset[frozenset[int]]: ...
def analyse(weapons, wl, perk_map, crafted_level_protect) -> CoverageAnalysis: ...
```

`CoverageSummary` field semantics, so the dataclass and the printed contract cannot drift: `compared_instances` counts copies in a `Hash` group holding at least two distinct rolls; `dominated` and `uncovered` count the clauses actually emitted, so hard-protected candidates are excluded from `uncovered`; `combination_counts` and `consensus_counts` are ascending `(value, count)` pairs over those compared copies.

- `canonical_perk_tokens` inverts `PerkMapData.names` deterministically: iterate names in sorted order, use `min(hashes)` as the token, first name wins for a hash that appears under several. A hash absent from the map maps to itself, so an unknown perk stays distinct rather than silently merging.
- `collapse` keeps only maximal elements under `⊆`.
- `analyse` groups by `Hash` over rows whose `exact_roll_fingerprint` is not `None`, and within a group compares only rows with different fingerprints. Hard-protected rows receive no advice but remain eligible partners. For each candidate `A`:
  - **dominated** when some partner `B` has `matched(A)` non-empty and `matched(A) < matched(B)`. Best partner: largest `len(collapse(matched(B)) - collapse(matched(A)))`, then lowest `instance_id_order`.
  - **uncovered** when `matched(A)` is empty and some partner `B` has non-empty `matched(B)`. Best partner: largest `len(collapse(matched(B)))`, then lowest `instance_id_order`.
  - otherwise nothing. Equal coverage, mutual trade-offs and mutually uncovered pairs produce no decision.
  - Each copy receives **at most one** clause, dominance taking precedence (the two conditions are mutually exclusive anyway).
- Emitted `Decision`s use `action="review"`, `tag=row["Tag"]` (tag preserved — the import must be a tag no-op), `kept_id=<partner id>`, and `note=append_tool_clause(row["Notes"], hashtag)`.
- The returned decision sequence is sorted by `instance_id_order(decision.id)`, mirroring [rules/armor_close.py:260-263](../src/vault_cleaner/rules/armor_close.py#L260-L263), so CSV row order cannot reorder the report.
- `consensus_counts` is `None` when `wl.keep_evidence` is `None`; the pass must not raise on an evidence-free wishlist.

**Exact clause formats** (the emitter contract; these strings are the ticket's user-facing copy):

```text
#vc-review: coverage-dominated by; compare [REF]; combinations N vs M; partner largest coverage gain
#vc-review: coverage-dominated by; compare [REF]; combinations N vs M; partner deterministic id tie-break
#vc-review: coverage-uncovered vs; compare [REF]; combinations 0 vs M; partner most combinations
#vc-review: coverage-uncovered vs; compare [REF]; combinations 0 vs M; partner deterministic id tie-break
```

`REF` is `weapon_reference(partner_row, exact_roll_display_prefix(partner_row), distinguish_from=<the other instance ids in that Hash group, sorted by instance_id_order>)`, reused verbatim from [rules/dupes.py:253,261](../src/vault_cleaner/rules/dupes.py#L253). `N` is the candidate's collapsed combination count, `M` the partner's. "combinations" stays plural in every case so the recognizer needs no alternation. `partner <reason>` names the first decisive dimension of the partner choice, exactly as the close pass does.

#### [MODIFY] [rules/weapons.py:59-111](../src/vault_cleaner/rules/weapons.py#L59-L111)

- `RunResult` gains `coverage: coverage.CoverageSummary | None = None`.
- After `decisions.extend(...)` at [line 110](../src/vault_cleaner/rules/weapons.py#L110), run the coverage pass over the rows that hold no decision yet:

```python
decided = {d.id for d in decisions}
analysis = coverage.analyse(
    weapons[~weapons["Id"].isin(decided)], wl, perk_map, crafted_level_protect
)
decisions.extend(analysis.decisions)
result.coverage = analysis.summary
```

Passing only undecided rows is what guarantees a cited partner is never itself a junk proposal. It is reinforced structurally: `weapons.run` only emits a wishlist-trash decision when keep matches are zero ([line 79](../src/vault_cleaner/rules/weapons.py#L79)), and every partner has non-empty coverage, so a partner can never be a trash candidate. Dominance is a strict partial order, so a chain (`A` cites `B`, `B` cites `C`) is possible but a cycle is not.

#### [MODIFY] [pipeline.py:44-49,132-156](../src/vault_cleaner/pipeline.py#L132-L156)

- `WeaponPipelineResult` gains `coverage: CoverageSummary | None = None`.
- `resolve_weapons` switches `load_all_with_sources` → `load_all_with_evidence` and passes `evidence.merged` to `weapons_rules.run`, so family consensus is available. `WishlistSourceData` is identical on both paths, so `_wishlist_identities` and the fingerprint are unaffected, and #158's `test_decision_invariance_under_load_all` already pins decision equality between the two loaders. Measured cost from the #158 entry in [WORKLOG.md](../WORKLOG.md): wishlist parsing goes from ~0.57 s to ~1.88 s and peak memory from ~138 MB to ~238 MB, against a 600 MB ceiling.
- The `no_wishlists` early return keeps `coverage=None`.

### Notes history

#### [MODIFY] [note_history.py:44-79](../src/vault_cleaner/note_history.py#L44-L79)

Add one recognizer covering both clauses, so a second run replaces the previous coverage clause instead of accumulating copies:

```python
(
    r"#vc-review: coverage-(?:dominated by|uncovered vs); "
    r"compare \[[^\]\r\n]*\]; combinations [0-9]+ vs [0-9]+; partner "
    r"(?:largest coverage gain|most combinations|deterministic id tie-break)"
),
```

`report.reason_slug` ([report.py:28-42](../src/vault_cleaner/report.py#L28-L42)) needs no change: its existing pattern yields `coverage-dominated by` and `coverage-uncovered vs`.

### Presentation

#### [MODIFY] [cli.py:173-218](../src/vault_cleaner/cli.py#L173-L218)

- `_resolve_weapons` returns the coverage summary alongside the existing tuple members.
- **The existing `resolved:` line must lose its `(soft-protected)` claim.** [cli.py:210](../src/vault_cleaner/cli.py#L210) currently prints `resolved: {j} junk, {r} review (soft-protected){wl_note}`, which was true while every review came from a soft rail. Coverage advice makes it false: 49 of the ~80 new review candidates carry no rail at all (evidence §1 block `[6]`). Replace it with the neutral form, keeping `wl_note` unchanged:

```python
print(f"resolved: {len(junk)} junk, {len(review)} review{wl_note}")
```

  The per-item lines already carry each decision's own `(locked)` / `(exotic)` reason, and the coverage lines below give the coverage breakdown, so no information is lost. Add a CLI regression test asserting that a run containing an unprotected coverage review does not describe its review total as soft-protected.
- `_cmd_dupes` prints, after that line and only when a summary is present:

```python
print(
    f"coverage: {s.dominated} dominated, {s.uncovered} uncovered vs a covered copy "
    f"— review-only, from {s.compared_instances} compared copies"
)
distribution = ", ".join(f"{n}: {rows}" for n, rows in s.combination_counts) or "none"
print(f"coverage combinations per compared copy — {distribution}")
if s.consensus_counts is not None:
    support = ", ".join(f"{families}: {count}" for families, count in s.consensus_counts)
    print(f"coverage evidence: combinations by supporting curation family — {support}")
```

Both distributions are reported over **compared copies only** — the copies that entered at least one same-`Hash` comparison — not over every analysed row. A distribution covering copies nothing was compared against is not evidence about coverage. `combination_counts` includes the zero bucket, because "no curated combination available" is the single most common state and hiding it would overstate coverage.

Expected values on the real export, from evidence §1 block `[8]`, which an implementer can check their output against:

```text
compared_instances=339 dominated=30 uncovered=50
combination_counts=[(0, 143), (1, 58), (2, 66), (3, 10), (4, 43), (5, 4), (6, 7), (8, 3), (9, 2), (10, 2), (12, 1)]
consensus_counts=[(1, 459), (2, 69)]
```

Note that block `[3]`'s consensus figures (724 / 99) span every row in the export, so they are deliberately larger than the summary's compared-copy figures. Add CLI assertions for all three lines, so an implementation following this handoff satisfies #34's "combination counts and family consensus appear in dry-run output" criterion rather than merely defining the field.

No review-UI, server, snapshot or `config.toml` change is in scope. The new decisions reach the review UI through the existing proposal path, whose reason filter is data-driven.

### Versioning

#### [MODIFY] [report_run.py:44](../src/vault_cleaner/report_run.py#L44)

`RULESET_VERSION` 4 → 5, with a comment recording that ruleset v5 adds the review-only weapon coverage pass. `SNAPSHOT_SCHEMA_VERSION` stays 2 — nothing about the snapshot's shape changes. The bump invalidates persisted vetoes by design; say so in the WORKLOG entry.

#### [MODIFY] [tests/fixtures/report_snapshot_v2.json](../tests/fixtures/report_snapshot_v2.json)

Regenerate with `python scripts/regenerate_report_snapshot.py`. That golden is built with `no_wishlists=True`, so the only expected delta is `ruleset_version` and the fingerprint derived from it. **A decision-level diff in that golden means the pass ran without wishlists and is a bug.**

### Tests

#### [NEW] [tests/fixtures/weapons_coverage.csv](../tests/fixtures/weapons_coverage.csv) and [tests/fixtures/wishlist_coverage.txt](../tests/fixtures/wishlist_coverage.txt)

Synthetic rows pinned to the real export header (copy it from an existing weapons fixture), fake items only. Generate any CSV with `lineterminator="\n"`. Cover: a strict-subset pair; a mutual trade-off pair; an equal-coverage pair with different rolls; a mutually uncovered pair; an uncovered-versus-covered pair; two sources recommending the same roll (consensus 2); a base/enhanced variant pair of one display name; a hard-protected copy that must be a partner but never a candidate; a soft-protected (locked or exotic) candidate; one ungroupable row with no tracker boundary; and — for the two tie-break branches — a `Hash` group of at least three distinct rolls in which two partners tie on gain, once for a dominated candidate and once for an uncovered one. An earlier prior-pass decision on a row that would otherwise be compared is worth one row too, so the decided-id exclusion is exercised.

#### [NEW] [tests/test_coverage.py](../tests/test_coverage.py)

At minimum: each relation produces the right decision or none; collapsed-versus-uncollapsed comparison (a case where comparing collapsed sets would miss a real dominance); base/enhanced canonicalisation; consensus counted by family, not source; `keep_evidence=None` yields `consensus_counts is None` without raising; hard-protected candidates get no note but serve as partners; soft-protected candidates keep their existing tag; ungroupable and same-fingerprint rows are never compared; reversing fixture row order changes no decision, partner or ordering; and no coverage decision has `action == "junk"`.

#### [MODIFY] [tests/test_note_history_roundtrip.py](../tests/test_note_history_roundtrip.py)

Add emitter-driven round-trip coverage for **all four emitting branches**, not just the two clause kinds. The emitter contract in [AGENTS.md](../AGENTS.md) covers "each winner or partner label in every emitting branch", and this pass has four: dominated/`largest coverage gain`, dominated/`deterministic id tie-break`, uncovered/`most combinations`, and uncovered/`deterministic id tie-break`. Take the clause text the rule actually emits, feed it back through `strip_trailing_tool_clauses`, and assert the user's original Notes text survives. Follow the pattern the armor close-pass clauses already use there.

**A two-member group cannot reach either tie-break branch**, since a tie needs two partners with equal gain. The fixture must therefore include a `Hash` group of at least three distinct rolls where two candidate partners tie. That is not a contrived shape: 54 of the 116 multi-roll hashes on the real export hold three or more distinct rolls (evidence §1 block `[4]`).

### Documentation

#### [NEW] [docs/weapon-coverage.md](../docs/weapon-coverage.md)

Short specification: the combination model and why nothing is enumerated, the comparison rule and its safety invariants, both clause formats, the consensus definition and its measured degeneracy, and the explicit statement that coverage never tags junk and that graduation needs separate owner approval.

#### [MODIFY] [PLAN.md](../PLAN.md)

Insert the coverage pass into the "Rules engine" ordering as weapons rule 4, renumbering the armor passes that follow.

#### [MODIFY] [WORKLOG.md](../WORKLOG.md)

Dated implementation entry: what landed, the ruleset bump and its veto invalidation, the evidence loader switch with its measured cost, the real-export authorisation for this ticket, and anything surprising.

## Mechanical inclusion test

A change is **in scope** if and only if it is required to:

- add the review-only coverage pass, its module, and its wiring into `weapons.run` and `resolve_weapons`;
- emit, recognise, or round-trip the two clause formats stated verbatim above;
- report coverage counts and family consensus in `dupes` dry-run output;
- bump `RULESET_VERSION` and regenerate the golden that bump invalidates;
- add or adjust fixtures, tests and documentation for the behaviour above.

Worked examples:

- **IN SCOPE:** adding `coverage.py`, calling it from `weapons.run` on undecided rows, and adding its recognizer to `note_history.py`.
- **IN SCOPE:** switching `resolve_weapons` to `load_all_with_evidence` so consensus can be counted.
- **IN SCOPE:** regenerating `report_snapshot_v2.json` after the ruleset bump.
- **OUT OF SCOPE:** any code path that tags a weapon `junk` from a coverage outcome, or changes an existing tag.
- **OUT OF SCOPE:** adding `family`, `activity` or `tier_format` to `WishlistSourceIdentity`, the fingerprint payload or the snapshot — that is Child 5's, per #158's handoff.
- **OUT OF SCOPE:** new `config.toml` keys, `_decision_config` projection changes, or a snapshot schema bump.
- **OUT OF SCOPE:** review-UI or server rendering work, cross-`Hash` comparison, role or activity inference, and the aggressive policy selector.
- **OUT OF SCOPE:** changing `rails.protection`, the wishlist-trash path, or #31's fingerprint, ranking or grouping.

### Stop conditions

Stop implementation and return to the orchestrator if:

- the uncollapsed comparison rule appears wrong against the real code or produces a same-`Hash` relation the plan does not describe;
- eliminating a coverage decision requires reading `family`, `activity` or `tier_format`, or consensus would have to enter a `Notes` clause or any decision input;
- `load_all_with_evidence` changes any existing decision, conflict count, or fingerprint;
- the regenerated golden shows a decision-level diff rather than only the ruleset/fingerprint change;
- a coverage outcome would need to tag junk, change a tag, or suppress a proposal to satisfy a test;
- the pass needs a tunable threshold, and therefore a `config.toml` key and `_decision_config` projection, to behave sensibly.

Escalation route: `implementer → orchestrator → planner`.

## Likely findings

1. **Collapsed-versus-uncollapsed comparison.** The most likely defect is comparing `collapse(matched(A)) ⊂ collapse(matched(B))` because the collapsed sets are already in hand for display. Measured, that drops three of 30 real dominance relations on the real export while inventing none, so it is invisible both to a test suite using single-source fixtures and to any assertion that no wrong advice is emitted. The fixture must pair an Aegis-style subset roll with a Voltron-style superset roll, and the test must assert the relation is **found**, not merely that nothing bogus appears.
2. **Absence treated as evidence.** `matched(A)` empty makes `matched(A) ⊆ matched(B)` vacuously true, so a naive implementation files the 53 uncovered copies under `coverage-dominated by`. They must carry the separate `coverage-uncovered vs` label, and the hard-protected three must receive no clause at all.
3. **Emitter/recognizer drift.** The recognizer regex is hand-written against strings the rule formats elsewhere; a stray space, a singular "combination", or a missing `partner` alternative leaves a clause that accumulates on the next run. The round-trip test must be driven by the emitter's own output, not by a re-typed literal.
4. **Prior review decisions left in the pool.** Soft-protected `wishlist-trash` reviews stay in the *dupes* pool by design, so an implementation that mirrors the dupe pass's filter instead of excluding every decided id will compare eight already-decided copies on the real export and can cite one as a partner. The planner made exactly this mistake in the first revision of the evidence transcript.
5. **Scope leak into presentation or policy.** Snapshot projections, review-UI rendering, or a `config.toml` gate are all adjacent and all out of scope; a diff touching `ui/`, `server/`, `review.py` or `config.toml` is a finding.

# Reusable implementer execution prompt

Implement issue #34 in `tonym999/vault-cleaner` using the committed handoff on `main` at:

```text
handoffs/issue-34-implementation-plan.md
```

Read the entire handoff, issue #34, `AGENTS.md`, `PLAN.md`, recent `WORKLOG.md`, `docs/evidence/issue-34/README.md`, and current relevant code before editing.

Rules:
- work on `feat/issue-34-coverage-review`; branch from latest `main` and record the base SHA;
- apply the plan's mechanical inclusion test to every production hunk;
- update `WORKLOG.md` with a dated entry;
- run all verification commands: `.venv/bin/ruff check src tests scripts`, `.venv/bin/pytest -q`, `python scripts/regenerate_report_snapshot.py` followed by `git diff tests/fixtures/report_snapshot_v2.json`, and `git diff --check origin/main...HEAD`;
- commit and push the implementation branch; and
- **do not open a pull request.**

Make ordinary implementation decisions yourself (local structure, naming, helpers, test shape, following established patterns, fixing failures your own change caused) and explain notable ones in your completion handoff. If any stop condition is reached, or the work needs a design decision the plan did not settle, stop implementation and return to the orchestrator with the exact conflict; do not broaden scope or silently redesign the solution.

When complete, report: base and head SHAs, changed files, the command output above, the decision-level diff of the regenerated golden, any deviation from the plan, and the coverage counts your implementation produces on `tests/fixtures/weapons_coverage.csv`.

# Ticket-specific review decision

**Review path:** `independent adversarial review`

**Reason:**
The change adds a new decision-emitting rule pass, bumps the ruleset version, and invalidates every persisted veto. Its correctness rests on set-theoretic invariants whose failure modes are quiet rather than loud: a collapsed-versus-uncollapsed mix-up silently loses relations, and a vacuous-subset bug converts "no wishlist evidence" into dominance advice — the exact confusion #31 was filed to stop. It also touches the emitter contract for generated `Notes`, where drift between production output and the history recognizer is invisible to green tests. [docs/aggressive-clearout-measurement.md](../docs/aggressive-clearout-measurement.md) §12 independently prescribes independent adversarial review for this child.

The orchestrator confirms the path against the real diff and, when adversarial review is required, selects and records the reviewer's exact provider, model ID, and native effort at dispatch time.

**Implementer selection rationale:** Judgement rung, `gpt-5.6-luna` (`high`). The plan settles the architecture, the comparison rule, both clause formats and the test matrix, which would suggest Bounded — but it delegates set-semantics-sensitive implementation where the wrong-but-plausible choice passes naive tests, a new pass's interaction with existing decision ordering and protection tiers, and two emitter contracts that must match hand-written recognizers exactly. That combination of quiet failure modes and real ambiguity sits above the Bounded rung.

# Review checklist

- [ ] Check 1: No coverage outcome produces `action == "junk"` or alters an existing `Tag`; every coverage decision preserves `row["Tag"]`.
- [ ] Check 2: Comparison uses the **uncollapsed** matched sets; a fixture proves a dominance relation that collapsed-set comparison would miss.
- [ ] Check 3: Empty candidate coverage yields `coverage-uncovered vs`, never `coverage-dominated by`; hard-protected copies receive no clause but remain eligible partners.
- [ ] Check 4: Copies sharing an exact-roll fingerprint, and copies whose fingerprint is `None`, are never compared.
- [ ] Check 5: Mutual trade-offs, equal coverage and mutually uncovered pairs produce no decision.
- [ ] Check 6: Both clauses match the verbatim formats; the `note_history` recognizer is emitter-driven and a second run replaces rather than accumulates. All four emitting branches — both clause kinds × both partner labels — have round-trip coverage, with the tie-break branches reached through a three-member group.
- [ ] Check 6b: The `resolved:` line no longer claims every review is soft-protected, and a regression test pins that; the three coverage summary lines print decision totals, the combination distribution and family consensus, each asserted in a CLI test.
- [ ] Check 6c: The coverage pool is built from emitted decision ids, so soft-protected `wishlist-trash` reviews and `dupe-lower` reviews are excluded from comparison.
- [ ] Check 7: Partner selection and decision order are deterministic under row reversal, using `instance_id_order` for every tie-break.
- [ ] Check 8: `family` reaches no decision input and no `Notes` clause; `WishlistSourceIdentity`, `_decision_config`, the fingerprint payload and the snapshot schema are untouched.
- [ ] Check 9: `RULESET_VERSION` is 5, `SNAPSHOT_SCHEMA_VERSION` is 2, and the regenerated golden differs only in the ruleset version and fingerprint.
- [ ] Check 10: `--no-wishlists` still reaches the early return and emits no coverage advice.
- [ ] Check 11: Diff touches no `ui/`, `server/`, `review*.py`, `rails.py` or `config.toml` path.
- [ ] Check 12: `.venv/bin/ruff check src tests scripts` and `.venv/bin/pytest -q` pass; `git diff --check origin/main...HEAD` is clean; `git ls-files data/` is empty.
- [ ] Check 13: `WORKLOG.md` records the ruleset bump and its veto invalidation, the evidence-loader switch, and the real-export authorisation.
- [ ] Check 14: Likely findings 1–4 are each specifically disproved against the real diff.

# Dispatch comment draft

Planned #34 in [handoffs/issue-34-implementation-plan.md](https://github.com/tonym999/vault-cleaner/blob/main/handoffs/issue-34-implementation-plan.md) on `main`.

- **Implementer model & effort:** `gpt-5.6-luna` (`high`)
- **Implementation branch:** `feat/issue-34-coverage-review`
- **Likely findings:** comparing collapsed instead of uncollapsed coverage sets; vacuous subset turning absent evidence into dominance advice; emitter/recognizer drift on the two new `Notes` clauses; scope leak into snapshot, UI or policy surfaces.
