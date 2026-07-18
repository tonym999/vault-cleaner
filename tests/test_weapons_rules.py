import pandas as pd

from vault_cleaner.rules.weapons import keep_match_count, row_perk_hashes, run, trash_match
from vault_cleaner.wishlist import parse_wishlist

PERK_MAP = {
    "perk a": frozenset({1}),
    "perk b": frozenset({2, 20}),  # base + enhanced variant share the name
    "bad perk": frozenset({3}),
}

WISHLIST = parse_wishlist(
    "\n".join(
        [
            "dimwishlist:item=100&perks=1,2",  # keep roll for hash 100
            "dimwishlist:item=-200&perks=",  # whole-item trash
            "dimwishlist:item=-300&perks=3",  # roll-specific trash
        ]
    )
)


def weapon(id, hash, perks=(), **kv):
    base = {
        "Name": f"W{hash}", "Hash": str(hash), "Id": id, "Tag": "",
        "Rarity": "Legendary", "Locked": "false", "Equipped": "false",
        "Crafted": "false", "Crafted Level": "0", "Tier": "5",
        "Masterwork Tier": "0", "Notes": "", "Owner": "Vault",
    }
    for i, p in enumerate(perks):
        base[f"Perks {i}"] = p
    base.update(kv)
    return base


def df(*rows):
    frame = pd.DataFrame(rows).fillna("")
    return frame.astype(str)


def test_row_perk_hashes_strips_star_and_casefolds():
    row = df(weapon("1", 100, perks=["Perk A*", "PERK B"])).iloc[0]
    assert row_perk_hashes(row, PERK_MAP) == frozenset({1, 2, 20})


def test_keep_and_trash_matching():
    row = df(weapon("1", 100, perks=["Perk A", "Perk B"])).iloc[0]
    hashes = row_perk_hashes(row, PERK_MAP)
    assert keep_match_count(100, hashes, WISHLIST) == 1
    assert trash_match(200, hashes, WISHLIST) == "whole-item"
    assert trash_match(300, frozenset({3}), WISHLIST) == "roll"
    assert trash_match(300, frozenset({1}), WISHLIST) is None


def test_keep_match_outranks_masterwork_in_dupes():
    weapons = df(
        weapon("A", 100, perks=["Perk A", "Perk B"]),  # keep-matched, MW 0
        weapon("B", 100, **{"Masterwork Tier": "10"}),  # unmatched, MW 10
    )
    decisions = run(weapons, WISHLIST, PERK_MAP, 10)
    assert [(d.id, d.action) for d in decisions] == [("B", "junk")]
    assert decisions[0].kept_id == "A"


def test_whole_item_trash_junked_locked_copy_reviewed():
    weapons = df(
        weapon("A", 200),
        weapon("B", 200, Locked="true"),
    )
    decisions = {d.id: d for d in run(weapons, WISHLIST, PERK_MAP, 10)}
    assert decisions["B"].action == "review"
    assert "wishlist-trash whole-item (locked)" in decisions["B"].note
    junked = decisions["A"]
    assert junked.action == "junk"
    assert "#vc-junk: wishlist-trash whole-item" in junked.note


def test_keep_roll_protects_from_trash():
    # Hash 200 is whole-item trash, but this copy also matches a keep roll
    wl = parse_wishlist("dimwishlist:item=200&perks=1\ndimwishlist:item=-200&perks=")
    weapons = df(weapon("A", 200, perks=["Perk A"]))
    assert run(weapons, wl, PERK_MAP, 10) == []


def test_roll_trash_only_hits_matching_roll():
    weapons = df(
        weapon("A", 300, perks=["Bad Perk"]),
        weapon("B", 301, perks=["Perk A"]),
    )
    decisions = run(weapons, WISHLIST, PERK_MAP, 10)
    assert [(d.id, d.action) for d in decisions] == [("A", "junk")]
    assert "wishlist-trash roll" in decisions[0].note


def test_no_double_row_when_trash_and_dupe_lower():
    weapons = df(
        weapon("A", 200, **{"Masterwork Tier": "10"}),
        weapon("B", 200),
    )
    decisions = run(weapons, WISHLIST, PERK_MAP, 10)
    assert sorted(d.id for d in decisions) == ["A", "B"]
    assert all("wishlist-trash" in d.note for d in decisions)


def test_hard_protected_never_trash_tagged():
    weapons = df(weapon("A", 200, Tag="favorite"))
    assert run(weapons, WISHLIST, PERK_MAP, 10) == []
