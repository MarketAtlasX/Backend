import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # API Configuration
    api_title: str = os.getenv("API_TITLE", "MarketAtlas")
    api_version: str = os.getenv("API_VERSION", "1.0.0")
    api_debug: bool = os.getenv("API_DEBUG", "False").lower() == "true"

    # Database Configuration
    db_driver: str = os.getenv("DB_DRIVER", "postgresql+asyncpg")
    db_user: str = os.getenv("DB_USER", "postgres")
    db_password: str = os.getenv("DB_PASSWORD", "postgres")
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "marketatlas")
    db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "20"))
    db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    db_echo: bool = os.getenv("DB_ECHO", "False").lower() == "true"

    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Celery Configuration
    celery_broker_url: Optional[str] = os.getenv("CELERY_BROKER_URL")
    celery_result_backend: Optional[str] = os.getenv("CELERY_RESULT_BACKEND")

    # Feature Flags
    enable_workers: bool = os.getenv("ENABLE_WORKERS", "True").lower() == "true"

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
