import json

import pytest

from vault_cleaner import manifest as mf
from vault_cleaner.manifest import ManifestError, _extract_names, load_perk_map

INDEX = {
    "Response": {
        "version": "v1",
        "jsonWorldComponentContentPaths": {"en": {"DestinyInventoryItemDefinition": "/defs.json"}},
    }
}
DEFS = {
    "101": {"plug": {"plugCategoryIdentifier": "frames"}, "displayProperties": {"name": "Perk A"}},
    "102": {"plug": {"plugCategoryIdentifier": "frames"}, "displayProperties": {"name": "Perk A"}},
    "103": {"plug": {}, "displayProperties": {"name": "No Plug Block"}},
    "104": {"displayProperties": {"name": "Not A Plug"}},
    "105": {"plug": {"plugCategoryIdentifier": "frames"}, "displayProperties": {"name": ""}},
}


def fake_get(index=INDEX, defs=DEFS):
    def _get(url, timeout=300):
        return index if "Platform" in url else defs
    return _get


def test_extract_names_plugs_only_casefolded():
    names = _extract_names(DEFS)
    assert names == {"perk a": [101, 102]}


def test_builds_and_caches_map(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "_get_json", fake_get())
    pm = load_perk_map(tmp_path)
    assert pm["perk a"] == frozenset({101, 102})
    cached = json.loads((tmp_path / "perk-name-map.json").read_text())
    assert cached["version"] == "v1"


def test_fresh_cache_skips_network(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "_get_json", fake_get())
    load_perk_map(tmp_path)

    def explode(url, timeout=300):
        raise AssertionError("network touched despite fresh cache")

    monkeypatch.setattr(mf, "_get_json", explode)
    assert load_perk_map(tmp_path)["perk a"] == frozenset({101, 102})


def test_stale_cache_same_version_skips_big_download(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "_get_json", fake_get())
    load_perk_map(tmp_path)

    calls = []

    def index_only(url, timeout=300):
        calls.append(url)
        assert "Platform" in url, "big definitions file re-downloaded for unchanged version"
        return INDEX

    monkeypatch.setattr(mf, "_get_json", index_only)
    assert load_perk_map(tmp_path, max_age_days=0)["perk a"] == frozenset({101, 102})
    assert calls  # index was consulted


def test_new_version_rebuilds(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "_get_json", fake_get())
    load_perk_map(tmp_path)
    new_index = {"Response": {**INDEX["Response"], "version": "v2"}}
    new_defs = {"201": {"plug": {"plugCategoryIdentifier": "frames"}, "displayProperties": {"name": "Perk B"}}}
    monkeypatch.setattr(mf, "_get_json", fake_get(new_index, new_defs))
    pm = load_perk_map(tmp_path, max_age_days=0)
    assert pm == {"perk b": frozenset({201})}


def test_structurally_invalid_cache_rebuilt(tmp_path, monkeypatch):
    # Valid JSON but wrong shape ({}, wrong types) must rebuild, not KeyError
    for bad in (
        "{}",
        '{"version": 1, "names": {}}',
        '{"version": "v1", "names": []}',
        '{"version": "v1", "names": {"perk a": null}}',
        '{"version": "v1", "names": {"perk a": [1, "bad"]}}',
        '{"version": "v1", "names": {"perk a": [true]}}',
        "not json",
    ):
        (tmp_path / "perk-name-map.json").write_text(bad)
        monkeypatch.setattr(mf, "_get_json", fake_get())
        assert load_perk_map(tmp_path)["perk a"] == frozenset({101, 102})
        (tmp_path / "perk-name-map.json").unlink()


def test_unwritable_cache_still_returns_map(tmp_path, monkeypatch, capsys):
    # Deterministic across filesystems (chmod is unreliable on Windows-backed
    # mounts): fail the write itself.
    monkeypatch.setattr(mf, "_get_json", fake_get())

    def fail_write(self, *args, **kwargs):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(mf.Path, "write_text", fail_write)
    assert load_perk_map(tmp_path)["perk a"] == frozenset({101, 102})
    assert "could not write perk map cache" in capsys.readouterr().err


def _down(url, timeout=300):
    raise OSError("bungie down")


def test_index_down_falls_back_to_cache(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mf, "_get_json", fake_get())
    load_perk_map(tmp_path)
    monkeypatch.setattr(mf, "_get_json", _down)
    assert load_perk_map(tmp_path, max_age_days=0)["perk a"] == frozenset({101, 102})
    assert "cached perk map" in capsys.readouterr().err


def test_index_down_without_cache_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(mf, "_get_json", _down)
    with pytest.raises(ManifestError, match="no cached perk map"):
        load_perk_map(tmp_path)
