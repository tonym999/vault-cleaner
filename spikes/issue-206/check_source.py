"""The slice's source rules, checked over the files themselves (#206).

No browser.  It scans ``frontend/src`` (tests and contract samples excluded
where a rule is about shipped code) and, when a build exists, the build
output.

    .venv/bin/python spikes/issue-206/check_source.py

Rules, from the plan:

* no ``{@html}``, ``innerHTML``, ``outerHTML``, ``insertAdjacentHTML``,
  ``eval`` or ``new Function``;
* no numeric conversion anywhere in shipped source (``Number(``,
  ``parseInt``, ``parseFloat``, and no unary ``+`` on an ``id`` or ``hash``),
  and ``id``/``hash`` fields are typed ``string``;
* no hand-written ``style`` attribute or ``style:`` directive;
* no remote URL in source; in the build, no URL that the page would load;
* direct DOM access only at the listed, justified places.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
SOURCE = SPIKE_DIR / "frontend" / "src"
DIST = SPIKE_DIR / "frontend" / "dist"

FORBIDDEN = {
    "raw HTML": re.compile(r"\{@html|innerHTML|outerHTML|insertAdjacentHTML|DOMParser|document\.write"),
    "code from strings": re.compile(r"\beval\s*\(|new\s+Function\b|setTimeout\s*\(\s*['\"`]"),
    "numeric conversion": re.compile(
        r"\bNumber\s*\(|\bparseInt\b|\bparseFloat\b|\bBigInt\s*\(|[=(,:?]\s*\+\s*[\w.]*\b(?:id|hash)\b"
    ),
    "hand-written inline style": re.compile(r"\bstyle\s*=|\bstyle:[\w-]+"),
    "remote URL": re.compile(r"https?://"),
}
# Direct DOM access and effects.  Each allowed place is named with its reason.
DOM = re.compile(
    r"\$effect|\bdocument\.|\bwindow\.|querySelector|createElement|appendChild|"
    r"\.focus\(|bind:this|\buse:\w|\.classList|\.setAttribute|\.textContent"
)
ALLOWED_DOM = {
    ("main.ts", "document.getElementById"): "the mount point, once at start-up",
    ("App.svelte", "$effect"): "focus policy on a report change (the slice's only effects: one before, one after the DOM change)",
    ("App.svelte", "document.activeElement"): "focus policy: has focus fallen to <body>?",
    ("App.svelte", "document.body"): "focus policy: has focus fallen to <body>?",
    ("App.svelte", ".focus("): "focus policy: move focus to the list heading",
    ("App.svelte", "bind:this"): "focus policy: the list, and its heading to focus",
}
ID_TYPES = re.compile(r"^\s*(?:\w*_)?(id|hash|group_id|preferred_survivor_id|selected_partner_id)\??:\s*([^;]+);", re.MULTILINE)
# URL strings that are in the build as text and are never requested.
INERT_URL = re.compile(
    r"https?://(?:www\.w3\.org/(?:1999/xhtml|2000/svg|1998/Math/MathML|1999/xlink)|svelte\.dev/e/[\w_]+|tailwindcss\.com)\b"
)
LOADING = re.compile(r"url\(\s*['\"]?\s*(?:https?:|//)|@import\s|@font-face|\bsrc\s*=\s*['\"]https?:")


def shipped(path: Path) -> bool:
    return not path.name.endswith(".test.ts") and "contract" not in path.parts


def main() -> int:
    failures: list[str] = []
    files = sorted(path for path in SOURCE.rglob("*") if path.suffix in {".ts", ".svelte", ".css"})
    code = [path for path in files if shipped(path)]
    print(f"shipped source files scanned: {len(code)}; test and contract files: {len(files) - len(code)}")

    for label, pattern in FORBIDDEN.items():
        hits = [
            f"{path.relative_to(SOURCE)}:{number}"
            for path in code
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if pattern.search(line)
        ]
        print(f"{label}: {len(hits)} {hits if hits else ''}".rstrip())
        if hits:
            failures.append(f"{label} in shipped source")

    types = (SOURCE / "lib" / "envelope.ts").read_text(encoding="utf-8")
    declared = ID_TYPES.findall(types)
    wrong = [(name, kind) for name, kind in declared if kind.replace(" | null", "") != "string"]
    print(f"id and hash fields declared in envelope.ts: {len(declared)}, all string: {not wrong}")
    if wrong or len(declared) < 8:
        failures.append(f"an id or hash field is not typed string: {wrong}")

    print("-- direct DOM access and effects in shipped source --")
    seen: set[tuple[str, str]] = set()
    for path in code:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("//"):
                continue
            for match in DOM.finditer(line):
                token = match.group(0)
                if token == "document.":
                    token = re.search(r"document\.\w+", line[match.start():]).group(0)
                key = (path.name, token)
                reason = ALLOWED_DOM.get(key)
                print(f"{path.relative_to(SOURCE)}:{number} {token}: {reason or 'NOT LISTED'}")
                seen.add(key)
                if reason is None:
                    failures.append(f"unlisted DOM access {token} at {path.name}:{number}")
    if seen != set(ALLOWED_DOM):
        failures.append(f"listed DOM exceptions not found: {sorted(set(ALLOWED_DOM) - seen)}")

    print("-- ordering computed in the browser --")
    for path in code:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\.sort\(|\.toSorted\(|\.reverse\(", line):
                print(f"{path.relative_to(SOURCE)}:{number} {line.strip()}")

    if not (DIST / "index.html").is_file():
        print("FAIL: no build to scan; run `npm ci && npm run build` in frontend/")
        failures.append("no build output")
    else:
        print("-- build output --")
        for path in sorted(p for p in DIST.rglob("*") if p.suffix in {".html", ".js", ".css"}):
            text = path.read_text(encoding="utf-8")
            urls = sorted(set(re.findall(r"https?://[\w./#?=&%-]+", text)))
            loaded = [url for url in urls if not INERT_URL.match(url)]
            loading = sorted(set(LOADING.findall(text)))
            data_uris = re.findall(r"[\w-]+:url\(\"data:[a-z]+/[\w+]+", text)
            print(f"{path.relative_to(DIST)}: {len(text.encode('utf-8'))} bytes; URL strings {len(urls)} "
                  f"(XML namespaces, Svelte error-message links, a Tailwind banner); "
                  f"URLs the page would load: {loaded}; data: URIs: {data_uris}; "
                  f"@import/@font-face/remote url(): {loading}")
            if loaded or loading:
                failures.append(f"{path.name} references something outside the build")
            if data_uris and (data_uris != ['--fx-noise:url("data:image/svg+xml']
                              or "--fx-noise:none" not in text):
                failures.append(f"{path.name} uses a data: URI other than the overridden noise texture")
            if data_uris:
                print("  the one data: URI is daisyUI's --fx-noise definition; the same file "
                      f"overrides it with --fx-noise:none: {'--fx-noise:none' in text}")
        html = (DIST / "index.html").read_text(encoding="utf-8")
        inline = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>|<style\b|\sstyle=|\son\w+=", html)
        print(f"index.html inline scripts, style elements, style or event attributes: {inline}")
        if inline:
            failures.append("index.html has inline script or style")

    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT: " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
