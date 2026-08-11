"""Provider API for plugins."""

from typing import Any

from backend.core.providers.interfaces import ModelCapability, ModelInfo
from backend.core.providers.registry import provider_registry


class ProviderAPI:
    """API for provider operations."""

    def __init__(self) -> None:
        pass

    def get_provider(self, provider_name: str) -> Any | None:
        """Get a provider by name."""
        return provider_registry.get_provider(provider_name)

    def get_all_providers(self) -> list[Any]:
        """Get all registered providers."""
        return provider_registry.list_all_providers()

    def get_provider_names(self) -> list[str]:
        """Get all provider names."""
        return provider_registry.list_provider_names()

    def get_providers_by_capability(self, capability: ModelCapability) -> list[Any]:
        """Get providers by capability."""
        return provider_registry.get_providers_by_capability(capability)

    def get_chat_providers(self) -> list[Any]:
        """Get all chat providers."""
        return provider_registry.get_chat_providers()

    def get_embedding_providers(self) -> list[Any]:
        """Get all embedding providers."""
        return provider_registry.get_embedding_providers()

    def get_image_providers(self) -> list[Any]:
        """Get all image providers."""
        return provider_registry.get_image_providers()

    def get_code_providers(self) -> list[Any]:
        """Get all code providers."""
        return provider_registry.get_code_providers()

    async def initialize_provider(self, provider_type: str, config: dict[str, Any]) -> Any | None:
        """Initialize and register a provider."""
        return await provider_registry.initialize_provider(provider_type, config)

    async def refresh_models(self, provider_name: str) -> list[ModelInfo]:
        """Refresh model list for a provider."""
        return await provider_registry.refresh_models(provider_name)

    def get_cached_models(self, provider_name: str) -> list[ModelInfo]:
        """Get cached models for a provider."""
        return provider_registry.get_cached_models(provider_name)

    async def close_all(self) -> None:
        """Close all providers."""
        await provider_registry.close_all()
