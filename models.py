"""Modelos de datos de Névora Moda!

Los modelos describen estructura y reglas simples de cada entidad.
La lógica de negocio (carrito, pedidos, pagos...) vive en el paquete services/.
"""
from flask import url_for
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

ROLE_USER = "user"
ROLE_ADMIN = "admin"
ROLES = (ROLE_USER, ROLE_ADMIN)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), default=ROLE_USER, nullable=False)
    fav_category1 = db.Column(db.String(50))
    fav_category2 = db.Column(db.String(50))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def favorite_categories(self):
        return [c for c in (self.fav_category1, self.fav_category2) if c]

    def __repr__(self):
        return f"<User {self.username}>"


_SIZE_ORDER = ("XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL")


def size_sort_key(label):
    """Ordena tallas de ropa (XS<S<M...) y numéricas (36<38<40) de forma natural."""
    upper = label.upper()
    if upper in _SIZE_ORDER:
        return (0, _SIZE_ORDER.index(upper), "")
    if upper.isdigit():
        return (1, int(upper), "")
    return (2, 0, upper)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    brand = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    # Existencias totales; si el producto maneja tallas es la suma de las de cada talla.
    stock = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    garment_type = db.Column(db.String(80))  # Camiseta, Jean, Blusa...
    image_filename = db.Column(db.String(255))

    sizes = db.relationship("ProductSize", back_populates="product",
                            cascade="all, delete-orphan", lazy="selectin")

    def image_url(self):
        if self.image_filename:
            return url_for("static", filename=f"uploads/{self.image_filename}")
        return url_for("static", filename="no_image.png")

    @property
    def has_image(self):
        return bool(self.image_filename)

    @property
    def has_sizes(self):
        return bool(self.sizes)

    @property
    def ordered_sizes(self):
        return sorted(self.sizes, key=lambda s: size_sort_key(s.label))

    @property
    def is_available(self):
        return (self.stock or 0) > 0

    def get_size(self, size_id):
        return next((s for s in self.sizes if s.id == size_id), None)

    def available_for(self, size):
        """Unidades disponibles del producto (o de una talla concreta)."""
        if self.has_sizes:
            return (size.stock or 0) if size is not None else 0
        return self.stock or 0

    def __repr__(self):
        return f"<Product {self.name}>"


class ProductSize(db.Model):
    """Talla de un producto con sus propias existencias."""
    __tablename__ = "product_sizes"
    __table_args__ = (db.UniqueConstraint("product_id", "label", name="uq_product_sizes_product_id_label"),)

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    label = db.Column(db.String(20), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)

    product = db.relationship("Product", back_populates="sizes")

    def __repr__(self):
        return f"<ProductSize {self.label} stock={self.stock}>"


class Cart(db.Model):
    """Carrito de un usuario con sesión (los visitantes usan una cookie firmada)."""
    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user = db.relationship("User", backref=db.backref("cart", uselist=False))


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size_id = db.Column(db.Integer, db.ForeignKey("product_sizes.id"), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    cart = db.relationship("Cart", backref=db.backref("items", cascade="all, delete-orphan"))
    product = db.relationship("Product")
    size = db.relationship("ProductSize")

    def line_total(self):
        return (self.product.price or 0) * (self.quantity or 0)


class Order(db.Model):
    __tablename__ = "orders"

    STATUS_CREATED = "created"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_LABELS = {
        STATUS_CREATED: "Pendiente de pago",
        STATUS_PAID: "Pagado",
        STATUS_SHIPPED: "Enviado",
        STATUS_DELIVERED: "Entregado",
        STATUS_CANCELLED: "Cancelado",
    }
    CANCELLABLE_STATUSES = (STATUS_CREATED, STATUS_PAID)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(50), default=STATUS_CREATED)
    total = db.Column(db.Float, default=0.0)

    # Datos de entrega (nullable: los pedidos anteriores a esta versión no los tienen)
    recipient_name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    municipality = db.Column(db.String(50))
    address = db.Column(db.String(200))
    neighborhood = db.Column(db.String(100))
    postal_code = db.Column(db.String(10))
    address_notes = db.Column(db.String(300))

    # Solo el nombre del método; nunca datos de tarjeta.
    payment_method = db.Column(db.String(30))

    user = db.relationship("User", backref=db.backref("orders", order_by="Order.id.desc()"))

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status or "Pendiente")

    @property
    def is_cancellable(self):
        return self.status in self.CANCELLABLE_STATUSES

    @property
    def is_payable(self):
        return self.status == self.STATUS_CREATED

    @property
    def has_shipping_info(self):
        return bool(self.municipality)


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    size_id = db.Column(db.Integer, db.ForeignKey("product_sizes.id", ondelete="SET NULL"), nullable=True)
    size_label = db.Column(db.String(20))  # copia de la talla al momento de comprar
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)  # precio unitario al momento del pedido

    order = db.relationship("Order", backref=db.backref("items", cascade="all, delete-orphan"))
    product = db.relationship("Product")
    size = db.relationship("ProductSize")

    def line_total(self):
        return (self.price or 0) * (self.quantity or 0)
