import argparse
import os
import time

from vault_cleaner import wishlist as wl_mod
from vault_cleaner.cli import _cmd_wishlists


def test_wishlists_cli_output_two_families(tmp_path, monkeypatch, capsys):
    fixed_mtime = 1700000000.0  # 2023-11-14T22:13:20Z
    now = fixed_mtime + 86400 * 2.5
    monkeypatch.setattr(time, "time", lambda: now)

    p1 = tmp_path / "s1.txt"
    p1.write_text(
        "title: S1 Title\n"
        "//notes:First note|tags:pve\n"
        "dimwishlist:item=10&perks=1,2\n"
        "dimwishlist:item=-20&perks=\n"
        "dimwishlist:item=malformed\n"
        "dimwishlist:item=69420&perks=1,2\n",
        encoding="utf-8",
    )
    os.utime(p1, (fixed_mtime, fixed_mtime))

    p2 = tmp_path / "s2.txt"
    p2.write_text(
        "title: S2 Title\n"
        "//notes:Aegis Endgame S Tier.\n"
        "dimwishlist:item=30&perks=3,4\n",
        encoding="utf-8",
    )
    os.utime(p2, (fixed_mtime, fixed_mtime))

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
wishlist_cache_dir = "{tmp_path.as_posix()}"

[wishlists]
max_age_days = 7

[wishlists.sources]
s1 = "https://example.test/s1.txt"

[wishlists.sources.s2]
url = "https://example.test/s2.txt"
family = "fam-beta"
activity = "pve"
tier_format = "ciceron-aegis"
"""
    )

    rc = _cmd_wishlists(argparse.Namespace(config=str(cfg_file), refresh=False))
    assert rc == 0
    captured = capsys.readouterr()

    s1_extras = ["1 malformed lines skipped", "1 wildcard entries ignored"]
    s1_suffix = f" ({', '.join(s1_extras)})"
    s1_line = f"s1: 1 keep rolls across 1 items, 1 trash entries across 1 items{s1_suffix}"
    s2_suffix = ""
    s2_line = f"s2: 1 keep rolls across 1 items, 0 trash entries across 0 items{s2_suffix}"
    total_line = f"total: {1 + 1} keep rolls, {1 + 0} trash entries"

    expected_out = (
        f"{s1_line}\n"
        "  family: s1; activity: any; tier format: none\n"
        "  fetch: served from cache; cache written 2023-11-14T22:13:20Z (2.5 days old; refresh after 7 days)\n"
        "  declared title: S1 Title\n"
        "  notes: 2 of 2 entries have notes, 2 have tags; tiers: not declared\n"
        f"{s2_line}\n"
        "  family: fam-beta; activity: pve; tier format: ciceron-aegis\n"
        "  fetch: served from cache; cache written 2023-11-14T22:13:20Z (2.5 days old; refresh after 7 days)\n"
        "  declared title: S2 Title\n"
        "  notes: 1 of 1 entries have notes, 0 have tags; tiers: S=1\n"
        "families: fam-beta = s2; s1 = s1\n"
        f"{total_line}\n"
    )
    assert captured.out == expected_out


def test_wishlists_cli_stale_fallback(tmp_path, monkeypatch, capsys):
    fixed_mtime = 1700000000.0
    now = fixed_mtime + 86400 * 10.0  # 10 days old, max_age is 7 -> stale
    monkeypatch.setattr(time, "time", lambda: now)
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: (_ for _ in ()).throw(OSError("offline")))

    p = tmp_path / "stale_src.txt"
    p.write_text("dimwishlist:item=1&perks=10\n", encoding="utf-8")
    os.utime(p, (fixed_mtime, fixed_mtime))

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
wishlist_cache_dir = "{tmp_path.as_posix()}"

[wishlists]
max_age_days = 7

[wishlists.sources]
stale_src = "https://example.test/stale.txt"
"""
    )

    rc = _cmd_wishlists(argparse.Namespace(config=str(cfg_file), refresh=False))
    assert rc == 0
    captured = capsys.readouterr()
    assert "stale cache used after failed download" in captured.out
    assert "warning: stale_src: download failed (offline); using stale cache" in captured.err


