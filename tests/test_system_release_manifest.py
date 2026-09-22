"""Contract tests for the system-release manifest validator (Issue #218)."""
from __future__ import annotations

import json
from pathlib import Path

from scripts import validate_system_release


def _manifest(tmp_path: Path, *, branch: str = "main", name: str = "YasinCoder") -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "system_release": "9.9.9-candidate",
                "release_name": "candidate",
                "release_date": "2026-01-01",
                "status": "candidate",
                "repositories": [
                    {"name": name, "branch": branch, "commit": "a" * 40},
                ],
                "verification": {
                    "repository_count": 1,
                    "sync": "PASS",
                    "ahead": 0,
                    "behind": 0,
                    "tracked_changes": 0,
                },
                "limitations": [],
                "excluded": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_master_branch_is_accepted(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv", ["validate_system_release.py", str(_manifest(tmp_path, branch="master"))]
    )
    assert validate_system_release.main() == 0
    assert "PASS" in capsys.readouterr().out


def test_non_coder_repo_may_not_use_master(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_system_release.py",
            str(_manifest(tmp_path, branch="master", name="YasinHub")),
        ],
    )
    assert validate_system_release.main() != 0


def test_yasincoder_may_not_use_main(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        ["validate_system_release.py", str(_manifest(tmp_path, branch="main"))],
    )
    assert validate_system_release.main() != 0


def test_yasincoder_may_be_included(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_system_release.py",
            str(_manifest(tmp_path, branch="master", name="YasinCoder")),
        ],
    )
    assert validate_system_release.main() == 0
    assert "PASS" in capsys.readouterr().out


def test_backup_checkout_is_still_rejected(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_system_release.py",
            str(_manifest(tmp_path, name="YasinHub-backup-20260904-094936")),
        ],
    )
    assert validate_system_release.main() != 0


def test_historical_v1_manifest_still_validates(monkeypatch, capsys):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setattr(
        "sys.argv",
        ["validate_system_release.py", str(root / "releases" / "YASIN-SYSTEM-v1.0.0.json")],
    )
    assert validate_system_release.main() == 0
    assert "PASS" in capsys.readouterr().out
