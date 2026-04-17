"""Merge multiple heads for sprint 49

Revision ID: 06d9d06f1ef3
Revises: 2ff47062d299, s47_001_bot_tables, s49_001_streak_fields
Create Date: 2026-04-17 11:01:01.713350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '06d9d06f1ef3'
down_revision: Union[str, None] = ('2ff47062d299', 's47_001_bot_tables', 's49_001_streak_fields')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
