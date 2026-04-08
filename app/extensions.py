"""
Flask extensions (shared app-wide).

Initialized in create_app() to support the application factory pattern.
"""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy ORM — models will subclass db.Model
db = SQLAlchemy()

# Alembic migrations bound to db
migrate = Migrate()

# Session-based auth (works with cookies); JWT is used for Bearer API clients too
login_manager = LoginManager()
