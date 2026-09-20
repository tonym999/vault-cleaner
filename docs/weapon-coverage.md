# Weapon Coverage Rule Pass

Review-only weapons rule pass (PLAN.md rule 4) added in ruleset v5 for issue #34 (Child 4 of #140).

## Objective

Compares copies of the same weapon `Hash` by the useful perk combinations each copy can provide, flagging copies whose useful coverage is wholly contained in another copy's (`coverage-dominated by`) or which provide no curated combinations while another copy does (`coverage-uncovered vs`).

The pass delivers cleanup advice without ever discarding a roll that provides coverage no other copy does.

## Key Design Principles

### 1. Read combinations from wishlists, never enumerate

DIM weapon exports flatten available socket options into `Perks N` fields without a measured socket partition. Enumerating selectable combinations from the export directly would require guesswork and risk forming impossible cross-column combinations.

Instead, combinations are read from curated wishlists:
- A curated keep roll is an author-asserted valid combination.
- The subset check `roll <= perk_hashes` determines whether a weapon copy can provide that combination.
- Perk hashes are canonicalised so base and enhanced variants sharing a display name map to one deterministic token, deduplicating equivalent recommendations across sources.

### 2. Compare uncollapsed matched sets, display monotonic curated matches

`matched(X)` is downward closed: if a copy matches a 4-perk roll, it also matches any curated 2-perk sub-roll for that Hash. Therefore, `matched(A) ⊆ matched(B)` represents the exact test that copy `B` provides everything copy `A` does.

Comparing collapsed sets directly would incorrectly drop genuine dominance relations (measured: 3 of 30 relations lost on real vault data). Dominance comparison must always use the uncollapsed sets.

Note explanations report uncollapsed matched-set cardinalities as `curated matches N vs M`, ensuring that the explanation is strictly monotonic ($N < M$ for dominated decisions). Displayed aggregate CLI distributions continue to report subsumption-collapsed maximal combinations.

### 3. Absence of coverage is uncertainty, not dominance

An empty coverage set `matched(A) = ∅` satisfies subset comparison vacuously against any covered copy. However, lacking wishlist coverage is uncertainty (an off-meta or niche roll), not evidence of junk.

Uncovered copies are therefore flagged under their own distinct label:
`coverage-uncovered vs`
They never share a clause with measured dominance (`coverage-dominated by`).

### 4. Review-only invariant

Coverage advice is strictly `#vc-review` only:
- Never tags an item `junk`.
- Preserves the existing DIM `Tag`.
- Never bypasses existing safety rails.
- Hard-protected items receive no coverage advice, but remain eligible comparison partners.
- Graduation to automatic junk tagging is explicitly out of scope and requires measured output and separate owner approval.

### 5. Pairwise, deterministic partner selection

Candidates are compared only within the same item `Hash`, among copies left undecided by earlier passes (wishlist-trash and exact-dupe) that carry distinct, known exact-roll fingerprints. Copies sharing an exact-roll fingerprint or lacking a measured tracker boundary are never compared.

Partner selection is deterministic:
- For `coverage-dominated by`: selects the partner with the largest collapsed combination gain `len(collapse(matched(B)) - collapse(matched(A)))`, broken deterministically by lowest opaque instance ID order.
- For `coverage-uncovered vs`: selects the partner with the most collapsed combinations `len(collapse(matched(B)))`, broken deterministically by lowest opaque instance ID order.

### 6. Subsumption-aware family consensus

Wishlist consensus counts supporting curation families, not sources. Raw exact-roll agreement across families is degenerate on real exports (because some sources curate 2-perk rolls while others curate 4-perk rolls). Subsumption-aware consensus counts a family as supporting a combination when one of its matched rolls is a subset of that combination.

Consensus is reported in dry-run output only and never enters decision logic, `Notes` clauses, or fingerprint payloads.

## Generated Notes Clauses

The pass emits four exact clause variations across two advice kinds:

```text
#vc-review: coverage-dominated by; compare [REF]; curated matches N vs M; partner largest coverage gain
#vc-review: coverage-dominated by; compare [REF]; curated matches N vs M; partner deterministic id tie-break
#vc-review: coverage-uncovered vs; compare [REF]; curated matches 0 vs M; partner most combinations
#vc-review: coverage-uncovered vs; compare [REF]; curated matches 0 vs M; partner deterministic id tie-break
```

Here, `REF` is a human-readable weapon reference (`weapon_reference`), `N` is the candidate's uncollapsed curated match count, and `M` is the partner's (guaranteeing `N < M` for dominated decisions).
