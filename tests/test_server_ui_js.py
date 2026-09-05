"""Exercise the browser server adapter without a browser dependency."""

from __future__ import annotations

import json
import shutil
import subprocess
from html.parser import HTMLParser
from importlib.resources import as_file, files
from pathlib import Path
from typing import ClassVar

import pytest

from vault_cleaner.server.session import SESSION_STATES

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


HARNESS = r"""
"use strict";
var server = require(process.argv[2]);
var state = server.createState();
state.sort = { field: "id", direction: "desc" };
state.grouped = false;
state.query.text = "hostile";
state.query.kind = "weapons";
state.query.classFacet = "missing-class";
state.expanded["18446744073709551615"] = true;
state.expanded.stale = true;
var envelope = {
  schema_version: 1, state: "reviewing", report_revision: 4,
  verdict_revision: 2, fingerprint: "fingerprint",
  snapshot: { sections: [{ kind: "weapons", decisions: [
    { id: "18446744073709551615", hash: "9", name: "<img src=x>",
      action: "junk", reason: "test" }
  ] }] },
  verdicts: [{ id: "18446744073709551615", verdict: "approved" }],
  override_status: [{ id: "18446744073709551615", status: "active",
    detail: "untrusted detail" }],
  retained_verdict_ids: ["18446744073709551615"],
  discarded_verdict_ids: ["999"]
};
server.applySessionEnvelope(envelope, state);
var invalidState = server.createState();
invalidState.sort = { field: "removed-column", direction: "desc" };
invalidState.query.kind = "ghosts";
invalidState.expanded.stale = true;
server.applySessionEnvelope(envelope, invalidState);
process.stdout.write(JSON.stringify({
  id: state.items[0].id,
  name: state.items[0].name,
  verdict: state.verdicts[state.items[0].id],
  persisted: state.persistedVetoIds.has(state.items[0].id),
  serverFields: {
    state: state.server_state,
    reportRevision: state.report_revision,
    verdictRevision: state.verdict_revision,
    fingerprint: state.fingerprint,
    snapshot: state.snapshot
  },
  sort: state.sort,
  grouped: state.grouped,
  query: state.query.text,
  kind: state.query.kind,
  classFacet: state.query.classFacet,
  expandedKept: state.expanded["18446744073709551615"],
  expandedStale: state.expanded.stale === undefined,
  invalidated: {
    sort: invalidState.sort,
    kind: invalidState.query.kind,
    expandedStale: invalidState.expanded.stale === undefined
  },
  retained: state.reconciliation.retained,
  discarded: state.reconciliation.discarded,
  uploadStatus: state.uploadStatus
}));
"""


def test_session_envelope_seam_preserves_local_presentation_state(tmp_path: Path):
    harness = tmp_path / "server-ui-harness.js"
    harness.write_text(HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "id": "18446744073709551615",
        "name": "<img src=x>",
        "verdict": "approved",
        "persisted": True,
        "serverFields": {
            "state": "reviewing",
            "reportRevision": 4,
            "verdictRevision": 2,
            "fingerprint": "fingerprint",
            "snapshot": {
                "sections": [
                    {
                        "kind": "weapons",
                        "decisions": [
                            {
                                "id": "18446744073709551615",
                                "hash": "9",
                                "name": "<img src=x>",
                                "action": "junk",
                                "reason": "test",
                            }
                        ],
                    }
                ]
            },
        },
        "sort": {"field": "id", "direction": "desc"},
        "grouped": False,
        "query": "hostile",
        "kind": "weapons",
        "classFacet": "",
        "expandedKept": True,
        "expandedStale": True,
        "invalidated": {
            "sort": {"field": "name", "direction": "asc"},
            "kind": "",
            "expandedStale": True,
        },
        "retained": ["18446744073709551615"],
        "discarded": ["999"],
        "uploadStatus": {
            "weapons": "idle",
            "armor": "idle",
            "ghosts": "idle",
        },
    }


def test_exact_group_surface_reconciles_without_changing_session_fields(tmp_path: Path):
    harness = tmp_path / "server-ui-armor-groups-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
function group(tuning, guardianClass, archetype) {
  return { group_kind: "exact_duplicate", group_id: "__proto__", hash: "990",
    name: "Armor", type: "Chest Armor", guardian_class: guardianClass,
    item_archetype: archetype, tier: 5,
    stats: {weapons: 30, health: 25, class: 20, grenade: 0, super: 0, melee: 0},
    tuning_mod_slot: tuning, preferred_survivor_id: "01", members: [
      {id: "01", disposition: "preferred_survivor"},
      {id: "loser", disposition: "proposed_junk", proposal_action: "junk"}
    ]
  };
}
function envelope(revision, groups) {
  return {schema_version: 1, state: "reviewing", report_revision: revision,
    verdict_revision: revision, fingerprint: "fp-" + revision,
    snapshot: {sections: [{kind: "armor", decisions: [
      {id: "loser", hash: "990", action: "junk"}
    ], armor: {
      exact_duplicate_groups: groups
    }}]}, verdicts: [], override_status: []};
}
var state = server.createState();
server.applySessionEnvelope(envelope(1, [group("Weapons", "", "")]), state);
state.surface = "armor-duplicates";
state.armorQuery.text = "Armor";
state.armorQuery.guardianClass = "none/unknown";
state.armorQuery.itemArchetype = "none/unknown";
state.armorQuery.tuningModSlot = "Weapons";
server.applySessionEnvelope(envelope(2, [group("Weapons", "", "")]), state);
var retained = {surface: state.surface, text: state.armorQuery.text,
  classValue: state.armorQuery.guardianClass, tuning: state.armorQuery.tuningModSlot,
  archetypeValue: state.armorQuery.itemArchetype,
  report: state.report_revision, fingerprint: state.fingerprint,
  groupId: state.armorGroups[0].groupId,
  memberIds: state.armorGroups[0].members.map(function (m) { return m.id; })};
server.applySessionEnvelope(envelope(3, [group("", "", "")]), state);
var invalidated = state.reconciliation.invalidated.slice();
var cleared = state.armorQuery.tuningModSlot === "" &&
  state.armorQuery.text === "Armor" && state.surface === "armor-duplicates";
server.applySessionEnvelope(envelope(4, []), state);
process.stdout.write(JSON.stringify({retained: retained, cleared: cleared,
  noGroups: state.surface === "proposals" && state.armorGroups.length === 0,
  invalidated: invalidated}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "retained": {
            "surface": "armor-duplicates", "text": "Armor",
            "classValue": "none/unknown", "tuning": "Weapons",
            "archetypeValue": "none/unknown", "report": 2,
            "fingerprint": "fp-2", "groupId": "__proto__",
            "memberIds": ["01", "loser"],
        },
        "cleared": True,
        "noGroups": True,
        "invalidated": ["duplicate filter tuningModSlot Weapons"],
    }


def test_duplicate_ack_repaints_shared_verdict_state_without_view_switch_reset(
    tmp_path: Path,
):
    harness = tmp_path / "server-ui-duplicate-ack-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
function envelope(verdictRevision, state) {
  return {schema_version: 1, state: state || "reviewing", report_revision: 1,
    verdict_revision: verdictRevision, fingerprint: "fingerprint",
    snapshot: {sections: [{kind: "armor", decisions: [
      {id: "loser", hash: "h", action: "junk"}
    ], armor: {exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "g",
      hash: "h", name: "Plate", guardian_class: "", item_archetype: "",
      preferred_survivor_id: "survivor", members: [
        {id: "survivor", disposition: "preferred_survivor"},
        {id: "loser", disposition: "proposed_junk", proposal_action: "junk"}
      ]
    }]}}]},
    verdicts: verdictRevision ? [{id: "loser", verdict: "approved"}] : [],
    override_status: []};
}
var state = server.createState();
server.applySessionEnvelope(envelope(0), state);
state.surface = "armor-duplicates";
state.armorQuery.text = "Plate";
state.armorQuery.guardianClass = "none/unknown";
state.duplicateRows.loser = {sentinel: true};
var registry = state.duplicateRows;
server.applySessionEnvelope(envelope(1), state);
var afterAck = {
  verdict: state.verdicts.loser, surface: state.surface,
  text: state.armorQuery.text, classValue: state.armorQuery.guardianClass,
  registryKept: state.duplicateRows === registry,
  groupKept: state.armorGroups[0].members.map(function (member) { return member.id; })
};
server.applySessionEnvelope(envelope(2, "finalized"), state);
var finalized = state.server_state === "finalized" && state.surface === "armor-duplicates" &&
  state.verdicts.loser === "approved";
