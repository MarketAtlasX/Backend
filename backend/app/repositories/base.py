from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

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
        limit: int = 100
    ) -> List[T]:
        """Retrieve all records with pagination."""
        query = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

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
        """Count total records."""
        query = select(self.model)
        result = await self.session.execute(query)
        return len(result.scalars().all())
