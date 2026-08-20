"""Adversarial contract tests for ecosystem adapters."""
from __future__ import annotations

import pytest

from yasin_operations.adapters.ecosystem import ServiceSnapshot, YasinAIAdapter, YasinPressAdapter, YasinRelayAdapter
from yasin_operations.adapters.ecosystem.contracts import ADAPTER_CONTRACT_VERSION
from yasin_operations.core.results.models import ErrorCategory


class Probe:
    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def inspect(self, service_name):
        if self.error:
            raise self.error
        return self.value


def test_snapshot_rejects_duplicate_or_unsorted_capabilities():
    with pytest.raises(ValueError, match="unique"):
        ServiceSnapshot("Yasin-AI", True, capabilities=("health", "health"))
    with pytest.raises(ValueError, match="ordered"):
        ServiceSnapshot("Yasin-AI", True, capabilities=("version", "health"))


def test_snapshot_rejects_invalid_version_and_state():
    with pytest.raises(ValueError, match="version"):
        ServiceSnapshot("Yasin-AI", True, version="latest")
    with pytest.raises(ValueError, match="state"):
        ServiceSnapshot("Yasin-AI", True, state="mystery")


def test_snapshot_serializes_contract_version():
    snapshot = ServiceSnapshot("Yasin-AI", True, capabilities=("health", "version"))
    assert snapshot.contract_version == ADAPTER_CONTRACT_VERSION
    assert snapshot.as_dict()["contract_version"] == ADAPTER_CONTRACT_VERSION


def test_mismatched_contract_version_fails_closed():
    snapshot = ServiceSnapshot("Yasin-AI", False, state="failed", error="bad contract", contract_version="2.0")
    result = YasinAIAdapter(Probe(snapshot)).inspect_result()
    assert not result.success
    assert result.error["category"] == ErrorCategory.UNAVAILABLE_DEPENDENCY.value


def test_malformed_probe_payload_isolated():
    result = YasinPressAdapter(Probe(object())).inspect_result()
    assert not result.success
    assert result.error["category"] == ErrorCategory.INTERNAL_ERROR.value or result.error["category"] == ErrorCategory.VALIDATION_ERROR.value
    assert result.data["service"] == "YasinPress"


def test_probe_exception_does_not_leak_exception_text():
    result = YasinRelayAdapter(Probe(error=RuntimeError("secret backend detail"))).inspect_result()
    assert not result.success
    assert "secret backend detail" not in result.error["message"]


def test_build_operation_rejects_invalid_target_and_parameters():
    adapter = YasinAIAdapter(Probe(ServiceSnapshot("Yasin-AI", True)))
    result = adapter.execute("yasin_ai_health", target_identifier="")
    assert not result.success
    assert result.error["category"] == ErrorCategory.VALIDATION_ERROR.value
    result = adapter.execute("yasin_ai_health", parameters=["bad"])
    assert not result.success
    assert result.error["category"] == ErrorCategory.VALIDATION_ERROR.value
