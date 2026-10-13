"""Data storage: memory / JSON file / Redis (selection via STORAGE_BACKEND)."""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


@dataclass
class Item:
    id: str
    fqdn: str
    type: str
    created_at: str

    @staticmethod
    def new(fqdn: str, type: str) -> Item:
        return Item(
            id=uuid.uuid4().hex,
            fqdn=fqdn,
            type=type,
            created_at=datetime.now(UTC).isoformat(),
        )


class Storage(Protocol):
    def create(self, fqdn: str, type: str) -> Item: ...
    def list(self) -> list[Item]: ...
    def get(self, item_id: str) -> Item | None: ...
    def delete(self, item_id: str) -> bool: ...
    def ping(self) -> bool: ...


class MemoryStorage:
    """Stores everything in memory — data is lost on restart. For testing/dev."""

    def __init__(self) -> None:
        self._items: dict[str, Item] = {}
        self._lock = threading.Lock()

    def create(self, fqdn: str, type: str) -> Item:
        item = Item.new(fqdn, type)
        with self._lock:
            self._items[item.id] = item
        return item

    def list(self) -> list[Item]:
        with self._lock:
            return list(self._items.values())

    def get(self, item_id: str) -> Item | None:
        with self._lock:
            return self._items.get(item_id)

    def delete(self, item_id: str) -> bool:
        with self._lock:
            return self._items.pop(item_id, None) is not None

    def ping(self) -> bool:
        return True


class FileStorage:
    """JSON file with atomic write (tmp + rename), thread-safe."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _load(self) -> dict[str, Item]:
        if not self._path.exists():
            return {}
        raw = json.loads(self._path.read_text(encoding="utf-8") or "{}")
        return {key: Item(**value) for key, value in raw.items()}

    def _save(self, items: dict[str, Item]) -> None:
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(
                {key: asdict(value) for key, value in items.items()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(tmp, self._path)

    def create(self, fqdn: str, type: str) -> Item:
        with self._lock:
            items = self._load()
            item = Item.new(fqdn, type)
            items[item.id] = item
            self._save(items)
            return item

    def list(self) -> list[Item]:
        with self._lock:
            return list(self._load().values())

    def get(self, item_id: str) -> Item | None:
        with self._lock:
            return self._load().get(item_id)

    def delete(self, item_id: str) -> bool:
        with self._lock:
            items = self._load()
            if item_id not in items:
                return False
            del items[item_id]
            self._save(items)
            return True

    def ping(self) -> bool:
        return self._path.parent.exists()


class RedisStorage:
    """Redis — main data storage for the production version.

    Items are stored in a hash `pyapi:items` (field = id, value = JSON).
    The client connects lazily (on the first request), so the application
    starts even before the Redis instance is ready.
    """

    def __init__(self, url: str) -> None:
        import redis  # noqa: PLC0415 — import here, so memory/file work without the package

        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._key = "pyapi:items"

    def create(self, fqdn: str, type: str) -> Item:
        item = Item.new(fqdn, type)
        self._client.hset(
            self._key, item.id, json.dumps(asdict(item), ensure_ascii=False)
        )
        return item

    def list(self) -> list[Item]:
        raw = self._client.hgetall(self._key)
        return [Item(**json.loads(value)) for value in raw.values()]

    def get(self, item_id: str) -> Item | None:
        raw = self._client.hget(self._key, item_id)
        return Item(**json.loads(raw)) if raw else None

    def delete(self, item_id: str) -> bool:
        return self._client.hdel(self._key, item_id) > 0

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:
            return False


def build_storage(backend: str, data_dir: str, redis_url: str) -> Storage:
    backend = backend.lower()
    if backend == "memory":
        return MemoryStorage()
    if backend == "file":
        return FileStorage(Path(data_dir) / "items.json")
    if backend == "redis":
        return RedisStorage(redis_url)
    raise ValueError(
        f"Unknown STORAGE_BACKEND={backend!r}; expected: memory | file | redis"
    )
