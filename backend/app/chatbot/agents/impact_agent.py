import json
import logging
from typing import Any

from ..knowledge.neo4j_client import Neo4jClient
from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class ImpactAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()
        self.neo4j = Neo4jClient()
        self._session = db_session
        self._signals_cache = []
        self._events_cache = []

    async def _load_real_data(self):
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                from app.models.raw_event import RawEvent
                stmt = select(RawEvent).order_by(RawEvent.fetched_at.desc()).limit(15)
                result = await session.execute(stmt)
                self._events_cache = list(result.scalars().all())
        except Exception as e:
            logger.warning(f"Could not load impact data: {e}")

    def _format_signals_and_events(self) -> str:
        lines = []
        if self._events_cache:
            lines.append("Recent geopolitical events:")
            for e in self._events_cache[:10]:
                ts = e.fetched_at.strftime("%Y-%m-%d %H:%M") if e.fetched_at else "unknown"
                lines.append(f"- [{ts}] [{e.source}] {e.title}")
        else:
            lines.append("No recent events in database.")
        return "\n".join(lines)

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        await self._load_real_data()
        knowledge = retrieve_context(query, limit=5)
        real_data = self._format_signals_and_events()

        system_prompt = """You are a geopolitical impact analyst at MarketAtlas. Assess how geopolitical events affect markets, sectors, and economies.
Consider direct and indirect consequences, cascading effects, and probability-weighted outcomes.
Use the live event data provided below."""

        prompt = f"""Query: {query}

Today's date: {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Live Event Data (from real-time feeds):
{real_data}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Analyze the geopolitical impact. Include:
1. Primary effects (direct consequences)
2. Secondary effects (indirect/ripple effects)
3. Sector impact analysis
4. Geographic impact scope
5. Time horizon (short/medium/long term)
6. Confidence level

Provide structured analysis:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt, history=(context or {}).get('conversation_history'))

        entities = self._extract_entities(query)
        graph_context = ""
        for entity in entities[:3]:
            gc = self.neo4j.get_graph_context(entity)
            if gc:
                graph_context += f"\nKnowledge graph relations for {entity}:\n{gc}"

        return {
            "agent": "ImpactAgent",
            "response": response,
            "composite_risk": self._calculate_risk(response),
            "entities": entities,
            "graph_context": graph_context,
        }

    def _extract_entities(self, text: str) -> list[str]:
        prompt = f"""Extract all geopolitical entities (countries, regions, organizations, people, sectors) from this query.
Return ONLY a JSON array of strings.
Query: {text}"""
        try:
            result = self.llm.generate(prompt, temperature=0.1)
            result = result.strip().strip("```json").strip("```").strip()
            return json.loads(result) if result.startswith("[") else []
        except Exception:
            return []

    def _calculate_risk(self, text: str) -> float:
        risk_keywords = ["high", "severe", "critical", "significant", "major", "escalation",
                         "disruption", "crisis", "conflict", "war", "sanctions", "collapse"]
        count = sum(1 for kw in risk_keywords if kw in text.lower())
        return min(round(0.3 + count * 0.08, 2), 0.95)
