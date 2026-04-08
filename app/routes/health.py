"""
Simple health endpoint to verify the app is running.

Database connectivity can be checked in a later step once models exist.
"""
from flask import Blueprint, jsonify

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "pos-system"})
