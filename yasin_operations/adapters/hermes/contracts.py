"""Transport-neutral contracts for an optional Hermes client adapter."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass


@dataclass(frozen=True)
class HermesOperationRequest:
    """Validated request received from an external Hermes interface."""

    operation: str
    target_kind: str
    target_identifier: str
    safety_class: SafetyClass
    parameters: Mapping[str, Any] = field(default_factory=dict)
    confirmation: bool = False
    dry_run: bool = False
    actor: str = "hermes"
    source: str = "hermes"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if not self.operation.strip():
            raise ValueError("operation must not be empty")
        if not self.target_kind.strip() or not self.target_identifier.strip():
            raise ValueError("target kind and identifier must not be empty")
        if not isinstance(self.safety_class, SafetyClass):
            raise ValueError("safety_class must be a SafetyClass member")
        if not self.actor.strip() or not self.source.strip():
            raise ValueError("actor and source must not be empty")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HermesOperationRequest":
        """Build a request from JSON-like data without executing anything."""
        try:
            safety = payload["safety_class"]
            if not isinstance(safety, SafetyClass):
                safety = SafetyClass(str(safety))
            return cls(
                operation=str(payload["operation"]),
                target_kind=str(payload["target_kind"]),
                target_identifier=str(payload["target_identifier"]),
                safety_class=safety,
                parameters=dict(payload.get("parameters", {})),
                confirmation=bool(payload.get("confirmation", False)),
                dry_run=bool(payload.get("dry_run", False)),
                actor=str(payload.get("actor", "hermes")),
                source=str(payload.get("source", "hermes")),
                request_id=str(payload.get("request_id", uuid.uuid4())),
                correlation_id=(
                    str(payload["correlation_id"])
                    if payload.get("correlation_id") is not None
                    else None
                ),
            )
        except KeyError as exc:
            raise ValueError(f"missing Hermes request field: {exc.args[0]}") from None
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid Hermes operation request: {exc}") from None


@dataclass(frozen=True)
class HermesOperationResponse:
    """Predictable response contract for the external Hermes interface."""

    request_id: str
    operation_id: str | None
    success: bool
    status: str
    data: Mapping[str, Any] = field(default_factory=dict)
    error: Mapping[str, Any] | None = None
    service_available: bool = True

    @classmethod
    def from_result(
        cls,
        request_id: str,
        result: OperationResult,
        *,
        service_available: bool = True,
    ) -> "HermesOperationResponse":
        error = None
        if result.error is not None:
            error = {
                "category": result.error.category.value,
                "message": result.error.message,
                "details": dict(result.error.details),
            }
        return cls(
            request_id=request_id,
            operation_id=result.operation_id,
            success=result.success,
            status="succeeded" if result.success else "failed",
            data=dict(result.data or {}),
            error=error,
            service_available=service_available,
        )

    @classmethod
    def unavailable(cls, request_id: str) -> "HermesOperationResponse":
        return cls(
            request_id=request_id,
            operation_id=None,
            success=False,
            status="unavailable",
            error={
                "category": "unavailable_dependency",
                "message": "Yasin-Operations runtime is unavailable",
                "details": {},
            },
            service_available=False,
        )
