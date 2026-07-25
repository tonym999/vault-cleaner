"""`vault-cleaner review-html`: dry-run by default, and a distinct surface.

The point of a separate subcommand is that the two write actions stay
unambiguous — `report --write` keeps producing the proposal CSV and this one
only ever produces the review page.
"""

import csv
import json
from pathlib import Path

from test_review import BIG_ID, build_report, proposals

from vault_cleaner import cli
from vault_cleaner.report_run import snapshot_dict
from vault_cleaner.review import check_manifest_matches, parse_manifest
from vault_cleaner.review_html import DEFAULT_REVIEW_HTML

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = str(FIXTURES / "weapons_dupes.csv")
ARMOR = str(FIXTURES / "armor.csv")
GHOSTS = str(FIXTURES / "ghosts_cleanup.csv")


def run_html(tmp_path, *extra: str, output: str | None = None) -> int:
    return cli.main([
        "review-html",
        "--weapons", WEAPONS, "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
        "--output", output or str(tmp_path / "review.html"),
        *extra,
    ])


def test_dry_run_describes_the_write_and_touches_nothing(tmp_path, capsys):
    target = tmp_path / "review.html"
    assert run_html(tmp_path) == 0
    out = capsys.readouterr().out
    assert f"would write {target}" in out
    assert "dry run — nothing written" in out
    assert "review page: 14 decision(s) (6 junk, 8 review)" in out
    assert not target.exists()


def test_dry_run_reports_the_fingerprint_the_manifest_will_carry(tmp_path, capsys):
    assert run_html(tmp_path) == 0
    assert f"fingerprint: {build_report().fingerprint}" in capsys.readouterr().out


def test_write_creates_the_page_and_says_how_to_apply_it(tmp_path, capsys):
    target = tmp_path / "review.html"
    assert run_html(tmp_path, "--write") == 0
    out = capsys.readouterr().out
    assert f"wrote {target}" in out
    assert "vault-cleaner review --manifest" in out
    assert "keep it local" in out, "the privacy warning must reach the terminal too"

    html = target.read_text(encoding="utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")


def test_default_output_stays_under_the_gitignored_data_dir():
    assert DEFAULT_REVIEW_HTML == "data/out/vault-review.html"


def test_dry_run_does_not_write_to_the_default_path_either(tmp_path, capsys, monkeypatch):
    """Belt and braces on the rule that matters most: no --write, no files.

    Run from `tmp_path`, because `DEFAULT_REVIEW_HTML` is relative: an artifact
    left in the checkout by any earlier `review-html --write` would otherwise
    fail this even though the dry run wrote nothing. The fixture paths are
    absolute, so only the default output moves.
    """
    monkeypatch.chdir(tmp_path)
    assert cli.main([
        "review-html", "--weapons", WEAPONS, "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
    ]) == 0
    assert "would write data/out/vault-review.html" in capsys.readouterr().out
    assert not Path(DEFAULT_REVIEW_HTML).exists()


def test_report_write_still_writes_the_csv_not_the_page(tmp_path, capsys):
    target = tmp_path / "dim-import.csv"
    assert cli.main([
        "report", "--weapons", WEAPONS, "--armor", ARMOR, "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
        "--overrides", str(tmp_path / "overrides.json"),
        "--output", str(target), "--write",
    ]) == 0
    capsys.readouterr()
    with target.open(encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["Id", "Hash", "Tag", "Notes"]


def test_missing_exports_are_an_error_not_a_traceback(tmp_path, capsys):
    assert cli.main([
        "review-html",
        "--weapons", str(tmp_path / "nope.csv"),
        "--armor", str(tmp_path / "nope.csv"),
        "--ghosts", str(tmp_path / "nope.csv"),
        "--no-wishlists", "--config", "nonexistent.toml",
        "--output", str(tmp_path / "review.html"), "--write",
    ]) == 1
    captured = capsys.readouterr()
    assert "error: no exports found" in captured.err
    assert not (tmp_path / "review.html").exists()


def test_a_skipped_export_is_warned_about_but_still_renders(tmp_path, capsys):
    target = tmp_path / "review.html"
    assert cli.main([
        "review-html", "--weapons", WEAPONS,
        "--armor", str(tmp_path / "nope.csv"), "--ghosts", GHOSTS,
        "--no-wishlists", "--config", "nonexistent.toml",
        "--output", str(target), "--write",
    ]) == 0
    assert "skipping armor" in capsys.readouterr().err
    assert target.exists()


def test_written_page_embeds_this_runs_snapshot(tmp_path, capsys):
    target = tmp_path / "review.html"
    assert run_html(tmp_path, "--write") == 0
    capsys.readouterr()
    html = target.read_text(encoding="utf-8")
    start = html.index('id="vc-snapshot">') + len('id="vc-snapshot">')
    embedded = json.loads(html[start:html.index("</script>", start)])
    assert embedded == snapshot_dict(build_report())


def test_a_manifest_for_this_page_is_accepted_by_review(tmp_path):
    """The handoff contract: what the page must emit, #36 must accept."""
    run = build_report()
    vetoed = proposals(run)[0].id
    payload = {
        "schema_version": 1,
        "generated_at": "2026-07-25T12:00:00Z",
        "snapshot": {
            "schema_version": snapshot_dict(run)["schema_version"],
            "ruleset_version": snapshot_dict(run)["ruleset_version"],
            "fingerprint": snapshot_dict(run)["fingerprint"],
        },
        "decisions": [
            {
                "id": d.id, "kind": d.kind, "hash": d.hash, "name": d.name,
                "action": d.action, "reason": d.reason,
                "verdict": "vetoed" if d.id == vetoed else "approved",
            }
            for d in proposals(run)
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    manifest = parse_manifest(path)
    check_manifest_matches(manifest, run)
    assert [d.id for d in manifest.vetoed] == [vetoed]
    assert all(isinstance(d.id, str) for d in manifest.decisions)


def test_big_instance_ids_reach_the_page_as_digits(tmp_path, capsys):
    target = tmp_path / "review.html"
    assert cli.main([
        "review-html",
        "--weapons", str(FIXTURES / "weapons_hostile.csv"),
        "--armor", str(tmp_path / "nope.csv"), "--ghosts", str(tmp_path / "nope.csv"),
        "--no-wishlists", "--config", "nonexistent.toml",
        "--output", str(target), "--write",
    ]) == 0
    capsys.readouterr()
    assert BIG_ID in target.read_text(encoding="utf-8")
