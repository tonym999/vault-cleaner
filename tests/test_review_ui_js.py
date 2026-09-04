"""Exercise the packaged, manifest-free presentation resource under node."""

import json
import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

import pytest
from test_review import build_report, proposals

from vault_cleaner.report import summarize
from vault_cleaner.report_run import run_report, snapshot_json
from vault_cleaner.review import apply_vetoes

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


FIXTURES = Path(__file__).parent / "fixtures"
HOSTILE = FIXTURES / "weapons_hostile.csv"


def hostile_report():
    """A run whose every item name is shaped like an injection attempt."""
    return run_report(
        config_path="nonexistent.toml",
        weapons_path=HOSTILE,
        armor_path=FIXTURES / "does-not-exist.csv",
        ghosts_path=FIXTURES / "does-not-exist.csv",
        no_wishlists=True,
    )


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
  hostileNotes: items.map(function (item) { return item.note; }),
  classFacets: items.map(function (item) { return item.classFacet; }),
  guardianClasses: items.map(function (item) { return item.guardianClass; }),
  locations: items.map(function (item) { return item.location; }),
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
    byClass: ids(api.filterItems(items, { classFacet: first.classFacet })),
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
var fs = require("fs");
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
    kind: "weapons", location: "Titan", guardianClass: "", classFacet: "weapons",
    action: "junk", reason: "dupe-lower",
    protectionLevel: "", protectionReason: "", tag: "junk", note: "#vc-junk",
    keptId: "9", originalTag: "", originalNotes: "", locked: false,
    equipped: false, inLoadout: false,
    candidateTuningModSlot: "Melee", selectedTuningModSlot: "Grenade",
    tuningModSlot: "Candidate: Melee · Selected: Grenade",
    armor: {
      slot: "helmet", equippable: true, best_archetype: "Melee-primary",
      score: 112, base_score: 110, set_bonus: 2, rank: 1, group_size: 2,
      stats: { Mobility: 12, Resilience: 30 }
    }
  },
  {
    id: "9", hash: "901", name: "Keep roll", kind: "weapons",
    location: "Titan", guardianClass: "", classFacet: "weapons",
    action: "review", reason: "wishlist", protectionLevel: "soft",
    protectionReason: "locked", tag: "", note: "#vc-review", keptId: "",
    originalTag: "", originalNotes: "", locked: true, equipped: false,
    inLoadout: false, armor: null
  }
];
var snapshotItems = process.argv[3]
  ? api.itemsFromSnapshot(JSON.parse(fs.readFileSync(process.argv[3], "utf8")))
  : [];
var unicodeItem = snapshotItems.filter(function (item) {
  return item.name.indexOf("\u202e") !== -1 &&
    item.note.indexOf("\u2028") !== -1 && item.note.indexOf("\u2029") !== -1;
})[0] || null;
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
var unicodeTable = null;
if (unicodeItem) {
  state.expanded[unicodeItem.id] = true;
  unicodeTable = view.table([unicodeItem]);
}
var header = view.headerRow();
if (header.textContent.indexOf("Verdict") === -1) fail("Verdict header is missing");
if (header.textContent.indexOf("Class") === -1 ||
    header.textContent.indexOf("Location") === -1 ||
    header.textContent.indexOf("Tuning Mod Slot") === -1 ||
    header.textContent.indexOf("Owner") !== -1) fail("Class/Location headers are incorrect");
