"""
POS application package.

Uses an application factory so tests and production can create the app
with different configuration without side effects at import time.
"""
import os
from typing import Optional

from flask import Flask

from app.extensions import db, login_manager, migrate


def create_app(config_name: Optional[str] = None) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config_name: One of 'development', 'production', or None to use
            FLASK_CONFIG / default.
    """
    app = Flask(__name__)

    name = config_name or os.environ.get("FLASK_CONFIG", "development")
    from config import config_by_name

    app.config.from_object(config_by_name.get(name, config_by_name["default"]))

    # --- Data layer ---
    db.init_app(app)
    migrate.init_app(app, db)

    # --- Auth (Flask-Login + optional session cookie) ---
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.models.user import User

        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def _unauthorized():
        from flask import jsonify, redirect, request, url_for

        if request.blueprint == "ui":
            return redirect(url_for("ui.login", next=request.url))
        return jsonify({"error": "Authentication required"}), 401

    # Register models with SQLAlchemy metadata (required for migrations).
    # Use relative import — `import app.models` would rebind local name `app` to the package.
    from . import models  # noqa: F401

    # --- Presentation layer (blueprints) ---
    from app.routes.auth import bp as auth_bp
    from app.routes.customers import bp as customers_bp
    from app.routes.health import bp as health_bp
    from app.routes.health import root_bp
    from app.routes.inventory import bp as inventory_bp
    from app.routes.payments import bp as payments_bp
    from app.routes.products import bp as products_bp
    from app.routes.receipts import bp as receipts_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.sales import bp as sales_bp
    from app.routes.ui import bp as ui_bp

    app.register_blueprint(root_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(receipts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(ui_bp)

    # HTML UI login redirect target for @login_required on the ``ui`` blueprint
    login_manager.login_view = "ui.login"

    return app
