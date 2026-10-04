"""The explicit Jinja environment the spike renders with (#137).

Three properties are fixed here rather than left to Flask's defaults:

* ``autoescape=True`` unconditionally.  Flask's own environment decides by
  file extension and turns escaping off for ``.j2`` and ``.txt``.
* ``undefined=StrictUndefined``.  A misspelt context key raises instead of
  rendering as nothing.
* a loader over a fixed allow-list of template names.  A name outside the
  list is "not found" before any source is read, so no request value can
  select a file.

Filters and globals are an allow-list, and the list is empty: the templates
need none.  Removing three named filters was not enough.  ``tojson``,
``urlize`` and ``xmlattr`` return ``Markup`` (``tojson`` output breaks out of
a double-quoted attribute), ``filesizeformat`` and ``round`` convert their
input to a number, and the ``lipsum`` global returns ``Markup`` too.  With an
allow-list a template that reaches for any filter fails to compile, and a new
filter has to be argued for by name.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.resources import files
from pathlib import Path

from jinja2 import BaseLoader, Environment, StrictUndefined, TemplateNotFound

TEMPLATE_NAMES = (
    "shell.html",
    "armor_duplicates.html",
    "_armor_group.html",
    "_verdict.html",
    "whole_page.html",
)
ALLOWED_FILTERS: frozenset[str] = frozenset()
ALLOWED_GLOBALS: frozenset[str] = frozenset()
SPIKE_TEMPLATES = Path(__file__).resolve().parent / "templates"

TemplateSource = Callable[[str], str]


def directory_source(directory: Path) -> TemplateSource:
    """Read an allow-listed name from one fixed directory."""

    def read(name: str) -> str:
        return (directory / name).read_text(encoding="utf-8")

    return read


def package_source(package: str, subdirectory: str) -> TemplateSource:
    """Read an allow-listed name from an installed package's resources."""
    root = files(package).joinpath(subdirectory)

    def read(name: str) -> str:
        return root.joinpath(name).read_text(encoding="utf-8")

    return read


class AllowListLoader(BaseLoader):
    """Serve exactly the names in ``names``; everything else is not found."""

    def __init__(self, names: tuple[str, ...], source: TemplateSource) -> None:
        self._names = frozenset(names)
        self._source = source

    def get_source(self, environment: Environment, template: str):
        if template not in self._names:
            raise TemplateNotFound(template)
        return self._source(template), template, lambda: True


def build_environment(source: TemplateSource | None = None) -> Environment:
    environment = Environment(
        loader=AllowListLoader(
            TEMPLATE_NAMES, source or directory_source(SPIKE_TEMPLATES)
        ),
        autoescape=True,
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    for registry, allowed in (
        (environment.filters, ALLOWED_FILTERS),
        (environment.globals, ALLOWED_GLOBALS),
    ):
        for name in set(registry) - allowed:
            del registry[name]
    return environment
