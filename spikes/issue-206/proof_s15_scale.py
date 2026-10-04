"""S15: every group of the tracked sanitised armor fixture, at real scale.

    .venv/bin/python spikes/issue-206/proof_s15_scale.py
    .venv/bin/python spikes/issue-206/proof_s15_scale.py --screenshots

No overlay, no export outside the one tracked sanitised armor fixture. S1's
independent oracle compares all groups/members; S6's layout/keyboard checks
and S13's axe/contrast checks run on the whole document. Screenshots are full
page. Timings are five alternating runs of each page at 1440px/light in the
same authenticated session/report, with no filters. Production selects the
duplicates surface in-page immediately after its DOM is built, so no human
or Playwright dwell is timed; its Proposals and hidden matrix DOM still count.

Navigation starts at performance.timeOrigin. An observer timestamps when
ALL groups have laid-out boxes, then records the next animation frame. For
verdicts a test-only fetch wrapper timestamps completion of response.json()
BEFORE returning the decoded answer to application code. A MutationObserver
records the target button's acknowledged aria-pressed change, then the next
animation frame: DOM completion and frame opportunity, not physical display
scanout. The wrapper changes no response/body and adds no network request.
"""

from __future__ import annotations

import sys
from collections import Counter
from statistics import median
from typing import Any

from dev import preload
from expected import compare, expected_groups
from harness import (
    CSP_INIT_SCRIPT,
    REAL_FIXTURE,
    REPO,
    authenticated_context,
    chromium,
    csp_events,
    finish,
    fixture_path,
    live_spike,
    main_guard,
    open_production_duplicates,
    read_slice,
    report,
    verdict_button,
    wait_status,
)
from proof_s1_parity import CASES, PRODUCTION_JS, apply_production, apply_slice
from proof_s6_layout import LAYOUT_JS, SHOTS, tab_through
from proof_s13_axe import AXE
from proof_s13_axe import run as axe_check

EVIDENCE = REPO / "docs" / "evidence" / "issue-206"
RUNS = 5

# Test instrumentation only: installed before either page's scripts run.
TIMING_JS = r"""
window.__scale = {ready: null, frame: null, built: null, ack: null, repaint: null, repaintFrame: null};
const measure = window.__scale;
const isSlice = location.pathname === "/spike/";
const groupSelector = isSlice ? "article[data-group]" : "#vc-duplicate-list article.armor-group";
const observeReady = () => {
  if (measure.ready !== null) return;
  if (!isSlice) {
    const tab = document.getElementById("vc-view-duplicates");
    // Production builds this surface lazily; activate only its report-ready
    // control. Observe the connected document, never a detached fragment.
    if (tab && !tab.disabled && tab.getAttribute("aria-label") ===
        `Armor duplicates (${window.__scaleGroups} groups)` &&
        tab.getAttribute("aria-pressed") !== "true") tab.click();
  }
  const groups = Array.from(document.querySelectorAll(groupSelector));
  if (groups.length !== window.__scaleGroups) return;
  if (measure.built === null) measure.built = performance.now();
  if (!groups.every(node => node.getBoundingClientRect().width > 0)) return;
  measure.ready = performance.now();
  requestAnimationFrame(() => { measure.frame = performance.now(); });
};
new MutationObserver(observeReady).observe(document, {subtree: true, childList: true, attributes: true});
document.addEventListener("DOMContentLoaded", observeReady);
const realFetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  const response = await realFetch(...args);
  if (new URL(String(args[0]), location.href).pathname === "/api/verdicts") {
    const realJson = response.json.bind(response);
    response.json = async () => {
      const answer = await realJson();
      measure.ack = performance.now();
      return answer;
    };
  }
  return response;
};
undefined;
"""
ARM_REPAINT_JS = """
button => {
  const m = window.__scale;
  m.ack = m.repaint = m.repaintFrame = null;
  window.__scaleButton = button;
  window.__scaleScroll = scrollY;
  window.__scaleTop = button.getBoundingClientRect().top;
  const observer = new MutationObserver(() => {
    if (m.ack === null || button.getAttribute('aria-pressed') !== 'true') return;
    m.repaint = performance.now();
    observer.disconnect();
    requestAnimationFrame(() => { m.repaintFrame = performance.now(); });
  });
  observer.observe(button, {attributes: true, attributeFilter: ['aria-pressed']});
}
"""


