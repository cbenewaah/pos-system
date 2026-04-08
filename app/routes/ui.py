"""
Browser UI (Jinja templates + session auth).

Uses the same Flask-Login session as the API and ``auth_service.verify_credentials``.
JSON API routes stay on their existing paths (e.g. GET /products). To avoid path
clashes, Products/POS HTML stubs live under /panel/ until those steps ship.
"""
from __future__ import annotations

from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.services.auth_service import verify_credentials

bp = Blueprint("ui", __name__)


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
    """Full metrics land in Step 2; placeholder keeps nav working."""
    return render_template("dashboard.html", nav_active="dashboard")


@bp.route("/panel/products")
@login_required
def products_stub():
    """Step 3 will replace with full product management UI (API remains /products)."""
    return render_template(
        "coming_soon.html",
        nav_active="products",
        page_title="Products",
        step_label="Step 3",
        api_hint="/products",
    )


@bp.route("/panel/pos")
@login_required
def pos_stub():
    """Step 4 — POS terminal UI (API sales routes unchanged)."""
    return render_template(
        "coming_soon.html",
        nav_active="pos",
        page_title="Point of sale",
        step_label="Step 4",
        api_hint="/sales",
    )
