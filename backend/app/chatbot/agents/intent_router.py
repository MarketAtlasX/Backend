import re

from ..llm.provider import get_llm
from ..models import IntentType

FOLLOWUP_PATTERNS = re.compile(
    r"^(what|which|who|where|why|how|tell me more|explain|elaborate|give me|show me|list|name"
    r"|can you|could you|what about|how about|what's|what are|and|but|so|"
    r"i asked|that|it|they|them|this|those|these|the|a|an)",
    re.IGNORECASE,
)

PRONOUN_PATTERN = re.compile(r"\b(it|they|them|this|that|those|these|the|its|their)\b", re.IGNORECASE)


class IntentRouter:
    def __init__(self):
        self.llm = get_llm()

    def classify(self, query: str, conversation_history: str = "") -> tuple[IntentType, float]:
        query_lower = query.lower()

        keyword_map = {
            IntentType.NEWS: ["latest", "news", "update", "headline", "breaking", "what happened", "sanctions", "conflict"],
            IntentType.MARKET: ["price", "market", "stock", "etf", "index", "s&p", "nifty", "sensex", "trading", "up today", "down today"],
            IntentType.IMPACT: ["impact", "affect", "consequence", "effect", "how does", "what does this mean", "why is", "tension", "geopolitical"],
            IntentType.RECOMMENDATION: ["buy", "sell", "invest", "should i", "recommend", "portfolio", "allocate", "position"],
            IntentType.SIMULATION: ["simulate", "what if", "scenario", "if happens", "if occurs", "what would"],
            IntentType.GRAPH: ["relationship", "connection", "how is", "related to", "linked to", "network", "graph", "connection between"],
            IntentType.REPORT: ["report", "brief", "analysis", "summary", "deep dive", "intelligence report", "overview"],
            IntentType.SIMILARITY: ["similar", "comparable", "analogous", "parallel", "like", "resemble", "alike", "remind", "mirror", "echo", "reminiscent", "historic", "precedent", "past event"],
            IntentType.RISK: ["risk", "volatility", "volatile", "safe", "dangerous", "drawdown", "value at risk", "how risky", "risk score", "risk assessment", "risk analysis"],
        }

        scores = {}
        for intent, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', query_lower))
            if score > 0:
                scores[intent] = score

        if not scores:
            context_hint = ""
            if conversation_history and PRONOUN_PATTERN.search(query):
                last_line = conversation_history.strip().split("\n")[-1] if conversation_history else ""
                if last_line:
                    context_hint = f"\nThe user's last message was: {last_line}"

            prompt = f"""Classify this user query into exactly one category. Return ONLY the category name.

Categories:
- NEWS: Current events, news, updates, developments
- MARKET: Market data, prices, trading, stocks, movements
- IMPACT: Geopolitical impact analysis, consequences, effects
- RECOMMENDATION: Investment advice, buying/selling suggestions
- SIMULATION: What-if scenarios, hypothetical situations
- GRAPH: Entity relationships, connections, network queries
- REPORT: Comprehensive analysis, briefings, intelligence reports
- SIMILARITY: Historical parallels, similar past events, precedents, comparisons to historical events
- RISK: Risk assessment, volatility analysis, risk scores, safety of investments, risk evaluation

This is a follow-up question in an ongoing conversation.{context_hint}
If the query refers to a previous exchange, classify it based on the topic of the conversation.

Query: {query}

Category:"""
            result = self.llm.generate(prompt, temperature=0.1).strip().upper()
            for intent in IntentType:
                if intent.value in result:
                    return intent, 0.7
            return IntentType.IMPACT, 0.5

        best_intent = max(scores, key=scores.get)
        confidence = min(0.5 + (scores[best_intent] * 0.15), 0.95)
        return best_intent, confidence

    def get_agents_for_intent(self, intent: IntentType) -> list[str]:
        routing = {
            IntentType.NEWS: ["NewsAgent"],
            IntentType.MARKET: ["MarketAgent", "NewsAgent"],
            IntentType.IMPACT: ["ImpactAgent", "NewsAgent", "MarketAgent"],
            IntentType.RECOMMENDATION: ["RecommendationAgent", "ImpactAgent", "GraphAgent"],
            IntentType.SIMULATION: ["SimulationAgent", "ImpactAgent"],
            IntentType.GRAPH: ["GraphAgent", "NewsAgent"],
            IntentType.REPORT: ["ReportAgent", "ImpactAgent", "MarketAgent", "GraphAgent", "NewsAgent"],
            IntentType.SIMILARITY: ["EventSimilarityAgent", "ImpactAgent"],
            IntentType.RISK: ["RiskAgent", "MarketAgent"],
        }
        return routing.get(intent, ["ImpactAgent"])
