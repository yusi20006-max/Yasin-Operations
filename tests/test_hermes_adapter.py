from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.adapters.hermes.contracts import HermesOperationRequest
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import OperationTarget
from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class FakeTool:
    def __init__(self):
        self._descriptor = ToolDescriptor(
            id="test.tool",
            description="test tool",
            capabilities=(
                ToolCapability("status", SafetyClass.READ_ONLY),
                ToolCapability("restart", SafetyClass.MUTATING),
            ),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation):
        return OperationResult.ok(operation.id, {"operation": operation.name})


def _adapter():
    registry = ToolRegistry()
    registry.register(FakeTool())
    return HermesOperationsAdapter(Executor(registry))


def test_mapping_request_executes_as_typed_operation():
    response = _adapter().handle(
        {
            "request_id": "req-1",
            "operation": "status",
            "target_kind": "service",
            "target_identifier": "demo",
            "safety_class": "read_only",
        }
    )
    assert response.success
    assert response.request_id == "req-1"
    assert response.operation_id
    assert response.data == {"operation": "status"}


def test_mutating_request_is_denied_without_confirmation():
    response = _adapter().handle(
        HermesOperationRequest(
            operation="restart",
            target_kind="service",
            target_identifier="demo",
            safety_class=SafetyClass.MUTATING,
        )
    )
    assert not response.success
    assert response.error["category"] == "permission_denied"


def test_invalid_request_is_structured():
    response = _adapter().handle({"request_id": "bad"})
    assert not response.success
    assert response.status == "invalid_request"
    assert response.error["category"] == "validation_error"


def test_unavailable_operations_is_graceful():
    response = HermesOperationsAdapter(None).handle(
        HermesOperationRequest(
            operation="status",
            target_kind="service",
            target_identifier="demo",
            safety_class=SafetyClass.READ_ONLY,
        )
    )
    assert not response.success
    assert response.status == "unavailable"
    assert response.service_available is False
    assert response.error["category"] == "unavailable_dependency"


def test_health_summary_never_requires_mutation():
    summary = _adapter().health_summary()
    assert summary["available"] is True
    assert summary["health"]["status"] == "failed"
    assert summary["diagnostics"]["status"] == "failed"
