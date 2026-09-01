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
        "sections": [{"kind": "armor", "decisions": [], "armor": {
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
                    "hash": "700", "name": "Other plate", "type": "Helmet",
                    "guardian_class": "Warlock", "item_archetype": "Bulwark",
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
        '  filtered: {name: api.filterArmorGroups(groups, {text: "gunner"}).length, id: api.filterArmorGroups(groups, {text: "loser"}).length, class: api.filterArmorGroups(groups, {guardianClass: "Hunter"}).length, slot: api.filterArmorGroups(groups, {type: "Helmet"}).length, archetype: api.filterArmorGroups(groups, {itemArchetype: "Gunner"}).length, tuning: api.filterArmorGroups(groups, {tuningModSlot: "none/unknown"}).length},\n'
        '  membersIntact: api.filterArmorGroups(groups, {text: "loser"})[0].members.length === 3,\n'
        '  roles: stats.rows.map(function (row) { return [row.role, row.name, row.value]; }),\n'
        '  zerosCollapsed: stats.zeroSummary.indexOf("three base stats") !== -1,\n'
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
        "filtered": {"name": 1, "id": 1, "class": 1, "slot": 1,
                     "archetype": 1, "tuning": 1},
        "membersIntact": True,
        "roles": [["Primary", "weapons", 30], ["Secondary", "health", 25],
                  ["Tertiary", "class", 20]],
        "zerosCollapsed": True,
        "fallback": True,
        "prototypeClean": True,
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
var group = api.exactDuplicateGroupsFromSnapshot({sections: [{kind: "armor", decisions: [], armor: {
  exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "g", hash: "h",
    name: "Plate", type: "Chest Armor", guardian_class: "Hunter", item_archetype: "Gunner",
    tier: 5, stats: {weapons: 30, health: 25, class: 20, grenade: 0, super: 0, melee: 0},
    tuning_mod_slot: "Weapons", preferred_survivor_id: "survivor", members: [
      {id: "survivor", location: "Vault", disposition: "preferred_survivor"},
      {id: "retained", location: "Hunter(550)", disposition: "retained_protected", protection_level: "hard"},
      {id: "proposal", location: "Vault", disposition: "proposed_junk", proposal_action: "junk"}
    ]}]
}}]})[0];
var article = view.armorGroup(group);
var proposal = state.duplicateRows.proposal;
var before = proposal.cell;
proposal.approve.click();
state.verdicts.proposal = "approved";
view.paintArmorMember("proposal");
process.stdout.write(JSON.stringify({
  complete: article.textContent.indexOf("Plate") !== -1 &&
    article.textContent.indexOf("survivor") !== -1 && article.textContent.indexOf("retained") !== -1 &&
    article.textContent.indexOf("proposal") !== -1 && article.textContent.indexOf("Tuning Mod Slot") !== -1,
  readOnly: count(state.duplicateRows.survivor.cell, function (node) { return node.tagName === "BUTTON"; }) === 0 &&
    count(state.duplicateRows.retained.cell, function (node) { return node.tagName === "BUTTON"; }) === 0,
  proposalControls: count(proposal.cell, function (node) { return node.tagName === "BUTTON"; }) === 3,
  callback: JSON.stringify(toggles) === JSON.stringify([["proposal", "approved"]]),
  repaintedInPlace: state.duplicateRows.proposal.cell === before && proposal.approve.getAttribute("aria-pressed") === "true",
  labels: article.textContent.indexOf("Preferred survivor") !== -1 && article.textContent.indexOf("Retained protected") !== -1 && article.textContent.indexOf("Proposed junk") !== -1
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
        "readOnly": True,
        "proposalControls": True,
        "callback": True,
        "repaintedInPlace": True,
        "labels": True,
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
