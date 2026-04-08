"""
Browser UI (Jinja templates + session auth).

Uses the same Flask-Login session as the API and ``auth_service.verify_credentials``.
JSON API routes stay on their existing paths (e.g. GET /products). To avoid path
clashes, panel HTML lives under ``/panel/...`` (e.g. products and POS).
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.models.user import UserRole
from app.services import (
    customer_service,
    inventory_service,
    product_service,
    receipt_service,
    reporting_service,
    sales_service,
)
from app.services.auth_service import verify_credentials

bp = Blueprint("ui", __name__)

_STAFF_ROLES = (UserRole.ADMIN, UserRole.MANAGER)


def _can_manage_catalog() -> bool:
    return bool(
        current_user.is_authenticated and current_user.role in _STAFF_ROLES
    )


def _staff_catalog_redirect():
    if not _can_manage_catalog():
        flash(
            "You do not have permission to add, edit, or delete products.",
            "danger",
        )
        return redirect(url_for("ui.products_list"))
    return None


def _safe_next_url(candidate: str | None) -> str | None:
    """Allow only relative same-site redirects after login."""
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        return None
    if not candidate.startswith("/"):
        return None
    return candidate


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Session-based login for the web UI (form POST)."""
    if current_user.is_authenticated:
        return redirect(url_for("ui.dashboard"))

    next_url = request.args.get("next") or ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        next_url = request.form.get("next") or next_url

        user = verify_credentials(username, password)
        if user is None:
            flash("Invalid username or password.", "danger")
        else:
            login_user(user, remember=True)
            flash("You are logged in.", "success")
            target = _safe_next_url(next_url.strip() or None)
            return redirect(target or url_for("ui.dashboard"))

    return render_template(
        "login.html",
        nav_active="login",
        next_url=_safe_next_url(next_url.strip() or None) or "",
    )


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("ui.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    """Today’s sales (UTC) + low-stock alert — uses same logic as reporting/inventory APIs."""
    today = datetime.now(timezone.utc).date()
    daily = reporting_service.daily_sales_report(today)
    low_stock_threshold = 5
    low_stock = inventory_service.low_stock_products(low_stock_threshold)

    return render_template(
        "dashboard.html",
        nav_active="dashboard",
        daily=daily,
        low_stock=low_stock,
        low_stock_threshold=low_stock_threshold,
    )


@bp.route("/panel/products")
@login_required
def products_list():
    """Catalog browser + search; writes require Admin or Manager (same as API)."""
    q = (request.args.get("q") or "").strip()
    category = request.args.get("category", type=str)
    cat_arg = category.strip() if category and category.strip() else None

    if q:
        products = product_service.search_products(q)
        if cat_arg:
            products = [
                p for p in products if p.category.lower() == cat_arg.lower()
            ]
    else:
        products = product_service.list_products(category=cat_arg)

    return render_template(
        "products.html",
        nav_active="products",
        products=products,
        search_q=q,
        search_category=category or "",
        can_manage=_can_manage_catalog(),
    )


@bp.route("/panel/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    if (redir := _staff_catalog_redirect()) is not None:
        return redir

    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "category": request.form.get("category"),
            "price": request.form.get("price"),
            "quantity": request.form.get("quantity"),
            "barcode": request.form.get("barcode"),
        }
        try:
            product = product_service.create_product(data)
            flash(f'Product "{product.name}" was created.', "success")
            return redirect(url_for("ui.products_list"))
        except ValueError as e:
            flash(str(e), "danger")

    return render_template(
        "add_product.html",
        nav_active="products",
        product=None,
        form_data=request.form if request.method == "POST" else None,
    )


@bp.route("/panel/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id: int):
    if (redir := _staff_catalog_redirect()) is not None:
        return redir

    product = product_service.get_product_by_id(product_id)
    if product is None:
        flash("Product not found.", "danger")
        return redirect(url_for("ui.products_list"))

    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "category": request.form.get("category"),
            "price": request.form.get("price"),
            "quantity": request.form.get("quantity"),
            "barcode": request.form.get("barcode"),
        }
        try:
            product_service.update_product(product_id, data)
            flash("Product was updated.", "success")
            return redirect(url_for("ui.products_list"))
        except ValueError as e:
            flash(str(e), "danger")
            return render_template(
                "edit_product.html",
                nav_active="products",
                product=product,
                form_data=request.form,
            )

    return render_template(
        "edit_product.html",
        nav_active="products",
        product=product,
        form_data=None,
    )


@bp.post("/panel/products/<int:product_id>/delete")
@login_required
def product_delete(product_id: int):
    if (redir := _staff_catalog_redirect()) is not None:
        return redir

    try:
        product_service.delete_product(product_id)
        flash("Product was deleted.", "success")
    except LookupError:
        flash("Product not found.", "danger")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("ui.products_list"))


@bp.route("/panel/pos")
@login_required
def pos_terminal():
    """POS terminal UI. Uses existing /sales and /products APIs from JS."""
    # Plain dicts only: ``|tojson`` cannot serialize SQLAlchemy models (500 in production).
    products = [
        product_service.product_to_dict(p) for p in product_service.list_products()
    ]
    customers = [
        customer_service.customer_to_dict(c)
        for c in customer_service.search_customers(None)
    ]
    return render_template(
        "pos.html",
        nav_active="pos",
        products=products,
        customers=customers,
    )


@bp.route("/receipt/<int:sale_id>")
@login_required
def receipt_view(sale_id: int):
    """Printable receipt page for a completed sale owned by current user."""
    sale = sales_service.get_sale_by_id(sale_id)
    if sale is None:
        flash("Sale not found.", "danger")
        return redirect(url_for("ui.pos_terminal"))
    if sale.user_id != current_user.id:
        flash("You can only view your own receipts.", "danger")
        return redirect(url_for("ui.pos_terminal"))

    try:
        receipt = receipt_service.build_receipt(sale)
    except ValueError as e:
        flash(str(e), "warning")
        return redirect(url_for("ui.pos_terminal"))

    return render_template(
        "receipt.html",
        nav_active="pos",
        receipt=receipt,
        sale_id=sale_id,
    )
