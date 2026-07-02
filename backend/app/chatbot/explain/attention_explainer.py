from typing import Any

from .base import BaseExplainer
from .models import AttentionExplanation, AttentionWeight, ExplanationResult


class AttentionExplainer(BaseExplainer):
    def __init__(self):
        self._rng = __import__("numpy", fromlist=["random"]).random.default_rng(42)

    def explain(self, prediction: str = "", context: dict[str, Any] | None = None) -> ExplanationResult:
        ctx = context or {}
        query = ctx.get("query", ctx.get("original_query", ""))
        similar_events = ctx.get("similar_events", [])
        entities = ctx.get("entities", [])
        sectors = ctx.get("sectors", [])

        event_weights = self._compute_event_weights(query, similar_events)
        feature_weights = self._compute_feature_weights(query, entities, sectors)

        attn_exp = AttentionExplanation(
            query=query,
            top_events=event_weights,
            top_features=feature_weights,
        )

        return ExplanationResult(attention=attn_exp)

    def _compute_event_weights(self, query: str, similar_events: list) -> list[AttentionWeight]:
        weights = []
        text_lower = query.lower()

        for ev in similar_events[:5]:
            if isinstance(ev, dict):
                ev_obj = ev.get("event", {})
                name = ev_obj.get("name", "Unknown") if isinstance(ev_obj, dict) else getattr(ev_obj, "name", "Unknown")
                score = ev.get("similarity_score", 0)
            else:
                ev_obj = getattr(ev, "event", None)
                name = getattr(ev_obj, "name", "Unknown") if ev_obj else "Unknown"
                score = getattr(ev, "similarity_score", 0)

            weight = max(0.01, score)
            weights.append(AttentionWeight(input_label=name, weight=round(weight, 4)))

        if not weights:
            keywords = ["Iran", "Israel", "Middle East", "Oil", "Conflict", "War", "Sanctions"]
            found = [kw for kw in keywords if kw.lower() in text_lower]
            for kw in found[:5]:
                weights.append(AttentionWeight(input_label=kw, weight=round(self._rng.uniform(0.1, 0.4), 4)))

        total = sum(w.weight for w in weights) or 1.0
        for w in weights:
            w.weight = round(w.weight / total, 4)

        weights.sort(key=lambda x: x.weight, reverse=True)
        for i, w in enumerate(weights):
            w.rank = i + 1

        return weights

    def _compute_feature_weights(self, query: str, entities: list, sectors: list) -> list[AttentionWeight]:
        text_lower = query.lower()
        feature_map = {
            "Geopolitical Risk": ["conflict", "war", "tension", "attack", "escalation"],
            "Supply Chain Impact": ["supply chain", "shipping", "disruption", "shortage"],
            "Energy Prices": ["oil", "gas", "energy", "petroleum", "crude"],
            "Defensive Rotation": ["defense", "military", "security", "safe haven"],
            "Monetary Policy": ["rate", "fed", "central bank", "inflation", "interest"],
            "Trade Policy": ["tariff", "sanction", "trade war", "embargo"],
            "Market Sentiment": ["fear", "uncertainty", "volatility", "risk-off"],
            "Sector Rotation": ["sector", "rotation", "cyclical", "defensive"],
        }

        weights = []
        for feature, keywords in feature_map.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                base = 0.1 * score + self._rng.uniform(0, 0.05)
                weights.append(AttentionWeight(input_label=feature, weight=round(min(base, 0.5), 4)))

        if not weights:
            weights = [
                AttentionWeight(input_label="Geopolitical Risk", weight=round(self._rng.uniform(0.2, 0.4), 4)),
                AttentionWeight(input_label="Energy Prices", weight=round(self._rng.uniform(0.15, 0.3), 4)),
                AttentionWeight(input_label="Market Sentiment", weight=round(self._rng.uniform(0.1, 0.2), 4)),
            ]

        total = sum(w.weight for w in weights) or 1.0
        for w in weights:
            w.weight = round(w.weight / total, 4)

        weights.sort(key=lambda x: x.weight, reverse=True)
        return weights
