from .home.routes import bp as home_bp
from .items.routes import bp as items_bp
from .recognize.routes import bp as recognize_bp
from .stock_in.routes import bp as stock_in_bp
from .stock_out.routes import bp as stock_out_bp
from .stocktake.routes import bp as stocktake_bp

blueprints = (home_bp, items_bp, recognize_bp, stock_in_bp, stock_out_bp, stocktake_bp)