if (table.textContent.indexOf("Armor scoring") === -1 ||
    table.textContent.indexOf(hostile) === -1 ||
    table.textContent.indexOf("Candidate: Melee · Selected: Grenade") === -1 ||
    hasTag(table, "img")) {
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
state.rows[items[0].id].clear.dispatch("click");
if (JSON.stringify(toggles) !== JSON.stringify([
  [items[0].id, "approved"], [items[0].id, ""]
])) fail("clear callback is not wired");
var originalRow = state.rows[items[0].id].tr;
state.verdicts[items[0].id] = "approved";
if (!view.paintRow(items[0].id) || state.rows[items[0].id].tr !== originalRow ||
    state.rows[items[0].id].approve.getAttribute("aria-pressed") !== "true") {
  fail("paintRow must update an existing row in place");
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
var readOnlyState = {
  sort: { field: "name", direction: "asc" },
  expanded: Object.create(null), rows: Object.create(null),
  verdicts: Object.create(null)
};
var readOnlyView = api.createView({
  document: document, state: readOnlyState, items: [items[0]],
  columns: api.COLUMNS, readOnly: true,
  verdictText: function () { return "read-only verdict"; }
});
readOnlyView.table([items[0]]);
if (readOnlyState.rows[items[0].id].approve !== null ||
    readOnlyState.rows[items[0].id].veto !== null) {
  fail("read-only rows must expose null verdict button handles");
}
var output = {
  hasHeader: header.textContent.indexOf("Verdict") !== -1,
  hasClassAndLocation: header.textContent.indexOf("Class") !== -1 &&
    header.textContent.indexOf("Location") !== -1 &&
    header.textContent.indexOf("Owner") === -1,
  hasDetails: table.textContent.indexOf("Armor scoring") !== -1,
  hasTuningColumn: header.textContent.indexOf("Tuning Mod Slot") !== -1 &&
    table.textContent.indexOf("Candidate: Melee · Selected: Grenade") !== -1,
  hostileIsText: inert.textContent === hostile && !hasTag(table, "img"),
  callbackState: toggles.length === 2 && renders === 2,
  paintedInPlace: state.rows[items[0].id].tr === originalRow,
  selected: select.value,
  optionCount: oldStyle.length,
  readOnlyNullHandles: readOnlyState.rows[items[0].id].approve === null &&
    readOnlyState.rows[items[0].id].veto === null
};
if (unicodeTable) {
  output.unicodeNameRendered = unicodeTable.textContent.indexOf("\u202e") !== -1;
  output.unicodeNoteRendered = unicodeTable.textContent.indexOf("\u2028") !== -1 &&
    unicodeTable.textContent.indexOf("\u2029") !== -1;
}
process.stdout.write(JSON.stringify(output));
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


def run_view(tmp_path: Path, snapshot: Path | None = None) -> dict:
    """Run the reusable DOM-facing view against a tiny Node DOM stub."""
    harness = tmp_path / "view-harness.js"
    harness.write_text(VIEW_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        subprocess.run([NODE, "--check", str(app)], check=True, timeout=60)
        command = [NODE, str(harness), str(app)]
        if snapshot is not None:
            command.append(str(snapshot))
        completed = subprocess.run(
            command,
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
        "hasClassAndLocation": True,
        "hasDetails": True,
        "hasTuningColumn": True,
        "hostileIsText": True,
        "callbackState": True,
        "selected": "weapons",
        "optionCount": 2,
        "readOnlyNullHandles": True,
        "paintedInPlace": True,
    }


def test_hostile_unicode_values_render_as_text(tmp_path, hostile):
    result = run_view(tmp_path, hostile.workdir / "snapshot.json")

    assert result["unicodeNameRendered"]
    assert result["unicodeNoteRendered"]


def test_kept_items_requires_an_active_set_like_input(plain):
    assert plain.results["persistedVetoContract"] == {
        "absentRejected": True,
        "arrayRejected": True,
        "objectRejected": True,
        "absentRejectedForEmptyItems": True,
    }
    assert plain.results["persistedVeto"]["excludesApprovedId"]


def test_packaged_presentation_resources_are_free_of_the_static_adapter():
    retired_symbols = (
        "read" + "Manifest", "read" + "PastedManifest",
        "decode" + "ManifestBytes",
        "fractional" + "NumberError", "build" + "Manifest",
        "export" + "Manifest", "manifest" + "Json",
        "offer" + "Download", "apply" + "Import",
        "render" + "Handoff", "load" + "Autosave",
        "save" + "Autosave", "local" + "Storage",
        "MANIFEST" + "_KEYS", "SNAPSHOT" + "_KEYS",
        "DECISION" + "_KEYS",
    )
    # This negative regression guard uses substring matching. The readManifest
    # substring deliberately covers readManifestText/readManifestBytes, while
    # readPastedManifest has its own entry because the Pasted infix breaks
    # that substring. No retired production/static-adapter corpus is retained;
    # the synthetic reader list below pins these four entry points.
    assert all(
        any(symbol in reader for symbol in retired_symbols)
        for reader in (
            "read" + "Manifest", "read" + "ManifestText",
            "read" + "ManifestBytes", "read" + "PastedManifest",
        )
    )
    for name in ("review_ui.js", "review_server.js"):
        resource = files("vault_cleaner.ui").joinpath(name)
        with as_file(resource) as path:
            source = path.read_text(encoding="utf-8")
        assert not any(symbol in source for symbol in retired_symbols), name


def test_packaged_sources_have_no_invisible_or_control_characters():
    invisible = {"Cf", "Cc", "Zl", "Zp"}
    resources = sorted(
        (
            resource
            for resource in files("vault_cleaner.ui").iterdir()
            if resource.name.endswith((".css", ".js"))
        ),
        key=lambda resource: resource.name,
    )
    for resource in resources:
        with as_file(resource) as path:
            source = path.read_bytes().decode("utf-8")
        assert all(
            char in "\n\t" or unicodedata.category(char) not in invisible
            for char in source
        ), resource.name


def test_every_decision_becomes_an_item(plain):
    decisions = proposals(plain.run)
    assert plain.results["itemCount"] == len(decisions)
    assert sorted(plain.results["ids"]) == sorted(decision.id for decision in decisions)


def test_class_and_location_axes_are_mapped_independently(plain):
    decisions = proposals(plain.run)
    first_class = decisions[0].guardian_class or decisions[0].kind
    assert set(plain.results["filters"]["byClass"]) == {
        decision.id for decision in decisions
        if (decision.guardian_class or decision.kind) == first_class
    }
    for item, decision in zip(plain.results["classFacets"], decisions):
        assert item == (decision.guardian_class or decision.kind)
    assert all(
        item == decision.guardian_class
        for item, decision in zip(plain.results["guardianClasses"], decisions)
    )
    assert all(
        item == decision.location
        for item, decision in zip(plain.results["locations"], decisions)
    )


def test_unknown_and_empty_guardian_classes_use_honest_presentation_values(tmp_path):
    snapshot = tmp_path / "class-values.json"
    snapshot.write_text(json.dumps({
        "sections": [{"kind": "armor", "decisions": [
            {"id": "1", "hash": "2", "kind": "armor", "guardian_class": "Spectre", "location": "Vault"},
            {"id": "3", "hash": "4", "kind": "ghosts", "guardian_class": "", "location": "Titan(550)"},
        ]}],
    }), encoding="utf-8")
    script = tmp_path / "class-values.js"
    script.write_text(
        'var fs = require("fs");\n'
        'var api = require(process.argv[2]);\n'
        'var snapshot = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));\n'
        'var items = api.itemsFromSnapshot(snapshot);\n'
        'process.stdout.write(JSON.stringify(items.map(function (item) {\n'
        '  return [item.guardianClass, item.classFacet, item.location];\n'
        '})));\n',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app), str(snapshot)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [
        ["Spectre", "Spectre", "Vault"],
        ["", "ghosts", "Titan(550)"],
    ]


def test_exact_groups_are_authoritative_and_filter_as_whole_groups(tmp_path):
    snapshot = tmp_path / "exact-groups.json"
    snapshot.write_text(json.dumps({
        "sections": [{"kind": "armor", "decisions": [
            {"id": "loser", "hash": "18446744073709551615", "action": "junk"},
        ], "armor": {
            "exact_duplicate_groups": [
                {
                    "group_kind": "exact_duplicate", "group_id": "__proto__",
                    "hash": "18446744073709551615", "name": "Gunner plate",
                    "type": "Chest Armor", "guardian_class": "Hunter",
                    "item_archetype": "Gunner", "tier": 5,
                    "stats": {"weapons": 30, "health": 25, "class": 20,
                              "grenade": 0, "super": 0, "melee": 0},
                    "tuning_mod_slot": "Weapons", "seasonal_mod": "Solar",
                    "holofoil": "false", "spirit_signature": [],
                    "preferred_survivor_id": "0009223372036854775808",
                    "members": [
                        {"id": "0009223372036854775808", "location": "Vault",
                         "disposition": "preferred_survivor"},
                        {"id": "__proto__", "location": "Hunter(550)",
                         "disposition": "retained_protected"},
                        {"id": "loser", "location": "Vault",
                         "disposition": "proposed_junk", "proposal_action": "junk"},
                    ],
                },
                {
                    "group_kind": "exact_duplicate", "group_id": "second",
                    "hash": "700", "name": "Other plate", "type": "",
                    "guardian_class": "", "item_archetype": "",
                    "tier": 4, "stats": {"weapons": 10, "health": 10},
                    "tuning_mod_slot": "", "members": [
                        {"id": "other", "location": "Vault",
                         "disposition": "preferred_survivor"},
                    ],
                    "preferred_survivor_id": "other",
                },
            ]
        }}]
    }), encoding="utf-8")
    script = tmp_path / "exact-groups.js"
    script.write_text(
        'var fs = require("fs");\n'
        'var api = require(process.argv[2]);\n'
        'var snapshot = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));\n'
        'var groups = api.exactDuplicateGroupsFromSnapshot(snapshot);\n'
        'var stats = api.armorStatDisplay(groups[0]);\n'
        'var fallback = api.armorStatDisplay(groups[1]);\n'
        'process.stdout.write(JSON.stringify({\n'
        '  ids: groups.map(function (g) { return [g.groupId, g.hash, g.preferredSurvivorId, g.members.map(function (m) { return m.id; })]; }),\n'
        '  strings: typeof groups[0].groupId === "string" && typeof groups[0].hash === "string" && typeof groups[0].members[0].id === "string",\n'
    '  filtered: {name: api.filterArmorGroups(groups, {text: "gunner"}).length, id: api.filterArmorGroups(groups, {text: "loser"}).length, class: api.filterArmorGroups(groups, {guardianClass: "Hunter"}).length, blankClass: api.filterArmorGroups(groups, {guardianClass: "none/unknown"}).length, slot: api.filterArmorGroups(groups, {type: "none/unknown"}).length, archetype: api.filterArmorGroups(groups, {itemArchetype: "Gunner"}).length, blankArchetype: api.filterArmorGroups(groups, {itemArchetype: "none/unknown"}).length, tuning: api.filterArmorGroups(groups, {tuningModSlot: "none/unknown"}).length},\n'
    '  categories: {class: api.countArmorGroups(groups, "guardianClass"), type: api.countArmorGroups(groups, "type"), archetype: api.countArmorGroups(groups, "itemArchetype"), tuning: api.countArmorGroups(groups, "tuningModSlot")},\n'
        '  membersIntact: api.filterArmorGroups(groups, {text: "loser"})[0].members.length === 3,\n'
        '  roles: stats.rows.map(function (row) { return [row.role, row.name, row.value]; }),\n'
        '  zeroSummary: stats.zeroSummary,\n'
        '  fallback: fallback.tier5 === false && fallback.rows.length === 2,\n'
        '  prototypeClean: Object.prototype.polluted === undefined\n'
        '}));\n',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app), str(snapshot)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "ids": [
            ["__proto__", "18446744073709551615", "0009223372036854775808",
             ["0009223372036854775808", "__proto__", "loser"]],
            ["second", "700", "other", ["other"]],
        ],
        "strings": True,
        "filtered": {"name": 1, "id": 1, "class": 1, "blankClass": 1,
                     "slot": 1, "archetype": 1, "blankArchetype": 1, "tuning": 1},
        "categories": {
            "class": [{"value": "Hunter", "count": 1, "unit": "group"}, {"value": "none/unknown", "count": 1, "unit": "group"}],
            "type": [{"value": "Chest Armor", "count": 1, "unit": "group"}, {"value": "none/unknown", "count": 1, "unit": "group"}],
            "archetype": [{"value": "Gunner", "count": 1, "unit": "group"}, {"value": "none/unknown", "count": 1, "unit": "group"}],
            "tuning": [{"value": "none/unknown", "count": 1, "unit": "piece"}, {"value": "Weapons", "count": 3, "unit": "piece"}],
        },
        "membersIntact": True,
        "roles": [["Primary", "weapons", 30], ["Secondary", "health", 25],
                  ["Tertiary", "class", 20]],
        # Named zero stats, not a generic sentence (#131): every zero-value
        # base stat, in stats-object order, then the fixed " · 0 base" tail.
        "zeroSummary": "grenade · super · melee · 0 base",
        "fallback": True,
        "prototypeClean": True,
    }


def test_exact_group_projection_rejects_cross_group_ids_and_bad_proposals(tmp_path):
    script = tmp_path / "exact-group-validation.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function group(id, preferred, proposal) {
  return {group_kind: "exact_duplicate", group_id: id, hash: "h", name: "Armor",
    preferred_survivor_id: preferred, members: [
      {id: preferred, disposition: "preferred_survivor"},
      {id: proposal, disposition: "proposed_junk", proposal_action: "junk"}
    ]};
}
function snapshot(groups, sections) {
  return {sections: sections || [{kind: "armor", decisions: groups.map(function (unused, index) {
    return {id: "proposal" + index, hash: "h", action: "junk"};
  }), armor: {exact_duplicate_groups: groups}}]};
}
function rejects(value) {
  try { api.exactDuplicateGroupsFromSnapshot(value); return false; }
  catch (error) { return true; }
}
var duplicated = snapshot([group("g1", "same", "one"), group("g2", "same", "two")], [
  {kind: "armor", decisions: [
    {id: "one", hash: "h", action: "junk"}, {id: "two", hash: "h", action: "junk"}
  ], armor: {exact_duplicate_groups: [group("g1", "same", "one"), group("g2", "same", "two")]}}
]);
var crossSection = snapshot([{
  group_kind: "exact_duplicate", group_id: "cross", hash: "h",
  preferred_survivor_id: "survivor", members: [
    {id: "survivor", disposition: "preferred_survivor"}
  ]
}], [
  {kind: "weapons", decisions: [{id: "survivor", hash: "h", action: "junk"}]},
  {kind: "armor", decisions: [], armor: {exact_duplicate_groups: [{
    group_kind: "exact_duplicate", group_id: "cross", hash: "h",
    preferred_survivor_id: "survivor", members: [
      {id: "survivor", disposition: "preferred_survivor"}
    ]
  }]}}
]);
var wrongHash = snapshot([{
  group_kind: "exact_duplicate", group_id: "wrong", hash: "h",
  preferred_survivor_id: "survivor", members: [
    {id: "survivor", disposition: "preferred_survivor"}
  ]
}], [{kind: "armor", decisions: [
  {id: "survivor", hash: "different", action: "junk"}
], armor: {exact_duplicate_groups: [{
  group_kind: "exact_duplicate", group_id: "wrong", hash: "h",
  preferred_survivor_id: "survivor", members: [
    {id: "survivor", disposition: "preferred_survivor"}
  ]
}]}}]);
var valid = api.exactDuplicateGroupsFromSnapshot(snapshot([{
  group_kind: "exact_duplicate", group_id: "valid", hash: "h",
  preferred_survivor_id: "survivor", members: [
    {id: "survivor", disposition: "preferred_survivor"}
  ]
}], [{kind: "armor", decisions: [
  {id: "survivor", hash: "h", action: "junk", reason: "later score"}
], armor: {exact_duplicate_groups: [{
  group_kind: "exact_duplicate", group_id: "valid", hash: "h",
  preferred_survivor_id: "survivor", members: [
    {id: "survivor", disposition: "preferred_survivor"}
  ]
}]}}]));
process.stdout.write(JSON.stringify({crossGroup: rejects(duplicated), crossSection: rejects(crossSection),
  wrongHash: rejects(wrongHash), validLaterProposal: valid[0].members[0].currentProposalAction === "junk"}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "crossGroup": True,
        "crossSection": True,
        "wrongHash": True,
        "validLaterProposal": True,
    }


def test_exact_group_dom_uses_read_only_survivors_and_proposal_controls(tmp_path):
    script = tmp_path / "exact-group-dom.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function Node(tag, document) {
  this.tagName = tag.toUpperCase(); this.ownerDocument = document;
  this.children = []; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
}
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) { this.children.push(child); return child; };
Node.prototype.removeChild = function (child) { this.children.splice(this.children.indexOf(child), 1); return child; };
Node.prototype.setAttribute = function (key, value) { this.attributes[key] = String(value); };
Node.prototype.getAttribute = function (key) { return this.attributes[key] === undefined ? null : this.attributes[key]; };
Node.prototype.addEventListener = function (key, callback) { this.listeners[key] = callback; };
Node.prototype.click = function () { if (!this.disabled && this.listeners.click) this.listeners.click({target: this}); };
function Document() {}
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) { var node = new Node("#text", this); node.textContent = text; return node; };
function find(node, predicate) {
  if (predicate(node)) return node;
  for (var i = 0; i < node.children.length; i++) { var found = find(node.children[i], predicate); if (found) return found; }
  return null;
}
function count(node, predicate) {
  var total = predicate(node) ? 1 : 0;
  node.children.forEach(function (child) { total += count(child, predicate); });
  return total;
}
var state = {expanded: Object.create(null), rows: Object.create(null), duplicateRows: Object.create(null), verdicts: Object.create(null)};
var toggles = [];
var view = api.createView({document: new Document(), state: state,
  toggleVerdict: function (id, verdict) { toggles.push([id, verdict]); },
  verdictText: function (member, verdict) { return verdict || "Unreviewed"; }});