process.stdout.write(JSON.stringify({afterAck: afterAck, finalized: finalized}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "afterAck": {
            "verdict": "approved", "surface": "armor-duplicates", "text": "Plate",
            "classValue": "none/unknown", "registryKept": True,
            "groupKept": ["survivor", "loser"],
        },
        "finalized": True,
    }


def test_authoritative_envelope_retains_valid_class_filter_and_local_state(
    tmp_path: Path,
):
    harness = tmp_path / "server-ui-class-retention-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
var state = server.createState();
function envelope(reportRevision) {
  return {
    schema_version: 1, state: "reviewing", report_revision: reportRevision,
    verdict_revision: 0, fingerprint: "fingerprint-" + reportRevision,
    snapshot: { sections: [{ kind: "armor", decisions: [
      { id: "1", hash: "2", name: "Hunter Plate", kind: "armor",
        guardian_class: "Hunter", location: "Titan(550)",
        action: "review", reason: "armor-score" }
    ] }] },
    verdicts: [], override_status: []
  };
}
server.applySessionEnvelope(envelope(1), state);
state.sort = { field: "location", direction: "desc" };
state.grouped = false;
state.query.text = "Hunter";
state.query.action = "review";
state.query.kind = "armor";
state.query.reason = "armor-score";
state.query.classFacet = "Hunter";
state.expanded["1"] = true;
server.applySessionEnvelope(envelope(2), state);
process.stdout.write(JSON.stringify({
  sort: state.sort,
  grouped: state.grouped,
  query: state.query,
  expanded: state.expanded["1"],
  invalidated: state.reconciliation.invalidated
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "sort": {"field": "location", "direction": "desc"},
        "grouped": False,
        "query": {
            "text": "Hunter",
            "action": "review",
            "kind": "armor",
            "reason": "armor-score",
            "classFacet": "Hunter",
            "protection": "",
            "verdict": "",
        },
        "expanded": True,
        "invalidated": [],
    }


def test_session_envelope_rejects_unknown_schema_without_mutating_state(tmp_path: Path):
    harness = tmp_path / "server-ui-schema-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
var state = server.createState();
state.query.text = "keep me";
var error = "";
try {
  server.applySessionEnvelope({ schema_version: 2, snapshot: null }, state);
} catch (failure) {
  error = failure.message;
}
process.stdout.write(JSON.stringify({
  error: error, envelope: state.envelope, query: state.query.text
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "error": "session schema version 2 is not supported by this page",
        "envelope": None,
        "query": "keep me",
    }


def test_inconsistent_duplicate_proposal_is_rejected_before_presentation_adoption(
    tmp_path: Path,
):
    harness = tmp_path / "server-ui-malformed-duplicate-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
function envelope(revision, member, decisions, weaponDecisions) {
  return {schema_version: 1, state: "reviewing", report_revision: revision,
    verdict_revision: revision, fingerprint: "fingerprint-" + revision,
    snapshot: {sections: [
      {kind: "weapons", decisions: weaponDecisions || []},
      {kind: "armor", decisions: decisions || [], armor: {
      exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "g",
        hash: "h", name: "Plate", preferred_survivor_id: "survivor",
        members: [
          {id: "survivor", disposition: "preferred_survivor"}, member
        ]
      }]
    }}]}, verdicts: [], override_status: []};
}
var state = server.createState();
server.applySessionEnvelope(envelope(1,
  {id: "loser", disposition: "proposed_junk", proposal_action: "junk"},
  [{id: "loser", hash: "h", action: "junk"}], []), state);
state.surface = "armor-duplicates";
state.armorQuery.text = "Plate";
var before = state.armorGroups;
var errors = [];
[
  {id: "loser", disposition: "proposed_junk", proposal_action: "review"},
  {id: "loser", disposition: "proposed_junk", proposal_action: "junk"},
  {id: "loser", disposition: "retained_protected", proposal_action: "junk"},
  {id: "loser", disposition: "other", proposal_action: ""}
].forEach(function (member, index) {
  try {
    var decisions = index < 2 ? [] : [{id: "loser", hash: index === 2 ? "wrong" : "h", action: "junk"}];
    var weaponDecisions = index === 0 ? [{id: "loser", hash: "h", action: "junk"}] : [];
    server.applySessionEnvelope(envelope(index + 2, member, decisions, weaponDecisions), state);
  } catch (error) {
    errors.push(error.message);
  }
});
process.stdout.write(JSON.stringify({errors: errors.length,
  stillValid: state.report_revision === 1 && state.surface === "armor-duplicates" &&
    state.armorQuery.text === "Plate" && state.armorGroups === before &&
    state.armorGroups[0].members[1].proposalAction === "junk"}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"errors": 4, "stillValid": True}


def test_reconnect_button_retains_and_calls_its_retry_callback(tmp_path: Path):
    harness = tmp_path / "server-ui-reconnect-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
var listener = null;
var button = {
  addEventListener: function (name, callback) {
    if (name === "click") listener = callback;
  }
};
var host = {
  ownerDocument: {
    createElement: function (name) {
      if (name !== "button") throw new Error("expected a button");
      return button;
    }
  },
  appendChild: function (child) {
    if (child !== button) throw new Error("unexpected child");
  }
};
var calls = 0;
server.showReconnect(host, function () { calls += 1; });
listener();
process.stdout.write(JSON.stringify({
  calls: calls, type: button.type, text: button.textContent
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "calls": 1,
        "type": "button",
        "text": "Reconnect",
    }


def test_server_adapter_uses_browser_owned_transport_and_server_mutations():
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        source = adapter.read_text(encoding="utf-8")
    assert "Content-Length" not in source
    assert "innerHTML" not in source
    assert "text/csv" in source
    assert "/api/finalize" in source
    assert "/api/verdicts" in source
    assert "/api/reset" in source
    assert "/api/shutdown" in source
    assert ".disabled = disabled" in source
    assert "Restart vault-cleaner serve and open its new bootstrap URL" in source
    for label in ('"proposed"', '"after vetoes"', '"reviewed"', '"shown"', '"unreviewed"'):
        assert label in source


def test_server_ui_session_state_vocabulary_matches_python(tmp_path: Path):
    harness = tmp_path / "server-ui-state-vocabulary.js"
    harness.write_text(
        'var server = require(process.argv[2]);\n'
        'process.stdout.write(JSON.stringify(server.SESSION_STATES));\n',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert set(json.loads(completed.stdout)) == set(SESSION_STATES)


BOOT_HARNESS = r'''
"use strict";
var fs = require("fs");
var vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");

function Node(document) {
  this.ownerDocument = document;
  this.children = [];
  this.listeners = Object.create(null);
  this.disabled = false;
  this.hidden = false;
  this.textContent = "";
}
Node.prototype.addEventListener = function (name, callback) {
  this.listeners[name] = callback;
};
Node.prototype.appendChild = function (child) { this.children.push(child); };

function Document(readyState) {
  this.readyState = readyState;
  this.nodes = Object.create(null);
  this.listeners = Object.create(null);
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-controls", "vc-list",
   "vc-upload-weapons", "vc-upload-armor", "vc-upload-ghosts",
   "vc-upload-status-weapons", "vc-upload-status-armor",
   "vc-upload-status-ghosts"].forEach(function (id) {
    this.nodes[id] = new Node(this);
  }, this);
}
Document.prototype.getElementById = function (id) { return this.nodes[id]; };
Document.prototype.createElement = function () { return new Node(this); };
Document.prototype.addEventListener = function (name, callback) {
  this.listeners[name] = callback;
};
Document.prototype.fire = function (name) { this.listeners[name](); };

function run(readyState) {
  var document = new Document(readyState);
  var context = {
    document: document,
    fetch: function () { return Promise.reject(new Error("offline")); },
    VaultCleanerReviewUI: { COLUMNS: [] },
    Promise: Promise, Set: Set
  };
  context.globalThis = context;
  vm.runInNewContext(source, context);
  var api = context.VaultCleanerServerUI;
  var beforeStart = api.start;
  var beforeState = api.state;
  if (readyState === "loading") document.fire("DOMContentLoaded");
  return {
    sameObject: api === context.VaultCleanerServerUI,
    stableStart: beforeStart === api.start,
    stateWasDelayed: readyState === "loading" ? beforeState === null : true,
    hasLiveStart: typeof api.start === "function",
    hasLiveState: api.state !== null && typeof api.state === "object",
    startsDisconnected: api.state.connected === false
  };
}
process.stdout.write(JSON.stringify({
  interactive: run("interactive"), loading: run("loading")
}));
'''


def test_server_global_api_remains_stable_for_both_dom_timings(tmp_path: Path):
    harness = tmp_path / "server-ui-boot-harness.js"
    harness.write_text(BOOT_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    expected = {
        "sameObject": True,
        "stableStart": True,
        "stateWasDelayed": True,
        "hasLiveStart": True,
        "hasLiveState": True,
        "startsDisconnected": True,
    }
    assert json.loads(completed.stdout) == {
        "interactive": expected,
        "loading": expected,
    }


class _UploadMarkupParser(HTMLParser):
    _VOID_TAGS: ClassVar[set[str]] = {"input", "meta", "link", "br", "hr", "img"}

    def __init__(self):
        super().__init__()
        self.inputs = {}
        self.statuses = {}
        self._label_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "label":
            self._label_depth = 1
        elif tag == "input" and attributes.get("id"):
            self.inputs[attributes["id"]] = attributes
        elif tag == "span" and attributes.get("id"):
            attributes["inside_label"] = self._label_depth > 0
            self.statuses[attributes["id"]] = attributes
        if self._label_depth and tag not in self._VOID_TAGS and tag != "label":
            self._label_depth += 1

    def handle_endtag(self, tag):
        if self._label_depth:
            self._label_depth -= 1


def test_server_upload_statuses_are_described_live_regions():
    resource = files("vault_cleaner.ui").joinpath("review_server.html")
    with as_file(resource) as page:
        source = page.read_text(encoding="utf-8")
    parser = _UploadMarkupParser()
    parser.feed(source)
    for kind in ("weapons", "armor", "ghosts"):
        input_id = f"vc-upload-{kind}"
        status_id = f"vc-upload-status-{kind}"
        assert parser.inputs[input_id]["aria-describedby"] == status_id
        assert parser.statuses[status_id]["role"] == "status"
        assert parser.statuses[status_id]["aria-live"] == "polite"
        assert parser.statuses[status_id]["inside_label"] is False


def test_skip_link_targets_visible_focusable_review_content():
    resource = files("vault_cleaner.ui").joinpath("review_server.html")
    with as_file(resource) as page:
        source = page.read_text(encoding="utf-8")
    assert '<a class="skip" href="#vc-skip-target">' in source
    assert '<h1 id="vc-skip-target" tabindex="-1">' in source
    assert 'href="#vc-list"' not in source


class _ActionMarkupParser(HTMLParser):
    _VOID_TAGS: ClassVar[set[str]] = {"input", "meta", "link", "br", "hr", "img"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.actions = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id") == "vc-actions":
            self.actions = {
                "parent": self.stack[-1] if self.stack else None,
                "role": attributes.get("role"),
            }
        if tag not in self._VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]


def test_server_session_actions_are_reachable_outside_hidden_report_panel():
    resource = files("vault_cleaner.ui").joinpath("review_server.html")
    with as_file(resource) as page:
        parser = _ActionMarkupParser()
        parser.feed(page.read_text(encoding="utf-8"))
    assert parser.actions == {"parent": "main", "role": "group"}


RESPONSE_HARNESS = r'''
"use strict";
var server = require(process.argv[2]);

function rejected(label, setup) {
  global.fetch = setup;
  return server.fetchEnvelope("/api/report").then(function () {
    return { label: label, resolved: true };
  }, function (error) {
    return {
      label: label, resolved: false, clientCode: error.clientCode,
      kind: error.failure && error.failure.kind,
      status: error.server && error.server.status,
      serverCode: error.server && error.server.code
    };
  });
}

Promise.all([
  rejected("network", function () { return Promise.reject(new Error("offline")); }),
  rejected("http", function () {
    return Promise.resolve({ ok: false, status: 422, json: function () {
      return Promise.resolve({ error: { code: "invalid_export", message: "bad CSV" } });
    }});
  }),
  rejected("json", function () {
    return Promise.resolve({ ok: true, status: 200, json: function () {
      return Promise.reject(new Error("bad JSON"));
    }});
  })
]).then(function (results) {
  process.stdout.write(JSON.stringify(results));
});
'''


def test_server_response_conversion_distinguishes_transport_http_and_json(tmp_path: Path):
    harness = tmp_path / "server-ui-response-harness.js"
    harness.write_text(RESPONSE_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == [
        {
            "label": "network", "resolved": False,
            "clientCode": "transport_error", "kind": "transport",
        },
        {
            "label": "http", "resolved": False,
            "clientCode": "invalid_export", "kind": "http",
            "status": 422, "serverCode": "invalid_export",
        },
        {
            "label": "json", "resolved": False,
            "clientCode": "invalid_json", "kind": "json",
        },
    ]


ENVELOPE_HARNESS = r'''
"use strict";
var server = require(process.argv[2]);
function base(decisions) {
  return {
    schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "fingerprint",
    snapshot: { sections: [{ kind: "weapons", decisions: decisions }] },
    verdicts: [], override_status: []
  };
}
function check(label, envelope) {
  try {
    server.applySessionEnvelope(envelope, server.createState());
    return { label: label, accepted: true };
  } catch (error) {
    return { label: label, accepted: false, message: error.message };
  }
}
process.stdout.write(JSON.stringify([
  check("array envelope", []),
  check("numeric decision id", base([{ id: 6917529027641981542, hash: "500" }])),
  check("duplicate decision id", base([
    { id: "500", hash: "500" }, { id: "500", hash: "500" }
  ]))
]));
'''


def test_server_envelope_validation_rejects_array_numeric_and_duplicate_decisions(
    tmp_path: Path,
):
    harness = tmp_path / "server-ui-envelope-harness.js"
    harness.write_text(ENVELOPE_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    results = json.loads(completed.stdout)
    assert [result["accepted"] for result in results] == [False, False, False]
    assert results[0]["message"] == "session envelope must be an object"
    assert "must be a JSON string" in results[1]["message"]
    assert "duplicate decision" in results[2]["message"]


OVERRIDE_HARNESS = r'''
"use strict";
var server = require(process.argv[2]);
function envelope(statuses) {
  return {
    schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "fingerprint",
    snapshot: { sections: [{ kind: "weapons", decisions: [] }] },
    verdicts: [], override_status: statuses
  };
}
function stateView(state) {
  return JSON.stringify({
    envelope: state.envelope,
    serverState: state.server_state,
    overrideStatus: state.override_status,
    persisted: Array.from(state.persistedVetoIds),
    query: state.query,
    sort: state.sort
  });
}
var state = server.createState();
server.applySessionEnvelope(envelope([
  { id: "1", status: "active", detail: "still matches" }
]), state);
state.query.text = "keep me";
state.sort = { field: "id", direction: "desc" };
var before = stateView(state);
var error = "";
try {
  server.applySessionEnvelope(envelope([
    { id: "1", status: "active", detail: "still matches" },
    { id: "1", status: "stale", detail: "duplicate" }
  ]), state);
} catch (failure) {
  error = failure.clientCode + ":" + failure.message;
}
process.stdout.write(JSON.stringify({
  error: error, unchanged: before === stateView(state),
  sanitized: state.override_status
}));
'''


def test_malformed_override_status_is_atomic_and_sanitized(tmp_path: Path):
    harness = tmp_path / "server-ui-override-harness.js"
    harness.write_text(OVERRIDE_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "error": (
            "unsupported_envelope:session envelope has duplicate override status id 1"
        ),
        "unchanged": True,
        "sanitized": [{"id": "1", "status": "active", "detail": "still matches"}],
    }


FAILURE_HARNESS = r'''
"use strict";
var fs = require("fs");
var vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var scenario = process.argv[3];
var shared = process.argv[4] ? require(process.argv[4]) : null;

function Node(document) {
  this.ownerDocument = document;
  this.children = [];
  this.listeners = Object.create(null);
  this.disabled = false;
  this.hidden = false;
  this.files = [];
  this.value = "";
  this.textContent = "";
}
Node.prototype.addEventListener = function (name, callback) {
  this.listeners[name] = callback;
};
Node.prototype.appendChild = function (child) { this.children.push(child); };
Node.prototype.dispatch = function (name) {
  this.listeners[name]({ target: this });
};

function Document() {
  this.readyState = "interactive";
  this.nodes = Object.create(null);
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-controls", "vc-list",
   "vc-upload-weapons", "vc-upload-armor", "vc-upload-ghosts",
   "vc-upload-status-weapons", "vc-upload-status-armor",
   "vc-upload-status-ghosts"].forEach(function (id) {
    this.nodes[id] = new Node(this);
  }, this);
}
Document.prototype.getElementById = function (id) { return this.nodes[id]; };
Document.prototype.createElement = function () { return new Node(this); };

function makeUi(document) {
  function node() { return new Node(document); }
  return {
    COLUMNS: [["name", "Name"]],
    itemsFromSnapshot: function () { return []; },
    actionCounts: function () { return { total: 0, junk: 0, review: 0 }; },
    keptItems: function () { return []; },
    reviewCounts: function () {
      return { approved: 0, vetoed: 0, unreviewed: 0 };
    },
    filterItems: function () { return []; },
    sortItems: function (items) { return items; },
    groupItems: function () { return []; },
    verdictOf: function () { return ""; },
    exactDuplicateGroupsFromSnapshot: shared && shared.exactDuplicateGroupsFromSnapshot,
    createView: function () {
      return {
        clear: function (host) { host.children = []; },
        el: function () { return node(); },
        optionsFor: function () { return []; },
        addSelect: function (host) { host.appendChild(node()); },
        select: function () {
          var outer = node();
          var select = node();
          outer.querySelector = function () { return select; };
          return outer;
        },
        tile: function () { return node(); },
        table: function () { return node(); }
      };
    }
  };
}

function envelope() {
  return {
    schema_version: 1, state: "idle", report_revision: 0,
    verdict_revision: 0, fingerprint: null, snapshot: null,
    verdicts: [], override_status: []
  };
}
function malformedDuplicateEnvelope(crossSection) {
  var armorDecision = {id: "9002", hash: crossSection ? "armor-hash" : "wrong-hash",
    action: "junk"};
  return {
    schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "fingerprint", snapshot: {sections: [
      {kind: "weapons", decisions: crossSection ? [
        {id: "9002", hash: "armor-hash", action: "junk"}
      ] : []},
      {kind: "armor", decisions: crossSection ? [] : [armorDecision], armor: {
        exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "9001",
          hash: "armor-hash", name: "Armor Plate", preferred_survivor_id: "9001",
          members: [
            {id: "9001", disposition: "preferred_survivor"},
            {id: "9002", disposition: "proposed_junk", proposal_action: "junk"}
          ]
        }]
      }}
    ]}, verdicts: [], override_status: []
  };
}
function malformedCrossGroupMemberEnvelope() {
  return {
    schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "fingerprint", snapshot: {sections: [{
      kind: "armor", decisions: [
        {id: "loser-one", hash: "h", action: "junk"},
        {id: "loser-two", hash: "h", action: "junk"}
      ], armor: {exact_duplicate_groups: [
        {group_kind: "exact_duplicate", group_id: "group-one", hash: "h",
          preferred_survivor_id: "shared", members: [
            {id: "shared", disposition: "preferred_survivor"},
            {id: "loser-one", disposition: "proposed_junk", proposal_action: "junk"}
          ]},
        {group_kind: "exact_duplicate", group_id: "group-two", hash: "h",
          preferred_survivor_id: "shared", members: [
            {id: "shared", disposition: "preferred_survivor"},
            {id: "loser-two", disposition: "proposed_junk", proposal_action: "junk"}
          ]}
      ]}
    }]}, verdicts: [], override_status: []
  };
}
function response(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status: status,
    json: function () { return Promise.resolve(payload); }
  };
}
function invalidJsonResponse(status) {
  return {
    ok: status >= 200 && status < 300,
    status: status,
    json: function () { return Promise.reject(new Error("bad JSON")); }
  };
}
function run() {
  var document = new Document();
  var queue;
  var upload = scenario.indexOf("upload-") === 0;
  if (scenario === "report-network") {
    queue = [new Error("offline")];
  } else if (scenario === "report-cross-section-duplicate") {
    queue = [response(200, malformedDuplicateEnvelope(true))];
  } else if (scenario === "report-wrong-hash-duplicate") {
    queue = [response(200, malformedDuplicateEnvelope(false))];
  } else if (scenario === "report-cross-group-member-duplicate") {
    queue = [response(200, envelope()), response(200, malformedCrossGroupMemberEnvelope())];
  } else if (scenario === "report-incompatible") {
    queue = [response(200, [])];
  } else if (scenario === "report-invalid-override") {
    var badEnvelope = envelope();
    badEnvelope.override_status = [{ id: "1", status: "active", detail: 7 }];
    queue = [response(200, badEnvelope)];
  } else if (scenario === "report-invalid-json") {
    queue = [invalidJsonResponse(200)];
  } else if (scenario === "report-unauthorized") {
    queue = [response(401, {
      error: { code: "authentication_required", message: "auth required" }
    })];
  } else if (scenario === "report-illegal") {
    queue = [response(409, {
      error: { code: "illegal_state", message: "session ended" }
    })];
  } else if (scenario === "report-http") {
    queue = [response(500, {
      error: { code: "internal_error", message: "internal error" }
    })];
  } else {
    queue = [response(200, envelope())];
    if (scenario === "ordinary") {
      queue.push(response(422, {
        error: { code: "invalid_export", message: "bad CSV" }
      }));
    } else if (scenario === "upload-unauthorized") {
      queue.push(response(401, {
        error: { code: "authentication_required", message: "auth required" }
      }));
    } else if (scenario === "upload-illegal") {
      queue.push(response(409, {
        error: { code: "illegal_state", message: "session ended" }
      }));
    } else if (scenario === "upload-malformed") {
      queue.push(response(200, []));
    } else if (scenario === "upload-network") {
      queue.push(new Error("offline"));
    } else if (scenario === "upload-collision") {
      queue.push(response(422, {
        error: { code: "transport_error", message: "bad CSV" }
      }));
    } else if (scenario === "upload-invalid-json") {
      queue.push(invalidJsonResponse(200));
    }
  }
  var context = {
    document: document,
    fetch: function () {
      var next = queue.shift();
      return next instanceof Error ? Promise.reject(next) : Promise.resolve(next);
    },
    VaultCleanerReviewUI: makeUi(document),
    Promise: Promise, Set: Set, setTimeout: setTimeout
  };
  context.globalThis = context;
  var api;
  var reportFailureDone = null;
  var reportFailureResolve = null;
  if (scenario === "report-cross-group-member-duplicate") {
    var statusNode = document.nodes["vc-status"];
    var statusText = statusNode.textContent;
    reportFailureDone = new Promise(function (resolve) {
      reportFailureResolve = resolve;
    });
    Object.defineProperty(statusNode, "textContent", {
      configurable: true,
      get: function () { return statusText; },
      set: function (value) {
        statusText = String(value);
        if (reportFailureResolve && api && api.state.terminal &&
            statusText.indexOf("incompatible response") !== -1) {
          var resolve = reportFailureResolve;
          reportFailureResolve = null;
          resolve();
        }
      }
    });
  }
  vm.runInNewContext(source, context);
  api = context.VaultCleanerServerUI;
  function result() {
    var output = {
      sameObject: api === context.VaultCleanerServerUI,
      connected: api.state.connected,
      terminal: api.state.terminal,
      mainStatus: document.nodes["vc-status"].textContent,
      uploadPhase: api.state.uploadStatus.weapons,
      uploadStatus: document.nodes["vc-upload-status-weapons"].textContent
    };
    if (scenario === "report-cross-group-member-duplicate") {
      output.reportRevision = api.state.report_revision;
      output.snapshot = api.state.snapshot;
    }
    return output;
  }
  if (scenario === "report-cross-group-member-duplicate") {
    api.start();
    return reportFailureDone.then(result);
  }
  return new Promise(function (resolve) {
    setTimeout(function () {
      if (upload || scenario === "ordinary") {
        var input = document.nodes["vc-upload-weapons"];
        input.files = [{}];
        input.dispatch("change");
      }
      setTimeout(function () {
        resolve(result());
      }, 0);
    }, 0);
  });
}
run().then(function (result) { process.stdout.write(JSON.stringify(result)); });
'''


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        (
            "report-network",
            {
                "sameObject": True,
                "connected": False,
                "terminal": False,
                "mainStatus": (
                    "Could not reach the review server. Check that it is still "
                    "running and reconnect."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "upload-network",
            {
                "sameObject": True,
                "connected": False,
                "terminal": False,
                "mainStatus": (
                    "Could not reach the review server. Check that it is still "
                    "running and reconnect."
                ),
                "uploadPhase": "rejected",
                "uploadStatus": (
                    "Rejected: Could not reach the review server. Check that it is "
                    "still running and reconnect."
                ),
            },
        ),
        (
            "report-incompatible",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "report-cross-section-duplicate",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "report-wrong-hash-duplicate",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "report-cross-group-member-duplicate",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
                "reportRevision": 0,
                "snapshot": None,
            },
        ),
        (
            "upload-malformed",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "rejected",
                "uploadStatus": (
                    "Rejected: The review server returned an incompatible response. "
                    "Restart vault-cleaner serve and open its new bootstrap URL."
                ),
            },
        ),
        (
            "report-invalid-override",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "report-invalid-json",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "report-unauthorized",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The authenticated session is unavailable. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "ordinary",
            {
                "sameObject": True,
                "connected": True,
                "terminal": False,
                "mainStatus": "Connected. Upload one or more DIM CSV exports to begin.",
                "uploadPhase": "rejected",
                "uploadStatus": "Rejected: bad CSV",
            },
        ),
        (
            "upload-collision",
            {
                "sameObject": True,
                "connected": True,
                "terminal": False,
                "mainStatus": "Connected. Upload one or more DIM CSV exports to begin.",
                "uploadPhase": "rejected",
                "uploadStatus": "Rejected: bad CSV",
            },
        ),
        (
            "upload-invalid-json",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": (
                    "The review server returned an incompatible response. Restart "
                    "vault-cleaner serve and open its new bootstrap URL."
                ),
                "uploadPhase": "rejected",
                "uploadStatus": (
                    "Rejected: The review server returned an incompatible response. "
                    "Restart vault-cleaner serve and open its new bootstrap URL."
                ),
            },
        ),
        (
            "upload-illegal",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": "session ended",
                "uploadPhase": "rejected",
                "uploadStatus": "Rejected: session ended",
            },
        ),
        (
            "report-illegal",
            {
                "sameObject": True,
                "connected": False,
                "terminal": True,
                "mainStatus": "session ended",
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
        (
            "report-http",
            {
                "sameObject": True,
                "connected": False,
                "terminal": False,
                "mainStatus": "The review server returned an HTTP error (500). Try reconnecting.",
                "uploadPhase": "idle",
                "uploadStatus": "",
            },
        ),
    ],
)
def test_server_adapter_classifies_browser_failures_without_losing_upload_state(
    tmp_path: Path, scenario: str, expected: dict[str, object]
):
    harness = tmp_path / f"server-ui-failure-{scenario}.js"
    harness.write_text(FAILURE_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), scenario, str(presentation)],
            capture_output=True,
            encoding="utf-8",
            check=False,
            timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == expected


MUTATION_HARNESS = r'''
"use strict";
var fs = require("fs"), vm = require("vm"), scenario = process.argv[3];
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[4]);

function Node(tag, document) {
  this.tagName = String(tag).toUpperCase(); this.ownerDocument = document;
  this.children = []; this.parentNode = null; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._textContent = ""; this.disabled = false;
  this.hidden = false; this.value = ""; this.selectionStart = 0; this.selectionEnd = 0; this.files = [];
}
Object.defineProperty(Node.prototype, "textContent", {
  get: function () { return this._textContent; },
  set: function (value) { this._textContent = String(value); this.children = []; }
});
Node.prototype.appendChild = function (child) {
  child.parentNode = this; this.children.push(child); return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child); if (index >= 0) this.children.splice(index, 1);
  child.parentNode = null;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  // Match browser activation: disabled form controls do not dispatch click
  // events. This catches stale references that would otherwise make a frozen
  // action look usable in this lightweight harness.
  if (name === "click" && this.disabled) return;
  event = event || { target: this, preventDefault: function () {} };
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null, wanted = selector.toLowerCase();
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child; else visit(child);
    });
  }
  visit(this); return found;
};
Node.prototype.focus = function () { this.ownerDocument.activeElement = this; };
Node.prototype.click = function () {
  if (this.ownerDocument && this.ownerDocument.downloads) {
    this.ownerDocument.downloads.push(this.download || "");
  }
};
Object.defineProperty(Node.prototype, "firstChild", { get: function () {
  return this.children[0] || null;
} });

function Document() {
  this.nodes = Object.create(null); this.listeners = Object.create(null);
  this.body = new Node("body", this); this.activeElement = null; this.downloads = [];
  this.main = new Node("main", this); this.body.appendChild(this.main);
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
  this.nodes["vc-actions"].setAttribute("role", "group");
  this.main.appendChild(this.nodes["vc-actions"]);
  this.main.appendChild(this.nodes["vc-report"]);
  this.main.appendChild(this.nodes["vc-view-selector"]);
  this.main.appendChild(this.nodes["vc-proposals"]);
  this.main.appendChild(this.nodes["vc-duplicates"]);
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Document.prototype.dispatch = function (name, event) {
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};

var id = "18446744073709551615";
var armorProposalId = "9002";
function envelope(verdictRevision, verdicts, state) {
  return { schema_version: 1, state: state || "reviewing", report_revision: 1,
    verdict_revision: verdictRevision, fingerprint: "opaque-fingerprint",
    snapshot: { sections: [{ kind: "weapons", decisions: [
      { id: id, hash: "18446744073709551614", name: "<img>", location: "Titan",
        guardian_class: "",
        action: "junk", reason: "dupe-lower" },
      { id: "2", hash: "500", name: "Second", location: "Hunter",
        guardian_class: "",
        action: "review", reason: "wishlist" }
    ] }] }, verdicts: verdicts || [],
    override_status: [{ id: id, status: "active", detail: "suppresses this item" }] };
}
function duplicateEnvelope(verdictRevision, verdicts, state) {
  var next = envelope(verdictRevision, verdicts, state);
  next.snapshot.sections.push({kind: "armor", decisions: [
    {id: armorProposalId, hash: "armor-hash", name: "Armor Plate", location: "Vault",
      guardian_class: "Hunter", action: "junk", reason: "armor-exact-dupe"}
  ], armor: {exact_duplicate_groups: [{
    group_kind: "exact_duplicate", group_id: "9001", hash: "armor-hash",
    name: "Armor Plate", type: "Chest Armor", guardian_class: "Hunter",
    item_archetype: "Gunner", tier: 5,
    stats: {weapons: 30, health: 25, class: 20, grenade: 0, super: 0, melee: 0},
    tuning_mod_slot: "Weapons", preferred_survivor_id: "9001", members: [
      {id: "9001", location: "Vault", disposition: "preferred_survivor"},
      {id: "9003", location: "Hunter(550)", disposition: "retained_protected",
        protection_level: "hard"},
      {id: armorProposalId, location: "Vault", disposition: "proposed_junk",
        proposal_action: "junk"}
    ]
  }]}});
  return next;
}
function classChangedEnvelope(verdicts) {
  var next = envelope(1, verdicts);
  next.snapshot.sections[0].kind = "armor";
  next.snapshot.sections[0].decisions.forEach(function (decision, index) {
    decision.kind = "armor";
    decision.guardian_class = index === 0 ? "Hunter" : "Warlock";
    decision.location = index === 0 ? "Vault" : "Hunter(550)";
  });
  return next;
}
function response(payload, status) {
  return { ok: (status || 200) < 300, status: status || 200,
    json: function () { return Promise.resolve(payload); } };
}
function csvResponse(mode) {
  mode = mode || "";
  var result = { ok: true, status: 200,
    headers: { get: function (name) {
      if (name === "Vault-Cleaner-Report-Revision") return "1";
      if (name === "Vault-Cleaner-Verdict-Revision") return "1";
      if (name === "Vault-Cleaner-Approved-Still-Vetoed") {
        return mode === "plural" ? "2" : (mode === "zero" ? "0" :
          (mode === "invalid" ? "not-a-count" : "1"));
      }
      if (name === "Vault-Cleaner-Serve-Once") return mode === "once" || mode.indexOf("once-") === 0 ? "true" : null;
      return null;
    } }
  };
  if (mode === "missing" || mode === "once-missing") return result;
  result.arrayBuffer = function () {
    if (mode === "reject" || mode === "once-reject") return Promise.reject(new Error("body read failed"));
    return Promise.resolve(new Uint8Array([65, 44, 66, 10]).buffer);
  };
  return result;
}
function idleEnvelope() {
  return { schema_version: 1, state: "idle", report_revision: 0,
    verdict_revision: 0, fingerprint: null, snapshot: null, verdicts: [],
    override_status: [] };
}
var pendingReportResolve = null, pendingSessionNote = null;
function pendingReport(payload) {
  return new Promise(function (resolve) {
    pendingReportResolve = function () { resolve(response(payload)); };
  });
}

var queue = [response(envelope(0))], calls = [];
if (scenario === "idle") queue = [response(idleEnvelope())];
if (scenario === "single" || scenario === "keyboard") queue.push(response(envelope(1, [{ id: id, verdict: "approved" }] )));
if (scenario === "clear") queue.push(response(envelope(1)));
if (scenario === "failure") queue.push(response({ error: { code: "invalid_export", message: "no" } }, 422));
if (scenario === "bulk") queue.push(response(envelope(1, [
  { id: id, verdict: "vetoed" }, { id: "2", verdict: "vetoed" }
])));
if (scenario === "filter-cleared-search") queue.push(response(envelope(1, [
  { id: id, verdict: "vetoed" }, { id: "2", verdict: "vetoed" }
])));
if (scenario === "filter-cleared-class") queue.push(response(classChangedEnvelope([
  { id: id, verdict: "vetoed" }, { id: "2", verdict: "vetoed" }
])));
if (scenario === "verdict-filter-approved") {
  queue = [response(envelope(0, [{ id: id, verdict: "approved" }])),
    response(envelope(1, [{ id: id, verdict: "approved" }]))];
}
if (scenario === "verdict-filter-vetoed") {
  queue = [response(envelope(0, [{ id: id, verdict: "vetoed" }])),
    response(envelope(1, [{ id: id, verdict: "vetoed" }]))];
}
if (scenario === "verdict-filter-unreviewed") {
  queue = [response(envelope(0)), response(envelope(1))];
}
if (scenario === "filter-cleared") {
  queue = [response(envelope(0, [{ id: id, verdict: "vetoed" }])), response(envelope(1))];
}
if (scenario === "stale") {
  queue.push(response({ error: { code: "stale_verdicts", message: "stale" } }, 409));
  queue.push(response(envelope(2, [{ id: id, verdict: "vetoed" }])));
}
if (scenario === "stale-failure") {
  queue.push(response({ error: { code: "stale_verdicts", message: "stale" } }, 409));
  queue.push(response({ error: { code: "temporary", message: "report unavailable" } }, 500));
}
if (scenario === "upload-gate") {
  queue = [response(idleEnvelope()), response(envelope(1)), response(envelope(2, [
    { id: id, verdict: "vetoed" }, { id: "2", verdict: "vetoed" }
  ]))];
}
if (scenario === "duplicate") {
  queue = [response(duplicateEnvelope(0)),
    response({ error: { code: "invalid_export", message: "bad duplicate CSV" } }, 422),
    response(duplicateEnvelope(1, [
      { id: id, verdict: "approved" }, { id: armorProposalId, verdict: "approved" }
    ])),
    csvResponse(),
    response(duplicateEnvelope(2, [
      { id: id, verdict: "approved" }, { id: armorProposalId, verdict: "approved" }
    ], "finalized"))];
}
if (scenario === "finalize" || scenario === "finalize-missing" ||
    scenario === "finalize-reject" || scenario === "finalize-plural" ||
    scenario === "finalize-zero" || scenario === "finalize-invalid-header" ||
    scenario === "finalize-once" || scenario === "finalize-once-missing" ||
    scenario === "finalize-once-reject" || scenario.indexOf("finalize-refetch-") === 0 ||
    scenario.indexOf("finalize-body-") === 0) {
  var csvMode = "ok";
  if (scenario === "finalize-missing") csvMode = "missing";
  else if (scenario === "finalize-reject" || scenario.indexOf("finalize-body-") === 0) {
    csvMode = "reject";
  } else if (scenario === "finalize-once-reject") csvMode = "once-reject";
  else if (scenario === "finalize-once-missing") csvMode = "once-missing";
  else if (scenario === "finalize-plural") csvMode = "plural";
  else if (scenario === "finalize-zero") csvMode = "zero";
  else if (scenario === "finalize-invalid-header") csvMode = "invalid";
  else if (scenario.indexOf("finalize-once") === 0) csvMode = "once";
  queue.push(csvResponse(csvMode));
  if (scenario === "finalize-refetch-http" || scenario === "finalize-refetch-failure") {
    queue.push(response({ error: { code: "temporary", message: "report unavailable" } }, 500));
  } else if (scenario === "finalize-refetch-transport") {
    queue.push(new Error("offline"));
  } else if (scenario === "finalize-refetch-pending") {
    queue.push(pendingReport(envelope(1, [{ id: id, verdict: "approved" }], "finalized")));
  } else if (scenario === "finalize-refetch-unauthorized") {
    queue.push(response({ error: { code: "authentication_required", message: "auth required" } }, 401));
  } else if (scenario === "finalize-refetch-illegal") {
    queue.push(response({ error: { code: "illegal_state", message: "session ended" } }, 409));
  } else if (scenario === "finalize-refetch-incompatible") {
    queue.push(response([], 200));
  } else if (scenario === "finalize-refetch-closed") {
    queue.push(response(envelope(1, [{ id: id, verdict: "approved" }], "closed")));
  } else if (scenario === "finalize-body-http") {
    queue.push(response({ error: { code: "temporary", message: "report unavailable" } }, 500));
  } else if (scenario === "finalize-body-transport") {
    queue.push(new Error("offline"));
  } else if (scenario === "finalize-body-unauthorized") {
    queue.push(response({ error: { code: "authentication_required", message: "auth required" } }, 401));
  } else if (scenario === "finalize-body-illegal") {
    queue.push(response({ error: { code: "illegal_state", message: "session ended" } }, 409));
  } else if (scenario === "finalize-body-incompatible") {
    queue.push(response([], 200));
  } else if (scenario === "finalize-body-closed") {
    queue.push(response(envelope(1, [{ id: id, verdict: "approved" }], "closed")));
  } else if (scenario !== "finalize-once" && scenario !== "finalize-once-missing" &&
      scenario !== "finalize-once-reject") {
    queue.push(response(envelope(1, [{ id: id, verdict: "approved" }], "finalized")));
  }
  if (scenario === "finalize-missing" || scenario === "finalize-reject" ||
      scenario === "finalize-refetch-failure" || scenario === "finalize-body-http") queue.push(csvResponse());
}
if (scenario === "reset") queue.push(response({ schema_version: 1, state: "idle", report_revision: 2,
  verdict_revision: 1, fingerprint: null, snapshot: null, verdicts: [], override_status: [] }));
if (scenario === "shutdown") queue.push(response({ schema_version: 1, state: "closed", report_revision: 1,
  verdict_revision: 0, fingerprint: null, snapshot: null, verdicts: [], override_status: [] }));

var document = new Document();
var revoked = 0;
var context = { document: document, VaultCleanerReviewUI: shared, Promise: Promise, Set: Set,
  Blob: Blob, URL: { createObjectURL: function () { return "blob:review"; },
    revokeObjectURL: function () { revoked += 1; } }, confirm: function () { return true; }, setTimeout: setTimeout,
  fetch: function (path, options) {
    calls.push({ path: path, options: options || null });
    var next = queue.shift();
    if (scenario === "upload-gate" && path === "/api/exports/weapons") {
      return new Promise(function (resolve) { setTimeout(function () { resolve(next); }, 5); });
    }
    return next instanceof Error ? Promise.reject(next) : Promise.resolve(next);
  } };
context.globalThis = context;
vm.runInNewContext(source, context);

function finish() {
  var state = context.VaultCleanerServerUI.state;
  var output = { paths: calls.map(function (call) { return call.path; }),
    state: state.server_state, verdicts: state.verdicts,
    status: document.nodes["vc-status"].textContent,
    pendingSessionNote: pendingSessionNote,
    revoked: revoked, downloads: document.downloads,
    finalizeHeaders: state.finalizeHeaders,
    filterValue: document.nodes["vc-f-verdict"] ? document.nodes["vc-f-verdict"].value : null,
    classFilterValue: document.nodes["vc-f-classFacet"] ? document.nodes["vc-f-classFacet"].value : null,
    sessionNote: document.nodes["vc-session-note"].textContent,
    searchValue: document.nodes["vc-search"] ? document.nodes["vc-search"].value : null,
    searchFocused: document.activeElement === document.nodes["vc-search"],
    searchSelectionStart: document.nodes["vc-search"] ? document.nodes["vc-search"].selectionStart : null,
    searchSelectionEnd: document.nodes["vc-search"] ? document.nodes["vc-search"].selectionEnd : null,
    queryVerdict: state.query.verdict,
    queryClassFacet: state.query.classFacet,
    viewInvalidated: state.viewInvalidated,
    searchSame: document.nodes["vc-search"] === beforeSearch,
    bulkSame: document.nodes["vc-bulk-veto"] === beforeBulk,
    classFilterSame: document.nodes["vc-f-classFacet"] === beforeClassFilter,
    rowIds: Object.keys(state.rows).sort(),
    actionRole: document.nodes["vc-actions"].getAttribute("role"),
    actionsReachable: document.nodes["vc-actions"].parentNode === document.main,
    shutdownVisible: document.nodes["vc-actions"].children.some(function (child) {
      return child.getAttribute && child.getAttribute("id") === "vc-shutdown";
    }),
    idleHintVisible: document.nodes["vc-actions"].children.some(function (child) {
      return child.textContent && child.textContent.indexOf("Upload one or more DIM") !== -1;
    }),
    actionsText: (function text(node) {
      return (node._textContent || "") + (node.children || []).map(text).join("");
    })(document.nodes["vc-actions"]),
    connected: state.connected, terminal: state.terminal,
    uploadBulkDisabled: uploadBulkDisabled,
    bulkDisabled: document.nodes["vc-bulk-veto"] ? document.nodes["vc-bulk-veto"].disabled : null,
    rowDisabled: state.rows[id] ? state.rows[id].approve.disabled : null,
    downloadDisabled: document.nodes["vc-download-again"] ? document.nodes["vc-download-again"].disabled : null,
    resetDisabled: document.nodes["vc-reset"] ? document.nodes["vc-reset"].disabled : null,
    shutdownDisabled: document.nodes["vc-shutdown"] ? document.nodes["vc-shutdown"].disabled : null,
    finalizeVisible: document.nodes["vc-actions"].children.some(function (child) {
      return child.getAttribute && child.getAttribute("id") === "vc-finalize";
    }),
    reconnectVisible: document.nodes["vc-status"].children.length > 0,
    bodylessShutdown: calls.some(function (call) { return call.path === "/api/shutdown" &&
      call.options && call.options.method === "POST" && !Object.prototype.hasOwnProperty.call(call.options, "body"); }),
    row: state.rows[id] ? { same: state.rows[id].tr === beforeRow, focused: document.activeElement === beforeFocus,
      presentation: state.rows[id].presentation && state.rows[id].presentation.textContent } : null };
  output.duplicate = {
    rejectedPreserved: duplicateRejected,
    gateDisabled: duplicateGateDisabled,
    repaintedInPlace: duplicateRepainted,
    crossViewVerdict: duplicateCrossViewVerdict,
    crossViewPressed: duplicateCrossViewPressed,
    surfacePreserved: duplicateSurfacePreserved,
    searchPreserved: duplicateSearchPreserved,
    finalizedDisabled: duplicateFinalizedDisabled,
    visible: !document.nodes["vc-duplicates"].hidden,
    scopeText: document.nodes["vc-duplicate-scope"] ? document.nodes["vc-duplicate-scope"].textContent : "",
    groupText: (function text(node) {
      return (node._textContent || "") + (node.children || []).map(text).join("");
    })(document.nodes["vc-duplicate-list"])
  };
  var payloadCall = calls.filter(function (call) { return call.path === "/api/verdicts" || call.path === "/api/reset"; })[0];
  if (payloadCall && payloadCall.options && payloadCall.options.body) output.payload = JSON.parse(payloadCall.options.body);
  process.stdout.write(JSON.stringify(output));
}
var beforeRow = null, beforeFocus = null, beforeFinalize = null, uploadBulkDisabled = null;
var beforeSearch = null, beforeBulk = null, beforeClassFilter = null;
var duplicateRejected = false, duplicateGateDisabled = false, duplicateCell = null;
var duplicateRepainted = false, duplicateCrossViewVerdict = null;
var duplicateCrossViewPressed = null, duplicateFinalizedDisabled = false;
var duplicateSurfacePreserved = false, duplicateSearchPreserved = false;
setTimeout(function () {
  var server = context.VaultCleanerServerUI, state = server.state;
  if (scenario === "single" || scenario === "clear" || scenario === "failure" || scenario === "stale" || scenario === "stale-failure") {
    beforeRow = state.rows[id].tr; beforeFocus = state.rows[id].approve; beforeFocus.focus();
    if (scenario === "clear") state.rows[id].clear.dispatch("click");
    else if (scenario === "stale") state.rows[id].approve.dispatch("click");
    else if (scenario === "stale-failure") state.rows[id].approve.dispatch("click");
    else state.rows[id].approve.dispatch("click");
  } else if (scenario === "keyboard") {
    document.dispatch("keydown", { target: state.rows[id].tr, key: "a", preventDefault: function () {} });
  } else if (scenario === "bulk") {
    document.nodes["vc-bulk-veto"].dispatch("click");
  } else if (scenario === "filter-cleared-search") {
    var verdictFilter = document.nodes["vc-f-verdict"];
    verdictFilter.value = "unreviewed";
    verdictFilter.dispatch("change", { target: verdictFilter });
    var search = document.nodes["vc-search"];
    beforeSearch = search;
    search.value = "Second";
    search.selectionStart = 1;
    search.selectionEnd = 4;
    search.dispatch("input", { target: search });
    search.focus();
    beforeBulk = document.nodes["vc-bulk-veto"];
    beforeBulk.dispatch("click");
  } else if (scenario === "filter-cleared-class") {
    var classFilter = document.nodes["vc-f-classFacet"];
    beforeClassFilter = classFilter;
    classFilter.value = "weapons";
    classFilter.dispatch("change", { target: classFilter });
    var classSearch = document.nodes["vc-search"];
    beforeSearch = classSearch;
    classSearch.value = "Second";
    classSearch.selectionStart = 1;
    classSearch.selectionEnd = 4;
    classSearch.dispatch("input", { target: classSearch });
    classSearch.focus();
    beforeBulk = document.nodes["vc-bulk-veto"];
    beforeBulk.dispatch("click");
  } else if (scenario === "verdict-filter-approved" || scenario === "verdict-filter-vetoed" || scenario === "verdict-filter-unreviewed") {
    var filter = document.nodes["vc-f-verdict"];
    filter.value = scenario === "verdict-filter-approved" ? "approved" :
      (scenario === "verdict-filter-vetoed" ? "vetoed" : "unreviewed");
    filter.dispatch("change", { target: filter });
    beforeRow = state.rows[id].tr;
    beforeFocus = scenario === "verdict-filter-approved" ? state.rows[id].approve :
      (scenario === "verdict-filter-vetoed" ? state.rows[id].veto : state.rows[id].clear);
    beforeFocus.focus();
    beforeFocus.dispatch("click");
  } else if (scenario === "filter-cleared") {
    var clearedFilter = document.nodes["vc-f-verdict"];
    clearedFilter.value = "vetoed";
    clearedFilter.dispatch("change", { target: clearedFilter });
    beforeRow = state.rows[id].tr;
    beforeFocus = state.rows[id].clear;
    beforeFocus.focus();
    beforeFocus.dispatch("click");
  } else if (scenario === "upload-gate") {
    var input = document.nodes["vc-upload-weapons"];
    input.files = [{}];
    input.dispatch("change", { target: input });
    uploadBulkDisabled = document.nodes["vc-bulk-veto"].disabled;
    setTimeout(function () { document.nodes["vc-bulk-veto"].dispatch("click"); }, 15);
  } else if (scenario === "duplicate") {
    document.nodes["vc-view-duplicates"].dispatch("click");
    var duplicateSearch = document.nodes["vc-dup-search"];
    duplicateSearch.value = armorProposalId;
    duplicateSearch.dispatch("input", { target: duplicateSearch });
    // Two orientations register the same member id twice (once per matrix
    // table); every occurrence must repaint, disable, and freeze together
    // (#131) -- assertions below check the whole occurrence list, never a
    // fixed position.
    var duplicateCells = state.duplicateRows[armorProposalId].map(function (row) { return row.cell; });
    var armorUpload = document.nodes["vc-upload-armor"];
    armorUpload.files = [{}];
    armorUpload.dispatch("change", { target: armorUpload });
    setTimeout(function () {
      duplicateRejected = state.surface === "armor-duplicates" &&
        state.armorQuery.text === armorProposalId &&
        !document.nodes["vc-duplicates"].hidden &&
        document.nodes["vc-dup-search"].value === armorProposalId;
      state.duplicateRows[armorProposalId][0].approve.dispatch("click");
      duplicateGateDisabled = state.duplicateRows[armorProposalId].every(function (row) {
        return row.approve.disabled;
      });
      setTimeout(function () {
        var occurrences = state.duplicateRows[armorProposalId];
        duplicateRepainted = occurrences.length === duplicateCells.length &&
          occurrences.every(function (row, index) {
            return row.cell === duplicateCells[index] &&
              row.approve.getAttribute("aria-pressed") === "true";
          });
        document.nodes["vc-view-proposals"].dispatch("click");
        duplicateCrossViewVerdict = state.verdicts[armorProposalId];
        document.nodes["vc-view-duplicates"].dispatch("click");
        duplicateCrossViewPressed = state.duplicateRows[armorProposalId].map(function (row) {
          return row.approve.getAttribute("aria-pressed");
        });
        duplicateSurfacePreserved = state.surface === "armor-duplicates";
        duplicateSearchPreserved = state.armorQuery.text === armorProposalId;
        document.nodes["vc-finalize"].dispatch("click");
        setTimeout(function () {
          duplicateFinalizedDisabled = state.server_state === "finalized" &&
            state.duplicateRows[armorProposalId].every(function (row) {
              return row.approve.disabled && row.veto.disabled && row.clear.disabled;
            });
        }, 10);
      }, 5);
    }, 5);
  } else if (scenario === "finalize") {
    beforeFinalize = document.nodes["vc-finalize"];
    document.nodes["vc-finalize"].dispatch("click");
    setTimeout(function () {
      state.rows[id].approve.dispatch("click");
      document.nodes["vc-bulk-veto"].dispatch("click");
    }, 5);
  } else if (scenario === "finalize-missing" || scenario === "finalize-reject" ||
      scenario === "finalize-plural" || scenario === "finalize-zero" || scenario === "finalize-invalid-header" || scenario === "finalize-once" ||
      scenario === "finalize-once-missing" || scenario === "finalize-once-reject" ||
      scenario.indexOf("finalize-refetch-") === 0 || scenario.indexOf("finalize-body-") === 0) {
    beforeFinalize = document.nodes["vc-finalize"];
    document.nodes["vc-finalize"].dispatch("click");
    setTimeout(function () {
      state.rows[id].approve.dispatch("click");
      document.nodes["vc-bulk-veto"].dispatch("click");
      if (scenario === "finalize-refetch-pending") {
        pendingSessionNote = document.nodes["vc-session-note"].textContent;
        pendingReportResolve();
      }
      if (scenario === "finalize-missing" || scenario === "finalize-reject" ||
          scenario === "finalize-refetch-failure" || scenario === "finalize-body-http") {
        document.nodes["vc-download-again"].dispatch("click");
      }
    }, 15);
  } else if (scenario === "reset") {
    document.nodes["vc-reset"].dispatch("click");
  } else if (scenario === "shutdown") {
    document.nodes["vc-shutdown"].dispatch("click");
  }
  setTimeout(finish, scenario === "duplicate" ? 60 :
    (scenario === "upload-gate" ? 40 : (scenario.indexOf("finalize-") === 0 ? 40 : 10)));
}, 10);
'''


@pytest.mark.parametrize(
    ("scenario", "expected_path", "expected_verdict"),
    [
        ("single", "/api/verdicts", "approved"),
        ("keyboard", "/api/verdicts", "approved"),
        ("clear", "/api/verdicts", None),
        ("failure", "/api/verdicts", None),
        ("bulk", "/api/verdicts", "vetoed"),
        ("filter-cleared-search", "/api/verdicts", "vetoed"),
        ("filter-cleared-class", "/api/verdicts", "vetoed"),
        ("verdict-filter-approved", "/api/verdicts", "approved"),
        ("verdict-filter-vetoed", "/api/verdicts", "vetoed"),
        ("verdict-filter-unreviewed", "/api/verdicts", None),
        ("filter-cleared", "/api/verdicts", None),
        ("idle", "/api/report", None),
        ("stale", "/api/report", "vetoed"),
        ("stale-failure", "/api/report", None),
        ("upload-gate", "/api/verdicts", "vetoed"),
        ("duplicate", "/api/finalize", "approved"),
        ("finalize", "/api/finalize", "approved"),
        ("finalize-missing", "/api/finalize", "approved"),
        ("finalize-reject", "/api/finalize", "approved"),
        ("finalize-zero", "/api/finalize", "approved"),
        ("finalize-invalid-header", "/api/finalize", "approved"),
        ("finalize-refetch-failure", "/api/finalize", None),
        ("finalize-refetch-http", "/api/finalize", None),
        ("finalize-refetch-transport", "/api/finalize", None),
        ("finalize-refetch-pending", "/api/finalize", "approved"),
        ("finalize-refetch-unauthorized", "/api/finalize", None),
        ("finalize-refetch-illegal", "/api/finalize", None),
        ("finalize-refetch-incompatible", "/api/finalize", None),
        ("finalize-refetch-closed", "/api/finalize", "approved"),
        ("finalize-once", "/api/finalize", None),
        ("finalize-once-missing", "/api/finalize", None),
        ("finalize-once-reject", "/api/finalize", None),
        ("finalize-body-http", "/api/finalize", None),
        ("finalize-body-transport", "/api/finalize", None),
        ("finalize-body-unauthorized", "/api/finalize", None),
        ("finalize-body-illegal", "/api/finalize", None),
        ("finalize-body-incompatible", "/api/finalize", None),
        ("finalize-body-closed", "/api/finalize", "approved"),
        ("reset", "/api/reset", None),
        ("shutdown", "/api/shutdown", None),
    ],
)
def test_server_ui_mutation_workflow_uses_acknowledged_state_and_exact_routes(
    tmp_path: Path, scenario: str, expected_path: str, expected_verdict: str | None
):
    harness = tmp_path / f"server-ui-mutation-{scenario}.js"
    harness.write_text(MUTATION_HARNESS, encoding="utf-8")
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), scenario, str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert expected_path in result["paths"]
    if expected_verdict is None:
        assert result["verdicts"] == {}
    else:
        assert result["verdicts"]["18446744073709551615"] == expected_verdict
    if scenario in {"single", "keyboard"}:
        assert result["payload"] == {
            "report_revision": 1, "verdict_revision": 0,
            "fingerprint": "opaque-fingerprint",
            "decisions": [{"id": "18446744073709551615", "verdict": "approved"}],
        }
        if scenario == "single":
            assert result["row"]["same"] is True
            assert result["row"]["focused"] is True
        assert result["row"] is not None
        assert result["row"]["presentation"] == (
            "Approved this session · active persisted veto still suppresses this item"
        )
    if scenario == "clear":
        assert result["payload"]["decisions"] == [
            {"id": "18446744073709551615", "verdict": None}
        ]
    if scenario == "failure":
        assert "no" in result["status"]
    if scenario == "stale":
        assert result["paths"] == ["/api/report", "/api/verdicts", "/api/report"]
        assert "not applied" in result["status"]
    if scenario == "stale-failure":
        assert result["paths"] == ["/api/report", "/api/verdicts", "/api/report"]
        assert result["connected"] is False
        assert result["terminal"] is False
        assert result["reconnectVisible"] is True
        assert result["rowDisabled"] is True
        assert result["bulkDisabled"] is True
        assert "could not be fetched" in result["status"]
    if scenario == "upload-gate":
        assert result["paths"] == [
            "/api/report", "/api/exports/weapons", "/api/verdicts"
        ]
        assert result["uploadBulkDisabled"] is True
        assert result["bulkDisabled"] is False
        assert result["payload"]["decisions"] == [
            {"id": "18446744073709551615", "verdict": "vetoed"},
            {"id": "2", "verdict": "vetoed"},
        ]
    if scenario == "bulk":
        assert result["paths"] == ["/api/report", "/api/verdicts"]
        assert result["payload"]["decisions"] == [
            {"id": "18446744073709551615", "verdict": "vetoed"},
            {"id": "2", "verdict": "vetoed"},
        ]
    if scenario == "filter-cleared-search":
        assert result["paths"] == ["/api/report", "/api/verdicts"]
        assert result["filterValue"] == ""
        assert result["searchValue"] == "Second"
        assert result["searchFocused"] is True
        assert result["searchSelectionStart"] == 1
        assert result["searchSelectionEnd"] == 4
        assert result["queryVerdict"] == ""
        assert result["searchSame"] is True
        assert result["bulkSame"] is True
    if scenario == "filter-cleared-class":
        assert result["paths"] == ["/api/report", "/api/verdicts"]
        assert result["classFilterValue"] == ""
        assert result["queryClassFacet"] == ""
        assert result["viewInvalidated"] == ["filter classFacet weapons"]
        assert result["classFilterSame"] is True
        assert result["searchValue"] == "Second"
        assert result["searchFocused"] is True
        assert result["searchSelectionStart"] == 1
        assert result["searchSelectionEnd"] == 4
        assert result["searchSame"] is True
        assert result["bulkSame"] is True
        assert result["rowIds"] == ["2"]
    if scenario in {"verdict-filter-approved", "verdict-filter-vetoed", "verdict-filter-unreviewed"}:
        assert result["paths"] == ["/api/report", "/api/verdicts"]
        assert result["row"]["same"] is True
        assert result["row"]["focused"] is True
    if scenario == "filter-cleared":
        assert result["paths"] == ["/api/report", "/api/verdicts"]
        assert result["filterValue"] == ""
        assert result["rowIds"] == ["18446744073709551615", "2"]
    if scenario in {"idle", "reset"}:
        assert result["actionRole"] == "group"
        assert result["actionsReachable"] is True
        assert result["shutdownVisible"] is True
        assert result["idleHintVisible"] is True
    if scenario == "finalize-refetch-failure":
        assert result["paths"] == [
            "/api/report", "/api/finalize", "/api/report", "/api/finalized.csv"
        ]
        assert result["state"] == "finalized"
        assert result["connected"] is True
        assert result["terminal"] is False
        assert result["downloadDisabled"] is False
        assert result["resetDisabled"] is False
        assert result["shutdownDisabled"] is False
        assert result["reconnectVisible"] is False
        assert result["status"] == "Downloaded dim-import.csv again."
    if scenario in {"finalize-refetch-http", "finalize-refetch-transport"}:
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["state"] == "finalized"
        assert result["connected"] is False
        assert result["terminal"] is False
        assert result["downloadDisabled"] is False
        assert result["resetDisabled"] is True
        assert result["shutdownDisabled"] is True
        assert result["reconnectVisible"] is True
        assert "Finalisation succeeded" in result["status"]
        assert result["sessionNote"].startswith(
            "Finalisation succeeded. The reviewed CSV was produced"
        )
    if scenario == "finalize-refetch-pending":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["pendingSessionNote"] == (
            "Finalisation succeeded. The reviewed CSV was produced; this session is now frozen."
        )
        assert result["sessionNote"] == result["pendingSessionNote"]
    if scenario in {"finalize-refetch-unauthorized", "finalize-refetch-illegal", "finalize-refetch-incompatible"}:
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["state"] == "finalized"
        assert result["connected"] is False
        assert result["terminal"] is True
        assert result["downloadDisabled"] is True
        assert result["resetDisabled"] is True
        assert result["shutdownDisabled"] is True
        assert result["reconnectVisible"] is False
        assert result["sessionNote"].startswith(
            "Finalisation succeeded. The reviewed CSV was produced"
        )
    if scenario == "finalize-refetch-unauthorized":
        assert "authenticated session is unavailable" in result["status"]
    if scenario == "finalize-refetch-illegal":
        assert result["status"] == "session ended"
    if scenario == "finalize-refetch-incompatible":
        assert "incompatible response" in result["status"]
    if scenario == "finalize-refetch-closed":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["state"] == "closed"
        assert result["connected"] is False
        assert result["terminal"] is True
        assert result["reconnectVisible"] is False
        assert "session has ended" in result["status"]
    if scenario == "finalize-body-http":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report", "/api/finalized.csv"]
        assert result["state"] == "finalized"
        assert result["connected"] is True
        assert result["terminal"] is False
        assert result["downloadDisabled"] is False
        assert result["resetDisabled"] is False
        assert result["shutdownDisabled"] is False
    if scenario == "finalize-body-transport":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["state"] == "finalized"
        assert result["connected"] is False
        assert result["terminal"] is False
        assert result["downloadDisabled"] is False
        assert result["resetDisabled"] is True
        assert result["shutdownDisabled"] is True
        assert result["reconnectVisible"] is True
    if scenario in {"finalize-body-unauthorized", "finalize-body-illegal", "finalize-body-incompatible"}:
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["state"] == "finalized"
        assert result["connected"] is False
        assert result["terminal"] is True
        assert result["downloadDisabled"] is True
        assert result["resetDisabled"] is True
        assert result["shutdownDisabled"] is True
        assert result["reconnectVisible"] is False
        assert result["sessionNote"].startswith(
            "Finalisation succeeded. The reviewed CSV was produced"
        )
    if scenario == "finalize-body-unauthorized":
        assert "authenticated session is unavailable" in result["status"]
    if scenario == "finalize-body-illegal":
        assert result["status"] == "session ended"
    if scenario == "finalize-body-incompatible":
        assert "incompatible response" in result["status"]
    if scenario == "finalize-body-closed":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["state"] == "closed"
        assert result["connected"] is False
        assert result["terminal"] is True
        assert result["reconnectVisible"] is False
        assert "session has ended" in result["status"]
    if scenario == "finalize":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["revoked"] == 1
        assert result["downloads"] == ["dim-import.csv"]
        assert result["finalizeHeaders"] == {
            "reportRevision": "1", "verdictRevision": "1", "approvedStillVetoed": "1",
            "serveOnce": False
        }
        assert result["finalizeVisible"] is False
        assert result["rowDisabled"] is True
        assert result["bulkDisabled"] is True
        assert result["connected"] is True
        assert result["terminal"] is False
        assert result["downloadDisabled"] is False
        assert result["resetDisabled"] is False
        assert result["shutdownDisabled"] is False
        assert "1 approved item remains suppressed" in result["actionsText"]
    if scenario == "finalize-plural":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["finalizeHeaders"]["approvedStillVetoed"] == "2"
        assert "2 approved items remain suppressed" in result["actionsText"]
    if scenario == "finalize-zero":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["finalizeHeaders"]["approvedStillVetoed"] == "0"
        assert result["actionsText"].startswith(
            "Finalised — this review is frozen. The reviewed CSV has been produced."
        )
        assert "approved" not in result["actionsText"]
        assert "suppressed" not in result["actionsText"]
    if scenario == "finalize-invalid-header":
        assert result["paths"] == ["/api/report", "/api/finalize", "/api/report"]
        assert result["finalizeHeaders"]["approvedStillVetoed"] == "not-a-count"
        assert "approved" not in result["actionsText"]
        assert "suppressed" not in result["actionsText"]
    if scenario == "finalize-once":
        assert result["paths"] == ["/api/report", "/api/finalize"]
        assert result["state"] == "finalized"
        assert result["finalizeHeaders"] == {
            "reportRevision": "1", "verdictRevision": "1",
            "approvedStillVetoed": "1", "serveOnce": True
        }
        assert result["connected"] is False
        assert result["terminal"] is True
        assert result["reconnectVisible"] is False
        assert result["downloadDisabled"] is True
        assert result["resetDisabled"] is True
        assert result["shutdownDisabled"] is True
        assert "--once review server has stopped" in result["status"]
        assert "1 approved item remains suppressed" in result["actionsText"]
        assert result["sessionNote"].startswith(
            "Finalisation succeeded. The reviewed CSV was produced"
        )
    if scenario in {"finalize-once-missing", "finalize-once-reject"}:
        assert result["paths"] == ["/api/report", "/api/finalize"]
        assert result["state"] == "finalized"
        assert result["finalizeHeaders"] == {
            "reportRevision": "1", "verdictRevision": "1",
            "approvedStillVetoed": "1", "serveOnce": True
        }
        assert result["connected"] is False
        assert result["terminal"] is True
        assert result["reconnectVisible"] is False
        assert result["downloadDisabled"] is True
        assert result["resetDisabled"] is True
        assert result["shutdownDisabled"] is True
        assert "could not be read before the --once server stopped" in result["status"]
        assert "1 approved item remains suppressed" in result["actionsText"]
        assert result["sessionNote"].startswith(
            "Finalisation succeeded. The reviewed CSV was produced"
        )
    if scenario in {"finalize-missing", "finalize-reject"}:
        assert result["paths"] == [
            "/api/report", "/api/finalize", "/api/report", "/api/finalized.csv"
        ]
        assert result["state"] == "finalized"
        assert result["finalizeVisible"] is False
        assert result["rowDisabled"] is True
        assert result["bulkDisabled"] is True
        assert result["connected"] is True
        assert result["terminal"] is False
        assert result["downloadDisabled"] is False
        assert result["resetDisabled"] is False
        assert result["shutdownDisabled"] is False
        assert result["downloads"] == ["dim-import.csv"]
        assert result["finalizeHeaders"] == {
            "reportRevision": "1", "verdictRevision": "1",
            "approvedStillVetoed": "1", "serveOnce": False
        }
        assert result["status"] == "Downloaded dim-import.csv again."
        assert "1 approved item remains suppressed" in result["actionsText"]
    if scenario == "reset":
        assert result["payload"] == {"report_revision": 1, "verdict_revision": 0}
    if scenario == "shutdown":
        assert result["bodylessShutdown"]
        assert result["state"] == "closed"
    if scenario == "duplicate":
        assert result["paths"] == [
            "/api/report", "/api/exports/armor", "/api/verdicts",
            "/api/finalize", "/api/report"
        ]
        assert result["payload"] == {
            "report_revision": 1, "verdict_revision": 0,
            "fingerprint": "opaque-fingerprint",
            "decisions": [{"id": "9002", "verdict": "approved"}],
        }
        assert result["duplicate"] == {
            "rejectedPreserved": True,
            "gateDisabled": True,
            "repaintedInPlace": True,
            "crossViewVerdict": "approved",
            # Every registered occurrence (one per matrix orientation) must
            # repaint identically, not just the first (#131).
            "crossViewPressed": ["true", "true"],
            "surfacePreserved": True,
            "searchPreserved": True,
            "finalizedDisabled": True,
            "visible": True,
            "scopeText": result["duplicate"]["scopeText"],
            "groupText": result["duplicate"]["groupText"],
        }
        assert result["duplicate"]["scopeText"] == (
            '1 of 1 group · 3 of 3 pieces — filtered to search "9002"'
        )
        assert "Armor Plate" in result["duplicate"]["groupText"]


def test_same_stat_kind_state_and_reconciliation(tmp_path: Path):
    harness = tmp_path / "server-ui-same-stat-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
function exact() { return {group_kind: "exact_duplicate", group_id: "e", hash: "h",
  name: "Exact", preferred_survivor_id: "e1", members: [
    {id: "e1", disposition: "preferred_survivor"}
  ]}; }
function same(id, tuning) { return {group_kind: "same_stat", group_id: id, hash: "h",
  name: "Same", members: [{id: id + "1", tuning_mod_slot: tuning},
    {id: id + "2", tuning_mod_slot: "Health"}]}; }
function envelope(revision, exactGroups, sameGroups) {
  return {schema_version: 1, state: "reviewing", report_revision: revision,
    verdict_revision: revision, fingerprint: "fp-" + revision,
    snapshot: {sections: [{kind: "armor", decisions: [], armor: {
      exact_duplicate_groups: exactGroups || [], same_stat_groups: sameGroups || []
    }}]}, verdicts: [], override_status: []};
}
var state = server.createState();
server.applySessionEnvelope(envelope(1, [exact()], [same("s", "Weapons")]), state);
var mixed = state.armorGroups.map(function (group) { return group.groupKind; });
state.surface = "armor-duplicates"; state.armorGroupKind = "same_stat";
state.armorQuery.tuningModSlot = "Weapons";
var before = state.armorGroups;
server.applySessionEnvelope(envelope(2, [], [same("s", "Weapons")]), state);
var retained = state.armorGroupKind === "same_stat" &&
  state.armorQuery.tuningModSlot === "Weapons" && state.surface === "armor-duplicates";
server.applySessionEnvelope(envelope(3, [exact()], []), state);
var reset = state.armorGroupKind === "all" && state.surface === "armor-duplicates" &&
  state.armorQuery.tuningModSlot === "";
var malformed = envelope(4, [], [same("bad", "Weapons")]);
malformed.snapshot.sections[0].armor.same_stat_groups[0].members.push({id: "bad1"});
var adopted = true;
try { server.applySessionEnvelope(malformed, state); } catch (error) { adopted = false; }
process.stdout.write(JSON.stringify({mixed: mixed, mixedKinds: server.armorGroupKinds(before),
  sameOnly: server.armorGroupsForKind(before, "same_stat").length === 1,
  retained: retained, reset: reset, rejectedPreserved: !adopted && state.report_revision === 3}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "mixed": ["exact_duplicate", "same_stat"],
        "mixedKinds": {"exact": True, "same_stat": True},
        "sameOnly": True, "retained": True, "reset": True,
        "rejectedPreserved": True,
    }


def test_adapter_repaints_cross_kind_overlap_and_freezes_every_occurrence(
    tmp_path: Path,
):
    harness = tmp_path / "server-ui-same-stat-overlap-harness.js"
    harness.write_text(
        r'''
"use strict";
var fs = require("fs"), vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[3]);
var sharedId = "0009223372036854775808";

function Node(tag, document) {
  this.tagName = String(tag).toUpperCase(); this.ownerDocument = document;
  this.children = []; this.parentNode = null; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
  this.hidden = false; this.value = ""; this.files = [];
}
Node.prototype.querySelector = function (selector) {
  var wanted = selector.toLowerCase(), found = null;
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child;
      else visit(child);
    });
  }
  visit(this); return found;
};
Object.defineProperty(Node.prototype, "firstChild", {get: function () {
  return this.children[0] || null;
}});
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) {
  child.parentNode = this; this.children.push(child); return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child);
  if (index !== -1) this.children.splice(index, 1);
  child.parentNode = null; return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  if (name === "click" && this.disabled) return;
  event = event || {target: this, preventDefault: function () {}};
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.focus = function () { this.ownerDocument.activeElement = this; };
Node.prototype.click = function () {};

function Document() {
  this.nodes = Object.create(null); this.listeners = Object.create(null);
  this.activeElement = null; this.body = new Node("body", this);
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};

function response(payload) {
  return {ok: true, status: 200, json: function () { return Promise.resolve(payload); }};
}
function csvResponse() {
  return {ok: true, status: 200, headers: {get: function () { return null; }},
    arrayBuffer: function () { return Promise.resolve(new Uint8Array([65, 10]).buffer); }};
}
function groupEnvelope(verdicts, lifecycle) {
  return {schema_version: 1, state: lifecycle || "reviewing", report_revision: 1,
    verdict_revision: verdicts.length ? 1 : 0, fingerprint: "same-stat-fingerprint",
    snapshot: {sections: [{kind: "armor", decisions: [{id: sharedId, hash: "h",
      name: "Shared Plate", action: "review", reason: "armor-similar to"},
      {id: "exact-loser", hash: "h", name: "Exact loser", action: "junk",
        reason: "exact"}], armor: {
      exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "exact",
          hash: "h", name: "Exact Plate", type: "Chest Armor", guardian_class: "Hunter",
          item_archetype: "Gunner", tier: 5, stats: {}, tuning_mod_slot: "Weapons",
          preferred_survivor_id: sharedId, members: [
            {id: sharedId, location: "Vault", disposition: "preferred_survivor"},
          {id: "exact-loser", location: "Vault", disposition: "proposed_junk",
            proposal_action: "junk"}
          ]}],
      same_stat_groups: [{group_kind: "same_stat", group_id: "same", hash: "h",
        name: "Same Plate", type: "Chest Armor", guardian_class: "Hunter",
        item_archetype: "Gunner", tier: 5, stats: {}, members: [
          {id: sharedId, location: "Vault", tuning_stat: "Weapons",
           tuning_mod_slot: "Weapons"},
          {id: "other", location: "Vault", tuning_stat: "Health",
           tuning_mod_slot: "Health"}
        ]}]
    }}]}, verdicts: verdicts, override_status: []};
}
var queue = [response(groupEnvelope([], "reviewing")),
  response(groupEnvelope([{id: sharedId, verdict: "approved"}], "reviewing")),
  csvResponse(),
  response(groupEnvelope([{id: sharedId, verdict: "approved"}], "finalized"))];
var calls = [];
var document = new Document();
var context = {document: document, VaultCleanerReviewUI: shared, Promise: Promise, Set: Set,
  Blob: function () {}, URL: {createObjectURL: function () { return "blob:review"; },
    revokeObjectURL: function () {}}, confirm: function () { return true; },
  fetch: function (path) {
    calls.push(path); var next = queue.shift();
    return next instanceof Error ? Promise.reject(next) : Promise.resolve(next);
  }};
context.globalThis = context;
vm.runInNewContext(source, context);
setTimeout(function () {
  var server = context.VaultCleanerServerUI, state = server.state;
  document.nodes["vc-view-duplicates"].dispatch("click");
  // Two orientations register every occurrence twice, so sharedId (a member
  // of both the exact and the same-stat group) now has four occurrences.
  // Assertions below hold across every occurrence of each group kind, not a
  // fixed position (#131).
  var occurrences = state.duplicateRows[sharedId];
  var exactOccurrences = occurrences.filter(function (o) { return o.group.groupKind === "exact_duplicate"; });
  var sameOccurrences = occurrences.filter(function (o) { return o.group.groupKind === "same_stat"; });
  var before = {
    count: occurrences.length,
    exactReadOnly: exactOccurrences.every(function (o) { return o.approve === null; }),
    sameMutable: sameOccurrences.every(function (o) { return !!o.approve; })
  };
  sameOccurrences[0].approve.dispatch("click");
  var duringAck = {
    sameDisabled: sameOccurrences.every(function (o) { return o.approve.disabled; }),
    exactReadOnly: exactOccurrences.every(function (o) { return o.approve === null; })
  };
  setTimeout(function () {
    var afterAck = {
      verdict: state.verdicts[sharedId],
      samePressed: sameOccurrences.every(function (o) {
        return o.approve.getAttribute("aria-pressed") === "true";
      }),
      exactText: exactOccurrences.every(function (o) {
        return o.presentation.textContent === exactOccurrences[0].presentation.textContent;
      }) ? exactOccurrences[0].presentation.textContent : null,
      exactReadOnly: exactOccurrences.every(function (o) { return o.approve === null; })
    };
    document.nodes["vc-finalize"].dispatch("click");
    setTimeout(function () {
      process.stdout.write(JSON.stringify({before: before, duringAck: duringAck, afterAck: afterAck,
        finalized: state.server_state === "finalized" &&
          exactOccurrences.every(function (o) { return o.approve === null &&
            o.presentation.textContent.indexOf("Read-only") !== -1; }) &&
          sameOccurrences.every(function (o) {
            return o.approve.disabled && o.veto.disabled && o.clear.disabled;
          }),
        calls: calls}));
    }, 10);
  }, 10);
}, 10);
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        # count is 4: two occurrences (row + column orientation) per group,
        # across the two groups sharedId belongs to (#131).
        "before": {"count": 4, "exactReadOnly": True, "sameMutable": True},
        "duringAck": {"sameDisabled": True, "exactReadOnly": True},
        "afterAck": {
            "verdict": "approved", "samePressed": True,
            "exactText": "Read-onlyDisposition: Preferred survivorAlso proposed review in ProposalsCurrent verdict: approvedProposal reason: armor-similar to",
            "exactReadOnly": True,
        },
        "finalized": True,
        "calls": ["/api/report", "/api/verdicts", "/api/finalize", "/api/report"],
    }


def test_malformed_exact_group_kind_cannot_enter_same_stat_presentation(tmp_path: Path):
    harness = tmp_path / "server-ui-malformed-exact-kind-harness.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
function sameGroup() {
  return {group_kind: "same_stat", group_id: "safe", hash: "h", name: "Safe",
    members: [{id: "safe-one"}, {id: "safe-two"}]};
}
function malformedGroup() {
  return {group_kind: "same_stat", group_id: "hostile", hash: "h",
    name: "Hostile", preferred_survivor_id: "hostile-one", members: [
      {id: "hostile-one", disposition: "preferred_survivor"}
    ]};
}
function envelope(revision, group) {
  return {schema_version: 1, state: "reviewing", report_revision: revision,
    verdict_revision: 0, fingerprint: "fp-" + revision,
    snapshot: {sections: [{kind: "armor", decisions: [], armor: {
      exact_duplicate_groups: group ? [group] : [], same_stat_groups: [sameGroup()]
    }}]}, verdicts: [], override_status: []};
}
var state = server.createState();
server.applySessionEnvelope(envelope(1), state);
function rejected(group) {
  var accepted = true;
  try { server.applySessionEnvelope(envelope(2, group), state); }
  catch (error) { accepted = false; }
  return !accepted;
}
var wrongKindRejected = rejected(malformedGroup());
var missingKind = malformedGroup(); delete missingKind.group_kind;
var missingKindRejected = rejected(missingKind);
process.stdout.write(JSON.stringify({
  wrongKindRejected: wrongKindRejected, missingKindRejected: missingKindRejected,
  reportRevision: state.report_revision,
  sameStatGroupIds: server.armorGroupsForKind(state.armorGroups, "same_stat").map(function (group) {
    return group.groupId;
  }),
  exactGroupCount: server.armorGroupsForKind(state.armorGroups, "exact").length,
  hostileFilterCount: server.armorGroupsForKind(state.armorGroups, "same_stat").filter(function (group) {
    return group.groupId === "hostile";
  }).length
}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "wrongKindRejected": True, "missingKindRejected": True,
        "reportRevision": 1, "sameStatGroupIds": ["safe"],
        "exactGroupCount": 0, "hostileFilterCount": 0,
    }


def test_local_duplicate_kind_switch_renders_filter_reconciliation(tmp_path: Path):
    harness = tmp_path / "server-ui-local-duplicate-kind-harness.js"
    harness.write_text(
        r'''
"use strict";
var fs = require("fs"), vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[3]);
function Node(tag, document) {
  this.tagName = String(tag).toUpperCase(); this.ownerDocument = document;
  this.children = []; this.parentNode = null; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
  this.hidden = false; this.value = ""; this.selectionStart = 0;
  this.selectionEnd = 0; this.files = [];
}
Object.defineProperty(Node.prototype, "firstChild", {get: function () {
  return this.children[0] || null;
}});
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) {
  child.parentNode = this; this.children.push(child); return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child); if (index >= 0) this.children.splice(index, 1);
  child.parentNode = null; return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  event = event || {target: this, preventDefault: function () {}};
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null, wanted = selector.toLowerCase();
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child; else visit(child);
    });
  }
  visit(this); return found;
};
Node.prototype.focus = function () { this.ownerDocument.activeElement = this; };
function Document() {
  this.readyState = "interactive"; this.nodes = Object.create(null);
  this.listeners = Object.create(null); this.activeElement = null;
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
function envelope() {
  return {schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "local-filter", snapshot: {sections: [{
      kind: "armor", decisions: [], armor: {
        exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "collision",
          hash: "h", name: "Exact", tuning_mod_slot: "Weapons",
          preferred_survivor_id: "exact-survivor", members: [
            {id: "exact-survivor", disposition: "preferred_survivor"}
          ]}],
        same_stat_groups: [{group_kind: "same_stat", group_id: "collision",
          hash: "h", name: "Same", members: [
            {id: "same-one", tuning_mod_slot: "Weapons"},
            {id: "same-two", tuning_mod_slot: "Health"}
          ]}]
      }
    }]}, verdicts: [], override_status: []};
}
var calls = [], document = new Document();
var context = {document: document, VaultCleanerReviewUI: shared, Promise: Promise,
  Set: Set, setTimeout: setTimeout, fetch: function (path) {
    calls.push(path); return Promise.resolve({ok: true, status: 200,
      json: function () { return Promise.resolve(envelope()); }});
  }};
