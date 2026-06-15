"""Async background workers for MarketAtlas.

Celery tasks handle long-running operations:
- AI analysis pipeline (event → signals)
- Market data fetching (yfinance)
- KG enrichment
"""

from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
