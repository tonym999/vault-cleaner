import json
from pathlib import Path

import pytest

from vault_cleaner import report_run
from vault_cleaner.config import DEFAULTS, ConfigError
from vault_cleaner.pipeline import (
    ManifestIdentity,
    WeaponPipelineResult,
    WishlistSourceIdentity,
)
from vault_cleaner.report_run import (
    NoExportsError,
    SourceReadError,
    compute_fingerprint,
    run_report,
    snapshot_dict,
    snapshot_json,
)

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = FIXTURES / "weapons_dupes.csv"
ARMOR = FIXTURES / "armor.csv"
GHOSTS = FIXTURES / "ghosts_cleanup.csv"
GOLDEN = FIXTURES / "report_snapshot_v1.json"


def build_report():
    return run_report(
        config_path="nonexistent.toml",
        weapons_path=WEAPONS,
        armor_path=ARMOR,
        ghosts_path=GHOSTS,
        no_wishlists=True,
    )


def _leaf_paths(value, prefix=()):
    if not isinstance(value, dict):
        return {prefix}
    if not value:
        return {prefix}
    paths = set()
    for key, item in value.items():
        paths.update(_leaf_paths(item, (*prefix, key)))
    return paths


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
    assert result.wishlist_sources == ()
    assert result.manifest is None

    expected_paths = {
        "weapons": str(WEAPONS),
        "armor": str(ARMOR),
        "ghosts": str(GHOSTS),
    }
    for section in result.sections:
        assert section.source.path == expected_paths[section.kind]
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
    assert document["ruleset_version"] == 3
    assert document["fingerprint"] == first.fingerprint


def test_fixture_bytes_are_checked_out_verbatim():
    """Digests, fingerprints, and the golden are sha256 over exact fixture bytes.

    On a checkout where `core.autocrlf` translated line endings (before the
    `.gitattributes` pin, #45), every digest comparison failed with an opaque
    hash mismatch. Fail here with the actual cause instead.
    """
    for path in sorted(FIXTURES.iterdir()):
        assert b"\r" not in path.read_bytes(), (
            f"{path.name} contains CR bytes — the checkout translated line "
            "endings. Re-materialise the pinned bytes with: "
            "git checkout HEAD -- tests/fixtures"
        )