context.globalThis = context;
vm.runInNewContext(source, context);
setTimeout(function () {
  var server = context.VaultCleanerServerUI, state = server.state;
  document.nodes["vc-view-duplicates"].dispatch("click");
  state.viewInvalidated = ["server reconciliation notice"];
  state.reconciliation.invalidated = ["server reconciliation notice"];
  document.nodes["vc-dup-kind-same_stat"].dispatch("click");
  var preserved = {
    viewInvalidated: state.viewInvalidated.slice(),
    reconciliationInvalidated: state.reconciliation.invalidated.slice(),
    notice: document.nodes["vc-reconciliation"].textContent,
    noticeVisible: !document.nodes["vc-reconciliation"].hidden
  };
  var tuning = document.nodes["vc-dup-f-tuningModSlot"];
  tuning.value = "Health"; tuning.dispatch("change", {target: tuning});
  state.viewInvalidated = ["filter stale server value"];
  state.reconciliation.invalidated = ["filter stale server value"];
  var exact = document.nodes["vc-dup-kind-exact"];
  exact.focus(); exact.dispatch("click");
  process.stdout.write(JSON.stringify({
    calls: calls, kind: state.armorGroupKind,
    preserved: preserved,
    filter: state.armorQuery.tuningModSlot,
    viewInvalidated: state.viewInvalidated,
    reconciliationInvalidated: state.reconciliation.invalidated,
    notice: document.nodes["vc-reconciliation"].textContent,
    noticeVisible: !document.nodes["vc-reconciliation"].hidden,
    focusedId: document.activeElement && document.activeElement.getAttribute("id"),
    scope: document.nodes["vc-duplicate-scope"].textContent
  }));
}, 10);
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {
        "calls": ["/api/report"], "kind": "exact",
        "preserved": {
            "viewInvalidated": ["server reconciliation notice"],
            "reconciliationInvalidated": ["server reconciliation notice"],
            "notice": " Local view state dropped: server reconciliation notice.",
            "noticeVisible": True,
        },
        "filter": "",
        "viewInvalidated": ["duplicate filter tuningModSlot Health"],
        "reconciliationInvalidated": ["duplicate filter tuningModSlot Health"],
        "notice": " Local view state dropped: duplicate filter tuningModSlot Health.",
        "noticeVisible": True, "focusedId": "vc-dup-kind-exact",
        # renderList has no reconcile call of its own (#119 review): the kind
        # selector's click handler must reconcile armorQuery for the *new*
        # kind's group universe before it renders, so the scope suffix it
        # computes never names the tuningModSlot=Health facet that switching
        # to "exact" just dropped.
        "scope": "1 of 2 groups · 1 of 3 pieces — filtered to exact duplicates",
    }
    assert "Health" not in result["scope"]


