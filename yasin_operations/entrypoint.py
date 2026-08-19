"""Installed console entrypoint with optional gateway subcommand."""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "gateway":
        from yasin_operations.gateway_cli import main as gateway_main

        return gateway_main(sys.argv[2:])

    from yasin_operations.cli import main as cli_main

    return cli_main(sys.argv[1:])
