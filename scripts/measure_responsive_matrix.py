"""Emit repeatable rendered measurements for the #128 responsive matrix plan."""

from pathlib import Path

from playwright.sync_api import sync_playwright

CASES = (
    ("390-n4", 4, False, "100%", 390, 316, "block", "none", 7),
    ("1440-n4", 4, False, "100%", 1_440, 1_156, "none", "block", 7),
    ("n2-below", 2, False, "527px", 900, 527, "block", "none", 7),
    ("n2-at", 2, False, "528px", 900, 528, "none", "block", 7),
    ("n3-below", 3, False, "719px", 1_000, 719, "block", "none", 7),
    ("n3-at", 3, False, "720px", 1_000, 720, "none", "block", 7),
    ("n4-below", 4, False, "911px", 1_200, 911, "block", "none", 7),
    ("n4-at", 4, False, "912px", 1_200, 912, "none", "block", 7),
    ("n1-wide", 1, False, "100%", 1_440, 1_156, "block", "none", 7),
    ("n5-wide", 5, False, "100%", 1_440, 1_156, "block", "none", 7),
    ("n4-cond-at", 4, True, "912px", 1_200, 912, "none", "block", 11),
    ("720-css-n4", 4, False, "100%", 720, 628, "block", "none", 7),
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
        try:
            page = browser.new_page()
            page.goto(PROBE.as_uri())
            results = {}
            for (
                name,
                count,
                conditional,
                width,
                viewport,
                expected_container,
                expected_rows,
                expected_columns,
                expected_row_count,
            ) in CASES:
                page.set_viewport_size({"width": viewport, "height": 844})
                page.evaluate(
                    "([count, conditional, width]) => renderProbe(count, conditional, width)",
                    [count, conditional, width],
                )
                result = page.evaluate(MEASURE)
                assert result["container"] == expected_container, (name, result)
                assert result["rows"] == expected_rows, (name, result)
                assert result["columns"] == expected_columns, (name, result)
                assert result["documentScroll"] == viewport, (name, result)
                assert result["columnRowCount"] == expected_row_count, (name, result)
                if expected_columns == "block":
                    assert result["columnScroll"] == expected_container, (name, result)
                else:
                    assert result["rowScroll"] >= expected_container, (name, result)
                results[name] = result
                print(name, result)

            for below, at in (("n2-below", "n2-at"), ("n3-below", "n3-at"), ("n4-below", "n4-at")):
                assert results[below]["rows"] == "block", (below, results[below])
                assert results[at]["columns"] == "block", (at, results[at])
            assert results["n4-cond-at"]["columnRowCount"] == results["n4-at"]["columnRowCount"] + 4
        finally:
            browser.close()


if __name__ == "__main__":
    main()
