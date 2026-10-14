from flask import Blueprint, render_template

bp = Blueprint(
    "stock_out",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/stock-out/static",
)


@bp.route("/stock-out")
def stock_out_page():
    return render_template("stock_out/page.html")
