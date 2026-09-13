"""消費端(庫存 demo app)自己的表,對應 docs/schema.md「消費端範例」章節。
範圍只涵蓋耗材出入庫,不含設備借還(沒有借用狀態/借用人欄位)。

跟 vision-service 是兩個完全獨立的資料庫,`items.recognition_entity_id` 是單向的
跨系統參照(存的是 vision-service 那邊的 id 值),不是這裡的 FK,兩邊沒有實際的
資料庫外鍵約束,一致性由應用層自己維護。
"""
import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TransactionType(str, enum.Enum):
    IN = "in"
    OUT = "out"


class Source(str, enum.Enum):
    AUTO_DETECTED = "auto_detected"
    MANUAL_ADD = "manual_add"
    MANUAL_CORRECT = "manual_correct"


class AnnotationStatus(str, enum.Enum):
    PENDING_REVIEW = "pending_review"
    NEEDS_BBOX = "needs_bbox"
    CONFIRMED = "confirmed"


def _enum_values(py_enum):
    return Enum(py_enum, values_callable=lambda e: [member.value for member in e])


class Item(Base):
    """品項主檔。"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    min_stock = Column(Integer, nullable=False, default=0)
    # 對應 vision-service 的 recognition_entities.id,跨系統參照,不是真的 FK
    recognition_entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Inventory(Base):
    """庫存現況,跟 items 現為 1:1,獨立成表避免編輯品項時連帶覆蓋 quantity。"""

    __tablename__ = "inventory"

    item_id = Column(Integer, ForeignKey("items.id"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class StockTransaction(Base):
    """出入庫事件,一次掃描/一個 session 一筆,是 StockTransactionItem 的 header。"""

    __tablename__ = "stock_transactions"

    id = Column(Integer, primary_key=True)
    type = Column(_enum_values(TransactionType), nullable=False)
    operator_id = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StockTransactionItem(Base):
    """出入庫明細,兼訓練資料池。一次出入庫對應多筆,每個被辨識/新增的物件各一筆。"""

    __tablename__ = "stock_transaction_items"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey("stock_transactions.id"), nullable=False)
    final_item_id = Column(Integer, ForeignKey("items.id"), nullable=True)
    final_bbox = Column(JSON, nullable=True)
    predicted_class = Column(String, nullable=True)
    predicted_class_score = Column(Float, nullable=True)
    predicted_objectness_conf = Column(Float, nullable=True)
    predicted_bbox = Column(JSON, nullable=True)
    source = Column(_enum_values(Source), nullable=False)
    annotation_status = Column(
        _enum_values(AnnotationStatus), nullable=False, default=AnnotationStatus.PENDING_REVIEW
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
