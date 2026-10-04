"""S1: information parity (gate H1).

For each of the four fake fixtures, without and then with verdicts, the
proof computes what must be shown from the server's envelope (``expected.py``,
which shares no code with the frontend) and compares it with what the page
shows, at 1440 px and at 390 px, with no interaction.  It then compares the
scope sentence and the Class options with the production page for the filter
sequences of #137's E10, and ends with a negative control.

    .venv/bin/python spikes/issue-206/proof_s1_parity.py
"""

from __future__ import annotations

from typing import Any

from expected import compare, expected_groups
from harness import (
    SLICE_FIXTURES,
    api_post,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_production_duplicates,
    open_slice,
    read_slice,
    reload_report,
    report,
    two_class_fixture,
    upload,
    upload_bytes,
)

WIDTHS = (1440, 390)
# #137 E10's cases.  The last two select a class and then a kind that has no
# group of that class: production recounts the options and drops the class.
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
PRODUCTION_JS = """
() => {
  const visible = (node) => node.getClientRects().length > 0;
  const select = document.getElementById("vc-dup-f-guardianClass");
  return {
    groups: Array.from(document.querySelectorAll("#vc-duplicate-list article.armor-group"))
      .filter(visible).map((a) => a.getAttribute("data-group-id")),
    scope: document.getElementById("vc-duplicate-scope").textContent,
    options: Array.from(select.options).map((o) => o.value + "=" + o.textContent),
    selected: select.value,
    reconciliation: document.getElementById("vc-reconciliation").textContent.trim(),
  };
}
"""


def all_proposal_verdicts(envelope: dict) -> list[dict]:
    """Alternate veto and approve over every proposal a duplicate group shows."""
    ids = [
        member["id"]
        for group in expected_groups(envelope)
        for member in group["members"]
        if member["controls"]
    ]
    return [
        {"id": item_id, "verdict": "vetoed" if index % 2 == 0 else "approved"}
        for index, item_id in enumerate(ids)
    ]


def check(page: Any, envelope: dict, label: str, failures: list[str]) -> None:
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 900})
        shown = read_slice(page)
        problems = compare(shown, envelope)
        sideways = page.evaluate(
            "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
        )
        differing = sum(
            len(member["differing"]) for group in expected_groups(envelope) for member in group["members"]
        )
        print(f"{label} at {width}px: {len(shown['groups'])} groups, "
              f"{sum(len(g['members']) for g in shown['groups'])} members, "
              f"{differing} differing member values all visible={not problems}, "
              f"page scrolls sideways={sideways}, differences={len(problems)}")
        failures.extend(f"{label} at {width}px: {problem}" for problem in problems)
        if sideways:
            failures.append(f"{label} at {width}px: the page scrolls sideways")


def apply_slice(page: Any, steps: tuple) -> None:
    page.locator("button", has_text="Reset filters").first.click()
    for kind, value in steps:
        if kind == "kind":
            page.locator(f"[data-kind-filter={value}]").click()
        else:
            page.locator("select[data-facet=guardian_class]").select_option(value)


def apply_production(page: Any, steps: tuple) -> None:
    for kind, value in (("class", ""), ("kind", "all"), *steps):
        if kind == "kind":
            page.locator(f"#vc-dup-kind-{value}").click()
        else:
            page.locator("#vc-dup-f-guardianClass").select_option(value)


def main() -> int:
    failures: list[str] = []
    with chromium() as browser:
        print("-- every required value, for four fixtures, without and with verdicts --")
        for fixture in SLICE_FIXTURES:
            with live_spike() as live:
                context = authenticated_context(browser, live)
                envelope = upload(context, live, fixture)
                page = open_slice(context, live)
                check(page, envelope, f"{fixture} unreviewed", failures)
                decisions = all_proposal_verdicts(envelope)
                answer = api_post(context, live, "/api/verdicts", {
                    "report_revision": envelope["report_revision"],
                    "verdict_revision": envelope["verdict_revision"],
                    "fingerprint": envelope["fingerprint"],
                    "decisions": decisions,
                })
                reload_report(page)
                check(page, answer.json(), f"{fixture} with {len(decisions)} verdicts", failures)
                context.close()

        with live_spike() as live:
            context = authenticated_context(browser, live)
            envelope = upload_bytes(context, live, two_class_fixture())
            production = open_production_duplicates(context, live)
            page = open_slice(context, live)

            print("-- filters: the slice beside the production page, same session --")
            for steps in CASES:
                label = ", then ".join(f"{kind}={value}" for kind, value in steps) or "no filter"
                apply_slice(page, steps)
                apply_production(production, steps)
                shown = read_slice(page)
                theirs = production.evaluate(PRODUCTION_JS)
                mine = {
                    "groups": [group["key"].replace("exact:", "exact_duplicate:") for group in shown["groups"]],
                    "scope": shown["scope"],
                    "options": shown["facets"]["guardian_class"]["options"],
                    "selected": shown["facets"]["guardian_class"]["selected"],
                }
                same = all(mine[key] == theirs[key] for key in mine)
                print(f"{label}: equal to production={same}; groups={mine['groups']}")
                print(f"  scope: {mine['scope']}")
                print(f"  Class options: {mine['options']}; selected={mine['selected']!r}")
                if not same:
                    failures.append(f"{label}: differs from production: {mine} / {theirs}")
            dropped = read_slice(page)["reconciliation"]
            theirs = production.evaluate(PRODUCTION_JS)["reconciliation"]
            print(f"after the dropped class, the slice says: {dropped!r}")
            print(f"after the dropped class, production says: {theirs!r}")
            if "Hunter" not in dropped or "Hunter" not in theirs:
                failures.append("the dropped class was not reported by both pages")

            print("-- negative control: remove one required value from the rendered page --")
            apply_slice(page, ())
            current = report(context, live)
            before = compare(read_slice(page), current)
            page.evaluate(
                "() => document.querySelector(\"[data-member='6032'] [data-field=masterwork_tier]\").remove()"
            )
            after = compare(read_slice(page), current)
            print(f"differences before removal: {len(before)}; after removal: {after}")
            if before or len(after) != 1 or "masterwork_tier" not in after[0]:
                failures.append("the negative control did not fail in the expected way")
            page.evaluate(
                "() => { document.querySelector(\"[data-member='6081'] [data-field=verdict]\")"
                ".textContent = 'Approved'; }"
            )
            wrong = compare(read_slice(page), current)
            print(f"after a verdict text was changed in the page: {wrong[1:]}")
            if len(wrong) != 2:
                failures.append("a wrong verdict text was not detected")
            context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
