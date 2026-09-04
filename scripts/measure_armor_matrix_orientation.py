"""Measure the issue #131 armor duplicate matrix orientation switch.

The difference-only comparison renders two semantic orientations of the same
field list: an artifact-shaped member-column table (``table.armor-matrix-
columns``) and an accessible member-row fallback (``table.armor-matrix-
rows``), switched by a CSS container query on ``article.armor-group``'s own
inline size. Design intent is not evidence -- AGENTS.md is blunt that
spec-first designs die on real data, and issue #113 established this
repository's method for a narrow claim: measure the component at the width it
will really have, with no enclosing chrome, and assert preconditions before
reporting a number. This script does that for the orientation switch,
including the flip point for each supported member count and the row-count
delta a group's conditional same-stat axes actually produce.

It boots the real packaged server (as ``tests/test_server_browser.py`` does),
uploads the committed fake fixtures over HTTP, and reads live geometry from
the production page -- never a standalone harness page.

Usage (from the repo root, with the project venv):

    .venv/bin/python scripts/measure_armor_matrix_orientation.py
"""

from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from vault_cleaner.server.app import DEFAULT_ASSETS, build_server
from vault_cleaner.server.session import Session

REPO = Path(__file__).resolve().parent.parent
FIXTURES = REPO / "tests" / "fixtures"
OUT = REPO / "docs" / "evidence" / "issue-131"

VIEWPORTS = [(1440, 1000), (1024, 900), (390, 844)]

# (fixture filename, member count, description)
FIXTURES_UNDER_TEST = [
    ("armor_duplicates_ui.csv", 3, "exact, 3 pieces"),
    ("armor_same_stat_ui.csv", 2, "same-stat, 2 pieces"),
    ("armor_same_stat_four_ui.csv", 4, "same-stat, 4 pieces"),
]

# The shipped CSS thresholds this script's flip-point search must corroborate
# (review.css `article.armor-group[data-member-count="N"] .armor-matrix-columns
# { min-width: ... }` / matching `@container (min-inline-size: ...)`).
CSS_THRESHOLDS_REM = {2: 38.5, 3: 51.0, 4: 63.5, 5: 76.0, 6: 88.5}

# A binary search range in viewport pixels wide enough to bracket every
# reachable flip point (measured comparison content boxes never exceed
# ~1190px, see the unreachable-thresholds measurement below) with margin on
# both sides, and narrow enough to keep the search itself fast.
SEARCH_LO = 320
SEARCH_HI = 1800

# A viewport comfortably wider than the `.wrap { max-width: 78rem }` cap can
# ever let the comparison content box reach, used to measure the real
# plateau for the N=5/N=6 unreachable-thresholds note.
WIDE_CAP_VIEWPORT = (2560, 1200)

PROBE = """() => {
  const group = document.querySelector('article.armor-group');
  if (!group) return null;
  const comparison = group.querySelector('.armor-comparison .scroller');
  const columns = group.querySelector('table.armor-matrix-columns');
  const rows = group.querySelector('table.armor-matrix-rows');
  const visible = el => !!el && el.getClientRects().length > 0 &&
    getComputedStyle(el).display !== 'none';
  const columnsVisible = visible(columns);
  const rowsVisible = visible(rows);
  return {
    groupWidth: group.getBoundingClientRect().width,
    comparisonWidth: comparison ? comparison.getBoundingClientRect().width : null,
    columnsVisible: columnsVisible,
    rowsVisible: rowsVisible,
    columnsRowCount: columns ? columns.querySelectorAll('tbody tr').length : null,
    rowsRowCount: rows ? rows.querySelectorAll('tbody tr').length : null,
    columnsAxisLabels: columns
      ? Array.from(columns.querySelectorAll('tbody th.armor-matrix-axis-label'))
          .map(th => th.textContent)
      : null,
    docScrollWidth: document.documentElement.scrollWidth,
  };
}"""


def probe_at(page: Page, width: int, height: int) -> dict | None:
    page.set_viewport_size({"width": width, "height": height})
    return page.evaluate(PROBE)


