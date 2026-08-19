import pytest

from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import (
    DuplicateToolError,
    ToolNotFoundError,
    ToolRegistry,
)


class FakeTool:
    """Minimal Tool implementation for registry/execution tests."""

    def __init__(self, tool_id: str, operation_names: tuple[str, ...], safety_class=SafetyClass.READ_ONLY):
        self._descriptor = ToolDescriptor(
            id=tool_id,
            description=f"fake tool {tool_id}",
            capabilities=tuple(
                ToolCapability(operation_name=name, safety_class=safety_class)
                for name in operation_names
            ),
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        return OperationResult.ok(operation.id, data={"handled_by": self._descriptor.id})


def test_register_and_get():
    registry = ToolRegistry()
    tool = FakeTool("tool-a", ("check_health",))
    registry.register(tool)
    assert registry.get("tool-a") is tool


def test_register_duplicate_raises():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    with pytest.raises(DuplicateToolError):
        registry.register(FakeTool("tool-a", ("other_op",)))


def test_get_missing_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get("does-not-exist")


def test_has_returns_true_for_registered():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    assert registry.has("tool-a") is True
    assert registry.has("tool-b") is False


def test_unregister_removes_tool():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    registry.unregister("tool-a")
    assert registry.has("tool-a") is False


def test_unregister_missing_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.unregister("does-not-exist")


def test_list_tools_returns_descriptors():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    registry.register(FakeTool("tool-b", ("restart",)))
    descriptors = registry.list_tools()
    ids = {d.id for d in descriptors}
    assert ids == {"tool-a", "tool-b"}


def test_list_tools_empty_registry():
    registry = ToolRegistry()
    assert registry.list_tools() == ()


def test_find_for_operation_returns_matching_tools():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    registry.register(FakeTool("tool-b", ("restart",)))
    matches = registry.find_for_operation("check_health")
    assert len(matches) == 1
    assert matches[0].descriptor.id == "tool-a"


def test_find_for_operation_no_match_returns_empty():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    assert registry.find_for_operation("unsupported_op") == ()


def test_find_for_operation_multiple_matches():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    registry.register(FakeTool("tool-b", ("check_health",)))
    matches = registry.find_for_operation("check_health")
    assert len(matches) == 2


def test_supports_true_and_false():
    registry = ToolRegistry()
    registry.register(FakeTool("tool-a", ("check_health",)))
    assert registry.supports("check_health") is True
    assert registry.supports("unsupported_op") is False


def test_descriptor_supports_and_capability_for():
    descriptor = ToolDescriptor(
        id="tool-a",
        description="d",
        capabilities=(
            ToolCapability("check_health", SafetyClass.READ_ONLY),
        ),
    )
    assert descriptor.supports("check_health") is True
    assert descriptor.supports("other") is False
    cap = descriptor.capability_for("check_health")
    assert cap is not None
    assert cap.safety_class == SafetyClass.READ_ONLY
    assert descriptor.capability_for("other") is None


def test_descriptor_rejects_empty_id():
    with pytest.raises(ValueError):
        ToolDescriptor(id="", description="d")


def test_descriptor_rejects_empty_description():
    with pytest.raises(ValueError):
        ToolDescriptor(id="x", description="")