def test_duplicate_facet_options_state_the_counted_noun(tmp_path: Path):
    """Every duplicate-surface facet option names what it counts (#118)."""
    harness = tmp_path / "server-ui-duplicate-facet-noun-harness.js"
    harness.write_text(
        r'''
"use strict";
var fs = require("fs"), vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[3]);
function Node(tag, document) {
  this.tagName = String(tag).toUpperCase(); this.ownerDocument = document;
  this.children = []; this.parentNode = null; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
  this.hidden = false; this.value = ""; this.selectionStart = 0;
  this.selectionEnd = 0; this.files = [];
}
Object.defineProperty(Node.prototype, "firstChild", {get: function () {
  return this.children[0] || null;
}});
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) {
  child.parentNode = this; this.children.push(child); return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child); if (index >= 0) this.children.splice(index, 1);
  child.parentNode = null; return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  event = event || {target: this, preventDefault: function () {}};
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null, wanted = selector.toLowerCase();
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child; else visit(child);
    });
  }
  visit(this); return found;
};
Node.prototype.focus = function () { this.ownerDocument.activeElement = this; };
function Document() {
  this.readyState = "interactive"; this.nodes = Object.create(null);
  this.listeners = Object.create(null); this.activeElement = null;
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
// Two groups, so a facet value shared by both is a plural count and a
// facet value unique to one group is a singular count. ``type`` is left
// unset on both groups, so it normalises to the same "none/unknown" value
// on both and exercises the plural case without inventing a shared value.
function envelope() {
  return {schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "facet-noun", snapshot: {sections: [{
      kind: "armor", decisions: [], armor: {
        exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "g-exact",
          hash: "h1", name: "Exact One", guardian_class: "Hunter",
          item_archetype: "Gunner", tuning_mod_slot: "Melee",
          preferred_survivor_id: "a-survivor", members: [
            {id: "a-survivor", disposition: "preferred_survivor"}
          ]}],
        same_stat_groups: [{group_kind: "same_stat", group_id: "g-same",
          hash: "h2", name: "Same One", guardian_class: "Titan",
          item_archetype: "Reaver", members: [
            {id: "b-one", tuning_mod_slot: "Melee"},
            {id: "b-two", tuning_mod_slot: "Health"}
          ]}]
      }
    }]}, verdicts: [], override_status: []};
}
var document = new Document();
var context = {document: document, VaultCleanerReviewUI: shared, Promise: Promise,
  Set: Set, setTimeout: setTimeout, fetch: function (path) {
    return Promise.resolve({ok: true, status: 200,
      json: function () { return Promise.resolve(envelope()); }});
  }};
context.globalThis = context;
vm.runInNewContext(source, context);
setTimeout(function () {
  document.nodes["vc-view-duplicates"].dispatch("click");
  function options(id) {
    return document.nodes[id].children.map(function (option) {
      return {value: option.getAttribute("value"), text: option.textContent};
    });
  }
  function textFor(id, value) {
    var matches = options(id).filter(function (option) { return option.value === value; });
    return matches.length ? matches[0].text : null;
  }
  process.stdout.write(JSON.stringify({
    guardianClassSingular: textFor("vc-dup-f-guardianClass", "Hunter"),
    guardianClassAllLabel: textFor("vc-dup-f-guardianClass", ""),
    typePlural: textFor("vc-dup-f-type", "none/unknown"),
    typeAllLabel: textFor("vc-dup-f-type", ""),
    itemArchetypeSingular: textFor("vc-dup-f-itemArchetype", "Reaver"),
    itemArchetypeAllLabel: textFor("vc-dup-f-itemArchetype", ""),
    tuningPlural: textFor("vc-dup-f-tuningModSlot", "Melee"),
    tuningSingular: textFor("vc-dup-f-tuningModSlot", "Health"),
    tuningAllLabel: textFor("vc-dup-f-tuningModSlot", "")
  }));
}, 10);
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "guardianClassSingular": "Hunter (1 group)",
        "guardianClassAllLabel": "any class",
        "typePlural": "none/unknown (2 groups)",
        "typeAllLabel": "any slot / type",
        "itemArchetypeSingular": "Reaver (1 group)",
        "itemArchetypeAllLabel": "any archetype",
        "tuningPlural": "Melee (2 pieces)",
        "tuningSingular": "Health (1 piece)",
        "tuningAllLabel": "any tuning slot",
    }


@pytest.mark.parametrize(
    ("case_name", "all_groups", "filtered_groups", "kind", "query", "expected"),
    [
        (
            "no filters",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            "all",
            {"guardianClass": "", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": ""},
            "2 groups · 5 pieces",
        ),
        (
            "kind exact",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "exact",
            {"guardianClass": "", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": ""},
            "1 of 2 groups · 2 of 5 pieces — filtered to exact duplicates",
        ),
        (
            "kind same_stat",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            "same_stat",
            {"guardianClass": "", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": ""},
            "1 of 2 groups · 3 of 5 pieces — filtered to same-stat groups",
        ),
        (
            "guardianClass only",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "all",
            {"guardianClass": "Titan", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": ""},
            "1 of 2 groups · 2 of 5 pieces — filtered to class Titan",
        ),
        (
            "type only",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "all",
            {"guardianClass": "", "type": "Chest Armor", "itemArchetype": "", "tuningModSlot": "", "text": ""},
            "1 of 2 groups · 2 of 5 pieces — filtered to slot Chest Armor",
        ),
        (
            "itemArchetype only",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "all",
            {"guardianClass": "", "type": "", "itemArchetype": "Gunner", "tuningModSlot": "", "text": ""},
            "1 of 2 groups · 2 of 5 pieces — filtered to archetype Gunner",
        ),
        (
            "tuningModSlot only",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "all",
            {"guardianClass": "", "type": "", "itemArchetype": "", "tuningModSlot": "Weapons", "text": ""},
            "1 of 2 groups · 2 of 5 pieces — filtered to tuning slot Weapons",
        ),
        (
            "text only",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "all",
            {"guardianClass": "", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": "Reaver"},
            '1 of 2 groups · 2 of 5 pieces — filtered to search "Reaver"',
        ),
        (
            "kind + all four facets + text",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "exact",
            {
                "guardianClass": "Titan",
                "type": "Chest Armor",
                "itemArchetype": "Gunner",
                "tuningModSlot": "Weapons",
                "text": "Reaver",
            },
            '1 of 2 groups · 2 of 5 pieces — filtered to exact duplicates, class Titan, slot Chest Armor, archetype Gunner, tuning slot Weapons, search "Reaver"',
        ),
        (
            "1 group · 2 pieces",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
            ],
            "all",
            {"guardianClass": "", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": ""},
            "1 group · 2 pieces",
        ),
        (
            "filtered, mixed-kind",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            "same_stat",
            {"guardianClass": "Hunter", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": ""},
            "1 of 2 groups · 3 of 5 pieces — filtered to same-stat groups, class Hunter",
        ),
        (
            # A filter that matches nothing (#119 review, H3): the scope
            # still states the "0 of N / 0 of M" totals rather than going
            # blank, since renderList writes this text before its early
            # return for the "no groups match" hint paragraph.
            "no matches",
            [
                {"groupKind": "exact_duplicate", "members": [{"id": "1"}, {"id": "2"}]},
                {"groupKind": "same_stat", "members": [{"id": "3"}, {"id": "4"}, {"id": "5"}]},
            ],
            [],
            "all",
            {"guardianClass": "", "type": "", "itemArchetype": "", "tuningModSlot": "", "text": "nope"},
            '0 of 2 groups · 0 of 5 pieces — filtered to search "nope"',
        ),
    ],
)
def test_duplicate_scope_summary_formats_exact_table(
    tmp_path: Path, case_name, all_groups, filtered_groups, kind, query, expected
):
    harness = tmp_path / "scope-test.js"
    harness.write_text(
        r'''
"use strict";
var server = require(process.argv[2]);
var allGroups = JSON.parse(process.argv[3]);
var filteredGroups = JSON.parse(process.argv[4]);
var kind = process.argv[5];
var query = JSON.parse(process.argv[6]);
var text = server.duplicateScopeText(allGroups, filteredGroups, kind, query);
process.stdout.write(JSON.stringify({text: text}));
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [
                NODE, str(harness), str(adapter),
                json.dumps(all_groups), json.dumps(filtered_groups),
                kind, json.dumps(query),
            ],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["text"] == expected


def test_duplicate_list_states_scope_before_the_empty_result_hint(tmp_path: Path):
    """renderList writes the scope line before its no-matches early return (#119 review, H3).

    A search that matches nothing must still leave the region stating the
    scope ("0 of N groups / 0 of M pieces ..."), alongside the
    "No armor duplicate groups match these filters." hint -- not blank.
    """
    harness = tmp_path / "server-ui-empty-duplicate-scope-harness.js"
    harness.write_text(
        r'''
"use strict";
var fs = require("fs"), vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[3]);
function Node(tag, document) {
  this.tagName = String(tag).toUpperCase(); this.ownerDocument = document;
  this.children = []; this.parentNode = null; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
  this.hidden = false; this.value = ""; this.selectionStart = 0;
  this.selectionEnd = 0; this.files = [];
}
Object.defineProperty(Node.prototype, "firstChild", {get: function () {
  return this.children[0] || null;
}});
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) {
  child.parentNode = this; this.children.push(child); return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child); if (index >= 0) this.children.splice(index, 1);
  child.parentNode = null; return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  event = event || {target: this, preventDefault: function () {}};
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null, wanted = selector.toLowerCase();
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child; else visit(child);
    });
  }
  visit(this); return found;
};
Node.prototype.focus = function () { this.ownerDocument.activeElement = this; };
function Document() {
  this.readyState = "interactive"; this.nodes = Object.create(null);
  this.listeners = Object.create(null); this.activeElement = null;
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
function envelope() {
  return {schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "local-filter", snapshot: {sections: [{
      kind: "armor", decisions: [], armor: {
        exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "collision",
          hash: "h", name: "Exact", tuning_mod_slot: "Weapons",
          preferred_survivor_id: "exact-survivor", members: [
            {id: "exact-survivor", disposition: "preferred_survivor"}
          ]}],
        same_stat_groups: [{group_kind: "same_stat", group_id: "collision",
          hash: "h", name: "Same", members: [
            {id: "same-one", tuning_mod_slot: "Weapons"},
            {id: "same-two", tuning_mod_slot: "Health"}
          ]}]
      }
    }]}, verdicts: [], override_status: []};
}
var document = new Document();
var context = {document: document, VaultCleanerReviewUI: shared, Promise: Promise,
  Set: Set, setTimeout: setTimeout, fetch: function (path) {
    return Promise.resolve({ok: true, status: 200,
      json: function () { return Promise.resolve(envelope()); }});
  }};
context.globalThis = context;
vm.runInNewContext(source, context);
setTimeout(function () {
  var server = context.VaultCleanerServerUI, state = server.state;
  document.nodes["vc-view-duplicates"].dispatch("click");
  var search = document.nodes["vc-dup-search"];
  search.value = "no-such-armor-piece";
  search.dispatch("input", {target: search});
  process.stdout.write(JSON.stringify({
    scope: document.nodes["vc-duplicate-scope"].textContent,
    listText: document.nodes["vc-duplicate-list"].textContent
  }));
}, 10);
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["scope"] == (
        '0 of 2 groups · 0 of 3 pieces — filtered to '
        'search "no-such-armor-piece"'
    )
    assert result["listText"] == "No armor duplicate groups match these filters."


def test_tab_and_segment_counts_and_section_headings(tmp_path: Path):
    """Surface tabs and the group-kind segment carry accurate counts (#131).

    Both the visible count chip and the accessible name must state the
    unfiltered total (proposals/groups, singular vs. plural correctly), and
    a mixed report renders both section headings, exact first.
    """
    harness = tmp_path / "server-ui-tab-segment-counts-harness.js"
    harness.write_text(
        r'''
"use strict";
var fs = require("fs"), vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[3]);
function Node(tag, document) {
  this.tagName = String(tag).toUpperCase(); this.ownerDocument = document;
  this.children = []; this.parentNode = null; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
  this.hidden = false; this.value = ""; this.selectionStart = 0;
  this.selectionEnd = 0; this.files = [];
}
Object.defineProperty(Node.prototype, "firstChild", {get: function () {
  return this.children[0] || null;
}});
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) {
  child.parentNode = this; this.children.push(child); return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child); if (index >= 0) this.children.splice(index, 1);
  child.parentNode = null; return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  event = event || {target: this, preventDefault: function () {}};
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null, wanted = selector.toLowerCase();
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child;
      else visit(child);
    });
  }
  visit(this); return found;
};
function Document() {
  this.nodes = Object.create(null); this.listeners = Object.create(null);
  this.activeElement = null; this.body = new Node("body", this);
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
  // Mirrors review_server.html's static class list: the adapter no longer
  // hard-assigns className on render (#131 P3-4), so the fake DOM must
  // start with the class the real static markup carries.
  this.nodes["vc-view-selector"].className = "panel view-selector tabs";
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
function hasClass(node, name) {
  return (String(node.className || "")).split(/\s+/).indexOf(name) !== -1;
}
function collect(node, predicate) {
  var result = [];
  (function walk(n) {
    if (predicate(n)) result.push(n);
    (n.children || []).forEach(walk);
  })(node);
  return result;
}
function response(payload) {
  return {ok: true, status: 200, json: function () { return Promise.resolve(payload); }};
}
var envelope = {schema_version: 1, state: "reviewing", report_revision: 1,
  verdict_revision: 0, fingerprint: "fp-counts",
  snapshot: {sections: [
    {kind: "weapons", decisions: [{id: "w1", hash: "h", action: "junk"}]},
    {kind: "armor", decisions: [
      {id: "a1", hash: "h", action: "junk"}, {id: "a2", hash: "h", action: "review"}
    ], armor: {
      exact_duplicate_groups: [{group_kind: "exact_duplicate", group_id: "e1", hash: "h",
        name: "Exact", preferred_survivor_id: "e-surv", members: [
          {id: "e-surv", disposition: "preferred_survivor"},
          {id: "a1", disposition: "proposed_junk", proposal_action: "junk"}
        ]}],
      same_stat_groups: [{group_kind: "same_stat", group_id: "s1", hash: "h", name: "Same",
        members: [{id: "a2", proposal_action: "review"}, {id: "other"}]}]
    }}
  ]}, verdicts: [], override_status: []};
var document = new Document();
var context = {document: document, VaultCleanerReviewUI: shared, Promise: Promise, Set: Set,
  fetch: function () { return Promise.resolve(response(envelope)); }};
context.globalThis = context;
vm.runInNewContext(source, context);
setTimeout(function () {
  var selector = document.nodes["vc-view-selector"];
  var proposalsButton = document.nodes["vc-view-proposals"];
  var duplicatesButton = document.nodes["vc-view-duplicates"];
  var before = {
    selectorClass: selector.className,
    proposalsCount: collect(proposalsButton, function (n) { return hasClass(n, "count"); })[0].textContent,
    proposalsLabel: proposalsButton.getAttribute("aria-label"),
    duplicatesCount: collect(duplicatesButton, function (n) { return hasClass(n, "count"); })[0].textContent,
    duplicatesLabel: duplicatesButton.getAttribute("aria-label")
  };
  duplicatesButton.dispatch("click");
  var segAll = document.nodes["vc-dup-kind-all"];
  var segExact = document.nodes["vc-dup-kind-exact"];
  var segSame = document.nodes["vc-dup-kind-same_stat"];
  var segment = {
    allCount: collect(segAll, function (n) { return hasClass(n, "count"); })[0].textContent,
    allLabel: segAll.getAttribute("aria-label"),
    exactCount: collect(segExact, function (n) { return hasClass(n, "count"); })[0].textContent,
    exactLabel: segExact.getAttribute("aria-label"),
    sameCount: collect(segSame, function (n) { return hasClass(n, "count"); })[0].textContent,
    sameLabel: segSame.getAttribute("aria-label")
  };
  var headings = collect(document.nodes["vc-duplicate-list"], function (n) {
    return hasClass(n, "armor-section-head");
  }).map(function (n) {
    return collect(n, function (c) { return c.tagName === "H3"; })[0].textContent;
  });
  process.stdout.write(JSON.stringify({before: before, segment: segment, headings: headings}));
}, 10);
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "before": {
            "selectorClass": "panel view-selector tabs",
            "proposalsCount": "3", "proposalsLabel": "Proposals (3 proposals)",
            "duplicatesCount": "2", "duplicatesLabel": "Armor duplicates (2 groups)",
        },
        "segment": {
            "allCount": "2", "allLabel": "All (2 groups)",
            "exactCount": "1", "exactLabel": "Exact (1 group)",
            "sameCount": "1", "sameLabel": "Same stats (1 group)",
        },
        "headings": ["Exact duplicates", "Same stats, different tuning"],
    }


