"""S13: automated accessibility check (gate H4).

axe-core runs on the slice in the light and the dark scheme, at 1440 and
390 px, for a report with both kinds of group and one verdict, and again
after finalising (when every verdict control is off and the persisted-veto
notice is shown).  All of axe's rules are run, including best practices.

axe reports "needs review" for the contrast of any element with a
``background-image`` declaration, and daisyUI declares ``background-image:
none`` on buttons, badges and alerts.  The proof measures those itself, with
the WCAG 2 formula, and requires 4.5:1.  The one element with a real
background image is the native select, whose image is daisyUI's two small
chevron gradients at the right edge, away from the text.

axe-core is MPL-2.0.  It is a development-only tool: the proof reads it from
``frontend/node_modules`` and evaluates it in the page through the browser's
debugging channel.  It is never imported by the frontend and is not in the
build (experiment S12 checks that).

    .venv/bin/python spikes/issue-206/proof_s13_axe.py
"""

from __future__ import annotations

import json
from typing import Any

from harness import (
    FRONTEND,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_slice,
    upload,
    verdict_button,
    wait_status,
)

AXE = FRONTEND / "node_modules" / "axe-core"
RUN_JS = """
async () => {
  const results = await axe.run(document, { resultTypes: ["violations", "incomplete"] });
  const brief = (entries) => entries.map((entry) => ({
    id: entry.id, impact: entry.impact, nodes: entry.nodes.length,
    first: entry.nodes[0] ? entry.nodes[0].target.join(" ") : "",
  }));
  // axe cannot judge contrast on an element that has a background-image
  // declaration, and daisyUI declares one (`none`) on buttons, badges and
  // alerts.  Measure those here: resolve each colour through a canvas (which
  // handles oklch), composite translucent layers, and apply the WCAG formula.
  const canvas = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  const rgba = (colour) => {
    canvas.clearRect(0, 0, 1, 1);
    canvas.fillStyle = colour;
    canvas.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = canvas.getImageData(0, 0, 1, 1).data;
    return [r, g, b, a / 255];
  };
  const over = (top, under) => top.slice(0, 3).map((value, i) => value * top[3] + under[i] * (1 - top[3])).concat(1);
  const background = (node) => {
    const layers = [];
    for (let at = node; at; at = at.parentElement) {
      const colour = rgba(getComputedStyle(at).backgroundColor);
      if (colour[3] > 0) layers.push(colour);
      if (colour[3] === 1) break;
    }
    const scheme = matchMedia("(prefers-color-scheme: dark)").matches ? [18, 18, 18, 1] : [255, 255, 255, 1];
    return layers.reduceRight((under, layer) => over(layer, under), scheme);
  };
  const luminance = (colour) => {
    const [r, g, b] = colour.slice(0, 3).map((value) => {
      const c = value / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const measured = [];
  const unmeasured = [];
  results.incomplete.forEach((entry) => entry.nodes.forEach((node) => {
    const element = document.querySelector(node.target.join(" "));
    const reason = node.any.map((check) => (check.data && check.data.messageKey) || "").join(",");
    if (entry.id !== "color-contrast" || !element || !/^bg(Image|Gradient)$/.test(reason)) {
      unmeasured.push(entry.id + " " + node.target.join(" "));
      return;
    }
    const style = getComputedStyle(element);
    const images = style.backgroundImage.split(",").map((part) => part.trim());
    const plain = images.every((part) => part === "none");
    const back = background(element);
    const text = over(rgba(style.color), back);
    const [high, low] = [luminance(text), luminance(back)].sort((a, b) => b - a);
    measured.push({ target: node.target.join(" "), ratio: (high + 0.05) / (low + 0.05), plain: plain,
      gradient: plain ? "" : style.backgroundImage });
  }));
  return {
    violations: brief(results.violations),
    incomplete: results.incomplete.reduce((sum, entry) => sum + entry.nodes.length, 0),
    unmeasured: unmeasured,
    measured: measured,
    passes: results.passes.length,
  };
}
"""


def run(page: Any, label: str, failures: list[str]) -> None:
    for width in (1440, 390):
        for scheme in ("light", "dark"):
            page.set_viewport_size({"width": width, "height": 900})
            page.emulate_media(color_scheme=scheme)
            # Theme changes transition button colours. Measure settled styles
            # rather than a contrast ratio halfway between the two themes.
            page.evaluate("async () => { await Promise.all(document.getAnimations().map("
                          "animation => animation.finished.catch(() => undefined))); }")
            result = page.evaluate(RUN_JS)
            ratios = [entry["ratio"] for entry in result["measured"]]
            low = min(result["measured"], key=lambda entry: entry["ratio"], default=None)
            painted = [entry["target"] for entry in result["measured"] if not entry["plain"]]
            print(f"{label}, {width}px {scheme}: rules passed={result['passes']}, "
                  f"violations={result['violations']}; contrast axe could not judge: "
                  f"{result['incomplete']} nodes, measured here {len(ratios)}, lowest "
                  f"{low['ratio']:.2f}:1 ({low['target']}), below 4.5:1: "
                  f"{[e['target'] for e in result['measured'] if e['ratio'] < 4.5]}; "
                  f"with a real background image: {painted}; not measured: {result['unmeasured']}")
            if (
                result["violations"] or result["unmeasured"]
                or any(ratio < 4.5 for ratio in ratios)
                or any(target != "select" for target in painted)
            ):
                failures.append(f"{label}, {width}px {scheme}: an accessibility problem is unexplained")


def main() -> int:
    failures: list[str] = []
    if not (AXE / "axe.min.js").is_file():
        print("FAIL: axe-core is not installed; run `npm ci` in spikes/issue-206/frontend")
        return 1
    version = json.loads((AXE / "package.json").read_text(encoding="utf-8"))
    print(f"axe-core {version['version']} ({version['license']}), development-only")
    source = (AXE / "axe.min.js").read_text(encoding="utf-8")
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        upload(context, live, "armor_close.csv")
        page = open_slice(context, live)
        page.evaluate(source + "\n;undefined")
        verdict_button(page, "6032", "Veto").click()
        wait_status(page, "recorded your veto")
        run(page, "reviewing, one veto", failures)
        page.locator("[data-kind-filter=exact]").click()
        page.locator("select[data-facet=guardian_class]").select_option("Titan")
        page.locator("[data-kind-filter=same_stat]").click()
        run(page, "filtered", failures)
        page.get_by_role("button", name="Finalise review").click()
        wait_status(page, "Finalised")
        run(page, "finalised", failures)
        page.get_by_role("button", name="Reset session").click()
        wait_status(page, "reset")
        run(page, "no report", failures)
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
