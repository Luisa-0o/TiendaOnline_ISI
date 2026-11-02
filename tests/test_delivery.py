"""Regla de negocio: solo se entrega en Medellín, Bello y Envigado (frontend, backend y servicio)."""
import pytest

from conftest import VALID_SHIPPING, add_to_cart, login, make_user, place_order
from models import Order, Product
from services.delivery import DeliveryPolicy, ShippingData

POLICY = DeliveryPolicy(("Medellín", "Bello", "Envigado"))


def ship(**over):
    return ShippingData(**{**VALID_SHIPPING, **over})


# --- Política (unitarias) -------------------------------------------------------------------
@pytest.mark.parametrize("town", ["Medellín", "Bello", "Envigado"])
def test_policy_accepts_allowed(town):
    assert POLICY.validate(ship(municipality=town)) == {}


@pytest.mark.parametrize("town", ["Itagüí", "Sabaneta", "Rionegro", "Bogotá", "Cali", "medellín", "MEDELLIN",
                                  "Medellin", " Bello x", "Medellín; DROP TABLE orders", "<script>", "Envigado Antioquia"])
def test_policy_rejects_everything_else(town):
    errors = POLICY.validate(ship(municipality=town))
    assert "municipality" in errors and "Medellín, Bello y Envigado" in errors["municipality"]


def test_policy_requires_municipality():
    assert "Selecciona el municipio" in POLICY.validate(ship(municipality=""))["municipality"]


def test_postal_code_is_not_used_to_decide_municipality():
    # código postal de Bogotá con municipio permitido: válido; municipio no permitido con CP de Medellín: inválido
    assert POLICY.validate(ship(municipality="Bello", postal_code="110111")) == {}
    assert "municipality" in POLICY.validate(ship(municipality="Bogotá", postal_code="050021"))


@pytest.mark.parametrize("field,value", [("recipient_name", ""), ("recipient_name", "A"), ("phone", "12345"),
                                         ("phone", "2001234567"), ("phone", "abcdefghij"), ("address", "Cra"),
                                         ("neighborhood", ""), ("postal_code", "12")])
def test_policy_required_fields(field, value):
    assert field in POLICY.validate(ship(**{field: value}))


def test_policy_normalizes_phone_and_optional_fields():
    assert POLICY.validate(ship(phone="+57 300 123 4567", postal_code="", address_notes="")) == {}


# --- Integración: el formulario de compra ---------------------------------------------------------
@pytest.fixture()
def ready(client, shop):
    make_user()
    login(client)
    add_to_cart(client, shop["shirt"].id, 2)
    return client


@pytest.mark.parametrize("town", ["Medellín", "Bello", "Envigado"])
def test_checkout_accepts_each_allowed_municipality(ready, town):
    r = place_order(ready, {**VALID_SHIPPING, "municipality": town})
    assert r.status_code == 302 and "/payment/" in r.headers["Location"]
    assert Order.query.one().municipality == town


@pytest.mark.parametrize("town", ["Itagüí", "Sabaneta", "Bogotá", "medellín", "Rionegro"])
def test_checkout_rejects_other_municipalities_and_creates_no_order(ready, shop, town):
    r = place_order(ready, {**VALID_SHIPPING, "municipality": town})
    assert r.status_code == 200
    assert "Solo entregamos en Medellín, Bello y Envigado" in r.get_data(as_text=True)
    assert Order.query.count() == 0
    assert Product.query.get(shop["shirt"].id).stock == 25      # no se descontó inventario
    assert "Camisa Oxford" in ready.get("/cart/").get_data(as_text=True)    # el carrito sigue intacto


def test_checkout_rejects_missing_municipality(ready):
    data = {k: v for k, v in VALID_SHIPPING.items() if k != "municipality"}
    r = place_order(ready, data)
    assert "Selecciona el municipio" in r.get_data(as_text=True) and Order.query.count() == 0


def test_manual_post_with_forbidden_municipality_is_rejected_by_backend(ready):
    """Petición «hecha a mano» con curl/Postman: no pasa por la lista desplegable."""
    r = ready.post("/checkout", data={**VALID_SHIPPING, "municipality": "Cartagena"},
                   headers={"User-Agent": "curl/8.0"})
    assert r.status_code == 200 and Order.query.count() == 0


def test_service_layer_rejects_independently_of_form(app, shop):
    """Defensa en profundidad: aunque se llame al servicio sin pasar por el formulario."""
    from extensions import db
    from services.cart import CartCookieCodec, CookieCartStore
    from services.orders import InvalidShippingError, OrderService
    from services.payments import build_default_registry
    user = make_user()
    store = CookieCartStore(None, CartCookieCodec("k", 3600))
    store.set_line(shop["shirt"].id, None, 1)
    service = OrderService(db.session, POLICY, build_default_registry())
    with pytest.raises(InvalidShippingError):
        service.place_order(user.id, store, ship(municipality="Bogotá"))
    assert Order.query.count() == 0 and len(store.lines()) == 1


def test_error_messages_are_next_to_fields_and_accessible(ready):
    r = place_order(ready, {**VALID_SHIPPING, "municipality": "Cali", "phone": "123"})
    body = r.get_data(as_text=True)
    assert 'aria-invalid="true"' in body and 'role="alert"' in body and "celular colombiano" in body


def test_form_lists_only_the_three_municipalities_in_a_select(ready):
    body = ready.get("/checkout").get_data(as_text=True)
    assert "<select" in body and 'name="municipality"' in body
    for town in ("Medellín", "Bello", "Envigado"):
        assert f'value="{town}"' in body
    assert 'value="Bogotá"' not in body


def test_restriction_does_not_apply_to_browsing_or_cart(client, shop):
    assert client.get("/catalogo").status_code == 200
    assert add_to_cart(client, shop["shirt"].id).status_code == 302


def test_shipping_data_is_saved_with_the_order_and_prefilled_next_time(ready):
    place_order(ready)
    order = Order.query.one()
    assert (order.recipient_name, order.phone, order.municipality, order.neighborhood, order.postal_code,
            order.address_notes) == ("Ana Gómez", "3001234567", "Medellín", "El Poblado", "050021", "Torre 2, apto 301")
    add_to_cart(ready, Product.query.first().id, 1)
    body = ready.get("/checkout").get_data(as_text=True)
    assert 'value="Ana Gómez"' in body and "selected" in body      # no repite datos
