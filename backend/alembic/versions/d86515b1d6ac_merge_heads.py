"""merge heads

Revision ID: d86515b1d6ac
Revises: 8e16136cae7d, f6a7b8c9d0e1
Create Date: 2026-03-06 01:56:05.394738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd86515b1d6ac'
down_revision: Union[str, None] = ('8e16136cae7d', 'f6a7b8c9d0e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
