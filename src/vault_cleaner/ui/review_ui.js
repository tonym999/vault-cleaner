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

  // Shared pure presentation functions and view helpers live here. The server
  // adapter is a separate resource and is intentionally not part of this
  // shared bundle.
  function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
  }

  // Data-keyed maps only: ids, reasons, classes, and locations come from the vault, so
  // an item named "__proto__" must not be able to reach Object.prototype.
  function emptyMap() {
    return Object.create(null);
  }

  function str(value) {
    return value === null || value === undefined ? "" : String(value);
  }

  function normalizeCategoricalValue(value) {
    var text = str(value);
    return text === "" ? "none/unknown" : text;
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

  function tuningComparison(candidate, selected) {
    if (candidate === null || candidate === undefined ||
        selected === null || selected === undefined) return "—";
    return "Candidate: " + String(candidate) + " · Selected: " + String(selected);
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
          location: str(decision.location),
          guardianClass: str(decision.guardian_class),
          // Class-neutral sections remain browseable from the Class facet
          // without writing a synthetic class into the snapshot model.
          classFacet: str(decision.guardian_class) || str(decision.kind) || str(section.kind),
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
          candidateTuningModSlot: decision.candidate_tuning_mod_slot === null ||
            decision.candidate_tuning_mod_slot === undefined
            ? null : str(decision.candidate_tuning_mod_slot),
          selectedTuningModSlot: decision.selected_tuning_mod_slot === null ||
            decision.selected_tuning_mod_slot === undefined
            ? null : str(decision.selected_tuning_mod_slot),
          tuningModSlot: tuningComparison(
            decision.candidate_tuning_mod_slot,
            decision.selected_tuning_mod_slot
          ),
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
      if (q.classFacet && item.classFacet !== q.classFacet) return false;
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

  var SORT_FIELDS = ["name", "id", "kind", "classFacet", "location",
    "action", "reason", "tuningModSlot"];

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

  // Armor duplicate groups are an authoritative report projection.  This
  // helper intentionally copies the presentation fields while preserving the
  // array order supplied by Python.  In particular, it does not derive a
  // fingerprint, select a survivor, or sort members in the browser.
  function exactDuplicateGroupsFromSnapshot(snapshot) {
    var groups = [];
    var sections = (snapshot && snapshot.sections) || [];
    var seenGroups = emptyMap();
    var proposalActions = emptyMap();
    sections.forEach(function (section) {
      (section && Array.isArray(section.decisions) ? section.decisions : []).forEach(function (decision) {
        if (!isObject(decision) || (decision.action !== "junk" && decision.action !== "review")) return;
        var id = requireIdString(decision.id, "proposal decision id");
        proposalActions[id] = decision.action;
      });
    });
    for (var s = 0; s < sections.length; s++) {
      var section = sections[s] || {};
      var armor = section.armor;
      if (section.kind !== "armor" || !armor ||
          !Array.isArray(armor.exact_duplicate_groups)) continue;
      armor.exact_duplicate_groups.forEach(function (source, index) {
        var where = "sections[" + s + "].armor.exact_duplicate_groups[" + index + "]";
        if (!isObject(source)) throw new Error(where + " must be an object");
        var groupId = requireIdString(source.group_id, where + ".group_id");
        var hash = requireIdString(source.hash, where + ".hash");
        var preferred = requireIdString(
          source.preferred_survivor_id, where + ".preferred_survivor_id"
        );
        if (seenGroups[groupId]) {
          throw new Error("duplicate exact duplicate group id " + groupId);
        }
        seenGroups[groupId] = true;
        if (!Array.isArray(source.members) || source.members.length === 0) {
          throw new Error(where + ".members must be a non-empty list");
        }
        var seenMembers = emptyMap();
        var members = source.members.map(function (member, memberIndex) {
          var memberWhere = where + ".members[" + memberIndex + "]";
          if (!isObject(member)) throw new Error(memberWhere + " must be an object");
          var id = requireIdString(member.id, memberWhere + ".id");
          if (seenMembers[id]) throw new Error("duplicate member id " + id + " at " + memberWhere);
          seenMembers[id] = true;
          var disposition = str(member.disposition);
          var proposalAction = member.proposal_action === null ||
            member.proposal_action === undefined ? "" : str(member.proposal_action);
          if (["preferred_survivor", "retained_protected", "proposed_junk",
            "proposed_review"].indexOf(disposition) === -1) {
            throw new Error(memberWhere + " has an unsupported disposition");
          }
          var expectedAction = disposition === "proposed_junk" ? "junk" :
            disposition === "proposed_review" ? "review" : "";
          if (proposalAction !== expectedAction ||
              (proposalAction && proposalActions[id] !== proposalAction)) {
            throw new Error(memberWhere + " has inconsistent disposition/proposal action");
          }
          return {
            id: id,
            location: str(member.location),
            protectionLevel: member.protection_level === null ||
              member.protection_level === undefined ? "" : str(member.protection_level),
            protectionReason: str(member.protection_reason),
            equipped: member.equipped === true,
            inLoadout: member.in_loadout === true,
            locked: member.locked === true,
            masterworkTier: member.masterwork_tier,
            power: member.power,
            disposition: disposition,
            proposalAction: proposalAction,
            proposalReason: member.proposal_reason === null ||
              member.proposal_reason === undefined ? "" : str(member.proposal_reason)
          };
        });
        groups.push({
          groupKind: str(source.group_kind) || "exact_duplicate",
          groupId: groupId,
          hash: hash,
          name: str(source.name),
          type: normalizeCategoricalValue(source.type),
          guardianClass: normalizeCategoricalValue(source.guardian_class),
          itemArchetype: normalizeCategoricalValue(source.item_archetype),
          tier: source.tier,
          stats: isObject(source.stats) ? Object.keys(source.stats).reduce(function (copy, name) {
            copy[name] = source.stats[name];
            return copy;
          }, emptyMap()) : emptyMap(),
          tuningModSlot: normalizeCategoricalValue(source.tuning_mod_slot),
          seasonalMod: str(source.seasonal_mod),
          holofoil: str(source.holofoil),
          spiritSignature: Array.isArray(source.spirit_signature)
            ? source.spirit_signature.map(str) : [],
          preferredSurvivorId: preferred,
          members: members
        });
      });
    }
    return groups;
  }

  function matchesArmorGroup(group, query) {
    var q = query || {};
    var needle = str(q.text).trim().toLowerCase();
    if (needle) {
      var nameMatch = str(group.name).toLowerCase().indexOf(needle) !== -1;
      var idMatch = group.members.some(function (member) {
        return member.id.indexOf(str(q.text).trim()) !== -1;
      });
      if (!nameMatch && !idMatch) return false;
    }
    if (q.guardianClass && normalizeCategoricalValue(group.guardianClass) !== normalizeCategoricalValue(q.guardianClass)) return false;
    if (q.type && normalizeCategoricalValue(group.type) !== normalizeCategoricalValue(q.type)) return false;
    if (q.itemArchetype && normalizeCategoricalValue(group.itemArchetype) !== normalizeCategoricalValue(q.itemArchetype)) return false;
    if (q.tuningModSlot && normalizeCategoricalValue(group.tuningModSlot) !== normalizeCategoricalValue(q.tuningModSlot)) return false;
    return true;
  }

  function filterArmorGroups(groups, query) {
    return (groups || []).filter(function (group) {
      return matchesArmorGroup(group, query);
    });
  }

  function countArmorGroups(groups, field) {
    var counts = emptyMap();
    (groups || []).forEach(function (group) {
      var value = normalizeCategoricalValue(group[field]);
      counts[value] = (counts[value] || 0) + 1;
    });
    return Object.keys(counts).map(function (value) {
      return { value: value, count: counts[value] };
    }).sort(function (a, b) { return compareText(a.value, b.value); });
  }

  // Return a display-only stat model.  The role labels are deliberately
  // derived from the six supplied values rather than a second archetype table.
  function armorStatDisplay(group) {
    var stats = group && isObject(group.stats) ? group.stats : emptyMap();
    var names = Object.keys(stats);
    var values = names.map(function (name) { return stats[name]; });
    var tier5 = group && group.tier === 5 && names.length === 6 &&
      values.filter(function (value) { return value === 30; }).length === 1 &&
      values.filter(function (value) { return value === 25; }).length === 1 &&
      values.filter(function (value) { return value === 20; }).length === 1 &&
      values.filter(function (value) { return value === 0; }).length === 3;
    if (!tier5) {
      return {
        tier5: false,
        rows: names.map(function (name) { return { name: name, value: stats[name] }; }),
        zeroSummary: ""
      };
    }
    var roles = { 30: "Primary", 25: "Secondary", 20: "Tertiary" };
    return {
      tier5: true,
      rows: names.filter(function (name) { return stats[name] !== 0; }).map(function (name) {
        return { name: name, value: stats[name], role: roles[stats[name]] };
      }),
      zeroSummary: "The other three base stats are 0 on this tier-5 piece."
    };
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
  /**
   * Build the DOM-facing view for a report.
   *
   * ``context.readOnly`` is a presentation-only mode. When it is true each
   * row renders ``context.verdictText(item, verdict)`` as text and does not
   * create verdict buttons; consequently the verdict handles are null. When
   * it is false, the row handles are buttons wired to ``context.toggleVerdict``
   * and ``context.clearVerdict``. The view also exposes ``paintRow`` so an
   * acknowledged server verdict can update the existing DOM nodes without
   * rebuilding the table (and thereby losing keyboard focus).
   */
  function createView(context) {
    context = context || {};
    var document = context.document || (root && root.document);
    var state = context.state || { sort: { field: "name", direction: "asc" },
      expanded: Object.create(null), rows: Object.create(null), verdicts: Object.create(null) };
    if (!state.duplicateRows) state.duplicateRows = emptyMap();
    var items = context.items || [];
    var toggleVerdict = context.toggleVerdict || function () {};
    var clearVerdict = context.clearVerdict || function (id) {
      toggleVerdict(id, "");
    };
    var verdictDisabled = context.verdictDisabled || function () { return false; };
    var renderList = context.renderList || function () {};
    var readOnly = context.readOnly === true;
    var verdictText = context.verdictText || function (item, verdict) {
      return verdict || "—";
    };
    var COLUMNS = context.columns || [
      ["name", "Name"], ["id", "Instance id"], ["kind", "Kind"],
      ["classFacet", "Class"], ["location", "Location"],
      ["action", "Action"], ["reason", "Reason"],
      ["tuningModSlot", "Tuning Mod Slot"]
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
          if (key === "disabled") { node.disabled = !!value; if (value) node.setAttribute(key, ""); return; }
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
      var approve = null, veto = null, clear = null, presentation = null;
      var actions;
      if (readOnly) {
        actions = el("span", { class: "hint", text: verdictText(item, verdict) });
      } else {
        approve = el("button", {
          type: "button", class: "approve", text: "Approve",
          "aria-pressed": verdict === "approved" ? "true" : "false",
          "aria-label": "approve " + (item.name || "unnamed item") + ", id " + item.id,
          disabled: verdictDisabled(),
          on: { click: function () { toggleVerdict(item.id, "approved"); } }
        });
        veto = el("button", {
          type: "button", class: "veto", text: "Veto",
          "aria-pressed": verdict === "vetoed" ? "true" : "false",
          "aria-label": "veto " + (item.name || "unnamed item") + ", id " + item.id,
          disabled: verdictDisabled(),
          on: { click: function () { toggleVerdict(item.id, "vetoed"); } }
        });
        clear = el("button", {
          type: "button", class: "clear-verdict", text: "Unset",
          "aria-pressed": verdict === "" ? "true" : "false",
          "aria-label": "unset verdict for " + (item.name || "unnamed item") +
            ", id " + item.id,
          disabled: verdictDisabled(),
          on: { click: function () { clearVerdict(item.id); } }
        });
        presentation = el("span", {
          class: "verdict-presentation",
          text: verdictText(item, verdict)
        });
        actions = el("div", { class: "row-actions" }, [
          approve, veto, clear, presentation
        ]);
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
        el("td", { text: item.classFacet }),
        el("td", { text: item.location }),
        el("td", null, [el("span", {
          class: "badge " + (item.action === "junk" ? "junk" : "review"),
          text: item.action
        })]),
        el("td", { text: item.reason }),
        el("td", { text: item.tuningModSlot }),
        el("td", { text: item.protectionLevel || "—" }),
        el("td", null, [actions])
      ]);
      state.rows[item.id] = {
        tr: tr, approve: approve, veto: veto, clear: clear,
        presentation: presentation, item: item
      };
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

    function paintRow(id) {
      var row = state.rows[id];
      if (!row) return false;
      var current = verdictOf(state.verdicts, id);
      row.tr.className = current === "vetoed" ? "vetoed" : "";
      if (row.approve) {
        row.approve.setAttribute("aria-pressed", current === "approved" ? "true" : "false");
        row.veto.setAttribute("aria-pressed", current === "vetoed" ? "true" : "false");
        row.clear.setAttribute("aria-pressed", current === "" ? "true" : "false");
        row.approve.disabled = verdictDisabled();
        row.veto.disabled = verdictDisabled();
        row.clear.disabled = verdictDisabled();
      }
      if (row.presentation) row.presentation.textContent = verdictText(row.item, current);
      return true;
    }

    function setVerdictControlsDisabled(disabled) {
      Object.keys(state.rows).forEach(function (id) {
        var row = state.rows[id];
        [row.approve, row.veto, row.clear].forEach(function (control) {
          if (control) control.disabled = !!disabled;
        });
      });
      Object.keys(state.duplicateRows).forEach(function (id) {
        var row = state.duplicateRows[id];
        [row.approve, row.veto, row.clear].forEach(function (control) {
          if (control) control.disabled = !!disabled;
        });
      });
    }

    function dispositionLabel(member) {
      if (member.disposition === "preferred_survivor") return "Preferred survivor";
      if (member.disposition === "retained_protected") return "Retained protected";
      if (member.disposition === "proposed_junk") return "Proposed junk";
      if (member.disposition === "proposed_review") return "Proposed review";
      return member.disposition || "Unclassified member";
    }

    function isProposalMember(member) {
      return (member.disposition === "proposed_junk" && member.proposalAction === "junk") ||
        (member.disposition === "proposed_review" && member.proposalAction === "review");
    }

    function armorGroupHeader(group) {
      var statDisplay = armorStatDisplay(group);
      var statNodes = statDisplay.rows.map(function (row) {
        return tile(row.role || "Base stat", str(row.name) + " " + str(row.value));
      });
      return el("header", { class: "armor-group-header" }, [
        el("h3", { text: group.name || "(unnamed armor)" }),
        el("p", { class: "sub", text: "Exact duplicate group · " + group.groupKind }),
        el("div", { class: "armor-group-meta" }, [
          tile("Type / slot", group.type || "unknown"),
          tile("Guardian class", group.guardianClass || "class-neutral/unknown"),
          tile("Tier", group.tier === null || group.tier === undefined ? "unknown" : group.tier),
          tile("Hash", group.hash),
          tile("Archetype", group.itemArchetype || "none/unknown"),
          tile("Tuning Mod Slot", group.tuningModSlot)
        ]),
        el("div", { class: "armor-stat-summary", "aria-label": "Base stat summary" }, statNodes),
        statDisplay.zeroSummary ? el("p", { class: "hint", text: statDisplay.zeroSummary }) : null,
        group.spiritSignature.length ? tile("Spirit signature", group.spiritSignature.join(" · ")) : null,
        group.seasonalMod ? tile("Seasonal Mod", group.seasonalMod) : null,
        group.holofoil && group.holofoil.toLowerCase() !== "false"
          ? tile("Holofoil", group.holofoil) : null
      ]);
    }

    function armorMemberCell(member) {
      var proposal = isProposalMember(member);
      var verdict = verdictOf(state.verdicts, member.id);
      var approve = null, veto = null, clearVerdict = null, presentation = null;
      if (proposal && !readOnly) {
        approve = el("button", {
          type: "button", class: "approve", text: "Approve",
          "aria-pressed": verdict === "approved" ? "true" : "false",
          "aria-label": "approve armor member id " + member.id,
          disabled: verdictDisabled(),
          on: { click: function () { toggleVerdict(member.id, "approved"); } }
        });
        veto = el("button", {
          type: "button", class: "veto", text: "Veto",
          "aria-pressed": verdict === "vetoed" ? "true" : "false",
          "aria-label": "veto armor member id " + member.id,
          disabled: verdictDisabled(),
          on: { click: function () { toggleVerdict(member.id, "vetoed"); } }
        });
        clearVerdict = el("button", {
          type: "button", class: "clear-verdict", text: "Unset",
          "aria-pressed": verdict === "" ? "true" : "false",
          "aria-label": "unset verdict for armor member id " + member.id,
          disabled: verdictDisabled(),
          on: { click: function () { clearVerdict(member.id); } }
        });
        presentation = el("span", {
          class: "verdict-presentation", text: verdictText(member, verdict)
        });
      } else {
        var readonlyText = proposal
          ? verdictText(member, verdict)
          : "Read-only · " + dispositionLabel(member);
        presentation = el("span", { class: "hint", text: readonlyText });
      }
      var controls = proposal && !readOnly
        ? el("div", { class: "row-actions" }, [approve, veto, clearVerdict, presentation])
        : presentation;
      var cell = el("td", { class: "armor-member-cell", "data-member-id": member.id }, [controls]);
      state.duplicateRows[member.id] = {
        cell: cell, approve: approve, veto: veto, clear: clearVerdict,
        presentation: presentation, member: member
      };
      return cell;
    }

    function armorGroupTable(group) {
      var headerCells = [el("th", { scope: "col", text: "Comparison" })];
      group.members.forEach(function (member, index) {
        headerCells.push(el("th", { scope: "col", class: "armor-member-heading" }, [
          el("span", { class: "armor-member-number", text: "Member " + (index + 1) }),
          el("span", { class: "mono", text: member.id }),
          el("span", { class: "sub", text: member.location || "location unknown" }),
          el("span", { class: "badge", text: dispositionLabel(member) })
        ]));
      });
      var rows = [
        ["Hard protection", function (member) {
          return member.protectionLevel
            ? member.protectionLevel + (member.protectionReason ? " — " + member.protectionReason : "")
            : "—";
        }],
        ["In loadout", function (member) { return member.inLoadout ? "Yes" : "No"; }],
        ["Locked", function (member) { return member.locked ? "Yes" : "No"; }],
        ["Masterwork Tier", function (member) {
          return member.masterworkTier === null || member.masterworkTier === undefined
            ? "unknown" : str(member.masterworkTier);
        }],
        ["Power", function (member) {
          return member.power === null || member.power === undefined ? "unknown" : str(member.power);
        }]
      ].map(function (row) {
        return el("tr", null, [el("th", { scope: "row", text: row[0] })].concat(
          group.members.map(function (member) {
            return el("td", { text: row[1](member) });
          })
        ));
      });
      rows.push(el("tr", { class: "armor-verdict-row" }, [
        el("th", { scope: "row", text: "Verdict" })
      ].concat(group.members.map(armorMemberCell))));
      return el("div", { class: "scroller armor-matrix" }, [
        el("table", { class: "armor-group-table" }, [
          el("thead", null, [el("tr", null, headerCells)]),
          el("tbody", null, rows)
        ])
      ]);
    }

    function armorGroup(group) {
      return el("article", {
        class: "armor-group", "data-group-id": group.groupId
      }, [armorGroupHeader(group), armorGroupTable(group)]);
    }

    function armorGroups(groups) {
      return (groups || []).map(armorGroup);
    }

    function paintArmorMember(id) {
      var row = state.duplicateRows[id];
      if (!row) return false;
      var current = verdictOf(state.verdicts, id);
      if (row.approve) {
        row.approve.setAttribute("aria-pressed", current === "approved" ? "true" : "false");
        row.veto.setAttribute("aria-pressed", current === "vetoed" ? "true" : "false");
        row.clear.setAttribute("aria-pressed", current === "" ? "true" : "false");
        row.approve.disabled = verdictDisabled();
        row.veto.disabled = verdictDisabled();
        row.clear.disabled = verdictDisabled();
      }
      if (row.presentation) row.presentation.textContent =
        isProposalMember(row.member) ? verdictText(row.member, current) :
          "Read-only · " + dispositionLabel(row.member);
      return true;
    }

    return {
      el: el, clear: clear, byId: byId, headerRow: headerRow, definition: definition,
      armorDetail: armorDetail, detailRow: detailRow, itemRows: itemRows, table: table,
      tile: tile, select: select, addSelect: addSelect, optionsFor: optionsFor,
      paintRow: paintRow, paintArmorMember: paintArmorMember,
      armorGroup: armorGroup, armorGroups: armorGroups, armorGroupHeader: armorGroupHeader,
      armorGroupTable: armorGroupTable, setVerdictControlsDisabled: setVerdictControlsDisabled
    };
  }

  return {
    COLUMNS: [["name", "Name"], ["id", "Instance id"], ["kind", "Kind"],
      ["classFacet", "Class"], ["location", "Location"],
      ["action", "Action"], ["reason", "Reason"],
      ["tuningModSlot", "Tuning Mod Slot"]],
    actionCounts: actionCounts, compareIds: compareIds, compareText: compareText,
    countBy: countBy, filterItems: filterItems, groupItems: groupItems, groupLabel: groupLabel,
    isObject: isObject, itemsFromSnapshot: itemsFromSnapshot, keptItems: keptItems,
    matchesProtection: matchesProtection, matchesText: matchesText, requireIdString: requireIdString,
    reviewCounts: reviewCounts, sortItems: sortItems, str: str, verdictOf: verdictOf,
    emptyMap: emptyMap, createView: createView,
    exactDuplicateGroupsFromSnapshot: exactDuplicateGroupsFromSnapshot,
    matchesArmorGroup: matchesArmorGroup, filterArmorGroups: filterArmorGroups,
    countArmorGroups: countArmorGroups, armorStatDisplay: armorStatDisplay,
    normalizeCategoricalValue: normalizeCategoricalValue
  };
});
