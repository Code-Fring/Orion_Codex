"""Plugin base classes and interfaces."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from backend.plugins.sdk.manifest import PluginManifest, PluginMetadata, PluginPermission, PluginType

logger = logging.getLogger(__name__)


@dataclass
class PluginContext:
    """Context provided to plugins during initialization."""
    config: dict[str, Any] = field(default_factory=dict)
    workspace_path: str = ""
    data_path: str = ""
    log_level: str = "INFO"
    services: dict[str, Any] = field(default_factory=dict)


class BasePlugin(ABC):
    """Base class for all plugins."""

    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        self.manifest = manifest
        self.context = context
        self._enabled = False
        self._initialized = False

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def initialized(self) -> bool:
        return self._initialized

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.context.config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.context.config[key] = value

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            await self._on_initialize()
            self._initialized = True
            logger.info(f"Plugin initialized: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Plugin initialization failed: {self.name}: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        try:
            await self._on_shutdown()
            self._initialized = False
            logger.info(f"Plugin shutdown: {self.name}")
        except Exception as e:
            logger.error(f"Plugin shutdown failed: {self.name}: {e}")

    async def enable(self) -> bool:
        """Enable the plugin."""
        if self._enabled:
            return True

        if not self._initialized:
            success = await self.initialize()
            if not success:
                return False

        try:
            await self._on_enable()
            self._enabled = True
            logger.info(f"Plugin enabled: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Plugin enable failed: {self.name}: {e}")
            return False

    async def disable(self) -> bool:
        """Disable the plugin."""
        if not self._enabled:
            return True

        try:
            await self._on_disable()
            self._enabled = False
            logger.info(f"Plugin disabled: {self.name}")
            return True
        except Exception as e:
            logger.error(f"Plugin disable failed: {self.name}: {e}")
            return False

    async def reload(self) -> bool:
        """Reload the plugin."""
        await self.disable()
        await self.shutdown()
        return await self.initialize() and await self.enable()

    # Override these methods in subclasses
    async def _on_initialize(self) -> None:
        """Called during initialization."""
        pass

    async def _on_shutdown(self) -> None:
        """Called during shutdown."""
        pass

    async def _on_enable(self) -> None:
        """Called when plugin is enabled."""
        pass

    async def _on_disable(self) -> None:
        """Called when plugin is disabled."""
        pass


class AIProviderPlugin(BasePlugin):
    """Plugin that provides an AI provider."""

    @property
    def provider_name(self) -> str:
        return self.manifest.name

    @abstractmethod
    async def get_provider(self) -> Any:
        """Get the provider instance."""

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """List available models."""

    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate provider connection."""


class AgentPlugin(BasePlugin):
    """Plugin that provides an agent."""

    @property
    def agent_type(self) -> str:
        return self.manifest.provides[0] if self.manifest.provides else self.manifest.name

    @abstractmethod
    async def create_agent(self, config: dict[str, Any] | None = None) -> Any:
        """Create an agent instance."""

    @abstractmethod
    def get_agent_schema(self) -> dict[str, Any]:
        """Get agent schema for registration."""


