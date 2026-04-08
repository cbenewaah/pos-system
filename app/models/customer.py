"""
Customers and loyalty points.
"""
from __future__ import annotations

from app.extensions import db


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    phone = db.Column(db.String(32), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(500), nullable=True)
    loyalty_points = db.Column(db.Integer, nullable=False, default=0)

    sales = db.relationship(
        "Sale",
        back_populates="customer",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Customer {self.name!r}>"
