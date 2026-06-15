"""add country, trade_route, military_relation, port tables

Revision ID: af9e2c4b1a0d
Revises: bce7de430380
Create Date: 2026-06-12

Adds the four new models for the frontend-facing globe/globe API:
  - countries       — rich country profiles matching frontend's Country interface
  - trade_routes    — bilateral trade flows between country pairs
  - military_relations — alliances, rivalries, conflicts
  - ports           — major port locations per country
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "af9e2c4b1a0d"
down_revision: Union[str, Sequence[str], None] = "bce7de430380"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- countries ---
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("stock_exchange", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("currency_symbol", sa.String(length=10), nullable=False),
        sa.Column("market_cap", sa.String(length=50), nullable=True),
        sa.Column("trading_hours", sa.String(length=100), nullable=True),
        sa.Column("tickers", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("commodities", sa.Text(), nullable=True),
        sa.Column("port_names", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_countries_code"), "countries", ["code"], unique=True)
    op.create_index(op.f("ix_countries_id"), "countries", ["id"], unique=False)

    # --- trade_routes ---
    op.create_table(
        "trade_routes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_country", sa.String(length=2), nullable=False),
        sa.Column("to_country", sa.String(length=2), nullable=False),
        sa.Column("value_label", sa.String(length=50), nullable=False),
        sa.Column("from_lat", sa.Float(), nullable=False),
        sa.Column("from_lng", sa.Float(), nullable=False),
        sa.Column("to_lat", sa.Float(), nullable=False),
        sa.Column("to_lng", sa.Float(), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_trade_routes_from_country"), "trade_routes", ["from_country"], unique=False
    )
    op.create_index(
        op.f("ix_trade_routes_id"), "trade_routes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_trade_routes_to_country"), "trade_routes", ["to_country"], unique=False
    )

    # --- military_relations ---
    op.create_table(
        "military_relations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("country_a", sa.String(length=2), nullable=False),
        sa.Column("country_b", sa.String(length=2), nullable=False),
        sa.Column("relation_type", sa.String(length=20), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("from_lat", sa.Float(), nullable=False),
        sa.Column("from_lng", sa.Float(), nullable=False),
        sa.Column("to_lat", sa.Float(), nullable=False),
        sa.Column("to_lng", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_military_relations_country_a"), "military_relations", ["country_a"], unique=False
    )
    op.create_index(
        op.f("ix_military_relations_country_b"), "military_relations", ["country_b"], unique=False
    )
    op.create_index(
        op.f("ix_military_relations_id"), "military_relations", ["id"], unique=False
    )

    # --- ports ---
    op.create_table(
        "ports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("volume", sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ports_country_code"), "ports", ["country_code"], unique=False
    )
    op.create_index(op.f("ix_ports_id"), "ports", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("ports")
    op.drop_table("military_relations")
    op.drop_table("trade_routes")
    op.drop_table("countries")
