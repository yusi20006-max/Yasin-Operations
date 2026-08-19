from __future__ import annotations

import json
import shutil
import subprocess
import sys
from importlib import metadata


def test_distribution_exposes_console_entrypoint() -> None:
    distribution = metadata.distribution("yasin-operations")
    entrypoints = {
        entry.name: entry.value
        for entry in distribution.entry_points
        if entry.group == "console_scripts"
    }
    assert entrypoints["yasin-operations"] == "yasin_operations.entrypoint:main"


def test_installed_cli_help() -> None:
    executable = shutil.which("yasin-operations")
    assert executable is not None
    result = subprocess.run(
        [executable, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Yasin-Operations control CLI" in result.stdout


def test_installed_and_module_versions_match() -> None:
    executable = shutil.which("yasin-operations")
    assert executable is not None
    installed = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
    module = subprocess.run([sys.executable, "-m", "yasin_operations", "--version"], capture_output=True, text=True, check=False)
    assert installed.returncode == 0
    assert module.returncode == 0
    assert installed.stdout.strip() == module.stdout.strip()
    assert installed.stdout.startswith("yasin-operations ")


def test_module_entrypoint_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "yasin_operations", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Yasin-Operations control CLI" in result.stdout


def test_doctor_is_graceful_on_supported_or_unsupported_hosts() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "yasin_operations", "--json", "doctor"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in {0, 1}
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["command"] == "doctor"
    assert payload["success"] is (result.returncode == 0)
