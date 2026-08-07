import json
import logging
from typing import Any

from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class SimulationAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        knowledge = retrieve_context(query, limit=5)

        system_prompt = """You are a geopolitical scenario analyst at MarketAtlas. Run structured what-if simulations
considering multiple variables, cascading effects, and probability-weighted outcomes. Be systematic and data-driven."""

        prompt = f"""Query: {query}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Run a structured simulation. Return your analysis as a JSON object with these fields:
- scenario: Description of the scenario
- consequences: Dictionary of affected sectors/regions with expected impact
- probability: Probability of this scenario (0.0 to 1.0)
- time_horizon: Expected time frame (short/medium/long term)
- key_risks: List of key risk factors

Simulation JSON:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt, temperature=0.3, history=(context or {}).get('conversation_history'))

        try:
            result = json.loads(response.strip().strip("```json").strip("```").strip())
        except Exception:
            result = {
                "scenario": str(query),
                "consequences": {},
                "probability": 0.5,
                "time_horizon": "medium term",
                "key_risks": ["Uncertainty in analysis"],
            }

        return {
            "agent": "SimulationAgent",
            "response": json.dumps(result),
            "simulation": result,
        }
