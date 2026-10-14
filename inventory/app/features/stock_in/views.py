from flask import Blueprint, render_template

bp = Blueprint(
    "stock_in",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/stock-in/static",
)


@bp.route("/stock-in")
def stock_in_page():
    return render_template("stock_in/page.html")
