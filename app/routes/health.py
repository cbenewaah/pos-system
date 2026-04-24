"""
Service info and health check.

GET / returns JSON for API clients; browsers are redirected to the web UI
so opening http://localhost:5000/ shows the login page instead of raw JSON.
"""
from flask import Blueprint, current_app, jsonify, redirect, request, url_for
from flask_login import current_user

# Site root (e.g. https://your-app.onrender.com/)
root_bp = Blueprint("root", __name__)

_API_INDEX = {
    "service": "pos-system",
    "status": "ok",
    "message": "API is running. Use /api/health for a simple health check. Web UI: /login",
    "auth": {
        "register": "POST /auth/register",
        "login": "POST /auth/login",
        "logout": "POST /auth/logout",
        "me": "GET /auth/me",
        "admin_check": "GET /auth/admin-check (Admin only)",
    },
    "products": "GET/POST /products; GET/PUT/DELETE /products/<id> (auth required)",
    "sales": "POST /sales, POST /sales/<id>/items, PATCH /sales/<id>, POST /sales/<id>/complete",
    "inventory": "GET /inventory/low-stock; PUT /inventory/products/<id>/quantity (Admin/Manager)",
    "payments": "GET /payments/sale/<sale_id> (see also sale.payments in GET /sales/<id>)",
    "customers": "GET/POST /customers; GET/PUT /customers/<id>; GET /customers/<id>/sales",
    "receipts": "GET /receipts/<sale_id> (?format=text for plain text; completed sales only)",
    "reports": "GET /reports/daily, /reports/products, /reports/inventory (Admin/Manager)",
}


@root_bp.get("/")
def index():
    """
    - Browsers (typical Accept: text/html): redirect to /login or /dashboard.
    - API / curl: ``Accept: application/json`` or ``?format=json`` → same JSON as before.
    """
    prefers_json = (
        request.args.get("format") == "json"
        or request.accept_mimetypes.best_match(["application/json", "text/html"])
        == "application/json"
    )
    if prefers_json:
        return jsonify(_API_INDEX)

    if current_user.is_authenticated:
        return redirect(url_for("ui.dashboard"))
    return redirect(url_for("ui.login"))


bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "pos-system"})


@bp.get("/debug/paystack-config")
def debug_paystack_config():
    """
    Runtime-safe Paystack config diagnostics.
    Does not expose the full secret key.
    """
    secret = str(current_app.config.get("PAYSTACK_SECRET_KEY", "") or "").strip()
    return jsonify(
        {
            "paystack_secret_key_set": bool(secret),
            "paystack_secret_key_prefix": secret[:7] if secret else "",
            "paystack_base_url": current_app.config.get("PAYSTACK_BASE_URL", ""),
            "paystack_currency": current_app.config.get("PAYSTACK_CURRENCY", ""),
            "paystack_verify_timeout": current_app.config.get("PAYSTACK_VERIFY_TIMEOUT", 20),
        }
    )