def value_count(groups: list[dict]) -> int:
    """Number of required text/value/role assertions covered by S1's oracle."""
    total = 0
    for group in groups:
        total += 3 + len(group["facts"]) + 2 * len(group["stats"]) + len(group["shared"])
        for member in group["members"]:
            total += 3 + len(member["differing"])
            if member["proposal"] is not None:
                total += 3  # proposed action, reason, current verdict
    return total


def parity(page: Any, envelope: dict, label: str, failures: list[str]) -> None:
    groups = expected_groups(envelope)
    problems = compare(read_slice(page), envelope)
    print(f"{label}: groups={len(groups)}, members={sum(len(g['members']) for g in groups)}, "
          f"value/role assertions={value_count(groups)}, differences={len(problems)}")
    failures.extend(problems)


def filters(page: Any, production: Any, failures: list[str]) -> None:
    for width in (1440, 390):
        page.set_viewport_size({"width": width, "height": 900})
        production.set_viewport_size({"width": width, "height": 900})
        executed = unsupported = drops = 0
        for steps in CASES:
            apply_slice(page, ())
            apply_production(production, ())
            label = ", then ".join(f"{kind}={value}" for kind, value in steps) or "no filter"
            available = True
            for kind, value in steps:
                if kind == "kind":
                    page.locator(f"[data-kind-filter={value}]").click()
                    production.locator(f"#vc-dup-kind-{value}").click()
                else:
                    mine_options = page.locator("select[data-facet=guardian_class] option").evaluate_all(
                        "nodes => nodes.map(node => node.value)"
                    )
                    their_options = production.locator("#vc-dup-f-guardianClass option").evaluate_all(
                        "nodes => nodes.map(node => node.value)"
                    )
                    assert mine_options == their_options
                    if value not in mine_options:
                        print(f"{width}px {label}: NOT EXECUTABLE; {value} absent from both Class lists")
                        unsupported += 1
                        available = False
                        break
                    page.locator("select[data-facet=guardian_class]").select_option(value)
                    production.locator("#vc-dup-f-guardianClass").select_option(value)
            if not available:
                continue
            executed += 1
            shown = read_slice(page)
            theirs = production.evaluate(PRODUCTION_JS)
            mine = {
                "groups": [g["key"].replace("exact:", "exact_duplicate:") for g in shown["groups"]],
                "scope": shown["scope"],
                "options": shown["facets"]["guardian_class"]["options"],
                "selected": shown["facets"]["guardian_class"]["selected"],
            }
            equal = all(mine[key] == theirs[key] for key in mine)
            print(f"{width}px {label}: equal={equal}; groups={len(mine['groups'])}; "
                  f"scope={mine['scope']!r}; Class={mine['options']}; selected={mine['selected']!r}")
            if not equal:
                failures.append(f"filter parity differs at {width}px for {label}")
            if steps == (("class", "Hunter"), ("kind", "exact")):
                dropped = shown["reconciliation"]
                theirs_drop = theirs["reconciliation"]
                assert mine["selected"] == "" and "Hunter" in dropped and "Hunter" in theirs_drop
                drops += 1
                print(f"  dropped-class notices: slice={dropped!r}; production={theirs_drop!r}")
        print(f"{width}px E10 sequences: executed={executed}, unsupported={unsupported}; "
              f"real-upload Hunter-to-Exact drops={drops}")
        assert executed == len(CASES) and unsupported == 0 and drops == 1
    apply_slice(page, ())
    apply_production(production, ())


def far_member(groups: list[dict]) -> tuple[int, dict, dict]:
    for index in range(len(groups) - 1, -1, -1):
        group = groups[index]
        for member in reversed(group["members"]):
            if member["controls"]:
                return index, group, member
    raise AssertionError("no proposal member for the far-down verdict")


def timed_verdict(page: Any, button: Any) -> dict:
    button.scroll_into_view_if_needed()
    button.focus()
    button.evaluate(ARM_REPAINT_JS)
    with page.expect_response("**/api/verdicts") as response:
        page.keyboard.press("Enter")
    assert response.value.status == 200
    page.wait_for_function("() => window.__scale.repaintFrame !== null")
    return page.evaluate("""() => ({
      dom: __scale.repaint - __scale.ack,
      frame: __scale.repaintFrame - __scale.ack,
      same: document.activeElement === __scaleButton && __scaleButton.isConnected,
      jump: Math.abs(scrollY - __scaleScroll),
      viewportJump: Math.abs(__scaleButton.getBoundingClientRect().top - __scaleTop),
      scroll: __scaleScroll,
    })""")


