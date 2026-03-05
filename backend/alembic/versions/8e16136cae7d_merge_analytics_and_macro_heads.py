"""merge analytics and macro heads

Revision ID: 8e16136cae7d
Revises: c3d4e5f6a7b8, d4e5f6a7b8c9
Create Date: 2026-03-06 02:20:30.695729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e16136cae7d'
down_revision: Union[str, None] = ('c3d4e5f6a7b8', 'd4e5f6a7b8c9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
