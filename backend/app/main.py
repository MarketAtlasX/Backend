from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import db_manager
from app.routes import (
    event_router,
    entity_router,
    market_price_router,
    signal_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events."""
    # Startup
    await db_manager.init_db()
    print("✓ Database initialized")
    yield
    # Shutdown
    await db_manager.close()
    print("✓ Database connection closed")


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


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MarketAtlas",
    }
