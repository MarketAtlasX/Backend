import logging
from typing import Any

from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class DebateAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()

    async def run_debate(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        knowledge = retrieve_context(query, limit=5)

        debate_roles = [
            ("Conflict Analyst", "Analyze conflict dynamics, escalation risks, and security implications"),
            ("Energy Analyst", "Analyze energy market impacts, supply chains, and commodity prices"),
            ("Market Strategist", "Analyze financial market implications, sector rotations, and investment flows"),
            ("Risk Analyst", "Assess overall risk levels, probability weights, and hedge effectiveness"),
        ]

        perspectives = []
        for role, instruction in debate_roles:
            prompt = f"""{instruction} regarding this query.

Query: {query}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Context: ' + str(context) if context else ''}

Provide your {role} perspective in 2-3 sentences:"""

            response = self.llm.generate(
                prompt,
                system_prompt=f"You are a {role} at MarketAtlas. Be analytical and data-driven.",
                temperature=0.3,
            )
            perspectives.append({"role": role, "analysis": response})

        synthesis_prompt = """You are the Lead Intelligence Officer at MarketAtlas. Synthesize the following analyst perspectives
into a final, coherent answer addressing the user's query.

"""
        for p in perspectives:
            synthesis_prompt += f"\n### {p['role']}\n{p['analysis']}\n"

        synthesis_prompt += f"\nQuery: {query}\n\nProvide a final synthesized answer that reconciles different viewpoints:"

        final_response = self.llm.generate(
            synthesis_prompt,
            system_prompt="You are a Lead Intelligence Officer. Synthesize analysis into clear, actionable intelligence.",
            temperature=0.3,
        )

        return {
            "agent": "DebateAgent",
            "response": final_response,
            "perspectives": perspectives,
        }
