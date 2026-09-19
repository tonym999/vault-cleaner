import os
import re
import time
from pathlib import Path

import pytest

from vault_cleaner import wishlist as wl_mod
from vault_cleaner.config import ConfigError, load_config
from vault_cleaner.wishlist import (
    WishlistConfigError,
    WishlistError,
    WishlistSourceSpec,
    fetch,
    fetch_with_status,
    load_all_with_evidence,
    load_all_with_sources,
    parse_wishlist,
    source_specs,
)

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


def test_explicit_empty_perks_param_is_whole_item_trash(parsed):
    # `&perks=` with no value is the Aegis trash list's whole-item convention
    assert parsed.trash[555] == [frozenset()]


def test_wildcard_entries_counted_not_stored(parsed):
    assert parsed.wildcards == 1
    assert 69420 not in parsed.keep and 69420 not in parsed.trash


def test_malformed_wishlist_line_counted(parsed):
    assert parsed.skipped == 1  # item=oops


def test_non_wishlist_lines_ignored_silently(parsed):
    # titles, comments, prose, @description junk — no effect on any counter
    assert parsed.entries == 6  # 3 keep rolls + 3 trash entries


def test_benign_comma_noise_tolerated():
    wl = parse_wishlist("dimwishlist:item=1&perks=10,20,\ndimwishlist:item=2&perks=30,,40")
    assert wl.keep[1] == [frozenset({10, 20})]
    assert wl.keep[2] == [frozenset({30, 40})]
    assert wl.skipped == 0


def test_empty_perks_param_is_malformed_not_any_roll():
    # perks= present but no perks: must not become an empty set (which would
    # mean "any roll" on keep or "whole item" on trash)
    wl = parse_wishlist("dimwishlist:item=1&perks=,\ndimwishlist:item=-2&perks=,")
    assert wl.keep == {} and wl.trash == {}
    assert wl.skipped == 2


def test_oversized_numbers_skipped_never_crash():
    # Python's int() raises on huge digit strings; these must land in skipped
    big = "9" * 5000
    assert parse_wishlist(f"dimwishlist:item=1&perks={big}").skipped == 1
    assert parse_wishlist(f"dimwishlist:item={big}&perks=1").skipped == 1
    # 11 digits — longer than any uint32 hash
    assert parse_wishlist("dimwishlist:item=1&perks=12345678901").skipped == 1


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


def test_fetch_stat_failure_redownloads(tmp_path, monkeypatch):
    p = tmp_path / "test.txt"
    p.write_text("old")
    real_stat = Path.stat

    def stat(path, *args, **kwargs):
        if path == p:
            raise OSError("cache metadata unavailable")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: "new")

    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=7).read_text() == "new"


def test_fetch_stat_failure_without_download_keeps_clean_error(tmp_path, monkeypatch):
    real_stat = Path.stat

    def stat(path, *args, **kwargs):
        if path == tmp_path / "test.txt":
            raise OSError("cache metadata unavailable")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    monkeypatch.setattr(wl_mod, "_download", _boom)

    with pytest.raises(WishlistError, match="no usable cached copy"):
        fetch("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=7)


def test_fetch_stat_failure_and_download_failure_uses_readable_cache(
    tmp_path,
    monkeypatch,
    capsys,
):
    p = tmp_path / "test.txt"
    p.write_text("stale")
    real_stat = Path.stat

    def stat(path, *args, **kwargs):
        if path == p:
            raise OSError("cache metadata unavailable")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", stat)
    monkeypatch.setattr(wl_mod, "_download", _boom)

    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=7).read_text() == "stale"
    assert "stale cache" in capsys.readouterr().err


def test_fetch_unreadable_cache_raises_clean_error(tmp_path, monkeypatch):
    p = tmp_path / "test.txt"
    p.write_text("stale")
    real_open = Path.open

    def open(path, *args, **kwargs):
        if path == p:
            raise OSError("cache unreadable")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open)
    monkeypatch.setattr(wl_mod, "_download", _boom)

    with pytest.raises(WishlistError, match="no usable cached copy"):
        fetch("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=0)


def test_fetch_refresh_forces_download(tmp_path, monkeypatch):
    (tmp_path / "test.txt").write_text("old")
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: "new")
    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path, refresh=True).read_text() == "new"


