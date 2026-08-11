"""NVIDIA Nemotron provider implementation."""

from typing import Any

from backend.core.providers.base import OpenAICompatibleProvider
from backend.core.providers.interfaces import (
    ModelCapability,
    ModelInfo,
)


class NVIDIAProvider(OpenAICompatibleProvider):
    """NVIDIA Nemotron provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            provider_name="nvidia",
            default_model="nemotron-3-ultra",
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
        """List available NVIDIA models."""
        known_models = [
            ModelInfo(
                id="nemotron-3-ultra",
                name="Nemotron 3 Ultra",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=8192,
            ),
            ModelInfo(
                id="nemotron-3-ultra-chat",
                name="Nemotron 3 Ultra Chat",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=8192,
            ),
            ModelInfo(
                id="nemotron-4-340b",
                name="Nemotron 4 340B",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=32768,
            ),
            ModelInfo(
                id="nvidia/nemotron-3-ultra",
                name="Nemotron 3 Ultra (NGC)",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=8192,
            ),
        ]
        return known_models
