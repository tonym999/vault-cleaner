"""Five alternating fresh documents, S15's unchanged stamps plus settled frames.

No run is thrown away. Each command invocation prints its complete samples
and all seven comparisons, and fails if any comparison fails. Diagnostics
reproduce M1/M2; the separate flip probe reproduces M4 without contaminating
the timed documents. A settled stamp is the second nested animation frame,
not S15's first-frame opportunity. No output or screenshot is written.
"""

from __future__ import annotations

import json
import subprocess
import sys
from statistics import median
from typing import Any

from run_proof import FRONTEND, configure

configure()
from dev import preload
from expected import expected_groups
from harness import (
    authenticated_context,
    chromium,
    finish,
    live_spike,
    report,
    verdict_button,
)
from proof_s15_scale import (
    ARM_REPAINT_JS,
    TIMING_JS,
    far_member,
    production_button,
)

RUNS = 5
COUNTERS = ("ScriptDuration", "RecalcStyleDuration", "LayoutDuration", "TaskDuration")
COMPARISONS = (
    ("A1 navigation to all groups", "navigation"),
    ("A2 navigation to next frame", "navigationFrame"),
    ("A3 acknowledgement to DOM", "dom"),
    ("A4 acknowledgement to next frame", "frame"),
    ("B1 navigation to settled", "navigationSettled"),
    ("B2 key press to settled", "keySettled"),
    ("B3 acknowledgement to settled", "ackSettled"),
)
SETTLED_JS = r"""
window.__settled = {navigation: null, verdict: null, key: null};
const settled = window.__settled;
let navigationArmed = false;
const observeSettled = () => {
  if (navigationArmed || window.__scale.ready === null) return;
  navigationArmed = true;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    settled.navigation = performance.now();
  }));
};
new MutationObserver(observeSettled).observe(document,
  {subtree: true, childList: true, attributes: true});
document.addEventListener('DOMContentLoaded', observeSettled);
document.addEventListener('keydown', event => {
  if (event.key === 'Enter' && event.target === window.__scaleButton) {
    settled.key = performance.now();
  }
}, true);
undefined;
"""
ARM_SETTLED_JS = r"""
button => {
  __settled.verdict = __settled.key = null;
  const observer = new MutationObserver(() => {
    if (__scale.ack === null || button.getAttribute('aria-pressed') !== 'true') return;
    observer.disconnect();
    requestAnimationFrame(() => requestAnimationFrame(() => {
      __settled.verdict = performance.now();
    }));
  });
  observer.observe(button, {attributes: true, attributeFilter: ['aria-pressed']});
}
"""
TWO_FRAMES = "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"


def metrics(cdp: Any) -> dict[str, float]:
    return {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}


def delta(before: dict, after: dict) -> dict:
    return {key: (after[key] - before.get(key, 0)) * 1000 for key in COUNTERS}


def sample(context: Any, live: Any, name: str, group: dict, member: dict) -> dict:
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    cdp.send("Performance.enable")
    page.goto(live.origin + ("/spike/" if name == "slice" else "/"), wait_until="domcontentloaded")
    page.wait_for_function("() => __settled.navigation !== null")
    nav = metrics(cdp)
    result = page.evaluate("""() => ({navigation: __scale.ready,
      navigationFrame: __scale.frame, navigationSettled: __settled.navigation,
      nodes: document.querySelectorAll('*').length,
      groups: document.querySelectorAll(location.pathname === '/spike/'
        ? 'article[data-group]' : '#vc-duplicate-list article.armor-group').length,
      responseEnd: performance.getEntriesByType('resource')
        .find(entry => entry.name.endsWith('/api/report'))?.responseEnd,
    })""")
    result["navigationMetrics"] = delta({}, nav)
    current = {v["id"]: v["verdict"] for v in report(context, live)["verdicts"]}
    action = "Veto" if current.get(member["id"]) == "approved" else "Approve"
    button = verdict_button(page, member["id"], action) if name == "slice" else production_button(
        page, group, member, action.lower()
    )
    button.scroll_into_view_if_needed()
    button.focus()
    page.evaluate(TWO_FRAMES)
    button.evaluate(ARM_REPAINT_JS)
    button.evaluate(ARM_SETTLED_JS)
    before = metrics(cdp)
    with page.expect_response("**/api/verdicts") as response:
        page.keyboard.press("Enter")
    assert response.value.status == 200
    page.wait_for_function("() => __settled.verdict !== null")
    after = metrics(cdp)
    result.update(page.evaluate("""() => ({
      dom: __scale.repaint - __scale.ack,
      frame: __scale.repaintFrame - __scale.ack,
      keySettled: __settled.verdict - __settled.key,
      ackSettled: __settled.verdict - __scale.ack,
      same: document.activeElement === __scaleButton && __scaleButton.isConnected,
      viewportJump: Math.abs(__scaleButton.getBoundingClientRect().top - __scaleTop),
    })"""))
    result["verdictMetrics"] = delta(before, after)
    assert result["groups"] == 74
    if name == "slice":
        assert result["same"] and result["viewportJump"] <= 1
    assert result["dom"] >= 0 and result["ackSettled"] >= result["frame"] >= result["dom"]
    page.close()
    return result


