"""Offline API smoke — health, login, auth gate, jobs list.

Uses an isolated KANNON_DATA_DIR so smoke does not depend on production jobs.db.
Isolation is fixture-scoped and restored afterward so other tests keep the real DB.
"""

from __future__ import annotations

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

_RELOAD_MODULES = (
    "app.paths",
    "app.db",
    "app.auth",
    "app.services",
    "app.main",
)


def _reload_app_modules() -> None:
    for mod_name in _RELOAD_MODULES:
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])
        else:
            importlib.import_module(mod_name)


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory):
    data_dir = tmp_path_factory.mktemp("kannon_smoke")
    previous = os.environ.get("KANNON_DATA_DIR")
    os.environ["KANNON_DATA_DIR"] = str(data_dir)
    _reload_app_modules()

    from app.main import app

    with TestClient(app) as c:
        yield c

    if previous is None:
        os.environ.pop("KANNON_DATA_DIR", None)
    else:
        os.environ["KANNON_DATA_DIR"] = previous
    _reload_app_modules()


@pytest.fixture(scope="module")
def password(client: TestClient) -> str:
    from app.paths import RATES_PATH
    from quote_core.config import load_shop_rates

    rates = load_shop_rates(RATES_PATH)
    return rates.shared_password or ""


@pytest.fixture(scope="module")
def token(client: TestClient, password: str) -> str:
    if not password:
        pytest.skip("shared_password empty — auth gate disabled")
    res = client.post("/api/login", json={"password": password})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("token")
    return str(body["token"])


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_login(client: TestClient, password: str) -> None:
    if not password:
        res = client.post("/api/login", json={"password": ""})
        assert res.status_code == 200
        assert res.json().get("token")
        return
    res = client.post("/api/login", json={"password": password})
    assert res.status_code == 200
    body = res.json()
    assert body.get("token")
    assert "default_efficiency_pct" in body


def test_rates_requires_auth(client: TestClient, password: str) -> None:
    if not password:
        pytest.skip("auth disabled")
    res = client.get("/api/rates")
    assert res.status_code == 401


def test_rates_with_token(client: TestClient, token: str) -> None:
    res = client.get("/api/rates", headers={"X-App-Token": token})
    assert res.status_code == 200
    body = res.json()
    assert "weld_ipm" in body
    assert body["weld_ipm"].get("1/4") == 3.5


def test_jobs_with_token(client: TestClient, token: str) -> None:
    res = client.get("/api/jobs", headers={"X-App-Token": token})
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)


def test_openapi_includes_batch_routes(client: TestClient) -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json().get("paths") or {}
    assert "/api/jobs/batch" in paths
    assert "post" in paths["/api/jobs/batch"]
    assert "/api/jobs/batch-push" in paths
    assert "post" in paths["/api/jobs/batch-push"]
    assert "/api/capabilities" in paths
    assert "/api/secturafab/status" in paths


def test_batch_post_is_not_method_not_allowed(client: TestClient, token: str) -> None:
    """Regression: stale/shadowed routes returned 405 for POST /api/jobs/batch."""
    res = client.post(
        "/api/jobs/batch",
        headers={"X-App-Token": token},
    )
    assert res.status_code != 405, res.text
    assert res.status_code in {400, 422}


def test_batch_push_post_is_not_method_not_allowed(
    client: TestClient, token: str
) -> None:
    res = client.post(
        "/api/jobs/batch-push",
        headers={"X-App-Token": token},
        json={},
    )
    assert res.status_code != 405, res.text
    assert res.status_code in {400, 422}


def test_capabilities_with_token(client: TestClient, token: str) -> None:
    res = client.get("/api/capabilities", headers={"X-App-Token": token})
    assert res.status_code == 200
    body = res.json()
    assert "tube_laser" in (body.get("outsourced") or {})
    assert "powder_coating" in (body.get("outsourced") or {})


def test_secturafab_status_without_keys(client: TestClient, token: str) -> None:
    res = client.get("/api/secturafab/status", headers={"X-App-Token": token})
    assert res.status_code == 200
    body = res.json()
    assert "configured" in body
    assert body.get("message")
