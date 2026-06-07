"""initial_schema

Revision ID: a3468edd5ab1
Revises: 
Create Date: 2026-06-02

Single authoritative baseline migration. Replaces two prior broken migrations:
  - b3388cc8ccf1 (entities had a spurious event_id FK column)
  - be822dc1fe8d (tried to CREATE TABLE entities again — duplicate table on fresh installs)

This migration creates the complete schema from scratch, including all
CheckConstraints for categorical fields.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3468edd5ab1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the complete MarketAtlas schema."""

    # ------------------------------------------------------------------
    # entities
    # ------------------------------------------------------------------
    op.create_table(
        'entities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('country_code', sa.String(length=2), nullable=True),
        sa.Column('ticker_symbols', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "entity_type IN ('country', 'company', 'person', 'region', 'index', 'commodity')",
            name='ck_entities_entity_type',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_entities_country_code', 'entities', ['country_code'], unique=False)
    op.create_index('ix_entities_entity_type', 'entities', ['entity_type'], unique=False)
    op.create_index(op.f('ix_entities_id'), 'entities', ['id'], unique=False)
    op.create_index('ix_entities_name', 'entities', ['name'], unique=False)

    # ------------------------------------------------------------------
    # events
    # ------------------------------------------------------------------
    op.create_table(
        'events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('event_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('sanction', 'election', 'trade_policy', 'military_conflict', "
            "'diplomatic', 'economic_data', 'regulatory', 'natural_disaster', 'other')",
            name='ck_events_event_type',
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name='ck_events_severity',
        ),
        sa.CheckConstraint(
            "status IN ('reported', 'confirmed', 'resolved')",
            name='ck_events_status',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_events_created_at', 'events', ['created_at'], unique=False)
    op.create_index('ix_events_event_date', 'events', ['event_date'], unique=False)
    op.create_index('ix_events_event_type', 'events', ['event_type'], unique=False)
    op.create_index(op.f('ix_events_id'), 'events', ['id'], unique=False)
    op.create_index('ix_events_severity', 'events', ['severity'], unique=False)
    op.create_index('ix_events_status', 'events', ['status'], unique=False)

    # ------------------------------------------------------------------
    # event_entities (junction table)
    # ------------------------------------------------------------------
    op.create_table(
        'event_entities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_event_entities_entity_id', 'event_entities', ['entity_id'], unique=False)
    op.create_index('ix_event_entities_event_id', 'event_entities', ['event_id'], unique=False)
    op.create_index(op.f('ix_event_entities_id'), 'event_entities', ['id'], unique=False)

    # ------------------------------------------------------------------
    # market_prices
    # ------------------------------------------------------------------
    op.create_table(
        'market_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('open_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('high_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('low_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('close_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('volume', sa.Integer(), nullable=False),
        sa.Column('price_date', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_id', 'price_date', name='uq_market_price_entity_date'),
    )
    op.create_index('ix_market_prices_created_at', 'market_prices', ['created_at'], unique=False)
    op.create_index('ix_market_prices_entity_id', 'market_prices', ['entity_id'], unique=False)
    op.create_index(op.f('ix_market_prices_id'), 'market_prices', ['id'], unique=False)
    op.create_index('ix_market_prices_price_date', 'market_prices', ['price_date'], unique=False)

    # ------------------------------------------------------------------
    # signals
    # ------------------------------------------------------------------
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('signal_type', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('target_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('stop_loss', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('exit_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('pnl_percent', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "signal_type IN ('buy', 'sell', 'hold', 'short')",
            name='ck_signals_signal_type',
        ),
        sa.CheckConstraint(
            "status IN ('active', 'closed', 'expired')",
            name='ck_signals_status',
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name='ck_signals_confidence_range',
        ),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_signals_confidence', 'signals', ['confidence'], unique=False)
    op.create_index('ix_signals_created_at', 'signals', ['created_at'], unique=False)
    op.create_index('ix_signals_entity_id', 'signals', ['entity_id'], unique=False)
    op.create_index('ix_signals_event_id', 'signals', ['event_id'], unique=False)
    op.create_index(op.f('ix_signals_id'), 'signals', ['id'], unique=False)
    op.create_index('ix_signals_signal_type', 'signals', ['signal_type'], unique=False)
    op.create_index('ix_signals_status', 'signals', ['status'], unique=False)


def downgrade() -> None:
    """Drop the complete MarketAtlas schema."""
    op.drop_index('ix_signals_status', table_name='signals')
    op.drop_index('ix_signals_signal_type', table_name='signals')
    op.drop_index(op.f('ix_signals_id'), table_name='signals')
    op.drop_index('ix_signals_event_id', table_name='signals')
    op.drop_index('ix_signals_entity_id', table_name='signals')
    op.drop_index('ix_signals_created_at', table_name='signals')
    op.drop_index('ix_signals_confidence', table_name='signals')
    op.drop_table('signals')

    op.drop_index('ix_market_prices_price_date', table_name='market_prices')
    op.drop_index(op.f('ix_market_prices_id'), table_name='market_prices')
    op.drop_index('ix_market_prices_entity_id', table_name='market_prices')
    op.drop_index('ix_market_prices_created_at', table_name='market_prices')
    op.drop_table('market_prices')

    op.drop_index(op.f('ix_event_entities_id'), table_name='event_entities')
    op.drop_index('ix_event_entities_event_id', table_name='event_entities')
    op.drop_index('ix_event_entities_entity_id', table_name='event_entities')
    op.drop_table('event_entities')

    op.drop_index('ix_events_status', table_name='events')
    op.drop_index('ix_events_severity', table_name='events')
    op.drop_index(op.f('ix_events_id'), table_name='events')
    op.drop_index('ix_events_event_type', table_name='events')
    op.drop_index('ix_events_event_date', table_name='events')
    op.drop_index('ix_events_created_at', table_name='events')
    op.drop_table('events')

    op.drop_index('ix_entities_name', table_name='entities')
    op.drop_index(op.f('ix_entities_id'), table_name='entities')
    op.drop_index('ix_entities_entity_type', table_name='entities')
    op.drop_index('ix_entities_country_code', table_name='entities')
    op.drop_table('entities')
