from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import close_db
from app.routes import (
    event_router,
    entity_router,
    market_price_router,
    signal_router,
    analysis_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Startup:  nothing — schema management is Alembic's responsibility, not
              the application's. Run `alembic upgrade head` before starting.
    Shutdown: dispose the async connection pool cleanly.
    """
    yield
    await close_db()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.api_debug,
    lifespan=lifespan,
)

# Include all routers
app.include_router(event_router)
app.include_router(entity_router)
app.include_router(market_price_router)
app.include_router(signal_router)
app.include_router(analysis_router)


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MarketAtlas",
        "version": settings.api_version,
    }
