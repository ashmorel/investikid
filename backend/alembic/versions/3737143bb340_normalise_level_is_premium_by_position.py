"""normalise level is_premium by position

Revision ID: 3737143bb340
Revises: b6c7d8e9f0a1
Create Date: 2026-06-09 19:52:17.643062

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '3737143bb340'
down_revision: Union[str, None] = 'b6c7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE levels SET is_premium = (order_index >= 2)")


def downgrade() -> None:
    # Data normalisation has no meaningful inverse.
    pass
