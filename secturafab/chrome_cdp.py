"""Chrome DevTools (box debug port) — Quotes page functions + DOM AF.

Live 7b723b9: cookie GET /Quote HTML AF is a *different claims-based user*
than the signed-in Quotes tab. Cookie-file HTTP POST /part/create 403s
even with an AF field.

Live 34137-2: CDP ``fetch('/part/create')`` with Upload file IDs → t.List=31.
fetch skips QuoteOrderEdit ``DoCreateDXFParts`` success, so ``#gridDXFParts``
stays empty. Reconstructed Finish is 200 empty / ItemList 0.

Live 34632-2: evaluating ``createAllParts`` / ``DoCreateDXFParts`` on the
Quotes **list** (no CAD Files dialog) posts an empty ``#gridDXF`` IDList →
t.List=0. HTTP Upload does not fill the browser grid.

Explode = proven fetch with Upload IDs (list or EDIT, same origin).
Bind/Finish = QuoteOrderEdit ``/Quote/EDIT/{id}`` (title ``*Quote-`` /
``Quote-``). Live a64509d: Quotes list has no ``#gridDXFParts``; cookie
GetItem_AddView is markup without kendo; Chrome EDIT after ``#but_dxf`` /
``AddNewItemHTML('dxf','top')`` has kendo ``#gridDXFParts``.
Do not require title ``Quotes`` for bind/Finish.

Live 5003313-001 (526d139): Chrome was still ``/Quote/EDIT/997f1eb7``
(105918-1 leftover). Title-only ``*Quote-`` accepted that tab, page
Finish stamped ItemList 66→108 on 105918-1, minted shell stayed 0.
Before ``#but_dxf`` / bind / SetPartMode / Finish the tab must be
``/Quote/EDIT/{minted_id}``. Refuse if ``edit_quote_id != minted_id``,
the tab is a spent id, or ``grid_dxf_row_count`` is leftover kendo
(65 vs FileList 12). Do not POST ``AddItem_DXFFiles`` on the leftover.

Live P001545 (9735155): EDIT-id matched, grid 53==FileList 53, page
Finish 200 empty body. Do not POST a Python-rebuilt FileList. HTTP
200 empty is not success.

Live BB2000-ASM (ad38881): EDIT-id + quote number held, grid 19==
FileList 19, then Finish was skipped because findFinishName required
the literal ``#gridDXFParts`` in the page-fn source. 23b96a9 invoked
``OnAddDXFClick`` (that is the QuoteOrderEdit Finish). When EDIT
matches and the grid is present, invoke that fn even if its source
does not contain ``#gridDXFParts``. Log ``finish_fn`` and whether
the source reads the kendo dataSource. Do not skip. Leave
a9497a26 / BB2000-ASM. Live EHB3112 (83c9200): OnAddDXFClick fired
(4==4) but HTTP 200 empty / GET 0 — SetPartMode / grid_classify
notes were missing (105918-1 had them, then GET 66). Set FileType
on this EDIT #gridDXFParts before OnAddDXFClick. Leave cf8ec36e /
EHB3112-1. Live 11796-1 (4c79659): SetPartMode + OnAddDXFClick on
1 Cad, filelist_from_kendo=false / finish_af_present=false /
200 empty. FileList must be this EDIT kendo dataSource with
chrome_dom AF on that document. n=1 Cad is Finishable. Leave
a8e1b40e / 11796-1. Next unused after kendo FileList + AF is
proven in tests: 11796-2 only if still needed.

Never scrape the Login tab or the claims-mismatch tab.
Never log cookie or AF token values. Names / bools / body keys / counts only.
Do not unwrap Windows Chrome. Do not ask Kyle to log in.
"""

from __future__ import annotations

import base64
import json
import os
import re
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


def _title_is_quote_order_edit(title: str) -> bool:
    """QuoteOrderEdit titles look like *Quote-106386-1 or Quote-106386-1."""
    norm = str(title or "").strip().lstrip("*").strip()
    return norm.lower().startswith("quote-")


def _url_is_quote_edit(url: str) -> bool:
    u = str(url or "").lower()
    return "/quote/edit/" in u or "/quote/edit?" in u


_EDIT_QUOTE_ID_RE = re.compile(r"/Quote/EDIT/([^/?#]+)", re.I)


def edit_tab_quote_id(tab: dict[str, Any] | None) -> str:
    """GUID from ``/Quote/EDIT/{id}``. Empty when the tab is not that document."""
    if not isinstance(tab, dict):
        return ""
    url = str(tab.get("url") or "")
    match = _EDIT_QUOTE_ID_RE.search(url)
    return str(match.group(1) or "").strip() if match else ""


def edit_ids_match(left: str | None, right: str | None) -> bool:
    a = str(left or "").strip().casefold()
    b = str(right or "").strip().casefold()
    return bool(a and b and a == b)


def grid_dxf_count_is_stale(grid_count: int | None, list_len: int | None) -> bool:
    """Leftover kendo (65) after bind of this t.List (12) is not a real bind.

    Slack of 2 covers Root on/off the grid. 15==15 (28110-2) is not stale.
    """
    if not isinstance(grid_count, (int, float)) or not isinstance(list_len, (int, float)):
        return False
    n_grid = int(grid_count)
    n_list = int(list_len)
    if n_list <= 0:
        return False
    return n_grid > n_list + 2


def _is_quotes_list_tab(tab: dict[str, Any]) -> bool:
    """Title Quotes on /Quote — the list, not QuoteOrderEdit."""
    if _is_rejected_tab(tab):
        return False
    title = str(tab.get("title") or "").strip()
    url = str(tab.get("url") or "").lower()
    if SECTURA_HOST not in url:
        return False
    if "/account/" in url or "getitem_addview" in url:
        return False
    if "/quote" not in url or _url_is_quote_edit(url):
        return False
    return title == "Quotes" or title.startswith("Quotes")


def _is_quote_edit_tab(tab: dict[str, Any]) -> bool:
    """/Quote/EDIT/{id} or title *Quote- / Quote-. Not GetItem_AddView."""
    if _is_rejected_tab(tab):
        return False
    title = str(tab.get("title") or "").strip()
    url = str(tab.get("url") or "").lower()
    if SECTURA_HOST not in url:
        return False
    if "/account/" in url or "getitem_addview" in url:
        return False
    return _url_is_quote_edit(url) or _title_is_quote_order_edit(title)


