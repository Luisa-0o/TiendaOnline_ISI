"""Cuentas: registro, autenticación, preferencias y administración con reglas de seguridad."""
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from models import ROLE_ADMIN, ROLE_USER, ROLES, Cart, CartItem, Order, User


class AccountError(Exception):
    """Error de negocio de cuentas."""


class AccountService:
    def __init__(self, session):
        self._session = session

    def find_by_email(self, email: str) -> Optional[User]:
        return self._session.scalar(select(User).where(func.lower(User.email) == (email or "").strip().lower()))

    def authenticate(self, email: str, password: str) -> Optional[User]:
        user = self.find_by_email(email)
        return user if user and user.check_password(password) else None

    def register(self, username: str, email: str, password: str) -> User:
        """Registro público: SIEMPRE rol «user». Los administradores se crean desde el panel
        (otro admin) o con ``flask create-admin``; nadie obtiene privilegios por registrarse."""
        return self._create(username, email, password, ROLE_USER)

    def change_password(self, user: User, current: str, new: str) -> None:
        if not user.check_password(current):
            raise AccountError("La contraseña actual es incorrecta.")
        user.set_password(new)
        self._session.commit()

    def save_favorites(self, user: User, categories: List[str]) -> None:
        if len(categories) != 2 or len(set(categories)) != 2:
            raise AccountError("Selecciona exactamente 2 categorías distintas.")
        user.fav_category1, user.fav_category2 = categories
        self._session.commit()

    def list_users(self) -> List[User]:
        return list(self._session.scalars(select(User).order_by(User.id)))

    def admin_create(self, username: str, email: str, password: str, role: str) -> User:
        return self._create(username, email, password, self._valid_role(role))

    def admin_update(self, user: User, username: str, email: str, role: str) -> User:
        role = self._valid_role(role)
        if user.is_admin and role != ROLE_ADMIN and self._admin_count() <= 1:
            raise AccountError("No puedes quitar el rol al único administrador de la tienda.")
        user.username, user.email, user.role = username.strip(), email.strip().lower(), role
        self._commit_unique()
        return user

    def admin_delete(self, user: User, acting_admin: User) -> None:
        if user.id == acting_admin.id:
            raise AccountError("No puedes eliminar tu propia cuenta.")
        if user.is_admin and self._admin_count() <= 1:
            raise AccountError("No puedes eliminar al único administrador de la tienda.")
        if self._session.scalar(select(func.count()).select_from(Order).where(Order.user_id == user.id)):
            raise AccountError("Este usuario tiene pedidos registrados y no puede eliminarse.")
        cart = self._session.scalar(select(Cart).where(Cart.user_id == user.id))
        if cart:
            self._session.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
            self._session.delete(cart)
        self._session.delete(user)
        self._session.commit()

    def _create(self, username, email, password, role) -> User:
        user = User(username=username.strip(), email=email.strip().lower(), role=role)
        user.set_password(password)
        self._session.add(user)
        self._commit_unique()
        return user

    def _commit_unique(self):
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            raise AccountError("Ya existe un usuario con ese nombre o correo.") from None

    def _admin_count(self) -> int:
        return self._session.scalar(select(func.count()).select_from(User).where(User.role == ROLE_ADMIN))

    @staticmethod
    def _valid_role(role: str) -> str:
        if role not in ROLES:
            raise AccountError("Rol no válido.")
        return role
