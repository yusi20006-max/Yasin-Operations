"""Optional Yasin-AI adapter; no dependency on the Yasin-AI repository."""
from __future__ import annotations

from yasin_operations.adapters.ecosystem.contracts import EcosystemServiceAdapter, ServiceProbe
from yasin_operations.core.execution.executor import Executor


class YasinAIAdapter(EcosystemServiceAdapter):
    service_name = "Yasin-AI"
    operation_prefix = "yasin_ai"

    def __init__(self, probe: ServiceProbe, executor: Executor | None = None) -> None:
        super().__init__(probe, executor)
