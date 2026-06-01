from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from app.config import settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class DatabaseManager:
    """Manages database connections and session lifecycle."""

    def __init__(self):
        self.engine: Optional[object] = None
        self.async_session_maker: Optional[async_sessionmaker] = None

    def _ensure_initialized(self) -> None:
        """Lazily initialize the engine and session maker."""
        if self.engine is None:
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.db_echo,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

    async def init_db(self) -> None:
        """Create all tables in the database. (Use Alembic in production)"""
        self._ensure_initialized()
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_db(self) -> None:
        """Drop all tables from the database."""
        self._ensure_initialized()
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close the database connection pool."""
        if self.engine is not None:
            await self.engine.dispose()

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a new database session."""
        self._ensure_initialized()
        async with self.async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    @asynccontextmanager
    async def session_context(self) -> AsyncGenerator[AsyncSession, None]:
        """Context manager for database sessions."""
        self._ensure_initialized()
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI route handlers
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to inject database session."""
    async for session in db_manager.get_session():
        yield session
