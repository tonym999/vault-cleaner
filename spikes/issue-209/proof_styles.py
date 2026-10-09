"""Isolate stylesheet invalidation by removing one fixed rule family at a time.

A fresh document per family; no source/build changes. Six complete flips,
forced style flush, then settled frames. These diagnostics are not gates.
"""

from __future__ import annotations

import sys
from pathlib import Path
from statistics import median

from run_proof import configure

configure()
from dev import preload
from harness import authenticated_context, chromium, finish, live_spike, open_slice
from proof_gate import TWO_FRAMES, delta, metrics

DELETE_JS = r"""
family => {
  const removed = [];
  const visit = sheet => {
    for (let i = sheet.cssRules.length - 1; i >= 0; i--) {
      const rule = sheet.cssRules[i];
      if (family === 'disabled-direct' && rule.selectorText?.includes('.btn:is(.btn-disabled')
          && rule.style.getPropertyValue('--btn-bg')) {
        removed.push(rule.cssText);
        for (const key of ['--btn-bg', '--btn-border', '--btn-inset', '--btn-shadow']) rule.style.removeProperty(key);
        rule.style.setProperty('background-color', 'transparent');
        rule.style.setProperty('border-color', 'transparent');
        rule.style.setProperty('box-shadow', '0 0 0 0 oklch(0% 0 0 / 0) inset, 0 0 0 0 oklch(0% 0 0 / 0)');
      }
      if (family === 'simple-selector' && rule.selectorText?.includes('.btn:is(.btn-disabled')) {
        removed.push(rule.cssText);
        rule.selectorText = rule.selectorText.replace('.btn:is(.btn-disabled, :disabled, [disabled], [aria-disabled="true"])', '.btn[aria-disabled="true"]');
      }
      const match = family === 'join-scope' ? rule.constructor.name === 'CSSScopeRule'
        : family === 'has' ? rule.selectorText?.includes(':has(')
        : family === 'disabled' ? rule.selectorText?.includes('aria-disabled')
        : family === 'join-and-disabled' ? rule.constructor.name === 'CSSScopeRule' || rule.selectorText?.includes('aria-disabled')
        : family === 'disabled-color' ? rule.selectorText?.includes('aria-disabled') && !!rule.style?.getPropertyValue('color')
        : family === 'disabled-background' ? rule.selectorText?.includes('aria-disabled') && !!rule.style?.getPropertyValue('background-color')
        : family === 'root-has' ? rule.selectorText?.includes(':root:has(') : false;
      if (match) { removed.push(rule.cssText); sheet.deleteRule(i); }
      else if (rule.cssRules) visit(rule);
    }
  };
  for (const sheet of document.styleSheets) visit(sheet);
  return removed;
}
"""
FLIP_JS = r"""
on => {
  for (const button of document.querySelectorAll('[data-member] button')) {
    button.classList.toggle('btn-disabled', on);
    button.setAttribute('aria-disabled', String(on));
  }
  getComputedStyle(document.querySelector('[data-member] button')).color;
}
"""


def main() -> int:
    if sys.argv[1:]:
        print("RESULT: FAIL (no arguments accepted)")
        return 1
    configure(Path(__file__).resolve().parents[1] / "issue-206" / "frontend")
    print("baseline #206 assets; diagnostic CSSOM changes only; six flips per fixed family")
    failures = []
    with live_spike() as live, chromium() as browser:
        preload(live, "real")
        context = authenticated_context(browser, live)
        medians = {}
        for family in ("unchanged", "join-scope", "has", "disabled", "join-and-disabled", "root-has", "disabled-direct", "disabled-color", "disabled-background", "simple-selector", "no-transitions"):
            page = open_slice(context, live)
            removed = page.evaluate(DELETE_JS, family)
            if family == "no-transitions":
                page.evaluate("""() => {
                  document.styleSheets[0].insertRule('[data-member] button { transition: none !important; }', document.styleSheets[0].cssRules.length);
                }""")
            page.wait_for_timeout(300)
            cdp = context.new_cdp_session(page)
            cdp.send("Performance.enable")
            samples = []
            for _ in range(6):
                before = metrics(cdp)
                page.evaluate(FLIP_JS, True)
                page.evaluate(TWO_FRAMES)
                samples.append(delta(before, metrics(cdp))["RecalcStyleDuration"])
                page.evaluate(FLIP_JS, False)
                page.wait_for_timeout(300)
            medians[family] = median(samples)
            print(f"{family}: removed={len(removed)}; style median={median(samples):.1f}ms; "
                  f"samples={[round(s, 1) for s in samples]}")
            if family in ("join-scope", "disabled-direct", "disabled"):
                for rule in removed:
                    print("isolated rule: " + rule)
            page.close()
        if medians["no-transitions"] >= medians["unchanged"]:
            failures.append("removing transitions did not reduce style recalculation")
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
