"""Provider registry and manager."""

import logging
from typing import Any

from backend.core.providers.interfaces import (
    BaseProvider,
    ChatProvider,
    CodeProvider,
    EmbeddingProvider,
    ImageProvider,
    ModelCapability,
    ModelInfo,
)

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Registry for AI providers."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._provider_classes: dict[str, type[BaseProvider]] = {}
        self._model_cache: dict[str, list[ModelInfo]] = {}

    def register_provider_class(
        self, provider_type: str, provider_class: type[BaseProvider]
    ) -> None:
        """Register a provider class."""
        self._provider_classes[provider_type] = provider_class
        logger.info(f"Registered provider class: {provider_type}")

    def register_provider(self, provider: BaseProvider) -> None:
        """Register a provider instance."""
        self._providers[provider.provider_name] = provider
        logger.info(f"Registered provider instance: {provider.provider_name}")

    def unregister_provider(self, provider_name: str) -> None:
        """Unregister a provider."""
        if provider_name in self._providers:
            del self._providers[provider_name]
            logger.info(f"Unregistered provider: {provider_name}")

    def get_provider(self, provider_name: str) -> BaseProvider | None:
        """Get a provider by name."""
        return self._providers.get(provider_name)

    def get_providers_by_capability(
        self, capability: ModelCapability
    ) -> list[BaseProvider]:
        """Get all providers supporting a capability."""
        return [
            p
            for p in self._providers.values()
            if capability in p.supported_capabilities
        ]

    def get_chat_providers(self) -> list[ChatProvider]:
        """Get all chat providers."""
        return [p for p in self._providers.values() if isinstance(p, ChatProvider)]

    def get_embedding_providers(self) -> list[EmbeddingProvider]:
        """Get all embedding providers."""
        return [p for p in self._providers.values() if isinstance(p, EmbeddingProvider)]

    def get_image_providers(self) -> list[ImageProvider]:
        """Get all image providers."""
        return [p for p in self._providers.values() if isinstance(p, ImageProvider)]

    def get_code_providers(self) -> list[CodeProvider]:
        """Get all code providers."""
        return [p for p in self._providers.values() if isinstance(p, CodeProvider)]

    def list_all_providers(self) -> list[BaseProvider]:
        """List all registered providers."""
        return list(self._providers.values())

    def list_provider_names(self) -> list[str]:
        """List all provider names."""
        return list(self._providers.keys())

    async def initialize_provider(
        self,
        provider_type: str,
        config: dict[str, Any],
    ) -> BaseProvider | None:
        """Initialize and register a provider from config."""
        provider_class = self._provider_classes.get(provider_type)
        if not provider_class:
            logger.error(f"Unknown provider type: {provider_type}")
            return None

        try:
            provider = provider_class(**config)
            await provider.validate_connection()
            self.register_provider(provider)
            return provider
        except Exception as e:
            logger.error(f"Failed to initialize provider {provider_type}: {e}")
            return None

    async def refresh_models(self, provider_name: str) -> list[ModelInfo]:
        """Refresh model list for a provider."""
        provider = self.get_provider(provider_name)
        if not provider:
            return []

        try:
            models = await provider.list_models()
            self._model_cache[provider_name] = models
            return models
        except Exception as e:
            logger.error(f"Failed to refresh models for {provider_name}: {e}")
            return []

    def get_cached_models(self, provider_name: str) -> list[ModelInfo]:
        """Get cached models for a provider."""
        return self._model_cache.get(provider_name, [])

    async def close_all(self) -> None:
        """Close all providers."""
        for provider in self._providers.values():
            try:
                await provider.close()
            except Exception as e:
                logger.error(f"Error closing provider {provider.provider_name}: {e}")
        self._providers.clear()


# Global provider registry
provider_registry = ProviderRegistry()
