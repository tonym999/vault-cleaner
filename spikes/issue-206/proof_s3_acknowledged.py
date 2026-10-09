"""S3: acknowledged state only, and no replay (gate H3).

Approve, Veto and Unset go through the unmodified ``POST /api/verdicts``.
The first response is held in the browser after the server has committed:
the page must still show the old verdict.  Then two stale cases, each made by
changing the session from outside the page: a verdict from another client
(``stale_verdicts``) and a new export (``stale_report``).  The refused action
must not be sent again.

    .venv/bin/python spikes/issue-206/proof_s3_acknowledged.py
"""

from __future__ import annotations

from typing import Any

from expected import compare
from harness import (
    api_post,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    member,
    open_slice,
    read_slice,
    report,
    status,
    upload,
    verdict_button,
    wait_status,
)

EXACT = "6032"
SAME_STAT = "6081"


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        upload(context, live, "armor_close.csv")
        page = open_slice(context, live)

        print("-- the response is held after the server has committed --")
        print(f"before: {member(page, EXACT)}")
        held: list[tuple[Any, Any]] = []

        def hold_first(route: Any) -> None:
            if held:
                route.continue_()
                return
            held.append((route, route.fetch()))

        page.route("**/api/verdicts", hold_first)
        before_status = status(page)
        verdict_button(page, EXACT, "Approve").click()
        while not held:
            page.wait_for_timeout(20)
        page.wait_for_timeout(300)
        during = member(page, EXACT)
        print(f"server while held: verdict_revision={live.session.verdict_revision}, "
              f"verdicts={live.session.verdicts}")
        print(f"page while held:   {during}")
        print(f"status unchanged while held: {status(page) == before_status}")
        if (
            live.session.verdict_revision != 1
            or during["verdict"] != "Unreviewed"
            or during["pressed"] != ["Unset"]
            or during["disabled"] != [True, True, True]
            or status(page) != before_status
        ):
            failures.append("the page changed before the acknowledgement")
        route, response = held[0]
        route.fulfill(response=response)
        wait_status(page, "recorded your approval")
        print(f"after release:     {member(page, EXACT)}; status={status(page)!r}")
        if member(page, EXACT)["pressed"] != ["Approve"]:
            failures.append("the approval was not shown after the acknowledgement")

        for label, word, verdict in (("Veto", "veto", "Vetoed"), ("Unset", "unset", "Unreviewed")):
            verdict_button(page, EXACT, label).click()
            wait_status(page, f"recorded your {word}")
            shown = member(page, EXACT)
            print(f"after {label}: {shown}; server verdicts={live.session.verdicts}")
            if shown["verdict"] != verdict or shown["pressed"] != [label]:
                failures.append(f"{label} was not shown after its acknowledgement")
        if compare(read_slice(page), report(context, live)):
            failures.append("the page and the server disagree after three verdicts")

        print("-- stale_verdicts: another client changes a verdict --")
        current = report(context, live)
        api_post(context, live, "/api/verdicts", {
            "report_revision": current["report_revision"],
            "verdict_revision": current["verdict_revision"],
            "fingerprint": current["fingerprint"],
            "decisions": [{"id": SAME_STAT, "verdict": "approved"}],
        })
        revision = live.session.verdict_revision
        posts: list[str] = []
        page.on("request", lambda request: posts.append(request.url.rsplit("/", 1)[-1])
                if request.method == "POST" else None)
        verdict_button(page, EXACT, "Veto").click()
        wait_status(page, "not applied")
        page.wait_for_timeout(300)
        print(f"status: {status(page)!r}")
        print(f"the page's own action is not shown: {member(page, EXACT)}")
        print(f"the other client's verdict is shown:  {member(page, SAME_STAT)}")
        print(f"verdict POSTs sent by the page: {posts}; server verdict_revision "
              f"before={revision} after={live.session.verdict_revision}; verdicts={live.session.verdicts}")
        if (
            posts != ["verdicts"]
            or live.session.verdict_revision != revision
            or member(page, EXACT)["pressed"] != ["Unset"]
            or member(page, SAME_STAT)["pressed"] != ["Approve"]
        ):
            failures.append("stale_verdicts was not reconciled without a replay")
        if member(page, EXACT)["disabled"] != [False, False, False]:
            failures.append("controls stayed disabled after reconciliation")

        print("-- stale_report: a new export is uploaded elsewhere --")
        upload(context, live, "armor_duplicates_ui.csv")
        revision = live.session.verdict_revision
        posts.clear()
        verdict_button(page, EXACT, "Approve").click()
        wait_status(page, "not applied")
        page.wait_for_timeout(300)
        shown = read_slice(page)
        print(f"status: {status(page)!r}")
        print(f"groups now shown: {[group['key'] for group in shown['groups']]}; scope: {shown['scope']}")
        print(f"verdict POSTs sent by the page: {posts}; server verdict_revision "
              f"before={revision} after={live.session.verdict_revision}; verdicts={live.session.verdicts}")
        problems = compare(shown, report(context, live))
        print(f"differences from the server's new report: {len(problems)}")
        if posts != ["verdicts"] or live.session.verdict_revision != revision or problems:
            failures.append("stale_report was not reconciled without a replay")
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
