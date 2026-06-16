"""Trading signal generation from geopolitical impact analysis."""

import logging
from typing import Optional
from decimal import Decimal

from app.geopolitical.models import MarketSnapshot, ImpactResult, SignalResult

logger = logging.getLogger(__name__)


def generate_signal(
    impact: Optional[ImpactResult] = None,
    market: Optional[MarketSnapshot] = None,
    hedge_buffer: float = 0.05,
) -> SignalResult:
    risk = impact.composite_risk if impact else 0.0
    momentum = market.momentum if market else 0.0
    volatility = market.volatility if market else 0.0

    if volatility > 0.04:
        return SignalResult(action="HOLD", confidence=0.6, reason="High volatility environment")

    if risk >= 0.7 and momentum < 0:
        return SignalResult(action="SELL", confidence=min(risk, 0.9), reason="High geopolitical risk with negative momentum")

    if risk < 0.3 and momentum > 0:
        return SignalResult(action="BUY", confidence=max(0.5, 1.0 - risk), reason="Low geopolitical risk with positive momentum")

    if 0.3 <= risk < 0.7 and momentum < -hedge_buffer:
        return SignalResult(action="HOLD", confidence=0.5, reason="Hedging against negative momentum in moderate risk environment")

    return SignalResult(action="HOLD", confidence=0.5, reason="Neutral conditions")
