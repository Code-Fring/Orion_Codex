"""Base interfaces for AI providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ModelCapability(Enum):
    """Model capabilities."""

    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE = "image"
    CODE = "code"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    REASONING = "reasoning"
    SECURITY = "security"


@dataclass
class ModelInfo:
    """Information about a model."""

    id: str
    name: str
    provider: str
    capabilities: list[ModelCapability]
    max_tokens: int
    context_window: int
    pricing: dict[str, float] | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ChatMessage:
    """Chat message structure."""

    role: str  # system, user, assistant, tool
    content: str
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


@dataclass
class ChatResponse:
    """Chat completion response."""

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class EmbeddingResponse:
    """Embedding response."""

    embeddings: list[list[float]]
    model: str
    usage: dict[str, int]


@dataclass
class ImageResponse:
    """Image generation response."""

    url: str | None = None
    b64_json: str | None = None
    revised_prompt: str | None = None


class BaseProvider(ABC):
    """Base interface for all AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""

    @property
    @abstractmethod
    def supported_capabilities(self) -> list[ModelCapability]:
        """Return list of supported capabilities."""

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """List available models."""

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate provider connection and credentials."""

    @abstractmethod
    async def close(self) -> None:
        """Close provider connections."""


class ChatProvider(BaseProvider):
    """Interface for chat/completion providers."""

    @abstractmethod
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

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming chat completion."""


class EmbeddingProvider(BaseProvider):
    """Interface for embedding providers."""

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: str,
        **kwargs: Any,
    ) -> EmbeddingResponse:
        """Generate embeddings for texts."""


class ImageProvider(BaseProvider):
    """Interface for image generation providers."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs: Any,
    ) -> list[ImageResponse]:
        """Generate images from prompt."""

    @abstractmethod
    async def edit_image(
        self,
        image: bytes,
        prompt: str,
        model: str,
        mask: bytes | None = None,
        **kwargs: Any,
    ) -> list[ImageResponse]:
        """Edit an image."""

    @abstractmethod
    async def create_variation(
        self,
        image: bytes,
        model: str,
        n: int = 1,
        **kwargs: Any,
    ) -> list[ImageResponse]:
        """Create variations of an image."""


class CodeProvider(ChatProvider):
    """Interface for code-specialized providers."""

    @abstractmethod
    async def complete_code(
        self,
        code: str,
        language: str,
        model: str,
        max_tokens: int = 500,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> ChatResponse:
        """Complete code snippet."""

    @abstractmethod
    async def explain_code(
        self,
        code: str,
        language: str,
        model: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Explain code."""

    @abstractmethod
    async def generate_tests(
        self,
        code: str,
        language: str,
        model: str,
        framework: str | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Generate tests for code."""

    @abstractmethod
    async def refactor_code(
        self,
        code: str,
        language: str,
        model: str,
        instructions: str,
        **kwargs: Any,
    ) -> ChatResponse:
        """Refactor code based on instructions."""
