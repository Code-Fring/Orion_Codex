"""Base provider implementation with common functionality."""

import asyncio
import json
import logging
import time
from abc import ABC
from typing import Any

import httpx
from backend.core.providers.interfaces import (
    BaseProvider,
    ChatMessage,
    ChatProvider,
    ChatResponse,
    EmbeddingProvider,
    EmbeddingResponse,
    ModelCapability,
    ModelInfo,
)

logger = logging.getLogger(__name__)

# Debug logging
DEBUG_LOG = logging.getLogger("orion.providers.debug")
DEBUG_LOG.setLevel(logging.DEBUG)

# Console handler for debug output
if not DEBUG_LOG.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[DEBUG %(asctime)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    DEBUG_LOG.addHandler(console_handler)
    DEBUG_LOG.propagate = False


class HTTPProviderBase(BaseProvider, ABC):
    """Base class for HTTP-based providers."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs: Any,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _log_request(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        """Log request details."""
        DEBUG_LOG.debug("=== REQUEST ===")
        DEBUG_LOG.debug(f"Provider: {self.provider_name}")
        DEBUG_LOG.debug(f"Method: {method}")
        DEBUG_LOG.debug(f"URL: {self.base_url}{endpoint}")
        DEBUG_LOG.debug(
            f"Headers: {json.dumps({k: v for k, v in headers.items() if 'authorization' not in k.lower()}, indent=2)}"
        )
        DEBUG_LOG.debug(f"Payload: {json.dumps(payload, indent=2)}")

    def _log_response(
        self,
        status_code: int,
        headers: dict[str, str],
        body: Any,
        elapsed: float,
    ) -> None:
        """Log response details."""
        DEBUG_LOG.debug("=== RESPONSE ===")
        DEBUG_LOG.debug(f"Status: {status_code}")
        DEBUG_LOG.debug(f"Elapsed: {elapsed:.3f}s")
        DEBUG_LOG.debug(f"Headers: {json.dumps(dict(headers), indent=2)}")
        if isinstance(body, (dict, list)):
            DEBUG_LOG.debug(f"Body: {json.dumps(body, indent=2)}")
        else:
            DEBUG_LOG.debug(f"Body: {body}")

    def _log_streaming_event(self, event_type: str, data: str) -> None:
        """Log streaming events."""
        DEBUG_LOG.debug(f"=== STREAM EVENT: {event_type} ===")
        DEBUG_LOG.debug(f"Data: {data[:500]}{'...' if len(data) > 500 else ''}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._get_default_headers(),
            )
        return self._client

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        payload: dict[str, Any],
        stream: bool = False,
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        client = await self._get_client()
        headers = self._get_default_headers()

        self._log_request(method, endpoint, payload, headers)

        # For GET requests, use query parameters instead of JSON body
        request_kwargs = {"headers": headers}
        if method.upper() == "GET":
            request_kwargs["params"] = payload
        else:
            request_kwargs["json"] = payload

        last_exception = None
        for attempt in range(self.max_retries + 1):
            try:
                start_time = time.time()

                if stream:
                    response = await client.stream(method, endpoint, **request_kwargs)
                else:
                    response = await client.request(method, endpoint, **request_kwargs)

                elapsed = time.time() - start_time

                # Read response body for non-streaming
                if not stream:
                    body = (
                        response.json()
                        if response.headers.get("content-type", "").startswith(
                            "application/json"
                        )
                        else response.text
                    )
                    self._log_response(
                        response.status_code, response.headers, body, elapsed
                    )

                response.raise_for_status()

                if attempt > 0:
                    logger.info(f"Request succeeded on retry attempt {attempt}")

                return response

            except httpx.TimeoutException as e:
                last_exception = e
                elapsed = time.time() - start_time if "start_time" in locals() else 0
                DEBUG_LOG.warning(
                    f"Timeout on attempt {attempt + 1}/{self.max_retries + 1} after {elapsed:.3f}s: {e}"
                )

            except httpx.HTTPStatusError as e:
                elapsed = time.time() - start_time if "start_time" in locals() else 0
                body = e.response.text if e.response else "No response"
                DEBUG_LOG.error(
                    f"HTTP error on attempt {attempt + 1}/{self.max_retries + 1}: {e.response.status_code} - {body}"
                )
                last_exception = e

                # Don't retry on client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise

            except httpx.RequestError as e:
                elapsed = time.time() - start_time if "start_time" in locals() else 0
                DEBUG_LOG.error(
                    f"Request error on attempt {attempt + 1}/{self.max_retries + 1}: {e}"
                )
                last_exception = e

            if attempt < self.max_retries:
                wait_time = self.retry_delay * (2**attempt)  # Exponential backoff
                DEBUG_LOG.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        # All retries exhausted
        raise last_exception or Exception("Max retries exceeded")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def validate_connection(self) -> bool:
        """Validate connection by listing models."""
        try:
            await self.list_models()
            return True
        except Exception as e:
            logger.error(f"Connection validation failed for {self.provider_name}: {e}")
            return False


class OpenAICompatibleProvider(HTTPProviderBase, ChatProvider, EmbeddingProvider):
    """Base class for OpenAI-compatible providers."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        provider_name: str,
        default_model: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key, base_url, **kwargs)
        self._provider_name = provider_name
        self._default_model = default_model

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
            ModelCapability.FUNCTION_CALLING,
        ]

    async def list_models(self) -> list[ModelInfo]:
        """List available models."""
        client = await self._get_client()
        response = await self._request_with_retry("GET", "/models", {})
        data = response.json()

        models = []
        for model_data in data.get("data", []):
            model_id = model_data.get("id", "")
            models.append(
                ModelInfo(
                    id=model_id,
                    name=model_id,
                    provider=self.provider_name,
                    capabilities=self.supported_capabilities,
                    max_tokens=model_data.get("max_tokens", 4096),
                    context_window=model_data.get("context_window", 4096),
                    metadata=model_data,
                )
            )
        return models

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

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Add any additional parameters
        payload.update(kwargs)

        if stream:
            # For streaming, we need to handle differently - return full response
            return await self._chat_stream_collect(
                messages, model, temperature, max_tokens, **kwargs
            )

        response = await self._request_with_retry("POST", "/chat/completions", payload)
        data = response.json()

        choice = data["choices"][0]
        return ChatResponse(
            content=choice["message"]["content"],
            model=data["model"],
            usage=data.get("usage", {}),
            finish_reason=choice.get("finish_reason", "stop"),
            tool_calls=choice["message"].get("tool_calls"),
        )

    async def _chat_stream_collect(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Collect streaming response into a full ChatResponse."""
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        client = await self._get_client()

        self._log_request(
            "POST", "/chat/completions", payload, self._get_default_headers()
        )

        full_content = ""
        finish_reason = "stop"
        usage = {}
        model_name = model
        tool_calls = None

        try:
            async with client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
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
                            if (
                                "choices" in chunk_data
                                and len(chunk_data["choices"]) > 0
                            ):
                                choice = chunk_data["choices"][0]
                                if "delta" in choice:
                                    delta = choice["delta"]
                                    if delta.get("content"):
                                        full_content += delta["content"]
                                    if "tool_calls" in delta:
                                        tool_calls = delta["tool_calls"]
                                if (
                                    choice.get("finish_reason")
                                ):
                                    finish_reason = choice["finish_reason"]
                        except json.JSONDecodeError:
                            pass

                elapsed = time.time() - start_time
                self._log_response(200, {}, {"content": full_content}, elapsed)

        except Exception as e:
            DEBUG_LOG.error(f"Streaming failed: {e}, falling back to non-streaming")
            # Fall back to non-streaming
            return await self.chat(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )

        return ChatResponse(
            content=full_content,
            model=model_name,
            usage=usage,
            finish_reason=finish_reason,
            tool_calls=tool_calls,
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
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        client = await self._get_client()

        self._log_request(
            "POST", "/chat/completions", payload, self._get_default_headers()
        )

        try:
            async with client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
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
            response = await self.chat(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )
            yield f"data: {json.dumps({'choices': [{'delta': {'content': response.content}}]})}\n\n"
            yield "data: [DONE]\n\n"

        except httpx.RemoteProtocolError as e:
            DEBUG_LOG.error(f"STREAM_EARLY_EOF: {e}")
            self._log_streaming_event("error", f"STREAM_EARLY_EOF: {e}")
            # Fall back to non-streaming
            DEBUG_LOG.info("Falling back to non-streaming mode")
            response = await self.chat(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )
            yield f"data: {json.dumps({'choices': [{'delta': {'content': response.content}}]})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            DEBUG_LOG.error(f"Streaming error: {e}")
            self._log_streaming_event("error", f"Streaming error: {e}")
            # Fall back to non-streaming
            DEBUG_LOG.info("Falling back to non-streaming mode")
            response = await self.chat(
                messages, model, temperature, max_tokens, stream=False, **kwargs
            )
            yield f"data: {json.dumps({'choices': [{'delta': {'content': response.content}}]})}\n\n"
            yield "data: [DONE]\n\n"

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate embeddings for texts."""
        payload = {
            "model": model,
            "input": texts,
        }
        payload.update(kwargs)

        response = await self._request_with_retry("POST", "/embeddings", payload)
        data = response.json()

        embeddings = [item["embedding"] for item in data["data"]]
        return EmbeddingResponse(
            embeddings=embeddings,
            model=data["model"],
            usage=data.get("usage", {}),
        )
