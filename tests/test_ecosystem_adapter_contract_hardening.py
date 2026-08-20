"""Adversarial ecosystem adapter contract tests."""
from __future__ import annotations

import pytest

from yasin_operations.adapters.ecosystem import YasinAIAdapter, YasinPressAdapter, YasinRelayAdapter
from yasin_operations.adapters.ecosystem.contracts import CONTRACT_VERSION, ServiceSnapshot
from yasin_operations.core.results.models import ErrorCategory, OperationError, OperationResult


class Probe:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def inspect(self, service_name):
        if self.error:
            raise self.error
        return self.value


class ExplodingExecutor:
    def execute(self, operation, **kwargs):
        raise RuntimeError("executor boundary exploded")


def snapshot(name: str, **kwargs):
    return ServiceSnapshot(service=name, available=True, state="running", **kwargs)


def test_snapshot_contract_is_versioned_and_deterministic():
    value = ServiceSnapshot(service="Yasin-AI", available=True, state="running", capabilities=("health", "status"))
    data = value.as_dict()
    assert data["contract_version"] == CONTRACT_VERSION
    assert data["capabilities"] == ["health", "status"]


def test_snapshot_rejects_unsorted_or_duplicate_capabilities():
    with pytest.raises(ValueError):
        ServiceSnapshot(service="Yasin-AI", available=True, capabilities=("status", "health"))
    with pytest.raises(ValueError):
        ServiceSnapshot(service="Yasin-AI", available=True, capabilities=("health", "health"))


def test_snapshot_rejects_unknown_state_and_contract_version():
    with pytest.raises(ValueError):
        ServiceSnapshot(service="Yasin-AI", available=True, state="provider_magic")
    with pytest.raises(ValueError):
        ServiceSnapshot(service="Yasin-AI", available=True, contract_version=999)


def test_wrong_probe_identity_isolated_to_one_adapter():
    adapter = YasinAIAdapter(Probe(snapshot("YasinPress")))
    result = adapter.inspect_result()
    assert not result.success
    assert result.error["category"] == ErrorCategory.UNAVAILABLE_DEPENDENCY.value
    assert result.data["service"] == "Yasin-AI"


def test_probe_timeout_is_structured():
    adapter = YasinPressAdapter(Probe(error=TimeoutError("probe timeout")))
    result = adapter.inspect_result()
    assert not result.success
    assert result.data["state"] == "unavailable"
    assert result.error["category"] == ErrorCategory.UNAVAILABLE_DEPENDENCY.value


def test_malformed_probe_return_is_failure_not_core_leak():
    adapter = YasinRelayAdapter(Probe(value={"service": "YasinRelay"}))
    result = adapter.inspect_result()
    assert not result.success
    assert result.data["state"] == "failed"
    assert result.error["category"] == ErrorCategory.UNAVAILABLE_DEPENDENCY.value


def test_executor_exception_is_normalized_at_adapter_boundary():
    adapter = YasinAIAdapter(Probe(snapshot("Yasin-AI")), ExplodingExecutor())
    result = adapter.execute("yasin_ai_health")
    assert not result.success
    assert result.error["category"] == ErrorCategory.INTERNAL_ERROR.value
    assert "exploded" in result.error["message"]


def test_each_adapter_keeps_own_contract_and_operation_namespace():
    adapters = [YasinAIAdapter, YasinPressAdapter, YasinRelayAdapter]
    prefixes = ["yasin_ai_", "yasin_press_", "yasin_relay_"]
    for adapter_cls, prefix in zip(adapters, prefixes):
        adapter = adapter_cls(Probe(snapshot(adapter_cls.service_name)))
        assert adapter.contract_version == CONTRACT_VERSION
        assert adapter.supported_operations
        assert all(name.startswith(prefix) for name in adapter.supported_operations)
        assert len(adapter.supported_operations) == len(set(adapter.supported_operations))


def test_unavailable_probe_does_not_change_other_adapter_behavior():
    failed = YasinAIAdapter(Probe(error=ConnectionError("AI down"))).inspect_result()
    healthy = YasinPressAdapter(Probe(snapshot("YasinPress", capabilities=("health",)))).inspect_result()
    assert not failed.success
    assert healthy.success
    assert healthy.data["service"] == "YasinPress"
