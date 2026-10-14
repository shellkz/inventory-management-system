import requests
from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import select

from ... import vision_client
from ...db import get_db
from ...models import Inventory, Item
from ...stock_ops import get_item_history

bp = Blueprint(
    "items",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/items/static",
)


@bp.route("/items")
def items_page():
    db = get_db()
    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    query = select(Item, Inventory.quantity).outerjoin(
        Inventory, Item.id == Inventory.item_id
    )
    if not include_deleted:
        query = query.where(Item.is_deleted.is_(False))
    rows = db.execute(query).all()

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
                "is_deleted": item.is_deleted,
            }
        )
    return render_template("items/list.html", items=items_view, include_deleted=include_deleted)


@bp.route("/items/add")
def add_item_page():
    return render_template("items/add.html")


@bp.route("/items/edit/<int:item_id>")
def item_edit_page(item_id):
    db = get_db()
    item = db.get(Item, item_id)

    try:
        instances = vision_client.get_instances(item.recognition_entity_id)
    except requests.RequestException as e:
        return jsonify(
            {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
        ), 502
    return render_template("items/edit.html", item=item, instances=instances)


@bp.route("/items/history/<int:item_id>")
def item_history_page(item_id):
    db = get_db()
    item = db.get(Item, item_id)
    history = get_item_history(db, item_id)
    return render_template("items/history.html", item=item, history=history)
