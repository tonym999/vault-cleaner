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

  /**
   * Project untrusted snapshot input into the Armor duplicates presentation.
   *
   * The authoritative group/member array order is copied verbatim. Opaque
   * identity strings, dispositions, uniqueness, and same-section/hash
   * proposal correlation are validated here before an adapter can adopt the
   * envelope. This function never reconstructs grouping, ranking, survivor,
   * or disposition truth in the browser.
   *
   * @param {Object|null|undefined} snapshot Untrusted report snapshot.
   * @returns {Array<Object>} Ordered presentation-only exact groups.
   * @throws {Error|TypeError} On an incompatible identity, disposition,
   *   proposal correlation, uniqueness, or snapshot contract.
   */
  function exactDuplicateGroupsFromSnapshot(snapshot) {
    var groups = [];
    var sections = (snapshot && snapshot.sections) || [];
    var seenGroups = emptyMap();
    var seenGroupMembers = emptyMap();
    var proposalDecisionsBySection = [];
    var proposalDecisionLocations = emptyMap();
    sections.forEach(function (section, sectionIndex) {
      var proposals = emptyMap();
      (section && Array.isArray(section.decisions) ? section.decisions : []).forEach(
        function (decision, decisionIndex) {
          if (!isObject(decision) || (decision.action !== "junk" &&
              decision.action !== "review")) return;
          var decisionWhere = "sections[" + sectionIndex + "].decisions[" +
            decisionIndex + "]";
          var decisionId = requireIdString(decision.id, decisionWhere + ".id");
          if (Object.prototype.hasOwnProperty.call(proposals, decisionId)) {
            throw new Error("duplicate proposal decision for id " + decisionId +
              " at " + decisionWhere);
          }
          proposals[decisionId] = decision;
          if (!proposalDecisionLocations[decisionId]) {
            proposalDecisionLocations[decisionId] = [];
          }
          proposalDecisionLocations[decisionId].push({
            sectionIndex: sectionIndex, decision: decision
          });
        }
      );
      proposalDecisionsBySection[sectionIndex] = proposals;
    });
    for (var s = 0; s < sections.length; s++) {
      var section = sections[s] || {};
      var armor = section.armor;
      if (section.kind !== "armor" || !armor ||
          !Array.isArray(armor.exact_duplicate_groups)) continue;
      var proposalDecisions = proposalDecisionsBySection[s] || emptyMap();
      armor.exact_duplicate_groups.forEach(function (source, index) {
        var where = "sections[" + s + "].armor.exact_duplicate_groups[" + index + "]";
        if (!isObject(source)) throw new Error(where + " must be an object");
        if (source.group_kind !== "exact_duplicate") {
          throw new Error(where + ".group_kind must be exact_duplicate");
        }
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
          if (Object.prototype.hasOwnProperty.call(seenMembers, id)) {
            throw new Error("duplicate member id " + id + " at " + memberWhere);
          }
          if (Object.prototype.hasOwnProperty.call(seenGroupMembers, id)) {
            throw new Error("duplicate member id " + id + " across exact duplicate groups at " + memberWhere);
          }
          seenMembers[id] = true;
          seenGroupMembers[id] = true;
          var disposition = str(member.disposition);
          var proposalAction = member.proposal_action === null ||
            member.proposal_action === undefined ? "" : str(member.proposal_action);
          if (["preferred_survivor", "retained_protected", "proposed_junk",
            "proposed_review"].indexOf(disposition) === -1) {
            throw new Error(memberWhere + " has an unsupported disposition");
          }
          var expectedAction = disposition === "proposed_junk" ? "junk" :
            disposition === "proposed_review" ? "review" : "";
          var proposalDecision = Object.prototype.hasOwnProperty.call(proposalDecisions, id)
            ? proposalDecisions[id] : null;
          var proposalLocations = proposalDecisionLocations[id] || [];
          if (proposalLocations.some(function (location) {
            return location.sectionIndex !== s;
          })) {
            throw new Error(memberWhere + " has a proposal decision in another section");
          }
          var currentProposalAction = "";
          var currentProposalReason = "";
          if (proposalDecision) {
            var proposalHash = requireIdString(proposalDecision.hash,
              memberWhere + ".proposal_hash");
            if (proposalHash !== hash) {
              throw new Error(memberWhere + " has a proposal decision for another hash");
            }
            currentProposalAction = str(proposalDecision.action);
            currentProposalReason = str(proposalDecision.reason);
          }
          if (proposalAction !== expectedAction || (proposalAction &&
              (!proposalDecision || proposalDecision.action !== proposalAction ||
               currentProposalAction !== proposalAction))) {
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
            // ``proposalAction`` is the exact-group disposition contract;
            // ``currentProposalAction`` is a separately correlated later-pass
            // proposal for a read-only member, when one exists.
            currentProposalAction: currentProposalAction,
            currentProposalReason: currentProposalReason,
            proposalReason: member.proposal_reason === null ||
              member.proposal_reason === undefined ? "" : str(member.proposal_reason)
          };
        });
        groups.push({
          groupKind: "exact_duplicate",
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

  // Project the close-pass same-stat comparison groups without deriving any
  // grouping or decision truth in the browser.  Exact and same-stat groups
  // deliberately use separate uniqueness maps: one item may occur in both
  // authoritative categories, while duplicate identities within a category
  // remain incompatible input.
  function sameStatGroupsFromSnapshot(snapshot) {
    var groups = [];
    var sections = (snapshot && snapshot.sections) || [];
    var seenGroups = emptyMap();
    var seenGroupMembers = emptyMap();
    var proposalDecisionsBySection = [];
    var proposalDecisionLocations = emptyMap();
    sections.forEach(function (section, sectionIndex) {
      var proposals = emptyMap();
      (section && Array.isArray(section.decisions) ? section.decisions : []).forEach(
        function (decision, decisionIndex) {
          if (!isObject(decision) || (decision.action !== "junk" &&
              decision.action !== "review")) return;
          var decisionWhere = "sections[" + sectionIndex + "].decisions[" +
            decisionIndex + "]";
          var decisionId = requireIdString(decision.id, decisionWhere + ".id");
          if (Object.prototype.hasOwnProperty.call(proposals, decisionId)) {
            throw new Error("duplicate proposal decision for id " + decisionId +
              " at " + decisionWhere);
          }
          proposals[decisionId] = decision;
          if (!proposalDecisionLocations[decisionId]) {
            proposalDecisionLocations[decisionId] = [];
          }
          proposalDecisionLocations[decisionId].push({
            sectionIndex: sectionIndex, decision: decision
          });
        }
      );
      proposalDecisionsBySection[sectionIndex] = proposals;
    });
    for (var s = 0; s < sections.length; s++) {
      var section = sections[s] || {};
      var armor = section.armor;
      if (section.kind !== "armor" || !armor ||
          !Array.isArray(armor.same_stat_groups)) continue;
      var proposalDecisions = proposalDecisionsBySection[s] || emptyMap();
      armor.same_stat_groups.forEach(function (source, index) {
        var where = "sections[" + s + "].armor.same_stat_groups[" + index + "]";
        if (!isObject(source)) throw new Error(where + " must be an object");
        if (source.group_kind !== "same_stat") {
          throw new Error(where + ".group_kind must be same_stat");
        }
        var groupId = requireIdString(source.group_id, where + ".group_id");
        var hash = requireIdString(source.hash, where + ".hash");
        if (Object.prototype.hasOwnProperty.call(seenGroups, groupId)) {
          throw new Error("duplicate same-stat group id " + groupId);
        }
        seenGroups[groupId] = true;
        if (!Array.isArray(source.members) || source.members.length < 2) {
          throw new Error(where + ".members must contain at least two members");
        }
        var seenMembers = emptyMap();
        var members = source.members.map(function (member, memberIndex) {
          var memberWhere = where + ".members[" + memberIndex + "]";
          if (!isObject(member)) throw new Error(memberWhere + " must be an object");
          var id = requireIdString(member.id, memberWhere + ".id");
          if (Object.prototype.hasOwnProperty.call(seenMembers, id)) {
            throw new Error("duplicate member id " + id + " at " + memberWhere);
          }
          if (Object.prototype.hasOwnProperty.call(seenGroupMembers, id)) {
            throw new Error("duplicate member id " + id +
              " across same-stat groups at " + memberWhere);
          }
          seenMembers[id] = true;
          seenGroupMembers[id] = true;
          var proposalAction = member.proposal_action === null ||
            member.proposal_action === undefined ? "" : str(member.proposal_action);
          if (proposalAction && ["junk", "review"].indexOf(proposalAction) === -1) {
            throw new Error(memberWhere + ".proposal_action is unsupported");
          }
          var proposalDecision = Object.prototype.hasOwnProperty.call(proposalDecisions, id)
            ? proposalDecisions[id] : null;
          var proposalLocations = proposalDecisionLocations[id] || [];
          if (proposalLocations.some(function (location) {
            return location.sectionIndex !== s;
          })) {
            throw new Error(memberWhere + " has a proposal decision in another section");
          }
          var currentProposalAction = "";
          var currentProposalReason = "";
          if (proposalDecision) {
            var proposalHash = requireIdString(proposalDecision.hash,
              memberWhere + ".proposal_hash");
            if (proposalHash !== hash) {
              throw new Error(memberWhere + " has a proposal decision for another hash");
            }
            // A same-section, same-hash decision is the authoritative
            // proposal seam. Close-pass member metadata may corroborate that
            // decision, but it cannot manufacture one when the decision is
            // absent.
            if (proposalAction && proposalDecision.action !== proposalAction) {
              throw new Error(memberWhere + " has inconsistent proposal action");
            }
            currentProposalAction = str(proposalDecision.action);
            currentProposalReason = str(proposalDecision.reason);
          }
          var selectedPartnerId = member.selected_partner_id === null ||
            member.selected_partner_id === undefined ? null :
            requireIdString(member.selected_partner_id, memberWhere + ".selected_partner_id");
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
            tuningStat: str(member.tuning_stat),
            tuningModSlot: normalizeCategoricalValue(member.tuning_mod_slot),
            seasonalMod: normalizeCategoricalValue(member.seasonal_mod),
            holofoil: normalizeCategoricalValue(member.holofoil),
            // The source action/reason are close-pass metadata.  A current
            // proposal is authoritative only when it is correlated above.
            proposalAction: proposalAction,
            proposalReason: member.proposal_reason === null ||
              member.proposal_reason === undefined ? "" : str(member.proposal_reason),
            selectedPartnerId: selectedPartnerId,
            currentProposalAction: currentProposalAction,
            currentProposalReason: currentProposalReason
          };
        });
        groups.push({
          groupKind: "same_stat",
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
          // Same-stat groups intentionally have no group-level tuning or
          // variation axes. Seasonal Mod and Holofoil are member-only fields
          // in the authoritative close-pass snapshot.
          tuningModSlot: "none/unknown",
          seasonalMod: "",
          holofoil: "",
          spiritSignature: Array.isArray(source.spirit_signature)
            ? source.spirit_signature.map(str) : [],
          preferredSurvivorId: null,
          members: members
        });
      });
    }
    return groups;
  }

  function armorGroupsFromSnapshot(snapshot) {
    return exactDuplicateGroupsFromSnapshot(snapshot).concat(
      sameStatGroupsFromSnapshot(snapshot)
    );
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
    if (q.tuningModSlot) {
      var requested = normalizeCategoricalValue(q.tuningModSlot);
      var isSameStat = group.groupKind === "same_stat";
      var tuningMatch = isSameStat
        ? (group.members || []).some(function (member) {
          return normalizeCategoricalValue(member.tuningModSlot) === requested;
        })
        : normalizeCategoricalValue(group.tuningModSlot) === requested;
      if (!tuningMatch) return false;
    }
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
      if (field === "tuningModSlot" && group.groupKind === "same_stat") {
        var values = emptyMap();
        (group.members || []).forEach(function (member) {
          values[normalizeCategoricalValue(member.tuningModSlot)] = true;
        });
        Object.keys(values).forEach(function (value) {
          counts[value] = (counts[value] || 0) + 1;
        });
        return;
      }
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
        (state.duplicateRows[id] || []).forEach(function (row) {
          [row.approve, row.veto, row.clear].forEach(function (control) {
            if (control) control.disabled = !!disabled;
          });
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

    function armorReadonlyText(member, verdict) {
      var text = "Read-only · " + dispositionLabel(member);
      if (member.currentProposalAction) {
        text += " · Also proposed " + member.currentProposalAction +
          " in Proposals · Current verdict: " + verdictText(member, verdict);
        if (member.currentProposalReason) text += " — " + member.currentProposalReason;
      }
      return text;
    }

    function armorMemberLabel(group, member) {
      if (group.groupKind === "same_stat") {
        return member.currentProposalAction
          ? "Existing Proposals action: " + member.currentProposalAction
          : "Read-only comparison";
      }
      return dispositionLabel(member);
    }

    function armorMemberCanVerdict(group, member) {
      if (group.groupKind === "same_stat") {
        return member.currentProposalAction === "junk" ||
          member.currentProposalAction === "review";
      }
      return isProposalMember(member);
    }

    function armorMemberDomIdentity(group, member) {
      return group.groupKind + ":" + member.id;
    }

    function armorMemberControlLabel(action, group, member) {
      var kind = group.groupKind === "same_stat" ? "same-stat" : "exact-duplicate";
      return action + " " + kind + " armor member id " + member.id;
    }

    function memberValues(group, field, normalize) {
      var values = emptyMap();
      (group.members || []).forEach(function (member) {
        var value = normalize ? normalize(member[field]) : str(member[field]);
        values[value] = true;
      });
      return Object.keys(values);
    }

    function armorGroupHeader(group) {
      var statDisplay = armorStatDisplay(group);
      var statNodes = statDisplay.rows.map(function (row) {
        return tile(row.role || "Base stat", str(row.name) + " " + str(row.value));
      });
      return el("header", { class: "armor-group-header" }, [
        el("h3", { text: group.name || "(unnamed armor)" }),
        el("p", { class: "sub", text: group.groupKind === "same_stat"
          ? "Same stats, different tuning · review-only"
          : "Exact duplicate group" }),
        el("div", { class: "armor-group-meta" }, [
          tile("Type / slot", group.type || "unknown"),
          tile("Guardian class", group.guardianClass || "class-neutral/unknown"),
          tile("Tier", group.tier === null || group.tier === undefined ? "unknown" : group.tier),
          tile("Hash", group.hash),
          tile("Archetype", group.itemArchetype || "none/unknown"),
          group.groupKind === "same_stat" ? null : tile("Tuning Mod Slot", group.tuningModSlot)
        ]),
        el("div", { class: "armor-stat-summary", "aria-label": "Base stat summary" }, statNodes),
        statDisplay.zeroSummary ? el("p", { class: "hint", text: statDisplay.zeroSummary }) : null,
        group.spiritSignature.length ? tile("Spirit signature", group.spiritSignature.join(" · ")) : null,
        group.seasonalMod ? tile("Seasonal Mod", group.seasonalMod) : null,
        group.holofoil && group.holofoil.toLowerCase() !== "false"
          ? tile("Holofoil", group.holofoil) : null
      ]);
    }

    function armorMemberCell(member, group) {
      var proposal = armorMemberCanVerdict(group, member);
      var verdict = verdictOf(state.verdicts, member.id);
      var approve = null, veto = null, clearButton = null, presentation = null;
      if (proposal && !readOnly) {
        approve = el("button", {
          type: "button", class: "approve", text: "Approve",
          "aria-pressed": verdict === "approved" ? "true" : "false",
          "aria-label": armorMemberControlLabel("approve", group, member),
          disabled: verdictDisabled(),
          on: { click: function () { toggleVerdict(member.id, "approved"); } }
        });
        veto = el("button", {
          type: "button", class: "veto", text: "Veto",
          "aria-pressed": verdict === "vetoed" ? "true" : "false",
          "aria-label": armorMemberControlLabel("veto", group, member),
          disabled: verdictDisabled(),
          on: { click: function () { toggleVerdict(member.id, "vetoed"); } }
        });
        clearButton = el("button", {
          type: "button", class: "clear-verdict", text: "Unset",
          "aria-pressed": verdict === "" ? "true" : "false",
          "aria-label": armorMemberControlLabel("unset verdict for", group, member),
          disabled: verdictDisabled(),
          on: { click: function () { clearVerdict(member.id); } }
        });
        presentation = el("span", {
          class: "verdict-presentation", text: verdictText(member, verdict)
        });
      } else {
        var readonlyText = proposal
          ? verdictText(member, verdict)
          : group.groupKind === "same_stat"
            ? "Read-only comparison · Current verdict: " + verdictText(member, verdict)
            : armorReadonlyText(member, verdict);
        presentation = el("span", { class: "hint", text: readonlyText });
      }
      var controls = proposal && !readOnly
        ? el("div", { class: "row-actions" }, [approve, veto, clearButton, presentation])
        : presentation;
      var cell = el("td", {
        class: "armor-member-cell", "data-member-id": armorMemberDomIdentity(group, member)
      }, [controls]);
      var handle = {
        cell: cell, approve: approve, veto: veto, clear: clearButton,
        presentation: presentation, member: member, group: group
      };
      var occurrences = state.duplicateRows[member.id];
      if (!occurrences) {
        occurrences = [];
        state.duplicateRows[member.id] = occurrences;
      }
      occurrences.push(handle);
      return cell;
    }

    function armorGroupTable(group) {
      var headerCells = [el("th", { scope: "col", text: "Comparison" })];
      group.members.forEach(function (member, index) {
        headerCells.push(el("th", { scope: "col", class: "armor-member-heading" }, [
          el("span", { class: "armor-member-number", text: "Member " + (index + 1) }),
          el("span", { class: "mono", text: member.id }),
          el("span", { class: "sub", text: member.location || "location unknown" }),
          el("span", { class: "badge", text: armorMemberLabel(group, member) })
        ]));
      });
      var rows = [];
      if (group.groupKind === "same_stat") {
        rows.push(["Tuning Mod Slot", function (member) {
          return normalizeCategoricalValue(member.tuningModSlot);
        }]);
        var seasonalValues = memberValues(group, "seasonalMod", normalizeCategoricalValue);
        if (seasonalValues.length > 1) {
          rows.push(["Seasonal Mod", function (member) {
            return normalizeCategoricalValue(member.seasonalMod);
          }]);
        }
        var holofoilValues = memberValues(group, "holofoil", normalizeCategoricalValue);
        if (holofoilValues.length > 1) {
          rows.push(["Holofoil", function (member) {
            return normalizeCategoricalValue(member.holofoil);
          }]);
        }
        var rawTuningValues = memberValues(group, "tuningStat");
        var tuningSlots = memberValues(group, "tuningModSlot", normalizeCategoricalValue);
        if (rawTuningValues.length > tuningSlots.length) {
          rows.push(["Tuning Stat", function (member) {
            return member.tuningStat || "none/unknown";
          }]);
        }
      }
      rows = rows.concat([
        ["Protection", function (member) {
          return member.protectionLevel
            ? member.protectionLevel + (member.protectionReason ? " — " + member.protectionReason : "")
            : "—";
        }],
        ["In loadout", function (member) { return member.inLoadout ? "Yes" : "No"; }],
        ["Equipped", function (member) { return member.equipped ? "Yes" : "No"; }],
        ["Locked", function (member) { return member.locked ? "Yes" : "No"; }],
        ["Masterwork Tier", function (member) {
          return member.masterworkTier === null || member.masterworkTier === undefined
            ? "unknown" : str(member.masterworkTier);
        }],
        ["Power", function (member) {
          return member.power === null || member.power === undefined ? "unknown" : str(member.power);
        }]
      ]).map(function (row) {
        return el("tr", null, [el("th", { scope: "row", text: row[0] })].concat(
          group.members.map(function (member) {
            return el("td", { text: row[1](member) });
          })
        ));
      });
      rows.push(el("tr", { class: "armor-verdict-row" }, [
        el("th", { scope: "row", text: "Verdict" })
      ].concat(group.members.map(function (member) {
        return armorMemberCell(member, group);
      }))));
      return el("div", { class: "scroller armor-matrix" }, [
        el("table", { class: "armor-group-table" }, [
          el("thead", null, [el("tr", null, headerCells)]),
          el("tbody", null, rows)
        ])
      ]);
    }

    function armorGroup(group) {
      return el("article", {
        class: "armor-group", "data-group-id": group.groupKind + ":" + group.groupId,
        "data-group-kind": group.groupKind
      }, [armorGroupHeader(group), armorGroupTable(group)]);
    }

    function armorGroups(groups) {
      return (groups || []).map(armorGroup);
    }

    function paintArmorMember(id) {
      var rows = state.duplicateRows[id];
      if (!rows || !rows.length) return false;
      var current = verdictOf(state.verdicts, id);
      rows.forEach(function (row) {
        if (row.approve) {
          row.approve.setAttribute("aria-pressed", current === "approved" ? "true" : "false");
          row.veto.setAttribute("aria-pressed", current === "vetoed" ? "true" : "false");
          row.clear.setAttribute("aria-pressed", current === "" ? "true" : "false");
          row.approve.disabled = verdictDisabled();
          row.veto.disabled = verdictDisabled();
          row.clear.disabled = verdictDisabled();
        }
        if (row.presentation) row.presentation.textContent = armorMemberCanVerdict(row.group, row.member)
          ? verdictText(row.member, current) : row.group.groupKind === "same_stat"
            ? "Read-only comparison · Current verdict: " + verdictText(row.member, current)
            : armorReadonlyText(row.member, current);
      });
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
    sameStatGroupsFromSnapshot: sameStatGroupsFromSnapshot,
    armorGroupsFromSnapshot: armorGroupsFromSnapshot,
    matchesArmorGroup: matchesArmorGroup, filterArmorGroups: filterArmorGroups,
    countArmorGroups: countArmorGroups, armorStatDisplay: armorStatDisplay,
    normalizeCategoricalValue: normalizeCategoricalValue
  };
});
