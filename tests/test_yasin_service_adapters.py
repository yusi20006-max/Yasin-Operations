from yasin_operations.adapters.yasin_services.discovery import default_adapters, inspect_all
from yasin_operations.adapters.yasin_services.yasin_ai import YasinAIAdapter
from yasin_operations.adapters.yasin_services.yasinpress import YasinPressAdapter
from yasin_operations.adapters.yasin_services.yasinrelay import YasinRelayAdapter
from yasin_operations.core.operations.models import OperationTarget
from yasin_operations.safety.classification import SafetyClass
from yasin_operations.adapters.yasin_services.base import AdapterRequest


def test_default_adapters_are_optional_and_named():
    adapters = default_adapters()
    assert [a.service_id for a in adapters] == ["yasin-ai", "yasinpress", "yasinrelay"]
    assert all(a.inspect().status.value == "unavailable" for a in adapters)


def test_all_adapters_have_read_only_observation_capabilities():
    for adapter in (YasinAIAdapter(), YasinPressAdapter(), YasinRelayAdapter()):
        assert all(value is SafetyClass.READ_ONLY for value in adapter.capabilities().values())


def test_inspection_is_graceful_when_backend_missing():
    results = inspect_all(default_adapters())
    assert len(results) == 3
    assert all(item.status.value == "unavailable" for item in results)


def test_request_translation_is_typed_and_rejects_mismatch():
    adapter = YasinAIAdapter()
    request = AdapterRequest(
        operation="status",
        target=OperationTarget("service", "yasin-ai"),
        safety_class=SafetyClass.READ_ONLY,
    )
    operation = adapter.build_operation(request)
    assert operation.name == "status"
    assert operation.target.identifier == "yasin-ai"
    bad = adapter.build_operation(AdapterRequest(
        operation="status",
        target=OperationTarget("service", "yasin-ai"),
        safety_class=SafetyClass.MUTATING,
    ))
    assert not bad.success
    assert bad.error.category.value == "validation_error"
