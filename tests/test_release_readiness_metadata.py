from pathlib import Path

from scripts.release_readiness import check_installed_metadata, check_project_metadata
from yasin_operations.version import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_project_metadata_matches_release_contract():
    ok, problems = check_project_metadata(ROOT)
    assert ok, problems


def test_installed_distribution_matches_authoritative_version():
    ok, installed = check_installed_metadata()
    assert ok, installed
    assert installed == __version__
