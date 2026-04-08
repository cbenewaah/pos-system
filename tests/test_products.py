from __future__ import annotations

from tests.conftest import auth_headers


def test_product_crud_and_cashier_write_forbidden(admin_client):
    client, token = admin_client
    h = auth_headers(token)

    r = client.post(
        "/products",
        json={
            "name": "Test Cola",
            "category": "Drinks",
            "price": 2.5,
            "quantity": 10,
            "barcode": "pytest-cola-1",
        },
        headers=h,
    )
    assert r.status_code == 201
    pid = r.get_json()["product"]["id"]

    r = client.get("/products", headers=h)
    assert r.status_code == 200
    names = [p["name"] for p in r.get_json()["products"]]
    assert "Test Cola" in names

    r = client.get(f"/products/{pid}", headers=h)
    assert r.status_code == 200

    client.post(
        "/auth/register",
        json={"username": "pytest_cashier", "password": "password123"},
    )
    r = client.post(
        "/auth/login",
        json={"username": "pytest_cashier", "password": "password123"},
    )
    ct = r.get_json()["access_token"]
    r = client.post(
        "/products",
        json={"name": "X", "category": "Y", "price": 1, "quantity": 1},
        headers=auth_headers(ct),
    )
    assert r.status_code == 403
