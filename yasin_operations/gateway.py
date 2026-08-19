"""Local JSONL gateway for external Operations Agent clients."""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from typing import Any, Mapping, TextIO

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.adapters.hermes.contracts import HermesOperationRequest, HermesOperationResponse

GATEWAY_SCHEMA_VERSION = 1
DEFAULT_MAX_LINE_BYTES = 64 * 1024
DEFAULT_MAX_PARAMETER_BYTES = 32 * 1024
DEFAULT_MAX_IDENTIFIER_LENGTH = 256
DEFAULT_RECENT_REQUEST_IDS = 1024


def _validate_identifier(name: str, value: str, maximum: int = DEFAULT_MAX_IDENTIFIER_LENGTH) -> None:
    if not value or len(value) > maximum:
        raise ValueError(f"{name} must be 1..{maximum} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} must not contain control characters")


@dataclass(frozen=True)
class GatewayResponse:
    schema_version: int
    response: HermesOperationResponse

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.response.request_id,
            "operation_id": self.response.operation_id,
            "success": self.response.success,
            "status": self.response.status,
            "data": dict(self.response.data),
            "error": dict(self.response.error or {}) if self.response.error is not None else None,
            "service_available": self.response.service_available,
        }


class JsonlGateway:
    """Serve validated operations over stdin/stdout JSONL."""

    def __init__(
        self,
        adapter: HermesOperationsAdapter,
        *,
        max_line_bytes: int = DEFAULT_MAX_LINE_BYTES,
        max_parameter_bytes: int = DEFAULT_MAX_PARAMETER_BYTES,
        max_identifier_length: int = DEFAULT_MAX_IDENTIFIER_LENGTH,
        recent_request_ids: int = DEFAULT_RECENT_REQUEST_IDS,
        reject_duplicates: bool = True,
    ) -> None:
        if max_line_bytes < 1024 or max_parameter_bytes < 256:
            raise ValueError("gateway size limits are too small")
        if max_identifier_length < 16 or recent_request_ids < 0:
            raise ValueError("gateway protocol limits are invalid")
        self._adapter = adapter
        self._max_line_bytes = max_line_bytes
        self._max_parameter_bytes = max_parameter_bytes
        self._max_identifier_length = max_identifier_length
        self._recent_request_ids = recent_request_ids
        self._reject_duplicates = reject_duplicates
        self._seen_ids: set[str] = set()
        self._seen_order: deque[str] = deque()
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self) -> None:
        self._stopped = True

    def _remember_request_id(self, request_id: str) -> None:
        if not self._recent_request_ids:
            return
        if request_id in self._seen_ids:
            if self._reject_duplicates:
                raise ValueError("duplicate request_id")
            return
        self._seen_ids.add(request_id)
        self._seen_order.append(request_id)
        while len(self._seen_order) > self._recent_request_ids:
            self._seen_ids.discard(self._seen_order.popleft())

    def handle_line(self, line: str) -> dict[str, Any]:
        request_id = "unknown"
        try:
            if len(line.encode("utf-8")) > self._max_line_bytes:
                raise ValueError("request exceeds maximum line size")
            payload = json.loads(line)
            if not isinstance(payload, Mapping):
                raise ValueError("request envelope must be a JSON object")
            if payload.get("schema_version", GATEWAY_SCHEMA_VERSION) != GATEWAY_SCHEMA_VERSION:
                raise ValueError("unsupported schema_version")
            if payload.get("request_id") is not None:
                request_id = str(payload["request_id"])
            request_payload = payload.get("request", payload)
            if not isinstance(request_payload, Mapping):
                raise ValueError("request must be a JSON object")
            request = HermesOperationRequest.from_mapping(request_payload)
            request_id = request.request_id
            _validate_identifier("request_id", request.request_id, self._max_identifier_length)
            _validate_identifier("actor", request.actor, self._max_identifier_length)
            _validate_identifier("source", request.source, self._max_identifier_length)
            _validate_identifier("operation", request.operation, self._max_identifier_length)
            _validate_identifier("target_kind", request.target_kind, self._max_identifier_length)
            _validate_identifier("target_identifier", request.target_identifier, self._max_identifier_length)
            if request.correlation_id is not None:
                _validate_identifier("correlation_id", request.correlation_id, self._max_identifier_length)
            parameter_bytes = len(json.dumps(request.parameters, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            if parameter_bytes > self._max_parameter_bytes:
                raise ValueError("parameters exceed maximum size")
            self._remember_request_id(request.request_id)
            response = self._adapter.handle(request)
        except json.JSONDecodeError as exc:
            response = HermesOperationResponse(
                request_id=request_id,
                operation_id=None,
                success=False,
                status="invalid_request",
                error={"category": "validation_error", "message": f"invalid JSON: {exc.msg}", "details": {}},
                service_available=self._adapter.available,
            )
        except ValueError as exc:
            response = HermesOperationResponse(
                request_id=request_id,
                operation_id=None,
                success=False,
                status="invalid_request",
                error={"category": "validation_error", "message": str(exc), "details": {}},
                service_available=self._adapter.available,
            )
        except Exception as exc:  # noqa: BLE001 - boundary must stay alive
            response = HermesOperationResponse(
                request_id=request_id,
                operation_id=None,
                success=False,
                status="failed",
                error={"category": "internal_error", "message": str(exc), "details": {}},
                service_available=self._adapter.available,
            )
        return GatewayResponse(GATEWAY_SCHEMA_VERSION, response).as_dict()

    def serve_once(self, input_stream: TextIO, output_stream: TextIO) -> bool:
        line = input_stream.readline()
        if line == "":
            return False
        if line.strip():
            output_stream.write(json.dumps(self.handle_line(line), ensure_ascii=False, sort_keys=True) + "\n")
            output_stream.flush()
        return True

    def serve(self, input_stream: TextIO, output_stream: TextIO) -> None:
        while not self._stopped and self.serve_once(input_stream, output_stream):
            pass
