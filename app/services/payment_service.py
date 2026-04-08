"""
Payment validation and recording — cash, mobile money, card; split tender supported.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.models.payment import Payment, PaymentMethod

_ALLOWED = frozenset(
    {
        PaymentMethod.CASH,
        PaymentMethod.MOMO,
        PaymentMethod.CARD,
    }
)


def normalize_method(raw: str) -> str:
    method = (raw or "").strip().lower()
    if method not in _ALLOWED:
        allowed = ", ".join(sorted(_ALLOWED))
        raise ValueError(f'Invalid payment method. Use one of: {allowed}')
    return method


def _money(value: Any, *, label: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError(f"{label} must be a number") from e
    return d.quantize(Decimal("0.01"))


def resolve_payment_plan(
    *,
    sale_total: Decimal,
    payment_method: str | None,
    payments: list[Any] | None,
) -> list[tuple[str, Decimal]]:
    """
    Build a list of (method, amount) rows that must equal ``sale_total``.

    * If ``payments`` is a non-empty list, it defines split tender (sums must match).
    * Else ``payment_method`` is used for a single tender of the full total.
    """
    total = sale_total.quantize(Decimal("0.01"))

    if payments is not None and len(payments) > 0:
        rows: list[tuple[str, Decimal]] = []
        for i, row in enumerate(payments):
            if not isinstance(row, dict):
                raise ValueError(f"payments[{i}] must be an object with method and amount")
            method = normalize_method(str(row.get("method", "")))
            amt = _money(row.get("amount"), label=f"payments[{i}].amount")
            if amt <= 0:
                raise ValueError(f"payments[{i}].amount must be greater than zero")
            rows.append((method, amt))

        paid = sum((a for _, a in rows), start=Decimal("0")).quantize(Decimal("0.01"))
        if paid != total:
            raise ValueError(
                f"Sum of payments {paid} must equal sale total {total}. "
                "Adjust amounts or the sale total before completing."
            )
        return rows

    if payment_method is not None and str(payment_method).strip() != "":
        m = normalize_method(payment_method)
        return [(m, total)]

    raise ValueError('Provide "payment_method" for a single tender or "payments" for split tender')


def summary_payment_field(rows: list[tuple[str, Decimal]]) -> str:
    """Short string stored on Sale.payment_method (receipts / reports)."""
    if len(rows) == 1:
        return rows[0][0]
    methods = {r[0] for r in rows}
    if len(methods) == 1:
        return rows[0][0]
    return "mixed"


def payment_to_dict(p: Payment) -> dict[str, Any]:
    return {
        "id": p.id,
        "sale_id": p.sale_id,
        "method": p.method,
        "amount": float(p.amount),
    }
