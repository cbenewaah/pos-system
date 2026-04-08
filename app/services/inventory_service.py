"""
Inventory helpers: stock checks and deductions tied to sales.
"""
from __future__ import annotations

from app.extensions import db
from app.models.product import Product
from app.models.sale import Sale


def ensure_stock_for_sale(sale: Sale) -> None:
    """Raise ValueError if any line exceeds on-hand quantity."""
    for item in sale.items:
        product = db.session.get(Product, item.product_id)
        if product is None:
            raise ValueError(f"Product id {item.product_id} no longer exists")
        if product.quantity < item.quantity:
            raise ValueError(
                f"Insufficient stock for {product.name!r}: need {item.quantity}, have {product.quantity}"
            )


def reduce_stock_for_sale(sale: Sale) -> None:
    """
    Decrement product.quantity for each line. Call only after ensure_stock_for_sale.

    Does not commit; caller commits the surrounding transaction.
    """
    for item in sale.items:
        product = db.session.get(Product, item.product_id)
        if product is None:
            raise ValueError(f"Product id {item.product_id} missing")
        product.quantity = int(product.quantity) - int(item.quantity)


def low_stock_products(threshold: int = 5) -> list[Product]:
    """Products at or below the threshold (useful for reorder alerts)."""
    if threshold < 0:
        threshold = 0
    return (
        Product.query.filter(Product.quantity <= threshold)
        .order_by(Product.quantity, Product.name)
        .all()
    )


def adjust_product_quantity(product_id: int, new_quantity: int) -> Product:
    """Set absolute stock (e.g. after a stock count)."""
    if new_quantity < 0:
        raise ValueError("quantity cannot be negative")
    product = db.session.get(Product, product_id)
    if product is None:
        raise LookupError("Product not found")
    product.quantity = new_quantity
    db.session.commit()
    return product
