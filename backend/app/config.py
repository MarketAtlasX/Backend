from pathlib import Path

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
        env_file=Path(__file__).resolve().parents[1] / ".env",
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
    # Redis Configuration
    # -------------------------------------------------------------------------
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
        description="Redis connection string for caching and Celery broker",
    )

    # -------------------------------------------------------------------------
    # Celery Configuration
    # -------------------------------------------------------------------------
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        alias="CELERY_BROKER_URL",
        description="Celery broker URL (Redis)",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        alias="CELERY_RESULT_BACKEND",
        description="Celery result backend URL (Redis)",
    )

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Auth Configuration
    # -------------------------------------------------------------------------
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_algorithm: str = Field(alias="JWT_ALGORITHM", default="HS256")
    jwt_expiry_hours: int = Field(alias="JWT_EXPIRY_HOURS", default=24)

    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # AI / LLM Configuration
    # -------------------------------------------------------------------------
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    claude_api_key: str = Field(default="", alias="CLAUDE_API_KEY")

    # -------------------------------------------------------------------------
    # Financial Data API
    # -------------------------------------------------------------------------
    alpha_vantage_api_key: str = Field(default="", alias="ALPHA_VANTAGE_API_KEY")

    # -------------------------------------------------------------------------
    # World State Service (external microservice from separate repo)
    # Runs as ``uvicorn world_state.server:app --port 8006`` in ../world_state/
    # -------------------------------------------------------------------------
    world_state_url: str = Field(
        default="http://localhost:8006",
        alias="WORLD_STATE_URL",
        description="Base URL of the Dynamic World State service",
    )
    world_state_api_key: str = Field(alias="WORLD_STATE_API_KEY")

    # -------------------------------------------------------------------------
    # Memory Service (external microservice from separate repo)
    # Runs as ``uvicorn main:app --port 8010`` in ../memory/
    # -------------------------------------------------------------------------
    memory_url: str = Field(
        default="http://localhost:8010",
        alias="MEMORY_URL",
        description="Base URL of the Geopolitical Episodic Memory (GEM) service",
    )

    # -------------------------------------------------------------------------
    # Graph Engine Service (external microservice from separate repo)
    # Runs as ``uvicorn graph_engine.main:app --port 8005`` in ../graph_engine/
    # -------------------------------------------------------------------------
    graph_engine_url: str = Field(
        default="http://localhost:8005",
        alias="GRAPH_ENGINE_URL",
        description="Base URL of the Graph Engine service",
    )

    # -------------------------------------------------------------------------
    # Simulator Service (external microservice from separate repo)
    # Runs as ``uvicorn simulator.main:app --port 8007`` in ../simulator/
    # -------------------------------------------------------------------------
    simulator_url: str = Field(
        default="http://localhost:8007",
        alias="SIMULATOR_URL",
        description="Base URL of the Scenario Simulator service",
    )

    # -------------------------------------------------------------------------
    # Sector Market Data Feed
    # Predefined sector -> ticker map used to compute per-sector return and
    # volatility. If the feed is unavailable, the simulator falls back to its
    # own static sector betas.
    # -------------------------------------------------------------------------
    sector_tickers: str = Field(
        default=(
            "technology:AAPL,MSFT,NVDA;"
            "semiconductors:AMD,INTC,AVGO;"
            "energy:XOM,CVX,COP;"
            "defense:LMT,RTX,NOC;"
            "financials:JPM,BAC,GS;"
            "healthcare:JNJ,UNH,LLY;"
            "consumer_cyclical:AMZN,TSLA,HD;"
            "consumer_defensive:PG,KO,WMT;"
            "utilities:NEE,DUK,SO;"
            "materials:LIN,SHW,FCX;"
            "commodities:GLD,SLV,USO"
        ),
        alias="SECTOR_TICKERS",
        description="Semicolon-separated 'sector:ticker1,ticker2' pairs",
    )
    sector_cache_ttl_seconds: int = Field(
        default=1800,
        alias="SECTOR_CACHE_TTL_SECONDS",
        ge=60,
        description="TTL for cached sector metrics (seconds)",
    )

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins",
    )

    # -------------------------------------------------------------------------
    # Feature Flags
    # -------------------------------------------------------------------------
    enable_workers: bool = Field(default=False, alias="ENABLE_WORKERS")

    @model_validator(mode="after")
    def reject_insecure_jwt_secret(self) -> "Settings":
        if self.jwt_secret == "change-me-in-production":
            raise ValueError("JWT_SECRET must not use the placeholder value")
        return self

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
