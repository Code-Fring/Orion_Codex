"""Plugin interfaces and base classes."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Types of plugins."""

    AI_PROVIDER = "ai_provider"
    BUILDER = "builder"
    LANGUAGE = "language"
    DEPLOYMENT = "deployment"
    TOOL = "tool"
    AGENT = "agent"


@dataclass
class PluginMetadata:
    """Plugin metadata."""

    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str
    config_schema: dict[str, Any] | None = None
    dependencies: list[str] = None
    tags: list[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []


class BasePlugin(ABC):
    """Base class for all plugins."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.enabled = True
        self._metadata: PluginMetadata | None = None

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the plugin."""

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value


class AIProviderPlugin(BasePlugin):
    """Base class for AI provider plugins."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            description="AI Provider Plugin",
            author="Orion Codex",
            plugin_type=PluginType.AI_PROVIDER,
            entry_point=self.__class__.__name__,
        )

    @abstractmethod
    async def get_provider(self):
        """Get the provider instance."""


class BuilderPlugin(BasePlugin):
    """Base class for builder plugins."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            description="Builder Plugin",
            author="Orion Codex",
            plugin_type=PluginType.BUILDER,
            entry_point=self.__class__.__name__,
        )

    @abstractmethod
    async def build(self, spec: dict[str, Any], output_path: str) -> dict[str, Any]:
        """Build project from specification."""


class LanguagePlugin(BasePlugin):
    """Base class for language support plugins."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            description="Language Plugin",
            author="Orion Codex",
            plugin_type=PluginType.LANGUAGE,
            entry_point=self.__class__.__name__,
        )

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """Get supported file extensions."""

    @abstractmethod
    def get_build_command(self) -> str:
        """Get build command."""

    @abstractmethod
    def get_test_command(self) -> str:
        """Get test command."""


class DeploymentPlugin(BasePlugin):
    """Base class for deployment plugins."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            description="Deployment Plugin",
            author="Orion Codex",
            plugin_type=PluginType.DEPLOYMENT,
            entry_point=self.__class__.__name__,
        )

    @abstractmethod
    async def deploy(self, project_path: str, config: dict[str, Any]) -> dict[str, Any]:
        """Deploy project."""

    @abstractmethod
    def get_deployment_targets(self) -> list[str]:
        """Get supported deployment targets."""


class ToolPlugin(BasePlugin):
    """Base class for tool plugins."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            description="Tool Plugin",
            author="Orion Codex",
            plugin_type=PluginType.TOOL,
            entry_point=self.__class__.__name__,
        )

    @abstractmethod
    async def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool."""

    @abstractmethod
    def get_tool_schema(self) -> dict[str, Any]:
        """Get tool schema for LLM function calling."""
