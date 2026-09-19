from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__, template_folder="frontend/templates", static_folder="frontend/static")

    from .backend.db import close_db

    app.teardown_appcontext(close_db)

    from .backend.routes import main

    app.register_blueprint(main)

    return app
