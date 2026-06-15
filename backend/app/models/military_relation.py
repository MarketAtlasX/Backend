"""Military relation model — alliances, rivalries, conflicts between countries."""

from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MilitaryRelation(Base):
    """A military or geopolitical relationship between two countries."""

    __tablename__ = "military_relations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    country_a: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    country_b: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    from_lat: Mapped[float] = mapped_column(Float, nullable=False)
    from_lng: Mapped[float] = mapped_column(Float, nullable=False)
    to_lat: Mapped[float] = mapped_column(Float, nullable=False)
    to_lng: Mapped[float] = mapped_column(Float, nullable=False)
