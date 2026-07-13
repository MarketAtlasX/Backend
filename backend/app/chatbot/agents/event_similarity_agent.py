import json
import logging
from typing import Any

from ..event_memory.event_store import event_store
from ..explain.attention_explainer import AttentionExplainer
from ..llm.provider import get_llm
from ..pipeline_adapter import (
    run_entity_extraction_pipeline,
    run_similarity_pipeline,
    run_historical_analogs_pipeline,
    run_graph_path_pipeline,
)
from ..utils.constants import SECTOR_KEYWORDS

logger = logging.getLogger(__name__)


class EventSimilarityAgent:
    def __init__(self):
        self.llm = get_llm()
        self.attention = AttentionExplainer()

    async def process(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        entities = await self._extract_entities(query)
        sectors = self._extract_sectors(query)

        pipeline_result = await run_similarity_pipeline(query=query, content=query, top_k=20)

        similar_events = pipeline_result.get("similar_events", [])
        aggregated = pipeline_result.get("aggregated_outcomes", {})

        analogs = await run_historical_analogs_pipeline(
            sentiment=0.0,
            event_type="economic",
        )

        path_result = await run_graph_path_pipeline(
            entities=entities or ["Geopolitical Event"],
            sectors=sectors or ["Energy", "Defense"],
        )

        formatted = self._format_response(similar_events, aggregated, analogs, query, pipeline_result.get("confidence", 0.5))

        ctx = context or {}
        ctx.update({
            "query": query,
            "entities": entities,
            "sectors": sectors,
            "similar_events": similar_events,
        })
        attn_result = await self.attention.explain(context=ctx)
        attn_formatted = self.attention.format_explanation(attn_result)

        return {
            "agent": "EventSimilarityAgent",
            "response": formatted,
            "similarity_data": {
                "similar_events": similar_events,
                "aggregated_outcomes": aggregated,
                "entities": entities,
                "sectors": sectors,
                "confidence": pipeline_result.get("confidence", 0.5),
                "historical_analogs": analogs,
                "graph_paths": path_result.get("graph_paths", []),
            },
            "entities": entities,
            "explanations": {
                "attention": attn_result.attention.model_dump() if attn_result.attention else None,
                "historical_analogs": analogs,
                "graph_paths": path_result.get("graph_paths", []),
            },
            "explanation_text": attn_formatted,
        }

    def _get_entity_name(self, ev: Any) -> str:
        if isinstance(ev, dict):
            return ev.get("title", ev.get("matched_event_id", ev.get("name", "Unknown")))
        return getattr(ev, "name", "Unknown")

    def _get_score(self, ev: Any) -> float:
        if isinstance(ev, dict):
            return ev.get("similarity_score", ev.get("score", 0))
        return getattr(ev, "similarity_score", 0)

    def _format_response(
        self,
        similar_events: list,
        aggregated: dict[str, float],
        analogs: list[dict],
        query: str,
        confidence: float = 0.5,
    ) -> str:
        lines = []
        lines.append("## Historical Event Similarity Analysis")
        lines.append("")
        lines.append(f"**Query:** {query}")
        lines.append("")

        if similar_events:
            lines.append("### Similar Historical Events")
            lines.append("")
            for i, ev in enumerate(similar_events[:5], 1):
                name = self._get_entity_name(ev)
                score = self._get_score(ev)
                lines.append(f"**{i}. {name}**")
                lines.append(f"   - Overall Similarity: **{score*100:.0f}%**")
                payload = ev.get("payload", {}) if isinstance(ev, dict) else {}
                if payload:
                    sim = payload.get("similarity", 0)
                    if sim:
                        lines.append(f"   - Confidence: {sim*100:.0f}%")
                outcome = ev.get("market_outcome", {}) if isinstance(ev, dict) else {}
                if outcome:
                    direction = outcome.get("direction", "neutral")
                    conf = outcome.get("confidence", 0)
                    lines.append(f"   - Market Direction: {direction} (confidence: {conf*100:.0f}%)")
                lines.append("")

        if analogs:
            lines.append("### Historical Analogs (Explainability)")
            lines.append("")
            for a in analogs[:3]:
                lines.append(f"- **{a['name']}** — similarity: {a['similarity_score']*100:.0f}%, type: {a['type']}, impact: {a['impact']}")
            lines.append("")

        if aggregated:
            lines.append("### Aggregated Historical Outcomes")
            lines.append("")
            lines.append("| Sector | Impact |")
            lines.append("|--------|--------|")
            for sector, impact in sorted(aggregated.items(), key=lambda x: abs(x[1]), reverse=True):
                sign = "+" if impact > 0 else ""
                lines.append(f"| {sector} | {sign}{impact}% |")
            lines.append("")

        if not similar_events and not analogs:
            lines.append("No significant historical parallels found for this query.")
            lines.append("")

        if similar_events:
            lines.append(f"**Confidence:** {confidence*100:.0f}%")

        return "\n".join(lines)

    def format_full_report(
        self,
        query: str,
        similarity_data: dict,
        news_response: str,
        impact_response: str,
        forecast_response: str,
        report_response: str,
        explanation_text: str = "",
    ) -> str:
        similar = similarity_data.get("similar_events", []) if similarity_data else []
        outcomes = similarity_data.get("aggregated_outcomes", {}) if similarity_data else {}
        analogs = similarity_data.get("historical_analogs", []) if similarity_data else []

        lines = []
        lines.append("# MarketAtlas Intelligence Report")
        lines.append("")
        lines.append(f"## Query: {query}")
        lines.append("")

        if similar:
            lines.append("### Similar Historical Events")
            lines.append("")
            for i, ev in enumerate(similar[:3], 1):
                name = self._get_entity_name(ev)
                score = self._get_score(ev)
                lines.append(f"{i}. {name}")
                lines.append(f"   Similarity: **{score*100:.0f}%**")
                lines.append("")

        if analogs:
            lines.append("### Historical Analogs")
            lines.append("")
            for a in analogs[:3]:
                lines.append(f"- **{a['name']}** — {a['similarity_score']*100:.0f}% match")
            lines.append("")

        if outcomes:
            lines.append("### Historical Outcomes")
            lines.append("")
            for sector, impact in sorted(outcomes.items(), key=lambda x: abs(x[1]), reverse=True):
                sign = "+" if impact > 0 else ""
                lines.append(f"   **{sector}:** {sign}{impact}%")
            lines.append("")

        lines.append("### Current Situation & Impact Analysis")
        lines.append("")
        lines.append(news_response[:500] if news_response else "No current event data available.")
        lines.append("")
        lines.append(impact_response[:500] if impact_response else "")
        lines.append("")

        if forecast_response:
            lines.append("### Market Forecast")
            lines.append("")
            lines.append(forecast_response[:500])
            lines.append("")

        if explanation_text:
            lines.append("### Explainable Intelligence")
            lines.append("")
            lines.append(explanation_text)
            lines.append("")

        lines.append("### Summary")
        lines.append("")
        summary_text = report_response[:800] if report_response else "Analysis complete."
        lines.append(summary_text)
        lines.append("")

        confidence = similarity_data.get("confidence", 0.5) if similarity_data else 0.5
        lines.append(f"**Confidence:** {confidence*100:.0f}%")
        lines.append("")
        lines.append("---")
        lines.append("*MarketAtlas AI | Geopolitical Trading Intelligence*")

        return "\n".join(lines)

    async def _extract_entities(self, text: str) -> list[str]:
        try:
            result = await run_entity_extraction_pipeline(text)
        except Exception:
            result = {"countries": [], "organizations": []}
        return result.get("countries", []) + result.get("organizations", [])

    def _extract_sectors(self, text: str) -> list[str]:
        text_lower = text.lower()
        found = []
        for sector, keywords in SECTOR_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(sector.title())
        return found if found else self._llm_extract_sectors(text)

    def _llm_extract_sectors(self, text: str) -> list[str]:
        prompt = f"""Extract the affected market sectors from this query. Common sectors include: Energy, Defense, Technology, Financials, Shipping, Agriculture, Airlines, Manufacturing, Healthcare, Cybersecurity, Real Estate, Retail, Travel & Hospitality.
Return ONLY a JSON array of strings.
Query: {text}"""
        try:
            result = self.llm.generate(prompt, temperature=0.1)
            result = result.strip().strip("```json").strip("```").strip()
            return json.loads(result) if result.startswith("[") else []
        except Exception:
            return []
