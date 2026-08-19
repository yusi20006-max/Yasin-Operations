from datetime import datetime, timezone

from yasin_operations.core.operations.models import OperationStatus, OperationTarget
from yasin_operations.logging.audit import AuditRecord, InMemoryAuditRecorder


def _record(operation_id="op-1"):
    return AuditRecord(
        operation_id=operation_id,
        operation_name="status",
        target=OperationTarget(kind="service", identifier="demo"),
        status=OperationStatus.SUCCEEDED,
        timestamp=datetime.now(timezone.utc),
        actor="operator",
        source="cli",
        correlation_id="corr-1",
        duration_ms=4.2,
    )


def test_audit_record_carries_required_attribution_fields():
    entry = _record()
    assert entry.operation_id == "op-1"
    assert entry.target.identifier == "demo"
    assert entry.actor == "operator"
    assert entry.source == "cli"
    assert entry.correlation_id == "corr-1"
    assert entry.duration_ms == 4.2


def test_in_memory_recorder_returns_isolated_snapshots():
    recorder = InMemoryAuditRecorder()
    recorder.record(_record())
    recorder.record(_record("op-2"))

    snapshot = recorder.entries
    snapshot.clear()
    assert len(recorder.entries) == 2
    assert len(recorder.for_operation("op-1")) == 1

    recorder.clear()
    assert recorder.entries == []
