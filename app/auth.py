from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Query, status

from quote_core.config import load_shop_rates

from .paths import RATES_PATH

# In-memory session tokens for v1 shared-password auth
_SESSIONS: set[str] = set()


def login(password: str) -> str:
    rates = load_shop_rates(RATES_PATH)
    expected = rates.shared_password or ""
    if expected and password != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    token = secrets.token_urlsafe(24)
    _SESSIONS.add(token)
    return token


def require_auth(
    authorization: Annotated[str | None, Header()] = None,
    x_app_token: Annotated[str | None, Header()] = None,
    token: Annotated[str | None, Query()] = None,
) -> str:
    rates = load_shop_rates(RATES_PATH)
    if not rates.shared_password:
        return "auth-disabled"

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
