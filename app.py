from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, User, Product, Cart, CartItem, Order, OrderItem
from forms import RegisterForm, LoginForm, ChangePasswordForm, ProductForm
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from urllib.parse import urlparse, urljoin
from sqlalchemy.exc import SQLAlchemyError
from flask_wtf import CSRFProtect
import os
import logging
from functools import wraps
from datetime import datetime

# --- Configuración inicial ---
load_dotenv()
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Crear tablas si no existen
with app.app_context():
    db.create_all()


# --- Seguridad para URLs ---
def is_safe_url(target):
    """Verifica que la URL sea interna a la aplicación."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


# --- Cargar usuario ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- Decorador para admin ---
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Primero inicia sesión.', 'warning')
            return redirect(url_for('login'))
        if not getattr(current_user, 'is_admin', False) and getattr(current_user, 'role', 'user') != 'admin':
            flash('Acceso denegado. Solo administradores.', 'danger')
            return redirect(url_for('index'))
        return fn(*args, **kwargs)
    return wrapper


# --- Rutas principales ---
@app.route('/')
def index():
    return render_template('profile.html', user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        if User.query.count() == 0:
            user.role = 'admin'  # Primer usuario será admin
        db.session.add(user)
        db.session.commit()
        # Loguear al usuario automáticamente y pedir que seleccione sus categorías favoritas
        login_user(user)
        flash('Registro exitoso. Por favor selecciona 2 categorías favoritas.', 'success')
        return redirect(url_for('select_favs'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Has ingresado correctamente.', 'success')
            return redirect(url_for('index'))
        flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Contraseña actual incorrecta.', 'danger')
            return render_template('change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Contraseña actualizada correctamente.', 'success')
        return redirect(url_for('index'))
    return render_template('change_password.html', form=form)


# --- Panel de administrador ---
@app.route('/admin')
@login_required
@admin_required
def admin():
    users = User.query.all()
    return render_template('admin.html', users=users)


# --- CRUD Productos ---
@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template('admin_products.html', products=products)


@app.route('/admin/products/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_product():
    form = ProductForm()
    if form.validate_on_submit():
        filename = None
        if form.image.data:
            try:
                f = form.image.data
                filename = secure_filename(f.filename)
                upload_folder = os.path.join('static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                f.save(os.path.join(upload_folder, filename))
            except OSError as e:
                app.logger.error(f"Error al guardar la imagen: {e}")
                flash("Error al guardar la imagen.", "danger")

        product = Product(
            name=form.name.data,
            brand=form.brand.data,
            category=form.category.data,
            price=form.price.data,
            stock=form.stock.data,
            description=form.description.data,
            image_filename=filename
        )
        db.session.add(product)
        db.session.commit()
        flash('Producto creado correctamente.', 'success')
        return redirect(url_for('admin_products'))
    return render_template('edit_product.html', form=form, action='Crear')


@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    if form.validate_on_submit():
        if form.image.data:
            try:
                f = form.image.data
                filename = secure_filename(f.filename)
                upload_folder = os.path.join('static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                f.save(os.path.join(upload_folder, filename))
                product.image_filename = filename
            except OSError as e:
                app.logger.error(f"Error al actualizar la imagen: {e}")
                flash("Error al actualizar la imagen.", "danger")

        product.name = form.name.data
        product.brand = form.brand.data
        product.category = form.category.data
        product.price = form.price.data
        product.stock = form.stock.data
        product.description = form.description.data
        db.session.commit()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('admin_products'))
    return render_template('edit_product.html', form=form, action='Editar', product=product)


@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    existing_orders = OrderItem.query.filter_by(product_id=product.id).first()
    if existing_orders:
        flash("⚠️ No puedes eliminar este producto porque tiene pedidos registrados.", "warning")
        return redirect(url_for('admin_products'))

    db.session.delete(product)
    db.session.commit()
    flash("✅ Producto eliminado correctamente.", "success")
    return redirect(url_for('admin_products'))


# --- CRUD Usuarios (ADMIN) ---
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'user')

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('✅ Usuario agregado correctamente.', 'success')
        return redirect(url_for('admin_users'))
    return render_template('add_user.html')


@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        user.role = request.form['role']
        db.session.commit()
        flash('✅ Usuario actualizado correctamente.', 'success')
        return redirect(url_for('admin_users'))
    return render_template('edit_user.html', user=user)


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.id == user.id:
        flash("❌ No puedes eliminarte a ti mismo.", "danger")
        return redirect(url_for('admin_users'))

    db.session.delete(user)
    db.session.commit()
    flash('🗑️ Usuario eliminado correctamente.', 'success')
    return redirect(url_for('admin_users'))


# --- Catálogo ---
@app.route('/catalogo')
@login_required
def catalogo():
    query = request.args.get('q', '').strip()
    selected_category = request.args.get('category', '').strip()

    products_q = Product.query
    if query:
        products_q = products_q.filter(
            (Product.name.ilike(f'%{query}%')) |
            (Product.brand.ilike(f'%{query}%'))
        )
    if selected_category:
        products_q = products_q.filter(Product.category == selected_category)

    products = products_q.order_by(Product.id.desc()).all()

    # Obtener lista de categorías existentes (no nulas)
    categories = [c[0] for c in db.session.query(Product.category).filter(Product.category != None).distinct().order_by(Product.category).all()]

    # Recomendaciones basadas en las 2 categorías favoritas del usuario (solo para usuarios normales)
    recommended_products = []
    if current_user.is_authenticated and not getattr(current_user, 'is_admin', False):
        fav1 = getattr(current_user, 'fav_category1', None)
        fav2 = getattr(current_user, 'fav_category2', None)
        favs = [c for c in (fav1, fav2) if c]
        if favs:
            recommended_products = Product.query.filter(Product.category.in_(favs)).order_by(Product.id.desc()).limit(8).all()

    return render_template('catalogo.html', products=products, query=query, categories=categories, selected_category=selected_category, recommended_products=recommended_products)


@app.route('/select-favs', methods=['GET', 'POST'])
@login_required
def select_favs():
    # Obtener categorías disponibles
    categories = [c[0] for c in db.session.query(Product.category).filter(Product.category != None).distinct().order_by(Product.category).all()]

    # Si es admin, no necesita seleccionar preferencias
    if current_user.is_authenticated and getattr(current_user, 'is_admin', False):
        return redirect(url_for('admin'))

    if request.method == 'POST':
        selected = request.form.getlist('categories')
        # Aceptar exactamente 2
        if len(selected) != 2:
            flash('Por favor selecciona exactamente 2 categorías.', 'warning')
            return render_template('select_favs.html', categories=categories)

        current_user.fav_category1 = selected[0]
        current_user.fav_category2 = selected[1]
        db.session.commit()
        flash('✅ Preferencias guardadas.', 'success')
        return redirect(url_for('catalogo'))

    return render_template('select_favs.html', categories=categories)


# --------------------------
# RUTAS DE CARRITO Y PEDIDOS
# --------------------------

@app.route('/cart')
@login_required
def view_cart():
    cart = current_user.cart
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()
    items = cart.items
    total = sum(item.line_total() for item in items)
    return render_template('cart.html', cart=cart, items=items, total=total)


@app.route('/cart/add/<int:product_id>', methods=['GET', 'POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    qty = int(request.form.get('quantity', 1)) if request.method == 'POST' else int(request.args.get('quantity', 1))

    if qty <= 0:
        flash('Cantidad inválida.', 'warning')
        return redirect(url_for('catalogo'))

    if product.stock < qty:
        flash('No hay suficiente stock disponible.', 'danger')
        return redirect(url_for('catalogo'))

    cart = current_user.cart
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if item:
        if product.stock < item.quantity + qty:
            flash('No hay suficiente stock para aumentar la cantidad.', 'danger')
            return redirect(url_for('catalogo'))
        item.quantity += qty
    else:
        item = CartItem(cart_id=cart.id, product_id=product.id, quantity=qty)
        db.session.add(item)

    db.session.commit()
    flash(f'✅ Añadido {qty} x "{product.name}" al carrito.', 'success')
    return redirect(url_for('catalogo'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart = current_user.cart
    if not cart:
        flash("No tienes un carrito activo.", "warning")
        return redirect(url_for('catalogo'))

    item = next((i for i in cart.items if i.id == item_id), None)
    if not item:
        flash("El producto no se encontró en tu carrito.", "warning")
        return redirect(url_for('view_cart'))

    if item.quantity > 1:
        item.quantity -= 1
        flash(f"Se eliminó una unidad de '{item.product.name}'.", "info")
    else:
        db.session.delete(item)
        flash(f"'{item.product.name}' fue eliminado del carrito.", "success")

    db.session.commit()
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['POST', 'GET'])
@login_required
def checkout():
    cart = current_user.cart
    if not cart or len(cart.items) == 0:
        flash('El carrito está vacío.', 'warning')
        return redirect(url_for('catalogo'))

    # Validar stock
    for item in cart.items:
        if item.product.stock < item.quantity:
            flash(f'No hay suficiente stock para "{item.product.name}".', 'danger')
            return redirect(url_for('view_cart'))

    # Crear pedido
    try:
        order = Order(user_id=current_user.id, status='created', total=0.0)
        db.session.add(order)
        db.session.flush()

        total = 0.0
        for item in cart.items:
            item.product.stock -= item.quantity
            price = item.product.price or 0.0
            order_item = OrderItem(order_id=order.id, product_id=item.product_id, quantity=item.quantity, price=price)
            db.session.add(order_item)
            total += price * item.quantity
            db.session.delete(item)

        order.total = total
        db.session.commit()
        flash('✅ Pedido creado correctamente.', 'success')
        return redirect(url_for('payment'))

    
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Error al crear el pedido")
        flash('Ocurrió un error creando el pedido.', 'danger')
        return redirect(url_for('view_cart'))

    


@app.route('/orders')
@login_required
def view_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).all()
    return render_template('orders.html', orders=orders)


@app.route('/orders/<int:order_id>')
@login_required
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('view_orders'))
    return render_template('order_detail.html', order=order)


@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Permite al usuario cancelar su pedido"""
    order = Order.query.get_or_404(order_id)

    # Verificar que el pedido pertenezca al usuario
    if order.user_id != current_user.id:
        flash('Acceso no permitido.', 'danger')
        return redirect(url_for('view_orders'))

    # Permitir cancelación solo en ciertos estados
    if order.status not in ['created', 'paid']:
        flash(f'No puedes cancelar un pedido en estado "{order.status}".', 'warning')
        return redirect(url_for('view_order', order_id=order_id))

    # Restaurar el stock de los productos
    for item in order.items:
        item.product.stock += item.quantity

    # Cambiar estado a cancelado
    order.status = 'cancelled'
    db.session.commit()

    flash('✅ Pedido cancelado correctamente. El stock ha sido restaurado.', 'success')
    return redirect(url_for('view_order', order_id=order_id))


