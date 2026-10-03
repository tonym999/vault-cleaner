"""E7: templates render and serve from an installed, non-editable wheel.

Modelled on ``scripts/check_wheel_install.py`` and reusing its helpers.  It
copies the tracked source to a temporary tree, overlays the spike's templates
at the proposed production location, builds wheels and inspects them, then
installs one into a fresh environment and runs ``wheel_probe.py`` there.

Three layouts are built:

* nested ``ui/templates/`` with today's ``package-data`` (expected: omitted);
* nested ``ui/templates/`` with ``"templates/*.html"`` added to it;
* flat, next to the existing resources in ``ui/``, with today's setting.

Nothing in the repository is changed: the ``pyproject.toml`` edit is made in
the temporary copy.

    .venv/bin/python spikes/issue-137/proof_e7_wheel.py
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

from render_env import SPIKE_TEMPLATES, TEMPLATE_NAMES

SPIKE_DIR = Path(__file__).resolve().parent
REPO = SPIKE_DIR.parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "armor_close.csv"
CURRENT = '"vault_cleaner.ui" = ["*.css", "*.html", "*.js"]'
PROPOSED = '"vault_cleaner.ui" = ["*.css", "*.html", "*.js", "templates/*.html"]'
MARKER = "<!-- rendered from the installed wheel -->"
EDITABLE_CHECK = (
    "import importlib.metadata as m; d = m.distribution('vault-cleaner');"
    "print('editable' in (d.read_text('direct_url.json') or ''))"
)


def load_wheel_script():
    spec = importlib.util.spec_from_file_location(
        "check_wheel_install", REPO / "scripts" / "check_wheel_install.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def overlay(source: Path, *, nested: bool, package_data: str) -> None:
    ui = source / "src" / "vault_cleaner" / "ui"
    target = ui / "templates" if nested else ui
    target.mkdir(exist_ok=True)
    for name in TEMPLATE_NAMES:
        text = (SPIKE_TEMPLATES / name).read_text(encoding="utf-8")
        if name == "armor_duplicates.html":
            text += MARKER + "\n"
        (target / name).write_text(text, encoding="utf-8")
    pyproject = source / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    if text.count(CURRENT) != 1:
        raise RuntimeError("pyproject.toml no longer has the package-data line the proof expects")
    pyproject.write_text(text.replace(CURRENT, package_data), encoding="utf-8")


def build(script, temp: Path, label: str, *, nested: bool, package_data: str) -> tuple[Path, list[str]]:
    source = temp / f"source-{label}"
    wheelhouse = temp / f"wheelhouse-{label}"
    source.mkdir()
    wheelhouse.mkdir()
    script.copy_tracked_source(source)
    overlay(source, nested=nested, package_data=package_data)
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps", "--wheel-dir",
         str(wheelhouse), str(source)],
        cwd=source, env=script.clean_environment(), check=True, capture_output=True,
    )
    (wheel,) = wheelhouse.glob("vault_cleaner-*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = sorted(name for name in archive.namelist() if name.startswith("vault_cleaner/ui/"))
    return wheel, names


def main() -> int:
    failures: list[str] = []
    script = load_wheel_script()
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-137-wheel-") as raw:
        temp = Path(raw)

        print("-- nested ui/templates/, package-data as it is today --")
        print(f"package-data: {CURRENT}")
        _wheel, names = build(script, temp, "nested-current", nested=True, package_data=CURRENT)
        packaged = [name for name in names if name.startswith("vault_cleaner/ui/templates/")]
        print(f"wheel files under vault_cleaner/ui/: {names}")
        print(f"templates in the wheel: {len(packaged)} of {len(TEMPLATE_NAMES)}")
        if packaged:
            failures.append("today's package-data unexpectedly packaged nested templates")

        print("-- nested ui/templates/, proposed package-data --")
        print(f"package-data: {PROPOSED}")
        wheel, names = build(script, temp, "nested-proposed", nested=True, package_data=PROPOSED)
        packaged = [name for name in names if name.startswith("vault_cleaner/ui/templates/")]
        print(f"templates in the wheel: {packaged}")
        if len(packaged) != len(TEMPLATE_NAMES):
            failures.append("the proposed package-data did not package every template")

        environment = temp / "environment"
        run_dir = temp / "run"
        run_dir.mkdir()
        venv.EnvBuilder(with_pip=True).create(environment)
        python = script.environment_python(environment)
        subprocess.run(
            [str(python), "-m", "pip", "install", "--quiet", str(wheel)],
            cwd=run_dir, env=script.clean_environment(), check=True, capture_output=True,
        )
        direct_url = subprocess.run(
            [str(python), "-c",
             EDITABLE_CHECK],
            cwd=run_dir, env=script.clean_environment(), check=True, capture_output=True, text=True,
        ).stdout.strip()
        print(f"installed into a fresh environment; editable install: {direct_url}")
        probe = subprocess.run(
            [str(python), str(SPIKE_DIR / "wheel_probe.py"), str(SPIKE_DIR), str(FIXTURE),
             str(REPO.resolve()), str(environment.resolve()), MARKER],
            cwd=run_dir, env=script.clean_environment(), capture_output=True, text=True,
            check=False,
        )
        print(probe.stdout.rstrip())
        if probe.returncode != 0:
            failures.append("the probe failed inside the installed environment")
            print(probe.stderr.rstrip())

        print("-- flat, beside the existing ui/ resources, package-data as it is today --")
        _wheel, names = build(script, temp, "flat-current", nested=False, package_data=CURRENT)
        flat = [name for name in names if Path(name).name in TEMPLATE_NAMES]
        print(f"templates in the wheel: {len(flat)} of {len(TEMPLATE_NAMES)}; "
              f"files now directly under vault_cleaner/ui/: {len(names)}")
        if len(flat) != len(TEMPLATE_NAMES):
            failures.append("the flat layout did not package every template")
        shutil.rmtree(temp / "source-flat-current")

    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT: " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
