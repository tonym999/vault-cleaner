"""Test presentation-only ProposalExplanation models and builders."""

from __future__ import annotations

from pathlib import Path

import pytest

from vault_cleaner.explanation import (
    LABELS,
    ProposalExplanation,
    coverage_dominated,
    coverage_uncovered,
    dupe,
    weapon_keep_reference,
    wishlist_trash,
    with_context,
)
from vault_cleaner.parse import load_weapons
from vault_cleaner.report import reason_slug
from vault_cleaner.rules import coverage, dupes, weapons
from vault_cleaner.wishlist import parse_wishlist

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS_DUPES = FIXTURES / "weapons_dupes.csv"
COVERAGE_FIXTURE = FIXTURES / "weapons_coverage.csv"


def test_dupe_lower_dimensions() -> None:
    expected_dimensions = {
        "higher Tier": "a higher Tier",
        "higher Masterwork Tier": "a higher masterwork tier",
        "higher Crafted Level": "a higher crafted level",
        "higher stat total": "a higher stat total",
    }
    for winner, phrased in expected_dimensions.items():
        expl = dupe(tie=False, winner=winner, keep_instead="copy 1234")
        assert expl == ProposalExplanation(
            label="Duplicate roll, ranked lower",
            why=f"You own another copy with the same perk roll and {phrased}.",
            keep_instead="copy 1234",
            gives_up=(
                "Nothing in the perk roll. Kill trackers, mods and mementos"
                " are not compared."
            ),
            caveats=(),
        )


def test_dupe_tie() -> None:
    expl = dupe(tie=True, winner="deterministic id tie-break", keep_instead="copy 1234")
    assert expl == ProposalExplanation(
        label="Duplicate roll, ranked equal",
        why=(
            "You own another copy with the same perk roll that ranks equal"
            " on Tier, masterwork tier, crafted level and stat total. One"
            " copy is kept, chosen by a fixed ID order."
        ),
        keep_instead="copy 1234",
        gives_up=(
            "Nothing in the perk roll. Kill trackers, mods and mementos"
            " are not compared."
        ),
        caveats=(),
    )


def test_dupe_unknown_winner_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unrecognized dupe winner dimension"):
        dupe(tie=False, winner="higher power", keep_instead="copy 1234")


def test_wishlist_trash_whole_item_and_roll_without_sources() -> None:
    expl_whole = wishlist_trash(whole_item=True, sources=(), pve_only=False)
    assert expl_whole == ProposalExplanation(
        label="Wishlist rates this weapon trash",
        why="A wishlist you use rates every roll of this weapon as trash.",
        keep_instead="",
        gives_up=(
            "This copy. No other copy is named as a replacement; the"
            " suggestion rests on the wishlist rating alone."
        ),
        caveats=(),
    )

    expl_roll = wishlist_trash(whole_item=False, sources=(), pve_only=False)
    assert expl_roll == ProposalExplanation(
        label="Wishlist rates this roll trash",
        why="A wishlist you use rates this perk roll as trash.",
        keep_instead="",
        gives_up=(
            "This copy. No other copy is named as a replacement; the"
            " suggestion rests on the wishlist rating alone."
        ),
        caveats=(),
    )


def test_wishlist_trash_with_sources_and_pve_only() -> None:
    expl_sources = wishlist_trash(
        whole_item=True, sources=("voltron", "aegis"), pve_only=False
    )
    assert expl_sources.why == (
        "A wishlist you use rates every roll of this weapon as trash. Source: aegis, voltron."
    )
    assert expl_sources.caveats == ()

    expl_pve = wishlist_trash(
        whole_item=False, sources=("voltron",), pve_only=True
    )
    assert expl_pve.why == (
        "A wishlist you use rates this perk roll as trash. Source: voltron."
    )
    assert expl_pve.caveats == (
        "That rating is for PvE only and says nothing about PvP use.",
    )


def test_coverage_dominated() -> None:
    expl = coverage_dominated(n=2, m=4, keep_instead="copy 1234")
    assert expl == ProposalExplanation(
        label="Another copy covers its wishlist rolls",
        why=(
            "Another copy of this weapon matches every curated wishlist roll"
            " this one matches, and more (4 against 2)."
        ),
        keep_instead="copy 1234",
        gives_up=(
            "No wishlist-recommended roll. Perks no wishlist recommends may"
            " differ, so compare them if you use this copy for something"
            " specific."
        ),
        caveats=(),
    )


