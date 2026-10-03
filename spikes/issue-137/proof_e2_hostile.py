"""E2: every untrusted string stays inert; ids and hashes stay opaque strings.

A real envelope (``armor_close.csv`` through the real upload route) has every
free-text string, every stat name, every id and every hash replaced with a
hostile value.  The fragment route renders that envelope and the browser
installs it with the spike's mechanism.  Fields that select a code path
(``kind``, ``group_kind``, ``disposition``, ``action``, ``proposal_action``,
``state``, ``status``) are not free text; the proof shows separately that a
hostile value in one of them is refused.

A control run then renders the same context with escaping switched off, to
show the detectors fire and what the insertion step and the CSP still stop.

    .venv/bin/python spikes/issue-137/proof_e2_hostile.py
"""

from __future__ import annotations

import copy
import json
from typing import Any

from context import ContextError, build_context
from harness import (
    authenticated_context,
    chromium,
    csp_events,
    finish,
    live_spike,
    main_guard,
    project,
    upload,
    walk,
    watch,
)
from jinja2 import Environment
from render_env import (
    SPIKE_TEMPLATES,
    TEMPLATE_NAMES,
    AllowListLoader,
    directory_source,
)

ID_KEYS = frozenset({"id", "group_id", "preferred_survivor_id", "selected_partner_id", "kept_id"})
ID_LIST_KEYS = frozenset({"cited_ids", "retained_verdict_ids", "discarded_verdict_ids"})
HASH_KEYS = frozenset({"hash"})
CODE_PATH_KEYS = frozenset(
    {"kind", "group_kind", "disposition", "action", "proposal_action", "state", "status"}
)
SPECIAL_IDS = ("18446744073709551615", "007", "9\"<'> x")
SPECIAL_HASHES = ("4294967295", "\"><img src=x onerror=alert(3)>")
PAYLOAD = (
    "<img src=x onerror=alert(1)><b>bold</b></td></table></article>"
    "<script>alert(2)</script>\"'&amp;&lt; {{7*7}} {% raw %} "
)
LONG_TAIL = "W" * 300


def hostile_text(path: str) -> str:
    return f"[{path}]{PAYLOAD}{LONG_TAIL}"


class Overlay:
    """Deterministically replace every string in an envelope."""

    def __init__(self, envelope: dict[str, Any]) -> None:
        self.ids: dict[str, str] = {}
        self.hashes: dict[str, str] = {}
        self.texts: dict[str, str] = {}
        # Ids and hashes are assigned from the groups, in list order, so the
        # server-side overlay and the proof's own overlay agree whatever order
        # a dict happens to iterate in.
        for original in self._controllable_first(envelope):
            self._id(original)
        for section in envelope["snapshot"]["sections"]:
            armor = section.get("armor") or {}
            for key in ("exact_duplicate_groups", "same_stat_groups"):
                for group in armor.get(key, []):
                    self._hash(group["hash"])

    @staticmethod
    def _controllable_first(envelope: dict[str, Any]) -> list[str]:
        """Give the three special ids to members that have verdict controls."""
        ordered: list[str] = []
        for section in envelope["snapshot"]["sections"]:
            proposals = {decision["id"] for decision in section["decisions"]}
            armor = section.get("armor") or {}
            controllable: list[str] = []
            read_only: list[str] = []
            for group in armor.get("exact_duplicate_groups", []):
                for member in group["members"]:
                    (controllable if member["proposal_action"] else read_only).append(member["id"])
            for group in armor.get("same_stat_groups", []):
                for member in group["members"]:
                    (controllable if member["id"] in proposals else read_only).append(member["id"])
            ordered += controllable + read_only
        return ordered

    def _id(self, original: str) -> str:
        if original not in self.ids:
            index = len(self.ids)
            self.ids[original] = (
                SPECIAL_IDS[index] if index < len(SPECIAL_IDS) else f"{original}\"<'> {index}"
            )
        return self.ids[original]

    def _hash(self, original: str) -> str:
        if original not in self.hashes:
            index = len(self.hashes)
            self.hashes[original] = (
                SPECIAL_HASHES[index] if index < len(SPECIAL_HASHES) else f"{original}<b>{index}</b>"
            )
        return self.hashes[original]

    def apply(self, value: Any, path: str = "", key: str = "") -> Any:
        if isinstance(value, dict):
            result = {}
            for name, child in sorted(value.items()):
                # Stat names are strings too: they are printed as labels.
                new_name = hostile_text(f"{path}.{name}#key") if key == "stats" else name
                if key == "stats":
                    self.texts[f"{path}.{name}#key"] = new_name
                result[new_name] = self.apply(child, f"{path}.{name}", name)
            return result
        if isinstance(value, list):
            return [
                self.apply(child, f"{path}[{index}]", key) for index, child in enumerate(value)
            ]
        if not isinstance(value, str):
            return value
        if key in ID_KEYS or key in ID_LIST_KEYS:
            return self._id(value)
        if key in HASH_KEYS:
            return self._hash(value)
        if key in CODE_PATH_KEYS:
            return value
        self.texts[path] = hostile_text(path)
        return self.texts[path]


