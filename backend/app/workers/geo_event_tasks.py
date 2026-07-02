"""Celery tasks for geopolitical event ingestion.

Fetches live news from the Knowledge Graph agent microservice and creates
structured Event records in the database, then auto-triggers AI analysis.
"""

import logging

from app.workers import _run_async
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

TICKER_ENTITIES: list[tuple[int, str]] = [
    (3, "AAPL"),
    (33, "SPY"),
    (34, "FXI"),
    (36, "EWJ"),
    (40, "INDA"),
    (41, "TSM"),
    (42, "EWY"),
    (43, "MSFT"),
    (44, "AMZN"),
    (45, "TSLA"),
    (46, "NVDA"),
    (47, "META"),
    (48, "GOOGL"),
    (49, "TSM"),
    (50, "SSNLF"),
    (51, "TM"),
    (52, "JPM"),
    (53, "GS"),
    (54, "BA"),
    (55, "PFE"),
    (56, "SHEL"),
    (57, "2222.SR"),
    (59, "VWAGY"),
    (60, "LVMUY"),
]

COUNTRIES_WITHOUT_TICKERS: list[tuple[str, int]] = [
    ("Russia", 35),
    ("United Kingdom", 37),
    ("Germany", 38),
    ("France", 39),
]


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def fetch_geo_events_for_entity(self, entity_id: int, ticker: str) -> dict:
    """Fetch news for a single entity via KG agent and create Event records.

    Usage:
        from app.workers.geo_event_tasks import fetch_geo_events_for_entity
        fetch_geo_events_for_entity.delay(entity_id=43, ticker="MSFT")
    """
    from app.database import AsyncSessionLocal
    from app.services.event_ingestion_service import EventIngestionService

    async def _run():
        async with AsyncSessionLocal() as db:
            service = EventIngestionService(db)
            new_events = await service.ingest_from_ticker(entity_id, ticker)
            return {
                "entity_id": entity_id,
                "ticker": ticker,
                "new_events": new_events,
                "status": "completed",
            }

    try:
        return _run_async(_run())
    except Exception as e:
        logger.exception("Geo event fetch failed for entity %s (%s)", entity_id, ticker)
        return {"entity_id": entity_id, "ticker": ticker, "error": str(e), "status": "failed"}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def fetch_geo_events_for_country(self, country_name: str, entity_id: int) -> dict:
    """Fetch news for a country via KG agent /analyze-country.

    Usage:
        from app.workers.geo_event_tasks import fetch_geo_events_for_country
        fetch_geo_events_for_country.delay(country_name="Russia", entity_id=35)
    """
    from app.database import AsyncSessionLocal
    from app.services.event_ingestion_service import EventIngestionService

    async def _run():
        async with AsyncSessionLocal() as db:
            service = EventIngestionService(db)
            new_events = await service.ingest_from_country(country_name, entity_id)
            return {
                "country": country_name,
                "entity_id": entity_id,
                "new_events": new_events,
                "status": "completed",
            }

    try:
        return _run_async(_run())
    except Exception as e:
        logger.exception("Geo event fetch failed for country %s", country_name)
        return {"country": country_name, "entity_id": entity_id, "error": str(e), "status": "failed"}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=300)
def fetch_all_geo_events(self) -> dict:
    """Fetch news for ALL entities with tickers and major countries.

    Dispatches individual tasks per entity so they run in parallel across
    the Celery worker pool.

    Usage:
        from app.workers.geo_event_tasks import fetch_all_geo_events
        fetch_all_geo_events.delay()
    """
    results = {"ticker_entities": 0, "country_entities": 0, "tasks_dispatched": 0}

    for entity_id, ticker in TICKER_ENTITIES:
        fetch_geo_events_for_entity.delay(entity_id=entity_id, ticker=ticker)
        results["tasks_dispatched"] += 1
        results["ticker_entities"] += 1

    for country_name, entity_id in COUNTRIES_WITHOUT_TICKERS:
        fetch_geo_events_for_country.delay(country_name=country_name, entity_id=entity_id)
        results["tasks_dispatched"] += 1
        results["country_entities"] += 1

    results["status"] = "dispatched"
    return results
