"""
Customer CRUD and purchase history (links to sales/receipts).
"""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from app.models.user import UserRole
from app.services import customer_service
from app.utils.http_auth import require_auth, roles_required

bp = Blueprint("customers", __name__, url_prefix="/customers")

_STAFF = (UserRole.ADMIN, UserRole.MANAGER)


def _err(msg: str, code: int):
    return jsonify({"error": msg}), code


@bp.get("")
@require_auth
def list_customers():
    """Optional query ``q`` searches name, phone, email."""
    term = request.args.get("q", type=str)
    rows = customer_service.search_customers(term)
    return jsonify({"customers": [customer_service.customer_to_dict(c) for c in rows]})


@bp.post("")
@require_auth
@roles_required(*_STAFF)
def create_customer():
    data = request.get_json(silent=True) or {}
    try:
        c = customer_service.create_customer(data)
    except ValueError as e:
        return _err(str(e), 400)
    return jsonify({"customer": customer_service.customer_to_dict(c)}), 201


@bp.get("/<int:customer_id>")
@require_auth
def get_customer(customer_id: int):
    c = customer_service.get_customer(customer_id)
    if c is None:
        return _err("Customer not found", 404)
    return jsonify({"customer": customer_service.customer_to_dict(c)})


@bp.put("/<int:customer_id>")
@require_auth
@roles_required(*_STAFF)
def put_customer(customer_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _err("Expected JSON object", 400)
    try:
        c = customer_service.update_customer(customer_id, data)
    except LookupError:
        return _err("Customer not found", 404)
    except ValueError as e:
        return _err(str(e), 400)
    return jsonify({"customer": customer_service.customer_to_dict(c)})


@bp.get("/<int:customer_id>/sales")
@require_auth
def customer_sales(customer_id: int):
    """Completed sales for loyalty / history (compact rows)."""
    try:
        sales = customer_service.customer_sales_history(customer_id)
    except LookupError:
        return _err("Customer not found", 404)
    out = []
    for s in sales:
        out.append(
            {
                "sale_id": s.id,
                "date": s.date.isoformat(),
                "total_amount": float(s.total_amount),
                "payment_method": s.payment_method,
            }
        )
    return jsonify({"sales": out})
