"""#210: the slice under the unchanged policy, in place of #206's S7 part 1.

    .venv/bin/python spikes/issue-210/proof_csp.py

S7 cannot run on this slice: it shows "the stylesheet applied" by reading
daisyUI's ``.btn``, which the slice no longer has (plan Amendment 1). This
proof repeats S7's part 1: the same exercise and the same pass conditions,
with that one reading taken from the slice's own buttons. It also requires
no image and no web font, which S7 only reported. S7's part 2 probes #206's
library shortlist and is not rerun.

It differs from S7 in one more way, on purpose. S7 keeps one policy per
path, so a later response to a path already seen is never checked, while its
output says "every response". This proof checks every response, and its
negative control removes the policy from later responses to a path whose
first response was intact (second review of #210, REV-02).
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


def watch_policies(page) -> list[tuple[str, str]]:
    """Every response's path and policy, in order. A list, not a mapping:
    a later response to a path already seen must be checked too."""
    responses: list[tuple[str, str]] = []
    page.on("response", lambda response: responses.append(
        (response.url.split("/", 3)[3], response.headers.get("content-security-policy", ""))))
    return responses


def wrong_policies(responses: list[tuple[str, str]]) -> list[str]:
    return [path for path, policy in responses if policy != SERVER_CSP]


def negative_control(browser, failures: list[str]) -> None:
    """Strip the policy from every verdict response after the first; it must be seen.

    The first response to that path is left intact, so a check that keeps one
    policy per path passes this and a check of every response does not.
    """
    with harness.live_spike(csp_additions=()) as live:
        context = harness.authenticated_context(browser, live)
        harness.upload_bytes(context, live, harness.two_class_fixture())
        page = context.new_page()
        responses = watch_policies(page)
        answered = 0

        def strip_later(route) -> None:
            nonlocal answered
            real = route.fetch()
            answered += 1
            headers = dict(real.headers)
            if answered > 1:
                headers.pop("content-security-policy", None)
            route.fulfill(response=real, headers=headers)

        page.route("**/api/verdicts", strip_later)
        page.goto(f"{live.origin}/spike/", wait_until="domcontentloaded")
        page.wait_for_selector("article[data-group]")
        for label, word in (("Approve", "approval"), ("Veto", "veto"), ("Unset", "unset"), ("Veto", "veto")):
            harness.verdict_button(page, "6032", label).click()
            harness.wait_status(page, f"recorded your {word}")
        wrong = wrong_policies(responses)
        by_path = {path: policy for path, policy in reversed(responses)}
        first_only = [path for path, policy in by_path.items() if policy != SERVER_CSP]
        print(f"negative control, policy removed from verdict responses after the first: verdict "
              f"responses={answered}; responses without production's policy={len(wrong)} {sorted(set(wrong))}; "
              f"a one-policy-per-path check would have seen={len(first_only)}")
        if len(wrong) != answered - 1 or answered != 4:
            failures.append("negative control: a later response without the policy was not detected")
        context.close()


def main() -> int:
    failures: list[str] = []
    print(f"production policy: {SERVER_CSP}")
    print(f"additions the slice is served with: {list(SLICE_CSP_ADDITIONS)}")
    with harness.chromium() as browser:
        with harness.live_spike(csp_additions=()) as live:
            context = harness.authenticated_context(browser, live)
            seen = harness.watch(context)
            harness.upload_bytes(context, live, harness.two_class_fixture())
            requests: list[str] = []
            page = context.new_page()
            page.on("request", lambda request: requests.append(
                f"{request.resource_type} {request.method} {request.url.split('/', 3)[3]}"))
            responses = watch_policies(page)
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
            wrong = wrong_policies(responses)
            print(f"exercised: {steps}")
            print(f"requests: {dict(Counter(re.sub(r'bootstrap.*', 'bootstrap', r) for r in requests))}")
            print(f"responses checked one by one: {len(responses)} for {len(requests)} requests; "
                  f"without production's policy: {len(wrong)} {sorted(set(wrong))}")
            print(f"violations: {harness.csp_events(page)}; console errors: {seen['console']}; "
                  f"page errors: {seen['errors']}")
            print(f"stylesheet applied: {applied['stylesheet']} (read from {applied['slots']} slice buttons); "
                  f"<style> elements: {applied['styleElements']}; style attributes: "
                  f"{applied['styleAttributes']}; images: {applied['images']}; web fonts: {applied['fonts']}")
            kinds = {request.split(" ", 1)[0] for request in requests}
            if (
                harness.csp_events(page) or seen["console"] or seen["errors"]
                or wrong or len(responses) != len(requests)
                or not applied["stylesheet"] or applied["styleElements"] or applied["styleAttributes"]
                or kinds - {"document", "script", "stylesheet", "fetch"}
                or applied["images"] or applied["fonts"]
            ):
                failures.append("the slice does not run cleanly under the unchanged policy")
            context.close()
        negative_control(browser, failures)
    return harness.finish(failures)


if __name__ == "__main__":
    sys.exit(main())
