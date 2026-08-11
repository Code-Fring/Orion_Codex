"""Configuration API for plugins."""

from typing import Any

from backend.config.settings import settings


class ConfigurationAPI:
    """API for configuration operations."""

    def __init__(self, plugin_name: str) -> None:
        self.plugin_name = plugin_name

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        # First check plugin-specific config
        plugin_config = getattr(settings, f"PLUGIN_{self.plugin_name.upper()}", {})
        if key in plugin_config:
            return plugin_config[key]

        # Fall back to global settings
        return getattr(settings, key, default)

    def get_all(self) -> dict[str, Any]:
        """Get all configuration."""
        return settings.model_dump()

    def get_plugin_config(self) -> dict[str, Any]:
        """Get plugin-specific configuration."""
        return getattr(settings, f"PLUGIN_{self.plugin_name.upper()}", {})

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value (runtime only)."""
        try:
            setattr(settings, key, value)
            return True
        except Exception:
            return False