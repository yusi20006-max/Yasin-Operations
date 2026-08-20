import pytest
from datetime import datetime, timezone

from yasin_operations.core.operations.models import OperationStatus, OperationTarget
from yasin_operations.core.results.models import ErrorCategory, OperationError
from yasin_operations.logging.audit import AuditRecord, InMemoryAuditRecorder


def _record(operation_id="op-1", **kwargs):
    values = {
        "operation_id": operation_id,
        "operation_name": "status",
        "target": OperationTarget(kind="service", identifier="demo"),
        "status": OperationStatus.SUCCEEDED,
        "timestamp": datetime.now(timezone.utc),
        "actor": "operator",
        "source": "cli",
        "correlation_id": "corr-1",
        "duration_ms": 4.2,
    }
    values.update(kwargs)
    return AuditRecord(**values)


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


def test_sensitive_metadata_is_redacted():
    entry = _record(
        metadata={
            "api_key": "super-secret-key",
            "password": "hunter2",
            "nested": {"authorization": "Bearer very-secret", "safe": "value"},
        }
    )
    assert entry.metadata["api_key"] == "<redacted>"
    assert entry.metadata["password"] == "<redacted>"
    assert entry.metadata["nested"]["authorization"] == "<redacted>"
    assert entry.metadata["nested"]["safe"] == "value"


def test_error_details_are_redacted():
    error = OperationError(
        category=ErrorCategory.INTERNAL_ERROR,
        message="operation failed token=super-secret",
        details={"credential": "secret-value", "attempt": 1},
    )
    entry = _record(error=error)
    assert "super-secret" not in entry.error.message
    assert entry.error.details["credential"] == "<redacted>"
    assert entry.error.details["attempt"] == 1


def test_audit_record_rejects_ambiguous_identity_and_status_types():
    with pytest.raises(ValueError):
        _record(actor=123)
    with pytest.raises(ValueError):
        _record(source=123)
    with pytest.raises(ValueError):
        _record(correlation_id=123)
    with pytest.raises(ValueError):
        _record(status="succeeded")
    with pytest.raises(ValueError):
        _record(dry_run=1)


def test_audit_text_is_bounded():
    entry = _record(metadata={"message": "x" * 5000})
    assert len(entry.metadata["message"]) <= 2048 + 1
