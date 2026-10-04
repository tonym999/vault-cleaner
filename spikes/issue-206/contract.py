"""Envelope samples for the frontend's type contract (#206).

The TypeScript types in ``frontend/src/lib/envelope.ts`` are hand-written.
This script asks the real server for envelopes built from a fake fixture and
writes them to ``frontend/src/contract/``, where ``samples.ts`` assigns them
to those types.  A field the Python side renames, removes or retypes then
fails the frontend's type check.

    .venv/bin/python spikes/issue-206/contract.py           # rewrite the samples
    .venv/bin/python spikes/issue-206/contract.py --check   # fail if they are stale

Two samples: ``reviewing.json`` (a report with two verdicts) and
``finalized.json`` (the same session after ``POST /api/finalize``, which adds
``override_status`` entries and moves neither revision).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from harness import FIXTURES, FRONTEND, _StagingTempfile

from vault_cleaner.server import app as server_app
from vault_cleaner.server.session import Session

SAMPLES = FRONTEND / "src" / "contract"
FIXTURE = "armor_close.csv"
VERDICTS = [{"id": "6032", "verdict": "vetoed"}, {"id": "6081", "verdict": "approved"}]
ORIGIN = "http://127.0.0.1"


def generate() -> dict[str, dict]:
    """Drive the unmodified production app in process; no socket is opened."""
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-206-contract-") as raw:
        root = Path(raw)
        (root / "staging").mkdir()
        (root / "config.toml").write_text("", encoding="utf-8")
        original = server_app.tempfile
        server_app.tempfile = _StagingTempfile(root / "staging")
        session = Session(
            overrides_path=str(root / "overrides.json"),
            config_path=str(root / "config.toml"),
            no_wishlists=True,
        )
        try:
            app = server_app.create_app(session)
            session.configure_bound_port(80)
            client = app.test_client()
            headers = {"Origin": ORIGIN}
            client.get(f"/bootstrap?token={session.bootstrap_token}", base_url=ORIGIN)
            uploaded = client.post(
                "/api/exports/armor", data=(FIXTURES / FIXTURE).read_bytes(),
                content_type="text/csv", headers=headers, base_url=ORIGIN,
            ).get_json()
            revisions = {
                "report_revision": uploaded["report_revision"],
                "verdict_revision": uploaded["verdict_revision"],
                "fingerprint": uploaded["fingerprint"],
            }
            reviewing = client.post(
                "/api/verdicts", json={**revisions, "decisions": VERDICTS},
                headers=headers, base_url=ORIGIN,
            ).get_json()
            revisions["verdict_revision"] = reviewing["verdict_revision"]
            finalize = client.post(
                "/api/finalize", json=revisions, headers=headers, base_url=ORIGIN
            )
            if finalize.status_code != 200:
                raise RuntimeError(f"finalize returned HTTP {finalize.status_code}")
            finalized = client.get("/api/report", base_url=ORIGIN).get_json()
        finally:
            session.close()
            server_app.tempfile = original
    return {"reviewing.json": reviewing, "finalized.json": finalized}


def render(envelope: dict) -> str:
    return json.dumps(envelope, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, envelope in generate().items():
        (directory / name).write_bytes(render(envelope).encode("utf-8"))


def main() -> int:
    if sys.argv[1:] not in ([], ["--check"]):
        print(__doc__)
        return 2
    if not sys.argv[1:]:
        write(SAMPLES)
        print(f"wrote {len(generate())} samples to {SAMPLES.relative_to(FRONTEND.parents[2])}")
        return 0
    stale = [
        name for name, envelope in generate().items()
        if not (SAMPLES / name).is_file()
        or (SAMPLES / name).read_text(encoding="utf-8") != render(envelope)
    ]
    for name in stale:
        print(f"STALE: {name} no longer matches what the server returns")
    print("RESULT: " + ("FAIL" if stale else "PASS"))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
