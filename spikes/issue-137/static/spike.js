// Spike browser script for #137.  It installs server-rendered fragments and
// keeps only browser-owned state: the adopted envelope, which filter is
// selected, focus, and the in-flight gate.  It builds no report DOM.
//
// Two experiment switches are read from the query string and checked against
// fixed lists; neither is ever sent to the server as a template or path:
//   ?repaint=r1|r2|r3      what happens after a verdict acknowledgement
//   ?filters=browser|server  who decides which groups are shown
(function () {
  "use strict";

  var FRAGMENT_PATH = "/spike/fragments/armor-duplicates";
  var MAX_SYNC_ATTEMPTS = 3;
  var params = new URLSearchParams(window.location.search);

  function choice(name, allowed, fallback) {
    var value = params.get(name);
    return allowed.indexOf(value) === -1 ? fallback : value;
  }

  var REPAINT = choice("repaint", ["r1", "r2", "r3"], "r1");
  var FILTERS = choice("filters", ["browser", "server"], "browser");

  function byId(id) { return document.getElementById(id); }
  function each(list, callback) { Array.prototype.forEach.call(list, callback); }

  var statusNode = byId("vc-status");
  var reconciliationNode = byId("vc-reconciliation");
  var scopeNode = byId("vc-duplicate-scope");
  var emptyNode = byId("vc-duplicate-empty");
  var listNode = byId("vc-duplicate-list");
  var classSelect = byId("vc-dup-f-guardianClass");
  var fingerprintNode = byId("vc-fingerprint");

  var state = {
    envelope: null,
    verdicts: Object.create(null),
    inFlight: false,
    usable: false,
    frozen: false,
    kind: "all",
    guardianClass: "",
    totalGroups: 0,
    totalPieces: 0
  };
  var log = [];

  function note(message) { log.push(message); }

  function announce(message, kind) {
    statusNode.className = kind === "error" ? "err" : (kind === "ok" ? "ok" : "hint");
    statusNode.textContent = message;
  }

  function setScope(text) {
    if (scopeNode.textContent !== text) scopeNode.textContent = text;
  }

  function request(path, options) {
    return fetch(path, options).then(function (response) {
      return response.text().then(function (text) {
        return { response: response, text: text };
      });
    });
  }

  function getEnvelope() {
    return request("/api/report", { headers: { "Accept": "application/json" } }).then(function (result) {
      if (!result.response.ok) {
        throw new Error("report request failed (HTTP " + result.response.status + ")");
      }
      return JSON.parse(result.text);
    });
  }

  // Adopt one authoritative envelope.  Returns whether the report changed.
  function adopt(envelope) {
    if (!envelope || envelope.schema_version !== 1 || !Array.isArray(envelope.verdicts)) {
      throw new Error("incompatible session envelope");
    }
    var verdicts = Object.create(null);
    envelope.verdicts.forEach(function (entry) {
      if (typeof entry.id !== "string") throw new Error("verdict id must be a string");
      if (entry.verdict === "approved" || entry.verdict === "vetoed") {
        verdicts[entry.id] = entry.verdict;
      }
    });
    var previous = state.envelope;
    var reportChanged = !previous ||
      previous.report_revision !== envelope.report_revision ||
      previous.fingerprint !== envelope.fingerprint;
    state.envelope = envelope;
    state.verdicts = verdicts;
    state.usable = envelope.state !== "closed";
    fingerprintNode.textContent = envelope.fingerprint || "";
    return reportChanged;
  }

  // [filters-b:start] server-owned filtering (experiment E10, candidate b)
  function fragmentUrl() {
    if (FILTERS !== "server") return FRAGMENT_PATH;
    var query = new URLSearchParams();
    query.set("kind", state.kind);
    if (state.guardianClass) query.set("guardian_class", state.guardianClass);
    return FRAGMENT_PATH + "?" + query.toString();
  }

  function applyServerFilters() {
    return loadFragment().then(install).catch(function (error) {
      note("server filter failed: " + error.message);
      announce("Filters need the review server, which could not be reached.", "error");
    });
  }
  // [filters-b:end]

  // [fragment-seam:start] fetch, check and install a fragment
  // Fetch the fragment and accept it only when its revision header pair
  // equals the adopted envelope's.  Otherwise re-read the envelope and try
  // again, a bounded number of times.  A discarded fragment is never parsed.
  function loadFragment(attempt) {
    var round = attempt || 1;
    return request(fragmentUrl(), { headers: { "Accept": "text/html" } }).then(function (result) {
      if (!result.response.ok) {
        throw new Error("fragment request failed (HTTP " + result.response.status + ")");
      }
      var report = result.response.headers.get("Vault-Cleaner-Report-Revision");
      var verdict = result.response.headers.get("Vault-Cleaner-Verdict-Revision");
      var adopted = state.envelope;
      if (report !== String(adopted.report_revision) || verdict !== String(adopted.verdict_revision)) {
        note("fragment discarded: rendered for report " + report + " verdict " + verdict +
          "; adopted report " + adopted.report_revision + " verdict " + adopted.verdict_revision);
        if (round >= MAX_SYNC_ATTEMPTS) throw new Error("fragment and envelope did not converge");
        return getEnvelope().then(function (envelope) {
          adopt(envelope);
          return loadFragment(round + 1);
        });
      }
      // DOMParser builds an inert document: scripts in it never run and
      // images in it never load.  Nothing is assigned to innerHTML.
      var parsed = new DOMParser().parseFromString(result.text, "text/html");
      var root = parsed.querySelector('[data-vc-fragment="armor-duplicates"]');
      if (!root || root.getAttribute("data-report-revision") !== report ||
          root.getAttribute("data-verdict-revision") !== verdict) {
        throw new Error("fragment is malformed");
      }
      note("fragment accepted: report " + report + " verdict " + verdict);
      return root;
    });
  }

  function readRoot(root) {
    state.frozen = root.getAttribute("data-vc-frozen") === "true";
    state.totalGroups = Number(root.getAttribute("data-total-groups"));
    state.totalPieces = Number(root.getAttribute("data-total-pieces"));
    state.serverScope = root.getAttribute("data-scope-text");
  }

  function importedPart(root, name) {
    return document.importNode(root.querySelector('[data-vc-part="' + name + '"]'), true);
  }

  function installOptions(root) {
    var selected = state.guardianClass;
    var options = importedPart(root, "class-options");
    classSelect.replaceChildren.apply(classSelect, Array.prototype.slice.call(options.childNodes));
    classSelect.value = selected;
    if (classSelect.value !== selected) {
      state.guardianClass = "";
      classSelect.value = "";
      reconciliationNode.textContent = "Local view state dropped: duplicate filter guardianClass " + selected + ".";
      reconciliationNode.hidden = false;
    }
  }

  function afterInstall() {
    paint();
    gate();
    if (FILTERS === "server") {
      emptyNode.hidden = true;
      setScope(state.serverScope);
    } else {
      applyBrowserFilters();
    }
  }

  // Replace the list with the fragment's content.
  function install(root) {
    readRoot(root);
    installOptions(root);
    var list = importedPart(root, "list");
    listNode.replaceChildren.apply(listNode, Array.prototype.slice.call(list.childNodes));
    afterInstall();
  }
  // [fragment-seam:end]

  // [repaint-r3:start] refetch and patch (experiment E5 only)
  // R3: apply only attribute and text differences to the existing nodes.
  function sameShape(current, next) {
    if (current.nodeType !== next.nodeType || current.nodeName !== next.nodeName) return false;
    if (current.childNodes.length !== next.childNodes.length) return false;
    for (var index = 0; index < current.childNodes.length; index++) {
      if (!sameShape(current.childNodes[index], next.childNodes[index])) return false;
    }
    return true;
  }

  function patch(current, next) {
    if (current.nodeType === 3) {
      if (current.data !== next.data) current.data = next.data;
      return;
    }
    if (current.nodeType !== 1) return;
    each(Array.prototype.slice.call(current.attributes), function (attribute) {
      if (!next.hasAttribute(attribute.name)) current.removeAttribute(attribute.name);
    });
    each(next.attributes, function (attribute) {
      if (current.getAttribute(attribute.name) !== attribute.value) {
        current.setAttribute(attribute.name, attribute.value);
      }
    });
    for (var index = 0; index < current.childNodes.length; index++) {
      patch(current.childNodes[index], next.childNodes[index]);
    }
  }

  function patchInstall(root) {
    var list = importedPart(root, "list");
    if (!sameShape(listNode, list)) {
      note("patch fell back to replace: fragment shape differs");
      install(root);
      return;
    }
    readRoot(root);
    for (var index = 0; index < listNode.childNodes.length; index++) {
      patch(listNode.childNodes[index], list.childNodes[index]);
    }
    afterInstall();
  }
  // [repaint-r3:end]

  // [fragment-seam:start] in-place verdict paint
  // R1: flip state on the existing nodes from the adopted envelope.  The
  // three texts a member can show were rendered by the server; this picks one.
  function paint() {
    each(listNode.querySelectorAll("[data-vc-verdict-id]"), function (cell) {
      var current = state.verdicts[cell.getAttribute("data-vc-verdict-id")] || "";
      each(cell.querySelectorAll("[data-vc-verdict-value]"), function (button) {
        var pressed = button.getAttribute("data-vc-verdict-value") === current ? "true" : "false";
        if (button.getAttribute("aria-pressed") !== pressed) button.setAttribute("aria-pressed", pressed);
      });
      var text = cell.querySelector("[data-vc-verdict-text]");
      if (text) {
        var next = text.getAttribute("data-vc-text-" + (current || "unset"));
        var leaf = text.firstChild;
        if (leaf && leaf.nodeType === 3 && !leaf.nextSibling) {
          if (leaf.data !== next) leaf.data = next;
        } else {
          text.textContent = next;
        }
      }
    });
  }
  // [fragment-seam:end]

  function controlsDisabled() {
    return state.inFlight || !state.usable || state.frozen;
  }

  function gate() {
    var disabled = controlsDisabled();
    each(listNode.querySelectorAll("button[data-vc-verdict-value]"), function (button) {
      button.disabled = disabled;
    });
  }

  function finish() {
    state.inFlight = false;
    gate();
  }

  // [fragment-seam:start] focus restoration by a stable key
  function keyOf(node) {
    return node && node.getAttribute ? node.getAttribute("data-vc-key") : null;
  }

  function restoreFocus(key) {
    if (!key || keyOf(document.activeElement) === key) return;
    var target = null;
    each(listNode.querySelectorAll("[data-vc-key]"), function (node) {
      if (!target && node.getAttribute("data-vc-key") === key) target = node;
    });
    if (target) target.focus();
  }
  // [fragment-seam:end]

  function repaintAfterAck() {
    if (REPAINT === "r1") {
      paint();
      return Promise.resolve();
    }
    return loadFragment().then(REPAINT === "r3" ? patchInstall : install);
  }

  function describe(value) {
    return value === "approved" ? "Approve" : (value === "vetoed" ? "Veto" : "Clear");
  }

  function reconcile(description, focusKey) {
    return getEnvelope().then(function (envelope) {
      var reportChanged = adopt(envelope);
      var repaint;
      if (reportChanged || REPAINT === "r2") repaint = loadFragment().then(install);
      else if (REPAINT === "r3") repaint = loadFragment().then(patchInstall);
      else repaint = Promise.resolve(paint());
      return repaint.then(function () {
        finish();
        restoreFocus(focusKey);
        announce("Your " + description.toLowerCase() +
          " was not applied because this review is stale. Repeat the action.", "error");
      });
    });
  }

  function mutate(id, value) {
    if (controlsDisabled()) return;
    var description = describe(value);
    var focusKey = keyOf(document.activeElement);
    var payload = {
      report_revision: state.envelope.report_revision,
      verdict_revision: state.envelope.verdict_revision,
      fingerprint: state.envelope.fingerprint,
      decisions: [{ id: id, verdict: value === "" ? null : value }]
    };
    state.inFlight = true;
    gate();
    request("/api/verdicts", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (result) {
      var body = JSON.parse(result.text);
      if (result.response.ok) {
        adopt(body);
        return repaintAfterAck().then(function () {
          finish();
          restoreFocus(focusKey);
          announce(description + " acknowledged for 1 item(s).", "ok");
        });
      }
      var code = body && body.error && body.error.code;
      if (code === "stale_report" || code === "stale_verdicts") {
        return reconcile(description, focusKey);
      }
      finish();
      announce((body && body.error && body.error.message) || "Verdict request failed.", "error");
    }).catch(function (error) {
      note("mutation failed: " + error.message);
      state.usable = false;
      finish();
      announce("Could not reach the review server.", "error");
    });
  }

  // [filters-a:start] browser-owned filtering (experiment E10, candidate a)
  // The server rendered every group and wrote the values to match on as
  // data-* attributes; this hides groups and words the scope sentence.
  function browserScopeText(shownGroups, shownPieces) {
    var parts = [];
    if (state.kind === "exact") parts.push("exact duplicates");
    else if (state.kind === "same_stat") parts.push("same-stat groups");
    if (state.guardianClass) parts.push("class " + state.guardianClass);
    var groupWord = state.totalGroups === 1 ? "group" : "groups";
    var pieceWord = state.totalPieces === 1 ? "piece" : "pieces";
    if (!parts.length) {
      return state.totalGroups + " " + groupWord + " · " + state.totalPieces + " " + pieceWord;
    }
    return shownGroups + " of " + state.totalGroups + " " + groupWord + " · " +
      shownPieces + " of " + state.totalPieces + " " + pieceWord +
      " — filtered to " + parts.join(", ");
  }

  function applyBrowserFilters() {
    var shownGroups = 0;
    var shownPieces = 0;
    var shownKinds = Object.create(null);
    each(listNode.querySelectorAll("article.armor-group"), function (article) {
      var kind = article.getAttribute("data-vc-filter-kind");
      var match = (state.kind === "all" || kind === state.kind) &&
        (!state.guardianClass ||
          article.getAttribute("data-vc-guardian-class") === state.guardianClass);
      article.hidden = !match;
      if (match) {
        shownGroups += 1;
        shownPieces += Number(article.getAttribute("data-member-count"));
        shownKinds[kind] = true;
      }
    });
    each(listNode.querySelectorAll("[data-vc-section]"), function (head) {
      head.hidden = !shownKinds[head.getAttribute("data-vc-section")];
    });
    emptyNode.hidden = shownGroups > 0 || state.totalGroups === 0;
    setScope(browserScopeText(shownGroups, shownPieces));
  }
  // [filters-a:end]

  function filtersChanged() {
    if (FILTERS === "server") return applyServerFilters();
    applyBrowserFilters();
    return Promise.resolve();
  }

  each(document.querySelectorAll("button[data-vc-kind]"), function (button) {
    button.addEventListener("click", function () {
      state.kind = button.getAttribute("data-vc-kind");
      each(document.querySelectorAll("button[data-vc-kind]"), function (other) {
        other.setAttribute("aria-pressed", other === button ? "true" : "false");
      });
      filtersChanged();
    });
  });

  classSelect.addEventListener("change", function () {
    state.guardianClass = classSelect.value;
    filtersChanged();
  });

  // One delegated listener on the persistent host: installing a fragment
  // never needs to bind handlers to the nodes it brings.
  listNode.addEventListener("click", function (event) {
    var button = event.target.closest("button[data-vc-verdict-value]");
    if (!button || button.disabled) return;
    var cell = button.closest("[data-vc-verdict-id]");
    mutate(cell.getAttribute("data-vc-verdict-id"), button.getAttribute("data-vc-verdict-value"));
  });

  function refresh() {
    return getEnvelope().then(function (envelope) {
      adopt(envelope);
      return loadFragment().then(install);
    });
  }

  window.VaultCleanerSpike = {
    log: log,
    mode: { repaint: REPAINT, filters: FILTERS },
    refresh: refresh
  };

  refresh().then(function () {
    announce("Connected — report loaded.", "ok");
  }).catch(function (error) {
    note("start failed: " + error.message);
    announce("The review server request failed.", "error");
  });
})();
