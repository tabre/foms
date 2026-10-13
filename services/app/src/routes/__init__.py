"""Routes layer: maps requests to controller operations. No business rules here."""


from src import errors as E


def error_dict(errs: list) -> dict:
    return {e["field"]: E.message(e["message"]) for e in errs}


from src.routes.auth_routes import bp as auth_bp
from src.routes.options_routes import bp as options_bp
from src.routes.order_routes import bp as order_bp
from src.routes.stock_routes import bp as stock_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(options_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(stock_bp)
