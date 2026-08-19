from yasin_operations.core.operations.models import Operation, OperationTarget
from yasin_operations.safety.classification import SafetyClass


def test_safety_class_has_read_only_and_mutating():
    assert SafetyClass.READ_ONLY.value == "read_only"
    assert SafetyClass.MUTATING.value == "mutating"


def test_read_only_operation_classification():
    op = Operation(
        name="check_status",
        target=OperationTarget(kind="service", identifier="x"),
        safety_class=SafetyClass.READ_ONLY,
    )
    assert op.safety_class == SafetyClass.READ_ONLY


def test_mutating_operation_classification():
    op = Operation(
        name="restart_service",
        target=OperationTarget(kind="service", identifier="x"),
        safety_class=SafetyClass.MUTATING,
    )
    assert op.safety_class == SafetyClass.MUTATING


def test_safety_classes_are_distinct():
    assert SafetyClass.READ_ONLY != SafetyClass.MUTATING
