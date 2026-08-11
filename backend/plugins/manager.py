"""Plugin manager for loading and managing plugins."""

import importlib.util
import json
import logging
from pathlib import Path
from typing import Any

from backend.plugins.interfaces import (
    AIProviderPlugin,
    BasePlugin,
    BuilderPlugin,
    DeploymentPlugin,
    LanguagePlugin,
    PluginMetadata,
    PluginType,
    ToolPlugin,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""

    def __init__(self, plugin_dirs: list[Path] | None = None) -> None:
        self.plugin_dirs = plugin_dirs or [Path("./plugins")]
        self._plugins: dict[str, BasePlugin] = {}
        self._plugin_classes: dict[str, type[BasePlugin]] = {}
        self._plugins_by_type: dict[PluginType, list[BasePlugin]] = {
            PluginType.AI_PROVIDER: [],
            PluginType.BUILDER: [],
            PluginType.LANGUAGE: [],
            PluginType.DEPLOYMENT: [],
            PluginType.TOOL: [],
            PluginType.AGENT: [],
        }

    def add_plugin_dir(self, path: Path) -> None:
        """Add a plugin directory."""
        if path not in self.plugin_dirs:
            self.plugin_dirs.append(path)

    def discover_plugins(self) -> list[PluginMetadata]:
        """Discover all plugins in plugin directories."""
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            for item in plugin_dir.iterdir():
                if item.is_dir():
                    manifest_path = item / "plugin.json"
                    if manifest_path.exists():
                        try:
                            metadata = self._load_manifest(manifest_path)
                            if metadata:
                                discovered.append(metadata)
                        except Exception as e:
                            logger.error(
                                f"Failed to load plugin manifest {manifest_path}: {e}"
                            )

        return discovered

    def _load_manifest(self, manifest_path: Path) -> PluginMetadata | None:
        """Load plugin manifest."""
        try:
            data = json.loads(manifest_path.read_text())
            return PluginMetadata(
                name=data["name"],
                version=data["version"],
                description=data["description"],
                author=data["author"],
                plugin_type=PluginType(data["plugin_type"]),
                entry_point=data["entry_point"],
                config_schema=data.get("config_schema"),
                dependencies=data.get("dependencies", []),
                tags=data.get("tags", []),
            )
        except Exception as e:
            logger.error(f"Failed to parse manifest {manifest_path}: {e}")
            return None

    def register_plugin_class(self, plugin_class: type[BasePlugin]) -> None:
        """Register a plugin class."""
        # Create instance to get metadata
        instance = plugin_class()
        metadata = instance.metadata

        self._plugin_classes[metadata.name] = plugin_class
        logger.info(f"Registered plugin class: {metadata.name}")

    async def load_plugin(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> BasePlugin | None:
        """Load and initialize a plugin."""
        if name in self._plugins:
            logger.warning(f"Plugin already loaded: {name}")
            return self._plugins[name]

        plugin_class = self._plugin_classes.get(name)
        if not plugin_class:
            # Try to load from plugin directory
            plugin_class = await self._load_plugin_class(name)
            if not plugin_class:
                logger.error(f"Plugin class not found: {name}")
                return None

        try:
            plugin = plugin_class(config)
            success = await plugin.initialize()

            if success:
                self._plugins[name] = plugin
                self._plugins_by_type[plugin.metadata.plugin_type].append(plugin)
                logger.info(f"Loaded plugin: {name}")
                return plugin
            else:
                logger.error(f"Plugin initialization failed: {name}")
                return None
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            return None

    async def _load_plugin_class(self, name: str) -> type[BasePlugin] | None:
        """Load plugin class from plugin directory."""
        for plugin_dir in self.plugin_dirs:
            plugin_path = plugin_dir / name
            if not plugin_path.exists():
                continue

            # Look for main module
            main_file = plugin_path / "main.py"
            if not main_file.exists():
                main_file = plugin_path / f"{name}.py"

            if not main_file.exists():
                continue

            try:
                spec = importlib.util.spec_from_file_location(name, main_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find plugin class
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BasePlugin)
                            and attr != BasePlugin
                        ):
                            self._plugin_classes[name] = attr
                            return attr
            except Exception as e:
                logger.error(f"Failed to load plugin module {main_file}: {e}")

        return None

    async def unload_plugin(self, name: str) -> bool:
        """Unload a plugin."""
        plugin = self._plugins.get(name)
        if not plugin:
            return False

        try:
            await plugin.shutdown()
            self._plugins_by_type[plugin.metadata.plugin_type].remove(plugin)
            del self._plugins[name]
            logger.info(f"Unloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin {name}: {e}")
            return False

    def get_plugin(self, name: str) -> BasePlugin | None:
        """Get a loaded plugin by name."""
        return self._plugins.get(name)

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[BasePlugin]:
        """Get all loaded plugins of a type."""
        return self._plugins_by_type.get(plugin_type, [])

    def get_ai_provider_plugins(self) -> list[AIProviderPlugin]:
        """Get all AI provider plugins."""
        return [
            p
            for p in self._plugins_by_type[PluginType.AI_PROVIDER]
            if isinstance(p, AIProviderPlugin)
        ]

    def get_builder_plugins(self) -> list[BuilderPlugin]:
        """Get all builder plugins."""
        return [
            p
            for p in self._plugins_by_type[PluginType.BUILDER]
            if isinstance(p, BuilderPlugin)
        ]

    def get_language_plugins(self) -> list[LanguagePlugin]:
        """Get all language plugins."""
        return [
            p
            for p in self._plugins_by_type[PluginType.LANGUAGE]
            if isinstance(p, LanguagePlugin)
        ]

    def get_deployment_plugins(self) -> list[DeploymentPlugin]:
        """Get all deployment plugins."""
        return [
            p
            for p in self._plugins_by_type[PluginType.DEPLOYMENT]
            if isinstance(p, DeploymentPlugin)
        ]

    def get_tool_plugins(self) -> list[ToolPlugin]:
        """Get all tool plugins."""
        return [
            p
            for p in self._plugins_by_type[PluginType.TOOL]
            if isinstance(p, ToolPlugin)
        ]

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all loaded plugins."""
        return [
            {
                "name": plugin.metadata.name,
                "version": plugin.metadata.version,
                "description": plugin.metadata.description,
                "author": plugin.metadata.author,
                "type": plugin.metadata.plugin_type.value,
                "enabled": plugin.enabled,
            }
            for plugin in self._plugins.values()
        ]

    async def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in list(self._plugins.values()):
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin.metadata.name}: {e}")

        self._plugins.clear()
        for plugin_type in self._plugins_by_type:
            self._plugins_by_type[plugin_type].clear()


# Global plugin manager
plugin_manager = PluginManager()
