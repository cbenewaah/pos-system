"""
Payments for a sale (cash, mobile money, card).

method values: "cash", "momo", "card" (enforced in services/API in later steps).
"""
from __future__ import annotations

from app.extensions import db


class PaymentMethod:
    """Common payment method codes stored in the database."""

    CASH = "cash"
    MOMO = "momo"
    CARD = "card"


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)

    sale = db.relationship("Sale", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment sale={self.sale_id} {self.method} {self.amount}>"
