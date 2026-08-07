import json
import logging
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ...services.financial_data_service import FinancialDataService
from ..event_memory.event_schema import HistoricalEvent
from ..event_memory.event_store import event_store
from ..explain.attention_explainer import AttentionExplainer
from ..explain.graph_explainer import GraphExplainer
from ..explain.shap_explainer import SHAPExplainer
from ..knowledge.neo4j_client import Neo4jClient
from ..memory.short_term import short_term_memory
from ..models import ChatRequest, RiskIndexRequest, SimilarityRequest
from ..rag.vector_store import search_knowledge
from ..workflow.graph import run_chat
from .data import COUNTRIES, COUNTRIES_BY_CODE, MILITARY_RELATIONS, PORTS, TRADE_ROUTES

logger = logging.getLogger(__name__)

chat_router = APIRouter(prefix="/api/v1/chat")
_financial_service = FinancialDataService()


@chat_router.post("")
async def chat(request: ChatRequest):
    try:
        response = await run_chat(
            query=request.query,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
        )
        return response
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.post("/stream")
async def chat_stream(request: ChatRequest):
    response = await run_chat(
        query=request.query,
        conversation_id=request.conversation_id,
        user_id=request.user_id,
    )

    async def generate():
        yield json.dumps({
            "conversation_id": response.conversation_id,
            "intent": response.intent.value,
            "agents_used": response.agents_used,
            "confidence": response.confidence,
            "sources": response.sources,
        }) + "\n"
        words = response.response.split(" ")
        for i in range(0, len(words), 4):
            yield json.dumps({"chunk": " ".join(words[i:i + 4]) + " "}) + "\n"
        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@chat_router.get("/history")
async def history(limit: int = 20, user_id: str = "1"):
    try:
        from app.services.chat_history import get_recent_messages, list_conversations

        convs = await list_conversations(user_id, limit=limit)
        return [
            {
                "id": c.id,
                "query": c.title,
                "intent": None,
                "confidence": None,
                "created_at": c.created_at.isoformat(),
            }
            for c in convs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/history/{conversation_id}")
async def conversation_messages(conversation_id: str, limit: int = 20):
    try:
        from app.services.chat_history import get_recent_messages

        messages = await get_recent_messages(conversation_id, limit=limit)
        return {"conversation_id": conversation_id, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/memory/{conversation_id}")
async def get_memory(conversation_id: str):
    history = short_term_memory.get_history(conversation_id)
    return {"conversation_id": conversation_id, "turns": len(history), "history": history}


@chat_router.get("/knowledge/search")
async def knowledge_search(q: str, limit: int = 5):
    results = search_knowledge(q, limit)
    return {"query": q, "results": results}


@chat_router.get("/graph/{entity}")
async def graph_query(entity: str):
    client = Neo4jClient()
    if not client.available:
        return {"entity": entity, "error": "Neo4j not available", "relations": []}
    relations = client.get_relations(entity)
    return {"entity": entity, "relations": relations}


@chat_router.get("/events")
async def list_events(
    skip: int = Query(0, description="Number of events to skip"),
    limit: int = Query(20, description="Max events to return"),
    type: str = Query(None, description="Filter by event type"),
    severity: str = Query(None, description="Filter by severity"),
):
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.live_event import LiveEvent

    async with AsyncSessionLocal() as db:
        query = select(LiveEvent).order_by(LiveEvent.first_seen_at.desc())
        if type:
            query = query.where(LiveEvent.event_type == type)
        if severity:
            buckets = {"critical": (9.0, 10.1), "high": (7.0, 9.0), "medium": (4.0, 7.0), "low": (0.0, 4.0)}
            lo, hi = buckets.get(severity.lower(), (None, None))
            if lo is not None:
                query = query.where(LiveEvent.severity >= lo, LiveEvent.severity < hi)
        total = len((await db.execute(query)).scalars().all())
        items = (await db.execute(query.offset(skip).limit(limit))).scalars().all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": ev.id,
                "title": ev.title,
                "description": ev.description,
                "event_type": ev.event_type,
                "severity": str(ev.severity),
                "status": ev.status,
                "event_date": ev.event_date.isoformat() if ev.event_date else None,
                "source": ev.source,
                "lat": ev.lat,
                "lng": ev.lng,
                "country_code": ev.country_code,
            }
            for ev in items
        ],
    }