def find_flip_point(
    page: Page, member_count: int, failures: list[str], fixture_name: str
) -> dict | None:
    """Binary-search the smallest viewport width at which the member-column
    orientation becomes active for this member count, in the real browser.

    Asserts the search range actually brackets a flip (rows active at
    ``SEARCH_LO``, columns active at ``SEARCH_HI``) before trusting the
    bisection result, per the "fail rather than report" requirement --
    reports nothing and appends a failure instead of guessing.
    """
    lo_probe = probe_at(page, SEARCH_LO, 900)
    hi_probe = probe_at(page, SEARCH_HI, 900)
    if lo_probe is None or hi_probe is None:
        failures.append(
            f"{fixture_name}: flip-point search found no article.armor-group"
        )
        return None
    if lo_probe["columnsVisible"] or not lo_probe["rowsVisible"]:
        failures.append(
            f"{fixture_name}: flip-point search precondition failed -- "
            f"expected rows active at {SEARCH_LO}px, got "
            f"columnsVisible={lo_probe['columnsVisible']} "
            f"rowsVisible={lo_probe['rowsVisible']}"
        )
        return None
    if not hi_probe["columnsVisible"] or hi_probe["rowsVisible"]:
        failures.append(
            f"{fixture_name}: flip-point search precondition failed -- "
            f"expected columns active at {SEARCH_HI}px, got "
            f"columnsVisible={hi_probe['columnsVisible']} "
            f"rowsVisible={hi_probe['rowsVisible']}"
        )
        return None

    lo, hi = SEARCH_LO, SEARCH_HI
    while hi - lo > 1:
        mid = (lo + hi) // 2
        result = probe_at(page, mid, 900)
        if result is None:
            failures.append(
                f"{fixture_name}: flip-point search lost article.armor-group at {mid}px"
            )
            return None
        if result["columnsVisible"] and not result["rowsVisible"]:
            hi = mid
        elif result["rowsVisible"] and not result["columnsVisible"]:
            lo = mid
        else:
            failures.append(
                f"{fixture_name}: flip-point search saw both-or-neither "
                f"orientation visible at {mid}px (columnsVisible="
                f"{result['columnsVisible']} rowsVisible={result['rowsVisible']})"
            )
            return None

    below = probe_at(page, lo, 900)
    at_flip = probe_at(page, hi, 900)
    if below is None or at_flip is None:
        failures.append(f"{fixture_name}: flip-point search lost the group at the boundary")
        return None
    if not (below["rowsVisible"] and not below["columnsVisible"]):
        failures.append(
            f"{fixture_name}: flip-point boundary check failed just below the flip "
            f"({lo}px)"
        )
        return None
    if not (at_flip["columnsVisible"] and not at_flip["rowsVisible"]):
        failures.append(
            f"{fixture_name}: flip-point boundary check failed at the flip ({hi}px)"
        )
        return None

    return {
        "member_count": member_count,
        "viewport_flip_px": hi,
        "viewport_just_below_px": lo,
        "comparison_width_at_flip_px": at_flip["comparisonWidth"],
        "comparison_width_just_below_px": below["comparisonWidth"],
    }


