"""Optional Hermes-facing adapter.

This package intentionally contains no Hermes imports. It exposes a
transport-neutral contract that an external Hermes client can bind to.
"""

from yasin_operations.adapters.hermes.adapter import HermesOperationsAdapter
from yasin_operations.adapters.hermes.contracts import HermesOperationRequest, HermesOperationResponse

__all__ = ["HermesOperationRequest", "HermesOperationResponse", "HermesOperationsAdapter"]
