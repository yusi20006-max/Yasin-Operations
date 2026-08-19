"""Local JSONL gateway for external Operations Agent clients."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, TextIO

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.adapters.hermes.contracts import HermesOperationRequest, HermesOperationResponse

GATEWAY_SCHEMA_VERSION = 1


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

    def __init__(self, adapter: HermesOperationsAdapter) -> None:
        self._adapter = adapter
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self) -> None:
        self._stopped = True

    def handle_line(self, line: str) -> dict[str, Any]:
        request_id = "unknown"
        try:
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
