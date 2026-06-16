from datetime import datetime
from sqlalchemy import String, Text, Float, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    extra_meta: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EntityRelationship {self.source_entity_id} -[{self.relation_type}]-> {self.target_entity_id}>"