def _is_live_quotes_tab(tab: dict[str, Any]) -> bool:
    """Signed-in Quotes list *or* Quote/EDIT. Not Login / claims / AddView."""
    return _is_quotes_list_tab(tab) or _is_quote_edit_tab(tab)


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


def _chrome_page_targets(base: str | None = None) -> list[dict[str, Any]]:
    bases = [base] if base else chrome_debug_bases()
    found: list[dict[str, Any]] = []
    for root in bases:
        if not root:
            continue
        found.extend(
            t
            for t in list_chrome_targets(root)
            if str(t.get("type") or "page") == "page" and t.get("webSocketDebuggerUrl")
        )
    return found


def quotes_tab(base: str | None = None) -> dict[str, Any] | None:
    """Signed-in Quotes list, or Quote/EDIT when that is the only session.

    Prefer title Quotes (explode fetch). Do not require it for liveness —
    QuoteOrderEdit title is *Quote-{PN}. Never Login / claims / AddView.
    """
    found = [t for t in _chrome_page_targets(base) if _is_live_quotes_tab(t)]
    if not found:
        return None

    def _rank(tab: dict[str, Any]) -> tuple[int, int]:
        url = str(tab.get("url") or "").lower()
        title = str(tab.get("title") or "").strip()
        if title == "Quotes":
            exact = 0
        elif title.startswith("Quotes"):
            exact = 1
        elif _is_quote_edit_tab(tab):
            exact = 2
        else:
            exact = 3
        edit = 0 if ("/quote/edit" in url or url.rstrip("/").endswith("/quote")) else 1
        return (exact, edit)

    found.sort(key=_rank)
    return found[0]


def quote_edit_tab(
    base: str | None = None,
    *,
    quote_id: str | None = None,
    quote_number: str | None = None,
) -> dict[str, Any] | None:
    """QuoteOrderEdit /Quote/EDIT/{id} or title *Quote- / Quote-.

    When ``quote_id`` is set, return only a tab whose URL is that EDIT id.
    Do not fall back to a leftover ``*Quote-`` tab (live 5003313-001).
    """
    found = [t for t in _chrome_page_targets(base) if _is_quote_edit_tab(t)]
    if not found:
        return None
    qid = str(quote_id or "").strip().lower()
    qnum = str(quote_number or "").strip().lower()
    if qid:
        matches = [
            tab
            for tab in found
            if qid in str(tab.get("url") or "").lower()
            and _url_is_quote_edit(str(tab.get("url") or ""))
        ]
        return matches[0] if matches else None

    def _rank(tab: dict[str, Any]) -> tuple[int, int, int]:
        url = str(tab.get("url") or "").lower()
        title = str(tab.get("title") or "").lower()
        id_hit = 0 if (qid and qid in url) else 1
        num_hit = 0 if (qnum and qnum in title) else 1
        path_hit = 0 if _url_is_quote_edit(url) else 1
        return (id_hit, num_hit, path_hit)

    found.sort(key=_rank)
    return found[0]


def chrome_quotes_live(base: str | None = None) -> bool:
    """True when the Quotes list *or* Quote/EDIT session is open."""
    return quotes_tab(base) is not None


