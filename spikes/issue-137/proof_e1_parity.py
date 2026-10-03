"""E1: rendered parity between the Jinja fragment and production's DOM.

For each slice fixture, upload it through the real upload route, then open
the production page and the spike page on the same session and compare a
normalised projection of ``#vc-duplicate-list``.  Two differences are
expected and counted; anything else fails the proof.

    .venv/bin/python spikes/issue-137/proof_e1_parity.py
"""

from __future__ import annotations

import json

from harness import (
    SLICE_FIXTURES,
    authenticated_context,
    chromium,
    finish,
    live_spike,
    main_guard,
    open_production_duplicates,
    open_spike,
    project,
    upload,
    walk,
)

SPIKE_ONLY_PREFIX = "data-vc-"


def normalise(tree: dict) -> tuple[dict, int, int]:
    """Drop the two declared differences and count each."""
    empty_classes = 0
    spike_only = 0
    for node in walk(tree):
        attributes = node.get("attributes")
        if attributes is None:
            continue
        if attributes.get("class") == "":
            del attributes["class"]
            empty_classes += 1
        for name in [name for name in attributes if name.startswith(SPIKE_ONLY_PREFIX)]:
            del attributes[name]
            spike_only += 1
    return tree, empty_classes, spike_only


def count(tree: dict, tag: str) -> int:
    return sum(1 for node in walk(tree) if node.get("tag") == tag)


def compare(context, live, fixture: str, verdict: str | None, failures: list[str]) -> None:
    production_page = open_production_duplicates(context, live)
    spike_page = open_spike(context, live)
    production, production_empty, production_spike = normalise(project(production_page))
    jinja, jinja_empty, jinja_spike = normalise(project(spike_page))
    equal = json.dumps(production, sort_keys=True) == json.dumps(jinja, sort_keys=True)
    label = f"{fixture} ({'no verdicts' if verdict is None else verdict})"
    print(
        f"{label}: groups={count(jinja, 'article')} tables={count(jinja, 'table')} "
        f"buttons={count(jinja, 'button')} nodes={sum(1 for _ in walk(jinja))} "
        f"equal={equal}"
    )
    print(
        f"  declared differences: empty class attributes production={production_empty} "
        f"jinja={jinja_empty}; data-vc-* attributes production={production_spike} "
        f"jinja={jinja_spike}"
    )
    if not equal:
        failures.append(f"{label}: projections differ")
    if count(jinja, "article") == 0:
        failures.append(f"{label}: no group was rendered")
    production_page.close()
    spike_page.close()


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        for fixture in SLICE_FIXTURES:
            envelope = upload(context, live, fixture)
            compare(context, live, fixture, None, failures)
            proposals = [
                decision["id"]
                for section in envelope["snapshot"]["sections"]
                for decision in section["decisions"]
            ]
            # Parity must also hold once the session has verdicts.
            for verdict, target in zip(("approved", "vetoed"), proposals, strict=False):
                current = context.request.get(f"{live.origin}/api/report").json()
                response = context.request.post(
                    f"{live.origin}/api/verdicts",
                    headers={"Origin": live.origin, "Content-Type": "application/json"},
                    data=json.dumps(
                        {
                            "report_revision": current["report_revision"],
                            "verdict_revision": current["verdict_revision"],
                            "fingerprint": current["fingerprint"],
                            "decisions": [{"id": target, "verdict": verdict}],
                        }
                    ),
                )
                if response.status != 200:
                    failures.append(f"{fixture}: verdict request returned {response.status}")
            compare(context, live, fixture, "one approved, one vetoed", failures)
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
