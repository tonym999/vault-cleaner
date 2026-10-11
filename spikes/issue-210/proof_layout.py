"""#210: what replaced "pieces in one column" (plan Amendments 1 and 2).

    .venv/bin/python spikes/issue-210/proof_layout.py

#206's S6 and S15 require every piece to share one left edge. Direction D
puts pieces side by side, so the runner replaces that one measure with a
constant and this proof asserts the layout that took its place.

On the synthetic both-kinds and four-member fixtures and on the tracked
sanitised fixture, in both schemes:

- at 1440 px, in every group of two to four pieces, the piece headers share
  one top edge and have strictly increasing left edges;
- at 390 px the same holds for every pair and triple, and every group of four
  is one block per piece: one left edge, strictly increasing top edges;
- where the pieces are columns, each row's cells share one top edge across
  the pieces, so a value lines up with the same field on the next piece;
- every piece header, cell and verdict button lies inside the viewport;
- no visible text is set smaller than 11 px.

Then two cases the fixtures do not hold:

- **identical tuning** (the #210 review's reproduction): a same-stat group
  whose pieces share one tuning and differ on Holofoil still shows a
  tuned-stat cell on every piece, first, and the parity oracle still holds;
- **negative control**: with the matrix forced to block layout through the
  CSSOM, the 1440 px side-by-side assertion must fail.
"""

from __future__ import annotations

import csv
import io
import sys
from itertools import pairwise
from typing import Any

from run_proof import configure

configure()

import harness
from dev import preload
from expected import compare

MIN_TEXT_PX = 11
LAYOUT_JS = """
() => {
  const width = document.documentElement.clientWidth;
  const round = (value) => Math.round(value * 2) / 2;
  const inside = (node) => {
    const box = node.getBoundingClientRect();
    return box.width > 0 && box.height > 0 && box.left >= -0.5 && box.right <= width + 0.5;
  };
  const groups = Array.from(document.querySelectorAll("article[data-group]")).map((article) => {
    const pieces = Array.from(article.querySelectorAll("li.piece"));
    const heads = pieces.map((piece) => piece.querySelector(".piece-head").getBoundingClientRect());
    const cells = pieces.map((piece) => Array.from(piece.querySelectorAll(".cell")));
    const rows = cells[0].map((_, row) => cells.map((column) => round(column[row].getBoundingClientRect().top)));
    return {
      key: article.getAttribute("data-group"),
      pieces: pieces.length,
      lefts: heads.map((box) => round(box.left)),
      tops: heads.map((box) => round(box.top)),
      sameRowCount: cells.every((column) => column.length === cells[0].length),
      rowsAligned: rows.every((tops) => tops.every((top) => top === tops[0])),
      // The pieces' own cells: the label column is not shown at narrow widths.
      outside: Array.from(article.querySelectorAll("li.piece .piece-head, li.piece .cell, li.piece button"))
        .filter((node) => !inside(node)).length,
    };
  });
  // Visible text only: a node clipped to a pixel is for screen readers.
  const small = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let texts = 0;
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!node.textContent.trim()) continue;
    const parent = node.parentElement;
    const box = parent.getBoundingClientRect();
    if (box.width <= 1 || box.height <= 1 || getComputedStyle(parent).visibility === "hidden") continue;
    texts += 1;
    const size = parseFloat(getComputedStyle(parent).fontSize);
    if (size < MIN_TEXT - 0.01) {
      const name = parent.className ? "." + String(parent.className).split(" ")[0] : parent.tagName.toLowerCase();
      small.set(name + " " + size + "px", (small.get(name + " " + size + "px") || 0) + 1);
    }
  }
  return { groups, texts, small: Array.from(small.entries()), sideways: document.documentElement.scrollWidth > width };
}
""".replace("MIN_TEXT", str(MIN_TEXT_PX))


def increasing(values: list[float]) -> bool:
    return all(later > earlier for earlier, later in pairwise(values))


def same(values: list[float]) -> bool:
    return len(set(values)) == 1


def side_by_side(group: dict) -> bool:
    return same(group["tops"]) and increasing(group["lefts"]) and group["rowsAligned"]


def stacked(group: dict) -> bool:
    return same(group["lefts"]) and increasing(group["tops"])


def judge(layout: dict, width: int) -> dict[str, list[str]]:
    """Each rule's offenders, by group key."""
    wrong: dict[str, list[str]] = {"columns": [], "blocks": [], "outside": [], "rows": []}
    for group in layout["groups"]:
        if not group["sameRowCount"]:
            wrong["rows"].append(group["key"])
        if group["outside"]:
            wrong["outside"].append(group["key"])
        if not 2 <= group["pieces"] <= 4:
            continue
        if width == 390 and group["pieces"] == 4:
            if not stacked(group):
                wrong["blocks"].append(group["key"])
        elif not side_by_side(group):
            wrong["columns"].append(group["key"])
    return wrong


