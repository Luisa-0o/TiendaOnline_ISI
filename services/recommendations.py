"""Recomendaciones basadas en las categorías favoritas del usuario."""
from typing import List

from sqlalchemy import select

from models import Product, User


class RecommendationService:
    def __init__(self, session):
        self._session = session

    def for_user(self, user: User, limit: int = 8) -> List[Product]:
        if user is None or not user.is_authenticated or user.is_admin:
            return []
        favorites = user.favorite_categories
        if not favorites:
            return []
        stmt = (select(Product).where(Product.category.in_(favorites), Product.stock > 0)
                .order_by(Product.id.desc()).limit(limit))
        return list(self._session.scalars(stmt))
