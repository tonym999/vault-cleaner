"""S2: hostile content and opaque ids (gate H2).

The real server will not hold an id such as ``9"<'> x``, so the proof
overlays hostile values on the envelope between the server and the page: it
intercepts ``GET /api/report`` in the browser, takes the server's real
answer, replaces **every string value** (and every stat name) with a hostile
one, and hands that to the page.  Structural values the page branches on
(``state``, ``kind``, ``group_kind``, ``status``, ``verdict`` and the
fingerprint it sends back) are kept.  ``disposition``, ``action`` and
``proposal_action`` are replaced in a first pass, where the page must then
show no verdict buttons, and kept in a second pass so a verdict can be
pressed.  Ids and hashes are replaced
consistently, so the same hostile id appears wherever the real one did.

It then checks that nothing ran or was injected, that the text shown is the
hostile text exactly, that ids are byte-identical in the DOM and in the
verdict request body, and that the page still does not scroll sideways.
``check_source.py`` is the source-rule half of this gate.

    .venv/bin/python spikes/issue-206/proof_s2_hostile.py
"""

from __future__ import annotations

import json
from typing import Any

from expected import compare, expected_groups
from harness import (
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    read_slice,
    upload,
)

MARKUP = "<img src=x onerror=alert(1)><script>alert(2)</script><i>&amp;\"'{@html x}${1+1}{{7*7}}"
LONG = "W" * 300
SPECIAL_IDS = ("18446744073709551615", "007", "9\"<'> x")
ID_KEYS = {"id", "group_id", "preferred_survivor_id", "selected_partner_id", "kept_id"}
KEEP = {"state", "kind", "group_kind", "status", "verdict", "fingerprint"}
# The three values that decide whether a member has verdict buttons.  The
# first pass replaces them too; the second keeps them so a verdict can be
# pressed on a member with a hostile id.
ELIGIBILITY = {"disposition", "action", "proposal_action"}


class Overlay:
    def __init__(self) -> None:
        self.ids: dict[str, str] = {}
        self.hashes: dict[str, str] = {}
        self.replaced = 0
        self.keep = set(KEEP)

    def _id(self, value: str) -> str:
        if value not in self.ids:
            index = len(self.ids)
            self.ids[value] = (
                SPECIAL_IDS[index] if index < len(SPECIAL_IDS)
                else f"{index}<b onclick=alert(3)>'\" id</b>"
            )
        return self.ids[value]

    def _hash(self, value: str) -> str:
        if value not in self.hashes:
            self.hashes[value] = f"00{len(self.hashes)}<script>alert(4)</script>"
        return self.hashes[value]

    def seed(self, envelope: dict) -> None:
        """Give the first group members the three ids the plan names."""
        for section in envelope["snapshot"]["sections"]:
            armor = section.get("armor", {})
            for key in ("exact_duplicate_groups", "same_stat_groups"):
                for group in armor.get(key, []):
                    for member in group["members"]:
                        self._id(member["id"])

    def apply(self, value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            if key == "stats":
                return {f"{name}<u>{MARKUP}": number for name, number in value.items()}
            return {name: self.apply(child, name) for name, child in value.items()}
        if isinstance(value, list):
            return [self.apply(child, key) for child in value]
        if not isinstance(value, str) or key in self.keep:
            return value
        self.replaced += 1
        if key in ID_KEYS or key in ("cited_ids",):
            return self._id(value)
        if key == "hash":
            return self._hash(value)
        return f"{key}:{MARKUP} {LONG}  two  spaces"


INJECTED_JS = """
() => ({
  elements: document.querySelectorAll("#app img, #app script, #app i, #app b, #app u").length,
  scripts: document.scripts.length,
  sideways: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  ids: Array.from(document.querySelectorAll("[data-member]")).map((row) => ({
    attribute: row.getAttribute("data-member"),
    text: row.querySelector("[data-field=id]").textContent,
  })),
  hashes: Array.from(document.querySelectorAll("article [data-field=hash] span")).map((n) => n.textContent.trim()),
  names: Array.from(document.querySelectorAll("article [data-field=name] span")).map((n) => n.textContent),
})
"""


def handlers(overlay: Overlay, seen: dict, hostile: dict):
    """The two interceptions: overlay the report, and acknowledge a verdict."""

    def on_report(route: Any) -> None:
        real = route.fetch()
        overlay.seed(real.json())
        hostile.clear()
        hostile.update(overlay.apply(real.json()))
        route.fulfill(response=real, body=json.dumps(hostile, ensure_ascii=False))

    def on_verdict(route: Any) -> None:
        raw = route.request.post_data
        seen["bodies"].append(raw)
        sent = json.loads(raw)
        answer = dict(hostile)
        answer["verdict_revision"] = hostile["verdict_revision"] + 1
        answer["verdicts"] = [dict(entry) for entry in sent["decisions"]]
        hostile.clear()
        hostile.update(answer)
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(answer, ensure_ascii=False))

    return on_report, on_verdict


