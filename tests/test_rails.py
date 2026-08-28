import pandas as pd
import pytest

from vault_cleaner.parse import SchemaError, is_crafted
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("crafted", True),
        (" CRAFTED ", True),
        ("false", False),
        (" False ", False),
        ("", False),
        ("   ", False),
    ],
)
def test_crafted_token_parser(value, expected):
    assert is_crafted(value) is expected


@pytest.mark.parametrize("value", ["true", "unknown"])
def test_crafted_token_parser_rejects_unknown_non_empty_values(value):
    with pytest.raises(SchemaError, match="unknown DIM Crafted value"):
        is_crafted(value)


def test_crafted_at_threshold_is_hard_protected():
    level, reason = protection(
        item(Crafted="crafted", **{"Crafted Level": "10"}), 10
    )
    assert level == HARD and "crafted" in reason


def test_crafted_level_accepts_trimmed_ascii_integer():
    level, reason = protection(
        item(Crafted=" CRAFTED ", **{"Crafted Level": " 010 "}), 10
    )
    assert level == HARD and "crafted" in reason


def test_crafted_above_threshold_is_hard_protected():
    level, reason = protection(
        item(Crafted="crafted", **{"Crafted Level": "12"}), 10
    )
    assert level == HARD and "crafted" in reason


def test_crafted_below_threshold_is_not_protected():
    assert protection(
        item(Crafted="crafted", **{"Crafted Level": "2"}), 10
    ) == (None, "")


def test_false_does_not_protect_even_at_high_level():
    assert protection(
        item(Crafted="false", **{"Crafted Level": "99"}), 10
    ) == (None, "")


def test_empty_does_not_protect_even_at_high_level():
    assert protection(item(Crafted="", **{"Crafted Level": "99"}), 10) == (
        None,
        "",
    )


def test_unknown_crafted_value_fails_through_protection():
    with pytest.raises(SchemaError, match="unknown DIM Crafted value"):
        protection(item(Crafted="true", **{"Crafted Level": "12"}), 10)


@pytest.mark.parametrize(
    "level",
    ["10.0", "1e1", "+10", "-1", "١٠", "unknown", ""],
)
def test_malformed_crafted_level_fails_through_protection(level):
    with pytest.raises(SchemaError, match="Crafted Level"):
        protection(
            item(Crafted="crafted", **{"Crafted Level": level}),
            10,
        )


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
