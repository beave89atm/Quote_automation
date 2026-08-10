from __future__ import annotations

from typing import Any

import requests

from .auth import AccessToken, SecturaFabAuthError, fetch_access_token
from .config import SecturaFabConfig


class SecturaFabApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class SecturaFabClient:
    """Thin authenticated HTTP client for SecturaFAB REST endpoints."""

    def __init__(
        self,
        config: SecturaFabConfig | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config or SecturaFabConfig.from_env()
        self.session = session or requests.Session()
        self._token: AccessToken | None = None

    def authenticate(self, force: bool = False) -> AccessToken:
        if self._token and not self._token.is_expired and not force:
            return self._token
        self._token = fetch_access_token(self.config, session=self.session)
        return self._token

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
        allow_absolute: bool = False,
        retry_on_auth_error: bool = True,
    ) -> requests.Response:
        token = self.authenticate()
        if path.startswith("http://") or path.startswith("https://"):
            if not allow_absolute:
                raise ValueError("Absolute URLs require allow_absolute=True")
            url = path
        else:
            url = f"{self.config.api_root}/{path.lstrip('/')}"

        req_headers = {
            "Accept": "application/json",
            "Authorization": token.authorization_header,
        }
        if headers:
            req_headers.update(headers)

        response = self.session.request(
            method=method.upper(),
            url=url,
            params=params,
            json=json,
            data=data,
            headers=req_headers,
            timeout=self.config.timeout_seconds,
        )

        if response.status_code in (401, 403) and retry_on_auth_error:
            self.authenticate(force=True)
            assert self._token is not None
            req_headers["Authorization"] = self._token.authorization_header
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json,
                data=data,
                headers=req_headers,
                timeout=self.config.timeout_seconds,
            )

        return response

    def get_json(self, path: str, **kwargs: Any) -> Any:
        """GET JSON with short retries on Cloudflare/origin overload (502/503/504)."""
        import time

        retries = int(kwargs.pop("retries", 4))
        last_exc: SecturaFabApiError | None = None
        for attempt in range(1, max(1, retries) + 1):
            response = self.request("GET", path, **kwargs)
            try:
                return self._parse_or_raise(response)
            except SecturaFabApiError as exc:
                last_exc = exc
                if exc.status_code not in {502, 503, 504} or attempt >= retries:
                    raise
                time.sleep(min(12.0, 1.5 * attempt))
        assert last_exc is not None
        raise last_exc

    def post_json(self, path: str, payload: Any = None, **kwargs: Any) -> Any:
        response = self.request("POST", path, json=payload, **kwargs)
        return self._parse_or_raise(response)

    def put_json(self, path: str, payload: Any = None, **kwargs: Any) -> Any:
        response = self.request("PUT", path, json=payload, **kwargs)
        return self._parse_or_raise(response)

    def delete_json(self, path: str, **kwargs: Any) -> Any:
        response = self.request("DELETE", path, **kwargs)
        if response.status_code == 204:
            return None
        return self._parse_or_raise(response)

    def post_multipart(
        self,
        path: str,
        *,
        files: list[tuple[str, tuple[str, Any, str]]],
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        """
        POST multipart/form-data (CAD / drawing uploads).

        `files` entries are requests-style:
          ("files", (filename, fileobj, content_type))
        """
        token = self.authenticate()
        url = f"{self.config.api_root}/{path.lstrip('/')}"
        req_headers = {
            "Accept": "application/json",
            "Authorization": token.authorization_header,
        }
        if headers:
            req_headers.update(headers)
        # Do not set Content-Type — requests adds the multipart boundary.
        response = self.session.post(
            url,
            params=params,
            files=files,
            headers=req_headers,
            timeout=timeout or max(self.config.timeout_seconds, 180.0),
        )
        return self._parse_or_raise(response)

    def whoami(self) -> Any:
        """Best-effort current-user probe across common Account routes."""
        candidates = [
            "Account/UserInfo",
            "Account/Me",
            "account/userinfo",
            "Users/Me",
            "User",
        ]
        errors: list[str] = []
        for path in candidates:
            response = self.request("GET", path, retry_on_auth_error=False)
            if response.status_code < 400:
                return self._parse_or_raise(response)
            errors.append(f"{path} -> {response.status_code}")
        raise SecturaFabApiError(
            "Could not resolve current user via known Account routes: "
            + "; ".join(errors)
        )

    @staticmethod
    def _parse_or_raise(response: requests.Response) -> Any:
        if response.status_code >= 400:
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = response.text[:1000]
            detail = ""
            if isinstance(body, dict):
                for key in ("ExceptionMessage", "detail", "Message", "title"):
                    if body.get(key):
                        detail = f" — {body.get(key)}"
                        break
            raise SecturaFabApiError(
                f"API request failed ({response.status_code}) for {response.url}{detail}",
                status_code=response.status_code,
                body=body,
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text


def ping_token_endpoint(config: SecturaFabConfig | None = None) -> dict[str, Any]:
    """
    Validate credentials by requesting a token.

    Returns a redacted summary suitable for logging.
    """
    cfg = config or SecturaFabConfig.from_env()
    try:
        token = fetch_access_token(cfg)
    except (SecturaFabAuthError, ValueError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "token_url": cfg.token_url,
            "api_base": cfg.base_url,
            "grant": "client_credentials" if cfg.uses_client_credentials else "password",
        }
    return {
        "ok": True,
        "token_type": token.token_type,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "access_token_preview": f"{token.access_token[:8]}…",
        "raw_keys": sorted((token.raw or {}).keys()),
        "token_url": cfg.token_url,
        "api_base": cfg.base_url,
        "grant": "client_credentials" if cfg.uses_client_credentials else "password",
    }
