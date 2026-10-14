from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static")

    # 共用的 base.html 放 app 自己的 template_folder(預設就是 templates/)。
    # 每個 blueprint 自己宣告 template_folder,Flask 內建的 DispatchingJinjaLoader
    # 會自動把 app 跟所有已註冊 blueprint 的 loader 一起排進查找鏈,不用手動組
    # ChoiceLoader。但 DispatchingJinjaLoader 是依註冊順序逐個 loader 找,不是只找
    # 「目前這個」blueprint 的資料夾,所以每個 blueprint 的 template_folder 底下
    # 還是要多包一層跟 blueprint 同名的子資料夾(例如 items/templates/items/xxx.html),
    # render_template 用「資料夾/檔名」的完整相對路徑呼叫,確保字串全域唯一。

    from .db import close_db

    app.teardown_appcontext(close_db)

    from .features import blueprints

    for bp in blueprints:
        app.register_blueprint(bp)

    return app
