"""Policy enforcement for operational safety.

The policy is deliberately deny-by-default for mutating work. It does not
execute anything and contains no shell or platform-specific logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Mapping, Tuple

from yasin_operations.core.operations.models import Operation
from yasin_operations.safety.classification import SafetyClass


TargetKey = Tuple[str, str]


@dataclass(frozen=True)
class PolicyDecision:
    """Machine-readable authorization decision."""

    allowed: bool
    reason: str
    requires_confirmation: bool = False
    dry_run: bool = False
    max_attempts: int = 1

    @property
    def denied(self) -> bool:
        return not self.allowed


@dataclass(frozen=True)
class SafetyPolicy:
    """Explicit authorization and execution-safety policy.

    READ_ONLY operations are allowed without confirmation. MUTATING
    operations require confirmation unless their operation name is in
    ``auto_approved_mutations``. Protected targets are denied by default and
    can only be changed when the operation name is also in
    ``protected_mutation_allowlist`` and explicit confirmation is given.
    """

    require_confirmation_for_mutations: bool = True
    protected_targets: FrozenSet[TargetKey] = field(default_factory=frozenset)
    auto_approved_mutations: FrozenSet[str] = field(default_factory=frozenset)
    protected_mutation_allowlist: FrozenSet[str] = field(default_factory=frozenset)
    max_read_only_attempts: int = 1
    max_mutating_attempts: int = 1
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.require_confirmation_for_mutations, bool):
            raise ValueError("require_confirmation_for_mutations must be a boolean")
        if self.max_read_only_attempts < 1 or self.max_mutating_attempts < 1:
            raise ValueError("attempt limits must be at least 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    @classmethod
    def with_protected_targets(
        cls, targets: Iterable[TargetKey], **kwargs: object
    ) -> "SafetyPolicy":
        return cls(protected_targets=frozenset(targets), **kwargs)

    def evaluate(
        self,
        operation: Operation,
        *,
        confirmation: bool = False,
        dry_run: bool = False,
    ) -> PolicyDecision:
        if not isinstance(confirmation, bool):
            raise ValueError("confirmation must be a boolean")
        if not isinstance(dry_run, bool):
            raise ValueError("dry_run must be a boolean")

        attempts = (
            self.max_read_only_attempts
            if operation.safety_class is SafetyClass.READ_ONLY
            else self.max_mutating_attempts
        )

        if dry_run:
            return PolicyDecision(
                allowed=True,
                reason="dry-run requested; no external mutation will be performed",
                dry_run=True,
                max_attempts=1,
            )

        if operation.safety_class is SafetyClass.READ_ONLY:
            return PolicyDecision(
                allowed=True,
                reason="read-only operation permitted",
                max_attempts=attempts,
            )

        target = (operation.target.kind, operation.target.identifier)
        protected = target in self.protected_targets
        explicitly_allowed = operation.name in self.protected_mutation_allowlist
        if protected and not explicitly_allowed:
            return PolicyDecision(
                allowed=False,
                reason="target is protected by safety policy",
                max_attempts=attempts,
            )
        if protected and explicitly_allowed and not confirmation:
            return PolicyDecision(
                allowed=False,
                reason="protected mutation requires explicit confirmation",
                requires_confirmation=True,
                max_attempts=attempts,
            )

        needs_confirmation = (
            self.require_confirmation_for_mutations
            and operation.name not in self.auto_approved_mutations
        )
        if needs_confirmation and not confirmation:
            return PolicyDecision(
                allowed=False,
                reason="mutating operation requires explicit confirmation",
                requires_confirmation=True,
                max_attempts=attempts,
            )

        return PolicyDecision(
            allowed=True,
            reason="mutating operation permitted by policy",
            max_attempts=attempts,
        )

    def plan(self, operation: Operation) -> Mapping[str, object]:
        """Return a deterministic, non-executing description of an operation."""
        decision = self.evaluate(operation, dry_run=True)
        return {
            "operation_id": operation.id,
            "operation": operation.name,
            "target": {
                "kind": operation.target.kind,
                "identifier": operation.target.identifier,
            },
            "safety_class": operation.safety_class.value,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "dry_run": True,
            "parameters": dict(operation.parameters),
        }
