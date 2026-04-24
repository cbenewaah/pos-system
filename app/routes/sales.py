"""
Sales API — draft sale (cart), line items, discounts, complete transaction.
"""
from __future__ import annotations

from decimal import Decimal
import webbrowser

from flask import Blueprint, g, jsonify, request

from app.services import paystack_service, sales_service
from app.utils.http_auth import require_auth

bp = Blueprint("sales", __name__, url_prefix="/sales")


def _err(message: str, code: int):
    return jsonify({"error": message}), code


@bp.post("")
@require_auth
def create_sale():
    """Start a new draft sale (empty cart)."""
    data = request.get_json(silent=True) or {}
    customer_id = data.get("customer_id")
    try:
        sale = sales_service.create_draft_sale(
            user_id=g.current_user.id,
            customer_id=customer_id,
        )
    except ValueError as e:
        return _err(str(e), 400)
    return jsonify({"sale": sales_service.sale_to_dict(sale)}), 201


@bp.get("/<int:sale_id>")
@require_auth
def get_sale(sale_id: int):
    sale = sales_service.get_sale_by_id(sale_id)
    if sale is None:
        return _err("Sale not found", 404)
    if sale.user_id != g.current_user.id:
        return _err("Forbidden", 403)
    return jsonify({"sale": sales_service.sale_to_dict(sale)})


@bp.post("/<int:sale_id>/items")
@require_auth
def add_item(sale_id: int):
    """Add a line item (uses current product price as unit price snapshot)."""
    data = request.get_json(silent=True) or {}
    try:
        sale = sales_service.add_line_item(
            sale_id,
            actor_user_id=g.current_user.id,
            product_id=int(data.get("product_id")),
            quantity=int(data.get("quantity")),
        )
    except (TypeError, ValueError) as e:
        return _err(str(e), 400)
    except LookupError:
        return _err("Sale or product not found", 404)
    except PermissionError:
        return _err("You can only modify your own draft sales", 403)
    return jsonify({"sale": sales_service.sale_to_dict(sale)}), 200


@bp.patch("/<int:sale_id>")
@require_auth
def patch_sale(sale_id: int):
    """Update customer and/or discounts (percent and/or fixed amount)."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return _err("Expected JSON object", 400)

    kw = {"actor_user_id": g.current_user.id}
    if "customer_id" in data:
        kw["customer_id"] = data.get("customer_id")
    if "discount_percent" in data:
        kw["discount_percent"] = data.get("discount_percent")
    if "discount_amount" in data:
        kw["discount_amount"] = data.get("discount_amount")

    try:
        sale = sales_service.update_sale_metadata(sale_id, **kw)
    except LookupError:
        return _err("Sale not found", 404)
    except ValueError as e:
        return _err(str(e), 400)
    except PermissionError:
        return _err("You can only modify your own draft sales", 403)
    return jsonify({"sale": sales_service.sale_to_dict(sale)})


@bp.post("/<int:sale_id>/complete")
@require_auth
def complete_sale(sale_id: int):
    """
    Finalize sale: validate stock, deduct inventory, record payment(s), set completed.

    **Single tender:** ``{"payment_method": "cash"|"momo"|"card"}``

    **Split tender:** ``{"payments": [{"method": "cash", "amount": "10.00"}, ...]}``
    — amounts must sum exactly to the sale total (after discounts).
    """
    data = request.get_json(silent=True) or {}
    try:
        sale = sales_service.complete_sale(
            sale_id,
            actor_user_id=g.current_user.id,
            payment_method=data.get("payment_method"),
            payments=data.get("payments"),
        )
    except LookupError:
        return _err("Sale not found", 404)
    except ValueError as e:
        return _err(str(e), 400)
    except PermissionError:
        return _err("You can only complete your own draft sales", 403)
    return jsonify({"sale": sales_service.sale_to_dict(sale)}), 200


@bp.post("/<int:sale_id>/paystack/initialize")
@require_auth
def initialize_paystack_payment(sale_id: int):
    """Initialize a Paystack card/mobile money payment for a draft sale."""
    sale = sales_service.get_sale_by_id(sale_id)
    if sale is None:
        return _err("Sale not found", 404)
    if sale.user_id != g.current_user.id:
        return _err("You can only modify your own draft sales", 403)
    if sale.status != "draft":
        return _err("Sale is no longer editable", 400)
    if not sale.items:
        return _err("Add at least one item before payment.", 400)

    data = request.get_json(silent=True) or {}
    method = (data.get("payment_method") or "").strip().lower()
    if method not in {"momo", "card"}:
        return _err('Paystack payments require "momo" or "card" method.', 400)

    sales_service._recompute_totals(sale)
    total = Decimal(sale.total_amount).quantize(Decimal("0.01"))
    if total <= 0:
        return _err("Sale total must be greater than zero.", 400)

    customer_email = (sale.customer.email if sale.customer and sale.customer.email else None)
    fallback_email = g.current_user.username
    if "@" not in fallback_email:
        fallback_email = f"{fallback_email}@example.com"
    email = customer_email or fallback_email
    try:
        initialized = paystack_service.initialize_transaction(
            sale_id=sale.id,
            amount=total,
            email=email,
            payment_method=method,
        )
    except paystack_service.PaystackError as e:
        return _err(str(e), 400)

    # Best-effort open in default browser for local desktop setups.
    webbrowser.open(initialized["authorization_url"])
    return jsonify(
        {
            "reference": initialized["reference"],
            "authorization_url": initialized["authorization_url"],
        }
    )


@bp.post("/<int:sale_id>/paystack/verify")
@require_auth
def verify_paystack_payment(sale_id: int):
    """Verify a Paystack transaction and complete sale only on success."""
    sale = sales_service.get_sale_by_id(sale_id)
    if sale is None:
        return _err("Sale not found", 404)
    if sale.user_id != g.current_user.id:
        return _err("You can only modify your own draft sales", 403)
    if sale.status != "draft":
        return _err("Sale is no longer editable", 400)

    data = request.get_json(silent=True) or {}
    reference = (data.get("reference") or "").strip()
    if not reference:
        return _err("Paystack reference is required.", 400)

    sales_service._recompute_totals(sale)
    expected_minor_amount = int(Decimal(sale.total_amount).quantize(Decimal("0.01")) * 100)
    method = (data.get("payment_method") or "").strip().lower()
    if method not in {"momo", "card"}:
        return _err('Paystack verification requires "momo" or "card" method.', 400)
    try:
        verified = paystack_service.verify_transaction(reference)
    except paystack_service.PaystackError as e:
        return _err(str(e), 400)

    if verified.get("status") != "success":
        return _err("Payment was not successful or was cancelled.", 400)
    if int(verified.get("amount") or 0) != expected_minor_amount:
        return _err("Verified payment amount does not match sale total.", 400)

    try:
        completed = sales_service.complete_sale(
            sale_id,
            actor_user_id=g.current_user.id,
            payment_method=method,
        )
    except (LookupError, ValueError, PermissionError) as e:
        return _err(str(e), 400)
    return jsonify({"sale": sales_service.sale_to_dict(completed)})


@bp.delete("/<int:sale_id>")
@require_auth
def delete_sale(sale_id: int):
    """Abandon a draft sale (only drafts)."""
    try:
        sales_service.delete_draft_sale(sale_id, actor_user_id=g.current_user.id)
    except LookupError:
        return _err("Sale not found", 404)
    except ValueError as e:
        return _err(str(e), 400)
    except PermissionError:
        return _err("You can only delete your own draft sales", 403)
    return "", 204
