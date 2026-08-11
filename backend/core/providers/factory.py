"""Provider factory for creating provider instances."""

import logging
from typing import Any

from backend.core.providers.anthropic import AnthropicProvider
from backend.core.providers.claude_cli import ClaudeCLIProvider
from backend.core.providers.deepseek import DeepSeekProvider
from backend.core.providers.google import GoogleProvider
from backend.core.providers.groq import GroqProvider
from backend.core.providers.interfaces import BaseProvider
from backend.core.providers.mock import MockProvider
from backend.core.providers.nvidia import NVIDIAProvider
from backend.core.providers.omniroute import OmniRouteProvider
from backend.core.providers.openai import OpenAIProvider
from backend.core.providers.openrouter import OpenRouterProvider
from backend.core.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating AI provider instances."""

    PROVIDER_MAP = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "nvidia": NVIDIAProvider,
        "deepseek": DeepSeekProvider,
        "groq": GroqProvider,
        "openrouter": OpenRouterProvider,
        "omniroute": OmniRouteProvider,
        "claude_cli": ClaudeCLIProvider,
        "mock": MockProvider,
    }

    @classmethod
    def register_provider_class(cls, provider_type: str, provider_class: type) -> None:
        """Register a new provider class."""
        cls.PROVIDER_MAP[provider_type] = provider_class
        provider_registry.register_provider_class(provider_type, provider_class)
        logger.info(f"Registered provider class: {provider_type}")

    @classmethod
    async def create_provider(
        cls,
        provider_type: str,
        config: dict[str, Any],
        validate: bool = True,
    ) -> BaseProvider | None:
        """Create and initialize a provider instance."""
        provider_class = cls.PROVIDER_MAP.get(provider_type)
        if not provider_class:
            logger.error(f"Unknown provider type: {provider_type}")
            return None

        try:
            provider = provider_class(**config)
            if validate:
                await provider.validate_connection()
            provider_registry.register_provider(provider)
            logger.info(f"Created and registered provider: {provider_type}")
            return provider
        except Exception as e:
            logger.error(f"Failed to create provider {provider_type}: {e}")
            return None

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Get list of supported provider types."""
        return list(cls.PROVIDER_MAP.keys())

    @classmethod
    def get_provider_class(cls, provider_type: str) -> type | None:
        """Get provider class by type."""
        return cls.PROVIDER_MAP.get(provider_type)
