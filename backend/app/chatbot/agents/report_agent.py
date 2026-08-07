import logging
from datetime import datetime
from typing import Any

from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class ReportAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()
        self._session = db_session

    async def _load_events(self) -> str:
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                from app.models.raw_event import RawEvent
                stmt = select(RawEvent).order_by(RawEvent.fetched_at.desc()).limit(15)
                result = await session.execute(stmt)
                events = list(result.scalars().all())
                if events:
                    lines = ["Live events:"]
                    for e in events[:10]:
                        ts = e.fetched_at.strftime("%Y-%m-%d %H:%M") if e.fetched_at else "unknown"
                        lines.append(f"- [{ts}] [{e.source}] {e.title}")
                    return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Could not load events for report: {e}")
        return ""

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        knowledge = retrieve_context(query, limit=5)
        events_text = await self._load_events()

        system_prompt = """You are a senior intelligence analyst at MarketAtlas. Generate comprehensive intelligence reports
with clear structure, actionable insights, and well-supported conclusions. Use the live data provided."""

        prompt = f"""Query: {query}

Today's date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

{events_text if events_text else 'No live events in database.'}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Generate a structured intelligence report covering:
1. Executive Summary
2. Situation Overview
3. Key Stakeholders & Entities
4. Market Impact Analysis
5. Risk Assessment (score 0-1)
6. Scenario Analysis
7. Recommended Actions
8. Confidence Level

Intelligence Report:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt, history=(context or {}).get('conversation_history'))

        return {
            "agent": "ReportAgent",
            "response": response,
            "sources": ["MarketAtlas Intelligence", "Real-time Event Feed"],
        }
