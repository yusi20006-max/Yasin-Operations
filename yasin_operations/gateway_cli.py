"""CLI entrypoint for the optional local JSONL Operations Gateway."""
from __future__ import annotations

import argparse
import sys

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.cli import build_runtime
from yasin_operations.gateway import JsonlGateway


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yasin-operations gateway",
        description="serve typed Operations requests over stdin/stdout JSONL",
    )
    parser.add_argument("--version", action="version", version="gateway-schema-1")
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    executor, _config, _audit = build_runtime()
    JsonlGateway(HermesOperationsAdapter(executor)).serve(sys.stdin, sys.stdout)
    return 0
