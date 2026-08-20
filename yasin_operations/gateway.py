"""Local JSONL gateway for external Operations Agent clients."""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Any, Mapping, TextIO

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.adapters.hermes.contracts import HermesOperationRequest, HermesOperationResponse
from yasin_operations.safety.classification import SafetyClass

GATEWAY_SCHEMA_VERSION = 1
DEFAULT_MAX_LINE_BYTES = 64 * 1024
DEFAULT_MAX_PARAMETER_BYTES = 32 * 1024
DEFAULT_MAX_IDENTIFIER_LENGTH = 256
DEFAULT_RECENT_REQUEST_IDS = 1024


def _validate_identifier(name: str, value: str, maximum: int = DEFAULT_MAX_IDENTIFIER_LENGTH) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if not value or len(value) > maximum:
        raise ValueError(f"{name} must be 1..{maximum} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} must not contain control characters")


def _validate_schema_version(value: object) -> None:
    if type(value) is not int or value != GATEWAY_SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")


def _request_fingerprint(request: HermesOperationRequest) -> str:
    """Return a stable digest of all execution-relevant request fields."""
    canonical = {
        "operation": request.operation,
        "target_kind": request.target_kind,
        "target_identifier": request.target_identifier,
        "safety_class": request.safety_class.value,
        "parameters": request.parameters,
        "confirmation": request.confirmation,
        "dry_run": request.dry_run,
        "actor": request.actor,
        "source": request.source,
        "correlation_id": request.correlation_id,
    }
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
    """Serve validated operations over stdin/stdout JSONL.

    The gateway is a trust boundary: transport metadata is validated before
    the adapter is called, and unexpected internal exceptions are converted to
    a stable generic error rather than exposing exception text to clients.

    Request lifecycle semantics are intentionally bounded and local:
    read-only requests may replay the exact completed response for a matching
    request ID; mutating requests reject duplicates. Concurrent reuse of an
    in-flight request ID is rejected for every operation class. The ledger is
    in-memory and is reset when the process restarts.
    """

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
        self._records: dict[str, tuple[str, SafetyClass, dict[str, Any]]] = {}
        self._record_order: deque[str] = deque()
        self._inflight: set[str] = set()
        self._ledger_lock = Lock()
        self._stopped = False

    @property
    def stopped(self) -> bool:
        return self._stopped

    def stop(self) -> None:
        self._stopped = True

    def _reserve_request(self, request: HermesOperationRequest) -> dict[str, Any] | None:
        """Reserve a request ID or return a cached read-only response."""
        if not self._recent_request_ids or not self._reject_duplicates:
            return None
        fingerprint = _request_fingerprint(request)
        with self._ledger_lock:
            record = self._records.get(request.request_id)
            if record is not None:
                old_fingerprint, safety_class, cached_response = record
                if old_fingerprint != fingerprint:
                    raise ValueError("request_id was already used for a different request")
                if safety_class is SafetyClass.READ_ONLY:
                    return dict(cached_response)
                raise ValueError("duplicate request_id for mutating operation")
            if request.request_id in self._inflight:
                raise ValueError("request_id is already in progress")
            self._inflight.add(request.request_id)
        return None

    def _record_request(
        self,
        request: HermesOperationRequest,
        response: dict[str, Any],
    ) -> None:
        if not self._recent_request_ids or not self._reject_duplicates:
            return
        fingerprint = _request_fingerprint(request)
        with self._ledger_lock:
            self._inflight.discard(request.request_id)
            self._records[request.request_id] = (fingerprint, request.safety_class, dict(response))
            self._record_order.append(request.request_id)
            while len(self._record_order) > self._recent_request_ids:
                old_id = self._record_order.popleft()
                self._records.pop(old_id, None)

    def _release_inflight(self, request_id: str) -> None:
        with self._ledger_lock:
            self._inflight.discard(request_id)

    def handle_line(self, line: str) -> dict[str, Any]:
        request_id = "unknown"
        tracked_request: HermesOperationRequest | None = None
        try:
            if len(line.encode("utf-8")) > self._max_line_bytes:
                raise ValueError("request exceeds maximum line size")
            payload = json.loads(line)
            if not isinstance(payload, Mapping):
                raise ValueError("request envelope must be a JSON object")
            _validate_schema_version(payload.get("schema_version", GATEWAY_SCHEMA_VERSION))

            envelope_request_id = payload.get("request_id")
            if envelope_request_id is not None:
                _validate_identifier("request_id", envelope_request_id, self._max_identifier_length)
                request_id = envelope_request_id

            request_payload = payload.get("request", payload)
            if not isinstance(request_payload, Mapping):
                raise ValueError("request must be a JSON object")
            request = HermesOperationRequest.from_mapping(request_payload)
            if envelope_request_id is not None and request.request_id != envelope_request_id:
                raise ValueError("envelope request_id does not match request request_id")

            request_id = request.request_id
            _validate_identifier("request_id", request.request_id, self._max_identifier_length)
            _validate_identifier("actor", request.actor, self._max_identifier_length)
            _validate_identifier("source", request.source, self._max_identifier_length)
            _validate_identifier("operation", request.operation, self._max_identifier_length)
            _validate_identifier("target_kind", request.target_kind, self._max_identifier_length)
            _validate_identifier("target_identifier", request.target_identifier, self._max_identifier_length)
            if request.correlation_id is not None:
                _validate_identifier("correlation_id", request.correlation_id, self._max_identifier_length)

            parameter_bytes = len(
                json.dumps(request.parameters, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            )
            if parameter_bytes > self._max_parameter_bytes:
                raise ValueError("parameters exceed maximum size")

            tracked_request = request if self._recent_request_ids and self._reject_duplicates else None
            if tracked_request is not None:
                cached = self._reserve_request(tracked_request)
                if cached is not None:
                    return cached

            response = self._adapter.handle(request)
            response_dict = GatewayResponse(GATEWAY_SCHEMA_VERSION, response).as_dict()
            if tracked_request is not None:
                self._record_request(tracked_request, response_dict)
            return response_dict
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
        except Exception:  # noqa: BLE001 - trust boundary must stay alive without leaking internals
            response = HermesOperationResponse(
                request_id=request_id,
                operation_id=None,
                success=False,
                status="failed",
                error={
                    "category": "internal_error",
                    "message": "internal gateway error",
                    "details": {},
                },
                service_available=self._adapter.available,
            )
        finally:
            if tracked_request is not None and request_id == tracked_request.request_id:
                # Successful paths record and clear the reservation; failures
                # before the response is constructed must not poison the ID.
                self._release_inflight(request_id)

        response_dict = GatewayResponse(GATEWAY_SCHEMA_VERSION, response).as_dict()
        return response_dict

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
