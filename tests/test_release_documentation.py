from pathlib import Path

from yasin_operations.version import __version__


ROOT = Path(__file__).resolve().parents[1]


def test_release_process_exists_and_contains_canonical_verification_order():
    document = (ROOT / "docs" / "RELEASE_PROCESS.md").read_text(encoding="utf-8")
    assert f"Yasin-Operations v{__version__}" in document
    assert "python -m pytest -q" in document
    assert "python scripts/production_acceptance.py --json" in document
    assert "python scripts/release_readiness.py --json" in document
    assert "python -m build --wheel --sdist" in document
    assert "3.11, 3.12, 3.13, and 3.14" in document


def test_readme_points_to_canonical_release_process():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/RELEASE_PROCESS.md" in readme
    assert "docs/RELEASE_READINESS_v0.1.0.md" in readme


def test_release_evidence_contains_no_machine_specific_identifiers():
    evidence = (ROOT / "docs" / "RELEASE_READINESS_v0.1.0.md").read_text(encoding="utf-8")
    assert "/data/data/" not in evidence
    assert "/home/" not in evidence
    assert "localhost:" not in evidence.lower()
    assert "127.0.0.1" not in evidence
    assert "private-user-images" not in evidence
