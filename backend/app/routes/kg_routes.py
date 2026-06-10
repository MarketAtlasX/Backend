from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models.event import Event
from app.repositories.entity import EntityRepository
from app.services.kg_service import analyze_stock_knowledge_graph

router = APIRouter(prefix="/events/{event_id}", tags=["knowledge-graph"])


class KnowledgeGraphResponse(BaseModel):
    event_id: int
    ticker: str
    entity_name: str
    news_count: int
    entities_count: int
    graph_nodes_count: int
    graph_edges_count: int
    knowledge_graph: dict | None


@router.post("/knowledge-graph")
async def get_knowledge_graph(
    event_id: int,
    entity_id: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> KnowledgeGraphResponse:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    entity_repo = EntityRepository(db)
    if entity_id:
        entities = [await entity_repo.get_by_id(entity_id)]
        if entities[0] is None:
            raise HTTPException(status_code=404, detail="Entity not found")
    else:
        stmt = (
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.entities))
        )
        result = await db.execute(stmt)
        event = result.scalars().first()
        entities = list(event.entities) if event else []

    if not entities:
        raise HTTPException(status_code=400, detail="No entities linked to this event")

    for entity in entities:
        ticker = (entity.ticker_symbols or "").split(",")[0].strip()
        if not ticker:
            continue

        kg = await analyze_stock_knowledge_graph(ticker)
        return KnowledgeGraphResponse(
            event_id=event_id,
            ticker=ticker,
            entity_name=entity.name,
            news_count=len(kg["news"]) if kg else 0,
            entities_count=len(kg["entities"]) if kg else 0,
            graph_nodes_count=len(kg["graph_nodes"]) if kg else 0,
            graph_edges_count=len(kg["graph_edges"]) if kg else 0,
            knowledge_graph=kg,
        )

    raise HTTPException(
        status_code=400,
        detail="No linked entities have ticker_symbols for KG analysis",
    )
