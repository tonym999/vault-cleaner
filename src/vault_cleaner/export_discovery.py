"""Deterministic discovery of browser-downloaded DIM exports."""

from __future__ import annotations

import re
from pathlib import Path

EXPORT_BASE_NAMES = {
    "weapons": "destiny-weapon",
    "armor": "destiny-armor",
    "ghosts": "destiny-ghost",
}
EXPORT_FILENAMES = {
    kind: f"{base}.csv"
    for kind, base in EXPORT_BASE_NAMES.items()
}
EXPORT_PATTERNS = {
    kind: re.compile(rf"^{base}( ?\(\d+\))?\.csv$")
    for kind, base in EXPORT_BASE_NAMES.items()
}
EXPLICIT_FLAGS = {
    "weapons": "--input or --weapons",
    "armor": "--input or --armor",
    "ghosts": "--input or --ghosts",
}


class ExportDiscoveryError(OSError):
    """An omitted export path could not be resolved safely."""


class MissingExportError(ExportDiscoveryError):
    """No candidate matched a kind's documented DIM filename pattern."""

    def __init__(self, kind: str, input_dir: Path):
        self.kind = kind
        self.input_dir = input_dir
        self.expected_name = EXPORT_FILENAMES[kind]
        self.pattern = EXPORT_PATTERNS[kind].pattern
        super().__init__(
            f"no {kind} export found in {input_dir}; expected "
            f"{self.expected_name} or a filename matching {self.pattern}"
        )

    @property
    def warning_reason(self) -> str:
        """Snapshot-safe detail: the full directory lives in warning.path."""
        return (
            f"not found; expected {self.expected_name} or pattern {self.pattern}"
        )


class AmbiguousExportError(ExportDiscoveryError):
    """More than one candidate matched, so selecting either would be unsafe."""

    def __init__(self, kind: str, input_dir: Path, filenames: tuple[str, ...]):
        self.kind = kind
        self.input_dir = input_dir
        self.filenames = filenames
        listed = "\n".join(f"  {name}" for name in filenames)
        super().__init__(
            f"multiple {kind} exports match {EXPORT_PATTERNS[kind].pattern} "
            f"in {input_dir}:\n{listed}\n"
            "delete or move the stale copies, or pass the intended file "
            f"explicitly with {EXPLICIT_FLAGS[kind]}"
        )


def expected_export_path(kind: str, input_dir: str | Path) -> Path:
    """Return the exact conventional path without claiming that it exists."""
    return Path(input_dir) / EXPORT_FILENAMES[kind]


def discover_export(kind: str, input_dir: str | Path) -> Path:
    """Return the sole matching export, refusing zero or multiple matches."""
    directory = Path(input_dir)
    pattern = EXPORT_PATTERNS[kind]
    try:
        entries = directory.iterdir()
        candidates = sorted(
            (
                entry
                for entry in entries
                if pattern.fullmatch(entry.name) and entry.is_file()
            ),
            key=lambda entry: entry.name,
        )
    except FileNotFoundError:
        candidates = []
    except OSError as e:
        raise ExportDiscoveryError(
            f"could not search for {kind} exports in {directory}: {e}"
        ) from e

    if not candidates:
        raise MissingExportError(kind, directory)
    if len(candidates) > 1:
        raise AmbiguousExportError(
            kind,
            directory,
            tuple(candidate.name for candidate in candidates),
        )
    return candidates[0]


def select_export(
    kind: str,
    explicit_path: str | Path | None,
    input_dir: str | Path,
) -> Path:
    """Keep explicit paths out of discovery; discover only when omitted."""
    if explicit_path is not None:
        return Path(explicit_path)
    return discover_export(kind, input_dir)
