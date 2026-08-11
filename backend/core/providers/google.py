"""Google Gemini provider implementation."""

from typing import Any

from backend.core.providers.base import HTTPProviderBase
from backend.core.providers.interfaces import (
    ChatMessage,
    ChatProvider,
    ChatResponse,
    EmbeddingProvider,
    EmbeddingResponse,
    ModelCapability,
    ModelInfo,
)


class GoogleProvider(HTTPProviderBase, ChatProvider, EmbeddingProvider):
    """Google Gemini provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key, base_url, **kwargs)
        self._provider_name = "google"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.EMBEDDING,
            ModelCapability.STREAMING,
            ModelCapability.CODE,
            ModelCapability.VISION,
        ]

    def _get_default_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
        }

    def _get_url(self, endpoint: str) -> str:
        """Get full URL with API key."""
        return f"{self.base_url}{endpoint}?key={self.api_key}"

    async def list_models(self) -> list[ModelInfo]:
        """List available Google models."""
        client = await self._get_client()
        response = await client.get(self._get_url("/models"))
        response.raise_for_status()
        data = response.json()

        models = []
        for model_data in data.get("models", []):
            model_id = model_data.get("name", "").replace("models/", "")
            capabilities = self.supported_capabilities

            if "embedding" in model_id:
                capabilities = [ModelCapability.EMBEDDING]

            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_data.get("displayName", model_id),
                    provider=self.provider_name,
                    capabilities=capabilities,
                    max_tokens=model_data.get("outputTokenLimit", 8192),
                    context_window=model_data.get("inputTokenLimit", 32768),
                    metadata=model_data,
                )
            )
        return models

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Convert messages to Gemini format."""
        gemini_messages = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else msg.role
            if role not in ("user", "model"):
                role = "user"
            gemini_messages.append(
                {
                    "role": role,
                    "parts": [{"text": msg.content}],
                }
            )
        return gemini_messages

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

        gemini_messages = self._convert_messages(messages)

        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        payload["generationConfig"].update(kwargs)

        endpoint = f"/models/{model}:generateContent"
        if stream:
            endpoint = f"/models/{model}:streamGenerateContent"

        response = await client.post(self._get_url(endpoint), json=payload)
        response.raise_for_status()
        data = response.json()

        content = ""
        if data.get("candidates"):
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        content += part["text"]

        usage = data.get("usageMetadata", {})

        return ChatResponse(
            content=content,
            model=model,
            usage={
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
            },
            finish_reason=data.get("candidates", [{}])[0].get("finishReason", "STOP"),
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

        gemini_messages = self._convert_messages(messages)

        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        payload["generationConfig"].update(kwargs)

        async with client.stream(
            "POST",
            self._get_url(f"/models/{model}:streamGenerateContent"),
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("candidates"):
                            candidate = data["candidates"][0]
                            if (
                                "content" in candidate
                                and "parts" in candidate["content"]
                            ):
                                for part in candidate["content"]["parts"]:
                                    if "text" in part:
                                        yield part["text"]
                    except json.JSONDecodeError:
                        pass

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate embeddings for texts."""
        client = await self._get_client()

        embeddings = []
        total_tokens = 0

        for text in texts:
            payload = {
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
            }

            response = await client.post(
                self._get_url(f"/models/{model}:embedContent"), json=payload
            )
            response.raise_for_status()
            data = response.json()

            if "embedding" in data and "values" in data["embedding"]:
                embeddings.append(data["embedding"]["values"])
                total_tokens += data.get("usageMetadata", {}).get("tokenCount", 0)

        return EmbeddingResponse(
            embeddings=embeddings,
            model=model,
            usage={"total_tokens": total_tokens},
        )


import json
