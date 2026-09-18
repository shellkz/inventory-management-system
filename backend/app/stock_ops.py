"""處理一次入庫提交:寫入異動紀錄/明細,更新庫存數量。"""
from collections import Counter

from sqlalchemy.orm import Session

from .models import Inventory, StockTransaction, StockTransactionItem, TransactionType
from .schemas import StockInRequest


def process_stock_in(db: Session, payload: StockInRequest) -> StockTransaction:
    transaction = StockTransaction(type=TransactionType.IN)
    db.add(transaction)
    db.flush()  # 取得 transaction.id

    quantity_deltas = Counter()

    for item in payload.items:
        db.add(
            StockTransactionItem(
                transaction_id=transaction.id,
                source=item.source,
                predicted_class=item.predicted_class,
                final_item_id=item.final_item_id,
                prediction_id=item.prediction_id,
            )
        )
        if item.final_item_id is not None:
            quantity_deltas[item.final_item_id] += 1

    for item_id, delta in quantity_deltas.items():
        inventory = db.get(Inventory, item_id)
        inventory.quantity += delta

    db.commit()
    db.refresh(transaction)
    return transaction
