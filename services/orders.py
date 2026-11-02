"""Pedidos: creación, pago, cancelación y cambios de estado.

``place_order`` aplica las reglas que NUNCA se delegan al navegador: municipio
permitido, existencia de productos, precios vigentes y existencias suficientes.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from models import Order, OrderItem, Product, ProductSize
from services.cart import CheckoutCart, only_left
from services.delivery import DeliveryPolicy, ShippingData
from services.payments import PaymentGatewayRegistry, PaymentRequest


class OrderError(Exception):
    """Error de negocio de pedidos con mensaje apto para el cliente."""


class EmptyCartError(OrderError):
    def __init__(self):
        super().__init__("Tu carrito está vacío.")


class InvalidShippingError(OrderError):
    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__("Revisa los datos de entrega: " + " ".join(errors.values()))


class StockError(OrderError):
    def __init__(self, issues: List[str]):
        self.issues = issues
        super().__init__("Algunas prendas cambiaron de disponibilidad: " + " ".join(issues))


class OrderStateError(OrderError):
    pass


@dataclass
class _Line:
    product: Product
    size: Optional[ProductSize]
    quantity: int


class OrderService:
    def __init__(self, session, delivery_policy: DeliveryPolicy, gateways: PaymentGatewayRegistry):
        self._session, self._policy, self._gateways = session, delivery_policy, gateways

    def place_order(self, user_id: int, cart: CheckoutCart, shipping: ShippingData) -> Order:
        """Valida todo en el servidor y crea el pedido en una sola transacción."""
        shipping = shipping.normalized()
        errors = self._policy.validate(shipping)
        if errors:
            raise InvalidShippingError(errors)
        cart_lines = cart.lines()
        if not cart_lines:
            raise EmptyCartError()
        try:
            lines = self._resolve_lines(cart_lines)
            order = Order(
                user_id=user_id, status=Order.STATUS_CREATED, total=0.0,
                recipient_name=shipping.recipient_name, phone=shipping.phone,
                municipality=shipping.municipality, address=shipping.address,
                neighborhood=shipping.neighborhood, postal_code=shipping.postal_code or None,
                address_notes=shipping.address_notes or None)
            self._session.add(order)
            self._session.flush()
            total = 0.0
            for line in lines:
                price = line.product.price or 0.0  # precio vigente en la base de datos
                self._reserve_stock(line)
                self._session.add(OrderItem(
                    order_id=order.id, product_id=line.product.id,
                    size_id=line.size.id if line.size else None,
                    size_label=line.size.label if line.size else None,
                    quantity=line.quantity, price=price))
                total += price * line.quantity
            order.total = round(total, 2)
            cart.clear()
            self._session.commit()
            return order
        except (OrderError, SQLAlchemyError):
            self._session.rollback()
            raise

    def _resolve_lines(self, cart_lines) -> List[_Line]:
        ids = sorted({l.product_id for l in cart_lines})
        products = {p.id: p for p in self._session.scalars(select(Product).where(Product.id.in_(ids)))}
        lines, issues = [], []
        for cl in cart_lines:
            product = products.get(cl.product_id)
            if product is None:
                issues.append("Una prenda de tu carrito ya no existe en la tienda.")
                continue
            size = product.get_size(cl.size_id) if cl.size_id else None
            label = f"«{product.name}»" + (f" talla {size.label}" if size else "")
            if product.has_sizes and size is None:
                issues.append(f"{label} requiere elegir una talla válida.")
                continue
            available = product.available_for(size)
            if available <= 0:
                issues.append(f"{label} se agotó.")
            elif cl.quantity > available:
                issues.append(f"{only_left(available)} de {label} y pediste {cl.quantity}.")
            else:
                lines.append(_Line(product, size, cl.quantity))
        if issues:
            raise StockError(issues)
        return lines

    def _reserve_stock(self, line: _Line) -> None:
        """Descuenta con UPDATE condicional: seguro ante compras simultáneas."""
        if line.size is not None:
            done = self._session.execute(
                update(ProductSize).where(ProductSize.id == line.size.id, ProductSize.stock >= line.quantity)
                .values(stock=ProductSize.stock - line.quantity)).rowcount
            if done != 1:
                raise StockError([f"«{line.product.name}» talla {line.size.label} se agotó mientras comprabas."])
            self._session.expire(line.size)
        done = self._session.execute(
            update(Product).where(Product.id == line.product.id, Product.stock >= line.quantity)
            .values(stock=Product.stock - line.quantity)).rowcount
        if done != 1:
            raise StockError([f"«{line.product.name}» se agotó mientras comprabas."])
        self._session.expire(line.product)

    def pay(self, order: Order, method_code: str, details) -> Order:
        if not order.is_payable:
            raise OrderStateError("Este pedido ya no está pendiente de pago.")
        gateway = self._gateways.get(method_code)  # PaymentError si no existe
        result = gateway.charge(PaymentRequest(order.id, order.total or 0.0, details))
        if not result.approved:
            raise OrderError(result.message or "El pago fue rechazado.")
        order.status = Order.STATUS_PAID
        order.payment_method = gateway.label
        self._session.commit()
        return order

    def cancel(self, order: Order) -> Order:
        if not order.is_cancellable:
            raise OrderStateError(f"No puedes cancelar un pedido en estado «{order.status_label}».")
        self._release_stock(order)
        order.status = Order.STATUS_CANCELLED
        self._session.commit()
        return order

    def change_status(self, order: Order, new_status: str) -> Order:
        if new_status not in Order.STATUS_LABELS:
            raise OrderStateError("Estado de pedido no válido.")
        if new_status == order.status:
            return order
        if order.status == Order.STATUS_CANCELLED:
            raise OrderStateError("Un pedido cancelado no puede reactivarse: el inventario ya fue devuelto.")
        if new_status == Order.STATUS_CANCELLED:
            self._release_stock(order)
        order.status = new_status
        self._session.commit()
        return order

    def _release_stock(self, order: Order) -> None:
        for item in order.items:
            if item.size_id:
                size = self._session.get(ProductSize, item.size_id)
                if size is not None:
                    size.stock += item.quantity
            if item.product is not None:
                item.product.stock += item.quantity

    def for_user(self, user_id: int) -> List[Order]:
        return list(self._session.scalars(select(Order).where(Order.user_id == user_id).order_by(Order.id.desc())))

    def latest_payable(self, user_id: int) -> Optional[Order]:
        return self._session.scalars(
            select(Order).where(Order.user_id == user_id, Order.status == Order.STATUS_CREATED)
            .order_by(Order.id.desc()).limit(1)).first()

    def last_shipping(self, user_id: int) -> Optional[ShippingData]:
        """Datos de entrega del último pedido, para no pedirlos de nuevo."""
        o = self._session.scalars(
            select(Order).where(Order.user_id == user_id, Order.municipality.is_not(None))
            .order_by(Order.id.desc()).limit(1)).first()
        if o is None:
            return None
        return ShippingData(o.recipient_name or "", o.phone or "", o.municipality or "", o.address or "",
                            o.neighborhood or "", o.postal_code or "", o.address_notes or "")
