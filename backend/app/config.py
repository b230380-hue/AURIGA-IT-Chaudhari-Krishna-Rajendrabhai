"""PharmaFlow application configuration."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    APP_NAME: str = "PharmaFlow"
    APP_SUBTITLE: str = "Expiry-Aware Pharmacy Inventory"
    APP_VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "pharmaflow.db",
    )

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    # Expiry alert defaults
    DEFAULT_EXPIRY_ALERT_DAYS: int = 30
    CRITICAL_DAYS_THRESHOLD: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
