from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class SecturaFabConfig:
    """Connection settings for the SecturaFAB API."""

    base_url: str = "https://www.secturafab.com"
    username: str = ""
    password: str = ""
    tenant: str = ""
    client_id: str = ""
    timeout_seconds: float = 60.0

    @property
    def token_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/token"

    @property
    def api_root(self) -> str:
        return f"{self.base_url.rstrip('/')}/api"

    def require_credentials(self) -> None:
        missing = [
            name
            for name, value in (
                ("SECTURAFAB_USERNAME", self.username),
                ("SECTURAFAB_PASSWORD", self.password),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "Missing required credentials: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and fill them in."
            )

    @classmethod
    def from_env(cls, env_file: str | None = ".env") -> "SecturaFabConfig":
        if env_file:
            load_dotenv(env_file, override=False)
        return cls(
            base_url=os.getenv("SECTURAFAB_BASE_URL", "https://www.secturafab.com").rstrip(
                "/"
            ),
            username=os.getenv("SECTURAFAB_USERNAME", "").strip(),
            password=os.getenv("SECTURAFAB_PASSWORD", "").strip(),
            tenant=os.getenv("SECTURAFAB_TENANT", "").strip(),
            client_id=os.getenv("SECTURAFAB_CLIENT_ID", "").strip(),
            timeout_seconds=float(os.getenv("SECTURAFAB_TIMEOUT_SECONDS", "60")),
        )
