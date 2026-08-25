"""Exercise the packaged, manifest-free presentation resource under node."""

import json
import re
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

import pytest
from test_review import build_report, proposals
from test_review_html import hostile_report

from vault_cleaner.report import summarize
from vault_cleaner.report_run import snapshot_json
from vault_cleaner.review import apply_vetoes
from vault_cleaner.review_html import render_review_html

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


HARNESS = r"""
"use strict";
var fs = require("fs");
var api = require(process.argv[2]);
var snapshot = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
var outDir = process.argv[4];
var items = api.itemsFromSnapshot(snapshot);
function ids(list) { return list.map(function (item) { return item.id; }); }

function verdictMap(pairs) {
  var map = Object.create(null);
  pairs.forEach(function (pair) { map[pair[0]] = pair[1]; });
  return map;
}
function rejectsKeptShape(shape, values) {
  try {
    api.keptItems(values || items, verdicts, shape);
    return false;
  } catch (error) {
    return /Set-like object with has/.test(error.message);
  }
}

var first = items[0];
var second = items[1];
var verdicts = Object.create(null);
verdicts[first.id] = "vetoed";
verdicts[second.id] = "approved";
var activePersistedVetoIds = new Set([second.id]);
var out = {
  itemCount: items.length,
  ids: ids(items),
  idsAndHashesAreStrings: items.every(function (item) {
    return typeof item.id === "string" && typeof item.hash === "string";
  }),
  hostileNames: items.map(function (item) { return item.name; }),
  groupLabels: api.groupItems(items).map(function (group) { return group.label; }),
  actionCounts: api.actionCounts(items),
  sortedById: ids(api.sortItems(items, "id", "asc")),
  sortedByIdDesc: ids(api.sortItems(items, "id", "desc")),
  sortedByName: api.sortItems(items, "name", "asc").map(function (item) {
    return item.name;
  }),
  unknownSortFieldFallsBackToName:
    JSON.stringify(ids(api.sortItems(items, "nope", "asc"))) ===
    JSON.stringify(ids(api.sortItems(items, "name", "asc"))),
  precision: {
    compare: api.compareIds("18446744073709551615", "18446744073709551614"),
    numberWouldTie: Number("18446744073709551615") ===
      Number("18446744073709551614"),
    shorterFirst: api.compareIds("9", "10"),
    ordered: ["10", "18446744073709551615", "9",
      "18446744073709551614"].sort(api.compareIds)
  },
  filters: {
    junk: ids(api.filterItems(items, { action: "junk" })),
    weaponsJunk: ids(api.filterItems(items, { action: "junk", kind: "weapons" })),
    byReason: ids(api.filterItems(items, { reason: first.reason })),
    byOwner: ids(api.filterItems(items, { owner: first.owner })),
    protectedOnly: ids(api.filterItems(items, { protection: "protected" })),
    unprotectedOnly: ids(api.filterItems(items, { protection: "unprotected" })),
    soft: ids(api.filterItems(items, { protection: "soft" })),
    hard: ids(api.filterItems(items, { protection: "hard" })),
    searchById: ids(api.filterItems(items, { text: first.id })),
    searchByNameLower: ids(api.filterItems(items, {
      text: first.name.toLowerCase()
    })),
    searchMisses: ids(api.filterItems(items, { text: "no such item anywhere" })),
    emptyQueryKeepsAll: api.filterItems(items, {}).length,
    vetoed: ids(api.filterItems(items, { verdict: "vetoed" }, verdicts)),
    approved: ids(api.filterItems(items, { verdict: "approved" }, verdicts)),
    unreviewed: api.filterItems(items, { verdict: "unreviewed" }, verdicts).length
  },
  counts: {
    kept: api.keptItems(items, verdicts, new Set()).length,
    keptExcludesVetoed: ids(api.keptItems(items, verdicts, new Set()))
      .indexOf(first.id) === -1,
    keptActions: api.actionCounts(api.keptItems(items, verdicts, new Set())),
    review: api.reviewCounts(items, verdicts),
    byKind: api.countBy(items, "kind"),
    byAction: api.countBy(items, "action")
  },
  persistedVeto: {
    kept: ids(api.keptItems(items, verdicts, activePersistedVetoIds)),
    excludesVetoedId: ids(api.keptItems(
      items, verdicts, activePersistedVetoIds
    )).indexOf(first.id) === -1,
    excludesApprovedId: ids(api.keptItems(
      items, verdicts, activePersistedVetoIds
    )).indexOf(second.id) === -1
  },
  persistedVetoContract: {
    absentRejected: rejectsKeptShape(undefined),
    arrayRejected: rejectsKeptShape([second.id]),
    objectRejected: rejectsKeptShape({}),
    absentRejectedForEmptyItems: rejectsKeptShape(undefined, [])
  },
  prototypeSafety: {
    names: api.countBy(items, "name").map(function (entry) {
      return [entry.value, entry.count];
    }),
    objectPrototypeClean: Object.prototype.polluted === undefined &&
      ({}).__proto__ === Object.prototype
  },
  verdictOf: {
    unset: api.verdictOf(Object.create(null), "1"),
    garbageIgnored: api.verdictOf(verdictMap([["1", "probably"]]), "1"),
    set: api.verdictOf(verdictMap([["1", "vetoed"]]), "1")
  }
};
process.stdout.write(JSON.stringify(out));
"""


