from enum import StrEnum
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    ENV: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True
    API_PORT: int = 8000
    API_TOKEN: SecretStr = SecretStr("change_me_in_production")
    STORAGE_BACKEND: str = "memory"  # memory | file | redis
    DATA_DIR: str = "data"
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