# --- RUTAS DE ADMIN PARA GESTIONAR PEDIDOS DE USUARIOS ---
@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    """Ver todos los pedidos de usuarios no-admin"""
    # Obtener todos los usuarios que NO son admins
    non_admin_users = User.query.filter_by(role='user').all()
    user_ids = [user.id for user in non_admin_users]
    
    # Obtener todos los pedidos de esos usuarios
    orders = Order.query.filter(Order.user_id.in_(user_ids)).order_by(Order.id.desc()).all()
    
    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/orders/<int:order_id>')
@login_required
@admin_required
def admin_view_order(order_id):
    """Ver detalles de un pedido de usuario (solo admin)"""
    order = Order.query.get_or_404(order_id)
    
    # Verificar que el pedido sea de un usuario no-admin
    if order.user.is_admin:
        flash('No puedes ver pedidos de admins.', 'danger')
        return redirect(url_for('admin_orders'))
    
    return render_template('order_detail.html', order=order)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
@admin_required
def admin_update_order_status(order_id):
    """Actualizar el estado de un pedido de usuario"""
    order = Order.query.get_or_404(order_id)
    
    # Verificar que el pedido sea de un usuario no-admin
    if order.user.is_admin:
        flash('No puedes editar pedidos de admins.', 'danger')
        return redirect(url_for('admin_orders'))
    
    new_status = request.form.get('status', '').strip()
    valid_statuses = ['created', 'paid', 'shipped', 'delivered', 'cancelled']
    
    if new_status not in valid_statuses:
        flash(f'Estado inválido. Debe ser uno de: {", ".join(valid_statuses)}', 'danger')
        return redirect(url_for('admin_view_order', order_id=order_id))
    
    order.status = new_status
    db.session.commit()
    
    flash(f'✅ Estado del pedido actualizado a "{new_status}".', 'success')
    return redirect(url_for('admin_view_order', order_id=order_id))


