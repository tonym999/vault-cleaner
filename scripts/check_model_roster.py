"""Schema and staleness check for the model roster (#191).

``handoffs/models.toml`` records which models fill each role of the
multi-agent handoff workflow, plus a catalog of those models with a
``verified`` date and sources per row. This script validates the file's
schema and cross-references (every error is reported, not just the first)
and warns, without failing, about catalog rows whose ``verified`` date is
older than the file's ``stale_after_days`` threshold.

Stdlib-only: no import of ``vault_cleaner`` or any third-party package, so
CI can run it with a bare ``python3``. It needs Python 3.11+ for ``tomllib``.

Run directly to check ``handoffs/models.toml`` relative to the repository
root:

    python3 scripts/check_model_roster.py [PATH] [--today YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import os
import sys
import tomllib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO / "handoffs" / "models.toml"

SCHEMA_VERSION = 1
ADAPTIVE = "adaptive"
ADAPTIVE_EFFORT = "n/a — adaptive"  # em dash, single spaces

TOP_KEYS = ("schema_version", "stale_after_days", "models", "assignments")
MODEL_REQUIRED = (
    "id",
    "provider",
    "family",
    "effort_control",
    "effort_values",
    "stability",
    "verified",
    "sources",
)
MODEL_OPTIONAL = ("default_effort", "notes", "launch_surfaces")
ASSIGNMENT_REQUIRED = ("role", "standing", "model")
ASSIGNMENT_OPTIONAL = ("rung", "effort", "effort_when_needed")

ROLES = ("planner", "orchestrator", "implementer", "reviewer")
STANDINGS = ("primary", "alternative")
RUNGS = ("bounded", "judgement", "high-risk")


class RosterError(ValueError):
    """The roster file could not be read or is not valid TOML."""


def load_roster(path: Path) -> dict:
    """Read and parse the roster file; raise RosterError naming the path."""
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise RosterError(f"{path}: not valid TOML: {exc}") from exc
    except OSError as exc:
        raise RosterError(f"{path}: cannot read file: {exc}") from exc


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _is_text(value: object) -> bool:
    """A non-empty string with no leading or trailing whitespace."""
    return isinstance(value, str) and value != "" and value == value.strip()


def _is_int(value: object) -> bool:
    # bool is an int subclass, so isinstance() would accept TOML ``true``.
    return type(value) is int


def _check_unique_texts(errors: list[str], where: str, key: str, value: object) -> bool:
    """Check ``value`` is a list of unique text strings; return True if so."""
    if not isinstance(value, list):
        errors.append(f"{where}: {key} must be a list")
        return False
    ok = True
    for item in value:
        if not _is_text(item):
            errors.append(f"{where}: {key} entries must be non-empty strings without surrounding whitespace")
            ok = False
            break
    if ok and len(set(value)) != len(value):
        errors.append(f"{where}: {key} has a duplicate entry")
        ok = False
    return ok


def _validate_model(
    row: dict, index: int, today: date, errors: list[str]
) -> None:
    ident = row.get("id")
    where = f'model "{ident}"' if _is_text(ident) else f"model #{index}"

    for key in MODEL_REQUIRED:
        if key not in row:
            errors.append(f"{where}: missing key {key}")
    for key in row:
        if key not in MODEL_REQUIRED and key not in MODEL_OPTIONAL:
            errors.append(f"{where}: unknown key {key}")

    for key in ("id", "provider", "family", "effort_control", "stability", "notes"):
        if key in row and not _is_text(row[key]):
            errors.append(f"{where}: {key} must be a non-empty string without surrounding whitespace")

    adaptive = row.get("effort_control") == ADAPTIVE
    values = row.get("effort_values")
    values_ok = False
    if "effort_values" in row:
        values_ok = _check_unique_texts(errors, where, "effort_values", values)
        if values_ok and _is_text(row.get("effort_control")):
            if adaptive and values:
                errors.append(f"{where}: effort_values must be empty when effort_control is {ADAPTIVE}")
            if not adaptive and not values:
                errors.append(f"{where}: effort_values must not be empty unless effort_control is {ADAPTIVE}")

    if "default_effort" in row:
        default = row["default_effort"]
        if adaptive:
            errors.append(f"{where}: default_effort is not allowed when effort_control is {ADAPTIVE}")
        elif not _is_text(default):
            errors.append(f"{where}: default_effort must be a non-empty string")
        elif values_ok and default not in values:
            errors.append(f"{where}: default_effort {default!r} is not in effort_values")

    if "verified" in row:
        verified = row["verified"]
        # datetime is a date subclass, so isinstance() would accept it.
        if type(verified) is not date:
            errors.append(f"{where}: verified must be a TOML date (YYYY-MM-DD), not {type(verified).__name__}")
        elif verified > today + timedelta(days=1):
            errors.append(f"{where}: verified {verified.isoformat()} is in the future")

    if "sources" in row:
        sources = row["sources"]
        if not isinstance(sources, list) or not sources:
            errors.append(f"{where}: sources must be a non-empty list")
        elif _check_unique_texts(errors, where, "sources", sources):
            for source in sources:
                if not source.startswith("https://"):
                    errors.append(f"{where}: source {source!r} must start with https://")

    if "launch_surfaces" in row:
        surfaces = row["launch_surfaces"]
        if isinstance(surfaces, list) and not surfaces:
            errors.append(f"{where}: launch_surfaces must not be empty")
        else:
            _check_unique_texts(errors, where, "launch_surfaces", surfaces)


def _validate_assignment(
    row: object, index: int, models: dict[str, dict], errors: list[str]
) -> None:
    if not isinstance(row, dict):
        errors.append(f"assignment #{index}: must be a table")
        return
    where = f"assignment #{index} (role={row.get('role')!r}, model={row.get('model')!r})"

    for key in ASSIGNMENT_REQUIRED:
        if key not in row:
            errors.append(f"{where}: missing key {key}")
    for key in row:
        if key not in ASSIGNMENT_REQUIRED and key not in ASSIGNMENT_OPTIONAL:
            errors.append(f"{where}: unknown key {key}")

    role = row.get("role")
    if "role" in row and role not in ROLES:
        errors.append(f"{where}: role must be one of {', '.join(ROLES)}")
    if "standing" in row and row["standing"] not in STANDINGS:
        errors.append(f"{where}: standing must be one of {', '.join(STANDINGS)}")

    if "rung" in row:
        if role != "implementer":
            errors.append(f"{where}: rung is only allowed for the implementer role")
        elif row["rung"] not in RUNGS:
            errors.append(f"{where}: rung must be one of {', '.join(RUNGS)}")
    elif role == "implementer":
        errors.append(f"{where}: implementer assignments require rung")

    if "effort" not in row and role in ROLES and role != "orchestrator":
        errors.append(f"{where}: effort is required unless role is orchestrator")
    if "effort_when_needed" in row:
        if "effort" not in row:
            errors.append(f"{where}: effort_when_needed requires effort")
        elif row["effort_when_needed"] == row["effort"]:
            errors.append(f"{where}: effort_when_needed must differ from effort")

    name = row.get("model")
    if "model" not in row:
        return
    if not isinstance(name, str) or name not in models:
        errors.append(f"{where}: model {name!r} is not in the models catalog")
        return
    model = models[name]
    values = model.get("effort_values")
    if model.get("effort_control") == ADAPTIVE:
        if "effort" in row and row["effort"] != ADAPTIVE_EFFORT:
            errors.append(f"{where}: effort for an adaptive model must be {ADAPTIVE_EFFORT!r}")
        if "effort_when_needed" in row:
            errors.append(f"{where}: effort_when_needed is not allowed for an adaptive model")
    elif isinstance(values, list):
        for key in ("effort", "effort_when_needed"):
            if key in row and row[key] not in values:
                errors.append(f"{where}: {key} {row[key]!r} is not in effort_values of model {name!r}")


def validate(data: dict, *, today: date) -> list[str]:
    """Return every schema and cross-reference error; empty means valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["top level must be a table"]

    for key in TOP_KEYS:
        if key not in data:
            errors.append(f"missing top-level key {key}")
    for key in data:
        if key not in TOP_KEYS:
            errors.append(f"unknown top-level key {key}")

    # type() is int: True == 1 and 1.0 == 1 in Python.
    if "schema_version" in data and not (_is_int(data["schema_version"]) and data["schema_version"] == SCHEMA_VERSION):
        errors.append(f"schema_version must be the integer {SCHEMA_VERSION}")
    if "stale_after_days" in data:
        days = data["stale_after_days"]
        if not _is_int(days) or days <= 0:
            errors.append("stale_after_days must be a positive integer")

    raw_models = data.get("models", [])
    raw_assignments = data.get("assignments", [])
    for key, raw in (("models", raw_models), ("assignments", raw_assignments)):
        if key in data and (not isinstance(raw, list) or not raw):
            errors.append(f"{key} must be a non-empty list of tables")
    if not isinstance(raw_models, list):
        raw_models = []
    if not isinstance(raw_assignments, list):
        raw_assignments = []

    models: dict[str, dict] = {}
    for index, row in enumerate(raw_models, start=1):
        if not isinstance(row, dict):
            errors.append(f"model #{index}: must be a table")
            continue
        _validate_model(row, index, today, errors)
        ident = row.get("id")
        if _is_text(ident):
            if ident in models:
                errors.append(f'model "{ident}": duplicate id')
            else:
                models[ident] = row

    seen: set[tuple] = set()
    used: set[str] = set()
    primaries: set[tuple[str, str | None]] = set()
    for index, row in enumerate(raw_assignments, start=1):
        _validate_assignment(row, index, models, errors)
        if not isinstance(row, dict):
            continue
        role, rung, model = row.get("role"), row.get("rung"), row.get("model")
        if isinstance(model, str):
            used.add(model)
        try:
            key = (role, rung, model)
            if key in seen:
                errors.append(
                    f"assignment #{index} (role={role!r}, model={model!r}): "
                    f"duplicate (role, rung, model) {key!r}"
                )
            seen.add(key)
        except TypeError:
            pass  # unhashable values were already reported above
        if row.get("standing") == "primary" and isinstance(role, str):
            primaries.add((role, rung if isinstance(rung, str) else None))

    if raw_models and raw_assignments:
        for ident in models:
            if ident not in used:
                errors.append(f'model "{ident}": not used by any assignment')
        needed = [("planner", None), ("orchestrator", None), ("reviewer", None)]
        needed += [("implementer", rung) for rung in RUNGS]
        for role, rung in needed:
            if (role, rung) not in primaries:
                label = f"{role} ({rung} rung)" if rung else role
                errors.append(f"no primary assignment for {label}")
    return errors