def test_single_kind_report_renders_exactly_one_section_heading(tmp_path: Path):
    """A single-kind filtered result renders exactly one section heading (#131).

    Plan SS4/SS10 require a section heading only for kinds present in the
    current filtered result. The regression this guards against is real, not
    cosmetic: deleting the `if (!section.groups.length) return;` guard in
    `review_server.js`'s duplicate-list render makes an exact-only (or
    same-stat-only) report render a stray *empty* second section heading.
    Render each kind alone and assert both the heading count and both
    section rule lines verbatim, so a mutation of either the guard or either
    rule string fails this test.
    """
    harness = tmp_path / "server-ui-single-kind-heading-harness.js"
    harness.write_text(
        r'''
"use strict";
var fs = require("fs"), vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[3]);
function Node(tag, document) {
  this.tagName = String(tag).toUpperCase(); this.ownerDocument = document;
  this.children = []; this.parentNode = null; this.attributes = Object.create(null);
  this.listeners = Object.create(null); this._text = ""; this.disabled = false;
  this.hidden = false; this.value = ""; this.selectionStart = 0;
  this.selectionEnd = 0; this.files = [];
}
Object.defineProperty(Node.prototype, "firstChild", {get: function () {
  return this.children[0] || null;
}});
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) {
  child.parentNode = this; this.children.push(child); return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child); if (index >= 0) this.children.splice(index, 1);
  child.parentNode = null; return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  event = event || {target: this, preventDefault: function () {}};
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null, wanted = selector.toLowerCase();
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child;
      else visit(child);
    });
  }
  visit(this); return found;
};
function Document() {
  this.nodes = Object.create(null); this.listeners = Object.create(null);
  this.activeElement = null; this.body = new Node("body", this);
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
  // Mirrors review_server.html's static class list: the adapter no longer
  // hard-assigns className on render (#131 P3-4), so the fake DOM must
  // start with the class the real static markup carries.
  this.nodes["vc-view-selector"].className = "panel view-selector tabs";
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this); node.textContent = text; return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
function hasClass(node, name) {
  return (String(node.className || "")).split(/\s+/).indexOf(name) !== -1;
}
function collect(node, predicate) {
  var result = [];
  (function walk(n) {
    if (predicate(n)) result.push(n);
    (n.children || []).forEach(walk);
  })(node);
  return result;
}
function response(payload) {
  return {ok: true, status: 200, json: function () { return Promise.resolve(payload); }};
}
function buildEnvelope(exactOnly) {
  return {schema_version: 1, state: "reviewing", report_revision: 1,
    verdict_revision: 0, fingerprint: "fp-single-kind",
    snapshot: {sections: [
      {kind: "armor", decisions: [
        {id: "a1", hash: "h", action: "junk"}, {id: "a2", hash: "h", action: "review"}
      ], armor: {
        exact_duplicate_groups: exactOnly ? [{group_kind: "exact_duplicate", group_id: "e1",
          hash: "h", name: "Exact", preferred_survivor_id: "e-surv", members: [
            {id: "e-surv", disposition: "preferred_survivor"},
            {id: "a1", disposition: "proposed_junk", proposal_action: "junk"}
          ]}] : [],
        same_stat_groups: exactOnly ? [] : [{group_kind: "same_stat", group_id: "s1",
          hash: "h", name: "Same", members: [
            {id: "a2", proposal_action: "review"}, {id: "other"}
          ]}]
      }}
    ]}, verdicts: [], override_status: []};
}
function runCase(exactOnly, done) {
  var document = new Document();
  var context = {document: document, VaultCleanerReviewUI: shared, Promise: Promise, Set: Set,
    fetch: function () { return Promise.resolve(response(buildEnvelope(exactOnly))); }};
  context.globalThis = context;
  vm.runInNewContext(source, context);
  setTimeout(function () {
    document.nodes["vc-view-duplicates"].dispatch("click");
    var sections = collect(document.nodes["vc-duplicate-list"], function (n) {
      return hasClass(n, "armor-section-head");
    });
    done({
      headingCount: sections.length,
      entries: sections.map(function (n) {
        return {
          heading: collect(n, function (c) { return c.tagName === "H3"; })[0].textContent,
          rule: collect(n, function (c) { return hasClass(c, "rule"); })[0].textContent
        };
      })
    });
  }, 10);
}
runCase(true, function (exactOnly) {
  runCase(false, function (sameStatOnly) {
    process.stdout.write(JSON.stringify({exactOnly: exactOnly, sameStatOnly: sameStatOnly}));
  });
});
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "exactOnly": {
            "headingCount": 1,
            "entries": [{
                "heading": "Exact duplicates",
                "rule": "Same archetype, same stats, same tuning — one copy survives",
            }],
        },
        "sameStatOnly": {
            "headingCount": 1,
            "entries": [{
                "heading": "Same stats, different tuning",
                "rule": "Review only — the tool never picks your tuning for you",
            }],
        },
    }


def test_dim_query_adapter_integration_and_isolation(tmp_path: Path):
    harness = tmp_path / "server-ui-dim-query-harness.js"
    harness.write_text(
        r'''
"use strict";
var fs = require("fs"), vm = require("vm");
var source = fs.readFileSync(process.argv[2], "utf8");
var shared = require(process.argv[3]);

function Node(tag, document) {
  this.tagName = String(tag).toUpperCase();
  this.ownerDocument = document;
  this.children = [];
  this.parentNode = null;
  this.attributes = Object.create(null);
  this.listeners = Object.create(null);
  this._text = "";
  this.disabled = false;
  this.hidden = false;
  this.value = "";
  this.selectionStart = 0;
  this.selectionEnd = 0;
  this.files = [];
}
Object.defineProperty(Node.prototype, "firstChild", {get: function () {
  return this.children[0] || null;
}});
Object.defineProperty(Node.prototype, "textContent", {get: function () {
  return this._text + this.children.map(function (child) { return child.textContent; }).join("");
}, set: function (value) { this._text = String(value); this.children = []; }});
Node.prototype.appendChild = function (child) {
  child.parentNode = this;
  this.children.push(child);
  return child;
};
Node.prototype.removeChild = function (child) {
  var index = this.children.indexOf(child);
  if (index >= 0) this.children.splice(index, 1);
  child.parentNode = null;
  return child;
};
Node.prototype.setAttribute = function (name, value) {
  this.attributes[name] = String(value);
  if (name === "id") this.ownerDocument.nodes[String(value)] = this;
};
Node.prototype.getAttribute = function (name) {
  return this.attributes[name] === undefined ? null : this.attributes[name];
};
Node.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};
Node.prototype.dispatch = function (name, event) {
  event = event || {target: this, preventDefault: function () {}};
  event.target = event.target || this;
  (this.listeners[name] || []).forEach(function (callback) { callback(event); });
};
Node.prototype.querySelector = function (selector) {
  var found = null, wanted = selector.toLowerCase();
  function visit(node) {
    if (found) return;
    (node.children || []).forEach(function (child) {
      if (found) return;
      if (child.tagName.toLowerCase() === wanted) found = child;
      else visit(child);
    });
  }
  visit(this);
  return found;
};

