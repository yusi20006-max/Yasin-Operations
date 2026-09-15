from __future__ import annotations

import subprocess
import sys

from yasin_operations import termux_launcher


def test_termux_launcher_main_list_outputs_registry_entries(capsys) -> None:
    code = termux_launcher.main(["list"])
    assert code == 0
    output = capsys.readouterr().out
    assert "runtime.process" in output
    assert "runtime.service" in output
    assert "runtime.health" in output
    assert "runtime.diagnostics" in output


def test_termux_launcher_module_execution() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "yasin_operations.termux_launcher", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "runtime.process" in result.stdout