def flip_probe(context: Any, live: Any) -> None:
    """Independent loaded page: six flips and forced flushes, as M4."""
    page = context.new_page()
    page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
    page.wait_for_function("() => __settled.navigation !== null")
    cdp = context.new_cdp_session(page)
    cdp.send("Performance.enable")
    for mode in ("one-class", "all-class", "all-aria", "all-both", "all-disabled", "all-unused"):
        values = []
        for _ in range(6):
            before = metrics(cdp)
            page.evaluate("""mode => {
              const buttons = Array.from(document.querySelectorAll('[data-member] button'));
              const targets = mode.startsWith('one') ? buttons.slice(0, 1) : buttons;
              for (const button of targets) {
                if (mode.endsWith('class') || mode.endsWith('both')) button.classList.add('btn-disabled');
                if (mode.endsWith('aria') || mode.endsWith('both')) button.setAttribute('aria-disabled', 'true');
                if (mode.endsWith('disabled')) button.disabled = true;
                if (mode.endsWith('unused')) button.setAttribute('data-unused-probe', 'true');
              }
              getComputedStyle(targets[0]).color;
            }""", mode)
            page.evaluate(TWO_FRAMES)
            values.append(delta(before, metrics(cdp))["RecalcStyleDuration"])
            page.evaluate("""() => {
              for (const button of document.querySelectorAll('[data-member] button')) {
                button.classList.remove('btn-disabled'); button.setAttribute('aria-disabled', 'false');
                button.disabled = false; button.removeAttribute('data-unused-probe');
              }
              getComputedStyle(document.querySelector('[data-member] button')).color;
            }""")
            page.evaluate(TWO_FRAMES)
        print(f"M4 {mode}: buttons={435 if mode.startswith('all') else 1}; "
              f"style median={median(values):.1f}ms; samples={[round(v, 1) for v in values]}")
    page.close()


def projection_probe(envelope: dict) -> None:
    """M5's warm Node projection/parse measurement, after browser timings."""
    script = r"""
import { readFileSync } from 'node:fs';
import { performance } from 'node:perf_hooks';
import { duplicateGroups } from './src/lib/view.ts';
const body = readFileSync(0, 'utf8');
const envelope = JSON.parse(body);
const previous = duplicateGroups(envelope);
const measure = fn => {
  for (let i = 0; i < 10; i++) fn();
  const samples = [];
  for (let i = 0; i < 50; i++) {
    const start = performance.now(); fn(); samples.push(performance.now() - start);
  }
  samples.sort((a, b) => a - b);
  return (samples[24] + samples[25]) / 2;
};
console.log(`M5 warm Node medians (50): bytes=${Buffer.byteLength(body)}; ` +
  `JSON.parse=${measure(() => JSON.parse(body)).toFixed(3)}ms; ` +
  `projection=${measure(() => duplicateGroups(envelope)).toFixed(3)}ms; ` +
  `value-stable projection=${measure(() => duplicateGroups(envelope, previous)).toFixed(3)}ms`);
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=FRONTEND,
                            input=json.dumps(envelope), text=True, capture_output=True, check=True)
    print(result.stdout.strip())


def main() -> int:
    if sys.argv[1:]:
        print("RESULT: FAIL (no arguments accepted)")
        return 1
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        preload(live, "real")
        context = authenticated_context(browser, live)
        groups = expected_groups(report(context, live))
        assert len(groups) == 74
        assert all(m["id"].startswith("1000") for g in groups for m in g["members"])
        index, group, member = far_member(groups)
        print("fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; no overlay")
        print(f"target: group {index + 1}/74; viewport 1440x1000 light; five alternating fresh documents")
        context.add_init_script(f"window.__scaleGroups = {len(groups)};\n" + TIMING_JS + SETTLED_JS)
        measured: dict[str, list[dict]] = {"slice": [], "production": []}
        for run in range(RUNS):
            order = ("slice", "production") if run % 2 == 0 else ("production", "slice")
            for name in order:
                result = sample(context, live, name, group, member)
                measured[name].append(result)
                print(f"run {run + 1} {name}: " + "; ".join(
                    f"{key}={result[key]:.1f}ms" for _, key in COMPARISONS
                ) + f"; responseEnd={result['responseEnd']:.1f}ms; elements={result['nodes']}")
        for label, key in COMPARISONS:
            mine = median(s[key] for s in measured["slice"])
            theirs = median(s[key] for s in measured["production"])
            passed = mine <= theirs
            print(f"{label}: slice={mine:.1f}ms production={theirs:.1f}ms "
                  f"gap={mine - theirs:+.1f}ms {'PASS' if passed else 'FAIL'}")
            if not passed:
                failures.append(label)
        for name, samples in measured.items():
            for window in ("navigation", "verdict"):
                print(f"{name} {window} CDP medians: " + "; ".join(
                    f"{key}={median(s[window + 'Metrics'][key] for s in samples):.1f}ms"
                    for key in COUNTERS
                ))
        flip_probe(context, live)
        projection_probe(report(context, live))
        context.close()
    return finish(failures)


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit as error:
        if error.code not in (None, 0):
            print("RESULT: FAIL (proof exited before completion)", flush=True)
        raise
    except Exception:
        print("RESULT: FAIL (proof raised an exception)", flush=True)
        raise
    sys.exit(code)