def test_download_rejects_non_http_scheme(monkeypatch):
    monkeypatch.setattr(
        wl_mod.urllib.request,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("urlopen should not be called"),
    )
    with pytest.raises(ValueError, match="unsupported wishlist URL scheme"):
        wl_mod._download("file:///etc/passwd")


def test_load_all_returns_the_exact_bytes_it_parsed(tmp_path):
    cfg = load_config("nonexistent.toml")
    cfg["paths"]["wishlist_cache_dir"] = str(tmp_path)
    cfg["wishlists"]["sources"] = {"test": "https://example.test/list"}
    raw = b"dimwishlist:item=123&perks=10,20\n"
    (tmp_path / "test.txt").write_bytes(raw)

    merged, sources = load_all_with_sources(cfg)

    assert merged.keep[123] == [frozenset({10, 20})]
    assert sources[0].content == raw


def _boom(url, timeout=30):
    raise OSError("network down")


def test_fetch_failure_falls_back_to_stale_cache(tmp_path, monkeypatch, capsys):
    p = tmp_path / "test.txt"
    p.write_text("stale")
    os.utime(p, (0, 0))
    monkeypatch.setattr(wl_mod, "_download", _boom)
    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path).read_text() == "stale"
    assert "stale cache" in capsys.readouterr().err


def test_fetch_zero_age_falls_back_to_future_dated_cache(tmp_path, monkeypatch, capsys):
    p = tmp_path / "test.txt"
    p.write_text("stale")
    future = time.time() + 60
    os.utime(p, (future, future))
    monkeypatch.setattr(wl_mod, "_download", _boom)
    assert fetch("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=0).read_text() == "stale"
    assert "stale cache" in capsys.readouterr().err


def test_fetch_failure_without_cache_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_mod, "_download", _boom)
    with pytest.raises(WishlistError, match="no usable cached copy"):
        fetch("test", "https://x/w.txt", cache_dir=tmp_path)


def _boom_url(url, timeout=30):
    raise ValueError("unknown url type: 'htp'")


def test_malformed_url_uses_stale_cache_or_clean_error(tmp_path, monkeypatch):
    monkeypatch.setattr(wl_mod, "_download", _boom_url)
    with pytest.raises(WishlistError, match="no usable cached copy"):
        fetch("test", "htp://typo/w.txt", cache_dir=tmp_path)
    p = tmp_path / "test.txt"
    p.write_text("stale")
    os.utime(p, (0, 0))
    assert fetch("test", "htp://typo/w.txt", cache_dir=tmp_path).read_text() == "stale"


def test_source_specs_string_and_table_normalization():
    sources = {
        "choosy_voltron": "https://example.test/voltron.txt",
        "aegis_keep": {
            "url": "https://example.test/aegis_keep.txt",
            "family": "aegis-endgame",
            "activity": "pve",
            "tier_format": "ciceron-aegis",
        },
        "minimal_table": {
            "url": "https://example.test/min.txt",
            "family": "custom-fam",
        },
    }
    specs = source_specs(sources)
    assert len(specs) == 3
    assert specs[0] == WishlistSourceSpec(
        name="choosy_voltron",
        url="https://example.test/voltron.txt",
        family="choosy_voltron",
        activity="any",
        tier_format="none",
    )
    assert specs[1] == WishlistSourceSpec(
        name="aegis_keep",
        url="https://example.test/aegis_keep.txt",
        family="aegis-endgame",
        activity="pve",
        tier_format="ciceron-aegis",
    )
    assert specs[2] == WishlistSourceSpec(
        name="minimal_table",
        url="https://example.test/min.txt",
        family="custom-fam",
        activity="any",
        tier_format="none",
    )