@chat_router.get("/events/{event_id}")
async def get_event(event_id: str):
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app.models.live_event import LiveEvent

    async with AsyncSessionLocal() as db:
        ev = (await db.execute(select(LiveEvent).where(LiveEvent.id == event_id))).scalar_one_or_none()
    if ev is not None:
        return {
            "id": ev.id,
            "title": ev.title,
            "description": ev.description,
            "event_type": ev.event_type,
            "severity": str(ev.severity),
            "status": ev.status,
            "event_date": ev.event_date.isoformat() if ev.event_date else None,
            "source": ev.source,
            "lat": ev.lat,
            "lng": ev.lng,
            "country_code": ev.country_code,
        }
    event = event_store.get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@chat_router.post("/events")
async def add_event(event: HistoricalEvent):
    event_store.add_event(event)
    return {"status": "added", "event_id": event.id, "name": event.name}


@chat_router.post("/similarity")
async def find_similar_events(request: SimilarityRequest):
    result = event_store.find_similar(
        query=request.query,
        top_k=request.top_k,
        min_score=request.min_score,
        sector_filter=request.sector_filter,
        event_type_filter=request.event_type_filter,
    )
    return result


@chat_router.get("/similarity/events")
async def list_historical_events():
    return {"events": [e.model_dump() for e in event_store.events]}


@chat_router.post("/explain/shap")
async def explain_shap(query: str, prediction: str = ""):
    explainer = SHAPExplainer()
    result = explainer.explain(prediction=prediction, context={"query": query})
    shap = result.shap
    if shap:
        return shap.model_dump()
    return {"prediction": prediction, "contributions": []}


@chat_router.post("/explain/attention")
async def explain_attention(query: str = "", entities: str = "", sectors: str = ""):
    explainer = AttentionExplainer()
    entity_list = [e.strip() for e in entities.split(",") if e.strip()] if entities else []
    sector_list = [s.strip() for s in sectors.split(",") if s.strip()] if sectors else []
    result = explainer.explain(context={"query": query, "entities": entity_list, "sectors": sector_list})
    attn = result.attention
    if attn:
        return attn.model_dump()
    return {"query": query, "top_events": [], "top_features": []}


@chat_router.post("/explain/graph")
async def explain_graph(query: str = "", entities: str = ""):
    explainer = GraphExplainer()
    entity_list = [e.strip() for e in entities.split(",") if e.strip()] if entities else []
    result = explainer.explain(context={"query": query, "entities": entity_list})
    graph = result.graph
    if graph:
        return graph.model_dump()
    return {"start_entity": "", "path": []}


@chat_router.get("/intelligence/market")
async def market_intelligence(
    ticker: str = Query("SPY"),
    include_profile: bool = Query(True),
    include_news: bool = Query(True),
    days: int = Query(30),
):
    result: dict = {}
    try:
        if include_profile:
            profile = _financial_service.get_company_profile(ticker)
            if profile:
                result["profile"] = profile
        if include_news:
            news = _financial_service.get_market_news(ticker, limit=5)
            if news:
                result["news"] = news
        quote = _financial_service.get_stock_quote(ticker)
        if quote:
            result["quote"] = quote
        history = _financial_service.get_price_history(ticker, days=days)
        if history:
            result["price_history"] = history
    except Exception as e:
        logger.error(f"Market intelligence error: {e}")
    if not result:
        raise HTTPException(status_code=503, detail="Financial data service unavailable")
    return {"ticker": ticker.upper(), "data": result}


