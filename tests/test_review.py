import json
import os
from pathlib import Path

import pytest

from vault_cleaner import review
from vault_cleaner.report_run import run_report
from vault_cleaner.review import (
    FingerprintMismatchError,
    OverridesError,
    OverrideStore,
    ReviewManifestError,
    Veto,
    apply_vetoes,
    check_manifest_matches,
    classify,
    load_overrides,
    merge_manifest,
    parse_manifest,
    save_overrides,
)

FIXTURES = Path(__file__).parent / "fixtures"
WEAPONS = FIXTURES / "weapons_dupes.csv"
ARMOR = FIXTURES / "armor.csv"
GHOSTS = FIXTURES / "ghosts_cleanup.csv"

# 2**64 - 1: the widest value a DIM instance id can carry. Any accidental
# int round trip through JSON or pandas mangles the low digits.
BIG_ID = "18446744073709551615"


def build_report(**kwargs):
    return run_report(
        config_path="nonexistent.toml",
        weapons_path=kwargs.pop("weapons_path", WEAPONS),
        armor_path=kwargs.pop("armor_path", ARMOR),
        ghosts_path=kwargs.pop("ghosts_path", GHOSTS),
        no_wishlists=True,
        **kwargs,
    )


def proposals(run):
    return [d for section in run.sections for d in section.decisions]


def manifest_payload(run, vetoed_ids=()):
    vetoed = set(vetoed_ids)
    return {
        "schema_version": 1,
        "generated_at": "2026-07-25T12:00:00Z",
        "snapshot": {
            "schema_version": 1,
            "ruleset_version": 1,
            "fingerprint": run.fingerprint,
        },
        "decisions": [
            {
                "id": d.id,
                "kind": d.kind,
                "hash": d.hash,
                "name": d.name,
                "action": d.action,
                "reason": d.reason,
                "verdict": "vetoed" if d.id in vetoed else "approved",
            }
            for d in proposals(run)
        ],
    }


def write_manifest(tmp_path, payload, name="manifest.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def a_veto(**kwargs):
    base = {
        "id": "3002",
        "kind": "weapons",
        "hash": "500",
        "name": "Dupe Rifle",
        "action": "junk",
        "reason": "dupe-lower",
        "fingerprint": "f" * 64,
        "recorded_at": "2026-07-25T12:00:00Z",
    }
    return Veto(**{**base, **kwargs})


def store_of(*vetoes):
    return OverrideStore(schema_version=1, vetoes=tuple(vetoes))


# --- manifest parsing -------------------------------------------------------


def test_valid_manifest_splits_vetoed_from_approved(tmp_path):
    run = build_report()
    ids = [d.id for d in proposals(run)][:2]
    path = write_manifest(tmp_path, manifest_payload(run, ids))

    manifest = parse_manifest(path)
    assert manifest.fingerprint == run.fingerprint
    assert [d.id for d in manifest.vetoed] == ids
    assert len(manifest.approved) == len(proposals(run)) - 2
    assert all(isinstance(d.id, str) for d in manifest.decisions)


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda p: p.update(schema_version=2), "schema_version 2 is not supported"),
        (lambda p: p["snapshot"].update(schema_version=99), "schema_version 99"),
        (lambda p: p["snapshot"].update(ruleset_version=7), "ruleset_version 7"),
        (lambda p: p.update(schema_version="1"), "'schema_version' must be an integer"),
        (lambda p: p.pop("snapshot"), "'snapshot' must be an object"),
        (lambda p: p.update(decisions={}), "'decisions' must be a list"),
        (lambda p: p["decisions"].append([]), "must be an object"),
    ],
)
def test_manifest_structural_rejections(tmp_path, mutate, expected):
    run = build_report()
    payload = manifest_payload(run)
    mutate(payload)
    with pytest.raises(ReviewManifestError, match=expected):
        parse_manifest(write_manifest(tmp_path, payload))


def test_manifest_rejects_unknown_top_level_key_including_paths(tmp_path):
    """A manifest must never be able to redirect this tool at a file."""
    run = build_report()
    payload = manifest_payload(run)
    payload["output_path"] = "/etc/passwd"
    with pytest.raises(ReviewManifestError, match=r"unknown key\(s\) \['output_path'\]"):
        parse_manifest(write_manifest(tmp_path, payload))


def test_manifest_rejects_unknown_decision_key(tmp_path):
    run = build_report()
    payload = manifest_payload(run)
    payload["decisions"][0]["input"] = "../../data/in/other.csv"
    with pytest.raises(ReviewManifestError, match=r"unknown key\(s\) \['input'\]"):
        parse_manifest(write_manifest(tmp_path, payload))


