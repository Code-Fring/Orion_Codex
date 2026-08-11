"""Application settings for Orion Codex."""


from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    APP_NAME: str = "Orion Codex"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:5173",
    ]

    # Database
    DATABASE_URL: str = "sqlite:///./orion.db"
    DATABASE_ECHO: bool = False

    # Authentication
    SECRET_KEY: str = Field(default="change-me-in-production", min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Providers
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    NVIDIA_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OMNIROUTE_API_KEY: str | None = None

    # Workspace
    WORKSPACE_ROOT: str = "./workspace"
    MAX_PROJECT_SIZE_MB: int = 500

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Plugins
    PLUGIN_DIRS: list[str] = ["./plugins"]

    # Task Queue
    TASK_QUEUE_MAX_SIZE: int = 1000
    TASK_WORKER_COUNT: int = 4


settings = Settings()
