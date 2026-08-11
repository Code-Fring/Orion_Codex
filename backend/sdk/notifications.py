"""Notification API for plugins."""

from typing import Any

from backend.events import publish_event, EventType


class NotificationAPI:
    """API for notifications."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    async def notify(
        self,
        title: str,
        message: str,
        level: str = "info",
        duration: int = 5000,
    ) -> None:
        """Show a notification."""
        await publish_event("notification", {
            "project_id": self.project_id,
            "title": title,
            "message": message,
            "level": level,
            "duration": duration,
        })

    async def info(self, title: str, message: str) -> None:
        """Show info notification."""
        await self.notify(title, message, "info")

    async def warning(self, title: str, message: str) -> None:
        """Show warning notification."""
        await self.notify(title, message, "warning")

    async def error(self, title: str, message: str) -> None:
        """Show error notification."""
        await self.notify(title, message, "error")

    async def success(self, title: str, message: str) -> None:
        """Show success notification."""
        await self.notify(title, message, "success")