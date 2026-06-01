from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_title: str = "MarketAtlas"
    api_version: str = "1.0.0"
    api_debug: bool = False

    # Database Configuration
    db_driver: str = "postgresql+asyncpg"
    db_user: str
    db_password: str
    db_host: str
    db_port: int = 5432
    db_name: str
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_echo: bool = False

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # Celery Configuration
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    # Feature Flags
    enable_workers: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"{self.db_driver}://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL, defaults to Redis."""
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL, defaults to Redis."""
        return self.celery_result_backend or self.redis_url


settings = Settings()