@pytest.mark.parametrize(
    "invalid_sources,match",
    [
        ("not-a-dict", "must be a table"),
        ({"s": 123}, "expected a string URL or table"),
        ({"s": []}, "expected a string URL or table"),
        ({"s": ""}, "s: url cannot be empty"),
        ({"s": {"url": "http://x", "family": "f", "extra": 1}}, "unknown key\\(s\\): extra"),
        ({"s": {"family": "f"}}, "missing required key 'url'"),
        ({"s": {"url": "", "family": "f"}}, "s: url cannot be empty"),
        ({"s": {"url": 123, "family": "f"}}, "s.url must be a string"),
        ({"s": {"url": True, "family": "f"}}, "s.url must be a string"),
        ({"s": {"url": "http://x"}}, "missing required key 'family'"),
        ({"s": {"url": "http://x", "family": 123}}, "s.family must be a string"),
        ({"s": {"url": "http://x", "family": True}}, "s.family must be a string"),
        ({"s": {"url": "http://x", "family": "bad_family"}}, "invalid family 'bad_family'"),
        ({"s": {"url": "http://x", "family": "-bad"}}, "invalid family '-bad'"),
        ({"s": {"url": "http://x", "family": "bad-"}}, "invalid family 'bad-'"),
        ({"s": {"url": "http://x", "family": "f", "activity": "pvx"}}, "invalid activity 'pvx'"),
        ({"s": {"url": "http://x", "family": "f", "activity": 1}}, "s.activity must be a string"),
        ({"s": {"url": "http://x", "family": "f", "tier_format": "unknown"}}, "invalid tier_format 'unknown'"),
        ({"s": {"url": "http://x", "family": "f", "tier_format": 2}}, "s.tier_format must be a string"),
    ],
)
def test_source_specs_rejections(invalid_sources, match):
    with pytest.raises(WishlistConfigError, match=match):
        source_specs(invalid_sources)


def test_load_config_validates_wishlists_sources(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        """
[wishlists.sources.bad]
url = "https://example.test"
family = "bad_fam"
"""
    )
    with pytest.raises(ConfigError, match=r"\[wishlists\.sources\] bad: invalid family 'bad_fam'"):
        load_config(cfg_file)


def test_committed_config_sources_valid():
    cfg = load_config("config.toml")
    specs = source_specs(cfg["wishlists"]["sources"])
    assert len(specs) == 3
    names = [s.name for s in specs]
    assert names == ["choosy_voltron", "aegis_keep", "aegis_trash"]
    assert specs[1].family == "aegis-endgame"
    assert specs[1].tier_format == "ciceron-aegis"
    assert specs[2].family == "aegis-endgame"
    assert specs[2].tier_format == "ciceron-aegis"


def test_evidence_scoping_on_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "wishlist_evidence.txt"
    spec = WishlistSourceSpec(
        name="test_src",
        url="https://example.test",
        family="test-family",
        activity="any",
        tier_format="ciceron-aegis",
    )
    wl = parse_wishlist(fixture_path.read_text(encoding="utf-8"), "test_src", spec=spec, evidence=True)

    assert wl.declared_title == "First List Title"
    assert wl.declared_description == "A synthetic test description for wishlist evidence"
    assert wl.section_titles == 3  # title: First, title: Second, title: Intervening
    assert wl.wildcards == 1
    assert wl.skipped == 1

    # 1001 & 1002: block note with tags
    e1001 = wl.keep_evidence[1001][0]
    assert e1001.notes == "Great weapon roll"
    assert e1001.tags == ("pve", "controller")
    assert e1001.section_title == "Second Section Title"
    assert e1001.activities == frozenset({"pve"})
    assert e1001.activity_basis == "tags"
    assert e1001.tier_status == "unrecognized"
    assert e1001.tier is None

    e1002 = wl.keep_evidence[1002][0]
    assert e1002.notes == "Great weapon roll"
    assert e1002.tags == ("pve", "controller")

    # 1003: blank-line reset
    e1003 = wl.keep_evidence[1003][0]
    assert e1003.notes is None
    assert e1003.tags == ()
    assert e1003.activities == frozenset()
    assert e1003.activity_basis == "unknown"

    # 1004: // comment reset
    e1004 = wl.keep_evidence[1004][0]
    assert e1004.notes is None
    assert e1004.tags == ()

    # 1005: tail note overrides block note
    e1005 = wl.keep_evidence[1005][0]
    assert e1005.notes == "Tail note text"
    assert e1005.tags == ()

    # 1006: #notes:x tail (1 char before pipe) falls back to block note
    e1006 = wl.keep_evidence[1006][0]
    assert e1006.notes == "Block note for short tail"
    assert e1006.tags == ()

    # 1007: #notes:x|tags:pve (1 char before pipe) falls back to block note with |tags:controller
    e1007 = wl.keep_evidence[1007][0]
    assert e1007.notes == "Block note with controller tag"
    assert e1007.tags == ("controller",)

    # 1008: #notes:xy|tags:pvp (2 chars before pipe) overrides block note
    e1008 = wl.keep_evidence[1008][0]
    assert e1008.notes == "xy"
    assert e1008.tags == ("pvp",)
    assert e1008.activities == frozenset({"pvp"})
    assert e1008.activity_basis == "tags"

    # 1009: | tags: pvp god-pvp with space
    e1009 = wl.keep_evidence[1009][0]
    assert e1009.tags == ("pvp", "god-pvp")
    assert e1009.activities == frozenset({"pvp"})

    # 1010: (Foo version) - Aegis Endgame S Tier.
    e1010 = wl.keep_evidence[1010][0]
    assert e1010.tier == "S"
    assert e1010.tier_status == "parsed"

    # 1011: Aegis Endgame A Tier.
    e1011 = wl.keep_evidence[1011][0]
    assert e1011.tier == "A"
    assert e1011.tier_status == "parsed"

    # 1012: D Tier. (trash)
    e1012 = wl.trash_evidence[1012][0]
    assert e1012.tier == "D"
    assert e1012.tier_status == "parsed"
    assert e1012.polarity == "trash"

    # 1013: F Tier. Weak Combo: slow reload
    e1013 = wl.trash_evidence[1013][0]
    assert e1013.tier == "F"
    assert e1013.tier_status == "parsed"

    # 1014: Arbitrary note without tier prefix
    e1014 = wl.keep_evidence[1014][0]
    assert e1014.notes == "Just some arbitrary note without tier prefix"
    assert e1014.tier is None
    assert e1014.tier_status == "unrecognized"

    # 1015: Sticky block note across whitespace line and title line
    e1015 = wl.keep_evidence[1015][0]
    assert e1015.notes == "Sticky block note across title"
    assert e1015.section_title == "Intervening Title"

    # 1016: |tags:PvE|tags:111 222 -> second segment ignored
    e1016 = wl.keep_evidence[1016][0]
    assert e1016.tags == ("pve",)
    assert "111" not in e1016.tags

    # 1017: |unknown:value -> non-tags segment ignored
    e1017 = wl.keep_evidence[1017][0]
    assert e1017.tags == ()

    # Both 1016 and 1017 had ignored note segments
    assert wl.ignored_note_segments == 2

    # 1018: whitespace-only line resets block note
    e1018 = wl.keep_evidence[1018][0]
    assert e1018.notes is None
    assert e1018.tags == ()


