"""Prove the packaged server UI works from a non-editable wheel install."""

from __future__ import annotations

import http.cookiejar
import os
import queue
import subprocess
import sys
import tempfile
import threading
import urllib.request
import venv
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ASSETS = {
    "/": "text/html; charset=utf-8",
    "/assets/review.css": "text/css; charset=utf-8",
    "/assets/review_ui.js": "text/javascript; charset=utf-8",
    "/assets/review_server.js": "text/javascript; charset=utf-8",
}
START_TIMEOUT_SECONDS = 30
HTTP_TIMEOUT_SECONDS = 10
STOP_TIMEOUT_SECONDS = 10


def environment_python(environment: Path) -> Path:
    """Return the interpreter created by ``venv`` on this platform."""
    scripts = "Scripts" if os.name == "nt" else "bin"
    executable = "python.exe" if os.name == "nt" else "python"
    return environment / scripts / executable


def environment_cli(environment: Path) -> Path:
    """Return the installed console script path on this platform."""
    scripts = "Scripts" if os.name == "nt" else "bin"
    executable = "vault-cleaner.exe" if os.name == "nt" else "vault-cleaner"
    return environment / scripts / executable


def clean_environment() -> dict[str, str]:
    """Remove source-path escape hatches inherited by child interpreters."""
    child = os.environ.copy()
    child.pop("PYTHONPATH", None)
    child["PYTHONNOUSERSITE"] = "1"
    return child


def run_checked(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=cwd, env=env, check=True)


def first_output_line(
    process: subprocess.Popen[str], *, timeout: int = START_TIMEOUT_SECONDS
) -> str:
    """Read the server's bootstrap line without an unbounded pipe wait."""
    assert process.stdout is not None
    result: queue.Queue[str] = queue.Queue(maxsize=1)
    reader = threading.Thread(
        target=lambda: result.put(process.stdout.readline()),
        name="wheel-proof-bootstrap-reader",
        daemon=True,
    )
    reader.start()
    try:
        line = result.get(timeout=timeout)
    except queue.Empty as error:
        raise RuntimeError("installed server did not print a bootstrap URL") from error
    if line:
        return line.strip()
    if process.poll() is None:
        raise RuntimeError("installed server closed stdout without exiting")
    stderr = process.stderr.read() if process.stderr is not None else ""
    raise RuntimeError(
        f"installed server exited before printing a bootstrap URL: {stderr.strip()}"
    )


def stop_process(process: subprocess.Popen[str]) -> None:
    """Bound cleanup even when the installed server fails midway."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=STOP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=STOP_TIMEOUT_SECONDS)


def assert_bootstrap_url(url: str) -> None:
    parsed = urlsplit(url)
    tokens = parse_qs(parsed.query, strict_parsing=True).get("token", [])
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port in (None, 0)
        or parsed.path != "/bootstrap"
        or len(tokens) != 1
    ):
        raise RuntimeError(f"installed server printed an invalid bootstrap URL: {url}")


def verify_http_assets(bootstrap_url: str) -> None:
    parsed = urlsplit(bootstrap_url)
    origin = f"http://{parsed.netloc}"
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )
    with opener.open(bootstrap_url, timeout=HTTP_TIMEOUT_SECONDS) as response:
        root = response.read()
        if response.status != 200 or response.geturl() != f"{origin}/":
            raise RuntimeError("bootstrap did not reach the authenticated root page")
        if response.headers.get("Content-Type") != EXPECTED_ASSETS["/"]:
            raise RuntimeError("installed root page has the wrong content type")

    required_references = (
        b'href="/assets/review.css"',
        b'src="/assets/review_ui.js"',
        b'src="/assets/review_server.js"',
    )
    if not root or not all(reference in root for reference in required_references):
        raise RuntimeError("installed root page does not reference every required asset")

    for path, expected_content_type in EXPECTED_ASSETS.items():
        if path == "/":
            continue
        with opener.open(origin + path, timeout=HTTP_TIMEOUT_SECONDS) as response:
            body = response.read()
            if response.status != 200:
                raise RuntimeError(f"installed asset returned HTTP {response.status}: {path}")
            if response.headers.get("Content-Type") != expected_content_type:
                raise RuntimeError(f"installed asset has the wrong content type: {path}")
            if not body:
                raise RuntimeError(f"installed asset is empty: {path}")


def main() -> int:
    child_env = clean_environment()
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-wheel-proof-") as raw_temp:
        temp = Path(raw_temp)
        wheelhouse = temp / "wheelhouse"
        wheelhouse.mkdir()
        run_dir = temp / "run"
        run_dir.mkdir()
        environment = temp / "environment"

        run_checked(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--wheel-dir",
                str(wheelhouse),
                ".",
            ],
            cwd=ROOT,
            env=child_env,
        )
        wheels = list(wheelhouse.glob("vault_cleaner-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one vault-cleaner wheel, found {len(wheels)}")

        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment_python(environment)
        run_checked(
            [str(python), "-m", "pip", "install", str(wheels[0])],
            cwd=run_dir,
            env=child_env,
        )
        origin = subprocess.run(
            [
                str(python),
                "-c",
                (
                    "import pathlib, vault_cleaner; "
                    "print(pathlib.Path(vault_cleaner.__file__).resolve())"
                ),
            ],
            cwd=run_dir,
            env=child_env,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        if str(ROOT.resolve()) in origin or str(environment.resolve()) not in origin:
            raise RuntimeError(f"isolated interpreter imported an unexpected package: {origin}")

        config = run_dir / "config.toml"
        config.write_text("", encoding="utf-8")
        process = subprocess.Popen(
            [
                str(environment_cli(environment)),
                "serve",
                "--no-wishlists",
                "--port",
                "0",
                "--config",
                str(config),
                "--overrides",
                str(run_dir / "overrides.json"),
            ],
            cwd=run_dir,
            env=child_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            bootstrap_url = first_output_line(process)
            assert_bootstrap_url(bootstrap_url)
            verify_http_assets(bootstrap_url)
        finally:
            stop_process(process)

        print(f"built non-editable wheel: {wheels[0].name}")
        print(f"isolated package origin: {origin}")
        print("verified installed root HTML and all three allow-listed UI assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
