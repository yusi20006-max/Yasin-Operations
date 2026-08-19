"""Optional YasinRelay adapter; no dependency on the YasinRelay repository."""
from __future__ import annotations

from yasin_operations.adapters.ecosystem.contracts import EcosystemServiceAdapter, ServiceProbe
from yasin_operations.core.execution.executor import Executor


class YasinRelayAdapter(EcosystemServiceAdapter):
    service_name = "YasinRelay"
    operation_prefix = "yasin_relay"

    def __init__(self, probe: ServiceProbe, executor: Executor | None = None) -> None:
        super().__init__(probe, executor)
