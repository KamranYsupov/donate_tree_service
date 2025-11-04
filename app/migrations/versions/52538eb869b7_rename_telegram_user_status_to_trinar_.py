"""rename telegram_user.status to trinar_status

Revision ID: 52538eb869b7
Revises: 356322f62cf2
Create Date: 2025-11-04 14:46:14.532994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52538eb869b7'
down_revision: Union[str, None] = '356322f62cf2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('telegram_users', 'status', new_column_name='trinary_status')

def downgrade():
    op.alter_column('telegram_users', 'trinary_status', new_column_name='status')
