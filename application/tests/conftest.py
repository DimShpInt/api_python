"""
Global pytest fixtures for tests in this directory and subdirectories.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


def pytest_configure() -> None:
    os.environ["API_TOKEN"] = "test-token"
    os.environ["STORAGE_BACKEND"] = "memory"


@pytest.fixture()
def client() -> Iterator[TestClient]:
    api = importlib.import_module("api_python.api")

    if hasattr(api.storage, "_items"):
        api.storage._items.clear()

    with TestClient(api.app) as test_client:
        yield test_client


AUTH = {"Authorization": "Bearer test-token"}
