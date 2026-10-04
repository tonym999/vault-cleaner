"""E10: who should own filtering, measured on the group-kind selector and
the Class facet.

Candidate (a): the server renders every group and the browser hides the ones
that do not match, from ``data-*`` attributes the server wrote.
Candidate (b): the server filters, from validated query parameters, and the
browser installs the result.

The proof checks both against the production page for the same session:
the groups shown, the section headings, the scope sentence, the Class
control's options and selected value and, where a selection is dropped, the
reconciliation message.  The cases include the one where production recounts
the Class options for the selected kind and drops a class that kind lacks.
It then stops the server and tries each again, and counts the lines each
candidate keeps in JavaScript or adds to Python.

    .venv/bin/python spikes/issue-137/proof_e10_filters.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness import (
    FIXTURES,
    REPO,
    SPIKE_DIR,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_production_duplicates,
    open_spike,
    upload_bytes,
)

# Each case is a sequence of steps taken from a reset page.  The last case
# selects a class and then a kind that has no group of that class.
CASES = (
    (),
    (("kind", "exact"),),
    (("kind", "same_stat"),),
    (("class", "Titan"),),
    (("kind", "exact"), ("class", "Titan")),
    (("class", "Hunter"),),
    (("kind", "same_stat"), ("class", "Hunter")),
    (("class", "Titan"), ("kind", "same_stat")),
    (("class", "Hunter"), ("kind", "exact")),
)
UI = REPO / "src" / "vault_cleaner" / "ui"
# (file, first line, last line, the text its first line must contain)
PRODUCTION_FILTER_CODE = (
    ("review_ui.js", 747, 771, "function matchesArmorGroup"),
    ("review_ui.js", 773, 777, "function filterArmorGroups"),
    ("review_ui.js", 779, 802, "function countArmorGroups"),
    ("review_server.js", 221, 238, "function armorGroupValueStillExists"),
    ("review_server.js", 240, 252, "function armorGroupsForKind"),
    ("review_server.js", 254, 261, "function armorGroupKinds"),
    ("review_server.js", 263, 275, "function reconcileArmorQueryForGroups"),
    ("review_server.js", 277, 281, "function countGroupPieces"),
    ("review_server.js", 283, 310, "function duplicateScopeText"),
    ("review_server.js", 1284, 1296, "function duplicateOptions"),
)

VISIBLE_JS = """
() => {
  function visible(node) { return node.getClientRects().length > 0; }
  var list = document.getElementById("vc-duplicate-list");
  var panel = document.getElementById("vc-duplicates");
  return {
    groups: Array.prototype.filter.call(list.querySelectorAll("article.armor-group"), visible)
      .map(a => a.getAttribute("data-group-id")),
    headings: Array.prototype.filter.call(list.querySelectorAll(".armor-section-head h3"), visible)
      .map(h => h.textContent),
    scope: document.getElementById("vc-duplicate-scope").textContent,
    options: Array.prototype.map.call(
      document.getElementById("vc-dup-f-guardianClass").options, o => o.value + "=" + o.textContent),
    selected: document.getElementById("vc-dup-f-guardianClass").value,
    empty: Array.prototype.filter.call(panel.querySelectorAll("p.hint"), visible)
      .some(p => p.textContent === "No armor duplicate groups match these filters.")
  };
}
"""


def two_class_fixture() -> bytes:
    """``armor_close.csv`` with its same-stat pair re-classed, in memory."""
    lines = (FIXTURES / "armor_close.csv").read_bytes().split(b"\n")
    changed = [
        line.replace(b",Titan,", b",Hunter,", 1) if line.startswith(b"Tuning Twin,") else line
        for line in lines
    ]
    return b"\n".join(changed)


def apply(page: Any, steps: tuple, settle: bool) -> None:
    """Reset the two filters, then take each step as a user would."""
    for kind, value in (("class", ""), ("kind", "all"), *steps):
        if kind == "kind":
            page.locator(f"#vc-dup-kind-{value}").click()
        else:
            page.locator("#vc-dup-f-guardianClass").select_option(value)
        if settle:
            page.wait_for_timeout(150)


def reconciliation(page: Any) -> str:
    return page.locator("#vc-reconciliation").text_content().strip()


def marked_lines(path: Path, marker: str) -> int:
    """Lines between ``[marker:start]`` and ``[marker:end]``, exclusive."""
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
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        upload_bytes(context, live, two_class_fixture())
        production = open_production_duplicates(context, live)
        browser_owned = open_spike(context, live, "?filters=browser")
        server_owned = open_spike(context, live, "?filters=server")
        pages = (("production", production), ("(a) browser", browser_owned), ("(b) server", server_owned))

        print("-- the same filter in production, candidate (a) and candidate (b) --")
        for steps in CASES:
            label = ", then ".join(f"{kind}={value}" for kind, value in steps) or "no filter"
            results = {}
            for name, page in pages:
                apply(page, steps, settle=name == "(b) server")
                results[name] = page.evaluate(VISIBLE_JS)
            agree = results["production"] == results["(a) browser"] == results["(b) server"]
            shown = results["production"]
            print(f"{label}: all three agree={agree}; groups={shown['groups']}; "
                  f"headings={shown['headings']}")
            print(f"  scope: {shown['scope']}")
            print(f"  Class options: {shown['options']}; selected={shown['selected']!r}")
            if not agree:
                failures.append(f"{label}: the candidates disagree")
                for name, result in results.items():
                    print(f"  {name}: {result}")
        messages = {name: reconciliation(page) for name, page in pages}
        same = len(set(messages.values())) == 1
        print(f"reconciliation message after the dropped class: all three agree={same}; "
              f"{messages['production']!r}")
        if not same or "guardianClass Hunter" not in messages["production"]:
            failures.append("the dropped class was not reported alike")
            print(f"  {messages}")

        print("-- requests per filter change --")
        for name, page in pages[1:]:
            apply(page, (), settle=True)
            requests: list[str] = []
            page.on("request", lambda request, seen=requests: seen.append(request.url))
            page.locator("#vc-dup-kind-exact").click()
            page.wait_for_timeout(250)
            print(f"{name}: {len(requests)} request(s)")
            apply(page, (), settle=True)

        print("-- the same filter after the server has stopped --")
        apply(production, (), settle=False)
        live.server.shutdown()
        live.server.server_close()
        for name, page in pages:
            before = page.evaluate(VISIBLE_JS)
            page.locator("#vc-dup-kind-same_stat").click()
            page.wait_for_timeout(500)
            after = page.evaluate(VISIBLE_JS)
            worked = after["groups"] == ["same_stat:6081"] and "same-stat" in after["scope"]
            print(f"{name}: filter applied={worked}; groups shown before={len(before['groups'])} "
                  f"after={len(after['groups'])}; status={page.locator('#vc-status').inner_text()!r}")
            if name != "(b) server" and not worked:
                failures.append(f"{name}: the filter did not work offline")
            if name == "(b) server" and worked:
                failures.append("candidate (b) filtered without a server")
        context.close()

    print("-- line counts (non-blank lines between the experiment markers) --")
    a_js = marked_lines(SPIKE_DIR / "static" / "spike.js", "filters-a")
    b_js = marked_lines(SPIKE_DIR / "static" / "spike.js", "filters-b")
    b_py = marked_lines(SPIKE_DIR / "context.py", "filters-b") + marked_lines(
        SPIKE_DIR / "spike_app.py", "filters-b"
    )
    print(f"candidate (a): JavaScript {a_js}, Python 0")
    print(f"candidate (b): JavaScript {b_js}, Python {b_py}")

    print("-- production filter code this would replace --")
    total = 0
    for name, first, last, expected in PRODUCTION_FILTER_CODE:
        lines = (UI / name).read_text(encoding="utf-8").splitlines()
        found = expected in lines[first - 1]
        total += last - first + 1
        print(f"{name}:{first}-{last} ({last - first + 1} lines) {expected}: found at that line={found}")
        if not found:
            failures.append(f"{name}:{first} is not {expected}")
    print(f"total: {total} lines")
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
