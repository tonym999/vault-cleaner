"""Suite-wide guard on which checkout is actually under test.

No fixtures live here on purpose: the single hook exists to remove a silent
failure mode, not to configure test behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import vault_cleaner


def pytest_configure(config: pytest.Config) -> None:
    """Refuse to run against a `vault_cleaner` from a different checkout.

    The editable install writes one absolute `src` path into a `.pth`, which
    every interpreter using the venv picks up regardless of cwd. Without
    pytest's `pythonpath`, a run from a git worktree therefore exercises the
    main checkout's source: a deliberately injected fault once passed that
    way. Assert the import origin rather than trusting the mechanism.
    """
    expected = (config.rootpath / "src" / "vault_cleaner").resolve()
    actual = Path(vault_cleaner.__file__).resolve().parent
    if actual != expected:
        raise pytest.UsageError(
            "vault_cleaner was imported from a different checkout than the "
            "one under test:\n"
            f"  imported: {actual}\n"
            f"  expected: {expected}\n"
            "Results would describe the other checkout's source. Check that "
            'pytest\'s `pythonpath = ["src"]` still applies, or set '
            "PYTHONPATH to this checkout's src/."
        )
