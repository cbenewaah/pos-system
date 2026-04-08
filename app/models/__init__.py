"""
SQLAlchemy models (data layer).

Import all models here so Flask-Migrate / Alembic sees every table.
"""
from app.models.customer import Customer
from app.models.payment import Payment, PaymentMethod
from app.models.product import Product
from app.models.sale import Sale, SaleItem
from app.models.user import User, UserRole

__all__ = [
    "Customer",
    "Payment",
    "PaymentMethod",
    "Product",
    "Sale",
    "SaleItem",
    "User",
    "UserRole",
]