def test_wishlists_cli_ignored_segment_counts_per_source(tmp_path, capsys):
    p1 = tmp_path / "src_a.txt"
    p1.write_text(
        "//notes:Block 1|tags:pve|ignored:one\n"
        "dimwishlist:item=1&perks=10\n",
        encoding="utf-8",
    )
    p2 = tmp_path / "src_b.txt"
    p2.write_text(
        "//notes:Block 2|ignored:first\n"
        "dimwishlist:item=2&perks=20\n"
        "//notes:Block 3|tags:pve|ignored:extra\n"
        "dimwishlist:item=3&perks=30\n",
        encoding="utf-8",
    )
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
wishlist_cache_dir = "{tmp_path.as_posix()}"

[wishlists]
max_age_days = 7

[wishlists.sources]
src_a = "https://example.test/a"
src_b = "https://example.test/b"
"""
    )
    rc = _cmd_wishlists(argparse.Namespace(config=str(cfg_file), refresh=False))
    assert rc == 0
    captured = capsys.readouterr()
    assert "; 1 entries had ignored note segments" in captured.out
    assert "; 2 entries had ignored note segments" in captured.out
    assert "; 3 entries had ignored note segments" not in captured.out


def test_wishlists_cli_title_escaping_and_truncation(tmp_path, capsys):
    long_raw_title = "A" * 50 + "\x00\x1b" + "B" * 60
    p = tmp_path / "title_src.txt"
    p.write_text(
        f"title: {long_raw_title}\n"
        "dimwishlist:item=1&perks=10\n",
        encoding="utf-8",
    )
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
wishlist_cache_dir = "{tmp_path.as_posix()}"

[wishlists]
max_age_days = 7

[wishlists.sources]
title_src = "https://example.test/t"
"""
    )
    rc = _cmd_wishlists(argparse.Namespace(config=str(cfg_file), refresh=False))
    assert rc == 0
    captured = capsys.readouterr()
    escaped = "".join(c if c.isprintable() else f"\\u{ord(c):04x}" for c in long_raw_title)
    prefix = escaped[:100]
    assert len(prefix) == 100
    expected_title = prefix + "…"
    assert f"  declared title: {expected_title}" in captured.out.splitlines()


def test_wishlists_cli_families_ordering(tmp_path, capsys):
    for name in ("src_z", "src_y", "src_x", "src_w"):
        p = tmp_path / f"{name}.txt"
        p.write_text("dimwishlist:item=1&perks=10\n", encoding="utf-8")

    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
wishlist_cache_dir = "{tmp_path.as_posix()}"

[wishlists]
max_age_days = 7

[wishlists.sources.src_z]
url = "https://example.test/z"
family = "zebra"

[wishlists.sources.src_y]
url = "https://example.test/y"
family = "alpha"

[wishlists.sources.src_x]
url = "https://example.test/x"
family = "zebra"

[wishlists.sources.src_w]
url = "https://example.test/w"
family = "alpha"
"""
    )
    rc = _cmd_wishlists(argparse.Namespace(config=str(cfg_file), refresh=False))
    assert rc == 0
    captured = capsys.readouterr()
    assert "families: alpha = src_w + src_y; zebra = src_x + src_z\n" in captured.out


def test_wishlists_cli_ignored_suffix_only_when_nonzero(tmp_path, capsys):
    p = tmp_path / "clean_src.txt"
    p.write_text("//notes:Clean note\ndimwishlist:item=1&perks=10\n", encoding="utf-8")
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
wishlist_cache_dir = "{tmp_path.as_posix()}"

[wishlists]
max_age_days = 7

[wishlists.sources]
clean_src = "https://example.test/clean"
"""
    )
    rc = _cmd_wishlists(argparse.Namespace(config=str(cfg_file), refresh=False))
    assert rc == 0
    captured = capsys.readouterr()
    assert "had ignored note segments" not in captured.out


def test_wishlists_cli_error_exit_code_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: (_ for _ in ()).throw(OSError("network down")))
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        f"""
[paths]
wishlist_cache_dir = "{tmp_path.as_posix()}"

[wishlists]
max_age_days = 7

[wishlists.sources]
missing = "https://example.test/missing"
"""
    )
    rc = _cmd_wishlists(argparse.Namespace(config=str(cfg_file), refresh=False))
    assert rc == 1
    captured = capsys.readouterr()
    assert "error: missing: download failed and no usable cached copy exists" in captured.err
