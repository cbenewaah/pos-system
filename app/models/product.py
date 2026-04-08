"""
Products sold at the POS (inventory lives in quantity).
"""
from __future__ import annotations

from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, default="General")
    price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    barcode = db.Column(db.String(64), unique=True, nullable=True, index=True)

    sale_items = db.relationship(
        "SaleItem",
        back_populates="product",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Product {self.name!r}>"
