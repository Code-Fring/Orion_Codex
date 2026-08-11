"""OpenRouter AI Provider Plugin."""

import logging
from typing import Any

from backend.plugins.sdk.base import AIProviderPlugin, PluginContext, PluginManifest
from backend.core.providers.interfaces import (
    BaseProvider,
    ChatProvider,
    ModelCapability,
    ModelInfo,
    ChatMessage,
    ChatResponse,
    EmbeddingProvider,
    EmbeddingResponse,
)

logger = logging.getLogger(__name__)


class OpenRouterProvider(ChatProvider, EmbeddingProvider):
    """OpenRouter provider implementation."""

    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._session = None

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.REASONING,
            ModelCapability.CODE,
        ]

    async def _get_session(self):
        import aiohttp
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self._api_key}"}
            )
        return self._session

    async def list_models(self) -> list[ModelInfo]:
        """List available models from OpenRouter."""
        session = await self._get_session()
        async with session.get(f"{self._base_url}/models") as resp:
            data = await resp.json()
            models = []
            for m in data.get("data", []):
                models.append(ModelInfo(
                    id=m["id"],
                    name=m.get("name", m["id"]),
                    provider="openrouter",
                    capabilities=self.supported_capabilities,
                    max_tokens=m.get("context_length", 4096),
                    context_window=m.get("context_length", 4096),
                    pricing=m.get("pricing"),
                ))
            return models

    async def validate_connection(self) -> bool:
        """Validate OpenRouter connection."""
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception:
            return False

    async def close(self) -> None:
        """Close provider connections."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate a chat completion."""
        session = await self._get_session()

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with session.post(f"{self._base_url}/chat/completions", json=payload) as resp:
            data = await resp.json()
            choice = data["choices"][0]
            return ChatResponse(
                content=choice["message"]["content"],
                model=data["model"],
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", "stop"),
            )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        """Generate a streaming chat completion."""
        session = await self._get_session()

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with session.post(f"{self._base_url}/chat/completions", json=payload) as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        pass

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate embeddings."""
        session = await self._get_session()

        payload = {
            "model": model,
            "input": texts,
        }

        async with session.post(f"{self._base_url}/embeddings", json=payload) as resp:
            data = await resp.json()
            return EmbeddingResponse(
                embeddings=[d["embedding"] for d in data["data"]],
                model=data["model"],
                usage=data.get("usage", {}),
            )


class OpenRouterProviderPlugin(AIProviderPlugin):
    """OpenRouter Provider Plugin."""

    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        super().__init__(manifest, context)
        self._provider: OpenRouterProvider | None = None

    async def _on_initialize(self) -> None:
        """Initialize the provider."""
        api_key = self.get_config("api_key")
        base_url = self.get_config("base_url", "https://openrouter.ai/api/v1")

        if not api_key:
            raise ValueError("OpenRouter API key is required")

        self._provider = OpenRouterProvider(api_key, base_url)

        # Validate connection
        if not await self._provider.validate_connection():
            logger.warning("OpenRouter connection validation failed")

    async def _on_shutdown(self) -> None:
        """Shutdown the provider."""
        if self._provider:
            await self._provider.close()
            self._provider = None

    async def get_provider(self) -> OpenRouterProvider:
        """Get the provider instance."""
        if not self._provider:
            await self._on_initialize()
        return self._provider

    async def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        if not self._provider:
            await self._on_initialize()
        models = await self._provider.list_models()
        return [
            {
                "id": m.id,
                "name": m.name,
                "provider": m.provider,
                "capabilities": [c.value for c in m.capabilities],
                "max_tokens": m.max_tokens,
                "context_window": m.context_window,
            }
            for m in models
        ]

    async def validate_connection(self) -> bool:
        """Validate provider connection."""
        if not self._provider:
            await self._on_initialize()
        return await self._provider.validate_connection()