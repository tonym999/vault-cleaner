import tomllib
from pathlib import Path


def test_runtime_dependencies_and_console_script_are_pinned():
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["dependencies"] == [
        "pandas>=3.0,<4",
        "flask>=3.1,<4",
    ]
    assert metadata["project"]["scripts"] == {
        "vault-cleaner": "vault_cleaner.cli:main"
    }
