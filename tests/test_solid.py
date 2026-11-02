"""Pruebas que demuestran los principios SOLID del diseño: extender sin modificar, sustituir, depender de abstracciones."""
from conftest import add_to_cart, login, make_product, make_user, place_order
from extensions import db
from models import Order, Product
from services.catalog import CatalogFilters, CatalogService, build_filters
from services.delivery import DeliveryPolicy, ShippingData
from services.payments import (PaymentError, PaymentGateway, PaymentGatewayRegistry, PaymentRequest,
                               PaymentResult, SimulatedCashGateway, build_default_registry)
from services.orders import OrderService


# -- O: nuevo método de pago sin tocar OrderService ni las rutas ------------------------------------------
class PseGateway(PaymentGateway):
    code, label = "pse", "PSE (banco)"

    def charge(self, request: PaymentRequest) -> PaymentResult:
        return PaymentResult(approved=request.amount < 1_000_000, message="")


def test_open_closed_new_payment_method_without_modifying_services(app, client, shop):
    registry = app.extensions["nevora_payment_registry"]
    registry.register(PseGateway())
    make_user(); login(client)
    add_to_cart(client, shop["shirt"].id, 1); place_order(client)
    order = Order.query.one()
    assert "PSE (banco)" in client.get(f"/payment/{order.id}").get_data(as_text=True)
    client.post(f"/payment/{order.id}", data={"payment_method": "pse"})
    assert db.session.get(Order, order.id).status == "paid" and order.payment_method == "PSE (banco)"


def test_open_closed_gateway_can_reject(app, shop):
    registry = PaymentGatewayRegistry()
    registry.register(PseGateway())
    user = make_user()
    from services.cart import CartCookieCodec, CookieCartStore
    store = CookieCartStore(None, CartCookieCodec("k", 60)); store.set_line(shop["jean"].sizes[0].product_id, shop["jean"].sizes[0].id, 3)
    service = OrderService(db.session, DeliveryPolicy(("Medellín",)), registry)
    order = service.place_order(user.id, store, ShippingData("Ana Gómez", "3001234567", "Medellín", "Calle 1 # 2-3", "Centro"))
    order.total = 2_000_000
    import pytest
    with pytest.raises(Exception):
        service.pay(order, "pse", {})
    assert order.status == "created"


# -- O: nuevo filtro del catálogo = una clase, sin cambiar CatalogService --------------------------------
class BrandFilter:
    def __init__(self, brand): self.brand = brand
    def apply(self, stmt): return stmt.where(Product.brand == self.brand)


def test_open_closed_catalog_accepts_new_filter(app, shop):
    make_product("Zapato X", 100000, 3, "Zapatos", "Zapato", brand="StepUp")
    from sqlalchemy import select
    stmt = select(Product)
    for f in build_filters(CatalogFilters()) + [BrandFilter("StepUp")]:
        stmt = f.apply(stmt)
    assert [p.name for p in db.session.scalars(stmt)] == ["Zapato X"]


# -- L: cualquier implementación de PaymentGateway es intercambiable --------------------------------------
def test_liskov_all_gateways_honour_the_contract():
    registry = build_default_registry()
    request = PaymentRequest(order_id=1, amount=10.0, details={"card_number": "4111111111111111", "expiry_date": "12/40", "cvv": "123"})
    for gateway in registry.all():
        assert isinstance(gateway, PaymentGateway)
        result = gateway.charge(request)             # mismo uso para todos, sin isinstance ni casos especiales
        assert isinstance(result, PaymentResult) and result.approved


def test_liskov_invalid_data_always_raises_payment_error_never_other_exceptions():
    registry = build_default_registry()
    for gateway in registry.all():
        if gateway.requires_card:
            try:
                gateway.charge(PaymentRequest(1, 1.0, {}))
            except PaymentError:
                pass
            else:
                raise AssertionError("debía lanzar PaymentError")


# -- I: OrderService solo necesita lines() y clear() --------------------------------------------------------
def test_interface_segregation_order_service_needs_only_lines_and_clear(app, shop):
    class MinimalCart:       # no implementa set_line/remove_line: no los necesita
        def __init__(self, lines): self._l = lines; self.cleared = False
        def lines(self): return self._l
        def clear(self): self.cleared = True
    from services.cart import CartLine
    user = make_user()
    cart = MinimalCart([CartLine(shop["shirt"].id, None, 2)])
    service = OrderService(db.session, DeliveryPolicy(("Bello",)), build_default_registry())
    order = service.place_order(user.id, cart, ShippingData("Ana Gómez", "3001234567", "Bello", "Calle 1 # 2-3", "Centro"))
    assert cart.cleared and order.total == 2 * 89900


# -- D: la política de entrega es configurable sin tocar el servicio ----------------------------------------
def test_dependency_inversion_delivery_policy_is_injected(app, shop):
    from services.cart import CartCookieCodec, CartLine, CookieCartStore
    user = make_user()
    store = CookieCartStore(None, CartCookieCodec("k", 60)); store.set_line(shop["shirt"].id, None, 1)
    only_sabaneta = DeliveryPolicy(("Sabaneta",))
    service = OrderService(db.session, only_sabaneta, build_default_registry())
    order = service.place_order(user.id, store, ShippingData("Ana Gómez", "3001234567", "Sabaneta", "Calle 1 # 2-3", "Centro"))
    assert order.municipality == "Sabaneta"


def test_dependency_inversion_services_do_not_import_flask():
    import importlib, inspect
    for name in ("services.cart", "services.orders", "services.catalog", "services.delivery", "services.payments",
                 "services.products", "services.users", "services.reports", "services.recommendations", "services.images"):
        source = inspect.getsource(importlib.import_module(name))
        assert "from flask" not in source and "import flask" not in source, name
