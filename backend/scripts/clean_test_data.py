"""Remove test entities (CountryA, CountryB) and the test event from the database."""
import asyncio
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '/Users/divijmazumdar')

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.event import Event
from app.models.entity import Entity
from app.models.event_entity import EventEntity
from app.models.signal import Signal
from app.models.market_price import MarketPrice


async def clean():
    async with AsyncSessionLocal() as session:
        test_entity_names = ["CountryA", "CountryB"]

        for name in test_entity_names:
            result = await session.execute(select(Entity).where(Entity.name == name))
            entity = result.scalars().first()
            if entity:
                await session.execute(
                    select(MarketPrice).where(MarketPrice.entity_id == entity.id)
                )
                await session.execute(
                    select(EventEntity).where(EventEntity.entity_id == entity.id)
                )
                await session.execute(
                    select(Signal).where(Signal.entity_id == entity.id)
                )

        result = await session.execute(
            select(EventEntity).where(
                EventEntity.event_id == 1
            )
        )
        for link in result.scalars().all():
            await session.delete(link)

        for name in test_entity_names:
            result = await session.execute(select(Entity).where(Entity.name == name))
            entity = result.scalars().first()
            if entity:
                await session.delete(entity)

        result = await session.execute(select(Event).where(Event.id == 1))
        event = result.scalars().first()
        if event:
            await session.delete(event)

        await session.commit()
        print("Cleaned: removed CountryA, CountryB, and test event")


if __name__ == "__main__":
    asyncio.run(clean())
