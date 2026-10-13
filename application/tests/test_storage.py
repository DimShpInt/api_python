"""
Tests for storage backends: memory, file, redis.
"""

from __future__ import annotations

import os

import pytest

from api_python.storage import Item, build_storage

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def test_memory_roundtrip() -> None:
    storage = build_storage("memory", "/tmp", REDIS_URL)
    item = storage.create("db.example.com", "A")
    assert isinstance(item, Item)
    assert storage.get(item.id) is not None
    assert [entry.id for entry in storage.list()] == [item.id]
    assert storage.delete(item.id) is True
    assert storage.get(item.id) is None
    assert storage.delete(item.id) is False
    assert storage.ping() is True


def test_file_roundtrip_and_persistence(tmp_path) -> None:
    first = build_storage("file", str(tmp_path), REDIS_URL)
    item = first.create("web.example.com", "AAAA")
    second = build_storage("file", str(tmp_path), REDIS_URL)
    loaded = second.get(item.id)
    assert loaded is not None
    assert loaded.fqdn == "web.example.com"
    assert loaded.type == "AAAA"
    assert (tmp_path / "items.json").exists()
    assert second.delete(item.id) is True
    assert second.get(item.id) is None


def test_unknown_backend_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="Unknown STORAGE_BACKEND"):
        build_storage("bogus", str(tmp_path), REDIS_URL)


def test_redis_roundtrip() -> None:
    storage = build_storage("redis", "/tmp", REDIS_URL)
    if not storage.ping():
        pytest.skip("Redis not available - test skipped")

    item = storage.create("mail.example.com", "MX")
    loaded = storage.get(item.id)
    assert loaded is not None
    assert loaded.fqdn == "mail.example.com"
    assert loaded.type == "MX"
    assert storage.delete(item.id) is True
    assert storage.get(item.id) is None
