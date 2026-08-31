import re
from pathlib import Path

import pandas as pd
import pytest

from vault_cleaner.config import load_config
from vault_cleaner.duplicate_reference import format_tuning_comparison
from vault_cleaner.note_history import strip_trailing_tool_clauses
from vault_cleaner.parse import load_armor, load_ghosts, load_weapons
from vault_cleaner.report import reason_slug
from vault_cleaner.rules import armor, armor_close, armor_dupes, dupes, ghosts, weapons
from vault_cleaner.wishlist import parse_wishlist

WEAPON_FIXTURE = Path(__file__).parent / "fixtures" / "weapons_dupes.csv"
ARMOR_FIXTURE = Path(__file__).parent / "fixtures" / "armor.csv"
ARMOR_DUPES_FIXTURE = Path(__file__).parent / "fixtures" / "armor_dupes.csv"
ARMOR_CLOSE_FIXTURE = Path(__file__).parent / "fixtures" / "armor_close.csv"
GHOST_FIXTURE = Path(__file__).parent / "fixtures" / "ghosts_cleanup.csv"

CURRENT_MARKER = re.compile(r"#vc-(?:junk|review):")
USER_PREFIX = "human-authored context stays exactly as written"


def _set_notes(frame: pd.DataFrame, item_id: str, notes: str) -> pd.DataFrame:
    result = frame.copy()
    matching = result["Id"].astype(str) == item_id
    assert matching.sum() == 1
    result.loc[matching, "Notes"] = notes
    return result


def _decision(decisions, item_id: str):
    matching = [decision for decision in decisions if decision.id == item_id]
    assert len(matching) == 1
    return matching[0]


def _comparison_from_selected_id(
    frame: pd.DataFrame, decision: dupes.Decision, *, selected_label: str
) -> str:
    rows = {str(row["Id"]): row for _, row in frame.iterrows()}
    return format_tuning_comparison(
        rows[decision.id]["Tuning Stat"],
        rows[decision.kept_id]["Tuning Stat"],
        selected_label=selected_label,
    )


def _assert_round_trip(
    frame: pd.DataFrame,
    produce,
    item_id: str,
    expected_action: str,
    expected_reason: str,
) -> dupes.Decision:
    """Prove an emitter's own current clause is safe to round-trip.

    The test deliberately never reconstructs the generated clause.  It takes
    the first emitted note verbatim, feeds it back as DIM's next Notes value,
    and requires later rule runs to emit the same note while preserving the
    exact human-authored prefix.
    """
    current = _set_notes(frame, item_id, USER_PREFIX)
    first = _decision(produce(current), item_id)
    assert first.action == expected_action
    actual_action, actual_reason = reason_slug(first.note)
    assert actual_action == expected_action
    assert actual_reason == expected_reason
    assert first.note.startswith(f"{USER_PREFIX} ")
    assert first.note[: len(USER_PREFIX)] == USER_PREFIX
    assert len(CURRENT_MARKER.findall(first.note)) == 1
    assert strip_trailing_tool_clauses(first.note) == USER_PREFIX

    for _ in range(3):
        current = _set_notes(current, item_id, first.note)
        repeated = _decision(produce(current), item_id)
        assert repeated.action == first.action
        assert repeated.note == first.note
        assert repeated.note[: len(USER_PREFIX)] == USER_PREFIX
        assert len(CURRENT_MARKER.findall(repeated.note)) == 1
        assert strip_trailing_tool_clauses(repeated.note) == USER_PREFIX
    return first


def _weapon_dupes(frame):
    return dupes.resolve(frame, crafted_level_protect=10)


def _weapon_crafted_level_frame():
    frame = load_weapons(WEAPON_FIXTURE)
    frame = frame[frame["Id"].isin(("3001", "3002"))].copy()
    frame.loc[frame["Id"] == "3001", "Id"] = "crafted-rank-winner"
    frame.loc[frame["Id"] == "3002", "Id"] = "crafted-rank-loser"
    frame["Masterwork Tier"] = "0"
    frame["Crafted"] = "crafted"
    frame.loc[frame["Id"] == "crafted-rank-winner", "Crafted Level"] = "4"
    frame.loc[frame["Id"] == "crafted-rank-loser", "Crafted Level"] = "3"
    frame["Notes"] = ""
    return frame


def _weapon_stat_total_frame():
    frame = load_weapons(WEAPON_FIXTURE)
    frame = frame[frame["Id"].isin(("3041", "3042"))].copy()
    frame.loc[frame["Id"] == "3041", "Impact"] = "31"
    frame.loc[frame["Id"] == "3042", "Impact"] = "30"
    frame["Notes"] = ""
    return frame


def _armor_exact(frame):
    return armor_dupes.run(frame, crafted_level_protect=10)


