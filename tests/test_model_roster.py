"""Tests for the model roster checker (scripts/check_model_roster.py, #191)."""

from __future__ import annotations

import copy
import importlib.util
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
REAL_ROSTER = REPO / "handoffs" / "models.toml"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


roster = _load_module("check_model_roster", SCRIPTS / "check_model_roster.py")

TODAY = date(2026, 10, 1)
EM_DASH_ADAPTIVE = "n/a — adaptive"


def _model(ident: str, **overrides) -> dict:
    row = {
        "id": ident,
        "provider": "FakeCo",
        "family": "Fake",
        "effort_control": "reasoning.effort",
        "effort_values": ["low", "medium", "high", "xhigh"],
        "default_effort": "medium",
        "stability": "Stable",
        "verified": date(2026, 9, 25),
        "sources": ["https://example.com/a", "https://example.com/b"],
    }
    row.update(overrides)
    return {k: v for k, v in row.items() if v is not None}


def _assignment(role: str, model: str, standing: str = "primary", **extra) -> dict:
    row = {"role": role, "standing": standing, "model": model}
    row.update(extra)
    return row


def baseline() -> dict:
    """A synthetic valid roster; never derived from the real file."""
    return {
        "schema_version": 1,
        "stale_after_days": 30,
        "models": [
            _model("fake-reasoner"),
            _model(
                "fake-adaptive",
                effort_control="adaptive",
                effort_values=[],
                default_effort=None,
                launch_surfaces=["Fake local surface"],
            ),
        ],
        "assignments": [
            _assignment("planner", "fake-reasoner", effort="high", effort_when_needed="xhigh"),
            _assignment("orchestrator", "fake-reasoner"),
            _assignment("reviewer", "fake-reasoner", effort="high"),
            _assignment("implementer", "fake-adaptive", rung="bounded", effort=EM_DASH_ADAPTIVE),
            _assignment("implementer", "fake-reasoner", rung="judgement", effort="high"),
            _assignment("implementer", "fake-reasoner", rung="high-risk", effort="high"),
        ],
    }


def _fresh() -> dict:
    return copy.deepcopy(baseline())


def _toml(data: dict) -> str:
    """Minimal TOML writer for the synthetic baseline's shapes."""

    def value(v) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, list):
            return "[" + ", ".join(value(i) for i in v) + "]"
        if isinstance(v, str):
            return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return str(v)

    lines = [f"schema_version = {data['schema_version']}", f"stale_after_days = {data['stale_after_days']}", ""]
    for table in ("models", "assignments"):
        for row in data[table]:
            lines.append(f"[[{table}]]")
            lines.extend(f"{k} = {value(v)}" for k, v in row.items())
            lines.append("")
    return "\n".join(lines)


def _write(tmp_path: Path, data: dict, name: str = "models.toml") -> Path:
    path = tmp_path / name
    path.write_text(_toml(data), encoding="utf-8", newline="\n")
    return path


def _errors(data: dict) -> list[str]:
    return roster.validate(data, today=TODAY)


# ---------------------------------------------------------------------------
# Valid inputs
# ---------------------------------------------------------------------------


def test_baseline_is_valid():
    assert _errors(_fresh()) == []


def test_real_roster_is_valid():
    data = roster.load_roster(REAL_ROSTER)
    assert roster.validate(data, today=datetime.now(UTC).date()) == []


# ---------------------------------------------------------------------------
# Negative cases: each mutates the baseline and expects a specific message
# ---------------------------------------------------------------------------


def _set(table, index, key, value):
    def mutate(data):
        data[table][index][key] = value

    return mutate


def _drop(table, index, key):
    def mutate(data):
        del data[table][index][key]

    return mutate


def _top(key, value):
    def mutate(data):
        data[key] = value

    return mutate


def _drop_top(key):
    def mutate(data):
        del data[key]

    return mutate


def _dup_model(data):
    data["models"].append(copy.deepcopy(data["models"][0]))


def _dup_assignment(data):
    data["assignments"].append(copy.deepcopy(data["assignments"][0]))


def _unused_model(data):
    data["models"].append(_model("fake-unused"))


def _no_primary_reviewer(data):
    data["assignments"][2]["standing"] = "alternative"


def _no_primary_high_risk(data):
    data["assignments"][5]["standing"] = "alternative"


