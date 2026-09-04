"""Emit repeatable rendered measurements for the #128 responsive matrix plan."""

from pathlib import Path

from playwright.sync_api import sync_playwright

CASES = (
    ("390-n4", 4, False, "100%", 390),
    ("1440-n4", 4, False, "100%", 1440),
    ("n2-below", 2, False, "527px", 900),
    ("n2-at", 2, False, "528px", 900),
    ("n3-below", 3, False, "719px", 1_000),
    ("n3-at", 3, False, "720px", 1_000),
    ("n4-below", 4, False, "911px", 1_200),
    ("n4-at", 4, False, "912px", 1_200),
    ("n1-wide", 1, False, "100%", 1_440),
    ("n5-wide", 5, False, "100%", 1_440),
    ("n4-cond-at", 4, True, "912px", 1_200),
    ("720-css-n4", 4, False, "100%", 720),
)
PROBE = Path("docs/evidence/issue-128/responsive-matrix-probe.html").resolve()
MEASURE = """() => {
  const matrix = document.querySelector('.armor-matrix');
  const rows = document.querySelector('.matrix--rows');
  const columns = document.querySelector('.matrix--columns');
  const rowTable = rows.querySelector('table');
  const columnTable = columns.querySelector('table');
  return {
    container: Math.round(matrix.getBoundingClientRect().width),
    rows: getComputedStyle(rows).display,
    columns: getComputedStyle(columns).display,
    rowScroll: Math.round(rowTable.scrollWidth),
    columnScroll: Math.round(columnTable.scrollWidth),
    documentScroll: document.documentElement.scrollWidth,
    columnRowCount: columnTable.tBodies[0].rows.length,
  };
}"""


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(PROBE.as_uri())
        for name, count, conditional, width, viewport in CASES:
            page.set_viewport_size({"width": viewport, "height": 844})
            page.evaluate(
                "([count, conditional, width]) => renderProbe(count, conditional, width)",
                [count, conditional, width],
            )
            print(name, page.evaluate(MEASURE))
        browser.close()


if __name__ == "__main__":
    main()
