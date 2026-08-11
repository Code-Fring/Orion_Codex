"""Claude Code CLI provider implementation."""

import asyncio
import json
import subprocess
from typing import Any

from backend.core.providers.interfaces import (
    ChatMessage,
    ChatProvider,
    ChatResponse,
    ModelCapability,
    ModelInfo,
)


class ClaudeCLIProvider(ChatProvider):
    """Claude Code CLI provider implementation."""

    def __init__(
        self,
        cli_path: str = "claude",
        working_dir: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.cli_path = cli_path
        self.working_dir = working_dir
        self._provider_name = "claude_cli"

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def supported_capabilities(self) -> list[ModelCapability]:
        return [
            ModelCapability.CHAT,
            ModelCapability.COMPLETION,
            ModelCapability.CODE,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ]

    async def list_models(self) -> list[ModelInfo]:
        """List available models (Claude CLI uses Anthropic models)."""
        return [
            ModelInfo(
                id="claude-fable-5",
                name="Claude Fable 5 (Latest)",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-sonnet-4",
                name="Claude Sonnet 4",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=200000,
            ),
            ModelInfo(
                id="claude-opus-4",
                name="Claude Opus 4",
                provider=self.provider_name,
                capabilities=self.supported_capabilities,
                max_tokens=8192,
                context_window=200000,
            ),
        ]

    async def validate_connection(self) -> bool:
        """Validate that Claude CLI is available."""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def close(self) -> None:
        """Close provider (no-op for CLI)."""

    def _convert_messages(self, messages: list[ChatMessage]) -> str:
        """Convert messages to a single prompt string for CLI."""
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        return "\n\n".join(prompt_parts)

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate a chat completion using Claude CLI."""
        prompt = self._convert_messages(messages)

        cmd = [
            self.cli_path,
            "-p",
            prompt,
            "--output-format",
            "json",
        ]

        if model and model != "default":
            cmd.extend(["--model", model])

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.working_dir,
            )

            if result.returncode != 0:
                raise Exception(f"Claude CLI error: {result.stderr}")

            data = json.loads(result.stdout)
            content = data.get("content", "") if isinstance(data, dict) else str(data)

            return ChatResponse(
                content=content,
                model=model,
                usage={"input_tokens": 0, "output_tokens": 0},
                finish_reason="stop",
            )

        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Claude CLI output: {e}")
        except subprocess.TimeoutExpired:
            raise Exception("Claude CLI timed out")

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ):
        """Generate a streaming chat completion using Claude CLI."""
        prompt = self._convert_messages(messages)

        cmd = [
            self.cli_path,
            "-p",
            prompt,
            "--output-format",
            "stream-json",
        ]

        if model and model != "default":
            cmd.extend(["--model", model])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
            )

            async for line in process.stdout:
                line = line.decode().strip()
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("type") == "content":
                            yield data.get("content", "")
                        elif data.get("type") == "complete":
                            break
                    except json.JSONDecodeError:
                        pass

            await process.wait()

        except Exception as e:
            yield f"Error: {e}"
