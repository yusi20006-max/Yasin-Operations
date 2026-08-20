"""Contract tests for the canonical external-agent transport boundary."""
from __future__ import annotations

import json
from pathlib import Path

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.gateway import GATEWAY_SCHEMA_VERSION, JsonlGateway


class FakeExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []

    def execute(self, operation, **kwargs):
        self.calls.append((operation, kwargs))
        from yasin_operations.core.results.models import OperationResult

        return OperationResult.ok(operation.id, {"transport": "jsonl"})

    def find_for_operation(self, _name):
        return []


def _request(**overrides: object) -> str:
    request = {
        "operation": "health_check",
        "target_kind": "self",
        "target_identifier": "runtime",
        "safety_class": "read_only",
        "request_id": "transport-contract-001",
    }
    request.update(overrides)
    return json.dumps({"schema_version": GATEWAY_SCHEMA_VERSION, "request": request})


def test_jsonl_gateway_is_the_current_component_transport() -> None:
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))

    response = gateway.handle_line(_request())

    assert response["schema_version"] == 1
    assert response["success"] is True
    assert response["data"] == {"transport": "jsonl"}
    assert len(executor.calls) == 1
    assert executor.calls[0][1]["source"] == "hermes"


def test_jsonl_schema_version_is_rejected_before_execution() -> None:
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))

    response = gateway.handle_line(
        json.dumps({"schema_version": 999, "request": json.loads(_request())["request"]})
    )

    assert response["success"] is False
    assert response["status"] == "invalid_request"
    assert response["error"]["category"] == "validation_error"
    assert executor.calls == []


def test_jsonl_boundary_replays_recent_read_only_request_without_reexecution() -> None:
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), recent_request_ids=2)

    first = gateway.handle_line(_request(request_id="replay-1"))
    second = gateway.handle_line(_request(request_id="replay-1"))

    assert first["success"] is True
    assert second == first
    assert len(executor.calls) == 1


def test_no_mcp_dependency_is_required_by_the_package() -> None:
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")

    assert "mcp" not in text.lower()
    assert "fastmcp" not in text.lower()


def test_repository_does_not_claim_the_jsonl_gateway_is_mcp() -> None:
    reconciliation = Path(__file__).parents[1] / "docs" / "ARCHITECTURE-RECONCILIATION.md"
    boundary = Path(__file__).parents[1] / "docs" / "TRANSPORT-BOUNDARY.md"

    reconciliation_text = reconciliation.read_text(encoding="utf-8").lower()
    boundary_text = boundary.read_text(encoding="utf-8").lower()

    assert "does not make yasin-operations an mcp server" in reconciliation_text
    assert "no mcp server implementation" in boundary_text
