import json
from pathlib import Path

import pytest

from vault_cleaner import report_run
from vault_cleaner.pipeline import (
    ManifestIdentity,
    WeaponPipelineResult,
    WishlistSourceIdentity,
)
from vault_cleaner.report_run import (
    NoExportsError,
    compute_fingerprint,
    run_report,
    snapshot_dict,
    snapshot_json,
)

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = FIXTURES / "weapons_dupes.csv"
ARMOR = FIXTURES / "armor.csv"
GHOSTS = FIXTURES / "ghosts_cleanup.csv"


def build_report():
    return run_report(
        config_path="nonexistent.toml",
        weapons_path=WEAPONS,
        armor_path=ARMOR,
        ghosts_path=GHOSTS,
        no_wishlists=True,
    )


def test_report_run_contains_sections_sources_decisions_and_config():
    result = build_report()
    assert [section.kind for section in result.sections] == [
        "weapons",
        "armor",
        "ghosts",
    ]
    assert result.effective_config["armor"]["score_floor"] == 65
    assert result.keep_trash_conflicts == 0
    assert not result.wishlists_used

    for section in result.sections:
        assert section.source.item_count > 0
        assert len(section.source.sha256) == 64
        assert all(isinstance(decision.id, str) for decision in section.decisions)
        assert all(isinstance(decision.hash, str) for decision in section.decisions)
        assert all(decision.reason != "unknown" for decision in section.decisions)

    locked = next(
        decision
        for section in result.sections
        for decision in section.decisions
        if decision.protection_reason == "locked"
    )
    assert locked.protection_level == "soft"
    assert locked.original_tag == ""
    assert locked.original_notes == ""


def test_snapshot_contains_complete_armor_score_metadata():
    result = build_report()
    armor = next(section for section in result.sections if section.kind == "armor")
    assert armor.armor is not None
    assert len(armor.armor.evaluations) == armor.armor.scored
    evaluation = armor.armor.evaluations[0]
    assert set(evaluation.stats) == {
        "weapons",
        "health",
        "class",
        "grenade",
        "super",
        "melee",
    }
    assert evaluation.rank >= 1
    assert evaluation.group_size >= evaluation.rank

    document = snapshot_dict(result)
    armor_doc = next(section for section in document["sections"] if section["kind"] == "armor")
    assert len(armor_doc["armor"]["evaluations"]) == armor_doc["armor"]["scored"]
    assert "cited_by_close_pass" in armor_doc["armor"]["evaluations"][0]
    assert "combo_kept_elsewhere" in armor_doc["armor"]["evaluations"][0]


def test_snapshot_serialization_is_deterministic():
    first = build_report()
    second = build_report()
    assert snapshot_json(first) == snapshot_json(second)
    document = json.loads(snapshot_json(first))
    assert document["schema_version"] == 1
    assert document["fingerprint"] == first.fingerprint


def test_large_instance_ids_remain_exact_json_strings(tmp_path):
    large_ids = tmp_path / "large-ids.csv"
    large_ids.write_text(WEAPONS.read_text().replace("3002", "1000000000000000002"))
    result = run_report(
        config_path="nonexistent.toml",
        weapons_path=large_ids,
        armor_path=tmp_path / "missing-armor.csv",
        ghosts_path=tmp_path / "missing-ghosts.csv",
        no_wishlists=True,
    )
    document = json.loads(snapshot_json(result))
    decision = next(
        item for item in document["sections"][0]["decisions"]
        if item["id"] == "1000000000000000002"
    )
    assert decision["id"] == "1000000000000000002"
    assert isinstance(decision["id"], str)
    assert isinstance(decision["hash"], str)


def test_fingerprint_changes_for_every_input_category():
    sources = {"weapons": "export-a"}
    config = {"armor": {"score_floor": 65}}
    wishlist = (
        WishlistSourceIdentity("test", "https://example.test/list", "wishlist-a"),
    )
    manifest = ManifestIdentity("v1", "manifest-a")
    baseline = compute_fingerprint(sources, config, wishlist, manifest)

    assert compute_fingerprint(
        {"weapons": "export-b"}, config, wishlist, manifest
    ) != baseline
    assert compute_fingerprint(
        sources, {"armor": {"score_floor": 66}}, wishlist, manifest
    ) != baseline
    assert compute_fingerprint(
        sources,
        config,
        (WishlistSourceIdentity("test", "https://example.test/list", "wishlist-b"),),
        manifest,
    ) != baseline
    assert compute_fingerprint(
        sources, config, wishlist, ManifestIdentity("v2", "manifest-a")
    ) != baseline
    assert compute_fingerprint(
        sources, config, wishlist, ManifestIdentity("v1", "manifest-b")
    ) != baseline


def test_external_identities_flow_into_snapshot(monkeypatch, tmp_path):
    wishlist = (
        WishlistSourceIdentity("test", "https://example.test/list", "wishlist"),
    )
    manifest = ManifestIdentity("v-test", "manifest")

    def fake_resolve(weapons, cfg, no_wishlists):
        return WeaponPipelineResult(
            decisions=[],
            keep_trash_conflicts=2,
            wishlists_used=True,
            wishlist_sources=wishlist,
            manifest=manifest,
        )

    monkeypatch.setattr(report_run, "resolve_weapons", fake_resolve)
    result = run_report(
        config_path="nonexistent.toml",
        weapons_path=WEAPONS,
        armor_path=tmp_path / "missing-armor.csv",
        ghosts_path=tmp_path / "missing-ghosts.csv",
    )
    document = snapshot_dict(result)
    assert result.keep_trash_conflicts == 2
    assert document["inputs"]["wishlist_sources"][0]["sha256"] == "wishlist"
    assert document["inputs"]["manifest"]["version"] == "v-test"


def test_library_errors_when_every_export_is_missing(tmp_path):
    with pytest.raises(NoExportsError, match="nothing to report on"):
        run_report(
            config_path="nonexistent.toml",
            weapons_path=tmp_path / "weapons.csv",
            armor_path=tmp_path / "armor.csv",
            ghosts_path=tmp_path / "ghosts.csv",
            no_wishlists=True,
        )
