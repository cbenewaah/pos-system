"""
Customer records — used on sales and receipts; loyalty points stub for later rules.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_

from app.extensions import db
from app.models.customer import Customer
from app.models.sale import Sale, SaleStatus


def customer_to_dict(c: Customer) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "email": c.email,
        "address": c.address,
        "loyalty_points": c.loyalty_points,
    }


def create_customer(data: dict) -> Customer:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")
    phone = data.get("phone")
    email = data.get("email")
    address = data.get("address")
    c = Customer(
        name=name,
        phone=(str(phone).strip() if phone else None) or None,
        email=(str(email).strip() if email else None) or None,
        address=(str(address).strip() if address else None) or None,
        loyalty_points=int(data.get("loyalty_points") or 0),
    )
    if c.loyalty_points < 0:
        raise ValueError("loyalty_points cannot be negative")
    db.session.add(c)
    db.session.commit()
    return c


def get_customer(customer_id: int) -> Customer | None:
    return db.session.get(Customer, customer_id)


def update_customer(customer_id: int, data: dict) -> Customer:
    c = get_customer(customer_id)
    if c is None:
        raise LookupError("Customer not found")
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("name cannot be empty")
        c.name = name
    if "phone" in data:
        p = data.get("phone")
        c.phone = (str(p).strip() if p else None) or None
    if "email" in data:
        e = data.get("email")
        c.email = (str(e).strip() if e else None) or None
    if "address" in data:
        a = data.get("address")
        c.address = (str(a).strip() if a else None) or None
    if "loyalty_points" in data:
        lp = int(data.get("loyalty_points"))
        if lp < 0:
            raise ValueError("loyalty_points cannot be negative")
        c.loyalty_points = lp
    db.session.commit()
    return c


def search_customers(term: str | None) -> list[Customer]:
    q = Customer.query
    if term and term.strip():
        pat = f"%{term.strip()}%"
        q = q.filter(
            or_(
                Customer.name.ilike(pat),
                Customer.phone.ilike(pat),
                Customer.email.ilike(pat),
            )
        )
    return q.order_by(Customer.name).limit(100).all()


def customer_sales_history(customer_id: int) -> list[Sale]:
    """Completed sales for this customer, newest first."""
    if get_customer(customer_id) is None:
        raise LookupError("Customer not found")
    return (
        Sale.query.filter_by(customer_id=customer_id, status=SaleStatus.COMPLETED)
        .order_by(Sale.date.desc())
        .limit(200)
        .all()
    )