class ToolPlugin(BasePlugin):
    """Plugin that provides a tool."""

    @property
    def tool_name(self) -> str:
        return self.manifest.name

    @abstractmethod
    async def execute(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute the tool."""

    @abstractmethod
    def get_tool_schema(self) -> dict[str, Any]:
        """Get tool schema for LLM function calling."""


class UIPanelPlugin(BasePlugin):
    """Plugin that provides a UI panel."""

    @property
    def panel_id(self) -> str:
        return self.manifest.name

    @abstractmethod
    def get_panel_component(self) -> Any:
        """Get the panel component."""

    @abstractmethod
    def get_panel_config(self) -> dict[str, Any]:
        """Get panel configuration."""


class ThemePlugin(BasePlugin):
    """Plugin that provides a theme."""

    @property
    def theme_name(self) -> str:
        return self.manifest.name

    @abstractmethod
    def get_theme(self) -> dict[str, Any]:
        """Get theme definition."""


class DashboardPlugin(BasePlugin):
    """Plugin that provides a dashboard."""

    @property
    def dashboard_id(self) -> str:
        return self.manifest.name

    @abstractmethod
    def get_dashboard_config(self) -> dict[str, Any]:
        """Get dashboard configuration."""

    @abstractmethod
    def get_widgets(self) -> list[dict[str, Any]]:
        """Get dashboard widgets."""


class MemoryProviderPlugin(BasePlugin):
    """Plugin that provides a memory backend."""

    @property
    def provider_name(self) -> str:
        return self.manifest.name

    @abstractmethod
    async def store(self, key: str, value: Any, project_id: str) -> bool:
        """Store a value."""

    @abstractmethod
    async def retrieve(self, key: str, project_id: str) -> Any | None:
        """Retrieve a value."""

    @abstractmethod
    async def delete(self, key: str, project_id: str) -> bool:
        """Delete a value."""

    @abstractmethod
    async def list_keys(self, project_id: str, prefix: str = "") -> list[str]:
        """List keys."""


class MCPServerPlugin(BasePlugin):
    """Plugin that provides an MCP server."""

    @property
    def server_name(self) -> str:
        return self.manifest.name

    @abstractmethod
    async def create_server(self) -> Any:
        """Create MCP server instance."""


class BackgroundServicePlugin(BasePlugin):
    """Plugin that provides a background service."""

    @abstractmethod
    async def start(self) -> None:
        """Start the service."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service."""

    @abstractmethod
    async def status(self) -> dict[str, Any]:
        """Get service status."""


class ValidatorPlugin(BasePlugin):
    """Plugin that provides a validator."""

    @property
    def validator_name(self) -> str:
        return self.manifest.name

    @abstractmethod
    async def validate(self, target: Any, context: dict[str, Any]) -> dict[str, Any]:
        """Validate target and return results."""


class HookPlugin(BasePlugin):
    """Plugin that provides hooks."""

    @property
    def hook_points(self) -> list[str]:
        """Return list of hook points this plugin handles."""
        return []

    @abstractmethod
    async def before_hook(self, hook_point: str, context: dict[str, Any]) -> dict[str, Any] | None:
        """Called before hook point execution."""

    @abstractmethod
    async def after_hook(self, hook_point: str, context: dict[str, Any], result: Any) -> Any:
        """Called after hook point execution."""


class EventListenerPlugin(BasePlugin):
    """Plugin that listens to events."""

    @property
    def event_types(self) -> list[str]:
        """Return list of event types this plugin handles."""
        return []

    @abstractmethod
    async def on_event(self, event_type: str, event_data: dict[str, Any]) -> None:
        """Handle an event."""


class CommandPlugin(BasePlugin):
    """Plugin that provides CLI commands."""

    @abstractmethod
    def get_commands(self) -> dict[str, Any]:
        """Return command definitions for CLI."""


# Plugin factory for creating plugin instances
class PluginFactory:
    """Factory for creating plugin instances from entry points."""

    @staticmethod
    async def create_plugin(metadata: PluginMetadata, context: PluginContext) -> BasePlugin | None:
        """Create a plugin instance from metadata."""
        manifest = metadata.manifest
        try:
            # Import the entry point module
            import importlib.util
            entry_path = metadata.path / manifest.entry_point
            if not entry_path.exists():
                logger.error(f"Entry point not found: {entry_path}")
                return None

            spec = importlib.util.spec_from_file_location(manifest.name, entry_path)
            if not spec or not spec.loader:
                logger.error(f"Failed to load spec for {manifest.name}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin class - look for a class defined in this module (not imported)
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) 
                    and issubclass(attr, BasePlugin) 
                    and attr != BasePlugin
                    and attr.__module__ == module.__name__):  # Only classes defined in this module
                    plugin_class = attr
                    break

            if not plugin_class:
                logger.error(f"No plugin class found in {manifest.name}")
                return None

            # Create instance
            plugin = plugin_class(manifest, context)
            return plugin

        except Exception as e:
            logger.error(f"Failed to create plugin {manifest.name}: {e}")
            return None