var group = api.exactDuplicateGroupsFromSnapshot({sections: [{kind: "armor", decisions: [
  {id: "proposal", hash: "h", action: "junk"}
], armor: {
  exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "g", hash: "h",
    name: "</script><img src=x onerror=alert(1)>", type: "Chest Armor",
    guardian_class: "Hunter", item_archetype: "</b><script>alert(1)</script>",
    tier: 5, stats: {weapons: 30, health: 25, class: 20, grenade: 0, super: 0, melee: 0},
    tuning_mod_slot: "</script><script>alert(1)</script>", seasonal_mod: "Solar",
    holofoil: "<img src=x onerror=alert(1)>",
    spirit_signature: ["</script><script>alert(1)</script>"],
    preferred_survivor_id: "survivor", members: [
      {id: "survivor", location: "<b onclick=alert(1)>Vault</b>", equipped: true, disposition: "preferred_survivor"},
      {id: "retained", location: "</b><script>alert(1)</script>", equipped: false, disposition: "retained_protected", protection_level: "hard"},
      {id: "proposal", location: "Vault", equipped: false, disposition: "proposed_junk", proposal_action: "junk"}
    ]}]
}}]})[0];
var article = view.armorGroup(group);
var proposal = state.duplicateRows.proposal[0];
var before = proposal.cell;
proposal.approve.click();
state.verdicts.proposal = "approved";
view.paintArmorMember("proposal");
proposal.veto.click();
proposal.clear.click();
var laterState = {expanded: Object.create(null), rows: Object.create(null), duplicateRows: Object.create(null), verdicts: Object.create(null)};
var laterView = api.createView({document: new Document(), state: laterState,
  verdictText: function (member, verdict) { return verdict || "Unreviewed"; }});
