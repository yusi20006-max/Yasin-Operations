import pytest

from yasin_operations.core.results.models import (
    ErrorCategory,
    OperationError,
    OperationResult,
)


def test_operation_error_construction():
    err = OperationError(
        category=ErrorCategory.VALIDATION_ERROR,
        message="bad input",
    )
    assert err.category == ErrorCategory.VALIDATION_ERROR
    assert err.message == "bad input"
    assert err.details == {}


def test_operation_error_rejects_empty_message():
    with pytest.raises(ValueError):
        OperationError(category=ErrorCategory.VALIDATION_ERROR, message="")


def test_operation_error_rejects_invalid_category():
    with pytest.raises(ValueError):
        OperationError(category="validation_error", message="x")  # type: ignore[arg-type]


def test_operation_error_with_details():
    err = OperationError(
        category=ErrorCategory.TIMEOUT,
        message="timed out",
        details={"seconds": 30},
    )
    assert err.details["seconds"] == 30


def test_result_ok_factory():
    result = OperationResult.ok("op-1", data={"count": 3})
    assert result.success is True
    assert result.error is None
    assert result.data == {"count": 3}
    assert result.operation_id == "op-1"


def test_result_ok_factory_defaults_empty_data():
    result = OperationResult.ok("op-1")
    assert result.data == {}


def test_result_fail_factory():
    err = OperationError(category=ErrorCategory.EXECUTION_FAILURE, message="boom")
    result = OperationResult.fail("op-1", err)
    assert result.success is False
    assert result.error is err
    assert result.data is None


def test_result_rejects_success_with_error():
    err = OperationError(category=ErrorCategory.EXECUTION_FAILURE, message="boom")
    with pytest.raises(ValueError):
        OperationResult(operation_id="op-1", success=True, error=err)


def test_result_rejects_failure_without_error():
    with pytest.raises(ValueError):
        OperationResult(operation_id="op-1", success=False, error=None)


def test_all_error_categories_are_distinct_values():
    values = [c.value for c in ErrorCategory]
    assert len(values) == len(set(values))
