"""表單/JSON request body 驗證用的 Pydantic models。回應直接在各路由組成 dict/
render_template 用,不用 response_model,理由跟 vision-service 的 schemas.py 一致。
"""
from pydantic import BaseModel

from .models import AnnotationStatus, Source


class ItemCreate(BaseModel):
    name: str
    category: str | None = None
    min_stock: int = 0


class ItemUpdate(BaseModel):
    min_stock: int


class StockInItem(BaseModel):
    source: Source
    predicted_class: str | None = None
    predicted_bbox: tuple[float, float, float, float] | None = None
    final_item_id: int | None = None
    final_bbox: tuple[float, float, float, float] | None = None
    annotation_status: AnnotationStatus
    prediction_id: int | None = None
    final_instance_id: int | None = None


class StockInRequest(BaseModel):
    items: list[StockInItem]
