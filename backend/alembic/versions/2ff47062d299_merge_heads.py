"""merge heads

Revision ID: 2ff47062d299
Revises: s40_001_external_signals, s45_001_tenants
Create Date: 2026-04-12 19:00:52.172936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ff47062d299'
down_revision: Union[str, None] = ('s40_001_external_signals', 's45_001_tenants')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
