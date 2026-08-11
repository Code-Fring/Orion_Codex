"""Plugin SDK package."""

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
    AIProviderPlugin,
    AgentPlugin,
    ToolPlugin,
    UIPanelPlugin,
    ThemePlugin,
    DashboardPlugin,
    MemoryProviderPlugin,
    MCPServerPlugin,
    BackgroundServicePlugin,
    ValidatorPlugin,
    HookPlugin,
    EventListenerPlugin,
    CommandPlugin,
)
from backend.plugins.sdk.manager import PluginManager, plugin_manager, PluginInstallResult
from backend.plugins.sdk.hotreload import HotReloadManager, hot_reload_manager

__all__ = [
    "PluginDependency",
    "PluginManifest",
    "PluginMetadata",
    "PluginPermission",
    "PluginType",
    "BasePlugin",
    "PluginContext",
    "PluginFactory",
    "AIProviderPlugin",
    "AgentPlugin",
    "ToolPlugin",
    "UIPanelPlugin",
    "ThemePlugin",
    "DashboardPlugin",
    "MemoryProviderPlugin",
    "MCPServerPlugin",
    "BackgroundServicePlugin",
    "ValidatorPlugin",
    "HookPlugin",
    "EventListenerPlugin",
    "CommandPlugin",
    "PluginManager",
    "plugin_manager",
    "PluginInstallResult",
    "HotReloadManager",
    "hot_reload_manager",
]