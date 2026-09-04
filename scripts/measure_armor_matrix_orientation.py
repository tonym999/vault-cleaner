"""Measure the issue #131 armor duplicate matrix orientation switch.

The difference-only comparison renders two semantic orientations of the same
field list: an artifact-shaped member-column table (``table.armor-matrix-
columns``) and an accessible member-row fallback (``table.armor-matrix-
rows``), switched by a CSS container query on ``article.armor-group``'s own
inline size. Design intent is not evidence -- AGENTS.md is blunt that
spec-first designs die on real data, and issue #113 established this
repository's method for a narrow claim: measure the component at the width it
will really have, with no enclosing chrome, and assert preconditions before
reporting a number. This script does that for the orientation switch.

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

from playwright.sync_api import sync_playwright

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
    docScrollWidth: document.documentElement.scrollWidth,
  };
}"""


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
                        page.set_viewport_size({"width": width, "height": height})
                        result = page.evaluate(PROBE)
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

        evidence = OUT / "orientation-measurements.md"
        header = [
            "# Issue #131 orientation-switch measurements",
            "",
            "Measured by uploading the committed fake fixtures into the real",
            "packaged server (`scripts/measure_armor_matrix_orientation.py`) and",
            "reading live geometry in managed Chromium. Every precondition below",
            "(exactly one orientation visible, no document horizontal overflow) is",
            "asserted by the script before this file is written; a failing",
            "precondition makes the script exit non-zero instead of reporting a",
            "number. `1rem = 16px`.",
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
