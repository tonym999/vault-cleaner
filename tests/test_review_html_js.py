"""Exercise the review page's browser logic by running the shipped script.

The script is extracted from a *generated artifact*, not from a copy, and run
under node — so these tests fail if the real page's filtering, grouping,
counting, or manifest handling drifts. The page's pure logic is exported under
CommonJS precisely so this is possible without a browser or a bundler.

Skipped when node is absent. CI's ubuntu runners ship it, and nothing in the
package depends on it at runtime.
"""

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from test_review import BIG_ID, build_report, proposals
from test_review_html import hostile_report, split_artifact

from vault_cleaner.report import summarize
from vault_cleaner.report_run import snapshot_json
from vault_cleaner.review import check_manifest_matches, parse_manifest
from vault_cleaner.review_html import render_review_html

NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(
    NODE is None, reason="node is not installed; the review page's logic is JavaScript"
)

# Drives the page's exported logic and prints one JSON blob of observations.
# Kept in-repo as a string so no packaging or asset wiring is involved.
HARNESS = r"""
"use strict";
var fs = require("fs");
var api = require(process.argv[2]);
var snapshot = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
var outDir = process.argv[4];

var items = api.itemsFromSnapshot(snapshot);
var out = {};

function ids(list) { return list.map(function (item) { return item.id; }); }

function verdictMap(pairs) {
  var map = Object.create(null);
  pairs.forEach(function (pair) { map[pair[0]] = pair[1]; });
  return map;
}

function write(name, value) {
  fs.writeFileSync(outDir + "/" + name, JSON.stringify(value, null, 2) + "\n");
}

out.itemCount = items.length;
out.ids = ids(items);
out.idsAndHashesAreStrings = items.every(function (item) {
  return typeof item.id === "string" && typeof item.hash === "string";
});
out.groupLabels = api.groupItems(items).map(function (g) { return g.label; });
out.actionCounts = api.actionCounts(items);
out.sortedById = ids(api.sortItems(items, "id", "asc"));
out.sortedByIdDesc = ids(api.sortItems(items, "id", "desc"));
out.sortedByName = api.sortItems(items, "name", "asc").map(function (i) {
  return i.name;
});
out.unknownSortFieldFallsBackToName =
  JSON.stringify(ids(api.sortItems(items, "nope", "asc"))) ===
  JSON.stringify(ids(api.sortItems(items, "name", "asc")));

// Numeric ordering of 64-bit ids, and why it cannot go through Number().
var BIG = "18446744073709551615", BIG_MINUS_1 = "18446744073709551614";
out.precision = {
  compare: api.compareIds(BIG, BIG_MINUS_1),
  numberWouldTie: Number(BIG) === Number(BIG_MINUS_1),
  shorterFirst: api.compareIds("9", "10"),
  ordered: ["10", BIG, "9", BIG_MINUS_1].sort(api.compareIds)
};

var first = items[0], second = items[1];
var verdicts = verdictMap([[first.id, "vetoed"], [second.id, "approved"]]);

out.filters = {
  junk: ids(api.filterItems(items, { action: "junk" })),
  weaponsJunk: ids(api.filterItems(items, { action: "junk", kind: "weapons" })),
  byReason: ids(api.filterItems(items, { reason: first.reason })),
  byOwner: ids(api.filterItems(items, { owner: first.owner })),
  protectedOnly: ids(api.filterItems(items, { protection: "protected" })),
  unprotectedOnly: ids(api.filterItems(items, { protection: "unprotected" })),
  soft: ids(api.filterItems(items, { protection: "soft" })),
  hard: ids(api.filterItems(items, { protection: "hard" })),
  searchById: ids(api.filterItems(items, { text: first.id })),
  searchByNameLower: ids(api.filterItems(items, { text: first.name.toLowerCase() })),
  searchMisses: ids(api.filterItems(items, { text: "no such item anywhere" })),
  emptyQueryKeepsAll: api.filterItems(items, {}).length,
  vetoed: ids(api.filterItems(items, { verdict: "vetoed" }, verdicts)),
  approved: ids(api.filterItems(items, { verdict: "approved" }, verdicts)),
  unreviewed: api.filterItems(items, { verdict: "unreviewed" }, verdicts).length
};

out.counts = {
  kept: api.keptItems(items, verdicts).length,
  keptExcludesVetoed: ids(api.keptItems(items, verdicts)).indexOf(first.id) === -1,
  keptActions: api.actionCounts(api.keptItems(items, verdicts)),
  review: api.reviewCounts(items, verdicts),
  byKind: api.countBy(items, "kind"),
  byAction: api.countBy(items, "action")
};

var manifest = api.buildManifest(snapshot, items, verdicts, "2026-07-25T12:00:00Z");
write("manifest.json", manifest);
out.manifest = {
  vetoedId: first.id,
  approvedId: second.id,
  emitted: manifest.decisions.map(function (d) { return [d.id, d.verdict]; }),
  keys: Object.keys(manifest).sort(),
  snapshotKeys: Object.keys(manifest.snapshot).sort(),
  decisionKeys: manifest.decisions.length ? Object.keys(manifest.decisions[0]).sort() : []
};

var everything = verdictMap(items.map(function (item) { return [item.id, "vetoed"]; }));
write("manifest-all-vetoed.json", api.buildManifest(
  snapshot, items, everything, "2026-07-25T12:00:00Z"));
write("manifest-empty.json", api.buildManifest(
  snapshot, items, Object.create(null), "2026-07-25T12:00:00Z"));

out.roundTrip = api.readManifest(snapshot, items, manifest);

function rejected(mutate) {
  var copy = JSON.parse(JSON.stringify(manifest));
  mutate(copy);
  var result = api.readManifest(snapshot, items, copy);
  return result.ok ? "ACCEPTED" : result.error;
}

out.rejections = {
  wrongFingerprint: rejected(function (m) {
    m.snapshot.fingerprint = new Array(65).join("f");
  }),
  wrongManifestSchema: rejected(function (m) { m.schema_version = 2; }),
  wrongSnapshotSchema: rejected(function (m) { m.snapshot.schema_version = 99; }),
  wrongRuleset: rejected(function (m) { m.snapshot.ruleset_version = 99; }),
  badVerdict: rejected(function (m) { m.decisions[0].verdict = "maybe"; }),
  numericId: rejected(function (m) { m.decisions[0].id = 123; }),
  nonDigitId: rejected(function (m) { m.decisions[0].id = "3001; DROP"; }),
  duplicateId: rejected(function (m) {
    m.decisions.push(JSON.parse(JSON.stringify(m.decisions[0])));
  }),
  decisionsNotAList: rejected(function (m) { m.decisions = "nope"; }),
  snapshotNotAnObject: rejected(function (m) { m.snapshot = "nope"; }),
  notAnObject: (function () {
    var r = api.readManifest(snapshot, items, [1, 2, 3]);
    return r.ok ? "ACCEPTED" : r.error;
  })()
};

out.unknownIds = (function () {
  var copy = JSON.parse(JSON.stringify(manifest));
  copy.decisions.push({
    id: "999999999999", kind: "weapons", hash: "1", name: "sold long ago",
    action: "junk", reason: "dupe-lower", verdict: "vetoed"
  });
  var r = api.readManifest(snapshot, items, copy);
  return {
    ok: r.ok, applied: r.applied, unknown: r.unknown,
    stored: Object.keys(r.verdicts).sort()
  };
})();

// countBy keys on item names, so a name that looks like a prototype slot is
// the pollution vector worth pinning.
out.prototypeSafety = {
  names: api.countBy(items, "name").map(function (e) { return [e.value, e.count]; }),
  objectPrototypeClean: Object.prototype.polluted === undefined &&
                        ({}).__proto__ === Object.prototype
};

out.clip = {
  longName: Array.from(api.clip(new Array(261).join("A"))).length,
  shortUnchanged: api.clip("abc") === "abc",
  emojiNotSplit: Array.from(api.clip(new Array(301).join("\u{1F480}"))).every(
    function (point) { return point === "\u{1F480}"; })
};

out.verdictOf = {
  unset: api.verdictOf(Object.create(null), "1"),
  garbageIgnored: api.verdictOf(verdictMap([["1", "probably"]]), "1"),
  set: api.verdictOf(verdictMap([["1", "vetoed"]]), "1")
};

process.stdout.write(JSON.stringify(out));
"""


