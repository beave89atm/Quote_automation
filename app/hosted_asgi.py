"""Slim ASGI app for hosts that cannot import the quoting engine.

Vercel loads ``app.main`` from ``api/index.py``. Cloudflare Workers load this
module from ``cloudflare/worker.py``. Both include the same hosted router.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI

from .hosted_platform import platform_name
from .hosted_routes import router as hosted_router


def build_hosted_app() -> FastAPI:
    app = FastAPI(title="Kannon Quote Queue", version="0.1.0")
    app.include_router(hosted_router)

    @app.on_event("startup")
    def _startup() -> None:
        from .auth import load_quote_password_env, warn_if_quote_password_missing

        load_quote_password_env()
        warn_if_quote_password_missing()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "platform": platform_name()}

    return app


async def run_asgi(
    app: Any,
    *,
    method: str,
    url: str,
    headers: list[tuple[str, str]],
    body: bytes,
) -> tuple[int, list[tuple[bytes, bytes]], bytes]:
    """One HTTP call through an ASGI app. Used by the Cloudflare fetch adapter."""
    parsed = urlsplit(url)
    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": parsed.scheme or "https",
        "path": parsed.path or "/",
        "raw_path": (parsed.path or "/").encode("utf-8"),
        "query_string": (parsed.query or "").encode("utf-8"),
        "headers": [(key.lower().encode("utf-8"), value.encode("utf-8")) for key, value in headers],
        "client": ("0.0.0.0", 0),
        "server": (parsed.hostname or "worker", 443),
    }
    sent: dict[str, Any] = {"status": 500, "headers": []}
    chunks: list[bytes] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            sent["status"] = int(message["status"])
            sent["headers"] = list(message.get("headers") or [])
        elif message["type"] == "http.response.body":
            chunk = message.get("body") or b""
            if chunk:
                chunks.append(chunk)

    await app(scope, receive, send)
    return int(sent["status"]), list(sent["headers"]), b"".join(chunks)
