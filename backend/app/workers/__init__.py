"""Async background workers for MarketAtlas.

Celery tasks handle long-running operations:
- AI analysis pipeline (event → signals)
- Market data fetching (yfinance)
- KG enrichment
"""

import asyncio

from app.workers.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from a sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


__all__ = ["celery_app", "_run_async"]
