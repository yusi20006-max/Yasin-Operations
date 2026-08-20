from __future__ import annotations

import json
import shutil
import subprocess


def test_installed_gateway_subcommand_smoke() -> None:
    executable = shutil.which("yasin-operations")
    assert executable is not None
    request = {
        "schema_version": 1,
        "request": {
            "operation": "health_check",
            "target_kind": "self",
            "target_identifier": "runtime",
            "safety_class": "read_only",
            "request_id": "release-gateway-smoke",
        },
    }
    result = subprocess.run(
        [executable, "gateway"],
        input=json.dumps(request) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["request_id"] == "release-gateway-smoke"
    assert payload["status"] in {"succeeded", "failed"}


def test_installed_gateway_help() -> None:
    executable = shutil.which("yasin-operations")
    assert executable is not None
    result = subprocess.run(
        [executable, "gateway", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "serve typed Operations requests over stdin/stdout JSONL" in result.stdout
