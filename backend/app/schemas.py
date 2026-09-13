"""表單/JSON request body 驗證用的 Pydantic models。回應直接在各路由組成 dict/
render_template 用,不用 response_model,理由跟 vision-service 的 schemas.py 一致。
"""
from pydantic import BaseModel


class ItemCreate(BaseModel):
    name: str
    category: str | None = None
    min_stock: int = 0