@pytest.mark.parametrize(
    "bad_id",
    ["", "  ", '"3002"', "3002x", "-1", "1e5", "3002.0", "1" * 21, "٣٠٠٢"],
)
def test_manifest_rejects_malformed_ids(tmp_path, bad_id):
    run = build_report()
    payload = manifest_payload(run)
    payload["decisions"][0]["id"] = bad_id
    with pytest.raises(ReviewManifestError, match="is not a DIM instance id"):
        parse_manifest(write_manifest(tmp_path, payload))


def test_manifest_rejects_non_string_id(tmp_path):
    """Ids stay opaque strings — a JSON number has already lost precision."""
    run = build_report()
    payload = manifest_payload(run)
    payload["decisions"][0]["id"] = 18446744073709551615
    with pytest.raises(ReviewManifestError, match="'id' must be a string, not int"):
        parse_manifest(write_manifest(tmp_path, payload))


def test_manifest_accepts_full_width_64_bit_id_unchanged(tmp_path):
    run = build_report()
    payload = manifest_payload(run)
    payload["decisions"][0]["id"] = BIG_ID
    manifest = parse_manifest(write_manifest(tmp_path, payload))
    assert manifest.decisions[0].id == BIG_ID


def test_manifest_rejects_duplicate_vetoes(tmp_path):
    run = build_report()
    payload = manifest_payload(run)
    entry = dict(payload["decisions"][0], verdict="vetoed")
    payload["decisions"] = [entry, dict(entry)]
    with pytest.raises(ReviewManifestError, match="duplicate 'vetoed' entries"):
        parse_manifest(write_manifest(tmp_path, payload))


def test_manifest_rejects_conflicting_verdicts_for_one_id(tmp_path):
    run = build_report()
    payload = manifest_payload(run)
    entry = payload["decisions"][0]
    payload["decisions"] = [
        dict(entry, verdict="approved"),
        dict(entry, verdict="vetoed"),
    ]
    with pytest.raises(ReviewManifestError, match="conflicting verdicts"):
        parse_manifest(write_manifest(tmp_path, payload))


def test_manifest_rejects_unknown_verdict(tmp_path):
    run = build_report()
    payload = manifest_payload(run)
    payload["decisions"][0]["verdict"] = "maybe"
    with pytest.raises(ReviewManifestError, match="verdict 'maybe' must be one of"):
        parse_manifest(write_manifest(tmp_path, payload))


def test_manifest_rejects_non_json_and_non_object(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ReviewManifestError, match="not valid JSON"):
        parse_manifest(bad)

    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ReviewManifestError, match="must be a JSON object"):
        parse_manifest(bad)


def test_manifest_rejects_non_finite_numbers(tmp_path):
    bad = tmp_path / "nan.json"
    bad.write_text('{"schema_version": NaN}', encoding="utf-8")
    with pytest.raises(ReviewManifestError, match="non-finite JSON number"):
        parse_manifest(bad)


def test_manifest_rejects_overlong_text(tmp_path):
    run = build_report()
    payload = manifest_payload(run)
    payload["decisions"][0]["name"] = "x" * 500
    with pytest.raises(ReviewManifestError, match="longer than 200 characters"):
        parse_manifest(write_manifest(tmp_path, payload))


def test_missing_manifest_is_an_error(tmp_path):
    with pytest.raises(ReviewManifestError, match="could not read review manifest"):
        parse_manifest(tmp_path / "absent.json")


# --- fingerprint gate -------------------------------------------------------


def test_matching_fingerprint_passes_and_mismatch_refuses(tmp_path):
    run = build_report()
    manifest = parse_manifest(write_manifest(tmp_path, manifest_payload(run)))
    check_manifest_matches(manifest, run)

    payload = manifest_payload(run)
    payload["snapshot"]["fingerprint"] = "0" * 64
    stale = parse_manifest(write_manifest(tmp_path, payload, "stale.json"))
    with pytest.raises(FingerprintMismatchError, match="different report run"):
        check_manifest_matches(stale, run)


def test_changed_export_invalidates_a_manifest(tmp_path):
    """The real staleness case: the same review against a re-exported vault."""
    run = build_report()
    manifest = parse_manifest(write_manifest(tmp_path, manifest_payload(run)))

    edited = tmp_path / "weapons.csv"
    lines = WEAPONS.read_text(encoding="utf-8").splitlines(keepends=True)
    edited.write_text("".join(lines[:-1]), encoding="utf-8")
    changed = build_report(weapons_path=edited)

    assert changed.fingerprint != run.fingerprint
    with pytest.raises(FingerprintMismatchError):
        check_manifest_matches(manifest, changed)