NEGATIVE_CASES = [
    ("unknown-top-key", _top("surprise", 1), "unknown top-level key surprise"),
    ("missing-assignments", _drop_top("assignments"), "missing top-level key assignments"),
    ("schema-version-2", _top("schema_version", 2), "schema_version must be"),
    ("schema-version-bool", _top("schema_version", True), "schema_version must be"),
    ("schema-version-float", _top("schema_version", 1.0), "schema_version must be"),
    ("stale-days-zero", _top("stale_after_days", 0), "stale_after_days must be a positive integer"),
    ("stale-days-bool", _top("stale_after_days", True), "stale_after_days must be a positive integer"),
    ("stale-days-string", _top("stale_after_days", "30"), "stale_after_days must be a positive integer"),
    ("duplicate-model-id", _dup_model, 'model "fake-reasoner": duplicate id'),
    ("unknown-model-key", _set("models", 0, "color", "red"), "unknown key color"),
    ("missing-sources", _drop("models", 0, "sources"), "missing key sources"),
    ("verified-string", _set("models", 0, "verified", "2026-10-01"), "verified must be a TOML date"),
    (
        "verified-datetime",
        _set("models", 0, "verified", datetime(2026, 9, 25, tzinfo=UTC)),
        "verified must be a TOML date",
    ),
    ("verified-future", _set("models", 0, "verified", date(2026, 10, 3)), "is in the future"),
    (
        "adaptive-with-values",
        _set("models", 1, "effort_values", ["low"]),
        "effort_values must be empty when effort_control is adaptive",
    ),
    (
        "non-adaptive-empty-values",
        _set("models", 0, "effort_values", []),
        "effort_values must not be empty unless",
    ),
    (
        "duplicate-effort-value",
        _set("models", 0, "effort_values", ["low", "low", "medium"]),
        "effort_values has a duplicate entry",
    ),
    (
        "default-not-in-values",
        _set("models", 0, "default_effort", "max"),
        "default_effort 'max' is not in effort_values",
    ),
    (
        "default-on-adaptive",
        _set("models", 1, "default_effort", "high"),
        "default_effort is not allowed when effort_control is adaptive",
    ),
    (
        "http-source",
        _set("models", 0, "sources", ["http://example.com/a"]),
        "must start with https://",
    ),
    ("empty-sources", _set("models", 0, "sources", []), "sources must be a non-empty list"),
    (
        "empty-launch-surfaces",
        _set("models", 1, "launch_surfaces", []),
        "launch_surfaces must not be empty",
    ),
    (
        "duplicate-launch-surface",
        _set("models", 1, "launch_surfaces", ["A", "A"]),
        "launch_surfaces has a duplicate entry",
    ),
    (
        "non-string-launch-surface",
        _set("models", 1, "launch_surfaces", [3]),
        "launch_surfaces entries must be non-empty strings",
    ),
    ("unknown-role", _set("assignments", 0, "role", "janitor"), "role must be one of"),
    ("unknown-standing", _set("assignments", 0, "standing", "maybe"), "standing must be one of"),
    ("unknown-rung", _set("assignments", 3, "rung", "huge"), "rung must be one of"),
    ("implementer-without-rung", _drop("assignments", 3, "rung"), "implementer assignments require rung"),
    ("planner-with-rung", _set("assignments", 0, "rung", "bounded"), "rung is only allowed for the implementer"),
    ("planner-without-effort", _drop("assignments", 0, "effort"), "effort is required unless role is orchestrator"),
    (
        "missing-model",
        _set("assignments", 0, "model", "ghost-model"),
        "model 'ghost-model' is not in the models catalog",
    ),
    (
        "effort-not-allowed",
        _set("assignments", 0, "effort", "turbo"),
        "effort 'turbo' is not in effort_values",
    ),
    (
        "adaptive-with-real-effort",
        _set("assignments", 3, "effort", "high"),
        "effort for an adaptive model must be",
    ),
    (
        "adaptive-with-hyphen",
        _set("assignments", 3, "effort", "n/a - adaptive"),
        "effort for an adaptive model must be",
    ),
    (
        "when-needed-not-allowed",
        _set("assignments", 0, "effort_when_needed", "turbo"),
        "effort_when_needed 'turbo' is not in effort_values",
    ),
    (
        "when-needed-on-adaptive",
        _set("assignments", 3, "effort_when_needed", "high"),
        "effort_when_needed is not allowed for an adaptive model",
    ),
    (
        "when-needed-equals-effort",
        _set("assignments", 0, "effort_when_needed", "high"),
        "effort_when_needed must differ from effort",
    ),
    (
        "when-needed-without-effort",
        _set("assignments", 1, "effort_when_needed", "high"),  # orchestrator has no effort
        "effort_when_needed requires effort",
    ),
    ("duplicate-assignment", _dup_assignment, "duplicate (role, rung, model)"),
    ("unused-model-row", _unused_model, 'model "fake-unused": not used by any assignment'),
    ("no-primary-reviewer", _no_primary_reviewer, "no primary assignment for reviewer"),
    ("no-primary-high-risk", _no_primary_high_risk, "no primary assignment for implementer (high-risk rung)"),
    ("unknown-assignment-key", _set("assignments", 0, "mood", "good"), "unknown key mood"),
]