# --- Prueba conexión BD ---
@app.route('/test-db')
def test_db():
    try:
        db.session.execute("SELECT 1")
        return "✅ Conexión exitosa a la base de datos"
    except SQLAlchemyError as e:
        app.logger.error(f"Error de base de datos: {e}")
        return "❌ Error al conectar a la base de datos"
    except SystemExit as e:
        app.logger.critical("SystemExit detectado, relanzando.")
        raise e
    except BaseException as e:
        app.logger.exception("Error inesperado crítico.")
        raise e
    

# --- Proceder con el pago ---
# ---------------------- PÁGINA DE PAGO ----------------------
@app.route('/payment', methods=['GET', 'POST'])
@login_required

def payment():
    # Buscar el último pedido del usuario en estado 'created'
    order = Order.query.filter_by(user_id=current_user.id).order_by(Order.id.desc()).filter(Order.status == 'created').first()

    if request.method == 'POST':
        request.form.get('payment_method')
        request.form.get('card_number')
        request.form.get('expiry_date')
        request.form.get('cvv')

        # Marcar el pedido como pagado
        if order:
            order.status = 'paid'
            db.session.commit()
        flash('✅ Pago procesado correctamente. ¡Gracias por tu compra!', 'success')
        return redirect(url_for('catalogo'))  # O una página de confirmación

    return render_template('payment.html', order=order)


# --- VER FACTURA ---
@app.route('/invoice/<int:order_id>')
@login_required
def view_invoice(order_id):
    """Muestra la factura del pedido"""
    order = Order.query.get_or_404(order_id)
    
    # Verificar que el pedido pertenezca al usuario actual o que sea admin
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Acceso restringido.', 'danger')
        return redirect(url_for('view_orders'))
    
    return render_template('invoice.html', order=order, now=datetime.now())


# --- Ejecutar aplicación ---
if __name__ == '__main__':
    app.run(debug=False)