var laterGroup = api.exactDuplicateGroupsFromSnapshot({sections: [{kind: "armor", decisions: [
  {id: "survivor", hash: "h", action: "junk", reason: "later score"},
  {id: "proposal", hash: "h", action: "junk"}
], armor: {exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "later", hash: "h",
  name: "Later proposal", preferred_survivor_id: "survivor", members: [
    {id: "survivor", disposition: "preferred_survivor"},
    {id: "proposal", disposition: "proposed_junk", proposal_action: "junk"}
  ]}]}}]})[0];
var laterArticle = laterView.armorGroup(laterGroup);
var laterSurvivor = laterState.duplicateRows.survivor[0];
laterState.verdicts.survivor = "approved";
laterView.paintArmorMember("survivor");
var malformedState = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var malformedView = api.createView({document: new Document(), state: malformedState,
  verdictText: function () { return "Unreviewed"; }});
var malformedArticle = malformedView.armorGroup({
  groupKind: "exact_duplicate", groupId: "malformed", hash: "h", name: "Malformed",
  type: "Chest Armor", guardianClass: "Hunter", itemArchetype: "Gunner", tier: 5,
  stats: {}, tuningModSlot: "Weapons", seasonalMod: "", holofoil: "",
  spiritSignature: [], preferredSurvivorId: "bad", members: [
    {id: "bad", location: "Vault", disposition: "proposed_junk", proposalAction: ""}
  ]
});
var finalizedState = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var finalizedView = api.createView({document: new Document(), state: finalizedState,
  verdictDisabled: function () { return true; },
  verdictText: function () { return "Unreviewed"; }});
finalizedView.armorGroup(group);
var finalizedProposal = finalizedState.duplicateRows.proposal[0];
process.stdout.write(JSON.stringify({
  complete: article.textContent.indexOf("</script><img src=x onerror=alert(1)>") !== -1 &&
    article.textContent.indexOf("survivor") !== -1 && article.textContent.indexOf("retained") !== -1 &&
    article.textContent.indexOf("proposal") !== -1 && article.textContent.indexOf("Tuning Mod Slot") !== -1,
  hostileText: article.textContent.indexOf("</b><script>alert(1)</script>") !== -1 &&
    article.textContent.indexOf("<b onclick=alert(1)>Vault</b>") !== -1,
  inert: count(article, function (node) {
    return node.tagName === "IMG" || node.tagName === "SCRIPT" || node.tagName === "B";
  }) === 0,
  malformedReadOnly: count(malformedArticle, function (node) {
    return node.tagName === "BUTTON";
  }) === 0,
  finalizedDisabled: finalizedProposal.approve.disabled && finalizedProposal.veto.disabled &&
    finalizedProposal.clear.disabled,
  readOnly: count(state.duplicateRows.survivor[0].cell, function (node) { return node.tagName === "BUTTON"; }) === 0 &&
    count(state.duplicateRows.retained[0].cell, function (node) { return node.tagName === "BUTTON"; }) === 0,
  proposalControls: count(proposal.cell, function (node) { return node.tagName === "BUTTON"; }) === 3,
  callback: JSON.stringify(toggles) === JSON.stringify([["proposal", "approved"], ["proposal", "vetoed"], ["proposal", ""]]),
  repaintedInPlace: state.duplicateRows.proposal[0].cell === before && proposal.approve.getAttribute("aria-pressed") === "true",
  labels: article.textContent.indexOf("Preferred survivor") !== -1 && article.textContent.indexOf("Retained protected") !== -1 && article.textContent.indexOf("Proposed junk") !== -1,
  equipped: article.textContent.indexOf("Equipped") !== -1 && article.textContent.indexOf("Yes") !== -1 && article.textContent.indexOf("No") !== -1,
  laterProposalDisclosure: laterArticle.textContent.indexOf("Also proposed junk in Proposals") !== -1 &&
    laterArticle.textContent.indexOf("Current verdict: approved") !== -1 &&
    count(laterSurvivor.cell, function (node) { return node.tagName === "BUTTON"; }) === 0,
  laterProposalRemainsMutable: count(laterState.duplicateRows.proposal[0].cell, function (node) {
    return node.tagName === "BUTTON";
  }) === 3
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "complete": True,
        "hostileText": True,
        "inert": True,
        "malformedReadOnly": True,
        "finalizedDisabled": True,
        "readOnly": True,
        "proposalControls": True,
        "callback": True,
        "repaintedInPlace": True,
        "labels": True,
        "equipped": True,
        "laterProposalDisclosure": True,
        "laterProposalRemainsMutable": True,
    }


def test_items_map_structured_tuning_without_reading_note_text(tmp_path):
    snapshot = tmp_path / "tuning.json"
    snapshot.write_text(json.dumps({
        "sections": [{"kind": "armor", "decisions": [
            {
                "id": "1", "hash": "2", "name": "Plate",
                "candidate_tuning_mod_slot": "Melee",
                "selected_tuning_mod_slot": "Grenade",
                "note": "#vc-review: deliberately misleading text",
            },
            {
                "id": "3", "hash": "4", "name": "Unknown Plate",
                "candidate_tuning_mod_slot": "none/unknown",
                "selected_tuning_mod_slot": "none/unknown",
                "note": "#vc-review: stale tuning Health vs Super",
            },
            {
                "id": "5", "hash": "6", "name": "No Comparison",
                "candidate_tuning_mod_slot": None,
                "selected_tuning_mod_slot": None,
                "note": "#vc-review: unrelated",
            },
        ]}],
    }), encoding="utf-8")
    script = tmp_path / "tuning.js"
    script.write_text(
        'var fs = require("fs");\n'
        'var api = require(process.argv[2]);\n'
        'var snapshot = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));\n'
        'var items = api.itemsFromSnapshot(snapshot);\n'
        'process.stdout.write(JSON.stringify(items.map(function (item) {\n'
        '  return [item.candidateTuningModSlot, item.selectedTuningModSlot, item.tuningModSlot];\n'
        '})));\n',
        encoding="utf-8",
    )
    with as_file(files("vault_cleaner.ui").joinpath("review_ui.js")) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app), str(snapshot)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [
        ["Melee", "Grenade", "Candidate: Melee · Selected: Grenade"],
        ["none/unknown", "none/unknown", "Candidate: none/unknown · Selected: none/unknown"],
        [None, None, "—"],
    ]


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


def test_hostile_rtl_name_and_separator_note_reach_renderer(hostile):
    assert any("\u202e" in name and "\u202c" in name
               for name in hostile.results["hostileNames"])
    assert any("\u2028" in note and "\u2029" in note
               for note in hostile.results["hostileNotes"])


def test_a_prototype_shaped_item_name_is_counted_not_absorbed(hostile):
    safety = hostile.results["prototypeSafety"]
    names = dict(safety["names"])
    assert names.get("__proto__") == 1
    assert safety["objectPrototypeClean"]


def test_unset_and_garbage_verdicts_read_as_unreviewed(plain):
    assert plain.results["verdictOf"] == {
        "unset": "", "garbageIgnored": "", "set": "vetoed"
    }


def test_same_stat_projection_and_cross_kind_dom_overlap(tmp_path: Path):
    script = tmp_path / "same-stat.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function Node(tag, document) {
  this.tagName = tag.toUpperCase(); this.ownerDocument = document;
  this.children = []; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
}
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) { this.children.push(child); return child; };
Node.prototype.setAttribute = function (key, value) { this.attributes[key] = String(value); };
Node.prototype.getAttribute = function (key) { return this.attributes[key] === undefined ? null : this.attributes[key]; };
Node.prototype.addEventListener = function (key, callback) { this.listeners[key] = callback; };
Node.prototype.click = function () { if (!this.disabled && this.listeners.click) this.listeners.click({target: this}); };
function Document() {}
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) { var node = new Node("#text", this); node.textContent = text; return node; };
function count(node, predicate) {
  var total = predicate(node) ? 1 : 0;
  node.children.forEach(function (child) { total += count(child, predicate); });
  return total;
}
var sharedId = "0009223372036854775808";
var partnerId = "18446744073709551615";
function snapshot(exactGroups, sameGroups) { return {sections: [{kind: "armor", decisions: [
  {id: sharedId, hash: "18446744073709551615", action: "review", reason: "armor-similar to"},
  {id: "exact-loser", hash: "18446744073709551615", action: "junk", reason: "exact"}
], armor: {exact_duplicate_groups: exactGroups, same_stat_groups: sameGroups}}]}; }
function exact() { return {group_kind: "exact_duplicate", group_id: "exact-group",
  hash: "18446744073709551615", name: "Exact plate", type: "Chest Armor",
  guardian_class: "Hunter", item_archetype: "Gunner", tier: 5,
  stats: {weapons: 30, health: 25, class: 20, grenade: 0, super: 0, melee: 0},
  spirit_signature: [], preferred_survivor_id: sharedId, members: [
    {id: sharedId, location: "Vault", disposition: "preferred_survivor"},
    {id: "exact-loser", location: "Vault", disposition: "proposed_junk",
     proposal_action: "junk", protection_level: "soft", protection_reason: "locked"}
  ]}; }
