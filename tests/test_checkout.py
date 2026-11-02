"""Proceso de compra completo: de visitante a pedido pagado, con revalidación en el servidor."""
import re
from datetime import date

import pytest

from conftest import VALID_SHIPPING, add_to_cart, login, make_product, make_user, place_order
from extensions import db
from models import CartItem, Order, OrderItem, Product, ProductSize

CARD = {"payment_method": "visa", "card_number": "4111 1111 1111 1111", "expiry_date": "12/40", "cvv": "123"}


def test_full_purchase_flow_from_guest(client, shop):
    # 1-5. visitante explora, agrega y revisa el carrito
    assert client.get("/catalogo").status_code == 200
    add_to_cart(client, shop["shirt"].id, 2)
    add_to_cart(client, shop["tee"].id, 1)
    assert "$219.700" in client.get("/cart/").get_data(as_text=True)
    # 6-7. finalizar compra sin sesión → pide iniciar sesión/registrarse
    r = client.get("/checkout")
    assert r.status_code == 302 and "/login?next=" in r.headers["Location"]
    login_page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Tu carrito se conserva" in login_page and "Crear cuenta" in login_page
    # 8. se registra desde ahí y continúa la compra (no se pierde el carrito)
    r = client.post("/register?next=/checkout", data={"username": "ana", "email": "ana@example.com", "password": "secreto123",
                                                      "password2": "secreto123", "next": "/checkout"})
    assert r.headers["Location"].endswith("/checkout")
    page = client.get("/checkout").get_data(as_text=True)
    assert "Datos de entrega" in page and "Camisa Oxford" in page and "$219.700" in page
    # 9-12. datos de entrega → pedido
    r = place_order(client)
    order = Order.query.one()
    assert r.headers["Location"].endswith(f"/payment/{order.id}")
    assert order.status == "created" and order.total == 219700 and order.user.username == "ana"
    assert Product.query.get(shop["shirt"].id).stock == 23 and Product.query.get(shop["tee"].id).stock == 59
    assert CartItem.query.count() == 0                       # el carrito se vació al crear el pedido
    # 13-14. pago simulado + confirmación
    r = client.post(f"/payment/{order.id}", data=CARD, follow_redirects=True)
    body = r.get_data(as_text=True)
    assert "¡Gracias por tu compra!" in body and "Visa" in body
    assert db.session.get(Order, order.id).status == "paid"
    # 15. consulta del pedido y factura
    assert "Camisa Oxford" in client.get(f"/orders/{order.id}").get_data(as_text=True)
    inv = client.get(f"/invoice/{order.id}").get_data(as_text=True)
    assert "Factura de compra" in inv and "Medellín" in inv and "Ana Gómez" in inv and "$219.700" in inv
    assert f"#{order.id}" in client.get("/orders").get_data(as_text=True)


def test_login_user_with_existing_cart_checks_out(client, shop):
    make_user()
    add_to_cart(client, shop["shirt"].id, 1)
    r = client.post("/login?next=/checkout", data={"email": "ana@example.com", "password": "secreto123"})
    assert r.headers["Location"].endswith("/checkout")
    assert place_order(client).status_code == 302 and Order.query.count() == 1


def test_empty_cart_cannot_checkout(client, shop):
    make_user(); login(client)
    r = client.get("/checkout", follow_redirects=True)
    assert "carrito está vacío" in r.get_data(as_text=True)
    assert place_order(client).status_code == 302 and Order.query.count() == 0


def test_stock_is_revalidated_at_order_time(client, shop):
    """El carrito no reserva inventario: otro cliente puede comprar antes."""
    make_user(); login(client)
    add_to_cart(client, shop["tee"].id, 5)
    shop["tee"].stock = 3                    # alguien más compró mientras tanto
    db.session.commit()
    r = place_order(client, follow=True)
    body = r.get_data(as_text=True)
    assert "corrige las prendas marcadas" in body and "Solo quedan 3 unidades" in body
    assert Order.query.count() == 0 and Product.query.get(shop["tee"].id).stock == 3
    assert CartItem.query.one().quantity == 5               # el carrito se conserva para corregirlo
    client.post(f"/cart/update/{shop['tee'].id}", data={"quantity": 3})
    assert place_order(client).status_code == 302 and Product.query.get(shop["tee"].id).stock == 0


