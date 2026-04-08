from __future__ import annotations

from datetime import datetime, timezone

from tests.conftest import auth_headers


def test_reports_staff_only_and_daily_shape(admin_client):
    client, admin_token = admin_client
    h = auth_headers(admin_token)

    day = datetime.now(timezone.utc).date().isoformat()
    r = client.get(f"/reports/daily?date={day}", headers=h)
    assert r.status_code == 200
    rep = r.get_json()["report"]
    assert "transaction_count" in rep
    assert "total_revenue" in rep
    assert "by_payment_method" in rep

    r = client.get("/reports/inventory", headers=h)
    assert r.status_code == 200
    assert "stock_value_at_retail" in r.get_json()["report"]

    r = client.get("/reports/products", headers=h)
    assert r.status_code == 200
    assert "products" in r.get_json()["report"]

    client.post(
        "/auth/register",
        json={"username": "pytest_rep_cashier", "password": "password123"},
    )
    r = client.post(
        "/auth/login",
        json={"username": "pytest_rep_cashier", "password": "password123"},
    )
    ct = r.get_json()["access_token"]
    r = client.get("/reports/daily", headers=auth_headers(ct))
    assert r.status_code == 403
