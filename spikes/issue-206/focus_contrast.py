"""Measure the actual keyboard-focus outline against its adjacent background.

The slice's indicator is outside the control (positive outline offset), so
the adjacent colour is the composited parent background. Canvas resolves
computed oklch colours; control opacity is included. No injected style tag,
markup or application code is used. S13 and S15 share this measurement.
"""

from __future__ import annotations

from typing import Any

FOCUS_JS = """
() => {
  const node = document.activeElement;
  const controls = Array.from(document.querySelectorAll('a[href], button, select, input'));
  if (!controls.includes(node)) return null;
  const canvas = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const rgba = colour => {
    canvas.clearRect(0, 0, 1, 1);
    canvas.fillStyle = colour;
    canvas.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = canvas.getImageData(0, 0, 1, 1).data;
    return [r, g, b, a / 255];
  };
  const over = (top, under) => top.slice(0, 3).map((v, i) => v * top[3] + under[i] * (1 - top[3])).concat(1);
  const layers = [];
  const images = [];
  let opacity = Number(getComputedStyle(node).opacity);
  for (let at = node.parentElement; at; at = at.parentElement) {
    const style = getComputedStyle(at);
    opacity *= Number(style.opacity);
    if (style.backgroundImage.split(',').some(image => image.trim() !== 'none')) images.push(style.backgroundImage);
    layers.push(rgba(style.backgroundColor));
  }
  // The built slice paints its root background. Fail if a default canvas
  // would have to be guessed, or if an adjacent image cannot be measured.
  const opaque = layers.some(layer => layer[3] === 1);
  const back = layers.reduceRight((under, layer) => over(layer, under), [255, 255, 255, 1]);
  const style = getComputedStyle(node);
  const ring = rgba(style.outlineColor);
  ring[3] *= opacity;
  const painted = over(ring, back);
  const luminance = colour => colour.slice(0, 3).map(v => {
    const c = v / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }).reduce((sum, v, i) => sum + v * [0.2126, 0.7152, 0.0722][i], 0);
  const [high, low] = [luminance(painted), luminance(back)].sort((a, b) => b - a);
  const box = node.getBoundingClientRect();
  return {
    order: controls.indexOf(node),
    name: node.getAttribute('aria-label') || node.textContent.trim().replace(/\\s+/g, ' ') ||
      node.getAttribute('data-facet') || node.id,
    tag: node.tagName.toLowerCase(), pressed: node.getAttribute('aria-pressed'),
    disabled: node.getAttribute('aria-disabled'), primary: node.classList.contains('btn-primary'),
    focusVisible: node.matches(':focus-visible'), visible: box.width > 0 && box.height > 0,
    outline: style.outlineStyle, width: parseFloat(style.outlineWidth), offset: parseFloat(style.outlineOffset),
    ratio: (high + 0.05) / (low + 0.05), opaque, images,
  };
}
"""
SETTLE_JS = """async () => {
  await Promise.all(document.getAnimations().map(animation => animation.finished.catch(() => undefined)));
}"""


def keyboard_lap(page: Any) -> list[dict]:
    """Measure one actual Tab lap; do not infer focus styling from unfocused nodes."""
    controls: list[dict] = []
    limit = page.locator("a[href], button, select, input").count() + 5
    for _ in range(limit):
        page.keyboard.press("Tab")
        page.evaluate(SETTLE_JS)
        measured = page.evaluate(FOCUS_JS)
        if measured is None:
            continue
        if controls and measured["order"] == controls[0]["order"]:
            break
        controls.append(measured)
    return sorted(controls, key=lambda entry: entry["order"])


def problems(controls: list[dict]) -> list[str]:
    return [entry["name"] for entry in controls if (
        not entry["focusVisible"] or not entry["visible"] or not entry["opaque"] or entry["images"]
        or entry["outline"] != "solid" or entry["width"] < 3 or entry["offset"] < 2 or entry["ratio"] < 3
    )]


def check(page: Any, label: str, failures: list[str]) -> None:
    controls = keyboard_lap(page)
    expected = page.locator("a[href], button, select, input").count()
    bad = problems(controls)
    low = min(controls, key=lambda entry: entry["ratio"])
    primary = [(entry["name"], round(entry["ratio"], 2)) for entry in controls if entry["primary"]]
    print(f"{label}: keyboard focus={len(controls)}/{expected}; lowest {low['ratio']:.2f}:1 "
          f"({low['name']}); primary={primary}; outline floor=3px/2px; problems={bad}")
    if len(controls) != expected or len({entry["order"] for entry in controls}) != expected or bad:
        failures.append(f"{label}: a keyboard focus indicator fails its floor or 3:1 contrast")


def negative_control(page: Any) -> None:
    """Recreate the old layered floor; dark primary controls must fail contrast."""
    page.emulate_media(color_scheme="dark")
    page.evaluate(SETTLE_JS)
    page.evaluate("""() => {
      for (const sheet of document.styleSheets) {
        const index = Array.from(sheet.cssRules).findIndex(rule => rule.selectorText === ':focus-visible');
        if (index === -1) continue;
        const saved = sheet.cssRules[index].cssText;
        sheet.deleteRule(index);
        sheet.insertRule('@layer base { :focus-visible { outline: 3px solid var(--color-primary); outline-offset: 2px; } }', index);
        window.__restoreFocusFloor = () => { sheet.deleteRule(index); sheet.insertRule(saved, index); };
        return;
      }
      throw new Error('unlayered focus floor not found');
    }""")
    try:
        entries = [entry for entry in keyboard_lap(page) if entry["primary"]]
        names = [entry["name"] for entry in entries]
        assert "Finalise review" in names and any(name.startswith("All (") for name in names)
        assert all(entry["focusVisible"] and entry["width"] == 2 and entry["ratio"] < 3 for entry in entries)
        print("pre-fix cascade negative control: " + "; ".join(
            f"{entry['name']}={entry['ratio']:.2f}:1/{entry['width']:.0f}px" for entry in entries
        ) + "; rejected=True")
    finally:
        page.evaluate("() => { window.__restoreFocusFloor(); delete window.__restoreFocusFloor; }")
