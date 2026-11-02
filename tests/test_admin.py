"""Panel administrativo: productos (con tallas e imagen), usuarios y pedidos."""
import io

import pytest

from conftest import add_to_cart, login, make_product, make_user, place_order
from extensions import db
from models import CartItem, Order, Product, ProductSize, User

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82")


@pytest.fixture()
def admin(app, client):
    make_user("boss", "boss@example.com", role="admin")
    login(client, "boss@example.com")
    return client


def product_form(**over):
    data = {"name": "Chaqueta Denim", "brand": "Denim Co.", "category": "Chaquetas", "garment_type": "Chaqueta",
            "price": "179900", "stock": "14", "sizes": "", "description": "Chaqueta clásica"}
    data.update(over)
    return data


def test_dashboard_shows_real_numbers(admin, shop):
    body = admin.get("/admin/").get_data(as_text=True)
    assert ">5<" in body and "Pocas existencias" in body and "Gorra Agotada" in body


def test_create_product_without_sizes(admin):
    r = admin.post("/admin/products/create", data=product_form(), follow_redirects=True)
    assert "Producto creado" in r.get_data(as_text=True)
    p = Product.query.one()
    assert (p.name, p.price, p.stock, p.garment_type, p.has_sizes) == ("Chaqueta Denim", 179900, 14, "Chaqueta", False)


def test_create_product_with_sizes_computes_total_stock(admin):
    admin.post("/admin/products/create", data=product_form(sizes="M:4, S:3, XL:2, L:1", stock=""))
    p = Product.query.one()
    assert p.stock == 10 and [s.label for s in p.ordered_sizes] == ["S", "M", "L", "XL"]


@pytest.mark.parametrize("sizes,msg", [("S:x", "número entero"), ("S", "TALLA:CANTIDAD"), ("S:1, S:2", "repetida"),
                                       ("S:-1", "número entero")])
def test_invalid_sizes_are_rejected(admin, sizes, msg):
    r = admin.post("/admin/products/create", data=product_form(sizes=sizes))
    assert msg in r.get_data(as_text=True) and Product.query.count() == 0


def test_stock_or_sizes_required(admin):
    r = admin.post("/admin/products/create", data=product_form(stock=""))
    assert "Indica las existencias" in r.get_data(as_text=True)


def test_product_form_validation(admin):
    r = admin.post("/admin/products/create", data=product_form(name="", price="-5"))
    assert Product.query.count() == 0 and "field-error" in r.get_data(as_text=True)


def test_upload_valid_image_and_reject_bad_type(admin, app):
    data = product_form()
    data["image"] = (io.BytesIO(PNG), "foto.png")
    admin.post("/admin/products/create", data=data, content_type="multipart/form-data")
    p = Product.query.one()
    assert p.image_filename.endswith("-foto.png")
    import os
    assert os.path.exists(os.path.join(app.config["UPLOAD_FOLDER"], p.image_filename))
    bad = product_form(name="Otra")
    bad["image"] = (io.BytesIO(b"<?php echo 1; ?>"), "shell.php")
    r = admin.post("/admin/products/create", data=bad, content_type="multipart/form-data")
    assert Product.query.count() == 1 and "Solo imágenes" in r.get_data(as_text=True)


def test_uploads_do_not_overwrite_each_other(admin, app):
    names = []
    for i in range(2):
        d = product_form(name=f"P{i}")
        d["image"] = (io.BytesIO(PNG), "misma.png")
        admin.post("/admin/products/create", data=d, content_type="multipart/form-data")
    names = [p.image_filename for p in Product.query.all()]
    assert len(set(names)) == 2


def test_edit_product_keeps_and_updates_sizes(admin, shop):
    jean = shop["jean"]
    page = admin.get(f"/admin/products/edit/{jean.id}").get_data(as_text=True)
    assert "28:3, 30:4, 32:0" in page
    admin.post(f"/admin/products/edit/{jean.id}", data=product_form(name="Jean Slim", sizes="28:9, 34:2", stock=""))
    p = db.session.get(Product, jean.id)
    assert {s.label: s.stock for s in p.sizes} == {"28": 9, "34": 2} and p.stock == 11


def test_removing_a_size_cleans_carts(admin, client, shop):
    jean = shop["jean"]
    size_30 = [s for s in jean.sizes if s.label == "30"][0]
    CartUser = make_user("c", "c@example.com")
    c2 = client.application.test_client()
    login(c2, "c@example.com")
    add_to_cart(c2, jean.id, 1, size_id=size_30.id)
    admin.post(f"/admin/products/edit/{jean.id}", data=product_form(name="Jean Slim", sizes="28:3", stock=""))
    assert CartItem.query.count() == 0


def test_delete_product_without_orders(admin, shop):
    r = admin.post(f"/admin/products/delete/{shop['sold'].id}", follow_redirects=True)
    assert "Producto eliminado" in r.get_data(as_text=True) and db.session.get(Product, shop["sold"].id) is None


def test_delete_product_with_orders_is_blocked(app, admin, shop):
    make_user("c", "c@example.com")
    c = app.test_client(); login(c, "c@example.com")
    add_to_cart(c, shop["shirt"].id, 1); place_order(c)
    r = admin.post(f"/admin/products/delete/{shop['shirt'].id}", follow_redirects=True)
    assert "tiene pedidos registrados" in r.get_data(as_text=True) and db.session.get(Product, shop["shirt"].id)


