"""Fixtures de pruebas. Por defecto usan SQLite en memoria; con TEST_DATABASE_URL se ejecutan
contra PostgreSQL (la misma suite, sin cambios)."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")  # evita crear el archivo de desarrollo al importar app

import pytest

from app import create_app
from config import TestingConfig
from extensions import db
from models import Order, Product, ProductSize, User

PASSWORD = "secreto123"
VALID_SHIPPING = {
    "recipient_name": "Ana Gómez", "phone": "3001234567", "municipality": "Medellín",
    "address": "Carrera 43A #1-50", "neighborhood": "El Poblado", "postal_code": "050021",
    "address_notes": "Torre 2, apto 301",
}


@pytest.fixture()
def app(tmp_path):
    class Cfg(TestingConfig):
        UPLOAD_FOLDER = str(tmp_path / "uploads")
    application = create_app(Cfg)

    @application.before_request
    def _fresh_g():
        # El fixture mantiene un contexto de aplicación abierto, por lo que `g` sobreviviría entre
        # peticiones. En producción cada petición tiene su propio `g`; aquí se reproduce ese comportamiento.
        from flask import g
        g.__dict__.clear()

    with application.app_context():
        db.drop_all()
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def make_product(name="Camisa Oxford", price=50000.0, stock=10, category="Camisas", garment_type="Camisa",
                 sizes=None, brand="Névora Basics", image=None):
    p = Product(name=name, brand=brand, price=price, stock=stock, category=category,
                garment_type=garment_type, description=f"{name} de prueba", image_filename=image)
    if sizes:
        p.sizes = [ProductSize(label=l, stock=s) for l, s in sizes.items()]
        p.stock = sum(sizes.values())
    db.session.add(p)
    db.session.commit()
    return p


def make_user(username="ana", email="ana@example.com", role="user", password=PASSWORD):
    u = User(username=username, email=email, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.commit()
    return u


def login(client, email="ana@example.com", password=PASSWORD, follow=True, next_url=None):
    url = "/login" + (f"?next={next_url}" if next_url else "")
    return client.post(url, data={"email": email, "password": password}, follow_redirects=follow)


def add_to_cart(client, product_id, quantity=1, size_id=None, follow=False):
    data = {"quantity": quantity}
    if size_id is not None:
        data["size_id"] = size_id
    return client.post(f"/cart/add/{product_id}", data=data, follow_redirects=follow)


def place_order(client, shipping=None, follow=False):
    return client.post("/checkout", data=shipping or VALID_SHIPPING, follow_redirects=follow)


@pytest.fixture()
def shop(app):
    """Catálogo de ejemplo con y sin tallas."""
    return {
        "shirt": make_product("Camisa Oxford", 89900, 25, "Camisas", "Camisa"),
        "tee": make_product("Camiseta Blanca", 39900, 60, "Camisas", "Camiseta"),
        "jean": make_product("Jean Slim", 129900, 30, "Pantalones", "Jean", sizes={"28": 3, "30": 4, "32": 0}),
        "dress": make_product("Vestido Midi", 159900, 12, "Vestidos", "Vestido", sizes={"S": 5, "M": 5, "L": 2}),
        "sold": make_product("Gorra Agotada", 34900, 0, "Accesorios", "Gorra"),
    }
