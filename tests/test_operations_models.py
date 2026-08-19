import pytest

from yasin_operations.core.operations.models import (
    InvalidTransitionError,
    Operation,
    OperationMetadata,
    OperationState,
    OperationStatus,
    OperationTarget,
    is_legal_transition,
    is_terminal,
)
from yasin_operations.safety.classification import SafetyClass


def _target():
    return OperationTarget(kind="service", identifier="example")


# -- Valid / invalid operation construction --------------------------------


def test_valid_operation_construction():
    op = Operation(
        name="check_health",
        target=_target(),
        safety_class=SafetyClass.READ_ONLY,
    )
    assert op.name == "check_health"
    assert op.safety_class == SafetyClass.READ_ONLY
    assert op.id  # auto-generated, non-empty
    assert op.created_at is not None


def test_operation_generates_unique_ids():
    op1 = Operation(name="a", target=_target(), safety_class=SafetyClass.READ_ONLY)
    op2 = Operation(name="a", target=_target(), safety_class=SafetyClass.READ_ONLY)
    assert op1.id != op2.id


def test_operation_rejects_empty_name():
    with pytest.raises(ValueError):
        Operation(name="", target=_target(), safety_class=SafetyClass.READ_ONLY)


def test_operation_rejects_whitespace_only_name():
    with pytest.raises(ValueError):
        Operation(name="   ", target=_target(), safety_class=SafetyClass.READ_ONLY)


def test_operation_rejects_invalid_safety_class():
    with pytest.raises(ValueError):
        Operation(name="a", target=_target(), safety_class="mutating")  # type: ignore[arg-type]


def test_operation_is_immutable():
    op = Operation(name="a", target=_target(), safety_class=SafetyClass.READ_ONLY)
    with pytest.raises(Exception):
        op.name = "b"  # type: ignore[misc]


def test_operation_metadata_defaults_empty():
    op = Operation(name="a", target=_target(), safety_class=SafetyClass.READ_ONLY)
    assert op.metadata.values == {}


def test_operation_metadata_explicit():
    op = Operation(
        name="a",
        target=_target(),
        safety_class=SafetyClass.READ_ONLY,
        metadata=OperationMetadata(values={"requested_by": "admin"}),
    )
    assert op.metadata.values["requested_by"] == "admin"


# -- Lifecycle transitions --------------------------------------------------


def test_pending_to_running_is_legal():
    assert is_legal_transition(OperationStatus.PENDING, OperationStatus.RUNNING)


def test_running_to_succeeded_is_legal():
    assert is_legal_transition(OperationStatus.RUNNING, OperationStatus.SUCCEEDED)


def test_running_to_failed_is_legal():
    assert is_legal_transition(OperationStatus.RUNNING, OperationStatus.FAILED)


def test_pending_to_denied_is_legal():
    assert is_legal_transition(OperationStatus.PENDING, OperationStatus.DENIED)


def test_pending_to_succeeded_is_illegal():
    assert not is_legal_transition(OperationStatus.PENDING, OperationStatus.SUCCEEDED)


def test_terminal_state_has_no_legal_transitions():
    for terminal in (
        OperationStatus.SUCCEEDED,
        OperationStatus.FAILED,
        OperationStatus.CANCELLED,
        OperationStatus.DENIED,
    ):
        assert not is_legal_transition(terminal, OperationStatus.RUNNING)


def test_is_terminal():
    assert is_terminal(OperationStatus.SUCCEEDED)
    assert is_terminal(OperationStatus.FAILED)
    assert is_terminal(OperationStatus.CANCELLED)
    assert is_terminal(OperationStatus.DENIED)
    assert not is_terminal(OperationStatus.PENDING)
    assert not is_terminal(OperationStatus.RUNNING)


def test_operation_state_starts_pending():
    state = OperationState(operation_id="op-1")
    assert state.status == OperationStatus.PENDING


def test_operation_state_transition_to_legal_state():
    state = OperationState(operation_id="op-1")
    new_state = state.transition_to(OperationStatus.RUNNING)
    assert new_state.status == OperationStatus.RUNNING
    assert new_state.operation_id == "op-1"
    # original state is untouched (immutability)
    assert state.status == OperationStatus.PENDING


def test_operation_state_transition_to_illegal_state_raises():
    state = OperationState(operation_id="op-1")
    with pytest.raises(InvalidTransitionError):
        state.transition_to(OperationStatus.SUCCEEDED)


def test_full_lifecycle_success_path():
    state = OperationState(operation_id="op-1")
    state = state.transition_to(OperationStatus.RUNNING)
    state = state.transition_to(OperationStatus.SUCCEEDED)
    assert state.status == OperationStatus.SUCCEEDED
    assert is_terminal(state.status)


def test_full_lifecycle_denied_path():
    state = OperationState(operation_id="op-1")
    state = state.transition_to(OperationStatus.DENIED)
    assert state.status == OperationStatus.DENIED
    with pytest.raises(InvalidTransitionError):
        state.transition_to(OperationStatus.RUNNING)
