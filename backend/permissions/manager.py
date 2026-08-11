"""Permission system for Orion Codex."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels."""
    DENIED = "denied"
    PROMPT = "prompt"
    GRANTED = "granted"


class PermissionCategory(Enum):
    """Permission categories."""
    FILESYSTEM = "filesystem"
    TERMINAL = "terminal"
    NETWORK = "network"
    GIT = "git"
    PROVIDERS = "providers"
    MEMORY = "memory"
    WORKSPACE = "workspace"
    BACKGROUND = "background"
    AGENTS = "agents"
    TASKS = "tasks"
    SETTINGS = "settings"
    UI = "ui"
    NOTIFICATIONS = "notifications"


@dataclass
class Permission:
    """Permission definition."""
    name: str
    category: PermissionCategory
    description: str
    risk_level: str = "medium"  # low, medium, high, critical
    default_level: PermissionLevel = PermissionLevel.PROMPT


# Core permissions
CORE_PERMISSIONS = {
    # Filesystem
    "filesystem:read": Permission(
        "filesystem:read",
        PermissionCategory.FILESYSTEM,
        "Read files from workspace",
        "low",
        PermissionLevel.GRANTED,
    ),
    "filesystem:write": Permission(
        "filesystem:write",
        PermissionCategory.FILESYSTEM,
        "Write files to workspace",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "filesystem:delete": Permission(
        "filesystem:delete",
        PermissionCategory.FILESYSTEM,
        "Delete files from workspace",
        "high",
        PermissionLevel.PROMPT,
    ),
    "filesystem:list": Permission(
        "filesystem:list",
        PermissionCategory.FILESYSTEM,
        "List directory contents",
        "low",
        PermissionLevel.GRANTED,
    ),

    # Terminal
    "terminal:execute": Permission(
        "terminal:execute",
        PermissionCategory.TERMINAL,
        "Execute terminal commands",
        "high",
        PermissionLevel.PROMPT,
    ),
    "terminal:read": Permission(
        "terminal:read",
        PermissionCategory.TERMINAL,
        "Read terminal output",
        "low",
        PermissionLevel.GRANTED,
    ),

    # Network
    "network:http": Permission(
        "network:http",
        PermissionCategory.NETWORK,
        "Make HTTP requests",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "network:websocket": Permission(
        "network:websocket",
        PermissionCategory.NETWORK,
        "Open WebSocket connections",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "network:listen": Permission(
        "network:listen",
        PermissionCategory.NETWORK,
        "Listen on network ports",
        "high",
        PermissionLevel.PROMPT,
    ),

    # Git
    "git:read": Permission(
        "git:read",
        PermissionCategory.GIT,
        "Read git repository",
        "low",
        PermissionLevel.GRANTED,
    ),
    "git:write": Permission(
        "git:write",
        PermissionCategory.GIT,
        "Write to git repository (commit, push)",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "git:admin": Permission(
        "git:admin",
        PermissionCategory.GIT,
        "Git admin operations (reset, rebase)",
        "high",
        PermissionLevel.PROMPT,
    ),

    # Providers
    "providers:list": Permission(
        "providers:list",
        PermissionCategory.PROVIDERS,
        "List available AI providers",
        "low",
        PermissionLevel.GRANTED,
    ),
    "providers:use": Permission(
        "providers:use",
        PermissionCategory.PROVIDERS,
        "Use AI providers",
        "low",
        PermissionLevel.GRANTED,
    ),
    "providers:configure": Permission(
        "providers:configure",
        PermissionCategory.PROVIDERS,
        "Configure AI providers",
        "medium",
        PermissionLevel.PROMPT,
    ),

    # Memory
    "memory:read": Permission(
        "memory:read",
        PermissionCategory.MEMORY,
        "Read from memory store",
        "low",
        PermissionLevel.GRANTED,
    ),
    "memory:write": Permission(
        "memory:write",
        PermissionCategory.MEMORY,
        "Write to memory store",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "memory:delete": Permission(
        "memory:delete",
        PermissionCategory.MEMORY,
        "Delete from memory store",
        "high",
        PermissionLevel.PROMPT,
    ),

    # Workspace
    "workspace:read": Permission(
        "workspace:read",
        PermissionCategory.WORKSPACE,
        "Read workspace info",
        "low",
        PermissionLevel.GRANTED,
    ),
    "workspace:write": Permission(
        "workspace:write",
        PermissionCategory.WORKSPACE,
        "Modify workspace",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "workspace:create": Permission(
        "workspace:create",
        PermissionCategory.WORKSPACE,
        "Create new workspaces",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "workspace:delete": Permission(
        "workspace:delete",
        PermissionCategory.WORKSPACE,
        "Delete workspaces",
        "high",
        PermissionLevel.PROMPT,
    ),

    # Background tasks
    "background:tasks": Permission(
        "background:tasks",
        PermissionCategory.BACKGROUND,
        "Run background tasks",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "background:services": Permission(
        "background:services",
        PermissionCategory.BACKGROUND,
        "Manage background services",
        "high",
        PermissionLevel.PROMPT,
    ),

    # Agents
    "agents:execute": Permission(
        "agents:execute",
        PermissionCategory.AGENTS,
        "Execute agents",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "agents:manage": Permission(
        "agents:manage",
        PermissionCategory.AGENTS,
        "Manage agent configurations",
        "medium",
        PermissionLevel.PROMPT,
    ),

    # Tasks
    "tasks:manage": Permission(
        "tasks:manage",
        PermissionCategory.TASKS,
        "Manage task queue",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "tasks:execute": Permission(
        "tasks:execute",
        PermissionCategory.TASKS,
        "Execute tasks",
        "medium",
        PermissionLevel.PROMPT,
    ),

    # Settings
    "settings:read": Permission(
        "settings:read",
        PermissionCategory.SETTINGS,
        "Read settings",
        "low",
        PermissionLevel.GRANTED,
    ),
    "settings:write": Permission(
        "settings:write",
        PermissionCategory.SETTINGS,
        "Write settings",
        "medium",
        PermissionLevel.PROMPT,
    ),

    # UI
    "ui:panels": Permission(
        "ui:panels",
        PermissionCategory.UI,
        "Create/manage UI panels",
        "medium",
        PermissionLevel.PROMPT,
    ),
    "ui:notifications": Permission(
        "ui:notifications",
        PermissionCategory.NOTIFICATIONS,
        "Show notifications",
        "low",
        PermissionLevel.GRANTED,
    ),
}


@dataclass
class PermissionRequest:
    """Permission request from a plugin."""
    plugin_name: str
    permissions: list[str]
    reason: str
    timestamp: float = field(default_factory=lambda: __import__('time').time())


class PermissionManager:
    """Manages permissions for plugins."""

    def __init__(self) -> None:
        self._plugin_permissions: dict[str, dict[str, PermissionLevel]] = {}
        self._pending_requests: list[PermissionRequest] = []
        self._approval_callbacks: list[Callable[[PermissionRequest], Any]] = []

    def check_permission(self, plugin_name: str, permission: str) -> PermissionLevel:
        """Check if a plugin has a permission."""
        plugin_perms = self._plugin_permissions.get(plugin_name, {})
        return plugin_perms.get(permission, PermissionLevel.PROMPT)

    def grant_permission(self, plugin_name: str, permission: str) -> None:
        """Grant a permission to a plugin."""
        if plugin_name not in self._plugin_permissions:
            self._plugin_permissions[plugin_name] = {}
        self._plugin_permissions[plugin_name][permission] = PermissionLevel.GRANTED
        logger.info(f"Granted {permission} to {plugin_name}")

    def deny_permission(self, plugin_name: str, permission: str) -> None:
        """Deny a permission to a plugin."""
        if plugin_name not in self._plugin_permissions:
            self._plugin_permissions[plugin_name] = {}
        self._plugin_permissions[plugin_name][permission] = PermissionLevel.DENIED
        logger.info(f"Denied {permission} to {plugin_name}")

    def request_permissions(self, plugin_name: str, permissions: list[str], reason: str) -> PermissionRequest:
        """Request permissions for a plugin."""
        request = PermissionRequest(
            plugin_name=plugin_name,
            permissions=permissions,
            reason=reason,
        )
        self._pending_requests.append(request)
        logger.info(f"Permission request from {plugin_name}: {permissions}")

        # Notify callbacks
        for callback in self._approval_callbacks:
            try:
                callback(request)
            except Exception as e:
                logger.error(f"Error in permission callback: {e}")

        return request

    def approve_request(self, request: PermissionRequest) -> None:
        """Approve a permission request."""
        for perm in request.permissions:
            self.grant_permission(request.plugin_name, perm)
        self._pending_requests.remove(request)

    def deny_request(self, request: PermissionRequest) -> None:
        """Deny a permission request."""
        for perm in request.permissions:
            self.deny_permission(request.plugin_name, perm)
        self._pending_requests.remove(request)

    def get_pending_requests(self) -> list[PermissionRequest]:
        """Get all pending permission requests."""
        return self._pending_requests.copy()

    def get_plugin_permissions(self, plugin_name: str) -> dict[str, PermissionLevel]:
        """Get all permissions for a plugin."""
        return self._plugin_permissions.get(plugin_name, {}).copy()

    def get_all_permissions(self) -> dict[str, Permission]:
        """Get all core permissions."""
        return CORE_PERMISSIONS.copy()

    def get_permissions_by_category(self, category: PermissionCategory) -> list[Permission]:
        """Get permissions by category."""
        return [p for p in CORE_PERMISSIONS.values() if p.category == category]

    def add_approval_callback(self, callback: Callable[[PermissionRequest], Any]) -> None:
        """Add a callback for permission approval requests."""
        self._approval_callbacks.append(callback)

    def remove_approval_callback(self, callback: Callable[[PermissionRequest], Any]) -> None:
        """Remove a callback."""
        if callback in self._approval_callbacks:
            self._approval_callbacks.remove(callback)

    def has_permission(self, plugin_name: str, permission: str) -> bool:
        """Check if plugin has a permission (granted or default granted)."""
        level = self.check_permission(plugin_name, permission)
        if level == PermissionLevel.GRANTED:
            return True

        # Check default
        perm_def = CORE_PERMISSIONS.get(permission)
        if perm_def and perm_def.default_level == PermissionLevel.GRANTED:
            return True

        return False


# Global permission manager
permission_manager = PermissionManager()
