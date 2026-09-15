from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from yasin_operations.termux_launcher import main, load_registry


def test_termux_launcher_list_outputs_all_registry_entries(capsys):
    registry = load_registry()
    rc = main(["list"])
    assert rc == 0
    captured = capsys.readouterr()
    for name, spec in registry.items():
        assert name in captured.out


def test_termux_launcher_module_execution():
    root = Path(__file__).resolve().parents[1]
    res = subprocess.run(
        [sys.executable, "-m", "yasin_operations.termux_launcher", "list"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    registry = load_registry()
    for name in registry:
        assert name in res.stdout


def test_termux_launcher_script_execution():
    root = Path(__file__).resolve().parents[1]
    script = root / "yasin_operations" / "termux_launcher.py"
    res = subprocess.run(
        [sys.executable, str(script), "list"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0
    registry = load_registry()
    for name in registry:
        assert name in res.stdout
