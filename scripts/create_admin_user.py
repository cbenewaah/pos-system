"""One-off: create user admin / admin123 with Admin role (local DB from .env)."""
from __future__ import annotations

from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.services.auth_service import register_user


def main() -> None:
    app = create_app()
    with app.app_context():
        if User.query.filter_by(username="admin").first():
            print('User "admin" already exists. No change made.')
            return
        user = register_user("admin", "admin123")
        if user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            db.session.commit()
        print(f'Created user "admin" with role {user.role}. Password: admin123')


if __name__ == "__main__":
    main()