@dataclass(frozen=True)
class Harness:
    results: dict
    workdir: Path
    run: object


def drive(workdir: Path, run) -> Harness:
    """Extract the shipped script from a rendered artifact and run it."""
    app = split_artifact(render_review_html(run))[2]
    (workdir / "app.js").write_text(app, encoding="utf-8")
    (workdir / "snapshot.json").write_text(snapshot_json(run), encoding="utf-8")
    (workdir / "harness.js").write_text(HARNESS, encoding="utf-8")

    # A syntax error here means the artifact ships a broken script.
    subprocess.run([NODE, "--check", str(workdir / "app.js")], check=True)
    completed = subprocess.run(
        [
            NODE, str(workdir / "harness.js"),
            str(workdir / "app.js"), str(workdir / "snapshot.json"), str(workdir),
        ],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return Harness(json.loads(completed.stdout), workdir, run)


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    return drive(tmp_path_factory.mktemp("plain"), build_report())


@pytest.fixture(scope="module")
def hostile(tmp_path_factory):
    return drive(tmp_path_factory.mktemp("hostile"), hostile_report())


# ------------------------------------------------------------------- loading


def test_every_decision_becomes_an_item(plain):
    assert plain.results["itemCount"] == len(proposals(plain.run))
    assert sorted(plain.results["ids"]) == sorted(d.id for d in proposals(plain.run))


def test_ids_and_hashes_stay_strings_in_the_browser(plain, hostile):
    assert plain.results["idsAndHashesAreStrings"]
    assert hostile.results["idsAndHashesAreStrings"]


def test_a_numeric_id_in_a_snapshot_is_refused_not_coerced(tmp_path):
    """Numbers have already lost precision by the time JSON.parse returns."""
    app = split_artifact(render_review_html(build_report()))[2]
    (tmp_path / "app.js").write_text(app, encoding="utf-8")
    (tmp_path / "numeric.js").write_text(
        'var api = require(process.argv[2]);\n'
        'try {\n'
        '  api.itemsFromSnapshot({ sections: [{ kind: "weapons", decisions: [\n'
        '    { id: 6917529027641981542, hash: "500" }\n'
        '  ] }] });\n'
        '  process.stdout.write("ACCEPTED");\n'
        '} catch (e) { process.stdout.write(e.message); }\n',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [NODE, str(tmp_path / "numeric.js"), str(tmp_path / "app.js")],
        capture_output=True, text=True, check=True,
    )
    assert "must be a JSON string, not number" in completed.stdout


# ------------------------------------------------------------------ grouping


def test_grouping_matches_the_terminal_summary_exactly(plain):
    """The page and `vault-cleaner report` must tell the same story in order."""
    expected = [
        line for line in summarize(plain.run.summary_sections()).splitlines()
        if line.startswith(("JUNK ", "REVIEW "))
    ]
    assert plain.results["groupLabels"] == expected


def test_action_counts_match_the_run(plain):
    decisions = proposals(plain.run)
    assert plain.results["actionCounts"] == {
        "total": len(decisions),
        "junk": sum(1 for d in decisions if d.action == "junk"),
        "review": sum(1 for d in decisions if d.action == "review"),
    }


def test_count_by_kind_covers_every_section(plain):
    by_kind = {entry["value"]: entry["count"] for entry in plain.results["counts"]["byKind"]}
    assert by_kind == {
        section.kind: len(section.decisions)
        for section in plain.run.sections
        if section.decisions
    }


# ------------------------------------------------------------------- sorting


def test_ids_sort_numerically_without_going_through_number(hostile):
    precision = hostile.results["precision"]
    assert precision["compare"] == 1, "the wider id must sort after the narrower"
    assert precision["numberWouldTie"], "Number() really does lose these digits"
    assert precision["shorterFirst"] == -1, "9 before 10, not lexicographically"
    assert precision["ordered"] == [
        "9", "10", "18446744073709551614", "18446744073709551615"
    ]


def test_sorting_by_id_is_a_reversible_total_order(plain):
    ascending = plain.results["sortedById"]
    assert ascending == sorted(ascending, key=int)
    assert plain.results["sortedByIdDesc"] == list(reversed(ascending))


def test_an_unknown_sort_field_falls_back_to_name(plain):
    assert plain.results["unknownSortFieldFallsBackToName"]


# ----------------------------------------------------------------- filtering


def test_filters_select_the_same_items_the_run_would(plain):
    decisions = {d.id: d for d in proposals(plain.run)}
    filters = plain.results["filters"]
    assert set(filters["junk"]) == {i for i, d in decisions.items() if d.action == "junk"}
    assert set(filters["weaponsJunk"]) == {
        i for i, d in decisions.items() if d.action == "junk" and d.kind == "weapons"
    }
    assert set(filters["protectedOnly"]) == {
        i for i, d in decisions.items() if d.protection_level
    }
    assert set(filters["soft"]) == {
        i for i, d in decisions.items() if d.protection_level == "soft"
    }
    assert not set(filters["protectedOnly"]) & set(filters["unprotectedOnly"])
    assert filters["emptyQueryKeepsAll"] == len(decisions)


def test_search_matches_name_case_insensitively_and_id_exactly(plain):
    filters = plain.results["filters"]
    first = plain.results["ids"][0]
    assert filters["searchById"] == [first]
    assert first in filters["searchByNameLower"]
    assert filters["searchMisses"] == []


def test_verdict_filter_partitions_the_items(plain):
    filters = plain.results["filters"]
    assert len(filters["vetoed"]) == 1
    assert len(filters["approved"]) == 1
    assert filters["unreviewed"] == plain.results["itemCount"] - 2


# ------------------------------------------------------------------- counting


def test_a_veto_removes_exactly_one_proposal_from_the_kept_set(plain):
    counts = plain.results["counts"]
    assert counts["kept"] == plain.results["itemCount"] - 1
    assert counts["keptExcludesVetoed"]
    assert counts["review"] == {
        "approved": 1, "vetoed": 1, "unreviewed": plain.results["itemCount"] - 2
    }


def test_kept_counts_mirror_python_apply_vetoes(plain):
    from vault_cleaner.review import apply_vetoes

    vetoed = plain.results["manifest"]["vetoedId"]
    kept = apply_vetoes(plain.run, frozenset({vetoed}))
    assert plain.results["counts"]["keptActions"] == {
        "total": len(kept),
        "junk": sum(1 for d in kept if d.action == "junk"),
        "review": sum(1 for d in kept if d.action == "review"),
    }


# -------------------------------------------------------- manifest handoff


def test_exported_manifest_has_exactly_the_keys_review_accepts(plain):
    manifest = plain.results["manifest"]
    assert manifest["keys"] == ["decisions", "generated_at", "schema_version", "snapshot"]
    assert manifest["snapshotKeys"] == ["fingerprint", "ruleset_version", "schema_version"]
    assert manifest["decisionKeys"] == [
        "action", "hash", "id", "kind", "name", "reason", "verdict"
    ]


def test_only_items_with_a_verdict_are_exported(plain):
    emitted = dict(plain.results["manifest"]["emitted"])
    assert emitted == {
        plain.results["manifest"]["vetoedId"]: "vetoed",
        plain.results["manifest"]["approvedId"]: "approved",
    }


def test_the_exported_manifest_is_accepted_by_review(plain):
    manifest = parse_manifest(plain.workdir / "manifest.json")
    check_manifest_matches(manifest, plain.run)
    assert [d.id for d in manifest.vetoed] == [plain.results["manifest"]["vetoedId"]]
    assert [d.id for d in manifest.approved] == [plain.results["manifest"]["approvedId"]]


def test_a_manifest_vetoing_everything_is_accepted(plain):
    manifest = parse_manifest(plain.workdir / "manifest-all-vetoed.json")
    check_manifest_matches(manifest, plain.run)
    assert len(manifest.vetoed) == len(proposals(plain.run))


def test_an_untouched_review_exports_an_empty_but_valid_manifest(plain):
    manifest = parse_manifest(plain.workdir / "manifest-empty.json")
    check_manifest_matches(manifest, plain.run)
    assert manifest.decisions == ()


def test_hostile_names_survive_export_and_python_validation(hostile):
    manifest = parse_manifest(hostile.workdir / "manifest.json")
    check_manifest_matches(manifest, hostile.run)
    names = {d.name for d in manifest.decisions}
    assert any("</script>" in name or "<img" in name for name in names)
    assert all(len(name) <= 200 for name in names), "review.py caps display text at 200"


def test_a_long_name_is_clipped_so_the_manifest_stays_acceptable(hostile):
    clip = hostile.results["clip"]
    assert clip["longName"] == 200
    assert clip["shortUnchanged"]
    assert clip["emojiNotSplit"], "clipping must not leave half a surrogate pair"
    # The 260-character fixture name reached a real manifest as exactly 200 —
    # one character more and review.parse_manifest would reject the file.
    manifest = parse_manifest(hostile.workdir / "manifest-all-vetoed.json")
    assert 200 in {len(d.name) for d in manifest.decisions}


def test_the_widest_id_round_trips_through_export(hostile):
    manifest = parse_manifest(hostile.workdir / "manifest.json")
    assert BIG_ID in {d.id for d in manifest.decisions}


def test_importing_the_exported_manifest_restores_the_same_verdicts(plain):
    trip = plain.results["roundTrip"]
    assert trip["ok"] is True
    assert trip["applied"] == 2
    assert trip["unknown"] == []
    assert trip["verdicts"] == {
        plain.results["manifest"]["vetoedId"]: "vetoed",
        plain.results["manifest"]["approvedId"]: "approved",
    }


def test_import_reports_ids_this_run_no_longer_proposes(plain):
    unknown = plain.results["unknownIds"]
    assert unknown["ok"] is True
    assert unknown["unknown"] == ["999999999999"]
    assert unknown["applied"] == 2
    assert "999999999999" not in unknown["stored"], "the run decides what is on the table"


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("wrongFingerprint", "different report run"),
        ("wrongManifestSchema", "unsupported manifest schema_version 2"),
        ("wrongSnapshotSchema", "targets snapshot schema 99"),
        ("wrongRuleset", "ruleset 99"),
        ("badVerdict", "must be 'approved' or 'vetoed'"),
        ("numericId", "'id' must be a string"),
        ("nonDigitId", "is not a DIM instance id"),
        ("duplicateId", "appears twice"),
        ("decisionsNotAList", "'decisions' must be a list"),
        ("snapshotNotAnObject", "'snapshot' must be an object"),
        ("notAnObject", "not a JSON object"),
    ],
)
def test_import_refuses_malformed_manifests(plain, case, expected):
    message = plain.results["rejections"][case]
    assert message != "ACCEPTED", f"{case} should have been refused"
    assert expected in message


# ------------------------------------------------------------------- hardening


def test_a_prototype_shaped_item_name_is_counted_not_absorbed(hostile):
    """With a plain `{}` accumulator this entry would vanish silently.

    Assigning a number to `__proto__` on a normal object is a no-op, so the
    name would never appear in the counts — and the filter dropdown would
    quietly omit a whole group of items.
    """
    safety = hostile.results["prototypeSafety"]
    names = dict(safety["names"])
    assert names.get("__proto__") == 1, "a __proto__ name must be a normal group key"
    assert safety["objectPrototypeClean"]


def test_unset_and_garbage_verdicts_read_as_unreviewed(plain):
    assert plain.results["verdictOf"] == {
        "unset": "", "garbageIgnored": "", "set": "vetoed"
    }
