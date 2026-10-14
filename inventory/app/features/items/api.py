import requests
from flask import Response, jsonify, request
from pydantic import ValidationError
from sqlalchemy import select

from ... import vision_client
from ...db import get_db
from ...models import Inventory, Item
from ...schemas import ItemCreate, ItemUpdate, SampleBboxPatch
from .views import bp


@bp.route("/api/items")
def items_list():
    db = get_db()
    include_deleted = request.args.get("include_deleted", "false").lower() == "true"

    query = select(Item, Inventory.quantity).outerjoin(
        Inventory, Item.id == Inventory.item_id
    )
    if not include_deleted:
        query = query.where(Item.is_deleted.is_(False))
    rows = db.execute(query).all()

    # instance清單是給入庫審核用的,每個entity都要查(即使只有一個instance),
    # 前端改類別時才有id可以填final_instance_id。
    instances_by_entity_id = {}
    try:
        for entity in vision_client.get_entities():
            instances = vision_client.get_instances(entity["id"])
            instances_by_entity_id[entity["id"]] = [
                {"id": i["id"], "name": i["name"]} for i in instances
            ]
    except requests.RequestException as e:
        return jsonify(
            {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
        ), 502

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
                "instances": instances_by_entity_id.get(item.recognition_entity_id, []),
            }
        )
    return jsonify(items_view)


@bp.route("/api/items", methods=["POST"])
def item_create():
    try:
        item_data = ItemCreate(
            name=request.form["name"],
            category=request.form.get("category") or None,
            min_stock=int(request.form.get("min_stock", 0)),
        )
    except (ValidationError, ValueError) as e:
        return jsonify({"error": "validation_error", "message": str(e)}), 422

    images = [f for f in request.files.getlist("images") if f.filename]
    if not images:
        return jsonify(
            {"error": "validation_error", "message": "請至少上傳一張照片"}
        ), 422

    try:
        entity = vision_client.create_entity(item_data.name)
        entity_id = entity["id"]

        files = [
            ("images", (image.filename, image.stream, image.mimetype))
            for image in images
        ]
        vision_client.create_instance(entity_id, files)
    except requests.RequestException as e:
        return jsonify(
            {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
        ), 502

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

    return jsonify({"id": item.id}), 201


@bp.route("/api/items/<int:item_id>", methods=["DELETE"])
def item_delete(item_id):
    db = get_db()
    item = db.get(Item, item_id)

    try:
        vision_client.delete_entity(item.recognition_entity_id)
    except requests.RequestException as e:
        return jsonify(
            {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
        ), 502

    item.is_deleted = True
    db.commit()
    return "", 204


@bp.route("/api/items/<int:item_id>", methods=["PATCH"])
def item_update(item_id):
    db = get_db()
    item = db.get(Item, item_id)

    body = request.get_json(silent=True)
    if body is None:
        return jsonify(
            {"error": "invalid_json", "message": "request body 不是合法的 JSON"}
        ), 400
    try:
        update = ItemUpdate.model_validate(body)
    except ValidationError as e:
        return jsonify({"error": "validation_error", "details": e.errors()}), 422
    item.name = update.name
    item.min_stock = update.min_stock
    db.commit()
    return jsonify({"id": item.id, "name": item.name, "min_stock": item.min_stock})


@bp.route("/api/items/<int:item_id>/samples", methods=["GET", "POST"])
def item_samples(item_id):
    """不討論多instance:固定拿該物品entity底下第一個instance的樣本清單。"""
    db = get_db()
    item = db.get(Item, item_id)

    if request.method == "POST":
        image = request.files.get("image")
        if image is None:
            return jsonify(
                {"error": "invalid_request", "message": "缺少image欄位"}
            ), 400
        try:
            instances = vision_client.get_instances(item.recognition_entity_id)
            sample = vision_client.add_sample(instances[0]["id"], image)
        except requests.RequestException as e:
            return jsonify(
                {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
            ), 502
        return jsonify(sample), 201

    try:
        instances = vision_client.get_instances(item.recognition_entity_id)
        samples = vision_client.get_samples(instances[0]["id"])
    except requests.RequestException as e:
        return jsonify(
            {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
        ), 502
    return jsonify(samples)


@bp.route("/api/items/<int:item_id>/samples/<int:sample_id>/image")
def item_sample_image(item_id, sample_id):
    try:
        content, content_type = vision_client.get_sample_image(sample_id)
    except requests.RequestException as e:
        return jsonify(
            {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
        ), 502
    return Response(content, mimetype=content_type)


@bp.route("/api/items/<int:item_id>/samples/<int:sample_id>", methods=["PATCH", "DELETE"])
def item_sample_detail(item_id, sample_id):
    if request.method == "PATCH":
        body = request.get_json(silent=True)
        if body is None:
            return jsonify(
                {"error": "invalid_json", "message": "request body 不是合法的 JSON"}
            ), 400
        try:
            update = SampleBboxPatch.model_validate(body)
        except ValidationError as e:
            return jsonify({"error": "validation_error", "details": e.errors()}), 422
        try:
            sample = vision_client.recrop_sample(sample_id, list(update.bbox))
        except requests.RequestException as e:
            return jsonify(
                {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
            ), 502
        return jsonify(sample)

    try:
        vision_client.delete_sample(sample_id)
    except requests.RequestException as e:
        return jsonify(
            {"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}
        ), 502
    return "", 204
