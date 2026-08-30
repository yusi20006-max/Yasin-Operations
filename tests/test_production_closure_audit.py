"""P4.5 production closure documentation contract."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "docs" / "FINAL_PRODUCTION_CLOSURE_MONITORING_P4.md"


def test_monitoring_program_closure_document_exists() -> None:
    assert CLOSURE.is_file()
    text = CLOSURE.read_text(encoding="utf-8")
    assert "Production closure for the Monitoring Completion Program: ACCEPTED" in text
    assert "Hosted CI vs live Termux evidence" in text
    assert "No Critical or High production findings" in text
    assert "yasin_monitor" in text
    assert "PASS/FAIL/SKIP/BLOCKED" in text or "PASS / FAIL / SKIP / BLOCKED" in text


def test_release_readiness_documents_optional_mcp_bridge() -> None:
    text = (ROOT / "docs" / "RELEASE_READINESS_v0.1.0.md").read_text(encoding="utf-8")
    assert "optional" in text.lower()
    assert "mcp_server" in text or "stdio MCP" in text
    assert "no MCP SDK implementation" not in text
