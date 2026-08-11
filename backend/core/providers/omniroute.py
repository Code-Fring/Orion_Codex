"""OmniRoute provider implementation."""

from typing import Any

from backend.core.providers.base import OpenAICompatibleProvider
from backend.core.providers.interfaces import ModelCapability, ModelInfo


class OmniRouteProvider(OpenAICompatibleProvider):
    """OmniRoute provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.omniroute.ai/v1",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            provider_name="omniroute",
            default_model="omniroute/auto",
            **kwargs,
        )

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.STREAMING,
            ModelCapability.CODE,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
        ]

    def _get_default_headers(self) -> dict[str, str]:
        headers = super()._get_default_headers()
        headers["HTTP-Referer"] = "https://orioncodex.ai"
        headers["X-Title"] = "Orion Codex"
        return headers

    async def list_models(self) -> list[ModelInfo]:
        """List available OmniRoute models."""
        client = await self._get_client()
        response = await client.get("/models")
        response.raise_for_status()
        data = response.json()

        models = []
        for model_data in data.get("data", []):
            model_id = model_data.get("id", "")
            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_data.get("name", model_id),
                    provider=self.provider_name,
                    capabilities=self.supported_capabilities,
                    max_tokens=model_data.get("top_provider", {}).get(
                        "max_completion_tokens", 4096
                    ),
                    context_window=model_data.get("context_length", 4096),
                    pricing={
                        "prompt": model_data.get("pricing", {}).get("prompt", 0),
                        "completion": model_data.get("pricing", {}).get(
                            "completion", 0
                        ),
                    },
                    metadata=model_data,
                )
            )
        return models
