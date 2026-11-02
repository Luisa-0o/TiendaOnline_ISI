"""Carrito de compras.

* ``CartStore`` es el contrato de almacenamiento: guarda SOLO identificadores y
  cantidades (producto, talla, unidades). Precios y existencias se leen siempre de
  la base de datos, así que nada que venga del navegador puede alterar un precio.
* ``CookieCartStore`` (visitantes) y ``DatabaseCartStore`` (usuarios con sesión)
  cumplen el mismo contrato y son intercambiables: CartService no sabe cuál usa.
* El carrito NO reserva inventario: las existencias se revalidan al crear el pedido.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Protocol, Tuple

from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import select

from models import Cart, CartItem, Product, ProductSize

LineKey = Tuple[int, Optional[int]]


def units(n: int) -> str:
    """1 -> '1 unidad', 3 -> '3 unidades'."""
    return f"{n} unidad" if n == 1 else f"{n} unidades"


def only_left(n: int) -> str:
    """1 -> 'Solo queda 1 unidad', 3 -> 'Solo quedan 3 unidades'."""
    return f"Solo queda {units(n)}" if n == 1 else f"Solo quedan {units(n)}"


class CartError(Exception):
    """Error de negocio del carrito, con mensaje apto para el cliente."""


@dataclass(frozen=True)
class CartLine:
    product_id: int
    size_id: Optional[int]
    quantity: int

    @property
    def key(self) -> LineKey:
        return (self.product_id, self.size_id)


class CheckoutCart(Protocol):
    """Lo único que OrderService necesita de un carrito (Interface Segregation)."""
    def lines(self) -> List[CartLine]: ...
    def clear(self) -> None: ...


class CartStore(ABC):
    """Contrato de almacenamiento. Ninguna operación hace commit."""

    @abstractmethod
    def lines(self) -> List[CartLine]: ...

    @abstractmethod
    def set_line(self, product_id: int, size_id: Optional[int], quantity: int) -> None: ...

    @abstractmethod
    def remove_line(self, product_id: int, size_id: Optional[int]) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...


class CartCookieCodec:
    """Serializa el carrito en un valor firmado (a prueba de manipulación) con caducidad."""

    def __init__(self, secret_key: str, max_age: int, max_qty: int = 99):
        self._serializer = URLSafeTimedSerializer(secret_key, salt="nevora-cart-v1")
        self._max_age = max_age
        self._max_qty = max_qty

    def encode(self, lines: Iterable[CartLine]) -> str:
        return self._serializer.dumps([[l.product_id, l.size_id or 0, l.quantity] for l in lines])

    def decode(self, raw: Optional[str]) -> List[CartLine]:
        if not raw:
            return []
        try:
            data = self._serializer.loads(raw, max_age=self._max_age)
        except BadSignature:
            return []
        if not isinstance(data, list):
            return []
        result: Dict[LineKey, CartLine] = {}
        for entry in data:
            try:
                pid, sid, qty = (int(x) for x in entry)
            except (TypeError, ValueError):
                continue
            if pid <= 0 or sid < 0 or not (1 <= qty <= self._max_qty):
                continue
            line = CartLine(pid, sid or None, qty)
            result[line.key] = line
        return list(result.values())


class CookieCartStore(CartStore):
    def __init__(self, raw_cookie: Optional[str], codec: CartCookieCodec):
        self._codec = codec
        self._lines: Dict[LineKey, CartLine] = {l.key: l for l in codec.decode(raw_cookie)}
        self.dirty = False

    def lines(self):
        return list(self._lines.values())

    def set_line(self, product_id, size_id, quantity):
        key = (product_id, size_id)
        if quantity <= 0:
            self._lines.pop(key, None)
        else:
            self._lines[key] = CartLine(product_id, size_id, quantity)
        self.dirty = True

    def remove_line(self, product_id, size_id):
        self._lines.pop((product_id, size_id), None)
        self.dirty = True

    def clear(self):
        self._lines.clear()
        self.dirty = True

    def to_cookie_value(self) -> Optional[str]:
        return self._codec.encode(self._lines.values()) if self._lines else None


class DatabaseCartStore(CartStore):
    def __init__(self, session, user_id: int):
        self._session = session
        self._user_id = user_id

    def _cart(self, create: bool = False) -> Optional[Cart]:
        cart = self._session.scalar(select(Cart).where(Cart.user_id == self._user_id))
        if cart is None and create:
            cart = Cart(user_id=self._user_id)
            self._session.add(cart)
            self._session.flush()
        return cart

    def _items(self) -> List[CartItem]:
        cart = self._cart()
        if cart is None:
            return []
        return list(self._session.scalars(select(CartItem).where(CartItem.cart_id == cart.id).order_by(CartItem.id)))

    def lines(self):
        merged: Dict[LineKey, int] = {}
        for item in self._items():  # tolera duplicados heredados de versiones anteriores
            key = (item.product_id, item.size_id)
            merged[key] = merged.get(key, 0) + item.quantity
        return [CartLine(p, s, q) for (p, s), q in merged.items() if q > 0]

    def set_line(self, product_id, size_id, quantity):
        matches = [i for i in self._items() if (i.product_id, i.size_id) == (product_id, size_id)]
        if quantity <= 0:
            for item in matches:
                self._session.delete(item)
        elif matches:
            matches[0].quantity = quantity
            for extra in matches[1:]:
                self._session.delete(extra)
        else:
            cart = self._cart(create=True)
            self._session.add(CartItem(cart_id=cart.id, product_id=product_id, size_id=size_id, quantity=quantity))
        self._session.flush()

    def remove_line(self, product_id, size_id):
        self.set_line(product_id, size_id, 0)

    def clear(self):
        for item in self._items():
            self._session.delete(item)
        self._session.flush()


@dataclass
class CartViewLine:
    product: Product
    size: Optional[ProductSize]
    quantity: int
    available: int
    problem: Optional[str] = None

    @property
    def unit_price(self) -> float:
        return self.product.price or 0.0

    @property
    def subtotal(self) -> float:
        return round(self.unit_price * self.quantity, 2)

    @property
    def size_label(self) -> Optional[str]:
        return self.size.label if self.size else None

    @property
    def max_selectable(self) -> int:
        return max(self.available, 0)


@dataclass
class CartView:
    lines: List[CartViewLine] = field(default_factory=list)
    notices: List[str] = field(default_factory=list)

    @property
    def total(self) -> float:
        return round(sum(l.subtotal for l in self.lines), 2)

    @property
    def count(self) -> int:
        return sum(l.quantity for l in self.lines)

    @property
    def has_problems(self) -> bool:
        return any(l.problem for l in self.lines)

    @property
    def is_empty(self) -> bool:
        return not self.lines


class CartService:
    """Casos de uso del carrito, independientes de dónde se almacene."""

    def __init__(self, store: CartStore, session, commit: Callable[[], None],
                 max_qty_per_line: int = 20, max_lines: int = 50):
        self._store, self._session, self._commit = store, session, commit
        self._max_qty, self._max_lines = max_qty_per_line, max_lines

    def count(self) -> int:
        return sum(l.quantity for l in self._store.lines())

    def view(self) -> CartView:
        """Vista con precios y existencias actuales; limpia líneas de productos eliminados."""
        lines = self._store.lines()
        products = self._load_products({l.product_id for l in lines})
        view, stale = CartView(), []
        for line in lines:
            product = products.get(line.product_id)
            if product is None:
                stale.append(line)
                continue
            size = product.get_size(line.size_id) if line.size_id else None
            view.lines.append(CartViewLine(product, size, line.quantity, product.available_for(size),
                                           self._problem(product, size, line.quantity)))
        if stale:
            for line in stale:
                self._store.remove_line(line.product_id, line.size_id)
            self._commit()
            view.notices.append("Quitamos del carrito prendas que ya no están disponibles en la tienda.")
        return view

    def add(self, product_id: int, size_id: Optional[int], quantity: int) -> CartLine:
        if quantity < 1:
            raise CartError("La cantidad debe ser de al menos 1 unidad.")
        product, size = self._resolve(product_id, size_id)
        sid = size.id if size else None
        current = self._current_quantity(product.id, sid)
        if current == 0 and len(self._store.lines()) >= self._max_lines:
            raise CartError("Tu carrito alcanzó el máximo de prendas distintas. Finaliza la compra o elimina alguna.")
        self._ensure_quantity_allowed(product, size, current + quantity, already_in_cart=current)
        self._store.set_line(product.id, sid, current + quantity)
        self._commit()
        return CartLine(product.id, sid, current + quantity)

    def set_quantity(self, product_id: int, size_id: Optional[int], quantity: int) -> None:
        if quantity <= 0:
            self.remove(product_id, size_id)
            return
        product, size = self._resolve(product_id, size_id)
        self._ensure_quantity_allowed(product, size, quantity, already_in_cart=0)
        self._store.set_line(product.id, size.id if size else None, quantity)
        self._commit()

    def remove(self, product_id: int, size_id: Optional[int]) -> None:
        self._store.remove_line(product_id, size_id)
        self._commit()

    def absorb(self, lines: Iterable[CartLine]) -> List[str]:
        """Fusiona líneas de otro carrito (el de visitante) sin duplicar ni superar existencias."""
        notices: List[str] = []
        for incoming in lines:
            product = self._session.get(Product, incoming.product_id)
            size = product.get_size(incoming.size_id) if product and incoming.size_id else None
            if product is None or (product.has_sizes and size is None):
                notices.append("Una prenda de tu carrito anterior ya no está disponible y no se agregó.")
                continue
            allowed = min(product.available_for(size), self._max_qty)
            current = self._current_quantity(product.id, size.id if size else None)
            if allowed <= 0:
                notices.append(f"«{product.name}» está agotado y no se agregó a tu carrito.")
                continue
            merged = min(current + incoming.quantity, allowed)
            if merged < current + incoming.quantity:
                notices.append(f"Ajustamos las unidades de «{product.name}» a las existencias disponibles ({merged}).")
            self._store.set_line(product.id, size.id if size else None, merged)
        self._commit()
        return notices

    # -- internos --
    def _load_products(self, ids) -> Dict[int, Product]:
        if not ids:
            return {}
        return {p.id: p for p in self._session.scalars(select(Product).where(Product.id.in_(ids)))}

    def _current_quantity(self, product_id, size_id) -> int:
        return next((l.quantity for l in self._store.lines() if l.key == (product_id, size_id)), 0)

    def _resolve(self, product_id: int, size_id: Optional[int]):
        product = self._session.get(Product, product_id)
        if product is None:
            raise CartError("Esta prenda ya no está disponible.")
        if product.has_sizes:
            size = product.get_size(size_id) if size_id else None
            if size is None:
                raise CartError("Selecciona una talla antes de agregar la prenda al carrito.")
            return product, size
        return product, None

    def _ensure_quantity_allowed(self, product, size, wanted: int, already_in_cart: int) -> None:
        available = product.available_for(size)
        label = f"«{product.name}»" + (f" talla {size.label}" if size else "")
        if available <= 0:
            raise CartError(f"{label} está agotado.")
        if wanted > available:
            if already_in_cart:
                raise CartError(f"{only_left(available)} de {label} y ya tienes {already_in_cart} en el carrito.")
            raise CartError(f"{only_left(available)} de {label}.")
        if wanted > self._max_qty:
            raise CartError(f"Puedes llevar hasta {units(self._max_qty)} de {label} por pedido.")

    @staticmethod
    def _problem(product, size, quantity) -> Optional[str]:
        if product.has_sizes and size is None:
            return "Esta prenda ahora requiere elegir talla. Elimínala y agrégala de nuevo."
        available = product.available_for(size)
        if available <= 0:
            return "Agotado. Elimínala del carrito para continuar."
        if quantity > available:
            return f"{only_left(available)}. Ajusta la cantidad."
        return None
