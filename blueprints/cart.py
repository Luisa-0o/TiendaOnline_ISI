"""Carrito. Funciona sin sesión (cookie firmada) y con sesión (base de datos)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from forms import EmptyForm
from security import is_safe_url
from services.cart import CartError
from services.factory import get_cart_service

bp = Blueprint("cart", __name__, url_prefix="/cart")


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _back(default_endpoint="cart.view_cart", **values):
    target = request.form.get("next", "")
    if target and is_safe_url(target):
        return redirect(target)
    return redirect(url_for(default_endpoint, **values))


@bp.route("/")
def view_cart():
    view = get_cart_service().view()
    for notice in view.notices:
        flash(notice, "info")
    return render_template("shop/cart.html", view=view, form=EmptyForm())


@bp.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    try:
        get_cart_service().add(product_id, _int(request.form.get("size_id")), _int(request.form.get("quantity"), 1))
    except CartError as exc:
        flash(str(exc), "danger")
        return _back("shop.product_detail", product_id=product_id)
    flash("Agregaste la prenda a tu carrito.", "success")
    return redirect(url_for("cart.view_cart"))


@bp.route("/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    quantity = _int(request.form.get("quantity"))
    if quantity is None:
        flash("Escribe una cantidad válida.", "danger")
        return redirect(url_for("cart.view_cart"))
    try:
        get_cart_service().set_quantity(product_id, _int(request.form.get("size_id")), quantity)
    except CartError as exc:
        flash(str(exc), "danger")
    else:
        flash("Actualizamos tu carrito.", "success")
    return redirect(url_for("cart.view_cart"))


@bp.route("/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    get_cart_service().remove(product_id, _int(request.form.get("size_id")))
    flash("Quitamos la prenda de tu carrito.", "success")
    return redirect(url_for("cart.view_cart"))
