"""Scan the spike's template bytes for constructs the design forbids.

The rules, from the #137 plan:

* every ``{{ ... }}`` inside a tag sits inside a quoted attribute value;
* no ``|safe``, ``Markup``, ``{% autoescape %}``, ``|int`` or ``|float``;
* no ``style=`` attribute, no ``on...=`` handler and no inline ``<script>``
  (a ``<script src="...">`` with an empty body is allowed);
* ``{% include %}``, ``{% extends %}``, ``{% import %}`` and ``{% from %}``
  name their template with a string literal;
* the files on disk are exactly the environment's allow-list.

The scanner first runs against snippets that each break one rule, so a rule
that stopped firing would fail the run rather than pass it silently.

    .venv/bin/python spikes/issue-137/check_templates.py
"""

from __future__ import annotations

import re
import sys

from render_env import SPIKE_TEMPLATES, TEMPLATE_NAMES

FORBIDDEN = (
    ("safe filter", re.compile(rb"\|\s*safe\b")),
    ("Markup", re.compile(rb"\bMarkup\b")),
    ("autoescape block", re.compile(rb"\{%-?\s*(end)?autoescape\b")),
    ("int filter", re.compile(rb"\|\s*int\b")),
    ("float filter", re.compile(rb"\|\s*float\b")),
    ("style attribute", re.compile(rb"(?i)[\s\"']style\s*=")),
    ("event handler attribute", re.compile(rb"(?i)[\s\"']on[a-z]+\s*=")),
    ("inline script", re.compile(rb"(?is)<script\b(?![^>]*\bsrc=)[^>]*>|<script\b[^>]*>\s*[^\s<]")),
    (
        "non-literal template name",
        re.compile(
            rb"\{%-?\s*(include|extends|import|from)\s+"
            rb"(?![\"'][^\"'{}]+[\"']\s*(-?%\}|(import|as|with|without|ignore)\b))"
        ),
    ),
)
COMMENT = re.compile(rb"\{#.*?#\}", re.DOTALL)


def unquoted_interpolations(source: bytes) -> list[int]:
    """Return the line of each ``{{`` that is inside a tag but not in quotes."""
    lines: list[int] = []
    in_tag = False
    quote: int | None = None
    index = 0
    while index < len(source):
        byte = source[index]
        pair = source[index : index + 2]
        if pair in (b"{{", b"{%"):
            close = b"}}" if pair == b"{{" else b"%}"
            end = source.find(close, index)
            if end == -1:
                break
            if pair == b"{{" and in_tag and quote is None:
                lines.append(source.count(b"\n", 0, index) + 1)
            index = end + 2
            continue
        if not in_tag:
            if byte == ord("<") and index + 1 < len(source) and (
                chr(source[index + 1]).isalpha() or source[index + 1] == ord("/")
            ):
                in_tag = True
        elif quote is not None:
            if byte == quote:
                quote = None
        elif byte in (ord('"'), ord("'")):
            quote = byte
        elif byte == ord(">"):
            in_tag = False
        index += 1
    return lines


def scan(source: bytes) -> list[str]:
    stripped = COMMENT.sub(lambda match: b"\n" * match.group().count(b"\n"), source)
    findings = [
        f"{label} at line {stripped.count(b'\n', 0, match.start()) + 1}"
        for label, pattern in FORBIDDEN
        for match in pattern.finditer(stripped)
    ]
    findings += [
        f"unquoted attribute interpolation at line {line}"
        for line in unquoted_interpolations(stripped)
    ]
    return findings


SELF_TEST = (
    ("safe filter", b"<p>{{ name|safe }}</p>"),
    ("safe filter", b"<p>{{ name | safe }}</p>"),
    ("Markup", b"{{ Markup(name) }}"),
    ("autoescape block", b"{% autoescape false %}{{ name }}{% endautoescape %}"),
    ("int filter", b'<td data-id="{{ id|int }}"></td>'),
    ("float filter", b"<td>{{ id | float }}</td>"),
    ("style attribute", b'<span style="width: {{ w }}%"></span>'),
    ("event handler attribute", b'<button onclick="go()">x</button>'),
    ("inline script", b"<script>go()</script>"),
    ("non-literal template name", b"{% include name %}"),
    ("non-literal template name", b'{% extends "base-" ~ kind ~ ".html" %}'),
    ("non-literal template name", b"{% from source import macro %}"),
    ("unquoted attribute interpolation", b"<td data-id={{ id }}></td>"),
    ("unquoted attribute interpolation", b"<td {{ attributes }}></td>"),
)
SELF_TEST_CLEAN = (
    b'<td class="a" data-id="{{ id }}">{{ name }}</td>',
    b'<script src="/assets/x.js" defer></script>',
    b'{% from "_verdict.html" import verdict_cell %}',
    b'<button type="button"{% if frozen %} disabled{% endif %}>Approve</button>',
    b"{#- a comment may mention |safe and style= -#}<p>{{ text }}</p>",
)


def main() -> int:
    failures: list[str] = []
    for label, snippet in SELF_TEST:
        fired = any(finding.startswith(label) for finding in scan(snippet))
        print(f"self-test rejects {label}: {snippet.decode()} -> {'rejected' if fired else 'MISSED'}")
        if not fired:
            failures.append(f"self-test snippet was not rejected: {snippet.decode()}")
    for snippet in SELF_TEST_CLEAN:
        findings = scan(snippet)
        print(f"self-test accepts: {snippet.decode()} -> {'accepted' if not findings else findings}")
        if findings:
            failures.append(f"self-test clean snippet was rejected: {snippet.decode()}")

    on_disk = sorted(path.name for path in SPIKE_TEMPLATES.iterdir())
    print(f"templates on disk: {on_disk}")
    print(f"environment allow-list: {sorted(TEMPLATE_NAMES)}")
    if on_disk != sorted(TEMPLATE_NAMES):
        failures.append("the templates on disk are not exactly the allow-list")
    for name in on_disk:
        source = (SPIKE_TEMPLATES / name).read_bytes()
        findings = scan(source)
        interpolations = source.count(b"{{")
        print(f"{name}: {len(source)} bytes, {interpolations} interpolations, findings={findings}")
        failures += [f"{name}: {finding}" for finding in findings]
    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT: " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
