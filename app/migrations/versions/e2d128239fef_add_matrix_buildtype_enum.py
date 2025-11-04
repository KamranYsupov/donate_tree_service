"""add matrix.buildtype enum 

Revision ID: e2d128239fef
Revises: 7a6f609b63f0
Create Date: 2025-11-04 11:45:36.360745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2d128239fef'
down_revision: Union[str, None] = '7a6f609b63f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Создание типа ENUM
    op.execute("CREATE TYPE matrixbuildtype AS ENUM ('BINARY', 'TRINARY')")

def downgrade():
    # Удаление типа ENUM
    op.execute("DROP TYPE matrixbuildtype")
