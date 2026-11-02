"""Configuración de Névora Moda!

Toda la configuración se lee del entorno (archivo .env). Hay una clase por
contexto de ejecución para que las pruebas nunca toquen la base de datos real.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DEV_SECRET_KEY = "dev-only-insecure-key-change-me"


def _database_uri() -> str:
    """URI de la base de datos: PostgreSQL en producción, SQLite por defecto."""
    uri = os.getenv("DATABASE_URL", "").strip()
    if not uri:
        return "sqlite:///" + os.path.join(BASE_DIR, "nevora_dev.sqlite3")
    if uri.startswith("postgres://"):  # esquema antiguo de algunos proveedores
        uri = "postgresql://" + uri[len("postgres://"):]
    return uri


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY") or DEV_SECRET_KEY
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(BASE_DIR, "static", "uploads"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = APP_ENV == "production"

    # Carrito de visitantes: cookie firmada (no depende del login ni de JavaScript)
    CART_COOKIE_NAME = "nevora_cart"
    CART_COOKIE_MAX_AGE = int(timedelta(days=30).total_seconds())
    CART_MAX_LINES = 50
    CART_MAX_QTY_PER_LINE = 20

    # Regla de negocio: solo se entrega en estos municipios de Antioquia
    DELIVERY_MUNICIPALITIES = ("Medellín", "Bello", "Envigado")

    # Pie de página (opcional; si no se definen no se muestran)
    STORE_CONTACT_EMAIL = os.getenv("STORE_CONTACT_EMAIL")
    STORE_CONTACT_PHONE = os.getenv("STORE_CONTACT_PHONE")
    STORE_CONTACT_ADDRESS = os.getenv("STORE_CONTACT_ADDRESS")
    STORE_CONTACT_HOURS = os.getenv("STORE_CONTACT_HOURS")

    CATALOG_PAGE_SIZE = 12
    LOW_STOCK_THRESHOLD = 5
    AUTO_INIT_SQLITE = True  # con SQLite la app crea el esquema sola la primera vez


class TestingConfig(Config):
    TESTING = True
    APP_ENV = "testing"
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite://")
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    AUTO_INIT_SQLITE = False
    SESSION_COOKIE_SECURE = False
