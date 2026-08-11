"""Logging API for plugins."""

import logging
from typing import Any

from backend.events import publish_event


class LoggingAPI:
    """API for logging operations."""

    def __init__(self, plugin_name: str) -> None:
        self.logger = logging.getLogger(f"orion.plugins.{plugin_name}")

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)

    async def log_to_ui(self, level: str, message: str, context: dict[str, Any] | None = None) -> None:
        """Log message to UI via event bus."""
        await publish_event("log", {
            "plugin": self.logger.name,
            "level": level,
            "message": message,
            "context": context or {},
        })