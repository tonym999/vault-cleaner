"""Line ranges behind the JavaScript keep/remove map, checked at this head.

Each row names a range in the production browser code and the text its first
line must contain, so a citation that has drifted fails here instead of in
review.  The second half counts what the spike wrote to replace the Armor
duplicates slice.

    .venv/bin/python spikes/issue-137/proof_js_map.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
UI = SPIKE_DIR.parents[1] / "src" / "vault_cleaner" / "ui"
S = "review_server.js"
U = "review_ui.js"

# (responsibility, file, first line, last line, text on the first line)
RANGES = (
    ("1 bootstrap/session", S, 81, 120, "function createState"),
    ("1 bootstrap/session", S, 128, 212, "function sanitizedOverrideStatus"),
    ("1 bootstrap/session", S, 312, 413, "function applySessionEnvelope"),
    ("1 bootstrap/session", S, 1773, 1792, "var api = {"),
    ("2 uploads", S, 752, 754, "function setUploadsDisabled"),
    ("2 uploads", S, 1483, 1508, "function markUpload"),
    ("2 uploads", S, 1760, 1767, "KINDS.forEach"),
    ("3 report fetching", S, 443, 570, "function responseHeader"),
    ("3 report fetching", S, 1509, 1525, "function requestReport"),
    ("4 filters/sort/search/navigation", U, 211, 262, "function matchesText"),
    ("4 filters/sort/search/navigation", U, 264, 302, "function groupLabel"),
    ("4 filters/sort/search/navigation", U, 747, 802, "function matchesArmorGroup"),
    ("4 filters/sort/search/navigation", U, 846, 857, "function countBy"),
    ("4 filters/sort/search/navigation", S, 214, 310, "function valueStillExists"),
    ("4 filters/sort/search/navigation", S, 786, 832, "function renderViewSelector"),
    ("4 filters/sort/search/navigation", S, 1212, 1218, "function queryChange"),
    ("5 verdict mutation and acknowledgement", S, 572, 584, "function makeVerdictPayload"),
    ("5 verdict mutation and acknowledgement", S, 899, 921, "function mutationAllowed"),
    ("5 verdict mutation and acknowledgement", S, 935, 943, "function repaintRows"),
    ("5 verdict mutation and acknowledgement", S, 1526, 1543, "function mutateVerdicts"),
    ("5 verdict mutation and acknowledgement", S, 1556, 1564, "function toggleVerdict"),
    ("5 verdict mutation and acknowledgement", S, 1737, 1759, "function rowForTarget"),
    ("5 verdict mutation and acknowledgement", U, 1168, 1199, "function paintRow"),
    ("5 verdict mutation and acknowledgement", U, 1790, 1815, "function paintArmorMember"),
    ("6 stale-state reconciliation", S, 760, 776, "function reportInvalidations"),
    ("6 stale-state reconciliation", S, 944, 1014, "function adopt"),
    ("6 stale-state reconciliation", S, 1544, 1555, "function reconcileStale"),
    ("7 finalise/download/reset/shutdown", S, 585, 601, "function makeFinalizePayload"),
    ("7 finalise/download/reset/shutdown", S, 777, 785, "function renderSessionNote"),
    ("7 finalise/download/reset/shutdown", S, 851, 877, "function handleCommittedFinalizeRefreshFailure"),
    ("7 finalise/download/reset/shutdown", S, 1447, 1482, "function renderSessionActions"),
    ("7 finalise/download/reset/shutdown", S, 1565, 1736, "function downloadBlob"),
    ("8 focus and live regions", S, 603, 610, "function showReconnect"),
    ("8 focus and live regions", S, 755, 759, "function announce"),
    ("8 focus and live regions", S, 833, 850, "function fail"),
    ("8 focus and live regions", S, 878, 898, "function handleCommonFailure"),
    ("9 responsive comparison switching", U, 1641, 1648, "function armorGroupTable"),
    ("10 DOM construction: shell", S, 627, 746, "var crosscheckPanel"),
    ("10 DOM construction: metrics", S, 1015, 1043, "function renderSummary"),
    ("10 DOM construction: weapon DIM query", S, 1044, 1211, "var lastDetailsOpen"),
    ("10 DOM construction: filters", S, 1219, 1369, "function renderControls"),
    ("10 DOM construction: lists", S, 1370, 1446, "function renderList"),
    ("10 DOM construction: element helpers", U, 892, 981, "// Every node is built with createElement"),
    ("10 DOM construction: proposals", U, 87, 150, "function itemsFromSnapshot"),
    ("10 DOM construction: proposals", U, 982, 1166, "function headerRow"),
    ("10 DOM construction: duplicate groups", U, 304, 624, "/**"),
    ("10 DOM construction: duplicate groups", U, 804, 844, "// Return a display-only stat model"),
    ("10 DOM construction: duplicate groups", U, 1201, 1640, "function dispositionLabel"),
    ("10 DOM construction: duplicate groups", U, 1773, 1788, "function armorGroup"),
    ("10 DOM construction: armor DIM query", U, 626, 739, "var DIM_QUERY_SAVEABLE_MAX"),
    ("10 DOM construction: armor DIM query", U, 1650, 1771, "function armorGroupDimQuery"),
)
# Ranges the Armor duplicates slice replaced in the spike.
SLICE = (
    (U, 304, 624), (U, 804, 844), (U, 1201, 1648), (U, 1773, 1788), (U, 1790, 1815),
    (S, 1376, 1431),
)


def code_lines(path: Path, skip_markers: tuple[str, ...] = ()) -> int:
    total = 0
    skipping = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if any(f"[{marker}:start]" in line for marker in skip_markers):
            skipping = True
        if not skipping and line.strip():
            total += 1
        if any(f"[{marker}:end]" in line for marker in skip_markers):
            skipping = False
    return total


def marked_lines(path: Path, marker: str) -> int:
    """Non-blank lines inside every ``[marker:start]``..``[marker:end]`` region."""
    total = 0
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if f"[{marker}:end]" in line:
            inside = False
        if inside and line.strip():
            total += 1
        if f"[{marker}:start]" in line:
            inside = True
    return total


def main() -> int:
    failures: list[str] = []
    sources = {name: (UI / name).read_text(encoding="utf-8").splitlines() for name in (S, U)}
    print(f"{S}: {len(sources[S])} lines; {U}: {len(sources[U])} lines")
    totals: dict[str, int] = {}
    for responsibility, name, first, last, expected in RANGES:
        found = expected in sources[name][first - 1]
        size = last - first + 1
        totals[responsibility] = totals.get(responsibility, 0) + size
        print(f"{responsibility}: {name}:{first}-{last} ({size}) {'ok' if found else 'ANCHOR MISSING'}")
        if not found:
            failures.append(f"{name}:{first} does not contain {expected!r}")
    print("-- lines per responsibility --")
    for responsibility, size in totals.items():
        print(f"{responsibility}: {size}")

    print("-- the Armor duplicates slice --")
    removed = sum(last - first + 1 for _name, first, last in SLICE)
    print(f"production JavaScript the slice replaces: {removed} lines in {len(SLICE)} ranges")
    spike_js = SPIKE_DIR / "static" / "spike.js"
    everything = code_lines(spike_js)
    chosen = code_lines(spike_js, ("repaint-r3", "filters-b"))
    templates = sum(
        code_lines(path) for path in sorted((SPIKE_DIR / "templates").iterdir())
        if path.name not in ("whole_page.html", "shell.html")
    )
    seam = marked_lines(spike_js, "fragment-seam")
    filters = marked_lines(spike_js, "filters-a")
    print(f"spike JavaScript, all experiments: {everything} non-blank lines")
    print(f"spike JavaScript without the R3 and server-filter experiments: {chosen} non-blank lines")
    print(f"  of which the fragment seam (fetch, check, install, paint, focus): {seam}")
    print(f"  of which browser-owned filtering for two filters: {filters}")
    print(f"  of which session, mutation and reconciliation that production already has: "
          f"{chosen - seam - filters}")
    print(f"spike context builder (Python): {code_lines(SPIKE_DIR / 'context.py')} non-blank lines")
    print(f"spike templates for the slice: {templates} non-blank lines")
    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT: " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
