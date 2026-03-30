"""merge v4_003 and v7_001

Revision ID: 5e66ab23ac8b
Revises: v4_003_trial_pause, v7_001_showcase_bundles
Create Date: 2026-03-30 13:34:30.464711

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e66ab23ac8b'
down_revision: Union[str, None] = ('v4_003_trial_pause', 'v7_001_showcase_bundles')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
