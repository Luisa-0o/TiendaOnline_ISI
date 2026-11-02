"""Registro, sesión, roles y protección de rutas."""
import pytest

from conftest import login, make_product, make_user, add_to_cart
from extensions import db
from models import User

REGISTER = {"username": "nuevo", "email": "nuevo@example.com", "password": "secreto123", "password2": "secreto123"}


def test_register_creates_user_and_logs_in(client, shop):
    r = client.post("/register", data=REGISTER, follow_redirects=True)
    assert r.status_code == 200 and "Elige tus 2 categorías" in r.get_data(as_text=True)
    user = User.query.filter_by(email="nuevo@example.com").one()
    assert user.check_password("secreto123") and user.password_hash != "secreto123"


def test_first_registered_user_is_NOT_admin(client):
    """Antes el primer usuario registrado recibía rol admin automáticamente."""
    client.post("/register", data=REGISTER)
    assert User.query.one().role == "user"


def test_registration_cannot_smuggle_a_role(client):
    client.post("/register", data={**REGISTER, "role": "admin", "is_admin": "1"})
    assert User.query.one().role == "user"


def test_register_validation_messages(client):
    make_user("ana", "ana@example.com")
    r = client.post("/register", data={**REGISTER, "email": "ANA@example.com"})
    assert "ya está registrado" in r.get_data(as_text=True)
    r = client.post("/register", data={**REGISTER, "username": "Ana"})
    assert "ya existe" in r.get_data(as_text=True)
    r = client.post("/register", data={**REGISTER, "password2": "otra"})
    assert "no coinciden" in r.get_data(as_text=True)
    assert User.query.count() == 1


def test_login_logout(client, app):
    make_user()
    assert "Correo o contraseña incorrectos" in login(client, password="mal").get_data(as_text=True)
    assert "Iniciaste sesión" in login(client).get_data(as_text=True)
    assert client.get("/logout").status_code == 405            # cerrar sesión solo por POST
    r = client.post("/logout", follow_redirects=True)
    assert "Cerraste sesión" in r.get_data(as_text=True)
    assert client.get("/checkout").status_code == 302


@pytest.mark.parametrize("url", ["/checkout", "/orders", "/orders/1", "/invoice/1", "/payment", "/payment/1",
                                 "/cuenta", "/change-password", "/select-favs"])
def test_private_routes_require_login(client, url):
    r = client.get(url)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


@pytest.mark.parametrize("url", ["/admin/", "/admin/products", "/admin/products/create", "/admin/users",
                                 "/admin/users/add", "/admin/orders", "/admin/orders/1"])
def test_admin_routes_redirect_visitors_to_login(client, url):
    r = client.get(url)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


@pytest.mark.parametrize("method,url", [("get", "/admin/"), ("get", "/admin/products"), ("get", "/admin/users"),
                                        ("get", "/admin/orders"), ("get", "/admin/products/create"),
                                        ("post", "/admin/products/delete/1"), ("post", "/admin/users/delete/1"),
                                        ("post", "/admin/orders/1/status"), ("post", "/admin/users/add")])
def test_normal_user_gets_403_on_every_admin_route(client, method, url):
    make_user()
    login(client)
    assert getattr(client, method)(url).status_code == 403


def test_admin_can_enter_panel(client):
    make_user("boss", "boss@example.com", role="admin")
    r = login(client, "boss@example.com")
    assert "Resumen" in r.get_data(as_text=True)      # el admin aterriza en su panel
    assert client.get("/admin/products").status_code == 200


def test_admin_panel_is_visually_separate_from_storefront(client):
    make_user("boss", "boss@example.com", role="admin")
    login(client, "boss@example.com")
    admin = client.get("/admin/").get_data(as_text=True)
    assert "admin-side" in admin and "site-header" not in admin
    assert "site-header" in client.get("/").get_data(as_text=True)


def test_open_redirect_is_blocked(client):
    make_user()
    r = client.post("/login?next=https://evil.example/x", data={"email": "ana@example.com", "password": "secreto123"})
    assert r.status_code == 302 and "evil.example" not in r.headers["Location"]
    make_user("b", "b@example.com")
    client2 = client.application.test_client()
    r = client2.post("/login?next=//evil.example", data={"email": "b@example.com", "password": "secreto123"})
    assert "evil.example" not in r.headers["Location"]


def test_login_next_is_honoured_when_safe(client):
    make_user()
    r = client.post("/login?next=/checkout", data={"email": "ana@example.com", "password": "secreto123"})
    assert r.headers["Location"].endswith("/checkout")


def test_change_password(client):
    make_user()
    login(client)
    r = client.post("/change-password", data={"current_password": "mal", "new_password": "nueva123", "new_password2": "nueva123"})
    assert "contraseña actual es incorrecta" in r.get_data(as_text=True)
    client.post("/change-password", data={"current_password": "secreto123", "new_password": "nueva123", "new_password2": "nueva123"})
    assert User.query.one().check_password("nueva123")


def test_favorites_and_recommendations(client, shop):
    make_user()
    login(client)
    r = client.post("/select-favs", data={"categories": ["Camisas"]}, follow_redirects=True)
    assert "exactamente 2" in r.get_data(as_text=True)
    client.post("/select-favs", data={"categories": ["Camisas", "Vestidos"]})
    user = User.query.one()
    assert user.favorite_categories == ["Camisas", "Vestidos"]
    home = client.get("/").get_data(as_text=True)
    assert "Pensado para ti" in home
    assert "Pensado para ti" in client.get("/catalogo").get_data(as_text=True)
    assert "Pensado para ti" not in client.get("/catalogo?q=jean").get_data(as_text=True)   # no estorba al buscar


def test_favorites_ignore_unknown_categories(client, shop):
    make_user()
    login(client)
    r = client.post("/select-favs", data={"categories": ["Inventada", "Camisas"]}, follow_redirects=True)
    assert "exactamente 2" in r.get_data(as_text=True)


def test_csrf_is_enforced_when_enabled(tmp_path, shop):
    from app import create_app
    from config import TestingConfig

    class Cfg(TestingConfig):
        WTF_CSRF_ENABLED = True
    app = create_app(Cfg)
    c = app.test_client()
    assert c.post(f"/cart/add/{shop['shirt'].id}", data={"quantity": 1}).status_code == 400
    assert c.post("/login", data={"email": "a@b.co", "password": "x"}).status_code == 400