def test_tag_case_rejection():
    spec = WishlistSourceSpec(
        name="test", url="http://x", family="fam", activity="any", tier_format="none"
    )
    text = "//notes:blk|TAGS:pvp\ndimwishlist:item=100&perks=1,2"
    wl = parse_wishlist(text, "test", spec=spec, evidence=True)
    entry = wl.keep_evidence[100][0]
    assert entry.tags == ()
    assert wl.ignored_note_segments == 1


@pytest.mark.parametrize(
    "note,polarity,expected_tier,expected_status",
    [
        ("Aegis Endgame S Tier.", "keep", "S", "parsed"),
        ("Aegis Endgame A Tier.", "keep", "A", "parsed"),
        ("(Pantheon version) - Aegis Endgame S Tier.", "keep", "S", "parsed"),
        ("(BRAVE version) - Aegis Endgame A Tier. Good combo", "keep", "A", "parsed"),
        ("Aegis Endgame B Tier.", "keep", None, "unrecognized"),
        ("D Tier.", "trash", "D", "parsed"),
        ("E Tier. Alternative", "trash", "E", "parsed"),
        ("F Tier.", "trash", "F", "parsed"),
        ("F Tier. Weak Combo: slow reload", "trash", "F", "parsed"),
        ("A Tier.", "trash", None, "unrecognized"),
        ("D Tier.", "keep", None, "unrecognized"),
        ("Some random text", "keep", None, "unrecognized"),
        (None, "keep", None, "unrecognized"),
    ],
)
def test_tier_recognizer_truth_table_ciceron(note, polarity, expected_tier, expected_status):
    item_id = -100 if polarity == "trash" else 100
    line = f"dimwishlist:item={item_id}&perks=1,2"
    if note is not None:
        text = f"//notes:{note}\n{line}"
    else:
        text = line
    spec = WishlistSourceSpec(
        name="test", url="http://x", family="fam", activity="any", tier_format="ciceron-aegis"
    )
    wl = parse_wishlist(text, "test", spec=spec, evidence=True)
    bucket = wl.trash_evidence if polarity == "trash" else wl.keep_evidence
    assert bucket is not None
    entry = bucket[100][0]
    assert entry.tier == expected_tier
    assert entry.tier_status == expected_status


