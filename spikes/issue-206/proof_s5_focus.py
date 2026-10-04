"""S5: focus and live regions (gate H4, contract section 7).

Node identity is measured by tagging DOM nodes before an action and looking
for the tag afterwards: a rebuilt node would not carry it.  Writes to the
three live regions are counted with a ``MutationObserver``.

Focus policy on a report change, stated and then measured:

* groups and members are keyed by id, so a control whose member is still in
  the new report is the same node and keeps focus;
* if the focused control's member is gone, focus moves to the list heading
  (``#vc-list-title``) instead of falling to ``<body>``.

    .venv/bin/python spikes/issue-206/proof_s5_focus.py
"""

from __future__ import annotations

from typing import Any

from harness import (
    LIVE_REGIONS,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_slice,
    two_class_fixture,
    upload,
    upload_bytes,
    verdict_button,
    wait_status,
)

TAG_JS = """
(regions) => {
  (window.__observers || []).forEach((observer) => observer.disconnect());
  window.__writes = Object.fromEntries(regions.map((id) => [id, 0]));
  window.__observers = regions.map((id) => {
    const node = document.getElementById(id);
    node.__tag = id;
    const observer = new MutationObserver((records) => { window.__writes[id] += records.length; });
    observer.observe(node, { childList: true, characterData: true, subtree: true });
    return observer;
  });
  document.querySelectorAll("button, select, a, h1, h2").forEach((node, index) => { node.__tag = index; });
  document.activeElement.__focused = true;
}
"""
AFTER_JS = """
(regions) => ({
  focusSameNode: document.activeElement.__focused === true,
  focus: document.activeElement.getAttribute("aria-label") || document.activeElement.id ||
    document.activeElement.tagName,
  regionsSameNodes: regions.every((id) => document.getElementById(id).__tag === id),
  writes: Object.assign({}, window.__writes),
  rebuiltControls: Array.from(document.querySelectorAll("button, select, a, h1, h2"))
    .filter((node) => node.__tag === undefined).length,
  tabStops: Array.from(document.querySelectorAll("button, select, a, [tabindex]"))
    .filter((node) => node.tabIndex >= 0 && !node.disabled).length,
  nativeDisabled: document.querySelectorAll("button[disabled]").length,
})
"""
STATIC_JS = """
() => ({
  skipLink: (document.querySelector("a[href='#vc-title']") || {}).textContent.trim(),
  h1Focusable: document.querySelector("h1#vc-title").tabIndex === -1,
  regions: ["vc-status", "vc-reconciliation", "vc-scope"].map((id) => {
    const node = document.getElementById(id);
    return id + ": role=" + node.getAttribute("role") + ", aria-live=" + node.getAttribute("aria-live");
  }),
  toggles: document.querySelectorAll("button[aria-pressed]").length,
  tabRoles: document.querySelectorAll("[role=tab], [role=tablist]").length,
  unnamed: Array.from(document.querySelectorAll("button, select, a")).filter((node) =>
    !(node.textContent.trim() || node.getAttribute("aria-label") || (node.labels && node.labels.length))).length,
  labelledSelects: Array.from(document.querySelectorAll("select")).every((node) => node.labels.length === 1),
})
"""


def hold_one(page: Any) -> list:
    held: list[tuple[Any, Any]] = []

    def hold(route: Any) -> None:
        held.append((route, route.fetch()))

    page.route("**/api/verdicts", hold)
    return held


