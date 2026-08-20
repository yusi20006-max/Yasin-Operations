"""Gateway protocol hardening tests."""
from __future__ import annotations

import json

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.gateway import JsonlGateway


class FakeResult:
    success = True
    data = {"ok": True}
    error = None
    operation_id = "op-1"


class FakeExecutor:
    def __init__(self):
        self.calls = 0

    def execute(self, operation, **kwargs):
        self.calls += 1
        return FakeResult()


class ExplodingExecutor(FakeExecutor):
    def execute(self, operation, **kwargs):
        self.calls += 1
        raise RuntimeError("secret internal path and credential-like detail")


def request(request_id="req-1", **extra):
    payload = {
        "schema_version": 1,
        "request": {
            "operation": "health_check",
            "target_kind": "self",
            "target_identifier": "runtime",
            "safety_class": "read_only",
            "request_id": request_id,
        },
    }
    payload["request"].update(extra)
    return json.dumps(payload)


def test_oversized_line_is_rejected():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), max_line_bytes=1024)
    response = gateway.handle_line(request(parameters={"blob": "x" * 2000}))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_parameter_limit_is_enforced():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), max_parameter_bytes=256)
    response = gateway.handle_line(request(parameters={"blob": "x" * 1000}))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_control_character_in_identifier_is_rejected():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(request(request_id="bad\nrequest"))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_identifier_length_is_enforced():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), max_identifier_length=32)
    response = gateway.handle_line(request(request_id="x" * 100))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_duplicate_request_id_is_deterministic():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), recent_request_ids=8)
    first = gateway.handle_line(request(request_id="same"))
    second = gateway.handle_line(request(request_id="same"))
    assert first["success"] is True
    assert second["status"] == "invalid_request"
    assert "duplicate" in second["error"]["message"]
    assert executor.calls == 1


def test_duplicate_detection_window_evicts_old_ids():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), recent_request_ids=1)
    assert gateway.handle_line(request(request_id="a"))["success"] is True
    assert gateway.handle_line(request(request_id="b"))["success"] is True
    assert gateway.handle_line(request(request_id="a"))["success"] is True
    assert executor.calls == 3


def test_duplicate_rejection_can_be_disabled():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor), reject_duplicates=False)
    assert gateway.handle_line(request(request_id="same"))["success"] is True
    assert gateway.handle_line(request(request_id="same"))["success"] is True
    assert executor.calls == 2


def test_boolean_fields_reject_string_coercion():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(request(confirmation="false"))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_safety_class_rejects_non_string_values():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(request(safety_class=True))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_parameters_reject_non_object_values():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(request(parameters=["unexpected", "list"]))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_unknown_fields_are_rejected():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    response = gateway.handle_line(request(unexpected="value"))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_envelope_and_request_ids_must_match():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    payload = json.loads(request(request_id="inner"))
    payload["request_id"] = "outer"
    response = gateway.handle_line(json.dumps(payload))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_schema_version_rejects_boolean_coercion():
    executor = FakeExecutor()
    gateway = JsonlGateway(HermesOperationsAdapter(executor))
    payload = json.loads(request())
    payload["schema_version"] = True
    response = gateway.handle_line(json.dumps(payload))
    assert response["status"] == "invalid_request"
    assert executor.calls == 0


def test_internal_executor_errors_are_not_disclosed():
    gateway = JsonlGateway(HermesOperationsAdapter(ExplodingExecutor()))
    response = gateway.handle_line(request())
    assert response["status"] == "failed"
    assert response["error"]["category"] == "internal_error"
    assert response["error"]["message"] == "operation failed due to an internal error"
    assert "secret internal path" not in json.dumps(response)
