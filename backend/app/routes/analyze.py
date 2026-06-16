from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_service import ai_service
from app.services.kg_service import analyze_stock_knowledge_graph
from app.geopolitical.pipeline import run_pipeline

router = APIRouter(tags=["analysis"])


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to analyze (e.g. 'Market sentiment for AAPL')")


class Snapshot(BaseModel):
    symbol: str
    momentum: float
    volatility: float
    volume_status: str


class Relation(BaseModel):
    source: str
    target: str
    label: str


class Impact(BaseModel):
    composite_risk: float
    local_severity: float
    entity_count: int
    relations: list[Relation]


class Recommendation(BaseModel):
    action: str
    reason: str
    confidence: float


class AnalyzeTextResponse(BaseModel):
    snapshot: Snapshot
    impact: Impact
    recommendation: Recommendation


@router.post("/analyze", response_model=AnalyzeTextResponse)
async def analyze_text(body: AnalyzeTextRequest) -> AnalyzeTextResponse:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text must be non-empty")

    ticker = _extract_ticker(text)

    result = await ai_service.analyze(
        event_title="Market sentiment analysis",
        event_description=text,
        event_type="other",
        severity="medium",
        entity_name=ticker or "Unknown",
        ticker_symbol=ticker,
    )

    kg = await analyze_stock_knowledge_graph(ticker) if ticker else None

    snapshot = Snapshot(
        symbol=ticker or "UNKNOWN",
        momentum=result.reasoning_snapshot.get("momentum", 0.0),
        volatility=result.reasoning_snapshot.get("volatility", 0.0),
        volume_status=result.reasoning_snapshot.get("volume", "unknown"),
    )

    impact = Impact(
        composite_risk=result.composite_risk,
        local_severity=result.local_severity,
        entity_count=len(result.entities_identified) + (len(kg.entities) if kg else 0),
        relations=[
            Relation(source=s, target=t, label=l)
            for s, t, l in result.relations[:10]
        ],
    )

    recommendation = Recommendation(
        action=result.signal_type.value.upper(),
        reason=result.reasoning[:500],
        confidence=float(result.confidence),
    )

    return AnalyzeTextResponse(
        snapshot=snapshot,
        impact=impact,
        recommendation=recommendation,
    )


class AnalyzeV2Request(BaseModel):
    text: str = Field(..., min_length=1, description="Query text (e.g. company or geopolitical topic)")
    ticker: Optional[str] = Field(None, description="Optional stock ticker symbol")
    price_history: Optional[list[float]] = Field(None, description="Optional price history for market signal")


@router.post("/analyze/v2")
async def analyze_v2(body: AnalyzeV2Request):
    result = await run_pipeline(
        query=body.text,
        ticker=body.ticker,
        price_history=body.price_history,
    )
    return result.model_dump()


def _extract_ticker(text: str) -> str | None:
    known = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "JPM", "V",
             "NVDA", "META", "SPY", "QQQ", "AMD", "INTC", "NFLX",
             "DIS", "BA", "XOM", "CVX", "JNJ", "PG", "KO", "PEP",
             "WMT", "HD", "MCD", "NKE", "SBUX", "T", "VZ", "IBM",
             "ORCL", "CRM", "ADBE", "ACN", "CSCO", "QCOM", "TXN",
             "AVGO", "AMAT", "MU", "NVIDIA", "APPLE", "TESLA",
             "MICROSOFT", "AMAZON", "META", "GOOGLE"]
    upper = text.upper()
    for t in known:
        if t in upper:
            return t
    for word in upper.split():
        word = word.strip(".,!?;:'\"()[]{}")
        if len(word) <= 5 and word.isalpha():
            return word
    return None
