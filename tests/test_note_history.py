import pytest

from vault_cleaner.note_history import (
    append_tool_clause,
    strip_trailing_tool_clauses,
)


@pytest.mark.parametrize(
    "clause",
    [
        "#vc-junk: dupe-lower, kept 3001",
        "#vc-review: armor-exact-dupe (locked), kept 5001",
        (
            "#vc-junk: dupe-lower; keep [id …3001; owner Vault]; "
            "winner higher Masterwork Tier"
        ),
        (
            "#vc-review: armor-exact-dupe-tie; keep [id …5001]; "
            "winner deterministic id tie-break"
        ),
        (
            "#vc-junk: armor-exact-dupe; keep [id …5001]; "
            "winner Masterwork Tier"
        ),
        "#vc-review: armor-dominated by 6001 (+5 total)",
        (
            "#vc-review: armor-dominated by; compare [id …6001]; +5 total; "
            "partner largest stat surplus"
        ),
        (
            "#vc-review: armor-similar to; compare [id …6012; owner Vault]; "
            "max stat delta 2, total 4; partner closest stat distance"
        ),
        "#vc-junk: wishlist-trash whole-item",
        "#vc-review: wishlist-trash roll (exotic)",
        (
            "#vc-junk: armor-score 41.0 < floor 65 "
            "(best: melee_primary, rank 9/9 titan chest armor)"
        ),
        (
            "#vc-review: armor-score 27.6 < floor 65 "
            "(best: melee_primary, rank 7/8 titan chest armor) (locked)"
        ),
        (
            "#vc-review: armor-last-archetype (no archetype), armor-score "
            "30.0 < floor 65 "
            "(best: melee_primary, rank 6/8 titan chest armor)"
        ),
        "#vc-junk: ghost-unprotected-surplus",
    ],
)
def test_known_trailing_tool_clause_is_removed(clause):
    assert strip_trailing_tool_clauses(f"manual build note {clause}") == (
        "manual build note"
    )


def test_multiple_trailing_tool_clauses_are_removed_without_user_text():
    notes = (
        "manual build note "
        "#vc-junk: dupe-lower, kept 1 "
        "#vc-review: armor-similar to 2 (identical stats)"
    )

    assert strip_trailing_tool_clauses(notes) == "manual build note"


def test_ambiguous_tool_looking_user_text_is_preserved():
    notes = "manual #vc-junk: dupe-lower, kept 1 remember this roll"
    current = "#vc-junk: dupe-lower, kept 2"

    assert append_tool_clause(notes, current) == f"{notes} {current}"


def test_repeated_current_clause_replaces_instead_of_compounding():
    current = (
        "#vc-junk: dupe-lower; keep [id …3001; owner Vault]; "
        "winner higher Masterwork Tier"
    )
    note = "manual build note"

    for _ in range(5):
        note = append_tool_clause(note, current)

    assert note == f"manual build note {current}"
    assert note.count("#vc-junk:") == 1


def test_unknown_tool_namespace_text_is_not_claimed():
    notes = "manual note #vc-test: sacrificial item"

    assert strip_trailing_tool_clauses(notes) == notes
