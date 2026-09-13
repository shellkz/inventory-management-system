import requests
from flask import Blueprint, render_template
from sqlalchemy import select

from . import config
from .db import get_db
from .models import Inventory, Item

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/catalog")
def catalog():
    """只回傳片段 HTML,給 htmx 掛進頁面用,不是獨立頁面。"""
    resp = requests.get(
        f"{config.VISION_SERVICE_URL}/v1/entities",
        headers={"Authorization": f"Bearer {config.VISION_API_KEY}"},
        timeout=10,
    )
    resp.raise_for_status()
    entities = resp.json()["result"]
    return render_template("_catalog.html", entities=entities)


@main.route("/items")
def items():
    db = get_db()
    rows = db.execute(
        select(Item, Inventory.quantity).outerjoin(Inventory, Item.id == Inventory.item_id)
    ).all()

    items_view = []
    for item, quantity in rows:
        quantity = quantity if quantity is not None else 0
        items_view.append(
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "quantity": quantity,
                "min_stock": item.min_stock,
                "is_low": quantity < item.min_stock,
            }
        )

    return render_template("items.html", items=items_view)
