"""Carrito: visitante (cookie firmada), persistencia, fusión al iniciar sesión y límites de inventario."""
import pytest

from conftest import add_to_cart, login, make_product, make_user
from extensions import db
from models import CartItem, Product
from services.cart import CartCookieCodec, CartLine, CartService, CookieCartStore, DatabaseCartStore


def cart_page(client):
    return client.get("/cart/").get_data(as_text=True)


def test_guest_adds_updates_removes(client, shop):
    r = add_to_cart(client, shop["shirt"].id, 2)
    assert r.status_code == 302 and "nevora_cart" in r.headers.get("Set-Cookie", "")
    body = cart_page(client)
    assert "Camisa Oxford" in body and "$179.800" in body  # 2 × 89.900
    pid = shop["shirt"].id
    client.post(f"/cart/update/{pid}", data={"quantity": 5})
    assert "$449.500" in cart_page(client)
    client.post(f"/cart/update/{pid}", data={"quantity": 0})   # 0 elimina
    assert "Tu carrito está vacío" in cart_page(client)
    add_to_cart(client, pid, 1)
    client.post(f"/cart/remove/{pid}")
    assert "Tu carrito está vacío" in cart_page(client)


def test_cart_indicator_counts_items(client, shop):
    add_to_cart(client, shop["shirt"].id, 2)
    add_to_cart(client, shop["tee"].id, 1)
    assert 'class="cart-badge" aria-hidden="true">3<' in client.get("/").get_data(as_text=True)


def test_cart_survives_closing_the_browser(app, client, shop):
    """Un navegador nuevo que conserva solo la cookie persistente recupera el carrito."""
    add_to_cart(client, shop["shirt"].id, 3)
    cookie = client.get_cookie("nevora_cart")
    assert cookie is not None
    reopened = app.test_client()   # sesión nueva: sin la cookie de sesión de Flask
    reopened.set_cookie("nevora_cart", cookie.value)
    assert "Camisa Oxford" in cart_page(reopened) and "$269.700" in cart_page(reopened)


def test_cookie_is_persistent_not_session_only(client, shop):
    r = add_to_cart(client, shop["shirt"].id)
    header = r.headers["Set-Cookie"]
    assert "Max-Age=" in header and "HttpOnly" in header and "SameSite=Lax" in header


def test_tampered_cookie_is_ignored(app, shop):
    c = app.test_client()
    c.set_cookie("nevora_cart", "esto-no-esta-firmado")
    assert "Tu carrito está vacío" in cart_page(c)


def test_forged_cookie_signed_with_other_key_is_ignored(app, shop):
    forged = CartCookieCodec("otra-clave", 3600).encode([CartLine(shop["shirt"].id, None, 5)])
    c = app.test_client()
    c.set_cookie("nevora_cart", forged)
    assert "Tu carrito está vacío" in cart_page(c)


def test_prices_always_come_from_database(client, shop):
    """La cookie solo guarda ids y cantidades: si el precio cambia, el carrito lo refleja."""
    add_to_cart(client, shop["shirt"].id, 1)
    assert "$89.900" in cart_page(client)
    shop["shirt"].price = 100000
    db.session.commit()
    assert "$100.000" in cart_page(client)
    assert "price" not in client.get_cookie("nevora_cart").value.lower()


def test_cannot_add_more_than_stock(client, shop):
    size_l = [s for s in shop["dress"].sizes if s.label == "L"][0]      # la talla L tiene 2 unidades
    assert add_to_cart(client, shop["dress"].id, 1, size_id=size_l.id).status_code == 302
    r = add_to_cart(client, shop["dress"].id, 3, size_id=size_l.id, follow=True)
    assert "Solo quedan 2 unidades" in r.get_data(as_text=True)
    r = add_to_cart(client, shop["dress"].id, 2, size_id=size_l.id, follow=True)   # 1 + 2 > 2
    assert "ya tienes 1 en el carrito" in r.get_data(as_text=True)
    assert "Vestido Midi" in cart_page(client)


def test_cannot_add_sold_out_product(client, shop):
    r = add_to_cart(client, shop["sold"].id, 1, follow=True)
    assert "agotado" in r.get_data(as_text=True).lower()
    assert "Tu carrito está vacío" in cart_page(client)


def test_sized_product_requires_size(client, shop):
    r = add_to_cart(client, shop["jean"].id, 1, follow=True)
    assert "Selecciona una talla" in r.get_data(as_text=True)
    assert "Tu carrito está vacío" in cart_page(client)


def test_size_of_another_product_is_rejected(client, shop):
    foreign = shop["jean"].sizes[0].id
    r = add_to_cart(client, shop["dress"].id, 1, size_id=foreign, follow=True)
    assert "Selecciona una talla" in r.get_data(as_text=True)


