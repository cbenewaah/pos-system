"""
Reporting API — daily sales, product sales, inventory snapshot (Admin / Manager).
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.models.user import UserRole
from app.services import reporting_service
from app.utils.http_auth import require_auth, roles_required

bp = Blueprint("reports", __name__, url_prefix="/reports")

_STAFF = (UserRole.ADMIN, UserRole.MANAGER)


@bp.get("/daily")
@require_auth
@roles_required(*_STAFF)
def report_daily():
    """
    Completed sales totals for one **UTC** calendar day.

    Query ``date=YYYY-MM-DD`` (default: today UTC).
    """
    raw = request.args.get("date", type=str)
    if raw:
        try:
            day = reporting_service.parse_iso_date(raw, label="date")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    else:
        day = datetime.now(timezone.utc).date()
    return jsonify({"report": reporting_service.daily_sales_report(day)})


@bp.get("/products")
@require_auth
@roles_required(*_STAFF)
def report_products():
    """
    Units and revenue per product over a date range (UTC, inclusive).

    Query ``start`` and ``end`` as ``YYYY-MM-DD``. If omitted, defaults to the last 7 days through today UTC.
    """
    start_raw = request.args.get("start", type=str)
    end_raw = request.args.get("end", type=str)
    try:
        start, end = reporting_service.parse_report_dates(start_raw, end_raw, default_days=7)
        payload = reporting_service.product_sales_report(start, end)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"report": payload})


@bp.get("/inventory")
@require_auth
@roles_required(*_STAFF)
def report_inventory():
    """Full inventory list plus total units and retail stock valuation."""
    return jsonify({"report": reporting_service.inventory_report()})
