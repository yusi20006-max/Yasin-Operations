"""Termux/runit live acceptance helpers (read-only).

Separates environment blockers from product defects and treats missing
optional service directories as SKIP rather than FAIL.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from yasin_operations.runtime.monitoring import (
    OPTIONAL_ECOSYSTEM_SERVICES,
    classify_service,
    is_optional_ecosystem_service,
)
from yasin_operations.runtime.termux.diagnostics import detect_termux
from yasin_operations.runtime.termux.runit import RunitServiceBackend, RunitServiceDefinition
from yasin_operations.runtime.local.process_backend import LocalProcessInspector

DEFAULT_OPTIONAL_SERVICES: tuple[str, ...] = (
    "hermes-agent",
    "yasin-ai",
    "yasinpress",
    "yasinrelay",
)


@dataclass(frozen=True)
class LiveCheckResult:
    """One live acceptance observation."""

    name: str
    status: str  # PASS | FAIL | SKIP | BLOCKED
    category: str  # environment | product | optional | observation
    detail: str = ""
    state: str | None = None
    presence: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class LiveAcceptanceReport:
    """Aggregate live acceptance report."""

    results: list[LiveCheckResult] = field(default_factory=list)
    service_root: str = ""
    is_termux: bool = False
    environment_blocked: bool = False

    def summary(self) -> dict[str, int]:
        counts = {"pass": 0, "fail": 0, "skip": 0, "blocked": 0}
        for item in self.results:
            key = item.status.lower()
            if key in counts:
                counts[key] += 1
        return counts

    @property
    def success(self) -> bool:
        # Environment blockers and product failures both prevent success.
        return not any(item.status in {"FAIL", "BLOCKED"} for item in self.results)

    def as_dict(self) -> dict[str, object]:
        return {
            "live": True,
            "success": self.success,
            "environment_blocked": self.environment_blocked,
            "is_termux": self.is_termux,
            "service_root": self.service_root,
            "summary": self.summary(),
            "results": [item.as_dict() for item in self.results],
        }


def _runit_prefix_state(output: str) -> str:
    text = (output or "").strip()
    if text.startswith("run:"):
        return "running"
    if text.startswith("down:"):
        return "stopped"
    if text.startswith("fail:") or text.startswith("timeout:"):
        return "failed"
    return "unknown"


class _EmptyInspector:
    def find_by_name(self, pattern: str):
        return []

    def is_alive(self, pid: int) -> bool:
        return False


def evaluate_live_services(
    services: Sequence[str] = DEFAULT_OPTIONAL_SERVICES,
    *,
    service_root: str | None = None,
    sv_path: str | None = None,
    environ: Mapping[str, str] | None = None,
    termux_marker: str | None = None,
    run_sv: bool = True,
) -> LiveAcceptanceReport:
    """Read-only live acceptance against a Termux/runit service root.

    Parameters are injectable so hosted CI can simulate Termux layouts without
    requiring a real device.
    """
    env = dict(os.environ if environ is None else environ)
    root = Path(
        service_root
        or env.get("YASIN_OPERATIONS_SERVICE_ROOT", "/data/data/com.termux/files/usr/var/service")
    ).expanduser()
    resolved_sv = (
        sv_path
        or env.get("YASIN_OPERATIONS_SV_PATH")
        or env.get("YASIN_OPERATIONS_SV")
        or shutil.which("sv")
        or "/data/data/com.termux/files/usr/bin/sv"
    )

    marker_kwargs = {}
    if termux_marker is not None:
        marker_kwargs["termux_marker"] = termux_marker

    diagnostics = detect_termux(
        str(root),
        sv_path=str(resolved_sv),
        expected_services=tuple(services),
        environ=env,
        **marker_kwargs,
    )

    report = LiveAcceptanceReport(
        service_root=str(root),
        is_termux=diagnostics.is_termux,
    )
    names = tuple(sorted({name.strip() for name in services if name.strip()}))

    # Environment gate: outside Termux without an explicit configured root for tests.
    if not diagnostics.is_termux and not root.is_dir():
        report.environment_blocked = True
        report.results.append(
            LiveCheckResult(
                name="environment:termux",
                status="SKIP",
                category="environment",
                detail="not a Termux host; live checks skipped (use a Termux device or provide a service root fixture)",
            )
        )
        return report

    if not diagnostics.service_root_exists:
        report.environment_blocked = True
        report.results.append(
            LiveCheckResult(
                name="environment:service_root",
                status="BLOCKED",
                category="environment",
                detail=f"service root missing: {root}",
            )
        )
        return report

    if not diagnostics.service_root_readable:
        report.environment_blocked = True
        report.results.append(
            LiveCheckResult(
                name="environment:service_root",
                status="BLOCKED",
                category="environment",
                detail=f"service root unreadable: {root}",
            )
        )
        return report

    if not diagnostics.sv_exists or not diagnostics.sv_executable:
        report.environment_blocked = True
        report.results.append(
            LiveCheckResult(
                name="environment:sv",
                status="BLOCKED",
                category="environment",
                detail=f"sv unavailable or not executable: {resolved_sv}",
            )
        )
        # Still enumerate missing dirs for operator diagnostics without calling sv.
        for name in names:
            service_dir = root / name
            if not service_dir.is_dir():
                report.results.append(
                    LiveCheckResult(
                        name=f"service:{name}",
                        status="SKIP",
                        category="optional",
                        detail=f"optional service directory absent: {service_dir}",
                        presence="missing",
                    )
                )
        return report

    report.results.append(
        LiveCheckResult(
            name="environment:runit",
            status="PASS",
            category="environment",
            detail=f"service_root={root}; sv={resolved_sv}",
        )
    )

    # Service-directory drift: directories present under root but not in the requested set.
    active = set(diagnostics.active_services)
    requested = set(names)
    drift = sorted(active - requested)
    if drift:
        report.results.append(
            LiveCheckResult(
                name="observation:service_directory_drift",
                status="PASS",
                category="observation",
                detail=f"extra service directories not in live set: {', '.join(drift)}",
            )
        )

    # Authoritative per-service observation via backend (isolation preserved).
    definitions = [
        RunitServiceDefinition(name=name, process_pattern=name, service_dir=str(root / name))
        for name in names
    ]
    backend = RunitServiceBackend(
        LocalProcessInspector() if run_sv else _EmptyInspector(),
        service_root=str(root),
        definitions=definitions,
        sv_path=str(resolved_sv),
        timeout=5.0,
        startup_grace=0.0,
        poll_interval=0.05,
    )

    # One bad service must not prevent observing the rest.
    for name in names:
        service_dir = root / name
        if not service_dir.is_dir():
            report.results.append(
                LiveCheckResult(
                    name=f"service:{name}",
                    status="SKIP",
                    category="optional" if is_optional_ecosystem_service(name) or name in OPTIONAL_ECOSYSTEM_SERVICES else "optional",
                    detail=f"optional service directory absent: {service_dir}",
                    presence="missing",
                    state="unknown",
                )
            )
            continue

        try:
            info = backend.get_status(name)
        except Exception as exc:  # pragma: no cover - isolation fallback
            report.results.append(
                LiveCheckResult(
                    name=f"service:{name}",
                    status="FAIL",
                    category="product",
                    detail=f"observation error: {exc}",
                    presence="present",
                )
            )
            continue

        presence = str((info.extra or {}).get("presence") or "present")
        raw = {
            "name": info.name,
            "state": info.state.value,
            "health_state": info.health_state,
            "extra": dict(info.extra or {}),
        }
        classification = classify_service(raw)

        if classification == "missing":
            status, category = "SKIP", "optional"
            detail = info.message or f"missing service directory: {service_dir}"
        elif classification == "unavailable":
            status, category = "BLOCKED", "environment"
            detail = info.message or "runit backend unavailable for service"
            report.environment_blocked = True
        elif classification == "healthy":
            status, category = "PASS", "product"
            detail = info.message or f"state={info.state.value}"
        elif classification in {"degraded", "failed", "unknown", "other"}:
            # Present service not healthy is a product/runtime finding for live acceptance.
            status, category = "FAIL", "product"
            detail = info.message or f"state={info.state.value}; health_state={info.health_state}"
        else:
            status, category = "FAIL", "product"
            detail = f"unclassified state={info.state.value}"

        report.results.append(
            LiveCheckResult(
                name=f"service:{name}",
                status=status,
                category=category,
                detail=detail[:300],
                state=info.state.value,
                presence=presence,
            )
        )

    return report
