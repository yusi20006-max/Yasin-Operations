from pathlib import Path

from scripts.release_readiness import check_external_imports, check_repository_hygiene, check_version
from yasin_operations.version import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_version_is_authoritative_and_nonempty():
    ok, version = check_version()
    assert ok
    assert version == __version__
    assert version.count(".") >= 2


def test_repository_hygiene_has_no_forbidden_tracked_artifacts():
    ok, violations = check_repository_hygiene(ROOT)
    assert ok, violations


def test_yasin_operations_has_no_external_yasin_imports():
    ok, violations = check_external_imports(ROOT)
    assert ok, violations
