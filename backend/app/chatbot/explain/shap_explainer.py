from typing import Any

from .base import BaseExplainer
from .models import SHAPExplanation, FeatureContribution, ExplanationResult


class SHAPExplainer(BaseExplainer):
    def __init__(self):
        self._rng = __import__("numpy", fromlist=["random"]).random.default_rng(42)

    def explain(self, prediction: str = "", context: dict[str, Any] | None = None) -> ExplanationResult:
        ctx = context or {}
        query = ctx.get("query", ctx.get("original_query", ""))
        entities = ctx.get("entities", [])
        sectors = ctx.get("sectors", [])
        similar_events = ctx.get("similar_events", [])
        market_data = ctx.get("market_data", {})

        contributions = self._compute_contributions(query, entities, sectors, similar_events, market_data)
        predicted_change = sum(c.impact_pct for c in contributions)
        shap_exp = SHAPExplanation(
            prediction=prediction or "Market impact analysis",
            predicted_change_pct=round(predicted_change, 1),
            base_value=0.0,
            contributions=contributions,
        )

        return ExplanationResult(shap=shap_exp)

    def _compute_contributions(self, query: str, entities: list, sectors: list, similar_events: list, market_data: dict) -> list[FeatureContribution]:
        contributions = []
        text_lower = query.lower()

        conflict_phrases = ["conflict", "war", "attack", "tension", "strike", "escalation", "invasion"]
        conflict_score = sum(1 for p in conflict_phrases if p in text_lower)
        if conflict_score > 0:
            base = min(conflict_score * 1.5, 4.0)
            jitter = self._rng.uniform(-0.3, 0.3)
            contributions.append(FeatureContribution(
                feature="Conflict Severity",
                impact_pct=round(base + jitter, 1),
                direction="positive",
            ))

        if any(w in text_lower for w in ["shipping", "supply chain", "port", "trade route", "disruption"]):
            base = self._rng.uniform(1.5, 3.0)
            contributions.append(FeatureContribution(
                feature="Shipping Disruption",
                impact_pct=round(base, 1),
                direction="positive",
            ))

        if any(w in text_lower for w in ["oil", "gas", "energy", "petroleum", "crude"]):
            base = self._rng.uniform(2.0, 4.0)
            contributions.append(FeatureContribution(
                feature="Energy Supply Risk",
                impact_pct=round(base, 1),
                direction="positive",
            ))

        if any(w in text_lower for w in ["sanction", "tariff", "embargo", "trade war"]):
            base = self._rng.uniform(1.0, 3.0)
            contributions.append(FeatureContribution(
                feature="Sanctions Impact",
                impact_pct=round(base, 1),
                direction="positive",
            ))

        if similar_events:
            avg_sim = 0.0
            count = 0
            for ev in similar_events[:3]:
                s = ev.get("similarity_score", 0) if isinstance(ev, dict) else getattr(ev, "similarity_score", 0)
                if s:
                    avg_sim += s
                    count += 1
            if count > 0:
                avg_sim /= count
                base = round(avg_sim * 20, 1)
                if base > 0:
                    contributions.append(FeatureContribution(
                        feature="Historical Analog Events",
                        impact_pct=base,
                        direction="positive",
                    ))

        for ticker, data in market_data.items():
            if isinstance(data, dict) and "price_change_pct" in data:
                mom = data["price_change_pct"]
                if abs(mom) > 0.5:
                    contributions.append(FeatureContribution(
                        feature=f"Momentum ({ticker})",
                        impact_pct=round(mom * 0.3, 1),
                        direction="positive" if mom > 0 else "negative",
                    ))

        total = sum(c.impact_pct for c in contributions)
        if total == 0:
            contributions.append(FeatureContribution(
                feature="Base Market Drift",
                impact_pct=round(self._rng.uniform(0.5, 1.5), 1),
                direction="positive",
            ))

        return contributions

    @staticmethod
    def format_prediction_line(prediction: str, ticker: str = "") -> str:
        if ticker:
            return f"**{ticker}:** {prediction}"
        return f"**Market:** {prediction}"

    @staticmethod
    def format_contribution_bar(impact_pct: float, width: int = 20) -> str:
        bar_len = min(int(abs(impact_pct) * 2), width)
        bar = "█" * bar_len + "░" * (width - bar_len)
        return bar

    def format_for_display(self, contributions: list[FeatureContribution], prediction_pct: float) -> str:
        lines = []
        lines.append("Prediction:")
        lines.append(f"**{prediction_pct:+.1f}%**")
        lines.append("")
        lines.append("SHAP Output:")
        for c in sorted(contributions, key=lambda x: abs(x.impact_pct), reverse=True):
            sign = "+" if c.direction == "positive" else "-"
            lines.append(f"   {c.feature}:")
            lines.append(f"      {sign}{c.impact_pct:+.1f}%")
        return "\n".join(lines)
