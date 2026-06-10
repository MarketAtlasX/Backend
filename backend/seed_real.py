"""Seed the database with real entities (countries + companies) with known coordinates."""

import asyncio
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '/Users/divijmazumdar')

from app.database import AsyncSessionLocal
from app.models.entity import Entity
from app.models.event import Event
from app.models.event_entity import EventEntity
from datetime import datetime

REAL_ENTITIES = [
    # Countries with lat/lng (capital city coords)
    {"name": "United States", "entity_type": "country", "country_code": "US", "latitude": 38.9072, "longitude": -77.0369, "ticker_symbols": "SPY"},
    {"name": "China", "entity_type": "country", "country_code": "CN", "latitude": 39.9042, "longitude": 116.4074, "ticker_symbols": "FXI"},
    {"name": "Russia", "entity_type": "country", "country_code": "RU", "latitude": 55.7558, "longitude": 37.6173},
    {"name": "Japan", "entity_type": "country", "country_code": "JP", "latitude": 35.6762, "longitude": 139.6503, "ticker_symbols": "EWJ"},
    {"name": "United Kingdom", "entity_type": "country", "country_code": "GB", "latitude": 51.5074, "longitude": -0.1278},
    {"name": "Germany", "entity_type": "country", "country_code": "DE", "latitude": 52.5200, "longitude": 13.4050},
    {"name": "France", "entity_type": "country", "country_code": "FR", "latitude": 48.8566, "longitude": 2.3522},
    {"name": "India", "entity_type": "country", "country_code": "IN", "latitude": 28.6139, "longitude": 77.2090, "ticker_symbols": "INDA"},
    {"name": "Taiwan", "entity_type": "country", "country_code": "TW", "latitude": 25.0330, "longitude": 121.5654, "ticker_symbols": "TSM"},
    {"name": "South Korea", "entity_type": "country", "country_code": "KR", "latitude": 37.5665, "longitude": 126.9780, "ticker_symbols": "EWY"},
    # Major tech companies with HQ coords
    {"name": "Apple Inc", "entity_type": "company", "country_code": "US", "latitude": 37.3349, "longitude": -122.0090, "ticker_symbols": "AAPL"},
    {"name": "Microsoft", "entity_type": "company", "country_code": "US", "latitude": 47.6397, "longitude": -122.1281, "ticker_symbols": "MSFT"},
    {"name": "Amazon", "entity_type": "company", "country_code": "US", "latitude": 47.6220, "longitude": -122.3368, "ticker_symbols": "AMZN"},
    {"name": "Tesla Inc", "entity_type": "company", "country_code": "US", "latitude": 30.2237, "longitude": -97.7550, "ticker_symbols": "TSLA"},
    {"name": "NVIDIA Corporation", "entity_type": "company", "country_code": "US", "latitude": 37.3953, "longitude": -121.9775, "ticker_symbols": "NVDA"},
    {"name": "Meta Platforms", "entity_type": "company", "country_code": "US", "latitude": 37.4848, "longitude": -122.1482, "ticker_symbols": "META"},
    {"name": "Alphabet Inc", "entity_type": "company", "country_code": "US", "latitude": 37.4220, "longitude": -122.0841, "ticker_symbols": "GOOGL"},
    {"name": "TSMC", "entity_type": "company", "country_code": "TW", "latitude": 22.9970, "longitude": 120.1895, "ticker_symbols": "TSM"},
    {"name": "Samsung Electronics", "entity_type": "company", "country_code": "KR", "latitude": 37.2752, "longitude": 127.1345, "ticker_symbols": "SSNLF"},
    {"name": "Toyota Motor Corp", "entity_type": "company", "country_code": "JP", "latitude": 35.0116, "longitude": 137.1556, "ticker_symbols": "TM"},
    {"name": "JPMorgan Chase", "entity_type": "company", "country_code": "US", "latitude": 40.7550, "longitude": -73.9844, "ticker_symbols": "JPM"},
    {"name": "Goldman Sachs", "entity_type": "company", "country_code": "US", "latitude": 40.7164, "longitude": -74.0095, "ticker_symbols": "GS"},
    {"name": "Boeing", "entity_type": "company", "country_code": "US", "latitude": 47.6319, "longitude": -122.3066, "ticker_symbols": "BA"},
    {"name": "Pfizer Inc", "entity_type": "company", "country_code": "US", "latitude": 40.7424, "longitude": -73.9740, "ticker_symbols": "PFE"},
    {"name": "Shell plc", "entity_type": "company", "country_code": "GB", "latitude": 51.5094, "longitude": -0.1276, "ticker_symbols": "SHEL"},
    {"name": "Saudi Aramco", "entity_type": "company", "country_code": "SA", "latitude": 24.7167, "longitude": 46.6750, "ticker_symbols": "2222.SR"},
    {"name": "PetroChina", "entity_type": "company", "country_code": "CN", "latitude": 39.9000, "longitude": 116.4000, "ticker_symbols": "PTR"},
    {"name": "Volkswagen Group", "entity_type": "company", "country_code": "DE", "latitude": 52.4334, "longitude": 10.7949, "ticker_symbols": "VWAGY"},
    {"name": "LVMH", "entity_type": "company", "country_code": "FR", "latitude": 48.8557, "longitude": 2.3149, "ticker_symbols": "LVMUY"},
    # Financial hubs as entities
    {"name": "New York Stock Exchange", "entity_type": "index", "country_code": "US", "latitude": 40.7069, "longitude": -74.0113},
    {"name": "London Stock Exchange", "entity_type": "index", "country_code": "GB", "latitude": 51.5151, "longitude": -0.0993},
    {"name": "Tokyo Stock Exchange", "entity_type": "index", "country_code": "JP", "latitude": 35.6819, "longitude": 139.7778},
    {"name": "Shanghai Stock Exchange", "entity_type": "index", "country_code": "CN", "latitude": 31.2304, "longitude": 121.4737},
]


async def seed():
    async with AsyncSessionLocal() as session:
        existing = 0
        created = 0
        for data in REAL_ENTITIES:
            from sqlalchemy import select
            result = await session.execute(
                select(Entity).where(Entity.name == data["name"])
            )
            if result.scalars().first():
                existing += 1
                continue
            session.add(Entity(**data))
            created += 1
        await session.commit()
        print(f"Seeded: {created} new entities, {existing} already existed")


if __name__ == "__main__":
    asyncio.run(seed())
