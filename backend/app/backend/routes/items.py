import requests
from flask import Blueprint, jsonify, make_response, render_template, request, url_for
from pydantic import ValidationError
from sqlalchemy import select

from .. import vision_client
from ..db import get_db
from ..models import Inventory, Item
from ..schemas import ItemCreate

bp = Blueprint("items", __name__)


@bp.route("/catalog")
def catalog():
    """只回傳片段 HTML,給 htmx 掛進頁面用,不是獨立頁面。"""
    try:
        entities = vision_client.get_entities()
    except requests.RequestException as e:
        return jsonify({"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}), 502
    return render_template("_catalog.html", entities=entities)


@bp.route("/items/add", methods=["GET", "POST"])
def add_item():
    if request.method == "GET":
        return render_template("add_item.html")

    try:
        item_data = ItemCreate(
            name=request.form["name"],
            category=request.form.get("category") or None,
            min_stock=int(request.form.get("min_stock", 0)),
        )
    except (ValidationError, ValueError) as e:
        return render_template("_add_item_error.html", message=str(e))

    try:
        entity = vision_client.create_entity(item_data.name)
        entity_id = entity["id"]

        files = [
            ("images", (image.filename, image.stream, image.mimetype))
            for image in request.files.getlist("images")
        ]
        vision_client.create_instance(entity_id, files)
    except requests.RequestException as e:
        return render_template("_add_item_error.html", message=f"辨識服務錯誤: {e}")

    db = get_db()
    item = Item(
        name=item_data.name,
        category=item_data.category,
        min_stock=item_data.min_stock,
        recognition_entity_id=entity_id,
    )
    db.add(item)
    db.flush()
    db.add(Inventory(item_id=item.id, quantity=0))
    db.commit()

    response = make_response("")
    response.headers["HX-Redirect"] = url_for("items.items")
    return response


@bp.route("/items")
def items():
    db = get_db()
    rows = db.execute(
        select(Item, Inventory.quantity).outerjoin(Inventory, Item.id == Inventory.item_id)
    ).all()

    is_json = request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json"

    # instance 清單只有 JSON(給入庫審核用)才需要,HTML 頁面不用,不用多打 vision-service。
    # 每個entity都要查(即使只有一個instance),前端改類別時才有id可以填final_instance_id;
    # UI要不要顯示選擇畫面,交給前端自己看instances長度決定。
    instances_by_entity_id = {}
    if is_json:
        try:
            for entity in vision_client.get_entities():
                instances = vision_client.get_instances(entity["id"])
                instances_by_entity_id[entity["id"]] = [
                    {"id": i["id"], "name": i["name"]} for i in instances
                ]
        except requests.RequestException as e:
            return jsonify({"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}), 502

    items_view = []
    for item, quantity in rows:
        quantity = quantity if quantity is not None else 0
        entry = {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "quantity": quantity,
            "min_stock": item.min_stock,
            "is_low": quantity < item.min_stock,
        }
        if is_json:
            entry["instances"] = instances_by_entity_id.get(item.recognition_entity_id, [])
        items_view.append(entry)

    if is_json:
        return jsonify(items_view)
    return render_template("items.html", items=items_view)
