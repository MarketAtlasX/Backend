import logging
from decimal import Decimal
from typing import Optional

from app.core.enums import SignalType
from app.geopolitical.pipeline import run_pipeline as unified_run_pipeline
from app.schemas.signal import SignalCreate
from app.services.market_agents_client import market_agents_client

logger = logging.getLogger(__name__)


def _get_market_snapshot(
    price_history: list[float] | None,
    ticker_symbol: str | None,
) -> dict:
    """Get market data snapshot — lazily imports MarketDataAgent to avoid
    a hard dependency on the market_agents package at import time."""
    if price_history and len(price_history) >= 5:
        try:
            from market_agents.market_data.market_data_agent import (
                MarketDataAgent,  # type: ignore[import-untyped]
            )
            agent = MarketDataAgent(prices=price_history)
            return agent.snapshot()
        except ImportError:
            pass
    elif ticker_symbol:
        try:
            from market_agents.market_data.market_data_agent import (
                MarketDataAgent,  # type: ignore[import-untyped]
            )
            agent = MarketDataAgent.from_yfinance(ticker_symbol)
            return agent.snapshot()
        except ImportError:
            pass
    return {"momentum": 0.0, "volatility": 0.0, "volume": "unknown"}


_SIGNAL_MAP = {
    "buy": SignalType.BUY,
    "sell": SignalType.SELL,
    "hold": SignalType.HOLD,
    "short": SignalType.SHORT,
}


class AIAnalysisResult:
    def __init__(
        self,
        signal_type: SignalType,
        confidence: Decimal,
        reasoning: str,
        target_price: Optional[Decimal] = None,
        stop_loss: Optional[Decimal] = None,
        composite_risk: float = 0.0,
        local_severity: float = 0.0,
        entities_identified: list[str] | None = None,
        relations: list[tuple[str, str, str]] | None = None,
        reasoning_snapshot: dict | None = None,
    ):
        self.signal_type = signal_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.target_price = target_price
        self.stop_loss = stop_loss
        self.composite_risk = composite_risk
        self.local_severity = local_severity
        self.entities_identified = entities_identified or []
        self.relations = relations or []
        self.reasoning_snapshot = reasoning_snapshot or {}

    def to_signal_create(self, event_id: int, entity_id: int) -> SignalCreate:
        return SignalCreate(
            event_id=event_id,
            entity_id=entity_id,
            signal_type=self.signal_type,
            confidence=self.confidence,
            reasoning=self.reasoning,
            target_price=self.target_price,
            stop_loss=self.stop_loss,
        )


class AIService:
    def __init__(self):
        pass

    async def analyze(
        self,
        event_title: str,
        event_description: str,
        event_type: str,
        severity: str,
        entity_name: str,
        ticker_symbol: Optional[str] = None,
        current_price: Optional[Decimal] = None,
        price_history: Optional[list[float]] = None,
    ) -> AIAnalysisResult:
        snapshot = _get_market_snapshot(price_history, ticker_symbol)

        raw = await market_agents_client.analyze(
            event_title=event_title,
            event_description=event_description,
            event_type=event_type,
            severity=severity,
            entity_name=entity_name,
            ticker_symbol=ticker_symbol,
            current_price=current_price,
            price_history=price_history,
        )

        if not raw or raw.get("confidence", 0) < 0.3:
            logger.info("market_agents returned low confidence — falling back to unified geopolitical pipeline")
            try:
                pipe_result = await unified_run_pipeline(
                    query=event_title,
                    ticker=ticker_symbol,
                    price_history=price_history,
                )
                if pipe_result.signal:
                    raw = {
                        "signal_type": pipe_result.signal.action.lower(),
                        "confidence": pipe_result.signal.confidence,
                        "reasoning": pipe_result.signal.reason,
                        "target_price": None,
                        "stop_loss": None,
                        "composite_risk": pipe_result.impact.composite_risk if pipe_result.impact else 0.0,
                        "local_severity": pipe_result.impact.local_severity if pipe_result.impact else 0.0,
                        "entities_identified": [e.name for e in pipe_result.entities],
                        "relations": [(e.source, e.relation, e.target) for e in pipe_result.graph_edges[:10]],
                        "reasoning_snapshot": pipe_result.market.model_dump() if pipe_result.market else {},
                    }
            except Exception as pipe_err:
                logger.warning(f"Unified pipeline fallback also failed: {pipe_err}")

        signal_type = _SIGNAL_MAP.get(raw.get("signal_type", "hold"), SignalType.HOLD)
        confidence = Decimal(str(raw.get("confidence", 0.5)))
        reasoning = raw.get("reasoning", "")

        composite_risk = raw.get("composite_risk", 0.0)
        local_severity = raw.get("local_severity", 0.0)
        entities_identified = raw.get("entities_identified", [])
        relations_raw = raw.get("relations", [])

        relations = []
        for r in relations_raw:
            if isinstance(r, list) and len(r) >= 3:
                relations.append((str(r[0]), str(r[1]), str(r[2])))
            elif isinstance(r, dict):
                relations.append(
                    (str(r.get("source", "")), str(r.get("label", "")), str(r.get("target", "")))
                )

        target_price = None
        stop_loss = None
        if raw.get("target_price"):
            try:
                target_price = Decimal(str(raw["target_price"]))
            except Exception:
                target_price = None
        if raw.get("stop_loss"):
            try:
                stop_loss = Decimal(str(raw["stop_loss"]))
            except Exception:
                stop_loss = None

        if target_price is None and current_price is not None:
            if signal_type in (SignalType.BUY, SignalType.SELL):
                price = current_price
                if signal_type == SignalType.BUY:
                    target_price = (price * Decimal("1.15")).quantize(Decimal("0.01"))
                    stop_loss = (price * Decimal("0.93")).quantize(Decimal("0.01"))
                else:
                    target_price = (price * Decimal("0.85")).quantize(Decimal("0.01"))
                    stop_loss = (price * Decimal("1.07")).quantize(Decimal("0.01"))

        reasoning_parts = [
            f"MarketAtlas analysis of '{event_title}' for {entity_name}.",
            f"Recommendation: {signal_type.value.upper()}.",
            f"Composite risk: {composite_risk:.2f}, local severity: {local_severity:.2f}.",
        ]
        if snapshot.get("volume", "unknown") != "unknown":
            reasoning_parts.append(
                f"Market momentum: {snapshot['momentum']:.4f}, "
                f"volatility: {snapshot['volatility']:.4f}, "
                f"volume: {snapshot['volume']}."
            )
        entities_str = ", ".join(entities_identified)
        if entities_str:
            reasoning_parts.append(f"Entities identified: {entities_str}.")
        relations_str = "; ".join(
            f"{a} {rel} {b}" for a, rel, b in relations[:3]
        )
        if relations_str:
            reasoning_parts.append(f"Relations: {relations_str}.")
        full_reasoning = " ".join(reasoning_parts)

        if reasoning:
            full_reasoning = reasoning + " " + full_reasoning

        return AIAnalysisResult(
            signal_type=signal_type,
            confidence=confidence,
            reasoning=full_reasoning,
            target_price=target_price,
            stop_loss=stop_loss,
            composite_risk=composite_risk,
            local_severity=local_severity,
            entities_identified=entities_identified,
            relations=relations,
            reasoning_snapshot=snapshot,
        )


ai_service = AIService()
