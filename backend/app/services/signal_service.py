"""
SignalService — business logic layer for Signal domain operations.

Responsibilities:
  - Validate that the referenced event_id and entity_id actually exist before
    creating a signal. Without this, the DB FK violation surfaces as a generic
    500-level IntegrityError instead of a meaningful 404 or 422.
  - Coordinate SignalRepository, EventRepository, and EntityRepository calls.
  - Own the session commit / refresh lifecycle for mutations.
  - Raise HTTPException so routes stay thin.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.signal import Signal
from app.repositories.signal import SignalRepository
from app.repositories.event import EventRepository
from app.repositories.entity import EntityRepository
from app.schemas.signal import SignalCreate, SignalUpdate
from app.schemas.pagination import Page
from app.core.enums import SignalType, SignalStatus


class SignalService:
    """Orchestrates all signal-related business operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SignalRepository(session)
        # Cross-domain repos used for FK validation on create
        self._event_repo = EventRepository(session)
        self._entity_repo = EntityRepository(session)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    async def create(self, data: SignalCreate) -> Signal:
        """
        Persist a new trading signal.

        Business rules enforced here (not at the DB layer):
          - event_id must reference an existing Event → 404 if missing
          - entity_id must reference an existing Entity → 404 if missing

        Without this validation, a bad FK produces a cryptic IntegrityError
        from asyncpg that would reach the client as a 500.
        """
        event = await self._event_repo.get_by_id(data.event_id)
        if event is None:
            raise HTTPException(
                status_code=404,
                detail=f"Event with id={data.event_id} not found",
            )

        entity = await self._entity_repo.get_by_id(data.entity_id)
        if entity is None:
            raise HTTPException(
                status_code=404,
                detail=f"Entity with id={data.entity_id} not found",
            )

        signal = await self._repo.create(data.model_dump())
        await self._session.commit()
        await self._session.refresh(signal)
        return signal

    async def update(self, signal_id: int, data: SignalUpdate) -> Signal:
        """
        Apply a partial update to an existing signal.

        Raises 404 if the signal does not exist.
        """
        update_data = data.model_dump(exclude_unset=True)
        signal = await self._repo.update(signal_id, update_data)
        if signal is None:
            raise HTTPException(status_code=404, detail="Signal not found")
        await self._session.commit()
        await self._session.refresh(signal)
        return signal

    async def delete(self, signal_id: int) -> None:
        """
        Permanently remove a signal.

        Raises 404 if the signal does not exist.
        """
        deleted = await self._repo.delete(signal_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Signal not found")
        await self._session.commit()

    # ------------------------------------------------------------------
    # Read operations — single record
    # ------------------------------------------------------------------

    async def get(self, signal_id: int) -> Signal:
        """Fetch a single signal by ID. Raises 404 if not found."""
        signal = await self._repo.get_by_id(signal_id)
        if signal is None:
            raise HTTPException(status_code=404, detail="Signal not found")
        return signal

    # ------------------------------------------------------------------
    # Read operations — paginated lists
    # ------------------------------------------------------------------

    async def list_all(self, skip: int, limit: int) -> Page[Signal]:
        """Return a paginated page of all signals."""
        items = await self._repo.get_all(skip=skip, limit=limit)
        total = await self._repo.count()
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_event(self, event_id: int, skip: int, limit: int) -> Page[Signal]:
        """Return a paginated page of signals for a specific event."""
        items = await self._repo.get_by_event_id(event_id, skip=skip, limit=limit)
        total = await self._repo.count_by_event(event_id)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_entity(self, entity_id: int, skip: int, limit: int) -> Page[Signal]:
        """Return a paginated page of signals for a specific entity."""
        items = await self._repo.get_by_entity_id(entity_id, skip=skip, limit=limit)
        total = await self._repo.count_by_entity(entity_id)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_type(self, signal_type: SignalType, skip: int, limit: int) -> Page[Signal]:
        """Return a paginated page of signals filtered by type."""
        items = await self._repo.get_by_type(signal_type, skip=skip, limit=limit)
        total = await self._repo.count_by_type(signal_type)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_by_status(self, status: SignalStatus, skip: int, limit: int) -> Page[Signal]:
        """Return a paginated page of signals filtered by status."""
        items = await self._repo.get_by_status(status, skip=skip, limit=limit)
        total = await self._repo.count_by_status(status)
        return Page(items=items, total=total, skip=skip, limit=limit)

    async def list_active(self, skip: int, limit: int) -> Page[Signal]:
        """Return a paginated page of all currently active signals."""
        return await self.list_by_status(SignalStatus.ACTIVE, skip=skip, limit=limit)

    async def list_high_confidence(
        self,
        min_confidence: float,
        skip: int,
        limit: int,
    ) -> Page[Signal]:
        """Return a paginated page of signals above a confidence threshold."""
        items = await self._repo.get_high_confidence(min_confidence, skip=skip, limit=limit)
        total = await self._repo.count_high_confidence(min_confidence)
        return Page(items=items, total=total, skip=skip, limit=limit)


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------

def get_signal_service(session: AsyncSession = Depends(get_db)) -> SignalService:
    """Inject a SignalService bound to the current request's DB session."""
    return SignalService(session)
