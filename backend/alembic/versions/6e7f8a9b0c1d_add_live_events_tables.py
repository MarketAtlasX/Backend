"""add live events tables

Revision ID: 6e7f8a9b0c1d
Revises: 4159c18327f5
Create Date: 2026-07-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


revision: str = "6e7f8a9b0c1d"
down_revision: Union[str, Sequence[str], None] = "4159c18327f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "live_events",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("sub_type", sa.String(100), nullable=True),
        sa.Column("severity", sa.Float, nullable=False, server_default="5.0"),
        sa.Column("impact_score", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="breaking"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_urls", JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
        sa.Column("lat", sa.Float, nullable=True),
        sa.Column("lng", sa.Float, nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("event_date", sa.DateTime, nullable=True),
        sa.Column("detected_at", sa.DateTime, nullable=True),
        sa.Column("first_seen_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("metadata", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint("severity >= 0.0 AND severity <= 10.0", name="ck_live_events_severity"),
        sa.CheckConstraint(
            "impact_score IS NULL OR (impact_score >= 0.0 AND impact_score <= 1.0)",
            name="ck_live_events_impact",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_live_events_confidence",
        ),
    )
    op.create_index("ix_live_events_status_first_seen", "live_events", ["status", "first_seen_at"])
    op.create_index("ix_live_events_event_type", "live_events", ["event_type"])
    op.create_index("ix_live_events_severity", "live_events", ["severity"])
    op.create_index("ix_live_events_country_code", "live_events", ["country_code"])
    op.create_index("ix_live_events_source", "live_events", ["source"])
    op.create_index("ix_live_events_first_seen_at", "live_events", ["first_seen_at"])

    op.create_table(
        "event_impacts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("event_id", UUID(as_uuid=False), sa.ForeignKey("live_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", sa.Integer, sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_name", sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("impact_direction", sa.String(20), nullable=False, server_default="neutral"),
        sa.Column("impact_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("impact_type", sa.String(50), nullable=False, server_default="price"),
        sa.Column("analysis_summary", sa.Text, nullable=True),
        sa.Column("reasoning_factors", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("generated_by", sa.String(50), nullable=False, server_default="ai_service"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("impact_score >= 0.0 AND impact_score <= 1.0", name="ck_event_impacts_score"),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_event_impacts_confidence"),
    )
    op.create_index("ix_event_impacts_event_id", "event_impacts", ["event_id"])
    op.create_index("ix_event_impacts_entity_id", "event_impacts", ["entity_id"])

    op.create_table(
        "event_affected_assets",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("impact_id", UUID(as_uuid=False), sa.ForeignKey("event_impacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("estimated_move", sa.Float, nullable=True),
        sa.Column("volatility_impact", sa.Float, nullable=True),
        sa.Column("time_horizon", sa.String(20), nullable=False, server_default="short_term"),
        sa.Column("current_price", sa.Float, nullable=True),
        sa.Column("price_direction", sa.String(10), nullable=False, server_default="mixed"),
    )
    op.create_index("ix_event_affected_assets_ticker", "event_affected_assets", ["ticker"])
    op.create_index("ix_event_affected_assets_asset_type", "event_affected_assets", ["asset_type"])

    op.create_table(
        "event_news_articles",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("event_id", UUID(as_uuid=False), sa.ForeignKey("live_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("published_at", sa.DateTime, nullable=True),
        sa.Column("content_snippet", sa.String(1000), nullable=True),
        sa.Column("sentiment", sa.Float, nullable=True),
        sa.Column("relevance_score", sa.Float, nullable=True),
        sa.Column("fetched_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("url", name="uq_event_news_article_url"),
    )
    op.create_index("ix_event_news_articles_event_id", "event_news_articles", ["event_id"])
    op.create_index("ix_event_news_articles_source", "event_news_articles", ["source"])
    op.create_index("ix_event_news_articles_relevance", "event_news_articles", ["event_id", "relevance_score"])

    op.create_table(
        "event_alerts",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_id", UUID(as_uuid=False), sa.ForeignKey("live_events.id", ondelete="CASCADE"), nullable=True),
        sa.Column("rule_name", sa.String(100), nullable=True),
        sa.Column("alert_type", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_delivered", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("delivered_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_event_alerts_user_read", "event_alerts", ["user_id", "is_read"])

    op.create_table(
        "user_event_filters",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("filter_config", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_event_filters_user", "user_event_filters", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_event_filters")
    op.drop_table("event_alerts")
    op.drop_table("event_news_articles")
    op.drop_table("event_affected_assets")
    op.drop_table("event_impacts")
    op.drop_table("live_events")
