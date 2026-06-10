"""API route handlers."""
from app.routes.event import router as event_router
from app.routes.entity import router as entity_router
from app.routes.market_price import router as market_price_router
from app.routes.signal import router as signal_router
from app.routes.ai_routes import router as analysis_router
from app.routes.kg_routes import router as kg_router
from app.routes.analyze import router as analyze_router
from app.routes.country import router as country_router

__all__ = [
    "event_router",
    "entity_router",
    "market_price_router",
    "signal_router",
    "analysis_router",
    "kg_router",
    "analyze_router",
    "country_router",
]
