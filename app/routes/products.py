"""
Product REST API — list, search, CRUD.

Reads: any authenticated role. Writes: Admin and Manager only.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.models.user import UserRole
from app.services import product_service
from app.utils.http_auth import require_auth, roles_required

bp = Blueprint("products", __name__, url_prefix="/products")

_STAFF_ROLES = (UserRole.ADMIN, UserRole.MANAGER)


def _json_error(message: str, code: int):
    return jsonify({"error": message}), code


@bp.get("")
@require_auth
def list_products():
    """
    List products.

    Query params:
      ``q`` — search name, category, barcode (if present, search mode).
      ``category`` — filter by category (optional; can combine after search or only filter — if ``q`` set, search first then category filter in code).

    Behavior: If ``q`` is non-empty, return search results (optional ``category`` narrows those rows).
    If ``q`` is empty, return all products (optional ``category`` filter).
    """
    q = request.args.get("q", type=str, default="") or ""
    category = request.args.get("category", type=str)

    if q.strip():
        products = product_service.search_products(q)
        if category is not None and category.strip():
            cat_lower = category.strip().lower()
            products = [p for p in products if p.category.lower() == cat_lower]
    else:
        products = product_service.list_products(
            category=category.strip() if category else None
        )

    return jsonify({"products": [product_service.product_to_dict(p) for p in products]})


@bp.get("/<int:product_id>")
@require_auth
def get_product(product_id: int):
    product = product_service.get_product_by_id(product_id)
    if product is None:
        return _json_error("Product not found", 404)
    return jsonify({"product": product_service.product_to_dict(product)})


@bp.post("")
@require_auth
@roles_required(*_STAFF_ROLES)
def create_product():
    data = request.get_json(silent=True) or {}
    try:
        product = product_service.create_product(data)
    except ValueError as e:
        return _json_error(str(e), 400)
    return jsonify({"product": product_service.product_to_dict(product)}), 201


@bp.put("/<int:product_id>")
@require_auth
@roles_required(*_STAFF_ROLES)
def update_product(product_id: int):
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _json_error("Expected JSON object", 400)
    try:
        product = product_service.update_product(product_id, data)
    except LookupError:
        return _json_error("Product not found", 404)
    except ValueError as e:
        return _json_error(str(e), 400)
    return jsonify({"product": product_service.product_to_dict(product)})


@bp.delete("/<int:product_id>")
@require_auth
@roles_required(*_STAFF_ROLES)
def delete_product(product_id: int):
    try:
        product_service.delete_product(product_id)
    except LookupError:
        return _json_error("Product not found", 404)
    except ValueError as e:
        return _json_error(str(e), 409)
    return "", 204