VIEW_HARNESS = r"""
"use strict";
var api = require(process.argv[2]);

function Node(tagName, ownerDocument) {
  this.tagName = tagName.toUpperCase();
  this.ownerDocument = ownerDocument;
  this.children = [];
  this.parentNode = null;
  this.attributes = Object.create(null);
  this.listeners = Object.create(null);
  this._text = "";
  this.value = "";
}
Object.defineProperty(Node.prototype, "firstChild", {
  get: function () { return this.children[0] || null; }
});
Object.defineProperty(Node.prototype, "textContent", {
  get: function () {
    return this._text + this.children.map(function (child) {
      return child.textContent;
    }).join("");
  },
  set: function (value) {
    this._text = String(value);
    this.children = [];
  }
});
Node.prototype.appendChild = function (child) {
  child.parentNode = this;
  this.children.push(child);
  return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child);
  if (index === -1) throw new Error("child is not present");
  this.children.splice(index, 1);
  child.parentNode = null;
  return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.ids[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name) {
  var event = { target: this, key: name, preventDefault: function () {} };
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null;
  function visit(node) {
    if (found || !node.children) return;
    for (var i = 0; i < node.children.length; i++) {
      var child = node.children[i];
      if (child.tagName.toLowerCase() === selector.toLowerCase()) {
        found = child;
        return;
      }
      visit(child);
      if (found) return;
    }
  }
  visit(this);
  return found;
};

function Document() { this.ids = Object.create(null); }
Document.prototype.createElement = function (tagName) {
  return new Node(tagName, this);
};
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this);
  node.textContent = text;
  return node;
};
Document.prototype.getElementById = function (id) { return this.ids[id] || null; };

function fail(message) { throw new Error(message); }
function find(node, predicate) {
  if (predicate(node)) return node;
  for (var i = 0; i < (node.children || []).length; i++) {
    var result = find(node.children[i], predicate);
    if (result) return result;
  }
  return null;
}
function hasTag(node, tagName) {
  return !!find(node, function (child) {
    return child.tagName === tagName.toUpperCase();
  });
}

var document = new Document();
var hostile = "<img src=x onerror=alert(1)>";
var items = [
  {
    id: "18446744073709551615", hash: "900", name: hostile,
    kind: "weapons", owner: "Titan", action: "junk", reason: "dupe-lower",
    protectionLevel: "", protectionReason: "", tag: "junk", note: "#vc-junk",
    keptId: "9", originalTag: "", originalNotes: "", locked: false,
    equipped: false, inLoadout: false,
    armor: {
      slot: "helmet", equippable: true, best_archetype: "Melee-primary",
      score: 112, base_score: 110, set_bonus: 2, rank: 1, group_size: 2,
      stats: { Mobility: 12, Resilience: 30 }
    }
  },
  {
    id: "9", hash: "901", name: "Keep roll", kind: "weapons", owner: "Titan",
    action: "review", reason: "wishlist", protectionLevel: "soft",
    protectionReason: "locked", tag: "", note: "#vc-review", keptId: "",
    originalTag: "", originalNotes: "", locked: true, equipped: false,
    inLoadout: false, armor: null
  }
];
var state = {
  sort: { field: "name", direction: "asc" },
  expanded: Object.create(null), rows: Object.create(null),
  verdicts: Object.create(null)
};
state.expanded[items[0].id] = true;
var toggles = [];
var renders = 0;
var queryChanges = [];
var view = api.createView({
  document: document, state: state, items: items, columns: api.COLUMNS,
  toggleVerdict: function (id, verdict) { toggles.push([id, verdict]); },
  renderList: function () { renders++; }
});

var inert = view.el("span", { text: hostile });
if (inert.textContent !== hostile || hasTag(inert, "img")) {
  fail("el must leave hostile values as text data");
}
var table = view.table(items);
if (!table.querySelector("table") || !table.querySelector("thead") ||
    !table.querySelector("tbody")) fail("table structure is incomplete");
var header = view.headerRow();
if (header.textContent.indexOf("Verdict") === -1) fail("Verdict header is missing");
if (table.textContent.indexOf("Armor scoring") === -1 ||
    table.textContent.indexOf(hostile) === -1 || hasTag(table, "img")) {
  fail("rows/details must render data through text nodes");
}
var nameButton = find(state.rows[items[0].id].tr, function (node) {
  return node.tagName === "BUTTON" && node.textContent.indexOf(hostile) !== -1;
});
if (!nameButton) fail("expanded row name button is missing");
nameButton.dispatch("click");
if (state.expanded[items[0].id] !== undefined || renders !== 1) {
  fail("detail toggle must wire state and render callback");
}
state.expanded[items[0].id] = true;
view.table([items[0]]);
state.rows[items[0].id].approve.dispatch("click");
if (JSON.stringify(toggles) !== JSON.stringify([[items[0].id, "approved"]])) {
  fail("approve callback is not wired");
}
var sortButton = find(header, function (node) {
  return node.tagName === "BUTTON" && node.textContent.indexOf("Name") !== -1;
});
if (!sortButton) fail("sortable header button is missing");
sortButton.dispatch("click");
if (state.sort.direction !== "desc" || renders !== 2) fail("sort callback is not wired");

var oldStyle = view.optionsFor("kind", "all kinds");
var explicitItems = view.optionsFor(items, "kind", "all kinds");
if (oldStyle.length !== 2 || explicitItems.length !== 2 ||
    oldStyle[1].textContent !== "weapons (2)") {
  fail("optionsFor compatibility shim or counts are broken");
}
var host = document.createElement("div");
view.addSelect(host, "kind", "Kind", oldStyle, "kind", "weapons",
  function (field) {
    return function (event) { queryChanges.push([field, event.target.value]); };
  });
var select = host.querySelector("select");
if (!select || select.value !== "weapons") fail("addSelect must select its value");
select.dispatch("change");
if (JSON.stringify(queryChanges) !== JSON.stringify([["kind", "weapons"]])) {
  fail("addSelect selection callback is not wired");
}
process.stdout.write(JSON.stringify({
  hasHeader: header.textContent.indexOf("Verdict") !== -1,
  hasDetails: table.textContent.indexOf("Armor scoring") !== -1,
  hostileIsText: inert.textContent === hostile && !hasTag(table, "img"),
  callbackState: toggles.length === 1 && renders === 2,
  selected: select.value,
  optionCount: oldStyle.length
}));
"""


