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


def test_server_adapter_has_no_content_length_or_inline_dom_html():
    resource = files("vault_cleaner.ui").joinpath("review_server.js")
    with as_file(resource) as adapter:
        source = adapter.read_text(encoding="utf-8")
    assert "Content-Length" not in source
    assert "innerHTML" not in source
    assert "text/csv" in source
    assert "/api/finalize" not in source
    assert "/api/verdicts" not in source
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
