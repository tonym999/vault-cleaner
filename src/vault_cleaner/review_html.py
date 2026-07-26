"""Render the self-contained static HTML review artifact (#37).

The browser reviews decisions; it never re-runs rules, edits config, or writes
the DIM CSV. The only thing it hands back is a review manifest, and
`review.parse_manifest` re-validates that from scratch — nothing the page
produces is authoritative.

The artifact is one file with inline CSS/JS and no network access of any kind,
so it works from `file://` and cannot phone home with the vault data it
carries. Output is deterministic for a given run: no timestamps, no ids
derived from the clock, so two renders of the same report are byte-identical.
"""

from __future__ import annotations

from pathlib import Path

from vault_cleaner.report_run import ReportRun, snapshot_json

DEFAULT_REVIEW_HTML = "data/out/vault-review.html"

PRIVACY_WARNING = (
    "This file embeds personal vault metadata — item names, instance ids, "
    "notes, and character names. Treat it like your DIM export: keep it local, "
    "and do not publish, paste, or attach it anywhere."
)

# `default-src 'none'` is the load-bearing part: no fonts, scripts, styles,
# images, or connections can be fetched, so the page cannot exfiltrate the
# vault data it carries. Inline script/style are allowed by necessity — a nonce
# cannot survive a file the user re-opens from disk, and hashing the blocks
# would silently break the whole artifact on any whitespace drift.
CSP = (
    "default-src 'none'; "
    "script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; "
    "connect-src 'none'; "
    "form-action 'none'; "
    "base-uri 'none'"
)

SNAPSHOT_ELEMENT_ID = "vc-snapshot"
APP_ELEMENT_ID = "vc-app"

CSS = """
:root {
  color-scheme: light dark;
  --bg: #f6f7f9;
  --panel: #ffffff;
  --ink: #16181d;
  --muted: #5b6270;
  --line: #d8dce4;
  --accent: #2f5bd7;
  --junk: #a8321f;
  --review: #8a5a00;
  --veto: #7a1f1f;
  --veto-bg: #fdeceb;
  --approve: #17603a;
  --approve-bg: #e8f5ee;
  --warn-bg: #fff6da;
  --warn-line: #d9b445;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14161a;
    --panel: #1d2027;
    --ink: #e9ebf0;
    --muted: #a2aab8;
    --line: #333844;
    --accent: #8fabff;
    --junk: #ff9d8a;
    --review: #ffd166;
    --veto: #ffb3ab;
    --veto-bg: #3a1f1d;
    --approve: #9fe3bd;
    --approve-bg: #13301f;
    --warn-bg: #33290c;
    --warn-line: #7a6320;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0 0 4rem;
  background: var(--bg);
  color: var(--ink);
  font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
}
.wrap { max-width: 78rem; margin: 0 auto; padding: 1rem; }
h1 { font-size: 1.35rem; margin: 0 0 .25rem; }
h2 { font-size: 1rem; margin: 0 0 .5rem; }
h3 { font-size: .9rem; margin: .6rem 0 .2rem; }
p { margin: .35rem 0; }
a { color: var(--accent); }
code, .mono, kbd {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
kbd {
  border: 1px solid var(--line); border-radius: 3px; padding: 0 .25rem;
  font-size: .85em;
}
.skip {
  position: absolute; left: -9999px; top: 0; background: var(--panel);
  padding: .5rem .75rem; z-index: 10;
}
.skip:focus { left: .5rem; top: .5rem; }
.panel {
  background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
  padding: .85rem 1rem; margin-bottom: 1rem;
}
.privacy {
  background: var(--warn-bg); border: 1px solid var(--warn-line);
  border-radius: 8px; padding: .75rem 1rem; margin-bottom: 1rem;
}
.privacy strong { display: block; margin-bottom: .2rem; }
.sub { color: var(--muted); font-size: .85rem; }
.tiles { display: flex; flex-wrap: wrap; gap: .75rem; }
.tile {
  border: 1px solid var(--line); border-radius: 6px; padding: .5rem .7rem;
  min-width: 11rem; flex: 1 1 11rem;
}
.tile .n { font-size: 1.3rem; font-weight: 600; display: block; }
.tile .k {
  color: var(--muted); font-size: .8rem; text-transform: uppercase;
  letter-spacing: .04em;
}
.dirty { color: var(--veto); font-weight: 600; }
.clean { color: var(--muted); }
.controls { display: flex; flex-wrap: wrap; gap: .6rem .8rem; align-items: flex-end; }
.field { display: flex; flex-direction: column; gap: .2rem; }
.field > span { font-size: .78rem; color: var(--muted); }
input[type="search"], input[type="file"], select, textarea {
  font: inherit; color: inherit; background: var(--bg);
  border: 1px solid var(--line); border-radius: 5px; padding: .35rem .45rem;
}
input[type="search"] { min-width: 14rem; }
textarea { width: 100%; min-height: 8rem; }
button {
  font: inherit; color: inherit; background: var(--bg); cursor: pointer;
  border: 1px solid var(--line); border-radius: 5px; padding: .35rem .6rem;
  text-align: left;
}
button:hover { border-color: var(--accent); }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 1px; }
.row-actions { display: flex; gap: .3rem; }
button.veto[aria-pressed="true"] {
  background: var(--veto-bg); border-color: var(--veto); color: var(--veto);
  font-weight: 600;
}
button.approve[aria-pressed="true"] {
  background: var(--approve-bg); border-color: var(--approve);
  color: var(--approve); font-weight: 600;
}
.scroller { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; min-width: 52rem; }
th, td {
  text-align: left; padding: .35rem .5rem; border-bottom: 1px solid var(--line);
  vertical-align: top;
}
th { font-size: .8rem; color: var(--muted); white-space: nowrap; }
th button {
  background: none; border: 0; padding: .1rem .2rem; font: inherit;
  color: inherit; font-weight: 600;
}
tr.vetoed > td { opacity: .55; }
tr.vetoed > td.namecell button { text-decoration: line-through; }
.badge {
  display: inline-block; border: 1px solid var(--line); border-radius: 999px;
  padding: 0 .5rem; font-size: .78rem; white-space: nowrap;
}
.badge.junk { color: var(--junk); border-color: var(--junk); }
.badge.review { color: var(--review); border-color: var(--review); }
.namecell button { background: none; border: 0; padding: 0; }
.group { margin-bottom: .75rem; }
.group > summary { cursor: pointer; font-weight: 600; padding: .3rem 0; }
.detail { background: var(--bg); }
.detail dl {
  display: grid; grid-template-columns: max-content 1fr; gap: .15rem .75rem;
  margin: .25rem 0;
}
.detail dt { color: var(--muted); font-size: .82rem; }
.detail dd { margin: 0; overflow-wrap: anywhere; }
.stats { display: flex; flex-wrap: wrap; gap: .4rem; }
.err { color: var(--veto); font-weight: 600; }
.ok { color: var(--approve); }
.hint { color: var(--muted); font-size: .85rem; }
@media (max-width: 640px) {
  .wrap { padding: .6rem; }
  .tile { min-width: 100%; }
  input[type="search"] { min-width: 100%; }
  .field { width: 100%; }
}
"""

