"""E3 and E4: server-acknowledged state only; no stale fragment is installed.

E3 holds the response of the unmodified ``POST /api/verdicts`` after the
server has committed it, shows the rendered verdict state has not moved, then
releases the response.  It repeats for each repaint mechanism.

E4 forces ``stale_verdicts`` and ``stale_report`` and then serves fragments
and envelopes whose revisions disagree, in both directions.

    .venv/bin/python spikes/issue-137/proof_e3_e4_mutation.py
"""

from __future__ import annotations

from typing import Any

from harness import (
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_spike,
    upload,
)

EXACT_PROPOSAL = "6032"
SAME_STAT_PROPOSALS = ("6081", "6082")
FRAGMENT_GLOB = "**/spike/fragments/armor-duplicates*"

STATE_JS = """
() => Array.prototype.map.call(
  document.querySelectorAll("#vc-duplicate-list [data-vc-verdict-id]"),
  function (cell) {
    var text = cell.querySelector("[data-vc-verdict-text]");
    return {
      id: cell.getAttribute("data-vc-verdict-id"),
      pressed: Array.prototype.map.call(
        cell.querySelectorAll("button[data-vc-verdict-value]"),
        b => b.getAttribute("aria-pressed")).join(","),
      text: text ? text.textContent : null,
      disabled: Array.prototype.map.call(
        cell.querySelectorAll("button[data-vc-verdict-value]"), b => b.disabled)
    };
  })
"""


def verdict_state(page: Any) -> list[dict]:
    return page.evaluate(STATE_JS)


def summary(state: list[dict], member: str) -> str:
    cells = [cell for cell in state if cell["id"] == member]
    shapes = {f"approve,veto,unset pressed={cell['pressed']} text={cell['text']!r}" for cell in cells}
    return f"{len(cells)} cells, {' | '.join(sorted(shapes))}"


def without_disabled(state: list[dict]) -> list[dict]:
    return [{key: value for key, value in cell.items() if key != "disabled"} for cell in state]


def button(page: Any, member: str, css: str) -> Any:
    return page.locator(
        f'table.armor-matrix-columns td[data-vc-verdict-id="{member}"] button.{css}'
    )


def status(page: Any) -> str:
    return page.locator("#vc-status").inner_text()


def wait_status(page: Any, fragment: str) -> None:
    page.wait_for_function(
        "text => document.getElementById('vc-status').textContent.indexOf(text) !== -1", arg=fragment
    )


def reset_status(page: Any) -> None:
    page.evaluate("() => { document.getElementById('vc-status').textContent = ''; }")


def spike_log(page: Any) -> list[str]:
    return page.evaluate("() => window.VaultCleanerSpike.log.slice()")


def clear_log(page: Any) -> None:
    page.evaluate("() => { window.VaultCleanerSpike.log.length = 0; }")


