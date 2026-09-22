#!/usr/bin/env python3
"""Validate a Yasin System Release manifest deterministically."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required: python -m pip install pyyaml") from exc

REQUIRED_KEYS = {
    "system_release",
    "release_name",
    "release_date",
    "status",
    "repositories",
    "verification",
    "limitations",
    "excluded",
}


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <manifest.yml>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    missing = REQUIRED_KEYS - set(data or {})
    if missing:
        print(f"missing keys: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1

    repositories = data["repositories"]
    if len(repositories) != data["verification"]["repository_count"]:
        print("repository_count does not match repositories list", file=sys.stderr)
        return 1

    names = [item.get("name") for item in repositories]
    if len(names) != len(set(names)):
        print("duplicate repository name", file=sys.stderr)
        return 1

    for item in repositories:
        commit = item.get("commit", "")
        if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
            print(f"invalid commit SHA for {item.get('name')}", file=sys.stderr)
            return 1
        if item.get("branch") != "main":
            print(f"unexpected branch for {item.get('name')}", file=sys.stderr)
            return 1

    if data["verification"].get("sync") != "PASS":
        print("verification.sync must be PASS", file=sys.stderr)
        return 1

    if data["verification"].get("ahead") != 0 or data["verification"].get("behind") != 0:
        print("release snapshot is not synchronized", file=sys.stderr)
        return 1

    if "YasinCoder" in names:
        print("retired YasinCoder must not be included", file=sys.stderr)
        return 1

    if "YasinHub-backup-20260904-094936" in names:
        print("backup checkout must not be included", file=sys.stderr)
        return 1

    print(f"PASS: {path} ({len(repositories)} repositories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
