from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class SecturaFabConfig:
    """Connection settings for the SecturaFAB API."""

    # REST calls go to the API host (avoids Cloudflare on the marketing site).
    base_url: str = "https://api.secturafab.com"
    # Token endpoint — www host accepts client_credentials (non-www returns unsupported_grant_type).
    token_url_override: str = "https://www.secturafab.com/token"
    client_id: str = ""
    client_secret: str = ""
    # Legacy resource-owner password grant (kept as fallback).
    username: str = ""
    password: str = ""
    tenant: str = ""
    timeout_seconds: float = 60.0

    @property
    def token_url(self) -> str:
        if self.token_url_override:
            return self.token_url_override.rstrip("/")
        return f"{self.base_url.rstrip('/')}/token"

    @property
    def api_root(self) -> str:
        return f"{self.base_url.rstrip('/')}/api"

    @property
    def uses_client_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def require_credentials(self) -> None:
        if self.uses_client_credentials:
            return
        if self.username and self.password:
            return
        raise ValueError(
            "Missing SecturaFAB credentials. Set SECTURAFAB_CLIENT_ID and "
            "SECTURAFAB_CLIENT_SECRET from https://secturafab.com/apikey "
            "(preferred), or SECTURAFAB_USERNAME / SECTURAFAB_PASSWORD."
        )

    @classmethod
    def from_env(cls, env_file: str | None = ".env") -> "SecturaFabConfig":
        if env_file:
            load_dotenv(env_file, override=False)
        return cls(
            base_url=os.getenv("SECTURAFAB_BASE_URL", "https://api.secturafab.com").rstrip(
                "/"
            ),
            token_url_override=os.getenv(
                "SECTURAFAB_TOKEN_URL", "https://www.secturafab.com/token"
            ).rstrip("/"),
            client_id=os.getenv("SECTURAFAB_CLIENT_ID", "").strip(),
            client_secret=os.getenv("SECTURAFAB_CLIENT_SECRET", "").strip(),
            username=os.getenv("SECTURAFAB_USERNAME", "").strip(),
            password=os.getenv("SECTURAFAB_PASSWORD", "").strip(),
            tenant=os.getenv("SECTURAFAB_TENANT", "").strip(),
            timeout_seconds=float(os.getenv("SECTURAFAB_TIMEOUT_SECONDS", "60")),
        )
