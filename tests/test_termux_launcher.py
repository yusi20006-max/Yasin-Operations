from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from yasin_operations.termux_launcher import _resolve_executable, main, load_registry


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


def test_hub_managed_service_rejects_arguments(capsys):
    rc = main(["yasin-agent", "--help"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "is a managed service and does not accept startup arguments" in err


def test_direct_launcher_skips_own_wrapper(tmp_path, monkeypatch):
    """A wrapper shadowing the real binary must not cause self-recursion."""
    real_dir = tmp_path / "realbin"
    wrap_dir = tmp_path / "wraps"
    real_dir.mkdir()
    wrap_dir.mkdir()
    real = real_dir / "yasin"
    wrap = wrap_dir / "yasin"
    real.write_text("#!/bin/sh\necho real\n", encoding="utf-8")
    real.chmod(0o755)
    wrap.write_text(
        '#!/data/data/com.termux/files/usr/bin/bash\n'
        'exec "python" "termux_launcher.py" "yasin" "$@"\n',
        encoding="utf-8",
    )
    wrap.chmod(0o755)
    monkeypatch.setenv(
        "PATH", os.pathsep.join([str(wrap_dir), str(real_dir)])
    )
    assert _resolve_executable("yasin") == str(real)


def test_resolve_executable_keeps_unknown_name(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert _resolve_executable("no-such-yasin-command") == "no-such-yasin-command"