def test_tier_recognizer_truth_table_none():
    notes = [
        "Aegis Endgame S Tier.",
        "D Tier.",
        "A tier with the word tier in it",
    ]
    spec = WishlistSourceSpec(
        name="test", url="http://x", family="fam", activity="any", tier_format="none"
    )
    for n in notes:
        text = f"//notes:{n}\ndimwishlist:item=100&perks=1,2"
        wl = parse_wishlist(text, "test", spec=spec, evidence=True)
        entry = wl.keep_evidence[100][0]
        assert entry.tier is None
        assert entry.tier_status == "not-declared"


def test_parse_invariance_across_fixtures():
    fixtures_dir = Path(__file__).parent / "fixtures"
    specs = [
        WishlistSourceSpec(name="t1", url="http://x", family="f1", activity="any", tier_format="none"),
        WishlistSourceSpec(name="t2", url="http://x", family="f2", activity="pve", tier_format="ciceron-aegis"),
    ]
    for p in fixtures_dir.glob("*.txt"):
        text = p.read_text(encoding="utf-8")
        wl_off = parse_wishlist(text, "off", evidence=False)
        assert wl_off.ignored_note_segments == 0
        for spec in specs:
            wl_on = parse_wishlist(text, spec.name, spec=spec, evidence=True)
            assert wl_on.keep == wl_off.keep
            assert wl_on.trash == wl_off.trash
            assert wl_on.skipped == wl_off.skipped
            assert wl_on.wildcards == wl_off.wildcards


def test_line_re_match_skip_outcome_unchanged():
    old_re = re.compile(r"^dimwishlist:item=(-?\d{1,10})(?:&perks=([\d,]*))?(?:#.*)?$")
    from vault_cleaner.wishlist import LINE_RE as new_re

    fixtures_dir = Path(__file__).parent / "fixtures"
    for p in fixtures_dir.glob("*.txt"):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("dimwishlist:"):
                continue
            assert bool(old_re.match(line)) == bool(new_re.match(line))


def test_alignment_invariant_and_merge():
    text = """
title: Test
//notes:First
dimwishlist:item=10&perks=1,2
dimwishlist:item=10&perks=3,4
dimwishlist:item=-20&perks=5,6
dimwishlist:item=-20&perks=
dimwishlist:item=69420&perks=1
dimwishlist:item=malformed
dimwishlist:item=30&perks=,
"""
    spec = WishlistSourceSpec(name="a", url="http://a", family="fam-a", activity="pve", tier_format="none")
    wl = parse_wishlist(text, "a", spec=spec, evidence=True)

    assert wl.keep_evidence.keys() == wl.keep.keys()
    assert wl.trash_evidence.keys() == wl.trash.keys()
    for d in (wl.keep, wl.keep_evidence, wl.trash, wl.trash_evidence):
        assert 30 not in d
        assert 69420 not in d

    for h, rolls in wl.keep.items():
        evs = wl.keep_evidence[h]
        assert len(rolls) == len(evs)
        for i in range(len(rolls)):
            assert evs[i].perks is rolls[i]

    for h, rolls in wl.trash.items():
        evs = wl.trash_evidence[h]
        assert len(rolls) == len(evs)
        for i in range(len(rolls)):
            assert evs[i].perks is rolls[i]

    # Merge with another evidence-bearing wishlist
    text_b = """
//notes:Second
dimwishlist:item=10&perks=7,8
dimwishlist:item=-20&perks=9,10
"""
    spec_b = WishlistSourceSpec(name="b", url="http://b", family="fam-b", activity="pvp", tier_format="none")
    wl_b = parse_wishlist(text_b, "b", spec=spec_b, evidence=True)

    wl.merge(wl_b)
    # Family of merged wishlist is unchanged
    assert wl.family == "fam-a"

    assert wl.keep_evidence.keys() == wl.keep.keys()
    assert wl.trash_evidence.keys() == wl.trash.keys()
    for d in (wl.keep, wl.keep_evidence, wl.trash, wl.trash_evidence):
        assert 30 not in d
        assert 69420 not in d

    for h, rolls in wl.keep.items():
        evs = wl.keep_evidence[h]
        assert len(rolls) == len(evs)
        for i in range(len(rolls)):
            assert evs[i].perks is rolls[i]

    for h, rolls in wl.trash.items():
        evs = wl.trash_evidence[h]
        assert len(rolls) == len(evs)
        for i in range(len(rolls)):
            assert evs[i].perks is rolls[i]

    # Merging evidence with non-evidence raises ValueError
    wl_no_ev = parse_wishlist(text_b, "c", evidence=False)
    with pytest.raises(ValueError, match="cannot merge evidence-bearing wishlist with evidence-free wishlist"):
        wl.merge(wl_no_ev)
    with pytest.raises(ValueError, match="cannot merge evidence-bearing wishlist with evidence-free wishlist"):
        wl_no_ev.merge(wl)