def measure_unreachable_cap(page: Page, failures: list[str]) -> dict | None:
    """Measure the real plateau the `.wrap { max-width: 78rem }` cap imposes
    on the comparison content box, at a viewport far wider than any threshold
    could need. Whatever group is currently loaded is fine: the cap comes
    from the page chrome, not the group's own member count."""
    width, height = WIDE_CAP_VIEWPORT
    result = probe_at(page, width, height)
    if result is None:
        failures.append("unreachable-cap measurement found no article.armor-group")
        return None
    if result["docScrollWidth"] > width:
        failures.append(
            f"unreachable-cap measurement: document scrolled horizontally at "
            f"{width}x{height} (scrollWidth={result['docScrollWidth']})"
        )
        return None
    return {
        "viewport": f"{width}x{height}",
        "comparison_width_px": result["comparisonWidth"],
        "group_width_px": result["groupWidth"],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-measure-") as tmp:
        tmp_path = Path(tmp)
        config = tmp_path / "config.toml"
        config.write_text("", encoding="utf-8")
        session = Session(
            overrides_path=str(tmp_path / "overrides.json"),
            config_path=str(config),
            no_wishlists=True,
            bootstrap_token="measure-bootstrap",
            session_token="measure-session",
        )
        server = build_server(session, 0, assets=DEFAULT_ASSETS)
        thread = threading.Thread(
            target=server.serve_forever, name="vault-cleaner-measure-server"
        )
        thread.start()
        origin = session.expected_origin
        bootstrap_url = f"{origin}/bootstrap?token={session.bootstrap_token}"

        failures: list[str] = []
        report_lines: list[str] = []
        flip_points: list[dict] = []
        axis_labels_by_fixture: dict[str, list[str]] = {}
        unreachable_cap: dict | None = None

        try:
            with sync_playwright() as play:
                browser = play.chromium.launch()
                # The bootstrap token is single-use, so authenticate once and
                # reuse the page for every fixture -- each upload replaces the
                # prior armor export within the same authenticated session,
                # exactly as a reviewer re-uploading a new export would.
                context = browser.new_context()
                page = context.new_page()
                page.goto(bootstrap_url, wait_until="domcontentloaded")
                if "Connected" not in page.locator("#vc-status").inner_text():
                    failures.append("bootstrap did not connect")
                for fixture_name, member_count, description in FIXTURES_UNDER_TEST:
                    fixture_path = FIXTURES / fixture_name
                    if not fixture_path.exists():
                        failures.append(f"missing fixture: {fixture_path}")
                        continue
                    page.locator("#vc-upload-armor").set_input_files(str(fixture_path))
                    page.wait_for_selector(
                        "#vc-upload-status-armor:has-text('Accepted')"
                    )
                    duplicates_button = page.locator("#vc-view-duplicates")
                    if not duplicates_button.is_enabled():
                        failures.append(
                            f"{fixture_name}: Armor duplicates tab never enabled"
                        )
                        continue
                    duplicates_button.click()
                    # Disambiguate from a still-present previous fixture's
                    # group: wait for a group with this fixture's own member
                    # count, not merely "some article.armor-group exists".
                    page.wait_for_selector(
                        f'article.armor-group[data-member-count="{member_count}"]'
                    )

                    report_lines.append(f"\n### {fixture_name} ({description})\n")
                    report_lines.append(
                        "| Viewport | `.armor-group` width | comparison content box "
                        "| active orientation | rows table `tbody tr` | columns table "
                        "`tbody tr` | doc scrollWidth |"
                    )
                    report_lines.append("|---|---|---|---|---|---|---|")

                    for width, height in VIEWPORTS:
                        result = probe_at(page, width, height)
                        if result is None:
                            failures.append(
                                f"{fixture_name} @ {width}x{height}: no article.armor-group found"
                            )
                            continue
                        both_visible = result["columnsVisible"] and result["rowsVisible"]
                        neither_visible = (
                            not result["columnsVisible"] and not result["rowsVisible"]
                        )
                        if both_visible or neither_visible:
                            failures.append(
                                f"{fixture_name} @ {width}x{height}: expected exactly one "
                                f"orientation visible, got columnsVisible="
                                f"{result['columnsVisible']} rowsVisible={result['rowsVisible']}"
                            )
                        if result["docScrollWidth"] > width:
                            failures.append(
                                f"{fixture_name} @ {width}x{height}: document scrolled "
                                f"horizontally (scrollWidth={result['docScrollWidth']})"
                            )
                        active = "columns" if result["columnsVisible"] else "rows"
                        report_lines.append(
                            f"| {width}x{height} | {result['groupWidth']:.1f}px "
                            f"| {result['comparisonWidth']:.1f}px | {active} "
                            f"| {result['rowsRowCount']} | {result['columnsRowCount']} "
                            f"| {result['docScrollWidth']}px |"
                        )
                        # The conditional-axis row-count delta needs the
                        # per-fixture axis labels while columns are active at
                        # a viewport known to fit every supported count
                        # (1440x1000, per the table above).
                        if (
                            width == 1440
                            and result["columnsVisible"]
                            and result["columnsAxisLabels"] is not None
                        ):
                            axis_labels_by_fixture[fixture_name] = result["columnsAxisLabels"]

                    flip = find_flip_point(page, member_count, failures, fixture_name)
                    if flip is not None:
                        flip_points.append(flip)

                unreachable_cap = measure_unreachable_cap(page, failures)

                context.close()
                browser.close()
        finally:
            if thread.is_alive():
                server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            session.close()
            if thread.is_alive():
                failures.append("measure server thread did not stop")

        if failures:
            print("FAILED preconditions:", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            return 1

        report_lines.append("\n## Flip points (binary-searched, per member count)\n")
        report_lines.append(
            "| Members | flip viewport width | just below the flip | comparison "
            "content box at the flip | shipped CSS threshold | matches |"
        )
        report_lines.append("|---|---|---|---|---|---|")
        for flip in sorted(flip_points, key=lambda entry: entry["member_count"]):
            n = flip["member_count"]
            threshold_rem = CSS_THRESHOLDS_REM[n]
            threshold_px = threshold_rem * 16
            measured_px = flip["comparison_width_at_flip_px"]
            matches = "yes" if abs(measured_px - threshold_px) < 1.0 else "no"
            report_lines.append(
                f"| {n} | {flip['viewport_flip_px']}px | "
                f"{flip['viewport_just_below_px']}px | {measured_px:.1f}px "
                f"| {threshold_rem}rem ({threshold_px:.0f}px) | {matches} |"
            )

        report_lines.append(
            "\nEach flip point above was found by bisecting the real browser "
            "viewport width until the member-column orientation first became "
            "active, then confirming the row fallback is active one pixel "
            "below that width and the member-column orientation is active at "
            "it -- not asserted from the stylesheet."
        )

        report_lines.append("\n## Conditional same-stat axis row-count delta\n")
        two_labels = axis_labels_by_fixture.get("armor_same_stat_ui.csv")
        four_labels = axis_labels_by_fixture.get("armor_same_stat_four_ui.csv")
        if two_labels is not None and four_labels is not None:
            delta = len(four_labels) - len(two_labels)
            report_lines.append(
                "Measured at 1440x1000 with the member-column orientation active "
                "(so `tbody th.armor-matrix-axis-label` enumerates exactly the "
                "rendered axis rows, one per differing or always-shown axis plus "
                "Verdict). Member count does not change this count by itself -- "
                "the delta below comes entirely from which conditional axes "
                "actually differ in each committed fixture's real data."
            )
            report_lines.append("")
            report_lines.append(
                f"- `armor_same_stat_ui.csv` (2 pieces): {len(two_labels)} rows -- "
                f"{', '.join(two_labels)}"
            )
            report_lines.append(
                f"- `armor_same_stat_four_ui.csv` (4 pieces): {len(four_labels)} rows -- "
                f"{', '.join(four_labels)}"
            )
            report_lines.append(f"- delta: {delta:+d} rows")
        else:
            failures.append(
                "conditional-axis row-count delta: missing axis labels for one or "
                "both same-stat fixtures"
            )

        if unreachable_cap is not None:
            report_lines.append(
                "\n## N=5 / N=6 thresholds are unreachable in practice\n"
            )
            report_lines.append(
                f"Measured at {unreachable_cap['viewport']} -- far wider than any "
                "supported member count could need -- the comparison content box "
                f"plateaus at {unreachable_cap['comparison_width_px']:.1f}px "
                f"(`.armor-group` width {unreachable_cap['group_width_px']:.1f}px), "
                "capped by `.wrap { max-width: 78rem }` (1248px) minus its own "
                "1rem padding on each side and `.armor-group`'s border and "
                ".75rem padding on each side. That plateau is below the N=5 "
                f"threshold ({CSS_THRESHOLDS_REM[5]}rem = "
                f"{CSS_THRESHOLDS_REM[5] * 16:.0f}px) and well below the N=6 "
                f"threshold ({CSS_THRESHOLDS_REM[6]}rem = "
                f"{CSS_THRESHOLDS_REM[6] * 16:.0f}px), so neither `@container` "
                "rule can ever match in this surface's real layout. They are "
                "deliberate defensive rules for a member count the producer "
                "cannot emit today, not measured thresholds -- shipped for "
                "consistency with N=2..4 and to fail safe (row fallback) rather "
                "than assume, should that ever change."
            )

        if failures:
            print("FAILED preconditions:", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            return 1

        evidence = OUT / "orientation-measurements.md"
        header = [
            "# Issue #131 orientation-switch measurements",
            "",
            "Measured by uploading the committed fake fixtures into the real",
            "packaged server (`scripts/measure_armor_matrix_orientation.py`) and",
            "reading live geometry in managed Chromium. Every precondition below",
            "(exactly one orientation visible, no document horizontal overflow,",
            "a real flip bracketed on both sides) is asserted by the script",
            "before this file is written; a failing precondition makes the",
            "script exit non-zero instead of reporting a number. `1rem = 16px`.",
        ]
        evidence.write_text(
            "\n".join(header) + "\n" + "\n".join(report_lines) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {evidence}")
        print("\n".join(report_lines))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
