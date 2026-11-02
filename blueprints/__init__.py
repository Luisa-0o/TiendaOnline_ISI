"""Registro de blueprints. Las rutas son delgadas: delegan toda la lógica en services/."""
from flask import Flask


def register_blueprints(app: Flask) -> None:
    from blueprints.admin import bp as admin_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.cart import bp as cart_bp
    from blueprints.checkout import bp as checkout_bp
    from blueprints.shop import bp as shop_bp

    for bp in (shop_bp, cart_bp, auth_bp, checkout_bp, admin_bp):
        app.register_blueprint(bp)
