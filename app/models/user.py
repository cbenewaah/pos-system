"""
User accounts and roles (Admin, Manager, Cashier).

Passwords are never stored in plain text — only password_hash (see auth step).
"""
from __future__ import annotations

from app.extensions import db


class UserRole:
    """Allowed role string values (stored in DB as plain strings)."""

    ADMIN = "Admin"
    MANAGER = "Manager"
    CASHIER = "Cashier"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(
        db.String(20),
        nullable=False,
        default=UserRole.CASHIER,
    )

    # One user can create many sales
    sales = db.relationship(
        "Sale",
        back_populates="user",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<User {self.username!r} ({self.role})>"
