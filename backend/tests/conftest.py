"""Pytest fixtures for MarketAtlas tests.

Uses a separate test database (marketatlas_test) to avoid interfering with
development data. Runs Alembic migrations at session scope and wraps each
test in a transaction rollback.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)

from app.main import app
from app.database import Base, get_db
from app.config import settings


# ---------------------------------------------------------------------------
# Test database — uses marketatlas_test with the same credentials
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = (
    f"{settings.db_driver}://{settings.db_user}:{settings.db_password}"
    f"@{settings.db_host}:{settings.db_port}/marketatlas_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop them after.

    This is faster than running Alembic migrations for every test run.
    For CI, run ``alembic upgrade head`` against the test DB first.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP client with the test DB injected."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sample_entity(db_session: AsyncSession) -> dict:
    """Create a sample entity and return its data."""
    from app.models.entity import Entity

    entity = Entity(
        name="Apple Inc",
        entity_type="company",
        country_code="US",
        ticker_symbols="AAPL",
        latitude=37.3349,
        longitude=-122.0090,
    )
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)
    return {
        "id": entity.id,
        "name": entity.name,
        "entity_type": entity.entity_type,
        "ticker_symbols": entity.ticker_symbols,
    }


@pytest_asyncio.fixture
async def sample_event(db_session: AsyncSession) -> dict:
    """Create a sample event and return its data."""
    from app.models.event import Event
    from datetime import datetime

    event = Event(
        title="US sanctions on Russian oil",
        description="The US Treasury imposed new sanctions targeting Russian oil exports.",
        event_type="sanction",
        severity="high",
        status="reported",
        event_date=datetime.utcnow(),
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return {
        "id": event.id,
        "title": event.title,
        "event_type": event.event_type,
    }


@pytest_asyncio.fixture
async def linked_event_entity(
    db_session: AsyncSession,
    sample_event: dict,
    sample_entity: dict,
) -> dict:
    """Create an event linked to an entity."""
    from app.models.event_entity import EventEntity

    link = EventEntity(event_id=sample_event["id"], entity_id=sample_entity["id"])
    db_session.add(link)
    await db_session.commit()
    return {"event_id": sample_event["id"], "entity_id": sample_entity["id"]}
