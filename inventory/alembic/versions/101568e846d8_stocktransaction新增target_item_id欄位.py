"""StockTransaction新增target_item_id欄位

Revision ID: 101568e846d8
Revises: fc47a506b893
Create Date: 2026-10-11 14:31:02.102917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '101568e846d8'
down_revision: Union[str, Sequence[str], None] = 'fc47a506b893'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite的ALTER TABLE不支援直接加外鍵約束,要用batch模式(底層是建新表複製資料)。
    with op.batch_alter_table('stock_transactions') as batch_op:
        batch_op.add_column(sa.Column('target_item_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_stock_transactions_target_item_id', 'items', ['target_item_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('stock_transactions') as batch_op:
        batch_op.drop_constraint('fk_stock_transactions_target_item_id', type_='foreignkey')
        batch_op.drop_column('target_item_id')
