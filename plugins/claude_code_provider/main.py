"""Claude Code CLI Provider Plugin."""

import asyncio
import logging
import subprocess
from typing import Any

from backend.plugins.sdk.base import AIProviderPlugin, PluginContext, PluginManifest
from backend.core.providers.interfaces import (
    ChatProvider,
    ModelCapability,
    ModelInfo,
    ChatMessage,
    ChatResponse,
)

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(ChatProvider):
    """Claude Code CLI provider implementation."""

    def __init__(self, claude_path: str = "claude", workspace_path: str = "") -> None:
        self._claude_path = claude_path
        self._workspace_path = workspace_path

    @property
    def provider_name(self) -> str:
        return "claude_code"

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.REASONING,
        ]

    async def list_models(self) -> list[ModelInfo]:
        """List available models (Claude Code uses Opus/Sonnet/Haiku)."""
        return [
            ModelInfo(
                id="claude-3-opus-20240229",
                name="Claude 3 Opus",
                provider="claude_code",
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                provider="claude_code",
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                provider="claude_code",
                capabilities=self.supported_capabilities,
                max_tokens=4096,
                context_window=200000,
            ),
        ]

    async def validate_connection(self) -> bool:
        """Validate Claude Code CLI is available."""
        try:
            result = await asyncio.create_subprocess_exec(
                self._claude_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()
            return result.returncode == 0
        except Exception:
            return False

    async def close(self) -> None:
        """Close provider connections."""
        pass

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate a chat completion using Claude Code."""
        # Build prompt from messages
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        prompt = "\n\n".join(prompt_parts)

        # Execute Claude Code
        cmd = [self._claude_path, "chat", "--model", model]
        if self._workspace_path:
            cmd.extend(["--workspace", self._workspace_path])

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate(input=prompt.encode())

        if process.returncode != 0:
            raise RuntimeError(f"Claude Code error: {stderr.decode()}")

        content = stdout.decode().strip()

        return ChatResponse(
            content=content,
            model=model,
            usage={"prompt_tokens": len(prompt), "completion_tokens": len(content)},
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
        """Generate a streaming chat completion."""
        # For simplicity, yield the full response
        response = await self.chat(messages, model, temperature, max_tokens)
        yield response.content


class ClaudeCodeProviderPlugin(AIProviderPlugin):
    """Claude Code Provider Plugin."""

    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        super().__init__(manifest, context)
        self._provider: ClaudeCodeProvider | None = None

    async def _on_initialize(self) -> None:
        """Initialize the provider."""
        claude_path = self.get_config("claude_path", "claude")
        workspace_path = self.get_config("workspace_path", "")

        self._provider = ClaudeCodeProvider(claude_path, workspace_path)

        if not await self._provider.validate_connection():
            logger.warning("Claude Code CLI not found or not working")

    async def _on_shutdown(self) -> None:
        """Shutdown the provider."""
        self._provider = None

    async def get_provider(self) -> ClaudeCodeProvider:
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