def test_invalid_quantities_rejected(client, shop):
    for qty in (0, -3):
        r = add_to_cart(client, shop["shirt"].id, qty, follow=True)
        assert "al menos 1" in r.get_data(as_text=True)
    r = add_to_cart(client, shop["tee"].id, 21, follow=True)   # máximo por línea = 20
    assert "hasta 20 unidades" in r.get_data(as_text=True)


def test_deleted_product_is_removed_with_notice(client, shop):
    add_to_cart(client, shop["tee"].id, 1)
    db.session.delete(db.session.get(Product, shop["tee"].id))
    db.session.commit()
    r = client.get("/cart/")
    assert "ya no están disponibles" in r.get_data(as_text=True)
    assert "Tu carrito está vacío" in cart_page(client)


def test_cart_marks_lines_that_lost_stock(client, shop):
    add_to_cart(client, shop["shirt"].id, 5)
    shop["shirt"].stock = 2
    db.session.commit()
    body = cart_page(client)
    assert "Solo quedan 2 unidades" in body and "disabled" in body   # no deja finalizar


def test_guest_cart_merges_into_user_cart_on_login(app, client, shop):
    user = make_user()
    add_to_cart(client, shop["shirt"].id, 2)
    add_to_cart(client, shop["tee"].id, 1)
    login(client)
    items = {(i.product_id, i.quantity) for i in CartItem.query.all()}
    assert items == {(shop["shirt"].id, 2), (shop["tee"].id, 1)}
    assert client.get_cookie("nevora_cart") is None      # la cookie de visitante se elimina
    assert "Camisa Oxford" in cart_page(client)


def test_merge_does_not_duplicate_or_exceed_stock(app, client, shop):
    user = make_user()
    shop["tee"].stock = 3
    db.session.commit()
    # carrito previo del usuario: 2 camisetas
    login(client)
    add_to_cart(client, shop["tee"].id, 2)
    client.post("/logout")
    # como visitante agrega 2 camisetas más y 1 camisa
    add_to_cart(client, shop["tee"].id, 2)
    add_to_cart(client, shop["shirt"].id, 1)
    r = login(client)
    quantities = {i.product_id: i.quantity for i in CartItem.query.all()}
    assert quantities[shop["tee"].id] == 3                # 2 + 2 recortado a las 3 existencias
    assert quantities[shop["shirt"].id] == 1
    assert CartItem.query.filter_by(product_id=shop["tee"].id).count() == 1   # sin líneas duplicadas
    assert "Ajustamos las unidades" in r.get_data(as_text=True)


def test_registering_also_keeps_the_cart(client, shop):
    add_to_cart(client, shop["shirt"].id, 2)
    client.post("/register", data={"username": "nuevo", "email": "nuevo@example.com",
                                   "password": "secreto123", "password2": "secreto123"})
    assert CartItem.query.one().quantity == 2


def test_user_cart_persists_across_sessions(app, client, shop):
    make_user()
    login(client)
    add_to_cart(client, shop["shirt"].id, 4)
    other_device = app.test_client()
    login(other_device)
    assert "$359.600" in cart_page(other_device)


# --- Sustitución de almacenes (Liskov): ambos cumplen el mismo contrato ------------------------
@pytest.fixture(params=["cookie", "database"])
def store(request, app):
    if request.param == "cookie":
        return CookieCartStore(None, CartCookieCodec("k", 3600))
    user = make_user("tienda", "store@example.com")
    return DatabaseCartStore(db.session, user.id)


def test_stores_are_interchangeable(store, shop):
    shirt, tee = shop["shirt"].id, shop["tee"].id
    size = shop["dress"].sizes[0].id
    dress = shop["dress"].id
    key = lambda l: (l.product_id, l.size_id or 0, l.quantity)
    assert store.lines() == []
    store.set_line(shirt, None, 2)
    store.set_line(dress, size, 1)
    store.set_line(shirt, None, 5)                   # reemplaza, no duplica
    assert sorted(map(key, store.lines())) == sorted([(shirt, 0, 5), (dress, size, 1)])
    store.remove_line(dress, size)
    assert [(l.size_id, l.quantity) for l in store.lines()] == [(None, 5)]
    store.set_line(shirt, None, 0)                   # cantidad 0 elimina
    assert store.lines() == []
    store.set_line(tee, None, 1)
    store.clear()
    assert store.lines() == []


def test_cart_service_works_with_any_store(app, shop, store):
    service = CartService(store, db.session, db.session.commit)
    service.add(shop["shirt"].id, None, 2)
    service.add(shop["shirt"].id, None, 1)
    assert service.count() == 3 and service.view().total == 3 * 89900
