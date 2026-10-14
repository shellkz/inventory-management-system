from .home.views import bp as home_bp
from .items.api import bp as items_bp
from .recognize.api import bp as recognize_bp
from .stock_in.api import bp as stock_in_bp
from .stock_out.api import bp as stock_out_bp
from .stocktake.api import bp as stocktake_bp

blueprints = (home_bp, items_bp, recognize_bp, stock_in_bp, stock_out_bp, stocktake_bp)
