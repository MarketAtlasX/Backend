import json
import logging
from datetime import datetime
from typing import Any

from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class MarketAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()
        self._session = db_session
        self._prices_cache = []
        self._tickers_seen = set()

    async def _load_market_data(self):
        try:
            from app.repositories.market_price import MarketPriceRepository
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                repo = MarketPriceRepository(session)
                from sqlalchemy import select
                from app.models.market_price import MarketPrice
                stmt = select(MarketPrice).order_by(MarketPrice.price_date.desc()).limit(30)
                result = await session.execute(stmt)
                self._prices_cache = list(result.scalars().all())
        except Exception as e:
            logger.warning(f"Could not load market data: {e}")

    def _format_prices(self) -> str:
        if not self._prices_cache:
            return ""
        lines = ["Live market prices:"]
        for p in self._prices_cache[:15]:
            ts = p.price_date.strftime("%Y-%m-%d") if p.price_date else "unknown"
            ticker = p.symbol if hasattr(p, 'symbol') else f"entity_{p.entity_id}"
            lines.append(f"- {ticker}: ${p.price:.2f} on {ts}")
            self._tickers_seen.add(ticker)
        return "\n".join(lines)

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        await self._load_market_data()
        knowledge = retrieve_context(query, limit=3)
        prices_text = self._format_prices()

        system_prompt = """You are a market analyst at MarketAtlas. Analyze market data and provide actionable trading insights.
Use the live market price data provided below. Be precise with numbers and trends."""

        prompt = f"""Query: {query}

Today's date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

Live Market Prices (from real-time feeds):
{prices_text if prices_text else "No market prices available in database."}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Provide market analysis including:
1. Price trends and momentum
2. Volume analysis
3. Sector implications
4. Key levels to watch

Analysis:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt)

        return {
            "agent": "MarketAgent",
            "response": response,
            "market_data": {
                "tickers": list(self._tickers_seen),
                "num_prices": len(self._prices_cache),
            },
        }
