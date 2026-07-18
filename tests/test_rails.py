import pandas as pd
import pytest

from vault_cleaner.rules.rails import HARD, SOFT, protection


def item(**kv):
    base = {"Tag": "", "Equipped": "false", "Locked": "false", "Rarity": "Legendary",
            "Crafted": "false", "Crafted Level": "0"}
    base.update(kv)
    return pd.Series(base)


@pytest.mark.parametrize("tag", ["favorite", "keep", "archive"])
def test_dim_tags_are_hard_protected(tag):
    assert protection(item(Tag=tag), 10) == (HARD, f"dim-tag:{tag}")


def test_equipped_is_hard_protected():
    assert protection(item(Equipped="true"), 10) == (HARD, "equipped")


def test_crafted_above_threshold_is_hard_protected():
    level, reason = protection(item(Crafted="true", **{"Crafted Level": "12"}), 10)
    assert level == HARD and "crafted" in reason


def test_crafted_below_threshold_is_not_protected():
    assert protection(item(Crafted="true", **{"Crafted Level": "2"}), 10) == (None, "")


def test_exotic_is_soft_protected():
    assert protection(item(Rarity="Exotic"), 10) == (SOFT, "exotic")


def test_locked_is_soft_protected():
    assert protection(item(Locked="true"), 10) == (SOFT, "locked")


def test_hard_wins_over_soft():
    # An equipped exotic is hard-protected, not merely review-flagged.
    level, _ = protection(item(Rarity="Exotic", Equipped="true"), 10)
    assert level == HARD


def test_plain_legendary_is_unprotected():
    assert protection(item(), 10) == (None, "")
