import json
import logging
from typing import Any

from ..event_memory.event_store import event_store
from ..event_memory.event_schema import SimilarityResponse
from ..explain.attention_explainer import AttentionExplainer
from ..explain.graph_explainer import GraphExplainer
from ..llm.provider import get_llm
from ..utils.constants import SECTOR_KEYWORDS

logger = logging.getLogger(__name__)


class EventSimilarityAgent:
    def __init__(self):
        self.llm = get_llm()
        self.attention = AttentionExplainer()
        self.graph_explainer = GraphExplainer()

    async def process(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        entities = self._extract_entities(query)
        sectors = self._extract_sectors(query)

        result = event_store.find_similar(
            query=query,
            top_k=5,
            sector_filter=sectors or None,
        )

        formatted = self._format_response(result, query)

        ctx = context or {}
        ctx.update({"query": query, "entities": entities, "sectors": sectors, "similar_events": result.similar_events})
        attn_result = self.attention.explain(context=ctx)
        graph_result = self.graph_explainer.explain(context=ctx)
        attn_formatted = self.attention.format_explanation(attn_result)

        return {
            "agent": "EventSimilarityAgent",
            "response": formatted,
            "similarity_data": result.model_dump(),
            "entities": entities,
            "explanations": {
                "attention": attn_result.attention.model_dump() if attn_result.attention else None,
                "graph": graph_result.graph.model_dump() if graph_result.graph else None,
            },
            "explanation_text": attn_formatted,
        }

    def _format_response(self, response: SimilarityResponse, query: str) -> str:
        lines = []
        lines.append("## Historical Event Similarity Analysis")
        lines.append("")
        lines.append(f"**Query:** {query}")
        lines.append("")
        lines.append("### Similar Historical Events")
        lines.append("")

        for i, result in enumerate(response.similar_events, 1):
            ev = result.event
            lines.append(f"**{i}. {ev.name}**")
            lines.append(f"   - Overall Similarity: **{result.similarity_score*100:.0f}%**")
            lines.append(f"   - Text Similarity: {result.text_similarity*100:.0f}% | "
                         f"Entity Similarity: {result.entity_similarity*100:.0f}% | "
                         f"Sector Similarity: {result.sector_similarity*100:.0f}%")
            lines.append(f"   - Type: {ev.event_type.replace('_', ' ').title()} | Date: {ev.date}")
            lines.append(f"   - {ev.summary}")
            lines.append("")

        if response.aggregated_outcomes:
            lines.append("### Aggregated Historical Outcomes")
            lines.append("")
            lines.append("| Sector | Impact |")
            lines.append("|--------|--------|")
            for sector, impact in sorted(response.aggregated_outcomes.items(), key=lambda x: abs(x[1]), reverse=True):
                sign = "+" if impact > 0 else ""
                lines.append(f"| {sector} | {sign}{impact}% |")
            lines.append("")
            lines.append(f"*Based on top {min(len(response.similar_events), 3)} most similar events*")
            lines.append("")
            lines.append(f"**Confidence:** {response.confidence*100:.0f}%")

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

        lines = []
        lines.append("# MarketAtlas Intelligence Report")
        lines.append("")
        lines.append(f"## Query: {query}")
        lines.append("")

        similar_events = similar[:3] if similar else []
        if similar_events:
            lines.append("### Similar Historical Events")
            lines.append("")
            for i, ev_data in enumerate(similar_events, 1):
                ev = ev_data.get("event", {}) if isinstance(ev_data, dict) else getattr(ev_data, "event", {})
                name = ev.get("name", "Unknown") if isinstance(ev, dict) else getattr(ev, "name", "Unknown")
                score = ev_data.get("similarity_score", 0) if isinstance(ev_data, dict) else getattr(ev_data, "similarity_score", 0)
                score_pct = score * 100 if isinstance(score, float) and score <= 1 else score
                lines.append(f"{i}. {name}")
                lines.append(f"   Similarity: **{score_pct:.0f}%**")
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

    def _extract_entities(self, text: str) -> list[str]:
        prompt = f"""Extract all geopolitical entities (countries, regions, organizations, people, militant groups) from this query.
Return ONLY a JSON array of strings.
Query: {text}"""
        try:
            result = self.llm.generate(prompt, temperature=0.1)
            result = result.strip().strip("```json").strip("```").strip()
            return json.loads(result) if result.startswith("[") else []
        except Exception:
            return []

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
