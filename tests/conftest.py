"""
Shared Flask app + DB fixtures.

Uses in-memory SQLite (see ``TestingConfig``) and ``create_all`` so tests do not
need PostgreSQL or Alembic migrations.
"""
from __future__ import annotations

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """Registered first user = Admin; returns (client, bearer_token)."""
    r = client.post(
        "/auth/register",
        json={"username": "pytest_admin", "password": "password123"},
    )
    assert r.status_code == 201
    r = client.post(
        "/auth/login",
        json={"username": "pytest_admin", "password": "password123"},
    )
    assert r.status_code == 200
    token = r.get_json()["access_token"]
    return client, token


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
