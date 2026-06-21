import logging
from typing import Any

from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class RecommendationAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()
        self._session = db_session

    async def _load_signals(self) -> str:
        try:
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                from app.repositories.signal import SignalRepository
                repo = SignalRepository(session)
                signals = await repo.get_high_confidence(min_confidence=0.5, limit=10)
                if signals:
                    lines = ["Recent trading signals:"]
                    for s in signals:
                        lines.append(f"- {s.signal_type} {s.direction} (confidence: {s.confidence:.2f}): {s.reasoning[:100]}")
                    return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Could not load signals: {e}")
        return ""

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        knowledge = retrieve_context(query, limit=3)
        signals_text = await self._load_signals()

        system_prompt = """You are an investment strategist at MarketAtlas. Provide clear, actionable recommendations
with proper risk assessment and conviction levels. Consider both upside and downside scenarios.
Use any available signal data to ground your recommendations."""

        prompt = f"""Query: {query}

{'Live Trading Signals:' + signals_text if signals_text else 'No live signals available in database.'}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Provide recommendation including:
1. Directional view (BUY/HOLD/SELL)
2. Conviction level
3. Key drivers
4. Risk factors
5. Suggested position sizing

Recommendation:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)

        return {
            "agent": "RecommendationAgent",
            "response": response,
        }
