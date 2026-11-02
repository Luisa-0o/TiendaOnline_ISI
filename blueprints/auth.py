"""Registro, inicio/cierre de sesión, cuenta del usuario y categorías favoritas."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from forms import ChangePasswordForm, EmptyForm, FavoritesForm, LoginForm, RegisterForm
from security import is_safe_url
from services.factory import get_account_service, get_catalog_service, merge_guest_cart_into
from services.users import AccountError

bp = Blueprint("auth", __name__)


def _next_url():
    target = request.args.get("next") or request.form.get("next") or ""
    return target if target and is_safe_url(target) else ""


def _after_login(user, default_endpoint):
    """Fusiona el carrito del visitante con el del usuario y continúa donde estaba."""
    for notice in merge_guest_cart_into(user):
        flash(notice, "info")
    return redirect(_next_url() or url_for(default_endpoint))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(_next_url() or url_for("shop.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = get_account_service().register(form.username.data, form.email.data, form.password.data)
        except AccountError as exc:
            flash(str(exc), "danger")
        else:
            login_user(user)
            flash("¡Bienvenida/o a Névora Moda! Tu cuenta fue creada.", "success")
            return _after_login(user, "auth.select_favs")  # si venía de comprar, continúa la compra
    return render_template("auth/register.html", form=form, next_url=_next_url())


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_next_url() or url_for("shop.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = get_account_service().authenticate(form.email.data, form.password.data)
        if user:
            login_user(user)
            flash("Iniciaste sesión correctamente.", "success")
            return _after_login(user, "admin.dashboard" if user.is_admin else "shop.home")
        flash("Correo o contraseña incorrectos.", "danger")
    return render_template("auth/login.html", form=form, next_url=_next_url())


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Cerraste sesión.", "info")
    return redirect(url_for("shop.home"))


@bp.route("/cuenta")
@login_required
def account():
    return render_template("auth/account.html", form=EmptyForm())


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        try:
            get_account_service().change_password(current_user, form.current_password.data, form.new_password.data)
        except AccountError as exc:
            form.current_password.errors = list(form.current_password.errors) + [str(exc)]
        else:
            flash("Contraseña actualizada correctamente.", "success")
            return redirect(url_for("auth.account"))
    return render_template("auth/change_password.html", form=form)


@bp.route("/select-favs", methods=["GET", "POST"])
@login_required
def select_favs():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    categories = get_catalog_service().facets().categories
    form = FavoritesForm()
    if form.validate_on_submit():
        selected = [c for c in request.form.getlist("categories") if c in categories]
        try:
            get_account_service().save_favorites(current_user, selected)
        except AccountError as exc:
            flash(str(exc), "warning")
        else:
            flash("Preferencias guardadas.", "success")
            return redirect(url_for("shop.catalogo"))
    return render_template("auth/select_favs.html", form=form, categories=categories,
                           current=current_user.favorite_categories)
