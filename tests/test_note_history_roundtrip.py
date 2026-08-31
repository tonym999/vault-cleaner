import re
from pathlib import Path

import pandas as pd
import pytest

from vault_cleaner.config import load_config
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


def _assert_round_trip(
    frame: pd.DataFrame,
    produce,
    item_id: str,
    expected_action: str,
    expected_reason: str,
) -> None:
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


def _weapon_dupes(frame):
    return dupes.resolve(frame, crafted_level_protect=10)


def _armor_exact(frame):
    return armor_dupes.run(frame, crafted_level_protect=10)


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
            "review",
            "armor-exact-dupe",
            id="armor-exact-soft-review",
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
