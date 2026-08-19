"""Independence test.

Confirms every public module imports cleanly and the core contracts
can be used end-to-end (construct an operation, register a tool,
execute it) with no dependency on Hermes, Yasin-AI, YasinPress,
YasinRelay, Termux services, or any external API. This test file
itself only imports from yasin_operations and the standard library.
"""

from yasin_operations.config.config import OperationsConfig, load_config
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import (
    Operation,
    OperationState,
    OperationStatus,
    OperationTarget,
)
from yasin_operations.core.results.models import OperationResult
from yasin_operations.logging.audit import AuditRecord, InMemoryAuditRecorder
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class _EchoTool:
    def __init__(self):
        self._descriptor = ToolDescriptor(
            id="echo",
            description="returns its input parameters as output",
            capabilities=(ToolCapability("echo", SafetyClass.READ_ONLY),),
        )

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, operation: Operation) -> OperationResult:
        return OperationResult.ok(operation.id, data=dict(operation.parameters))


def test_full_independent_flow():
    """Construct config, registry, executor, an operation, and an
    audit trail entirely from this package's own contracts."""
    config = load_config()
    assert isinstance(config, OperationsConfig)

    registry = ToolRegistry()
    registry.register(_EchoTool())

    executor = Executor(registry)
    recorder = InMemoryAuditRecorder()

    operation = Operation(
        name="echo",
        target=OperationTarget(kind="tool", identifier="echo"),
        safety_class=SafetyClass.READ_ONLY,
        parameters={"message": "hello"},
    )

    state = OperationState(operation_id=operation.id)
    state = state.transition_to(OperationStatus.RUNNING)

    result = executor.execute(operation)

    state = state.transition_to(
        OperationStatus.SUCCEEDED if result.success else OperationStatus.FAILED
    )

    recorder.record(
        AuditRecord(
            operation_id=operation.id,
            operation_name=operation.name,
            target=operation.target,
            status=state.status,
        )
    )

    assert result.success is True
    assert result.data == {"message": "hello"}
    assert state.status == OperationStatus.SUCCEEDED
    assert len(recorder.entries) == 1


def test_no_import_of_external_yasin_packages():
    """Static guard: scans this package's own source for accidental
    *import statements* referencing other Yasin repositories or
    Hermes, so a future contributor cannot silently introduce
    coupling that violates the independence requirement.

    Only actual `import`/`from ... import` lines are checked, not
    arbitrary text -- several modules correctly mention "Hermes" or
    other ecosystem project names in docstrings/comments to explain
    that no dependency on them exists, and that is not a violation.
    """
    import ast
    import pathlib

    package_root = pathlib.Path(__file__).parent.parent / "yasin_operations"
    forbidden_substrings = (
        "yasin_ai",
        "yasinai",
        "yasinpress",
        "yasinrelay",
        "hermes",
    )

    offending = []
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module_names = []
            if isinstance(node, ast.Import):
                module_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_names = [node.module]

            for name in module_names:
                lowered = name.lower()
                for term in forbidden_substrings:
                    if term in lowered:
                        offending.append((str(path), name))

    assert offending == [], f"Found forbidden import references: {offending}"