def _armor_exotic_class_loadout(frame):
    frame = frame.copy()
    frame.loc[frame["Id"] == "5031", "Equipped"] = "true"
    frame.loc[frame["Id"] == "5032", "Loadouts"] = "PvE Build"
    return _armor_exact(frame)


def _armor_exotic_class_locked(frame):
    frame = frame.copy()
    frame.loc[frame["Id"] == "5031", "Equipped"] = "true"
    frame.loc[frame["Id"] == "5032", "Locked"] = "true"
    return _armor_exact(frame)


def _close_cfg() -> dict:
    return load_config(Path("nonexistent.toml"))


def _armor_close(frame):
    return armor_close.run(frame, _close_cfg())


def _score_cfg() -> dict:
    cfg = load_config(Path("nonexistent.toml"))
    cfg["armor"]["top_n_per_slot"] = 2
    cfg["armor"]["score_floor"] = 60
    cfg["armor"]["favored_set_perks"] = ["Test Set Perk"]
    cfg["armor"]["archetypes"]["spike"] = {"top_stats": 2}
    return cfg


def _armor_score(frame):
    # Neutralize the guard for the ordinary junk and soft-review cases.
    kept_elsewhere = frozenset(
        (item_hash, archetype)
        for item_hash, archetype in zip(frame["Hash"], frame["Archetype"])
    )
    return armor.run(frame, _score_cfg(), kept_elsewhere).decisions


def _armor_last_archetype(frame):
    return armor.run(frame, _score_cfg(), frozenset()).decisions


def _ghosts(frame):
    return ghosts.run(frame)


def _wishlist_frame(item_hash: str, *, locked: bool = False, exotic: bool = False):
    frame = load_weapons(WEAPON_FIXTURE).iloc[[0]].copy()
    frame["Hash"] = item_hash
    frame["Id"] = "wishlist-roundtrip"
    frame["Rarity"] = "Exotic" if exotic else "Legendary"
    frame["Locked"] = "true" if locked else "false"
    frame["Equipped"] = "false"
    frame["Tag"] = ""
    frame["Perks 0"] = "Bad Perk"
    return frame


_PERK_MAP = {"bad perk": frozenset({3})}
_WHOLE_ITEM_TRASH = parse_wishlist("dimwishlist:item=-200&perks=\n")
_ROLL_TRASH = parse_wishlist("dimwishlist:item=-300&perks=3\n")


def _wishlist_whole_junk(frame):
    return weapons.run(frame, _WHOLE_ITEM_TRASH, _PERK_MAP, 10).decisions


def _wishlist_whole_review(frame):
    return weapons.run(frame, _WHOLE_ITEM_TRASH, _PERK_MAP, 10).decisions


def _wishlist_roll_junk(frame):
    return weapons.run(frame, _ROLL_TRASH, _PERK_MAP, 10).decisions


def _wishlist_roll_review(frame):
    return weapons.run(frame, _ROLL_TRASH, _PERK_MAP, 10).decisions


@pytest.mark.parametrize(
    ("frame", "produce", "item_id", "action", "reason"),
    [
        pytest.param(
            load_weapons(WEAPON_FIXTURE),
            _weapon_dupes,
            "3002",
            "junk",
            "dupe-lower",
            id="weapon-dupe-junk",
        ),
        pytest.param(
            load_weapons(WEAPON_FIXTURE),
            _weapon_dupes,
            "3003",
            "review",
            "dupe-lower",
            id="weapon-dupe-review",
        ),
        pytest.param(
            load_weapons(WEAPON_FIXTURE),
            _weapon_dupes,
            "3042",
            "junk",
            "dupe-tie",
            id="weapon-dupe-tie",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exact,
            "5002",
            "junk",
            "armor-exact-dupe",
            id="armor-exact-junk",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exact,
            "5012",
            "review",
            "armor-exact-dupe",
            id="armor-exact-loadout-review",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exact,
            "5032",
            "junk",
            "armor-exotic-class-dupe",
            id="armor-exact-exotic-class-junk",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exotic_class_loadout,
            "5032",
            "review",
            "armor-exotic-class-dupe",
            id="armor-exact-exotic-class-loadout-review",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exotic_class_locked,
            "5032",
            "review",
            "armor-exotic-class-dupe",
            id="armor-exact-exotic-class-locked-review",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exact,
            "5022",
            "junk",
            "armor-exact-dupe-tie",
            id="armor-exact-tie",
        ),
        pytest.param(
            load_armor(ARMOR_CLOSE_FIXTURE),
            _armor_close,
            "6002",
            "review",
            "armor-dominated by",
            id="armor-close-dominated",
        ),
        pytest.param(
            load_armor(ARMOR_CLOSE_FIXTURE),
            _armor_close,
            "6011",
            "review",
            "armor-similar to",
            id="armor-close-similar",
        ),
        pytest.param(
            _wishlist_frame("200"),
            _wishlist_whole_junk,
            "wishlist-roundtrip",
            "junk",
            "wishlist-trash whole-item",
            id="wishlist-whole-junk",
        ),
        pytest.param(
            _wishlist_frame("200", locked=True),
            _wishlist_whole_review,
            "wishlist-roundtrip",
            "review",
            "wishlist-trash whole-item",
            id="wishlist-whole-review",
        ),
        pytest.param(
            _wishlist_frame("300"),
            _wishlist_roll_junk,
            "wishlist-roundtrip",
            "junk",
            "wishlist-trash roll",
            id="wishlist-roll-junk",
        ),
        pytest.param(
            _wishlist_frame("300", locked=True),
            _wishlist_roll_review,
            "wishlist-roundtrip",
            "review",
            "wishlist-trash roll",
            id="wishlist-roll-review-locked",
        ),
        pytest.param(
            _wishlist_frame("300", exotic=True),
            _wishlist_roll_review,
            "wishlist-roundtrip",
            "review",
            "wishlist-trash roll",
            id="wishlist-roll-review-exotic",
        ),
        pytest.param(
            load_armor(ARMOR_FIXTURE),
            _armor_score,
            "4004",
            "junk",
            "armor-score",
            id="armor-score-junk",
        ),
        pytest.param(
            load_armor(ARMOR_FIXTURE),
            _armor_score,
            "4006",
            "review",
            "armor-score",
            id="armor-score-review",
        ),
        pytest.param(
            load_armor(ARMOR_FIXTURE),
            _armor_last_archetype,
            "4004",
            "review",
            "armor-last-archetype",
            id="armor-last-archetype",
        ),
        pytest.param(
            load_ghosts(GHOST_FIXTURE),
            _ghosts,
            "6007",
            "junk",
            "ghost-unprotected-surplus",
            id="ghost-junk",
        ),
    ],
)
def test_current_emitter_notes_round_trip(
    frame, produce, item_id, action, reason
):
    _assert_round_trip(frame, produce, item_id, action, reason)


