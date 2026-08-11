"""Groq provider implementation."""

from typing import Any

from backend.core.providers.base import OpenAICompatibleProvider
from backend.core.providers.interfaces import ModelCapability, ModelInfo


class GroqProvider(OpenAICompatibleProvider):
    """Groq provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.groq.com/openai/v1",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            provider_name="groq",
            default_model="mixtral-8x7b-32768",
            **kwargs,
        )

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
            ModelCapability.CODE,
        ]

    async def list_models(self) -> list[ModelInfo]:
        """List available Groq models."""
        known_models = [
            ModelInfo(
                id="mixtral-8x7b-32768",
                name="Mixtral 8x7B",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=32768,
            ),
            ModelInfo(
                id="llama2-70b-4096",
                name="Llama 2 70B",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=4096,
            ),
            ModelInfo(
                id="gemma-7b-it",
                name="Gemma 7B IT",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=8192,
            ),
            ModelInfo(
                id="llama-3.1-70b-versatile",
                name="Llama 3.1 70B",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=131072,
            ),
            ModelInfo(
                id="llama-3.1-8b-instant",
                name="Llama 3.1 8B",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=131072,
            ),
        ]
        return known_models
