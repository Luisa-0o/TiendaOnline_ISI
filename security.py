"""Seguridad: control de acceso por rol y redirecciones seguras."""
from functools import wraps
from urllib.parse import urljoin, urlparse

from flask import abort, request
from flask_login import current_user

from extensions import login_manager


def is_safe_url(target: str) -> bool:
    """True si ``target`` apunta al mismo sitio (evita «open redirect»)."""
    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ("http", "https") and ref.netloc == test.netloc


def admin_required(view):
    """Solo administradores. Sin sesión → login; usuario normal → 403."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper
