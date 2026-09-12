import os

import requests
from flask import Blueprint, render_template

main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/catalog")
def catalog():
    """只回傳片段 HTML,給 htmx 掛進頁面用,不是獨立頁面。"""
    resp = requests.get(
        f"{os.environ['VISION_SERVICE_URL']}/v1/entities",
        headers={"Authorization": f"Bearer {os.environ['VISION_API_KEY']}"},
        timeout=10,
    )
    resp.raise_for_status()
    entities = resp.json()["result"]
    return render_template("_catalog.html", entities=entities)
