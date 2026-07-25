import hashlib
from pathlib import Path

import pytest

from vault_cleaner import pipeline
from vault_cleaner import wishlist as wishlist_module
from vault_cleaner.config import load_config
from vault_cleaner.manifest import PerkMapData
from vault_cleaner.parse import load_weapons
from vault_cleaner.wishlist import WishlistError

FIXTURE = Path(__file__).parent / "fixtures" / "weapons_dupes.csv"


def test_weapon_pipeline_captures_actual_external_input_identities(
    tmp_path, monkeypatch
):
    cfg = load_config("nonexistent.toml")
    cfg["paths"]["wishlist_cache_dir"] = str(tmp_path / "wishlists")
    cfg["paths"]["manifest_cache_dir"] = str(tmp_path / "manifest")
    cfg["wishlists"]["sources"] = {
        "test": "https://example.test/wishlist",
    }

    cache = Path(cfg["paths"]["wishlist_cache_dir"])
    cache.mkdir()
    raw = "title changed but parsed rolls did not\n"
    (cache / "test.txt").write_text(raw)

    monkeypatch.setattr(
        pipeline,
        "load_perk_map_data",
        lambda *args: PerkMapData(names={}, version="manifest-v1"),
    )

    result = pipeline.resolve_weapons(load_weapons(FIXTURE), cfg)
    assert result.wishlists_used
    assert result.wishlist_sources[0].name == "test"
    assert result.wishlist_sources[0].sha256 == hashlib.sha256(raw.encode()).hexdigest()
    assert result.manifest is not None
    assert result.manifest.version == "manifest-v1"
    assert len(result.manifest.sha256) == 64


def test_missing_wishlist_cache_has_a_domain_error(tmp_path, monkeypatch):
    cfg = load_config("nonexistent.toml")
    cfg["paths"]["wishlist_cache_dir"] = str(tmp_path / "wishlists")
    cfg["wishlists"]["sources"] = {
        "test": "https://example.test/wishlist",
    }
    missing = tmp_path / "wishlists" / "missing.txt"
    monkeypatch.setattr(wishlist_module, "fetch", lambda *args, **kwargs: missing)

    with pytest.raises(WishlistError, match="could not read cached wishlist"):
        pipeline.resolve_weapons(load_weapons(FIXTURE), cfg)
