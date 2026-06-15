"""Port model — major port locations per country."""

from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Port(Base):
    """A major port location for trade visualization."""

    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[str] = mapped_column(String(10), nullable=False)
