from __future__ import annotations

from tests.conftest import auth_headers


def _session_login(client, username: str, password: str):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_ui_flow_product_to_receipt(client):
    # Register first user (Admin), then use UI session login.
    client.post(
        "/auth/register",
        json={"username": "flow_admin", "password": "password123"},
    )
    _session_login(client, "flow_admin", "password123")

    # Create product via Step 3 UI form.
    r = client.post(
        "/panel/products/new",
        data={
            "name": "Flow Item",
            "category": "Flow",
            "price": "5.00",
            "quantity": "10",
            "barcode": "",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    assert "/panel/products" in (r.location or "")

    # Use API endpoints with same session to complete a sale.
    # (Keeps this test deterministic without browser JS execution.)
    login_api = client.post(
        "/auth/login",
        json={"username": "flow_admin", "password": "password123"},
    )
    token = login_api.get_json()["access_token"]
    h = auth_headers(token)

    products = client.get("/products", headers=h).get_json()["products"]
    pid = [p["id"] for p in products if p["name"] == "Flow Item"][0]

    sale = client.post("/sales", headers=h, json={}).get_json()["sale"]
    sale_id = sale["id"]
    client.post(
        f"/sales/{sale_id}/items",
        headers=h,
        json={"product_id": pid, "quantity": 2},
    )
    client.post(
        f"/sales/{sale_id}/complete",
        headers=h,
        json={"payment_method": "cash"},
    )

    # Render Step 5 receipt page.
    r = client.get(f"/receipt/{sale_id}")
    assert r.status_code == 200
    assert b"Receipt #" in r.data
