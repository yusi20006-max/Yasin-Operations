#!/usr/bin/env python3
"""Validate a Yasin System Release JSON manifest deterministically."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

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
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} <manifest.json>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"invalid manifest: {exc}", file=sys.stderr)
        return 1

    missing = REQUIRED_KEYS - set(data)
    if missing:
        print(f"missing keys: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1

    repositories = data["repositories"]
    expected = data["verification"]["repository_count"]
    if len(repositories) != expected:
        print("repository_count does not match repositories list", file=sys.stderr)
        return 1

    names = [item.get("name") for item in repositories]
    if len(names) != len(set(names)):
        print("duplicate repository name", file=sys.stderr)
        return 1

    for item in repositories:
        if item.get("branch") != "main" or not SHA_RE.fullmatch(item.get("commit", "")):
            print(f"invalid repository ref for {item.get('name')}", file=sys.stderr)
            return 1

    verification = data["verification"]
    if verification.get("sync") != "PASS":
        print("verification.sync must be PASS", file=sys.stderr)
        return 1
    if verification.get("ahead") != 0 or verification.get("behind") != 0:
        print("release snapshot is not synchronized", file=sys.stderr)
        return 1
    if verification.get("tracked_changes") != 0:
        print("release snapshot has tracked changes", file=sys.stderr)
        return 1
    if "YasinCoder" in names or "YasinHub-backup-20260904-094936" in names:
        print("retired/backup repository must not be included", file=sys.stderr)
        return 1

    print(f"PASS: {path} ({len(repositories)} repositories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
