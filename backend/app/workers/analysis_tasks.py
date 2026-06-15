"""Celery tasks for the AI analysis pipeline.

These tasks offload the event → AI → signal workflow to background workers,
allowing the API to return immediately while analysis runs asynchronously.
"""

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_event_task(self, event_id: int, entity_ids: list[int] | None = None) -> dict:
    """Run the full AI analysis pipeline for an event as a background task.

    Calls the same logic as POST /events/{id}/analyze but returns immediately
    with a task ID. Results are stored in the Celery result backend.

    Usage:
        from app.workers.analysis_tasks import analyze_event_task
        task = analyze_event_task.delay(event_id=42)
        result = task.get(timeout=120)  # or poll with task.ready()
    """
    from app.database import AsyncSessionLocal
    from app.repositories.event import EventRepository
    from app.repositories.entity import EntityRepository
    from app.repositories.market_price import MarketPriceRepository
    from app.services.ai_service import ai_service
    from app.services.signal_service import SignalService
    from app.services.kg_service import analyze_stock_knowledge_graph
    from app.schemas.signal import SignalUpdate

    async def _run():
        async with AsyncSessionLocal() as db:
            event_repo = EventRepository(db)
            entity_repo = EntityRepository(db)
            price_repo = MarketPriceRepository(db)
            signal_service = SignalService(db)

            event = await event_repo.get_by_id(event_id)
            if event is None:
                raise ValueError(f"Event {event_id} not found")

            if entity_ids:
                entities = []
                for eid in entity_ids:
                    ent = await entity_repo.get_by_id(eid)
                    if ent:
                        entities.append(ent)
            else:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                from app.models.event import Event as EventModel

                query = (
                    select(EventModel)
                    .where(EventModel.id == event_id)
                    .options(selectinload(EventModel.entities))
                )
                result = await db.execute(query)
                event_obj = result.scalars().first()
                entities = list(event_obj.entities) if event_obj else []

            signals = []
            for entity in entities:
                latest_price = await price_repo.get_latest_by_entity(entity.id)
                current_price = latest_price.close_price if latest_price else None
                recent_prices = await price_repo.get_recent_by_entity(entity.id, days=90)
                price_history = [float(p.close_price) for p in recent_prices] if recent_prices else None
                ticker = entity.ticker_symbols.split(",")[0].strip() if entity.ticker_symbols else None

                result = await ai_service.analyze(
                    event_title=event.title,
                    event_description=event.description,
                    event_type=event.event_type,
                    severity=event.severity,
                    entity_name=entity.name,
                    ticker_symbol=ticker,
                    current_price=current_price,
                    price_history=price_history,
                )

                signal = await signal_service.create(result.to_signal_create(event_id, entity.id))

                if ticker:
                    kg = await analyze_stock_knowledge_graph(ticker)
                    if kg.news:
                        enrichment = (
                            f" [Knowledge Graph] Live news analysis: "
                            f"{len(kg.news)} articles, {len(kg.entities)} entities"
                        )
                        signal = await signal_service.update(
                            signal.id,
                            SignalUpdate(reasoning=signal.reasoning + enrichment),
                        )

                signals.append({
                    "id": signal.id,
                    "signal_type": signal.signal_type,
                    "confidence": float(signal.confidence),
                    "entity_id": entity.id,
                })

            return {"event_id": event_id, "signals": signals, "status": "completed"}

    try:
        return _run_async(_run())
    except Exception as e:
        logger.exception("Analysis task failed for event %s", event_id)
        raise self.retry(exc=e)
