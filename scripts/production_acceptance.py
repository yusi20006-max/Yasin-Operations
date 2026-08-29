#!/usr/bin/env python3
"""Read-only production acceptance harness for Yasin-Operations."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yasin_operations.adapters.ecosystem.contracts import ServiceProbe, ServiceSnapshot
from yasin_operations.adapters.ecosystem.yasin_ai import YasinAIAdapter
from yasin_operations.adapters.ecosystem.yasin_press import YasinPressAdapter
from yasin_operations.adapters.ecosystem.yasin_relay import YasinRelayAdapter
from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.adapters.hermes.contracts import HermesOperationRequest
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.tools.contracts.tool import ToolCapability, ToolDescriptor
from yasin_operations.tools.registry.registry import ToolRegistry


SERVICES = ("hermes-agent", "yasin-ai", "yasinpress", "yasinrelay")
DEFAULT_TERMUX_SERVICE_ROOT = "/data/data/com.termux/files/usr/var/service"


@dataclass
class Result:
    name: str
    status: str
    detail: str = ""


class FakeTool:
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


def check_cli() -> list[Result]:
    results: list[Result] = []
    commands = (("doctor-json", "doctor"), ("status-json", "status"), ("health-json", "health"))
    for name, command in commands:
        ok, payload, detail = _run_json([sys.executable, "-m", "yasin_operations", "--json", command])
        if not ok:
            results.append(Result(name, "FAIL", detail or str(payload)))
        else:
            results.append(Result(name, "PASS"))
    return results


def check_hermes() -> list[Result]:
    registry = ToolRegistry()
    registry.register(FakeTool())
    adapter = HermesOperationsAdapter(Executor(registry))
    results: list[Result] = []
    health = HermesOperationRequest(operation="status", target_kind="service", target_identifier="acceptance", safety_class=SafetyClass.READ_ONLY, request_id="acceptance-health-001")
    response = adapter.handle(health)
    results.append(Result("hermes-read-only-request", "PASS" if response.success else "FAIL", str(response.error or "")))
    mutation = HermesOperationRequest(operation="restart", target_kind="service", target_identifier="acceptance", safety_class=SafetyClass.MUTATING, request_id="acceptance-mutation-001")
    denied = adapter.handle(mutation)
    results.append(Result("hermes-mutation-denied-without-confirmation", "PASS" if not denied.success and denied.error and denied.error.get("category") == "permission_denied" else "FAIL", str(denied.error or "")))
    unavailable = HermesOperationsAdapter(None).handle(health)
    results.append(Result("hermes-unavailable-runtime", "PASS" if unavailable.status == "unavailable" and not unavailable.service_available else "FAIL", str(unavailable.error or "")))
    return results


def check_ecosystem_adapters() -> list[Result]:
    probe = FakeProbe()
    results: list[Result] = []
    for adapter_cls in (YasinAIAdapter, YasinPressAdapter, YasinRelayAdapter):
        adapter = adapter_cls(probe)
        result = adapter.inspect_result()
        results.append(Result(f"{adapter_cls.service_name}-probe", "PASS" if result.success and result.data.get("available") is True else "FAIL", str(result.error or "")))
    return results


def _runit_state(output: str) -> str:
    text = output.strip()
    if text.startswith("run:"): return "running"
    if text.startswith("down:"): return "stopped"
    if text.startswith("fail:") or text.startswith("timeout:"): return "failed"
    return "unknown"


def _service_root() -> Path:
    return Path(os.environ.get("YASIN_OPERATIONS_SERVICE_ROOT", DEFAULT_TERMUX_SERVICE_ROOT)).expanduser()


def check_live_services(services: tuple[str, ...]) -> list[Result]:
    """Check only installed services; absent optional services are not failures."""
    root = _service_root()
    sv = shutil.which("sv") or os.environ.get("YASIN_OPERATIONS_SV")
    if not sv:
        return [Result("live-runit-services", "SKIP", "sv executable not found")]
    results: list[Result] = []
    for service in services:
        service_dir = root / service
        if not service_dir.is_dir():
            results.append(Result(f"service:{service}", "SKIP", f"optional service not installed: {service_dir}"))
            continue
        completed = subprocess.run([sv, "status", str(service_dir)], text=True, capture_output=True, check=False)
        output = (completed.stdout or completed.stderr).strip()
        state = _runit_state(output)
        results.append(Result(f"service:{service}", "PASS" if state == "running" else "FAIL", f"state={state}; {output}"))
    return results


def repository_search() -> list[Result]:
    rg = shutil.which("rg")
    if rg is None: return [Result("repository-search", "SKIP", "rg executable not found")]
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run([rg, "-n", "hermes|mcp|endpoint|transport", str(root / "yasin_operations"), "--glob", "*.py"], text=True, capture_output=True, check=False)
    return [Result("repository-search", "PASS" if completed.returncode in (0, 1) else "FAIL", "portable rg invocation")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="include read-only live runit checks")
    parser.add_argument("--services", default=",".join(SERVICES), help="comma-separated live service names")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args()
    results = check_cli() + check_hermes() + check_ecosystem_adapters() + repository_search()
    if args.live:
        services = tuple(item.strip() for item in args.services.split(",") if item.strip())
        results.extend(check_live_services(services))
    else:
        results.append(Result("live-runit-services", "SKIP", "use --live for read-only host verification"))
    failed = [item for item in results if item.status == "FAIL"]
    payload = {"success": not failed, "summary": {"pass": sum(item.status == "PASS" for item in results), "fail": sum(item.status == "FAIL" for item in results), "skip": sum(item.status == "SKIP" for item in results)}, "results": [item.__dict__ for item in results]}
    if args.json: print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in results:
            suffix = f": {item.detail}" if item.detail else ""
            print(f"[{item.status}] {item.name}{suffix}")
        print(f"SUMMARY pass={payload['summary']['pass']} fail={payload['summary']['fail']} skip={payload['summary']['skip']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