# One IIFE that exports its pure logic under CommonJS and only touches the DOM
# when there is no `module` — that is what lets tests/test_review_html_js.py
# drive the *shipped* script under node instead of a copy of it.
APP_JS = r"""
(function () {
  "use strict";

  var MANIFEST_SCHEMA_VERSION = 1;
  var VERDICTS = ["approved", "vetoed"];
  var STORAGE_PREFIX = "vault-cleaner:review:";
  // review.py rejects manifest strings longer than this. Only `name` can
  // realistically reach it, and it is display metadata either way.
  var MAX_TEXT = 200;
  // The key allowlists from review.py. Kept identical on purpose: anything
  // this reader waves through is something Python will refuse later, after
  // the page has already told the user the review was restored.
  var MANIFEST_KEYS = ["schema_version", "snapshot", "decisions", "generated_at"];
  var SNAPSHOT_KEYS = ["schema_version", "ruleset_version", "fingerprint"];
  var DECISION_KEYS = ["id", "kind", "hash", "name", "action", "reason", "verdict"];

  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  // Data-keyed maps only: ids, reasons, and owners come from the vault, so
  // an item named "__proto__" must not be able to reach Object.prototype.
  function emptyMap() {
    return Object.create(null);
  }

  function str(value) {
    return value === null || value === undefined ? "" : String(value);
  }

  // Code points, not UTF-16 units, so the result cannot end in half a
  // surrogate pair and its length matches Python's len().
  function clip(text) {
    var points = Array.from(String(text));
    return points.length <= MAX_TEXT ? String(text) : points.slice(0, MAX_TEXT).join("");
  }

  // Ids and hashes are decimal uint64 strings. Comparing by length and then
  // lexicographically orders them numerically without ever building a Number,
  // which would silently round the low digits away.
  function compareIds(a, b) {
    var x = String(a), y = String(b);
    if (/^[0-9]+$/.test(x) && /^[0-9]+$/.test(y)) {
      var xs = x.replace(/^0+(?=[0-9])/, "");
      var ys = y.replace(/^0+(?=[0-9])/, "");
      if (xs.length !== ys.length) return xs.length < ys.length ? -1 : 1;
      return xs < ys ? -1 : (xs > ys ? 1 : 0);
    }
    return x < y ? -1 : (x > y ? 1 : 0);
  }

  function compareText(a, b) {
    return str(a).localeCompare(str(b), undefined, { sensitivity: "base" });
  }

  function requireIdString(value, where) {
    if (typeof value !== "string") {
      throw new Error(
        where + " must be a JSON string, not " + typeof value +
        " — a numeric id has already lost 64-bit precision by the time it parses"
      );
    }
    return value;
  }

  function itemsFromSnapshot(snapshot) {
    var items = [];
    var seen = emptyMap();
    var sections = (snapshot && snapshot.sections) || [];
    for (var s = 0; s < sections.length; s++) {
      var section = sections[s] || {};
      var evaluations = emptyMap();
      var armor = section.armor;
      if (armor && Array.isArray(armor.evaluations)) {
        for (var e = 0; e < armor.evaluations.length; e++) {
          var evaluation = armor.evaluations[e];
          evaluations[requireIdString(evaluation.id, "armor evaluation id")] = evaluation;
        }
      }
      var decisions = section.decisions || [];
      for (var d = 0; d < decisions.length; d++) {
        var decision = decisions[d];
        var where = "sections[" + s + "].decisions[" + d + "]";
        var id = requireIdString(decision.id, where + ".id");
        requireIdString(decision.hash, where + ".hash");
        if (seen[id]) throw new Error("duplicate decision for id " + id + " at " + where);
        seen[id] = true;
        items.push({
          id: id,
          hash: decision.hash,
          kind: str(decision.kind) || str(section.kind),
          name: str(decision.name),
          owner: str(decision.owner),
          action: str(decision.action),
          reason: str(decision.reason),
          tag: str(decision.tag),
          note: str(decision.note),
          keptId: str(decision.kept_id),
          originalTag: str(decision.original_tag),
          originalNotes: str(decision.original_notes),
          protectionLevel: str(decision.protection_level),
          protectionReason: str(decision.protection_reason),
          locked: decision.locked === true,
          equipped: decision.equipped === true,
          inLoadout: decision.in_loadout === true,
          armor: evaluations[id] || null
        });
      }
    }
    return items;
  }

  function verdictOf(verdicts, id) {
    var verdict = verdicts ? verdicts[id] : undefined;
    return verdict === "approved" || verdict === "vetoed" ? verdict : "";
  }

  function actionCounts(items) {
    var junk = 0, review = 0;
    for (var i = 0; i < items.length; i++) {
      if (items[i].action === "junk") junk++;
      else if (items[i].action === "review") review++;
    }
    return { total: items.length, junk: junk, review: review };
  }

  // What the reviewed export would still contain: a veto suppresses the
  // proposal, exactly as review.apply_vetoes does on the Python side.
  function keptItems(items, verdicts) {
    return items.filter(function (item) {
      return verdictOf(verdicts, item.id) !== "vetoed";
    });
  }

  function reviewCounts(items, verdicts) {
    var approved = 0, vetoed = 0;
    for (var i = 0; i < items.length; i++) {
      var verdict = verdictOf(verdicts, items[i].id);
      if (verdict === "approved") approved++;
      else if (verdict === "vetoed") vetoed++;
    }
    return {
      approved: approved,
      vetoed: vetoed,
      unreviewed: items.length - approved - vetoed
    };
  }

  function matchesText(item, text) {
    var needle = str(text).trim();
    if (!needle) return true;
    return item.name.toLowerCase().indexOf(needle.toLowerCase()) !== -1 ||
           item.id.indexOf(needle) !== -1;
  }

  function matchesProtection(item, mode) {
    if (!mode) return true;
    if (mode === "protected") return item.protectionLevel !== "";
    if (mode === "unprotected") return item.protectionLevel === "";
    return item.protectionLevel === mode;
  }

  function filterItems(items, query, verdicts) {
    var q = query || {};
    return items.filter(function (item) {
      if (q.action && item.action !== q.action) return false;
      if (q.kind && item.kind !== q.kind) return false;
      if (q.reason && item.reason !== q.reason) return false;
      if (q.owner && item.owner !== q.owner) return false;
      if (!matchesProtection(item, q.protection)) return false;
      if (q.verdict) {
        var verdict = verdictOf(verdicts, item.id);
        if (q.verdict === "unreviewed" ? verdict !== "" : verdict !== q.verdict) {
          return false;
        }
      }
      return matchesText(item, q.text);
    });
  }

  var SORT_FIELDS = ["name", "id", "kind", "action", "reason", "owner"];

  function sortItems(items, field, direction) {
    var key = SORT_FIELDS.indexOf(field) === -1 ? "name" : field;
    var sign = direction === "desc" ? -1 : 1;
    return items.slice().sort(function (a, b) {
      var order = key === "id" ? compareIds(a.id, b.id) : compareText(a[key], b[key]);
      if (order === 0) order = compareIds(a.id, b.id);
      return order * sign;
    });
  }

  function groupLabel(group) {
    return group.action.toUpperCase() + " " + group.reason + " (" + group.kind +
           ") — " + group.items.length + " item(s)";
  }

  // Same grouping and ordering as report.summarize: (action, kind, reason)
  // triples, junk before review, largest first, then alphabetical — so the
  // page and the terminal tell the same story in the same order.
  function groupItems(items) {
    var byKey = emptyMap();
    var order = [];
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var key = [item.action, item.kind, item.reason].join("\u0000");
      if (!byKey[key]) {
        byKey[key] = {
          action: item.action, kind: item.kind, reason: item.reason, items: []
        };
        order.push(key);
      }
      byKey[key].items.push(item);
    }
    var groups = order.map(function (key) { return byKey[key]; });
    groups.sort(function (a, b) {
      var aJunk = a.action === "junk", bJunk = b.action === "junk";
      if (aJunk !== bJunk) return aJunk ? -1 : 1;
      if (a.items.length !== b.items.length) return b.items.length - a.items.length;
      return compareText(a.action, b.action) || compareText(a.kind, b.kind) ||
             compareText(a.reason, b.reason);
    });
    groups.forEach(function (group) { group.label = groupLabel(group); });
    return groups;
  }

  function countBy(items, field) {
    var counts = emptyMap();
    for (var i = 0; i < items.length; i++) {
      var value = items[i][field];
      counts[value] = (counts[value] || 0) + 1;
    }
    return Object.keys(counts).map(function (value) {
      return { value: value, count: counts[value] };
    }).sort(function (a, b) {
      return b.count - a.count || compareText(a.value, b.value);
    });
  }

  function buildManifest(snapshot, items, verdicts, generatedAt) {
    var decisions = [];
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      var verdict = verdictOf(verdicts, item.id);
      if (!verdict) continue;
      decisions.push({
        id: item.id,
        kind: item.kind,
        hash: item.hash,
        name: clip(item.name),
        action: item.action,
        reason: item.reason,
        verdict: verdict
      });
    }
    return {
      schema_version: MANIFEST_SCHEMA_VERSION,
      generated_at: generatedAt,
      snapshot: {
        schema_version: snapshot.schema_version,
        ruleset_version: snapshot.ruleset_version,
        fingerprint: snapshot.fingerprint
      },
      decisions: decisions
    };
  }

  function fail(message) {
    return { ok: false, error: message };
  }

  // Return the first number token that is not written as a plain integer, or
  // "" if there is none. This has to work on the raw text: JSON.parse collapses
  // 1, 1.0, and 1e0 to the same IEEE-754 double, so by the time versionError
  // sees the value Number.isInteger(1.0) is true and the spelling is gone --
  // while Python's json.loads keeps 1.0 as a float and _require_version
  // refuses it. Legal to reject the whole class here because a review manifest
  // has no fractional field at all: every value is a string except the three
  // integer versions.
  //
  // Only ever run this over an imported manifest. The embedded report snapshot
  // legitimately contains floats (armor scores serialise as 112.0).
  function fractionalNumberError(text) {
    var body = String(text);
    var inString = false;
    var escaped = false;
    for (var i = 0; i < body.length; i++) {
      var ch = body.charAt(i);
      if (inString) {
        // Track escapes so a \" inside a name cannot end the string early and
        // let a fraction in the *text* be read as a fraction in the *data*.
        if (escaped) escaped = false;
        else if (ch === "\\") escaped = true;
        else if (ch === "\"") inString = false;
        continue;
      }
      if (ch === "\"") { inString = true; continue; }
      if (ch !== "-" && (ch < "0" || ch > "9")) continue;
      // Consume the whole number token before judging it, so the "e" in true
      // and false is never mistaken for an exponent.
      var end = i;
      while (end < body.length && "+-0123456789.eE".indexOf(body.charAt(end)) !== -1) {
        end++;
      }
      var token = body.slice(i, end);
      if (/[.eE]/.test(token)) return token;
      i = end - 1;
    }
    return "";
  }

  // The three checks below mirror review.py's _check_keys, _require_text, and
  // _require_version. Each returns an error string, or "" when the value is
  // acceptable. Parity is enforced by a test that runs one table of payloads
  // through both this reader and parse_manifest.

  function unknownKeyError(value, allowed, where) {
    var unknown = Object.keys(value).filter(function (key) {
      return allowed.indexOf(key) === -1;
    }).sort();
    if (!unknown.length) return "";
    // Rejected outright rather than ignored, for review.py's reason: a
    // silently dropped "output_path" is how a file from a browser becomes a
    // way to point this tool at other files.
    return where + ": unknown key(s) " + JSON.stringify(unknown) +
           " — expected " + JSON.stringify(allowed.slice().sort());
  }

  function textError(value, key, where, allowEmpty) {
    var text = value[key];
    if (typeof text !== "string") return where + ": '" + key + "' must be a string";
    if (!allowEmpty && !text) return where + ": '" + key + "' must not be empty";
    // Code points, matching Python's len(); counting UTF-16 units would
    // reject names that parse_manifest accepts.
    if (Array.from(text).length > MAX_TEXT) {
      return where + ": '" + key + "' is longer than " + MAX_TEXT + " characters";
    }
    return "";
  }

  function versionError(value, key, expected, where) {
    var version = value[key];
    if (typeof version !== "number" || !Number.isInteger(version)) {
      return where + ": '" + key + "' must be an integer";
    }
    if (version !== expected) {
      return where + ": " + key + " " + version +
             " is not supported by this build (expected " + expected + ")";
    }
    return "";
  }

  // As strict as review.parse_manifest, in the same order, plus the
  // fingerprint comparison that check_manifest_matches does on the Python
  // side — the browser holds the run, so it can do both at once. Anything
  // waved through here would be refused later, after the user had been told
  // the review was restored.
  function readManifest(snapshot, items, payload) {
    if (!isObject(payload)) return fail("the file is not a JSON object");

    var error = unknownKeyError(payload, MANIFEST_KEYS, "manifest") ||
                versionError(payload, "schema_version",
                             MANIFEST_SCHEMA_VERSION, "manifest");
    if (error) return fail(error);
    if ("generated_at" in payload) {
      error = textError(payload, "generated_at", "manifest");
      if (error) return fail(error);
    }

    var snap = payload.snapshot;
    if (!isObject(snap)) return fail("'snapshot' must be an object");
    error = unknownKeyError(snap, SNAPSHOT_KEYS, "snapshot") ||
            versionError(snap, "schema_version",
                         snapshot.schema_version, "snapshot") ||
            versionError(snap, "ruleset_version",
                         snapshot.ruleset_version, "snapshot") ||
            textError(snap, "fingerprint", "snapshot");
    if (error) return fail(error);

    // Structure first, identity second: a malformed manifest should say what
    // is malformed rather than complain about the fingerprint.
    if (snap.fingerprint !== snapshot.fingerprint) {
      return fail("this manifest was produced against a different report run " +
                  "(fingerprint " + str(snap.fingerprint).slice(0, 12) +
                  "…, this report is " + snapshot.fingerprint.slice(0, 12) +
                  "…) — re-run the report and review it again");
    }
    if (!Array.isArray(payload.decisions)) return fail("'decisions' must be a list");

    var known = emptyMap();
    items.forEach(function (item) { known[item.id] = true; });

    var verdicts = emptyMap();
    var unknown = [];
    var applied = 0;
    for (var i = 0; i < payload.decisions.length; i++) {
      var entry = payload.decisions[i];
      var at = "decisions[" + i + "]";
      if (!isObject(entry)) return fail(at + " must be an object");
      error = unknownKeyError(entry, DECISION_KEYS, at);
      if (error) return fail(error);
      if (typeof entry.id !== "string") return fail(at + ": 'id' must be a string");
      if (!/^[0-9]{1,20}$/.test(entry.id)) {
        return fail(at + ": 'id' " + JSON.stringify(entry.id) +
                    " is not a DIM instance id (1-20 decimal digits)");
      }
      error = textError(entry, "verdict", at);
      if (error) return fail(error);
      if (VERDICTS.indexOf(entry.verdict) === -1) {
        return fail(at + ": verdict " + JSON.stringify(entry.verdict) +
                    " must be 'approved' or 'vetoed'");
      }
      if (verdicts[entry.id] !== undefined) {
        return fail(at + ": id " + entry.id + " appears twice");
      }
      // Display metadata, but still required and still bounded: the manifest
      // must be the same shape Python will re-read.
      error = textError(entry, "kind", at) ||
              textError(entry, "hash", at) ||
              textError(entry, "name", at, true) ||
              textError(entry, "action", at) ||
              textError(entry, "reason", at);
      if (error) return fail(error);
      verdicts[entry.id] = entry.verdict;
      if (known[entry.id]) applied++; else unknown.push(entry.id);
    }

    // Verdicts for ids this run does not propose are reported, never kept:
    // the run is authoritative about what is on the table.
    var kept = emptyMap();
    Object.keys(verdicts).forEach(function (id) {
      if (known[id]) kept[id] = verdicts[id];
    });
    return { ok: true, verdicts: kept, applied: applied, unknown: unknown };
  }

  // Text in, verdict out. The number-spelling check lives here rather than in
  // readManifest because it needs the raw text, and routing every reader
  // through this function is what stops it being skipped.
  function readManifestText(snapshot, items, text) {
    var fractional = fractionalNumberError(text);
    if (fractional) {
      return fail("number " + fractional + " must be written as a plain " +
                  "integer — a review manifest has no fractional fields, and " +
                  "Python reads " + fractional + " as a float rather than a " +
                  "version");
    }
    var payload;
    try {
      payload = JSON.parse(text);
    } catch (e) {
      return fail("not valid JSON (" + e.message + ")");
    }
    return readManifest(snapshot, items, payload);
  }

  // Both options exist to match Python's Path.read_text(encoding="utf-8"), not
  // out of fussiness, and FileReader.readAsText gets both of them wrong:
  //
  //   fatal:      readAsText substitutes U+FFFD for a malformed sequence and
  //               carries on, so a mis-encoded file imported cleanly here while
  //               Python refused the same bytes.
  //   ignoreBOM:  confusingly named -- true means "do not strip a leading
  //               U+FEFF". readAsText and TextDecoder's default both strip it,
  //               but Python keeps it and json then refuses it, so stripping
  //               would just trade one divergence for another.
  function decodeManifestBytes(bytes) {
    try {
      var decoder = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });
      return { ok: true, text: decoder.decode(bytes) };
    } catch (e) {
      return { ok: false, error: "not valid UTF-8 (" + e.message + ")" };
    }
  }

  // Bytes in, verdict out: the same contract as review.parse_manifest(path),
  // which is what makes the two comparable in the parity test.
  function readManifestBytes(snapshot, items, bytes) {
    var decoded = decodeManifestBytes(bytes);
    if (!decoded.ok) return fail(decoded.error);
    return readManifestText(snapshot, items, decoded.text);
  }

  // The other import entry point: a textarea value, already a JS string.
  //
  // trim() answers exactly one question here -- "is the box empty" -- and must
  // not touch the value that gets validated. JavaScript's trim() removes U+FEFF,
  // U+00A0, U+2028, and U+3000, none of which JSON accepts, so trimming first
  // laundered four prefixes into manifests Python refuses. That is the same
  // divergence `ignoreBOM: true` closes on the file path, and passing the value
  // through untouched costs nothing: JSON.parse already allows ordinary leading
  // and trailing JSON whitespace.
  //
  // Exported rather than left inline in the click handler because normalisation
  // hidden in UI code is precisely where this bug survived three review rounds.
  function readPastedManifest(snapshot, items, value) {
    var text = value === null || value === undefined ? "" : String(value);
    if (!text.trim()) {
      return {
        ok: false,
        empty: true,
        error: "paste a review manifest into the box first"
      };
    }
    return readManifestText(snapshot, items, text);
  }

  var api = {
    MANIFEST_SCHEMA_VERSION: MANIFEST_SCHEMA_VERSION,
    STORAGE_PREFIX: STORAGE_PREFIX,
    MAX_TEXT: MAX_TEXT,
    actionCounts: actionCounts,
    buildManifest: buildManifest,
    clip: clip,
    compareIds: compareIds,
    countBy: countBy,
    decodeManifestBytes: decodeManifestBytes,
    filterItems: filterItems,
    fractionalNumberError: fractionalNumberError,
    groupItems: groupItems,
    groupLabel: groupLabel,
    itemsFromSnapshot: itemsFromSnapshot,
    keptItems: keptItems,
    readManifest: readManifest,
    readManifestBytes: readManifestBytes,
    readManifestText: readManifestText,
    readPastedManifest: readPastedManifest,
    reviewCounts: reviewCounts,
    sortItems: sortItems,
    verdictOf: verdictOf
  };

  if (typeof module === "object" && module !== null && module.exports) {
    module.exports = api;
    return;
  }

  /* ----------------------------------------------------------------- view */

  // Every node is built with createElement/textContent, and no snapshot value
  // is ever concatenated into innerHTML or into an href/src, so a hostile item
  // name -- a closing script tag, an img with an onerror handler, a CSV formula
  // -- is just a long, ugly, inert string. Nothing in this file may contain a
  // literal closing script tag either: it would end the script element early.
  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        var value = attrs[key];
        if (value === null || value === undefined || value === false) return;
        if (key === "text") { node.textContent = String(value); return; }
        if (key === "class") { node.className = String(value); return; }
        if (key === "on") {
          Object.keys(value).forEach(function (name) {
            node.addEventListener(name, value[name]);
          });
          return;
        }
        node.setAttribute(key, value === true ? "" : String(value));
      });
    }
    (children || []).forEach(function (child) {
      if (child === null || child === undefined || child === false) return;
      node.appendChild(typeof child === "string"
        ? document.createTextNode(child) : child);
    });
    return node;
  }

  function byId(id) { return document.getElementById(id); }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function boot() {
    var status = byId("vc-status");
    var snapshot, items;
    try {
      snapshot = JSON.parse(byId("__SNAPSHOT_ID__").textContent);
      items = itemsFromSnapshot(snapshot);
    } catch (e) {
      status.className = "err";
      status.textContent = "could not read the embedded report snapshot: " + e.message;
      return;
    }

    var storageKey = STORAGE_PREFIX + snapshot.fingerprint;
    var state = {
      verdicts: emptyMap(),
      sort: { field: "name", direction: "asc" },
      grouped: true,
      expanded: emptyMap(),
      // Set at each import/export; anything else is an unsaved change.
      handoff: "[]",
      // id -> the live row nodes, so a verdict change can update in place
      // instead of rebuilding the table and throwing away keyboard focus.
      rows: emptyMap(),
      query: {
        text: "", action: "", kind: "", reason: "", owner: "",
        protection: "", verdict: ""
      }
    };

    function verdictSignature() {
      return JSON.stringify(Object.keys(state.verdicts).sort(compareIds)
        .map(function (id) { return [id, state.verdicts[id]]; }));
    }

    function announce(message, isError) {
      status.className = isError ? "err" : "ok";
      status.textContent = message;
    }

    function loadAutosave() {
      var stored;
      try {
        stored = window.localStorage.getItem(storageKey);
      } catch (e) {
        return 0;
      }
      if (!stored) return 0;
      var parsed;
      try {
        parsed = JSON.parse(stored);
      } catch (e) {
        return 0;
      }
      if (!isObject(parsed)) return 0;
      var known = emptyMap();
      items.forEach(function (item) { known[item.id] = true; });
      var restored = 0;
      Object.keys(parsed).forEach(function (id) {
        if (known[id] && VERDICTS.indexOf(parsed[id]) !== -1) {
          state.verdicts[id] = parsed[id];
          restored++;
        }
      });
      return restored;
    }

    function saveAutosave() {
      var plain = {};
      Object.keys(state.verdicts).forEach(function (id) {
        plain[id] = state.verdicts[id];
      });
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(plain));
      } catch (e) {
        /* file:// origins may refuse storage; export is the durable handoff */
      }
    }

    function paintRow(id) {
      var row = state.rows[id];
      if (!row) return;
      var verdict = verdictOf(state.verdicts, id);
      row.tr.className = verdict === "vetoed" ? "vetoed" : "";
      row.approve.setAttribute("aria-pressed", verdict === "approved" ? "true" : "false");
      row.veto.setAttribute("aria-pressed", verdict === "vetoed" ? "true" : "false");
    }

    function setVerdict(id, verdict) {
      if (verdict) state.verdicts[id] = verdict;
      else delete state.verdicts[id];
      saveAutosave();
      // Only a verdict filter can change which rows belong on screen.
      if (state.query.verdict) renderList();
      else paintRow(id);
      renderSummary();
    }

    function toggleVerdict(id, verdict) {
      setVerdict(id, verdictOf(state.verdicts, id) === verdict ? "" : verdict);
    }

    function bulk(verdict) {
      var shown = filterItems(items, state.query, state.verdicts);
      shown.forEach(function (item) {
        if (verdict) state.verdicts[item.id] = verdict;
        else delete state.verdicts[item.id];
      });
      saveAutosave();
      renderList();
      renderSummary();
      announce((verdict || "cleared") + " " + shown.length + " shown item(s)");
    }

    /* -- summary ------------------------------------------------------ */

    function tile(kind, value, note) {
      return el("div", { class: "tile" }, [
        el("span", { class: "k", text: kind }),
        el("span", { class: "n", text: value }),
        note ? el("span", { class: "sub", text: note }) : null
      ]);
    }

    function renderSummary() {
      var host = byId("vc-summary");
      clear(host);
      var proposed = actionCounts(items);
      var kept = actionCounts(keptItems(items, state.verdicts));
      var reviewed = reviewCounts(items, state.verdicts);
      var shown = filterItems(items, state.query, state.verdicts).length;
      host.appendChild(el("div", { class: "tiles" }, [
        tile("proposed", String(proposed.total),
             proposed.junk + " junk, " + proposed.review + " review"),
        tile("after vetoes", String(kept.total),
             kept.junk + " junk, " + kept.review + " review"),
        tile("reviewed", reviewed.approved + " / " + reviewed.vetoed,
             "approved / vetoed, " + reviewed.unreviewed + " unreviewed"),
        tile("shown", String(shown), "matching the current filters")
      ]));
      var dirty = verdictSignature() !== state.handoff;
      host.appendChild(el("p", {
        class: dirty ? "dirty" : "clean",
        text: dirty
          ? "Unsaved review changes — export a review manifest to hand them to vault-cleaner review."
          : "No unsaved review changes since the last import or export."
      }));
    }

    /* -- filters ------------------------------------------------------ */

    function select(id, label, options, onChange) {
      return el("label", { class: "field", for: id }, [
        el("span", { text: label }),
        el("select", { id: id, on: { change: onChange } }, options)
      ]);
    }

    function optionsFor(field, allLabel) {
      var options = [el("option", { value: "", text: allLabel })];
      countBy(items, field).forEach(function (entry) {
        if (entry.value === "") return;
        options.push(el("option", {
          value: entry.value,
          text: entry.value + " (" + entry.count + ")"
        }));
      });
      return options;
    }

    function onQueryChange(field) {
      return function (event) {
        state.query[field] = event.target.value;
        renderList();
        renderSummary();
      };
    }

    function addSelect(host, id, label, options, field, value) {
      var node = select(id, label, options, onQueryChange(field));
      node.querySelector("select").value = value;
      host.appendChild(node);
    }

    function renderControls() {
      var host = byId("vc-controls");
      clear(host);

      host.appendChild(el("label", { class: "field", for: "vc-search" }, [
        el("span", { text: "Search name or instance id" }),
        el("input", {
          type: "search", id: "vc-search", value: state.query.text,
          placeholder: "e.g. Dupe Rifle or 3001",
          on: {
            input: function (event) {
              state.query.text = event.target.value;
              renderList();
              renderSummary();
            }
          }
        })
      ]));

      [
        ["vc-f-action", "Action", "action", "any action"],
        ["vc-f-kind", "Kind", "kind", "any kind"],
        ["vc-f-reason", "Reason", "reason", "any reason"],
        ["vc-f-owner", "Owner", "owner", "any owner"]
      ].forEach(function (spec) {
        addSelect(host, spec[0], spec[1], optionsFor(spec[2], spec[3]),
                  spec[2], state.query[spec[2]]);
      });

      addSelect(host, "vc-f-protection", "Protection", [
        el("option", { value: "", text: "any" }),
        el("option", { value: "protected", text: "protected" }),
        el("option", { value: "unprotected", text: "unprotected" }),
        el("option", { value: "soft", text: "soft only" }),
        el("option", { value: "hard", text: "hard only" })
      ], "protection", state.query.protection);

      addSelect(host, "vc-f-verdict", "Verdict", [
        el("option", { value: "", text: "any" }),
        el("option", { value: "unreviewed", text: "unreviewed" }),
        el("option", { value: "approved", text: "approved" }),
        el("option", { value: "vetoed", text: "vetoed" })
      ], "verdict", state.query.verdict);

      var grouping = select("vc-f-group", "View", [
        el("option", { value: "grouped", text: "grouped by action/kind/reason" }),
        el("option", { value: "flat", text: "one sortable table" })
      ], function (event) {
        state.grouped = event.target.value === "grouped";
        renderList();
      });
      grouping.querySelector("select").value = state.grouped ? "grouped" : "flat";
      host.appendChild(grouping);

      host.appendChild(el("div", { class: "field" }, [
        el("span", { text: "Bulk action on shown items" }),
        el("div", { class: "row-actions" }, [
          el("button", { type: "button", text: "Approve all",
                         on: { click: function () { bulk("approved"); } } }),
          el("button", { type: "button", text: "Veto all",
                         on: { click: function () { bulk("vetoed"); } } }),
          el("button", { type: "button", text: "Unset all",
                         on: { click: function () { bulk(""); } } })
        ])
      ]));

      host.appendChild(el("div", { class: "field" }, [
        el("span", { text: "Filters" }),
        el("button", {
          type: "button", text: "Reset filters",
          on: {
            click: function () {
              Object.keys(state.query).forEach(function (key) {
                state.query[key] = "";
              });
              renderControls();
              renderList();
              renderSummary();
            }
          }
        })
      ]));
    }

    /* -- item table --------------------------------------------------- */

    var COLUMNS = [
      ["name", "Name"], ["id", "Instance id"], ["kind", "Kind"],
      ["owner", "Owner"], ["action", "Action"], ["reason", "Reason"]
    ];

    function headerRow() {
      var cells = COLUMNS.map(function (column) {
        var field = column[0], label = column[1];
        var active = state.sort.field === field;
        var ascending = state.sort.direction === "asc";
        return el("th", {
          scope: "col",
          "aria-sort": active ? (ascending ? "ascending" : "descending") : "none"
        }, [
          el("button", {
            type: "button",
            text: label + (active ? (ascending ? " ▲" : " ▼") : ""),
            "aria-label": "sort by " + label,
            on: {
              click: function () {
                if (state.sort.field === field) {
                  state.sort.direction = ascending ? "desc" : "asc";
                } else {
                  state.sort = { field: field, direction: "asc" };
                }
                renderList();
              }
            }
          })
        ]);
      });
      cells.push(el("th", { scope: "col", text: "Protection" }));
      cells.push(el("th", { scope: "col", text: "Verdict" }));
      return el("tr", null, cells);
    }

    function definition(term, value) {
      if (value === "" || value === null || value === undefined) return [];
      return [el("dt", { text: term }), el("dd", { text: String(value) })];
    }

    function armorDetail(evaluation) {
      var stats = evaluation.stats || {};
      var rows = [];
      rows = rows.concat(definition("slot", evaluation.slot));
      rows = rows.concat(definition("equippable", evaluation.equippable));
      rows = rows.concat(definition("best archetype", evaluation.best_archetype));
      rows = rows.concat(definition("score", evaluation.score + " (base " +
        evaluation.base_score + ", set bonus " + evaluation.set_bonus + ")"));
      rows = rows.concat(definition("rank",
        evaluation.rank + " of " + evaluation.group_size));
      rows.push(el("dt", { text: "stats" }));
      rows.push(el("dd", null, [
        el("div", { class: "stats" }, Object.keys(stats).sort().map(function (name) {
          return el("span", { class: "badge", text: name + " " + stats[name] });
        }))
      ]));
      return el("div", null, [
        el("h3", { text: "Armor scoring" }),
        el("dl", null, rows)
      ]);
    }

    function detailRow(item, detailId, columns) {
      var rows = [];
      rows = rows.concat(definition("hash", item.hash));
      rows = rows.concat(definition("note vault-cleaner would write", item.note));
      rows = rows.concat(definition("DIM tag vault-cleaner would write", item.tag));
      rows = rows.concat(definition("surviving copy", item.keptId));
      rows = rows.concat(definition("protection", item.protectionLevel
        ? item.protectionLevel + " — " + item.protectionReason : ""));
      rows = rows.concat(definition("existing DIM tag", item.originalTag));
      rows = rows.concat(definition("existing DIM notes", item.originalNotes));
      rows = rows.concat(definition("flags", [
        item.locked ? "locked" : null,
        item.equipped ? "equipped" : null,
        item.inLoadout ? "in a loadout" : null
      ].filter(Boolean).join(", ")));
      return el("tr", { id: detailId }, [
        el("td", { class: "detail", colspan: String(columns) }, [
          el("dl", null, rows),
          item.armor ? armorDetail(item.armor) : null
        ])
      ]);
    }

    function itemRows(item, columns) {
      var verdict = verdictOf(state.verdicts, item.id);
      var expanded = state.expanded[item.id] === true;
      var detailId = "vc-detail-" + item.id;
      var approve = el("button", {
        type: "button", class: "approve", text: "Approve",
        "aria-pressed": verdict === "approved" ? "true" : "false",
        "aria-label": "approve " + (item.name || "unnamed item") + ", id " + item.id,
        on: { click: function () { toggleVerdict(item.id, "approved"); } }
      });
      var veto = el("button", {
        type: "button", class: "veto", text: "Veto",
        "aria-pressed": verdict === "vetoed" ? "true" : "false",
        "aria-label": "veto " + (item.name || "unnamed item") + ", id " + item.id,
        on: { click: function () { toggleVerdict(item.id, "vetoed"); } }
      });
      var tr = el("tr", {
        class: verdict === "vetoed" ? "vetoed" : "", "data-id": item.id
      }, [
        el("td", { class: "namecell" }, [
          el("button", {
            type: "button",
            text: (expanded ? "▾ " : "▸ ") + (item.name || "(unnamed)"),
            "aria-expanded": expanded ? "true" : "false",
            "aria-controls": detailId,
            on: {
              click: function () {
                if (expanded) delete state.expanded[item.id];
                else state.expanded[item.id] = true;
                renderList();
              }
            }
          })
        ]),
        el("td", { class: "mono", text: item.id }),
        el("td", { text: item.kind }),
        el("td", { text: item.owner }),
        el("td", null, [el("span", {
          class: "badge " + (item.action === "junk" ? "junk" : "review"),
          text: item.action
        })]),
        el("td", { text: item.reason }),
        el("td", { text: item.protectionLevel || "—" }),
        el("td", null, [el("div", { class: "row-actions" }, [approve, veto])])
      ]);
      state.rows[item.id] = { tr: tr, approve: approve, veto: veto };
      return expanded ? [tr, detailRow(item, detailId, columns)] : [tr];
    }

    function table(rows) {
      var columns = COLUMNS.length + 2;
      var body = el("tbody", null, []);
      rows.forEach(function (item) {
        itemRows(item, columns).forEach(function (row) { body.appendChild(row); });
      });
      return el("div", { class: "scroller" }, [
        el("table", null, [el("thead", null, [headerRow()]), body])
      ]);
    }

    function renderList() {
      var host = byId("vc-list");
      clear(host);
      state.rows = emptyMap();
      var shown = filterItems(items, state.query, state.verdicts);
      if (!shown.length) {
        host.appendChild(el("p", {
          class: "hint", text: "No items match these filters."
        }));
        return;
      }
      var sorted = sortItems(shown, state.sort.field, state.sort.direction);
      if (!state.grouped) {
        host.appendChild(table(sorted));
        return;
      }
      groupItems(sorted).forEach(function (group) {
        host.appendChild(el("details", { class: "group", open: true }, [
          el("summary", { text: group.label }),
          table(group.items)
        ]));
      });
    }

    /* -- import / export ---------------------------------------------- */

    function manifestJson() {
      return JSON.stringify(
        buildManifest(snapshot, items, state.verdicts, new Date().toISOString()),
        null, 2
      ) + "\n";
    }

    function offerDownload(text) {
      try {
        var url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
        var link = el("a", { href: url, download: "vault-review-manifest.json" });
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(function () { URL.revokeObjectURL(url); }, 0);
      } catch (e) {
        /* Downloads can be unavailable from file://. The textarea always
           holds the same bytes, so nothing is lost either way. */
      }
    }

    function exportManifest() {
      var text = manifestJson();
      byId("vc-export-json").value = text;
      state.handoff = verdictSignature();
      var reviewed = reviewCounts(items, state.verdicts);
      offerDownload(text);
      renderSummary();
      announce("exported " + (reviewed.approved + reviewed.vetoed) +
               " verdict(s) — apply with: vault-cleaner review --manifest <file> --write");
    }

    // `result` comes from readManifestText (the pasted-in path, already a JS
    // string) or readManifestBytes (the file path, decoded strictly).
    function applyImport(result, label) {
      if (!result.ok) {
        announce("could not apply " + label + ": " + result.error, true);
        return;
      }
      state.verdicts = result.verdicts;
      state.handoff = verdictSignature();
      saveAutosave();
      renderControls();
      renderList();
      renderSummary();
      announce("imported " + result.applied + " verdict(s) from " + label +
               (result.unknown.length
                 ? " — ignored " + result.unknown.length +
                   " id(s) this run does not propose"
                 : ""));
    }

    function renderHandoff() {
      var host = byId("vc-handoff");
      clear(host);

      host.appendChild(el("label", { class: "field", for: "vc-import" }, [
        el("span", { text: "Import a review manifest" }),
        el("input", {
          type: "file", id: "vc-import", accept: ".json,application/json",
          on: {
            change: function (event) {
              var chosen = event.target.files && event.target.files[0];
              if (!chosen) return;
              var reader = new FileReader();
              reader.onload = function () {
                // Bytes, not readAsText: that would substitute U+FFFD for a
                // malformed sequence and strip a BOM, either of which imports
                // a file Python refuses.
                applyImport(
                  readManifestBytes(
                    snapshot, items, new Uint8Array(reader.result)
                  ),
                  chosen.name
                );
              };
              reader.onerror = function () {
                announce("could not read that file", true);
              };
              reader.readAsArrayBuffer(chosen);
              event.target.value = "";
            }
          }
        })
      ]));

      host.appendChild(el("div", { class: "field" }, [
        el("span", { text: "Export" }),
        el("div", { class: "row-actions" }, [
          el("button", { type: "button", text: "Export review manifest",
                         on: { click: exportManifest } }),
          el("button", {
            type: "button", text: "Import from the box below",
            on: {
              click: function () {
                // No validation or normalisation inline: readPastedManifest
                // owns both, so a test can reach them.
                var result = readPastedManifest(
                  snapshot, items, byId("vc-export-json").value
                );
                if (result.empty) {
                  announce(result.error, true);
                  return;
                }
                applyImport(result, "the pasted manifest");
              }
            }
          })
        ])
      ]));
    }

    /* -- boot --------------------------------------------------------- */

    // Approve/veto/unset from the keyboard while focus is anywhere in a row.
    document.addEventListener("keydown", function (event) {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      var tag = (event.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      var row = event.target.closest ? event.target.closest("tr[data-id]") : null;
      if (!row) return;
      var id = row.getAttribute("data-id");
      var key = String(event.key).toLowerCase();
      if (key === "a") toggleVerdict(id, "approved");
      else if (key === "v") toggleVerdict(id, "vetoed");
      else if (key === "u") setVerdict(id, "");
      else return;
      event.preventDefault();
    });

    byId("vc-fingerprint").textContent = snapshot.fingerprint;
    renderHandoff();
    var restored = loadAutosave();
    renderControls();
    renderList();
    renderSummary();
    if (restored) {
      announce("restored " + restored + " autosaved verdict(s) for this report " +
               "from browser storage — export a manifest to make them durable");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
"""


