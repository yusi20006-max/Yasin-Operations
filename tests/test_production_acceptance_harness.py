from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.production_acceptance import (
    FakeProbe,
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