@pytest.mark.parametrize(
    ("frame", "produce", "item_id", "action", "reason", "winner"),
    [
        pytest.param(
            load_weapons(WEAPON_FIXTURE),
            _weapon_dupes,
            "3032",
            "junk",
            "dupe-lower",
            "higher Tier",
            id="weapon-winner-tier",
        ),
        pytest.param(
            _weapon_crafted_level_frame(),
            _weapon_dupes,
            "crafted-rank-loser",
            "junk",
            "dupe-lower",
            "higher Crafted Level",
            id="weapon-winner-crafted-level",
        ),
        pytest.param(
            _weapon_stat_total_frame(),
            _weapon_dupes,
            "3042",
            "junk",
            "dupe-lower",
            "higher stat total",
            id="weapon-winner-stat-total",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exact,
            "5082",
            "junk",
            "armor-exact-dupe",
            "loadout membership",
            id="armor-winner-loadout",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exact,
            "5092",
            "junk",
            "armor-exact-dupe",
            "lock",
            id="armor-winner-lock",
        ),
        pytest.param(
            load_armor(ARMOR_DUPES_FIXTURE),
            _armor_exact,
            "5072",
            "junk",
            "armor-exact-dupe",
            "higher Power",
            id="armor-winner-power",
        ),
    ],
)
def test_exact_dupe_winner_labels_round_trip(
    frame, produce, item_id, action, reason, winner
):
    first = _assert_round_trip(frame, produce, item_id, action, reason)
    if reason.startswith("armor-"):
        expected = _comparison_from_selected_id(
            frame, first, selected_label="Survivor"
        )
        assert first.note.endswith(f"; winner {winner}; {expected}")
    else:
        assert first.note.endswith(f"; winner {winner}")


@pytest.mark.parametrize(
    ("frame", "item_id", "reason", "partner_id"),
    [
        pytest.param(
            load_armor(ARMOR_CLOSE_FIXTURE),
            "6033",
            "armor-dominated by",
            "6031",
            id="armor-close-dominated-partner-tie",
        ),
        pytest.param(
            load_armor(ARMOR_FIXTURE),
            "4051",
            "armor-similar to",
            "4052",
            id="armor-close-similar-partner-tie",
        ),
    ],
)
def test_armor_close_partner_tie_labels_round_trip(
    frame, item_id, reason, partner_id
):
    # Call the close emitter directly so 6033 sees both equal-surplus
    # dominators (6031 and 6032); the normal pipeline removes 6032 in the
    # exact pass first.  Guard Plate 4051 likewise has two equally close
    # similar partners (4052 and 4053).
    first = _assert_round_trip(frame, _armor_close, item_id, "review", reason)
    assert first.kept_id == partner_id
    expected = _comparison_from_selected_id(
        frame, first, selected_label="Partner"
    )
    assert first.note.endswith(f"; partner deterministic id tie-break; {expected}")
