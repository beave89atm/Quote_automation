"""Chrome DevTools (box debug port) — Quotes page functions + DOM AF.

Live 7b723b9: cookie GET /Quote HTML AF is a *different claims-based user*
than the signed-in Quotes tab. Cookie-file HTTP POST /part/create 403s
even with an AF field.

Live 34137-2: CDP ``fetch('/part/create')`` 200 t.List=31 does **not** run
QuoteOrderEdit ``DoCreateDXFParts`` success, so ``#gridDXFParts`` stays
empty. Reconstructed Finish (cookie or fetch) is 200 empty / ItemList 0.
Drive ``createAllParts`` / ``DoCreateDXFParts`` then page Finish so the
grid bind happens.

Never scrape the Login tab or the claims-mismatch tab.
Never log cookie or AF token values. Names / bools / body keys / counts only.
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
DEFAULT_DEBUG_PORTS = (9222, 9223, 9224, 9333)
_CDP_TIMEOUT_S = 5.0
_PART_CREATE_TIMEOUT_S = 180.0

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


def chrome_debug_bases() -> list[str]:
    """Every live Chrome DevTools HTTP endpoint (box may use 9224, not 9222)."""
    found: list[str] = []
    for base in _debug_candidates():
        try:
            info = _http_json(f"{base}/json/version")
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(info, dict) and (
            info.get("webSocketDebuggerUrl") or info.get("Browser")
        ):
            found.append(base)
    return found


def chrome_debug_base() -> str | None:
    """First live Chrome DevTools HTTP endpoint, or None."""
    bases = chrome_debug_bases()
    return bases[0] if bases else None


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


def _is_rejected_tab(tab: dict[str, Any]) -> bool:
    """Login and claims-mismatch tabs must never be scraped (live 7b723b9)."""
    title = str(tab.get("title") or "").lower()
    url = str(tab.get("url") or "").lower()
    if "login" in title or "/account/login" in url:
        return True
    if (
        "anti-forgery" in title
        or "antiforgery" in title
        or "claims-based" in title
        or "different claims" in title
    ):
        return True
    return False


def _is_live_quotes_tab(tab: dict[str, Any]) -> bool:
    """Title Quotes + www /Quote — not Login, not claims-mismatch."""
    if _is_rejected_tab(tab):
        return False
    title = str(tab.get("title") or "").strip()
    url = str(tab.get("url") or "").lower()
    if SECTURA_HOST not in url:
        return False
    if "/account/" in url:
        return False
    if "/quote" not in url:
        return False
    return title == "Quotes" or title.startswith("Quotes")


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
    """Signed-in Quotes tab (title Quotes). Never Login / claims-mismatch."""
    bases = [base] if base else chrome_debug_bases()
    found: list[dict[str, Any]] = []
    for root in bases:
        if not root:
            continue
        pages = [
            t
            for t in list_chrome_targets(root)
            if str(t.get("type") or "page") == "page" and t.get("webSocketDebuggerUrl")
        ]
        found.extend(t for t in pages if _is_live_quotes_tab(t))
    if not found:
        return None

    def _rank(tab: dict[str, Any]) -> tuple[int, int]:
        url = str(tab.get("url") or "").lower()
        title = str(tab.get("title") or "").strip()
        exact = 0 if title == "Quotes" else 1
        edit = 0 if ("/quote/edit" in url or url.rstrip("/").endswith("/quote")) else 1
        return (exact, edit)

    found.sort(key=_rank)
    return found[0]


def chrome_quotes_live(base: str | None = None) -> bool:
    return quotes_tab(base) is not None


def _ws_handshake(ws_url: str, timeout: float = _CDP_TIMEOUT_S) -> socket.socket:
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
    sock = socket.create_connection((host, port), timeout=timeout)
    sock.settimeout(timeout)
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
    timeout: float = _CDP_TIMEOUT_S,
) -> Any:
    """One-shot CDP method. Never logs params that may hold secrets."""
    sock = _ws_handshake(ws_url, timeout=timeout)
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


# QuoteOrderEdit / CadImport only — never invent a path.
_QUOTES_TAB_FETCH_PATHS = frozenset(
    {
        "/part/create",
        "/Quote/AddItem_DXFFiles",
        "/CadImport/SetPartMode",
        "/CadImport/UpdateData",
    }
)

_QUOTES_TAB_FETCH_JS = """(function(spec) {
  var fields = [];
  document.querySelectorAll('input[name^="__RequestVerificationToken"]').forEach(function(el) {
    if (el.name && el.value) fields.push([el.name, el.value]);
  });
  var af = document.querySelector('input[name="afToken"]');
  if (af && af.value) fields.push([af.name, af.value]);
  var af_names = fields.map(function(p) { return p[0]; });
  if (!fields.length) {
    return Promise.resolve({
      has_antiforgery: false,
      af_names: [],
      status: 0,
      body_keys: [],
      body_type: "empty",
      has_NewItem: false,
      has_QuoteItem: false,
      list_len: 0,
      text_len: 0,
      List: null
    });
  }
  var path = String(spec.path || "/");
  var method = String(spec.method || "POST");
  var headers = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01"
  };
  var body = undefined;
  if (spec.query) {
    var qs = new URLSearchParams();
    Object.keys(spec.query).forEach(function(k) {
      qs.append(k, String(spec.query[k]));
    });
    path = path + (path.indexOf("?") >= 0 ? "&" : "?") + qs.toString();
  }
  if (spec.json != null) {
    var obj = spec.json;
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      fields.forEach(function(p) { obj[p[0]] = p[1]; });
    }
    headers["Content-Type"] = "application/json; charset=UTF-8";
    body = JSON.stringify(obj);
  } else if (method !== "GET") {
    var params = new URLSearchParams();
    (spec.form || []).forEach(function(pair) {
      params.append(String(pair[0]), String(pair[1]));
    });
    fields.forEach(function(pair) { params.append(pair[0], pair[1]); });
    headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8";
    body = params;
  }
  return fetch(path, {
    method: method,
    headers: headers,
    body: body,
    credentials: "same-origin"
  }).then(function(r) {
    return r.text().then(function(text) {
      var json = null;
      try { json = JSON.parse(text); } catch (e) { json = null; }
      var isObj = json && typeof json === "object" && !Array.isArray(json);
      var body_keys = isObj ? Object.keys(json) : [];
      var list = (isObj && Array.isArray(json.List)) ? json.List : null;
      var body_type = "empty";
      if (text) {
        body_type = isObj ? "object" : (json == null ? "str" : typeof json);
      }
      return {
        has_antiforgery: true,
        af_names: af_names,
        status: r.status,
        body_keys: body_keys,
        body_type: body_type,
        has_NewItem: !!(isObj && (json.NewItem || json.newItem)),
        has_QuoteItem: !!(isObj && (json.QuoteItem || json.quoteItem)),
        list_len: list ? list.length : 0,
        text_len: text ? String(text).length : 0,
        List: list
      };
    });
  });
})"""


def _unwrap_evaluate(result: Any) -> Any:
    if not isinstance(result, dict):
        return result
    inner = result.get("result")
    if isinstance(inner, dict) and "value" in inner:
        return inner.get("value")
    return inner if inner is not None else result


def _empty_quotes_fetch(*, include_list: bool = True) -> dict[str, Any]:
    out: dict[str, Any] = {
        "has_antiforgery": False,
        "af_names": [],
        "status": 0,
        "body_keys": [],
        "body_type": "empty",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "list_len": 0,
        "text_len": 0,
        "via": "chrome_dom_fetch",
    }
    if include_list:
        out["List"] = None
    return out


def quotes_tab_fetch(
    *,
    path: str,
    method: str = "POST",
    form_pairs: list[tuple[str, str]] | None = None,
    json_body: Any = None,
    query: dict[str, Any] | None = None,
    include_list: bool = False,
    timeout: float = _PART_CREATE_TIMEOUT_S,
    base: str | None = None,
) -> dict[str, Any]:
    """POST from the live Quotes document. Never logs AF or body text."""
    allowed = path if str(path or "").startswith("/") else f"/{path}"
    if allowed not in _QUOTES_TAB_FETCH_PATHS:
        return _empty_quotes_fetch(include_list=include_list)
    tab = quotes_tab(base)
    if not tab:
        return _empty_quotes_fetch(include_list=include_list)
    ws = str(tab.get("webSocketDebuggerUrl") or "")
    if not ws:
        return _empty_quotes_fetch(include_list=include_list)
    spec: dict[str, Any] = {"path": allowed, "method": str(method or "POST").upper()}
    if query:
        spec["query"] = {str(k): str(v) for k, v in query.items() if k}
    if json_body is not None:
        spec["json"] = json_body
    else:
        spec["form"] = [[str(k), str(v)] for k, v in (form_pairs or []) if k]
    expression = _QUOTES_TAB_FETCH_JS + "(" + json.dumps(spec, separators=(",", ":")) + ")"
    result = cdp_call(
        ws,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
        timeout=timeout,
    )
    value = _unwrap_evaluate(result)
    if not isinstance(value, dict):
        return _empty_quotes_fetch(include_list=include_list)
    out: dict[str, Any] = {
        "has_antiforgery": bool(value.get("has_antiforgery")),
        "af_names": [
            str(n)
            for n in (value.get("af_names") or [])
            if str(n).startswith("__RequestVerificationToken") or str(n) == "afToken"
        ],
        "status": int(value.get("status") or 0),
        "body_keys": [str(k) for k in (value.get("body_keys") or [])],
        "body_type": str(value.get("body_type") or "empty"),
        "has_NewItem": bool(value.get("has_NewItem")),
        "has_QuoteItem": bool(value.get("has_QuoteItem")),
        "list_len": int(value.get("list_len") or 0),
        "text_len": int(value.get("text_len") or 0),
        "via": "chrome_dom_fetch",
    }
    if include_list:
        out["List"] = value.get("List") if isinstance(value.get("List"), list) else None
    return out


def post_part_create_from_quotes_tab(
    form_pairs: list[tuple[str, str]],
    *,
    base: str | None = None,
) -> dict[str, Any]:
    """DoCreateDXFParts via fetch in the live Quotes document. Never logs AF."""
    return quotes_tab_fetch(
        path="/part/create",
        form_pairs=form_pairs,
        include_list=True,
        base=base,
    )


def post_add_item_dxf_files_from_quotes_tab(
    payload: dict[str, Any],
    *,
    base: str | None = None,
) -> dict[str, Any]:
    """Finish POST /Quote/AddItem_DXFFiles from the Quotes document."""
    return quotes_tab_fetch(
        path="/Quote/AddItem_DXFFiles",
        json_body=payload,
        include_list=False,
        base=base,
    )


def post_set_part_mode_from_quotes_tab(
    *,
    row_id: str,
    part_mode: int,
    base: str | None = None,
) -> dict[str, Any]:
    """POST /CadImport/SetPartMode from the Quotes document."""
    return quotes_tab_fetch(
        path="/CadImport/SetPartMode",
        query={"ID": row_id, "PartMode": int(part_mode)},
        include_list=False,
        timeout=30.0,
        base=base,
    )


def post_update_data_from_quotes_tab(
    payload: dict[str, Any],
    *,
    base: str | None = None,
) -> dict[str, Any]:
    """POST /CadImport/UpdateData from the Quotes document."""
    return quotes_tab_fetch(
        path="/CadImport/UpdateData",
        json_body=payload,
        include_list=False,
        timeout=30.0,
        base=base,
    )


# QuoteOrderEdit: createAllParts → DoCreateDXFParts success pushes t.List
# onto #gridDXFParts. Finish reads that grid (ErrorStatus===0, Qty>0).
# Live 34137-2: standalone fetch('/part/create') never runs that success.
_PAGE_CREATE_ALL_PARTS_JS = """(function(spec) {
  function hasPartsGrid() {
    try {
      return !!(window.jQuery && jQuery("#gridDXFParts").data("kendoGrid"));
    } catch (e) { return false; }
  }
  function gridCount() {
    try {
      var g = window.jQuery && jQuery("#gridDXFParts").data("kendoGrid");
      if (!g || !g.dataSource) return 0;
      var data = g.dataSource.data();
      return data ? data.length : 0;
    } catch (e) { return 0; }
  }
  function fullRows() {
    try {
      var g = jQuery("#gridDXFParts").data("kendoGrid");
      if (!g || !g.dataSource) return [];
      var raw = g.dataSource.data();
      return (raw && raw.toJSON) ? raw.toJSON() : [];
    } catch (e) { return []; }
  }
  function waitUntil(fn, ms) {
    return new Promise(function(resolve) {
      if (fn()) { resolve(true); return; }
      if (!ms) { resolve(fn()); return; }
      var t0 = Date.now();
      var iv = setInterval(function() {
        if (fn() || Date.now() - t0 > ms) {
          clearInterval(iv);
          resolve(fn());
        }
      }, 250);
    });
  }
  function openCadFiles() {
    if (hasPartsGrid()) return false;
    try {
      var nodes = document.querySelectorAll(
        "button, a, input[type=button], input[type=submit], [role=button]"
      );
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        var blob = (
          (el.getAttribute("onclick") || "") + " " + (el.textContent || "")
          + " " + (el.value || "") + " " + (el.id || "")
          + " " + (el.getAttribute("href") || "")
        ).toLowerCase();
        if (blob.indexOf("cad files") >= 0 || blob.indexOf("getitem_addview") >= 0
            || blob.indexOf("itemtype=dxf") >= 0 || blob.indexOf("adddxf") >= 0) {
          el.click();
          return true;
        }
      }
    } catch (e) {}
    return false;
  }
  function runCreate() {
    var called = "";
    var dxfN = 0;
    try {
      var dxf = window.jQuery && jQuery("#gridDXF").data("kendoGrid");
      dxfN = (dxf && dxf.dataSource && dxf.dataSource.data())
        ? dxf.dataSource.data().length : 0;
    } catch (e) { dxfN = 0; }
    try {
      if (typeof createAllParts === "function" && dxfN > 0) {
        createAllParts();
        called = "createAllParts";
      } else if (typeof DoCreateDXFParts === "function") {
        var ids = (spec && spec.idList) || [];
        var units = (spec && spec.unitList) || [];
        if (ids.length) {
          DoCreateDXFParts(ids, units);
          called = "DoCreateDXFParts";
          try { jQuery('#ulDXFTab a[href="#dxfparts"]').tab("show"); } catch (e2) {}
        }
      }
    } catch (e) {
      called = called || "error";
    }
    return {called: called, dxfN: dxfN};
  }
  var before = gridCount();
  var opened = openCadFiles();
  return waitUntil(hasPartsGrid, opened ? 15000 : 0).then(function() {
    var meta = runCreate();
    return waitUntil(function() { return gridCount() > before; }, 170000)
      .then(function() {
        var n = gridCount();
        return {
          called: meta.called,
          grid_dxf_row_count: n,
          grid_dxf_upload_count: meta.dxfN,
          has_createAllParts: typeof createAllParts === "function",
          has_DoCreateDXFParts: typeof DoCreateDXFParts === "function",
          has_gridDXFParts: hasPartsGrid(),
          has_gridDXF: !!(window.jQuery && jQuery("#gridDXF").data("kendoGrid")),
          opened_cad_files: opened,
          List: fullRows()
        };
      });
  });
})"""


_PAGE_FINISH_JS = """(function() {
  function gridRows() {
    try {
      var g = window.jQuery && jQuery("#gridDXFParts").data("kendoGrid");
      if (!g || !g.dataSource) return [];
      var raw = g.dataSource.data();
      var json = (raw && raw.toJSON) ? raw.toJSON() : [];
      return json.filter(function(r) {
        return (r.ErrorStatus === 0 || r.ErrorStatus === "0")
          && Number(r.Qty || r.Quantity || 0) > 0;
      });
    } catch (e) { return []; }
  }
  function summarize(status, data) {
    var isObj = data && typeof data === "object" && !Array.isArray(data);
    var keys = isObj ? Object.keys(data) : [];
    var body_type = "empty";
    if (data == null || data === "") body_type = "empty";
    else if (isObj) body_type = "object";
    else if (typeof data === "string") body_type = "str";
    else body_type = typeof data;
    return {
      status: status || 0,
      body_keys: keys,
      body_type: body_type,
      has_NewItem: !!(isObj && (data.NewItem || data.newItem)),
      has_QuoteItem: !!(isObj && (data.QuoteItem || data.quoteItem)),
      text_len: (typeof data === "string") ? data.length : (isObj ? 1 : 0),
      grid_dxf_row_count: gridRows().length
    };
  }
  var rows = gridRows();
  var count = rows.length;
  if (count <= 1) {
    return Promise.resolve(Object.assign(summarize(0, null), {
      via: "skipped",
      finish_fn: "",
      grid_dxf_row_count: count
    }));
  }
  function findFinishName() {
    var names = [
      "OnAddDXFClick", "OnAddDXFFilesClick", "AddDXFFiles", "AddItemDXFFiles"
    ];
    for (var i = 0; i < names.length; i++) {
      if (typeof window[names[i]] === "function") return names[i];
    }
    try {
      for (var k in window) {
        var fn = window[k];
        if (typeof fn === "function"
            && String(fn).indexOf("/Quote/AddItem_DXFFiles") >= 0) {
          return k;
        }
      }
    } catch (e) {}
    return "";
  }
  var finishName = findFinishName();
  var hooked = new Promise(function(resolve) {
    if (!window.jQuery || !jQuery.ajax) {
      resolve(null);
      return;
    }
    var orig = jQuery.ajax;
    var done = false;
    jQuery.ajax = function(opts) {
      var url = String((opts && opts.url) || "");
      var ret = orig.apply(this, arguments);
      if (!done && url.indexOf("/Quote/AddItem_DXFFiles") >= 0) {
        done = true;
        jQuery.ajax = orig;
        Promise.resolve(ret).then(function(data) {
          resolve({status: 200, data: data});
        }).catch(function(xhr) {
          resolve({
            status: (xhr && xhr.status) || 0,
            data: (xhr && xhr.responseJSON) || null
          });
        });
      }
      return ret;
    };
    setTimeout(function() {
      if (!done) {
        jQuery.ajax = orig;
        resolve(null);
      }
    }, 170000);
  });
  var via = "";
  if (finishName) {
    try { window[finishName](); via = "page_fn"; } catch (e) { via = ""; }
  }
  if (!via) {
    var clicked = false;
    try {
      var nodes = document.querySelectorAll(
        "button, a, input[type=button], input[type=submit]"
      );
      for (var i = 0; i < nodes.length; i++) {
        var el = nodes[i];
        var blob = (
          (el.getAttribute("onclick") || "") + " " + (el.textContent || "")
          + " " + (el.value || "") + " " + (el.id || "")
        ).toLowerCase();
        if (blob.indexOf("onadddxf") >= 0 || blob.indexOf("additem_dxf") >= 0
            || ((blob.indexOf("finish") >= 0) && blob.indexOf("dxf") >= 0)) {
          el.click();
          clicked = true;
          via = "page_fn";
          break;
        }
      }
    } catch (e) {}
    if (!clicked) via = "";
  }
  if (!via) {
    return Promise.resolve(Object.assign(summarize(0, null), {
      via: "",
      finish_fn: "",
      grid_dxf_row_count: count,
      List: rows
    }));
  }
  return hooked.then(function(hit) {
    var extra = hit ? summarize(hit.status, hit.data) : summarize(0, null);
    extra.via = via || "page_fn";
    extra.finish_fn = finishName;
    extra.grid_dxf_row_count = count;
    return extra;
  });
})"""


def _cdp_evaluate_promise(
    expression: str,
    *,
    timeout: float = _PART_CREATE_TIMEOUT_S,
    base: str | None = None,
) -> Any:
    tab = quotes_tab(base)
    if not tab:
        return None
    ws = str(tab.get("webSocketDebuggerUrl") or "")
    if not ws:
        return None
    result = cdp_call(
        ws,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
        timeout=timeout,
    )
    return _unwrap_evaluate(result)


def invoke_page_create_all_parts(
    id_list: list[str],
    unit_list: list[str],
    *,
    base: str | None = None,
) -> dict[str, Any]:
    """Run QuoteOrderEdit createAllParts / DoCreateDXFParts so success binds #gridDXFParts."""
    spec = {
        "idList": [str(x) for x in id_list if x],
        "unitList": [str(x) for x in unit_list],
    }
    expression = (
        _PAGE_CREATE_ALL_PARTS_JS + "(" + json.dumps(spec, separators=(",", ":")) + ")"
    )
    value = _cdp_evaluate_promise(expression, base=base)
    if not isinstance(value, dict):
        return {
            "called": "",
            "grid_dxf_row_count": 0,
            "has_createAllParts": False,
            "has_DoCreateDXFParts": False,
            "has_gridDXFParts": False,
            "List": [],
            "via": "page_fn",
        }
    rows = value.get("List") if isinstance(value.get("List"), list) else []
    return {
        "called": str(value.get("called") or ""),
        "grid_dxf_row_count": int(value.get("grid_dxf_row_count") or 0),
        "grid_dxf_upload_count": int(value.get("grid_dxf_upload_count") or 0),
        "has_createAllParts": bool(value.get("has_createAllParts")),
        "has_DoCreateDXFParts": bool(value.get("has_DoCreateDXFParts")),
        "has_gridDXFParts": bool(value.get("has_gridDXFParts")),
        "has_gridDXF": bool(value.get("has_gridDXF")),
        "opened_cad_files": bool(value.get("opened_cad_files")),
        "List": [r for r in rows if isinstance(r, dict)],
        "via": "page_fn",
    }


