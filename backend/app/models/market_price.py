from datetime import datetime
from decimal import Decimal

from sqlalchemy import Numeric, DateTime, ForeignKey, String, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MarketPrice(Base):
    """
    Stores OHLCV (Open, High, Low, Close, Volume) market data.
    
    This table captures historical price data fetched from yfinance,
    used to correlate market movements with geopolitical events.
    """

    __tablename__ = "market_prices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Foreign key to entity (company/ticker)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False)
    entity = relationship("Entity", back_populates="market_prices")
    
    # OHLCV data
    open_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    volume: Mapped[int] = mapped_column(nullable=False)
    
    # Price date (market trading date)
    price_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Data source tracking
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="yfinance")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("entity_id", "price_date", name="uq_market_price_entity_date"),
        Index("ix_market_prices_entity_id", "entity_id"),
        Index("ix_market_prices_price_date", "price_date"),
        Index("ix_market_prices_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<MarketPrice(id={self.id}, entity_id={self.entity_id}, price_date={self.price_date}, close={self.close_price})>"
