"""Plugin manager with full lifecycle support."""

import asyncio
import logging
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.plugins.sdk.manifest import (
    PluginDependency,
    PluginManifest,
    PluginMetadata,
    PluginPermission,
    PluginType,
)
from backend.plugins.sdk.base import (
    BasePlugin,
    PluginContext,
    PluginFactory,
)

logger = logging.getLogger(__name__)


@dataclass
class PluginInstallResult:
    """Result of plugin installation."""
    success: bool
    message: str
    plugin_path: Path | None = None
    metadata: PluginMetadata | None = None


class PluginManager:
    """Manages plugin discovery, installation, loading, and lifecycle."""

    def __init__(
        self,
        plugin_dirs: list[Path] | None = None,
        config_dir: Path | None = None,
        auto_discover: bool = True,
    ) -> None:
        self.plugin_dirs = plugin_dirs or [Path("./plugins")]
        self.config_dir = config_dir or Path.home() / ".orion" / "plugins"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._plugins: dict[str, PluginMetadata] = {}
        self._enabled_plugins: set[str] = set()
        self._plugin_configs: dict[str, dict[str, Any]] = {}
        self._permission_grants: dict[str, set[PluginPermission]] = {}
        self._pending_permissions: dict[str, list[PluginPermission]] = {}

        # Load persisted state
        self._load_state()

        # Auto-discover plugins
        if auto_discover:
            self.discover_plugins()

    def _load_state(self) -> None:
        """Load plugin state from config."""
        state_file = self.config_dir / "state.json"
        if state_file.exists():
            try:
                import json
                data = json.loads(state_file.read_text())
                self._enabled_plugins = set(data.get("enabled", []))
                self._plugin_configs = data.get("configs", {})
                self._permission_grants = {
                    k: set(PluginPermission(p) for p in v)
                    for k, v in data.get("permissions", {}).items()
                }
            except Exception as e:
                logger.error(f"Failed to load plugin state: {e}")

    def _save_state(self) -> None:
        """Save plugin state to config."""
        state_file = self.config_dir / "state.json"
        try:
            import json
            data = {
                "enabled": list(self._enabled_plugins),
                "configs": self._plugin_configs,
                "permissions": {
                    k: [p.value for p in v]
                    for k, v in self._permission_grants.items()
                },
            }
            state_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save plugin state: {e}")

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
                            metadata = self._load_plugin_metadata(manifest_path, item)
                            if metadata:
                                self._plugins[metadata.manifest.name] = metadata
                                discovered.append(metadata)
                        except Exception as e:
                            logger.error(f"Failed to load plugin {item}: {e}")

        return discovered

    def _load_plugin_metadata(self, manifest_path: Path, plugin_path: Path) -> PluginMetadata | None:
        """Load plugin metadata from manifest."""
        manifest = PluginManifest.load_from_file(manifest_path)
        return PluginMetadata(manifest=manifest, path=plugin_path)

    def get_plugin(self, name: str) -> PluginMetadata | None:
        """Get plugin metadata by name."""
        return self._plugins.get(name)

    def get_all_plugins(self) -> list[PluginMetadata]:
        """Get all discovered plugins."""
        return list(self._plugins.values())

    def get_plugins_by_type(self, plugin_type: PluginType) -> list[PluginMetadata]:
        """Get plugins by type."""
        return [p for p in self._plugins.values() if p.manifest.plugin_type == plugin_type]

    async def install_plugin(
        self,
        source: str | Path,
        name: str | None = None,
    ) -> PluginInstallResult:
        """Install a plugin from various sources."""
        source_path = Path(source) if isinstance(source, (str, Path)) else source

        try:
            if source_path.is_dir():
                return await self._install_from_dir(source_path, name)
            elif source_path.is_file() and source_path.suffix == ".zip":
                return await self._install_from_zip(source_path, name)
            else:
                return PluginInstallResult(
                    success=False,
                    message=f"Unsupported source: {source_path}",
                )
        except Exception as e:
            logger.error(f"Plugin install failed: {e}")
            return PluginInstallResult(
                success=False,
                message=str(e),
            )

    async def _install_from_dir(self, source_dir: Path, name: str | None) -> PluginInstallResult:
        """Install plugin from directory."""
        plugin_name = name or source_dir.name
        target_dir = self.plugin_dirs[0] / plugin_name

        if target_dir.exists():
            return PluginInstallResult(
                success=False,
                message=f"Plugin already exists: {plugin_name}",
            )

        # Copy directory
        shutil.copytree(source_dir, target_dir)

        # Validate manifest
        manifest_path = target_dir / "plugin.json"
        if not manifest_path.exists():
            shutil.rmtree(target_dir)
            return PluginInstallResult(
                success=False,
                message="No plugin.json found",
            )

        metadata = self._load_plugin_metadata(manifest_path, target_dir)
        if not metadata:
            shutil.rmtree(target_dir)
            return PluginInstallResult(
                success=False,
                message="Invalid plugin manifest",
            )

        # Check dependencies
        if not await self._check_dependencies(metadata.manifest.dependencies):
            shutil.rmtree(target_dir)
            return PluginInstallResult(
                success=False,
                message="Missing dependencies",
            )

        self._plugins[plugin_name] = metadata
        return PluginInstallResult(
            success=True,
            message=f"Plugin installed: {plugin_name}",
            plugin_path=target_dir,
            metadata=metadata,
        )

    async def _install_from_zip(self, zip_path: Path, name: str | None) -> PluginInstallResult:
        """Install plugin from zip file."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_path)

            # Find plugin directory
            items = list(tmp_path.iterdir())
            if len(items) == 1 and items[0].is_dir():
                return await self._install_from_dir(items[0], name)
            else:
                return PluginInstallResult(
                    success=False,
                    message="Zip must contain a single plugin directory",
                )

    async def _check_dependencies(self, dependencies: list[PluginDependency]) -> bool:
        """Check if all dependencies are satisfied."""
        for dep in dependencies:
            if dep.optional:
                continue
            if dep.name not in self._plugins:
                logger.warning(f"Missing dependency: {dep.name}")
                return False
        return True

    async def uninstall_plugin(self, name: str) -> bool:
        """Uninstall a plugin."""
        metadata = self._plugins.get(name)
        if not metadata:
            return False

        # Disable first
        await self.disable_plugin(name)

        # Remove from filesystem
        try:
            shutil.rmtree(metadata.path)
        except Exception as e:
            logger.error(f"Failed to remove plugin files: {e}")

        # Remove from registry
        del self._plugins[name]
        self._enabled_plugins.discard(name)
        self._plugin_configs.pop(name, None)
        self._permission_grants.pop(name, None)
        self._save_state()

        logger.info(f"Plugin uninstalled: {name}")
        return True

    async def enable_plugin(self, name: str) -> bool:
        """Enable a plugin."""
        metadata = self._plugins.get(name)
        if not metadata:
            logger.error(f"Plugin not found: {name}")
            return False

        if name in self._enabled_plugins:
            return True

        # Check permissions
        required_perms = set(metadata.manifest.permissions)
        granted_perms = self._permission_grants.get(name, set())
        missing_perms = required_perms - granted_perms

        if missing_perms:
            self._pending_permissions[name] = list(missing_perms)
            logger.warning(f"Plugin {name} requires permissions: {missing_perms}")
            return False

        # Create plugin instance
        context = PluginContext(
            config=self._plugin_configs.get(name, {}),
            workspace_path=str(Path.cwd()),
            data_path=str(self.config_dir / name),
        )

        plugin = await PluginFactory.create_plugin(metadata, context)
        if not plugin:
            return False

        # Initialize and enable
        if not await plugin.initialize():
            return False

        if not await plugin.enable():
            await plugin.shutdown()
            return False

        metadata.instance = plugin
        metadata.loaded = True
        metadata.enabled = True
        self._enabled_plugins.add(name)
        self._save_state()

        logger.info(f"Plugin enabled: {name}")
        return True

    async def disable_plugin(self, name: str) -> bool:
        """Disable a plugin."""
        metadata = self._plugins.get(name)
        if not metadata or not metadata.enabled:
            return True

        if metadata.instance:
            await metadata.instance.disable()
            await metadata.instance.shutdown()
            metadata.instance = None

        metadata.loaded = False
        metadata.enabled = False
        self._enabled_plugins.discard(name)
        self._save_state()

        logger.info(f"Plugin disabled: {name}")
        return True

    async def reload_plugin(self, name: str) -> bool:
        """Reload a plugin."""
        await self.disable_plugin(name)
        return await self.enable_plugin(name)

    async def update_plugin(self, name: str, source: str | Path) -> PluginInstallResult:
        """Update a plugin."""
        await self.uninstall_plugin(name)
        return await self.install_plugin(source, name)

    def set_plugin_config(self, name: str, config: dict[str, Any]) -> None:
        """Set plugin configuration."""
        self._plugin_configs[name] = config
        self._save_state()

    def get_plugin_config(self, name: str) -> dict[str, Any]:
        """Get plugin configuration."""
        return self._plugin_configs.get(name, {})

    def grant_permission(self, name: str, permission: PluginPermission) -> None:
        """Grant a permission to a plugin."""
        if name not in self._permission_grants:
            self._permission_grants[name] = set()
        self._permission_grants[name].add(permission)
        self._pending_permissions.pop(name, None)
        self._save_state()

    def revoke_permission(self, name: str, permission: PluginPermission) -> None:
        """Revoke a permission from a plugin."""
        if name in self._permission_grants:
            self._permission_grants[name].discard(permission)
        self._save_state()

    def get_pending_permissions(self, name: str) -> list[PluginPermission]:
        """Get pending permissions for a plugin."""
        return self._pending_permissions.get(name, [])

    def get_granted_permissions(self, name: str) -> set[PluginPermission]:
        """Get granted permissions for a plugin."""
        return self._permission_grants.get(name, set())

    def list_plugins(self) -> list[dict[str, Any]]:
        """List all plugins with status."""
        return [p.to_dict() for p in self._plugins.values()]

    async def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for name in list(self._enabled_plugins):
            await self.disable_plugin(name)


# Global plugin manager
plugin_manager = PluginManager()