@chat_router.get("/intelligence/country")
async def country_brief(
    country: str = Query(..., description="Country name"),
    include_tickers: bool = Query(True),
    days: int = Query(30),
):
    country_map = {
        "usa": {"name": "United States", "tickers": ["SPY", "QQQ", "DIA"]},
        "us": {"name": "United States", "tickers": ["SPY", "QQQ", "DIA"]},
        "india": {"name": "India", "tickers": ["INDA", "IFN"]},
        "china": {"name": "China", "tickers": ["FXI", "MCHI", "KWEB"]},
        "japan": {"name": "Japan", "tickers": ["EWJ", "DXJ"]},
        "uk": {"name": "United Kingdom", "tickers": ["EWU", "FKU"]},
        "germany": {"name": "Germany", "tickers": ["EWG", "DXGE"]},
        "france": {"name": "France", "tickers": ["EWQ"]},
        "russia": {"name": "Russia", "tickers": ["RSX"]},
        "brazil": {"name": "Brazil", "tickers": ["EWZ", "BRZU"]},
        "canada": {"name": "Canada", "tickers": ["EWC"]},
        "australia": {"name": "Australia", "tickers": ["EWA"]},
        "saudi arabia": {"name": "Saudi Arabia", "tickers": ["KSA"]},
        "south korea": {"name": "South Korea", "tickers": ["EWY"]},
        "taiwan": {"name": "Taiwan", "tickers": ["EWT"]},
    }
    key = country.lower().strip()
    info = country_map.get(key, {"name": country.title(), "tickers": []})
    result = {"country": info["name"]}
    if include_tickers and info["tickers"]:
        quotes = []
        for t in info["tickers"]:
            try:
                q = _financial_service.get_stock_quote(t)
                if q:
                    quotes.append({"ticker": t, "quote": q})
            except Exception:
                pass
        if quotes:
            result["market_data"] = quotes
    return result


@chat_router.get("/countries")
async def list_countries():
    return COUNTRIES


@chat_router.get("/countries/{code}")
async def get_country(code: str):
    c = COUNTRIES_BY_CODE.get(code.upper())
    if not c:
        raise HTTPException(status_code=404, detail="Country not found")
    return c


@chat_router.get("/countries/{code}/relations/trade")
async def country_trade_routes(code: str):
    upper = code.upper()
    return [r for r in TRADE_ROUTES if r["from"] == upper or r["to"] == upper]


@chat_router.get("/countries/{code}/relations/military")
async def country_military_relations(code: str):
    upper = code.upper()
    return [r for r in MILITARY_RELATIONS if r["countryA"] == upper or r["countryB"] == upper]


@chat_router.get("/countries/{code}/ports")
async def country_ports(code: str):
    upper = code.upper()
    return [p for p in PORTS if p["countryCode"] == upper]


@chat_router.get("/relations/trade")
async def all_trade_routes():
    return TRADE_ROUTES


@chat_router.get("/relations/military")
async def all_military_relations():
    return MILITARY_RELATIONS


@chat_router.get("/ports")
async def all_ports():
    return PORTS


_entity_market_data: dict[int, list[dict]] = {}


def _generate_market_data(entity_id: int) -> list[dict]:
    if entity_id in _entity_market_data:
        return _entity_market_data[entity_id]
    data = []
    base_price = random.uniform(50, 500)
    for i in range(60):
        date = (datetime.utcnow() - timedelta(days=59 - i)).strftime("%Y-%m-%d")
        change = random.uniform(-5, 5)
        o = round(base_price + change, 2)
        h = round(o + random.uniform(0, 3), 2)
        low_price = round(o - random.uniform(0, 3), 2)
        c = round(random.uniform(low_price, h), 2)
        v = random.randint(1000000, 50000000)
        data.append({
            "id": i + 1,
            "entity_id": entity_id,
            "open": o, "high": h, "low": low_price,
            "close": c, "volume": v,
            "price_date": date,
        })
        base_price = c
    _entity_market_data[entity_id] = data
    return data


@chat_router.get("/market-prices/entity/{entity_id}/recent")
async def entity_market_prices(entity_id: int, days: int = 30):
    data = _generate_market_data(entity_id)
    items = data[-days:] if days < len(data) else data
    return {"items": items}


@chat_router.get("/market-prices/entity/{entity_id}/latest")
async def entity_latest_price(entity_id: int):
    data = _generate_market_data(entity_id)
    if not data:
        raise HTTPException(status_code=404, detail="No data")
    return data[-1]


