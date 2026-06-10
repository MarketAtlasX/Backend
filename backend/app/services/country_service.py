"""Service for country overview — combines entities, events, companies, prices, and news."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entity import Entity
from app.models.event import Event
from app.models.event_entity import EventEntity
from app.models.market_price import MarketPrice
from app.services.kg_service import analyze_country_knowledge_graph


async def get_country_overview(country_id: int, db: AsyncSession) -> dict[str, Any]:
    """Return core country data instantly — events, companies, prices.
    
    KG agent news/graph data is NOT included here (it's slow).
    Call get_country_kg_news separately for the news & graph layer.
    """
    country = await db.get(Entity, country_id)
    if country is None or country.entity_type != "country":
        raise ValueError("Country not found")

    events_data = await _get_events_for_country(country_id, db)
    companies_data = await _get_companies_in_country(country.country_code, db)

    return {
        "country": {
            "id": country.id,
            "name": country.name,
            "country_code": country.country_code,
            "latitude": country.latitude,
            "longitude": country.longitude,
            "ticker_symbols": country.ticker_symbols,
        },
        "events": events_data,
        "companies": companies_data,
    }


async def get_country_kg_news(country_id: int, db: AsyncSession) -> dict[str, Any]:
    """Fetch KG agent news + graph data for a country (slower, ~10s)."""
    country = await db.get(Entity, country_id)
    if country is None or country.entity_type != "country":
        raise ValueError("Country not found")

    kg = await analyze_country_knowledge_graph(country.name, timeout=18.0)
    news, nodes, edges = _parse_kg_result(kg)
    generated_events = _generate_events_from_graph(country, edges)

    return {
        "country_id": country_id,
        "news": news,
        "graph_nodes": nodes,
        "graph_edges": edges,
        "events": generated_events,
    }


def _generate_events_from_graph(country: Entity, edges: list[dict]) -> list[dict]:
    """Convert graph relationships into displayable event objects."""
    country_name = country.name.upper()
    seen = set()
    events = []

    for edge in edges:
        src = (edge.get("source") or "").upper()
        tgt = (edge.get("target") or "").upper()
        rel = (edge.get("relationship") or "").lower()

        if src != country_name and tgt != country_name:
            continue

        other = tgt if src == country_name else src
        other_lower = other.lower()

        if "sanction" in rel:
            event_type = "sanction"
            severity = "high"
            title = f"Sanctions: {country.name} ↔ {other}"
        elif any(w in rel for w in ("conflict", "war", "military", "strike", "attack", "missile", "bomb")):
            event_type = "military_conflict"
            severity = "critical"
            title = f"Conflict: {country.name} - {other}"
        elif any(w in rel for w in ("trade", "export", "import", "tariff", "supply")):
            event_type = "trade_policy"
            severity = "medium"
            title = f"Trade: {country.name} ↔ {other}"
        elif any(w in rel for w in ("diplomat", "ally", "relation", "affect", "deal", "visit", "summit")):
            event_type = "diplomatic"
            severity = "medium"
            title = f"Diplomatic: {country.name} - {other}"
        elif any(w in rel for w in ("invest", "partner", "cooperation", "agreement")):
            event_type = "economic_data"
            severity = "low"
            title = f"Cooperation: {country.name} - {other}"
        elif any(w in rel for w in ("election", "vote", "protest", "policy", "regulatory")):
            event_type = "regulatory"
            severity = "medium"
            title = f"Policy: {other} affects {country.name}"
        else:
            event_type = "other"
            severity = "medium"
            title = f"{country.name} ↔ {other}"

        key = (title, event_type)
        if key in seen:
            continue
        seen.add(key)

        events.append({
            "id": 0,
            "title": title,
            "description": f"Relationship: {edge.get('relationship', '')} between {src} and {tgt}",
            "event_type": event_type,
            "severity": severity,
            "event_date": "",
            "affected_entities": [
                {"id": 0, "name": src, "entity_type": "country", "ticker_symbols": None},
                {"id": 0, "name": tgt, "entity_type": "country", "ticker_symbols": None},
            ],
        })

    return events[:10]


def _parse_kg_result(kg: dict | None) -> tuple[list[dict], list[dict], list[dict]]:
    if kg is None:
        return [], [], []
    news = [
        {
            "title": a.get("title", ""),
            "content": a.get("content", ""),
            "source": a.get("source", ""),
            "date": a.get("date", ""),
            "url": a.get("url", ""),
        }
        for a in (kg.get("news") or [])
    ][:10]
    nodes = kg.get("graph_nodes") or []
    edges = kg.get("graph_edges") or []
    return news, nodes, edges


async def _get_events_for_country(country_id: int, db: AsyncSession) -> list[dict]:
    stmt = (
        select(Event)
        .join(EventEntity)
        .where(EventEntity.entity_id == country_id)
        .options(selectinload(Event.entities))
        .order_by(Event.event_date.desc())
        .limit(20)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    output = []
    for event in events:
        affected = [
            {
                "id": e.id,
                "name": e.name,
                "entity_type": e.entity_type,
                "ticker_symbols": e.ticker_symbols,
            }
            for e in event.entities
            if e.id != country_id
        ]
        output.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "event_type": event.event_type,
            "severity": event.severity,
            "event_date": event.event_date.isoformat() if event.event_date else None,
            "affected_entities": affected,
        })
    return output


async def _get_companies_in_country(country_code: str | None, db: AsyncSession) -> list[dict]:
    if not country_code:
        return []

    stmt = (
        select(Entity)
        .where(Entity.country_code == country_code, Entity.entity_type == "company")
        .order_by(Entity.name)
    )
    result = await db.execute(stmt)
    companies = result.scalars().all()

    output = []
    for company in companies:
        latest_price = await _get_latest_price(company.id, db)
        price_info = {}
        if latest_price:
            price_info = {
                "close_price": float(latest_price.close_price),
                "price_date": latest_price.price_date.isoformat() if latest_price.price_date else None,
                "change": float(latest_price.close_price - latest_price.open_price) if latest_price.open_price else None,
            }

        output.append({
            "id": company.id,
            "name": company.name,
            "ticker_symbols": company.ticker_symbols,
            **price_info,
        })
    return output


async def _get_latest_price(entity_id: int, db: AsyncSession) -> MarketPrice | None:
    stmt = (
        select(MarketPrice)
        .where(MarketPrice.entity_id == entity_id)
        .order_by(MarketPrice.price_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()
