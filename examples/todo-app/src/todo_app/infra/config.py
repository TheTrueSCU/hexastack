"""Application settings and environment configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Service environment settings."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    service_name: str = "todo-app"
    environment: str = "development"