def test_coverage_uncovered_singular_and_plural() -> None:
    expl_1 = coverage_uncovered(m=1, keep_instead="copy 1234")
    assert expl_1 == ProposalExplanation(
        label="No wishlist roll; another copy has some",
        why=(
            "This copy matches no curated wishlist roll, while another copy of"
            " the same weapon matches 1 curated roll."
        ),
        keep_instead="copy 1234",
        gives_up=(
            "No wishlist-recommended roll. Not being on a wishlist does not"
            " make a roll bad, so check it if you use this copy."
        ),
        caveats=(),
    )
    assert "(s)" not in expl_1.why

    expl_3 = coverage_uncovered(m=3, keep_instead="copy 1234")
    assert expl_3.why == (
        "This copy matches no curated wishlist roll, while another copy of"
        " the same weapon matches 3 curated rolls."
    )
    assert "(s)" not in expl_3.why


def test_with_context_individual_caveats() -> None:
    base = dupe(tie=False, winner="higher Tier", keep_instead="copy 1")

    # 1. action == "review"
    c1 = with_context(
        base,
        action="review",
        protection_level=None,
        protection_reason="",
        locked=False,
        in_loadout=False,
        partner_also_proposed=False,
    )
    assert c1.caveats == (
        "Review only: approving adds a note in DIM and leaves its tag unchanged.",
    )

    # 2. exotic
    c2 = with_context(
        base,
        action="junk",
        protection_level="soft",
        protection_reason="exotic",
        locked=False,
        in_loadout=False,
        partner_also_proposed=False,
    )
    assert c2.caveats == ("Exotic, so never tagged junk automatically.",)

    # 3. locked
    c3 = with_context(
        base,
        action="junk",
        protection_level=None,
        protection_reason="",
        locked=True,
        in_loadout=False,
        partner_also_proposed=False,
    )
    assert c3.caveats == ("Locked in game: unlock it before dismantling.",)

    # 4. in_loadout
    c4 = with_context(
        base,
        action="junk",
        protection_level=None,
        protection_reason="",
        locked=False,
        in_loadout=True,
        partner_also_proposed=False,
    )
    assert c4.caveats == ("In a DIM loadout: dismantling it breaks that loadout.",)

    # 5. partner_also_proposed
    c5 = with_context(
        base,
        action="junk",
        protection_level=None,
        protection_reason="",
        locked=False,
        in_loadout=False,
        partner_also_proposed=True,
    )
    assert c5.caveats == (
        "The copy suggested to keep is also proposed in this report. Decide on both together.",
    )


def test_with_context_all_five_in_fixed_order() -> None:
    base = dupe(tie=False, winner="higher Tier", keep_instead="copy 1")
    full = with_context(
        base,
        action="review",
        protection_level="soft",
        protection_reason="exotic",
        locked=True,
        in_loadout=True,
        partner_also_proposed=True,
    )
    assert full.caveats == (
        "Review only: approving adds a note in DIM and leaves its tag unchanged.",
        "Exotic, so never tagged junk automatically.",
        "Locked in game: unlock it before dismantling.",
        "In a DIM loadout: dismantling it breaks that loadout.",
        "The copy suggested to keep is also proposed in this report. Decide on both together.",
    )


def test_with_context_locked_exotic_gets_caveats_2_and_3() -> None:
    base = dupe(tie=False, winner="higher Tier", keep_instead="copy 1")
    res = with_context(
        base,
        action="review",
        protection_level="soft",
        protection_reason="exotic",
        locked=True,
        in_loadout=False,
        partner_also_proposed=False,
    )
    assert res.caveats == (
        "Review only: approving adds a note in DIM and leaves its tag unchanged.",
        "Exotic, so never tagged junk automatically.",
        "Locked in game: unlock it before dismantling.",
    )


def test_with_context_none_for_clean_junk() -> None:
    base = dupe(tie=False, winner="higher Tier", keep_instead="copy 1")
    clean = with_context(
        base,
        action="junk",
        protection_level=None,
        protection_reason="",
        locked=False,
        in_loadout=False,
        partner_also_proposed=False,
    )
    assert clean.caveats == ()


