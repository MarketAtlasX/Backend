from typing import Dict, Any


class RecommendationAgent:
    def __init__(self, hedge_buffer: float = 0.05):
        self.hedge_buffer = hedge_buffer

    def decide(self, impact: Dict[str, Any], market: Dict[str, Any]):
        score = impact.get("composite_risk", 0.0)
        momentum = market.get("momentum", 0.0)
        vol = market.get("volatility", 0.0)

        if vol is None:
            vol = 0.0

        if vol > 0.04:
            return {"action": "HOLD", "reason": "high_volatility"}

        if score >= 0.7 and momentum < 0:
            return {"action": "SELL", "reason": "high_impact_negative_momentum"}

        if score < 0.3 and momentum > 0:
            return {"action": "BUY", "reason": "low_impact_positive_momentum"}

        if 0.3 <= score < 0.7 and momentum < -self.hedge_buffer:
            return {"action": "HOLD", "reason": "hedge_negative_momentum"}

        return {"action": "HOLD", "reason": "neutral"}
