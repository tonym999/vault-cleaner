"""E5: what each repaint mechanism does to focus, live regions and tab order.

For R1 (in place), R2 (refetch and replace) and R3 (refetch and patch), at a
desktop width (member columns active) and a phone width (row fallback
active): focus a verdict button with the keyboard, activate it with Enter,
wait for the acknowledgement, and measure.

    .venv/bin/python spikes/issue-137/proof_e5_repaint.py
"""

from __future__ import annotations

from typing import Any

from harness import (
    STATUS_REGIONS,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_spike,
    upload,
)

MEMBER = "6032"
VIEWPORTS = ((1440, 1000, "columns"), (390, 844, "rows"))

ARM_JS = """
regions => {
  var probe = { regions: {}, focused: document.activeElement, mutations:
    { added: 0, removed: 0, attributes: 0, text: 0 }, regionWrites: {},
    elements: Array.prototype.slice.call(
      document.querySelectorAll("#vc-duplicate-list *")) };
  regions.forEach(function (id) {
    probe.regions[id] = document.getElementById(id);
    probe.regionWrites[id] = 0;
    new MutationObserver(function (records) { probe.regionWrites[id] += records.length; })
      .observe(probe.regions[id], { childList: true, characterData: true, subtree: true });
  });
  new MutationObserver(function (records) {
    records.forEach(function (record) {
      probe.mutations.added += record.addedNodes.length;
      probe.mutations.removed += record.removedNodes.length;
      if (record.type === "attributes") probe.mutations.attributes += 1;
      if (record.type === "characterData") probe.mutations.text += 1;
    });
  }).observe(document.getElementById("vc-duplicate-list"),
    { childList: true, attributes: true, characterData: true, subtree: true });
  window.__probe = probe;
}
"""
MEASURE_JS = """
regions => {
  var probe = window.__probe;
  var active = document.activeElement;
  var result = {
    sameNode: active === probe.focused,
    oldNodeConnected: probe.focused.isConnected,
    activeKey: active && active.getAttribute ? active.getAttribute("data-vc-key") : null,
    activeTag: active ? active.nodeName.toLowerCase() : null,
    pressed: active && active.getAttribute ? active.getAttribute("aria-pressed") : null,
    mutations: probe.mutations,
    elements: probe.elements.length,
    elementsKept: probe.elements.filter(function (node) { return node.isConnected; }).length,
    regions: {}
  };
  regions.forEach(function (id) {
    result.regions[id] = {
      sameNode: document.getElementById(id) === probe.regions[id],
      connected: probe.regions[id].isConnected,
      writes: probe.regionWrites[id]
    };
  });
  return result;
}
"""
TAB_ORDER_JS = """
() => Array.prototype.filter.call(
  document.querySelectorAll("a[href], button, input, select, textarea, [tabindex]"),
  function (node) {
    return !node.disabled && node.getAttribute("tabindex") !== "-1" &&
      node.getClientRects().length > 0;
  }).map(function (node) {
    return node.id || node.getAttribute("data-vc-key") ||
      node.nodeName.toLowerCase() + ":" + node.textContent.trim();
  })
"""
ACTIVE_JS = """
() => {
  var node = document.activeElement;
  return node.id || node.getAttribute("data-vc-key") || node.nodeName.toLowerCase();
}
"""


def run(browser: Any, mode: str, width: int, height: int, orientation: str, failures: list[str]) -> None:
    with live_spike() as live:
        context = authenticated_context(browser, live, width, height)
        upload(context, live, "armor_close.csv")
        page = open_spike(context, live, f"?repaint={mode}")
        key = f"{orientation}:exact_duplicate:{MEMBER}:approve"
        target = page.locator(f'[data-vc-key="{key}"]')
        target.focus()
        order_before = page.evaluate(TAB_ORDER_JS)
        page.evaluate(ARM_JS, list(STATUS_REGIONS))
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => document.getElementById('vc-status').textContent.indexOf('acknowledged') !== -1"
        )
        measured = page.evaluate(MEASURE_JS, list(STATUS_REGIONS))
        order_after = page.evaluate(TAB_ORDER_JS)
        page.keyboard.press("Tab")
        next_stop = page.evaluate(ACTIVE_JS)
        expected_next = order_before[order_before.index(key) + 1]

        regions = measured["regions"]
        kept = all(region["sameNode"] and region["connected"] for region in regions.values())
        print(f"{mode} at {width}px ({orientation} table active):")
        print(f"  focused control is the same node after the ack: {measured['sameNode']}; "
              f"old node still in the document: {measured['oldNodeConnected']}")
        print(f"  focus is on the equivalent control: {measured['activeKey'] == key} "
              f"(active element: {measured['activeTag']}, aria-pressed={measured['pressed']})")
        print(f"  list elements still in the document: {measured['elementsKept']} of "
              f"{measured['elements']}")
        print(f"  list mutation records during the ack: child nodes added={measured['mutations']['added']} "
              f"removed={measured['mutations']['removed']} "
              f"attribute changes={measured['mutations']['attributes']} "
              f"text changes={measured['mutations']['text']}")
        print("  live regions: " + "; ".join(
            f"#{name} same node={region['sameNode']} writes={region['writes']}"
            for name, region in regions.items()
        ))
        print(f"  tab order unchanged: {order_before == order_after} ({len(order_after)} stops); "
              f"Tab from the control reaches the next stop: {next_stop == expected_next}")
        if not kept:
            failures.append(f"{mode} {width}: a live region was recreated")
        if measured["activeKey"] != key:
            failures.append(f"{mode} {width}: focus was neither kept nor restored")
        if order_before != order_after or next_stop != expected_next:
            failures.append(f"{mode} {width}: tab order changed")
        if mode == "r1" and not measured["sameNode"]:
            failures.append("r1 rebuilt the focused control")
        context.close()


def main() -> int:
    failures: list[str] = []
    with chromium() as browser:
        for mode in ("r1", "r2", "r3"):
            for width, height, orientation in VIEWPORTS:
                run(browser, mode, width, height, orientation, failures)
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
