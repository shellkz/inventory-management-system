from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__)

    from .db import close_db

    app.teardown_appcontext(close_db)

    from .routes import main

    app.register_blueprint(main)

    return app
