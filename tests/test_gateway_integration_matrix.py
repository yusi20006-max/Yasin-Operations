"""End-to-end external gateway integration and abuse-resistance tests."""
from __future__ import annotations

import io
import json
import subprocess
import sys

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.gateway import GATEWAY_SCHEMA_VERSION, JsonlGateway
from yasin_operations.safety.classification import SafetyClass


class FakeExecutor:
    def __init__(self, *, success=True):
        self.calls = []
        self.success = success

    def execute(self, operation, **kwargs):
        self.calls.append((operation, kwargs))
        if self.success:
            return OperationResult.ok(operation.id, {"operation": operation.name})
        return OperationResult.fail(operation.id, OperationError(ErrorCategory.UNAVAILABLE_DEPENDENCY, "runtime unavailable"))


def line(**request):
    return json.dumps({"schema_version": GATEWAY_SCHEMA_VERSION, "request": request}, ensure_ascii=False, separators=(",", ":"))


def valid(**overrides):
    request = {"operation": "health_check", "target_kind": "self", "target_identifier": "runtime", "safety_class": "read_only", "request_id": "integration-001"}
    request.update(overrides)
    return line(**request)


def test_round_trip_preserves_schema_identity_and_structured_data():
    executor = FakeExecutor()
    response = JsonlGateway(HermesOperationsAdapter(executor)).handle_line(valid())
    assert response["schema_version"] == 1
    assert response["request_id"] == "integration-001"
    assert response["operation_id"] == executor.calls[0][0].id
    assert response["success"] is True
    assert response["data"] == {"operation": "health_check"}


def test_non_object_and_invalid_json_are_structured():
    gateway = JsonlGateway(HermesOperationsAdapter(FakeExecutor()))
    for payload in ("[]", "null", '"string"', "{broken"):
        response = gateway.handle_line(payload)
        assert response["success"] is False
        assert response["status"] == "invalid_request"
        assert response["error"]["category"] == ErrorCategory.VALIDATION_ERROR.value


def test_identifier_control_characters_and_length_are_rejected():
    gateway = JsonlGateway(HermesOperationsAdapter(FakeExecutor()), max_identifier_length=16)
    for request_id in ("bad\nrequest", "x" * 17):
        response = gateway.handle_line(valid(request_id=request_id))
        assert response["success"] is False
        assert response["status"] == "invalid_request"


def test_oversized_parameter_is_rejected_before_execution():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), max_line_bytes=2048, max_parameter_bytes=256)
    response = gateway.handle_line(valid(parameters={"blob": "x" * 1000}))
    assert not response["success"]
    assert executor.calls == []
    assert response["error"]["category"] == ErrorCategory.VALIDATION_ERROR.value


def test_duplicate_mutation_request_cannot_reach_executor_twice():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    request = valid(operation="service_restart", target_kind="service", target_identifier="demo", safety_class="mutating", confirmation=True, request_id="mutation-1")
    first = gateway.handle_line(request)
    second = gateway.handle_line(request)
    assert first["success"] is True
    assert second["success"] is False
    assert second["status"] == "invalid_request"
    assert len(executor.calls) == 1


def test_duplicate_read_only_request_replays_cached_response_without_reexecution():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), recent_request_ids=2)
    first = gateway.handle_line(valid(request_id="a"))
    second = gateway.handle_line(valid(request_id="a"))
    assert second == first
    assert len(executor.calls) == 1


def test_replay_window_eviction_is_deterministic():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), recent_request_ids=2)
    assert gateway.handle_line(valid(request_id="a"))["success"]
    assert gateway.handle_line(valid(request_id="b"))["success"]
    assert gateway.handle_line(valid(request_id="c"))["success"]
    replayed = gateway.handle_line(valid(request_id="a"))
    assert replayed["success"]
    assert len(executor.calls) == 4


def test_mutation_without_confirmation_is_forwarded_to_policy_boundary():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(valid(operation="service_restart", target_kind="service", target_identifier="demo", safety_class="mutating", request_id="deny-1", confirmation=False))
    assert response["success"] is True
    assert executor.calls[0][1]["confirmation"] is False
    assert executor.calls[0][0].safety_class is SafetyClass.MUTATING


def test_dry_run_is_forwarded_and_never_changes_transport_contract():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(valid(operation="service_restart", target_kind="service", target_identifier="demo", safety_class="mutating", request_id="dry-1", dry_run=True))
    assert response["success"]
    assert executor.calls[0][1]["dry_run"] is True


def test_unavailable_runtime_preserves_canonical_error():
    gateway = JsonlGateway(HermesOperationsAdapter(FakeExecutor(success=False)))
    response = gateway.handle_line(valid())
    assert not response["success"]
    assert response["error"]["category"] == ErrorCategory.UNAVAILABLE_DEPENDENCY.value


def test_stream_processes_multiple_lines_without_protocol_contamination():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    inp = io.StringIO("not-json\n" + valid(request_id="ok-1") + "\n" + valid(request_id="ok-2") + "\n")
    out = io.StringIO()
    gateway.serve(inp, out)
    records = [json.loads(item) for item in out.getvalue().splitlines()]
    assert len(records) == 3
    assert all(isinstance(item, dict) for item in records)
    assert records[1]["request_id"] == "ok-1"
    assert records[2]["request_id"] == "ok-2"


def test_gateway_parser_is_available_in_a_clean_process_without_stderr_contamination():
    code = "from yasin_operations.gateway_cli import build_parser; print(build_parser().format_help(), end='')"
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert completed.returncode == 0
    assert "serve typed Operations requests over stdin/stdout JSONL" in completed.stdout
    assert completed.stderr == ""


def test_repository_does_not_advertise_jsonl_as_mcp():
    from pathlib import Path

    root = Path(__file__).parents[1]
    text = (root / "docs" / "TRANSPORT-BOUNDARY.md").read_text(encoding="utf-8").lower()
    assert "no mcp server implementation" in text
