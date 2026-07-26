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

# Generous: these runs are milliseconds in practice. The point is that an
# accidental infinite loop in the shipped script fails loudly instead of
# hanging the whole suite with no diagnostic.
NODE_TIMEOUT = 60

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

// The raw-text number scan, which exists because JSON.parse erases the
// difference between 1, 1.0, and 1e0. "" means the text is acceptable.
var exported = JSON.stringify(manifest, null, 2) + "\n";
out.numberSpelling = {
  integer: api.fractionalNumberError('{"v": 1}'),
  float: api.fractionalNumberError('{"v": 1.0}'),
  exponent: api.fractionalNumberError('{"v": 1e0}'),
  negativeFraction: api.fractionalNumberError('{"v": -2.5}'),
  fractionInsideAString: api.fractionalNumberError('{"name": "Price: 1.5 (v1.0)"}'),
  escapedQuoteThenFraction: api.fractionalNumberError('{"name": "say \\" then 1.5"}'),
  literalsContainingE: api.fractionalNumberError('{"a": true, "b": false, "c": null}'),
  bigIdAsString: api.fractionalNumberError('{"id": "18446744073709551615"}'),
  bareBigInteger: api.fractionalNumberError('{"n": 18446744073709551615}'),
  ourOwnExport: api.fractionalNumberError(exported)
};

// The page must always be able to re-read what it just wrote.
out.exportRoundTripsThroughText = (function () {
  var result = api.readManifestText(snapshot, items, exported);
  return { ok: result.ok, error: result.error || "", applied: result.applied };
})();

// Strict UTF-8 decoding, which FileReader.readAsText does not do: it
// substitutes U+FFFD for malformed sequences and strips a leading BOM.
function decodes(bytes) {
  var result = api.decodeManifestBytes(new Uint8Array(bytes));
  return result.ok ? "ok:" + result.text : "refused";
}
out.decoding = {
  ascii: decodes([0x7b, 0x7d]),
  multibyte: decodes([0x22, 0xc3, 0x9c, 0x22]),
  astral: decodes([0x22, 0xf0, 0x9f, 0x92, 0x80, 0x22]),
  loneContinuation: decodes([0x22, 0x80, 0x22]),
  truncatedSequence: decodes([0x22, 0xe2, 0x82, 0x22]),
  overlongSlash: decodes([0x22, 0xc0, 0xaf, 0x22]),
  loneSurrogate: decodes([0x22, 0xed, 0xa0, 0x80, 0x22]),
  // ignoreBOM: true means the U+FEFF is kept, so JSON.parse refuses it the way
  // Python's json does. Dropping that option would silently accept this.
  bomIsKept: decodes([0xef, 0xbb, 0xbf, 0x7b, 0x7d]),
  bomPrefixedManifestRefused:
    api.readManifestBytes(snapshot, items,
      new Uint8Array([0xef, 0xbb, 0xbf, 0x7b, 0x7d])).ok ? "accepted" : "refused",
  ourOwnExport: api.readManifestBytes(
    snapshot, items, new TextEncoder().encode(exported)).ok ? "accepted" : "refused"
};

