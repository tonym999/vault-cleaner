"""Compare the spike's explicit Jinja environment with Flask's own.

Also measures the shell-only shape: the production shell has no value to
interpolate, so rendering it through Jinja returns its own bytes.

    .venv/bin/python spikes/issue-137/proof_environment.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from flask import Flask, render_template
from jinja2 import Environment, TemplateAssertionError, TemplateNotFound, UndefinedError
from render_env import TEMPLATE_NAMES, build_environment

REPO = Path(__file__).resolve().parents[2]
PRODUCTION_SHELL = REPO / "src" / "vault_cleaner" / "ui" / "review_server.html"
HOSTILE = "\"><img src=x onerror=alert(1)>"
PROBE = '<td data-id="{{ value }}">{{ value }}</td>'


def outcome(action) -> str:
    try:
        return repr(action())
    except (TemplateNotFound, TemplateAssertionError, UndefinedError) as error:
        return f"{type(error).__name__}: {error}"


def main() -> int:
    failures: list[str] = []
    explicit = build_environment()

    print("-- autoescape, by template name --")
    with tempfile.TemporaryDirectory(prefix="vault-cleaner-spike-137-env-") as raw:
        folder = Path(raw)
        flask_app = Flask("probe", template_folder=str(folder))
        for name in ("probe.html", "probe.html.j2", "probe.j2", "probe.txt"):
            (folder / name).write_text(PROBE, encoding="utf-8")
            with flask_app.app_context():
                rendered = render_template(name, value=HOSTILE)
            escaped = "<img" not in rendered
            print(f"flask render_template {name}: escaped={escaped}")
        (folder / "typo.html").write_text("<p>{{ misspelt }}</p>", encoding="utf-8")
        with flask_app.app_context():
            silent = render_template("typo.html")
        print(f"flask render_template with a misspelt key: {silent!r}")
        searchpath = flask_app.jinja_loader.searchpath
        print(f"flask loader: {type(flask_app.jinja_loader).__name__} over {len(searchpath)} directory")

    rendered = explicit.from_string(PROBE).render(value=HOSTILE)
    print(f"explicit environment (autoescape is not chosen by name): escaped={'<img' not in rendered}")
    if "<img" in rendered:
        failures.append("the explicit environment did not escape")

    print("-- undefined --")
    strict = outcome(lambda: explicit.from_string("<p>{{ misspelt }}</p>").render())
    print(f"explicit environment with a misspelt key: {strict}")
    if "UndefinedError" not in strict:
        failures.append("StrictUndefined did not raise")

    print("-- loader --")
    print(f"allow-list: {sorted(TEMPLATE_NAMES)}")
    for name in ("../render_env.py", "/etc/hostname", "templates/shell.html", "missing.html"):
        result = outcome(lambda name=name: explicit.get_template(name).name)
        print(f"explicit get_template({name!r}): {result}")
        if "TemplateNotFound" not in result:
            failures.append(f"the loader served {name}")
    print(f"explicit get_template('shell.html'): {explicit.get_template('shell.html').name!r}")

    print("-- filters and globals that would break the opaque-id or escaping rule --")
    stock = Environment(autoescape=True)
    values = {"id": "18446744073709551615", "name": "<b>x</b>"}
    for expression in (
        "{{ id|int }}",
        "{{ id|float }}",
        "{{ id|filesizeformat }}",
        "{{ name|safe }}",
        "{{ name|tojson }}",
        "{{ name|urlize }}",
        "{{ {'onclick': name}|xmlattr }}",
    ):
        print(f"stock jinja2 {expression}: {outcome(lambda e=expression: stock.from_string(e).render(**values))}")
        result = outcome(lambda e=expression: explicit.from_string(e).render(**values))
        print(f"explicit environment {expression}: {result}")
        if "TemplateAssertionError" not in result:
            failures.append(f"the explicit environment compiled {expression}")
    print(f"explicit {{{{ id }}}}: {explicit.from_string('{{ id }}').render(id='18446744073709551615')!r}")
    print(f"stock jinja2: {len(stock.filters)} filters, {len(stock.globals)} globals; "
          f"explicit environment: {len(explicit.filters)} filters, {len(explicit.globals)} globals")
    attribute = '<td data-x="{{ name|tojson }}"></td>'
    breakout = stock.from_string(attribute).render(name='" onmouseover="alert(1)')
    print(f"stock jinja2 {attribute}: {breakout}")
    lorem = outcome(lambda: explicit.from_string("{{ lipsum(1) }}").render())
    print(f"explicit environment {{{{ lipsum(1) }}}}: {lorem}")
    if "UndefinedError" not in lorem or explicit.filters or explicit.globals:
        failures.append("the explicit environment still has a filter or a global")

    print("-- shell-only shape --")
    source = PRODUCTION_SHELL.read_text(encoding="utf-8")
    rendered = explicit.from_string(source).render()
    print(
        f"production shell: {len(source.encode())} bytes, "
        f"{source.count('{{') + source.count('{%')} template tags; "
        f"rendered through Jinja equals its own source: {rendered == source}"
    )
    if rendered != source:
        failures.append("the production shell did not render to itself")

    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT: " + ("FAIL" if failures else "PASS"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
