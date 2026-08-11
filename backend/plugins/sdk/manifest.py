"""Plugin manifest and type definitions."""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class PluginType(Enum):
    """Types of plugins."""
    AI_PROVIDER = "ai_provider"
    AGENT = "agent"
    TOOL = "tool"
    UI_PANEL = "ui_panel"
    THEME = "theme"
    DASHBOARD = "dashboard"
    MEMORY_PROVIDER = "memory_provider"
    MCP_SERVER = "mcp_server"
    BACKGROUND_SERVICE = "background_service"
    VALIDATOR = "validator"
    HOOK = "hook"
    EVENT_LISTENER = "event_listener"
    PROVIDER = "provider"
    MODEL = "model"
    COMMAND = "command"


class PluginPermission(Enum):
    """Plugin permissions."""
    FILESYSTEM_READ = "filesystem:read"
    FILESYSTEM_WRITE = "filesystem:write"
    FILESYSTEM_DELETE = "filesystem:delete"
    TERMINAL_EXECUTE = "terminal:execute"
    NETWORK_HTTP = "network:http"
    NETWORK_WEBSOCKET = "network:websocket"
    GIT_READ = "git:read"
    GIT_WRITE = "git:write"
    PROVIDERS_LIST = "providers:list"
    PROVIDERS_USE = "providers:use"
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    BACKGROUND_TASKS = "background:tasks"
    AGENTS_EXECUTE = "agents:execute"
    TASKS_MANAGE = "tasks:manage"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    UI_PANELS = "ui:panels"
    NOTIFICATIONS = "notifications"


@dataclass
class PluginDependency:
    """Plugin dependency specification."""
    name: str
    version: str = "*"
    optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "optional": self.optional,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginDependency":
        return cls(
            name=data["name"],
            version=data.get("version", "*"),
            optional=data.get("optional", False),
        )


@dataclass
class PluginManifest:
    """Plugin manifest (plugin.json)."""
    name: str
    version: str
    author: str
    description: str
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    plugin_type: PluginType = PluginType.TOOL
    entry_point: str = "main.py"
    min_orion_version: str = "0.1.0"
    max_orion_version: str | None = None
    supported_platforms: list[str] = field(default_factory=lambda: ["win32", "linux", "darwin"])
    dependencies: list[PluginDependency] = field(default_factory=list)
    permissions: list[PluginPermission] = field(default_factory=list)
    config_schema: dict[str, Any] | None = None
    provides: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "license": self.license,
            "homepage": self.homepage,
            "repository": self.repository,
            "plugin_type": self.plugin_type.value,
            "entry_point": self.entry_point,
            "min_orion_version": self.min_orion_version,
            "max_orion_version": self.max_orion_version,
            "supported_platforms": self.supported_platforms,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "permissions": [p.value for p in self.permissions],
            "config_schema": self.config_schema,
            "provides": self.provides,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginManifest":
        return cls(
            name=data["name"],
            version=data["version"],
            author=data["author"],
            description=data["description"],
            license=data.get("license", "MIT"),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            plugin_type=PluginType(data.get("plugin_type", "tool")),
            entry_point=data.get("entry_point", "main.py"),
            min_orion_version=data.get("min_orion_version", "0.1.0"),
            max_orion_version=data.get("max_orion_version"),
            supported_platforms=data.get("supported_platforms", ["win32", "linux", "darwin"]),
            dependencies=[PluginDependency.from_dict(d) for d in data.get("dependencies", [])],
            permissions=[PluginPermission(p) for p in data.get("permissions", [])],
            config_schema=data.get("config_schema"),
            provides=data.get("provides", []),
            tags=data.get("tags", []),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "PluginManifest":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load_from_file(cls, path: Path) -> "PluginManifest":
        return cls.from_json(path.read_text())

    def save_to_file(self, path: Path) -> None:
        path.write_text(self.to_json())


@dataclass
class PluginMetadata:
    """Plugin metadata for runtime."""
    manifest: PluginManifest
    path: Path
    loaded: bool = False
    enabled: bool = False
    error: str | None = None
    instance: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "author": self.manifest.author,
            "description": self.manifest.description,
            "type": self.manifest.plugin_type.value,
            "loaded": self.loaded,
            "enabled": self.enabled,
            "error": self.error,
            "path": str(self.path),
        }