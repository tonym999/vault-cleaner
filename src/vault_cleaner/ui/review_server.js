(function (root, factory) {
  "use strict";
  var shared = root && root.VaultCleanerReviewUI;
  if (!shared && typeof module === "object" && module !== null && module.exports) {
    shared = require("./review_ui.js");
  }
  var api = factory(root, shared);
  if (typeof module === "object" && module !== null && module.exports) {
    module.exports = api;
  } else if (root) {
    root.VaultCleanerServerUI = api;
  }
})(typeof globalThis === "object" ? globalThis : this, function (root, ui) {
  "use strict";

  // The server is authoritative.  This adapter never interprets a report as
  // an instruction to write a file; it only turns one session envelope into
  // read-only presentation state.
  var SESSION_SCHEMA_VERSION = 1;
  var KINDS = ["weapons", "armor", "ghosts"];
  var ENDPOINTS = {
    weapons: "/api/exports/weapons",
    armor: "/api/exports/armor",
    ghosts: "/api/exports/ghosts"
  };

  function emptyMap() { return Object.create(null); }
  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }
  function copyVerdicts(entries) {
    var values = emptyMap();
    if (!Array.isArray(entries)) return values;
    entries.forEach(function (entry) {
      if (isObject(entry) && typeof entry.id === "string" &&
          (entry.verdict === "approved" || entry.verdict === "vetoed")) {
        values[entry.id] = entry.verdict;
      }
    });
    return values;
  }
  function persistedVetoIds(entries) {
    var values = new Set();
    if (!Array.isArray(entries)) return values;
    entries.forEach(function (entry) {
      if (isObject(entry) && entry.status === "active" &&
          typeof entry.id === "string") values.add(entry.id);
    });
    return values;
  }

  function createState() {
    return {
      envelope: null,
      items: [],
      verdicts: emptyMap(),
      persistedVetoIds: new Set(),
      // These are the local presentation controls.  applySessionEnvelope
      // intentionally leaves them untouched when a report is reloaded.
      sort: { field: "name", direction: "asc" },
      grouped: true,
      expanded: emptyMap(),
      query: {
        text: "", action: "", kind: "", reason: "", owner: "",
        protection: "", verdict: ""
      },
      rows: emptyMap(),
      reconciliation: { retained: [], discarded: [] },
      uploadStatus: { weapons: "idle", armor: "idle", ghosts: "idle" },
      connected: false,
      terminal: false
    };
  }

  function envelopeError(message) {
    var error = new Error(message);
    error.clientCode = "unsupported_envelope";
    return error;
  }

  function valueStillExists(items, verdicts, field, value) {
    if (!value) return true;
    var query = emptyMap();
    query[field] = value;
    return ui.filterItems(items, query, verdicts).length > 0;
  }

  /**
   * Adopt a server response in one place while preserving local view state.
   * The reconciliation arrays are retained for diagnostics and reconnect
   * handling only; they are deliberately not rendered as vault content.
   */
  function applySessionEnvelope(envelope, state) {
    if (!isObject(envelope)) throw new TypeError("session envelope must be an object");
    if (!state || typeof state !== "object") throw new TypeError("state is required");
    if (envelope.schema_version !== SESSION_SCHEMA_VERSION) {
      throw envelopeError("session schema version " +
        String(envelope.schema_version) + " is not supported by this page");
    }
    var snapshot = envelope.snapshot;
    var nextItems = [];
    if (snapshot !== null && snapshot !== undefined) {
      if (!ui || typeof ui.itemsFromSnapshot !== "function") {
        throw new Error("shared review presentation core is unavailable");
      }
      nextItems = ui.itemsFromSnapshot(snapshot);
    }
    var nextVerdicts = copyVerdicts(envelope.verdicts);
    var nextIds = new Set(nextItems.map(function (item) { return item.id; }));
    Object.keys(state.expanded).forEach(function (id) {
      if (!nextIds.has(id)) delete state.expanded[id];
    });
    ["action", "kind", "reason", "owner", "protection", "verdict"].forEach(
      function (field) {
        if (!valueStillExists(nextItems, nextVerdicts, field, state.query[field])) {
          state.query[field] = "";
        }
      }
    );
    var sortFields = ui.COLUMNS.map(function (column) { return column[0]; });
    if (sortFields.indexOf(state.sort.field) === -1) {
      state.sort = { field: "name", direction: "asc" };
    }
    state.envelope = envelope;
    state.server_state = envelope.state;
    state.report_revision = envelope.report_revision;
    state.verdict_revision = envelope.verdict_revision;
    state.fingerprint = envelope.fingerprint;
    state.snapshot = snapshot;
    state.items = nextItems;
    state.verdicts = nextVerdicts;
    state.override_status = Array.isArray(envelope.override_status)
      ? envelope.override_status.slice() : [];
    state.persistedVetoIds = persistedVetoIds(envelope.override_status);
    state.rows = emptyMap();
    state.reconciliation = {
      retained: Array.isArray(envelope.retained_verdict_ids)
        ? envelope.retained_verdict_ids.slice() : [],
      discarded: Array.isArray(envelope.discarded_verdict_ids)
        ? envelope.discarded_verdict_ids.slice() : []
    };
    state.connected = envelope.state !== "closed";
    state.terminal = envelope.state === "closed";
    return state;
  }

  function sessionVerdictText(state, item) {
    var current = ui.verdictOf(state.verdicts, item.id);
    var persisted = state.persistedVetoIds.has(item.id);
    if (persisted && current) return "persisted veto; session " + current;
    if (persisted) return "persisted veto";
    return current || "—";
  }

  function responseError(response) {
    return response.json().then(function (payload) {
      var error = payload && payload.error;
      var message = error && typeof error.message === "string"
        ? error.message : "request failed (HTTP " + response.status + ")";
      return {
        status: response.status,
        code: error && error.code,
        message: message
      };
    }, function () {
      return {
        status: response.status,
        code: "network_error",
        message: "request failed (HTTP " + response.status + ")"
      };
    });
  }

  function fetchEnvelope(path, options) {
    return root.fetch(path, options).then(function (response) {
      if (response.ok) return response.json();
      return responseError(response).then(function (error) {
        var failure = new Error(error.message);
        failure.server = error;
        throw failure;
      });
    });
  }

  function showReconnect(host, reconnect) {
    var button = host.ownerDocument.createElement("button");
    button.type = "button";
    button.textContent = "Reconnect";
    button.addEventListener("click", function () {
      reconnect();
    });
    host.appendChild(button);
  }

  function boot(document) {
    if (!ui || !root.fetch) return;
    var status = document.getElementById("vc-status");
    var reportPanel = document.getElementById("vc-report");
    var filtersPanel = document.getElementById("vc-filters");
    var proposalsPanel = document.getElementById("vc-proposals");
    var state = createState();
    var view = null;

    function setUploadsDisabled(disabled) {
      KINDS.forEach(function (kind) {
        document.getElementById("vc-upload-" + kind).disabled = disabled;
      });
    }

    function announce(message, kind) {
      status.className = kind === "error" ? "err" :
        (kind === "ok" ? "ok" : "hint");
      status.textContent = message;
    }
    function fail(message, terminal) {
      announce(message, "error");
      state.connected = false;
      state.terminal = !!terminal;
      setUploadsDisabled(true);
      if (!terminal) showReconnect(status, requestReport);
    }
    function adopt(envelope) {
      applySessionEnvelope(envelope, state);
      setUploadsDisabled(state.terminal);
      var items = state.items;
      view = ui.createView({
        state: state,
        items: items,
        columns: ui.COLUMNS,
        readOnly: true,
        verdictText: function (item) { return sessionVerdictText(state, item); },
        toggleVerdict: function () {},
        renderList: renderList
      });
      renderControls();
      renderList();
      renderSummary();
      reportPanel.hidden = envelope.state === "idle";
      filtersPanel.hidden = envelope.state === "idle";
      proposalsPanel.hidden = envelope.state === "idle";
      document.getElementById("vc-fingerprint").textContent = envelope.fingerprint || "";
      if (envelope.state === "closed") {
        announce("This review session has ended. Start a new vault-cleaner serve session.", "error");
      } else if (envelope.state === "idle") {
        announce("Connected. Upload one or more DIM CSV exports to begin.", "ok");
      } else {
        announce("Connected — report loaded in read-only mode.", "ok");
      }
    }
    function renderSummary() {
      if (!view) return;
      var host = document.getElementById("vc-summary");
      view.clear(host);
      var proposed = ui.actionCounts(state.items);
      var kept = ui.actionCounts(ui.keptItems(
        state.items, state.verdicts, state.persistedVetoIds
      ));
      var reviewed = ui.reviewCounts(state.items, state.verdicts);
      var shown = ui.filterItems(state.items, state.query, state.verdicts).length;
      host.appendChild(view.tile("proposed", String(proposed.total),
        proposed.junk + " junk, " + proposed.review + " review"));
      host.appendChild(view.tile("after vetoes", String(kept.total),
        kept.junk + " junk, " + kept.review + " review"));
      host.appendChild(view.tile("reviewed", String(reviewed.approved + reviewed.vetoed),
        reviewed.approved + " approved, " + reviewed.vetoed + " vetoed"));
      host.appendChild(view.tile("shown", String(shown), "matching the current filters"));
      host.appendChild(view.tile("unreviewed", String(reviewed.unreviewed),
        "without a current-session verdict"));
      var overrideHost = document.getElementById("vc-overrides");
      view.clear(overrideHost);
      var statuses = state.envelope && Array.isArray(state.envelope.override_status)
        ? state.envelope.override_status : [];
      if (statuses.length) {
        overrideHost.appendChild(view.el("p", {
          class: "hint", text: statuses.length +
            " persisted override status(es), shown separately from session verdicts:"
        }));
        overrideHost.appendChild(view.el("ul", null, statuses.map(function (entry) {
          return view.el("li", { text: String(entry.status || "unknown") + ": " +
            String(entry.id || "") + (entry.detail ? " — " + String(entry.detail) : "") });
        })));
      }
    }
    function queryChange(field) {
      return function (event) {
        state.query[field] = event.target.value;
        renderList();
        renderSummary();
      };
    }
    function renderControls() {
      if (!view) return;
      var host = document.getElementById("vc-controls");
      view.clear(host);
      host.appendChild(view.el("label", { class: "field", for: "vc-search" }, [
        view.el("span", { text: "Search name or instance id" }),
        view.el("input", {
          type: "search", id: "vc-search", value: state.query.text,
          placeholder: "e.g. Dupe Rifle or 3001",
          on: { input: function (event) {
            state.query.text = event.target.value;
            renderList();
            renderSummary();
          }}
        })
      ]));
      [
        ["vc-f-action", "Action", "action", "any action"],
        ["vc-f-kind", "Kind", "kind", "any kind"],
        ["vc-f-reason", "Reason", "reason", "any reason"],
        ["vc-f-owner", "Owner", "owner", "any owner"]
      ].forEach(function (spec) {
        view.addSelect(host, spec[0], spec[1],
          view.optionsFor(state.items, spec[2], spec[3]), spec[2],
          state.query[spec[2]], queryChange);
      });
      view.addSelect(host, "vc-f-protection", "Protection", [
        view.el("option", { value: "", text: "any" }),
        view.el("option", { value: "protected", text: "protected" }),
        view.el("option", { value: "unprotected", text: "unprotected" }),
        view.el("option", { value: "soft", text: "soft only" }),
        view.el("option", { value: "hard", text: "hard only" })
      ], "protection", state.query.protection, queryChange);
      view.addSelect(host, "vc-f-verdict", "Session verdict", [
        view.el("option", { value: "", text: "any" }),
        view.el("option", { value: "unreviewed", text: "unreviewed" }),
        view.el("option", { value: "approved", text: "approved" }),
        view.el("option", { value: "vetoed", text: "vetoed" })
      ], "verdict", state.query.verdict, queryChange);
      var grouping = view.select("vc-f-group", "View", [
        view.el("option", { value: "grouped", text: "grouped by action/kind/reason" }),
        view.el("option", { value: "flat", text: "one sortable table" })
      ], function (event) {
        state.grouped = event.target.value === "grouped";
        renderList();
      });
      grouping.querySelector("select").value = state.grouped ? "grouped" : "flat";
      host.appendChild(grouping);
      host.appendChild(view.el("button", {
        type: "button", text: "Reset filters",
        on: { click: function () {
          Object.keys(state.query).forEach(function (key) { state.query[key] = ""; });
          renderControls();
          renderList();
          renderSummary();
        }}
      }));
    }
    function renderList() {
      if (!view) return;
      var host = document.getElementById("vc-list");
      view.clear(host);
      var shown = ui.filterItems(state.items, state.query, state.verdicts);
      if (!shown.length) {
        host.appendChild(view.el("p", { class: "hint", text: "No items match these filters." }));
        return;
      }
      var sorted = ui.sortItems(shown, state.sort.field, state.sort.direction);
      if (!state.grouped) {
        host.appendChild(view.table(sorted));
        return;
      }
      ui.groupItems(sorted).forEach(function (group) {
        host.appendChild(view.el("details", { class: "group", open: true }, [
          view.el("summary", { text: group.label }), view.table(group.items)
        ]));
      });
    }
    function markUpload(kind, phase, message) {
      var target = document.getElementById("vc-upload-status-" + kind);
      state.uploadStatus[kind] = phase;
      target.className = phase === "rejected" ? "err" :
        (phase === "accepted" ? "ok" : "hint");
      target.textContent = phase.charAt(0).toUpperCase() + phase.slice(1) +
        (message ? ": " + message : "");
    }
    function upload(kind, file) {
      markUpload(kind, "uploading", "");
      // Do not set a transport length header: browsers own it.  The
      // explicit media type is the server's accepted CSV upload contract.
      root.fetch(ENDPOINTS[kind], {
        method: "POST",
        headers: { "Content-Type": "text/csv", "Accept": "application/json" },
        body: file
      }).then(function (response) {
        if (response.ok) return response.json();
        return responseError(response).then(function (error) {
          var failure = new Error(error.message);
          failure.server = error;
          throw failure;
        });
      }).then(function (envelope) {
        adopt(envelope);
        markUpload(kind, "accepted", "");
      }).catch(function (error) {
        var server = error.server || {};
        markUpload(kind, "rejected", server.message || error.message || "Upload failed");
        if (server.status === 401) {
          fail("The authenticated session is unavailable. Restart vault-cleaner serve and open its new bootstrap URL.", true);
        } else if (server.code === "illegal_state") {
          fail(server.message, true);
        } else if (error.clientCode === "unsupported_envelope") {
          fail(error.message, true);
        } else if (!server.status) {
          fail("Could not reach the review server. Check that it is still running and reconnect.", false);
        }
      });
    }
    function requestReport() {
      setUploadsDisabled(true);
      announce("Connecting to the local review server…", "normal");
      fetchEnvelope("/api/report", { headers: { "Accept": "application/json" } })
        .then(adopt)
        .catch(function (error) {
          var server = error.server || {};
          if (server.status === 401) {
            fail("The authenticated session is unavailable. Restart vault-cleaner serve and open its new bootstrap URL.", true);
          } else if (server.code === "illegal_state") {
            fail(server.message, true);
          } else if (error.clientCode === "unsupported_envelope") {
            fail(error.message, true);
          } else {
            fail("Could not reach the review server. Check that it is still running and reconnect.", false);
          }
        });
    }
    KINDS.forEach(function (kind) {
      document.getElementById("vc-upload-" + kind).addEventListener("change", function (event) {
        var file = event.target.files && event.target.files[0];
        event.target.value = "";
        if (file && !state.terminal) upload(kind, file);
      });
    });
    root.VaultCleanerServerUI = {
      applySessionEnvelope: applySessionEnvelope,
      createState: createState,
      start: requestReport,
      state: state
    };
    requestReport();
  }

  var api = {
    KINDS: KINDS,
    ENDPOINTS: ENDPOINTS,
    applySessionEnvelope: applySessionEnvelope,
    createState: createState,
    persistedVetoIds: persistedVetoIds,
    copyVerdicts: copyVerdicts,
    showReconnect: showReconnect
  };
  if (root && root.document) {
    if (root.document.readyState === "loading") {
      root.document.addEventListener("DOMContentLoaded", function () { boot(root.document); });
    } else {
      boot(root.document);
    }
  }
  return api;
});
