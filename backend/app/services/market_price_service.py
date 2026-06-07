from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.market_price import MarketPrice
from app.repositories.market_price import MarketPriceRepository
from app.schemas.market_price import MarketPriceCreate
from app.schemas.pagination import Page


class MarketPriceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = MarketPriceRepository(session)

    async def create(self, data: MarketPriceCreate) -> MarketPrice:
        exists = await self._repo.exists(data.entity_id, data.price_date)
        if exists:
            raise HTTPException(
                status_code=409,
                detail="Market price for this entity on this date already exists",
            )
        price = await self._repo.create(data.model_dump())
        await self._session.commit()
        await self._session.refresh(price)
        return price

    async def get(self, price_id: int) -> MarketPrice:
        price = await self._repo.get_by_id(price_id)
        if price is None:
            raise HTTPException(status_code=404, detail="Market price not found")
        return price

    async def list_by_entity(
        self, entity_id: int, skip: int, limit: int
    ) -> Page[MarketPrice]:
        items = await self._repo.get_by_entity_id(entity_id, skip=skip, limit=limit)
        total = await self._repo.count_by_entity(entity_id)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def get_latest(self, entity_id: int) -> MarketPrice:
        price = await self._repo.get_latest_by_entity(entity_id)
        if price is None:
            raise HTTPException(
                status_code=404, detail="No market prices found for this entity"
            )
        return price

    async def get_recent(
        self, entity_id: int, days: int = 30
    ) -> list[MarketPrice]:
        return await self._repo.get_recent_by_entity(entity_id, days=days)

    async def get_range(
        self, entity_id: int, start_date: datetime, end_date: datetime
    ) -> list[MarketPrice]:
        if start_date > end_date:
            raise HTTPException(
                status_code=400, detail="start_date must be before end_date"
            )
        return await self._repo.get_by_date_range(entity_id, start_date, end_date)

    async def bulk_create(
        self, records: list[MarketPriceCreate]
    ) -> list[MarketPrice]:
        created: list[MarketPrice] = []
        for rec in records:
            exists = await self._repo.exists(rec.entity_id, rec.price_date)
            if not exists:
                price = await self._repo.create(rec.model_dump())
                created.append(price)
        if created:
            await self._session.commit()
            for p in created:
                await self._session.refresh(p)
        return created


def get_market_price_service(
    session: AsyncSession = Depends(get_db),
) -> MarketPriceService:
    return MarketPriceService(session)
