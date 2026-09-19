from pathlib import Path

from vault_cleaner.parse import load_weapons
from vault_cleaner.rules import weapons as weapons_rules
from vault_cleaner.wishlist import (
    FetchResult,
    Wishlist,
    WishlistEntry,
    WishlistEvidenceSet,
    WishlistSourceSpec,
    WishlistSourceStatus,
    load_all_with_evidence,
    load_all_with_sources,
    parse_wishlist,
)
from vault_cleaner.wishlist_evidence import (
    EvidenceConflict,
    item_evidence,
)


def _make_dummy_status(name: str, family: str, status_str: str = "cache") -> WishlistSourceStatus:
    spec = WishlistSourceSpec(name=name, url=f"http://{name}", family=family, activity="any", tier_format="ciceron-aegis")
    fetch = FetchResult(path=Path(f"{name}.txt"), status=status_str, cache_written_at=1000.0)
    return WishlistSourceStatus(
        spec=spec,
        fetch=fetch,
        max_age_days=7.0,
        declared_title=None,
        declared_description=None,
        keep_entries=0,
        keep_items=0,
        trash_entries=0,
        trash_items=0,
        skipped=0,
        wildcards=0,
        noted_entries=0,
        tagged_entries=0,
        tier_counts=(),
        unrecognized_tier_entries=0,
        ignored_note_segment_entries=0,
    )


def test_family_deduplication_and_uncovered_families():
    # Two sources in family "aegis", one in family "voltron", one in family "other"
    # item 100 has keep matches in both aegis sources -> keep_families should be ("aegis",)
    e1 = WishlistEntry(
        source="aegis1",
        family="aegis",
        polarity="keep",
        item_hash=100,
        perks=frozenset({10, 20}),
        notes=None,
        tags=(),
        section_title=None,
        activities=frozenset(),
        activity_basis="unknown",
        tier="S",
        tier_status="parsed",
    )
    e2 = WishlistEntry(
        source="aegis2",
        family="aegis",
        polarity="keep",
        item_hash=100,
        perks=frozenset({10, 30}),
        notes=None,
        tags=(),
        section_title=None,
        activities=frozenset(),
        activity_basis="unknown",
        tier="S",
        tier_status="parsed",
    )

    wl = Wishlist(
        name="merged",
        keep={100: [frozenset({10, 20}), frozenset({10, 30})]},
        trash={},
        keep_evidence={100: [e1, e2]},
        trash_evidence={},
    )
    statuses = (
        _make_dummy_status("aegis1", "aegis"),
        _make_dummy_status("aegis2", "aegis"),
        _make_dummy_status("voltron", "voltron"),
        _make_dummy_status("other", "other"),
    )
    ev_set = WishlistEvidenceSet(merged=wl, sources=(), statuses=statuses)

    ev = item_evidence(ev_set, 100, frozenset({10, 20, 30}))
    assert ev.keep_families == ("aegis",)
    assert len(ev.keep_matches) == 2
    assert ev.trash_matches == ()
    assert ev.trash_kind is None
    assert ev.covered_families == ("aegis",)
    assert ev.uncovered_families == ("other", "voltron")
    assert ev.conflicts == ()


def test_covered_but_no_perk_match_and_stale_source():
    # item 200 is in aegis (keep with perks {10}) and voltron (trash with perks {20})
    # weapon perks has only {99} -> covered by both families, but no matches
    # aegis status is stale-cache-after-failed-download -> stale_sources should list aegis
    e_aegis = WishlistEntry(
        source="aegis",
        family="aegis",
        polarity="keep",
        item_hash=200,
        perks=frozenset({10}),
        notes=None,
        tags=(),
        section_title=None,
        activities=frozenset(),
        activity_basis="unknown",
        tier="A",
        tier_status="parsed",
    )
    e_voltron = WishlistEntry(
        source="voltron",
        family="voltron",
        polarity="trash",
        item_hash=200,
        perks=frozenset({20}),
        notes=None,
        tags=(),
        section_title=None,
        activities=frozenset(),
        activity_basis="unknown",
        tier=None,
        tier_status="not-declared",
    )
    wl = Wishlist(
        name="merged",
        keep={200: [frozenset({10})]},
        trash={200: [frozenset({20})]},
        keep_evidence={200: [e_aegis]},
        trash_evidence={200: [e_voltron]},
    )
    statuses = (
        _make_dummy_status("aegis", "aegis", status_str="stale-cache-after-failed-download"),
        _make_dummy_status("voltron", "voltron", status_str="cache"),
    )
    ev_set = WishlistEvidenceSet(merged=wl, sources=(), statuses=statuses)

    ev = item_evidence(ev_set, 200, frozenset({99}))
    assert ev.keep_matches == ()
    assert ev.trash_matches == ()
    assert ev.keep_families == ()
    assert ev.trash_families == ()
    assert ev.covered_families == ("aegis", "voltron")
    assert ev.uncovered_families == ()
    assert ev.stale_sources == ("aegis",)
    assert ev.tiers_by_family == (("aegis", ("A",)), ("voltron", ()))
    assert ev.conflicts == ()


