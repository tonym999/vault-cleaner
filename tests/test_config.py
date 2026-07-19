import pytest

from vault_cleaner.config import ConfigError, load_config


def test_missing_file_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "nope.toml")
    assert cfg["rails"]["crafted_level_protect"] == 10


def test_file_values_override_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[rails]\ncrafted_level_protect = 5\n")
    assert load_config(p)["rails"]["crafted_level_protect"] == 5


def test_malformed_toml_raises_config_error(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[rails\nnot toml")
    with pytest.raises(ConfigError):
        load_config(p)


@pytest.mark.parametrize(
    "snippet,match",
    [
        ("[armor.archetypes.bad]\nweights = { meele = 3.0 }", "unknown stat"),
        ("[armor]\narchetypes = {}", "at least one archetype"),
        ("[armor.archetypes.bad]\nweights = { melee = -1.0 }", ">= 0"),
        ("[armor.archetypes.bad]\nweights = { melee = 0.0 }", "positive weight"),
        ("[armor.archetypes.bad]\ntop_stats = 0", "in 1..6"),
        ("[armor.archetypes.bad]\ntop_stats = 7", "in 1..6"),
        ("[armor.archetypes.bad]\nweights = { melee = 1.0 }\ntop_stats = 2", "exactly one"),
        ("[armor.archetypes.bad]\nnothing = true", "exactly one"),
        ("[armor]\ntop_n_per_slot = -1", "non-negative"),
        ("[armor]\ntop_n_per_slot = true", "non-negative"),
        ('[armor]\nscore_floor = "high"', "finite number"),
        ("[armor]\nscore_floor = nan", "finite number"),
        ("[armor]\nset_bonus = inf", "finite number"),
        ("[armor]\nset_bonus = -10", ">= 0"),
        ("[armor.archetypes.bad]\nweights = { melee = 1.0, health = nan }", ">= 0"),
        ('[armor]\nfavored_set_perks = "Erebos Glance"', "list of non-empty strings"),
        ("[armor]\nfavored_set_perks = [1]", "list of non-empty strings"),
        ('[armor]\nfavored_set_perks = [""]', "list of non-empty strings"),
        ("armor = true", "must be a table"),
        ("rails = 5", "must be a table"),
    ],
)
def test_invalid_armor_config_rejected(tmp_path, snippet, match):
    # A silent typo here would skew every score and --write the damage
    p = tmp_path / "config.toml"
    p.write_text(snippet + "\n")
    with pytest.raises(ConfigError, match=match):
        load_config(p)


def test_valid_custom_archetype_accepted(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[armor.archetypes.grenadier]\nweights = { grenade = 3.0, super = 1.0 }\n")
    cfg = load_config(p)
    assert cfg["armor"]["archetypes"] == {"grenadier": {"weights": {"grenade": 3.0, "super": 1.0}}}