function same() { return {group_kind: "same_stat", group_id: "__proto__",
  hash: "18446744073709551615", name: "<img src=x onerror=alert(1)>",
  type: "<img src=type>", guardian_class: "<img src=class>",
  item_archetype: "<img src=archetype>", tier: 5,
  stats: {weapons: 30, health: 25, class: 20, grenade: 0, super: 0, melee: 0},
  seasonal_mod: "<img src=group-seasonal>", holofoil: "<img src=group-holofoil>",
  spirit_signature: [], members: [
    {id: sharedId, location: "<img src=location>", tuning_stat: "<img src=tuning-stat>",
     tuning_mod_slot: "<img src=tuning-slot>", seasonal_mod: "Solar",
     holofoil: "false"},
    {id: "not-digit-id", location: "Vault", tuning_stat: "Health",
     tuning_mod_slot: "Health", seasonal_mod: "Arc", holofoil: "true",
     selected_partner_id: partnerId, protection_level: "soft",
     protection_reason: "locked"}
  ]}; }
var projected = api.armorGroupsFromSnapshot(snapshot([exact()], [same()]));
var state = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var toggles = [];
var view = api.createView({document: new Document(), state: state,
  toggleVerdict: function (id, verdict) { toggles.push([id, verdict]); },
  verdictText: function (member, verdict) { return verdict || "Unreviewed"; }});
