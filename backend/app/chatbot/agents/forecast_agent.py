import logging
from typing import Any

from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class ForecastAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        knowledge = retrieve_context(query, limit=5)

        system_prompt = """You are a geopolitical forecaster at MarketAtlas. Generate probability-weighted forecasts
with clear scenarios, time horizons, and confidence levels. Be specific and data-driven."""

        prompt = f"""Query: {query}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Generate forecasts including:
1. Most likely scenario with probability
2. Alternative scenarios
3. Key indicators to monitor
4. Time horizon for each scenario
5. Market implications
6. Confidence level

Forecast:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt, history=(context or {}).get('conversation_history'))

        return {
            "agent": "ForecastAgent",
            "response": response,
        }
