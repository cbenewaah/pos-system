from __future__ import annotations

import time

import jwt

from tests.conftest import auth_headers


def test_bearer_wrong_secret_rejected_when_no_session(app):
    """Malformed / wrong-key JWT must not authenticate (no login cookie yet)."""
    c = app.test_client()
    bad_sig = jwt.encode(
        {"sub": "1", "exp": int(time.time()) + 3600},
        "wrong-signing-key-not-app-secret",
        algorithm="HS256",
    )
    r = c.get("/auth/me", headers={"Authorization": f"Bearer {bad_sig}"})
    assert r.status_code == 401
    assert c.get("/auth/me").status_code == 401


def test_register_and_login_me(app):
    """Valid Bearer works; after login, session cookie also authenticates."""
    c = app.test_client()

    r = c.post(
        "/auth/register",
        json={"username": "u1", "password": "password123"},
    )
    assert r.status_code == 201
    assert r.get_json()["user"]["role"] == "Admin"

    r = c.post("/auth/login", json={"username": "u1", "password": "wrong"})
    assert r.status_code == 401

    r = c.post("/auth/login", json={"username": "u1", "password": "password123"})
    assert r.status_code == 200
    token = r.get_json()["access_token"]

    r = c.get("/auth/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.get_json()["user"]["username"] == "u1"

    # Session cookie from login_user — no Authorization header
    r = c.get("/auth/me")
    assert r.status_code == 200
    assert r.get_json()["user"]["username"] == "u1"


def test_cashier_cannot_admin_check(client):
    client.post(
        "/auth/register",
        json={"username": "admin_only", "password": "password123"},
    )
    client.post(
        "/auth/register",
        json={"username": "cashier_only", "password": "password123"},
    )
    r = client.post(
        "/auth/login",
        json={"username": "cashier_only", "password": "password123"},
    )
    token = r.get_json()["access_token"]
    r = client.get("/auth/admin-check", headers=auth_headers(token))
    assert r.status_code == 403
