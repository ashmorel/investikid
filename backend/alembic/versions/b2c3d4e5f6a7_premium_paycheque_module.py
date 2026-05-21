"""mark 'Your First Paycheque' module premium (4b breadth)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-19 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE modules SET is_premium = true "
        "WHERE topic = 'taxes' AND title = 'Your First Paycheque'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE modules SET is_premium = false "
        "WHERE topic = 'taxes' AND title = 'Your First Paycheque'"
    )
