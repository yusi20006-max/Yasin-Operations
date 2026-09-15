"""Termux launcher script and module entrypoint."""
from __future__ import annotations

import sys
from typing import Sequence

from yasin_operations.config.config import load_config
from yasin_operations.runtime.local.process_backend import LocalProcessInspector
from yasin_operations.runtime.local.service_backend import LocalServiceBackend
from yasin_operations.runtime.tools import register_runtime_tools
from yasin_operations.tools.registry.registry import ToolRegistry


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] == "list":
        config = load_config()
        inspector = LocalProcessInspector()
        backend = LocalServiceBackend(
            inspector,
            definitions=config.service_definitions(),
            command_timeout_seconds=config.execution_timeout_seconds,
            startup_grace_seconds=config.startup_grace_seconds,
        )
        registry = ToolRegistry()
        register_runtime_tools(registry, inspector=inspector, service_backend=backend, config=config)

        for descriptor in registry.list_tools():
            print(descriptor.id)
        for name in config.service_names:
            print(name)
        return 0

    from yasin_operations.entrypoint import main as entrypoint_main
    return entrypoint_main()


if __name__ == "__main__":
    raise SystemExit(main())
