"""CLI entrypoint for the optional local JSONL Operations Gateway."""
from __future__ import annotations

import argparse
import sys

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.cli import build_runtime
from yasin_operations.gateway import (
    DEFAULT_MAX_IDENTIFIER_LENGTH,
    DEFAULT_MAX_LINE_BYTES,
    DEFAULT_MAX_PARAMETER_BYTES,
    DEFAULT_RECENT_REQUEST_IDS,
    JsonlGateway,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yasin-operations gateway",
        description="serve typed Operations requests over stdin/stdout JSONL",
    )
    parser.add_argument("--version", action="version", version="gateway-schema-1")
    parser.add_argument("--max-line-bytes", type=int, default=DEFAULT_MAX_LINE_BYTES)
    parser.add_argument("--max-parameter-bytes", type=int, default=DEFAULT_MAX_PARAMETER_BYTES)
    parser.add_argument("--max-identifier-length", type=int, default=DEFAULT_MAX_IDENTIFIER_LENGTH)
    parser.add_argument("--recent-request-ids", type=int, default=DEFAULT_RECENT_REQUEST_IDS)
    parser.add_argument("--allow-duplicate-request-ids", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    executor, _config, _audit = build_runtime()
    gateway = JsonlGateway(
        HermesOperationsAdapter(executor),
        max_line_bytes=args.max_line_bytes,
        max_parameter_bytes=args.max_parameter_bytes,
        max_identifier_length=args.max_identifier_length,
        recent_request_ids=args.recent_request_ids,
        reject_duplicates=not args.allow_duplicate_request_ids,
    )
    gateway.serve(sys.stdin, sys.stdout)
    return 0
