"""Render the self-contained static HTML review artifact (#37).

The browser reviews decisions; it never re-runs rules, edits config, or writes
the DIM CSV. The only thing it hands back is a review manifest, and
`review.parse_manifest` re-validates that from scratch — nothing the page
produces is authoritative.

The artifact is one file with inline CSS/JS and no network access of any kind,
so it works from `file://` and cannot phone home with the vault data it
carries. Output is deterministic for a given run: no timestamps, no ids
derived from the clock, so two renders of the same report are byte-identical.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from vault_cleaner.report_run import ReportRun, snapshot_json

DEFAULT_REVIEW_HTML = "data/out/vault-review.html"

PRIVACY_WARNING = (
    "This file embeds personal vault metadata — item names, instance ids, "
    "notes, and character names. Treat it like your DIM export: keep it local, "
    "and do not publish, paste, or attach it anywhere."
)

# `default-src 'none'` is the load-bearing part: no fonts, scripts, styles,
# images, or connections can be fetched, so the page cannot exfiltrate the
# vault data it carries. Inline script/style are allowed by necessity — a nonce
# cannot survive a file the user re-opens from disk, and hashing the blocks
# would silently break the whole artifact on any whitespace drift.
CSP = (
    "default-src 'none'; "
    "script-src 'unsafe-inline'; "
    "style-src 'unsafe-inline'; "
    "connect-src 'none'; "
    "form-action 'none'; "
    "base-uri 'none'"
)

SNAPSHOT_ELEMENT_ID = "vc-snapshot"
APP_ELEMENT_ID = "vc-app"

_UI_RESOURCES = files("vault_cleaner.ui")


def _resource_text(name: str) -> str:
    """Read one UTF-8 UI asset from the installed package."""
    return _UI_RESOURCES.joinpath(name).read_bytes().decode("utf-8")


# CSS and the shared presentation layer are packaged resources so the server
# can serve these exact bytes. The static adapter remains inline only while
# the standalone review artifact exists; #51 removes that adapter wholesale.
CSS = _resource_text("review.css")
_SHARED_JS = _resource_text("review_ui.js")
_STATIC_ADAPTER_JS = _resource_text("review_static.js")
APP_JS = _SHARED_JS + _STATIC_ADAPTER_JS


def embed_json(payload: str) -> str:
    r"""Make already-valid JSON safe to inline inside an HTML script element.

    `<`, `>`, and `&` only ever occur inside JSON string literals, where
    `\uXXXX` is an equivalent encoding — so escaping them keeps the JSON
    parseable and value-identical while making `</script>`, `<!--`, and `-->`
    impossible to spell. U+2028/U+2029 are escaped for the same reason: legal
    in a JSON string, but a line terminator in JavaScript source.
    """
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


# Static chrome only. Every element the app fills in is empty here, so the
# markup carries no vault data and needs no escaping of its own.
BODY_HTML = """\
<a class="skip" href="#vc-list">Skip to the item list</a>
<div class="wrap">
<h1>vault-cleaner review</h1>
<p class="sub">Report fingerprint <code id="vc-fingerprint"></code></p>
<div class="privacy">
<strong>Personal data &mdash; keep this file local</strong>
__PRIVACY_WARNING__
</div>
<noscript><p class="err">This review page needs JavaScript. The decisions are
still readable as JSON inside this file, and <code>vault-cleaner report</code>
prints the same ones in the terminal.</p></noscript>
<div class="panel">
<h2>Summary</h2>
<div id="vc-summary"></div>
</div>
<div class="panel">
<h2>Filters</h2>
<div class="controls" id="vc-controls"></div>
</div>
<div class="panel">
<h2>Handoff</h2>
<div class="controls" id="vc-handoff"></div>
<p id="vc-status" role="status" aria-live="polite" class="hint">Approve or veto
proposals, then export a review manifest and apply it with
<code>vault-cleaner review --manifest &lt;file&gt; --write</code>.</p>
<label class="field" for="vc-export-json"><span>Review manifest JSON &mdash;
copy it out, or paste one in and use &ldquo;Import from the box
below&rdquo;</span><textarea id="vc-export-json" spellcheck="false"></textarea>
</label>
<p class="hint">Browser storage autosaves your verdicts for this report as a
convenience only. Export is the durable handoff, and Python re-validates every
manifest before anything is written.</p>
</div>
<div class="panel">
<h2>Proposals</h2>
<p class="hint">With focus inside a row: <kbd>a</kbd> approve, <kbd>v</kbd>
veto, <kbd>u</kbd> unset.</p>
<div id="vc-list"></div>
</div>
</div>
"""

_HEAD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="__CSP__">
<meta name="referrer" content="no-referrer">
<title>vault-cleaner review</title>
<style>__CSS__</style>
</head>
<body>
"""


def render_review_html(run: ReportRun) -> str:
    """One portable HTML file: no network, no dependencies, no timestamps."""
    return "".join(
        [
            _HEAD_HTML.replace("__CSP__", CSP).replace("__CSS__", CSS),
            BODY_HTML.replace("__PRIVACY_WARNING__", PRIVACY_WARNING),
            # A non-executable data block: the app parses the snapshot out of
            # textContent, so nothing in here is ever evaluated as script.
            f'<script type="application/json" id="{SNAPSHOT_ELEMENT_ID}">',
            embed_json(snapshot_json(run)),
            "</script>\n",
            f'<script id="{APP_ELEMENT_ID}">',
            APP_JS,
            "</script>\n",
            "</body>\n</html>\n",
        ]
    )


def write_review_html(run: ReportRun, path: str | Path) -> Path:
    """Write the artifact, creating its parent directory like the CSV writer."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_review_html(run), encoding="utf-8")
    return target
