"""Repository independence and dependency-boundary tests."""

from __future__ import annotations

import ast
import pathlib


def test_no_import_of_external_yasin_packages():
    """No source file may import external Yasin projects or Hermes itself.

    The internal ``yasin_operations.adapters.hermes`` namespace is
    intentionally allowed; only external modules named ``hermes`` or
    other Yasin projects are forbidden.
    """
    package_root = pathlib.Path(__file__).parent.parent / "yasin_operations"
    forbidden_substrings = (
        "yasin_ai",
        "yasinai",
        "yasinpress",
        "yasinrelay",
    )

    offending = []
    for path in package_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module_names = []
            if isinstance(node, ast.Import):
                module_names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_names = [node.module]

            for name in module_names:
                lowered = name.lower()
                if lowered == "hermes" or lowered.startswith("hermes."):
                    offending.append((str(path), name))
                    continue
                for term in forbidden_substrings:
                    if term in lowered:
                        offending.append((str(path), name))

    assert offending == [], f"Found forbidden external imports: {offending}"
