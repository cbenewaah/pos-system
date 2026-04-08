from __future__ import annotations


def _session_login(client, username: str, password: str):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_panel_pos_redirects_unauthenticated(client):
    r = client.get("/panel/pos")
    assert r.status_code == 302
    assert "/login" in (r.location or "")


def test_panel_pos_renders_for_authenticated_user(client):
    client.post(
        "/auth/register",
        json={"username": "ui_pos_user", "password": "password123"},
    )
    _session_login(client, "ui_pos_user", "password123")
    r = client.get("/panel/pos")
    assert r.status_code == 200
    assert b"POS Terminal" in r.data
    assert b"pos.js" in r.data