def act(page: Any, label: str, press: str, expect: str) -> dict:
    page.evaluate(TAG_JS, list(LIVE_REGIONS))
    page.keyboard.press(press)
    wait_status(page, expect)
    page.wait_for_timeout(200)
    result = page.evaluate(AFTER_JS, list(LIVE_REGIONS))
    print(f"{label}: focused control is the same node={result['focusSameNode']} ({result['focus']}); "
          f"live regions are the same nodes={result['regionsSameNodes']}; "
          f"writes to them={result['writes']}; controls rebuilt={result['rebuiltControls']}; "
          f"tab stops={result['tabStops']}; natively disabled buttons={result['nativeDisabled']}")
    return result


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        upload(context, live, "armor_close.csv")
        page = open_slice(context, live)

        print("-- static semantics (contract section 7) --")
        static = page.evaluate(STATIC_JS)
        print(static)
        if (
            static["skipLink"] != "Skip to review content"
            or not static["h1Focusable"]
            or any("role=status, aria-live=polite" not in region for region in static["regions"])
            or static["tabRoles"]
            or static["unnamed"]
            or not static["labelledSelects"]
        ):
            failures.append("a section 7 semantic is missing")
        page.keyboard.press("Tab")
        first = page.evaluate("() => document.activeElement.textContent.trim()")
        page.keyboard.press("Enter")
        target = page.evaluate("() => document.activeElement.id")
        print(f"first Tab stop: {first!r}; activating it moves focus to: #{target}")
        if first != "Skip to review content" or target != "vc-title":
            failures.append("the skip link does not work")

        print("-- why the slice uses aria-disabled: what native `disabled` does to focus here --")
        dropped = page.evaluate("""() => {
          const probe = document.querySelector("button[data-kind-filter=all]");
          probe.focus();
          probe.disabled = true;
          const where = document.activeElement.tagName;
          probe.disabled = false;
          return where;
        }""")
        print(f"a focused button set to disabled: focus is then on <{dropped}>")

        print("-- a verdict by keyboard --")
        held = hold_one(page)
        verdict_button(page, "6032", "Approve").focus()
        page.keyboard.press("Enter")
        while not held:
            page.wait_for_timeout(20)
        page.wait_for_timeout(200)
        during = page.evaluate(
            "() => ({ focus: document.activeElement.getAttribute('aria-label'),"
            " ariaDisabled: document.activeElement.getAttribute('aria-disabled') })"
        )
        print(f"while the request is in flight: {during}")
        if during != {"focus": "Approve item 6032", "ariaDisabled": "true"}:
            failures.append("focus moved while the request was in flight")
        held[0][0].fulfill(response=held[0][1])
        wait_status(page, "recorded your approval")
        page.unroute("**/api/verdicts")
        verdict_button(page, "6032", "Unset").focus()
        first = act(page, "Unset (Enter)", "Enter", "recorded your unset")
        verdict_button(page, "6032", "Veto").focus()
        second = act(page, "Veto (Space)", "Space", "recorded your veto")
        for result in (first, second):
            if (
                not result["focusSameNode"]
                or not result["regionsSameNodes"]
                or result["rebuiltControls"]
                or result["writes"] != {"vc-status": 1, "vc-reconciliation": 0, "vc-scope": 0}
                or result["tabStops"] != first["tabStops"]
            ):
                failures.append("an acknowledgement moved focus, rebuilt a node or announced twice")

        print("-- a filter change --")
        page.locator("[data-kind-filter=exact]").focus()
        page.evaluate(TAG_JS, list(LIVE_REGIONS))
        page.keyboard.press("Enter")
        page.wait_for_timeout(200)
        result = page.evaluate(AFTER_JS, list(LIVE_REGIONS))
        print(f"kind filter: focused control is the same node={result['focusSameNode']}; "
              f"writes={result['writes']}; live regions are the same nodes={result['regionsSameNodes']}")
        if not result["focusSameNode"] or result["writes"]["vc-scope"] != 1 or result["writes"]["vc-status"]:
            failures.append("a filter change moved focus or announced in the wrong region")
        page.locator("[data-kind-filter=all]").click()

        print("-- report change, the focused member is still in the new report --")
        upload_bytes(context, live, two_class_fixture())
        verdict_button(page, "6032", "Approve").focus()
        kept = act(page, "stale_report, member 6032 still present", "Enter", "not applied")
        if not kept["focusSameNode"] or not kept["regionsSameNodes"]:
            failures.append("focus was lost although the member is still present")

        print("-- report change, the focused member is gone --")
        upload(context, live, "armor_duplicates_ui.csv")
        verdict_button(page, "6032", "Veto").focus()
        gone = act(page, "stale_report, member 6032 gone", "Enter", "not applied")
        if gone["focus"] != "vc-list-title" or not gone["regionsSameNodes"]:
            failures.append("focus did not move to the list heading")
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
