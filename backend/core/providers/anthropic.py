"""Anthropic provider implementation."""

import json
from typing import Any

from backend.core.providers.base import HTTPProviderBase
from backend.core.providers.interfaces import (
    ChatMessage,
    ChatProvider,
    ChatResponse,
    ModelCapability,
    ModelInfo,
)


class AnthropicProvider(HTTPProviderBase, ChatProvider):
    """Anthropic provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key, base_url, **kwargs)
        self._provider_name = "anthropic"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
            ModelCapability.CODE,
            ModelCapability.VISION,
        ]

    def _get_default_headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[ModelInfo]:
        """List available Anthropic models."""
        # Anthropic doesn't have a models endpoint, return known models
        known_models = [
            ModelInfo(
                id="claude-3-opus-20240229",
                name="Claude 3 Opus",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-2.1",
                name="Claude 2.1",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-2.0",
                name="Claude 2.0",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=100000,
            ),
            ModelInfo(
                id="claude-instant-1.2",
                name="Claude Instant 1.2",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=100000,
            ),
        ]
        return known_models

    def _convert_messages(
        self, messages: list[ChatMessage]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Convert messages to Anthropic format."""
        system_prompt = ""
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                anthropic_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return system_prompt, anthropic_messages

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
        client = await self._get_client()

        system_prompt, anthropic_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "stream": stream,
        }

        if system_prompt:
            payload["system"] = system_prompt
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = 4096

        payload.update(kwargs)

        response = await client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        content = ""
        for block in data.get("content", []):
            if block["type"] == "text":
                content += block["text"]

        return ChatResponse(
            content=content,
            model=data["model"],
            usage={
                "input_tokens": data["usage"]["input_tokens"],
                "output_tokens": data["usage"]["output_tokens"],
            },
            finish_reason=data.get("stop_reason", "end_turn"),
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
        client = await self._get_client()

        system_prompt, anthropic_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "stream": True,
        }

        if system_prompt:
            payload["system"] = system_prompt
        if max_tokens:
            payload["max_tokens"] = max_tokens
        else:
            payload["max_tokens"] = 4096

        payload.update(kwargs)

        async with client.stream("POST", "/v1/messages", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                    except json.JSONDecodeError:
                        pass