def test_delete_product_clears_it_from_carts(app, admin, shop):
    make_user("c", "c@example.com")
    c = app.test_client(); login(c, "c@example.com")
    add_to_cart(c, shop["tee"].id, 1)
    admin.post(f"/admin/products/delete/{shop['tee'].id}")
    assert CartItem.query.count() == 0 and "carrito está vacío" in c.get("/cart/").get_data(as_text=True)


# --- Usuarios ------------------------------------------------------------------------------------------
def test_admin_creates_edits_deletes_users(admin):
    admin.post("/admin/users/add", data={"username": "ventas", "email": "ventas@example.com", "password": "secreto123", "role": "admin"})
    u = User.query.filter_by(email="ventas@example.com").one()
    assert u.is_admin
    admin.post(f"/admin/users/edit/{u.id}", data={"username": "ventas", "email": "ventas@example.com", "password": "", "role": "user"})
    assert not db.session.get(User, u.id).is_admin
    admin.post(f"/admin/users/edit/{u.id}", data={"username": "ventas", "email": "ventas@example.com", "password": "nuevaclave1", "role": "user"})
    assert db.session.get(User, u.id).check_password("nuevaclave1")
    admin.post(f"/admin/users/delete/{u.id}")
    assert db.session.get(User, u.id) is None


def test_admin_user_validation(admin):
    r = admin.post("/admin/users/add", data={"username": "x", "email": "mal", "password": "", "role": "root"})
    assert User.query.count() == 1 and "field-error" in r.get_data(as_text=True)
    make_user("dup", "dup@example.com")
    r = admin.post("/admin/users/add", data={"username": "dup", "email": "otro@example.com", "password": "secreto123", "role": "user"})
    assert "Ya existe un usuario" in r.get_data(as_text=True)


def test_cannot_delete_self_or_last_admin_or_demote_last_admin(admin):
    boss = User.query.filter_by(email="boss@example.com").one()
    assert "No puedes eliminar tu propia cuenta" in admin.post(f"/admin/users/delete/{boss.id}", follow_redirects=True).get_data(as_text=True)
    r = admin.post(f"/admin/users/edit/{boss.id}", data={"username": "boss", "email": "boss@example.com", "password": "", "role": "user"})
    assert "único administrador" in r.get_data(as_text=True) and db.session.get(User, boss.id).is_admin


def test_cannot_delete_user_with_orders(app, admin, shop):
    user = make_user("c", "c@example.com")
    c = app.test_client(); login(c, "c@example.com")
    add_to_cart(c, shop["shirt"].id, 1); place_order(c)
    r = admin.post(f"/admin/users/delete/{user.id}", follow_redirects=True)
    assert "tiene pedidos" in r.get_data(as_text=True) and db.session.get(User, user.id)


# --- Pedidos -----------------------------------------------------------------------------------------------
@pytest.fixture()
def customer_order(app, shop):
    make_user("c", "c@example.com")
    c = app.test_client(); login(c, "c@example.com")
    add_to_cart(c, shop["shirt"].id, 2); place_order(c)
    return Order.query.one()


def test_admin_lists_filters_and_views_orders(admin, customer_order):
    assert f"#{customer_order.id}" in admin.get("/admin/orders").get_data(as_text=True)
    assert f"#{customer_order.id}" not in admin.get("/admin/orders?status=shipped").get_data(as_text=True)
    detail = admin.get(f"/admin/orders/{customer_order.id}").get_data(as_text=True)
    assert "Medellín" in detail and "Camisa Oxford" in detail and "c@example.com" in detail


def test_admin_updates_status(admin, customer_order):
    for status in ("paid", "shipped", "delivered"):
        r = admin.post(f"/admin/orders/{customer_order.id}/status", data={"status": status}, follow_redirects=True)
        assert "Estado del pedido actualizado" in r.get_data(as_text=True)
        assert db.session.get(Order, customer_order.id).status == status


def test_admin_rejects_invalid_status(admin, customer_order):
    r = admin.post(f"/admin/orders/{customer_order.id}/status", data={"status": "hackeado"}, follow_redirects=True)
    assert "no válido" in r.get_data(as_text=True) and db.session.get(Order, customer_order.id).status == "created"


def test_admin_cancel_restores_stock_once_and_cannot_reactivate(admin, customer_order, shop):
    admin.post(f"/admin/orders/{customer_order.id}/status", data={"status": "cancelled"})
    assert Product.query.get(shop["shirt"].id).stock == 25
    admin.post(f"/admin/orders/{customer_order.id}/status", data={"status": "cancelled"})   # idempotente
    r = admin.post(f"/admin/orders/{customer_order.id}/status", data={"status": "paid"}, follow_redirects=True)
    assert "no puede reactivarse" in r.get_data(as_text=True)
    assert Product.query.get(shop["shirt"].id).stock == 25


def test_admin_sees_orders_of_other_admins_too(app, admin, shop):
    """Antes el panel ocultaba pedidos hechos por administradores; ahora se muestran todos."""
    add_to_cart(admin, shop["shirt"].id, 1); place_order(admin)
    assert "boss" in admin.get("/admin/orders").get_data(as_text=True)
