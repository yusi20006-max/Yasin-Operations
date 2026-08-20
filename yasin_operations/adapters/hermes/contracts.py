"""Transport-neutral contracts for an optional Hermes client adapter."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

from yasin_operations.core.results.models import OperationResult
from yasin_operations.safety.classification import SafetyClass


_REQUEST_FIELDS = frozenset(
    {
        "operation",
        "target_kind",
        "target_identifier",
        "safety_class",
        "parameters",
        "confirmation",
        "dry_run",
        "actor",
        "source",
        "request_id",
        "correlation_id",
    }
)


def _require_string(name: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if not allow_empty and not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def _require_bool(name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be a boolean")
    return value


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
        for name in ("operation", "target_kind", "target_identifier", "actor", "source", "request_id"):
            _require_string(name, getattr(self, name))
        if self.correlation_id is not None:
            _require_string("correlation_id", self.correlation_id)
        if not isinstance(self.safety_class, SafetyClass):
            raise ValueError("safety_class must be a SafetyClass member")
        if not isinstance(self.parameters, Mapping):
            raise ValueError("parameters must be an object")
        if not isinstance(self.confirmation, bool):
            raise ValueError("confirmation must be a boolean")
        if not isinstance(self.dry_run, bool):
            raise ValueError("dry_run must be a boolean")

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "HermesOperationRequest":
        """Build a request from JSON-like data without executing anything.

        External callers are deliberately not allowed to rely on Python's
        permissive ``str(...)``/``bool(...)`` coercions. Ambiguous values are
        rejected before they can become authorization inputs.
        """
        if not isinstance(payload, Mapping):
            raise ValueError("request must be an object")
        unknown = set(payload) - _REQUEST_FIELDS
        if unknown:
            raise ValueError(f"unknown request field: {sorted(unknown)[0]}")
        try:
            safety_value = payload["safety_class"]
            if not isinstance(safety_value, str):
                raise ValueError("safety_class must be a string")
            safety = SafetyClass(safety_value)

            parameters = payload.get("parameters", {})
            if not isinstance(parameters, Mapping):
                raise ValueError("parameters must be an object")

            confirmation = payload.get("confirmation", False)
            dry_run = payload.get("dry_run", False)
            _require_bool("confirmation", confirmation)
            _require_bool("dry_run", dry_run)

            request_id = payload.get("request_id", str(uuid.uuid4()))
            correlation_id = payload.get("correlation_id")
            return cls(
                operation=_require_string("operation", payload["operation"]),
                target_kind=_require_string("target_kind", payload["target_kind"]),
                target_identifier=_require_string("target_identifier", payload["target_identifier"]),
                safety_class=safety,
                parameters=dict(parameters),
                confirmation=confirmation,
                dry_run=dry_run,
                actor=_require_string("actor", payload.get("actor", "hermes")),
                source=_require_string("source", payload.get("source", "hermes")),
                request_id=_require_string("request_id", request_id),
                correlation_id=(
                    _require_string("correlation_id", correlation_id)
                    if correlation_id is not None
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
