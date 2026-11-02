"""Composition root: aquí (y solo aquí) se decide qué implementación concreta recibe cada servicio.

Las rutas piden servicios a estas funciones y los servicios reciben sus dependencias
por constructor, de modo que la lógica de negocio no conoce Flask, cookies ni la
forma de almacenar el carrito (Dependency Inversion).
"""
from typing import List, Optional

from flask import current_app, g, request
from flask_login import current_user

from extensions import db
from services.cart import CartCookieCodec, CartService, CookieCartStore, DatabaseCartStore
from services.catalog import CatalogService
from services.delivery import DeliveryPolicy
from services.images import ImageStorage
from services.orders import OrderService
from services.payments import PaymentGatewayRegistry, build_default_registry
from services.products import ProductService
from services.recommendations import RecommendationService
from services.reports import DashboardService
from services.users import AccountService


def _cfg(key):
    return current_app.config[key]


def get_delivery_policy() -> DeliveryPolicy:
    return DeliveryPolicy(_cfg("DELIVERY_MUNICIPALITIES"))


def get_payment_registry() -> PaymentGatewayRegistry:
    return current_app.extensions["nevora_payment_registry"]


def get_catalog_service() -> CatalogService:
    return CatalogService(db.session, page_size=_cfg("CATALOG_PAGE_SIZE"))


def get_order_service() -> OrderService:
    return OrderService(db.session, get_delivery_policy(), get_payment_registry())


def get_product_service() -> ProductService:
    return ProductService(db.session, ImageStorage(_cfg("UPLOAD_FOLDER")))


def get_account_service() -> AccountService:
    return AccountService(db.session)


def get_recommendation_service() -> RecommendationService:
    return RecommendationService(db.session)


def get_dashboard_service() -> DashboardService:
    return DashboardService(db.session, _cfg("LOW_STOCK_THRESHOLD"))


def _codec() -> CartCookieCodec:
    return CartCookieCodec(_cfg("SECRET_KEY"), _cfg("CART_COOKIE_MAX_AGE"), _cfg("CART_MAX_QTY_PER_LINE"))


def get_guest_cart_store() -> CookieCartStore:
    """Carrito del visitante (cookie firmada); una sola instancia por petición."""
    if "guest_cart_store" not in g:
        g.guest_cart_store = CookieCartStore(request.cookies.get(_cfg("CART_COOKIE_NAME")), _codec())
    return g.guest_cart_store


def _cart_service(store, commit) -> CartService:
    return CartService(store, db.session, commit, max_qty_per_line=_cfg("CART_MAX_QTY_PER_LINE"),
                       max_lines=_cfg("CART_MAX_LINES"))


def get_database_cart_store(user_id: int) -> DatabaseCartStore:
    return DatabaseCartStore(db.session, user_id)


def get_cart_service() -> CartService:
    """Base de datos si hay usuario con sesión; cookie si es visitante."""
    if "cart_service" not in g:
        if current_user.is_authenticated:
            g.cart_service = _cart_service(get_database_cart_store(current_user.id), db.session.commit)
        else:
            g.cart_service = _cart_service(get_guest_cart_store(), lambda: None)
    return g.cart_service


def get_user_cart_store() -> Optional[DatabaseCartStore]:
    return get_database_cart_store(current_user.id) if current_user.is_authenticated else None


def merge_guest_cart_into(user) -> List[str]:
    """Pasa el carrito del visitante al de ``user`` sin duplicar líneas; devuelve avisos."""
    guest = get_guest_cart_store()
    lines = guest.lines()
    if not lines:
        return []
    notices = _cart_service(get_database_cart_store(user.id), db.session.commit).absorb(lines)
    guest.clear()  # la cookie se elimina en apply_cart_cookie
    g.pop("cart_service", None)  # el servicio en caché pertenecía al visitante
    return notices


def apply_cart_cookie(response):
    """after_request: escribe o borra la cookie del carrito si cambió en esta petición."""
    store = g.get("guest_cart_store")
    if store is not None and store.dirty:
        name = _cfg("CART_COOKIE_NAME")
        value = store.to_cookie_value()
        if value is None:
            response.delete_cookie(name)
        else:
            response.set_cookie(name, value, max_age=_cfg("CART_COOKIE_MAX_AGE"), httponly=True,
                                samesite="Lax", secure=_cfg("SESSION_COOKIE_SECURE"))
    return response


def init_payment_registry(app) -> None:
    app.extensions["nevora_payment_registry"] = build_default_registry()
