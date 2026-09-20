from pathlib import Path

import pandas as pd

from vault_cleaner import cli
from vault_cleaner.parse import load_weapons
from vault_cleaner.rules import coverage
from vault_cleaner.rules import weapons as weapons_rules
from vault_cleaner.rules.dupes import exact_roll_fingerprint
from vault_cleaner.wishlist import (
    Wishlist,
    WishlistSourceSpec,
    parse_wishlist,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
WEAPONS_CSV = FIXTURES_DIR / "weapons_coverage.csv"
WISHLIST_TXT = FIXTURES_DIR / "wishlist_coverage.txt"

PERK_MAP = {
    "frame": frozenset({1000}),
    "perk a": frozenset({1}),
    "perk b": frozenset({2, 20}),  # base + enhanced
    "perk c": frozenset({3}),
    "perk d": frozenset({4}),
    "perk e": frozenset({5}),
    "perk f": frozenset({6}),
    "bad perk": frozenset({99}),
}


def _load_fixture_wishlist(evidence: bool = False) -> Wishlist:
    text = WISHLIST_TXT.read_text(encoding="utf-8")
    if not evidence:
        return parse_wishlist(text)
    spec = WishlistSourceSpec(
        name="test_cov", url="https://example.test/cov", family="cov_family",
        activity="any", tier_format="none"
    )
    return parse_wishlist(text, name="test_cov", spec=spec, evidence=True)


def test_canonical_perk_tokens_deterministic():
    perk_map = {
        "z perk": frozenset({200, 100}),
        "a perk": frozenset({20, 10}),
        "empty perk": frozenset(),
        "shared perk": frozenset({10, 50}),  # 10 already appeared in "a perk"
    }
    tokens = coverage.canonical_perk_tokens(perk_map)
    # "a perk" sorted first: min is 10. Both 10 and 20 map to 10.
    assert tokens[10] == 10
    assert tokens[20] == 10
    # "shared perk" seen later: 10 setdefault keeps 10, 50 gets min of shared perk (10).
    assert tokens[50] == 10
    # "z perk": min is 100. Both 100 and 200 map to 100.
    assert tokens[100] == 100
    assert tokens[200] == 100
    # Unmapped perk maps to itself via get.
    assert tokens.get(999, 999) == 999


def test_collapse_subsumption():
    rolls = frozenset({
        frozenset({1, 2}),
        frozenset({1, 2, 3}),  # superset of {1, 2}
        frozenset({4, 5}),      # disjoint
    })
    collapsed = coverage.collapse(rolls)
    # {1, 2} is dropped because it is a strict subset of {1, 2, 3}.
    assert collapsed == frozenset({frozenset({1, 2, 3}), frozenset({4, 5})})
    assert coverage.collapse(frozenset()) == frozenset()


def test_collapsed_vs_uncollapsed_comparison():
    """Prove that comparing collapsed sets would miss a genuine dominance relation.

    Candidate A matches traits-only Roll 1.
    Candidate B matches 4-perk Roll 2 (superset of Roll 1) and Roll 3.
    Under uncollapsed sets: matched(A) < matched(B) (A is dominated).
    Under collapsed sets: collapse(matched(A)) is NOT a subset of collapse(matched(B)).
    """
    wl = Wishlist(
        keep={
            9001: [
                frozenset({10, 20}),          # Roll 1 (traits only)
                frozenset({10, 20, 30, 40}),  # Roll 2 (4 perks)
                frozenset({50, 60}),          # Roll 3
            ]
        }
    )
    tokens = {10: 10, 20: 20, 30: 30, 40: 40, 50: 50, 60: 60}
    perk_map = {
        "p10": frozenset({10}), "p20": frozenset({20}),
        "p30": frozenset({30}), "p40": frozenset({40}),
        "p50": frozenset({50}), "p60": frozenset({60}),
    }

    matched_a = coverage.matched_rolls(9001, frozenset({10, 20}), wl, tokens)
    matched_b = coverage.matched_rolls(9001, frozenset({10, 20, 30, 40, 50, 60}), wl, tokens)

    assert matched_a == frozenset({frozenset({10, 20})})
    assert matched_b == frozenset({
        frozenset({10, 20}),
        frozenset({10, 20, 30, 40}),
        frozenset({50, 60}),
    })

    # Uncollapsed test: A is a strict subset of B.
    assert matched_a < matched_b

    # Collapsed test: {10, 20} is NOT in collapse(B), so collapsed comparison misses dominance!
    collapsed_a = coverage.collapse(matched_a)
    collapsed_b = coverage.collapse(matched_b)
    assert collapsed_a == frozenset({frozenset({10, 20})})
    assert collapsed_b == frozenset({frozenset({10, 20, 30, 40}), frozenset({50, 60})})
    assert not collapsed_a.issubset(collapsed_b)

    # Now verify coverage.analyse finds the dominance relation.
    df = pd.DataFrame([
        {
            "Name": "Missed Dom", "Hash": "9001", "Id": "1", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false",
            "Crafted": "false", "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "p10*", "Perks 1": "p20*", "Perks 2": "Kill Tracker",
        },
        {
            "Name": "Missed Dom", "Hash": "9001", "Id": "2", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false",
            "Crafted": "false", "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "p10*", "Perks 1": "p20*", "Perks 2": "p30*", "Perks 3": "p40*",
            "Perks 4": "p50*", "Perks 5": "p60*", "Perks 6": "Kill Tracker",
        },
    ]).fillna("")
    analysis = coverage.analyse(df, wl, perk_map, crafted_level_protect=10)
    assert len(analysis.decisions) == 1
    d = analysis.decisions[0]
    assert d.id == "1"
    assert d.kept_id == "2"
    assert "coverage-dominated by" in d.note
    assert "curated matches 1 vs 3" in d.note


def test_base_enhanced_variant_canonicalisation():
    """Base and enhanced perk hashes of the same name map to the same token."""
    wl = Wishlist(
        keep={
            1012: [
                frozenset({1, 20}),  # Curates enhanced perk hash 20
            ]
        }
    )
    tokens = coverage.canonical_perk_tokens(PERK_MAP)
    # Weapon copy resolving "Perk A" and "Perk B" yields hashes {1, 2, 20}
    perks = frozenset({1, 2, 20})
    matched = coverage.matched_rolls(1012, perks, wl, tokens)
    # 20 canonicalises to token 2, so the matched roll is {1, 2}
    assert matched == frozenset({frozenset({1, 2})})


def test_consensus_counted_by_family_not_source():
    """Consensus counts unique curation families, not raw sources."""
    # Build two sources in the SAME family
    spec_a1 = WishlistSourceSpec(name="src_a1", url="http://a1", family="family-alpha", activity="any", tier_format="none")
    spec_a2 = WishlistSourceSpec(name="src_a2", url="http://a2", family="family-alpha", activity="any", tier_format="none")
    wl1 = parse_wishlist("dimwishlist:item=1001&perks=1,2\n", name="src_a1", spec=spec_a1, evidence=True)
    wl2 = parse_wishlist("dimwishlist:item=1001&perks=1,2\n", name="src_a2", spec=spec_a2, evidence=True)

    merged_same = Wishlist(name="merged", keep_evidence={}, trash_evidence={})
    merged_same.merge(wl1)
    merged_same.merge(wl2)

    df = pd.DataFrame([
        {
            "Name": "W", "Hash": "1001", "Id": "1", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false", "Crafted": "false",
            "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "Perk A*", "Perks 1": "Perk B*", "Perks 2": "Kill Tracker",
        },
        {
            "Name": "W", "Hash": "1001", "Id": "2", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false", "Crafted": "false",
            "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "Perk E*", "Perks 1": "Kill Tracker",
        },
    ]).fillna("")

    analysis_same = coverage.analyse(df, merged_same, PERK_MAP, crafted_level_protect=10)
    # 2 sources in same family -> 1 family supporting the combination
    assert analysis_same.summary.consensus_counts == ((1, 1),)

    # Now with a second source in a DIFFERENT family
    spec_b = WishlistSourceSpec(name="src_b", url="http://b", family="family-beta", activity="any", tier_format="none")
    wl_diff = parse_wishlist("dimwishlist:item=1001&perks=1,2\n", name="src_b", spec=spec_b, evidence=True)
    merged_diff = Wishlist(name="merged", keep_evidence={}, trash_evidence={})
    merged_diff.merge(wl1)
    merged_diff.merge(wl_diff)

    analysis_diff = coverage.analyse(df, merged_diff, PERK_MAP, crafted_level_protect=10)
    # 2 distinct families supporting the combination -> 2 families
    assert analysis_diff.summary.consensus_counts == ((2, 1),)


def test_keep_evidence_none_yields_none_consensus():
    wl = _load_fixture_wishlist(evidence=False)
    assert wl.keep_evidence is None
    weapons = load_weapons(WEAPONS_CSV)
    analysis = coverage.analyse(weapons, wl, PERK_MAP, crafted_level_protect=10)
    assert analysis.summary.consensus_counts is None


def test_fixture_all_coverage_relations():
    wl = _load_fixture_wishlist(evidence=True)
    weapons = load_weapons(WEAPONS_CSV)
    run_res = weapons_rules.run(weapons, wl, PERK_MAP, crafted_level_protect=10)
    summary = run_res.coverage
    assert summary is not None

    # Yield assertions on weapons_coverage.csv:
    # 22 compared copies, 3 dominated, 4 uncovered
    assert summary.compared_instances == 22
    assert summary.dominated == 3
    assert summary.uncovered == 4
    assert summary.combination_counts == ((0, 6), (1, 13), (2, 3))
    # Consensus is counted by combination (not per copy).
    # On this fixture, 19 collapsed combinations are supported by 1 family across
    # 16 copies that hold at least one combination. A per-copy implementation would
    # incorrectly produce ((1, 16),) instead of the correct ((1, 19),).
    assert summary.consensus_counts == ((1, 19),)

    coverage_decisions = [d for d in run_res.decisions if "coverage-" in d.note]
    assert len(coverage_decisions) == 7

    decisions_by_id = {d.id: d for d in coverage_decisions}

    # Hash 1001: strict subset (10011 dominated by 10012)
    # Distinguishing case for F3: 10011 is dominated by 10012 under uncollapsed matching,
    # even though collapse(matched(10011)) is not a subset of collapse(matched(10012)).
    from vault_cleaner.rules.weapons import row_perk_hashes

    tokens = coverage.canonical_perk_tokens(PERK_MAP)
    row_10011 = weapons[weapons["Id"] == "10011"].iloc[0]
    row_10012 = weapons[weapons["Id"] == "10012"].iloc[0]
    matched_10011 = coverage.matched_rolls(1001, row_perk_hashes(row_10011, PERK_MAP), wl, tokens)
    matched_10012 = coverage.matched_rolls(1001, row_perk_hashes(row_10012, PERK_MAP), wl, tokens)
    assert matched_10011 < matched_10012
    assert not (coverage.collapse(matched_10011) <= coverage.collapse(matched_10012))

    d_10011 = decisions_by_id["10011"]
    assert d_10011.action == "review"
    assert d_10011.kept_id == "10012"
    assert "#vc-review: coverage-dominated by" in d_10011.note
    assert "curated matches 1 vs 3; partner largest coverage gain" in d_10011.note

    # Hash 1002: mutual trade-off -> neither in decisions
    assert "10021" not in decisions_by_id
    assert "10022" not in decisions_by_id

    # Hash 1003: equal coverage -> neither in decisions
    assert "10031" not in decisions_by_id
    assert "10032" not in decisions_by_id

    # Hash 1004: mutually uncovered -> neither in decisions
    assert "10041" not in decisions_by_id
    assert "10042" not in decisions_by_id

    # Hash 1005: uncovered vs covered (10051 vs 10052)
    d_10051 = decisions_by_id["10051"]
    assert d_10051.action == "review"
    assert d_10051.kept_id == "10052"
    assert "#vc-review: coverage-uncovered vs" in d_10051.note
    assert "curated matches 0 vs 1; partner most combinations" in d_10051.note

    # Hash 1006: hard-protected copy 10062 acts as partner, never candidate
    assert "10062" not in decisions_by_id
    d_10061 = decisions_by_id["10061"]
    assert d_10061.kept_id == "10062"
    assert "#vc-review: coverage-uncovered vs" in d_10061.note

    # Hash 1007: soft-protected candidate 10071 preserves tag "infuse"
    d_10071 = decisions_by_id["10071"]
    assert d_10071.action == "review"
    assert d_10071.tag == "infuse"
    assert d_10071.kept_id == "10072"
    assert "#vc-review: coverage-dominated by" in d_10071.note

    # Hash 1008: ungroupable row (10082 has no tracker) -> neither in decisions
    assert "10081" not in decisions_by_id
    assert "10082" not in decisions_by_id

    # Hash 1009: dominated candidate with tied partners (gain 1 on 10092 and 10093)
    d_10091 = decisions_by_id["10091"]
    assert d_10091.kept_id == "10092"  # 10092 has lower instance id order than 10093
    assert "partner deterministic id tie-break" in d_10091.note
    assert "curated matches 1 vs 2" in d_10091.note

    # Hash 1010: uncovered candidate with tied partners (count 1 on 10102 and 10103)
    d_10101 = decisions_by_id["10101"]
    assert d_10101.kept_id == "10102"  # 10102 has lower instance id order than 10103
    assert "partner deterministic id tie-break" in d_10101.note
    assert "curated matches 0 vs 1" in d_10101.note

    # Hash 1012: uncovered vs covered (10122 vs 10121)
    d_10122 = decisions_by_id["10122"]
    assert d_10122.kept_id == "10121"
    assert "#vc-review: coverage-uncovered vs" in d_10122.note

    # No decision has action == "junk"
    assert all(d.action == "review" for d in coverage_decisions)


def test_reversing_row_order_is_deterministic():
    wl = _load_fixture_wishlist(evidence=True)
    weapons = load_weapons(WEAPONS_CSV)
    analysis_forward = coverage.analyse(weapons, wl, PERK_MAP, crafted_level_protect=10)

    reversed_weapons = weapons.iloc[::-1].reset_index(drop=True)
    analysis_reversed = coverage.analyse(reversed_weapons, wl, PERK_MAP, crafted_level_protect=10)

    assert analysis_forward.decisions == analysis_reversed.decisions
    assert analysis_forward.summary == analysis_reversed.summary


def test_same_fingerprint_rows_never_compared():
    wl = Wishlist(
        keep={2001: [frozenset({1, 2})]}
    )
    df = pd.DataFrame([
        {
            "Name": "Twin", "Hash": "2001", "Id": "1", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false",
            "Crafted": "false", "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "Perk A*", "Perks 1": "Perk B*", "Perks 2": "Kill Tracker",
        },
        {
            "Name": "Twin", "Hash": "2001", "Id": "2", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false",
            "Crafted": "false", "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "Perk A*", "Perks 1": "Perk B*", "Perks 2": "Kill Tracker",
        },
    ]).fillna("")
    fp0 = exact_roll_fingerprint(df.iloc[0])
    fp1 = exact_roll_fingerprint(df.iloc[1])
    assert fp0 is not None
    assert fp0 == fp1
    analysis = coverage.analyse(df, wl, PERK_MAP, crafted_level_protect=10)
    # Not compared: 0 compared instances, 0 decisions
    assert analysis.summary.compared_instances == 0
    assert len(analysis.decisions) == 0


def test_non_cardinality_monotone_inversion_emits_curated_matches():
    """Dominance explanation is monotonic even when collapsed counts invert."""
    wl = Wishlist(
        keep={
            7001: [
                frozenset({1, 2}),
                frozenset({1, 3}),
                frozenset({1, 2, 3, 4}),
            ]
        }
    )
    perk_map = {
        "perk a": frozenset({1}),
        "perk b": frozenset({2}),
        "perk c": frozenset({3}),
        "perk d": frozenset({4}),
    }
    df = pd.DataFrame([
        {
            "Name": "Inversion Gun", "Hash": "7001", "Id": "cand", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false",
            "Crafted": "false", "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "perk a*", "Perks 1": "perk b*", "Perks 2": "perk c*", "Perks 3": "Kill Tracker",
        },
        {
            "Name": "Inversion Gun", "Hash": "7001", "Id": "part", "Tag": "",
            "Rarity": "Legendary", "Locked": "false", "Equipped": "false",
            "Crafted": "false", "Crafted Level": "0", "Notes": "", "Owner": "Vault",
            "Perks 0": "perk a*", "Perks 1": "perk b*", "Perks 2": "perk c*", "Perks 3": "perk d*", "Perks 4": "Kill Tracker",
        },
    ]).fillna("")
    tokens = coverage.canonical_perk_tokens(perk_map)
    matched_cand = coverage.matched_rolls(7001, frozenset({1, 2, 3}), wl, tokens)
    matched_part = coverage.matched_rolls(7001, frozenset({1, 2, 3, 4}), wl, tokens)
    # Candidate matches {1, 2} and {1, 3} -> 2 uncollapsed matches, 2 collapsed combinations
    assert len(matched_cand) == 2
    assert len(coverage.collapse(matched_cand)) == 2
    # Partner matches {1, 2}, {1, 3}, {1, 2, 3, 4} -> 3 uncollapsed matches, 1 collapsed combination
    assert len(matched_part) == 3
    assert len(coverage.collapse(matched_part)) == 1

    # Dominance holds on uncollapsed sets
    assert matched_cand < matched_part

    analysis = coverage.analyse(df, wl, perk_map, crafted_level_protect=10)
    assert len(analysis.decisions) == 1
    d = analysis.decisions[0]
    assert d.id == "cand"
    assert d.kept_id == "part"
    assert "#vc-review: coverage-dominated by" in d.note
    assert "curated matches 2 vs 3" in d.note
    assert "combinations 2 vs 1" not in d.note


def test_weapons_run_excludes_prior_decided_rows():
    wl = _load_fixture_wishlist(evidence=False)
    weapons = load_weapons(WEAPONS_CSV)
    run_res = weapons_rules.run(weapons, wl, PERK_MAP, crafted_level_protect=10)

    # 10111 matches wishlist trash -> junk decision in pass 2
    trash_decisions = [d for d in run_res.decisions if d.id == "10111"]
    assert len(trash_decisions) == 1
    assert trash_decisions[0].action == "junk"

    # 10112 is left alone because 10111 was excluded from the coverage pool
    coverage_decisions_1011 = [d for d in run_res.decisions if d.hash == "1011" and d.id != "10111"]
    assert len(coverage_decisions_1011) == 0


def test_cli_output_neutral_resolved_and_coverage_lines(tmp_path, capsys, monkeypatch):
    from vault_cleaner import pipeline
    from vault_cleaner.manifest import PerkMapData

    monkeypatch.setattr(
        pipeline,
        "load_perk_map_data",
        lambda *args: PerkMapData(names=PERK_MAP, version="test-v1"),
    )
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
manifest_cache_dir = "{tmp_path.as_posix()}"
wishlist_cache_dir = "{tmp_path.as_posix()}"

[rails]
crafted_level_protect = 10

[wishlists]
max_age_days = 7

[wishlists.sources.cov]
url = "{WISHLIST_TXT.as_uri()}"
family = "cov-family"
activity = "any"
tier_format = "none"

[manifest]
max_age_days = 30
"""
    )
    # Copy wishlist to cache
    (tmp_path / "cov.txt").write_text(WISHLIST_TXT.read_text(encoding="utf-8"), encoding="utf-8")

    # Run cli dupes
    args = [
        "dupes",
        "--input", str(WEAPONS_CSV),
        "--config", str(cfg_file),
    ]
    rc = cli.main(args)
    assert rc == 0
    out = capsys.readouterr().out

    # Check 6b: resolved: line does NOT say (soft-protected)
    assert "(soft-protected)" not in out
    assert "resolved: 1 junk, 7 review" in out

    # Check coverage summary lines
    assert "coverage: 3 dominated, 4 uncovered vs a covered copy — review-only, from 22 compared copies" in out
    assert "coverage combinations per compared copy — 0: 6, 1: 13, 2: 3" in out
    assert "coverage evidence: combinations by supporting curation family — 1: 19" in out
