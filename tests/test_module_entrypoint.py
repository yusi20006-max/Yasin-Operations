from __future__ import annotations

import subprocess
import sys


def test_module_help_entrypoint() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "yasin_operations", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Yasin-Operations control CLI" in result.stdout
    assert "doctor" in result.stdout


def test_module_entrypoint_is_importable() -> None:
    import yasin_operations.__main__ as entrypoint

    assert callable(entrypoint.main)
