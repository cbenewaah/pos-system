"""
Authentication business logic — registration and password verification.
"""
from __future__ import annotations

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.user import User, UserRole


def register_user(username: str, password: str) -> User:
    """
    Create a new user. First user in the database becomes Admin (easy bootstrap);
    everyone else defaults to Cashier.
    """
    username = (username or "").strip()
    if not username:
        raise ValueError("Username is required")
    min_len = current_app.config.get("PASSWORD_MIN_LENGTH", 8)
    if not password or len(password) < min_len:
        raise ValueError(f"Password must be at least {min_len} characters")

    if User.query.filter_by(username=username).first():
        raise ValueError("Username already taken")

    # First account is Admin so you can manage the system without manual DB edits.
    role = UserRole.ADMIN if User.query.count() == 0 else UserRole.CASHIER

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role,
    )
    db.session.add(user)
    db.session.commit()
    return user


def verify_credentials(username: str, password: str) -> User | None:
    """Return User if username/password match; otherwise None."""
    username = (username or "").strip()
    if not username or not password:
        return None
    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return None
    return user


def user_to_public_dict(user: User) -> dict:
    """Safe user fields for JSON responses (no password hash)."""
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }
