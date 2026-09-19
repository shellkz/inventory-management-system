import requests
from flask import Blueprint, jsonify, render_template, request

from .. import vision_client
from ..db import get_db
from ..models import Item

bp = Blueprint("recognize", __name__)


@bp.route("/recognize", methods=["GET", "POST"])
def recognize():
    if request.method == "GET":
        return render_template("recognize.html")

    image = request.files["image"]
    try:
        data = vision_client.recognize(image)
    except requests.RequestException as e:
        return jsonify({"error": "vision_service_error", "message": f"辨識服務錯誤: {e}"}), 502

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
                "prediction_id": r["prediction_id"],
                "instance_id": r["instance_id"],
                "entity_id": r["entity_id"],
            }
        )

    return jsonify({"score_threshold": data["score_threshold"], "result": result})
