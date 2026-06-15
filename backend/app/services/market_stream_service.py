"""Real-time market data streaming via Yahoo Finance WebSocket.

Streams live prices for our tracked tickers and broadcasts them to
WebSocket clients. No DB storage — the Celery beat continues to persist
daily OHLCV candles for the analysis pipeline.
"""

import logging

import yfinance as yf

from app.services.event_broadcaster import EventBroadcaster

logger = logging.getLogger(__name__)

STREAM_TICKERS = [
    "AAPL", "SPY", "FXI", "EWJ", "INDA", "TSM", "EWY",
    "MSFT", "AMZN", "TSLA", "NVDA", "META", "GOOGL",
    "SSNLF", "TM", "JPM", "GS", "BA", "PFE", "SHEL",
    "2222.SR", "VWAGY", "LVMUY",
]

TICKER_TO_ENTITY = {
    "AAPL": 3, "SPY": 33, "FXI": 34, "EWJ": 36, "INDA": 40,
    "TSM": 41, "EWY": 42, "MSFT": 43, "AMZN": 44, "TSLA": 45,
    "NVDA": 46, "META": 47, "GOOGL": 48, "SSNLF": 50, "TM": 51,
    "JPM": 52, "GS": 53, "BA": 54, "PFE": 55, "SHEL": 56,
    "2222.SR": 57, "VWAGY": 59, "LVMUY": 60,
}


class MarketStreamService:
    """Maintains a persistent Yahoo Finance WebSocket and broadcasts ticks."""

    def __init__(self, broadcaster: EventBroadcaster) -> None:
        self._broadcaster = broadcaster
        self._ws: yf.AsyncWebSocket | None = None

    async def run(self) -> None:
        logger.info("Market stream starting for %d tickers", len(STREAM_TICKERS))
        self._ws = yf.AsyncWebSocket(verbose=False)
        await self._ws.subscribe(STREAM_TICKERS)
        logger.info("Market stream subscribed, listening for ticks...")
        await self._ws.listen(self._handle_tick)

    async def _handle_tick(self, tick: dict) -> None:
        try:
            symbol = tick.get("id", "")
            price = tick.get("price")
            if not symbol or price is None:
                return
            entity_id = TICKER_TO_ENTITY.get(symbol)
            if entity_id is None:
                return

            await self._broadcaster.broadcast("market_tick", {
                "entity_id": entity_id,
                "ticker": symbol,
                "price": round(float(price), 2),
                "time": tick.get("time", ""),
                "volume": tick.get("volume", 0),
            })
        except Exception:
            logger.exception("Error handling market tick for %s", tick.get("id"))
