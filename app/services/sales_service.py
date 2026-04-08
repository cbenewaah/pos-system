"""
Sales workflow: draft sale (cart), line items, discounts, complete & save.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.extensions import db

from app.models.customer import Customer
from app.models.payment import Payment
from app.models.product import Product
from app.models.sale import Sale, SaleItem, SaleStatus
from app.services import inventory_service, payment_service

_UNSET = object()


def _decimal(value, *, field: str) -> Decimal:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError(f"{field} must be a number") from e
    return d


def _recompute_totals(sale: Sale) -> None:
    """Update subtotal and total_amount from lines and discount fields."""
    sub = Decimal(0)
    for item in sale.items:
        sub += Decimal(item.quantity) * Decimal(item.price)
    sale.subtotal = sub

    pct = Decimal(sale.discount_percent or 0)
    flat = Decimal(sale.discount_amount or 0)
    if pct < 0 or pct > 100:
        raise ValueError("discount_percent must be between 0 and 100")
    if flat < 0:
        raise ValueError("discount_amount cannot be negative")

    after_pct = sub * (Decimal(1) - pct / Decimal(100))
    total = after_pct - flat
    if total < 0:
        total = Decimal(0)
    sale.total_amount = total.quantize(Decimal("0.01"))


def sale_to_dict(sale: Sale) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": sale.id,
        "date": sale.date.isoformat(),
        "status": sale.status,
        "user_id": sale.user_id,
        "customer_id": sale.customer_id,
        "subtotal": float(sale.subtotal),
        "discount_percent": float(sale.discount_percent),
        "discount_amount": float(sale.discount_amount),
        "total_amount": float(sale.total_amount),
        "payment_method": sale.payment_method,
        "payments": [
            {
                "id": p.id,
                "method": p.method,
                "amount": float(p.amount),
            }
            for p in sale.payments.order_by(Payment.id)
        ],
        "items": [
            {
                "id": line.id,
                "product_id": line.product_id,
                "quantity": line.quantity,
                "unit_price": float(line.price),
                "line_total": float(
                    (Decimal(line.quantity) * Decimal(line.price)).quantize(Decimal("0.01"))
                ),
            }
            for line in sale.items
        ],
    }
    return out


def get_sale_by_id(sale_id: int) -> Sale | None:
    return db.session.get(Sale, sale_id)


def create_draft_sale(*, user_id: int, customer_id: int | None = None) -> Sale:
    if customer_id is not None:
        try:
            cid = int(customer_id)
        except (TypeError, ValueError) as e:
            raise ValueError("customer_id must be an integer") from e
        if db.session.get(Customer, cid) is None:
            raise ValueError("Customer not found")
        customer_id = cid
    sale = Sale(
        user_id=user_id,
        customer_id=customer_id,
        status=SaleStatus.DRAFT,
        subtotal=Decimal(0),
        discount_percent=Decimal(0),
        discount_amount=Decimal(0),
        total_amount=Decimal(0),
    )
    db.session.add(sale)
    db.session.commit()
    return sale


def assert_draft(sale: Sale) -> None:
    if sale.status != SaleStatus.DRAFT:
        raise ValueError("Sale is no longer editable")


def assert_owner(sale: Sale, user_id: int) -> None:
    if sale.user_id != user_id:
        raise PermissionError("You can only modify your own draft sales")


def add_line_item(
    sale_id: int,
    *,
    actor_user_id: int,
    product_id: int,
    quantity: int,
) -> Sale:
    sale = get_sale_by_id(sale_id)
    if sale is None:
        raise LookupError("Sale not found")
    assert_draft(sale)
    assert_owner(sale, actor_user_id)

    if quantity <= 0:
        raise ValueError("quantity must be positive")
    product = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Product not found")

    line = SaleItem(
        sale_id=sale.id,
        product_id=product.id,
        quantity=quantity,
        price=product.price,
    )
    db.session.add(line)
    db.session.flush()
    # Ensure line items are visible on the parent before summing totals.
    db.session.refresh(sale)
    _recompute_totals(sale)
    db.session.commit()
    return sale


def update_sale_metadata(
    sale_id: int,
    *,
    actor_user_id: int,
    customer_id: Any = _UNSET,
    discount_percent: Any = _UNSET,
    discount_amount: Any = _UNSET,
) -> Sale:
    sale = get_sale_by_id(sale_id)
    if sale is None:
        raise LookupError("Sale not found")
    assert_draft(sale)
    assert_owner(sale, actor_user_id)

    if customer_id is not _UNSET:
        if customer_id is None:
            sale.customer_id = None
        else:
            if db.session.get(Customer, int(customer_id)) is None:
                raise ValueError("Customer not found")
            sale.customer_id = int(customer_id)

    if discount_percent is not _UNSET:
        sale.discount_percent = _decimal(discount_percent, field="discount_percent")
    if discount_amount is not _UNSET:
        sale.discount_amount = _decimal(discount_amount, field="discount_amount")

    _recompute_totals(sale)
    db.session.commit()
    return sale


def delete_draft_sale(sale_id: int, *, actor_user_id: int) -> None:
    sale = get_sale_by_id(sale_id)
    if sale is None:
        raise LookupError("Sale not found")
    assert_draft(sale)
    assert_owner(sale, actor_user_id)
    db.session.delete(sale)
    db.session.commit()


def complete_sale(
    sale_id: int,
    *,
    actor_user_id: int,
    payment_method: str | None = None,
    payments: list | None = None,
) -> Sale:
    sale = get_sale_by_id(sale_id)
    if sale is None:
        raise LookupError("Sale not found")
    assert_draft(sale)
    assert_owner(sale, actor_user_id)

    if not sale.items:
        raise ValueError("Add at least one item before completing the sale")

    _recompute_totals(sale)
    inventory_service.ensure_stock_for_sale(sale)
    inventory_service.reduce_stock_for_sale(sale)

    total = Decimal(sale.total_amount).quantize(Decimal("0.01"))
    plan = payment_service.resolve_payment_plan(
        sale_total=total,
        payment_method=payment_method,
        payments=payments,
    )
    sale.payment_method = payment_service.summary_payment_field(plan)
    sale.status = SaleStatus.COMPLETED

    for method, amount in plan:
        db.session.add(Payment(sale_id=sale.id, method=method, amount=amount))
    db.session.commit()
    return sale
