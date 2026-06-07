from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """
    Generic base repository providing common CRUD operations.

    All specific repositories inherit from this to reduce code duplication.
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def create(self, obj_in: dict) -> T:
        """Create a new record in the database."""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def get_by_id(self, obj_id: int) -> Optional[T]:
        """Retrieve a record by ID."""
        return await self.session.get(self.model, obj_id)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[T]:
        """Retrieve all records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, obj_id: int, obj_in: dict) -> Optional[T]:
        """Update an existing record."""
        db_obj = await self.get_by_id(obj_id)
        if not db_obj:
            return None

        for key, value in obj_in.items():
            setattr(db_obj, key, value)

        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def delete(self, obj_id: int) -> bool:
        """Delete a record by ID."""
        db_obj = await self.get_by_id(obj_id)
        if not db_obj:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def count(self) -> int:
        """Count all records using a single SQL COUNT(*) query."""
        query = select(func.count()).select_from(self.model)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_where(self, whereclause: ColumnElement) -> int:
        """
        Count records matching an arbitrary WHERE clause using SQL COUNT(*).

        Use this in concrete repositories to build accurate filtered counts
        that mirror their filtered query methods.

        Example:
            await self.count_where(self.model.status == "active")
        """
        query = (
            select(func.count())
            .select_from(self.model)
            .where(whereclause)
        )
        result = await self.session.execute(query)
        return result.scalar_one()