@dataclass(frozen=True)
class Harness:
    run: object
    results: dict
    workdir: Path


def run_shared(tmp_path: Path, builder=build_report):
    run = builder()
    snapshot = tmp_path / "snapshot.json"
    harness = tmp_path / "harness.js"
    snapshot.write_text(snapshot_json(run), encoding="utf-8")
    harness.write_text(HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        subprocess.run(
            [NODE, "--check", str(app)], check=True, timeout=60
        )
        completed = subprocess.run(
            [NODE, str(harness), str(app), str(snapshot), str(tmp_path)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
        assert completed.returncode == 0, completed.stderr
    return Harness(run, json.loads(completed.stdout), tmp_path)


def run_view(tmp_path: Path) -> dict:
    """Run the reusable DOM-facing view against a tiny Node DOM stub."""
    harness = tmp_path / "view-harness.js"
    harness.write_text(VIEW_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        subprocess.run([NODE, "--check", str(app)], check=True, timeout=60)
        completed = subprocess.run(
            [NODE, str(harness), str(app)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
        assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


@pytest.fixture(scope="module")
def plain(tmp_path_factory):
    return run_shared(tmp_path_factory.mktemp("plain"))


@pytest.fixture(scope="module")
def hostile(tmp_path_factory):
    return run_shared(tmp_path_factory.mktemp("hostile"), hostile_report)


def test_create_view_contract_under_a_small_node_dom_stub(tmp_path):
    result = run_view(tmp_path)
    assert result == {
        "hasHeader": True,
        "hasDetails": True,
        "hostileIsText": True,
        "callbackState": True,
        "selected": "weapons",
        "optionCount": 2,
    }


def test_kept_items_requires_an_active_set_like_input(plain):
    assert plain.results["persistedVetoContract"] == {
        "absentRejected": True,
        "arrayRejected": True,
        "objectRejected": True,
        "absentRejectedForEmptyItems": True,
    }
    assert plain.results["persistedVeto"]["excludesApprovedId"]


def test_packaged_presentation_resource_has_no_manifest_adapter():
    resource = (
        Path(__file__).parents[1] / "src" / "vault_cleaner" / "ui" / "review_ui.js"
    ).read_text(encoding="utf-8")
    static_only_surface = (
        "loadAutosave", "saveAutosave", "localStorage",
        "MANIFEST_SCHEMA_VERSION", "VERDICTS", "STORAGE_PREFIX", "MAX_TEXT",
        "MANIFEST_KEYS", "SNAPSHOT_KEYS", "DECISION_KEYS",
        "buildManifest", "clip", "manifestJson", "exportManifest",
        "offerDownload", "applyImport", "renderHandoff", "readManifest",
        "readManifestText", "readManifestBytes", "readPastedManifest",
        "decodeManifestBytes", "fractionalNumberError", "fail",
        "unknownKeyError", "textError", "versionError",
        "window",
    )
    constants = {
        "MANIFEST_SCHEMA_VERSION", "VERDICTS", "STORAGE_PREFIX", "MAX_TEXT",
        "MANIFEST_KEYS", "SNAPSHOT_KEYS", "DECISION_KEYS",
    }
    functions = {
        "loadAutosave", "saveAutosave", "buildManifest", "clip", "manifestJson",
        "exportManifest", "offerDownload", "applyImport", "renderHandoff",
        "readManifest", "readManifestText", "readManifestBytes", "readPastedManifest",
        "decodeManifestBytes", "fractionalNumberError", "fail", "unknownKeyError",
        "textError", "versionError",
    }
    assert set(static_only_surface) == constants | functions | {"localStorage", "window"}

    # A presentation resource may discuss failure or clipping in prose, so a
    # bare substring check is too broad. SCREAMING_CASE constants are simple
    # identifiers: any word-boundary use would import the temporary adapter,
    # including ordinary reads and member access. Generic functions and
    # browser globals retain syntactic guards so prose and longer identifiers
    # such as "clipboard" remain accepted. Keep the complete issue-listed
    # surface above so adding a temporary-only name cannot silently shrink this
    # guard.
    patterns_by_name = {}
    for name in constants:
        patterns_by_name[name] = (rf"\b{re.escape(name)}\b",)
    for name in functions:
        escaped = re.escape(name)
        patterns_by_name[name] = (
            rf"(?m)^\s*function\s+{escaped}\s*\(",
            rf"\b{escaped}\s*\(",
            rf"(?:^|[{{,])\s*{escaped}\s*:",
        )
    patterns_by_name["window"] = (r"\bwindow\s*(?:\.|\[)",)
    patterns_by_name["localStorage"] = (r"\blocalStorage\s*\.",)
    adapter = files("vault_cleaner.ui").joinpath("review_static.js").read_text(
        encoding="utf-8"
    )
    patterns = [pattern for group in patterns_by_name.values() for pattern in group]
    assert not any(re.search(pattern, "fail loudly; clipboard") for pattern in patterns)
    constant_sentinels = {
        "var limit = MAX_TEXT;": "MAX_TEXT",
        "VERDICTS.indexOf(v)": "VERDICTS",
        "return value <= MAX_TEXT ? value : 0;": "MAX_TEXT",
    }
    for source, name in constant_sentinels.items():
        assert any(
            re.search(pattern, source) for pattern in patterns_by_name[name]
        ), (name, source)
    for name, name_patterns in patterns_by_name.items():
        assert any(re.search(pattern, adapter) for pattern in name_patterns), name
        assert not any(re.search(pattern, resource) for pattern in name_patterns), name


def test_packaged_sources_cannot_truncate_their_html_script_or_hide_controls():
    root = Path(__file__).parents[1] / "src" / "vault_cleaner" / "ui"
    invisible = {"Cf", "Cc", "Zl", "Zp"}
    for path in sorted(root.iterdir()):
        if path.suffix not in {".css", ".js"}:
            continue
        source = path.read_bytes().decode("utf-8")
        assert not re.search(r"</script", source, re.IGNORECASE), path
        assert "<!--" not in source and "-->" not in source, path
        assert all(
            char in "\n\t" or unicodedata.category(char) not in invisible
            for char in source
        ), path


def test_every_decision_becomes_an_item(plain):
    decisions = proposals(plain.run)
    assert plain.results["itemCount"] == len(decisions)
    assert sorted(plain.results["ids"]) == sorted(decision.id for decision in decisions)


def test_ids_and_hashes_stay_strings_in_the_browser(plain, hostile):
    assert plain.results["idsAndHashesAreStrings"]
    assert hostile.results["idsAndHashesAreStrings"]


def test_a_numeric_id_in_a_snapshot_is_refused_not_coerced(tmp_path):
    """Numbers have already lost precision by the time JSON.parse returns."""
    script = tmp_path / "numeric.js"
    script.write_text(
        'var api = require(process.argv[2]);\n'
        'try {\n'
        '  api.itemsFromSnapshot({ sections: [{ kind: "weapons", decisions: [\n'
        '    { id: 6917529027641981542, hash: "500" }\n'
        '  ] }] });\n'
        '  process.stdout.write("ACCEPTED");\n'
        '} catch (e) { process.stdout.write(e.message); }\n',
        encoding="utf-8",
    )
    with as_file(files("vault_cleaner.ui").joinpath("review_ui.js")) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=True, timeout=60,
        )
    assert "must be a JSON string, not number" in completed.stdout


def test_grouping_matches_the_terminal_summary_exactly(plain):
    expected = [
        line for line in summarize(plain.run.summary_sections()).splitlines()
        if line.startswith(("JUNK ", "REVIEW "))
    ]
    assert plain.results["groupLabels"] == expected


def test_action_counts_match_the_run(plain):
    decisions = proposals(plain.run)
    assert plain.results["actionCounts"] == {
        "total": len(decisions),
        "junk": sum(decision.action == "junk" for decision in decisions),
        "review": sum(decision.action == "review" for decision in decisions),
    }


def test_count_by_kind_covers_every_section(plain):
    by_kind = {entry["value"]: entry["count"] for entry in plain.results["counts"]["byKind"]}
    assert by_kind == {
        section.kind: len(section.decisions)
        for section in plain.run.sections
        if section.decisions
    }


def test_ids_sort_numerically_without_going_through_number(hostile):
    precision = hostile.results["precision"]
    assert precision["compare"] == 1
    assert precision["numberWouldTie"]
    assert precision["shorterFirst"] == -1
    assert precision["ordered"] == [
        "9", "10", "18446744073709551614", "18446744073709551615"
    ]


def test_sorting_by_id_is_a_reversible_total_order(plain):
    ascending = plain.results["sortedById"]
    assert ascending == sorted(ascending, key=int)
    assert plain.results["sortedByIdDesc"] == list(reversed(ascending))


def test_an_unknown_sort_field_falls_back_to_name(plain):
    assert plain.results["unknownSortFieldFallsBackToName"]


def test_filters_select_the_same_items_the_run_would(plain):
    decisions = {decision.id: decision for decision in proposals(plain.run)}
    filters = plain.results["filters"]
    assert set(filters["junk"]) == {
        item_id for item_id, decision in decisions.items() if decision.action == "junk"
    }
    assert set(filters["weaponsJunk"]) == {
        item_id for item_id, decision in decisions.items()
        if decision.action == "junk" and decision.kind == "weapons"
    }
    assert set(filters["protectedOnly"]) == {
        item_id for item_id, decision in decisions.items()
        if decision.protection_level
    }
    assert set(filters["soft"]) == {
        item_id for item_id, decision in decisions.items()
        if decision.protection_level == "soft"
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


def test_a_veto_removes_exactly_one_proposal_from_the_kept_set(plain):
    counts = plain.results["counts"]
    assert counts["kept"] == plain.results["itemCount"] - 1
    assert counts["keptExcludesVetoed"]
    assert counts["review"] == {
        "approved": 1, "vetoed": 1,
        "unreviewed": plain.results["itemCount"] - 2,
    }


def test_kept_counts_mirror_python_apply_vetoes(plain):
    vetoed = plain.results["ids"][0]
    kept = apply_vetoes(plain.run, frozenset({vetoed}))
    assert plain.results["counts"]["keptActions"] == {
        "total": len(kept),
        "junk": sum(decision.action == "junk" for decision in kept),
        "review": sum(decision.action == "review" for decision in kept),
    }


def test_active_persisted_veto_ids_are_applied_by_kept_items(plain):
    persisted = plain.results["persistedVeto"]
    assert persisted["excludesVetoedId"]
    assert persisted["excludesApprovedId"]
    assert len(persisted["kept"]) == plain.results["itemCount"] - 2


def test_hostile_names_are_data_not_executable_source(hostile):
    names = hostile.results["hostileNames"]
    assert any("</script>" in name or "<img" in name for name in names)


def test_a_prototype_shaped_item_name_is_counted_not_absorbed(hostile):
    safety = hostile.results["prototypeSafety"]
    names = dict(safety["names"])
    assert names.get("__proto__") == 1
    assert safety["objectPrototypeClean"]


def test_unset_and_garbage_verdicts_read_as_unreviewed(plain):
    assert plain.results["verdictOf"] == {
        "unset": "", "garbageIgnored": "", "set": "vetoed"
    }


def test_static_artifact_inlines_exact_packaged_resource_bytes():
    html = render_review_html(build_report())
    app = html.split('<script id="vc-app">', 1)[1].split("</script>", 1)[0]
    style = html.split("<style>", 1)[1].split("</style>", 1)[0]
    css = files("vault_cleaner.ui").joinpath("review.css").read_bytes()
    shared = files("vault_cleaner.ui").joinpath("review_ui.js").read_bytes()
    adapter = files("vault_cleaner.ui").joinpath("review_static.js").read_bytes()
    assert style.encode("utf-8") == css
    app_bytes = app.encode("utf-8")
    assert app_bytes.startswith(shared)
    assert app_bytes[len(shared) :] == adapter
