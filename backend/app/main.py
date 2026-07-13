import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from sqlalchemy import text

from app.cache import cache
from app.chatbot.api.routes import chat_router
from app.chatbot.api.websocket import handle_websocket as chat_ws_handler
from app.chatbot.llm.provider import get_llm, MockLLM
from app.chatbot.pipeline_adapter import run_daily_pipeline
from app.config import settings
from app.database import AsyncSessionLocal, close_db
from app.middleware import MetricsMiddleware, RequestLoggingMiddleware
from app.middleware.ratelimit import RateLimitMiddleware
from app.routes import (
    analysis_router,
    analyze_router,
    backtest_router,
    country_router,
    dashboard_router,
    entity_router,
    event_router,
    globe_router,
    kg_router,
    market_price_router,
    signal_router,
    ws_router,
)
from app.routes.auth import router as auth_router
from app.services.event_broadcaster import EventBroadcaster
from app.services.market_stream_service import MarketStreamService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Startup:
      - Connect Redis cache.
      - Start real-time market streaming via Yahoo Finance WebSocket.
      - Geopolitical events are fetched by Celery Beat every 15 min via KG agent.
    Shutdown:
      - Stop streaming services.
      - Close Redis and DB connections.
    """
    await cache.connect()

    broadcaster = EventBroadcaster()
    app.state.broadcaster = broadcaster
    from app.services.event_broadcaster import set_broadcaster
    set_broadcaster(broadcaster)

    stream_tasks = []

    market_stream = MarketStreamService(broadcaster)
    stream_tasks.append(asyncio.create_task(market_stream.run(), name="market-stream"))

    llm = get_llm()
    llm_provider = type(llm).__name__
    is_mock = isinstance(llm, MockLLM)
    if is_mock:
        logger.warning(
            "⚠ No real LLM available! Chatbot will use MockLLM (keyword templates). "
            "Set GEMINI_API_KEY, OPENAI_API_KEY, or CLAUDE_API_KEY in .env, "
            "or ensure Ollama is running with 'ollama pull qwen2.5:7b && ollama run qwen2.5:7b'"
        )
    else:
        logger.info("LLM provider: %s", llm_provider)

    async def _daily_pipeline_worker():
        logger.info("Starting daily GDELT -> signals pipeline...")
        try:
            result = await run_daily_pipeline()
            status = result.get("status", "unknown")
            logger.info("Daily pipeline: status=%s", status)
        except Exception as exc:
            logger.warning("Daily pipeline failed (non-fatal): %s", exc)

    stream_tasks.append(asyncio.create_task(_daily_pipeline_worker(), name="daily-pipeline"))

    logger.info(
        "MarketAtlas v%s started (workers=%s, streaming=%d, llm=%s)",
        settings.api_version,
        "enabled" if settings.enable_workers else "disabled",
        len(stream_tasks),
        llm_provider,
    )
    yield

    for task in stream_tasks:
        task.cancel()
    await asyncio.gather(*stream_tasks, return_exceptions=True)

    await cache.close()
    await close_db()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.api_debug,
    lifespan=lifespan,
)

# Register middleware (order matters: outermost first)
app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(MetricsMiddleware)

# API v1 group — all data routes under /api/v1 to match frontend proxy
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(event_router)
api_v1_router.include_router(entity_router)
api_v1_router.include_router(market_price_router)
api_v1_router.include_router(signal_router)
api_v1_router.include_router(analysis_router)   # ai_routes with /events prefix
api_v1_router.include_router(kg_router)          # kg_routes with /events prefix
api_v1_router.include_router(analyze_router)     # /analyze, /analyze/v2
api_v1_router.include_router(country_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(globe_router)       # /relations/trade, /relations/military, /ports
api_v1_router.include_router(backtest_router)
app.include_router(api_v1_router)

# Chat router already has /api/v1/chat prefix — include at root
app.include_router(chat_router)

# WebSocket stays at root
app.include_router(ws_router)


@app.websocket("/ws/chat")
async def chat_websocket(websocket):
    await chat_ws_handler(websocket)


@app.get("/health")
@app.get("/api/v1/health")
async def health_check() -> dict:
    """Deep health check — verifies DB connectivity and service status."""
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    redis_ok = cache._redis is not None

    llm = get_llm()
    llm_provider = type(llm).__name__
    is_mock = isinstance(llm, MockLLM)

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": "MarketAtlas",
        "version": settings.api_version,
        "checks": {
            "database": "ok" if db_ok else "down",
            "redis": "ok" if redis_ok else "unavailable",
            "workers": "enabled" if settings.enable_workers else "disabled",
            "llm": f"⚠ MOCK — no real LLM configured" if is_mock else f"ok ({llm_provider})",
        },
    }
