"""Punto de entrada de Névora Moda!

``create_app`` arma la aplicación (extensiones, blueprints, manejadores de error).
``app`` queda disponible a nivel de módulo para ``flask run`` y ``gunicorn app:app``.
"""
import logging

from flask import Flask, render_template
from sqlalchemy import inspect

from config import Config, DEV_SECRET_KEY
from extensions import csrf, db, login_manager, migrate


def format_cop(value) -> str:
    """89900 -> $89.900"""
    try:
        return "$" + f"{float(value or 0):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def join_es(items) -> str:
    """['Medellín', 'Bello', 'Envigado'] -> 'Medellín, Bello y Envigado'"""
    items = list(items)
    if not items:
        return ""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def init_schema(app: Flask) -> bool:
    """Crea las tablas si la base está vacía y la marca como migrada. True si creó algo."""
    from flask_migrate import stamp
    with app.app_context():
        if "users" in inspect(db.engine).get_table_names():
            return False
        db.create_all()
        stamp(revision="head")
        return True


def create_app(config_object=Config) -> Flask:
    logging.basicConfig(level=logging.INFO)
    app = Flask(__name__)
    app.config.from_object(config_object)

    if app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        if app.config.get("APP_ENV") == "production":
            raise RuntimeError("Define SECRET_KEY en el entorno antes de ejecutar en producción.")
        app.logger.warning("SECRET_KEY no está definida: usando una clave de desarrollo insegura.")

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    import models  # noqa: F401  (registra los modelos)
    from services.factory import apply_cart_cookie, init_payment_registry
    init_payment_registry(app)
    app.after_request(apply_cart_cookie)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    from blueprints import register_blueprints
    register_blueprints(app)
    register_template_helpers(app)
    register_error_handlers(app)

    from cli import register_cli
    register_cli(app)

    if app.config.get("AUTO_INIT_SQLITE") and app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        if init_schema(app):
            app.logger.info("Base de datos SQLite creada.")
    return app


def register_template_helpers(app: Flask) -> None:
    from datetime import datetime
    from services.factory import get_cart_service, get_catalog_service, get_delivery_policy

    app.jinja_env.filters["cop"] = format_cop
    app.jinja_env.filters["join_es"] = join_es

    @app.context_processor
    def inject_globals():
        # Funciones perezosas: solo consultan la base de datos si la plantilla las usa.
        return {
            "current_year": datetime.now().year,
            "cart_count": lambda: get_cart_service().count(),
            "nav_categories": lambda: get_catalog_service().facets().categories,
            "delivery_municipalities": get_delivery_policy().municipalities,
            "store_contact": {
                "email": app.config.get("STORE_CONTACT_EMAIL"), "phone": app.config.get("STORE_CONTACT_PHONE"),
                "address": app.config.get("STORE_CONTACT_ADDRESS"), "hours": app.config.get("STORE_CONTACT_HOURS"),
            },
        }


def register_error_handlers(app: Flask) -> None:
    def page(code, title, message):
        def handler(error):
            if code == 500:
                db.session.rollback()
            return render_template("errors/error.html", code=code, title=title, message=message), code
        return handler

    app.register_error_handler(403, page(403, "Acceso restringido", "No tienes permiso para ver esta página."))
    app.register_error_handler(404, page(404, "Página no encontrada", "La página que buscas no existe o fue movida."))
    app.register_error_handler(413, page(413, "Archivo demasiado grande", "La imagen supera el tamaño máximo de 5 MB."))
    app.register_error_handler(500, page(500, "Algo salió mal", "Tuvimos un problema al procesar tu solicitud. Inténtalo de nuevo."))


app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
