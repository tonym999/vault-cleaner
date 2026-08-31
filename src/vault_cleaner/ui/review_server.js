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

  var SESSION_SCHEMA_VERSION = 1;
  var SESSION_STATES = ["idle", "exports-loaded", "reviewing", "finalized", "closed"];
  var OVERRIDE_STATUS_VALUES = ["active", "stale", "orphaned", "unchecked"];
  var INCOMPATIBLE_MESSAGE = "The review server returned an incompatible response. Restart vault-cleaner serve and open its new bootstrap URL.";
  var KINDS = ["weapons", "armor", "ghosts"];
  var ENDPOINTS = {
    weapons: "/api/exports/weapons",
    armor: "/api/exports/armor",
    ghosts: "/api/exports/ghosts"
  };
  var VERDICTS_ENDPOINT = "/api/verdicts";
  var FINALIZE_ENDPOINT = "/api/finalize";
  var FINALIZED_CSV_ENDPOINT = "/api/finalized.csv";
  var RESET_ENDPOINT = "/api/reset";
  var SHUTDOWN_ENDPOINT = "/api/shutdown";
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
      server_state: "idle",
      report_revision: 0,
      verdict_revision: 0,
      fingerprint: null,
      snapshot: null,
      override_status: [],
      sort: { field: "name", direction: "asc" },
      grouped: true,
      expanded: emptyMap(),
      query: {
        text: "", action: "", kind: "", reason: "", classFacet: "",
        protection: "", verdict: ""
      },
      // DOM row handles are local presentation state, not part of an envelope.
      rows: emptyMap(),
      viewInvalidated: [],
      reconciliation: { retained: [], discarded: [], invalidated: [] },
      uploadStatus: { weapons: "idle", armor: "idle", ghosts: "idle" },
      bulkControls: [],
      mutationInFlight: null,
      finalizeHeaders: null,
      connected: false,
      terminal: false
    };
  }

  function envelopeError(message) {
    var error = new Error(message);
    error.clientCode = "unsupported_envelope";
    return error;
  }

  function sanitizedOverrideStatus(entries) {
    if (!Array.isArray(entries)) {
      throw envelopeError("session envelope override_status must be a list");
    }
    var seen = emptyMap();
    return entries.map(function (entry, index) {
      if (!isObject(entry) || Object.keys(entry).length !== 3 ||
          !Object.prototype.hasOwnProperty.call(entry, "id") ||
          !Object.prototype.hasOwnProperty.call(entry, "status") ||
          !Object.prototype.hasOwnProperty.call(entry, "detail") ||
          typeof entry.id !== "string" ||
          OVERRIDE_STATUS_VALUES.indexOf(entry.status) === -1 ||
          typeof entry.detail !== "string") {
        throw envelopeError("session envelope override status " + index + " is invalid");
      }
      if (seen[entry.id]) {
        throw envelopeError("session envelope has duplicate override status id " + entry.id);
      }
      seen[entry.id] = true;
      return { id: entry.id, status: entry.status, detail: entry.detail };
    });
  }

  function validateEnvelope(envelope) {
    ["state", "report_revision", "verdict_revision", "fingerprint", "snapshot",
      "verdicts", "override_status"].forEach(function (key) {
      if (!Object.prototype.hasOwnProperty.call(envelope, key)) {
        throw envelopeError("session envelope is missing " + key);
      }
    });
    if (SESSION_STATES.indexOf(envelope.state) === -1) {
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
    if (envelope.fingerprint !== null && typeof envelope.fingerprint !== "string") {
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
    var overrideStatus = sanitizedOverrideStatus(envelope.override_status);
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
    ["retained_verdict_ids", "discarded_verdict_ids"].forEach(function (key) {
      if (envelope[key] === undefined) return;
      if (!Array.isArray(envelope[key]) || envelope[key].some(function (id) {
        return typeof id !== "string";
      })) {
        throw envelopeError("session envelope " + key + " is invalid");
      }
    });
    return overrideStatus;
  }

  function valueStillExists(items, verdicts, field, value) {
    if (!value) return true;
    var query = emptyMap();
    query[field] = value;
    return ui.filterItems(items, query, verdicts).length > 0;
  }

  function applySessionEnvelope(envelope, state) {
    if (!isObject(envelope)) throw envelopeError("session envelope must be an object");
    if (!state || typeof state !== "object") throw new TypeError("state is required");
    if (envelope.schema_version !== SESSION_SCHEMA_VERSION) {
      throw envelopeError("session schema version " + String(envelope.schema_version) +
        " is not supported by this page");
    }
    var nextOverrideStatus = validateEnvelope(envelope);
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
    var invalidated = [];
    Object.keys(state.expanded).forEach(function (id) {
      if (!nextIds.has(id)) {
        delete state.expanded[id];
        invalidated.push("expanded item " + id);
      }
    });
    ["action", "kind", "reason", "classFacet", "protection", "verdict"].forEach(
      function (field) {
        if (state.query[field] &&
            !valueStillExists(nextItems, nextVerdicts, field, state.query[field])) {
          invalidated.push("filter " + field + " " + state.query[field]);
          state.query[field] = "";
        }
      }
    );
    var sortFields = ui.COLUMNS.map(function (column) { return column[0]; });
    if (sortFields.indexOf(state.sort.field) === -1) {
      invalidated.push("sort field " + state.sort.field);
      state.sort = { field: "name", direction: "asc" };
    }
    var reportChanged = state.envelope === null ||
      state.report_revision !== envelope.report_revision ||
      state.fingerprint !== envelope.fingerprint;
    state.envelope = envelope;
    state.server_state = envelope.state;
    state.report_revision = envelope.report_revision;
    state.verdict_revision = envelope.verdict_revision;
    state.fingerprint = envelope.fingerprint;
    state.snapshot = snapshot;
    state.items = nextItems;
    state.verdicts = nextVerdicts;
    state.override_status = nextOverrideStatus;
    state.persistedVetoIds = persistedVetoIds(nextOverrideStatus);
    // A verdict acknowledgement keeps the registry. A new report invalidates it.
    if (reportChanged) state.rows = emptyMap();
    state.viewInvalidated = invalidated.slice();
    state.reconciliation = {
      retained: Array.isArray(envelope.retained_verdict_ids)
        ? envelope.retained_verdict_ids.slice() : [],
      discarded: Array.isArray(envelope.discarded_verdict_ids)
        ? envelope.discarded_verdict_ids.slice() : [],
      invalidated: invalidated.slice()
    };
    state.connected = envelope.state !== "closed";
    state.terminal = envelope.state === "closed";
    return state;
  }

  function sessionVerdictText(state, item) {
    var current = ui.verdictOf(state.verdicts, item.id);
    var persisted = state.persistedVetoIds.has(item.id);
    if (persisted && current === "approved") {
      return "Approved this session · active persisted veto still suppresses this item";
    }
    if (persisted && current === "vetoed") {
      return "Vetoed this session · active persisted veto still suppresses this item";
    }
    if (persisted) return "Active persisted veto still suppresses this item";
    return current || "Unreviewed";
  }

  function visibleIds(items, query, verdicts) {
    var ids = emptyMap();
    ui.filterItems(items, query, verdicts).forEach(function (item) {
      ids[item.id] = true;
    });
    return ids;
  }

  function sameIds(left, right) {
    var leftKeys = Object.keys(left);
    var rightKeys = Object.keys(right);
    if (leftKeys.length !== rightKeys.length) return false;
    return leftKeys.every(function (id) { return right[id] === true; });
  }

  function responseHeader(headers, name) {
    if (!headers) return null;
    if (typeof headers.get === "function") return headers.get(name);
    if (Object.prototype.hasOwnProperty.call(headers, name)) return headers[name];
    var lower = name.toLowerCase();
    return Object.prototype.hasOwnProperty.call(headers, lower) ? headers[lower] : null;
  }

  function responseIsServeOnce(response) {
    return responseHeader(response && response.headers, "Vault-Cleaner-Serve-Once") === "true";
  }

  function finalizeResponseHeaders(response) {
    return {
      reportRevision: responseHeader(response && response.headers, "Vault-Cleaner-Report-Revision"),
      verdictRevision: responseHeader(response && response.headers, "Vault-Cleaner-Verdict-Revision"),
      approvedStillVetoed: responseHeader(response && response.headers, "Vault-Cleaner-Approved-Still-Vetoed"),
      serveOnce: responseIsServeOnce(response)
    };
  }

  function responseError(response) {
    var status = response && response.status;
    var fallback = "request failed (HTTP " + String(status || "unknown") + ")";
    if (!response || typeof response.json !== "function") {
      return Promise.resolve({ kind: "http", status: status, code: "http_error", message: fallback });
    }
    var body;
    try { body = response.json(); } catch (cause) {
      return Promise.resolve({ kind: "http", status: status, code: "invalid_error_body", message: fallback });
    }
    if (!body || typeof body.then !== "function") {
      return Promise.resolve({ kind: "http", status: status, code: "invalid_error_body", message: fallback });
    }
    return body.then(function (payload) {
      var error = payload && payload.error;
      return {
        kind: "http", status: status,
        code: error && error.code || "http_error",
        message: error && typeof error.message === "string" ? error.message : fallback
      };
    }, function () {
      return { kind: "http", status: status, code: "invalid_error_body", message: fallback };
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
    return requestError({ kind: "transport", code: "transport_error",
      message: "Could not reach the review server. Check that it is still running and reconnect." }, cause);
  }
  function incompatibleResponse(cause) {
    return requestError({ kind: "incompatible", code: "incompatible_response",
      message: INCOMPATIBLE_MESSAGE }, cause);
  }
  function responsePayload(response) {
    if (!response || !response.ok) {
      return responseError(response).then(function (error) { throw requestError(error); });
    }
    if (typeof response.json !== "function") {
      throw requestError({ kind: "json", code: "invalid_json", message: INCOMPATIBLE_MESSAGE });
    }
    var body;
    try { body = response.json(); } catch (cause) {
      throw requestError({ kind: "json", code: "invalid_json", message: INCOMPATIBLE_MESSAGE }, cause);
    }
    if (!body || typeof body.then !== "function") {
      throw requestError({ kind: "json", code: "invalid_json", message: INCOMPATIBLE_MESSAGE });
    }
    return body.then(function (payload) { return payload; }, function (cause) {
      throw requestError({ kind: "json", code: "invalid_json", message: INCOMPATIBLE_MESSAGE }, cause);
    });
  }
  function callFetch(path, options) {
    var request;
    try { request = root.fetch(path, options); } catch (cause) {
      return Promise.reject(transportError(cause));
    }
    return request.then(function (response) { return response; }, function (cause) {
      throw transportError(cause);
    });
  }
  function fetchEnvelope(path, options) {
    return callFetch(path, options).then(responsePayload);
  }
  function responseBytes(response) {
    if (!response || !response.ok) {
      return responseError(response).then(function (error) { throw requestError(error); });
    }
    // Read all protocol metadata before asking the browser for the body. A
    // body stream may reject or be absent after the server has committed the
    // result, but the headers still carry the revision and conflict count the
    // finalized UI must disclose.
    var finalizeHeaders = finalizeResponseHeaders(response);
    if (typeof response.arrayBuffer !== "function") {
      var missing = requestError({ kind: "bytes", code: "invalid_bytes", message: INCOMPATIBLE_MESSAGE });
      missing.committedResponse = true;
      missing.serveOnce = finalizeHeaders.serveOnce;
      missing.finalizeHeaders = finalizeHeaders;
      return Promise.reject(missing);
    }
    var value;
    try { value = response.arrayBuffer(); } catch (cause) {
      var thrown = requestError({ kind: "bytes", code: "invalid_bytes", message: INCOMPATIBLE_MESSAGE }, cause);
      thrown.committedResponse = true;
      thrown.serveOnce = finalizeHeaders.serveOnce;
      thrown.finalizeHeaders = finalizeHeaders;
      return Promise.reject(thrown);
    }
    return Promise.resolve(value).then(function (bytes) {
      return { response: response, bytes: bytes, finalizeHeaders: finalizeHeaders };
    }, function (cause) {
      var rejected = requestError({ kind: "bytes", code: "invalid_bytes", message: INCOMPATIBLE_MESSAGE }, cause);
      rejected.committedResponse = true;
      rejected.serveOnce = finalizeHeaders.serveOnce;
      rejected.finalizeHeaders = finalizeHeaders;
      throw rejected;
    });
  }
  function fetchBytes(path, options) {
    return callFetch(path, options).then(responseBytes);
  }

  function makeVerdictPayload(state, decisions) {
    return {
      report_revision: state.report_revision,
      verdict_revision: state.verdict_revision,
      fingerprint: state.fingerprint,
      decisions: decisions.map(function (entry) {
        if (!entry || typeof entry.id !== "string") {
          throw new TypeError("verdict decision id must remain an opaque string");
        }
        return { id: entry.id, verdict: entry.verdict === undefined ? null : entry.verdict };
      })
    };
  }
  function makeFinalizePayload(state) {
    return {
      report_revision: state.report_revision,
      verdict_revision: state.verdict_revision,
      fingerprint: state.fingerprint
    };
  }
  function makeResetPayload(state) {
    return {
      report_revision: state.report_revision,
      verdict_revision: state.verdict_revision
    };
  }
  function makeShutdownOptions() {
    // Deliberately omit body and Content-Type. Normal fetch supplies Origin.
    return { method: "POST", headers: { "Accept": "application/json" } };
  }

  function showReconnect(host, reconnect) {
    if (!host || !host.ownerDocument) return;
    var button = host.ownerDocument.createElement("button");
    button.type = "button";
    button.textContent = "Reconnect";
    button.addEventListener("click", function () { reconnect(); });
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

    function byId(id) { return document.getElementById(id); }
    function setNodeDisabled(node, disabled) { if (node) node.disabled = disabled; }
    function setUploadsDisabled(disabled) {
      KINDS.forEach(function (kind) { setNodeDisabled(byId("vc-upload-" + kind), !!disabled); });
    }
    function announce(message, kind) {
      if (!status) return;
      status.className = kind === "error" ? "err" : (kind === "ok" ? "ok" : "hint");
      status.textContent = message;
    }
    function reportInvalidations() {
      return state.viewInvalidated.length
        ? " Local view state dropped: " + state.viewInvalidated.join("; ") + "." : "";
    }
    function renderSessionNote() {
      var sessionNote = byId("vc-session-note");
      if (!sessionNote) return;
      sessionNote.textContent = state.server_state === "finalized"
        ? "Finalisation succeeded. The reviewed CSV was produced; this session is now frozen."
        : state.server_state === "closed"
          ? "This review session is closed. It cannot accept further uploads or verdicts."
          : "Decisions are held in this server session, but no reviewed CSV has been produced and this session's new vetoes have not been persisted.";
    }
    function fail(message, terminal) {
      state.connected = false;
      state.terminal = !!terminal;
      refreshMutationControls();
      announce(message, "error");
      if (!terminal) showReconnect(status, requestReport);
    }
    function disconnectForRecovery(message) {
      // Keep the known envelope for display, but make it explicitly unsafe to
      // mutate until a fresh authoritative report is adopted. The reconnect
      // control is appended after the announcement because setting
      // textContent clears existing children in a real browser.
      state.connected = false;
      state.terminal = false;
      refreshMutationControls();
      announce(message, "error");
      showReconnect(status, requestReport);
    }
    function handleCommittedFinalizeRefreshFailure(error, message) {
      // The finalize POST already committed the result. Keep this note
      // truthful when the authoritative follow-up report cannot be adopted.
      renderSessionNote();
      var failure = error.failure || {};
      var server = error.server || {};
      // These responses describe a terminal session or an incompatible page,
      // not a transient inability to refresh the already-committed result.
      if (failure.kind === "http" && server.status === 401) {
        fail("The authenticated session is unavailable. Restart vault-cleaner serve and open its new bootstrap URL.", true);
        return;
      }
      if (failure.kind === "http" && server.code === "illegal_state") {
        fail(server.message || "The finalized review session has ended.", true);
        return;
      }
      if (failure.kind === "incompatible" || failure.kind === "json" || failure.kind === "bytes") {
        fail(INCOMPATIBLE_MESSAGE, true);
        return;
      }
      var recoveryMessage = message;
      if (failure.kind === "http" && server.status) {
        recoveryMessage = recoveryMessage.replace(/[.]$/, "") +
          " (HTTP " + String(server.status) + ").";
      }
      disconnectForRecovery(recoveryMessage);
    }
    function handleCommonFailure(error) {
      var failure = error.failure || {};
      var server = failure.kind === "http" ? error.server || {} : {};
      if (failure.kind === "http" && server.status === 401) {
        fail("The authenticated session is unavailable. Restart vault-cleaner serve and open its new bootstrap URL.", true);
        return true;
      }
      if (failure.kind === "http" && server.code === "illegal_state") {
        fail(server.message, true);
        return true;
      }
      if (failure.kind === "incompatible" || failure.kind === "json" || failure.kind === "bytes") {
        fail(INCOMPATIBLE_MESSAGE, true);
        return true;
      }
      if (failure.kind === "transport") {
        fail(error.message, false);
        return true;
      }
      return false;
    }
    function mutationAllowed() {
      return state.connected && !state.terminal && state.server_state !== "finalized" && !state.mutationInFlight;
    }
    function lifecycleAllowed() {
      return state.connected && !state.terminal && !state.mutationInFlight;
    }
    function mutationControlsDisabled() {
      return !!state.mutationInFlight || !state.connected || state.terminal ||
        state.server_state === "finalized";
    }
    function refreshMutationControls() {
      var disabled = mutationControlsDisabled();
      setUploadsDisabled(disabled);
      state.bulkControls.forEach(function (control) { control.disabled = disabled; });
      if (view && typeof view.setVerdictControlsDisabled === "function") {
        view.setVerdictControlsDisabled(disabled);
      }
      renderSessionActions();
    }
    function setMutationGate(label) {
      state.mutationInFlight = label;
      refreshMutationControls();
    }
    function buildView() {
      view = ui.createView({
        document: document, state: state, items: state.items, columns: ui.COLUMNS,
        readOnly: false,
        verdictDisabled: function () {
          return !!state.mutationInFlight || state.terminal || state.server_state === "finalized" || !state.connected;
        },
        verdictText: function (item, verdict) { return sessionVerdictText(state, item, verdict); },
        toggleVerdict: toggleVerdict,
        clearVerdict: function (id) { mutateVerdicts([{ id: id, verdict: null }], "Clear"); },
        renderList: renderList
      });
    }
    function repaintRows() {
      if (!view || typeof view.paintRow !== "function") return;
      Object.keys(state.rows).forEach(function (id) { view.paintRow(id); });
    }
    function adopt(envelope) {
      var beforeRevision = state.report_revision;
      var beforeFingerprint = state.fingerprint;
      var beforeVisible = state.envelope === null
        ? null : visibleIds(state.items, state.query, state.verdicts);
      try {
        applySessionEnvelope(envelope, state);
      } catch (error) {
        throw incompatibleResponse(error);
      }
      var rebuilt = !view || beforeRevision !== state.report_revision || beforeFingerprint !== state.fingerprint;
      var membershipChanged = beforeVisible !== null &&
        !sameIds(beforeVisible, visibleIds(state.items, state.query, state.verdicts));
      var controlsInvalidated = state.viewInvalidated.some(function (entry) {
        return entry.indexOf("filter ") === 0 || entry.indexOf("sort field ") === 0;
      });
      var queryInvalidated = state.viewInvalidated.filter(function (entry) {
        return entry.indexOf("filter ") === 0;
      });
      if (rebuilt) {
        buildView();
        renderControls();
        renderList();
      } else {
        // applySessionEnvelope may clear an invalid filter while preserving
        // the report revision. Synchronize only affected live controls;
        // rebuilding the panel would steal search focus and discard edits.
        queryInvalidated.forEach(function (entry) {
          var field = entry.slice("filter ".length).split(" ")[0];
          var control = byId("vc-f-" + field);
          if (control) control.value = state.query[field];
        });
        if (membershipChanged || controlsInvalidated) renderList();
        else repaintRows();
      }
      refreshMutationControls();
      renderSummary();
      if (reportPanel) reportPanel.hidden = envelope.state === "idle";
      if (filtersPanel) filtersPanel.hidden = envelope.state === "idle";
      if (proposalsPanel) proposalsPanel.hidden = envelope.state === "idle";
      var fingerprintNode = byId("vc-fingerprint");
      if (fingerprintNode) fingerprintNode.textContent = envelope.fingerprint || "";
      renderSessionNote();
      var recon = byId("vc-reconciliation");
      if (recon) {
        recon.textContent = "";
        if (state.reconciliation.retained.length) recon.textContent += "Retained verdict IDs: " + state.reconciliation.retained.join(", ") + ". ";
        if (state.reconciliation.discarded.length) recon.textContent += "Discarded verdict IDs: " + state.reconciliation.discarded.join(", ") + ". ";
        recon.textContent += reportInvalidations();
        recon.hidden = !recon.textContent;
      }
      return { rebuilt: rebuilt, invalidated: state.viewInvalidated.slice() };
    }
    function renderSummary() {
      if (!view) return;
      var host = byId("vc-summary");
      if (!host) return;
      view.clear(host);
      var proposed = ui.actionCounts(state.items);
      var kept = ui.actionCounts(ui.keptItems(state.items, state.verdicts, state.persistedVetoIds));
      var reviewed = ui.reviewCounts(state.items, state.verdicts);
      var shown = ui.filterItems(state.items, state.query, state.verdicts).length;
      host.appendChild(view.tile("proposed", String(proposed.total), proposed.junk + " junk, " + proposed.review + " review"));
      host.appendChild(view.tile("after vetoes", String(kept.total), kept.junk + " junk, " + kept.review + " review"));
      host.appendChild(view.tile("reviewed", String(reviewed.approved + reviewed.vetoed), reviewed.approved + " approved, " + reviewed.vetoed + " vetoed"));
      host.appendChild(view.tile("shown", String(shown), "matching the current filters"));
      host.appendChild(view.tile("unreviewed", String(reviewed.unreviewed), "without a current-session verdict"));
      var overrideHost = byId("vc-overrides");
      if (!overrideHost) return;
      view.clear(overrideHost);
      if (state.override_status.length) {
        overrideHost.appendChild(view.el("p", { class: "hint", text: state.override_status.length + " persisted override status(es), shown separately from session verdicts:" }));
        overrideHost.appendChild(view.el("ul", null, state.override_status.map(function (entry) {
          return view.el("li", { text: String(entry.status || "unknown") + ": " + String(entry.id || "") + (entry.detail ? " — " + String(entry.detail) : "") });
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
      var host = byId("vc-controls");
      if (!host) return;
      view.clear(host);
      state.bulkControls = [];
      host.appendChild(view.el("label", { class: "field", for: "vc-search" }, [
        view.el("span", { text: "Search name or instance id" }),
        view.el("input", { type: "search", id: "vc-search", value: state.query.text,
          placeholder: "e.g. Dupe Rifle or 3001", on: { input: function (event) {
            state.query.text = event.target.value; renderList(); renderSummary();
          } } })
      ]));
      [["vc-f-action", "Action", "action", "any action"], ["vc-f-kind", "Kind", "kind", "any kind"],
       ["vc-f-reason", "Reason", "reason", "any reason"], ["vc-f-class", "Class", "classFacet", "any class"]].forEach(function (spec) {
        view.addSelect(host, spec[0], spec[1], view.optionsFor(state.items, spec[2], spec[3]), spec[2], state.query[spec[2]], queryChange);
      });
      view.addSelect(host, "vc-f-protection", "Protection", [
        view.el("option", { value: "", text: "any" }), view.el("option", { value: "protected", text: "protected" }),
        view.el("option", { value: "unprotected", text: "unprotected" }), view.el("option", { value: "soft", text: "soft only" }),
        view.el("option", { value: "hard", text: "hard only" })
      ], "protection", state.query.protection, queryChange);
      view.addSelect(host, "vc-f-verdict", "Session verdict", [
        view.el("option", { value: "", text: "any" }), view.el("option", { value: "unreviewed", text: "unreviewed" }),
        view.el("option", { value: "approved", text: "approved" }), view.el("option", { value: "vetoed", text: "vetoed" })
      ], "verdict", state.query.verdict, queryChange);
      var grouping = view.select("vc-f-group", "View", [
        view.el("option", { value: "grouped", text: "grouped by action/kind/reason" }), view.el("option", { value: "flat", text: "one sortable table" })
      ], function (event) { state.grouped = event.target.value === "grouped"; renderList(); });
      var groupingSelect = grouping.querySelector("select");
      if (groupingSelect) groupingSelect.value = state.grouped ? "grouped" : "flat";
      host.appendChild(grouping);
      var bulkApprove = view.el("button", { id: "vc-bulk-approve", type: "button", text: "Approve all shown", disabled: mutationControlsDisabled(), on: { click: function () { bulkVerdict("approved"); } } });
      var bulkVeto = view.el("button", { id: "vc-bulk-veto", type: "button", text: "Veto all shown", disabled: mutationControlsDisabled(), on: { click: function () { bulkVerdict("vetoed"); } } });
      var bulkUnset = view.el("button", { id: "vc-bulk-unset", type: "button", text: "Unset all shown", disabled: mutationControlsDisabled(), on: { click: function () { bulkVerdict(null); } } });
      state.bulkControls = [bulkApprove, bulkVeto, bulkUnset];
      host.appendChild(view.el("div", { class: "field" }, [
        view.el("span", { text: "Bulk action on shown items" }),
        view.el("div", { class: "row-actions" }, [
          bulkApprove, bulkVeto, bulkUnset
        ])
      ]));
      host.appendChild(view.el("button", { type: "button", text: "Reset filters", on: { click: function () {
        Object.keys(state.query).forEach(function (key) { state.query[key] = ""; });
        renderControls(); renderList(); renderSummary();
      } } }));
    }
    function renderList() {
      if (!view) return;
      var host = byId("vc-list");
      if (!host) return;
      view.clear(host);
      state.rows = emptyMap();
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
        host.appendChild(view.el("details", { class: "group", open: true }, [view.el("summary", { text: group.label }), view.table(group.items)]));
      });
    }
    function renderSessionActions() {
      var host = byId("vc-actions");
      if (!host || !view) return;
      view.clear(host);
      var disabled = !!state.mutationInFlight || !state.connected || state.terminal;
      if (state.server_state === "finalized") {
        // A successful finalise response is committed even when its body or
        // follow-up report cannot be read. Download remains a safe recovery
        // action while disconnected; reset/shutdown still require a live
        // authoritative session.
        var downloadDisabled = !!state.mutationInFlight || state.terminal;
        var lifecycleDisabled = !!state.mutationInFlight || !state.connected || state.terminal;
        var suppression = state.finalizeHeaders && state.finalizeHeaders.approvedStillVetoed;
        var suppressionText = "";
        if (typeof suppression === "string" && suppression !== "0" && /^(?:0|[1-9][0-9]*)$/.test(suppression)) {
          suppressionText = suppression === "1"
            ? " 1 approved item remains suppressed by an active persisted veto."
            : " " + suppression + " approved items remain suppressed by active persisted vetoes.";
        }
        host.appendChild(view.el("p", { class: "ok", text: "Finalised — this review is frozen. The reviewed CSV has been produced." + suppressionText }));
        host.appendChild(view.el("button", { id: "vc-download-again", type: "button", text: "Download again", disabled: downloadDisabled, on: { click: downloadAgain } }));
        host.appendChild(view.el("button", { id: "vc-reset", type: "button", text: "Reset / Start new review", disabled: lifecycleDisabled, on: { click: resetSession } }));
        host.appendChild(view.el("button", { id: "vc-shutdown", type: "button", text: "Shutdown", disabled: lifecycleDisabled, on: { click: shutdownSession } }));
        return;
      }
      if (state.server_state === "exports-loaded" || state.server_state === "reviewing") {
        host.appendChild(view.el("button", { id: "vc-finalize", type: "button", text: "Finalise review", disabled: disabled, on: { click: finalizeSession } }));
        host.appendChild(view.el("button", { id: "vc-reset", type: "button", text: "Reset / Start new review", disabled: disabled, on: { click: resetSession } }));
      }
      if (state.server_state !== "closed") {
        host.appendChild(view.el("button", { id: "vc-shutdown", type: "button", text: "Shutdown", disabled: disabled, on: { click: shutdownSession } }));
      }
      if (state.server_state === "idle" && state.connected) {
        host.appendChild(view.el("p", { class: "hint", text: "Connected. Upload one or more DIM CSV exports to begin." }));
      }
    }
    function markUpload(kind, phase, message) {
      var target = byId("vc-upload-status-" + kind);
      state.uploadStatus[kind] = phase;
      if (!target) return;
      target.className = phase === "rejected" ? "err" : (phase === "accepted" ? "ok" : "hint");
      target.textContent = phase.charAt(0).toUpperCase() + phase.slice(1) + (message ? ": " + message : "");
    }
    function upload(kind, file) {
      if (!mutationAllowed()) return;
      markUpload(kind, "uploading", "");
      setMutationGate("upload");
      fetchEnvelope(ENDPOINTS[kind], { method: "POST", headers: { "Content-Type": "text/csv", "Accept": "application/json" }, body: file })
        .then(function (envelope) {
          adopt(envelope); markUpload(kind, "accepted", ""); setMutationGate(null);
          if (state.reconciliation.retained.length || state.reconciliation.discarded.length) {
            announce("Upload accepted." + reportInvalidations() +
              (state.reconciliation.retained.length ? " Retained verdict IDs: " + state.reconciliation.retained.join(", ") + "." : "") +
              (state.reconciliation.discarded.length ? " Discarded verdict IDs: " + state.reconciliation.discarded.join(", ") + "." : ""), "ok");
          }
        }).catch(function (error) {
          setMutationGate(null);
          var server = error.server || {};
          markUpload(kind, "rejected", server.message || error.message || "Upload failed");
          if (handleCommonFailure(error)) return;
        });
    }
    function requestReport() {
      setUploadsDisabled(true);
      announce("Connecting to the local review server…", "normal");
      fetchEnvelope("/api/report", { headers: { "Accept": "application/json" } }).then(function (envelope) {
        adopt(envelope);
        if (envelope.state === "idle") announce("Connected. Upload one or more DIM CSV exports to begin.", "ok");
        else if (envelope.state === "finalized") announce("This review is finalised and frozen.", "ok");
        else if (envelope.state === "closed") announce("This review session has ended. Start a new vault-cleaner serve session.", "error");
        else announce("Connected — report loaded with server-backed verdict controls.", "ok");
      }).catch(function (error) {
        var failure = error.failure || {};
        var server = error.server || {};
        var handled = handleCommonFailure(error);
        if (!handled && failure.kind === "http") fail("The review server returned an HTTP error (" + String(server.status || "unknown") + "). Try reconnecting.", false);
        else if (!handled) fail("The review server request failed. Try reconnecting.", false);
      });
    }
    function mutateVerdicts(decisions, description) {
      if (!mutationAllowed()) return Promise.resolve(false);
      var payload = makeVerdictPayload(state, decisions);
      setMutationGate("verdicts");
      return fetchEnvelope(VERDICTS_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" }, body: JSON.stringify(payload) })
        .then(function (envelope) {
          var result = adopt(envelope);
          setMutationGate(null);
          announce((description || "Verdict") + " acknowledged for " + decisions.length + " item(s)." + reportInvalidations(), "ok");
          return result;
        }).catch(function (error) {
          var server = error.server || {};
          if (server.code === "stale_report" || server.code === "stale_verdicts") return reconcileStale(description || "Verdict");
          setMutationGate(null);
          if (!handleCommonFailure(error)) announce(server.message || error.message || "Verdict request failed.", "error");
          return false;
        });
    }
    function reconcileStale(description) {
      setMutationGate("reconciling");
      return fetchEnvelope("/api/report", { headers: { "Accept": "application/json" } }).then(function (envelope) {
        adopt(envelope); setMutationGate(null);
        announce("Your " + description.toLowerCase() + " was not applied because this review is stale. Repeat the action." + reportInvalidations(), "error");
        return false;
      }).catch(function (error) {
        setMutationGate(null);
        if (!handleCommonFailure(error)) disconnectForRecovery("Your " + description.toLowerCase() + " was not applied because this review is stale, and the current report could not be fetched. Repeat the action after reconnecting.");
        return false;
      });
    }
    function toggleVerdict(id, verdict) {
      if (!mutationAllowed()) return;
      mutateVerdicts([{ id: String(id), verdict: verdict }], verdict === "approved" ? "Approve" : "Veto");
    }
    function bulkVerdict(verdict) {
      if (!mutationAllowed()) return;
      var shown = ui.filterItems(state.items, state.query, state.verdicts);
      mutateVerdicts(shown.map(function (item) { return { id: item.id, verdict: verdict === null ? null : verdict }; }), verdict === "approved" ? "Approve all" : (verdict === "vetoed" ? "Veto all" : "Unset all"));
    }
    function downloadBlob(bytes) {
      if (!root.Blob || !root.URL || typeof root.URL.createObjectURL !== "function" || typeof root.URL.revokeObjectURL !== "function" || !document.body) throw new Error("browser download APIs are unavailable");
      var objectUrl = null;
      var link = null;
      try {
        objectUrl = root.URL.createObjectURL(new root.Blob([bytes], { type: "text/csv" }));
        link = document.createElement("a"); link.href = objectUrl; link.download = "dim-import.csv";
        document.body.appendChild(link); link.click(); document.body.removeChild(link);
      } finally {
        if (objectUrl !== null) root.URL.revokeObjectURL(objectUrl);
      }
    }
    function finishOnceSession(message, kind) {
      state.server_state = "finalized";
      state.connected = false;
      state.terminal = true;
      renderSessionNote();
      refreshMutationControls();
      announce(message, kind || "ok");
    }
    function afterCsvDownload(result, source) {
      state.finalizeHeaders = result.finalizeHeaders || finalizeResponseHeaders(result.response);
      // A successful CSV response is itself proof that the server committed
      // finalisation (and a finalized.csv response is likewise terminal for
      // the report). Freeze mutation controls while the envelope refresh runs.
      state.server_state = "finalized";
      // Set the committed lifecycle note before any download handling or
      // authoritative report refresh can await. A slow report must not leave
      // the pre-finalization explanation visible after POST /api/finalize.
      renderSessionNote();
      var downloadError = null;
      try { downloadBlob(result.bytes); } catch (error) { downloadError = error; }
      if (source === "retry") {
        // A successful finalized.csv response proves the still-running
        // session is reachable even when the earlier report refresh failed.
        // Restore lifecycle actions after the download gate is released; the
        // report remains frozen and verdict controls stay disabled.
        state.connected = true;
        state.terminal = false;
        renderSessionNote();
        refreshMutationControls();
        announce(downloadError
          ? "Finalisation succeeded, but download handling failed. Use Download again."
          : "Downloaded dim-import.csv again.", downloadError ? "error" : "ok");
        return Promise.resolve(!downloadError);
      }
      if (state.finalizeHeaders.serveOnce) {
        finishOnceSession(downloadError
          ? "Finalisation succeeded, but the CSV could not be handled before the --once server stopped. Start a new review session."
          : "Finalised and downloaded dim-import.csv. The --once review server has stopped; start a new review session for another review.",
        downloadError ? "error" : "ok");
        return Promise.resolve(!downloadError);
      }
      return fetchEnvelope("/api/report", { headers: { "Accept": "application/json" } }).then(function (envelope) {
        adopt(envelope);
        if (envelope.state === "closed") {
          announce("Finalisation succeeded, but this review session has ended. Start a new vault-cleaner serve session.", "error");
        } else if (downloadError) announce("Finalisation succeeded, but download handling failed. Use Download again." + reportInvalidations(), "error");
        else announce("Finalised and downloaded dim-import.csv.", "ok");
        return !downloadError;
      }).catch(function (error) {
        // The CSV response already committed finalisation. Preserve the
        // terminal/recoverable distinction of the failed refresh rather than
        // flattening every response into ordinary disconnection.
        var refreshMessage = "Finalisation succeeded, but the finalized session state could not be refreshed. Use Download again or reconnect.";
        if (downloadError) refreshMessage = "Finalisation succeeded, but download handling and the finalized session state could not be refreshed. Use Download again or reconnect.";
        handleCommittedFinalizeRefreshFailure(error, refreshMessage);
        return false;
      });
    }
    function recoverCommittedFinalize(reason) {
      state.server_state = "finalized";
      renderSessionNote();
      return fetchEnvelope("/api/report", { headers: { "Accept": "application/json" } }).then(function (envelope) {
        adopt(envelope);
        setMutationGate(null);
        if (envelope.state === "closed") {
          announce("Finalisation succeeded, but this review session has ended. Start a new vault-cleaner serve session.", "error");
        } else {
          announce("Finalisation succeeded, but " + reason + ". Use Download again." + reportInvalidations(), "error");
        }
        return false;
      }).catch(function (error) {
        setMutationGate(null);
        handleCommittedFinalizeRefreshFailure(error, "Finalisation succeeded, but " + reason + ". Use Download again or reconnect.");
        return false;
      });
    }
    function finalizeSession() {
      if (!lifecycleAllowed() || state.server_state === "idle") return;
      var reviewed = ui.reviewCounts(state.items, state.verdicts);
      if (reviewed.unreviewed > 0) {
        var message = "Unreviewed proposals will remain in the generated import CSV unless an existing active persisted veto suppresses them. Continue?";
        if (typeof root.confirm === "function" && !root.confirm(message)) return;
      }
      setMutationGate("finalize");
      fetchBytes(FINALIZE_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json", "Accept": "text/csv" }, body: JSON.stringify(makeFinalizePayload(state)) })
        .then(function (result) { return afterCsvDownload(result, "finalize"); })
        .then(function () { setMutationGate(null); })
        .catch(function (error) {
          if (error.committedResponse) {
            state.finalizeHeaders = error.finalizeHeaders || state.finalizeHeaders;
            if (error.serveOnce) {
              finishOnceSession("Finalisation succeeded, but the CSV response could not be read before the --once server stopped. Start a new review session.", "error");
              setMutationGate(null);
            } else {
              recoverCommittedFinalize("the CSV response could not be read");
            }
            return;
          }
          setMutationGate(null);
          var server = error.server || {};
          if (server.code === "stale_report" || server.code === "stale_verdicts") {
            reconcileStale("Finalise");
          } else if (!handleCommonFailure(error)) {
            announce(server.message || error.message || "Finalisation failed.", "error");
          }
        });
    }
    function downloadAgain() {
      if (state.server_state !== "finalized" || state.mutationInFlight) return;
      setMutationGate("download");
      fetchBytes(FINALIZED_CSV_ENDPOINT, { headers: { "Accept": "text/csv" } }).then(function (result) { return afterCsvDownload(result, "retry"); })
        .then(function () { setMutationGate(null); })
        .catch(function (error) {
          if (error.committedResponse) {
            state.finalizeHeaders = error.finalizeHeaders || state.finalizeHeaders;
            state.server_state = "finalized";
            state.connected = true;
            state.terminal = false;
            renderSessionNote();
            setMutationGate(null);
            announce("Finalisation succeeded, but download handling failed. Use Download again.", "error");
            return;
          }
          setMutationGate(null);
          handleCommittedFinalizeRefreshFailure(error, "Finalisation succeeded, but Download again failed. Use Download again or reconnect.");
        });
    }
    function resetSession() {
      if (!lifecycleAllowed()) return;
      setMutationGate("reset");
      fetchEnvelope(RESET_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" }, body: JSON.stringify(makeResetPayload(state)) }).then(function (envelope) {
        adopt(envelope); setMutationGate(null); announce("Review reset. Durable overrides were not changed.", "ok");
      }).catch(function (error) {
        setMutationGate(null);
        var server = error.server || {};
        if (server.code === "stale_report" || server.code === "stale_verdicts") {
          reconcileStale("Reset");
        } else if (!handleCommonFailure(error)) {
          announce(server.message || error.message || "Reset failed.", "error");
        }
      });
    }
    function shutdownSession() {
      if (!lifecycleAllowed()) return;
      setMutationGate("shutdown");
      fetchEnvelope(SHUTDOWN_ENDPOINT, makeShutdownOptions()).then(function (envelope) {
        // The shutdown response is authoritative; do not request the report again.
        adopt(envelope); setMutationGate(null);
        announce("This review session has ended. Shutdown completed; start a new vault-cleaner serve session for another review.", "error");
      }).catch(function (error) {
        setMutationGate(null);
        if (!handleCommonFailure(error)) announce((error.server && error.server.message) || error.message || "Shutdown failed.", "error");
      });
    }
    function rowForTarget(target) {
      var node = target;
      if (node && typeof node.closest === "function") return node.closest("tr[data-id]");
      while (node) {
        if (node.getAttribute && node.getAttribute("data-id") !== null) return node;
        node = node.parentNode;
      }
      return null;
    }
    if (typeof document.addEventListener === "function") document.addEventListener("keydown", function (event) {
      if (event.ctrlKey || event.metaKey || event.altKey || !mutationAllowed()) return;
      var tag = ((event.target && event.target.tagName) || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      var row = rowForTarget(event.target);
      if (!row || !row.getAttribute) return;
      var id = row.getAttribute("data-id");
      var key = String(event.key || "").toLowerCase();
      if (key === "a") toggleVerdict(id, "approved");
      else if (key === "v") toggleVerdict(id, "vetoed");
      else if (key === "u") mutateVerdicts([{ id: String(id), verdict: null }], "Clear");
      else return;
      if (event.preventDefault) event.preventDefault();
    });
    KINDS.forEach(function (kind) {
      var input = byId("vc-upload-" + kind);
      if (!input || typeof input.addEventListener !== "function") return;
      input.addEventListener("change", function (event) {
        var file = event.target.files && event.target.files[0]; event.target.value = "";
        if (file && !state.terminal) upload(kind, file);
      });
    });
    liveState = state;
    liveStart = requestReport;
    requestReport();
  }

  var api = {
    SESSION_STATES: SESSION_STATES.slice(), KINDS: KINDS, ENDPOINTS: ENDPOINTS,
    VERDICTS_ENDPOINT: VERDICTS_ENDPOINT, FINALIZE_ENDPOINT: FINALIZE_ENDPOINT,
    FINALIZED_CSV_ENDPOINT: FINALIZED_CSV_ENDPOINT, RESET_ENDPOINT: RESET_ENDPOINT,
    SHUTDOWN_ENDPOINT: SHUTDOWN_ENDPOINT, applySessionEnvelope: applySessionEnvelope,
    createState: createState, persistedVetoIds: persistedVetoIds, copyVerdicts: copyVerdicts,
    showReconnect: showReconnect, responseError: responseError, fetchEnvelope: fetchEnvelope,
    makeVerdictPayload: makeVerdictPayload, makeFinalizePayload: makeFinalizePayload,
    makeResetPayload: makeResetPayload, makeShutdownOptions: makeShutdownOptions,
    start: function () { if (liveStart) return liveStart.apply(null, arguments); }
  };
  Object.defineProperty(api, "state", { enumerable: true, get: function () { return liveState; } });
  if (root && root.document) {
    if (root.document.readyState === "loading") root.document.addEventListener("DOMContentLoaded", function () { boot(root.document); });
    else boot(root.document);
  }
  return api;
});
