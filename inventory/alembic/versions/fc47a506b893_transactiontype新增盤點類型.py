"""TransactionType新增盤點類型

Revision ID: fc47a506b893
Revises: 67617b993e51
Create Date: 2026-10-11 13:26:16.643788

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc47a506b893'
down_revision: Union[str, Sequence[str], None] = '67617b993e51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite的ALTER TABLE不支援改欄位型態,要用batch模式(底層是建新表複製資料)。
    with op.batch_alter_table('stock_transactions') as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.VARCHAR(length=3),
            type_=sa.Enum('in', 'out', 'stocktake', name='transactiontype'),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('stock_transactions') as batch_op:
        batch_op.alter_column(
            'type',
            existing_type=sa.Enum('in', 'out', 'stocktake', name='transactiontype'),
            type_=sa.VARCHAR(length=3),
            existing_nullable=False,
        )
