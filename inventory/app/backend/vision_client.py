"""呼叫 vision-service 的薄封裝層。

只負責組request、發送、回傳解析後的JSON,不吞例外——遇到`requests.RequestException`
一律往外拋,由呼叫端(routes.py)自己決定要回502、渲染錯誤模板、還是log後跳過,
因為每個呼叫情境對「vision失敗了怎麼辦」的答案不一樣,不該由這層決定。
"""
import requests

from . import config


def _headers():
    return {"Authorization": f"Bearer {config.VISION_API_KEY}"}


def get_entities():
    resp = requests.get(f"{config.VISION_SERVICE_URL}/v1/entities", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()["result"]


def get_instances(entity_id):
    resp = requests.get(
        f"{config.VISION_SERVICE_URL}/v1/entities/{entity_id}/instances",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["result"]


def create_entity(name):
    resp = requests.post(
        f"{config.VISION_SERVICE_URL}/v1/entities",
        json={"name": name},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def create_instance(entity_id, files):
    resp = requests.post(
        f"{config.VISION_SERVICE_URL}/v1/entities/{entity_id}/instances",
        files=files,
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def recognize(image):
    resp = requests.post(
        f"{config.VISION_SERVICE_URL}/v1/recognize",
        files={"file": (image.filename, image.stream, image.mimetype)},
        headers=_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def patch_prediction(prediction_id, final_instance_id, final_bbox):
    resp = requests.patch(
        f"{config.VISION_SERVICE_URL}/v1/predictions/{prediction_id}",
        json={"final_instance_id": final_instance_id, "final_bbox": final_bbox},
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