def e3(browser: Any, mode: str, failures: list[str]) -> None:
    print(f"-- E3, repaint={mode} --")
    with live_spike() as live:
        context = authenticated_context(browser, live)
        upload(context, live, "armor_close.csv")
        page = open_spike(context, live, f"?repaint={mode}")
        before = verdict_state(page)
        print(f"before: {summary(before, EXACT_PROPOSAL)}")

        held: list[tuple[Any, Any]] = []

        def hold_first(route: Any) -> None:
            """Let the server answer, then keep the first response back."""
            if held:
                route.continue_()
                return
            held.append((route, route.fetch()))

        page.route("**/api/verdicts", hold_first)
        reset_status(page)
        button(page, EXACT_PROPOSAL, "approve").click()
        while not held:
            page.wait_for_timeout(20)
        page.wait_for_timeout(300)
        during = verdict_state(page)
        committed = live.session.verdict_revision
        print(f"response held; server verdict_revision={committed}, "
              f"server verdicts={live.session.verdicts}")
        unchanged = without_disabled(during) == without_disabled(before)
        gated = all(all(cell["disabled"]) for cell in during if cell["disabled"])
        print(f"while held: {summary(during, EXACT_PROPOSAL)}")
        print(f"while held: verdict state unchanged={unchanged}; every verdict button disabled={gated}; "
              f"status text={status(page)!r}")
        if committed != 1 or not unchanged or not gated:
            failures.append(f"{mode}: the DOM moved before the acknowledgement")

        route, response = held[0]
        route.fulfill(response=response)
        wait_status(page, "acknowledged")
        after = verdict_state(page)
        print(f"after release: {summary(after, EXACT_PROPOSAL)}; status={status(page)!r}")
        expected = {"true,false,false"}
        if {cell["pressed"] for cell in after if cell["id"] == EXACT_PROPOSAL} != expected:
            failures.append(f"{mode}: approve was not shown after the acknowledgement")

        for css, label, pressed in (("veto", "Veto", "false,true,false"), ("clear-verdict", "Clear", "false,false,true")):
            reset_status(page)
            button(page, EXACT_PROPOSAL, css).click()
            wait_status(page, f"{label} acknowledged")
            state = verdict_state(page)
            print(f"after {label}: {summary(state, EXACT_PROPOSAL)}; "
                  f"server verdicts={live.session.verdicts}")
            if {cell["pressed"] for cell in state if cell["id"] == EXACT_PROPOSAL} != {pressed}:
                failures.append(f"{mode}: {label} was not shown after the acknowledgement")
        print(f"fragment log: {spike_log(page)}")
        context.close()


def e4_stale(browser: Any, mode: str, failures: list[str]) -> None:
    print(f"-- E4 stale responses, repaint={mode} --")
    with live_spike() as live:
        context = authenticated_context(browser, live)
        upload(context, live, "armor_close.csv")
        tab_a = open_spike(context, live, f"?repaint={mode}")
        tab_b = open_spike(context, live, f"?repaint={mode}")

        reset_status(tab_b)
        button(tab_b, SAME_STAT_PROPOSALS[0], "approve").click()
        wait_status(tab_b, "acknowledged")
        revision = live.session.verdict_revision
        clear_log(tab_a)
        reset_status(tab_a)
        button(tab_a, EXACT_PROPOSAL, "veto").click()
        wait_status(tab_a, "not applied")
        state = verdict_state(tab_a)
        print(f"stale_verdicts: tab A status={status(tab_a)!r}")
        print(f"stale_verdicts: tab A shows tab B's verdict: {summary(state, SAME_STAT_PROPOSALS[0])}")
        print(f"stale_verdicts: tab A's own action not shown: {summary(state, EXACT_PROPOSAL)}")
        print(f"stale_verdicts: server verdict_revision before={revision} after={live.session.verdict_revision}; "
              f"server verdicts={live.session.verdicts}")
        print(f"stale_verdicts: fragment log: {spike_log(tab_a)}")
        if live.session.verdict_revision != revision:
            failures.append(f"{mode}: the stale action was replayed")
        if {c["pressed"] for c in state if c["id"] == SAME_STAT_PROPOSALS[0]} != {"true,false,false"}:
            failures.append(f"{mode}: reconciliation did not show the other client's verdict")
        if {c["pressed"] for c in state if c["id"] == EXACT_PROPOSAL} != {"false,false,true"}:
            failures.append(f"{mode}: the stale action was shown as applied")

        upload(context, live, "armor_duplicates_ui.csv")
        clear_log(tab_a)
        reset_status(tab_a)
        button(tab_a, EXACT_PROPOSAL, "approve").click()
        wait_status(tab_a, "not applied")
        groups = tab_a.evaluate(
            "() => Array.prototype.map.call(document.querySelectorAll('article.armor-group'),"
            " a => a.getAttribute('data-group-id'))"
        )
        old_cells = len([c for c in verdict_state(tab_a) if c["id"] == EXACT_PROPOSAL])
        print(f"stale_report: tab A status={status(tab_a)!r}")
        print(f"stale_report: groups now rendered={groups}; cells left for the old member={old_cells}")
        print(f"stale_report: server verdicts={live.session.verdicts}")
        print(f"stale_report: fragment log: {spike_log(tab_a)}")
        if groups != ["exact_duplicate:8201"] or old_cells:
            failures.append(f"{mode}: reconciliation did not install the new report")
        context.close()


