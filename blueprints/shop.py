"""Tienda pública: inicio, catálogo y detalle de producto. No requiere sesión."""
from flask import Blueprint, abort, render_template, request
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from forms import EmptyForm
from services.catalog import SORT_OPTIONS, CatalogFilters
from services.factory import get_catalog_service, get_recommendation_service

bp = Blueprint("shop", __name__)


@bp.route("/")
def home():
    catalog = get_catalog_service()
    categories = [{"name": n, "cover": catalog.category_cover(n)} for n in catalog.facets().categories]
    return render_template(
        "shop/home.html", hero=catalog.hero_product(), new_arrivals=catalog.latest(8),
        best_sellers=catalog.best_sellers(4), categories=categories,
        recommended=get_recommendation_service().for_user(current_user, 4))


@bp.route("/catalogo")
def catalogo():
    catalog = get_catalog_service()
    filters = CatalogFilters.from_args(request.args)
    page = catalog.search(filters, request.args.get("page", 1, type=int) or 1)
    return render_template(
        "shop/catalog.html", page=page, filters=filters, facets=catalog.facets(),
        sort_options={key: label for key, (label, _) in SORT_OPTIONS.items()},
        recommended=get_recommendation_service().for_user(current_user, 4) if not filters.active_count else [])


@bp.route("/producto/<int:product_id>")
def product_detail(product_id):
    catalog = get_catalog_service()
    product = catalog.get(product_id)
    if product is None:
        abort(404)
    return render_template("shop/product_detail.html", product=product, related=catalog.related(product), form=EmptyForm())


@bp.route("/test-db")
def test_db():
    """Comprobación rápida de conexión a la base de datos (se conserva de la versión anterior)."""
    try:
        db.session.execute(text("SELECT 1"))
        return "✅ Conexión exitosa a la base de datos"
    except SQLAlchemyError:
        db.session.rollback()
        return "❌ Error al conectar a la base de datos", 500
