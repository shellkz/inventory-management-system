from flask import Blueprint, render_template

bp = Blueprint(
    "recognize",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/recognize/static",
)


@bp.route("/recognize")
def recognize_page():
    return render_template("recognize/page.html")
