from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from secturafab.auth import (
    SecturaFabAuthError,
    fetch_client_credentials_token,
    fetch_password_token,
)
from secturafab.config import SecturaFabConfig


def test_config_requires_credentials() -> None:
    cfg = SecturaFabConfig(username="", password="", client_id="", client_secret="")
    with pytest.raises(ValueError, match="SECTURAFAB_CLIENT_ID"):
        cfg.require_credentials()


def test_config_client_credentials_ok() -> None:
    cfg = SecturaFabConfig(client_id="id", client_secret="secret")
    cfg.require_credentials()
    assert cfg.uses_client_credentials
    assert cfg.token_url == "https://www.secturafab.com/token"
    assert cfg.api_root == "https://api.secturafab.com/api"


def test_fetch_client_credentials_token_success() -> None:
    cfg = SecturaFabConfig(client_id="cid", client_secret="csecret")
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "access_token": "abc123token",
        "token_type": "Bearer",
        "expires_in": 3600,
    }
    session.post.return_value = response

    token = fetch_client_credentials_token(cfg, session=session)

    assert token.access_token == "abc123token"
    assert session.post.call_args.args[0] == cfg.token_url
    kwargs = session.post.call_args.kwargs
    assert kwargs["data"]["grant_type"] == "client_credentials"
    assert kwargs["data"]["client_id"] == "cid"
    assert kwargs["data"]["client_secret"] == "csecret"


def test_fetch_password_token_success() -> None:
    cfg = SecturaFabConfig(username="user@example.com", password="secret", tenant="Acme")
    session = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {
        "access_token": "abc123token",
        "token_type": "bearer",
        "expires_in": 3600,
    }
    session.post.return_value = response

    token = fetch_password_token(cfg, session=session)

    assert token.access_token == "abc123token"
    assert token.token_type == "bearer"
    assert token.expires_at is not None
    kwargs = session.post.call_args.kwargs
    assert kwargs["data"]["grant_type"] == "password"
    assert kwargs["data"]["username"] == "user@example.com"
    assert kwargs["data"]["tenant"] == "Acme"


def test_fetch_password_token_invalid_grant() -> None:
    cfg = SecturaFabConfig(username="user@example.com", password="wrong")
    session = MagicMock()
    response = MagicMock()
    response.status_code = 400
    response.json.return_value = {
        "error": "invalid_grant",
        "error_description": "The user name or password is incorrect.",
    }
    session.post.return_value = response

    with pytest.raises(SecturaFabAuthError, match="invalid_grant"):
        fetch_password_token(cfg, session=session)


def test_auth_check_cli_missing_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECTURAFAB_USERNAME", raising=False)
    monkeypatch.delenv("SECTURAFAB_PASSWORD", raising=False)
    monkeypatch.delenv("SECTURAFAB_CLIENT_ID", raising=False)
    monkeypatch.delenv("SECTURAFAB_CLIENT_SECRET", raising=False)
    from secturafab.__main__ import main

    with patch("secturafab.__main__.SecturaFabConfig.from_env") as from_env:
        from_env.return_value = SecturaFabConfig(
            username="", password="", client_id="", client_secret=""
        )
        code = main(["auth-check"])
    assert code == 1
