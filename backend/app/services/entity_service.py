"""
EntityService — business logic layer for Entity domain operations.

Responsibilities:
  - Enforce the unique-name constraint at the application layer (409 before
    the DB constraint fires, giving callers a clean error message).
  - Coordinate EntityRepository calls.
  - Own the session commit / refresh lifecycle for mutations.
  - Raise HTTPException so routes stay thin.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.entity import Entity
from app.repositories.entity import EntityRepository
from app.schemas.entity import EntityCreate, EntityUpdate
from app.schemas.pagination import Page
from app.core.enums import EntityType


class EntityService:
    """Orchestrates all entity-related business operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EntityRepository(session)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, data: EntityCreate) -> Entity:
        """
        Persist a new entity.

        Raises 409 if an entity with the same name already exists.
        """
        existing = await self._repo.get_by_name(data.name)
        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Entity with name '{data.name}' already exists",
            )
        entity = await self._repo.create(data.model_dump())
        await self._session.commit()
        await self._session.refresh(entity)
        return entity

    async def update(self, entity_id: int, data: EntityUpdate) -> Entity:
        """
        Apply a partial update to an existing entity.

        If the name is being changed, checks for conflicts first.
        Raises 404 if the entity does not exist, 409 on name collision.
        """
        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            collision = await self._repo.get_by_name(update_data["name"])
            if collision is not None and collision.id != entity_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Entity with name '{update_data['name']}' already exists",
                )

        entity = await self._repo.update(entity_id, update_data)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        await self._session.commit()
        await self._session.refresh(entity)
        return entity

    async def delete(self, entity_id: int) -> None:
        """
        Permanently remove an entity.

        Raises 404 if the entity does not exist.
        """
        deleted = await self._repo.delete(entity_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Entity not found")
        await self._session.commit()

    # ------------------------------------------------------------------
    # Read operations — single record
    # ------------------------------------------------------------------

    async def get(self, entity_id: int) -> Entity:
        """Fetch a single entity by ID. Raises 404 if not found."""
        entity = await self._repo.get_by_id(entity_id)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity

    async def get_by_name(self, name: str) -> Entity:
        """Fetch an entity by exact name. Raises 404 if not found."""
        entity = await self._repo.get_by_name(name)
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")
        return entity

    async def get_by_ticker(self, ticker: str) -> Entity:
        """
        Fetch an entity by ticker symbol (substring search).

        Raises 404 if not found.
        """
        entity = await self._repo.get_by_ticker(ticker)
        if entity is None:
            raise HTTPException(
                status_code=404,
                detail=f"No entity found with ticker '{ticker}'",
            )
        return entity

    # ------------------------------------------------------------------
    # Read operations — paginated lists
    # ------------------------------------------------------------------

    async def list_all(self, skip: int, limit: int) -> Page[Entity]:
        """Return a paginated page of all entities."""
        items = await self._repo.get_all(skip=skip, limit=limit)
        total = await self._repo.count()
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_type(self, entity_type: EntityType, skip: int, limit: int) -> Page[Entity]:
        """Return a paginated page of entities filtered by type."""
        items = await self._repo.get_by_type(entity_type, skip=skip, limit=limit)
        total = await self._repo.count_by_type(entity_type)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_country(self, country_code: str, skip: int, limit: int) -> Page[Entity]:
        """Return a paginated page of entities filtered by ISO country code."""
        items = await self._repo.get_by_country_code(country_code, skip=skip, limit=limit)
        total = await self._repo.count_by_country_code(country_code)
        return Page(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------

def get_entity_service(session: AsyncSession = Depends(get_db)) -> EntityService:
    """Inject an EntityService bound to the current request's DB session."""
    return EntityService(session)