def one_width(browser: Any, live: Any, width: int, state: Any, failures: list[str]) -> Any:
    """Run the whole check at one viewport width; returns the signed-in state."""
    overlay = Overlay()
    if state is None:
        context = authenticated_context(browser, live, width=width)
        upload(context, live, "armor_close.csv")
        state = context.storage_state()
    else:
        context = browser.new_context(viewport={"width": width, "height": 900}, storage_state=state)
    seen: dict[str, list] = {"dialogs": [], "console": [], "errors": [], "bodies": []}
    context.add_init_script(
        "window.__csp = []; document.addEventListener('securitypolicyviolation',"
        " (event) => window.__csp.push(event.effectiveDirective));"
    )
    page = context.new_page()
    page.on("dialog", lambda dialog: (seen["dialogs"].append(dialog.message), dialog.dismiss()))
    page.on("console", lambda m: seen["console"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda error: seen["errors"].append(str(error)))
    hostile: dict[str, Any] = {}

    on_report, on_verdict = handlers(overlay, seen, hostile)
    page.route("**/api/report", on_report)
    page.route("**/api/verdicts", on_verdict)
    page.goto(f"{live.origin}/spike/", wait_until="domcontentloaded")
    page.wait_for_selector("article[data-group]")

    print(f"-- {width}px: every string in the envelope replaced --")
    print(f"string values replaced: {overlay.replaced}; distinct ids: {len(overlay.ids)}; "
          f"distinct hashes: {len(overlay.hashes)}")
    problems = compare(read_slice(page), hostile)
    print(f"differences from the hostile envelope, value by value: {len(problems)}")
    failures.extend(problems[:5])

    found = page.evaluate(INJECTED_JS)
    member_ids = [m["id"] for g in expected_groups(hostile) for m in g["members"]]
    ids_exact = [entry["attribute"] for entry in found["ids"]] == member_ids and [
        entry["text"] for entry in found["ids"]
    ] == member_ids
    hashes = [g["facts"]["hash"][0] for g in expected_groups(hostile)]
    names = [g["name"][0] for g in expected_groups(hostile)]
    print(f"ids in the DOM (attribute and text, untrimmed) byte-identical: {ids_exact}: "
          f"{[entry['text'] for entry in found['ids']][:3]}")
    print(f"hashes in the DOM identical: {found['hashes'] == hashes}: {found['hashes']}")
    print(f"names shown as exact text, internal double spaces kept: {found['names'] == names}; "
          f"length {len(names[0])}")
    print(f"elements created from values (img, script, i, b, u): {found['elements']}; "
          f"script elements in the document: {found['scripts']} (the bundle)")
    print(f"page scrolls sideways with 300-character unbroken values: {found['sideways']}")
    if not ids_exact or found["hashes"] != hashes or found["names"] != names:
        failures.append("a value did not round-trip exactly")
    if found["elements"] or found["scripts"] != 1 or found["sideways"]:
        failures.append("a hostile value created an element or widened the page")

    controls = page.locator("[data-member] button").count()
    print(f"verdict buttons with every disposition and action hostile: {controls} "
          "(no member's disposition and action agree, so none is a proposal member)")
    if controls:
        failures.append("a member with a hostile disposition or action got verdict buttons")

    overlay.keep |= ELIGIBILITY
    overlay.replaced = 0
    with page.expect_response("**/api/report"):
        page.locator("button", has_text="Reload report").click()
    page.wait_for_selector("[data-member] button")
    again = compare(read_slice(page), hostile)
    print(f"second pass, disposition and action values kept: strings replaced {overlay.replaced}; "
          f"verdict buttons {page.locator('[data-member] button').count()}; "
          f"differences from the envelope {len(again)}")
    failures.extend(again[:5])

    target = member_ids[1] if width == 1440 else member_ids[2]
    row = page.locator("[data-member]").nth(member_ids.index(target))
    row.locator("button", has_text="Veto").click()
    page.wait_for_function(
        "(index) => document.querySelectorAll('[data-member]')[index]"
        ".querySelector('[data-field=verdict]').textContent === 'Vetoed'",
        arg=member_ids.index(target),
    )
    body = seen["bodies"][-1]
    sent = json.loads(body)["decisions"]
    print(f"verdict request body: {body}")
    print(f"id in the request equals the envelope's id: {sent == [{'id': target, 'verdict': 'vetoed'}]}; "
          f"is a JSON string: {isinstance(sent[0]['id'], str)}")
    status = page.locator("#vc-status").text_content().strip()
    print(f"status after the acknowledgement names the id as text: {target in status}")
    if sent != [{"id": target, "verdict": "vetoed"}] or target not in status:
        failures.append("the id changed on its way into the verdict request")
    after = compare(read_slice(page), hostile)
    if after:
        failures.extend(after[:3])

    print(f"dialogs: {seen['dialogs']}; CSP violations: {csp_events_or(page)}; "
          f"console errors: {seen['console']}; page errors: {seen['errors']}")
    if seen["dialogs"] or seen["console"] or seen["errors"] or csp_events_or(page):
        failures.append("a hostile value had an effect")
    context.close()
    return state


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        state = None
        for width in (1440, 390):
            state = one_width(browser, live, width, state, failures)
    return finish(failures)


def csp_events_or(page: Any) -> list[str]:
    return page.evaluate("() => window.__csp.slice()")


if __name__ == "__main__":
    main_guard(main)
