"""Optional YasinPress adapter; no dependency on the YasinPress repository."""
from __future__ import annotations

from yasin_operations.adapters.ecosystem.contracts import EcosystemServiceAdapter, ServiceProbe
from yasin_operations.core.execution.executor import Executor


class YasinPressAdapter(EcosystemServiceAdapter):
    service_name = "YasinPress"
    operation_prefix = "yasin_press"

    def __init__(self, probe: ServiceProbe, executor: Executor | None = None) -> None:
        super().__init__(probe, executor)
