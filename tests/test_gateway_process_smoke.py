"""Process-level smoke tests for the external JSONL gateway boundary."""
from __future__ import annotations

import json
import subprocess
import sys


def test_gateway_cli_help_is_machine_safe() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "yasin_operations.gateway_cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "serve typed Operations requests over stdin/stdout JSONL" in completed.stdout
    assert completed.stderr == ""


def test_gateway_cli_version_is_machine_safe() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "yasin_operations.gateway_cli", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout.strip() == "gateway-schema-1"
    assert completed.stderr == ""


def test_gateway_cli_smoke_round_trip_has_only_jsonl_on_stdout() -> None:
    request = {
        "schema_version": 1,
        "request": {
            "operation": "health_check",
            "target_kind": "self",
            "target_identifier": "runtime",
            "safety_class": "read_only",
            "request_id": "process-smoke-1",
        },
    }
    completed = subprocess.run(
        [sys.executable, "-m", "yasin_operations.gateway_cli"],
        input=json.dumps(request) + "\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    lines = completed.stdout.splitlines()
    assert len(lines) == 1
    response = json.loads(lines[0])
    assert response["schema_version"] == 1
    assert response["request_id"] == "process-smoke-1"
    assert isinstance(response["success"], bool)
    assert set(response) == {
        "schema_version",
        "request_id",
        "operation_id",
        "success",
        "status",
        "data",
        "error",
        "service_available",
    }


def test_gateway_cli_eof_exits_cleanly() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "yasin_operations.gateway_cli"],
        input="",
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""
