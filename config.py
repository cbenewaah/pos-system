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

    # JWT access tokens (signed with SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "24"))

    # Minimum password length for registration
    PASSWORD_MIN_LENGTH = 8

    # Printed / API receipts (override via environment on Render)
    STORE_NAME = os.environ.get("STORE_NAME", "POS Store")
    STORE_ADDRESS = os.environ.get("STORE_ADDRESS", "")
    STORE_PHONE = os.environ.get("STORE_PHONE", "")
    # Drop dead connections before use (fixes “server closed the connection unexpectedly”).
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }


class DevelopmentConfig(Config):
    """Local development."""

    DEBUG = True
    SESSION_COOKIE_SECURE = False
    # Recycle connections before managed Postgres (e.g. Render) idle-closes them.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.environ.get("SQLALCHEMY_POOL_RECYCLE", "280")),
    }


class ProductionConfig(Config):
    """Production (e.g. Render web service + PostgreSQL)."""

    DEBUG = False
    # Send session cookie only over HTTPS (Render serves HTTPS)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = "https"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.environ.get("SQLALCHEMY_POOL_RECYCLE", "280")),
    }


class TestingConfig(Config):
    """In-memory SQLite for pytest (no PostgreSQL required)."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    # Stable secrets so JWT tests do not depend on developer .env (length ≥32 for HS256)
    SECRET_KEY = "test-secret-key-not-for-production-use-32b"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
