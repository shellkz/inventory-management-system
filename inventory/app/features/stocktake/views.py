from flask import Blueprint, render_template

bp = Blueprint(
    "stocktake",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/stocktake/static",
)


@bp.route("/stocktake")
def stocktake_page():
    return render_template("stocktake/page.html")
