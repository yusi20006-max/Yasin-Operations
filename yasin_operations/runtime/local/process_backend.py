"""Local process inspector for Termux/Linux.

Prefers reading /proc (no subprocess). Falls back to a fixed-argv
`ps` invocation when /proc is unavailable. Never accepts user
command strings.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional

from yasin_operations.runtime.process import (
    InvalidPIDError,
    ProcessInfo,
    ProcessInspector,
    ProcessNotFoundError,
)

_PROC = Path("/proc")
_STATUS_MAP = {
    "R": "running",
    "S": "sleeping",
    "D": "disk_sleep",
    "Z": "zombie",
    "T": "stopped",
    "t": "tracing_stop",
    "X": "dead",
    "x": "dead",
    "K": "wakekill",
    "W": "waking",
    "P": "parked",
    "I": "idle",
}


def _validate_pid(pid: object) -> int:
    if isinstance(pid, bool) or not isinstance(pid, int):
        try:
            pid = int(pid)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise InvalidPIDError(pid) from None
    if pid <= 0:
        raise InvalidPIDError(pid)
    return pid


class LocalProcessInspector:
    """ProcessInspector implementation for local Linux/Termux."""

    def list_processes(self) -> list[ProcessInfo]:
        if _PROC.is_dir():
            return self._list_from_proc()
        return self._list_from_ps()

    def get_process(self, pid: int) -> ProcessInfo:
        pid = _validate_pid(pid)
        if _PROC.is_dir():
            info = self._read_proc(pid)
            if info is None:
                raise ProcessNotFoundError(str(pid))
            return info
        for p in self._list_from_ps():
            if p.pid == pid:
                return p
        raise ProcessNotFoundError(str(pid))

    def find_by_name(self, pattern: str) -> list[ProcessInfo]:
        if not pattern:
            return []
        needle = pattern.lower()
        results: list[ProcessInfo] = []
        for p in self.list_processes():
            hay = f"{p.name} {p.cmdline or ''}".lower()
            if needle in hay:
                results.append(p)
        return results

    def is_alive(self, pid: int) -> bool:
        try:
            info = self.get_process(pid)
            return info.is_alive()
        except (ProcessNotFoundError, InvalidPIDError):
            return False

    def _list_from_proc(self) -> list[ProcessInfo]:
        results: list[ProcessInfo] = []
        try:
            entries = list(_PROC.iterdir())
        except OSError:
            return self._list_from_ps()
        for entry in entries:
            if not entry.name.isdigit():
                continue
            info = self._read_proc(int(entry.name))
            if info is not None:
                results.append(info)
        return results

    def _read_proc(self, pid: int) -> Optional[ProcessInfo]:
        base = _PROC / str(pid)
        if not base.is_dir():
            return None
        try:
            status_text = (base / "status").read_text(encoding="utf-8", errors="replace")
            name = "unknown"
            ppid: Optional[int] = None
            state_code = "?"
            rss_pages: Optional[int] = None
            uid: Optional[int] = None
            for line in status_text.splitlines():
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("State:"):
                    state_code = line.split(":", 1)[1].strip()[:1]
                elif line.startswith("PPid:"):
                    try:
                        ppid = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("VmRSS:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            rss_pages = int(parts[1]) * 1024
                        except ValueError:
                            pass
                elif line.startswith("Uid:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            uid = int(parts[1])
                        except ValueError:
                            pass

            cmdline = ""
            try:
                raw = (base / "cmdline").read_bytes()
                cmdline = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
            except OSError:
                pass

            username: Optional[str] = None
            if uid is not None:
                try:
                    import pwd

                    username = pwd.getpwuid(uid).pw_name
                except Exception:
                    username = str(uid)

            create_time: Optional[float] = None
            status = _STATUS_MAP.get(state_code, state_code or "unknown")
            return ProcessInfo(
                pid=pid,
                name=name,
                status=status,
                ppid=ppid,
                username=username,
                cmdline=cmdline or None,
                memory_rss_bytes=rss_pages,
                create_time=create_time,
            )
        except (OSError, PermissionError, FileNotFoundError):
            return None

    def _list_from_ps(self) -> list[ProcessInfo]:
        """Fixed-argv ps only — no shell, no user input in the command."""
        argv = [
            "ps",
            "-eo",
            "pid=,ppid=,user=,comm=,args=,stat=",
        ]
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return []
        if completed.returncode != 0:
            return []
        results: list[ProcessInfo] = []
        for line in completed.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 4)
            if len(parts) < 4:
                continue
            try:
                pid = int(parts[0])
                ppid = int(parts[1])
            except ValueError:
                continue
            user = parts[2]
            if len(parts) == 4:
                comm = parts[3]
                args = ""
                stat = "?"
            else:
                rest = parts[4]
                tokens = rest.rsplit(None, 1)
                if len(tokens) == 2 and len(tokens[1]) <= 8:
                    args, stat = tokens
                else:
                    args = rest
                    stat = "?"
                comm = args.split(None, 1)[0] if args else "?"
            status = _STATUS_MAP.get(stat[:1], stat or "unknown")
            results.append(
                ProcessInfo(
                    pid=pid,
                    name=comm,
                    status=status,
                    ppid=ppid,
                    username=user,
                    cmdline=args or None,
                )
            )
        return results
