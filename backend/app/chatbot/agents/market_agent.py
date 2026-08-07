import logging
from datetime import datetime
from typing import Any

from ...services.financial_data_service import FinancialDataService
from ..llm.provider import get_llm
from ..rag.retriever import retrieve_context

logger = logging.getLogger(__name__)


class MarketAgent:
    def __init__(self, db_session=None):
        self.llm = get_llm()
        self._session = db_session
        self._tickers_seen = set()
        self._financial_service = FinancialDataService()

    def _extract_tickers(self, query: str) -> list[str]:
        words = query.split()
        tickers = []
        for w in words:
            clean = w.strip(".,;:!?$()[]").upper()
            if 1 <= len(clean) <= 5 and clean.isalpha():
                tickers.append(clean)
        known = {"SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "XLE", "XLF", "GDX", "TLT", "IWM", "DIA"}
        return [t for t in tickers if t in known] or ["SPY"]

    async def _load_market_data(self, query: str) -> str:
        try:
            tickers = self._extract_tickers(query)
            lines = []
            for ticker in tickers[:3]:
                try:
                    quote = self._financial_service.get_stock_quote(ticker)
                    if quote and "error" not in quote:
                        price = quote.get("price", quote.get("c", "N/A"))
                        change = quote.get("change_percent", quote.get("dp", 0))
                        lines.append(f"- {ticker}: ${price} ({change:+.2f}%)")
                        self._tickers_seen.add(ticker)
                except Exception:
                    pass
            if not lines:
                return ""
            return "Live market prices:\n" + "\n".join(lines)
        except Exception as e:
            logger.warning(f"Could not load financial data: {e}")
            return ""

    async def process(self, query: str, context: dict[str, Any] = None) -> dict[str, Any]:
        prices_text = await self._load_market_data(query)
        if not prices_text:
            try:
                from app.database import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    from sqlalchemy import select

                    from app.models.market_price import MarketPrice
                    stmt = select(MarketPrice).order_by(MarketPrice.price_date.desc()).limit(15)
                    result = await session.execute(stmt)
                    prices = list(result.scalars().all())
                    if prices:
                        lines = ["Live market prices (from database):"]
                        for p in prices:
                            ts = p.price_date.strftime("%Y-%m-%d") if p.price_date else "unknown"
                            ticker = p.symbol if hasattr(p, 'symbol') else f"entity_{p.entity_id}"
                            lines.append(f"- {ticker}: ${p.price:.2f} on {ts}")
                        prices_text = "\n".join(lines)
            except Exception:
                pass

        knowledge = retrieve_context(query, limit=3)

        system_prompt = """You are a market analyst at MarketAtlas. Analyze market data and provide actionable trading insights.
Use the live market price data provided below. Be precise with numbers and trends."""

        prompt = f"""Query: {query}

Today's date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

{prices_text if prices_text else "No market prices available."}

Relevant Knowledge:
{knowledge if knowledge else "No specific knowledge base results."}

{'Conversation Context: ' + context.get('conversation_context', '') if context and context.get('conversation_context') else ''}

Provide market analysis including:
1. Price trends and momentum
2. Volume analysis
3. Sector implications
4. Key levels to watch

Analysis:"""

        response = self.llm.generate(prompt, system_prompt=system_prompt, history=(context or {}).get('conversation_history'))

        return {
            "agent": "MarketAgent",
            "response": response,
            "market_data": {
                "tickers": list(self._tickers_seen),
            },
        }
