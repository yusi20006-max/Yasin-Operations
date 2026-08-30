from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from subprocess import CompletedProcess
from unittest.mock import patch

from scripts.production_acceptance import (
    FakeProbe,
    _run_cli_command,
    check_ecosystem_adapters,
    check_hermes,
    check_live_services,
)
from yasin_operations.runtime.termux.live_acceptance import _runit_prefix_state


def test_runit_state_normalization_is_authoritative():
    assert _runit_prefix_state("run: service: (pid 123) 10s") == "running"
    assert _runit_prefix_state("down: service: 10s, normally up") == "stopped"
    assert _runit_prefix_state("fail: service: 10s") == "failed"
    assert _runit_prefix_state("timeout: service: 10s") == "failed"
    assert _runit_prefix_state("unexpected output") == "unknown"


def test_fake_probe_matches_requested_service():
    snapshot = FakeProbe().inspect("Yasin-AI")
    assert snapshot.service == "Yasin-AI"
    assert snapshot.available is True
    assert snapshot.state == "running"


def test_hermes_acceptance_checks_use_current_typed_contract():
    results = check_hermes()
    assert results
    assert all(result.status == "PASS" for result in results)


def test_ecosystem_acceptance_checks_inject_probes():
    results = check_ecosystem_adapters()
    assert len(results) == 3
    assert all(result.status == "PASS" for result in results)


def test_live_acceptance_skips_absent_optional_termux_services(tmp_path, monkeypatch):
    root = tmp_path / "service"
    root.mkdir()
    sv = tmp_path / "sv"
    sv.write_text("#!/bin/sh\nexit 0\n")
    sv.chmod(0o755)
    monkeypatch.setenv("YASIN_OPERATIONS_SERVICE_ROOT", str(root))
    monkeypatch.setenv("YASIN_OPERATIONS_SV_PATH", str(sv))
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    results = check_live_services(("hermes-agent", "yasin-ai"))
    service_results = [r for r in results if r.name.startswith("service:")]
    assert len(service_results) == 2
    assert all(result.status == "SKIP" for result in service_results)
    assert all("optional" in result.detail for result in service_results)


def test_doctor_acceptance_valid_degraded_diagnostic_passes():
    payload = {
        "command": "doctor",
        "schema_version": 1,
        "success": False,
        "configuration": {"missing_services": ["yasin-core"], "service_names": ["yasin-core"]},
        "termux": {"status": "degraded", "missing_services": ["yasin-core"]},
        "error": {"category": "diagnostics", "message": "one or more diagnostics reported issues"},
    }
    mock_cp = CompletedProcess(
        args=["python", "-m", "yasin_operations", "--json", "doctor"],
        returncode=1,
        stdout=json.dumps(payload),
        stderr="",
    )
    with patch("subprocess.run", return_value=mock_cp):
        ok, res_payload, detail = _run_cli_command("doctor")
        assert ok is True
        assert res_payload["success"] is False
        assert res_payload["error"]["category"] == "diagnostics"


def test_doctor_acceptance_malformed_json_fails():
    mock_cp = CompletedProcess(
        args=["python", "-m", "yasin_operations", "--json", "doctor"],
        returncode=1,
        stdout="{not-valid-json",
        stderr="parse error",
    )
    with patch("subprocess.run", return_value=mock_cp):
        ok, res_payload, detail = _run_cli_command("doctor")
        assert ok is False
        assert "invalid JSON" in detail


def test_doctor_acceptance_non_diagnostic_error_fails():
    payload = {
        "command": "doctor",
        "schema_version": 1,
        "success": False,
        "configuration": {},
        "termux": {},
        "error": {"category": "configuration", "message": "invalid options"},
    }
    mock_cp = CompletedProcess(
        args=["python", "-m", "yasin_operations", "--json", "doctor"],
        returncode=2,
        stdout=json.dumps(payload),
        stderr="config error",
    )
    with patch("subprocess.run", return_value=mock_cp):
        ok, res_payload, detail = _run_cli_command("doctor")
        assert ok is False
        assert "unexpected exit code" in detail or "non-diagnostic error" in detail


def test_status_and_health_invalid_execution_fails():
    payload_status_fail = {
        "command": "status",
        "schema_version": 1,
        "success": False,
        "error": {"category": "execution_failed", "message": "failed to query"},
    }
    mock_cp_status = CompletedProcess(
        args=["python", "-m", "yasin_operations", "--json", "status"],
        returncode=2,
        stdout=json.dumps(payload_status_fail),
        stderr="",
    )
    with patch("subprocess.run", return_value=mock_cp_status):
        ok, res_payload, detail = _run_cli_command("status")
        assert ok is False
        assert "payload success is not True" in detail

    payload_health_malformed = {
        "command": "health",
        "schema_version": 1,
        "success": True,
    }
    mock_cp_health = CompletedProcess(
        args=["python", "-m", "yasin_operations", "--json", "health"],
        returncode=0,
        stdout=json.dumps(payload_health_malformed),
        stderr="",
    )
    with patch("subprocess.run", return_value=mock_cp_health):
        ok, res_payload, detail = _run_cli_command("health")
        assert ok is False
        assert "malformed health payload structure" in detail


def test_acceptance_cli_emits_successful_json_envelope():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "production_acceptance.py"), "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True
    assert payload["summary"]["fail"] == 0
    assert payload["summary"]["pass"] > 0
    assert payload["summary"]["skip"] >= 1
    assert "blocked" in payload["summary"]
