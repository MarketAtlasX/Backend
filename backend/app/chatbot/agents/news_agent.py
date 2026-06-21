import json
import logging
from datetime import datetime
from typing import Any

from ..knowledge.neo4j_client import Neo4jClient
from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class NewsAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()
        self.neo4j = Neo4jClient()
        self._session = db_session
        self._events_cache = []

    async def _load_recent_events(self):
        try:
            if self._session:
                from sqlalchemy import select
                stmt = select(__import__('app.models.raw_event', fromlist=['RawEvent']).RawEvent).order_by(
                    __import__('app.models.raw_event', fromlist=['RawEvent']).RawEvent.fetched_at.desc()
                ).limit(20)
                result = await self._session.execute(stmt)
                self._events_cache = list(result.scalars().all())
                return
        except Exception as e:
            logger.warning(f"Could not load events from DB: {e}")

        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                stmt = select(__import__('app.models.raw_event', fromlist=['RawEvent']).RawEvent).order_by(
                    __import__('app.models.raw_event', fromlist=['RawEvent']).RawEvent.fetched_at.desc()
                ).limit(20)
                result = await session.execute(stmt)
                self._events_cache = list(result.scalars().all())
        except Exception as e:
            logger.warning(f"Could not create session for events: {e}")

    def _format_events(self) -> str:
        if not self._events_cache:
            return ""
        lines = ["Recent geopolitical events from live data:"]
        for e in self._events_cache[:10]:
            ts = e.fetched_at.strftime("%Y-%m-%d %H:%M") if e.fetched_at else "unknown"
            lines.append(f"- [{ts}] [{e.source}] {e.title}")
            if e.description:
                lines.append(f"  {e.description[:200]}")
        return "\n".join(lines)

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        await self._load_recent_events()
        knowledge = retrieve_context(query, limit=3)
        events_text = self._format_events()

        system_prompt = """You are a geopolitical news analyst at MarketAtlas. Summarize recent events relevant to the query.
Be factual, precise, and cite sources where possible. Focus on actionable intelligence.
Use the live event data provided below — it comes from real-time news feeds."""

        prompt = f"""Query: {query}

Today's date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Live Event Data (from real-time feeds):
{events_text if events_text else "No recent events in database — relying on knowledge base."}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Provide a concise summary of relevant news/events with timestamps and sources:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)

        entities = self._extract_entities(query)
        graph_context = ""
        for entity in entities:
            gc = self.neo4j.get_graph_context(entity)
            if gc:
                graph_context += f"\nRelations for {entity}:\n{gc}"

        return {
            "agent": "NewsAgent",
            "response": response,
            "sources": [f"MarketAtlas Live: {e.title}" for e in self._events_cache[:5]],
            "entities": entities,
            "graph_context": graph_context,
        }

    def _extract_entities(self, text: str) -> list[str]:
        prompt = f"""Extract geopolitical entities (countries, organizations, people, sectors) from this query.
Return ONLY a JSON array of strings, nothing else.
Query: {text}"""
        try:
            result = self.llm.generate(prompt, temperature=0.1)
            result = result.strip().strip("```json").strip("```").strip()
            return json.loads(result) if result.startswith("[") else []
        except Exception:
            return []
