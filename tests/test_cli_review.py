import json
from pathlib import Path

from test_review import (
    BIG_ID,
    build_report,
    manifest_payload,
    proposals,
    write_manifest,
)

from vault_cleaner import cli
from vault_cleaner.report import write_import_csv
from vault_cleaner.review import OverrideStore, Veto, load_overrides, save_overrides

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = str(FIXTURES / "weapons_dupes.csv")
ARMOR = str(FIXTURES / "armor.csv")
GHOSTS = str(FIXTURES / "ghosts_cleanup.csv")


def run_review(tmp_path, *extra: str) -> int:
    return cli.main([
        "review", "--weapons", WEAPONS, "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
        "--overrides", str(tmp_path / "overrides.json"),
        "--output", str(tmp_path / "reviewed.csv"), *extra,
    ])


def run_report_cmd(tmp_path, *extra: str) -> int:
    return cli.main([
        "report", "--weapons", WEAPONS, "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
        "--overrides", str(tmp_path / "overrides.json"), *extra,
    ])


def two_vetoed_ids(run):
    return [d.id for d in proposals(run)][:2]


def test_dry_run_reports_counts_and_writes_nothing(tmp_path, capsys):
    run = build_report()
    ids = two_vetoed_ids(run)
    manifest = write_manifest(tmp_path, manifest_payload(run, ids))

    assert run_review(tmp_path, "--manifest", str(manifest)) == 0
    out = capsys.readouterr().out

    total = len(proposals(run))
    assert f"report: {total} decision(s)" in out
    assert "fingerprint matches" in out
    assert "overrides: would add 2, update 0, leave 0 unchanged" in out
    assert f"after vetoes: {total - 2} decision(s)" in out
    assert "would write" in out and "would update" in out
    assert "dry run — nothing written" in out

    assert not (tmp_path / "reviewed.csv").exists()
    assert not (tmp_path / "overrides.json").exists()


def test_write_persists_vetoes_and_writes_the_reviewed_csv(tmp_path, capsys):
    run = build_report()
    ids = two_vetoed_ids(run)
    manifest = write_manifest(tmp_path, manifest_payload(run, ids))

    assert run_review(tmp_path, "--manifest", str(manifest), "--write") == 0
    out = capsys.readouterr().out
    assert "overrides: added 2" in out
    assert f"wrote {len(proposals(run)) - 2} row(s)" in out

    stored = load_overrides(tmp_path / "overrides.json")
    assert sorted(v.id for v in stored.vetoes) == sorted(ids)

    written = (tmp_path / "reviewed.csv").read_text(encoding="utf-8")
    for vetoed in ids:
        assert f'"""{vetoed}"""' not in written


def test_reviewed_csv_is_byte_identical_to_the_python_writer(tmp_path):
    """The reviewed export must be the same writer, not a second one."""
    run = build_report()
    ids = two_vetoed_ids(run)
    manifest = write_manifest(tmp_path, manifest_payload(run, ids))
    assert run_review(tmp_path, "--manifest", str(manifest), "--write") == 0

    expected = tmp_path / "expected.csv"
    write_import_csv(
        [d.import_row() for d in proposals(run) if d.id not in set(ids)], expected
    )
    assert (tmp_path / "reviewed.csv").read_bytes() == expected.read_bytes()


def test_persisted_vetoes_apply_without_a_manifest(tmp_path, capsys):
    run = build_report()
    ids = two_vetoed_ids(run)
    manifest = write_manifest(tmp_path, manifest_payload(run, ids))
    assert run_review(tmp_path, "--manifest", str(manifest), "--write") == 0
    capsys.readouterr()

    assert run_review(tmp_path) == 0
    out = capsys.readouterr().out
    assert "2 active, 0 stale, 0 orphaned, 0 unchecked" in out
    assert f"after vetoes: {len(proposals(run)) - 2} decision(s)" in out
    assert "manifest:" not in out
    assert "would update" not in out  # nothing to persist without a manifest


def test_stale_fingerprint_refuses_and_changes_nothing(tmp_path, capsys):
    run = build_report()
    payload = manifest_payload(run, two_vetoed_ids(run))
    payload["snapshot"]["fingerprint"] = "0" * 64
    manifest = write_manifest(tmp_path, payload)

    assert run_review(tmp_path, "--manifest", str(manifest), "--write") == 1
    err = capsys.readouterr().err
    assert "different report run" in err
    assert "Re-run the report" in err
    assert not (tmp_path / "overrides.json").exists()
    assert not (tmp_path / "reviewed.csv").exists()


