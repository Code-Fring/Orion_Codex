"""Hot reload system for plugin development."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    FileModifiedEvent = object

from backend.plugins.sdk.manager import plugin_manager
from backend.plugins.sdk.manifest import PluginManifest

logger = logging.getLogger(__name__)


class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot reload."""

    def __init__(self, plugin_name: str, reload_callback: Callable[[str], Any]) -> None:
        super().__init__()
        self.plugin_name = plugin_name
        self.reload_callback = reload_callback
        self._debounce_task: asyncio.Task | None = None

    def on_modified(self, event: FileModifiedEvent) -> None:
        if event.is_directory:
            return

        # Debounce rapid changes
        if self._debounce_task:
            self._debounce_task.cancel()

        async def debounced_reload():
            await asyncio.sleep(1.0)  # Wait for file writes to complete
            try:
                await self.reload_callback(self.plugin_name)
                logger.info(f"Hot reloaded plugin: {self.plugin_name}")
            except Exception as e:
                logger.error(f"Hot reload failed for {self.plugin_name}: {e}")

        self._debounce_task = asyncio.create_task(debounced_reload())


class HotReloadManager:
    """Manages hot reloading of plugins during development."""

    def __init__(self) -> None:
        self._observers: dict[str, Observer] = {}
        self._handlers: dict[str, PluginFileHandler] = {}
        self._watch_enabled = False

    def start_watching(self, plugin_name: str) -> bool:
        """Start watching a plugin directory for changes."""
        if not WATCHDOG_AVAILABLE:
            logger.warning("Watchdog not available, hot reload disabled")
            return False

        metadata = plugin_manager.get_plugin(plugin_name)
        if not metadata:
            logger.error(f"Plugin not found: {plugin_name}")
            return False

        plugin_path = metadata.path
        if not plugin_path.exists():
            logger.error(f"Plugin path does not exist: {plugin_path}")
            return False

        # Create handler and observer
        handler = PluginFileHandler(plugin_name, self._reload_plugin)
        observer = Observer()
        observer.schedule(handler, str(plugin_path), recursive=True)
        observer.start()

        self._observers[plugin_name] = observer
        self._handlers[plugin_name] = handler
        self._watch_enabled = True

        logger.info(f"Started hot reload watching for {plugin_name} at {plugin_path}")
        return True

    def stop_watching(self, plugin_name: str) -> bool:
        """Stop watching a plugin directory."""
        if plugin_name in self._observers:
            observer = self._observers.pop(plugin_name)
            observer.stop()
            observer.join(timeout=5.0)

        if plugin_name in self._handlers:
            self._handlers.pop(plugin_name)

        if not self._observers:
            self._watch_enabled = False

        logger.info(f"Stopped hot reload watching for {plugin_name}")
        return True

    def stop_all(self) -> None:
        """Stop all watchers."""
        for plugin_name in list(self._observers.keys()):
            self.stop_watching(plugin_name)

    async def _reload_plugin(self, plugin_name: str) -> None:
        """Reload a plugin."""
        try:
            await plugin_manager.reload_plugin(plugin_name)
        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")

    def is_watching(self, plugin_name: str) -> bool:
        """Check if a plugin is being watched."""
        return plugin_name in self._observers

    def get_watched_plugins(self) -> list[str]:
        """Get list of watched plugins."""
        return list(self._observers.keys())


# Global hot reload manager
hot_reload_manager = HotReloadManager()