from decimal import Decimal
from typing import Optional

from market_agents.impact.impact_agent import ImpactAgent
from market_agents.market_data.market_data_agent import MarketDataAgent
from market_agents.recommendation.recommendation_agent import RecommendationAgent

from app.core.enums import SignalType
from app.schemas.signal import SignalCreate


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


_SIGNAL_MAP = {
    "BUY": SignalType.BUY,
    "SELL": SignalType.SELL,
    "HOLD": SignalType.HOLD,
}


class AIService:
    def __init__(self):
        self._impact_agent = ImpactAgent()
        self._rec_agent = RecommendationAgent()

    def analyze(
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
        text = f"{event_title}. {event_description}"

        state = {"text": text}
        state = self._impact_agent.ingest(state)
        state = self._impact_agent.extract(state)
        state = self._impact_agent.store(state)
        state = self._impact_agent.propagate(state)
        state = self._impact_agent.output(state)

        composite_risk = state.get("composite_risk", 0.0)
        local_severity = state.get("local_severity", 0.0)
        relations = state.get("relations", [])

        if price_history and len(price_history) >= 5:
            market_agent = MarketDataAgent(prices=price_history)
            snapshot = market_agent.snapshot()
        elif ticker_symbol:
            market_agent = MarketDataAgent.from_yfinance(ticker_symbol)
            snapshot = market_agent.snapshot()
        else:
            snapshot = {"momentum": 0.0, "volatility": 0.0, "volume": "unknown"}

        impact_data = {
            "composite_risk": composite_risk,
            "local_severity": local_severity,
            "graph_summary": state.get("graph_summary", {}),
        }
        decision = self._rec_agent.decide(impact_data, snapshot)

        action = decision.get("action", "HOLD")
        rec_reason = decision.get("reason", "neutral")
        signal_type = _SIGNAL_MAP.get(action, SignalType.HOLD)

        if composite_risk > 0:
            base_confidence = composite_risk if signal_type == SignalType.SELL else (1 - composite_risk)
        elif local_severity > 0:
            base_confidence = local_severity
        else:
            base_confidence = 0.5

        base_confidence = max(0.1, min(0.95, base_confidence))
        confidence = Decimal(str(round(base_confidence, 2)))

        reasoning_parts = [
            f"MarketAtlas analysis of '{event_title}' for {entity_name}.",
            f"Recommendation: {action} ({rec_reason}).",
            f"Composite risk: {composite_risk:.2f}, local severity: {local_severity:.2f}.",
        ]
        if snapshot["volume"] != "unknown":
            reasoning_parts.append(
                f"Market momentum: {snapshot['momentum']:.4f}, "
                f"volatility: {snapshot['volatility']:.4f}, "
                f"volume: {snapshot['volume']}."
            )
        entities_str = ", ".join(state.get("entities", []))
        if entities_str:
            reasoning_parts.append(f"Entities identified: {entities_str}.")
        relations_str = "; ".join(
            f"{a} {rel} {b}" for a, rel, b in relations[:3]
        )
        if relations_str:
            reasoning_parts.append(f"Relations: {relations_str}.")
        reasoning = " ".join(reasoning_parts)

        target_price = None
        stop_loss = None
        if current_price is not None and signal_type in (SignalType.BUY, SignalType.SELL):
            price = current_price
            if signal_type == SignalType.BUY:
                target_price = (price * Decimal("1.15")).quantize(Decimal("0.01"))
                stop_loss = (price * Decimal("0.93")).quantize(Decimal("0.01"))
            else:
                target_price = (price * Decimal("0.85")).quantize(Decimal("0.01"))
                stop_loss = (price * Decimal("1.07")).quantize(Decimal("0.01"))

        return AIAnalysisResult(
            signal_type=signal_type,
            confidence=confidence,
            reasoning=reasoning,
            target_price=target_price,
            stop_loss=stop_loss,
            composite_risk=composite_risk,
            local_severity=local_severity,
            entities_identified=list(state.get("entities", [])),
            relations=list(relations),
            reasoning_snapshot=snapshot,
        )


ai_service = AIService()
