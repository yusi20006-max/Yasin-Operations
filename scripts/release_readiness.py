#!/usr/bin/env python3
"""Run the safe, deterministic release-readiness checks for Yasin-Operations."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import subprocess
import sys
import tomllib
from pathlib import Path

from yasin_operations.version import __version__

FORBIDDEN_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
}
FORBIDDEN_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
FORBIDDEN_PARTS = {"__pycache__", ".pytest_cache", ".venv", "venv", "dist", "build"}
EXTERNAL_YASIN_PACKAGES = (
    "yasin_ai",
    "yasinai",
    "yasinpress",
    "yasinrelay",
    "yasinhub",
    "yasinfeed",
)


def _run(command: list[str]) -> tuple[int, str, str]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    return completed.returncode, completed.stdout, completed.stderr


def check_version() -> tuple[bool, str]:
    return bool(__version__.strip()), __version__


def check_project_metadata(root: Path) -> tuple[bool, list[str]]:
    """Validate release-critical project metadata without invoking build tooling."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return False, ["pyproject.toml is missing"]

    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return False, [f"unable to parse pyproject.toml: {exc}"]

    project = document.get("project", {})
    scripts = project.get("scripts", {})
    dynamic = project.get("dynamic", [])
    problems: list[str] = []

    if project.get("name") != "yasin-operations":
        problems.append("project.name must be yasin-operations")
    if project.get("requires-python") != ">=3.11":
        problems.append("project.requires-python must remain >=3.11")
    if "version" not in dynamic:
        problems.append("project.version must remain dynamically sourced")
    if scripts.get("yasin-operations") != "yasin_operations.entrypoint:main":
        problems.append("yasin-operations console script is not authoritative")

    version_file = root / "yasin_operations" / "version.py"
    if not version_file.is_file():
        problems.append("authoritative version.py is missing")

    return not problems, problems


def check_installed_metadata() -> tuple[bool, str]:
    """Ensure installed distribution metadata agrees with the package version."""
    try:
        installed = importlib.metadata.version("yasin-operations")
    except importlib.metadata.PackageNotFoundError:
        return False, "installed distribution metadata not found"
    return installed == __version__, installed


def check_repository_hygiene(root: Path) -> tuple[bool, list[str]]:
    code, stdout, stderr = _run(["git", "-C", str(root), "ls-files"])
    if code != 0:
        return False, [f"git ls-files failed: {stderr.strip()}"]

    violations: list[str] = []
    for raw in stdout.splitlines():
        path = Path(raw)
        name = path.name.lower()
        if name in FORBIDDEN_NAMES or name.endswith(FORBIDDEN_SUFFIXES):
            violations.append(raw)
        if any(part.lower() in FORBIDDEN_PARTS for part in path.parts):
            violations.append(raw)
    return not violations, sorted(set(violations))


def check_external_imports(root: Path) -> tuple[bool, list[str]]:
    violations: list[str] = []
    source_root = root / "yasin_operations"
    for path in source_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for package in EXTERNAL_YASIN_PACKAGES:
            if f"import {package}" in text or f"from {package}" in text:
                violations.append(f"{path}: {package}")
    return not violations, violations


def check_acceptance(root: Path) -> tuple[bool, str]:
    code, stdout, stderr = _run(
        [sys.executable, str(root / "scripts" / "production_acceptance.py"), "--json"]
    )
    if code != 0:
        return False, stdout or stderr
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return False, f"acceptance produced invalid JSON: {exc}"
    return payload.get("success") is True, json.dumps(payload.get("summary", {}), sort_keys=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    version_ok, version = check_version()
    metadata_ok, metadata = check_project_metadata(root)
    installed_ok, installed_version = check_installed_metadata()
    hygiene_ok, hygiene = check_repository_hygiene(root)
    imports_ok, imports = check_external_imports(root)
    acceptance_ok, acceptance = check_acceptance(root)

    checks = [
        {"name": "version", "pass": version_ok, "detail": version},
        {"name": "project_metadata", "pass": metadata_ok, "detail": metadata},
        {
            "name": "installed_metadata",
            "pass": installed_ok,
            "detail": installed_version,
        },
        {"name": "repository_hygiene", "pass": hygiene_ok, "detail": hygiene},
        {"name": "external_yasin_imports", "pass": imports_ok, "detail": imports},
        {"name": "production_acceptance", "pass": acceptance_ok, "detail": acceptance},
    ]
    payload = {"success": all(item["pass"] for item in checks), "version": version, "checks": checks}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in checks:
            status = "PASS" if item["pass"] else "FAIL"
            print(f"[{status}] {item['name']}: {item['detail']}")
    return 0 if payload["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
