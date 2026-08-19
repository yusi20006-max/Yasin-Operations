"""Termux/runit availability and startup diagnostics."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class TermuxDiagnostics:
    is_termux: bool
    runit_available: bool
    service_root: str
    active_services: tuple[str, ...]
    issues: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "is_termux": self.is_termux,
            "runit_available": self.runit_available,
            "service_root": self.service_root,
            "active_services": list(self.active_services),
            "issues": list(self.issues),
        }


def detect_termux(service_root: str = "/data/data/com.termux/files/usr/var/service") -> TermuxDiagnostics:
    prefix = os.environ.get("PREFIX", "")
    is_termux = "/data/data/com.termux" in prefix or Path("/data/data/com.termux/files/usr/bin/termux-info").exists()
    root = Path(service_root)
    sv = Path("/data/data/com.termux/files/usr/bin/sv")
    services: list[str] = []
    issues: list[str] = []
    if root.is_dir():
        services = sorted(p.name for p in root.iterdir() if p.is_dir())
    elif is_termux:
        issues.append("service_root_missing")
    runit = sv.exists() or any(Path(p).exists() for p in ("/usr/bin/sv", "/bin/sv"))
    if is_termux and not runit:
        issues.append("runit_sv_missing")
    return TermuxDiagnostics(is_termux, runit, str(root), tuple(services), tuple(issues))
