(function (root, factory) {
  "use strict";
  var api = factory(root);
  if (typeof module === "object" && module !== null && module.exports) {
    module.exports = api;
  } else {
    root.VaultCleanerReviewUI = api;
  }
})(typeof globalThis === "object" ? globalThis : this, function (root) {
  "use strict";

  // Shared pure presentation functions and view helpers live here. The static
  // page adapter is a separate resource and is intentionally not part of this
  // served bundle.
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

  function hasPersistedVeto(ids, id) {
    return ids.has(id);
  }

  /**
   * Return a filtered copy excluding persisted or current-session vetoes.
   * Active persisted veto ids must be Set-like with `has(id)`; item ids are
   * opaque strings and are never coerced through Number. Invalid active-id
   * shapes throw TypeError.
   *
   * @param {Array<Object>} items Items with opaque string `id` values.
   * @param {Object} verdicts Current-session verdicts keyed by item id.
   * @param {{has: function(string): boolean}} activePersistedVetoIds
   *   Active persisted veto ids.
   * @returns {Array<Object>} A new filtered array.
   * @throws {TypeError} If activePersistedVetoIds has no callable `has`.
   */
  function keptItems(items, verdicts, activePersistedVetoIds) {
    if (!activePersistedVetoIds ||
        typeof activePersistedVetoIds.has !== "function") {
      throw new TypeError(
        "active persisted veto ids must be a Set-like object with has(id)"
      );
    }
    return items.filter(function (item) {
      return !hasPersistedVeto(activePersistedVetoIds, item.id) &&
             verdictOf(verdicts, item.id) !== "vetoed";
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
  function createView(context) {
    context = context || {};
    var document = context.document || (root && root.document);
    var state = context.state || { sort: { field: "name", direction: "asc" },
      expanded: Object.create(null), rows: Object.create(null), verdicts: Object.create(null) };
    var items = context.items || [];
    var toggleVerdict = context.toggleVerdict || function () {};
    var renderList = context.renderList || function () {};
    var readOnly = context.readOnly === true;
    var verdictText = context.verdictText || function (item, verdict) {
      return verdict || "—";
    };
    var COLUMNS = context.columns || [
      ["name", "Name"], ["id", "Instance id"], ["kind", "Kind"],
      ["owner", "Owner"], ["action", "Action"], ["reason", "Reason"]
    ];
    // Every node is built with createElement/textContent, and no snapshot
    // value is concatenated into innerHTML or into an href/src, so hostile
    // item names remain inert text. A source-level HTML script end-tag marker
    // would truncate the containing element, so never spell one here.
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
    function tile(kind, value, note) {
      return el("div", { class: "tile" }, [
        el("span", { class: "k", text: kind }),
        el("span", { class: "n", text: value }),
        note ? el("span", { class: "sub", text: note }) : null
      ]);
    }
    function select(id, label, options, onChange) {
      return el("label", { class: "field", for: id }, [
        el("span", { text: label }),
        el("select", { id: id, on: { change: onChange } }, options)
      ]);
    }
    function optionsFor(viewItems, field, allLabel) {
      if (arguments.length < 3) {
        allLabel = field;
        field = viewItems;
        viewItems = items;
      }
      var options = [el("option", { value: "", text: allLabel })];
      countBy(viewItems, field).forEach(function (entry) {
        if (entry.value === "") return;
        options.push(el("option", {
          value: entry.value,
          text: entry.value + " (" + entry.count + ")"
        }));
      });
      return options;
    }
    function addSelect(host, id, label, options, field, value, onChange) {
      var node = select(id, label, options, onChange ? onChange(field) : null);
      node.querySelector("select").value = value;
      host.appendChild(node);
    }
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
      var approve = null, veto = null;
      var actions;
      if (readOnly) {
        actions = el("span", { class: "hint", text: verdictText(item, verdict) });
      } else {
        approve = el("button", {
          type: "button", class: "approve", text: "Approve",
          "aria-pressed": verdict === "approved" ? "true" : "false",
          "aria-label": "approve " + (item.name || "unnamed item") + ", id " + item.id,
          on: { click: function () { toggleVerdict(item.id, "approved"); } }
        });
        veto = el("button", {
          type: "button", class: "veto", text: "Veto",
          "aria-pressed": verdict === "vetoed" ? "true" : "false",
          "aria-label": "veto " + (item.name || "unnamed item") + ", id " + item.id,
          on: { click: function () { toggleVerdict(item.id, "vetoed"); } }
        });
        actions = el("div", { class: "row-actions" }, [approve, veto]);
      }
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
        el("td", null, [actions])
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

    return {
      el: el, clear: clear, byId: byId, headerRow: headerRow, definition: definition,
      armorDetail: armorDetail, detailRow: detailRow, itemRows: itemRows, table: table,
      tile: tile, select: select, addSelect: addSelect, optionsFor: optionsFor
    };
  }

  return {
    COLUMNS: [["name", "Name"], ["id", "Instance id"], ["kind", "Kind"],
      ["owner", "Owner"], ["action", "Action"], ["reason", "Reason"]],
    actionCounts: actionCounts, compareIds: compareIds, compareText: compareText,
    countBy: countBy, filterItems: filterItems, groupItems: groupItems, groupLabel: groupLabel,
    isObject: isObject, itemsFromSnapshot: itemsFromSnapshot, keptItems: keptItems,
    matchesProtection: matchesProtection, matchesText: matchesText, requireIdString: requireIdString,
    reviewCounts: reviewCounts, sortItems: sortItems, str: str, verdictOf: verdictOf,
    emptyMap: emptyMap, createView: createView
  };
});
