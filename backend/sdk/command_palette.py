"""Command Palette API for plugins."""

import asyncio
from collections.abc import Callable
from typing import Any

from backend.events import publish_event


class CommandPaletteAPI:
    """API for command palette operations."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self._commands: dict[str, Callable] = {}

    def register_command(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        category: str = "Custom",
        shortcut: str | None = None,
    ) -> None:
        """Register a command in the palette."""
        self._commands[name] = handler

        # Publish to event bus for UI to pick up
        asyncio.create_task(publish_event("command_palette.register", {
            "project_id": self.project_id,
            "name": name,
            "description": description,
            "category": category,
            "shortcut": shortcut,
        }))

    def unregister_command(self, name: str) -> None:
        """Unregister a command."""
        self._commands.pop(name, None)

        asyncio.create_task(publish_event("command_palette.unregister", {
            "project_id": self.project_id,
            "name": name,
        }))

    async def execute_command(self, name: str, args: dict[str, Any] | None = None) -> Any:
        """Execute a registered command."""
        handler = self._commands.get(name)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(args or {})
            return handler(args or {})
        return None

    def get_commands(self) -> dict[str, Callable]:
        """Get all registered commands."""
        return self._commands.copy()
