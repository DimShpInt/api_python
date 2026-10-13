"""
Tesrts for the API endpoints.
"""

from __future__ import annotations

from conftest import AUTH


def test_healthz_without_token(client) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["storage"] == "memory"


def test_list_without_token_401(client) -> None:
    resp = client.get("/api/v1/items")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


def test_list_wrong_token_401(client) -> None:
    resp = client.get("/api/v1/items", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_wrong_scheme_401(client) -> None:
    resp = client.get("/api/v1/items", headers={"Authorization": "Token nope"})
    assert resp.status_code == 401


def test_crud_roundtrip(client) -> None:
    created = client.post(
        "/api/v1/items",
        json={"fqdn": "api.example.com", "type": "A"},
        headers=AUTH,
    )
    assert created.status_code == 201
    item = created.json()
    assert item["fqdn"] == "api.example.com"
    assert item["type"] == "A"
    item_id = item["id"]

    listed = client.get("/api/v1/items", headers=AUTH)
    assert listed.status_code == 200
    assert [entry["id"] for entry in listed.json()] == [item_id]

    fetched = client.get(f"/api/v1/items/{item_id}", headers=AUTH)
    assert fetched.status_code == 200
    assert fetched.json() == item

    deleted = client.delete(f"/api/v1/items/{item_id}", headers=AUTH)
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/items/{item_id}", headers=AUTH)
    assert missing.status_code == 404
    repeat = client.delete(f"/api/v1/items/{item_id}", headers=AUTH)
    assert repeat.status_code == 404


def test_post_requires_fqdn(client) -> None:
    resp = client.post("/api/v1/items", json={"type": "A"}, headers=AUTH)
    assert resp.status_code == 422


def test_post_rejects_empty_fqdn(client) -> None:
    resp = client.post("/api/v1/items", json={"fqdn": "", "type": "A"}, headers=AUTH)
    assert resp.status_code == 422
