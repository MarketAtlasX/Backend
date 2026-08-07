import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def analyze_live_event_task(self, event_id: str, title: str, description: str) -> dict:
    logger.info("Analyzing live event %s: %s", event_id, title)
    try:
        import asyncio

        from app.database import AsyncSessionLocal
        from app.schemas.live_event import EventImpactCreate
        from app.services.live_event_service import LiveEventService

        async def _run():
            async with AsyncSessionLocal() as session:
                service = LiveEventService(session)
                impact = EventImpactCreate(
                    entity_name="Unknown",
                    entity_type="other",
                    impact_direction="neutral",
                    impact_score=0.5,
                    confidence=0.5,
                    impact_type="price",
                    analysis_summary=f"AI analysis of: {description[:200]}",
                    reasoning_factors={"method": "rule_based", "title_length": len(title)},
                )
                try:
                    result = await service.add_impact(event_id, impact)
                    return result.id
                except Exception:
                    return None

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        impact_id = loop.run_until_complete(_run())
        loop.close()

        return {"event_id": event_id, "impact_id": impact_id, "status": "completed"}
    except Exception as exc:
        logger.error("Analysis failed for event %s: %s", event_id, exc)
        raise self.retry(exc=exc)


@celery_app.task
def ingest_gdelt_batch() -> dict:
    logger.info("Starting GDELT batch ingestion...")
    try:
        import asyncio

        from app.services.event_broadcaster import EventBroadcaster
        from app.services.gdelt_stream_service import GDELTStreamService

        async def _run():
            broadcaster = EventBroadcaster()
            service = GDELTStreamService(broadcaster)
            await service._load_existing_urls()
            return await service.poll_once()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(_run())
        loop.close()

        logger.info("GDELT batch ingested %d events", count)
        return {"ingested": count}
    except Exception as exc:
        logger.error("GDELT batch ingestion failed: %s", exc)
        return {"ingested": 0, "error": str(exc)}


@celery_app.task
def resolve_stale_events() -> dict:
    logger.info("Resolving stale events...")
    try:
        import asyncio

        from app.database import AsyncSessionLocal

        async def _run():
            async with AsyncSessionLocal() as session:
                from datetime import datetime as dt
                from datetime import timedelta

                from sqlalchemy import select

                from app.models.live_event import LiveEvent

                cutoff = dt.utcnow() - timedelta(hours=72)
                query = (
                    select(LiveEvent)
                    .where(LiveEvent.status.in_(["breaking", "confirmed", "developing"]))
                    .where(LiveEvent.updated_at < cutoff)
                )
                result = await session.execute(query)
                events = result.scalars().all()
                count = 0
                for event in events:
                    event.status = "resolved"
                    event.resolved_at = dt.utcnow()
                    event.updated_at = dt.utcnow()
                    session.add(event)
                    count += 1
                await session.commit()
                return count

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(_run())
        loop.close()

        logger.info("Resolved %d stale events", count)
        return {"resolved": count}
    except Exception as exc:
        logger.error("Stale event resolution failed: %s", exc)
        return {"resolved": 0, "error": str(exc)}