# ---------------------------------------------------------------------------
# Staleness
# ---------------------------------------------------------------------------


def _stale(data: dict, *, today: date) -> list[tuple[str, str]]:
    threshold = data["stale_after_days"]
    found = []
    for row in data["models"]:
        age = (today - row["verified"]).days
        if age > threshold:
            message = (
                f'model row "{row["id"]}" was verified {row["verified"].isoformat()}, '
                f"{age} days ago (threshold {threshold} days); "
                're-verify it against its sources and update "verified" '
                "(handoffs/README.md, Re-verification)"
            )
            found.append((row["id"], message))
    return found


def stale_rows(data: dict, *, today: date) -> list[str]:
    """One warning per model row older than ``stale_after_days``.

    Only call this on data that ``validate`` accepted.
    """
    return [message for _, message in _stale(data, today=today)]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _id_line(path: Path, ident: str) -> int | None:
    """1-based line of the first ``id = "<ident>"`` line, if any."""
    wanted = f'id = "{ident}"'
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    for number, line in enumerate(lines, start=1):
        if line.strip() == wanted:
            return number
    return None


def _relpath(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO).as_posix()
    except ValueError:
        return resolved.as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate handoffs/models.toml and warn about stale rows.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PATH)
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="treat this YYYY-MM-DD date as today (default: current UTC date)",
    )
    args = parser.parse_args(argv)
    path: Path = args.path
    today: date = args.today or datetime.now(UTC).date()
    annotate = os.environ.get("GITHUB_ACTIONS") == "true"
    rel = _relpath(path)

    def error(message: str, *, names_path: bool = False) -> None:
        if annotate:
            print(f"::error file={rel}::{message}")
        else:
            print(f"error: {message}" if names_path else f"error: {path}: {message}")

    try:
        data = load_roster(path)
    except RosterError as exc:
        error(str(exc), names_path=True)  # RosterError messages start with the path
        return 1
    problems = validate(data, today=today)
    if problems:
        for problem in problems:
            error(problem)
        return 1

    stale = _stale(data, today=today)
    for ident, message in stale:
        if annotate:
            line = _id_line(path, ident)
            where = f"file={rel}" + (f",line={line}" if line is not None else "")
            print(f"::warning {where},title=Stale model row::{message}")
        else:
            print(f"warning: {path}: {message}")
    print(f"{path}: {len(data['models'])} models, {len(data['assignments'])} assignments, {len(stale)} stale")
    return 0


if __name__ == "__main__":
    sys.exit(main())
