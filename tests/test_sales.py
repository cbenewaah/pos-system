from __future__ import annotations

from tests.conftest import auth_headers


def test_sale_complete_single_payment_receipt(admin_client):
    client, token = admin_client
    h = auth_headers(token)

    r = client.post(
        "/products",
        json={
            "name": "Sale Item",
            "category": "T",
            "price": 5.0,
            "quantity": 20,
            "barcode": "pytest-sale-1",
        },
        headers=h,
    )
    pid = r.get_json()["product"]["id"]

    r = client.post("/sales", json={}, headers=h)
    assert r.status_code == 201
    sid = r.get_json()["sale"]["id"]
    assert r.get_json()["sale"]["status"] == "draft"

    r = client.get(f"/receipts/{sid}", headers=h)
    assert r.status_code == 400

    r = client.post(
        f"/sales/{sid}/items",
        json={"product_id": pid, "quantity": 2},
        headers=h,
    )
    assert r.status_code == 200
    assert r.get_json()["sale"]["total_amount"] == 10.0

    r = client.post(
        f"/sales/{sid}/complete",
        json={"payment_method": "cash"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.get_json()["sale"]["status"] == "completed"
    assert len(r.get_json()["sale"]["payments"]) == 1

    r = client.get(f"/products/{pid}", headers=h)
    assert r.get_json()["product"]["quantity"] == 18

    r = client.get(f"/receipts/{sid}", headers=h)
    assert r.status_code == 200
    rec = r.get_json()["receipt"]
    assert rec["total"] == 10.0
    assert rec["payments"][0]["method"] == "cash"

    r = client.get(f"/receipts/{sid}?format=text", headers=h)
    assert r.status_code == 200
    assert "TOTAL:" in r.get_data(as_text=True)


def test_sale_split_payment_must_match_total(admin_client):
    client, token = admin_client
    h = auth_headers(token)

    r = client.post(
        "/products",
        json={
            "name": "Split Item",
            "category": "T",
            "price": 3.0,
            "quantity": 10,
            "barcode": "pytest-split-1",
        },
        headers=h,
    )
    pid = r.get_json()["product"]["id"]

    r = client.post("/sales", json={}, headers=h)
    sid = r.get_json()["sale"]["id"]
    client.post(
        f"/sales/{sid}/items",
        json={"product_id": pid, "quantity": 1},
        headers=h,
    )
    r = client.post(
        f"/sales/{sid}/complete",
        json={"payments": [{"method": "cash", "amount": 1}]},
        headers=h,
    )
    assert r.status_code == 400

    r = client.post(
        f"/sales/{sid}/complete",
        json={
            "payments": [
                {"method": "cash", "amount": 1.5},
                {"method": "momo", "amount": 1.5},
            ]
        },
        headers=h,
    )
    assert r.status_code == 200
    assert r.get_json()["sale"]["payment_method"] == "mixed"
