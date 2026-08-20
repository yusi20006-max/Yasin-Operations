"""Production acceptance checks for the public Yasin-Operations boundary."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from yasin_operations.adapters.ecosystem import ServiceProbe, ServiceSnapshot, YasinAIAdapter, YasinPressAdapter, YasinRelayAdapter
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


class AcceptanceTool:
    def __init__(self) -> None:
        self._descriptor = ToolDescriptor(
            id="acceptance.tool",
            description="deterministic acceptance fake",
            capabilities=(
                ToolCapability("status", SafetyClass.READ_ONLY),
                ToolCapability("restart", SafetyClass.MUTATING),
            ),
        )

    @property
    def descriptor(self) -> ToolDescriptor:
        return self._descriptor

    def execute(self, operation: Any) -> OperationResult:
        return OperationResult.ok(operation.id, {"operation": operation.name})


class FakeProbe(ServiceProbe):
    def inspect(self, service_name: str) -> ServiceSnapshot:
        return ServiceSnapshot(
            service=service_name,
            available=True,
            state="running",
            version="test",
            capabilities=("capabilities", "health", "status", "version"),
        )


def _run_json(command: list[str]) -> tuple[bool, dict[str, Any], str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    output = completed.stdout.strip()
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        return False, {}, f"invalid JSON: {exc}; stderr={completed.stderr.strip()!r}"
    return completed.returncode == 0 and payload.get("success") is True, payload, completed.stderr.strip()


def check_ecosystem_adapters():
    results = []
    for adapter_cls in (YasinAIAdapter, YasinPressAdapter, YasinRelayAdapter):
        adapter = adapter_cls(FakeProbe())
        results.append(_check_adapter(adapter))
    return results


def _check_adapter(adapter):
    class Result:
        def __init__(self, status: str, detail: str = ""):
            self.status = status
            self.detail = detail

    try:
        snapshot = adapter.inspect_result()
        if not snapshot.success:
            return Result("FAIL", snapshot.error)
        expected = tuple(sorted(adapter.supported_operations))
        actual = tuple(sorted(name for name in adapter.supported_operations))
        if expected != actual:
            return Result("FAIL", "non-deterministic capability namespace")
        return Result("PASS")
    except Exception as exc:  # noqa: BLE001
        return Result("FAIL", str(exc))


def main() -> int:
    payload = {"success": all(item.status == "PASS" for item in check_ecosystem_adapters())}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
