"""Status Bar API for plugins."""


from backend.events import publish_event


class StatusBarAPI:
    """API for status bar operations."""

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    async def set_status(self, key: str, value: str, priority: int = 0) -> None:
        """Set a status bar item."""
        await publish_event("statusbar.set", {
            "project_id": self.project_id,
            "key": key,
            "value": value,
            "priority": priority,
        })

    async def remove_status(self, key: str) -> None:
        """Remove a status bar item."""
        await publish_event("statusbar.remove", {
            "project_id": self.project_id,
            "key": key,
        })

    async def show_progress(self, key: str, progress: float, message: str = "") -> None:
        """Show progress in status bar."""
        await publish_event("statusbar.progress", {
            "project_id": self.project_id,
            "key": key,
            "progress": progress,
            "message": message,
        })
