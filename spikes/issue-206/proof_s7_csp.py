"""S7: the Content-Security-Policy (gate H7).

Part 1 runs the whole slice under production's **unchanged** policy and
exercises every component it has: both filters, the verdict buttons, the
session actions, the reconciliation notice and each empty state.  It records
every violation, every request the page made, and checks that styles really
applied (a blocked style is silent, so "no violation" alone is not enough).

Part 2 loads one probe page per shortlisted library, and plain Svelte 5,
under the unchanged policy: a button, a toggle, a select and an overlay.  For
any that violates it, the proof then tries the owner's pre-approved additions
one at a time and reports the fewest that clear it.

    .venv/bin/python spikes/issue-206/proof_s7_csp.py

Needs both builds: ``npm ci && npm run build`` in ``frontend/`` and in
``probes/``.
"""

from __future__ import annotations

import re
from collections import Counter
from itertools import combinations
from typing import Any

from harness import (
    authenticated_context,
    chromium,
    csp_events,
    finish,
    live_spike,
    main_guard,
    two_class_fixture,
    upload_bytes,
    verdict_button,
    wait_status,
    watch,
)
from spike_app import APPROVED_ADDITIONS, PROBES_DIST, SLICE_CSP_ADDITIONS, policy_with

from vault_cleaner.server.app import SERVER_CSP

PROBES = (
    ("plain", "plain Svelte 5, no library"),
    ("shadcn", "shadcn-svelte 1.7.0 on Bits UI 2.19.5"),
    ("skeleton", "Skeleton 5.0.1 (Zag.js)"),
    ("daisy", "daisyUI 5.7.47 (CSS only)"),
)
PROBE_JS = """
() => {
  const style = (selector, property) => {
    const node = document.querySelector(selector);
    return node ? getComputedStyle(node)[property] : null;
  };
  const overlay = document.querySelector("[data-probe=overlay]");
  const box = overlay ? overlay.getBoundingClientRect() : null;
  return {
    buttonStyled: style("[data-probe=button]", "paddingLeft") !== "0px" ||
      style("[data-probe=button]", "borderTopWidth") !== "0px",
    overlayVisible: !!box && box.width > 0 && box.height > 0,
    directiveWidth: style("[data-probe=style-directive]", "width"),
    attributeWidth: style("[data-probe=style-attribute]", "width"),
    spreadOutline: style("[data-probe=style-spread]", "outlineStyle"),
    styleElements: document.querySelectorAll("style").length,
    styleAttributes: document.querySelectorAll("[style]").length,
    parent: document.querySelector("[data-probe=style-directive]")
      ? document.querySelector("[data-probe=style-directive]").parentElement.getBoundingClientRect().width : 0,
  };
}
"""


def exercise_probe(page: Any, origin: str, name: str) -> dict:
    page.goto(f"{origin}/spike/probes/{name}.html", wait_until="domcontentloaded")
    page.wait_for_selector("[data-probe=button]")
    page.locator("[data-probe=button]").click()
    page.locator("[data-probe=toggle]").click()
    select = page.locator("[data-probe=select]")
    custom_select = select.evaluate("node => node.tagName") != "SELECT"
    if custom_select:
        select.click()
        page.locator("[data-probe=select-option]").click()
    else:
        select.select_option("b")
    page.wait_for_timeout(300)
    page.locator("[data-probe=overlay-open]").click()
    page.wait_for_timeout(400)
    result = page.evaluate(PROBE_JS)
    result["customSelect"] = custom_select
    result["violations"] = dict(Counter(re.sub(r" from .*", "", event) for event in csp_events(page)))
    return result


DATA_URI = re.compile(r"""url\(["']?data:""")
REMOTE_URL = re.compile(r"""url\(["']?https?:""")


def probe_assets(name: str) -> str:
    css = (PROBES_DIST / "assets" / f"{name}.css").read_text(encoding="utf-8")
    js = (PROBES_DIST / "assets" / f"{name}.js").read_text(encoding="utf-8")
    return (f"css {len(css.encode())} bytes, js {len(js.encode())} bytes (shared chunks excluded); "
            f"data: URIs in css {len(DATA_URI.findall(css))}; @font-face {css.count('@font-face')}; "
            f"remote url() {len(REMOTE_URL.findall(css))}")


