import requests
from flask import Blueprint, jsonify, make_response, render_template, request, url_for
from pydantic import ValidationError
from sqlalchemy import select

from . import config
from .db import get_db
from .models import Inventory, Item
from .schemas import ItemCreate, StockInRequest
from .stock_ops import process_stock_in

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


@main.route("/items/add", methods=["GET", "POST"])
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

    headers = {"Authorization": f"Bearer {config.VISION_API_KEY}"}

    try:
        entity_resp = requests.post(
            f"{config.VISION_SERVICE_URL}/v1/entities",
            json={"name": item_data.name},
            headers=headers,
            timeout=10,
        )
        entity_resp.raise_for_status()
        entity_id = entity_resp.json()["id"]

        files = [
            ("images", (image.filename, image.stream, image.mimetype))
            for image in request.files.getlist("images")
        ]
        instance_resp = requests.post(
            f"{config.VISION_SERVICE_URL}/v1/entities/{entity_id}/instances",
            files=files,
            headers=headers,
            timeout=30,
        )
        instance_resp.raise_for_status()
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
    response.headers["HX-Redirect"] = url_for("main.items")
    return response


@main.route("/recognize", methods=["GET", "POST"])
def recognize():
    if request.method == "GET":
        return render_template("recognize.html")

    image = request.files["image"]
    try:
        resp = requests.post(
            f"{config.VISION_SERVICE_URL}/v1/recognize",
            files={"file": (image.filename, image.stream, image.mimetype)},
            headers={"Authorization": f"Bearer {config.VISION_API_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}), 502

    data = resp.json()

    # 把 vision-service 自己的 entity_id 翻譯成 backend 的 item_id,
    # 不讓 vision-service 的 ID 系統外流到前端。查不到對應 item 就是 null
    # (孤兒 entity,或 objectness 高但沒有夠接近的比對結果,兩種情況前端都一視同仁處理)。
    db = get_db()
    result = []
    for r in data["result"]:
        item = db.query(Item).filter(Item.recognition_entity_id == r["entity_id"]).first()
        result.append(
            {
                "bbox": r["bbox"],
                "score": r["score"],
                "meets_threshold": r["meets_threshold"],
                "item_id": item.id if item else None,
            }
        )

    return jsonify({"score_threshold": data["score_threshold"], "result": result})


@main.route("/stock-in", methods=["GET", "POST"])
def stock_in():
    if request.method == "GET":
        return render_template("stock_in.html")

    body = request.get_json(silent=True)
    if body is None:
        return jsonify({"error": "invalid_json", "message": "request body 不是合法的 JSON"}), 400

    try:
        payload = StockInRequest.model_validate(body)
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.errors()}), 422

    db = get_db()
    transaction = process_stock_in(db, payload)
    return jsonify({"transaction_id": transaction.id}), 200


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

    if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json":
        return jsonify(items_view)
    return render_template("items.html", items=items_view)