// The paste entry point. JS trim() counts U+FEFF, U+00A0, U+2028, and U+3000 as
// whitespace and JSON does not, so trimming before validating laundered all
// four into accepted manifests.
function pasted(value) {
  var result = api.readPastedManifest(snapshot, items, value);
  if (result.empty) return "empty";
  return result.ok ? "accepted" : "refused";
}
out.pasting = {
  plain: pasted(exported),
  surroundingJsonWhitespace: pasted("\n\t  " + exported + "  \n\n"),
  bom: pasted("\ufeff" + exported),
  nbsp: pasted("\u00a0" + exported),
  lineSeparator: pasted("\u2028" + exported),
  ideographicSpace: pasted("\u3000" + exported),
  trailingBom: pasted(exported + "\ufeff"),
  emptyString: pasted(""),
  whitespaceOnly: pasted("   \n\t  "),
  nullish: pasted(null),
  // trim() would have made every one of these look like the plain case.
  trimWouldHaveAccepted: ["\ufeff", "\u00a0", "\u2028", "\u3000"].map(
    function (prefix) { return (prefix + exported).trim() === exported.trim(); })
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
    subprocess.run(
        [NODE, "--check", str(workdir / "app.js")], check=True, timeout=NODE_TIMEOUT
    )
    completed = subprocess.run(
        [
            NODE, str(workdir / "harness.js"),
            str(workdir / "app.js"), str(workdir / "snapshot.json"), str(workdir),
        ],
        capture_output=True, text=True, check=False, timeout=NODE_TIMEOUT,
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
        capture_output=True, text=True, check=True, timeout=NODE_TIMEOUT,
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
        ("wrongManifestSchema", "manifest: schema_version 2 is not supported"),
        ("wrongSnapshotSchema", "snapshot: schema_version 99 is not supported"),
        ("wrongRuleset", "snapshot: ruleset_version 99 is not supported"),
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


# ------------------------------------------------------- validation parity
#
# The page validates a manifest and so does Python, and the two drifted apart
# once already: the browser accepted unknown keys, missing display fields, and
# over-long names that `parse_manifest` refuses, so an import could report
# success on a file Python would later reject. Hand-maintained case lists on
# each side are what let that happen, so parity is checked from ONE table of
# payloads run through BOTH implementations.


PARITY_HARNESS = r"""
"use strict";
var fs = require("fs");
var path = require("path");
var api = require(process.argv[2]);
var snapshot = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
var caseDir = process.argv[4];

// Bytes in, verdict out — the same contract as parse_manifest(path), so
// encoding, number spelling, and unparseable text are all inside what this
// compares. Reading the file as a Buffer and handing it to the page's own
// readManifestBytes matters: decoding here with node's lenient "utf8" would
// model a decode the page does not perform (it strips no BOM, where the
// browser's FileReader does).
// Both import entry points, because the UI has two and a divergence hid in the
// one that was not covered: the file input (bytes) and the paste box (text).
var items = api.itemsFromSnapshot(snapshot);
var byFile = {};
var byPaste = {};
fs.readdirSync(caseDir).filter(function (name) {
  return name.slice(-5) === ".json";
}).forEach(function (name) {
  var key = name.slice(0, -5);
  var bytes = fs.readFileSync(path.join(caseDir, name));
  byFile[key] = api.readManifestBytes(snapshot, items, bytes).ok
    ? "accepted" : "refused";
  // Bytes that are not text cannot be pasted, so those cases have no paste
  // equivalent. Everything else must agree on both paths.
  var decoded = api.decodeManifestBytes(bytes);
  if (decoded.ok) {
    byPaste[key] = api.readPastedManifest(snapshot, items, decoded.text).ok
      ? "accepted" : "refused";
  }
});
process.stdout.write(JSON.stringify({ file: byFile, paste: byPaste }));
"""


def parity_cases(run) -> dict[str, bytes]:
    """One case per manifest, as the exact *file bytes* both sides will read.

    Bytes rather than text, and text rather than objects, because each layer
    hid a divergence: `JSON.parse` collapses 1, 1.0, and 1e0 to one double
    while Python keeps 1.0 as a float, and `FileReader.readAsText` substitutes
    U+FFFD for malformed sequences and strips BOMs where Python does neither.

    Accept cases matter as much as refusals: they are what stops the browser
    from becoming *stricter* than Python and rejecting good manifests.
    """
    decisions = proposals(run)
    assert len(decisions) >= 2, "parity table needs at least two proposals"
    first, second = decisions[0], decisions[1]

    def entry(decision, verdict="vetoed", **overrides):
        base = {
            "id": decision.id, "kind": decision.kind, "hash": decision.hash,
            "name": decision.name, "action": decision.action,
            "reason": decision.reason, "verdict": verdict,
        }
        base.update(overrides)
        return base

    def manifest(**overrides):
        base = {
            "schema_version": 1,
            "generated_at": "2026-07-26T12:00:00Z",
            "snapshot": {
                "schema_version": 1, "ruleset_version": 1,
                "fingerprint": run.fingerprint,
            },
            "decisions": [entry(first), entry(second, "approved")],
        }
        base.update(overrides)
        return base

    def snapshot_block(**overrides):
        block = dict(manifest()["snapshot"])
        block.update(overrides)
        return block

    cases: dict[str, object] = {
        # -- must be accepted by both --------------------------------------
        "ok_full": manifest(),
        "ok_no_generated_at": {
            key: value for key, value in manifest().items() if key != "generated_at"
        },
        "ok_no_decisions": manifest(decisions=[]),
        "ok_empty_name": manifest(decisions=[entry(first, name="")]),
        # 200 code points but 400 UTF-16 units: legal for Python's len(), and
        # the case that fails if the browser counts `.length`.
        "ok_name_200_astral": manifest(
            decisions=[entry(first, name="\U0001f480" * 200)]
        ),
        # -- must be refused by both ---------------------------------------
        "bad_root_unknown_key": manifest(input="../../etc/passwd"),
        "bad_snapshot_unknown_key": manifest(
            snapshot=snapshot_block(output_path="/etc/passwd")
        ),
        "bad_decision_unknown_key": manifest(decisions=[entry(first, tag="junk")]),
        "bad_decision_only_id_and_verdict": manifest(
            decisions=[{"id": first.id, "verdict": "vetoed"}]
        ),
        "bad_name_too_long": manifest(decisions=[entry(first, name="A" * 201)]),
        "bad_name_201_astral": manifest(
            decisions=[entry(first, name="\U0001f480" * 201)]
        ),
        "bad_kind_numeric": manifest(decisions=[entry(first, kind=7)]),
        "bad_kind_empty": manifest(decisions=[entry(first, kind="")]),
        "bad_hash_missing": manifest(
            decisions=[{k: v for k, v in entry(first).items() if k != "hash"}]
        ),
        "bad_action_missing": manifest(
            decisions=[{k: v for k, v in entry(first).items() if k != "action"}]
        ),
        "bad_reason_null": manifest(decisions=[entry(first, reason=None)]),
        "bad_generated_at_empty": manifest(generated_at=""),
        "bad_generated_at_numeric": manifest(generated_at=20260726),
        "bad_generated_at_too_long": manifest(generated_at="z" * 201),
        "bad_schema_version_bool": manifest(schema_version=True),
        "bad_schema_version_string": manifest(schema_version="1"),
        "bad_schema_version_two": manifest(schema_version=2),
        "bad_schema_version_missing": {
            key: value for key, value in manifest().items() if key != "schema_version"
        },
        "bad_snapshot_missing": {
            key: value for key, value in manifest().items() if key != "snapshot"
        },
        "bad_snapshot_not_object": manifest(snapshot="nope"),
        "bad_ruleset_version_wrong": manifest(snapshot=snapshot_block(ruleset_version=99)),
        "bad_snapshot_schema_wrong": manifest(snapshot=snapshot_block(schema_version=99)),
        "bad_fingerprint_missing": manifest(
            snapshot={"schema_version": 1, "ruleset_version": 1}
        ),
        "bad_fingerprint_empty": manifest(snapshot=snapshot_block(fingerprint="")),
        "bad_fingerprint_numeric": manifest(snapshot=snapshot_block(fingerprint=1)),
        # Well-formed but for another run: parse_manifest alone accepts this,
        # which is why the Python side of this test also runs
        # check_manifest_matches.
        "bad_fingerprint_other_run": manifest(
            snapshot=snapshot_block(fingerprint="f" * 64)
        ),
        "bad_decisions_missing": {
            key: value for key, value in manifest().items() if key != "decisions"
        },
        "bad_decisions_not_a_list": manifest(decisions="nope"),
        "bad_decision_not_an_object": manifest(decisions=["nope"]),
        "bad_id_numeric": manifest(decisions=[entry(first, id=3001)]),
        "bad_id_not_digits": manifest(decisions=[entry(first, id="3001; DROP")]),
        "bad_id_empty": manifest(decisions=[entry(first, id="")]),
        "bad_id_duplicated": manifest(decisions=[entry(first), entry(first)]),
        "bad_verdict_unknown": manifest(decisions=[entry(first, verdict="maybe")]),
        "bad_verdict_missing": manifest(
            decisions=[{k: v for k, v in entry(first).items() if k != "verdict"}]
        ),
        "bad_verdict_null": manifest(decisions=[entry(first, verdict=None)]),
    }

    # Everything above is a JSON-serialisable object; below are cases that only
    # exist as *text*, because the bug that prompted them is about spelling and
    # about input that never parses at all.
    raw: dict[str, str] = {
        # A `name` whose text contains fractions. Python accepts it (it is just
        # a string), so the browser's raw-text scan must not trip on it — this
        # is the over-rejection guard for the whole approach.
        "ok_fraction_inside_a_name": json.dumps(
            manifest(decisions=[entry(first, name="Price: 1.5 credits (v1.0)")]),
            ensure_ascii=False,
        ),
        "ok_escaped_quote_then_fraction": json.dumps(
            manifest(decisions=[entry(first, name='say " then 1.5')]),
            ensure_ascii=False,
        ),
        "ok_pretty_printed": json.dumps(manifest(), indent=2, ensure_ascii=False),
        # JSON.parse collapses all three of these to the same double; Python
        # keeps the latter two as floats and _require_version refuses them.
        "bad_version_float": json.dumps(manifest()).replace(
            '"schema_version": 1,', '"schema_version": 1.0,', 1
        ),
        "bad_version_exponent": json.dumps(manifest()).replace(
            '"schema_version": 1,', '"schema_version": 1e0,', 1
        ),
        "bad_snapshot_version_float": json.dumps(manifest()).replace(
            '"schema_version": 1, "ruleset_version"',
            '"schema_version": 1.0, "ruleset_version"',
            1,
        ),
        "bad_ruleset_version_float": json.dumps(manifest()).replace(
            '"ruleset_version": 1', '"ruleset_version": 1.0', 1
        ),
        # Reachable only through the text entry point.
        "bad_not_json_at_all": "{not json",
        "bad_json_truncated": json.dumps(manifest())[:-5],
        "bad_json_root_array": "[]",
        "bad_json_root_string": '"a manifest"',
        "bad_json_nan": json.dumps(manifest()).replace(
            '"schema_version": 1,', '"schema_version": NaN,', 1
        ),
        "bad_json_infinity": json.dumps(manifest()).replace(
            '"schema_version": 1,', '"schema_version": Infinity,', 1
        ),
    }

    # Multi-byte text that is *correctly* encoded must survive strict decoding —
    # item names really do contain accents and emoji, and refusing them would
    # be an over-rejection that breaks manifests Python accepts.
    multibyte = json.dumps(
        manifest(decisions=[entry(first, name="Ünïcödé \U0001f480 shell")]),
        ensure_ascii=False,
    ).encode("utf-8")
    # U+FEFF *inside* a string is an ordinary character, not a byte-order mark;
    # Python accepts it, so the browser must too.
    interior_bom = json.dumps(
        manifest(decisions=[entry(first, name="zero\ufeffwidth")]), ensure_ascii=False
    ).encode("utf-8")
    valid = json.dumps(manifest(), ensure_ascii=False).encode("utf-8")

    # Cases that only exist as *bytes*. FileReader.readAsText silently repaired
    # every one of the malformed ones into a manifest that imported cleanly,
    # while Python refused the same file.
    raw_bytes: dict[str, bytes] = {
        "ok_utf8_multibyte_name": multibyte,
        "ok_utf8_interior_feff": interior_bom,
        "bad_utf8_lone_continuation": multibyte.replace(b"shell", b"sh\x80ell"),
        "bad_utf8_truncated_sequence": multibyte.replace(b"shell", b"sh\xe2\x82ell"),
        "bad_utf8_overlong_slash": multibyte.replace(b"shell", b"sh\xc0\xafell"),
        "bad_utf8_lone_surrogate": multibyte.replace(b"shell", b"sh\xed\xa0\x80ell"),
        # A BOM is stripped by readAsText and by TextDecoder's default, but
        # Python keeps it and json refuses it — so `ignoreBOM: true` is what
        # keeps this case in agreement.
        "bad_utf8_bom_prefix": b"\xef\xbb\xbf" + valid,
        # Prefixes JavaScript's trim() treats as whitespace and JSON does not.
        # Valid UTF-8, so these reach the paste path too — which is where they
        # were being laundered into accepted manifests.
        "bad_leading_nbsp": "\u00a0".encode() + valid,
        "bad_leading_line_separator": "\u2028".encode() + valid,
        "bad_leading_ideographic_space": "\u3000".encode() + valid,
        # The row that makes dropping trim() safe: ordinary JSON whitespace is
        # still fine, on both paths and in Python.
        "ok_surrounding_json_whitespace": b"\n  " + valid + b"\n\n",
    }

    text = {
        name: json.dumps(payload, ensure_ascii=False).encode("utf-8")
        for name, payload in cases.items()
    }
    raw_encoded = {name: body.encode("utf-8") for name, body in raw.items()}
    for table in (raw_encoded, raw_bytes):
        overlap = set(text) & set(table)
        assert not overlap, f"case name reused between tables: {overlap}"
        text.update(table)

    for name, body in raw_bytes.items():
        if name.startswith("bad_utf8_") and "bom" not in name:
            assert body != multibyte, f"{name} substitution missed"

    # A replace() that silently matched nothing would leave a *valid* manifest
    # under a "bad_" name, and the naming check would then fail confusingly.
    for name in ("bad_version_float", "bad_version_exponent",
                 "bad_snapshot_version_float", "bad_ruleset_version_float",
                 "bad_json_nan", "bad_json_infinity"):
        assert text[name] != json.dumps(manifest()).encode(), f"{name} missed"
    return text


def python_verdict(path: Path, run) -> str:
    """What Python does with this file, parse and identity check together.

    Only `ReviewError` counts as a refusal. Anything else propagating means
    Python *crashed* on the file rather than rejecting it, which is a bug in
    its own right — mis-encoded bytes used to reach here as an uncaught
    `UnicodeDecodeError` — so let it fail the test loudly.
    """
    from vault_cleaner.review import ReviewError

    try:
        check_manifest_matches(parse_manifest(path), run)
    except ReviewError:
        return "refused"
    return "accepted"


@pytest.fixture(scope="module")
def parity(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("parity")
    run = build_report()
    app = split_artifact(render_review_html(run))[2]
    (workdir / "app.js").write_text(app, encoding="utf-8")
    (workdir / "snapshot.json").write_text(snapshot_json(run), encoding="utf-8")
    (workdir / "parity.js").write_text(PARITY_HARNESS, encoding="utf-8")

    cases = parity_cases(run)
    case_dir = workdir / "cases"
    case_dir.mkdir()
    for name, body in cases.items():
        # write_bytes, so a deliberately mis-encoded case stays mis-encoded.
        (case_dir / f"{name}.json").write_bytes(body)

    completed = subprocess.run(
        [
            NODE, str(workdir / "parity.js"), str(workdir / "app.js"),
            str(workdir / "snapshot.json"), str(case_dir),
        ],
        capture_output=True, text=True, check=False, timeout=NODE_TIMEOUT,
    )
    assert completed.returncode == 0, completed.stderr
    browser = json.loads(completed.stdout)
    python = {name: python_verdict(case_dir / f"{name}.json", run) for name in cases}
    undecodable = set()
    for name, body in cases.items():
        try:
            body.decode("utf-8")
        except UnicodeDecodeError:
            undecodable.add(name)
    return {
        "file": browser["file"],
        "paste": browser["paste"],
        "python": python,
        "names": sorted(cases),
        "undecodable": undecodable,
    }


@pytest.mark.parametrize("entry_point", ["file", "paste"])
def test_the_browser_and_python_agree_on_every_manifest(parity, entry_point):
    """The assertion that keeps the two validators from drifting apart.

    Run for *both* import entry points. The paste path was missing from this
    table for three review rounds, and a divergence lived there the whole time.
    """
    browser = parity[entry_point]
    disagreements = {
        name: {"browser": browser[name], "python": parity["python"][name]}
        for name in parity["names"]
        if name in browser and browser[name] != parity["python"][name]
    }
    assert not disagreements, (
        f"the review page's {entry_point} import and review.parse_manifest "
        "disagree — the page must refuse exactly what Python refuses: "
        f"{json.dumps(disagreements, indent=2)}"
    )


def test_the_paste_path_covers_every_case_that_can_be_pasted(parity):
    """Guard the skip list, or coverage can shrink without anyone noticing.

    Bytes that are not valid UTF-8 have no paste equivalent — a clipboard holds
    text — so those cases are file-path only. Everything else must appear in
    both columns.
    """
    expected = set(parity["names"]) - parity["undecodable"]
    assert set(parity["paste"]) == expected, (
        "the paste column skipped cases that can be pasted: "
        f"{sorted(expected - set(parity['paste']))}"
    )
    assert parity["undecodable"], "the table should still cover undecodable bytes"


def test_number_spelling_is_judged_on_the_raw_text(plain):
    """`Number.isInteger` cannot see the difference; only the text can.

    `JSON.parse` collapses 1, 1.0, and 1e0 to the same double, while Python's
    `json.loads` keeps the latter two as floats that `_require_version` refuses.
    """
    spelling = plain.results["numberSpelling"]
    assert spelling["float"] == "1.0"
    assert spelling["exponent"] == "1e0"
    assert spelling["negativeFraction"] == "-2.5"


def test_the_scan_does_not_trip_on_fractions_that_are_only_text(plain):
    """The over-rejection guard: refusing these would break good manifests."""
    spelling = plain.results["numberSpelling"]
    assert spelling["integer"] == ""
    assert spelling["fractionInsideAString"] == "", "a name may contain '1.5'"
    assert spelling["escapedQuoteThenFraction"] == "", "escapes must be tracked"
    assert spelling["literalsContainingE"] == "", "the 'e' in true is not an exponent"
    assert spelling["bigIdAsString"] == ""
    assert spelling["bareBigInteger"] == ""


def test_the_page_can_always_reread_its_own_export(plain):
    assert plain.results["numberSpelling"]["ourOwnExport"] == ""
    assert plain.results["exportRoundTripsThroughText"] == {
        "ok": True, "error": "", "applied": 2
    }
    assert plain.results["decoding"]["ourOwnExport"] == "accepted"


def test_malformed_utf8_is_refused_rather_than_repaired(plain):
    """`FileReader.readAsText` substitutes U+FFFD and imports the file happily.

    Python's `read_text(encoding="utf-8")` refuses the same bytes, so the page
    has to decode with `fatal: true` or the two disagree at the file boundary.
    """
    decoding = plain.results["decoding"]
    for case in ("loneContinuation", "truncatedSequence", "overlongSlash",
                 "loneSurrogate"):
        assert decoding[case] == "refused", case


def test_a_leading_bom_is_kept_so_json_refuses_it_like_python_does(plain):
    """`ignoreBOM: true` is load-bearing, not decoration.

    `readAsText` and `TextDecoder`'s default both strip a leading U+FEFF, but
    Python keeps it and `json` then refuses it. Stripping would trade the
    malformed-bytes divergence for a BOM one.
    """
    decoding = plain.results["decoding"]
    assert decoding["bomIsKept"] == "ok:\ufeff{}"
    assert decoding["bomPrefixedManifestRefused"] == "refused"


def test_correctly_encoded_multibyte_text_still_decodes(plain):
    """The over-rejection guard: real item names have accents and emoji."""
    decoding = plain.results["decoding"]
    assert decoding["ascii"] == "ok:{}"
    assert decoding["multibyte"] == 'ok:"Ü"'
    assert decoding["astral"] == 'ok:"\U0001f480"'


def test_pasting_does_not_trim_before_validating(plain):
    """JS `trim()` is not JSON whitespace, so it must not run first.

    It removes U+FEFF, U+00A0, U+2028, and U+3000 — none of which JSON accepts —
    so trimming before validation laundered four prefixes into manifests Python
    refuses. Exactly the divergence `ignoreBOM: true` closes on the file path,
    left open on this one for three rounds because the trim lived in an
    un-exported click handler.
    """
    pasting = plain.results["pasting"]
    for case in ("bom", "nbsp", "lineSeparator", "ideographicSpace", "trailingBom"):
        assert pasting[case] == "refused", case
    # And the reason it was easy to miss: trim() makes all four indistinguishable
    # from a clean paste.
    assert pasting["trimWouldHaveAccepted"] == [True, True, True, True]


def test_pasting_still_accepts_ordinary_whitespace(plain):
    """The row that makes dropping `trim()` safe.

    `JSON.parse` already allows leading and trailing JSON whitespace, so nothing
    is lost by handing the value over untouched.
    """
    pasting = plain.results["pasting"]
    assert pasting["plain"] == "accepted"
    assert pasting["surroundingJsonWhitespace"] == "accepted"


def test_an_empty_paste_is_reported_separately_from_a_bad_one(plain):
    """`trim()` still answers the one question it can: is the box empty."""
    pasting = plain.results["pasting"]
    assert pasting["emptyString"] == "empty"
    assert pasting["whitespaceOnly"] == "empty"
    assert pasting["nullish"] == "empty"


def test_the_parity_table_covers_both_outcomes(parity):
    """A table of all-refusals would pass vacuously while the page over-rejects."""
    outcomes = parity["python"]
    assert [n for n in parity["names"] if outcomes[n] == "accepted"], "no accept cases"
    assert [n for n in parity["names"] if outcomes[n] == "refused"], "no refuse cases"
    # Naming is load-bearing: an `ok_`/`bad_` prefix that disagrees with the
    # actual outcome means the case does not test what it claims to.
    for name in parity["names"]:
        expected = "accepted" if name.startswith("ok_") else "refused"
        assert outcomes[name] == expected, f"{name} is {outcomes[name]}"
