"""QUOTE_APP_PASSWORD is the only staff password. Unset refuses login."""

from __future__ import annotations

import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from quote_core.config import load_shop_rates


def test_unset_quote_app_password_refuses_login(monkeypatch, caplog) -> None:
    monkeypatch.setenv("QUOTE_APP_PASSWORD", "")
    from app.main import app

    with caplog.at_level(logging.ERROR, logger="uvicorn.error"):
        with TestClient(app) as client:
            denied = client.post("/api/login", json={"password": "anything"})
            blank = client.post("/api/login", json={"password": ""})
            rates = client.get("/api/rates")

    assert denied.status_code == 401
    assert denied.json()["detail"] == "Login unavailable: QUOTE_APP_PASSWORD is unset or blank"
    assert blank.status_code == 401
    assert blank.json()["detail"] == denied.json()["detail"]
    assert rates.status_code == 401
    assert "QUOTE_APP_PASSWORD" in caplog.text
    assert "shop_rates.yaml" in caplog.text
    assert "refused" in caplog.text


def test_blank_env_password_refuses_login(monkeypatch) -> None:
    monkeypatch.setenv("QUOTE_APP_PASSWORD", "   ")
    from app.auth import login

    with pytest.raises(HTTPException) as exc:
        login("   ")
    assert exc.value.status_code == 401
    assert "QUOTE_APP_PASSWORD" in str(exc.value.detail)


def test_wrong_password_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("QUOTE_APP_PASSWORD", "test-quote-password")
    from app.auth import login

    with pytest.raises(HTTPException) as exc:
        login("nope")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid password"


def test_yaml_shared_password_is_ignored(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("QUOTE_APP_PASSWORD", "from-env")
    cfg = tmp_path / "shop_rates.yaml"
    cfg.write_text(
        "app:\n  shared_password: from-yaml\n  default_efficiency_pct: 85\n",
        encoding="utf-8",
    )
    rates = load_shop_rates(cfg)
    assert "shared_password" not in (rates.raw.get("app") or {})
    assert not hasattr(rates, "shared_password")

    from app.auth import login

    assert login("from-env")
    with pytest.raises(HTTPException) as exc:
        login("from-yaml")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid password"


def test_unset_password_rejects_existing_session(monkeypatch) -> None:
    monkeypatch.setenv("QUOTE_APP_PASSWORD", "test-quote-password")
    from app.auth import login, require_auth

    token = login("test-quote-password")
    monkeypatch.delenv("QUOTE_APP_PASSWORD", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_auth(x_app_token=token)
    assert exc.value.status_code == 401


def test_hosted_local_password_uses_env(monkeypatch) -> None:
    monkeypatch.setenv("QUOTE_APP_PASSWORD", "test-quote-password")
    from app.hosted_auth import check_local_password

    assert check_local_password("test-quote-password") is True
    assert check_local_password("other") is False
    monkeypatch.setenv("QUOTE_APP_PASSWORD", "")
    assert check_local_password("test-quote-password") is False
    assert check_local_password("") is False