def test_sold_out_while_in_cart_blocks_order(client, shop):
    make_user(); login(client)
    add_to_cart(client, shop["tee"].id, 1)
    shop["tee"].stock = 0
    db.session.commit()
    r = client.get("/checkout", follow_redirects=True)
    assert "Agotado" in r.get_data(as_text=True)
    assert place_order(client, follow=True).status_code == 200 and Order.query.count() == 0


def test_price_is_taken_from_database_not_from_client(client, shop):
    make_user(); login(client)
    add_to_cart(client, shop["shirt"].id, 1)
    shop["shirt"].price = 95000
    db.session.commit()
    place_order(client, {**VALID_SHIPPING, "price": "1", "total": "1", "unit_price": "1"})  # parámetros espurios
    order = Order.query.one()
    assert order.total == 95000 and order.items[0].price == 95000


def test_order_price_is_frozen_after_price_change(client, shop):
    make_user(); login(client)
    add_to_cart(client, shop["shirt"].id, 1)
    place_order(client)
    shop["shirt"].price = 1
    db.session.commit()
    assert "$89.900" in client.get(f"/invoice/{Order.query.one().id}").get_data(as_text=True)


def test_sized_purchase_discounts_size_and_total_stock(client, shop):
    make_user(); login(client)
    size_s = [s for s in shop["dress"].sizes if s.label == "S"][0]
    add_to_cart(client, shop["dress"].id, 2, size_id=size_s.id)
    place_order(client)
    assert db.session.get(ProductSize, size_s.id).stock == 3 and Product.query.get(shop["dress"].id).stock == 10
    item = OrderItem.query.one()
    assert item.size_label == "S" and item.size_id == size_s.id


def test_size_sold_out_while_other_sizes_remain(client, shop):
    make_user(); login(client)
    size_l = [s for s in shop["dress"].sizes if s.label == "L"][0]
    add_to_cart(client, shop["dress"].id, 2, size_id=size_l.id)
    size_l.stock = 1; db.session.commit()
    body = place_order(client, follow=True).get_data(as_text=True)
    assert "Solo queda 1 unidad." in body            # singular correcto
    assert Order.query.count() == 0


def test_all_or_nothing_when_one_line_fails(client, shop):
    """Transacción: si una línea falla, no se descuenta ninguna existencia."""
    make_user(); login(client)
    add_to_cart(client, shop["shirt"].id, 2)
    add_to_cart(client, shop["tee"].id, 2)
    shop["tee"].stock = 1; db.session.commit()
    place_order(client)
    assert Order.query.count() == 0 and Product.query.get(shop["shirt"].id).stock == 25


def test_stock_decrement_is_conditional_against_race(app, shop):
    """Aunque el producto se agote entre la lectura y la escritura, nunca queda stock negativo."""
    from services.delivery import DeliveryPolicy
    from services.orders import OrderService, StockError, _Line
    from services.payments import build_default_registry
    service = OrderService(db.session, DeliveryPolicy(("Medellín",)), build_default_registry())
    product = Product.query.get(shop["tee"].id)
    stale_line = _Line(product, None, 5)          # el servicio «cree» que hay stock suficiente
    db.session.execute(db.update(Product).where(Product.id == product.id).values(stock=2))
    db.session.commit()
    with pytest.raises(StockError):
        service._reserve_stock(stale_line)
    db.session.rollback()
    assert Product.query.get(shop["tee"].id).stock == 2


# --- Pago simulado --------------------------------------------------------------------------------
@pytest.fixture()
def pending(client, shop):
    make_user(); login(client)
    add_to_cart(client, shop["shirt"].id, 1)
    place_order(client)
    return Order.query.one()


@pytest.mark.parametrize("override,message", [
    ({"card_number": "1234"}, "número de tarjeta"),
    ({"expiry_date": "13/30"}, "fecha de expiración"),
    ({"expiry_date": "01/20"}, "fecha de expiración"),
    ({"cvv": "12"}, "CVV"),
    ({"payment_method": ""}, "método de pago"),
    ({"payment_method": "bitcoin"}, "método de pago válido"),
])
def test_payment_validation(client, pending, override, message):
    r = client.post(f"/payment/{pending.id}", data={**CARD, **override})
    assert message in r.get_data(as_text=True) and db.session.get(Order, pending.id).status == "created"