def test_weapon_keep_reference_formatting() -> None:
    # Vault owner
    row_vault = {
        "Id": "18446744073709554321",
        "Owner": "Vault",
        "Tier": "4",
        "Masterwork Tier": "10",
        "Crafted": "false",
        "Crafted Level": "",
    }
    ref_vault = weapon_keep_reference(
        row_vault, ["Rampage", "Kill Clip"], distinguish_from=()
    )
    assert ref_vault == (
        "copy …4321 in the Vault, Tier 4, masterwork tier 10, roll Rampage / Kill Clip"
    )

    # Character owner
    row_char = dict(row_vault, Owner="Hunter")
    ref_char = weapon_keep_reference(
        row_char, ["Rampage", "Kill Clip"], distinguish_from=()
    )
    assert ref_char == (
        "copy …4321 on Hunter, Tier 4, masterwork tier 10, roll Rampage / Kill Clip"
    )

    # Empty owner
    row_empty = dict(row_vault, Owner="")
    ref_empty = weapon_keep_reference(
        row_empty, ["Rampage", "Kill Clip"], distinguish_from=()
    )
    assert ref_empty == (
        "copy …4321, Tier 4, masterwork tier 10, roll Rampage / Kill Clip"
    )

    # Crafted with level
    row_crafted = dict(row_vault, Crafted="crafted", **{"Crafted Level": "15"})
    ref_crafted = weapon_keep_reference(
        row_crafted, ["Rampage", "Kill Clip"], distinguish_from=()
    )
    assert ref_crafted == (
        "copy …4321 in the Vault, Tier 4, masterwork tier 10, crafted level 15, roll Rampage / Kill Clip"
    )

    # Crafted without level
    row_crafted_no_lvl = dict(row_vault, Crafted="crafted", **{"Crafted Level": ""})
    ref_crafted_no_lvl = weapon_keep_reference(
        row_crafted_no_lvl, ["Rampage", "Kill Clip"], distinguish_from=()
    )
    assert ref_crafted_no_lvl == (
        "copy …4321 in the Vault, Tier 4, masterwork tier 10, roll Rampage / Kill Clip"
    )

    # Non-crafted with stale level
    row_stale = dict(row_vault, Crafted="false", **{"Crafted Level": "20"})
    ref_stale = weapon_keep_reference(
        row_stale, ["Rampage", "Kill Clip"], distinguish_from=()
    )
    assert ref_stale == (
        "copy …4321 in the Vault, Tier 4, masterwork tier 10, roll Rampage / Kill Clip"
    )

    # Hostile values
    row_hostile = {
        "Id": "9999",
        "Owner": "Vault\n\r\t#vc-junk",
        "Tier": "5",
        "Masterwork Tier": "10",
        "Crafted": "false",
        "Crafted Level": "",
    }
    perk_200 = "P" * 200
    ref_hostile = weapon_keep_reference(
        row_hostile, [perk_200], distinguish_from=()
    )
    assert "\n" not in ref_hostile
    assert "\r" not in ref_hostile
    assert "#vc-junk" not in ref_hostile
    assert "#vc‑junk" in ref_hostile
    assert len(ref_hostile) < 200
    assert ref_hostile.endswith("…")


def test_label_slug_agreement_across_all_emitting_branches() -> None:
    # 1. dupe-lower and dupe-tie
    df_dupes = load_weapons(WEAPONS_DUPES)
    dupe_decs = dupes.resolve(df_dupes, crafted_level_protect=10)
    seen_slugs: set[str] = set()
    for d in dupe_decs:
        assert d.explanation is not None
        _, slug = reason_slug(d.note)
        seen_slugs.add(slug)
        assert LABELS[slug] == d.explanation.label
    assert "dupe-lower" in seen_slugs
    assert "dupe-tie" in seen_slugs

    # 2. wishlist-trash whole-item and roll
    from vault_cleaner.wishlist import WishlistSourceSpec

    wl_content = (
        "// title: Test WL\n"
        "dimwishlist:item=-500&perks=\n"  # whole-item trash for hash 500
        "dimwishlist:item=-800&perks=1001,1002\n"  # roll trash for hash 800
    )
    spec = WishlistSourceSpec(
        name="test_src", url="https://example.test", family="test_family",
        activity="any", tier_format="none"
    )
    wl = parse_wishlist(wl_content, name="test_src", spec=spec, evidence=True)
    perk_map = {"mag b": frozenset({1001}), "trait a": frozenset({1002})}
    run_res = weapons.run(
        df_dupes, wl, perk_map, crafted_level_protect=10
    )
    for d in run_res.decisions:
        assert d.explanation is not None
        _, slug = reason_slug(d.note)
        seen_slugs.add(slug)
        assert LABELS[slug] == d.explanation.label
    assert "wishlist-trash whole-item" in seen_slugs
    assert "wishlist-trash roll" in seen_slugs

    # 3. coverage-dominated by and coverage-uncovered vs
    df_cov = load_weapons(COVERAGE_FIXTURE)
    cov_wl_text = (FIXTURES / "wishlist_coverage.txt").read_text(encoding="utf-8")
    wl_cov = parse_wishlist(cov_wl_text)
    cov_perks = {
        "frame": frozenset({1000}),
        "perk a": frozenset({1}),
        "perk b": frozenset({2, 20}),
        "perk c": frozenset({3}),
        "perk d": frozenset({4}),
        "perk e": frozenset({5}),
        "perk f": frozenset({6}),
    }
    cov_res = coverage.analyse(
        df_cov, wl_cov, cov_perks, crafted_level_protect=10
    )
    for d in cov_res.decisions:
        assert d.explanation is not None
        _, slug = reason_slug(d.note)
        seen_slugs.add(slug)
        assert LABELS[slug] == d.explanation.label
    assert "coverage-dominated by" in seen_slugs
    assert "coverage-uncovered vs" in seen_slugs
