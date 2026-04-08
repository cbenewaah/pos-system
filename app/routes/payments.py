"""
Payment listing by sale (rows are also embedded in GET /sales/<id>).
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify

from app.models.payment import Payment
from app.services import payment_service, sales_service
from app.utils.http_auth import require_auth

bp = Blueprint("payments", __name__, url_prefix="/payments")


@bp.get("/sale/<int:sale_id>")
@require_auth
def list_payments_for_sale(sale_id: int):
    """All recorded payment lines for a sale (same owner as the sale)."""
    sale = sales_service.get_sale_by_id(sale_id)
    if sale is None:
        return jsonify({"error": "Sale not found"}), 404
    if sale.user_id != g.current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    rows = sale.payments.order_by(Payment.id).all()
    return jsonify({"payments": [payment_service.payment_to_dict(p) for p in rows]})