def measure(page: Any, label: str, failures: list[str]) -> None:
    for width in (1440, 390):
        for scheme in ("light", "dark"):
            page.set_viewport_size({"width": width, "height": 900})
            page.emulate_media(color_scheme=scheme)
            page.evaluate("() => window.scrollTo(0, 0)")
            layout = page.evaluate(LAYOUT_JS)
            wrong = judge(layout, width)
            sizes = {pieces: sum(group["pieces"] == pieces for group in layout["groups"])
                     for pieces in sorted({group["pieces"] for group in layout["groups"]})}
            print(f"{label}, {width}px {scheme}: groups by piece count={sizes}; not side by side with "
                  f"aligned rows={len(wrong['columns'])}; fours not stacked={len(wrong['blocks'])}; "
                  f"uneven row counts={len(wrong['rows'])}; groups with a cell or button outside the "
                  f"viewport={len(wrong['outside'])}; page scrolls sideways={layout['sideways']}; visible "
                  f"text nodes={layout['texts']}, under {MIN_TEXT_PX}px={layout['small']}")
            if any(wrong.values()) or layout["sideways"] or layout["small"]:
                failures.append(f"{label}, {width}px {scheme}: " + "; ".join(
                    f"{rule} {keys[:2]}" for rule, keys in wrong.items() if keys) + f" small={layout['small'][:2]}")


def identical_tuning() -> bytes:
    """The review's case, built in memory: one tuning on both pieces, Holofoil differs."""
    source = (harness.FIXTURES / "armor_same_stat_ui.csv").read_text(encoding="utf-8", newline="")
    reader = csv.DictReader(io.StringIO(source))
    rows = list(reader)
    rows[1]["Tuning Stat"] = rows[0]["Tuning Stat"]
    rows[1]["Holofoil"] = "true"
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


TUNED_JS = """
() => Array.from(document.querySelectorAll("article[data-kind=same_stat]")).map((article) => ({
  key: article.getAttribute("data-group"),
  shared: Array.from(article.querySelectorAll("[data-shared]")).map((node) => node.getAttribute("data-shared")),
  pieces: Array.from(article.querySelectorAll("li.piece")).map((piece) => {
    const first = piece.querySelector(".piece-fields .cell");
    const value = first.querySelector("[data-field=tuning_mod_slot]");
    const box = value ? value.getBoundingClientRect() : { width: 0, height: 0 };
    return {
      id: piece.getAttribute("data-member"),
      firstRowIsTuning: first.classList.contains("tuned"),
      value: value ? value.textContent.trim() : null,
      visible: box.width > 0 && box.height > 0,
      marked: first.querySelectorAll(".tuned-box.on").length,
    };
  }),
}))
"""


def main() -> int:
    failures: list[str] = []
    harness.require_build()
    with harness.chromium() as browser:
        for fixture in ("armor_close.csv", "armor_same_stat_four_ui.csv", "real"):
            with harness.live_spike() as live:
                preload(live, fixture)
                context = harness.authenticated_context(browser, live)
                page = harness.open_slice(context, live)
                page.wait_for_selector("article[data-group]")
                measure(page, fixture, failures)
                if fixture == "real":
                    page.set_viewport_size({"width": 1440, "height": 900})
                    page.evaluate("""() => {
                      const sheet = document.styleSheets[0];
                      sheet.insertRule(".matrix { display: block !important; }", sheet.cssRules.length);
                    }""")
                    broken = judge(page.evaluate(LAYOUT_JS), 1440)
                    groups = page.locator("article[data-group]").count()
                    print(f"negative control, matrix forced to block at 1440px: groups failing "
                          f"side by side={len(broken['columns'])} of {groups}")
                    if len(broken["columns"]) != groups:
                        failures.append("negative control: a stacked matrix was not detected")
                context.close()

        print("-- identical tuning, Holofoil differs (built in memory, uploaded through the server) --")
        with harness.live_spike() as live:
            context = harness.authenticated_context(browser, live)
            harness.upload_bytes(context, live, identical_tuning(), fixture="identical tuning")
            page = harness.open_slice(context, live)
            page.wait_for_selector("article[data-group]")
            envelope = harness.report(context, live)
            for width in (1440, 390):
                page.set_viewport_size({"width": width, "height": 900})
                groups = page.evaluate(TUNED_JS)
                pieces = [piece for group in groups for piece in group["pieces"]]
                good = bool(pieces) and all(
                    piece["firstRowIsTuning"] and piece["value"] and piece["visible"] and piece["marked"] == 1
                    for piece in pieces
                )
                parity = compare(harness.read_slice(page), envelope)
                print(f"{width}px: same-stat groups={len(groups)}; pieces={len(pieces)}; every piece "
                      f"leads with a visible tuned stat and one marker={good} "
                      f"{[(piece['id'], piece['value']) for piece in pieces]}; also in the shared line="
                      f"{['tuning_mod_slot' in group['shared'] for group in groups]}; differences from "
                      f"the server's report={len(parity)} {parity[:2]}")
                if not good or parity or len(groups) != 1:
                    failures.append(f"identical tuning at {width}px: the tuned-stat row or parity fails")
            context.close()
    return harness.finish(failures)


if __name__ == "__main__":
    sys.exit(main())
