"""E11: state that changes while both revisions stay equal.

``POST /api/finalize`` moves ``state`` to ``finalized`` and replaces the
override store, so ``override_status`` gains active entries, without changing
``report_revision``, ``verdict_revision`` or the fingerprint.  A fragment
that depended on either could not be validated by the revision pair.

The proof shows the fragment's bytes do not change across a finalise, that a
page with the fragment already installed reaches the finalised presentation
by painting from the envelope with no fragment request, and that it equals
production loaded fresh.  It then does the same for reset and for a report
loaded while a persisted veto is active.

    .venv/bin/python spikes/issue-137/proof_e11_finalize.py
"""

from __future__ import annotations

import json
from typing import Any

from harness import (
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

MEMBER = "6032"
FRAGMENT = "/spike/fragments/armor-duplicates"
REVISION_HEADERS = ("vault-cleaner-report-revision", "vault-cleaner-verdict-revision")
CELL_JS = """
id => Array.prototype.map.call(
  document.querySelectorAll('#vc-duplicate-list [data-vc-verdict-id]'),
  cell => cell).filter(cell => cell.getAttribute('data-vc-verdict-id') === id).map(cell => ({
    text: cell.querySelector('[data-vc-verdict-text]').textContent,
    pressed: Array.prototype.map.call(
      cell.querySelectorAll('button'), b => b.getAttribute('aria-pressed')).join(','),
    disabled: Array.prototype.every.call(cell.querySelectorAll('button'), b => b.disabled)
  }))
"""


def strip(tree: dict) -> dict:
    """Drop the two declared parity differences (see E1)."""
    for node in walk(tree):
        attributes = node.get("attributes")
        if attributes is None:
            continue
        if attributes.get("class") == "":
            del attributes["class"]
        for name in [name for name in attributes if name.startswith("data-vc-")]:
            del attributes[name]
    return tree


def post(context: Any, live: Any, path: str, keys: tuple[str, ...]) -> Any:
    current = context.request.get(f"{live.origin}/api/report").json()
    return context.request.post(
        f"{live.origin}{path}",
        headers={"Origin": live.origin, "Content-Type": "application/json"},
        data=json.dumps({key: current[key] for key in keys}),
    )


def fragment(context: Any, live: Any) -> tuple[bytes, dict[str, str]]:
    response = context.request.get(f"{live.origin}{FRAGMENT}")
    return response.body(), {name: response.headers[name] for name in REVISION_HEADERS}


def cells(page: Any) -> str:
    shapes = {
        f"text={cell['text']!r} pressed={cell['pressed']} all disabled={cell['disabled']}"
        for cell in page.evaluate(CELL_JS, MEMBER)
    }
    return " | ".join(sorted(shapes))


def sync(page: Any) -> list[str]:
    page.evaluate("() => { window.VaultCleanerSpike.log.length = 0; }")
    page.evaluate("() => window.VaultCleanerSpike.sync()")
    return page.evaluate("() => window.VaultCleanerSpike.log.slice()")


def parity(context: Any, live: Any, page: Any, label: str, failures: list[str]) -> None:
    production = open_production_duplicates(context, live)
    fresh = open_spike(context, live)
    expected = json.dumps(strip(project(production)), sort_keys=True)
    installed = json.dumps(strip(project(page)), sort_keys=True) == expected
    loaded = json.dumps(strip(project(fresh)), sort_keys=True) == expected
    print(f"{label}: production loaded fresh equals the spike page with its fragment already "
          f"installed={installed}; equals the spike page loaded fresh={loaded}")
    if not (installed and loaded):
        failures.append(f"{label}: the spike does not match production")
    production.close()
    fresh.close()


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        upload(context, live, "armor_close.csv")
        page = open_spike(context, live)
        page.locator(
            f'table.armor-matrix-columns td[data-vc-verdict-id="{MEMBER}"] button.veto'
        ).click()
        page.wait_for_function(
            "() => document.getElementById('vc-status').textContent.indexOf('acknowledged') !== -1"
        )

        print("-- finalise --")
        before_body, before_headers = fragment(context, live)
        before = context.request.get(f"{live.origin}/api/report").json()
        response = post(context, live, "/api/finalize",
                        ("report_revision", "verdict_revision", "fingerprint"))
        after_body, after_headers = fragment(context, live)
        after = context.request.get(f"{live.origin}/api/report").json()
        print(f"POST /api/finalize: {response.status}")
        print(f"envelope before: state={before['state']} report={before['report_revision']} "
              f"verdict={before['verdict_revision']} active persisted vetoes="
              f"{[e['id'] for e in before['override_status'] if e['status'] == 'active']}")
        print(f"envelope after:  state={after['state']} report={after['report_revision']} "
              f"verdict={after['verdict_revision']} active persisted vetoes="
              f"{[e['id'] for e in after['override_status'] if e['status'] == 'active']}")
        print(f"fragment revision headers equal before and after: {before_headers == after_headers}")
        print(f"fragment bytes equal before and after: {before_body == after_body} "
              f"({len(before_body)} and {len(after_body)} bytes)")
        if before_headers != after_headers or before_body != after_body:
            failures.append("the fragment changed while the revision pair did not")
        print(f"page before it learns of the finalise: {cells(page)}")
        log = sync(page)
        print(f"page after adopting the envelope: {cells(page)}")
        print(f"fragment requests made to get there: {len(log)} {log}")
        if log:
            failures.append("the page needed a fragment to show the finalised state")
        parity(context, live, page, "finalised", failures)

        print("-- reset --")
        response = post(context, live, "/api/reset", ("report_revision", "verdict_revision"))
        after_reset = response.json()
        print(f"POST /api/reset: {response.status}; state={after_reset['state']} "
              f"report={after_reset['report_revision']} verdict={after_reset['verdict_revision']}")
        log = sync(page)
        groups = page.locator("article.armor-group").count()
        print(f"page after adopting the envelope: groups rendered={groups}; fragment log={log}")
        if groups or not any("accepted" in entry for entry in log):
            failures.append("reset did not replace the installed fragment")

        print("-- a new report while the saved veto is active --")
        envelope = upload(context, live, "armor_close.csv")
        print(f"envelope: state={envelope['state']} report={envelope['report_revision']} "
              f"active persisted vetoes="
              f"{[e['id'] for e in envelope['override_status'] if e['status'] == 'active']}")
        log = sync(page)
        print(f"page after adopting the envelope: {cells(page)}; fragment log={log}")
        parity(context, live, page, "active saved veto", failures)
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