def enrich(envelope: dict[str, Any]) -> dict[str, Any]:
    """Fill the optional fields ``armor_close.csv`` leaves empty.

    The fixture has no protected member, no Spirit perks and no read-only
    member with a later proposal, so those strings would never be printed.
    This gives each one a value for the overlay to replace.
    """
    enriched = copy.deepcopy(envelope)
    section = enriched["snapshot"]["sections"][0]
    group = section["armor"]["exact_duplicate_groups"][0]
    group["spirit_signature"] = ["Spirit perk one", "Spirit perk two"]
    group["seasonal_mod"] = "A seasonal mod"
    group["holofoil"] = "true"
    survivor, proposed = group["members"][0], group["members"][1]
    survivor["protection_level"] = "soft"
    survivor["protection_reason"] = "locked"
    later = copy.deepcopy(
        next(d for d in section["decisions"] if d["id"] == proposed["id"])
    )
    later.update({"id": survivor["id"], "action": "review", "reason": "a later proposal"})
    section["decisions"].append(later)
    return enriched


def overlay(envelope: dict[str, Any]) -> tuple[dict[str, Any], Overlay]:
    enriched = enrich(envelope)
    worker = Overlay(enriched)
    hostile = worker.apply(enriched)
    # Give the same-stat members one shared Tuning Mod Slot, so their
    # (different) Tuning Stat values become an informative row and are printed.
    for section in hostile["snapshot"]["sections"]:
        for group in (section.get("armor") or {}).get("same_stat_groups", []):
            for member in group["members"]:
                member["tuning_mod_slot"] = group["members"][0]["tuning_mod_slot"]
    return hostile, worker


def transform(envelope: dict[str, Any]) -> dict[str, Any]:
    return overlay(envelope)[0] if envelope.get("snapshot") else envelope


def field_of(path: str) -> str:
    """The field a replaced string belongs to, without list positions."""
    name = path.rsplit(".", 1)[-1].split("[")[0]
    return "stats (stat name)" if name.endswith("#key") else name


def strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for child in value.values() for text in strings(child)]
    if isinstance(value, list | tuple):
        return [text for child in value for text in strings(child)]
    return []


CORPUS_JS = """
root => {
  var parts = [];
  var walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
  for (var node = walker.currentNode; node; node = walker.nextNode()) {
    if (node.nodeType === 3) parts.push(node.data);
    else Array.prototype.forEach.call(node.attributes, function (a) { parts.push(a.value); });
  }
  return parts;
}
"""
COUNTS_JS = """
root => ({
  script: root.querySelectorAll("script").length,
  img: root.querySelectorAll("img").length,
  b: root.querySelectorAll("b").length,
  documentScripts: document.querySelectorAll("script").length,
  documentImages: document.querySelectorAll("img").length
})
"""
IDS_JS = """
root => ({
  memberIds: Array.prototype.map.call(
    root.querySelectorAll("[data-member-id]"), n => n.getAttribute("data-member-id")),
  verdictIds: Array.prototype.map.call(
    root.querySelectorAll("[data-vc-verdict-id]"), n => n.getAttribute("data-vc-verdict-id")),
  printedIds: Array.prototype.map.call(
    root.querySelectorAll(".armor-member-heading > .mono"), n => n.textContent),
  groupIds: Array.prototype.map.call(
    root.querySelectorAll("[data-group-id]"), n => n.getAttribute("data-group-id")),
  hashes: Array.prototype.map.call(
    root.querySelectorAll(".armor-group-meta .mono"), n => n.textContent)
})
"""


def serve_envelope(page: Any, envelope: dict[str, Any]) -> None:
    """Hand both pages the same hostile envelope the fragment was rendered from."""
    body = json.dumps(envelope, sort_keys=True)
    page.route(
        "**/api/report",
        lambda route: route.fulfill(status=200, content_type="application/json", body=body),
    )


