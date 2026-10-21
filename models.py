from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for 

db = SQLAlchemy()


# MODELO DE USUARIO


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), default='user')  # puede ser 'user' o 'admin'
    # Preferencias del usuario: dos categorías favoritas (opcional)
    fav_category1 = db.Column(db.String(50))
    fav_category2 = db.Column(db.String(50))

    def set_password(self, password):
        """Guarda la contraseña encriptada"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica si la contraseña es correcta"""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """Devuelve True si el usuario es administrador"""
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'



# MODELO DE PRODUCTO (PRENDA)


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)      # nombre de la prenda
    brand = db.Column(db.String(120), nullable=False)     # marca de la prenda
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    # Categoría de la prenda: Camisas, Pantalones, Zapatos, Accesorios, etc. (opcional)
    category = db.Column(db.String(50))
    image_filename = db.Column(db.String(255))  # nombre de archivo de la foto de la prenda

    def image_url(self):
        """Devuelve la URL de la imagen o una por defecto"""
        if self.image_filename:
            return url_for('static', filename=f'uploads/{self.image_filename}')
        return url_for('static', filename='no_image.png')

    def __repr__(self):
        return f'<Product {self.name}>'



# MODELO DE CARRITO


class Cart(db.Model):
    __tablename__ = 'carts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    user = db.relationship('User', backref=db.backref('cart', uselist=False))

    def __repr__(self):
        return f'<Cart user_id={self.user_id}>'



# MODELO DE ITEMS DEL CARRITO


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    cart = db.relationship('Cart', backref=db.backref('items', cascade='all, delete-orphan'))
    product = db.relationship('Product')

    def line_total(self):
        """Subtotal del ítem"""
        return (self.product.price or 0) * (self.quantity or 0)

    def __repr__(self):
        return f'<CartItem product_id={self.product_id} qty={self.quantity}>'



# MODELOS DE PEDIDO


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(50), default='created')
    total = db.Column(db.Float, default=0.0)

    user = db.relationship('User', backref=db.backref('orders', order_by='Order.id.desc()'))

    def __repr__(self):
        return f'<Order id={self.id} user_id={self.user_id} total={self.total}>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)  # precio unitario en el momento del pedido

    order = db.relationship('Order', backref=db.backref('items', cascade='all, delete-orphan'))
    product = db.relationship('Product')

    def line_total(self):
        """Subtotal del ítem del pedido"""
        return (self.price or 0) * (self.quantity or 0)

    def __repr__(self):
        return f'<OrderItem product_id={self.product_id} qty={self.quantity} price={self.price}>'
