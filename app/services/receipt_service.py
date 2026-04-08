"""
Build customer-facing receipts (JSON or plain text) from a completed sale.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import current_app

from app.models.payment import Payment
from app.models.sale import Sale, SaleStatus


def build_receipt(sale: Sale) -> dict[str, Any]:
    """
    Structured receipt for printing, email, or JSON APIs.

    Raises ``ValueError`` if the sale is not completed (no receipt for open carts).
    """
    if sale.status != SaleStatus.COMPLETED:
        raise ValueError("Receipts are only generated for completed sales")

    store_name = current_app.config.get("STORE_NAME", "POS Store")
    store_address = (current_app.config.get("STORE_ADDRESS") or "").strip() or None
    store_phone = (current_app.config.get("STORE_PHONE") or "").strip() or None

    items_out: list[dict[str, Any]] = []
    for line in sale.items:
        product = line.product
        name = product.name if product is not None else f"Product #{line.product_id}"
        line_total = (Decimal(line.quantity) * Decimal(line.price)).quantize(Decimal("0.01"))
        items_out.append(
            {
                "product_id": line.product_id,
                "name": name,
                "quantity": line.quantity,
                "unit_price": float(line.price),
                "line_total": float(line_total),
            }
        )

    customer_out: dict[str, Any] | None = None
    if sale.customer_id is not None and sale.customer is not None:
        c = sale.customer
        customer_out = {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "email": c.email,
            "loyalty_points": c.loyalty_points,
        }

    payments_out = [
        {"method": p.method, "amount": float(p.amount)}
        for p in sale.payments.order_by(Payment.id)
    ]

    return {
        "store": {
            "name": store_name,
            **({"address": store_address} if store_address else {}),
            **({"phone": store_phone} if store_phone else {}),
        },
        "sale_id": sale.id,
        "date": sale.date.isoformat(),
        "cashier_user_id": sale.user_id,
        "customer": customer_out,
        "items": items_out,
        "subtotal": float(sale.subtotal),
        "discount_percent": float(sale.discount_percent),
        "discount_amount": float(sale.discount_amount),
        "total": float(sale.total_amount),
        "payment_summary": sale.payment_method,
        "payments": payments_out,
    }


def receipt_to_text(data: dict[str, Any]) -> str:
    """Fixed-width plain text suitable for thermal printers or logs."""
    lines: list[str] = []
    store = data.get("store") or {}
    name = store.get("name", "Store")
    width = 40
    lines.append(name.center(width))
    if store.get("address"):
        lines.append(str(store["address"])[:width].center(width))
    if store.get("phone"):
        lines.append(str(store["phone"])[:width].center(width))
    lines.append("-" * width)

    lines.append(f"Receipt #{data.get('sale_id')}")
    lines.append(str(data.get("date", "")))
    cust = data.get("customer")
    if cust:
        lines.append("-" * width)
        lines.append(f"Customer: {cust.get('name', '')}")
        if cust.get("phone"):
            lines.append(f"Phone: {cust['phone']}")
        if cust.get("email"):
            lines.append(f"Email: {cust['email']}")
    lines.append("-" * width)

    lines.append(f"{'Item':<18} {'Qty':>4} {'Each':>7} {'Tot':>8}")
    lines.append("-" * width)
    for it in data.get("items") or []:
        title = str(it.get("name", ""))[:18]
        q = it.get("quantity", 0)
        each = it.get("unit_price", 0)
        tot = it.get("line_total", 0)
        lines.append(f"{title:<18} {q:>4} {each:>7.2f} {tot:>8.2f}")
    lines.append("-" * width)

    lines.append(f"{'Subtotal:':<24}{data.get('subtotal', 0):>16.2f}")
    dp = data.get("discount_percent") or 0
    da = data.get("discount_amount") or 0
    if dp or da:
        lines.append(f"{'Discount %:':<24}{float(dp):>16.2f}")
        lines.append(f"{'Discount amt:':<24}{float(da):>16.2f}")
    lines.append(f"{'TOTAL:':<24}{data.get('total', 0):>16.2f}")
    lines.append("-" * width)
    lines.append(f"Payment ({data.get('payment_summary', '')}):")
    for p in data.get("payments") or []:
        lines.append(f"  {p.get('method',''):<10} {p.get('amount',0):>28.2f}")
    lines.append("=" * width)
    lines.append("Thank you!".center(width))
    return "\n".join(lines) + "\n"
