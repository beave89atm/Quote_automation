from __future__ import annotations

import logging
import os
import secrets
from typing import Annotated, NoReturn

from fastapi import Header, HTTPException, Query, status

PASSWORD_ENV = "QUOTE_APP_PASSWORD"
MISSING_PASSWORD_DETAIL = "Login unavailable: QUOTE_APP_PASSWORD is unset or blank"
_MISSING_PASSWORD_LOG = (
    "QUOTE_APP_PASSWORD is unset or blank. Staff logins are refused. "
    "Set QUOTE_APP_PASSWORD in the environment. "
    "The password is not read from config/shop_rates.yaml."
)

log = logging.getLogger("uvicorn.error")

# In-memory session tokens for v1 shared-password auth
_SESSIONS: set[str] = set()


def load_quote_password_env() -> None:
    """Apply a local .env without overriding a password already in the environment."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(override=False)


def quote_app_password() -> str:
    """Staff shared password from QUOTE_APP_PASSWORD. Empty when unset or blank."""
    return (os.getenv(PASSWORD_ENV) or "").strip()


def warn_if_quote_password_missing() -> None:
    if quote_app_password():
        return
    log.error(_MISSING_PASSWORD_LOG)


def _reject_missing_password() -> NoReturn:
    warn_if_quote_password_missing()
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=MISSING_PASSWORD_DETAIL,
    )


def login(password: str) -> str:
    expected = quote_app_password()
    if not expected:
        _reject_missing_password()
    supplied = password or ""
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    token = secrets.token_urlsafe(24)
    _SESSIONS.add(token)
    return token


def require_auth(
    authorization: Annotated[str | None, Header()] = None,
    x_app_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query()] = None,
) -> str:
    if not quote_app_password():
        _reject_missing_password()

    resolved = None
    if x_app_token:
        resolved = x_app_token.strip()
    elif authorization and authorization.lower().startswith("bearer "):
        resolved = authorization[7:].strip()
    elif token:
        resolved = token.strip()

    if not resolved or resolved not in _SESSIONS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return resolved
