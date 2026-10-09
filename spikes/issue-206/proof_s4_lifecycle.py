"""S4: finalise, reset and disconnect (gate H3).

``POST /api/finalize`` sets ``state`` and ``override_status`` and moves
neither revision, so nothing keyed on the revision pair can notice it.  The
proof finalises with a veto in place, from the already-open page and then
from outside it, and checks the open page reaches the frozen state and the
persisted-veto notice without a reload.  It compares that with the production
page loaded fresh.  Then a reset, a new upload, and filtering with the server
stopped.

    .venv/bin/python spikes/issue-206/proof_s4_lifecycle.py
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
    open_production_duplicates,
    open_slice,
    read_slice,
    reload_report,
    report,
    status,
    upload,
    verdict_button,
    wait_status,
)

VETOED = "6032"
PRODUCTION_JS = """
() => {
  const cell = document.querySelector("#vc-duplicate-list [data-member-id='exact_duplicate:6032']");
  return {
    verdict: cell.querySelector(".verdict-presentation").textContent,
    disabled: Array.from(cell.querySelectorAll("button")).map((b) => b.disabled),
    note: document.getElementById("vc-session-note").textContent,
  };
}
"""


def pair(envelope: dict) -> tuple[int, int, str]:
    return envelope["report_revision"], envelope["verdict_revision"], envelope["fingerprint"]


def frozen_summary(page: Any) -> dict:
    shown = read_slice(page)
    return {
        "session": shown["session"]["text"],
        VETOED: member(page, VETOED),
        "all verdict controls disabled": all(
            button["disabled"] for group in shown["groups"] for row in group["members"]
            for button in row["buttons"]
        ),
        "download link": page.locator("a[href='/api/finalized.csv']").count(),
    }


def main() -> int:
    failures: list[str] = []
    with chromium() as browser:
        print("-- finalise from the open page, with a veto in place --")
        with live_spike() as live:
            context = authenticated_context(browser, live)
            upload(context, live, "armor_close.csv")
            page = open_slice(context, live)
            verdict_button(page, VETOED, "Veto").click()
            wait_status(page, "recorded your veto")
            before = report(context, live)
            print(f"before: state={before['state']}, revisions={pair(before)[:2]}, "
                  f"override_status={before['override_status']}")
            print(f"page before: {member(page, VETOED)}")
            requests: list[str] = []
            page.on("request", lambda request: requests.append(f"{request.method} {request.url.split('/', 3)[3]}"))
            page.get_by_role("button", name="Finalise review").click()
            wait_status(page, "Finalised")
            after = report(context, live)
            print(f"after:  state={after['state']}, revisions={pair(after)[:2]}, "
                  f"active persisted vetoes={[e['id'] for e in after['override_status'] if e['status'] == 'active']}")
            print(f"revision pair and fingerprint unchanged by the finalise: {pair(before) == pair(after)}")
            print(f"requests the page made: {requests}; page navigations or reloads: 0")
            summary = frozen_summary(page)
            print(f"open page now: {summary}")
            problems = compare(read_slice(page), after, frozen=True)
            print(f"differences between the open page and the finalised envelope: {len(problems)}")
            if (
                pair(before) != pair(after)
                or problems
                or not summary[VETOED]["persisted_veto"]
                or not summary["all verdict controls disabled"]
                or "Finalised" not in summary["session"]
                or summary["download link"] != 1
            ):
                failures.append("the open page did not reach the finalised presentation")
                failures.extend(problems[:3])

            production = open_production_duplicates(context, live)
            theirs = production.evaluate(PRODUCTION_JS)
            print(f"production, loaded fresh: {theirs}")
            same_meaning = (
                "persisted veto still suppresses" in theirs["verdict"]
                and theirs["verdict"].startswith("Vetoed")
                and all(theirs["disabled"])
                and "frozen" in theirs["note"]
            )
            print(f"same meaning as production (vetoed, a persisted veto still suppresses it, "
                  f"controls off, frozen): {same_meaning}")
            if not same_meaning:
                failures.append("production's fresh page means something else")
            production.close()

            print("-- reset, then a new upload --")
            page.get_by_role("button", name="Reset session").click()
            wait_status(page, "reset")
            shown = read_slice(page)
            idle = report(context, live)
            print(f"after reset: server state={idle['state']}, report_revision={idle['report_revision']}; "
                  f"page groups={len(shown['groups'])}, empty state={shown['empty']}, "
                  f"session note={shown['session']['text']!r}")
            if idle["state"] != "idle" or shown["groups"] or shown["empty"] != ["no-report"]:
                failures.append("the page did not show the reset session")
            upload(context, live, "armor_close.csv")
            reload_report(page)
            again = report(context, live)
            problems = compare(read_slice(page), again)
            print(f"after a new upload and Reload: state={again['state']}, {member(page, VETOED)}")
            print(f"the veto saved by the finalise is still reported and shown: "
                  f"{member(page, VETOED)['persisted_veto']}; differences from the envelope: {len(problems)}")
            if problems or not member(page, VETOED)["persisted_veto"]:
                failures.append("the page after reset and upload differs from the envelope")
            context.close()

        print("-- finalise from outside the already-open page --")
        with live_spike() as live:
            context = authenticated_context(browser, live)
            upload(context, live, "armor_close.csv")
            page = open_slice(context, live)
            verdict_button(page, VETOED, "Veto").click()
            wait_status(page, "recorded your veto")
            current = report(context, live)
            outside = api_post(context, live, "/api/finalize", {
                "report_revision": current["report_revision"],
                "verdict_revision": current["verdict_revision"],
                "fingerprint": current["fingerprint"],
            })
            print(f"finalise posted outside the page: HTTP {outside.status}; "
                  f"revisions unchanged={pair(report(context, live)) == pair(current)}")
            print(f"open page, before it makes any request: {member(page, VETOED)}")
            posts: list[str] = []
            page.on("request", lambda request: posts.append(request.url.rsplit("/", 1)[-1])
                    if request.method == "POST" else None)
            verdict_button(page, "6081", "Approve").click()
            wait_status(page, "not applied")
            print(f"status: {status(page)!r}")
            print(f"POSTs sent by the page: {posts}; server verdicts={live.session.verdicts}")
            summary = frozen_summary(page)
            print(f"open page now: {summary}")
            problems = compare(read_slice(page), report(context, live), frozen=True)
            if problems or posts != ["verdicts"] or not summary[VETOED]["persisted_veto"]:
                failures.append("the open page did not reconcile a finalise made elsewhere")
            reloaded = open_slice(context, live)
            print(f"a fresh load shows the same: {frozen_summary(reloaded) == summary}")
            if frozen_summary(reloaded) != summary:
                failures.append("the open page and a fresh load differ after a finalise")
            context.close()

        print("-- the server stops --")
        with live_spike() as live:
            context = authenticated_context(browser, live)
            upload(context, live, "armor_close.csv")
            page = open_slice(context, live)
            live.server.shutdown()
            live.server.server_close()
            page.locator("[data-kind-filter=same_stat]").click()
            shown = read_slice(page)
            print(f"filter with the server stopped: groups={[g['key'] for g in shown['groups']]}; "
                  f"scope={shown['scope']!r}")
            if [g["key"] for g in shown["groups"]] != ["same_stat:6081"]:
                failures.append("filtering needs the server")
            verdict_button(page, "6081", "Approve").click()
            wait_status(page, "did not answer")
            print(f"a verdict with the server stopped: status={status(page)!r}")
            print(f"nothing shown as applied, controls off: {member(page, '6081')}; "
                  f"connection={read_slice(page)['connection']}")
            if member(page, "6081")["pressed"] != ["Unset"] or not all(member(page, "6081")["disabled"]):
                failures.append("a verdict was shown without an acknowledgement")
            page.locator("[data-kind-filter=exact]").click()
            shown = read_slice(page)
            print(f"filter again while disconnected: groups={[g['key'] for g in shown['groups']]}; "
                  f"scope={shown['scope']!r}")
            if [g["key"] for g in shown["groups"]] != ["exact:6031"]:
                failures.append("filtering stopped working after the disconnect")
            context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
