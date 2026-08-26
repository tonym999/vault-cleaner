"""Exercise the browser server adapter without a browser dependency."""

from __future__ import annotations

import json
import shutil
import subprocess
from importlib.resources import as_file, files
from pathlib import Path

import pytest

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