# --- overrides persistence --------------------------------------------------


def test_missing_overrides_file_is_an_empty_store(tmp_path):
    store = load_overrides(tmp_path / "absent.json")
    assert store.vetoes == ()


def test_overrides_round_trip_preserves_big_ids(tmp_path):
    path = tmp_path / "overrides.json"
    store = store_of(a_veto(id=BIG_ID), a_veto(id="3003", kind="armor"))
    save_overrides(store, path)

    reloaded = load_overrides(path)
    assert {v.id for v in reloaded.vetoes} == {BIG_ID, "3003"}
    assert reloaded.by_id()[BIG_ID].id == BIG_ID
    assert '"' + BIG_ID + '"' in path.read_text(encoding="utf-8")


def test_saved_overrides_are_deterministically_ordered(tmp_path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    vetoes = [a_veto(id="3003", kind="weapons"), a_veto(id="3002", kind="armor")]
    save_overrides(store_of(*vetoes), first, updated_at="2026-07-25T12:00:00Z")
    save_overrides(store_of(*reversed(vetoes)), second, updated_at="2026-07-25T12:00:00Z")
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda p: p.update(schema_version=4), "schema_version 4"),
        (lambda p: p.update(vetoes={}), "'vetoes' must be a list"),
        (lambda p: p.update(extra=1), r"unknown key\(s\) \['extra'\]"),
        (lambda p: p["vetoes"][0].update(id="nope"), "is not a DIM instance id"),
        (lambda p: p["vetoes"][0].update(surprise=1), r"unknown key\(s\) \['surprise'\]"),
        (lambda p: p["vetoes"][0].update(kind="weapon"), "not a known export kind"),
        (lambda p: p["vetoes"][0].update(kind="Ghosts"), "not a known export kind"),
        (lambda p: p["vetoes"].append(dict(p["vetoes"][0])), "appears twice"),
    ],
)
def test_malformed_overrides_are_rejected(tmp_path, mutate, expected):
    path = tmp_path / "overrides.json"
    save_overrides(store_of(a_veto()), path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(OverridesError, match=expected):
        load_overrides(path)


def test_interrupted_save_leaves_the_previous_file_intact(tmp_path, monkeypatch):
    """A half-written overrides file would lose real review work."""
    path = tmp_path / "overrides.json"
    save_overrides(store_of(a_veto()), path, updated_at="2026-07-25T12:00:00Z")
    original = path.read_bytes()

    def boom(src, dst):
        raise OSError("interrupted")

    monkeypatch.setattr(review.os, "replace", boom)
    with pytest.raises(OSError, match="interrupted"):
        save_overrides(store_of(a_veto(), a_veto(id="9999")), path)

    assert path.read_bytes() == original
    assert load_overrides(path).vetoes == (a_veto(),)
    assert [p.name for p in tmp_path.iterdir()] == ["overrides.json"]


def test_failure_while_serializing_leaves_no_partial_file(tmp_path, monkeypatch):
    path = tmp_path / "overrides.json"
    save_overrides(store_of(a_veto()), path, updated_at="2026-07-25T12:00:00Z")
    original = path.read_bytes()

    def boom(*args, **kwargs):
        raise MemoryError("no room")

    monkeypatch.setattr(review.json, "dump", boom)
    with pytest.raises(MemoryError):
        save_overrides(store_of(a_veto(id="9999")), path)

    assert path.read_bytes() == original
    assert [p.name for p in tmp_path.iterdir()] == ["overrides.json"]


def test_save_creates_missing_parent_directories(tmp_path):
    path = tmp_path / "nested" / "deeper" / "overrides.json"
    save_overrides(store_of(a_veto()), path)
    assert load_overrides(path).vetoes[0].id == "3002"


def test_save_survives_a_platform_that_refuses_directory_handles(tmp_path, monkeypatch):
    """os.replace has already committed by then — never fail the caller.

    A raise here would abort `review --write` before it writes the reviewed
    CSV, leaving persisted vetoes with no export to match them.
    """
    real_open = os.open

    def picky_open(path, flags, *args, **kwargs):
        # Selective on purpose: review.os is the os module, so mkstemp's own
        # os.open (O_CREAT|O_EXCL|O_RDWR) must still get through.
        if flags == os.O_RDONLY:
            raise OSError("directory handles are not supported here")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(review.os, "open", picky_open)
    path = tmp_path / "overrides.json"
    assert save_overrides(store_of(a_veto()), path) == path
    assert load_overrides(path).vetoes[0].id == "3002"


def test_save_survives_a_filesystem_that_refuses_directory_fsync(tmp_path, monkeypatch):
    real_fsync = os.fsync
    calls = []

    def picky_fsync(fd):
        calls.append(fd)
        if len(calls) > 1:  # the directory handle, not the file
            raise OSError("fsync not supported")
        return real_fsync(fd)

    monkeypatch.setattr(review.os, "fsync", picky_fsync)
    path = tmp_path / "overrides.json"
    save_overrides(store_of(a_veto()), path)
    assert load_overrides(path).vetoes[0].id == "3002"


# --- classification ---------------------------------------------------------


def test_active_when_the_proposal_still_matches():
    run = build_report()
    decision = proposals(run)[0]
    status = classify(
        store_of(
            a_veto(
                id=decision.id,
                kind=decision.kind,
                action=decision.action,
                reason=decision.reason,
            )
        ),
        run,
    )
    assert status.active_ids == {decision.id}
    assert not status.stale and not status.orphaned and not status.unchecked


def test_changed_proposal_goes_stale_rather_than_suppressing_it():
    """The reviewer never saw this decision, so the veto must not apply."""
    run = build_report()
    decision = proposals(run)[0]
    status = classify(
        store_of(
            a_veto(id=decision.id, kind=decision.kind, action="junk", reason="was-different")
        ),
        run,
    )
    assert status.active == ()
    assert [entry.veto.id for entry in status.stale] == [decision.id]
    assert "re-review it" in status.stale[0].detail


def test_item_still_present_but_no_longer_proposed_is_stale():
    run = build_report()
    decided = {d.id for d in proposals(run)}
    section = next(s for s in run.sections if s.kind == "weapons")
    survivor = min(section.item_ids - decided)

    status = classify(store_of(a_veto(id=survivor, kind="weapons")), run)
    assert [entry.veto.id for entry in status.stale] == [survivor]
    assert "no longer proposed" in status.stale[0].detail
    assert status.orphaned == ()


def test_id_absent_from_the_export_is_orphaned():
    run = build_report()
    status = classify(store_of(a_veto(id="404404404", kind="weapons")), run)
    assert [v.id for v in status.orphaned] == ["404404404"]


def test_veto_for_an_unloaded_export_is_unchecked_not_orphaned(tmp_path):
    """A skipped export must not look like a dismantled item."""
    run = build_report(ghosts_path=tmp_path / "absent.csv")
    status = classify(store_of(a_veto(id="404404404", kind="ghosts")), run)
    assert [v.id for v in status.unchecked] == ["404404404"]
    assert status.orphaned == ()


# --- applying ---------------------------------------------------------------


def test_apply_vetoes_removes_only_the_vetoed_rows_in_order():
    run = build_report()
    all_decisions = proposals(run)
    vetoed = {all_decisions[1].id, all_decisions[3].id}

    kept = apply_vetoes(run, vetoed)
    assert [d.id for d in kept] == [d.id for d in all_decisions if d.id not in vetoed]


def test_vetoing_a_loser_does_not_promote_or_rerank_anything():
    """Overrides run after the pipeline: one more copy simply survives."""
    run = build_report()
    all_decisions = proposals(run)
    loser = next(d for d in all_decisions if d.kept_id)

    kept = apply_vetoes(run, [loser.id])
    assert loser.id not in {d.id for d in kept}
    # the winner it deferred to is still untouched by any decision
    assert loser.kept_id not in {d.id for d in kept}
    # every other decision is byte-identical to before
    assert [d for d in kept] == [d for d in all_decisions if d.id != loser.id]


def test_apply_vetoes_ignores_ids_that_were_never_proposed():
    run = build_report()
    assert apply_vetoes(run, ["404404404"]) == proposals(run)


# --- merging ----------------------------------------------------------------


def test_merge_adds_new_vetoes_and_reports_counts(tmp_path):
    run = build_report()
    ids = [d.id for d in proposals(run)][:2]
    manifest = parse_manifest(write_manifest(tmp_path, manifest_payload(run, ids)))

    merged = merge_manifest(review.empty_store(), manifest, run)
    assert sorted(v.id for v in merged.added) == sorted(ids)
    assert merged.updated == () and merged.unchanged == ()
    assert sorted(v.id for v in merged.store.vetoes) == sorted(ids)


def test_reapplying_the_same_manifest_changes_nothing(tmp_path):
    run = build_report()
    ids = [d.id for d in proposals(run)][:2]
    manifest = parse_manifest(write_manifest(tmp_path, manifest_payload(run, ids)))

    first = merge_manifest(review.empty_store(), manifest, run)
    second = merge_manifest(first.store, manifest, run)

    assert second.added == () and second.updated == ()
    assert len(second.unchanged) == 2
    assert second.store == first.store  # including recorded_at — no churn


def test_merge_updates_a_veto_whose_proposal_changed(tmp_path):
    run = build_report()
    decision = proposals(run)[0]
    manifest = parse_manifest(
        write_manifest(tmp_path, manifest_payload(run, [decision.id]))
    )
    stored = store_of(
        a_veto(id=decision.id, kind=decision.kind, action="junk", reason="older-reason")
    )

    merged = merge_manifest(stored, manifest, run)
    assert [v.id for v in merged.updated] == [decision.id]
    assert merged.store.by_id()[decision.id].reason == decision.reason


def test_merge_trusts_the_run_not_the_manifests_display_metadata(tmp_path):
    """Only identity crosses the boundary; the rest is the UI's copy."""
    run = build_report()
    decision = proposals(run)[0]
    payload = manifest_payload(run, [decision.id])
    entry = next(e for e in payload["decisions"] if e["id"] == decision.id)
    entry.update(name="Lies", kind="ghosts", hash="999", action="junk", reason="fake")
    manifest = parse_manifest(write_manifest(tmp_path, payload))

    veto = merge_manifest(review.empty_store(), manifest, run).store.by_id()[decision.id]
    assert (veto.name, veto.kind, veto.hash) == (decision.name, decision.kind, decision.hash)
    assert (veto.action, veto.reason) == (decision.action, decision.reason)
    assert veto.fingerprint == run.fingerprint


def test_approving_never_removes_an_existing_veto(tmp_path):
    """A UI that forgot last session must not resurrect rejected junk."""
    run = build_report()
    decision = proposals(run)[0]
    manifest = parse_manifest(write_manifest(tmp_path, manifest_payload(run, [])))
    stored = store_of(
        a_veto(
            id=decision.id,
            kind=decision.kind,
            action=decision.action,
            reason=decision.reason,
        )
    )

    merged = merge_manifest(stored, manifest, run)
    assert merged.store.by_id().keys() == {decision.id}
    assert [d.id for d in merged.already_vetoed_but_approved] == [decision.id]


def test_manifest_veto_for_an_unproposed_id_is_reported_not_stored(tmp_path):
    run = build_report()
    payload = manifest_payload(run, [])
    payload["decisions"].append(
        {
            "id": "404404404",
            "kind": "weapons",
            "hash": "1",
            "name": "Ghost Of A Row",
            "action": "junk",
            "reason": "dupe-lower",
            "verdict": "vetoed",
        }
    )
    manifest = parse_manifest(write_manifest(tmp_path, payload))

    merged = merge_manifest(review.empty_store(), manifest, run)
    assert [d.id for d in merged.unknown_ids] == ["404404404"]
    assert merged.store.vetoes == ()


def test_imported_junk_tags_flags_items_already_tagged_in_dim(tmp_path):
    """Vetoing cannot undo a junk tag an earlier cleanup already imported."""
    edited = tmp_path / "weapons.csv"
    rows = WEAPONS.read_text(encoding="utf-8").splitlines()
    header = rows[0].split(",")
    tag_column = header.index("Tag")
    target = next(i for i, row in enumerate(rows) if '"""3002"""' in row)
    cells = rows[target].split(",")
    # DIM quotes the id, so it occupies three comma-free cells either side of
    # the split — the Tag column sits before it, unaffected by that quoting.
    assert cells[tag_column] == ""
    cells[tag_column] = "junk"
    rows[target] = ",".join(cells)
    edited.write_text("\n".join(rows) + "\n", encoding="utf-8")

    run = build_report(weapons_path=edited)
    decision = next(d for d in proposals(run) if d.id == "3002")
    assert decision.original_tag == "junk"

    status = classify(
        store_of(
            a_veto(
                id=decision.id,
                kind=decision.kind,
                action=decision.action,
                reason=decision.reason,
            )
        ),
        run,
    )
    assert [v.id for v, _ in review.imported_junk_tags(status)] == [decision.id]