@chat_router.post("/analyze")
async def analyze(body: dict):
    text = body.get("text", "")
    symbol = body.get("ticker") or _pick_symbol(text)

    q = text.lower()
    if any(w in q for w in ["energy", "oil", "gas", "xle"]):
        momentum = round(random.uniform(0.03, 0.12), 4)
        risk = round(random.uniform(0.5, 0.85), 4)
        action = "BUY"
        action_reason = "Energy sector strengthening amid geopolitical supply concerns."
    elif any(w in q for w in ["tech", "semiconductor", "xlk", "qqq"]):
        momentum = round(random.uniform(-0.03, 0.06), 4)
        risk = round(random.uniform(0.3, 0.6), 4)
        action = "HOLD" if risk < 0.5 else "SELL"
        action_reason = "Tech sector mixed with regulatory headwinds and valuation concerns."
    elif any(w in q for w in ["defense", "ita", "military"]):
        momentum = round(random.uniform(0.02, 0.10), 4)
        risk = round(random.uniform(0.4, 0.7), 4)
        action = "BUY"
        action_reason = "Defense spending outlook positive given geopolitical tensions."
    elif any(w in q for w in ["safe", "haven", "gold", "gld"]):
        momentum = round(random.uniform(0.01, 0.05), 4)
        risk = round(random.uniform(0.2, 0.4), 4)
        action = "BUY"
        action_reason = "Safe-haven demand increasing amid global uncertainty."
    else:
        momentum = round(random.uniform(-0.05, 0.08), 4)
        risk = round(random.uniform(0.3, 0.7), 4)
        action = "BUY" if momentum > 0 else "SELL"
        action_reason = "Mixed signals based on current market conditions."

    return {
        "snapshot": {
            "symbol": symbol,
            "momentum": momentum,
            "volatility": round(random.uniform(0.015, 0.05), 4),
            "volume_status": random.choice(["surge", "normal", "thin"]),
        },
        "impact": {
            "composite_risk": risk,
            "local_severity": round(random.uniform(0.2, 0.8), 4),
            "entity_count": random.randint(3, 10),
            "relations": [
                {"source": "Russia", "target": "Oil", "label": "sanction"},
                {"source": "China", "target": "Tech", "label": "restriction"},
            ],
        },
        "recommendation": {
            "action": action,
            "reason": action_reason,
            "confidence": round(random.uniform(0.6, 0.95), 4),
        },
    }


@chat_router.get("/risk/{ticker}")
async def get_risk_index(ticker: str):
    from ..agents.risk_agent import RiskAgent
    agent = RiskAgent()
    risk = await agent._compute_risk_index(ticker.upper())
    return risk.model_dump()


@chat_router.post("/risk")
async def risk_index(body: RiskIndexRequest):
    from ..agents.risk_agent import RiskAgent
    agent = RiskAgent()
    risk = await agent._compute_risk_index(body.ticker.upper())
    return risk.model_dump()


def _pick_symbol(text: str) -> str:
    text_lower = text.lower()
    if "energy" in text_lower or "oil" in text_lower or "gas" in text_lower:
        return "XLE"
    if "tech" in text_lower or "semiconductor" in text_lower:
        return "XLK"
    if "defense" in text_lower or "military" in text_lower:
        return "ITA"
    if "gold" in text_lower or "safe" in text_lower:
        return "GLD"
    if "financial" in text_lower or "bank" in text_lower:
        return "XLF"
    country_map = {
        "US": "SPY", "JP": "EWJ", "CN": "FXI", "GB": "EWU", "DE": "EWG",
        "IN": "INDA", "BR": "EWZ", "KR": "EWY", "TW": "EWT", "SG": "EWS",
        "AU": "EWA", "CA": "EWC", "MX": "EWW", "ZA": "EZA", "RU": "RSX",
    }
    for name, ticker in country_map.items():
        if name.lower() in text_lower:
            return ticker
    return random.choice(["SPY", "QQQ", "EEM", "XLE", "XLK", "GLD"])


@chat_router.get("/health")
async def health():
    return {"status": "ok", "service": "MarketAtlas Chat"}
