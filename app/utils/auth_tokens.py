"""
Create and validate JWT access tokens (API Bearer auth).

Tokens are signed with the app's SECRET_KEY — keep it private in production.
"""
from __future__ import annotations

import jwt
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from flask import current_app


def create_access_token(user_id: int, role: str, username: str) -> str:
    """Build a short-lived JWT for Authorization: Bearer ..."""
    hours = current_app.config.get("JWT_EXPIRATION_HOURS", 24)
    algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
    secret = current_app.config["SECRET_KEY"]
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=hours),
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """Return payload dict or None if token is invalid/expired."""
    try:
        algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
        secret = current_app.config["SECRET_KEY"]
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError:
        return None
