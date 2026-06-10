from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.event import Event
from app.models.event_entity import EventEntity
from app.repositories.event import EventRepository
from app.repositories.entity import EntityRepository
from app.repositories.market_price import MarketPriceRepository
from app.services.ai_service import ai_service
from app.services.kg_service import analyze_stock_knowledge_graph
from app.services.signal_service import SignalService
from app.schemas.analysis import AnalyzeEventRequest, AnalyzeEventResponse
from app.schemas.event import EventRead
from app.schemas.signal import SignalUpdate
from app.core.enums import EventType, EventSeverity

router = APIRouter(prefix="/events", tags=["analysis"])


@router.post("/{event_id}/analyze", response_model=AnalyzeEventResponse)
async def analyze_event(
    event_id: int = Path(..., gt=0),
    body: AnalyzeEventRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeEventResponse:
    event_repo = EventRepository(db)
    entity_repo = EntityRepository(db)
    price_repo = MarketPriceRepository(db)
    signal_service = SignalService(db)

    event = await event_repo.get_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    if body and body.entity_ids:
        entities = []
        for eid in body.entity_ids:
            ent = await entity_repo.get_by_id(eid)
            if ent is None:
                raise HTTPException(
                    status_code=404, detail=f"Entity with id={eid} not found"
                )
            entities.append(ent)
    else:
        query = (
            select(Event)
            .where(Event.id == event_id)
            .options(selectinload(Event.entities))
        )
        result = await db.execute(query)
        event = result.scalars().first()
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found")
        entities = list(event.entities)

    if not entities:
        raise HTTPException(
            status_code=400,
            detail="No entities linked to this event. Link entities first or provide entity_ids.",
        )

    event_type = (
        EventType(event.event_type)
        if isinstance(event.event_type, str)
        else event.event_type
    )
    severity = (
        EventSeverity(event.severity)
        if isinstance(event.severity, str)
        else event.severity
    )

    signals = []
    for entity in entities:
        latest_price = await price_repo.get_latest_by_entity(entity.id)
        current_price = latest_price.close_price if latest_price else None

        recent_prices = await price_repo.get_recent_by_entity(entity.id, days=90)
        price_history = [float(p.close_price) for p in recent_prices] if recent_prices else None

        ticker_symbol = entity.ticker_symbols.split(",")[0].strip() if entity.ticker_symbols else None

        result = ai_service.analyze(
            event_title=event.title,
            event_description=event.description,
            event_type=event_type,
            severity=severity,
            entity_name=entity.name,
            ticker_symbol=ticker_symbol,
            current_price=current_price,
            price_history=price_history,
        )

        signal_create = result.to_signal_create(event_id, entity.id)
        signal = await signal_service.create(signal_create)

        # Enrich with knowledge graph if entity has a ticker
        if ticker_symbol:
            kg = await analyze_stock_knowledge_graph(ticker_symbol)
            if kg:
                kg_entities = kg.get("entities", [])
                kg_nodes = kg.get("graph_nodes", [])
                kg_edges = kg.get("graph_edges", [])
                kg_news = kg.get("news", [])
                enrichment = (
                    f" [Knowledge Graph] Live news analysis for {ticker_symbol}: "
                    f"{len(kg_news)} articles, "
                    f"{len(kg_entities)} entities "
                    f"({', '.join(e['entity'] for e in kg_entities[:5])}), "
                    f"{len(kg_nodes)} graph nodes, "
                    f"{len(kg_edges)} relationships."
                )
                signal = await signal_service.update(
                    signal.id,
                    SignalUpdate(reasoning=signal.reasoning + enrichment),
                )

        signals.append(signal)

    return AnalyzeEventResponse(
        event=EventRead.model_validate(event),
        signals=[s for s in signals],
    )
