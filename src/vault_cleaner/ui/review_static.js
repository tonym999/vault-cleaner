(function (root) {
  "use strict";

  /* TEMPORARY STATIC REVIEW ADAPTER (#51 deletes this layer wholesale). */
  var ui = root.VaultCleanerReviewUI;
  if (!ui && typeof module === "object" && module !== null && module.exports) {
    ui = module.exports && module.exports.itemsFromSnapshot
      ? module.exports : require("./review_ui.js");
  }
  if (!ui) return;

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

  // Code points, not UTF-16 units, so the result cannot end in half a
  // surrogate pair and its length matches Python's len().
  function clip(text) {
    var points = Array.from(String(text));
    return points.length <= MAX_TEXT ? String(text) : points.slice(0, MAX_TEXT).join("");
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

  // The three checks below mirror review.py's check_keys, require_text, and
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

  var isObject = ui.isObject;
  var emptyMap = ui.emptyMap;
  var itemsFromSnapshot = ui.itemsFromSnapshot;
  var verdictOf = ui.verdictOf;
  var actionCounts = ui.actionCounts;
  var reviewCounts = ui.reviewCounts;
  var filterItems = ui.filterItems;
  var sortItems = ui.sortItems;
  var groupItems = ui.groupItems;
  var countBy = ui.countBy;
  var compareIds = ui.compareIds;
  var str = ui.str;
  function boot() {
    var status = root.document.getElementById("vc-status");
    var snapshot, items;
    try {
      snapshot = JSON.parse(root.document.getElementById("vc-snapshot").textContent);
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

    var view = ui.createView({
      state: state, items: items, columns: ui.COLUMNS,
      toggleVerdict: toggleVerdict, renderList: renderList
    });
    var el = view.el, clear = view.clear, byId = view.byId;

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

    function renderSummary() {
      var host = byId("vc-summary");
      clear(host);
      var proposed = actionCounts(items);
      var kept = actionCounts(ui.keptItems(items, state.verdicts, new Set()));
      var reviewed = reviewCounts(items, state.verdicts);
      var shown = filterItems(items, state.query, state.verdicts).length;
      host.appendChild(el("div", { class: "tiles" }, [
        view.tile("proposed", String(proposed.total),
             proposed.junk + " junk, " + proposed.review + " review"),
        view.tile("after vetoes", String(kept.total),
             kept.junk + " junk, " + kept.review + " review"),
        view.tile("reviewed", reviewed.approved + " / " + reviewed.vetoed,
             "approved / vetoed, " + reviewed.unreviewed + " unreviewed"),
        view.tile("shown", String(shown), "matching the current filters")
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

    function onQueryChange(field) {
      return function (event) {
        state.query[field] = event.target.value;
        renderList();
        renderSummary();
      };
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
        view.addSelect(host, spec[0], spec[1],
                     view.optionsFor(items, spec[2], spec[3]), spec[2],
                     state.query[spec[2]], onQueryChange);
      });

      view.addSelect(host, "vc-f-protection", "Protection", [
        el("option", { value: "", text: "any" }),
        el("option", { value: "protected", text: "protected" }),
        el("option", { value: "unprotected", text: "unprotected" }),
        el("option", { value: "soft", text: "soft only" }),
        el("option", { value: "hard", text: "hard only" })
      ], "protection", state.query.protection, onQueryChange);

      view.addSelect(host, "vc-f-verdict", "Verdict", [
        el("option", { value: "", text: "any" }),
        el("option", { value: "unreviewed", text: "unreviewed" }),
        el("option", { value: "approved", text: "approved" }),
        el("option", { value: "vetoed", text: "vetoed" })
      ], "verdict", state.query.verdict, onQueryChange);

      var grouping = view.select("vc-f-group", "View", [
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
        host.appendChild(view.table(sorted));
        return;
      }
      groupItems(sorted).forEach(function (group) {
        host.appendChild(el("details", { class: "group", open: true }, [
          el("summary", { text: group.label }),
          view.table(group.items)
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

  // Node drives the temporary adapter's manifest parity tests without a DOM.
  // Keep that surface confined to this file; the reusable resource above stays
  // free of manifest construction and validation names.
  if (!root.document) {
    if (typeof module === "object" && module !== null && module.exports) {
      module.exports = Object.assign({}, ui, {
        MANIFEST_SCHEMA_VERSION: MANIFEST_SCHEMA_VERSION,
        STORAGE_PREFIX: STORAGE_PREFIX,
        MAX_TEXT: MAX_TEXT,
        buildManifest: buildManifest,
        clip: clip,
        decodeManifestBytes: decodeManifestBytes,
        fail: fail,
        fractionalNumberError: fractionalNumberError,
        readManifest: readManifest,
        readManifestBytes: readManifestBytes,
        readManifestText: readManifestText,
        readPastedManifest: readPastedManifest
      });
    }
    return;
  }

  if (root.document.readyState === "loading") {
    root.document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})(typeof globalThis === "object" ? globalThis : this);
