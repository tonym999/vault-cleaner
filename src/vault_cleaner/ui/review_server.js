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
  var liveStart = null;
  var liveState = null;
  var booted = false;

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

  function validateEnvelope(envelope) {
    var states = ["idle", "exports-loaded", "reviewing", "finalized", "closed"];
    ["state", "report_revision", "verdict_revision", "fingerprint", "snapshot",
      "verdicts", "override_status"].forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(envelope, key)) {
        throw envelopeError("session envelope is missing " + key);
      }
    });
    if (states.indexOf(envelope.state) === -1) {
      throw envelopeError("session envelope state is not supported");
    }
    if (typeof envelope.report_revision !== "number" ||
        !isFinite(envelope.report_revision) ||
        Math.floor(envelope.report_revision) !== envelope.report_revision ||
        envelope.report_revision < 0) {
      throw envelopeError("session envelope report revision is invalid");
    }
    if (typeof envelope.verdict_revision !== "number" ||
        !isFinite(envelope.verdict_revision) ||
        Math.floor(envelope.verdict_revision) !== envelope.verdict_revision ||
        envelope.verdict_revision < 0) {
      throw envelopeError("session envelope verdict revision is invalid");
    }
    if (envelope.fingerprint !== null &&
        typeof envelope.fingerprint !== "string") {
      throw envelopeError("session envelope fingerprint is invalid");
    }
    if (envelope.snapshot !== null && envelope.snapshot !== undefined) {
      if (!isObject(envelope.snapshot) || !Array.isArray(envelope.snapshot.sections)) {
        throw envelopeError("session envelope snapshot is invalid");
      }
      envelope.snapshot.sections.forEach(function (section, index) {
        if (!isObject(section) || !Array.isArray(section.decisions)) {
          throw envelopeError("session envelope section " + index + " is invalid");
        }
      });
    } else if (envelope.state !== "idle" && envelope.state !== "closed") {
      throw envelopeError("session envelope snapshot is required in this state");
    }
    if (envelope.verdicts !== undefined) {
      if (!Array.isArray(envelope.verdicts)) {
        throw envelopeError("session envelope verdicts must be a list");
      }
      var seenVerdicts = emptyMap();
      envelope.verdicts.forEach(function (entry, index) {
        if (!isObject(entry) || typeof entry.id !== "string" ||
            (entry.verdict !== "approved" && entry.verdict !== "vetoed")) {
          throw envelopeError("session envelope verdict " + index + " is invalid");
        }
        if (seenVerdicts[entry.id]) {
          throw envelopeError("session envelope has duplicate verdict id " + entry.id);
        }
        seenVerdicts[entry.id] = true;
      });
    }
    ["retained_verdict_ids", "discarded_verdict_ids"].forEach(function (key) {
      if (envelope[key] === undefined) return;
      if (!Array.isArray(envelope[key]) || envelope[key].some(function (id) {
        return typeof id !== "string";
      })) {
        throw envelopeError("session envelope " + key + " is invalid");
      }
    });
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
    if (!isObject(envelope)) throw envelopeError("session envelope must be an object");
    if (!state || typeof state !== "object") throw new TypeError("state is required");
    if (envelope.schema_version !== SESSION_SCHEMA_VERSION) {
      throw envelopeError("session schema version " +
        String(envelope.schema_version) + " is not supported by this page");
    }
    validateEnvelope(envelope);
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
    var status = response && response.status;
    var fallback = "request failed (HTTP " + String(status || "unknown") + ")";
    if (!response || typeof response.json !== "function") {
      return Promise.resolve({
        kind: "http", status: status, code: "http_error", message: fallback
      });
    }
    var body;
    try {
      body = response.json();
    } catch (cause) {
      return Promise.resolve({
        kind: "http", status: status, code: "invalid_error_body", message: fallback
      });
    }
    if (!body || typeof body.then !== "function") {
      return Promise.resolve({
        kind: "http", status: status, code: "invalid_error_body", message: fallback
      });
    }
    return body.then(function (payload) {
      var error = payload && payload.error;
      var message = error && typeof error.message === "string"
        ? error.message : fallback;
      return {
        kind: "http", status: status,
        code: error && error.code || "http_error", message: message
      };
    }, function () {
      return {
        kind: "http", status: status, code: "invalid_error_body", message: fallback
      };
    });
  }

  function requestError(failure, cause) {
    var error = new Error(failure.message);
    error.clientCode = failure.code;
    error.failure = failure;
    if (failure.kind === "http") error.server = failure;
    if (cause) error.cause = cause;
    return error;
  }

  function transportError(cause) {
    return requestError({
      kind: "transport", code: "transport_error",
      message: "Could not reach the review server. Check that it is still running and reconnect."
    }, cause);
  }

  function incompatibleResponse(cause) {
    return requestError({
      kind: "incompatible", code: "incompatible_response",
      message: "The review server returned an incompatible response. Restart vault-cleaner serve and open its new bootstrap URL."
    }, cause);
  }

  function responsePayload(response) {
    if (!response || !response.ok) {
      return responseError(response).then(function (error) {
        throw requestError(error);
      });
    }
    if (typeof response.json !== "function") {
      throw requestError({
        kind: "json", code: "invalid_json",
        message: "The review server returned an invalid JSON response."
      });
    }
    var body;
    try {
      body = response.json();
    } catch (cause) {
      throw requestError({
        kind: "json", code: "invalid_json",
        message: "The review server returned an invalid JSON response."
      }, cause);
    }
    if (!body || typeof body.then !== "function") {
      throw requestError({
        kind: "json", code: "invalid_json",
        message: "The review server returned an invalid JSON response."
      });
    }
    return body.then(function (payload) {
      return payload;
    }, function (cause) {
      throw requestError({
        kind: "json", code: "invalid_json",
        message: "The review server returned an invalid JSON response."
      }, cause);
    });
  }

  function fetchEnvelope(path, options) {
    var request;
    try {
      request = root.fetch(path, options);
    } catch (cause) {
      return Promise.reject(transportError(cause));
    }
    return request.then(function (response) {
      return responsePayload(response);
    }, function (cause) {
      throw transportError(cause);
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
    if (booted || !ui || !root.fetch) return;
    booted = true;
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
    function handleCommonFailure(error) {
      var server = error.server || {};
      if (server.status === 401) {
        fail("The authenticated session is unavailable. Restart vault-cleaner serve and open its new bootstrap URL.", true);
        return true;
      }
      if (server.code === "illegal_state") {
        fail(server.message, true);
        return true;
      }
      if (error.clientCode === "incompatible_response" ||
          error.clientCode === "invalid_json") {
        fail(error.clientCode === "invalid_json"
          ? "The review server returned an incompatible response. Restart vault-cleaner serve and open its new bootstrap URL."
          : error.message, true);
        return true;
      }
      if (error.clientCode === "transport_error") {
        fail(error.message, false);
        return true;
      }
      return false;
    }
    function adopt(envelope) {
      try {
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
      } catch (error) {
        throw incompatibleResponse(error);
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
      fetchEnvelope(ENDPOINTS[kind], {
        method: "POST",
        headers: { "Content-Type": "text/csv", "Accept": "application/json" },
        body: file
      }).then(function (envelope) {
        adopt(envelope);
        markUpload(kind, "accepted", "");
      }).catch(function (error) {
        var server = error.server || {};
        markUpload(kind, "rejected", server.message || error.message || "Upload failed");
        if (handleCommonFailure(error)) return;
      });
    }
    function requestReport() {
      setUploadsDisabled(true);
      announce("Connecting to the local review server…", "normal");
      fetchEnvelope("/api/report", { headers: { "Accept": "application/json" } })
        .then(adopt)
        .catch(function (error) {
          var server = error.server || {};
          var handled = handleCommonFailure(error);
          if (!handled && server.kind === "http") {
            fail("The review server returned an HTTP error (" +
              String(server.status || "unknown") + "). Try reconnecting.", false);
          } else if (!handled) {
            fail("The review server request failed. Try reconnecting.", false);
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
    liveState = state;
    liveStart = requestReport;
    requestReport();
  }

  var api = {
    KINDS: KINDS,
    ENDPOINTS: ENDPOINTS,
    applySessionEnvelope: applySessionEnvelope,
    createState: createState,
    persistedVetoIds: persistedVetoIds,
    copyVerdicts: copyVerdicts,
    showReconnect: showReconnect,
    responseError: responseError,
    fetchEnvelope: fetchEnvelope,
    start: function () {
      if (liveStart) return liveStart.apply(null, arguments);
    }
  };
  Object.defineProperty(api, "state", {
    enumerable: true,
    get: function () { return liveState; }
  });
  if (root && root.document) {
    if (root.document.readyState === "loading") {
      root.document.addEventListener("DOMContentLoaded", function () { boot(root.document); });
    } else {
      boot(root.document);
    }
  }
  return api;
});
