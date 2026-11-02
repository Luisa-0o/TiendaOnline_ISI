"""Panel de administración. TODAS las rutas exigen rol admin (before_request del blueprint)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from extensions import db
from forms import AdminUserForm, EmptyForm, OrderStatusForm, ProductForm
from models import Order, Product, User
from security import admin_required
from services.factory import get_account_service, get_dashboard_service, get_order_service, get_product_service
from services.orders import OrderError
from services.products import ProductData, ProductError, format_sizes
from services.users import AccountError

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@admin_required
def _require_admin():
    """Protege el blueprint completo: una ruta nueva no puede quedar abierta por olvido."""


@bp.route("/")
def dashboard():
    return render_template("admin/dashboard.html", summary=get_dashboard_service().summary())


@bp.route("/products")
def products():
    return render_template("admin/products.html", products=get_product_service().list_all(), form=EmptyForm())


def _product_data(form: ProductForm) -> ProductData:
    return ProductData(name=form.name.data.strip(), brand=form.brand.data.strip(), price=form.price.data,
                       category=form.category.data, garment_type=form.garment_type.data,
                       description=form.description.data, stock=form.stock.data, sizes=form.parsed_sizes)


@bp.route("/products/create", methods=["GET", "POST"])
def create_product():
    form = ProductForm()
    if form.validate_on_submit():
        try:
            get_product_service().create(_product_data(form), form.image.data or None)
        except ProductError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Producto creado correctamente.", "success")
            return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", form=form, action="Crear", product=None)


@bp.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    product = db.get_or_404(Product, product_id)
    form = ProductForm(obj=product)
    if request.method == "GET":
        form.sizes.data = format_sizes(product)
    if form.validate_on_submit():
        try:
            get_product_service().update(product, _product_data(form), form.image.data or None)
        except ProductError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        else:
            flash("Producto actualizado.", "success")
            return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", form=form, action="Editar", product=product)


@bp.route("/products/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    try:
        get_product_service().delete(product)
    except ProductError as exc:
        flash(str(exc), "warning")
    else:
        flash("Producto eliminado correctamente.", "success")
    return redirect(url_for("admin.products"))


@bp.route("/users")
def users():
    return render_template("admin/users.html", users=get_account_service().list_users(), form=EmptyForm())


@bp.route("/users/add", methods=["GET", "POST"])
def add_user():
    form = AdminUserForm()
    if form.validate_on_submit():
        try:
            get_account_service().admin_create(form.username.data, form.email.data, form.password.data, form.role.data)
        except AccountError as exc:
            flash(str(exc), "danger")
        else:
            flash("Usuario agregado correctamente.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, action="Agregar", user=None)


@bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = db.get_or_404(User, user_id)
    form = AdminUserForm(obj=user, require_password=False)
    if form.validate_on_submit():
        try:
            get_account_service().admin_update(user, form.username.data, form.email.data, form.role.data)
            if form.password.data:
                user.set_password(form.password.data)
                db.session.commit()
        except AccountError as exc:
            flash(str(exc), "danger")
        else:
            flash("Usuario actualizado correctamente.", "success")
            return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, action="Editar", user=user)


@bp.route("/users/delete/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    try:
        get_account_service().admin_delete(user, current_user)
    except AccountError as exc:
        flash(str(exc), "danger")
    else:
        flash("Usuario eliminado correctamente.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/orders")
def orders():
    status = request.args.get("status", "")
    stmt = select(Order).order_by(Order.id.desc())
    if status in Order.STATUS_LABELS:
        stmt = stmt.where(Order.status == status)
    return render_template("admin/orders.html", orders=db.session.scalars(stmt).all(), status=status,
                           Order_labels=Order.STATUS_LABELS)


@bp.route("/orders/<int:order_id>")
def order_detail(order_id):
    order = db.get_or_404(Order, order_id)
    form = OrderStatusForm(status=order.status)
    form.status.choices = list(Order.STATUS_LABELS.items())
    return render_template("admin/order_detail.html", order=order, form=form)


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id):
    order = db.get_or_404(Order, order_id)
    try:
        get_order_service().change_status(order, request.form.get("status", "").strip())
    except OrderError as exc:
        flash(str(exc), "danger")
    else:
        flash(f"Estado del pedido actualizado a «{order.status_label}».", "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))
