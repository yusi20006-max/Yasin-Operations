"""Optional adapter for YasinPress."""
from __future__ import annotations

from typing import Optional

from yasin_operations.runtime.service import ServiceBackend
from yasin_operations.safety.classification import SafetyClass

from .adapter import YasinServiceAdapter


class YasinPressAdapter(YasinServiceAdapter):
    def __init__(self, backend: Optional[ServiceBackend] = None, version: Optional[str] = None) -> None:
        super().__init__("yasinpress", "YasinPress", backend, version, {
            "status": SafetyClass.READ_ONLY,
            "health": SafetyClass.READ_ONLY,
            "version": SafetyClass.READ_ONLY,
            "diagnostics": SafetyClass.READ_ONLY,
        })
