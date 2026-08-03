"""add portfolios simulation_runs sector_cache

Revision ID: c5b8c9ed52d9
Revises: 6e7f8a9b0c1d
Create Date: 2026-08-03 12:43:16.185187

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5b8c9ed52d9"
down_revision: Union[str, Sequence[str], None] = "6e7f8a9b0c1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "portfolios",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("allocation", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_portfolios_user_id", "portfolios", ["user_id"])
    op.create_index("ix_portfolios_user_created", "portfolios", ["user_id", "created_at"])

    op.create_table(
        "simulation_runs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "portfolio_id",
            UUID(as_uuid=False),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scenario", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("market_snapshot_time", sa.DateTime, nullable=True),
        sa.Column("sector_data_version", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_simulation_runs_portfolio_id", "simulation_runs", ["portfolio_id"])
    op.create_index(
        "ix_simulation_runs_portfolio_created", "simulation_runs", ["portfolio_id", "created_at"]
    )

    op.create_table(
        "sector_cache",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sector", sa.String(50), nullable=False),
        sa.Column("return_pct", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("volatility", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("computed_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_sector_cache_sector", "sector_cache", ["sector"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("sector_cache")
    op.drop_table("simulation_runs")
    op.drop_table("portfolios")
