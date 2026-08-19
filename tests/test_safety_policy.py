import pytest

from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.safety.policy import SafetyPolicy


def _operation(safety_class=SafetyClass.MUTATING, name="restart"):
    return Operation(
        name=name,
        target=OperationTarget(kind="service", identifier="demo"),
        safety_class=safety_class,
        parameters={"reason": "test"},
    )


def test_read_only_is_allowed_without_confirmation():
    decision = SafetyPolicy().evaluate(_operation(SafetyClass.READ_ONLY))
    assert decision.allowed
    assert not decision.requires_confirmation


def test_mutation_requires_confirmation_by_default():
    decision = SafetyPolicy().evaluate(_operation())
    assert decision.denied
    assert decision.requires_confirmation


def test_confirmed_mutation_is_allowed():
    decision = SafetyPolicy().evaluate(_operation(), confirmation=True)
    assert decision.allowed


def test_auto_approved_mutation_does_not_need_confirmation():
    policy = SafetyPolicy(auto_approved_mutations=frozenset({"restart"}))
    assert policy.evaluate(_operation()).allowed


def test_protected_target_is_denied_by_default():
    policy = SafetyPolicy.with_protected_targets({("service", "demo")})
    decision = policy.evaluate(_operation(), confirmation=True)
    assert decision.denied
    assert "protected" in decision.reason


def test_protected_target_requires_allowlist_and_confirmation():
    policy = SafetyPolicy.with_protected_targets(
        {("service", "demo")},
        protected_mutation_allowlist=frozenset({"restart"}),
    )
    assert policy.evaluate(_operation()).denied
    assert policy.evaluate(_operation(), confirmation=True).allowed


def test_dry_run_is_non_mutating_and_deterministic():
    operation = _operation()
    policy = SafetyPolicy()
    first = policy.plan(operation)
    second = policy.plan(operation)
    assert first == second
    assert first["dry_run"] is True
    assert first["operation_id"] == operation.id
    assert first["parameters"] == {"reason": "test"}


def test_invalid_limits_are_rejected():
    with pytest.raises(ValueError):
        SafetyPolicy(max_read_only_attempts=0)
    with pytest.raises(ValueError):
        SafetyPolicy(timeout_seconds=0)
