"""Discovery helpers for optional Yasin service adapters."""
from __future__ import annotations

from typing import Iterable, Optional

from yasin_operations.runtime.service import ServiceBackend

from .base import EcosystemAdapter, EcosystemService
from .yasin_ai import YasinAIAdapter
from .yasinpress import YasinPressAdapter
from .yasinrelay import YasinRelayAdapter


def default_adapters(backend: Optional[ServiceBackend] = None) -> tuple[EcosystemAdapter, ...]:
    return (
        YasinAIAdapter(backend),
        YasinPressAdapter(backend),
        YasinRelayAdapter(backend),
    )


def inspect_all(adapters: Iterable[EcosystemAdapter]) -> tuple[EcosystemService, ...]:
    return tuple(adapter.inspect() for adapter in adapters)