def e4_fragments(browser: Any, failures: list[str]) -> None:
    print("-- E4 fragment and envelope revisions disagree --")
    with live_spike() as live:
        context = authenticated_context(browser, live)
        upload(context, live, "armor_close.csv")
        tab_a = open_spike(context, live)
        tab_b = open_spike(context, live)
        old_fragment = context.request.get(f"{live.origin}/spike/fragments/armor-duplicates")
        old_envelope = context.request.get(f"{live.origin}/api/report").text()
        marked = old_fragment.text().replace(
            '<div data-vc-part="list">', '<div data-vc-part="list"><p id="stale-marker">STALE</p>', 1
        )
        old_headers = {
            name: old_fragment.headers[name.lower()]
            for name in ("Vault-Cleaner-Report-Revision", "Vault-Cleaner-Verdict-Revision")
        }
        reset_status(tab_b)
        button(tab_b, SAME_STAT_PROPOSALS[0], "approve").click()
        wait_status(tab_b, "acknowledged")
        print(f"captured fragment headers={old_headers}; server now at report "
              f"{live.session.report_revision} verdict {live.session.verdict_revision}")

        def stale_fragment(route: Any) -> None:
            route.fulfill(
                status=200, content_type="text/html; charset=utf-8", headers=old_headers, body=marked
            )

        # A trailing fragment, served once.
        served = []

        def once(route: Any) -> None:
            if served:
                route.continue_()
                return
            served.append(True)
            stale_fragment(route)

        clear_log(tab_a)
        tab_a.route(FRAGMENT_GLOB, once)
        tab_a.evaluate("() => window.VaultCleanerSpike.refresh()")
        tab_a.unroute(FRAGMENT_GLOB)
        markers = tab_a.locator("#stale-marker").count()
        state = verdict_state(tab_a)
        print(f"trailing fragment: log={spike_log(tab_a)}")
        print(f"trailing fragment: stale markers installed={markers}; "
              f"{summary(state, SAME_STAT_PROPOSALS[0])}")
        if markers or "fragment discarded" not in " ".join(spike_log(tab_a)):
            failures.append("a trailing fragment was installed")

        # A leading fragment: the browser adopts an old envelope, the server has moved on.
        envelopes = []

        def old_report_once(route: Any) -> None:
            if envelopes:
                route.continue_()
                return
            envelopes.append(True)
            route.fulfill(status=200, content_type="application/json", body=old_envelope)

        clear_log(tab_a)
        tab_a.route("**/api/report", old_report_once)
        tab_a.evaluate("() => window.VaultCleanerSpike.refresh()")
        tab_a.unroute("**/api/report")
        print(f"leading fragment: log={spike_log(tab_a)}")
        print(f"leading fragment: {summary(verdict_state(tab_a), SAME_STAT_PROPOSALS[0])}")
        if "fragment discarded" not in " ".join(spike_log(tab_a)):
            failures.append("a fragment newer than the adopted envelope was installed")

        # A fragment that never matches: the browser gives up and keeps what it has.
        clear_log(tab_a)
        tab_a.route(FRAGMENT_GLOB, stale_fragment)
        outcome = tab_a.evaluate(
            "() => window.VaultCleanerSpike.refresh().then(() => 'installed', e => 'refused: ' + e.message)"
        )
        tab_a.unroute(FRAGMENT_GLOB)
        markers = tab_a.locator("#stale-marker").count()
        print(f"never-matching fragment: outcome={outcome!r}; discards={len(spike_log(tab_a))}; "
              f"stale markers installed={markers}; groups still rendered="
              f"{tab_a.locator('article.armor-group').count()}")
        if markers or not outcome.startswith("refused"):
            failures.append("a never-matching fragment was installed")
        context.close()


def main() -> int:
    failures: list[str] = []
    with chromium() as browser:
        for mode in ("r1", "r2", "r3"):
            e3(browser, mode, failures)
        for mode in ("r1", "r2", "r3"):
            e4_stale(browser, mode, failures)
        e4_fragments(browser, failures)
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
