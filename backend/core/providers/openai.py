"""OpenAI provider implementation."""

from typing import Any

from backend.core.providers.base import OpenAICompatibleProvider
from backend.core.providers.interfaces import (
    ChatMessage,
    ChatResponse,
    ModelCapability,
    ModelInfo,
)


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            provider_name="openai",
            default_model="gpt-4-turbo-preview",
            **kwargs,
        )

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.EMBEDDING,
            ModelCapability.IMAGE,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
            ModelCapability.CODE,
        ]

    async def list_models(self) -> list[ModelInfo]:
        """List available OpenAI models."""
        models = await super().list_models()

        # Add known model information
        model_info = {
            "gpt-4-turbo-preview": {"max_tokens": 4096, "context_window": 128000},
            "gpt-4": {"max_tokens": 8192, "context_window": 8192},
            "gpt-4-32k": {"max_tokens": 8192, "context_window": 32768},
            "gpt-3.5-turbo": {"max_tokens": 4096, "context_window": 16385},
            "gpt-3.5-turbo-16k": {"max_tokens": 4096, "context_window": 16385},
            "gpt-4o": {"max_tokens": 4096, "context_window": 128000},
            "gpt-4o-mini": {"max_tokens": 16384, "context_window": 128000},
            "o1-preview": {"max_tokens": 32768, "context_window": 128000},
            "o1-mini": {"max_tokens": 65536, "context_window": 128000},
            "text-embedding-3-small": {"max_tokens": 8191, "context_window": 8191},
            "text-embedding-3-large": {"max_tokens": 8191, "context_window": 8191},
            "text-embedding-ada-002": {"max_tokens": 8191, "context_window": 8191},
            "dall-e-3": {"max_tokens": 0, "context_window": 0},
            "dall-e-2": {"max_tokens": 0, "context_window": 0},
        }

        for model in models:
            info = model_info.get(model.id, {})
            model.max_tokens = info.get("max_tokens", model.max_tokens)
            model.context_window = info.get("context_window", model.context_window)

            # Update capabilities based on model type
            if "embedding" in model.id:
                model.capabilities = [ModelCapability.EMBEDDING]
            elif "dall-e" in model.id:
                model.capabilities = [ModelCapability.IMAGE]
            else:
                model.capabilities = self.supported_capabilities

        return models

    async def responses(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate a response using OpenAI Responses API."""

        payload = {
            "model": model,
            "input": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["max_output_tokens"] = max_tokens

        payload.update(kwargs)

        if stream:
            return await self._responses_stream_collect(
                messages, model, temperature, max_tokens, **kwargs
            )

        response = await self._request_with_retry("POST", "/responses", payload)
        data = response.json()

        content = ""
        if data.get("output"):
            for item in data["output"]:
                if item.get("type") == "message":
                    for content_item in item.get("content", []):
                        if content_item.get("type") == "output_text":
                            content += content_item.get("text", "")

        usage = data.get("usage", {})

        return ChatResponse(
            content=content,
            model=data.get("model", model),
            usage={
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
            },
            finish_reason=data.get("status", "completed"),
        )

    async def _responses_stream_collect(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Collect streaming response from Responses API into a full ChatResponse."""
        payload = {
            "model": model,
            "input": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        payload.update(kwargs)

        client = await self._get_client()

        self._log_request("POST", "/responses", payload, self._get_default_headers())

        full_content = ""
        finish_reason = "completed"
        usage = {}
        model_name = model

        try:
            async with client.stream("POST", "/responses", json=payload) as response:
                response.raise_for_status()
                start_time = time.time()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        self._log_streaming_event("chunk", data_str)

                        try:
                            chunk_data = json.loads(data_str)
                            if chunk_data.get("output"):
                                for item in chunk_data["output"]:
                                    if item.get("type") == "message":
                                        for content_item in item.get("content", []):
                                            if (
                                                content_item.get("type")
                                                == "output_text"
                                            ):
                                                full_content += content_item.get(
                                                    "text", ""
                                                )
                            if "usage" in chunk_data:
                                usage = chunk_data["usage"]
                            if "status" in chunk_data:
                                finish_reason = chunk_data["status"]
                        except json.JSONDecodeError:
                            pass

                elapsed = time.time() - start_time
                self._log_response(200, {}, {"content": full_content}, elapsed)

        except Exception as e:
            DEBUG_LOG.error(
                f"Responses API streaming failed: {e}, falling back to non-streaming"
            )
            return await self.responses(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )

        return ChatResponse(
            content=full_content,
            model=model_name,
            usage=usage,
            finish_reason=finish_reason,
            tool_calls=None,
        )

    async def responses_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        """Generate a streaming response using OpenAI Responses API."""
        payload = {
            "model": model,
            "input": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        payload.update(kwargs)

        client = await self._get_client()

        self._log_request("POST", "/responses", payload, self._get_default_headers())

        try:
            async with client.stream("POST", "/responses", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break

                        self._log_streaming_event("chunk", data_str)
                        yield data_str

        except httpx.TimeoutException as e:
            DEBUG_LOG.error(f"STREAM_READINESS_TIMEOUT: {e}")
            self._log_streaming_event("error", f"STREAM_READINESS_TIMEOUT: {e}")
            # Fall back to non-streaming
            DEBUG_LOG.info("Falling back to non-streaming mode")
            response = await self.responses(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )
            yield f"data: {json.dumps({'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': response.content}]}]})}\n\n"
            yield "data: [DONE]\n\n"

        except httpx.RemoteProtocolError as e:
            DEBUG_LOG.error(f"STREAM_EARLY_EOF: {e}")
            self._log_streaming_event("error", f"STREAM_EARLY_EOF: {e}")
            # Fall back to non-streaming
            DEBUG_LOG.info("Falling back to non-streaming mode")
            response = await self.responses(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )
            yield f"data: {json.dumps({'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': response.content}]}]})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            DEBUG_LOG.error(f"Responses API streaming error: {e}")
            self._log_streaming_event("error", f"Responses API streaming error: {e}")
            # Fall back to non-streaming
            DEBUG_LOG.info("Falling back to non-streaming mode")
            response = await self.responses(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )
            yield f"data: {json.dumps({'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': response.content}]}]})}\n\n"
            yield "data: [DONE]\n\n"


import json
import time

import httpx

from backend.core.providers.base import DEBUG_LOG
