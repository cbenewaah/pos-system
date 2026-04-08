"""
Reporting queries — daily totals, product performance, inventory valuation.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.models.product import Product
from app.models.sale import Sale, SaleItem, SaleStatus
from app.services import product_service


def _utc_day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def parse_iso_date(value: str, *, label: str = "date") -> date:
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError) as e:
        raise ValueError(f"{label} must be YYYY-MM-DD") from e


def daily_sales_report(day: date) -> dict[str, Any]:
    """Completed sales for one calendar day (UTC boundaries)."""
    start, end = _utc_day_bounds(day)
    sales = (
        Sale.query.filter(Sale.status == SaleStatus.COMPLETED)
        .filter(Sale.date >= start, Sale.date < end)
        .order_by(Sale.id)
        .all()
    )

    total = Decimal(0)
    by_method: dict[str, Decimal] = {}
    for s in sales:
        amt = Decimal(s.total_amount)
        total += amt
        key = s.payment_method or "unknown"
        by_method[key] = by_method.get(key, Decimal(0)) + amt

    return {
        "date": day.isoformat(),
        "timezone": "UTC",
        "transaction_count": len(sales),
        "total_revenue": float(total.quantize(Decimal("0.01"))),
        "by_payment_method": {
            k: float(v.quantize(Decimal("0.01"))) for k, v in sorted(by_method.items())
        },
    }


def product_sales_report(start: date, end: date) -> dict[str, Any]:
    """
    Aggregated units and revenue per product between ``start`` and ``end`` (inclusive, UTC dates).
    """
    if end < start:
        raise ValueError("end date must be on or after start date")

    start_dt, _ = _utc_day_bounds(start)
    _, end_after = _utc_day_bounds(
        end
    )  # exclusive upper bound: start of day after `end`

    revenue_expr = func.sum(SaleItem.quantity * SaleItem.price).label("revenue")
    units_expr = func.sum(SaleItem.quantity).label("units_sold")

    rows = (
        db.session.query(
            Product.id,
            Product.name,
            Product.category,
            units_expr,
            revenue_expr,
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.status == SaleStatus.COMPLETED)
        .filter(Sale.date >= start_dt, Sale.date < end_after)
        .group_by(Product.id, Product.name, Product.category)
        .order_by(revenue_expr.desc())
        .all()
    )

    products_out = []
    for pid, name, category, units, revenue in rows:
        rev = Decimal(revenue or 0).quantize(Decimal("0.01"))
        products_out.append(
            {
                "product_id": pid,
                "name": name,
                "category": category,
                "units_sold": int(units or 0),
                "revenue": float(rev),
            }
        )

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": "UTC",
        "products": products_out,
    }


def inventory_report() -> dict[str, Any]:
    """On-hand quantities and retail value using current prices."""
    products = Product.query.order_by(Product.category, Product.name).all()
    total_units = sum(int(p.quantity) for p in products)
    value = Decimal(0)
    for p in products:
        value += Decimal(int(p.quantity)) * Decimal(p.price)
    return {
        "product_count": len(products),
        "total_units": total_units,
        "stock_value_at_retail": float(value.quantize(Decimal("0.01"))),
        "products": [product_service.product_to_dict(p) for p in products],
    }


def parse_report_dates(
    start_raw: str | None, end_raw: str | None, *, default_days: int = 7
) -> tuple[date, date]:
    """Default window: last ``default_days`` days ending today (UTC)."""
    today = datetime.now(timezone.utc).date()
    if end_raw:
        end = parse_iso_date(end_raw, label="end")
    else:
        end = today
    if start_raw:
        start = parse_iso_date(start_raw, label="start")
    else:
        start = end - timedelta(days=default_days - 1)
    return start, end