def invoke_page_dxf_finish(*, base: str | None = None) -> dict[str, Any]:
    """Kyle Finish: page fn / click that POSTs /Quote/AddItem_DXFFiles from #gridDXFParts."""
    value = _cdp_evaluate_promise(_PAGE_FINISH_JS + "()", base=base)
    if not isinstance(value, dict):
        return {
            "via": "",
            "finish_fn": "",
            "grid_dxf_row_count": 0,
            "status": 0,
            "body_keys": [],
            "body_type": "empty",
            "has_NewItem": False,
            "has_QuoteItem": False,
            "text_len": 0,
            "List": [],
        }
    rows = value.get("List") if isinstance(value.get("List"), list) else []
    via = str(value.get("via") or "")
    if via and via not in {"page_fn", "grid_finish", "skipped"}:
        via = "page_fn"
    return {
        "via": via,
        "finish_fn": str(value.get("finish_fn") or ""),
        "grid_dxf_row_count": int(value.get("grid_dxf_row_count") or 0),
        "status": int(value.get("status") or 0),
        "body_keys": [str(k) for k in (value.get("body_keys") or [])],
        "body_type": str(value.get("body_type") or "empty"),
        "has_NewItem": bool(value.get("has_NewItem")),
        "has_QuoteItem": bool(value.get("has_QuoteItem")),
        "text_len": int(value.get("text_len") or 0),
        "List": [r for r in rows if isinstance(r, dict)],
    }


def grid_dxf_parts_rows_from_quotes_tab(
    *,
    base: str | None = None,
) -> list[dict[str, Any]]:
    """#gridDXFParts dataSource.toJSON() after DoCreateDXFParts success."""
    js = """(() => {
      try {
        var g = window.jQuery && jQuery("#gridDXFParts").data("kendoGrid");
        if (!g || !g.dataSource) return [];
        var raw = g.dataSource.data();
        return (raw && raw.toJSON) ? raw.toJSON() : [];
      } catch (e) { return []; }
    })()"""
    tab = quotes_tab(base)
    if not tab:
        return []
    ws = str(tab.get("webSocketDebuggerUrl") or "")
    if not ws:
        return []
    result = cdp_call(
        ws,
        "Runtime.evaluate",
        {"expression": js, "returnByValue": True},
    )
    value = _unwrap_evaluate(result)
    if not isinstance(value, list):
        return []
    return [r for r in value if isinstance(r, dict)]