def test_regeneration_script_reproduces_the_committed_golden(tmp_path):
    """The regen helper and the committed golden must agree byte-for-byte.

    The script deliberately duplicates build_report's recipe instead of
    importing this module; this comparison is what stops the two drifting.
    Running on both CI platforms makes the golden's byte-stability a checked
    invariant rather than a claim (#45, #53).
    """
    import importlib.util

    script = Path(__file__).parent.parent / "scripts" / "regenerate_report_snapshot.py"
    spec = importlib.util.spec_from_file_location("regenerate_report_snapshot", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    regenerated = module.write_golden(tmp_path / "regenerated.json")
    assert regenerated.read_bytes() == GOLDEN.read_bytes()


def test_snapshot_matches_schema_v1_golden():
    assert snapshot_dict(build_report()) == json.loads(GOLDEN.read_text())


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
    assert document["inputs"]["sources"][0]["path"] == "large-ids.csv"
    assert result.sections[0].source.path == str(large_ids)
    assert [warning.path for warning in result.warnings] == [
        str(tmp_path / "missing-armor.csv"),
        str(tmp_path / "missing-ghosts.csv"),
    ]
    assert result.warnings[0].render() == (
        f"skipping armor: {tmp_path / 'missing-armor.csv'} not found"
    )
    assert document["warnings"] == [
        {"kind": "armor", "path": "missing-armor.csv", "reason": "not found"},
        {"kind": "ghosts", "path": "missing-ghosts.csv", "reason": "not found"},
    ]
    assert str(tmp_path) not in snapshot_json(result)


def test_unknown_config_is_normalized_internally_but_omitted_from_snapshot(tmp_path):
    config = tmp_path / "dated.toml"
    config.write_text(
        "[metadata]\n"
        "last_refreshed = 2026-07-01\n"
        "[paths]\n"
        'input_dir = "/home/example/private/in"\n'
    )
    result = run_report(
        config_path=config,
        weapons_path=WEAPONS,
        armor_path=tmp_path / "missing-armor.csv",
        ghosts_path=tmp_path / "missing-ghosts.csv",
        no_wishlists=True,
    )

    document = json.loads(snapshot_json(result))
    assert result.effective_config["paths"]["input_dir"] == "/home/example/private/in"
    assert result.effective_config["metadata"] == {
        "last_refreshed": "2026-07-01"
    }
    assert len(result.fingerprint) == 64
    assert set(document["inputs"]["effective_config"]) == {"armor", "rails"}
    assert "/home/example" not in snapshot_json(result)


def test_non_finite_unknown_config_has_a_clean_error(tmp_path):
    config = tmp_path / "non-finite.toml"
    config.write_text("[metadata]\nvalue = nan\n")
    with pytest.raises(ConfigError, match="not snapshot-safe"):
        run_report(
            config_path=config,
            weapons_path=WEAPONS,
            armor_path=tmp_path / "missing-armor.csv",
            ghosts_path=tmp_path / "missing-ghosts.csv",
            no_wishlists=True,
        )


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
    assert compute_fingerprint(
        sources,
        config,
        wishlist,
        manifest,
        ruleset_version=1,
    ) != baseline


def test_fingerprint_ignores_paths_covered_by_content_identities():
    sources = {"weapons": "export"}
    first = {"armor": {"score_floor": 65}, "paths": {"input_dir": "one"}}
    second = {"armor": {"score_floor": 65}, "paths": {"input_dir": "two"}}
    assert compute_fingerprint(sources, first) == compute_fingerprint(sources, second)


def test_decision_config_allowlist_covers_non_external_defaults():
    excluded = {"paths", "wishlists", "manifest"}
    expected = {
        section: values
        for section, values in DEFAULTS.items()
        if section not in excluded
    }
    projected = report_run._decision_config(DEFAULTS)
    assert set(projected) == set(DEFAULTS) - excluded
    assert _leaf_paths(projected) == _leaf_paths(expected)


def test_snapshot_fingerprint_is_recomputable_from_recorded_inputs(tmp_path):
    config = tmp_path / "private.toml"
    private_input = tmp_path / "pri'vate" / "input"
    private_note = tmp_path / "pri'vate" / "vault"
    config.write_text(
        "[paths]\n"
        f"input_dir = {json.dumps(str(private_input))}\n"
        "[notes]\n"
        f"my_vault = {json.dumps(str(private_note))}\n"
        "[rails]\n"
        f"private_path = {json.dumps(str(private_note))}\n"
        "[armor]\n"
        f"private_path = {json.dumps(str(private_note))}\n"
        "[armor.close_dupes]\n"
        "max_stat_delta = 5\n"
        "max_total_delta = 12\n"
        f"private_path = {json.dumps(str(private_note))}\n"
        "[armor.archetypes.private]\n"
        "top_stats = 2\n"
        f"private_path = {json.dumps(str(private_note))}\n"
    )
    result = run_report(
        config_path=config,
        weapons_path=WEAPONS,
        armor_path=ARMOR,
        ghosts_path=GHOSTS,
        no_wishlists=True,
    )
    document = snapshot_dict(result)
    inputs = document["inputs"]
    assert result.effective_config["paths"]["input_dir"] == str(private_input)
    assert result.effective_config["notes"]["my_vault"] == str(private_note)
    assert result.effective_config["rails"]["private_path"] == str(private_note)
    assert result.effective_config["armor"]["private_path"] == str(private_note)
    assert set(inputs["effective_config"]) == {"armor", "rails"}
    assert "private_path" not in inputs["effective_config"]["rails"]
    assert "private_path" not in inputs["effective_config"]["armor"]
    assert "private_path" not in inputs["effective_config"]["armor"]["close_dupes"]
    assert "private_path" not in (
        inputs["effective_config"]["armor"]["archetypes"]["private"]
    )
    assert str(tmp_path) not in snapshot_json(result)
    source_digests = {
        source["kind"]: source["sha256"] for source in inputs["sources"]
    }
    wishlist_sources = tuple(
        WishlistSourceIdentity(**source) for source in inputs["wishlist_sources"]
    )
    manifest = (
        ManifestIdentity(**inputs["manifest"])
        if inputs["manifest"] is not None
        else None
    )
    assert compute_fingerprint(
        source_digests,
        inputs["effective_config"],
        wishlist_sources,
        manifest,
        ruleset_version=document["ruleset_version"],
    ) == document["fingerprint"]


def test_snapshot_schema_version_does_not_change_input_fingerprint(monkeypatch):
    before = build_report()
    monkeypatch.setattr(report_run, "SNAPSHOT_SCHEMA_VERSION", 2)
    after = build_report()
    assert snapshot_dict(after)["schema_version"] == 2
    assert after.fingerprint == before.fingerprint


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


def test_export_hash_failure_has_a_domain_error(monkeypatch, tmp_path):
    def fail_hash(path):
        raise OSError("file disappeared")

    monkeypatch.setattr(report_run, "sha256_file", fail_hash)
    with pytest.raises(SourceReadError, match="could not fingerprint weapons export"):
        run_report(
            config_path="nonexistent.toml",
            weapons_path=WEAPONS,
            armor_path=tmp_path / "missing-armor.csv",
            ghosts_path=tmp_path / "missing-ghosts.csv",
            no_wishlists=True,
        )


def test_export_change_during_load_has_a_domain_error(monkeypatch, tmp_path):
    digests = iter(["before", "after"])
    monkeypatch.setattr(report_run, "sha256_file", lambda path: next(digests))

    with pytest.raises(SourceReadError, match="changed while being read"):
        run_report(
            config_path="nonexistent.toml",
            weapons_path=WEAPONS,
            armor_path=tmp_path / "missing-armor.csv",
            ghosts_path=tmp_path / "missing-ghosts.csv",
            no_wishlists=True,
        )