def test_conflict_kinds():
    # 1. keep-trash-cross-family: keep match in fam1, trash match in fam2
    e_k = WishlistEntry(
        source="s1", family="fam1", polarity="keep", item_hash=300, perks=frozenset({1}),
        notes=None, tags=(), section_title=None, activities=frozenset(), activity_basis="unknown",
        tier="S", tier_status="parsed"
    )
    e_t = WishlistEntry(
        source="s2", family="fam2", polarity="trash", item_hash=300, perks=frozenset({2}),
        notes=None, tags=(), section_title=None, activities=frozenset(), activity_basis="unknown",
        tier=None, tier_status="not-declared"
    )
    wl1 = Wishlist(
        keep={300: [frozenset({1})]}, trash={300: [frozenset({2})]},
        keep_evidence={300: [e_k]}, trash_evidence={300: [e_t]},
    )
    statuses1 = (_make_dummy_status("s1", "fam1"), _make_dummy_status("s2", "fam2"))
    ev1 = item_evidence(WishlistEvidenceSet(wl1, (), statuses1), 300, frozenset({1, 2}))
    assert len(ev1.conflicts) == 1
    assert ev1.conflicts[0] == EvidenceConflict(kind="keep-trash-cross-family", families=("fam1", "fam2"))

    # 2. keep-trash-same-family: keep match and trash match both in fam1
    e_t_same = WishlistEntry(
        source="s1_trash", family="fam1", polarity="trash", item_hash=300, perks=frozenset({2}),
        notes=None, tags=(), section_title=None, activities=frozenset(), activity_basis="unknown",
        tier="D", tier_status="parsed"
    )
    wl2 = Wishlist(
        keep={300: [frozenset({1})]}, trash={300: [frozenset({2})]},
        keep_evidence={300: [e_k]}, trash_evidence={300: [e_t_same]},
    )
    statuses2 = (_make_dummy_status("s1", "fam1"), _make_dummy_status("s1_trash", "fam1"))
    ev2 = item_evidence(WishlistEvidenceSet(wl2, (), statuses2), 300, frozenset({1, 2}))
    # Note: no cross family since keep_families == ("fam1",) and trash_families == ("fam1",)
    # But tier disagreement: fam1 has S and D!
    assert ev2.conflicts == (
        EvidenceConflict(kind="keep-trash-same-family", families=("fam1",)),
        EvidenceConflict(kind="tier-disagreement", families=("fam1",), tiers=("S", "D")),
    )


def test_tier_disagreement_within_family():
    # Two entries in fam1 for item 400: one tier S, one tier A
    e1 = WishlistEntry(
        source="s1", family="fam1", polarity="keep", item_hash=400, perks=frozenset({1}),
        notes=None, tags=(), section_title=None, activities=frozenset(), activity_basis="unknown",
        tier="S", tier_status="parsed"
    )
    e2 = WishlistEntry(
        source="s2", family="fam1", polarity="keep", item_hash=400, perks=frozenset({2}),
        notes=None, tags=(), section_title=None, activities=frozenset(), activity_basis="unknown",
        tier="A", tier_status="parsed"
    )
    wl = Wishlist(
        keep={400: [frozenset({1}), frozenset({2})]}, trash={},
        keep_evidence={400: [e1, e2]}, trash_evidence={},
    )
    statuses = (_make_dummy_status("s1", "fam1"), _make_dummy_status("s2", "fam1"))
    ev = item_evidence(WishlistEvidenceSet(wl, (), statuses), 400, frozenset({1}))
    assert ev.conflicts == (
        EvidenceConflict(kind="tier-disagreement", families=("fam1",), tiers=("S", "A")),
    )


