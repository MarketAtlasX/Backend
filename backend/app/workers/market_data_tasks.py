"""Celery tasks for market data ingestion.

Offloads yfinance fetching to background workers so the API doesn't block
during potentially slow external data retrieval.
"""

import logging

from app.workers import _run_async
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_market_data_task(
    self, entity_id: int, period: str = "1mo", interval: str = "1d"
) -> dict:
    """Fetch market prices from yfinance and store them, as a background task.

    Usage:
        from app.workers.market_data_tasks import fetch_market_data_task
        task = fetch_market_data_task.delay(entity_id=1, period="6mo")
        result = task.get(timeout=120)
    """
    from app.database import AsyncSessionLocal
    from app.services.market_data_service import MarketDataService
    from app.services.market_price_service import MarketPriceService

    async def _run():
        async with AsyncSessionLocal() as db:
            data_service = MarketDataService(db)
            price_service = MarketPriceService(db)

            records = await data_service.fetch_and_store(
                entity_id=entity_id, period=period, interval=interval
            )
            stored = await price_service.bulk_create(records)

            return {
                "entity_id": entity_id,
                "records_fetched": len(records),
                "records_stored": len(stored),
                "source": "yfinance",
                "status": "completed",
            }

    try:
        return _run_async(_run())
    except ValueError as e:
        logger.error("Market data fetch failed for entity %s: %s", entity_id, e)
        return {"entity_id": entity_id, "error": str(e), "status": "failed"}
    except Exception as e:
        logger.exception("Market data fetch failed for entity %s", entity_id)
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def fetch_all_market_data_task(self, period: str = "1mo", interval: str = "1d") -> dict:
    """Fetch market data for ALL entities with ticker symbols.

    Useful for scheduled bulk updates (e.g., daily market data refresh).

    Usage:
        from app.workers.market_data_tasks import fetch_all_market_data_task
        fetch_all_market_data_task.delay(period="1d")
    """
    from app.database import AsyncSessionLocal
    from app.repositories.entity import EntityRepository
    from app.services.market_data_service import MarketDataService
    from app.services.market_price_service import MarketPriceService

    async def _run():
        import asyncio

        async with AsyncSessionLocal() as db:
            entity_repo = EntityRepository(db)
            all_entities = await entity_repo.get_all(limit=1000)
            entities_with_tickers = [
                e for e in all_entities if e.ticker_symbols
            ]

            results = []
            for entity in entities_with_tickers:
                try:
                    data_service = MarketDataService(db)
                    price_service = MarketPriceService(db)
                    records = await data_service.fetch_and_store(
                        entity_id=entity.id, period=period, interval=interval
                    )
                    stored = await price_service.bulk_create(records)
                    results.append({
                        "entity_id": entity.id,
                        "name": entity.name,
                        "records_stored": len(stored),
                    })
                except Exception as e:
                    logger.warning("Failed to fetch data for %s: %s", entity.name, e)
                # Pace requests to stay clear of Yahoo's unauthenticated rate limit.
                await asyncio.sleep(0.5)

            return {
                "total_entities": len(entities_with_tickers),
                "successful": len(results),
                "results": results,
                "status": "completed",
            }

    return _run_async(_run())
