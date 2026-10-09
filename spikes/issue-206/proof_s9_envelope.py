"""S9: the request envelope (gate H7).

No browser.  Every spike route must carry production's security headers and
refuse an unauthenticated request, a wrong ``Host`` and a wrong ``Origin``,
exactly as a production asset does.  Production routes served by the spike
app must keep the unchanged policy byte for byte.

A second server is started with all three pre-approved additions switched on,
to show that the mechanism rewrites the header for ``/spike/`` paths only.
The slice itself is served with none (see S7).

    .venv/bin/python spikes/issue-206/proof_s9_envelope.py
"""

from __future__ import annotations

import http.client
from typing import Any

from harness import finish, live_spike, main_guard
from spike_app import APPROVED_ADDITIONS, SLICE_CSP_ADDITIONS, SLICE_FILES, policy_with

from vault_cleaner.server.app import DEFAULT_ASSETS, SERVER_CSP

SECURITY_HEADERS = (
    "Cache-Control", "Referrer-Policy", "X-Content-Type-Options", "X-Frame-Options",
    "Content-Security-Policy",
)
PRODUCTION_PATHS = (*DEFAULT_ASSETS, "/api/report")
NOT_SERVED = (
    "/spike/assets/other.js", "/spike/assets/../../pyproject.toml", "/spike/assets/%2e%2e/app.js",
    "/spike/modules.json", "/spike/index.html",
)


def request(live: Any, path: str, *, cookie: bool = True, host: str | None = None,
            origin: str | None = None, method: str = "GET") -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", live.session.bound_port, timeout=10)
    headers = {"Host": host or live.session.expected_host}
    if cookie:
        headers["Cookie"] = f"vault_cleaner_session={live.session.session_token}"
    if origin is not None:
        headers["Origin"] = origin
    connection.request(method, path, headers=headers)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response.status, dict(response.getheaders()), body


def main() -> int:
    failures: list[str] = []
    with live_spike() as live:
        print(f"-- served as the slice is: additions {list(SLICE_CSP_ADDITIONS)} --")
        _status, reference, _body = request(live, "/assets/review.css")
        wanted = {name: reference[name] for name in SECURITY_HEADERS}
        print(f"production asset headers: {wanted}")
        for path, (content_type, _name) in SLICE_FILES.items():
            status, headers, body = request(live, path)
            same = {name: headers.get(name) for name in SECURITY_HEADERS} == wanted
            refusals = {
                "no cookie": request(live, path, cookie=False)[0],
                "wrong Host": request(live, path, host="localhost:1")[0],
                "wrong Origin": request(live, path, origin="http://evil.example")[0],
                "POST": request(live, path, method="POST", origin=live.origin)[0],
            }
            print(f"{path}: HTTP {status}, {headers['Content-Type']}, {len(body)} bytes; "
                  f"security headers equal production's={same}; refusals={refusals}")
            if (
                status != 200 or headers["Content-Type"] != content_type or not same
                or refusals != {"no cookie": 401, "wrong Host": 400, "wrong Origin": 403, "POST": 404}
            ):
                failures.append(f"{path} differs from a production asset")
        for path in PRODUCTION_PATHS:
            status, headers, _body = request(live, path)
            unchanged = headers.get("Content-Security-Policy") == SERVER_CSP
            print(f"production route {path}: HTTP {status}; policy byte-identical to SERVER_CSP={unchanged}")
            if not unchanged:
                failures.append(f"{path} lost the production policy")
        for path in NOT_SERVED:
            status, _headers, body = request(live, path)
            print(f"{path}: HTTP {status}")
            if status != 404 or b"tool.setuptools" in body:
                failures.append(f"{path} was served")

        page = request(live, "/spike/")[2]
        status, _headers, body = request(live, "/spike/?file=../../pyproject.toml&name=app.js")
        print(f"/spike/ with a file-like query string: HTTP {status}; the body is the same index.html={body == page}")
        if body != page:
            failures.append("a query string changed what was served")
        status, headers, _body = request(live, "/spike")
        print(f"/spike (no trailing slash): HTTP {status} -> {headers.get('Location', '').replace(live.origin, '')}")

    print("-- the mechanism, with all three pre-approved additions switched on --")
    additions = tuple(APPROVED_ADDITIONS)
    with live_spike(csp_additions=additions) as live:
        spike_policy = request(live, "/spike/")[1]["Content-Security-Policy"]
        print(f"/spike/: {spike_policy}")
        if spike_policy != policy_with(additions):
            failures.append("the spike policy is not the approved envelope")
        base = {part.strip() for part in SERVER_CSP.split(";")}
        changed = sorted({part.strip() for part in spike_policy.split(";")} - base)
        print(f"directives that differ from production: {changed}")
        if changed != ["font-src 'self'", "img-src 'self' data:", "style-src 'self' 'unsafe-inline'"]:
            failures.append("the envelope differs from the three pre-approved additions")
        for path in PRODUCTION_PATHS:
            policy = request(live, path)[1].get("Content-Security-Policy")
            print(f"production route {path}: policy byte-identical to SERVER_CSP={policy == SERVER_CSP}")
            if policy != SERVER_CSP:
                failures.append(f"{path} changed policy")
        refused = request(live, "/spike/", cookie=False)
        print(f"/spike/ without a cookie: HTTP {refused[0]}, policy on the refusal is the spike's="
              f"{refused[1].get('Content-Security-Policy') == spike_policy}")
    return finish(failures)


if __name__ == "__main__":
    main_guard(main)