def production_button(page: Any, group: dict, member: dict, action: str) -> Any:
    key = group["key"].replace("exact:", "exact_duplicate:")
    return page.locator(f'article[data-group-id="{key}"]') .locator(
        f'[data-member-id$=":{member["id"]}"] button.{action}:visible'
    )


def timings(context: Any, live: Any, groups: list[dict], failures: list[str]) -> None:
    context.add_init_script(f"window.__scaleGroups = {len(groups)};\n" + TIMING_JS)
    index, group, member = far_member(groups)
    measured: dict[str, list[dict]] = {"slice": [], "production": []}
    for run in range(RUNS):
        # Alternate which implementation runs first; fresh documents each time.
        order = ("slice", "production") if run % 2 == 0 else ("production", "slice")
        for name in order:
            page = context.new_page()
            page.goto(live.origin + ("/spike/" if name == "slice" else "/"), wait_until="domcontentloaded")
            page.wait_for_function("() => window.__scale.frame !== null")
            sample = page.evaluate("""() => ({
              navigation: __scale.ready, navigationFrame: __scale.frame,
              built: __scale.built, nodes: document.querySelectorAll('*').length,
            })""")
            shown = read_slice(page)["groups"] if name == "slice" else page.evaluate(PRODUCTION_JS)["groups"]
            keys = [g["key"] for g in shown] if name == "slice" else [
                key.replace("exact_duplicate:", "exact:") for key in shown
            ]
            assert keys == [g["key"] for g in groups]
            # Alternate target verdict after each mutation; every request changes state.
            current = {v["id"]: v["verdict"] for v in report(context, live)["verdicts"]}
            action = "Veto" if current.get(member["id"]) == "approved" else "Approve"
            button = verdict_button(page, member["id"], action) if name == "slice" else production_button(
                page, group, member, action.lower()
            )
            repaint = timed_verdict(page, button)
            sample.update(repaint)
            assert sample["dom"] >= 0 and sample["frame"] >= sample["dom"]
            if name == "slice" and (not sample["same"] or sample["viewportJump"] > 1):
                failures.append("real-scale verdict lost focus or jumped")
            measured[name].append(sample)
            print(f"timing run {run + 1} {name}: all groups={len(keys)}; "
                  f"navigation={sample['navigation']:.1f}ms, next frame={sample['navigationFrame']:.1f}ms; "
                  f"ack-to-DOM={sample['dom']:.1f}ms, next frame={sample['frame']:.1f}ms; "
                  f"DOM elements={sample['nodes']}")
            page.close()
    print(f"verdict target: group {index + 1}/{len(groups)}, chosen from the envelope")
    for name, samples in measured.items():
        medians = {key: median(s[key] for s in samples) for key in (
            "navigation", "navigationFrame", "dom", "frame", "nodes"
        )}
        print(f"{name} medians ({RUNS} runs): navigation={medians['navigation']:.1f}ms, "
              f"next frame={medians['navigationFrame']:.1f}ms; ack-to-DOM={medians['dom']:.1f}ms, "
              f"next frame={medians['frame']:.1f}ms; DOM elements={medians['nodes']}")


