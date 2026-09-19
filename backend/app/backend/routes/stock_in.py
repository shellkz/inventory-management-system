import requests
from flask import Blueprint, current_app, jsonify, render_template, request
from pydantic import ValidationError

from .. import vision_client
from ..db import get_db
from ..schemas import StockInRequest
from ..stock_ops import process_stock_in

bp = Blueprint("stock_in", __name__)


@bp.route("/stock-in", methods=["GET", "POST"])
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

    # 把人工審核結果回饋給vision。失敗只記log,不影響這次入庫已經成功的事實。
    for item in payload.items:
        if item.prediction_id is None:
            continue
        if item.final_item_id is None:
            final_instance_id = None  # 確認為誤判(false positive)
        elif item.final_instance_id is not None:
            final_instance_id = item.final_instance_id
        else:
            continue  # 還沒有明確的instance資訊(例如舊版前端尚未提供),暫不同步

        try:
            vision_client.patch_prediction(
                item.prediction_id,
                final_instance_id,
                list(item.final_bbox) if item.final_bbox else None,
            )
        except requests.RequestException as e:
            current_app.logger.warning(
                f"同步修正結果到vision失敗 prediction_id={item.prediction_id}: {e}"
            )

    return jsonify({"transaction_id": transaction.id}), 200
