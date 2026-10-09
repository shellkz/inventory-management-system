"""處理一次入庫/出庫提交:寫入異動紀錄/明細,更新庫存數量。"""
from collections import Counter

from sqlalchemy.orm import Session

from .models import Inventory, StockTransaction, StockTransactionItem, TransactionType
from .schemas import StockInRequest


class InsufficientStockError(Exception):
    """出庫會讓某些item的庫存變負數,整筆拒絕,不寫入任何東西。"""

    def __init__(self, shortages):
        self.shortages = shortages  # [{"item_id", "available", "requested"}, ...]


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


def process_stock_out(db: Session, payload: StockInRequest) -> StockTransaction:
    quantity_deltas = Counter()
    for item in payload.items:
        if item.final_item_id is not None:
            quantity_deltas[item.final_item_id] += 1

    # 驗證階段:全部算完才檢查,不夠扣的話整筆拒絕,不寫入任何東西。
    shortages = []
    for item_id, requested in quantity_deltas.items():
        inventory = db.get(Inventory, item_id)
        available = inventory.quantity if inventory else 0
        if available < requested:
            shortages.append({"item_id": item_id, "available": available, "requested": requested})

    if shortages:
        raise InsufficientStockError(shortages)

    # 驗證通過才真正寫入。
    transaction = StockTransaction(type=TransactionType.OUT)
    db.add(transaction)
    db.flush()  # 取得 transaction.id

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

    for item_id, requested in quantity_deltas.items():
        inventory = db.get(Inventory, item_id)
        inventory.quantity -= requested

    db.commit()
    db.refresh(transaction)
    return transaction
