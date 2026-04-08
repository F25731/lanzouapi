from __future__ import annotations

from typing import Dict

from app.providers.base import SourceProvider
from app.providers.lanzou_http import LanzouHttpProvider
from app.providers.mock_provider import MockSourceProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: Dict[str, SourceProvider] = {}

    def register(self, provider: SourceProvider) -> None:
        self._providers[provider.adapter_type] = provider

    def get(self, adapter_type: str) -> SourceProvider:
        provider = self._providers.get(adapter_type)
        if provider is None:
            raise ValueError(f"unsupported source adapter: {adapter_type}")
        return provider


provider_registry = ProviderRegistry()
provider_registry.register(MockSourceProvider())
provider_registry.register(LanzouHttpProvider())
