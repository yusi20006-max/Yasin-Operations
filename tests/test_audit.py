from yasin_operations.core.operations.models import OperationStatus, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError
from yasin_operations.logging.audit import AuditRecord, InMemoryAuditRecorder


def _target():
    return OperationTarget(kind="service", identifier="x")


def test_audit_record_construction():
    record = AuditRecord(
        operation_id="op-1",
        operation_name="check_health",
        target=_target(),
        status=OperationStatus.SUCCEEDED,
    )
    assert record.operation_id == "op-1"
    assert record.status == OperationStatus.SUCCEEDED
    assert record.timestamp is not None
    assert record.error is None
    assert record.metadata == {}


def test_audit_record_with_error():
    err = OperationError(category=ErrorCategory.EXECUTION_FAILURE, message="failed")
    record = AuditRecord(
        operation_id="op-1",
        operation_name="do_thing",
        target=_target(),
        status=OperationStatus.FAILED,
        error=err,
    )
    assert record.error is err


def test_in_memory_recorder_records_entries():
    recorder = InMemoryAuditRecorder()
    record = AuditRecord(
        operation_id="op-1",
        operation_name="check_health",
        target=_target(),
        status=OperationStatus.SUCCEEDED,
    )
    recorder.record(record)
    assert len(recorder.entries) == 1
    assert recorder.entries[0] is record


def test_in_memory_recorder_starts_empty():
    recorder = InMemoryAuditRecorder()
    assert recorder.entries == []


def test_in_memory_recorder_preserves_order():
    recorder = InMemoryAuditRecorder()
    for i in range(3):
        recorder.record(
            AuditRecord(
                operation_id=f"op-{i}",
                operation_name="do_thing",
                target=_target(),
                status=OperationStatus.SUCCEEDED,
            )
        )
    assert [e.operation_id for e in recorder.entries] == ["op-0", "op-1", "op-2"]
