"""
Authentication API — register, login (JWT + session), logout, current user.
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_user, logout_user, current_user

from app.models.user import UserRole
from app.services.auth_service import register_user, user_to_public_dict, verify_credentials
from app.utils.auth_tokens import create_access_token
from app.utils.http_auth import require_auth, roles_required

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.post("/register")
def register():
    """Create an account (first user becomes Admin, others Cashier)."""
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    try:
        user = register_user(username, password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"user": user_to_public_dict(user)}), 201


@bp.post("/login")
def login():
    """
    Verify credentials. Returns a JWT and sets a Flask-Login session (cookie).

    API clients: send header ``Authorization: Bearer <access_token>``.
    Browser / Postman with cookies: session also works for protected routes.
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    user = verify_credentials(username, password)
    if user is None:
        return jsonify({"error": "Invalid username or password"}), 401

    login_user(user, remember=True)
    token = create_access_token(user.id, user.role, user.username)
    return jsonify(
        {
            "access_token": token,
            "token_type": "Bearer",
            "user": user_to_public_dict(user),
        }
    )


@bp.post("/logout")
def logout():
    """End the session cookie if present (JWT is forgotten on the client)."""
    if current_user.is_authenticated:
        logout_user()
    return jsonify({"message": "Logged out"}), 200


@bp.get("/me")
@require_auth
def me():
    """Who am I? Requires Bearer token or session."""
    from flask import g

    return jsonify({"user": user_to_public_dict(g.current_user)})


@bp.get("/admin-check")
@require_auth
@roles_required(UserRole.ADMIN)
def admin_check():
    """Example RBAC endpoint — only users with role Admin can access this."""
    return jsonify({"message": "You have Admin access."})