def main() -> int:
    failures: list[str] = []
    with live_spike(transform_envelope=transform) as live, chromium() as browser:
        context = authenticated_context(browser, live)
        seen = watch(context)
        real = upload(context, live, "armor_close.csv")
        for key in ("retained_verdict_ids", "discarded_verdict_ids"):
            real.pop(key)
        hostile, worker = overlay(real)
        page_context = build_context(hostile)
        rendered_strings = strings(page_context)
        groups = [group for section in page_context["sections"] for group in section["groups"]]

        print("-- overlay --")
        print(f"free-text and stat-name strings replaced: {len(worker.texts)}")
        print(f"ids replaced: {len(worker.ids)}; hashes replaced: {len(worker.hashes)}")
        print(f"special ids in use: {[worker.ids[key] for key in list(worker.ids)[:3]]}")
        print(f"special hashes in use: {list(worker.hashes.values())[:2]}")
        used = {
            path: text
            for path, text in worker.texts.items()
            if any(text in candidate for candidate in rendered_strings)
        }
        printed_fields = {field_of(path) for path in used}
        other_fields = sorted({field_of(path) for path in worker.texts} - printed_fields)
        print(f"replaced strings the slice prints: {len(used)}")
        print(f"fields the slice prints: {sorted(printed_fields)}")
        print(f"fields replaced but never printed by this slice: {other_fields}")

        print("-- spike page: Jinja fragment installed with DOMParser + importNode --")
        spike_context = authenticated_page(context, live, hostile)
        page = spike_context
        counts = page.locator("#vc-duplicate-list").evaluate(COUNTS_JS)
        print(f"elements created from hostile text inside the list: script={counts['script']} "
              f"img={counts['img']} b={counts['b']}")
        print(f"script elements in the document: {counts['documentScripts']} (the page's own)")
        if counts["script"] or counts["img"] or counts["b"] or counts["documentScripts"] != 1:
            failures.append("hostile text created an element")
        corpus = page.locator("body").evaluate(CORPUS_JS)
        missing = [
            path for path, text in used.items()
            if not any(text in candidate for candidate in corpus)
        ]
        print(f"replaced strings found verbatim in the DOM: {len(used) - len(missing)} of {len(used)}")
        if missing:
            failures.append(f"strings did not round-trip: {missing[:3]}")
        print(f"literal '{{{{7*7}}}}' present, never evaluated: "
              f"{any('{{7*7}}' in candidate for candidate in corpus)}")

        ids = page.locator("#vc-duplicate-list").evaluate(IDS_JS)
        expected_members = [
            member["dom_id"] for group in groups for _ in range(2) for member in group["members"]
        ]
        expected_printed = [
            member["id"] for group in groups for _ in range(2) for member in group["members"]
        ]
        expected_groups = [group["dom_id"] for group in groups]
        expected_hashes = [group["hash_text"] for group in groups]
        checks = {
            "data-member-id values": ids["memberIds"] == expected_members,
            "printed member ids": ids["printedIds"] == expected_printed,
            "data-group-id values": ids["groupIds"] == expected_groups,
            "printed hashes": ids["hashes"] == expected_hashes,
            "data-vc-verdict-id values are envelope ids": set(ids["verdictIds"])
            <= set(worker.ids.values()),
        }
        for label, passed in checks.items():
            print(f"{label} byte-identical to the envelope: {passed}")
            if not passed:
                failures.append(f"{label} changed")
        print(f"distinct member ids in the DOM: {sorted(set(ids['printedIds']))}")

        print("-- verdict request for each special id (intercepted, never sent) --")
        captured: list[str] = []

        def capture(route: Any) -> None:
            captured.append(route.request.post_data)
            route.fulfill(
                status=400,
                content_type="application/json",
                body=json.dumps({"error": {"code": "bad_request", "message": "intercepted"}}),
            )

        page.route("**/api/verdicts", capture)
        for special in SPECIAL_IDS:
            before = len(captured)
            buttons = page.locator(
                "table.armor-matrix-columns td[data-vc-verdict-id] button.approve"
            )
            # Find the button by comparing the attribute as a string, so the
            # hostile id never has to be escaped into a selector.
            index = buttons.evaluate_all(
                "(nodes, id) => nodes.findIndex("
                "b => b.closest('[data-vc-verdict-id]').getAttribute('data-vc-verdict-id') === id)",
                special,
            )
            if index < 0:
                failures.append(f"id {special!r} has no verdict control")
                continue
            buttons.nth(index).click()
            page.wait_for_function(
                "() => document.getElementById('vc-status').textContent === 'intercepted'"
            )
            page.evaluate("() => { document.getElementById('vc-status').textContent = ''; }")
            body = json.loads(captured[before])
            sent = body["decisions"][0]["id"]
            raw_quoted = json.dumps(special) in captured[before]
            print(f"id {special!r}: sent as {type(sent).__name__}, equal={sent == special}, "
                  f"quoted in the request body={raw_quoted}")
            if sent != special or not isinstance(sent, str) or not raw_quoted:
                failures.append(f"id {special!r} changed on the way to the request")

        print("-- parity with production's createElement/textContent DOM --")
        production = open_production_page(context, live, hostile)
        equal = json.dumps(strip(project(production)), sort_keys=True) == json.dumps(
            strip(project(page)), sort_keys=True
        )
        print(f"hostile envelope: Jinja projection equals production projection: {equal}")
        if not equal:
            failures.append("hostile projections differ")

        violations = csp_events(page) + csp_events(production)
        print(f"dialogs: {seen['dialogs']}")
        print(f"CSP violation events: {violations}; CSP console messages: {seen['csp_console']}")
        if seen["dialogs"] or violations or seen["csp_console"]:
            failures.append("a dialog or CSP violation occurred")
        production.close()
        page.close()

        print("-- code-path fields refuse hostile values --")
        for key in ("group_kind", "disposition"):
            broken = copy.deepcopy(real)
            group = broken["snapshot"]["sections"][0]["armor"]["exact_duplicate_groups"][0]
            target = group if key == "group_kind" else group["members"][0]
            target[key] = PAYLOAD
            try:
                build_context(broken)
                outcome = "rendered"
                failures.append(f"a hostile {key} was rendered")
            except ContextError as error:
                outcome = f"ContextError: {str(error).split(' has ')[-1].split(' must ')[-1]}"
            print(f"hostile {key}: {outcome}")
        numeric = copy.deepcopy(real)
        numeric["snapshot"]["sections"][0]["armor"]["exact_duplicate_groups"][0]["members"][0][
            "id"
        ] = 6031
        try:
            build_context(numeric)
            failures.append("a numeric id was rendered")
            print("numeric member id: rendered")
        except ContextError as error:
            print(f"numeric member id: ContextError: {error}")

        print("-- control: the same context with escaping switched off --")
        unescaped = Environment(
            loader=AllowListLoader(TEMPLATE_NAMES, directory_source(SPIKE_TEMPLATES)),
            autoescape=False,
        ).get_template("armor_duplicates.html").render(**page_context)
        control = context.new_page()
        serve_envelope(control, hostile)
        control.route(
            "**/spike/fragments/armor-duplicates",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html; charset=utf-8",
                headers={
                    "Vault-Cleaner-Report-Revision": str(hostile["report_revision"]),
                    "Vault-Cleaner-Verdict-Revision": str(hostile["verdict_revision"]),
                },
                body=unescaped,
            ),
        )
        control.goto(f"{live.origin}/spike/", wait_until="domcontentloaded")
        control.wait_for_function(
            "() => /Connected|failed/.test(document.getElementById('vc-status').textContent)"
        )
        control.wait_for_timeout(500)
        control_counts = control.locator("#vc-duplicate-list").evaluate(COUNTS_JS)
        control_events = sorted(set(csp_events(control)))
        print(f"control elements inside the list: script>0={control_counts['script'] > 0} "
              f"img>0={control_counts['img'] > 0} b>0={control_counts['b'] > 0}")
        print(f"control dialogs: {seen['dialogs']}")
        print(f"control CSP violation directives: {control_events}")
        if not (control_counts["img"] and control_counts["b"]):
            failures.append("the control did not trip the element detector")
        if seen["dialogs"]:
            failures.append("the control ran script")
        control.close()
        context.close()
    return finish(failures)


def strip(tree: dict) -> dict:
    for node in walk(tree):
        attributes = node.get("attributes")
        if attributes is None:
            continue
        if attributes.get("class") == "":
            del attributes["class"]
        for name in [name for name in attributes if name.startswith("data-vc-")]:
            del attributes[name]
    return tree


def authenticated_page(context: Any, live: Any, envelope: dict[str, Any]) -> Any:
    page = context.new_page()
    serve_envelope(page, envelope)
    page.goto(f"{live.origin}/spike/", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => /Connected|failed/.test(document.getElementById('vc-status').textContent)"
    )
    return page


def open_production_page(context: Any, live: Any, envelope: dict[str, Any]) -> Any:
    page = context.new_page()
    serve_envelope(page, envelope)
    page.goto(f"{live.origin}/", wait_until="domcontentloaded")
    page.wait_for_function(
        "() => /Connected/.test(document.getElementById('vc-status').textContent)"
    )
    page.locator("#vc-view-duplicates").click()
    return page


if __name__ == "__main__":
    main_guard(main)
