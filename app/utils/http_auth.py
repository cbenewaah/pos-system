"""
HTTP authentication helpers: Bearer JWT and/or Flask-Login session.

Stack decorators with ``@require_auth`` above ``@roles_required(...)`` so the
user is loaded before the role is checked::

    @require_auth
    @roles_required(UserRole.ADMIN)
    def view(...): ...
"""
from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, Union

from flask import Response, g, jsonify, request
from flask_login import current_user

from app.extensions import db
from app.models.user import User
from app.utils.auth_tokens import decode_access_token

F = TypeVar("F", bound=Callable[..., Union[Response, tuple]])


def require_auth(f: F) -> F:
    """
    Require a valid JWT (Authorization: Bearer ...) or Flask-Login session.

    Sets flask.g.current_user to the loaded User on success.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _user_from_bearer_token()
        if user is None and current_user.is_authenticated:
            user = current_user
        if user is None:
            return jsonify({"error": "Authentication required"}), 401
        g.current_user = user
        return f(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def roles_required(*allowed_roles: str) -> Callable[[F], F]:
    """403 unless g.current_user.role is one of allowed_roles (use after @require_auth)."""

    def decorator(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if user is None:
                return jsonify({"error": "Authentication required"}), 401
            if user.role not in allowed_roles:
                return (
                    jsonify(
                        {
                            "error": "Forbidden",
                            "required_roles": list(allowed_roles),
                        }
                    ),
                    403,
                )
            return f(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def _user_from_bearer_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        uid = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    return db.session.get(User, uid)
