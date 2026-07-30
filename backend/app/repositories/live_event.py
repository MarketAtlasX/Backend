from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.live_event import (
    EventAlert,
    EventImpact,
    EventNewsArticle,
    LiveEvent,
    UserEventFilter,
)
from app.repositories.base import BaseRepository


class LiveEventRepository(BaseRepository[LiveEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, LiveEvent)

    async def search(
        self,
        *,
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
    ) -> List[LiveEvent]:
        query = select(self.model)

        if event_type:
            query = query.where(self.model.event_type == event_type)
        if sub_type:
            query = query.where(self.model.sub_type == sub_type)
        if status:
            query = query.where(self.model.status == status)
        if severity_min is not None:
            query = query.where(self.model.severity >= severity_min)
        if severity_max is not None:
            query = query.where(self.model.severity <= severity_max)
        if country_code:
            query = query.where(self.model.country_code == country_code)
        if region:
            query = query.where(self.model.region == region)
        if source:
            query = query.where(self.model.source == source)
        if keyword:
            query = query.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.description.ilike(f"%{keyword}%")
            )
        if sector:
            query = query.where(
                self.model.extra_meta["sectors"].as_string().ilike(f"%{sector}%")
            )

        sort_col = getattr(self.model, sort_by, self.model.first_seen_at)
        order_fn = func.desc if sort_desc else func.asc
        query = query.order_by(order_fn(sort_col)).offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_search(
        self,
        *,
        event_type: Optional[str] = None,
        sub_type: Optional[str] = None,
        status: Optional[str] = None,
        severity_min: Optional[float] = None,
        severity_max: Optional[float] = None,
        country_code: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> int:
        query = select(func.count()).select_from(self.model)

        if event_type:
            query = query.where(self.model.event_type == event_type)
        if sub_type:
            query = query.where(self.model.sub_type == sub_type)
        if status:
            query = query.where(self.model.status == status)
        if severity_min is not None:
            query = query.where(self.model.severity >= severity_min)
        if severity_max is not None:
            query = query.where(self.model.severity <= severity_max)
        if country_code:
            query = query.where(self.model.country_code == country_code)
        if keyword:
            query = query.where(
                self.model.title.ilike(f"%{keyword}%")
                | self.model.description.ilike(f"%{keyword}%")
            )

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_with_relations(self, event_id: str) -> Optional[LiveEvent]:
        query = (
            select(self.model)
            .where(self.model.id == event_id)
            .options(
                selectinload(self.model.impacts).selectinload(EventImpact.affected_assets),
                selectinload(self.model.news_articles),
            )
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_stats(self) -> dict:
        total_q = select(func.count()).select_from(self.model)
        total_result = await self.session.execute(total_q)
        total = total_result.scalar_one()

        rows = await self.session.execute(
            select(self.model.event_type, func.count())
            .group_by(self.model.event_type)
        )
        by_type = dict(rows.all())

        status_rows = await self.session.execute(
            select(self.model.status, func.count())
            .group_by(self.model.status)
        )
        by_status = dict(status_rows.all())

        severity_rows = await self.session.execute(
            select(
                func.floor(self.model.severity).label("bucket"),
                func.count(),
            )
            .group_by("bucket")
            .order_by("bucket")
        )
        by_severity = {f"{int(r[0])}-{int(r[0])+1}": r[1] for r in severity_rows.all()}

        avg_q = select(func.avg(self.model.severity))
        avg_result = await self.session.execute(avg_q)
        avg_severity = avg_result.scalar_one() or 0.0

        impact_avg_q = select(func.avg(self.model.impact_score)).where(
            self.model.impact_score.isnot(None)
        )
        impact_result = await self.session.execute(impact_avg_q)
        avg_impact = impact_result.scalar_one()

        breaking_q = select(func.count()).select_from(self.model).where(
            self.model.status == "breaking"
        )
        breaking_result = await self.session.execute(breaking_q)
        breaking_count = breaking_result.scalar_one()

        return {
            "total": total,
            "by_type": by_type,
            "by_status": by_status,
            "by_severity_bucket": by_severity,
            "avg_severity": round(float(avg_severity), 2),
            "avg_impact_score": round(float(avg_impact), 2) if avg_impact else None,
            "breaking_count": breaking_count,
        }

    async def get_timeline(self, hours: int = 24) -> List[dict]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        buckets = []
        current = cutoff
        while current < datetime.utcnow():
            bucket_end = current + timedelta(hours=1)
            q = (
                select(func.count(), func.avg(self.model.severity))
                .where(self.model.first_seen_at >= current)
                .where(self.model.first_seen_at < bucket_end)
            )
            result = await self.session.execute(q)
            row = result.one()
            count = row[0]
            avg_sev = row[1] or 0.0

            type_q = (
                select(self.model.event_type, func.count())
                .where(self.model.first_seen_at >= current)
                .where(self.model.first_seen_at < bucket_end)
                .group_by(self.model.event_type)
                .order_by(func.count().desc())
                .limit(3)
            )
            type_result = await self.session.execute(type_q)
            top_types = [r[0] for r in type_result.all()]

            buckets.append({
                "bucket": current.strftime("%Y-%m-%dT%H:00:00"),
                "count": count,
                "avg_severity": round(float(avg_sev), 1),
                "top_types": top_types,
            })
            current = bucket_end

        return buckets


class EventImpactRepository(BaseRepository[EventImpact]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EventImpact)

    async def get_by_event(self, event_id: str) -> List[EventImpact]:
        query = (
            select(self.model)
            .where(self.model.event_id == event_id)
            .options(selectinload(self.model.affected_assets))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class EventNewsArticleRepository(BaseRepository[EventNewsArticle]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EventNewsArticle)

    async def get_by_event(self, event_id: str) -> List[EventNewsArticle]:
        query = (
            select(self.model)
            .where(self.model.event_id == event_id)
            .order_by(func.desc(self.model.relevance_score))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def exists_by_url(self, url: str) -> bool:
        query = select(func.count()).select_from(self.model).where(self.model.url == url)
        result = await self.session.execute(query)
        return result.scalar_one() > 0


class EventAlertRepository(BaseRepository[EventAlert]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, EventAlert)

    async def get_unread_by_user(self, user_id: int) -> List[EventAlert]:
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(~self.model.is_read)
            .order_by(func.desc(self.model.created_at))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_read(self, alert_id: str) -> None:
        alert = await self.get_by_id(alert_id)
        if alert:
            alert.is_read = True
            self.session.add(alert)

    async def mark_all_read(self, user_id: int) -> None:
        query = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .where(~self.model.is_read)
        )
        result = await self.session.execute(query)
        alerts = result.scalars().all()
        for alert in alerts:
            alert.is_read = True
            self.session.add(alert)

    async def unread_count(self, user_id: int) -> int:
        query = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.user_id == user_id)
            .where(~self.model.is_read)
        )
        result = await self.session.execute(query)
        return result.scalar_one()


class UserEventFilterRepository(BaseRepository[UserEventFilter]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserEventFilter)

    async def get_by_user(self, user_id: int) -> List[UserEventFilter]:
        query = select(self.model).where(self.model.user_id == user_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())
