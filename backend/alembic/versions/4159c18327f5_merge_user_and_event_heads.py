"""merge user and event heads

Revision ID: 4159c18327f5
Revises: 894cc5e6b1c1, d4f5e6a7b8c9
Create Date: 2026-06-16 09:48:11.367770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4159c18327f5'
down_revision: Union[str, Sequence[str], None] = ('894cc5e6b1c1', 'd4f5e6a7b8c9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
