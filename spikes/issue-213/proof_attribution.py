"""#213 step 1: where the redesigned slice's first-render time goes.

    .venv/bin/python spikes/issue-213/proof_attribution.py

Diagnostic only. Nothing here is a gate comparison, and no variant it builds
is kept: every variant is made in a temporary directory, or by rewriting a
served file in flight, and is gone when the proof exits.

Four parts, all on the tracked sanitised fixture at 1440x1000, light:

1. **Timeline.** Slice beside production: when each file finished loading,
   when the report request started and ended, when the first group was in
   the document, S15's ``ready`` stamp, the settled frame, and Chromium's
   own script, style and layout counters up to that frame.
2. **Profile.** A sampling CPU profile of an unminified build of the same
   source, grouped by the module each function came from. Sampling inflates
   every figure; read them as proportions.
3. **Floor.** The slice's own rendered markup and stylesheet with no
   framework: the script is replaced by one that waits for the same report
   and then assigns the captured markup. No client renderer that produces
   this document can be faster than this.
4. **Ablations.** One suspected cause removed at a time, measured against
   the unchanged build in the same alternation. A cause counts only if
   removing it moves the number.

Every arm has its document and its static files answered through the same
interception: the slice's three files, the floor's, and production's page,
stylesheet and two scripts. API requests are not intercepted on any arm. The
arms then differ only in the bytes named.

Interception is not free. Part 0 measures what it adds to each page, so the
figures here are comparable with each other and are not the gate's: the gate
intercepts nothing.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any

from run_proof import FRONTEND, configure

configure()

import harness
from dev import preload
from proof_gate import COUNTERS, SETTLED_JS, delta, metrics
from proof_s15_scale import TIMING_JS

RUNS = 5
INTERVAL_US = 200
FILES = {"/spike/": "index.html", "/spike/assets/app.js": "assets/app.js", "/spike/assets/app.css": "assets/app.css"}
FLOOR_URL = "/spike/assets/floor.txt"

FIRST_JS = r"""
window.__first = null;
new MutationObserver((_, observer) => {
  const selector = location.pathname === "/spike/" ? "article[data-group]" : "#vc-duplicate-list article.armor-group";
  if (document.querySelector(selector)) { window.__first = performance.now(); observer.disconnect(); }
}).observe(document, {subtree: true, childList: true});
undefined;
"""
READ_JS = r"""
() => {
  const resources = {};
  for (const entry of performance.getEntriesByType("resource")) {
    const name = new URL(entry.name).pathname;
    resources[name] = {start: entry.startTime, end: entry.responseEnd};
  }
  const navigation = performance.getEntriesByType("navigation")[0];
  return {
    resources, html: navigation.responseEnd, first: window.__first,
    built: __scale.built, ready: __scale.ready, frame: __scale.frame, settled: __settled.navigation,
    elements: document.querySelectorAll("*").length,
    height: document.documentElement.scrollHeight,
  };
}
"""
# The floor's script: the same report request, then the captured markup.
FLOOR_JS = """
const [, markup] = await Promise.all([
  fetch('/api/report', {headers: {Accept: 'application/json'}}).then((response) => response.json()),
  fetch('./assets/floor.txt').then((response) => response.text()),
]);
document.getElementById('app').innerHTML = markup;
"""
MARKUP_JS = "() => document.getElementById('app').innerHTML"
# What a reader sees: tags, attributes and text, without Svelte's comment anchors.
SHAPE_JS = "() => document.getElementById('app').innerHTML.replace(/<!--.*?-->/g, '')"
BOXES_JS = r"""
() => Array.from(document.querySelectorAll("#app *")).map((node) => {
  const box = node.getBoundingClientRect();
  return [box.left, box.top + scrollY, box.width, box.height].map((value) => Math.round(value * 4) / 4).join(",");
}).join(";")
"""

# One suspected cause each. (file, text to find exactly once, replacement.)
BADGE = "components/ui/badge.svelte"
SOURCE_ABLATIONS: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "class-merge-once": (
        "a badge's class string is merged once per distinct input, not once per badge",
        [
            (BADGE, "  export type BadgeVariant = VariantProps<typeof badgeVariants>['variant'];\n",
             ("  export type BadgeVariant = VariantProps<typeof badgeVariants>['variant'];\n"
              "  const resolved = new Map<string, string>();\n"
             "  export const badgeClass = (variant: BadgeVariant, extra: unknown): string => {\n"
             "    const key = `${variant}\\n${String(extra ?? '')}`;\n"
             "    let value = resolved.get(key);\n"
             "    if (value === undefined) {\n"
             "      value = cn(badgeVariants({ variant }), 'h-auto shrink whitespace-normal transition-none', extra as string);\n"
             "      resolved.set(key, value);\n"
             "    }\n"
             "    return value;\n"
             "  };\n")),
            (BADGE, "  import { type VariantProps, tv } from 'tailwind-variants';\n",
             ("  import { type VariantProps, tv } from 'tailwind-variants';\n"
              "  import { cn } from './cn';\n")),
            (BADGE, "  import { cn } from './cn';\n\n  let {", "  let {"),
            (BADGE, "class={cn(badgeVariants({ variant }), 'h-auto shrink whitespace-normal transition-none', className)}",
             "class={badgeClass(variant, className)}"),
        ],
    ),
    "report-first": (
        "the report is requested before the page is mounted, not after",
        [("main.ts", "mount(App, { target: document.getElementById('app')!, props: { session } });\nvoid session.load();\n",
          "void session.load();\nmount(App, { target: document.getElementById('app')!, props: { session } });\n")],
    ),
}
VALUE_USE = re.compile(r"<Value cell=\{([^}]+)\} />")
# Layout ablations change what the page looks like. They are measurements of
# what the comparison grid costs to lay out, never candidates.
MATRIX_BLOCK = ".matrix{display:block!important}"
GRIDS_BLOCK = (".matrix,.group-head,.group-title,.stat,.verdict-cell,.list,.groups,.tuned-boxes"
               "{display:block!important}")
PRELOAD = '  <link rel="preload" as="fetch" href="../api/report" crossorigin>\n</head>'


def sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:16]


def build(source: Path, out: Path, minify: bool = True) -> dict[str, bytes]:
    """Build ``source`` into ``out`` and return the three served files."""
    command = ["npx", "vite", "build", "--outDir", str(out), "--emptyOutDir"]
    if not minify:
        command += ["--minify", "false"]
    done = subprocess.run(command, cwd=source, capture_output=True, text=True, check=False)
    if done.returncode:
        print(done.stdout + done.stderr)
        raise SystemExit("FAIL: a variant did not build")
    return {name: (out / name).read_bytes() for name in FILES.values()}


def ablated_source(copy: Path, name: str) -> None:
    src = copy / "src"
    if name == "value-inline":
        count = 0
        for path in sorted((src / "components").glob("*.svelte")):
            text = path.read_text(encoding="utf-8").replace("<Value {cell} />", "<Value cell={cell} />")
            text, found = VALUE_USE.subn(
                r"<span class:italic={\1.unknown} data-unknown={\1.unknown ? '' : undefined}>{\1.text}</span>", text)
            if found:
                path.write_text(text, encoding="utf-8")
                count += found
        print(f"  value-inline: {count} uses of the Value component written out as their one span")
        return
    for file, old, new in SOURCE_ABLATIONS[name][1]:
        path = src / file
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise SystemExit(f"FAIL: ablation {name}: {file} does not contain its anchor exactly once")
        path.write_text(text.replace(old, new), encoding="utf-8")


def static_containers(css: str, width: float) -> tuple[str, int]:
    """Resolve every ``@container group`` rule for one known group width.

    A diagnostic rewrite for one viewport, not a stylesheet anyone could ship.
    """
    out, position, resolved = [], 0, 0
    # The build writes range syntax: `@container group (width<=479.98px){`.
    pattern = re.compile(r"@container group\s*\(width(<=|>=)([0-9.]+)px\)\s*\{")
    while True:
        match = pattern.search(css, position)
        if match is None:
            out.append(css[position:])
            break
        out.append(css[position:match.start()])
        depth, end = 1, match.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(css[end], 0)
            end += 1
        limit = float(match.group(2))
        if (width >= limit) if match.group(1) == ">=" else (width <= limit):
            out.append(css[match.end():end - 1])
        position, resolved = end, resolved + 1
    text = "".join(out)
    if "@container" in text:
        raise SystemExit("FAIL: a container rule was not resolved")
    text, declarations = re.subn(r"container:\s*group\s*/\s*inline-size;?", "", text)
    if declarations != 1 or "container" in text.replace("container-", ""):
        raise SystemExit("FAIL: the container declaration was not removed exactly once")
    return text, resolved + declarations


class Arm:
    """One set of served bytes. ``files`` replaces any of the three by name."""

    def __init__(self, label: str, files: dict[str, bytes] | None = None, path: str = "/spike/",
                 floor: bytes | None = None, routed: bool = True) -> None:
        self.label, self.files, self.path, self.floor = label, files or {}, path, floor
        self.routed = routed

    def open(self, context: Any, live: Any) -> tuple[Any, Any, list[str]]:
        page = context.new_page()
        requests: list[str] = []
        page.on("request", lambda request: requests.append(request.url))

        def serve(route: Any) -> None:
            path = route.request.url.removeprefix(live.origin).split("?")[0]
            if path == FLOOR_URL and self.floor is not None:
                route.fulfill(status=200, content_type="text/plain; charset=utf-8", body=self.floor)
            elif path in FILES:
                response = route.fetch()
                route.fulfill(response=response, body=self.files.get(FILES[path], response.body()))
            elif path == "/" or path.startswith("/assets/"):
                # Production's page and static files: the same round trip, bytes unchanged.
                response = route.fetch()
                route.fulfill(response=response)
            else:
                route.continue_()

        if self.routed:
            page.route("**/*", serve)
        cdp = context.new_cdp_session(page)
        cdp.send("Performance.enable")
        return page, cdp, requests

    def sample(self, context: Any, live: Any) -> dict:
        page, cdp, requests = self.open(context, live)
        page.goto(live.origin + self.path, wait_until="domcontentloaded")
        page.wait_for_function("() => __settled.navigation !== null")
        counters = delta({}, metrics(cdp))
        result = page.evaluate(READ_JS)
        result.update(counters)
        result["reportRequests"] = sum(url.endswith("/api/report") for url in requests)
        report = result["resources"].get("/api/report", {})
        result["reportStart"], result["reportEnd"] = report.get("start"), report.get("end")
        assert result["elements"] > 10000, f"{self.label}: the report was not rendered"
        page.close()
        return result


KEYS = ("reportStart", "reportEnd", "first", "ready", "settled", *COUNTERS)


def compare(context: Any, live: Any, arms: list[Arm]) -> dict[str, dict[str, float]]:
    """Five fresh documents per arm, rotating which arm goes first."""
    samples: dict[str, list[dict]] = {arm.label: [] for arm in arms}
    for run in range(RUNS):
        for arm in arms[run % len(arms):] + arms[:run % len(arms)]:
            samples[arm.label].append(arm.sample(context, live))
    medians = {label: {key: median(s[key] for s in rows) for key in KEYS} for label, rows in samples.items()}
    base = medians[arms[0].label]
    for arm in arms:
        mine = medians[arm.label]
        rows = samples[arm.label]
        print(f"  {arm.label}: ready={mine['ready']:.1f}ms ({mine['ready'] - base['ready']:+.1f}); "
              f"settled={mine['settled']:.1f}ms ({mine['settled'] - base['settled']:+.1f}); "
              f"script={mine['ScriptDuration']:.1f} style={mine['RecalcStyleDuration']:.1f} "
              f"layout={mine['LayoutDuration']:.1f} task={mine['TaskDuration']:.1f}ms; "
              f"report {mine['reportStart']:.1f}-{mine['reportEnd']:.1f}ms; first group={mine['first']:.1f}ms; "
              f"elements={rows[0]['elements']}; report requests={sorted({s['reportRequests'] for s in rows})}; "
              f"ready samples={[round(s['ready'], 1) for s in rows]}")
    return medians


def timeline(context: Any, live: Any, slice_arm: Arm) -> None:
    print("-- 1. timeline, medians of 5 alternating fresh documents, ms from navigation start --")
    production = Arm("production", path="/")
    samples = {"slice": [], "production": []}
    for run in range(RUNS):
        for arm in ((slice_arm, production) if run % 2 == 0 else (production, slice_arm)):
            samples["slice" if arm is slice_arm else "production"].append(arm.sample(context, live))
    for name, rows in samples.items():
        files = sorted({path for row in rows for path in row["resources"] if not path.startswith("/api/")})
        loaded = "; ".join(f"{path} loaded={median(r['resources'][path]['end'] for r in rows):.1f}" for path in files)
        mid = {key: median(r[key] for r in rows) for key in ("html", *KEYS, "frame", "built")}
        print(f"  {name}: document={mid['html']:.1f}; {loaded}")
        print(f"  {name}: report request {mid['reportStart']:.1f} to {mid['reportEnd']:.1f}; "
              f"first group in document={mid['first']:.1f}; all groups in document={mid['built']:.1f}; "
              f"ready={mid['ready']:.1f}; next frame={mid['frame']:.1f}; settled={mid['settled']:.1f}")
        print(f"  {name}: before the report arrived={mid['reportEnd']:.1f}; "
              f"report arrival to ready={mid['ready'] - mid['reportEnd']:.1f}; "
              f"counters to settled: script={mid['ScriptDuration']:.1f} style={mid['RecalcStyleDuration']:.1f} "
              f"layout={mid['LayoutDuration']:.1f} task={mid['TaskDuration']:.1f}; elements={rows[0]['elements']}")


def regions(script: str) -> list[str]:
    """The module each line of an unminified bundle came from."""
    owner, current = [], ""
    for line in script.splitlines():
        if line.startswith("//#region "):
            current = line.removeprefix("//#region ").strip()
        elif line.startswith("//#endregion"):
            current = ""
        owner.append(current)
    return owner


def bucket(frame: dict, owner: list[str]) -> str:
    if not frame["url"]:
        return {"(garbage collector)": "garbage collection", "(idle)": "idle", "(program)": "browser, outside script",
                "(root)": "idle"}.get(frame["functionName"], "browser built-ins called from script")
    if not frame["url"].endswith("/assets/app.js"):
        return "other script (test instrumentation)"
    module = owner[frame["lineNumber"]] if 0 <= frame["lineNumber"] < len(owner) else ""
    for package in ("svelte", "tailwind-merge", "tailwind-variants", "clsx"):
        if f"node_modules/{package}/" in module:
            return f"package: {package}"
    return f"slice: {module.removeprefix('src/')}" if module.startswith("src/") else "bundle, no module marker"


def profile(context: Any, live: Any, files: dict[str, bytes]) -> None:
    print(f"-- 2. profile: unminified build of the same source, sampling every {INTERVAL_US} us, "
          f"medians of {RUNS} fresh documents; proportions, not timings --")
    owner = regions(files["assets/app.js"].decode("utf-8"))
    arm = Arm("unminified", files)
    selfs, inclusive = [], []
    for _ in range(RUNS):
        page, cdp, _requests = arm.open(context, live)
        cdp.send("Profiler.enable")
        cdp.send("Profiler.setSamplingInterval", {"interval": INTERVAL_US})
        cdp.send("Profiler.start")
        page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
        page.wait_for_function("() => __settled.navigation !== null")
        found = cdp.send("Profiler.stop")["profile"]
        page.close()
        nodes = {node["id"]: node for node in found["nodes"]}
        parent = {child: node["id"] for node in found["nodes"] for child in node.get("children", [])}
        by_bucket: dict[str, float] = defaultdict(float)
        by_component: dict[str, float] = defaultdict(float)
        for node_id, micros in zip(found["samples"], found["timeDeltas"]):
            by_bucket[bucket(nodes[node_id]["callFrame"], owner)] += micros / 1000
            seen, walk = set(), node_id
            while walk is not None:
                frame = nodes[walk]["callFrame"]
                module = owner[frame["lineNumber"]] if frame["url"].endswith("/assets/app.js") else ""
                name = frame["functionName"]
                if module.startswith("src/") and module.endswith(".svelte") and name.lower() == Path(module).stem.lower():
                    seen.add(name)
                walk = parent.get(walk)
            for name in seen:
                by_component[name] += micros / 1000
        selfs.append(by_bucket)
        inclusive.append(by_component)
    for title, rows in (("self time by where the function came from", selfs),
                        ("inclusive time under each component", inclusive)):
        print(f"  {title}:")
        keys = sorted({key for row in rows for key in row}, key=lambda key: -median(row.get(key, 0) for row in rows))
        for key in keys:
            value = median(row.get(key, 0) for row in rows)
            if value >= 0.5 and key != "idle":
                print(f"    {value:7.1f} ms  {key}")


def same_document(context: Any, live: Any, base: Arm, other: Arm, boxes: bool) -> str:
    """Whether a variant renders what the unchanged build renders."""
    read = []
    for arm in (base, other):
        page, _cdp, _requests = arm.open(context, live)
        page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
        page.wait_for_function("() => __settled.navigation !== null")
        read.append((page.evaluate(SHAPE_JS), page.evaluate(BOXES_JS) if boxes else ""))
        page.close()
    return f"markup equal (comment anchors ignored)={read[0][0] == read[1][0]}" + (
        f"; every element's box equal={read[0][1] == read[1][1]}" if boxes else "")


def main() -> int:
    if sys.argv[1:]:
        print("RESULT: FAIL (no arguments accepted)")
        return 1
    failures: list[str] = []
    harness.require_build()
    served = {name: (FRONTEND / "dist" / name).read_bytes() for name in FILES.values()}
    print("fixture: tests/fixtures/real/2026-09-01T-current/armor.csv; viewport 1440x1000 light")
    with harness.live_spike() as live, harness.chromium() as browser:
        preload(live, "real")
        context = harness.authenticated_context(browser, live)
        context.add_init_script("window.__scaleGroups = 74;\n" + TIMING_JS + SETTLED_JS + FIRST_JS)
        unchanged = Arm("unchanged", served)

        print("-- 0. what interception adds: each page with and without it --")
        compare(context, live, [
            unchanged,
            Arm("slice, not intercepted", routed=False),
            Arm("production", path="/"),
            Arm("production, not intercepted", path="/", routed=False),
        ])

        timeline(context, live, unchanged)

        with harness.frontend_copy() as copy:
            profile(context, live, build(copy, copy / "dist-unminified", minify=False))

        page, _cdp, _requests = unchanged.open(context, live)
        page.goto(live.origin + "/spike/", wait_until="domcontentloaded")
        page.wait_for_function("() => __settled.navigation !== null")
        markup = page.evaluate(MARKUP_JS).encode("utf-8")
        widths = page.evaluate("() => [...new Set(Array.from(document.querySelectorAll('article[data-group]'))"
                               ".map((group) => group.clientWidth))]")
        page.close()
        print("-- 3. floor: the slice's own markup and stylesheet, no framework --")
        print(f"  captured markup: {len(markup)} bytes; assigned once the same report request has answered")
        floor = Arm("floor", {"assets/app.js": FLOOR_JS.encode("utf-8")}, floor=markup)
        production = Arm("production", path="/")
        print("  " + same_document(context, live, unchanged, floor, boxes=True))
        medians = compare(context, live, [unchanged, floor, production])
        if medians["floor"]["ready"] >= medians["unchanged"]["ready"]:
            failures.append("the floor was not faster than the slice, so it is not a floor")

        print("-- 4. ablations: one suspected cause removed, against the unchanged build --")
        arms = [unchanged]
        for name in (*SOURCE_ABLATIONS, "value-inline"):
            with harness.frontend_copy() as copy:
                print(f"  {name}: {SOURCE_ABLATIONS[name][0] if name in SOURCE_ABLATIONS else 'no Value component'}")
                ablated_source(copy, name)
                files = build(copy, copy / "dist")
            arm = Arm(name, files)
            print(f"  {name}: app.js {len(files['assets/app.js'])} bytes sha256={sha(files['assets/app.js'])}; "
                  + same_document(context, live, unchanged, arm, boxes=False))
            arms.append(arm)
        if len(widths) != 1:
            failures.append(f"groups have more than one width at 1440 px: {widths}")
        css, resolved = static_containers(served["assets/app.css"].decode("utf-8"), widths[0])
        static = Arm("no-container-queries", {"assets/app.css": css.encode("utf-8")})
        print(f"  no-container-queries: {resolved} container rules and declarations resolved for a "
              f"{widths[0]} px group; " + same_document(context, live, unchanged, static, boxes=True))
        arms.append(static)
        html = served["index.html"].decode("utf-8")
        if html.count("</head>") != 1:
            failures.append("index.html has no single </head>")
        hinted = Arm("report-preload", {"index.html": html.replace("</head>", PRELOAD).encode("utf-8")})
        print("  report-preload: a preload hint for /api/report in index.html; "
              + same_document(context, live, unchanged, hinted, boxes=False))
        arms.append(hinted)
        compare(context, live, arms)
        def floor_with(label: str, sheet: str) -> Arm:
            return Arm(label, {"assets/app.js": FLOOR_JS.encode("utf-8"), "assets/app.css": sheet.encode("utf-8")},
                       floor=markup)

        sheet = served["assets/app.css"].decode("utf-8")
        print("  the floor again with stylesheet ablations, beside production. The two layout")
        print("  ablations change the page's geometry: they measure the grid, they are not candidates:")
        compare(context, live, [
            floor,
            floor_with("floor + no-container-queries", css),
            floor_with("floor + comparison grid as blocks", sheet + MATRIX_BLOCK),
            floor_with("floor + every grid as blocks", sheet + GRIDS_BLOCK),
            floor_with("floor + no-container-queries + every grid as blocks", css + GRIDS_BLOCK),
            production,
        ])
        context.close()
    return harness.finish(failures)


if __name__ == "__main__":
    sys.exit(main())
