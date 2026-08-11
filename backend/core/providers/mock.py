"""Mock provider for testing without API keys."""

import asyncio
from typing import Any

from backend.core.providers.interfaces import (
    ChatMessage,
    ChatProvider,
    ChatResponse,
    EmbeddingProvider,
    EmbeddingResponse,
    ModelCapability,
    ModelInfo,
)


class MockProvider(ChatProvider, EmbeddingProvider):
    """Mock provider for testing."""

    def __init__(
        self,
        api_key: str = "mock-key",
        base_url: str = "http://localhost",
        **kwargs: Any,
    ) -> None:
        self._provider_name = "mock"
        self.api_key = api_key
        self.base_url = base_url

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
            ModelCapability.FUNCTION_CALLING,
        ]

    async def list_models(self) -> list[ModelInfo]:
        """List mock models."""
        return [
            ModelInfo(
                id="mock-model",
                name="Mock Model",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=32768,
            ),
            ModelInfo(
                id="mock-model-large",
                name="Mock Model Large",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=128000,
            ),
        ]

    async def validate_connection(self) -> bool:
        """Always validate successfully."""
        return True

    async def close(self) -> None:
        """Close provider."""

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate a mock chat completion."""
        user_message = ""
        system_message = ""
        tool_results = []
        for msg in messages:
            if msg.role == "user":
                if msg.content.startswith("Tool result"):
                    tool_results.append(msg.content)
                else:
                    user_message = msg.content
            elif msg.role == "system":
                system_message = msg.content

        # Check if this is an agent task with tools
        if (
            "TOOL_NAME" in system_message
            or "GLOB" in system_message
            or "tools" in system_message.lower()
        ):
            # Handle tool results
            if tool_results:
                # Respond to tool result
                last_result = tool_results[-1]
                if "GLOB" in last_result:
                    content = "Found Python files:\n" + last_result.replace(
                        "Tool result for GLOB:\n", ""
                    )
                elif "LIST_DIR" in last_result:
                    content = "Directory contents:\n" + last_result.replace(
                        "Tool result for LIST_DIR:\n", ""
                    )
                elif "READ_FILE" in last_result:
                    content = "File contents:\n" + last_result.replace(
                        "Tool result for READ_FILE:\n", ""
                    )
                elif "RUN_COMMAND" in last_result:
                    content = "Command output:\n" + last_result.replace(
                        "Tool result for RUN_COMMAND:\n", ""
                    )
                elif "GREP" in last_result:
                    content = "Search results:\n" + last_result.replace(
                        "Tool result for GREP:\n", ""
                    )
                else:
                    content = "Task completed. Here's the result:\n" + last_result
            else:
                # Initial tool call
                if "list" in user_message.lower() and "python" in user_message.lower():
                    content = '{"tool": "GLOB", "args": {"pattern": "**/*.py"}}'
                elif "list" in user_message.lower() and (
                    "file" in user_message.lower()
                    or "directory" in user_message.lower()
                ):
                    content = '{"tool": "LIST_DIR", "args": {"path": "."}}'
                elif "read" in user_message.lower() and (
                    "file" in user_message.lower() or "content" in user_message.lower()
                ):
                    content = '{"tool": "READ_FILE", "args": {"path": "README.md"}}'
                elif (
                    "run" in user_message.lower() and "command" in user_message.lower()
                ):
                    content = '{"tool": "RUN_COMMAND", "args": {"command": "ls -la"}}'
                elif "search" in user_message.lower() or "grep" in user_message.lower():
                    content = (
                        '{"tool": "GREP", "args": {"pattern": "TODO", "path": "."}}'
                    )
                else:
                    content = '{"tool": "LIST_DIR", "args": {"path": "."}}'
        else:
            # Generate a contextual mock response
            if "hello" in user_message.lower() or "hi" in user_message.lower():
                content = "Hello! I'm a mock AI provider for testing Orion Codex. How can I help you today?"
            elif "code" in user_message.lower() or "program" in user_message.lower():
                content = "I can help you with code! Here's a simple example:\n\n```python\ndef hello_world():\n    print('Hello, World!')\n\nhello_world()\n```"
            elif "test" in user_message.lower():
                content = "This is a test response from the mock provider. The provider pipeline is working correctly!"
            else:
                content = f"I received your message: '{user_message}'. This is a mock response for testing purposes."

        return ChatResponse(
            content=content,
            model=model,
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            finish_reason="stop",
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        """Generate a mock streaming chat completion."""
        # Pop stream from kwargs to avoid duplicate
        kwargs.pop("stream", None)
        response = await self.chat(
            messages, model, temperature, max_tokens, stream=False, **kwargs
        )

        # Simulate streaming by yielding content chunks (not SSE format)
        words = response.content.split()
        for i, word in enumerate(words):
            yield word + " "
            await asyncio.sleep(0.05)  # Simulate network delay

    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate mock embeddings."""
        embeddings = []
        for text in texts:
            # Simple hash-based mock embedding
            embedding = [float(ord(c) % 100) / 100.0 for c in text[:384]]
            # Pad to 384 dimensions
            while len(embedding) < 384:
                embedding.append(0.0)
            embeddings.append(embedding[:384])

        return EmbeddingResponse(
            embeddings=embeddings,
            model=model,
            usage={"total_tokens": sum(len(t) for t in texts)},
        )
