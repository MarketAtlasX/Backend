import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.live_event import (
    EventAlert,
    EventImpact,
    EventNewsArticle,
    LiveEvent,
    UserEventFilter,
)
from app.repositories.entity import EntityRepository
from app.repositories.live_event import (
    EventAlertRepository,
    EventImpactRepository,
    EventNewsArticleRepository,
    LiveEventRepository,
    UserEventFilterRepository,
)
from app.schemas.live_event import (
    EventImpactCreate,
    EventNewsArticleCreate,
    LiveEventCreate,
    LiveEventUpdate,
)
from app.schemas.pagination import Page
from app.services.event_broadcaster import get_broadcaster

logger = logging.getLogger(__name__)


class LiveEventService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = LiveEventRepository(session)
        self._impact_repo = EventImpactRepository(session)
        self._news_repo = EventNewsArticleRepository(session)
        self._alert_repo = EventAlertRepository(session)
        self._filter_repo = UserEventFilterRepository(session)
        self._entity_repo = EntityRepository(session)
        self._broadcaster = get_broadcaster()

    async def create(self, data: LiveEventCreate) -> LiveEvent:
        create_data = data.model_dump(exclude_unset=True)
        if "first_seen_at" not in create_data:
            create_data["first_seen_at"] = datetime.utcnow()
        if "detected_at" not in create_data:
            create_data["detected_at"] = datetime.utcnow()
        create_data["id"] = str(uuid.uuid4())

        event = await self._repo.create(create_data)
        await self._session.commit()
        await self._session.refresh(event)

        await self._broadcaster.broadcast("live_events", {
            "type": "live_event_new",
            "data": self._event_to_dict(event),
            "timestamp": datetime.utcnow().isoformat(),
        })

        await self._check_alerts(event)

        return event

    async def get(self, event_id: str) -> LiveEvent:
        event = await self._repo.get_with_relations(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Live event not found")
        return event

    async def get_brief(self, event_id: str) -> LiveEvent:
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Live event not found")
        return event

    async def update(self, event_id: str, data: LiveEventUpdate) -> LiveEvent:
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        event = await self._repo.update(event_id, update_data)
        if event is None:
            raise HTTPException(status_code=404, detail="Live event not found")
        await self._session.commit()
        await self._session.refresh(event)

        await self._broadcaster.broadcast("live_events", {
            "type": "live_event_update",
            "data": self._event_to_dict(event),
            "timestamp": datetime.utcnow().isoformat(),
        })
        return event

    async def change_status(self, event_id: str, status: str) -> LiveEvent:
        update_data = {"status": status, "updated_at": datetime.utcnow()}
        if status in ("resolved", "archived"):
            update_data["resolved_at"] = datetime.utcnow()
        event = await self._repo.update(event_id, update_data)
        if event is None:
            raise HTTPException(status_code=404, detail="Live event not found")
        await self._session.commit()
        await self._session.refresh(event)

        is_resolved = status in ("resolved", "archived")
        msg_type = "live_event_resolved" if is_resolved else "live_event_update"
        await self._broadcaster.broadcast("live_events", {
            "type": msg_type,
            "data": self._event_to_dict(event),
            "timestamp": datetime.utcnow().isoformat(),
        })
        return event

    async def delete(self, event_id: str) -> None:
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Live event not found")
        await self._repo.delete(event_id)
        await self._session.commit()

    async def search(
        self,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        status: Optional[str] = None,
        severity_min: Optional[float] = None,
        severity_max: Optional[float] = None,
        country_code: Optional[str] = None,
        region: Optional[str] = None,
        source: Optional[str] = None,
        keyword: Optional[str] = None,
        sector: Optional[str] = None,
        sort_by: str = "first_seen_at",
        sort_desc: bool = True,
    ) -> Page[LiveEvent]:
        items = await self._repo.search(
            skip=skip, limit=limit,
            event_type=event_type, sub_type=sub_type, status=status,
            severity_min=severity_min, severity_max=severity_max,
            country_code=country_code, region=region, source=source,
            keyword=keyword, sector=sector,
            sort_by=sort_by, sort_desc=sort_desc,
        )
        total = await self._repo.count_search(
            event_type=event_type, sub_type=sub_type, status=status,
            severity_min=severity_min, severity_max=severity_max,
            country_code=country_code, keyword=keyword,
        )
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def get_stats(self) -> dict:
        return await self._repo.get_stats()

    async def get_timeline(self, hours: int = 24) -> list:
        return await self._repo.get_timeline(hours=hours)

    async def add_impact(self, event_id: str, data: EventImpactCreate) -> EventImpact:
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Live event not found")

        create_data = data.model_dump()
        create_data["id"] = str(uuid.uuid4())
        create_data["event_id"] = event_id

        impact = await self._impact_repo.create(create_data)
        await self._session.flush()

        if event.impact_score is None or (data.impact_score > event.impact_score):
            event.impact_score = data.impact_score
            event.confidence = data.confidence
            event.updated_at = datetime.utcnow()
            self._session.add(event)

        await self._session.commit()
        await self._session.refresh(impact)

        await self._broadcaster.broadcast("impacts", {
            "type": "impact_new",
            "data": self._impact_to_dict(impact),
            "event_id": event_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return impact

    async def get_impacts(self, event_id: str) -> list[EventImpact]:
        return await self._impact_repo.get_by_event(event_id)

    async def add_news_article(
        self, event_id: str, data: EventNewsArticleCreate
    ) -> EventNewsArticle:
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Live event not found")

        if await self._news_repo.exists_by_url(data.url):
            raise HTTPException(status_code=409, detail="News article with this URL already exists")

        create_data = data.model_dump()
        create_data["id"] = str(uuid.uuid4())
        create_data["event_id"] = event_id

        article = await self._news_repo.create(create_data)
        await self._session.commit()
        await self._session.refresh(article)
        return article

    async def get_news(self, event_id: str) -> list[EventNewsArticle]:
        return await self._news_repo.get_by_event(event_id)

    async def get_alerts(self, user_id: int) -> list[EventAlert]:
        return await self._alert_repo.get_unread_by_user(user_id)

    async def get_all_alerts(self, user_id: int) -> list[EventAlert]:
        return await self._alert_repo.get_unread_by_user(user_id)

    async def mark_alert_read(self, alert_id: str) -> None:
        await self._alert_repo.mark_read(alert_id)
        await self._session.commit()

    async def mark_all_alerts_read(self, user_id: int) -> None:
        await self._alert_repo.mark_all_read(user_id)
        await self._session.commit()

    async def alert_unread_count(self, user_id: int) -> int:
        return await self._alert_repo.unread_count(user_id)

    async def get_filters(self, user_id: int) -> list[UserEventFilter]:
        return await self._filter_repo.get_by_user(user_id)

    async def create_filter(
        self, user_id: int, name: str, filter_config: dict, is_default: bool = False
    ) -> UserEventFilter:
        filter_obj = UserEventFilter(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            filter_config=filter_config,
            is_default=is_default,
        )
        await self._filter_repo.create(filter_obj.__dict__)
        await self._session.commit()
        return filter_obj

    async def _check_alerts(self, event: LiveEvent) -> None:
        try:
            if event.severity >= 7.0:
                alert = EventAlert(
                    id=str(uuid.uuid4()),
                    event_id=event.id,
                    rule_name="high_severity",
                    title=f"High Severity Event: {event.title}",
                    message=(
                        f"Event with severity {event.severity}/10 detected:"
                        f" {event.description}"
                    ),
                )
                self._session.add(alert)
                await self._session.flush()

                await self._broadcaster.broadcast("alerts", {
                    "type": "alert",
                    "data": {
                        "id": alert.id,
                        "event_id": alert.event_id,
                        "rule_name": alert.rule_name,
                        "title": alert.title,
                        "message": alert.message,
                        "created_at": alert.created_at.isoformat(),
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            logger.warning("Alert check failed (non-fatal): %s", e)

    def _event_to_dict(self, event: LiveEvent) -> dict:
        return {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type,
            "sub_type": event.sub_type,
            "severity": event.severity,
            "impact_score": event.impact_score,
            "confidence": event.confidence,
            "status": event.status,
            "source": event.source,
            "lat": event.lat,
            "lng": event.lng,
            "country_code": event.country_code,
            "region": event.region,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "first_seen_at": event.first_seen_at.isoformat() if event.first_seen_at else None,
            "updated_at": event.updated_at.isoformat() if event.updated_at else None,
        }

    def _impact_to_dict(self, impact: EventImpact) -> dict:
        return {
            "id": impact.id,
            "event_id": impact.event_id,
            "entity_name": impact.entity_name,
            "entity_type": impact.entity_type,
            "impact_direction": impact.impact_direction,
            "impact_score": impact.impact_score,
            "confidence": impact.confidence,
            "impact_type": impact.impact_type,
            "analysis_summary": impact.analysis_summary,
        }


def get_live_event_service(session: AsyncSession = Depends(get_db)) -> LiveEventService:
    return LiveEventService(session)
