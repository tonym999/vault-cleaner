"""#210: no verdict control animates, and switching them all costs little.

    .venv/bin/python spikes/issue-210/proof_no_transition.py

#209 found the #206 slice's largest cost: every request flips
``aria-disabled`` on all verdict buttons, and each button transitioned five
properties, so one verdict cost 138.7 ms of style recalculation.

Gated here, on the tracked sanitised fixture, in both colour schemes:

- every verdict button's computed ``transition-duration`` and
  ``animation-duration`` are ``0s``, pressed or not;
- no rule in the built stylesheet selects on ``aria-disabled``, so the flip
  restyles nothing.

Recorded, not gated: style recalculation over one acknowledged verdict, from
Chromium's own counters (CDP ``Performance.getMetrics``,
``RecalcStyleDuration``), five runs, median.
"""

from __future__ import annotations

import statistics
import sys

from run_proof import FRONTEND, configure

configure()

import harness
from dev import preload

DURATIONS_JS = """
() => {
  const buttons = Array.from(document.querySelectorAll("[data-member] button"));
  const zero = (value) => value.split(",").every((part) => parseFloat(part) === 0);
  const moving = buttons.filter((button) => {
    const style = getComputedStyle(button);
    return !zero(style.transitionDuration) || !zero(style.animationDuration);
  });
  return {
    buttons: buttons.length,
    pressed: buttons.filter((button) => button.getAttribute("aria-pressed") === "true").length,
    moving: moving.length,
    first: moving.length ? moving[0].getAttribute("aria-label") : "",
  };
}
"""
RUNS = 5


def recalc(session) -> float:
    metrics = session.send("Performance.getMetrics")["metrics"]
    return next(metric["value"] for metric in metrics if metric["name"] == "RecalcStyleDuration")


def measure(context, page, failures: list[str]) -> None:
    """One verdict at a time on the first proposal member; counters around each."""
    session = context.new_cdp_session(page)
    session.send("Performance.enable")
    controls = page.locator("[data-member] div[role=group]").first
    samples = []
    for run in range(RUNS):
        label, word = (("Approve", "approval"), ("Unset", "unset"))[run % 2]
        before = recalc(session)
        controls.get_by_text(label, exact=True).click()
        harness.wait_status(page, f"recorded your {word}")
        page.evaluate("() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))")
        samples.append((recalc(session) - before) * 1000)
    print("style recalculation over one acknowledged verdict, ms: "
          + ", ".join(f"{sample:.1f}" for sample in samples)
          + f"; median {statistics.median(samples):.1f} (recorded, not gated; #209 measured 138.7 on #206)")
    after = page.evaluate(DURATIONS_JS)
    print(f"after {RUNS} verdicts: pressed={after['pressed']}, with a transition or animation={after['moving']}")
    if after["moving"]:
        failures.append("a verdict control animates after a verdict")


def negative_control(page, failures: list[str]) -> None:
    """Give the buttons #206's transition through the CSSOM; the check must see it."""
    page.evaluate("""() => {
      const sheet = document.styleSheets[0];
      sheet.insertRule("[data-member] button { transition: color 0.2s, background-color 0.2s; }",
                       sheet.cssRules.length);
    }""")
    seen = page.evaluate(DURATIONS_JS)
    print(f"negative control, a 0.2s transition added: with a transition={seen['moving']} of {seen['buttons']}")
    if seen["moving"] != seen["buttons"]:
        failures.append("the negative control was not detected")


def main() -> int:
    failures: list[str] = []
    harness.require_build()
    css = (FRONTEND / "dist" / "assets" / "app.css").read_text(encoding="utf-8")
    mentions = css.count("aria-disabled")
    print(f"built stylesheet: rules mentioning aria-disabled={mentions}")
    if mentions:
        failures.append("a stylesheet rule selects on aria-disabled")

    with harness.chromium() as browser, harness.live_spike() as live:
        preload(live, "real")
        signed_in = harness.authenticated_context(browser, live)
        state = signed_in.storage_state()
        signed_in.close()
        for scheme in ("dark", "light"):
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}, color_scheme=scheme, storage_state=state
            )
            page = harness.open_slice(context, live)
            page.wait_for_selector("article[data-group]")
            found = page.evaluate(DURATIONS_JS)
            print(f"{scheme}: verdict buttons={found['buttons']}, pressed={found['pressed']}, "
                  f"with a transition or animation={found['moving']} {found['first']}")
            if found["buttons"] != 435 or found["moving"]:
                failures.append(f"{scheme}: a verdict control animates, or the count is not 435")
            if scheme == "dark":
                measure(context, page, failures)
                negative_control(page, failures)
            context.close()
    return harness.finish(failures)


if __name__ == "__main__":
    sys.exit(main())
