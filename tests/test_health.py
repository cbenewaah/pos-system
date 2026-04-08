from __future__ import annotations


def test_root_json(client):
    r = client.get("/", headers={"Accept": "application/json"})
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "auth" in data


def test_api_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["service"] == "pos-system"
