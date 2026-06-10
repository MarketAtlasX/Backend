from typing import Optional
from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.

    All fields are validated at startup — a missing required variable or a
    type mismatch (e.g. DB_PORT='abc') will raise a descriptive ValidationError
    before the application begins serving traffic.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # API Configuration
    # -------------------------------------------------------------------------
    api_title: str = Field(default="MarketAtlas", alias="API_TITLE")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    api_debug: bool = Field(default=False, alias="API_DEBUG")

    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    db_driver: str = Field(default="postgresql+asyncpg", alias="DB_DRIVER")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="marketatlas", alias="DB_NAME")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE", ge=1, le=100)
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW", ge=0, le=50)
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    # -------------------------------------------------------------------------
    # Market Agents Service (external microservice from separate repo)
    # Runs as ``uvicorn market_agents.services.gateway:app --port 8004``
    # -------------------------------------------------------------------------
    market_agents_url: str = Field(
        default="http://localhost:8004",
        alias="MARKET_AGENTS_URL",
        description="Base URL of the market_agents gateway service",
    )

    # -------------------------------------------------------------------------
    # Knowledge Graph Agent Service (external microservice)
    # Runs as ``uvicorn service:app --port 8005`` in ../knowledge-graph-agent/
    # -------------------------------------------------------------------------
    kg_agent_url: str = Field(
        default="http://localhost:8005",
        alias="KG_AGENT_URL",
        description="Base URL of the knowledge-graph-agent service",
    )

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    enable_workers: bool = Field(default=False, alias="ENABLE_WORKERS")

    # -------------------------------------------------------------------------
    # Computed properties
    # -------------------------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"{self.db_driver}://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """Synchronous PostgreSQL URL for Alembic migrations."""
        sync_driver = self.db_driver.replace("+asyncpg", "")
        return (
            f"{sync_driver}://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
