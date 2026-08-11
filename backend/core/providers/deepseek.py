"""DeepSeek provider implementation."""

from typing import Any

from backend.core.providers.base import OpenAICompatibleProvider
from backend.core.providers.interfaces import ModelCapability, ModelInfo


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            provider_name="deepseek",
            default_model="deepseek-chat",
            **kwargs,
        )

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
        ]

    async def list_models(self) -> list[ModelInfo]:
        """List available DeepSeek models."""
        known_models = [
            ModelInfo(
                id="deepseek-chat",
                name="DeepSeek Chat",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=32768,
            ),
            ModelInfo(
                id="deepseek-coder",
                name="DeepSeek Coder",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=16384,
            ),
            ModelInfo(
                id="deepseek-chat-67b",
                name="DeepSeek Chat 67B",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=32768,
            ),
        ]
        return known_models
