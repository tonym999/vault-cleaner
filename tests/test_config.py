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
