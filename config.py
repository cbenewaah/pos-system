"""
Application configuration.

Loads settings from environment variables. Set DATABASE_URL to your Render
PostgreSQL connection string in production or local .env for development.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _database_uri() -> str:
    """
    Build SQLAlchemy database URI.

    Render often provides postgres://...; SQLAlchemy 2.x expects postgresql://...
    """
    uri = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/pos_db",
    )
    if uri.startswith("postgres://"):
        uri = "postgresql://" + uri[len("postgres://") :]
    return uri


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-in-production")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Helpful defaults for API-style apps (JSON errors)
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    """Local development."""

    DEBUG = True


class ProductionConfig(Config):
    """Production (e.g. Render web service + PostgreSQL)."""

    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
