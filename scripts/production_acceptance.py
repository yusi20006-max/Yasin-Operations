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


def _service_root() -> Path:
    """Resolve the configured Termux/runit service root (test/operator helper)."""
    return Path(os.environ.get("YASIN_OPERATIONS_SERVICE_ROOT", DEFAULT_TERMUX_SERVICE_ROOT)).expanduser()


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


def _run_cli_command(command_name: str) -> tuple[bool, dict[str, Any], str]:
    command = [sys.executable, "-m", "yasin_operations", "--json", command_name]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    output = completed.stdout.strip()
    stderr = completed.stderr.strip()
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        return False, {}, f"invalid JSON: {exc}; stderr={stderr!r}"

    if not isinstance(payload, dict):
        return False, {}, f"payload is not a JSON object; stderr={stderr!r}"

    if payload.get("command") != command_name or payload.get("schema_version") != 1:
        return False, payload, f"malformed envelope for {command_name}; stderr={stderr!r}"

    if command_name == "doctor":
        if completed.returncode not in (0, 1):
            return False, payload, f"unexpected exit code {completed.returncode}; stderr={stderr!r}"
        if not isinstance(payload.get("success"), bool):
            return False, payload, f"malformed doctor success field; stderr={stderr!r}"
        if not isinstance(payload.get("termux"), dict) or not isinstance(payload.get("configuration"), dict):
            return False, payload, f"malformed doctor payload structure; stderr={stderr!r}"
        if payload["success"] is False:
            err = payload.get("error")
            if not isinstance(err, dict) or err.get("category") != "diagnostics":
                return False, payload, f"doctor failed with non-diagnostic error: {err}; stderr={stderr!r}"
        return True, payload, stderr

    if completed.returncode not in (0, 1, 2):
        return False, payload, f"unexpected exit code {completed.returncode}; stderr={stderr!r}"

    if payload.get("success") is not True:
        return False, payload, f"command {command_name} payload success is not True; stderr={stderr!r}"

    if command_name == "status":
        data = payload.get("data")
        if not isinstance(data, dict) or "services" not in data or "summary" not in data:
            return False, payload, f"malformed status payload structure; stderr={stderr!r}"

    if command_name == "health":
        if not isinstance(payload.get("health"), dict) or not isinstance(payload.get("services"), dict):
            return False, payload, f"malformed health payload structure; stderr={stderr!r}"

    return True, payload, stderr


def check_cli() -> list[Result]:
    results: list[Result] = []
    commands = (("doctor-json", "doctor"), ("status-json", "status"), ("health-json", "health"))
    for name, command in commands:
        ok, payload, detail = _run_cli_command(command)
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


def check_live_services(services: tuple[str, ...]) -> list[Result]:
    """Read-only live Termux/runit checks with environment vs product separation."""
    from yasin_operations.runtime.termux.live_acceptance import evaluate_live_services

    report = evaluate_live_services(services)
    results: list[Result] = []
    for item in report.results:
        detail = item.detail
        if item.category:
            detail = f"[{item.category}] {detail}" if detail else f"[{item.category}]"
        if item.state:
            detail = f"{detail}; state={item.state}" if detail else f"state={item.state}"
        results.append(Result(item.name, item.status, detail))
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
    failed = [item for item in results if item.status in {"FAIL", "BLOCKED"}]
    payload = {
        "success": not failed,
        "summary": {
            "pass": sum(item.status == "PASS" for item in results),
            "fail": sum(item.status == "FAIL" for item in results),
            "skip": sum(item.status == "SKIP" for item in results),
            "blocked": sum(item.status == "BLOCKED" for item in results),
        },
        "results": [item.__dict__ for item in results],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in results:
            suffix = f": {item.detail}" if item.detail else ""
            print(f"[{item.status}] {item.name}{suffix}")
        s = payload["summary"]
        print(
            f"SUMMARY pass={s['pass']} fail={s['fail']} skip={s['skip']} blocked={s['blocked']}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
