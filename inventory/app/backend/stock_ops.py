"""處理一次入庫/出庫提交:寫入異動紀錄/明細,更新庫存數量。"""
from collections import Counter

from sqlalchemy import func
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


def get_item_history(db: Session, item_id: int):
    """依transaction分組,算出每次入/出庫對這個item的數量變化。一次異動裡同個item
    對應多筆StockTransactionItem(每筆代表一個單位),所以用count()合計成一個數字。
    """
    rows = (
        db.query(
            StockTransaction.id,
            StockTransaction.type,
            StockTransaction.operator_id,
            StockTransaction.created_at,
            func.count(StockTransactionItem.id).label("count"),
        )
        .join(StockTransactionItem, StockTransactionItem.transaction_id == StockTransaction.id)
        .filter(StockTransactionItem.final_item_id == item_id)
        .group_by(StockTransaction.id)
        .order_by(StockTransaction.created_at.desc())
        .all()
    )
    return [
        {
            "transaction_id": r.id,
            "type": r.type.value,
            "quantity_change": r.count if r.type == TransactionType.IN else -r.count,
            "operator_id": r.operator_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]


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