def test_parity_with_weapons_rules():
    # Load weapons fixtures and compare item_evidence with weapons rule helpers
    fixtures_dir = Path(__file__).parent / "fixtures"
    weapons_files = [fixtures_dir / "weapons.csv", fixtures_dir / "weapons_dupes.csv"]

    # Build perk map from real perk cells across the fixture files
    perk_map: dict[str, frozenset[int]] = {}
    current_id = 1000
    for w_file in weapons_files:
        df = load_weapons(w_file)
        for _, row in df.iterrows():
            for col in row.index:
                if col.startswith("Perks ") and row[col]:
                    name = str(row[col]).strip().removesuffix("*").strip().casefold()
                    if name and name not in perk_map:
                        perk_map[name] = frozenset({current_id})
                        current_id += 1

    barrel_a_id = next(iter(perk_map["barrel a"]))
    mag_a_id = next(iter(perk_map["mag a"]))
    barrel_exotic_id = next(iter(perk_map["barrel exotic"]))
    mag_exotic_id = next(iter(perk_map["mag exotic"]))

    # Synthetic wishlist text using real fixture item hashes and perk ids
    wl_text = f"""
title: Test
dimwishlist:item=500&perks={barrel_a_id},{mag_a_id}
dimwishlist:item=-600&perks={barrel_exotic_id},{mag_exotic_id}
dimwishlist:item=-800&perks=
"""
    spec = WishlistSourceSpec(name="test", url="http://test", family="test-fam", activity="any", tier_format="none")
    wl_evidence = parse_wishlist(wl_text, "test", spec=spec, evidence=True)
    wl_plain = parse_wishlist(wl_text, "test", evidence=False)
    status = WishlistSourceStatus(
        spec=spec,
        fetch=FetchResult(path=Path("test.txt"), status="cache", cache_written_at=0.0),
        max_age_days=7.0,
        declared_title="Test",
        declared_description=None,
        keep_entries=1,
        keep_items=1,
        trash_entries=2,
        trash_items=2,
        skipped=0,
        wildcards=0,
        noted_entries=0,
        tagged_entries=0,
        tier_counts=(),
        unrecognized_tier_entries=0,
        ignored_note_segment_entries=0,
    )
    ev_set = WishlistEvidenceSet(merged=wl_evidence, sources=(), statuses=(status,))

    keep_matches_count = 0
    roll_trash_count = 0
    whole_trash_count = 0

    for w_file in weapons_files:
        df = load_weapons(w_file)
        for _, row in df.iterrows():
            item_hash = int(row["Hash"])
            perk_hashes = weapons_rules.row_perk_hashes(row, perk_map)
            ev = item_evidence(ev_set, item_hash, perk_hashes)

            expected_keep_count = weapons_rules.keep_match_count(item_hash, perk_hashes, wl_plain)
            expected_trash_kind = weapons_rules.trash_match(item_hash, perk_hashes, wl_plain)

            assert bool(ev.keep_matches) == (expected_keep_count > 0)
            assert ev.trash_kind == expected_trash_kind

            if ev.keep_matches:
                keep_matches_count += 1
            if ev.trash_kind == "roll":
                roll_trash_count += 1
            if ev.trash_kind == "whole-item":
                whole_trash_count += 1

    assert keep_matches_count >= 1
    assert roll_trash_count >= 1
    assert whole_trash_count >= 1


def test_decision_invariance_under_load_all(tmp_path):
    # Verify that weapons_rules.run produces byte-identical decisions and conflicts
    # whether run with load_all_with_sources(cfg)[0] or load_all_with_evidence(cfg).merged
    fixture_dir = Path(__file__).parent / "fixtures"
    weapons_df = load_weapons(fixture_dir / "weapons_dupes.csv")

    perk_map: dict[str, frozenset[int]] = {}
    current_id = 1000
    for _, row in weapons_df.iterrows():
        for col in row.index:
            if col.startswith("Perks ") and row[col]:
                name = str(row[col]).strip().removesuffix("*").strip().casefold()
                if name and name not in perk_map:
                    perk_map[name] = frozenset({current_id})
                    current_id += 1

    barrel_a_id = next(iter(perk_map["barrel a"]))
    mag_a_id = next(iter(perk_map["mag a"]))

    w1_text = f"""
dimwishlist:item=500&perks={barrel_a_id},{mag_a_id}
dimwishlist:item=-500&perks=
"""
    w2_text = """
//notes:Aegis Endgame S Tier.
dimwishlist:item=600&perks=9999
//notes:D Tier.
dimwishlist:item=-900&perks=
"""
    (tmp_path / "w1.txt").write_text(w1_text, encoding="utf-8")
    (tmp_path / "w2.txt").write_text(w2_text, encoding="utf-8")

    cfg = {
        "paths": {"wishlist_cache_dir": str(tmp_path)},
        "wishlists": {
            "max_age_days": 7,
            "sources": {
                "w1": "https://example.test/w1.txt",
                "w2": {
                    "url": "https://example.test/w2.txt",
                    "family": "aegis-endgame",
                    "tier_format": "ciceron-aegis",
                },
            },
        },
    }

    wl_sources, _ = load_all_with_sources(cfg)
    ev_set = load_all_with_evidence(cfg)

    res_sources = weapons_rules.run(weapons_df, wl_sources, perk_map, crafted_level_protect=10)
    res_evidence = weapons_rules.run(weapons_df, ev_set.merged, perk_map, crafted_level_protect=10)

    keep_protected_count = sum(
        1 for _, row in weapons_df.iterrows()
        if weapons_rules.keep_match_count(int(row["Hash"]), weapons_rules.row_perk_hashes(row, perk_map), wl_sources) > 0
    )
    trash_decisions = [d for d in res_sources.decisions if "wishlist-trash" in d.note]

    assert keep_protected_count >= 1
    assert len(trash_decisions) >= 1
    assert res_sources.keep_trash_conflicts > 0

    assert res_sources.keep_trash_conflicts == res_evidence.keep_trash_conflicts
    assert len(res_sources.decisions) == len(res_evidence.decisions)
    for d1, d2 in zip(res_sources.decisions, res_evidence.decisions, strict=True):
        assert d1.id == d2.id
        assert d1.tag == d2.tag
        assert d1.note == d2.note
        assert d1.kept_id == d2.kept_id
