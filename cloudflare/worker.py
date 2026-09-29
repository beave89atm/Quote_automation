"""Cloudflare Python worker for the hosted queue API.

Static files come from Workers assets (``frontend/dist``). This entry serves
``/api/*`` only. It does not import the full application module: PyMuPDF and
the quoting engine stay on the shop box.
"""

from __future__ import annotations

_app = None


def _header_pairs(request: object) -> list[tuple[str, str]]:
    raw = getattr(request, "headers", None)
    if raw is None:
        return []
    items = getattr(raw, "items", None)
    if callable(items):
        return [(str(key), str(value)) for key, value in items()]
    pairs: list[tuple[str, str]] = []
    try:
        for key in raw:  # type: ignore[union-attr]
            pairs.append((str(key), str(raw[key])))  # type: ignore[index]
    except Exception:
        return []
    return pairs


async def _body(request: object, method: str) -> bytes:
    if method in {"GET", "HEAD"}:
        return b""
    reader = getattr(request, "bytes", None)
    if callable(reader):
        data = reader()
        if hasattr(data, "__await__"):
            data = await data
        return data or b""
    reader = getattr(request, "text", None)
    if callable(reader):
        data = reader()
        if hasattr(data, "__await__"):
            data = await data
        return (data or "").encode("utf-8")
    return b""


async def on_fetch(request: object) -> object:
    from workers import Response

    from app.hosted_asgi import build_hosted_app, run_asgi

    global _app
    if _app is None:
        _app = build_hosted_app()
    method = str(getattr(request, "method", "GET") or "GET").upper()
    status, raw_headers, payload = await run_asgi(
        _app,
        method=method,
        url=str(getattr(request, "url", "https://worker.local/")),
        headers=_header_pairs(request),
        body=await _body(request, method),
    )
    headers: dict[str, str] = {}
    for key, value in raw_headers:
        name = key.decode("utf-8") if isinstance(key, bytes) else str(key)
        if name.lower() == "content-length":
            continue
        headers[name] = value.decode("utf-8") if isinstance(value, bytes) else str(value)
    return Response(payload, status=status, headers=headers)