def _quotes_or_edit_tab(
    base: str | None = None,
    *,
    prefer_edit: bool = True,
) -> dict[str, Any] | None:
    if prefer_edit:
        edit = quote_edit_tab(base)
        if isinstance(edit, dict) and edit.get("webSocketDebuggerUrl"):
            return edit
    return quotes_tab(base)


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
    """(name, value) for secturafab.com from EDIT or Quotes. Values stay in RAM."""
    tab = _quotes_or_edit_tab(base, prefer_edit=True)
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
    """kendo inputs from Quote/EDIT or the Quotes list. Never log values."""
    tab = _quotes_or_edit_tab(base, prefer_edit=True)
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
    prefer_edit: bool = False,
) -> dict[str, Any]:
    """POST from the live Quotes or Quote/EDIT document. Never logs AF."""
    allowed = path if str(path or "").startswith("/") else f"/{path}"
    if allowed not in _QUOTES_TAB_FETCH_PATHS:
        return _empty_quotes_fetch(include_list=include_list)
    tab = _quotes_or_edit_tab(base, prefer_edit=prefer_edit) if prefer_edit else quotes_tab(base)
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
    """Finish POST /Quote/AddItem_DXFFiles from the Quote/EDIT document."""
    return quotes_tab_fetch(
        path="/Quote/AddItem_DXFFiles",
        json_body=payload,
        include_list=False,
        base=base,
        prefer_edit=True,
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
        prefer_edit=True,
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


# QuoteOrderEdit DoCreateDXFParts success (cited):
#   success:function(t){var i=$("#gridDXFParts").data("kendoGrid");
#     for(var e=0;e<t.List.length;e++)i.dataSource.data().toJSON().push(t.List[e])}
# Live a64509d: #gridDXFParts kendo is on /Quote/EDIT after #but_dxf /
# AddNewItemHTML('dxf','top'). Quotes list and cookie GetItem_AddView
# are the wrong documents (markup without kendo). Bind only if kendo.
_BIND_DO_CREATE_SUCCESS_JS = """(function(spec) {
  function gridWin() {
    try {
      if (window.jQuery && jQuery("#gridDXFParts").data("kendoGrid")) return window;
    } catch (e) {}
    try {
      var frames = document.querySelectorAll("iframe");
      for (var i = 0; i < frames.length; i++) {
        try {
          var w = frames[i].contentWindow;
          if (w && w.jQuery && w.jQuery("#gridDXFParts").data("kendoGrid")) return w;
        } catch (e2) {}
      }
    } catch (e3) {}
    return null;
  }
  function gridPresent() { return !!gridWin(); }
  function gridCount() {
    var w = gridWin();
    if (!w) return 0;
    try {
      var data = w.jQuery("#gridDXFParts").data("kendoGrid").dataSource.data();
      return data ? data.length : 0;
    } catch (e) { return 0; }
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
  function clickLabeled(needles) {
    var nodes = document.querySelectorAll(
      "button, a, input, [role=button], [role=menuitem], .k-button, .k-link, li, span, td"
    );
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var text = String(el.textContent || el.value || "").replace(/\\s+/g, " ").trim();
      if (text.length > 48) continue;
      var blob = (
        (el.getAttribute("onclick") || "") + " " + text + " " + (el.id || "")
        + " " + (el.className || "") + " " + (el.getAttribute("title") || "")
        + " " + (el.getAttribute("href") || "")
      ).toLowerCase();
      for (var n = 0; n < needles.length; n++) {
        if (blob.indexOf(needles[n]) >= 0) {
          try { el.click(); return needles[n]; } catch (e) {}
        }
      }
    }
    return "";
  }
  function selectQuoteRow(qid, qnum) {
    if (!window.jQuery) return "";
    var hit = "";
    jQuery("[data-role=grid]").each(function() {
      if (hit) return;
      var g = jQuery(this).data("kendoGrid");
      if (!g || !g.dataSource) return;
      var data = g.dataSource.data();
      for (var i = 0; i < data.length; i++) {
        var row = data[i];
        var id = String(row.ID || row.QuoteID || row.Id || "");
        var num = String(row.QuoteNumber || row.Number || row.Name || "");
        if ((qid && id.toLowerCase() === qid.toLowerCase())
            || (qnum && num && num.toLowerCase() === qnum.toLowerCase())) {
          var tr = g.tbody && g.tbody.find("tr[data-uid='" + row.uid + "']");
          if (tr && tr.length) {
            try { g.select(tr); } catch (e) {}
            try { tr.trigger("dblclick"); } catch (e2) {}
            try { tr.click(); } catch (e3) {}
            hit = "quote_row";
          }
        }
      }
    });
    return hit;
  }
  function callPageOpen(qid) {
    var names = [
      "AddNewItemHTML", "OnAddCADClick", "OnCADFilesClick", "AddDXF",
      "AddDXFItem", "ShowCADFiles", "OpenCADFiles", "AddItemDXF"
    ];
    for (var i = 0; i < names.length; i++) {
      if (typeof window[names[i]] === "function") {
        try {
          var fn = window[names[i]];
          if (names[i] === "AddNewItemHTML") {
            fn("dxf", "top");
            return names[i];
          }
          if (fn.length >= 2) fn(qid, "dxf");
          else if (fn.length === 1) fn(qid);
          else fn();
          return names[i];
        } catch (e) {}
      }
    }
    try {
      for (var k in window) {
        var fn = window[k];
        if (typeof fn !== "function") continue;
        var src = String(fn);
        if (src.indexOf("/Quote/GetItem_AddView") >= 0) {
          try {
            if (fn.length >= 2) fn(qid, "dxf");
            else if (fn.length === 1) fn(qid);
            else fn();
            return k;
          } catch (e2) {}
        }
      }
    } catch (e3) {}
    return "";
  }
  function openDialog() {
    if (gridPresent()) return "already";
    var btn = document.querySelector("#but_dxf");
    if (btn) {
      try { btn.click(); return "but_dxf"; } catch (e0) {}
    }
    if (typeof AddNewItemHTML === "function") {
      try { AddNewItemHTML("dxf", "top"); return "AddNewItemHTML"; } catch (e1) {}
    }
    var qid = String((spec && spec.quoteId) || "");
    var qnum = String((spec && spec.quoteNumber) || "");
    var via = selectQuoteRow(qid, qnum);
    var cad = clickLabeled([
      "cad files", "cad file", "add cad", "adddxf", "itemtype=dxf"
    ]);
    if (cad) return via ? via + "+click" : "click";
    var fn = callPageOpen(qid);
    if (fn) return fn;
    return via || "";
  }
  function bindIfPresent() {
    var present = gridPresent();
    var empty = {
      grid_present: present,
      has_gridDXFParts: present,
      grid_dxf_row_count: present ? gridCount() : 0,
      bound: false,
      list_len: ((spec && spec.List) || []).length
    };
    if (!present) return empty;
    var t = {List: (spec && spec.List) || []};
    var i = gridWin().jQuery("#gridDXFParts").data("kendoGrid");
    for (var e = 0; e < t.List.length; e++) {
      i.dataSource.data().toJSON().push(t.List[e]);
    }
    if (gridCount() < 1) {
      var cur = i.dataSource.data().toJSON ? i.dataSource.data().toJSON() : [];
      i.dataSource.data(cur.concat(t.List));
    }
    try { gridWin().jQuery('#ulDXFTab a[href="#dxfparts"]').tab("show"); } catch (e2) {}
    return {
      grid_present: true,
      has_gridDXFParts: true,
      grid_dxf_row_count: gridCount(),
      bound: true,
      list_len: t.List.length
    };
  }
  var opened = openDialog();
  return waitUntil(gridPresent, opened && opened !== "already" ? 12000 : 0)
    .then(function() {
      var out = bindIfPresent();
      out.opened_via = opened || "";
      return out;
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
  function kendoGridPresent() {
    try {
      return !!(window.jQuery && jQuery("#gridDXFParts").data("kendoGrid"));
    } catch (e) { return false; }
  }
  function rowKey(r) {
    r = r || {};
    return String(r.SourceDataID || "")
      || String(r.ID || "")
      || String(r.FileID || "")
      || String(r.Name || "");
  }
  function looksKendoFileList(fl) {
    if (!Array.isArray(fl) || !fl.length) return false;
    var r = fl[0] || {};
    return !!(r.SourceDataID || r.ID || r.FileID || r.Name);
  }
  function fileListFromThisKendo(fl, krows) {
    if (!Array.isArray(fl) || !fl.length || !krows.length) return false;
    if (fl === krows) return true;
    var keys = {};
    for (var i = 0; i < krows.length; i++) {
      var k = rowKey(krows[i]);
      if (k) keys[k] = true;
    }
    var hits = 0;
    for (var j = 0; j < fl.length; j++) {
      var fk = rowKey(fl[j]);
      if (fk && keys[fk]) hits++;
    }
    return hits === fl.length;
  }
  function hasAf(data) {
    if (!data || typeof data !== "object") return false;
    var keys = Object.keys(data);
    for (var i = 0; i < keys.length; i++) {
      var kn = String(keys[i] || "");
      if (kn.indexOf("RequestVerification") >= 0
          || kn.toLowerCase() === "aftoken"
          || /verif|forgery|antiforgery/i.test(kn)) {
        return true;
      }
    }
    return false;
  }
  function hasChromeDomAf() {
    try {
      var names = ["__RequestVerificationToken", "RequestVerificationToken"];
      for (var i = 0; i < names.length; i++) {
        var el = document.querySelector('input[name="' + names[i] + '"]');
        if (el && String(el.value || "").trim()) return true;
      }
      var any = document.querySelector("input[name*='RequestVerification']");
      if (any && String(any.value || "").trim()) return true;
      if (window.kendo && typeof kendo.antiForgeryTokens === "function") {
        var t = kendo.antiForgeryTokens();
        if (t && typeof t === "object") {
          var tk = Object.keys(t);
          for (var j = 0; j < tk.length; j++) {
            if (t[tk[j]]) return true;
          }
        }
      }
      return false;
    } catch (e) { return false; }
  }
  function attachChromeDomAf(data) {
    if (!data || typeof data !== "object" || hasAf(data)) return;
    try {
      var names = ["__RequestVerificationToken", "RequestVerificationToken"];
      for (var i = 0; i < names.length; i++) {
        var el = document.querySelector('input[name="' + names[i] + '"]');
        if (el && String(el.value || "").trim()) {
          data[names[i]] = el.value;
          return;
        }
      }
      var any = document.querySelector("input[name*='RequestVerification']");
      if (any && String(any.value || "").trim()) {
        data[any.getAttribute("name")] = any.value;
        return;
      }
      if (window.kendo && typeof kendo.antiForgeryTokens === "function") {
        var t = kendo.antiForgeryTokens();
        if (t && typeof t === "object") {
          var tk = Object.keys(t);
          for (var j = 0; j < tk.length; j++) {
            if (t[tk[j]]) {
              data[tk[j]] = t[tk[j]];
              return;
            }
          }
        }
      }
    } catch (e) {}
  }
  function finishWhy(fromKendo, afOnDoc, afInReq, krows) {
    var why = [];
    if (!kendoGridPresent()) why.push("wrong_document");
    if (kendoGridPresent() && !krows.length) why.push("empty_dataSource");
    if (!fromKendo) why.push("filelist_not_kendo");
    if (!afOnDoc) why.push("af_missing_on_document");
    else if (!afInReq) why.push("af_not_in_request");
    return why.join(",");
  }
  var rows = gridRows();
  var count = rows.length;
  if (count < 1) {
    var skipWhy = kendoGridPresent() ? "empty_dataSource" : "wrong_document";
    return Promise.resolve(Object.assign(summarize(0, null), {
      via: "skipped",
      finish_fn: "",
      reads_kendo: false,
      grid_dxf_row_count: count,
      filelist_from_kendo: false,
      finish_af_present: false,
      finish_why: skipWhy
    }));
  }
  function fnSource(fn) {
    try { return Function.prototype.toString.call(fn); } catch (e) { return ""; }
  }
  function readsKendo(src) {
    src = String(src || "");
    return src.indexOf("gridDXFParts") >= 0 || src.indexOf("dataSource") >= 0;
  }
  function postsFinish(src) {
    return String(src || "").indexOf("/Quote/AddItem_DXFFiles") >= 0;
  }
  function findFinishName() {
    var preferred = [
      "OnAddDXFClick", "OnAddDXFFilesClick", "AddDXFFiles", "AddItemDXFFiles"
    ];
    for (var i = 0; i < preferred.length; i++) {
      if (typeof window[preferred[i]] === "function") return preferred[i];
    }
    try {
      for (var k in window) {
        var fn = window[k];
        if (typeof fn === "function" && postsFinish(fnSource(fn))) return k;
      }
    } catch (e) {}
    return "";
  }
  var finishName = findFinishName();
  var finishSrc = finishName ? fnSource(window[finishName]) : "";
  var reads_kendo = readsKendo(finishSrc);
  var hooked = new Promise(function(resolve) {
    if (!window.jQuery || !jQuery.ajax) {
      resolve(null);
      return;
    }
    var orig = jQuery.ajax;
    var done = false;
    jQuery.ajax = function(opts) {
      var url = String((opts && opts.url) || "");
      if (!done && url.indexOf("/Quote/AddItem_DXFFiles") >= 0) {
        done = true;
        jQuery.ajax = orig;
        if (!opts || typeof opts !== "object") opts = {url: url};
        if (typeof opts.data === "string") {
          try { opts.data = JSON.parse(opts.data); } catch (e) { opts.data = {}; }
        }
        if (!opts.data || typeof opts.data !== "object" || Array.isArray(opts.data)) {
          opts.data = {};
        }
        var krows = gridRows();
        if (!looksKendoFileList(opts.data.FileList || opts.data.fileList) && krows.length) {
          opts.data.FileList = krows;
        }
        attachChromeDomAf(opts.data);
        arguments[0] = opts;
        var d = opts.data;
        var fl = d.FileList || d.fileList || [];
        var n = Array.isArray(fl) ? fl.length : 0;
        var req_keys = Object.keys(d);
        var sid_n = 0;
        var ft = {Cad: 0, Linear: 0, Assembly: 0, Component: 0, blank: 0};
        for (var fi = 0; fi < n; fi++) {
          var r = fl[fi] || {};
          if (r.SourceDataID) sid_n += 1;
          var cat = String(r.FileType || r.ItemType || r.Category || "");
          var mode = Number(r.PartMode);
          if (!cat) {
            if (mode === 0) cat = "Cad";
            else if (mode === 1) cat = "Linear";
            else if (r.IsAssembly || Number(r.ProductType) === 300) cat = "Assembly";
          }
          if (ft[cat] !== undefined) ft[cat] += 1;
          else ft.blank += 1;
        }
        var fromKendo = fileListFromThisKendo(fl, krows);
        var afOnDoc = hasChromeDomAf();
        var afInReq = hasAf(d);
        var cap = {
          finish_filelist_n: n,
          request_keys: req_keys,
          filelist_from_kendo: fromKendo,
          filelist_sourcedataid_n: sid_n,
          filelist_filetype: ft,
          finish_af_present: afInReq,
          finish_why: finishWhy(fromKendo, afOnDoc, afInReq, krows)
        };
        var ret = orig.apply(this, arguments);
        Promise.resolve(ret).then(function(data) {
          cap.status = 200;
          cap.data = data;
          resolve(cap);
        }).catch(function(xhr) {
          cap.status = (xhr && xhr.status) || 0;
          cap.data = (xhr && xhr.responseJSON) || null;
          resolve(cap);
        });
        return ret;
      }
      return orig.apply(this, arguments);
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
    try { window[finishName](); } catch (e) {}
    via = "page_fn";
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
        if (blob.indexOf("onadddxf") >= 0
            || blob.indexOf("griddxfparts") >= 0) {
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
      reads_kendo: false,
      grid_dxf_row_count: count,
      List: rows
    }));
  }
  return hooked.then(function(hit) {
    if (!hit) {
      return Object.assign(summarize(0, null), {
        via: "page_fn",
        finish_fn: finishName,
        reads_kendo: reads_kendo,
        grid_dxf_row_count: count,
        finish_filelist_n: 0,
        request_keys: [],
        filelist_from_kendo: false,
        finish_af_present: false,
        finish_why: finishWhy(false, hasChromeDomAf(), false, rows),
        body_empty: true
      });
    }
    var extra = summarize(hit.status, hit.data);
    extra.via = via || "page_fn";
    extra.finish_fn = finishName;
    extra.reads_kendo = reads_kendo;
    extra.grid_dxf_row_count = count;
    extra.finish_filelist_n = Number(hit.finish_filelist_n || 0);
    extra.request_keys = hit.request_keys || [];
    extra.filelist_from_kendo = !!hit.filelist_from_kendo;
    extra.filelist_sourcedataid_n = Number(hit.filelist_sourcedataid_n || 0);
    extra.filelist_filetype = hit.filelist_filetype || {};
    extra.finish_af_present = !!hit.finish_af_present;
    extra.finish_why = String(hit.finish_why || "");
    extra.body_empty = extra.body_type === "empty" && !extra.has_NewItem;
    return extra;
  });
})"""


def _cdp_evaluate_promise(
    expression: str,
    *,
    timeout: float = _PART_CREATE_TIMEOUT_S,
    base: str | None = None,
    tab: dict[str, Any] | None = None,
    fallback: bool = True,
) -> Any:
    target = tab if isinstance(tab, dict) else None
    if not (target and target.get("webSocketDebuggerUrl")):
        if not fallback:
            return None
        target = quotes_tab(base)
    if not target:
        return None
    ws = str(target.get("webSocketDebuggerUrl") or "")
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


def _quote_edit_url(quote_id: str) -> str:
    """QuoteOrderEdit — kendo #gridDXFParts after #but_dxf. Not GetItem_AddView."""
    qid = str(quote_id or "").strip()
    return f"https://www.secturafab.com/Quote/EDIT/{qid}"


def minted_edit_tab_ready(
    minted_id: str | None,
    *,
    quote_number: str | None = None,
    base: str | None = None,
    navigate: bool = True,
) -> dict[str, Any]:
    """Require Chrome ``/Quote/EDIT/{minted_id}`` before bind / SetPartMode / Finish.

    Logs ``edit_quote_id`` vs ``minted_id``. ``ok`` is false when the tab is
    still a leftover / spent EDIT (live 997f1eb7 / 5003313-001).
    """
    from .forbidden_quotes import is_forbidden_quote_id

    minted = str(minted_id or "").strip()
    leftover = quote_edit_tab(base)
    leftover_id = edit_tab_quote_id(leftover)
    tab = quote_edit_tab(base, quote_id=minted, quote_number=quote_number) if minted else None
    edit_id = edit_tab_quote_id(tab) or leftover_id
    if minted and is_forbidden_quote_id(minted):
        return {
            "ok": False,
            "tab": None,
            "edit_quote_id": edit_id,
            "minted_id": minted,
            "reason": "spent_minted_id",
        }
    if (
        minted
        and edit_ids_match(edit_id, minted)
        and isinstance(tab, dict)
        and tab.get("webSocketDebuggerUrl")
        and not is_forbidden_quote_id(edit_id)
    ):
        return {
            "ok": True,
            "tab": tab,
            "edit_quote_id": edit_id,
            "minted_id": minted,
            "reason": "",
        }
    if minted and navigate:
        ensured = _ensure_quote_edit_page(minted, base=base)
        edit_id = edit_tab_quote_id(ensured) or leftover_id
        if (
            edit_ids_match(edit_id, minted)
            and isinstance(ensured, dict)
            and ensured.get("webSocketDebuggerUrl")
            and not is_forbidden_quote_id(edit_id)
        ):
            return {
                "ok": True,
                "tab": ensured,
                "edit_quote_id": edit_id,
                "minted_id": minted,
                "reason": "",
            }
        tab = ensured
    if not minted:
        reason = "missing_minted_id"
    elif is_forbidden_quote_id(edit_id) or is_forbidden_quote_id(leftover_id):
        reason = "spent_edit_id"
    elif edit_id and not edit_ids_match(edit_id, minted):
        reason = "edit_quote_id!=minted_id"
    else:
        reason = "edit_tab_missing"
    return {
        "ok": False,
        "tab": None,
        "edit_quote_id": edit_id or leftover_id,
        "minted_id": minted,
        "reason": reason,
    }


def _ensure_quote_edit_page(
    quote_id: str,
    *,
    base: str | None = None,
) -> dict[str, Any] | None:
    """Open /Quote/EDIT/{id} in Chrome. Do not use /Quote?ID= or GetItem_AddView.

    Title ``*Quote-`` alone is not enough — leftover 105918-1 must not count
    as the minted EDIT document. After navigate, URL id must equal minted.
    """
    qid = str(quote_id or "").strip()
    if not qid:
        return None
    existing = quote_edit_tab(base, quote_id=qid)
    if isinstance(existing, dict) and existing.get("webSocketDebuggerUrl"):
        here_id = edit_tab_quote_id(existing)
        if edit_ids_match(here_id, qid):
            return existing
    leftover = quote_edit_tab(base)
    tab = leftover if isinstance(leftover, dict) else quotes_tab(base)
    if not isinstance(tab, dict):
        return None
    here_id = edit_tab_quote_id(tab)
    if edit_ids_match(here_id, qid) and tab.get("webSocketDebuggerUrl"):
        return tab
    ws = str(tab.get("webSocketDebuggerUrl") or "")
    if not ws:
        return None
    cdp_call(ws, "Page.navigate", {"url": _quote_edit_url(qid)})
    want = json.dumps(qid)
    waited = _cdp_evaluate_promise(
        "(function(){"
        f"  var want = {want};"
        """
      return new Promise(function(resolve){
        function editId(){
          var path = String(location.pathname || "");
          var m = path.match(/\\/Quote\\/EDIT\\/([^/?#]+)/i);
          return m ? String(m[1]) : "";
        }
        function done(){
          var id = editId();
          resolve({
            edit_quote_id: id,
            ok: !!(id && id.toLowerCase() === String(want || "").toLowerCase())
          });
        }
        if (document.readyState === "complete") { done(); return; }
        window.addEventListener("load", function(){ setTimeout(done, 250); });
        setTimeout(done, 15000);
      });
    })()""",
        timeout=20.0,
        base=base,
        tab=tab,
        fallback=False,
    )
    page_id = ""
    navigated_ok = False
    if isinstance(waited, dict):
        page_id = str(waited.get("edit_quote_id") or "").strip()
        navigated_ok = bool(waited.get("ok")) and edit_ids_match(page_id, qid)
    if navigated_ok:
        stamped = dict(tab)
        stamped["url"] = _quote_edit_url(qid)
        return stamped
    verified = quote_edit_tab(base, quote_id=qid)
    if isinstance(verified, dict) and edit_ids_match(edit_tab_quote_id(verified), qid):
        return verified
    return None


def bind_do_create_dxf_parts_success(
    list_rows: list[dict[str, Any]],
    *,
    quote_id: str | None = None,
    quote_number: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """Bind t.List onto kendo #gridDXFParts on /Quote/EDIT only.

    Click #but_dxf / AddNewItemHTML('dxf','top'). Cookie GetItem_AddView
    and the Quotes list are the wrong documents (live a64509d).
    Does not POST /part/create.
    """
    kids = [r for r in list_rows if isinstance(r, dict)]
    spec = {
        "List": kids,
        "quoteId": str(quote_id or ""),
        "quoteNumber": str(quote_number or ""),
    }
    expression = (
        _BIND_DO_CREATE_SUCCESS_JS + "(" + json.dumps(spec, separators=(",", ":")) + ")"
    )
    gate = minted_edit_tab_ready(
        quote_id, quote_number=quote_number, base=base, navigate=True
    )
    empty = {
        "grid_present": False,
        "has_gridDXFParts": False,
        "grid_dxf_row_count": 0,
        "bound": False,
        "list_len": len(kids),
        "opened_via": "",
        "edit_quote_id": str(gate.get("edit_quote_id") or ""),
        "minted_id": str(gate.get("minted_id") or quote_id or ""),
        "edit_gate": str(gate.get("reason") or ""),
        "stale_grid": False,
    }
    if not gate.get("ok"):
        return empty
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    value = _cdp_evaluate_promise(expression, base=base, tab=tab, fallback=False)
    if not isinstance(value, dict):
        return empty
    present = bool(value.get("grid_present") or value.get("has_gridDXFParts"))
    n_grid = int(value.get("grid_dxf_row_count") or 0) if present else 0
    n_list = int(value.get("list_len") or len(kids) or 0)
    stale = grid_dxf_count_is_stale(n_grid, n_list)
    bound = bool(value.get("bound")) and present and not stale
    return {
        "grid_present": present,
        "has_gridDXFParts": present,
        "grid_dxf_row_count": n_grid,
        "bound": bound,
        "list_len": n_list,
        "opened_via": str(value.get("opened_via") or ""),
        "edit_quote_id": str(gate.get("edit_quote_id") or ""),
        "minted_id": str(gate.get("minted_id") or quote_id or ""),
        "edit_gate": "stale_grid" if stale else "",
        "stale_grid": stale,
    }


def page_finish_skip_after_edit_match_is_fail(
    *,
    edit_quote_id: str | None,
    minted_id: str | None,
    grid_n: int,
    filelist_n: int,
    via: str | None,
) -> bool:
    """True when skip-Finish after EDIT match + equal counts is a fixture fail.

    Live BB2000-ASM (ad38881): edit==minted, grid 19==FileList 19,
    ``finish_via=skipped``. Must invoke the 23b96a9 page fn instead.
    """
    edit = str(edit_quote_id or "").strip()
    minted = str(minted_id or "").strip()
    if not edit or edit != minted:
        return False
    try:
        gn = int(grid_n)
        fn = int(filelist_n)
    except (TypeError, ValueError):
        return False
    if gn < 1 or gn != fn:
        return False
    return str(via or "").strip() in {"", "skipped"}


def invoke_page_dxf_finish(
    *,
    base: str | None = None,
    quote_id: str | None = None,
) -> dict[str, Any]:
    """Kyle Finish on /Quote/EDIT: page fn that POSTs /Quote/AddItem_DXFFiles."""
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    skipped = {
        "via": "skipped",
        "finish_fn": "",
        "reads_kendo": False,
        "grid_dxf_row_count": 0,
        "finish_filelist_n": 0,
        "request_keys": [],
        "status": 0,
        "body_keys": [],
        "body_type": "empty",
        "has_NewItem": False,
        "has_QuoteItem": False,
        "text_len": 0,
        "List": [],
        "edit_quote_id": str(gate.get("edit_quote_id") or ""),
        "minted_id": str(gate.get("minted_id") or quote_id or ""),
        "edit_gate": str(gate.get("reason") or "missing_minted_id"),
        "filelist_from_kendo": False,
        "finish_af_present": False,
        "finish_why": "wrong_document",
    }
    if not gate.get("ok"):
        return skipped
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    value = _cdp_evaluate_promise(
        _PAGE_FINISH_JS + "()", base=base, tab=tab, fallback=False
    )
    if not isinstance(value, dict):
        skipped["edit_gate"] = "finish_eval_empty"
        return skipped
    rows = value.get("List") if isinstance(value.get("List"), list) else []
    via = str(value.get("via") or "")
    if via and via not in {"page_fn", "grid_finish", "skipped"}:
        via = "page_fn"
    return {
        "via": via,
        "finish_fn": str(value.get("finish_fn") or ""),
        "reads_kendo": bool(value.get("reads_kendo")),
        "grid_dxf_row_count": int(value.get("grid_dxf_row_count") or 0),
        "finish_filelist_n": int(value.get("finish_filelist_n") or 0),
        "request_keys": [str(k) for k in (value.get("request_keys") or [])],
        "filelist_from_kendo": bool(value.get("filelist_from_kendo")),
        "filelist_sourcedataid_n": int(value.get("filelist_sourcedataid_n") or 0),
        "filelist_filetype": (
            value.get("filelist_filetype")
            if isinstance(value.get("filelist_filetype"), dict)
            else {}
        ),
        "finish_af_present": bool(value.get("finish_af_present")),
        "finish_why": str(value.get("finish_why") or ""),
        "status": int(value.get("status") or 0),
        "body_keys": [str(k) for k in (value.get("body_keys") or [])],
        "body_type": str(value.get("body_type") or "empty"),
        "has_NewItem": bool(value.get("has_NewItem")),
        "has_QuoteItem": bool(value.get("has_QuoteItem")),
        "text_len": int(value.get("text_len") or 0),
        "List": [r for r in rows if isinstance(r, dict)],
        "edit_quote_id": str(gate.get("edit_quote_id") or ""),
        "minted_id": str(gate.get("minted_id") or quote_id or ""),
        "edit_gate": "",
    }


# QuoteOrderEdit: $.ajax({type:"POST",url:"/CadImport/SetPartMode",data:{ID,PartMode}})
# Kyle STP Loom: Component→CAD sets Machine=Laser; Structural→Linear + Product Type.
# Live 105918-1: Finish without this left plates as Component (0 Cad).
_APPLY_GRID_PART_MODES_JS = """(function(spec) {
  function grid() {
    try {
      return window.jQuery && jQuery("#gridDXFParts").data("kendoGrid");
    } catch (e) { return null; }
  }
  function catOf(row) {
    var mode = Number(row.PartMode);
    var pt = Number(row.ProductType);
    var item = String(row.ItemType || row.Category || "");
    var name = String(row.Name || row.Description || row.FileName || "");
    if (row.IsAssembly || pt === 300 || /weldment/i.test(name) || item === "Assembly") {
      return "Assembly";
    }
    if (mode === 0 || item === "Cad" || pt === 100) return "Cad";
    if (mode === 1 || row.IsLinear || item === "Linear" || pt === 10 || pt === 30 || pt === 40) {
      return "Linear";
    }
    return "Component";
  }
  function findSetFn() {
    var names = [
      "SetPartMode", "ChangePartMode", "OnPartModeChange", "OnFileTypeChange"
    ];
    for (var i = 0; i < names.length; i++) {
      if (typeof window[names[i]] === "function") return names[i];
    }
    try {
      for (var k in window) {
        var fn = window[k];
        if (typeof fn === "function"
            && String(fn).indexOf("/CadImport/SetPartMode") >= 0) {
          return k;
        }
      }
    } catch (e) {}
    return "";
  }
  function applyFields(row, want) {
    var cat = String(want.Category || "");
    var mode = Number(want.PartMode);
    if (cat === "Assembly" || row.IsAssembly || Number(row.ProductType) === 300) {
      return false;
    }
    if (row.set) {
      row.set("PartMode", mode);
      row.set("ItemType", cat);
      row.set("Category", cat);
      if (cat === "Cad") {
        row.set("Machine", want.Machine || "Laser");
        row.set("ProductType", 100);
        row.set("IsPlate", true);
        row.set("IsLinear", false);
      } else if (cat === "Linear") {
        row.set("Machine", want.Machine || "Saw");
        row.set("ProductType", Number(want.ProductType) || 10);
        row.set("IsLinear", true);
        row.set("IsPlate", false);
      } else if (cat === "Component") {
        row.set("Machine", want.Machine || "");
        row.set("IsLinear", false);
        row.set("IsPlate", false);
      }
    } else {
      row.PartMode = mode;
      row.ItemType = cat;
      row.Category = cat;
      if (cat === "Cad") {
        row.Machine = want.Machine || "Laser";
        row.ProductType = 100;
        row.IsPlate = true;
        row.IsLinear = false;
      } else if (cat === "Linear") {
        row.Machine = want.Machine || "Saw";
        row.ProductType = Number(want.ProductType) || 10;
        row.IsLinear = true;
        row.IsPlate = false;
      }
    }
    return true;
  }
  function matchWant(row, wants) {
    var id = String(row.ID || row.ItemID || "").toLowerCase();
    var sid = String(row.SourceDataID || "").toLowerCase();
    var name = String(row.Name || row.Description || "").toLowerCase();
    for (var i = 0; i < wants.length; i++) {
      var w = wants[i];
      var wid = String(w.ID || "").toLowerCase();
      var wsid = String(w.SourceDataID || "").toLowerCase();
      var wname = String(w.Name || "").toLowerCase();
      if ((wid && id && wid === id) || (wsid && sid && wsid === sid)
          || (wname && name && wname === name)) {
        return w;
      }
    }
    return null;
  }
  function wantFromName(row) {
    var name = String(row.Name || row.Description || row.FileName || "");
    if (!name || /^root$/i.test(name.trim())) return null;
    if (/weldment|assembly|\bassy\b|\basm\b/i.test(name)) {
      return {Category: "Assembly", PartMode: 2};
    }
    if (/\b(tube|channel|pipe|angle|beam|hss|bars?)\b/i.test(name)) {
      return {Category: "Linear", PartMode: 1, Machine: "Saw"};
    }
    return {Category: "Cad", PartMode: 0, Machine: "Laser"};
  }
  function postMode(id, mode, fnName) {
    return new Promise(function(resolve) {
      if (!id || id === "00000000-0000-0000-0000-000000000000") {
        resolve("");
        return;
      }
      if (fnName && typeof window[fnName] === "function") {
        try {
          var fn = window[fnName];
          if (fn.length >= 2) fn(id, mode);
          else fn(id);
          resolve("page_fn");
          return;
        } catch (e) {}
      }
      if (window.jQuery && jQuery.ajax) {
        jQuery.ajax({
          type: "POST",
          url: "/CadImport/SetPartMode",
          data: {ID: id, PartMode: mode}
        }).always(function() { resolve("jquery_ajax"); });
        return;
      }
      resolve("");
    });
  }
  function applyAll() {
    var g = grid();
    if (!g || !g.dataSource) {
      return Promise.resolve({
        grid_present: false,
        cad: 0, linear: 0, assembly: 0, component: 0,
        set_count: 0, setpartmode_via: "", grid_dxf_row_count: 0
      });
    }
    var wants = (spec && spec.rows) || [];
    var data = g.dataSource.data();
    var chain = Promise.resolve("");
    var setCount = 0;
    var via = "";
    var fnName = findSetFn();
    for (var i = 0; i < data.length; i++) {
      (function(row) {
        var want = matchWant(row, wants) || wantFromName(row);
        if (!want) return;
        if (!applyFields(row, want)) return;
        setCount += 1;
        var id = String(row.ID || row.ItemID || want.ID || "");
        chain = chain.then(function(prev) {
          if (prev && !via) via = prev;
          return postMode(id, Number(want.PartMode), fnName);
        });
      })(data[i]);
    }
    return chain.then(function(last) {
      if (last && !via) via = last;
      var counts = {Cad: 0, Linear: 0, Assembly: 0, Component: 0};
      var fresh = g.dataSource.data();
      for (var j = 0; j < fresh.length; j++) {
        counts[catOf(fresh[j])] += 1;
      }
      return {
        grid_present: true,
        cad: counts.Cad,
        linear: counts.Linear,
        assembly: counts.Assembly,
        component: counts.Component,
        set_count: setCount,
        setpartmode_via: via || (fnName ? "page_fn" : (setCount ? "grid_set" : "")),
        grid_dxf_row_count: fresh.length
      };
    });
  }
  if (grid() && grid().dataSource) return applyAll();
  var btn = document.querySelector("#but_dxf");
  if (btn) { try { btn.click(); } catch (e0) {} }
  return new Promise(function(resolve) {
    var t0 = Date.now();
    (function tick() {
      if (grid() && grid().dataSource) { applyAll().then(resolve); return; }
      if (Date.now() - t0 >= 8000) {
        resolve({
          grid_present: false,
          cad: 0, linear: 0, assembly: 0, component: 0,
          set_count: 0, setpartmode_via: "", grid_dxf_row_count: 0
        });
        return;
      }
      setTimeout(tick, 200);
    })();
  });
})"""


def apply_grid_dxf_part_modes(
    rows: list[dict[str, Any]],
    *,
    quote_id: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """Set File type on EDIT #gridDXFParts via SetPartMode (QuoteOrderEdit).

    Does not POST /Quote/AddItem_DXFFiles. Capture counts from the grid.
    """
    kids = [r for r in rows if isinstance(r, dict)]
    spec_rows: list[dict[str, Any]] = []
    for row in kids:
        cat = str(row.get("Category") or row.get("ItemType") or "")
        if cat not in {"Cad", "Linear", "Component", "Assembly"}:
            continue
        spec_rows.append(
            {
                "ID": str(row.get("ID") or row.get("ItemID") or ""),
                "SourceDataID": str(row.get("SourceDataID") or ""),
                "Name": str(row.get("Name") or row.get("Description") or ""),
                "Category": cat,
                "PartMode": int(row["PartMode"]) if "PartMode" in row else (
                    0 if cat == "Cad" else 1 if cat == "Linear" else 2
                ),
                "ProductType": row.get("ProductType"),
                "Machine": str(row.get("Machine") or ""),
            }
        )
    empty = {
        "grid_present": False,
        "cad": 0,
        "linear": 0,
        "assembly": 0,
        "component": 0,
        "set_count": 0,
        "setpartmode_via": "",
        "grid_dxf_row_count": 0,
        "edit_quote_id": "",
        "minted_id": str(quote_id or ""),
        "edit_gate": "",
    }
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    empty["edit_quote_id"] = str(gate.get("edit_quote_id") or "")
    empty["minted_id"] = str(gate.get("minted_id") or quote_id or "")
    empty["edit_gate"] = str(gate.get("reason") or "")
    if not gate.get("ok"):
        return empty
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    expression = (
        _APPLY_GRID_PART_MODES_JS
        + "("
        + json.dumps({"rows": spec_rows}, separators=(",", ":"))
        + ")"
    )
    value = _cdp_evaluate_promise(
        expression,
        timeout=_PART_CREATE_TIMEOUT_S,
        base=base,
        tab=tab,
        fallback=False,
    )
    if not isinstance(value, dict):
        return empty
    present = bool(value.get("grid_present"))
    return {
        "grid_present": present,
        "cad": int(value.get("cad") or 0) if present else 0,
        "linear": int(value.get("linear") or 0) if present else 0,
        "assembly": int(value.get("assembly") or 0) if present else 0,
        "component": int(value.get("component") or 0) if present else 0,
        "set_count": int(value.get("set_count") or 0) if present else 0,
        "setpartmode_via": str(value.get("setpartmode_via") or "") if present else "",
        "grid_dxf_row_count": int(value.get("grid_dxf_row_count") or 0) if present else 0,
        "edit_quote_id": str(gate.get("edit_quote_id") or ""),
        "minted_id": str(gate.get("minted_id") or quote_id or ""),
        "edit_gate": "",
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
    edit = quote_edit_tab(base)
    tab = edit if isinstance(edit, dict) and edit.get("webSocketDebuggerUrl") else quotes_tab(base)
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
