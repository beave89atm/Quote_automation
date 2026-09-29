"""R2 and SharePoint blob stores. Local and Vercel stores stay in hosted_queue."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .hosted_auth import entra_client_id, entra_tenant
from .hosted_queue import ALLOWED_SUFFIXES, MAX_UPLOAD_BYTES, BlobNotProvisioned

_GRAPH = "https://graph.microsoft.com/v1.0"
_graph_cache = {"token": "", "until": 0.0}


def reset_sharepoint_cache() -> None:
    _graph_cache["token"] = ""
    _graph_cache["until"] = 0.0


def store_for(provider: str) -> R2Store | SharePointStore:
    if provider == "r2":
        return R2Store()
    if provider == "sharepoint":
        return SharePointStore()
    raise BlobNotProvisioned("unknown_blob_provider")


def _check_upload(filename: str, data: bytes) -> str:
    name = Path(filename).name
    if Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("bad_file_type")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("file_too_large")
    return name


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _r2_settings() -> tuple[str, str, str, str]:
    account = (os.getenv("R2_ACCOUNT_ID") or "").strip()
    bucket = (os.getenv("R2_BUCKET") or "").strip()
    access = (os.getenv("R2_ACCESS_KEY_ID") or "").strip()
    secret = (os.getenv("R2_SECRET_ACCESS_KEY") or "").strip()
    endpoint = (os.getenv("R2_ENDPOINT") or "").strip()
    if not access or not secret or not bucket or not (account or endpoint):
        raise BlobNotProvisioned("r2_not_configured")
    if not endpoint:
        endpoint = f"https://{account}.r2.cloudflarestorage.com"
    return endpoint.rstrip("/"), bucket, access, secret


def _r2_url(endpoint: str, bucket: str, key: str) -> tuple[str, str]:
    encoded_bucket = urllib.parse.quote(bucket, safe="")
    encoded_key = urllib.parse.quote(key, safe="/")
    path = f"/{encoded_bucket}/{encoded_key}"
    return endpoint + path, path


def _signed_headers(method: str, url: str, access: str, secret: str) -> dict[str, str]:
    parsed = urllib.parse.urlsplit(url)
    now = datetime.now(timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    payload_hash = "UNSIGNED-PAYLOAD"
    canonical_headers = (
        f"host:{parsed.hostname}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = (
        f"{method}\n{parsed.path}\n\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    scope = f"{date_stamp}/auto/s3/aws4_request"
    string_to_sign = (
        "AWS4-HMAC-SHA256\n"
        f"{amz_date}\n"
        f"{scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )
    signing = _hmac(_hmac(_hmac(_hmac(("AWS4" + secret).encode("utf-8"), date_stamp), "auto"), "s3"), "aws4_request")
    signature = hmac.new(signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={access}/{scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )
    if secret and secret in url:
        raise BlobNotProvisioned("r2_not_configured")
    return {
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
        "Authorization": authorization,
    }


def _open(req: urllib.request.Request) -> bytes:
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        code = exc.code
        raise BlobNotProvisioned(f"r2_http_{code}") from None


class R2Store:
    """S3 SigV4 against Cloudflare R2. The secret never goes in the URL."""

    def put(self, filename: str, data: bytes) -> dict[str, Any]:
        endpoint, bucket, access, secret = _r2_settings()
        name = _check_upload(filename, data)
        key = f"hosted/{uuid.uuid4().hex}/{name}"
        url, _path = _r2_url(endpoint, bucket, key)
        headers = _signed_headers("PUT", url, access, secret)
        if secret in url or secret in headers.get("Authorization", ""):
            raise BlobNotProvisioned("r2_not_configured")
        req = urllib.request.Request(url, data=data, method="PUT", headers=headers)
        _open(req)
        return {"name": name, "blob_key": key, "url": url, "size": len(data)}

    def get(self, blob_key: str, *, url: str = "") -> bytes:
        del url
        endpoint, bucket, access, secret = _r2_settings()
        target, _path = _r2_url(endpoint, bucket, blob_key)
        headers = _signed_headers("GET", target, access, secret)
        req = urllib.request.Request(target, method="GET", headers=headers)
        try:
            return _open(req)
        except BlobNotProvisioned as exc:
            if str(exc) == "r2_http_404":
                raise ValueError("blob_missing") from None
            raise

    def delete(self, blob_key: str, *, url: str = "") -> None:
        del url
        if not blob_key:
            return
        endpoint, bucket, access, secret = _r2_settings()
        target, _path = _r2_url(endpoint, bucket, blob_key)
        headers = _signed_headers("DELETE", target, access, secret)
        req = urllib.request.Request(target, method="DELETE", headers=headers)
        try:
            _open(req)
        except BlobNotProvisioned as exc:
            if str(exc) == "r2_http_404":
                return
            raise


def _sharepoint_settings() -> tuple[str, str, str, str, str]:
    tenant = entra_tenant()
    client_id = entra_client_id()
    secret = (os.getenv("HOSTED_ENTRA_CLIENT_SECRET") or "").strip()
    drive = (os.getenv("HOSTED_SHAREPOINT_DRIVE_ID") or "").strip()
    folder = (os.getenv("HOSTED_SHAREPOINT_FOLDER") or "QuoteQueue").strip().strip("/")
    if not tenant or not client_id or not secret or not drive or not folder:
        raise BlobNotProvisioned("sharepoint_not_configured")
    return tenant, client_id, secret, drive, folder


def _graph_token() -> str:
    now = time.monotonic()
    cached = str(_graph_cache["token"] or "")
    if cached and now < float(_graph_cache["until"]):
        return cached
    tenant, client_id, secret, _drive, _folder = _sharepoint_settings()
    body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{urllib.parse.quote(tenant, safe='')}/oauth2/v2.0/token",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise BlobNotProvisioned(f"graph_http_{exc.code}") from None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BlobNotProvisioned("graph_token_missing") from exc
    token = str(payload.get("access_token") or "").strip() if isinstance(payload, dict) else ""
    if not token:
        raise BlobNotProvisioned("graph_token_missing")
    expires = int(payload.get("expires_in") or 3600) if isinstance(payload, dict) else 3600
    _graph_cache["token"] = token
    _graph_cache["until"] = time.monotonic() + max(30, expires - 60)
    return token


def _item_url(drive: str, path: str, *, content: bool) -> str:
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/") if part)
    base = f"{_GRAPH}/drives/{urllib.parse.quote(drive, safe='')}/root:/{encoded}"
    if content:
        return base + ":/content"
    return base


def _graph_open(url: str, token: str, *, method: str, body: bytes | None = None) -> bytes:
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/octet-stream"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise BlobNotProvisioned(f"graph_http_{exc.code}") from None


class SharePointStore:
    """Microsoft Graph upload into an existing SharePoint or OneDrive folder."""

    def put(self, filename: str, data: bytes) -> dict[str, Any]:
        _tenant, _client, secret, drive, folder = _sharepoint_settings()
        name = _check_upload(filename, data)
        key = f"hosted/{uuid.uuid4().hex}/{name}"
        token = _graph_token()
        url = _item_url(drive, f"{folder}/{key}", content=True)
        if secret in url:
            raise BlobNotProvisioned("sharepoint_not_configured")
        _graph_open(url, token, method="PUT", body=data)
        return {"name": name, "blob_key": key, "url": url, "size": len(data)}

    def get(self, blob_key: str, *, url: str = "") -> bytes:
        del url
        _tenant, _client, _secret, drive, folder = _sharepoint_settings()
        token = _graph_token()
        target = _item_url(drive, f"{folder}/{blob_key}", content=True)
        try:
            return _graph_open(target, token, method="GET")
        except BlobNotProvisioned as exc:
            if str(exc) == "graph_http_404":
                raise ValueError("blob_missing") from None
            raise

    def delete(self, blob_key: str, *, url: str = "") -> None:
        del url
        if not blob_key:
            return
        _tenant, _client, _secret, drive, folder = _sharepoint_settings()
        token = _graph_token()
        target = _item_url(drive, f"{folder}/{blob_key}", content=False)
        try:
            _graph_open(target, token, method="DELETE")
        except BlobNotProvisioned as exc:
            if str(exc) == "graph_http_404":
                return
            raise