def main() -> int:
    write = sys.argv[1:] == ["--screenshots"]
    failures: list[str] = []
    assert fixture_path("real") == REAL_FIXTURE
    try:
        fixture_path("../armor.csv")
    except ValueError:
        pass
    else:
        raise AssertionError("command-line fixture path is not fixed")
    with live_spike() as live, chromium() as browser:
        # The SAME preload() is called by serve.py and dev.py.
        preload(live, "real")
        context = authenticated_context(browser, live)
        envelope = report(context, live)
        groups = expected_groups(envelope)
        counts = Counter(g["kind"] for g in groups)
        sizes = Counter(len(g["members"]) for g in groups if g["kind"] == "same_stat")
        print("fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay")
        print(f"report: exact={counts['exact']}, same-stat={counts['same_stat']}; "
              f"same-stat sizes={dict(sorted(sizes.items()))}; "
              f"members={sum(len(g['members']) for g in groups)}; "
              f"wire bytes={len(context.request.get(live.origin + '/api/report').body())}")
        assert counts == {"exact": 9, "same_stat": 65}
        assert sizes == {2: 57, 3: 6, 4: 2}
        assert all(m["id"].startswith("1000") for g in groups for m in g["members"])
        production = open_production_duplicates(context, live)
        # Watch only this page, before navigation, keeping production's
        # console separate from the slice's browser-error result.
        seen: dict[str, list[str]] = {"dialogs": [], "console": [], "errors": []}
        page = context.new_page()
        page.add_init_script(CSP_INIT_SCRIPT)
        page.on("console", lambda message: seen["console"].append(message.text)
                if message.type == "error" else None)
        page.on("pageerror", lambda error: seen["errors"].append(str(error)))

        def dialog_seen(dialog: Any) -> None:
            seen["dialogs"].append(dialog.message)
            dialog.dismiss()

        page.on("dialog", dialog_seen)
        page.goto(f"{live.origin}/spike/", wait_until="domcontentloaded")
        page.wait_for_selector("article[data-group]")
        for width in (1440, 390):
            page.set_viewport_size({"width": width, "height": 900})
            parity(page, envelope, f"unreviewed {width}px", failures)
        spirit = [g for g in groups if g["kind"] == "exact" and "spirit_signature" in g["shared"]]
        assert len(spirit) == 5
        shown = {g["key"]: g for g in read_slice(page)["groups"]}
        assert all(shown[g["key"]]["shared"]["spirit_signature"]["text"] == g["shared"]["spirit_signature"][0]
                   for g in spirit)
        print(f"spirit signatures from unmodified upload: {len(spirit)}/{len(spirit)} exact groups correct")
        filters(page, production, failures)
        index, _, member = far_member(groups)
        # Install only mutation timing on this already-open page.
        page.evaluate(TIMING_JS)
        focus = timed_verdict(page, verdict_button(page, member["id"], "Approve"))
        wait_status(page, "recorded your approval")
        print(f"far-down acknowledged verdict: group={index + 1}/{len(groups)}; "
              f"scroll before={focus['scroll']:.0f}px; same focused node={focus['same']}; "
              f"scroll change={focus['jump']:.0f}px; control viewport change={focus['viewportJump']:.0f}px")
        assert index >= len(groups) * 0.75
        if not focus["same"] or focus["viewportJump"] > 1:
            failures.append("far-down verdict lost focus or jumped")
        envelope = report(context, live)
        for width in (1440, 1024, 390):
            for scheme in ("light", "dark"):
                page.set_viewport_size({"width": width, "height": 900})
                page.emulate_media(color_scheme=scheme)
                layout = page.evaluate(LAYOUT_JS)
                parity(page, envelope, f"acknowledged {width}px {scheme}", failures)
                stops = tab_through(page)
                in_order = [s["order"] for s in stops] == list(range(len(stops)))
                good = (not layout["sideways"] and not layout["scrollers"] and layout["opaqueInside"]
                        and not layout["opaqueClipped"] and not layout["hiddenControls"]
                        and layout["memberColumns"] == 1 and len(stops) == layout["controls"]
                        and in_order and all(s["visible"] for s in stops))
                print(f"layout {width}px {scheme}: sideways={layout['sideways']}; "
                      f"internal sideways scrollers={layout['scrollers']}; opaque values inside="
                      f"{layout['opaqueInside']}, clipped={layout['opaqueClipped']}; "
                      f"member columns={layout['memberColumns']}; Tab={len(stops)}/{layout['controls']}, "
                      f"document order={in_order}, all visible={all(s['visible'] for s in stops)}")
                if not good:
                    failures.append(f"real layout {width}px {scheme}")
                if write and (width, scheme) in SHOTS:
                    page.evaluate("() => { document.activeElement.blur(); window.scrollTo(0, 0); }")
                    target = EVIDENCE / f"real-{SHOTS[width, scheme]}.png"
                    page.screenshot(path=str(target), full_page=True)
                    height = page.evaluate("() => document.documentElement.scrollHeight")
                    print(f"wrote {target.relative_to(REPO)}: full page {width}x{height}, all {len(groups)} groups")
        page.mouse.move(0, 0)
        page.evaluate((AXE / "axe.min.js").read_text(encoding="utf-8") + "\n;undefined")
        axe_check(page, "sanitised report, acknowledged verdict", failures)
        print(f"slice CSP violations: {csp_events(page)}; console/errors/dialogs: {seen}")
        if csp_events(page) or any(seen.values()):
            failures.append("slice browser error or CSP violation")
        page.close()
        production.close()
        timings(context, live, groups, failures)
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
