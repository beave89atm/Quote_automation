"""Pluggable sign-in for the hosted front door.

Local dev keeps the shared password. Entra, Auth.js, and Clerk all pass
the same claim check; switching them is ``HOSTED_AUTH_PROVIDER``. Token
signature verification fail-closes until a verifier is configured. This
module does not call Microsoft, Auth.js, or Clerk.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlencode

from fastapi import Header, HTTPException, status

HOSTED_TOKEN_HEADER = "X-Hosted-Token"
_SESSION_HOURS = 12


class AuthRejected(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class Identity:
    email: str
    role: str
    tenant: str = ""


class RejectingVerifier:
    """No network and no unsigned tokens."""

    def verify(self, token: str) -> dict[str, Any]:
        del token
        raise AuthRejected("verifier_not_configured")


_verifier: RejectingVerifier | Callable[[str], dict[str, Any]] | None = None


def reset_verifier_for_tests() -> None:
    global _verifier
    _verifier = None
    reset_jwks_cache_for_tests()


def set_verifier_for_tests(fn: Callable[[str], dict[str, Any]]) -> None:
    global _verifier
    _verifier = fn


def provider_name() -> str:
    raw = (os.getenv("HOSTED_AUTH_PROVIDER") or "local").strip().lower()
    if raw not in {"local", "entra", "authjs", "clerk"}:
        return "local"
    return raw


def auth_domain() -> str:
    return (os.getenv("HOSTED_AUTH_DOMAIN") or "kannonmfg.com").strip().lower()


def auth_tenant_id() -> str:
    return (os.getenv("HOSTED_AUTH_TENANT_ID") or "").strip()


def _split_emails(raw: str) -> set[str]:
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def admin_emails() -> set[str]:
    return _split_emails(os.getenv("HOSTED_AUTH_ADMINS") or "")


def user_emails() -> set[str]:
    return _split_emails(os.getenv("HOSTED_AUTH_USERS") or "")


def authorize_claims(claims: dict[str, Any], *, provider: str | None = None) -> Identity:
    """Allow-list and tenant gate. ``claims`` must already be verified."""
    chosen = provider or provider_name()
    email = str(claims.get("preferred_username") or claims.get("email") or "").strip().lower()
    if "@" not in email:
        raise AuthRejected("email_missing")
    domain = email.split("@", 1)[1]
    if domain != auth_domain():
        raise AuthRejected("wrong_domain")
    tenant = auth_tenant_id()
    if chosen != "local":
        if not tenant:
            raise AuthRejected("tenant_not_configured")
        if str(claims.get("tid") or "") != tenant:
            raise AuthRejected("wrong_tenant")
    if email in admin_emails():
        role = "admin"
    elif email in user_emails():
        role = "user"
    else:
        raise AuthRejected("not_allow_listed")
    return Identity(email=email, role=role, tenant=tenant)


_jwks_cache: dict[str, Any] = {"url": "", "keys": [], "at": 0.0}
_JWKS_TTL_S = 3600


def reset_jwks_cache_for_tests() -> None:
    _jwks_cache["url"] = ""
    _jwks_cache["keys"] = []
    _jwks_cache["at"] = 0.0


def entra_client_id() -> str:
    return (os.getenv("HOSTED_ENTRA_CLIENT_ID") or "").strip()


def entra_tenant() -> str:
    """Auth tenant and Entra tenant must name the same directory."""
    auth_tenant = auth_tenant_id()
    entra = (os.getenv("HOSTED_ENTRA_TENANT_ID") or "").strip()
    if auth_tenant and entra and auth_tenant != entra:
        return ""
    return auth_tenant or entra


def entra_jwks_url() -> str:
    explicit = (os.getenv("HOSTED_ENTRA_JWKS_URL") or "").strip()
    if explicit:
        return explicit
    tenant = entra_tenant()
    if not tenant:
        return ""
    return f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys"


def entra_issuer() -> str:
    tenant = entra_tenant()
    if not tenant:
        return ""
    return f"https://login.microsoftonline.com/{tenant}/v2.0"


def entra_configured() -> bool:
    return bool(entra_client_id() and entra_tenant() and entra_jwks_url())


def dev_bypass_allowed(hostname: str) -> bool:
    if (os.getenv("HOSTED_AUTH_DEV") or "").strip() != "1":
        return False
    host = (hostname or "").split(":")[0].strip().lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def _fetch_jwks(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise AuthRejected("verifier_not_configured")
    return payload


def _jwks_keys(url: str, *, force: bool = False) -> list[dict[str, Any]]:
    now = time.time()
    fresh = (
        not force
        and _jwks_cache["url"] == url
        and _jwks_cache["keys"]
        and now - float(_jwks_cache["at"]) < _JWKS_TTL_S
    )
    if fresh:
        return list(_jwks_cache["keys"])
    payload = _fetch_jwks(url)
    keys = [row for row in payload["keys"] if isinstance(row, dict)]
    _jwks_cache["url"] = url
    _jwks_cache["keys"] = keys
    _jwks_cache["at"] = now
    return keys


class EntraVerifier:
    """RS256 ID token check. Fetches JWKS only when Entra is configured."""

    def verify(self, token: str) -> dict[str, Any]:
        if not entra_configured():
            raise AuthRejected("verifier_not_configured")
        import jwt
        from jwt import PyJWK

        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthRejected("token_rejected") from exc
        kid = str(header.get("kid") or "")
        if header.get("alg") != "RS256" or not kid:
            raise AuthRejected("token_rejected")
        url = entra_jwks_url()
        key_dict = _find_jwk(_jwks_keys(url), kid)
        if key_dict is None:
            key_dict = _find_jwk(_jwks_keys(url, force=True), kid)
        if key_dict is None:
            raise AuthRejected("token_rejected")
        try:
            claims = jwt.decode(
                token,
                PyJWK.from_dict(key_dict).key,
                algorithms=["RS256"],
                audience=entra_client_id(),
                issuer=entra_issuer(),
                options={"require": ["exp", "iss", "aud"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthRejected("token_expired") from exc
        except jwt.InvalidAudienceError as exc:
            raise AuthRejected("wrong_audience") from exc
        except jwt.InvalidIssuerError as exc:
            raise AuthRejected("wrong_issuer") from exc
        except jwt.PyJWTError as exc:
            raise AuthRejected("token_rejected") from exc
        if not isinstance(claims, dict):
            raise AuthRejected("token_rejected")
        if str(claims.get("tid") or "") != entra_tenant():
            raise AuthRejected("wrong_tenant")
        return claims


def _find_jwk(keys: list[dict[str, Any]], kid: str) -> dict[str, Any] | None:
    for row in keys:
        if str(row.get("kid") or "") == kid:
            return row
    return None


def verify_bearer_claims(token: str) -> dict[str, Any]:
    verifier = _verifier
    if verifier is None:
        verifier = EntraVerifier() if provider_name() == "entra" else RejectingVerifier()
    if isinstance(verifier, (RejectingVerifier, EntraVerifier)):
        return verifier.verify(token)
    claims = verifier(token)
    if not isinstance(claims, dict):
        raise AuthRejected("verifier_not_configured")
    return claims


def entra_authorize_url() -> str | None:
    tenant = (os.getenv("HOSTED_ENTRA_TENANT_ID") or auth_tenant_id()).strip()
    client_id = (os.getenv("HOSTED_ENTRA_CLIENT_ID") or "").strip()
    redirect = (os.getenv("HOSTED_ENTRA_REDIRECT_URI") or "").strip()
    if not tenant or not client_id or not redirect:
        return None
    query = urlencode(
        {
            "client_id": client_id,
            "response_type": "id_token",
            "response_mode": "form_post",
            "redirect_uri": redirect,
            "scope": "openid profile email",
            "nonce": secrets.token_urlsafe(12),
        }
    )
    return f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{query}"


def auth_config() -> dict[str, Any]:
    provider = provider_name()
    hint: dict[str, Any] = {
        "provider": provider,
        "domain": auth_domain(),
        "mode": "password" if provider == "local" else "redirect",
        "authorize_url": None,
        "client_id": entra_client_id() if provider == "entra" else "",
        "tenant_id": auth_tenant_id() if provider == "entra" else "",
        "redirect_uri": (os.getenv("HOSTED_ENTRA_REDIRECT_URI") or "").strip() if provider == "entra" else "",
        "dev_bypass": (os.getenv("HOSTED_AUTH_DEV") or "").strip() == "1",
    }
    if provider == "entra":
        hint["authorize_url"] = entra_authorize_url()
    elif provider == "authjs":
        hint["authorize_url"] = (os.getenv("HOSTED_AUTHJS_SIGNIN_URL") or "").strip() or None
    elif provider == "clerk":
        hint["authorize_url"] = (os.getenv("HOSTED_CLERK_SIGNIN_URL") or "").strip() or None
    return hint


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_token() -> tuple[str, str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=_SESSION_HOURS)
    return token, hash_token(token), expires


def check_local_password(password: str) -> bool:
    from quote_core.config import load_shop_rates

    from .paths import RATES_PATH

    expected = load_shop_rates(RATES_PATH).shared_password or ""
    if not expected:
        return False
    return secrets.compare_digest(password, expected)


def require_worker(
    x_worker_token: str | None = Header(default=None, alias="X-Worker-Token"),
) -> str:
    expected = (os.getenv("HOSTED_WORKER_TOKEN") or "").strip()
    got = (x_worker_token or "").strip()
    if not expected or not got or not secrets.compare_digest(got, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="worker_unauthorized")
    return "worker"
