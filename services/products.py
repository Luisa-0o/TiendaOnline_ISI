"""Administración de productos: crear, editar y eliminar (incluye tallas y foto)."""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from sqlalchemy import delete, func, select, update

from models import CartItem, OrderItem, Product, ProductSize, size_sort_key
from services.images import ImageStorage

_SIZE_LABEL_RE = re.compile(r"^[A-Za-z0-9ÁÉÍÓÚÑáéíóúñ./-]{1,20}$")


class ProductError(Exception):
    """Error de negocio al administrar productos."""


@dataclass
class ProductData:
    name: str
    brand: str
    price: float
    category: Optional[str] = None
    garment_type: Optional[str] = None
    description: Optional[str] = None
    stock: Optional[int] = None  # solo si el producto NO maneja tallas
    sizes: List[Tuple[str, int]] = field(default_factory=list)


def parse_sizes(text: str) -> List[Tuple[str, int]]:
    """«S:10, M:15» -> [("S", 10), ("M", 15)]. ValueError con mensaje claro si no es válido."""
    result, seen = [], set()
    for raw in re.split(r"[,\n;]+", text or ""):
        raw = raw.strip()
        if not raw:
            continue
        label, sep, qty = raw.partition(":")
        label, qty = label.strip().upper(), qty.strip()
        if not sep or not _SIZE_LABEL_RE.match(label):
            raise ValueError(f"«{raw}» no es válido. Usa el formato TALLA:CANTIDAD, por ejemplo S:10, M:15.")
        if not qty.isdigit():
            raise ValueError(f"La cantidad de la talla {label} debe ser un número entero mayor o igual a 0.")
        if label in seen:
            raise ValueError(f"La talla {label} está repetida.")
        seen.add(label)
        result.append((label, int(qty)))
    return sorted(result, key=lambda item: size_sort_key(item[0]))


def format_sizes(product: Product) -> str:
    return ", ".join(f"{s.label}:{s.stock}" for s in product.ordered_sizes)


class ProductService:
    def __init__(self, session, images: ImageStorage):
        self._session, self._images = session, images

    def list_all(self) -> List[Product]:
        return list(self._session.scalars(select(Product).order_by(Product.id.desc())))

    def create(self, data: ProductData, image_file=None) -> Product:
        product = Product(name=data.name, brand=data.brand, price=data.price, stock=0)
        self._apply(product, data)
        self._session.add(product)
        if image_file:
            product.image_filename = self._save_image(image_file)
        self._session.commit()
        return product

    def update(self, product: Product, data: ProductData, image_file=None) -> Product:
        old_image = None
        product.name, product.brand, product.price = data.name, data.brand, data.price
        self._apply(product, data)
        if image_file:
            old_image = product.image_filename
            product.image_filename = self._save_image(image_file)
        self._session.commit()
        if old_image:
            self._delete_image_if_unused(old_image)
        return product

    def delete(self, product: Product) -> None:
        has_orders = self._session.scalar(
            select(func.count()).select_from(OrderItem).where(OrderItem.product_id == product.id))
        if has_orders:
            raise ProductError("No puedes eliminar este producto porque tiene pedidos registrados. "
                               "Puedes dejar sus existencias en 0 para que figure como agotado.")
        image = product.image_filename
        self._session.execute(delete(CartItem).where(CartItem.product_id == product.id))
        self._session.delete(product)
        self._session.commit()
        self._delete_image_if_unused(image)

    def _apply(self, product: Product, data: ProductData) -> None:
        product.category = (data.category or "").strip() or None
        product.garment_type = (data.garment_type or "").strip() or None
        product.description = (data.description or "").strip() or None
        wanted = dict(data.sizes)
        current = {s.label: s for s in product.sizes}
        for label, size in list(current.items()):
            if label not in wanted:
                self._remove_size(product, size)
        for label, stock in wanted.items():
            if label in current:
                current[label].stock = stock
            else:
                product.sizes.append(ProductSize(label=label, stock=stock))
        product.stock = sum(wanted.values()) if wanted else (data.stock or 0)

    def _remove_size(self, product: Product, size: ProductSize) -> None:
        if size.id is not None:
            self._session.execute(delete(CartItem).where(CartItem.size_id == size.id))
            self._session.execute(update(OrderItem).where(OrderItem.size_id == size.id).values(size_id=None))
        product.sizes.remove(size)

    def _save_image(self, image_file) -> str:
        try:
            return self._images.save(image_file)
        except ValueError as exc:
            raise ProductError(str(exc)) from exc
        except OSError as exc:
            raise ProductError("No se pudo guardar la imagen. Inténtalo de nuevo.") from exc

    def _delete_image_if_unused(self, filename: Optional[str]) -> None:
        if not filename:
            return
        used = self._session.scalar(select(func.count()).select_from(Product).where(Product.image_filename == filename))
        if not used:
            self._images.delete(filename)
