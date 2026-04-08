"""
Sales (transactions) and line items.

price on SaleItem is the unit price at checkout (snapshot; product price may change later).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class SaleStatus:
    """draft = cart / building; completed = paid and inventory deducted."""

    DRAFT = "draft"
    COMPLETED = "completed"


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    status = db.Column(
        db.String(20),
        nullable=False,
        default=SaleStatus.DRAFT,
    )
    # Line sums (before / after discount); total_amount is the amount to pay
    subtotal = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    discount_percent = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    # Quick summary for receipts; detailed rows live in payments (e.g. split tender)
    payment_method = db.Column(db.String(20), nullable=True)

    user = db.relationship("User", back_populates="sales")
    customer = db.relationship("Customer", back_populates="sales")
    items = db.relationship(
        "SaleItem",
        back_populates="sale",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    payments = db.relationship(
        "Payment",
        back_populates="sale",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Sale {self.id} total={self.total_amount}>"


class SaleItem(db.Model):
    __tablename__ = "sales_items"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)

    sale = db.relationship("Sale", back_populates="items")
    product = db.relationship("Product", back_populates="sale_items")

    def __repr__(self) -> str:
        return f"<SaleItem sale={self.sale_id} product={self.product_id} x{self.quantity}>"
