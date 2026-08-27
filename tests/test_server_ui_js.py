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
state.query.owner = "missing-owner";
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
  owner: state.query.owner,
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
        "owner": "",
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
  vm.runInNewContext(source, context);
  var api = context.VaultCleanerServerUI;
  return new Promise(function (resolve) {
    setTimeout(function () {
      if (upload || scenario === "ordinary") {
        var input = document.nodes["vc-upload-weapons"];
        input.files = [{}];
        input.dispatch("change");
      }
      setTimeout(function () {
        resolve({
          sameObject: api === context.VaultCleanerServerUI,
          connected: api.state.connected,
          terminal: api.state.terminal,
          mainStatus: document.nodes["vc-status"].textContent,
          uploadPhase: api.state.uploadStatus.weapons,
          uploadStatus: document.nodes["vc-upload-status-weapons"].textContent
        });
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
    with as_file(resource) as adapter:
        completed = subprocess.run(
            [NODE, str(harness), str(adapter), scenario],
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
   "vc-upload-status-armor", "vc-upload-status-ghosts"].forEach(function (id) {
    this.nodes[id] = new Node("div", this);
  }, this);
  this.nodes["vc-actions"].setAttribute("role", "group");
  this.main.appendChild(this.nodes["vc-actions"]);
  this.main.appendChild(this.nodes["vc-report"]);
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
function envelope(verdictRevision, verdicts, state) {
  return { schema_version: 1, state: state || "reviewing", report_revision: 1,
    verdict_revision: verdictRevision, fingerprint: "opaque-fingerprint",
    snapshot: { sections: [{ kind: "weapons", decisions: [
      { id: id, hash: "18446744073709551614", name: "<img>", owner: "Titan",
        action: "junk", reason: "dupe-lower" },
      { id: "2", hash: "500", name: "Second", owner: "Hunter",
        action: "review", reason: "wishlist" }
    ] }] }, verdicts: verdicts || [],
    override_status: [{ id: id, status: "active", detail: "suppresses this item" }] };
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
    sessionNote: document.nodes["vc-session-note"].textContent,
    searchValue: document.nodes["vc-search"] ? document.nodes["vc-search"].value : null,
    searchFocused: document.activeElement === document.nodes["vc-search"],
    searchSelectionStart: document.nodes["vc-search"] ? document.nodes["vc-search"].selectionStart : null,
    searchSelectionEnd: document.nodes["vc-search"] ? document.nodes["vc-search"].selectionEnd : null,
    queryVerdict: state.query.verdict,
    searchSame: document.nodes["vc-search"] === beforeSearch,
    bulkSame: document.nodes["vc-bulk-veto"] === beforeBulk,
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
  var payloadCall = calls.filter(function (call) { return call.path === "/api/verdicts" || call.path === "/api/reset"; })[0];
  if (payloadCall && payloadCall.options && payloadCall.options.body) output.payload = JSON.parse(payloadCall.options.body);
  process.stdout.write(JSON.stringify(output));
}
var beforeRow = null, beforeFocus = null, beforeFinalize = null, uploadBulkDisabled = null;
var beforeSearch = null, beforeBulk = null;
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
  setTimeout(finish, scenario === "upload-gate" ? 40 : (scenario.indexOf("finalize-") === 0 ? 40 : 10));
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
        ("verdict-filter-approved", "/api/verdicts", "approved"),
        ("verdict-filter-vetoed", "/api/verdicts", "vetoed"),
        ("verdict-filter-unreviewed", "/api/verdicts", None),
        ("filter-cleared", "/api/verdicts", None),
        ("idle", "/api/report", None),
        ("stale", "/api/report", "vetoed"),
        ("stale-failure", "/api/report", None),
        ("upload-gate", "/api/verdicts", "vetoed"),
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
