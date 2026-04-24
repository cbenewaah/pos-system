"""
Paystack integration helpers: initialize and verify transactions.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
import uuid

import requests
from flask import current_app


class PaystackError(Exception):
    """Raised when Paystack calls fail or return invalid data."""


def _secret_key() -> str:
    key = (current_app.config.get("PAYSTACK_SECRET_KEY") or "").strip()
    if not key:
        raise PaystackError("Paystack is not configured. Set PAYSTACK_SECRET_KEY.")
    return key


def _base_url() -> str:
    return str(current_app.config.get("PAYSTACK_BASE_URL", "https://api.paystack.co")).rstrip("/")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_secret_key()}",
        "Content-Type": "application/json",
    }


def _to_minor_units(amount: Decimal) -> int:
    try:
        normalized = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise PaystackError("Invalid amount for Paystack payment.") from e
    if normalized <= 0:
        raise PaystackError("Payment amount must be greater than zero.")
    return int(normalized * 100)


def _transaction_reference(sale_id: int) -> str:
    return f"sale-{sale_id}-{uuid.uuid4().hex[:12]}"


def initialize_transaction(
    *,
    sale_id: int,
    amount: Decimal,
    email: str,
    payment_method: str,
) -> dict[str, Any]:
    method = (payment_method or "").strip().lower()
    channels = ["card"] if method == "card" else ["mobile_money"]
    reference = _transaction_reference(sale_id)
    payload = {
        "email": email,
        "amount": _to_minor_units(amount),
        "reference": reference,
        "currency": str(current_app.config.get("PAYSTACK_CURRENCY", "GHS")),
        "channels": channels,
        "metadata": {"sale_id": sale_id, "payment_method": method},
    }
    timeout = int(current_app.config.get("PAYSTACK_VERIFY_TIMEOUT", 20))
    try:
        resp = requests.post(
            f"{_base_url()}/transaction/initialize",
            headers=_headers(),
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise PaystackError("Could not reach Paystack. Please try again.") from e

    body = resp.json() if resp.content else {}
    if not resp.ok or not body.get("status"):
        msg = body.get("message") if isinstance(body, dict) else None
        raise PaystackError(msg or "Paystack initialization failed.")
    data = body.get("data") or {}
    auth_url = data.get("authorization_url")
    if not auth_url:
        raise PaystackError("Paystack did not return an authorization URL.")
    return {
        "reference": data.get("reference", reference),
        "authorization_url": auth_url,
    }


def verify_transaction(reference: str) -> dict[str, Any]:
    if not reference:
        raise PaystackError("Missing Paystack reference.")
    timeout = int(current_app.config.get("PAYSTACK_VERIFY_TIMEOUT", 20))
    try:
        resp = requests.get(
            f"{_base_url()}/transaction/verify/{reference}",
            headers=_headers(),
            timeout=timeout,
        )
    except requests.RequestException as e:
        raise PaystackError("Could not verify payment with Paystack.") from e

    body = resp.json() if resp.content else {}
    if not resp.ok or not body.get("status"):
        msg = body.get("message") if isinstance(body, dict) else None
        raise PaystackError(msg or "Paystack verification failed.")
    return body.get("data") or {}
