"""E6: the orientation switch and the inactive table, on Jinja markup.

Repeats, against the spike page, the checks of
``test_armor_matrix_inactive_orientation_is_unreachable_by_keyboard``,
``test_armor_matrix_orientation_flips_at_its_measured_threshold`` and
``test_duplicates_surface_does_not_scroll_horizontally``
(``tests/test_server_browser.py``), and compares each measurement with the
production page for the same session.

    .venv/bin/python spikes/issue-137/proof_e6_orientation.py
"""

from __future__ import annotations

import re
from typing import Any

from harness import (
    REPO,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_production_duplicates,
    open_spike,
    upload,
)

CSS = REPO / "src" / "vault_cleaner" / "ui" / "review.css"
VIEWPORTS = ((1440, 1000), (1024, 900), (390, 844))
FIXTURES = (
    ("armor_same_stat_ui.csv", 2),
    ("armor_duplicates_ui.csv", 3),
    ("armor_same_stat_four_ui.csv", 4),
)

MEASURE_JS = """
() => {
  var group = document.querySelector("article.armor-group");
  var columns = group.querySelector("table.armor-matrix-columns");
  var rows = group.querySelector("table.armor-matrix-rows");
  // A container query measures the container's content box.
  function contentInlineSize(node) {
    var style = getComputedStyle(node);
    var chrome = ["paddingLeft", "paddingRight", "borderLeftWidth", "borderRightWidth"]
      .reduce(function (sum, name) { return sum + parseFloat(style[name]); }, 0);
    return Math.round((node.getBoundingClientRect().width - chrome) * 100) / 100;
  }
  function shown(table) { return getComputedStyle(table).display !== "none"; }
  function refusesFocus(table) {
    var button = table.querySelector("button");
    if (!button) return null;
    button.focus();
    var refused = document.activeElement !== button;
    if (!refused) button.blur();
    return refused;
  }
  var active = shown(columns) ? columns : rows;
  var inactive = shown(columns) ? rows : columns;
  return {
    container: contentInlineSize(group),
    rootFontSize: parseFloat(getComputedStyle(document.documentElement).fontSize),
    columns: shown(columns),
    rows: shown(rows),
    inactiveOffsetParentNull: inactive.offsetParent === null,
    inactiveRefusesFocus: refusesFocus(inactive),
    activeAcceptsFocus: refusesFocus(active) === false,
    documentScrollWidth: document.documentElement.scrollWidth,
    scrollerOverflowX: getComputedStyle(group.querySelector(".scroller")).overflowX,
    buttonsInDom: group.querySelectorAll("button[aria-pressed]").length
  };
}
"""


def css_thresholds() -> dict[int, float]:
    """The per-member-count container thresholds, read from review.css."""
    source = CSS.read_text(encoding="utf-8")
    pattern = re.compile(
        r"@container \(min-inline-size: ([0-9.]+)rem\) \{\s*"
        r'article\.armor-group\[data-member-count="(\d)"\] \.armor-matrix-columns \{ display: table; \}'
    )
    return {int(count): float(rem) for rem, count in pattern.findall(source)}


def accessible_buttons(page: Any) -> int:
    """Pressed-state buttons the accessibility tree exposes for the group."""
    snapshot = page.locator("article.armor-group").aria_snapshot()
    return len(re.findall(r"- button .*\[pressed", snapshot)) + len(
        re.findall(r'- button "(?:approve|veto|unset verdict)[^"]*"(?! \[pressed)', snapshot)
    )


def measure(page: Any, width: int, height: int) -> dict:
    page.set_viewport_size({"width": width, "height": height})
    return page.evaluate(MEASURE_JS)


def flip_width(page: Any, low: int, high: int) -> int:
    """Smallest viewport width at which the member-column table is shown."""
    while low < high:
        middle = (low + high) // 2
        if measure(page, middle, 900)["columns"]:
            high = middle
        else:
            low = middle + 1
    return low


def main() -> int:
    failures: list[str] = []
    thresholds = css_thresholds()
    print(f"review.css container thresholds (rem): {thresholds}")
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        for fixture, members in FIXTURES:
            upload(context, live, fixture)
            production = open_production_duplicates(context, live)
            spike = open_spike(context, live)
            print(f"-- {fixture}: {members} members, threshold {thresholds[members]}rem --")
            for width, height in VIEWPORTS:
                ours = measure(spike, width, height)
                theirs = measure(production, width, height)
                threshold_px = thresholds[members] * ours["rootFontSize"]
                expected_columns = ours["container"] >= threshold_px
                tree_buttons = accessible_buttons(spike)
                print(
                    f"{width}px: container content box jinja={ours['container']}px production={theirs['container']}px; "
                    f"threshold={threshold_px}px; active table jinja="
                    f"{'columns' if ours['columns'] else 'rows'} production="
                    f"{'columns' if theirs['columns'] else 'rows'}"
                )
                print(
                    f"  inactive table: offsetParent null={ours['inactiveOffsetParentNull']}, "
                    f"refuses focus={ours['inactiveRefusesFocus']}; active table accepts focus="
                    f"{ours['activeAcceptsFocus']}; verdict buttons in DOM={ours['buttonsInDom']}, "
                    f"in the accessibility tree={tree_buttons}"
                )
                print(
                    f"  document scrollWidth={ours['documentScrollWidth']} (viewport {width}); "
                    f"matrix scroller overflow-x={ours['scrollerOverflowX']}"
                )
                if ours != theirs:
                    failures.append(f"{fixture} at {width}: jinja and production measure differently")
                if ours["columns"] != expected_columns or ours["columns"] == ours["rows"]:
                    failures.append(f"{fixture} at {width}: wrong orientation for the threshold")
                if not ours["inactiveOffsetParentNull"] or ours["inactiveRefusesFocus"] is False:
                    failures.append(f"{fixture} at {width}: the inactive table is reachable")
                if tree_buttons * 2 != ours["buttonsInDom"]:
                    failures.append(f"{fixture} at {width}: the inactive table is in the accessibility tree")
                if ours["documentScrollWidth"] > width or ours["scrollerOverflowX"] != "auto":
                    failures.append(f"{fixture} at {width}: the page scrolls sideways")
            if members == 2:
                ours_flip = flip_width(spike, 400, 1200)
                theirs_flip = flip_width(production, 400, 1200)
                below = measure(spike, ours_flip - 1, 900)
                at = measure(spike, ours_flip, 900)
                back = measure(spike, ours_flip - 1, 900)
                print(
                    f"flip search: columns first shown at viewport jinja={ours_flip}px "
                    f"production={theirs_flip}px; container just below={below['container']}px "
                    f"(rows={below['rows']}), at the flip={at['container']}px (columns={at['columns']}); "
                    f"narrowing again shows rows={back['rows']}"
                )
                threshold_px = thresholds[2] * at["rootFontSize"]
                if ours_flip != theirs_flip or not (below["container"] < threshold_px <= at["container"]):
                    failures.append("the flip point is not the review.css threshold")
                if not back["rows"]:
                    failures.append("the flip is not reversible")
            production.close()
            spike.close()
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
