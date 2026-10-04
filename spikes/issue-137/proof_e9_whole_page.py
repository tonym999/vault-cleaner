"""E9: what a full-document response after a mutation does.

``/spike/whole`` renders the report into the document itself and requests
the document again once a verdict is acknowledged.  The proof records what
happens to focus, scroll position, the live regions and unsent filter text,
and shows that the CSP's ``form-action 'none'`` blocks a script-free post.

    .venv/bin/python spikes/issue-137/proof_e9_whole_page.py
"""

from __future__ import annotations

from harness import (
    authenticated_context,
    chromium,
    csp_events,
    finish,
    live_spike,
    main_guard,
    upload,
    watch,
)

KEY = "columns:exact_duplicate:6032:approve"
STATE_JS = """
() => {
  var active = document.activeElement;
  return {
    activeTag: active ? active.nodeName.toLowerCase() : null,
    activeKey: active && active.getAttribute ? active.getAttribute("data-vc-key") : null,
    scrollY: Math.round(window.scrollY),
    search: document.getElementById("vc-dup-search").value,
    status: document.getElementById("vc-status").textContent,
    markerSurvived: window.__marker === true,
    statusNodeSurvived: document.getElementById("vc-status") === window.__statusNode
  };
}
"""


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live, 1440, 500)
        seen = watch(context)
        upload(context, live, "armor_close.csv")
        page = context.new_page()
        page.goto(f"{live.origin}/spike/whole", wait_until="load")
        page.locator("#vc-dup-search").fill("unsent filter text")
        page.evaluate(
            "() => { window.__marker = true; window.__statusNode = document.getElementById('vc-status'); }"
        )
        target = page.locator(f'[data-vc-key="{KEY}"]')
        target.focus()
        before = page.evaluate(STATE_JS)
        print(f"before the verdict: focus on {before['activeKey']!r}; scrollY={before['scrollY']}; "
              f"filter text={before['search']!r}; status={before['status']!r}")

        with page.expect_navigation(wait_until="load"):
            page.keyboard.press("Enter")
        after = page.evaluate(STATE_JS)
        pressed = target.get_attribute("aria-pressed")
        print(f"server verdicts: {live.session.verdicts}; rendered aria-pressed on the new document: {pressed}")
        print(f"after the reload: active element={after['activeTag']} key={after['activeKey']!r}")
        print(f"after the reload: scrollY={after['scrollY']}")
        print(f"after the reload: filter text={after['search']!r}")
        print(f"after the reload: status={after['status']!r}")
        print(f"after the reload: the old document's objects survived={after['markerSurvived']}; "
              f"#vc-status is the node that was there before={after['statusNodeSurvived']}")
        page.keyboard.press("Tab")
        first_stop = page.evaluate(
            "() => document.activeElement.id || document.activeElement.nodeName.toLowerCase()"
        )
        print(f"after the reload: the next Tab lands on {first_stop!r}")
        if after["activeKey"] == KEY or after["statusNodeSurvived"]:
            failures.append("the measurement did not observe a new document")
        if pressed != "true":
            failures.append("the reloaded document does not show the acknowledged verdict")

        print("-- script-free form post --")
        revision = live.session.verdict_revision
        url = page.url
        page.locator("#vc-form-submit").click(no_wait_after=True)
        page.wait_for_timeout(500)
        events = csp_events(page)
        print(f"submitting <form method=post action=/api/verdicts>: CSP violation events={events}; "
              f"navigated={page.url != url}; server verdict_revision before={revision} "
              f"after={live.session.verdict_revision}")
        print(f"CSP console messages: {len(seen['csp_console'])}")
        if events != ["form-action"] or live.session.verdict_revision != revision:
            failures.append("the form post was not blocked by form-action")

        print("-- bytes per acknowledged verdict --")
        whole = context.request.get(f"{live.origin}/spike/whole")
        fragment = context.request.get(f"{live.origin}/spike/fragments/armor-duplicates")
        report = context.request.get(f"{live.origin}/api/report")
        print(f"whole document: {len(whole.body())}; fragment: {len(fragment.body())}; "
              f"JSON envelope: {len(report.body())}")
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