var articles = view.armorGroups(projected);
var exactArticle = articles[0], sameArticle = articles[1];
// Two orientations register every member id twice per group it appears in,
// so sharedId (read-only in the exact group, proposal-capable in the
// same-stat group) now has four occurrences, not two. Assertions below walk
// the whole occurrence list rather than indexing a fixed position (#131).
var overlap = state.duplicateRows[sharedId];
var exactOccurrences = overlap.filter(function (o) { return o.group.groupKind === "exact_duplicate"; });
var sameOccurrences = overlap.filter(function (o) { return o.group.groupKind === "same_stat"; });
sameOccurrences[0].approve.click();
state.verdicts[sharedId] = "approved";
view.paintArmorMember(sharedId);
view.setVerdictControlsDisabled(true);
function hasClass(node, name) {
  return (String(node.className || "")).split(/\s+/).indexOf(name) !== -1;
}
function firstByClass(article, name) {
  var found = null;
  (function walk(n) {
    if (found) return;
    if (hasClass(n, name)) { found = n; return; }
    (n.children || []).forEach(walk);
  })(article);
  return found;
}
function rejects(value) {
  try { api.sameStatGroupsFromSnapshot(value); return false; }
  catch (error) { return true; }
}
function collect(node, predicate) {
  var result = [];
  (function walk(n) {
    if (predicate(n)) result.push(n);
    (n.children || []).forEach(walk);
  })(node);
  return result;
}
function colHeaders(article) {
  return collect(article, function (node) {
    return node.tagName === "TH" && node.getAttribute("scope") === "col";
  }).map(function (node) { return node.textContent; });
}
function columnCells(article, headerText) {
  var thead = collect(article, function (node) { return node.tagName === "THEAD"; })[0];
  if (!thead) return [];
  var headers = collect(thead, function (node) { return node.tagName === "TH"; });
  var colIndex = -1;
  for (var i = 0; i < headers.length; i++) {
    if (headers[i].textContent === headerText) {
      colIndex = i;
      break;
    }
  }
  if (colIndex === -1) return [];
  var tbody = collect(article, function (node) { return node.tagName === "TBODY"; })[0];
  if (!tbody) return [];
  var rows = collect(tbody, function (node) { return node.tagName === "TR"; });
  return rows.map(function (row) {
    return row.children[colIndex] ? row.children[colIndex].textContent : "";
  });
}
var exactHeaders = colHeaders(exactArticle);
var sameHeaders = colHeaders(sameArticle);
var exactProtectionCells = columnCells(exactArticle, "Protection");
var sameProtectionCells = columnCells(sameArticle, "Protection");
var singleGroupArticle = view.armorGroup({
  groupKind: "exact_duplicate", groupId: "single", hash: "h", name: "Single",
  type: "", guardianClass: "", itemArchetype: "", tier: 5, stats: {},
  tuningModSlot: "", spiritSignature: [],
  members: [{id: "m1", location: "Vault", disposition: "preferred_survivor"}]
});
var unproposedSameArticle = view.armorGroup({
  groupKind: "same_stat", groupId: "unprop", hash: "h", name: "Unproposed",
  type: "", guardianClass: "", itemArchetype: "", tier: 5, stats: {},
  spiritSignature: [],
  members: [
    {id: "u1", location: "Vault", tuningModSlot: "Weapons"},
    {id: "u2", location: "Vault", tuningModSlot: "Health"}
  ]
});
var sharedSameArticle = view.armorGroup({
  groupKind: "same_stat", groupId: "shared", hash: "h", name: "Shared",
  type: "", guardianClass: "", itemArchetype: "", tier: 5, stats: {},
  spiritSignature: [],
  members: [
    {id: "s1", location: "Vault", tuningModSlot: "Weapons", seasonalMod: "Solar", holofoil: "true"},
    {id: "s2", location: "Vault", tuningModSlot: "Health", seasonalMod: "Solar", holofoil: "true"}
  ]
});
var sharedSameHeaders = colHeaders(sharedSameArticle);
var readOnlySameState = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var readOnlySameView = api.createView({
  document: new Document(), state: readOnlySameState, readOnly: true,
  verdictText: function (member, verdict) { return verdict || "Unreviewed"; }
});
var readOnlySameArticle = readOnlySameView.armorGroup({
  groupKind: "same_stat", groupId: "readonly-same", hash: "h", name: "ReadOnlySame",
  type: "", guardianClass: "", itemArchetype: "", tier: 5, stats: {},
  spiritSignature: [],
  members: [
    {id: "ro1", location: "Vault", tuningModSlot: "Weapons", currentProposalAction: "junk"},
    {id: "ro2", location: "Vault", tuningModSlot: "Health"}
  ]
});
process.stdout.write(JSON.stringify({
  order: projected.map(function (group) { return group.groupKind; }),
  memberOrder: projected[1].members.map(function (member) { return member.id; }),
  strings: typeof projected[1].groupId === "string" && projected[1].groupId === "__proto__" &&
    typeof projected[1].hash === "string" && typeof projected[1].members[1].selectedPartnerId === "string",
  overlapArray: Array.isArray(overlap) && overlap.length === 4,
  exactReadOnly: exactOccurrences.length === 2 && exactOccurrences.every(function (o) {
    return o.approve === null && o.presentation.textContent.indexOf("Read-only") !== -1;
  }),
  sameRepainted: sameOccurrences.length === 2 && sameOccurrences.every(function (o) {
    return o.approve.getAttribute("aria-pressed") === "true" && o.approve.disabled;
  }),
  labels: sameArticle.textContent.indexOf("Same stats · review only") !== -1 &&
    sameArticle.textContent.indexOf("Tuning Mod Slot") !== -1 &&
    sameArticle.textContent.indexOf("<img src=tuning-slot>") !== -1,
  noExactDisposition: sameArticle.textContent.indexOf("Preferred survivor") === -1 &&
    sameArticle.textContent.indexOf("Proposed junk") === -1,
  seasonalAndHolofoil: sameArticle.textContent.indexOf("Seasonal Mod") !== -1 &&
    sameArticle.textContent.indexOf("Solar") !== -1 && sameArticle.textContent.indexOf("Arc") !== -1 &&
    sameArticle.textContent.indexOf("Holofoil") !== -1,
  noBogusGroupAxes: projected[1].seasonalMod === "" && projected[1].holofoil === "" &&
    sameArticle.textContent.indexOf("group-seasonal") === -1 &&
    sameArticle.textContent.indexOf("group-holofoil") === -1,
  // Two orientations double every proposal-capable member's controls (one
  // set per table), so the button count doubles too (#131).
  controls: count(exactArticle, function (node) { return node.tagName === "BUTTON"; }) === 6 &&
    count(sameArticle, function (node) { return node.tagName === "BUTTON"; }) === 6,
  filterAny: api.filterArmorGroups(projected, {tuningModSlot: "Health"}).length === 1,
  countsOnce: (function () {
    var counts = api.countArmorGroups(projected, "tuningModSlot");
    return counts.length === 3 && counts.every(function (entry) {
      return entry.unit === "piece";
    }) && counts.some(function (entry) { return entry.value === "none/unknown" && entry.count === 2; }) &&
      counts.some(function (entry) { return entry.value === "Health" && entry.count === 1; }) &&
      counts.some(function (entry) { return entry.value === "<img src=tuning-slot>" && entry.count === 1; });
  }()),
  hostileInert: count(sameArticle, function (node) { return node.tagName === "IMG"; }) === 0 &&
    sameArticle.textContent.indexOf("<img src=x onerror=alert(1)>") !== -1,
  prototypeClean: Object.prototype.polluted === undefined,
  callback: JSON.stringify(toggles) === JSON.stringify([[sharedId, "approved"]]),
  exactSubLine: exactArticle.textContent.indexOf("Exact") !== -1 &&
    exactArticle.textContent.indexOf("Exact duplicate group") === -1,
  exactNoEnumToken: exactArticle.textContent.indexOf("exact_duplicate") === -1 &&
    exactArticle.textContent.indexOf("_") === -1,
  sameSubLineUnchanged: sameArticle.textContent.indexOf(
    "Same stats · review only") !== -1,
  protectionHeaderPresent: exactHeaders.indexOf("Protection") !== -1 &&
    sameHeaders.indexOf("Protection") !== -1,
  noHardProtectionHeader: exactHeaders.indexOf("Hard protection") === -1 &&
    sameHeaders.indexOf("Hard protection") === -1,
  protectionCellsHonest: exactProtectionCells.length === 2 &&
    exactProtectionCells[0] === "—" &&
    exactProtectionCells[1] === "soft — locked" &&
    sameProtectionCells.length === 2 &&
    sameProtectionCells[0] === "—" &&
    sameProtectionCells[1] === "soft — locked",
  // Class-scoped, not positional: a header restructure must not silently
  // stop covering the piece count (#131 -- see review checklist item 11).
  exactPieces: firstByClass(exactArticle, "armor-group-pieces").textContent === "2 pieces",
  samePieces: firstByClass(sameArticle, "armor-group-pieces").textContent === "2 pieces",
  singularPiece: firstByClass(singleGroupArticle, "armor-group-pieces").textContent === "1 piece",
  sameBannerBothSentences: sameArticle.textContent.indexOf(
    "Base stats match but tuning differs, so this pass selects no survivor. Pieces below that already carry a proposal keep their verdict controls."
  ) !== -1,
  sameBannerUnconditionalOnly: unproposedSameArticle.textContent.indexOf(
    "Base stats match but tuning differs, so this pass selects no survivor."
  ) !== -1 && unproposedSameArticle.textContent.indexOf(
    "Pieces below that already carry a proposal keep their verdict controls."
  ) === -1,
  conditionalColumnsPresentWhenDiffer: sameHeaders.indexOf("Seasonal Mod") !== -1 &&
    sameHeaders.indexOf("Holofoil") !== -1 && sameHeaders.indexOf("Tuning Stat") === -1,
  conditionalColumnsAbsentWhenEqual: sharedSameHeaders.indexOf("Seasonal Mod") === -1 &&
    sharedSameHeaders.indexOf("Holofoil") === -1,
  facetUnits: api.countArmorGroups(projected, "tuningModSlot").every(function (e) { return e.unit === "piece"; }) &&
    api.countArmorGroups(projected, "type").every(function (e) { return e.unit === "group"; }),
  sameBannerPresentWhenReadOnly: readOnlySameArticle.textContent.indexOf(
    "Base stats match but tuning differs, so this pass selects no survivor. Pieces below that already carry a proposal keep their verdict controls."
  ) !== -1 && count(readOnlySameArticle, function (node) {
    return node.tagName === "BUTTON" && node.className === "approve";
  }) === 0,
  // Exact-group tuning banner suffix, both branches (#131 P2-1): N > 1 names
  // the count and the grouping reason; N === 1 (the untitled single-member
  // article built above) uses the singular sentence instead.
  tuningSuffixMultiplePieces: exactArticle.textContent.indexOf(
    "— identical across all 2 pieces, and part of why they are one group."
  ) !== -1,
  tuningSuffixSinglePiece: singleGroupArticle.textContent.indexOf(
    "— the only piece in this group."
  ) !== -1
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "order": ["exact_duplicate", "same_stat"],
        "memberOrder": ["0009223372036854775808", "not-digit-id"],
        "strings": True, "overlapArray": True, "exactReadOnly": True,
        "sameRepainted": True,
        "labels": True, "noExactDisposition": True,
        "seasonalAndHolofoil": True, "noBogusGroupAxes": True,
        "controls": True,
        "filterAny": True, "countsOnce": True,
        "hostileInert": True, "prototypeClean": True,
        "callback": True,
        "exactSubLine": True, "exactNoEnumToken": True,
        "sameSubLineUnchanged": True,
        "protectionHeaderPresent": True, "noHardProtectionHeader": True,
        "protectionCellsHonest": True,
        "exactPieces": True,
        "samePieces": True,
        "singularPiece": True,
        "sameBannerBothSentences": True,
        "sameBannerUnconditionalOnly": True,
        "conditionalColumnsPresentWhenDiffer": True,
        "conditionalColumnsAbsentWhenEqual": True,
        "facetUnits": True,
        "sameBannerPresentWhenReadOnly": True,
        "tuningSuffixMultiplePieces": True,
        "tuningSuffixSinglePiece": True,
    }


def test_same_stat_projection_trust_boundary_and_opaque_values(tmp_path: Path):
    script = tmp_path / "same-stat-validation.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function member(id) { return {id: id, location: "Vault"}; }
function group(id, members, kind) {
  var value = {group_id: id, hash: "18446744073709551615", name: "Plate",
    members: members};
  if (kind !== undefined) value.group_kind = kind;
  return value;
}
function snapshot(groups, decisions, sections) {
  return {sections: sections || [{kind: "armor", decisions: decisions || [], armor: {
    same_stat_groups: groups}}]};
}
function rejects(value) {
  try { api.sameStatGroupsFromSnapshot(value); return false; }
  catch (error) { return true; }
}
var missingKind = snapshot([group("missing", [member("a"), member("b")])]);
var oneMember = snapshot([group("one", [member("a")])]);
var duplicateGroups = snapshot([
  group("same", [member("a"), member("b")]),
  group("same", [member("c"), member("d")])
]);
var duplicateMembers = snapshot([
  group("first", [member("a"), member("b")]),
  group("second", [member("b"), member("c")])
]);
var wrongHash = snapshot([group("wrong", [member("wrong"), member("other")])], [
  {id: "wrong", hash: "different", action: "review"}
]);
var crossSection = snapshot([], [], [
  {kind: "armor", decisions: [], armor: {same_stat_groups: [
    group("cross", [member("cross"), member("other")])
  ]}},
  {kind: "weapons", decisions: [
    {id: "cross", hash: "18446744073709551615", action: "junk"}
  ]}
]);
var valid = group("__proto__", [
  member("0009223372036854775808"),
  {id: "not-digit-id", selected_partner_id: "00000000000000000001", location: "Vault"}
], "same_stat");
var projected = api.sameStatGroupsFromSnapshot(snapshot([valid]));
process.stdout.write(JSON.stringify({
  missingKindRejected: rejects(missingKind),
  oneMemberRejected: rejects(oneMember),
  duplicateGroupRejected: rejects(duplicateGroups),
  duplicateMemberRejected: rejects(duplicateMembers),
  wrongHashRejected: rejects(wrongHash),
  crossSectionRejected: rejects(crossSection),
  opaqueStrings: projected[0].groupId === "__proto__" &&
    typeof projected[0].groupId === "string" &&
    projected[0].members[0].id === "0009223372036854775808" &&
    typeof projected[0].members[0].id === "string" &&
    projected[0].members[1].id === "not-digit-id" &&
    projected[0].members[1].selectedPartnerId === "00000000000000000001" &&
    typeof projected[0].members[1].selectedPartnerId === "string",
  prototypeClean: Object.prototype.polluted === undefined &&
    ({}).__proto__ === Object.prototype
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "missingKindRejected": True, "oneMemberRejected": True,
        "duplicateGroupRejected": True, "duplicateMemberRejected": True,
        "wrongHashRejected": True, "crossSectionRejected": True,
        "opaqueStrings": True, "prototypeClean": True,
    }


def test_same_stat_renderer_preserves_unknown_tuning_distinction(tmp_path: Path):
    script = tmp_path / "same-stat-tuning-render.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function Node(tag, document) {
  this.tagName = tag.toUpperCase(); this.ownerDocument = document;
  this.children = []; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = "";
}
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) { this.children.push(child); return child; };
Node.prototype.setAttribute = function (key, value) { this.attributes[key] = String(value); };
Node.prototype.addEventListener = function (key, callback) { this.listeners[key] = callback; };
function Document() {}
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) { var node = new Node("#text", this); node.textContent = text; return node; };
var projected = api.sameStatGroupsFromSnapshot({
  sections: [{kind: "armor", decisions: [], armor: {
    same_stat_groups: [{group_kind: "same_stat", group_id: "tuning", hash: "h",
      name: "Tuning distinction", members: [
        {id: "empty", location: "Vault", tuning_stat: "", tuning_mod_slot: "none/unknown"},
        {id: "future", location: "Vault", tuning_stat: "future socket", tuning_mod_slot: "none/unknown"},
        {id: "known", location: "Vault", tuning_stat: "Weapons", tuning_mod_slot: "Weapons"}
      ]}]
  }}]
})[0];
var state = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var article = api.createView({document: new Document(), state: state}).armorGroup(projected);
function countExact(node, value) {
  var total = node._text === value ? 1 : 0;
  node.children.forEach(function (child) { total += countExact(child, value); });
  return total;
}
function tuningColumnCells(article, headerText) {
  function collectNodes(node, predicate) {
    var res = [];
    (function walk(n) {
      if (predicate(n)) res.push(n);
      (n.children || []).forEach(walk);
    })(node);
    return res;
  }
  var thead = collectNodes(article, function (node) { return node.tagName === "THEAD"; })[0];
  if (!thead) return [];
  var headers = collectNodes(thead, function (node) { return node.tagName === "TH"; });
  var colIndex = -1;
  for (var i = 0; i < headers.length; i++) {
    if (headers[i].textContent === headerText) {
      colIndex = i;
      break;
    }
  }
  if (colIndex === -1) return [];
  var tbody = collectNodes(article, function (node) { return node.tagName === "TBODY"; })[0];
  if (!tbody) return [];
  var rows = collectNodes(tbody, function (node) { return node.tagName === "TR"; });
  return rows.map(function (row) {
    return row.children[colIndex] ? row.children[colIndex].textContent : "";
  });
}
var rawCells = tuningColumnCells(article, "Tuning Stat");
process.stdout.write(JSON.stringify({
  rawRows: countExact(article, "Tuning Stat"),
  emptyVisible: article.textContent.indexOf("none/unknown") !== -1,
  futureRawVisible: rawCells.indexOf("future socket") !== -1,
  recognizedVisible: article.textContent.indexOf("Weapons") !== -1
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        # Two orientations each render their own "Tuning Stat" header (#131).
        "rawRows": 2, "emptyVisible": True, "futureRawVisible": True,
        "recognizedVisible": True,
    }


def test_cross_kind_group_ids_are_namespaced_only_in_rendered_dom(tmp_path: Path):
    script = tmp_path / "cross-kind-group-id.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function Node(tag, document) {
  this.tagName = tag.toUpperCase(); this.ownerDocument = document;
  this.children = []; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = "";
}
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) { this.children.push(child); return child; };
Node.prototype.setAttribute = function (key, value) { this.attributes[key] = String(value); };
Node.prototype.getAttribute = function (key) { return this.attributes[key] === undefined ? null : this.attributes[key]; };
Node.prototype.addEventListener = function (key, callback) { this.listeners[key] = callback; };
function Document() {}
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) { var node = new Node("#text", this); node.textContent = text; return node; };
var snapshot = {sections: [{kind: "armor", decisions: [], armor: {
  exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "collision", hash: "h",
    name: "Exact", preferred_survivor_id: "exact-survivor", members: [
      {id: "exact-survivor", disposition: "preferred_survivor"}
    ]}],
  same_stat_groups: [{group_kind: "same_stat", group_id: "collision", hash: "h",
    name: "Same", members: [
      {id: "same-one", location: "Vault"}, {id: "same-two", location: "Vault"}
    ]}]
}}]};
var groups = api.armorGroupsFromSnapshot(snapshot);
var state = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var view = api.createView({document: new Document(), state: state});
var articles = view.armorGroups(groups);
var rendered = articles.map(function (article) {
  return [article.getAttribute("data-group-id"), article.getAttribute("data-group-kind")];
});
process.stdout.write(JSON.stringify({
  sourceIds: groups.map(function (group) { return group.groupId; }),
  rendered: rendered,
  distinct: rendered[0][0] !== rendered[1][0],
  bothAddressable: rendered.filter(function (entry) {
    return entry[0] === "exact_duplicate:collision" || entry[0] === "same_stat:collision";
  }).length === 2
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "sourceIds": ["collision", "collision"],
        "rendered": [
            ["exact_duplicate:collision", "exact_duplicate"],
            ["same_stat:collision", "same_stat"],
        ],
        "distinct": True, "bothAddressable": True,
    }


def test_cross_kind_member_ids_and_verdict_labels_are_namespaced_in_rendered_dom(
    tmp_path: Path,
):
    script = tmp_path / "cross-kind-member-id.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function Node(tag, document) {
  this.tagName = tag.toUpperCase(); this.ownerDocument = document;
  this.children = []; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
}
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) { this.children.push(child); return child; };
Node.prototype.setAttribute = function (key, value) { this.attributes[key] = String(value); };
Node.prototype.getAttribute = function (key) {
  return this.attributes[key] === undefined ? null : this.attributes[key];
};
Node.prototype.addEventListener = function (key, callback) { this.listeners[key] = callback; };
Node.prototype.click = function () {
  if (!this.disabled && this.listeners.click) this.listeners.click({target: this});
};
function Document() {}
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
var snapshot = {sections: [{kind: "armor", decisions: [
  {id: "shared", hash: "h", action: "junk", reason: "exact"}
], armor: {
  exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "exact",
    hash: "h", name: "Exact", preferred_survivor_id: "survivor", members: [
      {id: "survivor", disposition: "preferred_survivor"},
      {id: "shared", disposition: "proposed_junk", proposal_action: "junk"}
    ]}],
  same_stat_groups: [{group_kind: "same_stat", group_id: "same", hash: "h",
    name: "Same", members: [
      {id: "shared", proposal_action: "junk"}, {id: "other"}
    ]}]
}}]};
var groups = api.armorGroupsFromSnapshot(snapshot);
var state = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var view = api.createView({document: new Document(), state: state});
view.armorGroups(groups);
// "shared" is a member of both groups, and each group renders two
// orientations, so it now has four registered occurrences: two per group,
// identical to each other and distinct from the other group's (#131).
var overlap = state.duplicateRows.shared;
var byIdentity = {};
overlap.forEach(function (row) {
  var identity = row.cell.getAttribute("data-member-id");
  (byIdentity[identity] || (byIdentity[identity] = [])).push(row);
});
var identityKeys = Object.keys(byIdentity).sort();
var labelsFor = function (row) {
  return [row.approve.getAttribute("aria-label"), row.veto.getAttribute("aria-label"),
    row.clear.getAttribute("aria-label")];
};
process.stdout.write(JSON.stringify({
  sourceId: overlap[0].member.id,
  occurrenceCount: overlap.length,
  identityKeys: identityKeys,
  countPerIdentity: identityKeys.map(function (key) { return byIdentity[key].length; }),
  labelsConsistentWithinIdentity: identityKeys.every(function (key) {
    var rows = byIdentity[key];
    var first = JSON.stringify(labelsFor(rows[0]));
    return rows.every(function (row) { return JSON.stringify(labelsFor(row)) === first; });
  }),
  distinctLabelsAcrossIdentity: JSON.stringify(labelsFor(byIdentity[identityKeys[0]][0])) !==
    JSON.stringify(labelsFor(byIdentity[identityKeys[1]][0])),
  labels: [labelsFor(byIdentity[identityKeys[0]][0]), labelsFor(byIdentity[identityKeys[1]][0])],
  rawRegistryKey: Object.prototype.hasOwnProperty.call(state.duplicateRows, "shared")
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "sourceId": "shared",
        "occurrenceCount": 4,
        "identityKeys": ["exact_duplicate:shared", "same_stat:shared"],
        "countPerIdentity": [2, 2],
        "labelsConsistentWithinIdentity": True,
        "distinctLabelsAcrossIdentity": True,
        "labels": [
            [
                "approve exact-duplicate armor member id shared",
                "veto exact-duplicate armor member id shared",
                "unset verdict for exact-duplicate armor member id shared",
            ],
            [
                "approve same-stat armor member id shared",
                "veto same-stat armor member id shared",
                "unset verdict for same-stat armor member id shared",
            ],
        ],
        "rawRegistryKey": True,
    }


def test_difference_only_rows_and_identical_axes_line(tmp_path: Path):
    """An axis identical across members is a row nowhere and named once (#131).

    A row-table axis label is present iff a same-value axis (differs); an
    axis that is uniform across every member is absent from both matrix
    orientations and restated, once per group, in the muted
    ``p.armor-identical-axes`` line -- so the read-only protected/mutable
    context a suppressed row would have carried is never simply lost.
    """
    script = tmp_path / "difference-only.js"
    script.write_text(
        r'''
"use strict";
var api = require(process.argv[2]);
function Node(tag, document) {
  this.tagName = tag.toUpperCase(); this.ownerDocument = document;
  this.children = []; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
}
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) { this.children.push(child); return child; };
Node.prototype.setAttribute = function (key, value) { this.attributes[key] = String(value); };
Node.prototype.getAttribute = function (key) { return this.attributes[key] === undefined ? null : this.attributes[key]; };
Node.prototype.addEventListener = function (key, callback) { this.listeners[key] = callback; };
function Document() {}
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) { var node = new Node("#text", this); node.textContent = text; return node; };
function collect(node, predicate) {
  var result = [];
  (function walk(n) {
    if (predicate(n)) result.push(n);
    (n.children || []).forEach(walk);
  })(node);
  return result;
}
function hasClass(node, name) {
  return (String(node.className || "")).split(/\s+/).indexOf(name) !== -1;
}
var group = {
  groupKind: "same_stat", groupId: "diff-only", hash: "h", name: "Diff Only Plate",
  type: "Chest Armor", guardianClass: "Titan", itemArchetype: "Reaver", tier: 5,
  stats: {}, spiritSignature: [], members: [
    {id: "m1", location: "Vault", protectionLevel: "hard", protectionReason: "equipped",
     locked: true, masterworkTier: 5, power: 400, inLoadout: false, equipped: false,
     tuningModSlot: "Weapons"},
    {id: "m2", location: "Vault", protectionLevel: "", locked: false, masterworkTier: 5,
     power: 400, inLoadout: false, equipped: false, tuningModSlot: "Health"},
    {id: "m3", location: "Vault", protectionLevel: "", locked: false, masterworkTier: 5,
     power: 400, inLoadout: false, equipped: false, tuningModSlot: "Weapons"}
  ]
};
var state = {expanded: Object.create(null), rows: Object.create(null),
  duplicateRows: Object.create(null), verdicts: Object.create(null)};
var view = api.createView({document: new Document(), state: state});
var article = view.armorGroup(group);
var rowsTableHeaders = collect(
  collect(article, function (n) { return hasClass(n, "armor-matrix-rows"); })[0],
  function (n) { return n.tagName === "TH" && n.getAttribute("scope") === "col"; }
).map(function (n) { return n.textContent; });
var columnsTableAxisLabels = collect(
  collect(article, function (n) { return hasClass(n, "armor-matrix-columns"); })[0],
  function (n) { return hasClass(n, "armor-matrix-axis-label"); }
).map(function (n) { return n.textContent; });
var identicalLine = collect(article, function (n) { return hasClass(n, "armor-identical-axes"); })[0];
process.stdout.write(JSON.stringify({
  rowsHasProtection: rowsTableHeaders.indexOf("Protection") !== -1,
  rowsHasLocked: rowsTableHeaders.indexOf("Locked") !== -1,
  rowsHasTuning: rowsTableHeaders.indexOf("Tuning Mod Slot") !== -1,
  rowsHasInLoadout: rowsTableHeaders.indexOf("In loadout") !== -1,
  rowsHasEquipped: rowsTableHeaders.indexOf("Equipped") !== -1,
  rowsHasMasterwork: rowsTableHeaders.indexOf("Masterwork Tier") !== -1,
  rowsHasPower: rowsTableHeaders.indexOf("Power") !== -1,
  columnsHasProtection: columnsTableAxisLabels.indexOf("Protection") !== -1,
  columnsHasLocked: columnsTableAxisLabels.indexOf("Locked") !== -1,
  columnsHasMasterwork: columnsTableAxisLabels.indexOf("Masterwork Tier") !== -1,
  identicalText: identicalLine ? identicalLine.textContent : null
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as app:
        completed = subprocess.run(
            [NODE, str(script), str(app)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "rowsHasProtection": True, "rowsHasLocked": True, "rowsHasTuning": True,
        "rowsHasInLoadout": False, "rowsHasEquipped": False,
        "rowsHasMasterwork": False, "rowsHasPower": False,
        "columnsHasProtection": True, "columnsHasLocked": True,
        "columnsHasMasterwork": False,
        "identicalText": (
            "Identical across all pieces: Seasonal Mod none/unknown · "
            "Holofoil none/unknown · In loadout No · Equipped No · "
            "Masterwork Tier 5 · Power 400"
        ),
    }
