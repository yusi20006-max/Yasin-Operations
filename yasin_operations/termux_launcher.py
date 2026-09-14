"""Unified named launchers for the Termux/Android runtime.

The launcher deliberately keeps lifecycle policy in a small registry.  It does
not infer ownership from a port alone and never terminates a foreign process.
Hub-managed services must delegate to their authoritative lifecycle command.
"""
from __future__ import annotations

import json
import os
import shlex
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

DEFAULT_REGISTRY = Path(__file__).with_name("termux-launchers.json")


class LauncherError(RuntimeError):
    """A safe launcher refusal or startup failure."""


@dataclass(frozen=True)
class LauncherSpec:
    name: str
    command: tuple[str, ...]
    root: str | None = None
    port: int | None = None
    identity: str | None = None
    start: tuple[str, ...] | None = None
    stop: tuple[str, ...] | None = None
    lifecycle: str = "direct"


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, LauncherSpec]:
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, LauncherSpec] = {}
    for raw in data.get("launchers", []):
        spec = LauncherSpec(
            name=raw["name"],
            command=tuple(raw["command"]),
            root=raw.get("root"),
            port=raw.get("port"),
            identity=raw.get("identity"),
            start=tuple(raw["start"]) if raw.get("start") else None,
            stop=tuple(raw["stop"]) if raw.get("stop") else None,
            lifecycle=raw.get("lifecycle", "direct"),
        )
        result[spec.name] = spec
    return result


def _pids_for_port(port: int) -> list[int]:
    """Return listener PIDs using Termux-friendly `ss` output when available."""
    try:
        proc = subprocess.run(
            ["ss", "-ltnp"], capture_output=True, text=True, check=False
        )
    except OSError:
        return []
    needle = f":{port}"
    pids: set[int] = set()
    for line in proc.stdout.splitlines():
        if needle not in line or "LISTEN" not in line:
            continue
        for token in line.split("pid=")[1:]:
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                pids.add(int(digits))
    return sorted(pids)


def port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) != 0


def process_identity(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b" ").decode(errors="replace").strip()


def same_program(pid: int, spec: LauncherSpec) -> bool:
    identity = process_identity(pid)
    return bool(identity and spec.identity and spec.identity in identity)


def _run(command: Sequence[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, text=True)


def _wait_until(predicate: Callable[[], bool], timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return predicate()


def _stop_owned(spec: LauncherSpec, pid: int) -> None:
    if not same_program(pid, spec):
        raise LauncherError(
            f"refusing to stop pid={pid}: ownership of {spec.name} is not proven"
        )
    if spec.stop:
        result = _run(spec.stop, cwd=spec.root)
        if result.returncode != 0:
            raise LauncherError(f"graceful stop failed for {spec.name}: exit={result.returncode}")
    else:
        os.kill(pid, signal.SIGTERM)
    if not _wait_until(lambda: not Path(f"/proc/{pid}").exists()):
        raise LauncherError(f"refusing restart: pid={pid} did not exit gracefully")
    if spec.port is not None and not _wait_until(lambda: port_is_free(spec.port)):
        raise LauncherError(f"refusing restart: port {spec.port} was not released")


def launch(spec: LauncherSpec, args: Sequence[str]) -> int:
    if spec.port is None:
        command = [*spec.command, *args]
        return _run(command, cwd=spec.root).returncode

    pids = _pids_for_port(spec.port)
    if pids or not port_is_free(spec.port):
        if not pids:
            raise LauncherError(
                f"port {spec.port} is occupied but its owner cannot be identified; refusing startup"
            )
        for pid in pids:
            if not same_program(pid, spec):
                identity = process_identity(pid) or "<unknown>"
                raise LauncherError(
                    f"port conflict: port={spec.port} pid={pid} process={identity!r}; refusing startup"
                )
        for pid in pids:
            _stop_owned(spec, pid)

    command = [*(spec.start or spec.command), *args]
    result = _run(command, cwd=spec.root)
    if result.returncode != 0:
        return result.returncode
    if not _wait_until(lambda: not port_is_free(spec.port)):
        raise LauncherError(f"{spec.name} exited/startup incomplete: port {spec.port} is not listening")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print("usage: yasin-launch <name> [args...]")
        return 0
    if args[0] == "list":
        for name, spec in load_registry().items():
            port = str(spec.port) if spec.port is not None else "portless"
            print(f"{name}\t{port}\t{spec.lifecycle}")
        return 0
    name, rest = args[0], args[1:]
    spec = load_registry().get(name)
    if spec is None:
        print(f"unknown launcher: {name}", file=sys.stderr)
        return 2
    try:
        return launch(spec, rest)
    except LauncherError as exc:
        print(f"launcher refused: {exc}", file=sys.stderr)
        return 2