def test_ignored_note_segments_source_vs_merged(tmp_path):
    text1 = """
//notes:Block 1|tags:pve|ignored:one
dimwishlist:item=1&perks=10
"""
    text2 = """
//notes:Block 2|ignored:first
dimwishlist:item=2&perks=20
//notes:Block 3|tags:pve|ignored:extra
dimwishlist:item=3&perks=30
"""
    (tmp_path / "s1.txt").write_text(text1, encoding="utf-8")
    (tmp_path / "s2.txt").write_text(text2, encoding="utf-8")

    cfg = {
        "paths": {"wishlist_cache_dir": str(tmp_path)},
        "wishlists": {
            "max_age_days": 7,
            "sources": {
                "s1": {"url": "http://s1", "family": "fam-a"},
                "s2": {"url": "http://s2", "family": "fam-b"},
            },
        },
    }

    ev_set = load_all_with_evidence(cfg)
    assert ev_set.statuses[0].ignored_note_segment_entries == 1
    assert ev_set.statuses[1].ignored_note_segment_entries == 2
    assert ev_set.merged.ignored_note_segments == 3


def test_fetch_with_status_covers_all_three_statuses(tmp_path, monkeypatch, capsys):
    p = tmp_path / "test.txt"
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: "downloaded-text")

    # 1. Downloaded
    res = fetch_with_status("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=7)
    assert res.status == "downloaded"
    assert res.cache_written_at is not None
    assert res.error is None
    assert p.read_text() == "downloaded-text"

    # 2. Fresh cache
    res2 = fetch_with_status("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=7)
    assert res2.status == "cache"
    assert res2.cache_written_at == res.cache_written_at
    assert res2.error is None

    # 3. Stale cache after failed download
    os.utime(p, (time.time() - 10 * 86400, time.time() - 10 * 86400))
    monkeypatch.setattr(wl_mod, "_download", _boom)
    res3 = fetch_with_status("test", "https://x/w.txt", cache_dir=tmp_path, max_age_days=7)
    assert res3.status == "stale-cache-after-failed-download"
    assert res3.error == "network down"
    assert "stale cache" in capsys.readouterr().err


def test_fetch_with_status_preserves_crlf_without_doubling(tmp_path, monkeypatch):
    text = "//notes:a\r\ndimwishlist:item=1&perks=2\r\n"
    monkeypatch.setattr(wl_mod, "_download", lambda url, timeout=30: text)
    res = fetch_with_status("crlf_test", "https://example.test/crlf.txt", cache_dir=tmp_path, max_age_days=7)
    assert res.path.read_bytes() == text.encode("utf-8")
    assert b"\r\r\n" not in res.path.read_bytes()


def test_parse_wishlist_doubled_cr_normalization():
    text = "//notes:blk|tags:pve\r\r\ndimwishlist:item=1&perks=2\r\r\n"
    spec = WishlistSourceSpec(name="test", url="http://test", family="fam", activity="any", tier_format="none")
    wl_ev = parse_wishlist(text, "test", spec=spec, evidence=True)
    entry = wl_ev.keep_evidence[1][0]
    assert entry.notes == "blk"
    assert entry.tags == ("pve",)
    assert entry.activity_basis == "tags"

    wl_no_ev = parse_wishlist(text, "test", evidence=False)
    assert wl_ev.keep == wl_no_ev.keep
    assert wl_ev.trash == wl_no_ev.trash
    assert wl_ev.skipped == wl_no_ev.skipped
    assert wl_ev.wildcards == wl_no_ev.wildcards
