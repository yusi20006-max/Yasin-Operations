from yasin_operations.adapters.ecosystem import (
    ServiceSnapshot,
    YasinAIAdapter,
    YasinPressAdapter,
    YasinRelayAdapter,
)
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class FakeProbe:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def inspect(self, service_name):
        return self.snapshot


class AdapterTool:
    def __init__(self):
        names = (
            "yasin_ai_status", "yasin_ai_health", "yasin_ai_version", "yasin_ai_capabilities",
            "yasin_press_status", "yasin_press_health", "yasin_press_version", "yasin_press_capabilities",
            "yasin_relay_status", "yasin_relay_health", "yasin_relay_version", "yasin_relay_capabilities",
        )
        self._descriptor = ToolDescriptor(
            id="test.ecosystem",
            description="test ecosystem operations",
            capabilities=tuple(ToolCapability(name, SafetyClass.READ_ONLY) for name in names),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation):
        return OperationResult.ok(operation.id, {"operation": operation.name})


def _executor():
    registry = ToolRegistry()
    registry.register(AdapterTool())
    return Executor(registry)


def test_each_adapter_inspects_its_own_service():
    for adapter_cls, name in (
        (YasinAIAdapter, "Yasin-AI"),
        (YasinPressAdapter, "YasinPress"),
        (YasinRelayAdapter, "YasinRelay"),
    ):
        adapter = adapter_cls(
            FakeProbe(ServiceSnapshot(service=name, available=True, state="running", version="1.2.3", capabilities=("health",)))
        )
        result = adapter.inspect_result()
        assert result.success
        assert result.data["service"] == name
        assert result.data["available"] is True


def test_each_adapter_maps_typed_operations():
    for adapter_cls, operation in (
        (YasinAIAdapter, "yasin_ai_health"),
        (YasinPressAdapter, "yasin_press_health"),
        (YasinRelayAdapter, "yasin_relay_health"),
    ):
        adapter = adapter_cls(FakeProbe(ServiceSnapshot(service=adapter_cls.service_name, available=True)), _executor())
        result = adapter.execute(operation)
        assert result.success
        assert result.data["operation"] == operation


def test_unsupported_capability_is_explicit():
    adapter = YasinAIAdapter(FakeProbe(ServiceSnapshot(service="Yasin-AI", available=True)))
    try:
        adapter.build_operation("shell")
        assert False
    except ValueError as exc:
        assert "unsupported capability" in str(exc)


def test_unavailable_target_is_structured():
    adapter = YasinRelayAdapter(
        FakeProbe(ServiceSnapshot(service="YasinRelay", available=False, state="unavailable", error="connection refused"))
    )
    result = adapter.inspect_result()
    assert not result.success
    assert result.error["category"] == "unavailable_dependency"
    assert result.data["error"] == "connection refused"


def test_missing_operations_executor_is_graceful():
    adapter = YasinPressAdapter(FakeProbe(ServiceSnapshot(service="YasinPress", available=True)))
    result = adapter.execute("yasin_press_status")
    assert not result.success
    assert result.error["category"] == "unavailable_dependency"
