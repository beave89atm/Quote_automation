"""Chrome DevTools (box debug port) — cookies + Quotes DOM AF.

Cookie HTTP GET /Quote is 302 AccessDenied (live aa86d56). CadImport and
GetItem_AddView still 200 on the same file cookie. The signed-in Chrome
Quotes tab is 200 and has input[name^=__RequestVerificationToken].

Hypothesis A: refresh the in-memory Cookie header from CDP
(Network.getCookies) and retry GET /Quote with Chrome's User-Agent.
Hypothesis B: Runtime.evaluate querySelector on the open Quotes tab and
copy name+value into the /part/create form in memory.

Never log cookie or AF token values. Name presence only.
Do not unwrap Windows Chrome. Do not ask Kyle to log in.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

SECTURA_HOST = "secturafab.com"
DEFAULT_DEBUG_PORTS = (9222, 9223, 9333)
_CDP_TIMEOUT_S = 5.0

# kendo.antiForgeryTokens: input[name^='__RequestVerificationToken']
_AF_DOM_JS = """(() => {
  const out = [];
  const seen = new Set();
  const add = (name, value) => {
    name = String(name || "");
    value = String(value || "");
    if (!name || !value || seen.has(name)) return;
    seen.add(name);
    out.push({name, value});
  };
  document.querySelectorAll('input[name^="__RequestVerificationToken"]').forEach((el) => {
    add(el.name, el.value);
  });
  const af = document.querySelector('input[name="afToken"]');
  if (af) add(af.name, af.value);
  document.querySelectorAll('meta[name="csrf-token"],meta[name="_csrf"]').forEach((el) => {
    add(el.getAttribute("name"), el.getAttribute("content"));
  });
  return out;
})()"""


def cookie_names_from_header(header: str | None) -> list[str]:
    """Cookie header names only — never values."""
    names: list[str] = []
    seen: set[str] = set()
    for part in str(header or "").split(";"):
        raw = part.strip()
        if not raw or "=" not in raw:
            continue
        name = raw.split("=", 1)[0].strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def compare_cookie_name_presence(
    file_header: str | None,
    chrome_names: list[str] | None,
) -> dict[str, list[str]]:
    """Set-Cookie / Cookie name presence. Never values."""
    file_names = set(cookie_names_from_header(file_header))
    chrome = set(str(n).strip() for n in (chrome_names or []) if str(n).strip())
    return {
        "cookie_file_names": sorted(file_names),
        "chrome_cookie_names": sorted(chrome),
        "chrome_only": sorted(chrome - file_names),
        "file_only": sorted(file_names - chrome),
    }


def _debug_candidates() -> list[str]:
    raw = (
        (os.getenv("SECTURA_CHROME_DEBUG") or os.getenv("CHROME_DEBUG_PORT") or "")
        .strip()
    )
    out: list[str] = []
    if raw:
        if raw.startswith("http://") or raw.startswith("https://"):
            out.append(raw.rstrip("/"))
        elif "://" in raw:
            out.append(raw.rstrip("/"))
        elif raw.isdigit():
            out.append(f"http://127.0.0.1:{raw}")
        else:
            out.append("http://" + raw.lstrip("/"))
    for port in DEFAULT_DEBUG_PORTS:
        url = f"http://127.0.0.1:{port}"
        if url not in out:
            out.append(url)
    return out


def _http_json(url: str, timeout: float = _CDP_TIMEOUT_S) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    if not body:
        return None
    return json.loads(body.decode("utf-8", errors="replace"))


def chrome_debug_base() -> str | None:
    """First live Chrome DevTools HTTP endpoint, or None."""
    for base in _debug_candidates():
        try:
            info = _http_json(f"{base}/json/version")
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(info, dict) and (
            info.get("webSocketDebuggerUrl") or info.get("Browser")
        ):
            return base
    return None


def chrome_version_user_agent(base: str | None = None) -> str:
    """Browser UA from /json/version — not a secret; used on Quote GETs."""
    root = base or chrome_debug_base()
    if not root:
        return ""
    try:
        info = _http_json(f"{root}/json/version")
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return ""
    if not isinstance(info, dict):
        return ""
    return str(info.get("User-Agent") or "").strip()


def _is_quotes_url(url: str) -> bool:
    raw = str(url or "").lower()
    if SECTURA_HOST not in raw:
        return False
    return "/quote" in raw


def list_chrome_targets(base: str | None = None) -> list[dict[str, Any]]:
    root = base or chrome_debug_base()
    if not root:
        return []
    try:
        rows = _http_json(f"{root}/json/list")
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        try:
            rows = _http_json(f"{root}/json")
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return []
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def quotes_tab(base: str | None = None) -> dict[str, Any] | None:
    """Prefer an open www Quotes / Quote edit tab."""
    pages = [
        t
        for t in list_chrome_targets(base)
        if str(t.get("type") or "page") == "page" and t.get("webSocketDebuggerUrl")
    ]
    quotes = [t for t in pages if _is_quotes_url(str(t.get("url") or ""))]
    def _rank(tab: dict[str, Any]) -> tuple[int, int]:
        url = str(tab.get("url") or "").lower()
        edit = 0 if ("/quote/edit" in url or "quoteorderedit" in url) else 1
        return (edit, 0 if "/quote?" in url or "/quote/" in url else 1)

    quotes.sort(key=_rank)
    if quotes:
        return quotes[0]
    sectura = [
        t
        for t in pages
        if SECTURA_HOST in str(t.get("url") or "").lower()
    ]
    return sectura[0] if sectura else None


def _ws_handshake(ws_url: str) -> socket.socket:
    parsed = urlparse(ws_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock = socket.create_connection((host, port), timeout=_CDP_TIMEOUT_S)
    sock.settimeout(_CDP_TIMEOUT_S)
    sock.sendall(req.encode("ascii"))
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            sock.close()
            raise OSError("CDP websocket handshake closed")
        buf += chunk
        if len(buf) > 64_000:
            sock.close()
            raise OSError("CDP websocket handshake too large")
    return sock


def _ws_send_text(sock: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    mask = os.urandom(4)
    header = bytearray([0x81])
    n = len(payload)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    sock.sendall(bytes(header) + mask + masked)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    out = b""
    while len(out) < n:
        chunk = sock.recv(n - len(out))
        if not chunk:
            raise OSError("CDP websocket closed")
        out += chunk
    return out


def _ws_recv_text(sock: socket.socket) -> str:
    while True:
        hdr = _recv_exact(sock, 2)
        opcode = hdr[0] & 0x0F
        masked = bool(hdr[1] & 0x80)
        length = hdr[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", _recv_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", _recv_exact(sock, 8))[0]
        mask = _recv_exact(sock, 4) if masked else b""
        payload = _recv_exact(sock, length)
        if masked:
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:
            raise OSError("CDP websocket closed")
        if opcode == 0x1:
            return payload.decode("utf-8", errors="replace")
        if opcode == 0xA:
            continue


def cdp_call(
    ws_url: str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    call_id: int = 1,
) -> Any:
    """One-shot CDP method. Never logs params that may hold secrets."""
    sock = _ws_handshake(ws_url)
    try:
        msg: dict[str, Any] = {"id": call_id, "method": method}
        if params:
            msg["params"] = params
        _ws_send_text(sock, json.dumps(msg, separators=(",", ":")))
        while True:
            raw = _ws_recv_text(sock)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if payload.get("id") != call_id:
                continue
            if payload.get("error"):
                return None
            return payload.get("result")
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _host_is_sectura(host: str) -> bool:
    h = str(host or "").lower().lstrip(".")
    return h == SECTURA_HOST or h.endswith("." + SECTURA_HOST)


def sectura_cookies_from_cdp(base: str | None = None) -> list[tuple[str, str]]:
    """(name, value) for secturafab.com from the Quotes tab. Values stay in RAM."""
    tab = quotes_tab(base)
    if not tab:
        return []
    ws = str(tab.get("webSocketDebuggerUrl") or "")
    if not ws:
        return []
    result = cdp_call(
        ws,
        "Network.getCookies",
        {"urls": ["https://www.secturafab.com/", "https://www.secturafab.com/Quote"]},
    )
    cookies = []
    if isinstance(result, dict):
        cookies = list(result.get("cookies") or [])
    if not cookies:
        result = cdp_call(ws, "Network.getAllCookies")
        if isinstance(result, dict):
            cookies = list(result.get("cookies") or [])
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in cookies:
        if not isinstance(row, dict):
            continue
        if not _host_is_sectura(str(row.get("domain") or "")):
            continue
        name = str(row.get("name") or "").strip()
        value = str(row.get("value") or "")
        if not name or not value or name in seen:
            continue
        seen.add(name)
        out.append((name, value))
    return out


def cookie_header_from_pairs(pairs: list[tuple[str, str]]) -> str:
    return "; ".join(f"{name}={value}" for name, value in pairs if name and value)


def scrape_quotes_af_fields(base: str | None = None) -> list[tuple[str, str]]:
    """kendo inputs from the open Chrome Quotes tab. Never log values."""
    tab = quotes_tab(base)
    if not tab:
        return []
    ws = str(tab.get("webSocketDebuggerUrl") or "")
    if not ws:
        return []
    result = cdp_call(
        ws,
        "Runtime.evaluate",
        {"expression": _AF_DOM_JS, "returnByValue": True},
    )
    if not isinstance(result, dict):
        return []
    value = result.get("result")
    if isinstance(value, dict) and "value" in value:
        value = value.get("value")
    if not isinstance(value, list):
        return []
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in value:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        val = str(row.get("value") or "").strip()
        if not name or not val or name in seen:
            continue
        seen.add(name)
        out.append((name, val))
    return out
