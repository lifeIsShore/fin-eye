"""merge_heads

Revision ID: 6fe5eb0b421c
Revises: 42862909e9cc, s27_001_signal_grade_history
Create Date: 2026-03-23 00:00:14.856829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6fe5eb0b421c'
down_revision: Union[str, None] = ('42862909e9cc', 's27_001_signal_grade_history')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
