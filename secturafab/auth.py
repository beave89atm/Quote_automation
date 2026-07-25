from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .config import SecturaFabConfig


@dataclass
class AccessToken:
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    raw: dict[str, Any] | None = None

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        # Refresh a little early to avoid edge races.
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(seconds=30))

    @property
    def authorization_header(self) -> str:
        return f"{self.token_type} {self.access_token}"


class SecturaFabAuthError(RuntimeError):
    """Raised when OAuth token acquisition fails."""


def fetch_password_token(
    config: SecturaFabConfig,
    session: requests.Session | None = None,
) -> AccessToken:
    """
    Acquire an OAuth access token via resource-owner password credentials.

    SecturaFAB exposes POST /token (ASP.NET OAuth / Katana).
    """
    config.require_credentials()
    http = session or requests.Session()

    form: dict[str, str] = {
        "grant_type": "password",
        "username": config.username,
        "password": config.password,
    }
    if config.client_id:
        form["client_id"] = config.client_id
    if config.tenant:
        # Tenant naming varies by tenant setup; send common variants.
        form["tenant"] = config.tenant
        form["tenantId"] = config.tenant
        form["TenantId"] = config.tenant

    response = http.post(
        config.token_url,
        data=form,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=config.timeout_seconds,
    )

    if response.status_code >= 400:
        detail: Any
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:500]
        raise SecturaFabAuthError(
            f"Token request failed ({response.status_code}): {detail}"
        )

    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise SecturaFabAuthError(f"Token response missing access_token: {payload}")

    expires_at = None
    if "expires_in" in payload:
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=int(payload["expires_in"])
            )
        except (TypeError, ValueError):
            expires_at = None

    return AccessToken(
        access_token=access_token,
        token_type=str(payload.get("token_type") or "Bearer"),
        expires_at=expires_at,
        raw=payload,
    )