@pytest.mark.parametrize(
    "mutate, expected",
    [pytest.param(m, e, id=name) for name, m, e in NEGATIVE_CASES],
)
def test_negative_cases(mutate, expected):
    data = _fresh()
    mutate(data)
    errors = _errors(data)
    assert any(expected in error for error in errors), (expected, errors)


def test_validate_reports_every_error():
    data = _fresh()
    data["models"][0]["sources"] = ["http://example.com/a"]
    data["assignments"][0]["role"] = "janitor"
    errors = _errors(data)
    assert len(errors) >= 2
    assert any("must start with https://" in e for e in errors)
    assert any("role must be one of" in e for e in errors)


def test_broken_row_does_not_raise():
    data = _fresh()
    del data["models"][0]["id"]
    data["assignments"][1] = "not a table"
    errors = _errors(data)
    assert any("model #1: missing key id" in e for e in errors)
    assert any("assignment #2: must be a table" in e for e in errors)


# ---------------------------------------------------------------------------
# Stale-row signal
# ---------------------------------------------------------------------------


def _stale_data() -> dict:
    data = _fresh()
    data["models"][0]["verified"] = date(2026, 9, 1)
    return data


def test_stale_boundary_is_strictly_greater_than_threshold():
    data = _stale_data()
    assert roster.stale_rows(data, today=date(2026, 10, 1)) == []  # 30 days
    messages = roster.stale_rows(data, today=date(2026, 10, 2))  # 31 days
    assert messages == [
        (
            'model row "fake-reasoner" was verified 2026-09-01, 31 days ago (threshold 30 days); '
            're-verify it against its sources and update "verified" (handoffs/README.md, Re-verification)'
        )
    ]


def test_main_stale_row_warns_and_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    path = _write(tmp_path, _stale_data())
    assert roster.main([str(path), "--today", "2026-10-02"]) == 0
    out = capsys.readouterr().out
    assert "warning:" in out
    assert "1 stale" in out


def test_main_github_annotation(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    path = _write(tmp_path, _stale_data())
    expected_line = next(
        n for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if line.strip() == 'id = "fake-reasoner"'
    )
    assert roster.main([str(path), "--today", "2026-10-02"]) == 0
    out = capsys.readouterr().out
    assert "::warning file=" in out
    assert f",line={expected_line},title=Stale model row::" in out
    assert "1 stale" in out


def test_main_fresh_file_has_no_warnings(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    path = _write(tmp_path, _fresh())
    assert roster.main([str(path), "--today", "2026-10-01"]) == 0
    out = capsys.readouterr().out
    assert "warning" not in out
    assert "0 stale" in out


def test_main_invalid_exits_one(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    data = _fresh()
    data["assignments"][0]["role"] = "janitor"
    bad_schema = _write(tmp_path, data, "bad-schema.toml")
    assert roster.main([str(bad_schema), "--today", "2026-10-01"]) == 1
    out = capsys.readouterr().out
    assert "error:" in out and "role must be one of" in out

    bad_toml = tmp_path / "bad-toml.toml"
    bad_toml.write_text("this is = = not toml\n", encoding="utf-8", newline="\n")
    assert roster.main([str(bad_toml)]) == 1
    out = capsys.readouterr().out
    assert "error:" in out and str(bad_toml) in out


def test_main_missing_file_exits_one(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    missing = tmp_path / "nope.toml"
    assert roster.main([str(missing)]) == 1
    assert str(missing) in capsys.readouterr().out
