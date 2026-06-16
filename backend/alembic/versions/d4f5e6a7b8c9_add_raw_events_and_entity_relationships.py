"""add raw_events and entity_relationships tables

Revision ID: d4f5e6a7b8c9
Revises: af9e2c4b1a0d
Create Date: 2026-06-15

Adds the event-store persistence layer:
  - raw_events            — ingested geopolitical events from external sources
  - entity_relationships  — directed weighted relationships between entities
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4f5e6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "af9e2c4b1a0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- raw_events ---
    op.create_table(
        "raw_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_url"),
    )
    op.create_index(op.f("ix_raw_events_fetched_at"), "raw_events", ["fetched_at"], unique=False)
    op.create_index(op.f("ix_raw_events_id"), "raw_events", ["id"], unique=False)
    op.create_index(op.f("ix_raw_events_processed"), "raw_events", ["processed"], unique=False)
    op.create_index(op.f("ix_raw_events_source"), "raw_events", ["source"], unique=False)

    # --- entity_relationships ---
    op.create_table(
        "entity_relationships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_entity_id", sa.Integer(), nullable=False),
        sa.Column("target_entity_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_entity_relationships_id"), "entity_relationships", ["id"], unique=False)
    op.create_index(op.f("ix_entity_relationships_relation_type"), "entity_relationships", ["relation_type"], unique=False)
    op.create_index(op.f("ix_entity_relationships_source_entity_id"), "entity_relationships", ["source_entity_id"], unique=False)
    op.create_index(op.f("ix_entity_relationships_target_entity_id"), "entity_relationships", ["target_entity_id"], unique=False)


def downgrade() -> None:
    op.drop_table("entity_relationships")
    op.drop_table("raw_events")
