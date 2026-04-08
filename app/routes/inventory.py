"""
Inventory API — low-stock list and manual stock adjustment.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models.user import UserRole
from app.services import inventory_service, product_service
from app.utils.http_auth import require_auth, roles_required

bp = Blueprint("inventory", __name__, url_prefix="/inventory")

_STAFF = (UserRole.ADMIN, UserRole.MANAGER)


@bp.get("/low-stock")
@require_auth
def low_stock():
    """Products with quantity at or below ``threshold`` (default 5)."""
    threshold = request.args.get("threshold", default=5, type=int)
    if threshold is None:
        threshold = 5
    products = inventory_service.low_stock_products(threshold)
    return jsonify(
        {
            "threshold": threshold,
            "products": [product_service.product_to_dict(p) for p in products],
        }
    )


@bp.put("/products/<int:product_id>/quantity")
@require_auth
@roles_required(*_STAFF)
def set_product_quantity(product_id: int):
    """Set on-hand quantity (e.g. after a stock count)."""
    data = request.get_json(silent=True) or {}
    try:
        qty = int(data.get("quantity"))
    except (TypeError, ValueError):
        return jsonify({"error": "quantity must be an integer"}), 400
    try:
        product = inventory_service.adjust_product_quantity(product_id, qty)
    except LookupError:
        return jsonify({"error": "Product not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"product": product_service.product_to_dict(product)})
