"""Optional Hermes-facing operations gateway.

Hermes is treated as an untrusted interface client. The adapter only
translates validated requests into typed Core Operations and delegates
execution to the existing policy-enforcing Executor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from yasin_operations.adapters.hermes.contracts import HermesOperationRequest, HermesOperationResponse
from yasin_operations.core.execution.executor import Executor
from yasin_operations.core.operations.models import Operation, OperationMetadata, OperationTarget
from yasin_operations.core.results.models import ErrorCategory
from yasin_operations.safety.classification import SafetyClass


@dataclass(frozen=True)
class HermesOperationsAdapter:
    """Transport-neutral gateway for an optional Hermes integration."""

    executor: Executor | None

    @property
    def available(self) -> bool:
        return self.executor is not None

    def handle(
        self,
        request: HermesOperationRequest | Mapping[str, Any],
    ) -> HermesOperationResponse:
        request_id = self._request_id(request)
        try:
            normalized = (
                request
                if isinstance(request, HermesOperationRequest)
                else HermesOperationRequest.from_mapping(request)
            )
        except ValueError as exc:
            return HermesOperationResponse(
                request_id=request_id,
                operation_id=None,
                success=False,
                status="invalid_request",
                error={
                    "category": ErrorCategory.VALIDATION_ERROR.value,
                    "message": str(exc),
                    "details": {},
                },
                service_available=self.available,
            )

        if self.executor is None:
            return HermesOperationResponse.unavailable(normalized.request_id)

        operation = Operation(
            name=normalized.operation,
            target=OperationTarget(
                kind=normalized.target_kind,
                identifier=normalized.target_identifier,
            ),
            safety_class=normalized.safety_class,
            parameters=normalized.parameters,
            metadata=OperationMetadata(values={"hermes_request_id": normalized.request_id}),
        )
        try:
            result = self.executor.execute(
                operation,
                actor=normalized.actor,
                source=normalized.source,
                confirmation=normalized.confirmation,
                dry_run=normalized.dry_run,
                correlation_id=normalized.correlation_id,
            )
        except (ConnectionError, TimeoutError):
            return HermesOperationResponse(
                request_id=normalized.request_id,
                operation_id=operation.id,
                success=False,
                status="unavailable",
                error={
                    "category": ErrorCategory.UNAVAILABLE_DEPENDENCY.value,
                    "message": "Yasin-Operations runtime dependency is unavailable",
                    "details": {},
                },
                service_available=False,
            )
        except Exception:  # noqa: BLE001 - interface boundary must stay structured
            return HermesOperationResponse(
                request_id=normalized.request_id,
                operation_id=operation.id,
                success=False,
                status="failed",
                error={
                    "category": ErrorCategory.INTERNAL_ERROR.value,
                    "message": "operation failed due to an internal error",
                    "details": {},
                },
                service_available=True,
            )
        return HermesOperationResponse.from_result(normalized.request_id, result)

    def health_summary(self) -> Mapping[str, Any]:
        """Return safe health and diagnostics summaries for the interface."""
        if self.executor is None:
            return {
                "available": False,
                "health": None,
                "diagnostics": None,
                "error": "Yasin-Operations runtime is unavailable",
            }

        return {
            "available": True,
            "health": self._read_only_summary(
                operation="health_check",
                target_kind="self",
                target_identifier="runtime",
            ),
            "diagnostics": self._read_only_summary(
                operation="diagnostics",
                target_kind="runtime",
                target_identifier="local",
            ),
        }

    def _read_only_summary(
        self,
        *,
        operation: str,
        target_kind: str,
        target_identifier: str,
    ) -> Mapping[str, Any]:
        request = HermesOperationRequest(
            operation=operation,
            target_kind=target_kind,
            target_identifier=target_identifier,
            safety_class=SafetyClass.READ_ONLY,
            actor="hermes",
            source="hermes.health_summary",
        )
        response = self.handle(request)
        return {
            "success": response.success,
            "status": response.status,
            "data": dict(response.data),
            "error": dict(response.error or {}),
        }

    @staticmethod
    def _request_id(request: HermesOperationRequest | Mapping[str, Any]) -> str:
        if isinstance(request, HermesOperationRequest):
            return request.request_id
        if not isinstance(request, Mapping):
            return "unknown"
        value = request.get("request_id")
        return value if isinstance(value, str) else "unknown"
