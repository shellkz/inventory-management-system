from .home.views import bp as home_bp
from .items.views import bp as items_bp
from .recognize.views import bp as recognize_bp
from .stock_in.views import bp as stock_in_bp
from .stock_out.views import bp as stock_out_bp
from .stocktake.views import bp as stocktake_bp

blueprints = (home_bp, items_bp, recognize_bp, stock_in_bp, stock_out_bp, stocktake_bp)
