from __future__ import annotations

from app.models.product import Product


def _session_login(client, username: str, password: str):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_panel_products_redirects_unauthenticated(client):
    r = client.get("/panel/products")
    assert r.status_code == 302
    assert "/login" in (r.location or "")


def test_panel_products_list_renders_as_admin(app, client):
    client.post(
        "/auth/register",
        json={"username": "ui_adm", "password": "password123"},
    )
    _session_login(client, "ui_adm", "password123")
    r = client.get("/panel/products")
    assert r.status_code == 200
    assert b"Products" in r.data


def test_panel_product_new_forbidden_for_cashier(client):
    client.post(
        "/auth/register",
        json={"username": "ui_adm2", "password": "password123"},
    )
    client.post(
        "/auth/register",
        json={"username": "ui_cash", "password": "password123"},
    )
    _session_login(client, "ui_cash", "password123")
    r = client.get("/panel/products/new")
    assert r.status_code == 302
    loc = r.location or ""
    assert "/panel/products" in loc
    assert "/new" not in loc


def test_panel_product_create_as_admin(app, client):
    client.post(
        "/auth/register",
        json={"username": "ui_adm3", "password": "password123"},
    )
    _session_login(client, "ui_adm3", "password123")
    r = client.post(
        "/panel/products/new",
        data={
            "name": "UI Widget",
            "category": "Demo",
            "price": "12.99",
            "quantity": "5",
            "barcode": "",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302
    with app.app_context():
        p = Product.query.filter_by(name="UI Widget").first()
        assert p is not None
        assert p.quantity == 5
        assert float(p.price) == 12.99