def main() -> int:
    failures: list[str] = []
    print(f"production policy: {SERVER_CSP}")
    print(f"additions the slice is served with: {list(SLICE_CSP_ADDITIONS)}")
    with chromium() as browser:
        print("-- part 1: the whole slice under the unchanged policy --")
        with live_spike(csp_additions=()) as live:
            context = authenticated_context(browser, live)
            seen = watch(context)
            upload_bytes(context, live, two_class_fixture())
            requests: list[str] = []
            headers: dict[str, str] = {}
            page = context.new_page()
            page.on("request", lambda request: requests.append(
                f"{request.resource_type} {request.method} {request.url.split('/', 3)[3]}"))
            page.on("response", lambda response: headers.setdefault(
                response.url.split("/", 3)[3], response.headers.get("content-security-policy", "")))
            page.goto(f"{live.origin}/spike/", wait_until="domcontentloaded")
            page.wait_for_selector("article[data-group]")
            steps = []
            page.locator("select[data-facet=guardian_class]").select_option("Hunter"); steps.append("class facet")
            page.locator("[data-kind-filter=exact]").click(); steps.append("kind filter, dropping the class (reconciliation notice)")
            page.locator("select[data-facet=guardian_class]").select_option("Titan")
            page.locator("[data-kind-filter=all]").click()
            page.locator("select[data-facet=guardian_class]").select_option("")
            for label, word in (("Approve", "approval"), ("Veto", "veto"), ("Unset", "unset"), ("Veto", "veto")):
                verdict_button(page, "6032", label).click()
                wait_status(page, f"recorded your {word}")
            steps.append("verdict buttons (approve, veto, unset)")
            page.keyboard.press("Tab"); steps.append("focus ring")
            page.get_by_role("button", name="Finalise review").click()
            wait_status(page, "Finalised"); steps.append("finalise (frozen controls, persisted-veto notice, download link)")
            page.get_by_role("button", name="Reset session").click()
            wait_status(page, "reset"); steps.append("reset (the no-report empty state)")
            page.get_by_role("button", name="Reload report").click(); steps.append("reload")
            page.wait_for_timeout(300)
            applied = page.evaluate("""() => ({
              stylesheet: getComputedStyle(document.querySelector(".btn")).borderRadius !== "0px",
              styleElements: document.querySelectorAll("style").length,
              styleAttributes: document.querySelectorAll("[style]").length,
              images: document.images.length,
              fonts: document.fonts.size,
            })""")
            print(f"exercised: {steps}")
            print(f"requests: {dict(Counter(re.sub(r'bootstrap.*', 'bootstrap', r) for r in requests))}")
            policies = set(headers.values())
            print(f"policy on every response equals production's: {policies == {SERVER_CSP}}")
            print(f"violations: {csp_events(page)}; console errors: {seen['console']}; page errors: {seen['errors']}")
            print(f"stylesheet applied: {applied['stylesheet']}; <style> elements: {applied['styleElements']}; "
                  f"style attributes: {applied['styleAttributes']}; images: {applied['images']}; "
                  f"web fonts: {applied['fonts']}")
            kinds = {request.split(" ", 1)[0] for request in requests}
            if (
                csp_events(page) or seen["console"] or seen["errors"] or policies != {SERVER_CSP}
                or not applied["stylesheet"] or applied["styleElements"] or applied["styleAttributes"]
                or kinds - {"document", "script", "stylesheet", "fetch"}
            ):
                failures.append("the slice does not run cleanly under the unchanged policy")
            context.close()

        print("-- part 2: library probes under the unchanged policy --")
        results: dict[str, dict] = {}
        with live_spike(probes=True, csp_additions=()) as live:
            context = authenticated_context(browser, live)
            watch(context)
            page = context.new_page()
            for name, title in PROBES:
                result = exercise_probe(page, live.origin, name)
                results[name] = result
                print(f"{title}: violations={result['violations'] or 'none'}; button styled="
                      f"{result['buttonStyled']}; overlay visible={result['overlayVisible']}; "
                      f"custom (non-native) select={result['customSelect']}; "
                      f"style attributes in the DOM={result['styleAttributes']}; "
                      f"<style> elements={result['styleElements']}")
                print(f"  build: {probe_assets(name)}")
                if not result["buttonStyled"] or not result["overlayVisible"]:
                    failures.append(f"{name}: the probe did not render its components")
            plain = results["plain"]
            print(f"plain Svelte: style: directive applied (width {plain['directiveWidth']} of "
                  f"{plain['parent']}px); style attribute applied (width {plain['attributeWidth']}); "
                  f"spread style applied (outline {plain['spreadOutline']})")
            if plain["violations"] or plain["spreadOutline"] != "dotted" or plain["styleAttributes"] < 3:
                failures.append("plain Svelte 5 output does not run under the unchanged policy")
            context.close()

        needing = [name for name, _title in PROBES if results[name]["violations"]]
        print(f"probes with violations under the unchanged policy: {needing}")
        for name in needing:
            cleared = None
            for size in (1, 2, 3):
                for additions in combinations(APPROVED_ADDITIONS, size):
                    with live_spike(probes=True, csp_additions=additions) as live:
                        context = authenticated_context(browser, live)
                        watch(context)
                        page = context.new_page()
                        violations = exercise_probe(page, live.origin, name)["violations"]
                        context.close()
                    print(f"{name} with {list(additions)}: violations={violations or 'none'}")
                    if not violations and cleared is None:
                        cleared = additions
                if cleared:
                    break
            if cleared is None:
                print(f"{name}: no combination of the pre-approved additions clears it")
                failures.append(f"{name} needs more than the approved envelope")
            else:
                print(f"{name}: fewest additions that clear it: {list(cleared)} -> {policy_with(cleared)}")
        print("the slice uses daisyUI and overrides the texture that needs img-src "
              "(`--fx-noise: none` in app.css), which is why part 1 has no violation")
        if SLICE_CSP_ADDITIONS:
            failures.append("the slice is served with an addition although part 1 needs none")
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
