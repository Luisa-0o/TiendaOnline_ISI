"""Indicadores del panel de administración (calculados desde la base de datos)."""
from dataclasses import dataclass
from typing import Dict, List

from sqlalchemy import func, select

from models import Order, Product, User


@dataclass
class DashboardSummary:
    products: int
    users: int
    orders: int
    revenue: float
    orders_by_status: Dict[str, int]
    low_stock: List[Product]
    recent_orders: List[Order]


class DashboardService:
    REVENUE_STATUSES = (Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED)

    def __init__(self, session, low_stock_threshold: int = 5):
        self._session, self._threshold = session, low_stock_threshold

    def summary(self) -> DashboardSummary:
        s = self._session
        by_status = dict(s.execute(select(Order.status, func.count()).group_by(Order.status)).all())
        revenue = s.scalar(select(func.coalesce(func.sum(Order.total), 0.0)).where(Order.status.in_(self.REVENUE_STATUSES)))
        return DashboardSummary(
            products=s.scalar(select(func.count()).select_from(Product)),
            users=s.scalar(select(func.count()).select_from(User)),
            orders=s.scalar(select(func.count()).select_from(Order)),
            revenue=float(revenue or 0),
            orders_by_status=by_status,
            low_stock=list(s.scalars(select(Product).where(Product.stock <= self._threshold)
                                     .order_by(Product.stock, Product.id).limit(8))),
            recent_orders=list(s.scalars(select(Order).order_by(Order.id.desc()).limit(6))),
        )
