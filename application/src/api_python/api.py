"""py-api — REST API с token authorization and memory/file/redis storage.

Endpoints:
  GET    /healthz            — check health
  POST   /api/v1/items       — create item (Bearer token)
  GET    /api/v1/items       — list items
  GET    /api/v1/items/{id}  — get item
  DELETE /api/v1/items/{id}  — delete item
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from .config import settings
from .storage import Item, build_storage

logger = logging.getLogger("py-api")

storage = build_storage(settings.STORAGE_BACKEND, settings.DATA_DIR, settings.REDIS_URL)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "Starting py-api: storage=%s data_dir=%s",
        settings.STORAGE_BACKEND,
        settings.DATA_DIR,
    )
    yield


app = FastAPI(
    title="py-api",
    version="1.0.0",
    description="API: Bearer-token auth + memory/file/redis storage",
    lifespan=lifespan,
)


class ItemIn(BaseModel):
    fqdn: str = Field(min_length=1, max_length=100, examples=["demo"])
    type: str = Field(default="", max_length=4096, examples=["hello world"])


class ItemOut(BaseModel):
    id: str
    fqdn: str
    type: str
    created_at: str


def _to_out(item: Item) -> ItemOut:
    return ItemOut(
        id=item.id, fqdn=item.fqdn, type=item.type, created_at=item.created_at
    )


# ---------- authorization ----------


def require_token(authorization: str = Header(default="")) -> None:
    """Проверяет заголовок `Authorization: Bearer <token>`."""
    scheme, _, token = authorization.partition(" ")
    if (
        scheme.lower() != "bearer"
        or not token
        or not secrets.compare_digest(token, settings.API_TOKEN.get_secret_value())
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------- endpoints ----------


@app.get("/healthz", tags=["ops"])
def healthz() -> dict[str, str]:
    """Готовность: для redis дополнительно проверяем PING (нужен для readiness)."""
    if not storage.ping():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="storage is not available",
        )
    return {"status": "ok", "storage": settings.STORAGE_BACKEND}


@app.post(
    "/api/v1/items",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_token)],
    tags=["items"],
)
def create_item(body: ItemIn) -> ItemOut:
    return _to_out(storage.create(body.fqdn, body.type))


@app.get(
    "/api/v1/items",
    response_model=list[ItemOut],
    dependencies=[Depends(require_token)],
    tags=["items"],
)
def list_items() -> list[ItemOut]:
    return [_to_out(item) for item in storage.list()]


@app.get(
    "/api/v1/items/{item_id}",
    response_model=ItemOut,
    dependencies=[Depends(require_token)],
    tags=["items"],
)
def get_item(item_id: str) -> ItemOut:
    item = storage.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return _to_out(item)


@app.delete(
    "/api/v1/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_token)],
    tags=["items"],
)
def delete_item(item_id: str) -> None:
    if not storage.delete(item_id):
        raise HTTPException(status_code=404, detail="Item not found")
