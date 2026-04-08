"""
Product catalog — CRUD and search (business logic).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.product import Product


def product_to_dict(product: Product) -> dict[str, Any]:
    """Serialize product for JSON (numeric types are JSON-friendly)."""
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "price": float(product.price),
        "quantity": product.quantity,
        "barcode": product.barcode,
    }


def list_products(*, category: str | None = None) -> list[Product]:
    """All products, optionally filtered by exact category name (case-insensitive)."""
    q = Product.query
    if category is not None and category.strip():
        q = q.filter(Product.category.ilike(category.strip()))
    return q.order_by(Product.name).all()


def search_products(term: str) -> list[Product]:
    """Match name, category, or barcode (partial, case-insensitive)."""
    if not term or not term.strip():
        return []
    pattern = f"%{term.strip()}%"
    return (
        Product.query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.category.ilike(pattern),
                Product.barcode.ilike(pattern),
            )
        )
        .order_by(Product.name)
        .all()
    )


def get_product_by_id(product_id: int) -> Product | None:
    return db.session.get(Product, product_id)


def _parse_price(value) -> Decimal:
    if value is None:
        raise ValueError("price is required")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError("price must be a number") from e
    if d < 0:
        raise ValueError("price cannot be negative")
    return d


def _parse_quantity(value, *, default: int = 0) -> int:
    if value is None:
        return default
    try:
        q = int(value)
    except (TypeError, ValueError) as e:
        raise ValueError("quantity must be an integer") from e
    if q < 0:
        raise ValueError("quantity cannot be negative")
    return q


def create_product(data: dict) -> Product:
    """Insert a new product; raises ValueError on bad input."""
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")

    category = (data.get("category") or "General").strip() or "General"
    price = _parse_price(data.get("price"))
    quantity = _parse_quantity(data.get("quantity"), default=0)

    barcode = data.get("barcode")
    if barcode is not None:
        barcode = str(barcode).strip() or None

    product = Product(
        name=name,
        category=category,
        price=price,
        quantity=quantity,
        barcode=barcode,
    )
    db.session.add(product)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("barcode must be unique") from None
    return product


def update_product(product_id: int, data: dict) -> Product:
    """Partial update; missing fields are left unchanged."""
    product = get_product_by_id(product_id)
    if product is None:
        raise LookupError("Product not found")

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("name cannot be empty")
        product.name = name
    if "category" in data:
        cat = (data.get("category") or "").strip() or "General"
        product.category = cat
    if "price" in data:
        product.price = _parse_price(data.get("price"))
    if "quantity" in data:
        product.quantity = _parse_quantity(data.get("quantity"), default=product.quantity)
    if "barcode" in data:
        raw = data.get("barcode")
        product.barcode = None if raw is None else (str(raw).strip() or None)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError("barcode must be unique") from None
    return product


def delete_product(product_id: int) -> None:
    """Delete by id; raises LookupError if missing, ValueError if referenced by sales."""
    product = get_product_by_id(product_id)
    if product is None:
        raise LookupError("Product not found")
    db.session.delete(product)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValueError(
            "Cannot delete this product because it is linked to past sales. "
            "Deactivate it by setting quantity to 0 instead."
        ) from None