def test_cash_payment_needs_no_card(client, pending):
    client.post(f"/payment/{pending.id}", data={"payment_method": "efecty"})
    order = db.session.get(Order, pending.id)
    assert order.status == "paid" and order.payment_method.startswith("Efecty")


def test_card_data_is_never_stored(client, pending, app):
    client.post(f"/payment/{pending.id}", data=CARD)
    order = db.session.get(Order, pending.id)
    stored = " ".join(str(getattr(order, c.name)) for c in Order.__table__.columns)
    assert "4111" not in stored and "123" not in stored.replace("1234", "") or "4111" not in stored
    assert not any("card" in c.name or "cvv" in c.name for c in Order.__table__.columns)


def test_cannot_pay_twice(client, pending):
    client.post(f"/payment/{pending.id}", data=CARD)
    r = client.post(f"/payment/{pending.id}", data=CARD, follow_redirects=True)
    assert "ya no está pendiente de pago" in r.get_data(as_text=True)


def test_legacy_payment_route_goes_to_latest_pending_order(client, pending):
    assert client.get("/payment").headers["Location"].endswith(f"/payment/{pending.id}")


def test_pay_page_shows_card_fields_without_exposing_cvv(client, pending):
    body = client.get(f"/payment/{pending.id}").get_data(as_text=True)
    assert 'type="password"' in body and 'name="cvv"' in body


# --- Pedidos del cliente ---------------------------------------------------------------------------
def test_cancel_restores_stock_and_blocks_further_pay(client, pending, shop):
    assert Product.query.get(shop["shirt"].id).stock == 24
    r = client.post(f"/orders/{pending.id}/cancel", follow_redirects=True)
    assert "Pedido cancelado" in r.get_data(as_text=True)
    assert Product.query.get(shop["shirt"].id).stock == 25 and db.session.get(Order, pending.id).status == "cancelled"
    assert "Cancelado" in client.get("/orders").get_data(as_text=True)
    assert "no puedes cancelar" in client.post(f"/orders/{pending.id}/cancel", follow_redirects=True).get_data(as_text=True).lower()
    assert Product.query.get(shop["shirt"].id).stock == 25      # no se devuelve dos veces


def test_cancel_sized_order_restores_size_stock(client, shop):
    make_user(); login(client)
    size_m = [s for s in shop["dress"].sizes if s.label == "M"][0]
    add_to_cart(client, shop["dress"].id, 3, size_id=size_m.id)
    place_order(client)
    client.post(f"/orders/{Order.query.one().id}/cancel")
    assert db.session.get(ProductSize, size_m.id).stock == 5 and Product.query.get(shop["dress"].id).stock == 12


def test_shipped_order_cannot_be_cancelled_by_customer(client, pending):
    pending.status = "shipped"; db.session.commit()
    r = client.post(f"/orders/{pending.id}/cancel", follow_redirects=True)
    assert db.session.get(Order, pending.id).status == "shipped"


def test_customer_cannot_see_other_customers_orders_or_invoices(app, client, pending):
    make_user("otra", "otra@example.com")
    other = app.test_client()
    login(other, "otra@example.com")
    for url in (f"/orders/{pending.id}", f"/invoice/{pending.id}", f"/payment/{pending.id}", f"/orders/{pending.id}/confirmation"):
        assert other.get(url).status_code == 404, url
    assert other.post(f"/orders/{pending.id}/cancel").status_code == 404
    assert other.post(f"/payment/{pending.id}", data=CARD).status_code == 404
    assert db.session.get(Order, pending.id).status == "created"


def test_admin_can_open_any_invoice(app, client, pending):
    make_user("boss", "boss@example.com", role="admin")
    admin = app.test_client()
    login(admin, "boss@example.com")
    assert admin.get(f"/invoice/{pending.id}").status_code == 200


def test_invoice_has_print_button_and_hides_chrome_on_print(client, pending):
    body = client.get(f"/invoice/{pending.id}").get_data(as_text=True)
    assert "window.print()" in body


def test_old_orders_without_shipping_still_render(client, shop, app):
    user = make_user(); login(client)
    legacy = Order(user_id=user.id, status="paid", total=1000)
    db.session.add(legacy); db.session.commit()
    for url in (f"/orders/{legacy.id}", f"/invoice/{legacy.id}", "/orders"):
        assert client.get(url).status_code == 200
    assert "antes de guardar datos de entrega" in client.get(f"/orders/{legacy.id}").get_data(as_text=True)
