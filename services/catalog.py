"""Consulta del catálogo: búsqueda, filtros combinables, orden y paginación.

Cada filtro es una clase con un único método ``apply``. CatalogService solo los
compone: agregar un filtro nuevo (p. ej. por marca) es escribir una clase y añadirla
a ``build_filters`` sin modificar el servicio (Open/Closed).
"""
from dataclasses import dataclass
from typing import Generic, List, Optional, Protocol, TypeVar

from sqlalchemy import and_, func, or_, select

from models import Order, OrderItem, Product, ProductSize, size_sort_key

AVAILABILITY_ALL = "all"
AVAILABILITY_IN_STOCK = "available"
AVAILABILITY_SOLD_OUT = "sold_out"

SORT_OPTIONS = {
    "newest": ("Novedades", lambda: Product.id.desc()),
    "price_asc": ("Precio: menor a mayor", lambda: Product.price.asc()),
    "price_desc": ("Precio: mayor a menor", lambda: Product.price.desc()),
    "name": ("Nombre A-Z", lambda: func.lower(Product.name).asc()),
}
DEFAULT_SORT = "newest"

T = TypeVar("T")


@dataclass(frozen=True)
class Page(Generic[T]):
    items: List[T]
    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.per_page))

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages


def _to_float(value) -> Optional[float]:
    try:
        number = float(str(value).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass(frozen=True)
class CatalogFilters:
    """Parámetros de búsqueda ya saneados (nunca se confía en la query string cruda)."""
    query: str = ""
    category: str = ""
    garment_type: str = ""
    size: str = ""
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    availability: str = AVAILABILITY_ALL
    sort: str = DEFAULT_SORT

    @classmethod
    def from_args(cls, args) -> "CatalogFilters":
        availability = args.get("availability", AVAILABILITY_ALL)
        if availability not in (AVAILABILITY_ALL, AVAILABILITY_IN_STOCK, AVAILABILITY_SOLD_OUT):
            availability = AVAILABILITY_ALL
        sort = args.get("sort", DEFAULT_SORT)
        if sort not in SORT_OPTIONS:
            sort = DEFAULT_SORT
        return cls(
            query=args.get("q", "").strip()[:100],
            category=args.get("category", "").strip(),
            garment_type=args.get("garment_type", "").strip(),
            size=args.get("size", "").strip(),
            min_price=_to_float(args.get("min_price")),
            max_price=_to_float(args.get("max_price")),
            availability=availability,
            sort=sort,
        )

    @property
    def active_count(self) -> int:
        """Filtros activos (sin contar el orden)."""
        simple = sum(bool(v) for v in (self.query, self.category, self.garment_type, self.size))
        prices = (self.min_price is not None) + (self.max_price is not None)
        return simple + prices + (self.availability != AVAILABILITY_ALL)

    def as_params(self, **overrides) -> dict:
        """Parámetros de URL equivalentes, sin vacíos (útil para paginación y chips)."""
        params = {
            "q": self.query, "category": self.category, "garment_type": self.garment_type,
            "size": self.size, "min_price": self._fmt(self.min_price), "max_price": self._fmt(self.max_price),
            "availability": self.availability if self.availability != AVAILABILITY_ALL else "",
            "sort": self.sort if self.sort != DEFAULT_SORT else "",
        }
        params.update(overrides)
        return {k: v for k, v in params.items() if v not in ("", None)}

    @staticmethod
    def _fmt(value):
        return None if value is None else (int(value) if float(value).is_integer() else value)


class CatalogFilter(Protocol):
    def apply(self, stmt): ...


class SearchFilter:
    def __init__(self, text: str):
        self.text = text

    def apply(self, stmt):
        if not self.text:
            return stmt
        pattern = f"%{_escape_like(self.text)}%"
        columns = (Product.name, Product.brand, Product.category, Product.garment_type)
        return stmt.where(or_(*(c.ilike(pattern, escape="\\") for c in columns)))


class CategoryFilter:
    def __init__(self, category: str):
        self.category = category

    def apply(self, stmt):
        return stmt.where(Product.category == self.category) if self.category else stmt


class GarmentTypeFilter:
    def __init__(self, garment_type: str):
        self.garment_type = garment_type

    def apply(self, stmt):
        return stmt.where(Product.garment_type == self.garment_type) if self.garment_type else stmt


class PriceRangeFilter:
    def __init__(self, min_price: Optional[float], max_price: Optional[float]):
        self.min_price, self.max_price = min_price, max_price

    def apply(self, stmt):
        if self.min_price is not None:
            stmt = stmt.where(Product.price >= self.min_price)
        if self.max_price is not None:
            stmt = stmt.where(Product.price <= self.max_price)
        return stmt


class AvailabilityFilter:
    def __init__(self, availability: str):
        self.availability = availability

    def apply(self, stmt):
        if self.availability == AVAILABILITY_IN_STOCK:
            return stmt.where(Product.stock > 0)
        if self.availability == AVAILABILITY_SOLD_OUT:
            return stmt.where(Product.stock <= 0)
        return stmt


class SizeFilter:
    """Productos que tienen esa talla con existencias."""

    def __init__(self, size: str):
        self.size = size

    def apply(self, stmt):
        if not self.size:
            return stmt
        return stmt.where(Product.sizes.any(and_(ProductSize.label == self.size, ProductSize.stock > 0)))


def build_filters(f: CatalogFilters) -> List[CatalogFilter]:
    return [SearchFilter(f.query), CategoryFilter(f.category), GarmentTypeFilter(f.garment_type),
            PriceRangeFilter(f.min_price, f.max_price), AvailabilityFilter(f.availability), SizeFilter(f.size)]


@dataclass(frozen=True)
class CatalogFacets:
    """Valores reales de la base de datos para armar los filtros."""
    categories: List[str]
    garment_types: List[str]
    sizes: List[str]
    min_price: float
    max_price: float


class CatalogService:
    def __init__(self, session, page_size: int = 12):
        self.session = session
        self.page_size = page_size

    def search(self, filters: CatalogFilters, page: int = 1) -> Page[Product]:
        base = select(Product)
        for flt in build_filters(filters):
            base = flt.apply(base)
        total = self.session.scalar(select(func.count()).select_from(base.order_by(None).subquery()))
        pages = max(1, -(-total // self.page_size))
        page = min(max(page, 1), pages)
        stmt = (base.order_by(SORT_OPTIONS[filters.sort][1](), Product.id.desc())
                .limit(self.page_size).offset((page - 1) * self.page_size))
        return Page(items=list(self.session.scalars(stmt)), page=page, per_page=self.page_size, total=total)

    def facets(self) -> CatalogFacets:
        s = self.session
        categories = s.scalars(select(Product.category).where(Product.category.is_not(None), Product.category != "")
                               .distinct().order_by(Product.category)).all()
        types = s.scalars(select(Product.garment_type).where(Product.garment_type.is_not(None), Product.garment_type != "")
                          .distinct().order_by(Product.garment_type)).all()
        sizes = s.scalars(select(ProductSize.label).distinct()).all()
        lo, hi = s.execute(select(func.min(Product.price), func.max(Product.price))).one()
        return CatalogFacets(list(categories), list(types), sorted(sizes, key=size_sort_key), lo or 0, hi or 0)

    def get(self, product_id: int) -> Optional[Product]:
        return self.session.get(Product, product_id)

    def latest(self, limit: int = 8, only_available: bool = True) -> List[Product]:
        stmt = select(Product).order_by(Product.id.desc()).limit(limit)
        if only_available:
            stmt = stmt.where(Product.stock > 0)
        return list(self.session.scalars(stmt))

    def related(self, product: Product, limit: int = 4) -> List[Product]:
        if not product.category:
            return []
        stmt = (select(Product).where(Product.category == product.category, Product.id != product.id, Product.stock > 0)
                .order_by(Product.id.desc()).limit(limit))
        return list(self.session.scalars(stmt))

    def category_cover(self, category: str) -> Optional[Product]:
        stmt = (select(Product).where(Product.category == category, Product.image_filename.is_not(None),
                                      Product.image_filename != "").order_by(Product.id.desc()).limit(1))
        return self.session.scalars(stmt).first()

    def best_sellers(self, limit: int = 4) -> List[Product]:
        """Prendas disponibles con más unidades vendidas (pedidos no cancelados)."""
        stmt = (select(Product).join(OrderItem, OrderItem.product_id == Product.id)
                .join(Order, Order.id == OrderItem.order_id)
                .where(Order.status != Order.STATUS_CANCELLED, Product.stock > 0)
                .group_by(Product.id)
                .order_by(func.sum(OrderItem.quantity).desc(), Product.id.desc()).limit(limit))
        return list(self.session.scalars(stmt))

    def hero_product(self) -> Optional[Product]:
        stmt = (select(Product).where(Product.stock > 0, Product.image_filename.is_not(None), Product.image_filename != "")
                .order_by(Product.id.desc()).limit(1))
        return self.session.scalars(stmt).first()
