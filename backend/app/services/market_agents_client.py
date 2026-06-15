"""HTTP client for the market_agents microservice gateway.

Replaces the previous direct Python import of market_agents with a proper
HTTP-based decoupled integration. The market_agents service runs as a
standalone FastAPI gateway (port 8004) and this client calls its /analyze
endpoint.
"""

import logging
from decimal import Decimal
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


_SIGNAL_MAP = {
    "BUY": "buy",
    "SELL": "sell",
    "HOLD": "hold",
    "SHORT": "short",
}


class MarketAgentsClient:
    """Thin HTTP client for the market_agents gateway service.

    Usage:
        result = await market_agents_client.analyze(
            event_title="...",
            event_description="...",
            event_type="sanction",
            severity="high",
            entity_name="Apple Inc",
            ticker_symbol="AAPL",
            current_price=Decimal("150.00"),
            price_history=[148.0, 149.0, 150.0, 151.0, 152.0],
        )
        signal_type = result["signal_type"]  # "buy" | "sell" | "hold" | "short"
    """

    def __init__(self, base_url: str = "") -> None:
        self._base_url = (base_url or settings.market_agents_url).rstrip("/")

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
    ) -> dict[str, Any]:
        """Run the market agents pipeline for a single entity.

        Sends {text, prices, volumes} to the gateway at POST /analyze and
        maps the AnalysisResponse (snapshot + impact + recommendation) back
        to the flat dict that ai_service.py expects.

        Falls back to HOLD/0.5 if the gateway is unreachable.
        """
        text_parts = [event_title]
        if event_description:
            text_parts.append(event_description)
        text_parts.append(f"Entity: {entity_name}")
        text = ". ".join(text_parts)

        prices = price_history if price_history and len(price_history) >= 2 else [100, 101, 102]
        volumes = None

        payload: dict[str, Any] = {
            "text": text,
            "prices": prices,
        }
        if volumes is not None:
            payload["volumes"] = volumes

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self._base_url}/analyze", json=payload)
                resp.raise_for_status()
                raw: dict[str, Any] = resp.json()
        except httpx.TimeoutException:
            logger.warning("market_agents gateway timed out — fallback to HOLD")
            return self._fallback()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "market_agents returned %s: %s",
                e.response.status_code,
                e.response.text,
            )
            return self._fallback()
        except httpx.RequestError as e:
            logger.warning("market_agents unreachable: %s", e)
            return self._fallback()

        snapshot = raw.get("snapshot", {})
        impact = raw.get("impact", {})
        recommendation = raw.get("recommendation", {})

        action = recommendation.get("action", "HOLD")
        signal_type = _SIGNAL_MAP.get(action.upper(), "hold")

        composite_risk = impact.get("composite_risk", 0.0)
        local_severity = impact.get("local_severity", 0.0)

        relations_raw = impact.get("relations", [])
        relations = [[str(r[0]), str(r[1]), str(r[2])] for r in relations_raw] if relations_raw else []

        return {
            "signal_type": signal_type,
            "confidence": max(0.5, min(1.0, (1.0 - composite_risk / 10.0))),
            "reasoning": recommendation.get("reason", "No specific reasoning provided."),
            "target_price": None,
            "stop_loss": None,
            "composite_risk": composite_risk,
            "local_severity": local_severity,
            "entities_identified": [entity_name] if entity_name else [],
            "relations": relations,
            "reasoning_snapshot": snapshot,
        }

    def _fallback(self) -> dict[str, Any]:
        return {
            "signal_type": "hold",
            "confidence": 0.5,
            "reasoning": "Market agents gateway unavailable — defaulting to HOLD",
            "target_price": None,
            "stop_loss": None,
            "composite_risk": 0.0,
            "local_severity": 0.0,
            "entities_identified": [],
            "relations": [],
            "reasoning_snapshot": {},
        }


market_agents_client = MarketAgentsClient()
