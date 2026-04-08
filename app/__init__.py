"""
POS application package.

Uses an application factory so tests and production can create the app
with different configuration without side effects at import time.
"""
import os
from typing import Optional

from flask import Flask

from app.extensions import db, migrate


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
    # Register models with SQLAlchemy metadata (required for migrations).
    # Use relative import — `import app.models` would rebind local name `app` to the package.
    from . import models  # noqa: F401

    # --- Presentation layer (blueprints) ---
    # Health check; auth, products, sales APIs added in later steps.
    from app.routes.health import bp as health_bp

    app.register_blueprint(health_bp)

    return app
