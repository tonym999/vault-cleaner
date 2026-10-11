"""#210: the slice under the unchanged policy, in place of #206's S7 part 1.

    .venv/bin/python spikes/issue-210/proof_csp.py

S7 cannot run on this slice: it shows "the stylesheet applied" by reading
daisyUI's ``.btn``, which the slice no longer has (plan Amendment 1). This
proof repeats S7's part 1: the same exercise and the same pass conditions,
with that one reading taken from the slice's own buttons. It also requires
no image and no web font, which S7 only reported. S7's part 2 probes #206's
library shortlist and is not rerun.
"""

from __future__ import annotations

import re
import sys
from collections import Counter

from run_proof import configure

configure()

import harness
from spike_app import SLICE_CSP_ADDITIONS

from vault_cleaner.server.app import SERVER_CSP

APPLIED_JS = """() => {
  const button = document.querySelector("[data-slot=button]");
  return {
    stylesheet: getComputedStyle(button).borderRadius !== "0px"
      && getComputedStyle(document.body).backgroundColor !== "rgba(0, 0, 0, 0)",
    slots: document.querySelectorAll("[data-slot=button]").length,
    styleElements: document.querySelectorAll("style").length,
    styleAttributes: document.querySelectorAll("[style]").length,
    images: document.images.length,
    fonts: document.fonts.size,
  };
}"""


def main() -> int:
    failures: list[str] = []
    print(f"production policy: {SERVER_CSP}")
    print(f"additions the slice is served with: {list(SLICE_CSP_ADDITIONS)}")
    with harness.chromium() as browser, harness.live_spike(csp_additions=()) as live:
        context = harness.authenticated_context(browser, live)
        seen = harness.watch(context)
        harness.upload_bytes(context, live, harness.two_class_fixture())
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
        page.locator("select[data-facet=guardian_class]").select_option("Hunter")
        steps.append("class facet")
        page.locator("[data-kind-filter=exact]").click()
        steps.append("kind filter, dropping the class (reconciliation notice)")
        page.locator("select[data-facet=guardian_class]").select_option("Titan")
        page.locator("[data-kind-filter=all]").click()
        page.locator("select[data-facet=guardian_class]").select_option("")
        for label, word in (("Approve", "approval"), ("Veto", "veto"), ("Unset", "unset"), ("Veto", "veto")):
            harness.verdict_button(page, "6032", label).click()
            harness.wait_status(page, f"recorded your {word}")
        steps.append("verdict buttons (approve, veto, unset)")
        page.keyboard.press("Tab")
        steps.append("focus ring")
        page.get_by_role("button", name="Finalise review").click()
        harness.wait_status(page, "Finalised")
        steps.append("finalise (frozen controls, persisted-veto notice, download link)")
        page.get_by_role("button", name="Reset session").click()
        harness.wait_status(page, "reset")
        steps.append("reset (the no-report empty state)")
        page.get_by_role("button", name="Reload report").click()
        steps.append("reload")
        page.wait_for_timeout(300)
        applied = page.evaluate(APPLIED_JS)
        print(f"exercised: {steps}")
        print(f"requests: {dict(Counter(re.sub(r'bootstrap.*', 'bootstrap', r) for r in requests))}")
        policies = set(headers.values())
        print(f"policy on every response equals production's: {policies == {SERVER_CSP}}")
        print(f"violations: {harness.csp_events(page)}; console errors: {seen['console']}; "
              f"page errors: {seen['errors']}")
        print(f"stylesheet applied: {applied['stylesheet']} (read from {applied['slots']} slice buttons); "
              f"<style> elements: {applied['styleElements']}; style attributes: "
              f"{applied['styleAttributes']}; images: {applied['images']}; web fonts: {applied['fonts']}")
        kinds = {request.split(" ", 1)[0] for request in requests}
        if (
            harness.csp_events(page) or seen["console"] or seen["errors"] or policies != {SERVER_CSP}
            or not applied["stylesheet"] or applied["styleElements"] or applied["styleAttributes"]
            or kinds - {"document", "script", "stylesheet", "fetch"}
            or applied["images"] or applied["fonts"]
        ):
            failures.append("the slice does not run cleanly under the unchanged policy")
        context.close()
    return harness.finish(failures)


if __name__ == "__main__":
    sys.exit(main())
