from __future__ import annotations

import importlib.util
import os
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def api_app() -> FastAPI:
    db_path = Path("./test_nexuscargo.db")
    if db_path.exists():
        db_path.unlink()

    os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    os.environ["AUTH_JWT_SECRET"] = "test-jwt-secret-123456789"
    os.environ["AUTH_REFRESH_SECRET"] = "test-refresh-secret-123456789"
    os.environ["EVENT_BUS_BACKEND"] = "memory"

    from libs.common.config import get_settings

    get_settings.cache_clear()

    module_path = Path("apps/api-gateway/main.py")
    spec = importlib.util.spec_from_file_location("api_gateway_main", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load api gateway module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(FastAPI, module.app)


@pytest.fixture
def client(api_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(api_app) as test_client:
        yield test_client
