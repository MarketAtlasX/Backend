"""Trade route model — bilateral trade flows between countries."""

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TradeRoute(Base):
    """A bilateral trade relationship between two countries."""

    __tablename__ = "trade_routes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    from_country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    to_country: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    value_label: Mapped[str] = mapped_column(String(50), nullable=False)
    from_lat: Mapped[float] = mapped_column(Float, nullable=False)
    from_lng: Mapped[float] = mapped_column(Float, nullable=False)
    to_lat: Mapped[float] = mapped_column(Float, nullable=False)
    to_lng: Mapped[float] = mapped_column(Float, nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False)
