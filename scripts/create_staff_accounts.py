"""Create or update demo Cashier and Manager accounts (uses DATABASE_URL from .env)."""
from __future__ import annotations

import time

from sqlalchemy.exc import OperationalError
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.services.auth_service import register_user


def _ensure_user(username: str, password: str, role: str) -> None:
    user = User.query.filter_by(username=username).first()
    if user is None:
        user = register_user(username, password)
    else:
        user.password_hash = generate_password_hash(password)
    user.role = role
    db.session.commit()
    print(f'OK: username={username!r} role={role} (password set)')


def _ensure_user_retry(username: str, password: str, role: str, *, attempts: int = 4) -> None:
    """Retry on transient Postgres disconnects (common with remote DBs)."""
    delay = 0.75
    last_err: OperationalError | None = None
    for i in range(attempts):
        try:
            _ensure_user(username, password, role)
            return
        except OperationalError as e:
            last_err = e
            db.session.rollback()
            db.session.remove()
            if i == attempts - 1:
                break
            print(f'  DB connection issue ({e}); retry {i + 2}/{attempts} in {delay:.1f}s...')
            time.sleep(delay)
            delay = min(delay * 1.6, 8.0)
    assert last_err is not None
    raise last_err


def main() -> None:
    app = create_app()
    with app.app_context():
        _ensure_user_retry("cashier", "cashier123", UserRole.CASHIER)
        db.session.remove()
        _ensure_user_retry("manager", "manager123", UserRole.MANAGER)


if __name__ == "__main__":
    main()
