"""rename bill to trinary_bill

Revision ID: ae7a3c9ac3df
Revises: f01044691b10
Create Date: 2025-11-08 12:26:34.811040

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ae7a3c9ac3df'
down_revision: Union[str, None] = 'f01044691b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('telegram_users', 'bill', new_column_name='trinary_bill')

def downgrade():
    op.alter_column('telegram_users', 'trinary_bill', new_column_name='bill')