def test_changed_export_refuses_rather_than_warning(tmp_path, capsys):
    """The acceptance case: a re-exported vault invalidates the review."""
    run = build_report()
    manifest = write_manifest(tmp_path, manifest_payload(run, two_vetoed_ids(run)))

    edited = tmp_path / "weapons.csv"
    lines = Path(WEAPONS).read_text(encoding="utf-8").splitlines(keepends=True)
    edited.write_text("".join(lines[:-1]), encoding="utf-8")

    rc = cli.main([
        "review", "--weapons", str(edited), "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
        "--overrides", str(tmp_path / "overrides.json"),
        "--output", str(tmp_path / "reviewed.csv"),
        "--manifest", str(manifest), "--write",
    ])
    assert rc == 1
    assert "different report run" in capsys.readouterr().err
    assert not (tmp_path / "reviewed.csv").exists()


def test_malformed_manifest_is_a_clean_error(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema_version": 1, "nope": true}', encoding="utf-8")
    assert run_review(tmp_path, "--manifest", str(bad), "--write") == 1
    assert "unknown key(s) ['nope']" in capsys.readouterr().err
    assert not (tmp_path / "reviewed.csv").exists()


def test_malformed_overrides_are_a_clean_error(tmp_path, capsys):
    (tmp_path / "overrides.json").write_text('{"schema_version": 99}', encoding="utf-8")
    assert run_review(tmp_path) == 1
    assert "schema_version 99" in capsys.readouterr().err


def test_stale_and_orphaned_overrides_are_reported(tmp_path, capsys):
    run = build_report()
    decision = proposals(run)[0]
    survivor = min(
        next(s for s in run.sections if s.kind == "weapons").item_ids
        - {d.id for d in proposals(run)}
    )
    base = {
        "hash": "500", "name": "Whatever", "fingerprint": "f" * 64,
        "recorded_at": "2026-07-01T00:00:00Z",
    }
    save_overrides(
        OverrideStore(
            schema_version=1,
            vetoes=(
                Veto(id=decision.id, kind=decision.kind, action="junk",
                     reason="a-reason-that-moved-on", **base),
                Veto(id=survivor, kind="weapons", action="junk",
                     reason="dupe-lower", **base),
                Veto(id="404404404", kind="weapons", action="junk",
                     reason="dupe-lower", **base),
                Veto(id=BIG_ID, kind="ghosts", action="junk",
                     reason="ghost-unprotected-surplus", **base),
            ),
        ),
        tmp_path / "overrides.json",
    )

    assert run_review(tmp_path) == 0
    out = capsys.readouterr().out
    # both exports are present here, so an absent id is a dismantled item
    assert "0 active, 2 stale, 2 orphaned, 0 unchecked" in out
    assert "re-review it" in out
    assert "no longer proposed for cleanup" in out
    assert "no longer in the export" in out
    assert f"Whatever (id {BIG_ID}, ghosts" in out


def test_unchecked_beats_orphaned_when_an_export_is_missing(tmp_path, capsys):
    run = build_report()
    manifest = write_manifest(tmp_path, manifest_payload(run, two_vetoed_ids(run)))
    assert run_review(tmp_path, "--manifest", str(manifest), "--write") == 0
    capsys.readouterr()

    rc = cli.main([
        "review", "--weapons", str(tmp_path / "absent.csv"), "--armor", ARMOR,
        "--ghosts", GHOSTS, "--no-wishlists", "--config", "nonexistent.toml",
        "--overrides", str(tmp_path / "overrides.json"),
        "--output", str(tmp_path / "reviewed.csv"),
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert "skipping weapons" in captured.err
    assert "0 active, 0 stale, 0 orphaned, 2 unchecked" in captured.out
    assert "weapons export not loaded this run" in captured.out


def test_warns_that_a_veto_cannot_undo_an_imported_junk_tag(tmp_path, capsys):
    edited = tmp_path / "weapons.csv"
    rows = Path(WEAPONS).read_text(encoding="utf-8").splitlines()
    tag_column = rows[0].split(",").index("Tag")
    target = next(i for i, row in enumerate(rows) if '"""3002"""' in row)
    cells = rows[target].split(",")
    cells[tag_column] = "junk"
    rows[target] = ",".join(cells)
    edited.write_text("\n".join(rows) + "\n", encoding="utf-8")

    run = build_report(weapons_path=edited)
    manifest = write_manifest(tmp_path, manifest_payload(run, ["3002"]))
    rc = cli.main([
        "review", "--weapons", str(edited), "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
        "--overrides", str(tmp_path / "overrides.json"),
        "--output", str(tmp_path / "reviewed.csv"),
        "--manifest", str(manifest),
    ])
    err = capsys.readouterr().err
    assert rc == 0
    assert "already tagged junk in DIM" in err
    assert "it does not restore the previous tag" in err
    assert "id 3002" in err


def test_manifest_veto_for_an_unproposed_id_is_reported(tmp_path, capsys):
    run = build_report()
    payload = manifest_payload(run, [])
    payload["decisions"].append({
        "id": "404404404", "kind": "weapons", "hash": "1", "name": "Gone",
        "action": "junk", "reason": "dupe-lower", "verdict": "vetoed",
    })
    manifest = write_manifest(tmp_path, payload)

    assert run_review(tmp_path, "--manifest", str(manifest)) == 0
    assert "not proposed by this run" in capsys.readouterr().err


def test_approved_id_that_is_already_vetoed_is_kept_and_explained(tmp_path, capsys):
    run = build_report()
    ids = two_vetoed_ids(run)
    vetoing = write_manifest(tmp_path, manifest_payload(run, ids))
    assert run_review(tmp_path, "--manifest", str(vetoing), "--write") == 0
    capsys.readouterr()

    approving = write_manifest(tmp_path, manifest_payload(run, []), "approve.json")
    assert run_review(tmp_path, "--manifest", str(approving), "--write") == 0
    captured = capsys.readouterr()
    assert "applying a manifest never removes a veto" in captured.err
    assert load_overrides(tmp_path / "overrides.json").vetoes != ()
    assert f"after vetoes: {len(proposals(run)) - 2} decision(s)" in captured.out


def test_report_mentions_but_does_not_apply_overrides(tmp_path, capsys):
    run = build_report()
    ids = two_vetoed_ids(run)
    manifest = write_manifest(tmp_path, manifest_payload(run, ids))
    assert run_review(tmp_path, "--manifest", str(manifest), "--write") == 0
    capsys.readouterr()

    assert run_report_cmd(tmp_path) == 0
    out = capsys.readouterr().out
    assert "note: 2 persisted veto(es)" in out
    assert "run `vault-cleaner review` for the reviewed export" in out
    # the raw proposal set is unchanged
    junked = sum(1 for d in proposals(run) if d.action == "junk")
    reviewed = sum(1 for d in proposals(run) if d.action == "review")
    assert out.startswith(f"would junk {junked} item(s) and flag {reviewed} for review")


def test_report_survives_a_malformed_overrides_file(tmp_path, capsys):
    (tmp_path / "overrides.json").write_text("{ broken", encoding="utf-8")
    assert run_report_cmd(tmp_path) == 0
    captured = capsys.readouterr()
    assert "warning: ignoring overrides" in captured.err
    assert captured.out.startswith("would junk")


def test_report_without_overrides_says_nothing_about_them(tmp_path, capsys):
    assert run_report_cmd(tmp_path) == 0
    assert "persisted veto" not in capsys.readouterr().out


def test_full_width_64_bit_ids_survive_the_whole_round_trip(tmp_path):
    """Ids stay opaque strings from manifest to overrides file to CSV."""
    run = build_report()
    decision = proposals(run)[0]
    payload = manifest_payload(run, [decision.id])
    manifest = write_manifest(tmp_path, payload)
    assert run_review(tmp_path, "--manifest", str(manifest), "--write") == 0

    raw = json.loads((tmp_path / "overrides.json").read_text(encoding="utf-8"))
    assert raw["vetoes"][0]["id"] == decision.id
    assert isinstance(raw["vetoes"][0]["id"], str)

    written = (tmp_path / "reviewed.csv").read_text(encoding="utf-8")
    for kept in proposals(run):
        if kept.id != decision.id:
            assert f'"""{kept.id}"""' in written
