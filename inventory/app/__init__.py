from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader


def create_app() -> Flask:
    app = Flask(__name__, static_folder="frontend/static")

    # 模板分兩個根目錄:frontend/templates放共用的(base.html),
    # frontend/pages放各頁面自己的,兩邊都要能找到。
    # 不能靠blueprint自己的template_folder,因為Flask是用同一個檔名在所有
    # blueprint的資料夾裡依註冊順序找,不是只找「目前這個」blueprint的資料夾,
    # 每個頁面都叫page.html會互相撞到,所以render_template一律用「資料夾/檔名」
    # 的完整相對路徑呼叫,確保字串全域唯一。
    app.jinja_loader = ChoiceLoader(
        [
            FileSystemLoader(f"{app.root_path}/frontend/templates"),
            FileSystemLoader(f"{app.root_path}/frontend/pages"),
        ]
    )

    from .backend.db import close_db

    app.teardown_appcontext(close_db)

    from .backend.routes import blueprints

    for bp in blueprints:
        app.register_blueprint(bp)

    return app
