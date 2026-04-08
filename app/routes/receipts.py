"""
Receipt endpoints — JSON (default) or plain text.
"""
from __future__ import annotations

from flask import Blueprint, Response, g, jsonify, request

from app.services import receipt_service, sales_service
from app.utils.http_auth import require_auth

bp = Blueprint("receipts", __name__, url_prefix="/receipts")


@bp.get("/<int:sale_id>")
@require_auth
def get_receipt(sale_id: int):
    """
    Receipt for a **completed** sale (same owner as ``GET /sales/<id>``).

    Query ``format=text`` for ``text/plain``; default is JSON.
    """
    sale = sales_service.get_sale_by_id(sale_id)
    if sale is None:
        return jsonify({"error": "Sale not found"}), 404
    if sale.user_id != g.current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    try:
        payload = receipt_service.build_receipt(sale)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    fmt = (request.args.get("format") or "json").strip().lower()
    if fmt == "text":
        text = receipt_service.receipt_to_text(payload)
        return Response(text, mimetype="text/plain; charset=utf-8")
    return jsonify({"receipt": payload})
