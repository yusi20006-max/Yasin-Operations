"""Non-invasive Termux/runit availability and startup diagnostics."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


DEFAULT_TERMUX_MARKER = "/data/data/com.termux/files/usr/bin/termux-info"
DEFAULT_SV_PATH = "/data/data/com.termux/files/usr/bin/sv"


@dataclass(frozen=True)
class TermuxDiagnostics:
    """Stable, read-only diagnostic snapshot for the Termux runtime."""

    is_termux: bool
    runit_available: bool
    service_root: str
    service_root_exists: bool
    service_root_readable: bool
    sv_path: str
    sv_exists: bool
    sv_executable: bool
    active_services: tuple[str, ...]
    configured_services: tuple[str, ...]
    missing_services: tuple[str, ...]
    issues: tuple[str, ...]

    @property
    def status(self) -> str:
        if not self.is_termux:
            return "unsupported"
        return "healthy" if not self.issues else "degraded"

    def as_dict(self) -> dict[str, object]:
        """Return the public JSON/human-readable diagnostic contract."""
        return {
            "is_termux": self.is_termux,
            "status": self.status,
            "runit_available": self.runit_available,
            "service_root": self.service_root,
            "service_root_exists": self.service_root_exists,
            "service_root_readable": self.service_root_readable,
            "sv_path": self.sv_path,
            "sv_exists": self.sv_exists,
            "sv_executable": self.sv_executable,
            "active_services": list(self.active_services),
            "configured_services": list(self.configured_services),
            "missing_services": list(self.missing_services),
            "issues": list(self.issues),
        }


def detect_termux(
    service_root: str = "/data/data/com.termux/files/usr/var/service",
    *,
    sv_path: str = DEFAULT_SV_PATH,
    expected_services: Sequence[str] = (),
    environ: Mapping[str, str] | None = None,
    termux_marker: str = DEFAULT_TERMUX_MARKER,
) -> TermuxDiagnostics:
    """Inspect Termux/runit state without invoking ``sv`` or changing services.

    Outside Termux the result is explicitly ``unsupported`` and does not report
    missing Termux files as failures. Inside Termux, failures are deterministic
    issue codes suitable for both CLI output and automation.
    """
    env = os.environ if environ is None else environ
    prefix = env.get("PREFIX", "")
    is_termux = "/data/data/com.termux" in prefix or Path(termux_marker).exists()

    root = Path(service_root)
    sv = Path(sv_path)
    root_exists = root.is_dir()
    root_readable = root_exists and os.access(root, os.R_OK | os.X_OK)
    sv_exists = sv.is_file()
    sv_executable = sv_exists and os.access(sv, os.X_OK)

    services: list[str] = []
    issues: list[str] = []
    configured = tuple(sorted({name.strip() for name in expected_services if name.strip()}))

    if is_termux:
        if not root_exists:
            issues.append("service_root_missing")
        elif not root_readable:
            issues.append("service_root_unreadable")
        else:
            services = sorted(p.name for p in root.iterdir() if p.is_dir())

        if not sv_exists:
            issues.append("runit_sv_missing")
        elif not sv_executable:
            issues.append("runit_sv_not_executable")

        missing = tuple(name for name in configured if name not in services)
        issues.extend(f"service_missing:{name}" for name in missing)
    else:
        missing = ()

    return TermuxDiagnostics(
        is_termux=is_termux,
        runit_available=sv_exists and sv_executable,
        service_root=str(root),
        service_root_exists=root_exists,
        service_root_readable=root_readable,
        sv_path=str(sv),
        sv_exists=sv_exists,
        sv_executable=sv_executable,
        active_services=tuple(services),
        configured_services=configured,
        missing_services=missing,
        issues=tuple(issues),
    )
