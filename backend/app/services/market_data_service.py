from decimal import Decimal
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.entity import EntityRepository
from app.schemas.market_price import MarketPriceCreate


class MarketDataService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._entity_repo = EntityRepository(session)

    async def fetch_and_store(
        self,
        entity_id: int,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[MarketPriceCreate]:
        entity = await self._entity_repo.get_by_id(entity_id)
        if entity is None:
            raise ValueError(f"Entity with id={entity_id} not found")

        if not entity.ticker_symbols:
            raise ValueError(f"Entity '{entity.name}' has no ticker symbols")

        ticker = entity.ticker_symbols.split(",")[0].strip()

        records = self._fetch_yfinance_data(ticker, period, interval, entity_id)
        return records

    def _fetch_yfinance_data(
        self,
        ticker: str,
        period: str,
        interval: str,
        entity_id: int,
    ) -> list[MarketPriceCreate]:
        try:
            import yfinance as yf
        except ImportError:
            raise ImportError("yfinance is not installed")

        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)

        if df.empty:
            raise ValueError(f"No price data returned for ticker '{ticker}'")

        records: list[MarketPriceCreate] = []
        for index, row in df.iterrows():
            pd_timestamp = index
            if hasattr(pd_timestamp, "to_pydatetime"):
                price_date = pd_timestamp.to_pydatetime()
            else:
                price_date = pd_timestamp

            price_date = price_date.replace(tzinfo=None)

            records.append(
                MarketPriceCreate(
                    entity_id=entity_id,
                    open_price=Decimal(str(round(float(row["Open"]), 2))),
                    high_price=Decimal(str(round(float(row["High"]), 2))),
                    low_price=Decimal(str(round(float(row["Low"]), 2))),
                    close_price=Decimal(str(round(float(row["Close"]), 2))),
                    volume=int(row["Volume"]),
                    price_date=price_date,
                    source="yfinance",
                )
            )

        return records


def get_market_data_service(
    session: AsyncSession,
) -> MarketDataService:
    return MarketDataService(session)
