"""Finalizar compra (con sesión), pago simulado, pedidos del cliente y facturas."""
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from forms import EmptyForm, PaymentForm, ShippingForm
from models import Order
from services.factory import get_cart_service, get_order_service, get_payment_registry, get_user_cart_store
from services.orders import EmptyCartError, InvalidShippingError, OrderError, StockError
from services.payments import PaymentError

bp = Blueprint("checkout", __name__)


def _own_order_or_404(order_id: int) -> Order:
    order = db.session.get(Order, order_id)
    if order is None or order.user_id != current_user.id:
        abort(404)
    return order


@bp.route("/checkout", methods=["GET", "POST"])
@login_required  # la autenticación solo se exige aquí, no al navegar ni al armar el carrito
def checkout():
    view = get_cart_service().view()
    for notice in view.notices:
        flash(notice, "info")
    if view.is_empty:
        flash("Tu carrito está vacío. Agrega prendas para continuar.", "warning")
        return redirect(url_for("shop.catalogo"))
    if view.has_problems:
        flash("Antes de pagar, corrige las prendas marcadas en tu carrito.", "warning")
        return redirect(url_for("cart.view_cart"))

    orders = get_order_service()
    form = ShippingForm()
    if request.method == "GET":
        previous = orders.last_shipping(current_user.id)
        if previous:
            form.fill_from(previous)  # no obliga a repetir datos

    if form.validate_on_submit():
        try:
            order = orders.place_order(current_user.id, get_user_cart_store(), form.to_shipping_data())
        except InvalidShippingError as exc:  # defensa en profundidad: el servicio valida otra vez
            for field, message in exc.errors.items():
                getattr(form, field).errors = list(getattr(form, field).errors) + [message]
        except StockError as exc:
            for issue in exc.issues:
                flash(issue, "danger")
            flash("Ajusta tu carrito y vuelve a intentarlo.", "warning")
            return redirect(url_for("cart.view_cart"))
        except EmptyCartError:
            flash("Tu carrito está vacío.", "warning")
            return redirect(url_for("shop.catalogo"))
        except SQLAlchemyError:
            current_app.logger.exception("Error al crear el pedido")
            flash("Ocurrió un error creando el pedido. Tu carrito sigue intacto; inténtalo de nuevo.", "danger")
        else:
            flash("Pedido creado. Ahora elige cómo pagar.", "success")
            return redirect(url_for("checkout.payment", order_id=order.id))
    return render_template("shop/checkout.html", view=view, form=form)


@bp.route("/payment")
@login_required
def payment_latest():
    """Compatibilidad con la ruta anterior: lleva al último pedido pendiente de pago."""
    order = get_order_service().latest_payable(current_user.id)
    if order is None:
        flash("No tienes pedidos pendientes de pago.", "info")
        return redirect(url_for("checkout.view_orders"))
    return redirect(url_for("checkout.payment", order_id=order.id))


@bp.route("/payment/<int:order_id>", methods=["GET", "POST"])
@login_required
def payment(order_id):
    order = _own_order_or_404(order_id)
    if not order.is_payable:
        flash("Este pedido ya no está pendiente de pago.", "info")
        return redirect(url_for("checkout.view_order", order_id=order.id))
    form = PaymentForm(get_payment_registry())
    if form.validate_on_submit():
        try:
            get_order_service().pay(order, form.payment_method.data, form.details())
        except PaymentError as exc:
            flash(str(exc), "danger")
        except OrderError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("checkout.view_order", order_id=order.id))
        else:
            return redirect(url_for("checkout.confirmation", order_id=order.id))
    return render_template("shop/payment.html", order=order, form=form,
                           card_methods=[g.code for g in get_payment_registry().all() if g.requires_card])


@bp.route("/orders/<int:order_id>/confirmation")
@login_required
def confirmation(order_id):
    return render_template("shop/confirmation.html", order=_own_order_or_404(order_id))


@bp.route("/orders")
@login_required
def view_orders():
    return render_template("shop/orders.html", orders=get_order_service().for_user(current_user.id))


@bp.route("/orders/<int:order_id>")
@login_required
def view_order(order_id):
    return render_template("shop/order_detail.html", order=_own_order_or_404(order_id), form=EmptyForm())


@bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = _own_order_or_404(order_id)
    try:
        get_order_service().cancel(order)
    except OrderError as exc:
        flash(str(exc), "warning")
    else:
        flash("Pedido cancelado. Las existencias fueron devueltas a la tienda.", "success")
    return redirect(url_for("checkout.view_order", order_id=order.id))


@bp.route("/invoice/<int:order_id>")
@login_required
def view_invoice(order_id):
    order = db.session.get(Order, order_id)
    if order is None or (order.user_id != current_user.id and not current_user.is_admin):
        abort(404)
    return render_template("shop/invoice.html", order=order, now=datetime.now())
