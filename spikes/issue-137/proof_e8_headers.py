"""E8: the request envelope and response headers on every spike route.

Raw HTTP requests compare each spike route's security headers with the
production root page's, and show the unauthenticated, wrong-Host and
wrong-Origin refusals.  Chromium then exercises the whole slice and reports
CSP violations, with a control that proves the detector is live.

    .venv/bin/python spikes/issue-137/proof_e8_headers.py
"""

from __future__ import annotations

import http.client
import json
from urllib.parse import urlsplit

from harness import (
    authenticated_context,
    chromium,
    csp_events,
    finish,
    live_spike,
    main_guard,
    open_spike,
    upload,
    watch,
)
from spike_app import FRAGMENT_PATH, SPIKE_ROUTES, WHOLE_PAGE_PATH

from vault_cleaner.server.app import SERVER_CSP, SESSION_COOKIE_NAME

SECURITY_HEADERS = (
    "Cache-Control",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
)


def fetch(live, path: str, *, method: str = "GET", cookie: bool = True, host: str | None = None,
          origin: str | None = None) -> tuple[int, dict[str, str], bytes]:
    netloc = urlsplit(live.origin).netloc
    connection = http.client.HTTPConnection(netloc, timeout=10)
    headers = {"Host": host or netloc}
    if cookie:
        headers["Cookie"] = f"{SESSION_COOKIE_NAME}={live.session.session_token}"
    if origin is not None:
        headers["Origin"] = origin
    connection.request(method, path, headers=headers)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, dict(response.getheaders()), body


def error_code(body: bytes) -> str:
    try:
        return json.loads(body)["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return "(no error body)"


def main() -> int:
    failures: list[str] = []
    with live_spike() as live, chromium() as browser:
        context = authenticated_context(browser, live)
        seen = watch(context)
        upload(context, live, "armor_close.csv")

        _status, production, _body = fetch(live, "/")
        baseline = {name: production.get(name) for name in SECURITY_HEADERS}
        print("-- production root page --")
        for name, value in baseline.items():
            print(f"{name}: {value}")
        print(f"CSP equals vault_cleaner.server.app.SERVER_CSP: "
              f"{baseline['Content-Security-Policy'] == SERVER_CSP}")

        print("-- spike routes --")
        for path in SPIKE_ROUTES:
            status, headers, _body = fetch(live, path)
            same = {name: headers.get(name) for name in SECURITY_HEADERS} == baseline
            unauthenticated, _h, body_a = fetch(live, path, cookie=False)
            wrong_host, _h, body_h = fetch(live, path, host="evil.example")
            wrong_origin, _h, body_o = fetch(live, path, origin="http://evil.example")
            post, _h, body_p = fetch(live, path, method="POST", origin=live.origin)
            post_no_origin, _h, body_n = fetch(live, path, method="POST")
            print(f"{path}: {status} {headers.get('Content-Type')}; security headers equal production: {same}")
            print(f"  no cookie: {unauthenticated} {error_code(body_a)}; wrong Host: {wrong_host} "
                  f"{error_code(body_h)}; wrong Origin: {wrong_origin} {error_code(body_o)}; "
                  f"POST: {post} {error_code(body_p)}; POST without Origin: {post_no_origin} "
                  f"{error_code(body_n)}")
            if status != 200 or not same:
                failures.append(f"{path}: headers differ from production")
            if (unauthenticated, wrong_host, wrong_origin, post, post_no_origin) != (401, 400, 403, 404, 403):
                failures.append(f"{path}: a refusal case was not refused as production refuses it")

        print("-- fragment route parameters --")
        for query in ("?kind=exact", "?kind=bogus", "?template=shell.html", "?kind=all&kind=exact",
                      "?guardian_class=" + "x" * 201):
            status, headers, body = fetch(live, FRAGMENT_PATH + query)
            shown = query if len(query) < 40 else query[:20] + "...(201 characters)"
            print(f"{shown}: {status} {'' if status == 200 else error_code(body)}".rstrip())
        status, _headers, body = fetch(live, WHOLE_PAGE_PATH + "?kind=exact")
        print(f"{WHOLE_PAGE_PATH}?kind=exact: {status} {error_code(body)}")
        print(f"revision headers on the fragment: "
              f"{ {k: v for k, v in fetch(live, FRAGMENT_PATH)[1].items() if k.startswith('Vault-Cleaner')} }")

        print("-- Chromium, whole slice --")
        for query in ("", "?repaint=r2", "?repaint=r3", "?filters=server"):
            page = open_spike(context, live, query)
            page.locator('table.armor-matrix-columns td[data-vc-verdict-id="6032"] button.approve').click()
            page.wait_for_function(
                "() => /acknowledged|not applied/.test(document.getElementById('vc-status').textContent)"
            )
            page.locator("#vc-dup-kind-exact").click()
            page.locator("#vc-dup-f-guardianClass").select_option("Titan")
            page.locator("#vc-dup-kind-all").click()
            page.wait_for_timeout(200)
            events = csp_events(page)
            print(f"/spike/{query}: CSP violation events={events}")
            if events:
                failures.append(f"/spike/{query}: CSP violation")
            page.close()
        whole = context.new_page()
        whole.goto(f"{live.origin}{WHOLE_PAGE_PATH}", wait_until="load")
        print(f"{WHOLE_PAGE_PATH}: CSP violation events={csp_events(whole)}")
        if csp_events(whole):
            failures.append("whole page: CSP violation")
        print(f"CSP console messages across the slice: {seen['csp_console']}")
        if seen["csp_console"]:
            failures.append("CSP console message")

        whole.evaluate("() => document.body.setAttribute('style', 'color: red')")
        whole.wait_for_timeout(200)
        control = csp_events(whole)
        print(f"control (an inline style attribute set on purpose): events={control}, "
              f"console messages={len(seen['csp_console'])}")
        if not control:
            failures.append("the CSP detector did not fire on the control")
        context.close()
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
