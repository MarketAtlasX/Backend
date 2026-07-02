"""Country model — first-class entity matching frontend's Country interface."""

from sqlalchemy import Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Country(Base):
    """Rich country data matching the frontend's Country interface."""

    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    stock_exchange: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    currency_symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    market_cap: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trading_hours: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tickers: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    commodities: Mapped[str | None] = mapped_column(Text, nullable=True)
    port_names: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