def embed_json(payload: str) -> str:
    r"""Make already-valid JSON safe to inline inside an HTML script element.

    `<`, `>`, and `&` only ever occur inside JSON string literals, where
    `\uXXXX` is an equivalent encoding — so escaping them keeps the JSON
    parseable and value-identical while making `</script>`, `<!--`, and `-->`
    impossible to spell. U+2028/U+2029 are escaped for the same reason: legal
    in a JSON string, but a line terminator in JavaScript source.
    """
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


# Static chrome only. Every element the app fills in is empty here, so the
# markup carries no vault data and needs no escaping of its own.
BODY_HTML = """\
<a class="skip" href="#vc-list">Skip to the item list</a>
<div class="wrap">
<h1>vault-cleaner review</h1>
<p class="sub">Report fingerprint <code id="vc-fingerprint"></code></p>
<div class="privacy">
<strong>Personal data &mdash; keep this file local</strong>
__PRIVACY_WARNING__
</div>
<noscript><p class="err">This review page needs JavaScript. The decisions are
still readable as JSON inside this file, and <code>vault-cleaner report</code>
prints the same ones in the terminal.</p></noscript>
<div class="panel">
<h2>Summary</h2>
<div id="vc-summary"></div>
</div>
<div class="panel">
<h2>Filters</h2>
<div class="controls" id="vc-controls"></div>
</div>
<div class="panel">
<h2>Handoff</h2>
<div class="controls" id="vc-handoff"></div>
<p id="vc-status" role="status" aria-live="polite" class="hint">Approve or veto
proposals, then export a review manifest and apply it with
<code>vault-cleaner review --manifest &lt;file&gt; --write</code>.</p>
<label class="field" for="vc-export-json"><span>Review manifest JSON &mdash;
copy it out, or paste one in and use &ldquo;Import from the box
below&rdquo;</span><textarea id="vc-export-json" spellcheck="false"></textarea>
</label>
<p class="hint">Browser storage autosaves your verdicts for this report as a
convenience only. Export is the durable handoff, and Python re-validates every
manifest before anything is written.</p>
</div>
<div class="panel">
<h2>Proposals</h2>
<p class="hint">With focus inside a row: <kbd>a</kbd> approve, <kbd>v</kbd>
veto, <kbd>u</kbd> unset.</p>
<div id="vc-list"></div>
</div>
</div>
"""

_HEAD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="__CSP__">
<meta name="referrer" content="no-referrer">
<title>vault-cleaner review</title>
<style>__CSS__</style>
</head>
<body>
"""


def render_review_html(run: ReportRun) -> str:
    """One portable HTML file: no network, no dependencies, no timestamps."""
    return "".join(
        [
            _HEAD_HTML.replace("__CSP__", CSP).replace("__CSS__", CSS),
            BODY_HTML.replace("__PRIVACY_WARNING__", PRIVACY_WARNING),
            # A non-executable data block: the app parses the snapshot out of
            # textContent, so nothing in here is ever evaluated as script.
            f'<script type="application/json" id="{SNAPSHOT_ELEMENT_ID}">',
            embed_json(snapshot_json(run)),
            "</script>\n",
            f'<script id="{APP_ELEMENT_ID}">',
            APP_JS.replace("__SNAPSHOT_ID__", SNAPSHOT_ELEMENT_ID),
            "</script>\n",
            "</body>\n</html>\n",
        ]
    )


def write_review_html(run: ReportRun, path: str | Path) -> Path:
    """Write the artifact, creating its parent directory like the CSV writer."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_review_html(run), encoding="utf-8")
    return target