function Document() {
  this.nodes = Object.create(null);
  this.listeners = Object.create(null);
  this.activeElement = null;
  this.body = new Node("body", this);
  ["vc-status", "vc-report", "vc-filters", "vc-proposals", "vc-fingerprint",
   "vc-summary", "vc-overrides", "vc-reconciliation", "vc-session-note",
   "vc-actions", "vc-controls", "vc-list", "vc-upload-weapons",
   "vc-upload-armor", "vc-upload-ghosts", "vc-upload-status-weapons",
   "vc-upload-status-armor", "vc-upload-status-ghosts", "vc-view-selector",
   "vc-duplicates", "vc-duplicate-scope", "vc-duplicate-list"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
  this.nodes["vc-view-selector"].className = "panel view-selector tabs";
}
Document.prototype.getElementById = function (id) { return this.nodes[id] || null; };
Document.prototype.createElement = function (tag) { return new Node(tag, this); };
Document.prototype.createTextNode = function (text) {
  var node = new Node("#text", this);
  node.textContent = text;
  return node;
};
Document.prototype.addEventListener = function (name, callback) {
  (this.listeners[name] || (this.listeners[name] = [])).push(callback);
};

function hasClass(node, name) {
  return (String(node.className || "")).split(/\s+/).indexOf(name) !== -1;
}
function collect(node, predicate) {
  var result = [];
  (function walk(n) {
    if (predicate(n)) result.push(n);
    (n.children || []).forEach(walk);
  })(node);
  return result;
}
function response(payload) {
  return {ok: true, status: 200, json: function () { return Promise.resolve(payload); }};
}

var envelope = {
  schema_version: 1,
  state: "reviewing",
  report_revision: 1,
  verdict_revision: 0,
  fingerprint: "fp-dim-query",
  snapshot: {
    sections: [
      {
        kind: "armor",
        decisions: [
          {id: "1002", hash: "h-exact", action: "junk"},
          {id: "2001", hash: "h-same", action: "junk"}
        ],
        armor: {
          exact_duplicate_groups: [
            {
              group_kind: "exact_duplicate",
              group_id: "exact-fero",
              hash: "h-exact",
              name: "Feropotent Bond",
              type: "Warlock Bond",
              guardian_class: "Warlock",
              item_archetype: "Tuning A",
              tier: 5,
              stats: {weapons: 30, health: 25, class: 20},
              tuning_mod_slot: "Weapons",
              seasonal_mod: "",
              holofoil: "",
              spirit_signature: [],
              preferred_survivor_id: "1001",
              members: [
                {id: "1001", location: "Vault", disposition: "preferred_survivor"},
                {id: "1002", location: "Vault", disposition: "proposed_junk", proposal_action: "junk"}
              ]
            },
            {
              group_kind: "exact_duplicate",
              group_id: "exact-empty",
              hash: "h-empty",
              name: "Empty Junk Group",
              type: "Chest Armor",
              guardian_class: "Titan",
              item_archetype: "Gunner",
              tier: 5,
              stats: {weapons: 30, health: 25, class: 20},
              tuning_mod_slot: "Weapons",
              seasonal_mod: "",
              holofoil: "",
              spirit_signature: [],
              preferred_survivor_id: "3001",
              members: [
                {id: "3001", location: "Vault", disposition: "preferred_survivor"},
                {id: "3002", location: "Vault", disposition: "retained_protected", protection_level: "hard"}
              ]
            }
          ],
          same_stat_groups: [
            {
              group_kind: "same_stat",
              group_id: "same-fero",
              hash: "h-same",
              name: "Feropotent Bond",
              type: "Warlock Bond",
              guardian_class: "Warlock",
              item_archetype: "Tuning B",
              tier: 5,
              stats: {weapons: 30, health: 25, class: 20},
              spirit_signature: [],
              preferred_survivor_id: null,
              members: [
                {id: "2001", location: "Vault", tuning_stat: "Weapons", tuning_mod_slot: "Weapons"},
                {id: "2002", location: "Vault", tuning_stat: "Health", tuning_mod_slot: "Health"}
              ]
            }
          ]
        }
      }
    ]
  },
  verdicts: [],
  override_status: []
};

var fetchCalls = 0;
var document = new Document();
var context = {
  document: document,
  VaultCleanerReviewUI: shared,
  Promise: Promise,
  Set: Set,
  fetch: function () {
    fetchCalls++;
    return Promise.resolve(response(envelope));
  }
};
context.globalThis = context;
vm.runInNewContext(source, context);

setTimeout(function () {
  var duplicatesButton = document.nodes["vc-view-duplicates"];
  duplicatesButton.dispatch("click");

  var groups = collect(document.nodes["vc-duplicate-list"], function (n) {
    return hasClass(n, "armor-group");
  });
  var exactFero = groups[0];
  var exactEmpty = groups[1];
  var sameFero = groups[2];

  var server = context.VaultCleanerServerUI;
  var state = server.state;

  function captureRequiredState() {
    return {
      verdicts: JSON.stringify(state.verdicts),
      report_revision: state.report_revision,
      verdict_revision: state.verdict_revision,
      mutationInFlight: state.mutationInFlight,
      duplicateRowsKeys: Object.keys(state.duplicateRows || {}).sort().join(","),
      duplicateRowsRef: state.duplicateRows,
      fetchCalls: fetchCalls
    };
  }

  function assertStateUnchanged(before, label) {
    var after = captureRequiredState();
    if (before.verdicts !== after.verdicts) {
      throw new Error(label + ": verdicts changed: " + before.verdicts + " vs " + after.verdicts);
    }
    if (before.report_revision !== after.report_revision) {
      throw new Error(label + ": report_revision changed: " + before.report_revision + " vs " + after.report_revision);
    }
    if (before.verdict_revision !== after.verdict_revision) {
      throw new Error(label + ": verdict_revision changed: " + before.verdict_revision + " vs " + after.verdict_revision);
    }
    if (before.mutationInFlight !== after.mutationInFlight) {
      throw new Error(label + ": mutationInFlight changed: " + before.mutationInFlight + " vs " + after.mutationInFlight);
    }
    if (before.duplicateRowsKeys !== after.duplicateRowsKeys) {
      throw new Error(label + ": duplicateRowsKeys changed: " + before.duplicateRowsKeys + " vs " + after.duplicateRowsKeys);
    }
    if (before.duplicateRowsRef !== after.duplicateRowsRef) {
      throw new Error(label + ": duplicateRows reference changed");
    }
    if (before.fetchCalls !== after.fetchCalls) {
      throw new Error(label + ": fetchCalls changed: " + before.fetchCalls + " vs " + after.fetchCalls);
    }
  }

  var exactFeroBtns = collect(exactFero, function (n) { return hasClass(n, "dim-query-btn"); });
  var sameFeroBtns = collect(sameFero, function (n) { return hasClass(n, "dim-query-btn"); });
  var exactEmptyBtns = collect(exactEmpty, function (n) { return hasClass(n, "dim-query-btn"); });

  var initialFetchCalls = fetchCalls;

  // 1. Reviewing & connected state: snapshot and compare state around both controls on each group
  var snap = captureRequiredState();
  sameFeroBtns[0].dispatch("click");
  var sameFeroTextareaWhole = collect(sameFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "reviewing sameFero whole");

  snap = captureRequiredState();
  sameFeroBtns[1].dispatch("click");
  var sameFeroTextareaJunk = collect(sameFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "reviewing sameFero junk");

  snap = captureRequiredState();
  exactFeroBtns[0].dispatch("click");
  var exactFeroTextareaWhole = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "reviewing exactFero whole");

  snap = captureRequiredState();
  exactFeroBtns[1].dispatch("click");
  var exactFeroTextareaJunk = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "reviewing exactFero junk");

  var emptyHint = collect(exactEmpty, function (n) { return hasClass(n, "dim-query-empty-hint"); })[0].textContent;
  var emptyJunkDisabled = exactEmptyBtns[1].disabled;

  // 2. Disconnected state while reviewing: snapshot and compare state around both controls
  state.connected = false;
  var disconnectedReviewingConnected = state.connected;
  var disconnectedReviewingState = state.server_state;

  snap = captureRequiredState();
  exactFeroBtns[0].dispatch("click");
  var exactWholeDisconnected = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "disconnected exactFero whole");

  snap = captureRequiredState();
  exactFeroBtns[1].dispatch("click");
  var exactJunkDisconnected = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "disconnected exactFero junk");

  snap = captureRequiredState();
  sameFeroBtns[0].dispatch("click");
  var sameWholeDisconnected = collect(sameFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "disconnected sameFero whole");

  snap = captureRequiredState();
  sameFeroBtns[1].dispatch("click");
  var sameJunkDisconnected = collect(sameFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "disconnected sameFero junk");

  // 3. Finalized state: transition via applySessionEnvelope, snapshot and compare state around both controls
  var finalizedEnvelope = JSON.parse(JSON.stringify(envelope));
  finalizedEnvelope.state = "finalized";
  server.applySessionEnvelope(finalizedEnvelope, state);
  var finalizedState = state.server_state;
  var finalizedConnected = state.connected;

  snap = captureRequiredState();
  exactFeroBtns[0].dispatch("click");
  var exactWholeFinalized = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "finalized exactFero whole");

  snap = captureRequiredState();
  exactFeroBtns[1].dispatch("click");
  var exactJunkFinalized = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "finalized exactFero junk");

  snap = captureRequiredState();
  sameFeroBtns[0].dispatch("click");
  var sameWholeFinalized = collect(sameFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "finalized sameFero whole");

  snap = captureRequiredState();
  sameFeroBtns[1].dispatch("click");
  var sameJunkFinalized = collect(sameFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "finalized sameFero junk");

  // 4. Finalized AND disconnected state: snapshot and compare state around both controls
  state.connected = false;
  var finalizedDisconnectedState = state.server_state;
  var finalizedDisconnectedConnected = state.connected;

  snap = captureRequiredState();
  exactFeroBtns[0].dispatch("click");
  var exactWholeFinalizedDisconnected = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "finalized disconnected exactFero whole");

  snap = captureRequiredState();
  exactFeroBtns[1].dispatch("click");
  var exactJunkFinalizedDisconnected = collect(exactFero, function (n) { return n.tagName === "TEXTAREA"; })[0].textContent;
  assertStateUnchanged(snap, "finalized disconnected exactFero junk");

  process.stdout.write(JSON.stringify({
    groupCount: groups.length,
    exactFeroBtnCount: exactFeroBtns.length,
    sameFeroBtnCount: sameFeroBtns.length,
    exactEmptyBtnCount: exactEmptyBtns.length,
    sameFeroTextareaWhole: sameFeroTextareaWhole,
    sameFeroTextareaJunk: sameFeroTextareaJunk,
    exactFeroTextareaWhole: exactFeroTextareaWhole,
    exactFeroTextareaJunk: exactFeroTextareaJunk,
    emptyHint: emptyHint,
    emptyJunkDisabled: emptyJunkDisabled,
    initialFetchCalls: initialFetchCalls,
    fetchCallsDuringGeneration: fetchCalls - initialFetchCalls,
    disconnectedReviewingState: disconnectedReviewingState,
    disconnectedReviewingConnected: disconnectedReviewingConnected,
    exactWholeDisconnected: exactWholeDisconnected,
    exactJunkDisconnected: exactJunkDisconnected,
    sameWholeDisconnected: sameWholeDisconnected,
    sameJunkDisconnected: sameJunkDisconnected,
    finalizedState: finalizedState,
    finalizedConnected: finalizedConnected,
    exactWholeFinalized: exactWholeFinalized,
    exactJunkFinalized: exactJunkFinalized,
    sameWholeFinalized: sameWholeFinalized,
    sameJunkFinalized: sameJunkFinalized,
    finalizedDisconnectedState: finalizedDisconnectedState,
    finalizedDisconnectedConnected: finalizedDisconnectedConnected,
    exactWholeFinalizedDisconnected: exactWholeFinalizedDisconnected,
    exactJunkFinalizedDisconnected: exactJunkFinalizedDisconnected
  }));
}, 10);
''',
        encoding="utf-8",
    )
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    shared_resource = files("vault_cleaner.ui").joinpath("review_ui.js")
    with as_file(resource) as adapter, as_file(shared_resource) as presentation:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), str(presentation)],
            capture_output=True, encoding="utf-8", check=False, timeout=60,
        )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result == {
        "groupCount": 3,
        "exactFeroBtnCount": 2,
        "sameFeroBtnCount": 2,
        "exactEmptyBtnCount": 2,
        "sameFeroTextareaWhole": "id:2001 or id:2002",
        "sameFeroTextareaJunk": "id:2001",
        "exactFeroTextareaWhole": "id:1001 or id:1002",
        "exactFeroTextareaJunk": "id:1002",
        "emptyHint": "This group has no junk candidates.",
        "emptyJunkDisabled": True,
        "initialFetchCalls": 1,
        "fetchCallsDuringGeneration": 0,
        "disconnectedReviewingState": "reviewing",
        "disconnectedReviewingConnected": False,
        "exactWholeDisconnected": "id:1001 or id:1002",
        "exactJunkDisconnected": "id:1002",
        "sameWholeDisconnected": "id:2001 or id:2002",
        "sameJunkDisconnected": "id:2001",
        "finalizedState": "finalized",
        "finalizedConnected": True,
        "exactWholeFinalized": "id:1001 or id:1002",
        "exactJunkFinalized": "id:1002",
        "sameWholeFinalized": "id:2001 or id:2002",
        "sameJunkFinalized": "id:2001",
        "finalizedDisconnectedState": "finalized",
        "finalizedDisconnectedConnected": False,
        "exactWholeFinalizedDisconnected": "id:1001 or id:1002",
        "exactJunkFinalizedDisconnected": "id:1002",
    }
