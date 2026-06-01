"""API route handlers."""
from app.routes.event import router as event_router
from app.routes.entity import router as entity_router
from app.routes.market_price import router as market_price_router
from app.routes.signal import router as signal_router

__all__ = [
    "event_router",
    "entity_router",
    "market_price_router",
    "signal_router",
]
