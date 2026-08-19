"""Optional adapters for Yasin ecosystem services.

These modules depend only on Yasin-Operations contracts. Target
repositories remain independent and are never imported here.
"""

from yasin_operations.adapters.ecosystem.contracts import AdapterResult, EcosystemServiceAdapter, ServiceProbe, ServiceSnapshot
from yasin_operations.adapters.ecosystem.yasin_ai import YasinAIAdapter
from yasin_operations.adapters.ecosystem.yasin_press import YasinPressAdapter
from yasin_operations.adapters.ecosystem.yasin_relay import YasinRelayAdapter

__all__ = [
    "AdapterResult",
    "EcosystemServiceAdapter",
    "ServiceProbe",
    "ServiceSnapshot",
    "YasinAIAdapter",
    "YasinPressAdapter",
    "YasinRelayAdapter",
]
