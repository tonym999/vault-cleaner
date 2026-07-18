import os
import time
from pathlib import Path

import pytest

from vault_cleaner import wishlist as wl_mod
from vault_cleaner.wishlist import Wishlist, WishlistError, fetch, parse_wishlist

FIXTURE = Path(__file__).parent / "fixtures" / "wishlist.txt"


@pytest.fixture
def parsed():
    return parse_wishlist(FIXTURE.read_text(), "fixture")


def test_keep_rolls_grouped_by_item(parsed):
    assert parsed.keep[111] == [frozenset({1, 2, 3}), frozenset({1, 2, 4})]


def test_inline_notes_suffix_stripped(parsed):
    assert parsed.keep[222] == [frozenset({5, 6})]


def test_whole_item_trash_entry_has_empty_perks(parsed):
    assert parsed.trash[333] == [frozenset()]


def test_trash_roll_with_perks(parsed):
    assert parsed.trash[444] == [frozenset({7, 8})]


def test_wildcard_entries_counted_not_stored(parsed):
    assert parsed.wildcards == 1
    assert 69420 not in parsed.keep and 69420 not in parsed.trash


def test_malformed_wishlist_line_counted(parsed):
    assert parsed.skipped == 1  # item=oops


def test_non_wishlist_lines_ignored_silently(parsed):
    # titles, comments, prose, @description junk — no effect on any counter
    assert parsed.entries == 5  # 3 keep rolls + 2 trash entries


def test_merge_combines_and_sums():
    a = parse_wishlist("dimwishlist:item=1&perks=10", "a")
    b = parse_wishlist("dimwishlist:item=1&perks=11\ndimwishlist:item=-2", "b")
    a.merge(b)
    assert a.keep[1] == [frozenset({10}), frozenset({11})]
    assert a.trash[2] == [frozenset()]


def test_fetch_downloads_and_caches(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: calls.append(url) or "data")
    p = fetch("test", "https://x/w.txt", cache_dir=tmp_path)
    assert p.read_text() == "data"
    fetch("test", "https://x/w.txt", cache_dir=tmp_path)
    assert len(calls) == 1  # fresh cache — no second download


def test_fetch_stale_cache_redownloads(tmp_path, monkeypatch):
    p = tmp_path / "test.txt"
    p.write_text("old")
    os.utime(p, (time.time() - 8 * 86400, time.time() - 8 * 86400))
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: "new")
    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=7).read_text() == "new"


def test_fetch_refresh_forces_download(tmp_path, monkeypatch):
    (tmp_path / "test.txt").write_text("old")
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: "new")
    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path, refresh=True).read_text() == "new"


def _boom(url, timeout=30):
    raise OSError("network down")


def test_fetch_failure_falls_back_to_stale_cache(tmp_path, monkeypatch, capsys):
    p = tmp_path / "test.txt"
    p.write_text("stale")
    os.utime(p, (0, 0))
    monkeypatch.setattr(wl_mod, "_download", _boom)
    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path).read_text() == "stale"
    assert "stale cache" in capsys.readouterr().err


def test_fetch_failure_without_cache_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_mod, "_download", _boom)
    with pytest.raises(WishlistError, match="no cached copy"):
        fetch("test", "https://x/w.txt", cache_dir=tmp_path)
