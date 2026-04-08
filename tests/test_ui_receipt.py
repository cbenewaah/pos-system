from __future__ import annotations

from tests.conftest import auth_headers


def _session_login(client, username: str, password: str):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def _create_completed_sale(client, token: str) -> int:
    h = auth_headers(token)
    r = client.post(
        "/products",
        headers=h,
        json={
            "name": "Receipt Product",
            "category": "Test",
            "price": 10.00,
            "quantity": 20,
        },
    )
    assert r.status_code == 201
    pid = r.get_json()["product"]["id"]

    r = client.post("/sales", headers=h, json={})
    assert r.status_code == 201
    sale_id = r.get_json()["sale"]["id"]

    r = client.post(
        f"/sales/{sale_id}/items",
        headers=h,
        json={"product_id": pid, "quantity": 2},
    )
    assert r.status_code == 200

    r = client.post(
        f"/sales/{sale_id}/complete",
        headers=h,
        json={"payment_method": "cash"},
    )
    assert r.status_code == 200
    return sale_id


def test_receipt_page_redirects_unauthenticated(client):
    r = client.get("/receipt/1")
    assert r.status_code == 302
    assert "/login" in (r.location or "")


def test_receipt_page_renders_for_sale_owner(client):
    client.post(
        "/auth/register",
        json={"username": "r_admin", "password": "password123"},
    )
    login = client.post(
        "/auth/login",
        json={"username": "r_admin", "password": "password123"},
    )
    token = login.get_json()["access_token"]
    sale_id = _create_completed_sale(client, token)

    _session_login(client, "r_admin", "password123")
    r = client.get(f"/receipt/{sale_id}")
    assert r.status_code == 200
    assert b"Receipt #" in r.data
    assert str(sale_id).encode() in r.data


def test_receipt_page_forbidden_for_other_user(client):
    client.post(
        "/auth/register",
        json={"username": "owner_admin", "password": "password123"},
    )
    owner_login = client.post(
        "/auth/login",
        json={"username": "owner_admin", "password": "password123"},
    )
    owner_token = owner_login.get_json()["access_token"]
    sale_id = _create_completed_sale(client, owner_token)

    client.post(
        "/auth/register",
        json={"username": "other_user", "password": "password123"},
    )
    client.get("/logout")
    _session_login(client, "other_user", "password123")
    r = client.get(f"/receipt/{sale_id}", follow_redirects=False)
    assert r.status_code == 302
    assert "/panel/pos" in (r.location or "")
