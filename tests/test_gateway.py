"""Local JSONL Operations Gateway contract tests."""
from __future__ import annotations

import io
import json

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.core.results.models import ErrorCategory
from yasin_operations.gateway import GATEWAY_SCHEMA_VERSION, JsonlGateway
from yasin_operations.safety.classification import SafetyClass


class FakeResult:
    def __init__(self, success=True, data=None, error=None, operation_id="op-1"):
        self.success = success
        self.data = data or {"ok": True}
        self.error = error
        self.operation_id = operation_id


class FakeExecutor:
    def __init__(self, result=None):
        self.result = result or FakeResult()
        self.calls = []

    def execute(self, operation, **kwargs):
        self.calls.append((operation, kwargs))
        return self.result


def _line(**request):
    return json.dumps({"schema_version": GATEWAY_SCHEMA_VERSION, "request": request})


def test_valid_read_only_request_is_forwarded():
    executor = FakeExecutor(FakeResult(data={"services": []}))
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(_line(
        operation="list_services",
        target_kind="service",
        target_identifier="*",
        safety_class="read_only",
        request_id="req-1",
    ))
    assert response["schema_version"] == 1
    assert response["request_id"] == "req-1"
    assert response["success"] is True
    assert response["data"] == {"services": []}
    assert executor.calls[0][1]["source"] == "hermes"


def test_malformed_json_is_structured_and_does_not_raise():
    gateway = JsonlGateway(HermesOperationsAdapter(FakeExecutor()))
    response = gateway.handle_line("{not-json")
    assert response["success"] is False
    assert response["status"] == "invalid_request"
    assert response["error"]["category"] == ErrorCategory.VALIDATION_ERROR.value


def test_invalid_schema_version_is_rejected():
    gateway = JsonlGateway(HermesOperationsAdapter(FakeExecutor()))
    response = gateway.handle_line(json.dumps({"schema_version": 999, "request": {}}))
    assert response["success"] is False
    assert response["status"] == "invalid_request"


def test_missing_required_request_field_is_rejected():
    gateway = JsonlGateway(HermesOperationsAdapter(FakeExecutor()))
    response = gateway.handle_line(json.dumps({"schema_version": 1, "request": {"operation": "health_check"}}))
    assert response["success"] is False
    assert response["error"]["category"] == ErrorCategory.VALIDATION_ERROR.value


def test_mutating_request_still_reaches_existing_policy_boundary():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(_line(
        operation="service_restart",
        target_kind="service",
        target_identifier="demo",
        safety_class="mutating",
        request_id="mut-1",
        confirmation=False,
    ))
    assert response["request_id"] == "mut-1"
    assert len(executor.calls) == 1
    operation, kwargs = executor.calls[0]
    assert operation.safety_class is SafetyClass.MUTATING
    assert kwargs["confirmation"] is False


def test_unavailable_runtime_is_machine_readable():
    gateway = JsonlGateway(HermesOperationsAdapter(None))
    response = gateway.handle_line(_line(
        operation="health_check",
        target_kind="self",
        target_identifier="runtime",
        safety_class="read_only",
        request_id="down-1",
    ))
    assert response["success"] is False
    assert response["status"] == "unavailable"
    assert response["service_available"] is False
    assert response["error"]["category"] == ErrorCategory.UNAVAILABLE_DEPENDENCY.value


def test_gateway_survives_bad_line_and_processes_next_request():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    inp = io.StringIO("not-json\n" + _line(
        operation="health_check",
        target_kind="self",
        target_identifier="runtime",
        safety_class="read_only",
        request_id="next-1",
    ) + "\n")
    out = io.StringIO()
    gateway.serve(inp, out)
    lines = [json.loads(line) for line in out.getvalue().splitlines()]
    assert len(lines) == 2
    assert lines[0]["success"] is False
    assert lines[1]["request_id"] == "next-1"


def test_stop_stops_loop():
    gateway = JsonlGateway(HermesOperationsAdapter(FakeExecutor()))
    gateway.stop()
    inp = io.StringIO(_line(
        operation="health_check",
        target_kind="self",
        target_identifier="runtime",
        safety_class="read_only",
    ) + "\n")
    out = io.StringIO()
    gateway.serve(inp, out)
    assert out.getvalue() == ""
