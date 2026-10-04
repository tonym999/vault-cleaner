"""S12: code comparison, dependency tree and licence scan.

No browser.  Three parts:

1. Non-blank line counts for the slice by category, beside the production
   JavaScript the slice replaces (the six ranges #137 identified, checked
   again at this head) and the Jinja hybrid's figures from #137's evidence.
2. The npm tree: package count against the lockfile, and ``npm audit``.
3. Licences.  Every package in the tree ``npm ci`` installed, read from the
   installed ``package.json`` files (and a ``LICENSE`` file where the field
   is missing), must be MIT, Apache-2.0, BSD or ISC, or MPL-2.0.  Then every
   package that contributes to the **built output** must be MIT, Apache-2.0,
   BSD or ISC: the JavaScript modules are taken from the list the bundler
   wrote (``dist/modules.json``), and the stylesheet's sources from the
   ``@import`` and ``@plugin`` lines of the CSS entry file in that list.
   That stylesheet half is a text match on the entry file: Tailwind inlines
   its imports itself, so the bundler has no finer list, and a package pulled
   in by an imported stylesheet rather than by ``app.css`` would not be seen.

    .venv/bin/python spikes/issue-206/proof_s12_code.py
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from harness import FRONTEND, REPO, SPIKE_DIR, finish, main_guard, require_build

UI = REPO / "src" / "vault_cleaner" / "ui"
# The production code the Armor duplicates slice replaces (#137, section 5).
PRODUCTION_RANGES = (
    ("review_ui.js", 304, 624, ""),
    ("review_ui.js", 804, 844, ""),
    ("review_ui.js", 1201, 1648, "function dispositionLabel"),
    ("review_ui.js", 1773, 1788, ""),
    ("review_ui.js", 1790, 1815, ""),
    ("review_server.js", 1376, 1431, ""),
)
HYBRID_CLAIM = "93 lines of fragment seam and 62 lines of browser-owned filtering in JavaScript, a 474-line Python context builder and 187 lines of templates"
SLICE = (
    ("components and markup", ["frontend/src/App.svelte", "frontend/src/components/*.svelte", "frontend/index.html"]),
    ("presentation projection (wording, shared/differing split)", ["frontend/src/lib/view.ts"]),
    ("application logic (requests, revisions, reconciliation, lifecycle)",
     ["frontend/src/lib/session.svelte.ts", "frontend/src/lib/api.ts", "frontend/src/main.ts"]),
    ("filtering", ["frontend/src/lib/filters.ts"]),
    ("types", ["frontend/src/lib/envelope.ts"]),
    ("stylesheet", ["frontend/src/app.css"]),
    ("Python: serving the build", ["spike_app.py"]),
)
NOT_SHIPPED = (
    ("unit tests and the type-contract module", ["frontend/src/lib/*.test.ts", "frontend/src/contract/samples.ts"]),
    ("build configuration", ["frontend/vite.config.ts", "frontend/tsconfig.json", "frontend/svelte.config.js"]),
    ("Python: contract sample generator", ["contract.py"]),
)
BUNDLED_OK = re.compile(r"^(MIT|Apache-2\.0|ISC|BSD-2-Clause|BSD-3-Clause|0BSD)$")
BUILD_ONLY_OK = re.compile(r"^(MIT|Apache-2\.0|ISC|BSD-2-Clause|BSD-3-Clause|0BSD|MPL-2\.0)$")


def lines(patterns: list[str]) -> tuple[int, int]:
    files = sorted(path for pattern in patterns for path in SPIKE_DIR.glob(pattern))
    total = sum(
        1 for path in files for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    return total, len(files)


def licence_of(package: Path) -> str:
    data = json.loads((package / "package.json").read_text(encoding="utf-8"))
    declared = data.get("license")
    if isinstance(declared, str) and declared:
        return declared
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "license"):
        if (package / name).is_file():
            head = (package / name).read_text(encoding="utf-8", errors="replace")[:200]
            if "MIT License" in head:
                return "MIT"
    return "UNKNOWN"


def installed(root: Path) -> dict[str, tuple[str, str]]:
    """lockfile-style path -> (name@version, licence), for every installed package."""
    found: dict[str, tuple[str, str]] = {}

    def walk(directory: Path) -> None:
        for entry in sorted(directory.iterdir()):
            if entry.name.startswith(".") or not entry.is_dir():
                continue
            if entry.name.startswith("@"):
                walk(entry)
                continue
            manifest = entry / "package.json"
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                key = entry.relative_to(root.parent).as_posix()
                found[key] = (f"{data['name']}@{data['version']}", licence_of(entry))
            if (entry / "node_modules").is_dir():
                walk(entry / "node_modules")

    walk(root)
    return found


def package_of(module: str) -> Path | None:
    """The package directory a bundled module id belongs to, or None for the slice."""
    if "node_modules/" not in module:
        return None
    head, tail = module.rsplit("node_modules/", 1)
    parts = tail.split("/")
    name = "/".join(parts[:2]) if parts[0].startswith("@") else parts[0]
    return FRONTEND / head / "node_modules" / name


def scan_tree(label: str, project: Path, failures: list[str]) -> None:
    tree = installed(project / "node_modules")
    lock = json.loads((project / "package-lock.json").read_text(encoding="utf-8"))["packages"]
    locked = {key: value for key, value in lock.items() if key}
    mismatched = [
        key for key, (name, _licence) in tree.items()
        if key not in locked or f"{name.rsplit('@', 1)[0]}@{locked[key]['version']}" != name
    ]
    absent = sorted(set(locked) - set(tree))
    absent_licences = Counter(locked[key].get("license", "UNKNOWN") for key in absent)
    print(f"{label}: {len(tree)} packages installed; {len(locked)} in the lockfile; installed but "
          f"not as locked: {mismatched}; locked but not installed here (other platforms' optional "
          f"binaries): {len(absent)}, all optional={all(locked[k].get('optional') for k in absent)}, "
          f"lockfile licences {dict(absent_licences)}")
    print(f"  licences in the installed tree: {dict(sorted(Counter(l for _n, l in tree.values()).items()))}")
    outside = sorted(name for name, licence in tree.values() if not BUILD_ONLY_OK.match(licence))
    mpl = sorted(name for name, licence in tree.values() if licence == "MPL-2.0")
    print(f"  MPL-2.0 (accepted for build-time-only use): {mpl}")
    print(f"  outside the approved licences: {outside}")
    banned = sorted(name for name, _l in tree.values() if name.startswith(("apexcharts@", "flowbite")))
    print(f"  apexcharts or Flowbite installed: {banned}")
    if mismatched or outside or banned or not all(locked[k].get("optional") for k in absent) or any(
        not BUILD_ONLY_OK.match(licence) for licence in absent_licences
    ):
        failures.append(f"{label}: the tree is not the lockfile's, or holds an unapproved licence")


def main() -> int:
    failures: list[str] = []
    require_build()

    print("-- lines (non-blank) --")
    production = 0
    for name, first, last, expected in PRODUCTION_RANGES:
        text = (UI / name).read_text(encoding="utf-8").splitlines()
        found = expected in text[first - 1]
        production += last - first + 1
        if not found:
            failures.append(f"{name}:{first} is not {expected}")
    print(f"production JavaScript the slice replaces: {production} lines in "
          f"{len(PRODUCTION_RANGES)} ranges (anchors found: {not failures})")
    evidence = (REPO / "docs" / "evidence" / "issue-137" / "README.md").read_text(encoding="utf-8")
    print(f"Jinja hybrid (#137 evidence, quoted): {HYBRID_CLAIM}: quote found={HYBRID_CLAIM in evidence}")
    if HYBRID_CLAIM not in evidence:
        failures.append("the hybrid's figures are no longer what #137's evidence says")
    shipped = 0
    for label, patterns in SLICE:
        total, files = lines(patterns)
        shipped += total
        print(f"slice, {label}: {total} lines in {files} files")
    print(f"slice, everything that runs or is served: {shipped} lines")
    for label, patterns in NOT_SHIPPED:
        total, files = lines(patterns)
        print(f"slice, {label}: {total} lines in {files} files")
    proofs, proof_files = lines(["proof_*.py", "expected.py", "harness.py", "focus_contrast.py", "check_source.py",
                                 "wheel_server.py", "dev.py", "serve.py"])
    print(f"proof and tooling scripts (not part of any comparison): {proofs} lines in {proof_files} files")
    imperative = sum(
        len(re.findall(r"createElement|appendChild|\.textContent\s*=|setAttribute|innerHTML|\bel\(", path.read_text(encoding="utf-8")))
        for path in (FRONTEND / "src").rglob("*") if path.suffix in {".ts", ".svelte"} and ".test." not in path.name
    )
    theirs = sum(
        len(re.findall(r"createElement|appendChild|\.textContent\s*=|setAttribute|innerHTML|\bel\(", "\n".join(
            (UI / name).read_text(encoding="utf-8").splitlines()[first - 1:last])))
        for name, first, last, _expected in PRODUCTION_RANGES
    )
    print(f"imperative DOM calls (createElement, el(), appendChild, textContent=, setAttribute): "
          f"slice {imperative}; the production ranges {theirs}")

    print("-- npm tree and audit --")
    scan_tree("frontend", FRONTEND, failures)
    if (SPIKE_DIR / "probes" / "node_modules").is_dir():
        scan_tree("probes", SPIKE_DIR / "probes", failures)
    else:
        print("probes: not installed, not scanned")
    manifest = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))
    print(f"frontend direct dependencies: runtime {len(manifest.get('dependencies', {}))}, "
          f"development {len(manifest['devDependencies'])}; every version exact: "
          f"{all(re.fullmatch(r'[0-9][0-9A-Za-z.+-]*', v) for v in manifest['devDependencies'].values())}")
    audit = subprocess.run(["npm", "audit", "--json"], cwd=FRONTEND, capture_output=True, text=True, check=False)
    try:
        vulnerabilities = json.loads(audit.stdout)["metadata"]["vulnerabilities"]
        print(f"npm audit: {vulnerabilities}")
        if vulnerabilities["total"]:
            failures.append("npm audit reports a vulnerability")
    except (json.JSONDecodeError, KeyError):
        print(f"npm audit did not answer (exit {audit.returncode}); not measured")
        failures.append("npm audit could not be run")

    print("-- what is in the built output --")
    listing = (FRONTEND / "dist" / "modules.json").read_text(encoding="utf-8")
    modules = json.loads(listing)
    listed = [module for ids in modules["outputs"].values() for module in ids] + modules["css"]
    relative = not any(module.startswith("/") or ":\\" in module for module in listed)
    print(f"dist/modules.json: {len(listing.encode())} bytes; every path relative to frontend/: {relative}")
    if not relative:
        failures.append("modules.json holds an absolute path")
    contributing: dict[str, tuple[str, int]] = {}
    own = 0
    for output, ids in modules["outputs"].items():
        for module in ids:
            package = package_of(module.split("?")[0])
            if package is None:
                own += 1
                continue
            data = json.loads((package / "package.json").read_text(encoding="utf-8"))
            name = f"{data['name']}@{data['version']}"
            contributing[name] = (licence_of(package), contributing.get(name, ("", 0))[1] + 1)
        print(f"{output}: {len(ids)} modules, {own} of them the slice's own source")
    css_sources: list[str] = []
    for entry in modules["css"]:
        text = (FRONTEND / entry).read_text(encoding="utf-8")
        css_sources += re.findall(r'@(?:import|plugin)\s+"([^"./][^"]*)"', text)
        print(f"assets/app.css: built from {entry}, which pulls in {css_sources}")
    for name in css_sources:
        package = FRONTEND / "node_modules" / name
        data = json.loads((package / "package.json").read_text(encoding="utf-8"))
        contributing[f"{data['name']}@{data['version']}"] = (licence_of(package), 0)
    for name, (licence, count) in sorted(contributing.items()):
        print(f"  contributes to the output: {name} ({licence})" + (f", {count} modules" if count else ", stylesheet"))
        if not BUNDLED_OK.match(licence):
            failures.append(f"{name} is in the built output under {licence}")
    built = "".join(
        (FRONTEND / "dist" / name).read_text(encoding="utf-8")
        for name in ("index.html", "assets/app.js", "assets/app.css")
    )
    traces = [token for token in ("lightningcss", "Mozilla Public", "MPL-2", "axe-core", "axe.run") if token in built]
    print(f"MPL-2.0 packages contributing to the output: "
          f"{[n for n, (l, _c) in contributing.items() if l == 'MPL-2.0']}; traces of lightningcss or "
          f"axe-core in the built files: {traces}")
    if traces:
        failures.append("an MPL-2.0 package left a trace in the build")
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
