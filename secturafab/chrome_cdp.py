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

Live FA Assembly ``0d4b8a46`` on cba5fa2: fetch + ``#img`` H/W copied
(nonzero float) + AF + ``IDList[]`` → n=28 InternalData empty 28/28.
Live Skin Assembly ``5b622a0d`` on 1a2274f: page ``$.ajax`` on minted
EDIT + ``#img`` + AF + ``IDList[]`` → n=8 InternalData empty 8/8.
Fetch-vs-``$.ajax`` is not the miss. Server never fills InternalData
on explode. ``UpdateDXF_LoadNew`` is editor-only / not gold — do
not fire ``UpdateDataNext``. Classify→Finish without ``#DXFEdit``
has no editor InternalData-fill XHR. CAD Files bind is in-page
``#files`` in ``#dxfupload_Zone`` (saveUrl ``/CadImport/UploadItem_DXFFiles``)
so ``onSuccess_Upload`` fills ``#gridDXF``. Page Next is
``createAllParts`` / ``DoCreateDXFParts`` on minted EDIT.
``GetPerimeterAndWeight`` remains ``#gridPDF`` only. Do not fire
``UpdateDataNext``. Leave ``5b622a0d``.

Explode = page ``$.ajax`` with Upload IDs (EDIT when minted id matches).
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
200 empty. Live 11796-2 (619ebf2): AF on the request, FileList
SourceDataID=0 / filelist_sourcedataid_n=0. FileList must be
``#gridDXFParts.dataSource.data()`` with ID/FileID copied onto
empty SourceDataID. Leave a8e1b40e / 11796-1 and 8de920f0 /
11796-2. Live 107292-1 (ce5d2c1): kendo+AF+SID+Cad FileType green,
empty body vs 105918-1 List,Result. Leave d59318c8 / 107292-1.
Live 16629-1: CadType+Stock on kendo and posted FileList; FileType
and Status absent; 200 empty / GET 0. Persist FileType from
SetPartMode ItemType/Category/PartMode onto the dataItem. Do not
invent Status. Leave aab5b3e2 / 16629-1.
Live 10098-1 (315cb19 leftover PIVOTING FOOT, 6a568912): posted
FileType=Cad (string) plus CadType+Stock+SID and InternalData/
ImageString/HadOpenContours/OutsidePerimeter *keys*. Finish still
200 empty / GET 0. Unfold*/DXF* child keys absent. Named miss:
Cad AddItem_DXFFiles no-ops when InternalData/ImageString are
empty. Copy those keys through if present; log emptiness bools
only; skip Finish. Do not invent unfold/geometry or FileType
"CAD"/100. Bundle hunt: no fill after DoCreateDXFParts t.List;
form keys match the UI (no missing key). Live SC0600 weldment
n=143 InternalData empty 143/143 after fetch Height/Width=0.
Live Skin Assembly ``5b622a0d``: page ``$.ajax`` on EDIT still empty
8/8. Server never fills InternalData on explode. Leave b8a62e76 /
SC0600, 0d4b8a46 / FA Assembly, and 5b622a0d / Skin Assembly.
Do not remint. Do not mint.

Live 1001898-5 (491f6387): Image Files reconstructed FileList +
Update Item ``OnAddPDFClick`` HTTP-looked success without the
calculator. GET 8 (3 Cad unitcost filled, OperationCostList [],
no PR tag). Kyle Loom: Image Files + typed L×W + green
**New Line Item(s)** with Machine already Laser Bay 1 stamps PR
+ Primary Costs. ``POST /Quote/AddItem_PDFFiles`` body
``{ ID, ItemID, FileList }`` where FileList is ``GetPDFData()``
/ ``#gridPDF`` (or QuoteOrderEdit PDF kendo) rows with
``Status>0``. Reconstructed FileList is fail-closed even if
GET>0. Leave 491f6387 / 1001898-5. No STEP. Do not mint.

Live 29743-1 (d2f7b031 SUBFRAME WELDMENT): leftover EDIT
pack_xhr_named=false addrow_stamps_pr=false. Pack is on
AddItem_PDFFiles List (Tag / ProductionReady /
OperationCostList). AddRow only copies. QuoteOrderEdit has
zero JS strings Laser / Deburr / Sheet Loading / Laser-Setup.
#files bind + dataItem.set L×W skipped UpdatePerimeterWeight
→ POST /Quote/GetPerimeterAndWeight. Posted OutsidePerimeter
empty → server List Tag "" / OCL [] / UnitCost 0 /
CuttingLength 0. Type L×W in kendo cells then fire
UpdatePerimeterWeight (onLength/onWidth) so the page XHR
fills #OutsidePerimeter + CuttingLengthDisp before
OnAddPDFClick. Empty perimeter → do not Finish. Copy Status
from dataItem onto posted FileList. Do not AddOperation /
nest / Operation→Profile. Do not graft. Leave d2f7b031.
Do not mint.
Live 103535-1 (bd5c2e3e Q10095 GATE WELDMENT): leftover Image
Files dialog (read-only; closed; no Finish). GetItem_AddView
pdf injects empty #gridPDF + kendoUpload #files.
onSuccess_PDFUpload is the only fill (dataSource.add from
response.List). transport.read.url is "". GetPDFData() walks
#gridPDF tbody dataItem Status>0 — not an XHR. Cookie HTTP
saveUrl off-page does not run onSuccess → empty_dataSource.
Kyle: drag onto +Add Files (dropZoneElement), not Select files.
Leave bd5c2e3e / 103535-1. Do not mint.

Never scrape the Login tab or the claims-mismatch tab.
Never log cookie or AF token values. Names / bools / body keys /
counts, plus posted ErrorStatus, Qty, and FileType value/type.
Do not unwrap Windows Chrome. Do not ask Kyle to log in.
"""

from __future__ import annotations

import base64
import json
import os
import re
import socket
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path
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


_CAD_DIALOG_IMG_HW_JS = """(function() {
  var from_img = false;
  var h = 0;
  var w = 0;
  try {
    if (window.jQuery) {
      var el = jQuery("#img");
      if (el && el.length) {
        from_img = true;
        h = Number(el.height()) || 0;
        w = Number(el.width()) || 0;
      }
    }
  } catch (e) {}
  return Promise.resolve({from_img: from_img, height: h, width: w});
})()"""


def cad_dialog_img_hw(*, base: str | None = None) -> dict[str, Any]:
    """Copy #img height/width if present — UI DoCreateDXFParts e/o. Never invent."""
    value = _cdp_evaluate_promise(
        _CAD_DIALOG_IMG_HW_JS, base=base, fallback=True
    )
    if not isinstance(value, dict):
        return {
            "from_img": False,
            "height": 0,
            "width": 0,
            "height_zero": True,
            "width_zero": True,
        }
    try:
        h = float(value.get("height") or 0)
    except (TypeError, ValueError):
        h = 0.0
    try:
        w = float(value.get("width") or 0)
    except (TypeError, ValueError):
        w = 0.0
    from_img = bool(value.get("from_img"))
    return {
        "from_img": from_img,
        "height": h,
        "width": w,
        "height_zero": h == 0,
        "width_zero": w == 0,
    }


# QuoteOrderEdit DoCreateDXFParts (cited): $.ajax({type:"POST",url:"/part/create",
# dataType:"json",data:{Location,IDList,unitList,OtherFileIDList,Height,Width}}).
# Live FA Assembly 0d4b8a46: chrome fetch already sent those keys + #img H/W +
# AF + IDList[] and InternalData was still empty 28/28. fetch ran on the
# Quotes list (Referer /Quote) and skipped kendo.antiForgeryTokens ajax merge.
# Copy the page XHR. Do not invent InternalData / Height / Width / extra keys.
_DO_CREATE_DXF_PARTS_AJAX_JS = """(function(spec) {
  function empty(via) {
    return {
      has_antiforgery: false,
      af_names: [],
      status: 0,
      body_keys: [],
      body_type: "empty",
      has_NewItem: false,
      has_QuoteItem: false,
      list_len: 0,
      text_len: 0,
      List: null,
      via: via || "jquery_ajax_missing"
    };
  }
  if (!(window.jQuery && jQuery.ajax)) {
    return Promise.resolve(empty("jquery_ajax_missing"));
  }
  var data = {};
  var arrays = {};
  (spec.form || []).forEach(function(pair) {
    var k = String(pair[0] || "");
    var v = pair[1];
    if (!k) return;
    if (k.slice(-2) === "[]") {
      var name = k.slice(0, -2);
      if (!arrays[name]) arrays[name] = [];
      arrays[name].push(v);
    } else if (k === "Height" || k === "Width") {
      var n = Number(v);
      data[k] = (v === "" || v == null || isNaN(n)) ? v : n;
    } else {
      data[k] = v;
    }
  });
  Object.keys(arrays).forEach(function(k) { data[k] = arrays[k]; });
  var af_names = [];
  if (window.kendo && typeof kendo.antiForgeryTokens === "function") {
    var tokens = kendo.antiForgeryTokens() || {};
    Object.keys(tokens).forEach(function(k) {
      data[k] = tokens[k];
      if (k.indexOf("__RequestVerificationToken") === 0 || k === "afToken") {
        af_names.push(k);
      }
    });
  }
  if (!af_names.length) {
    document.querySelectorAll('input[name^="__RequestVerificationToken"]').forEach(function(el) {
      if (el.name && el.value) {
        data[el.name] = el.value;
        af_names.push(el.name);
      }
    });
    var af = document.querySelector('input[name="afToken"]');
    if (af && af.value) {
      data[af.name] = af.value;
      af_names.push(af.name);
    }
  }
  if (!af_names.length) {
    return Promise.resolve(empty("jquery_ajax"));
  }
  return new Promise(function(resolve) {
    jQuery.ajax({
      type: "POST",
      url: "/part/create",
      dataType: "json",
      data: data,
      success: function(t, _status, xhr) {
        var isObj = t && typeof t === "object" && !Array.isArray(t);
        var list = (isObj && Array.isArray(t.List)) ? t.List : null;
        resolve({
          has_antiforgery: true,
          af_names: af_names,
          status: (xhr && xhr.status) || 200,
          body_keys: isObj ? Object.keys(t) : [],
          body_type: isObj ? "object" : (t == null ? "empty" : typeof t),
          has_NewItem: !!(isObj && (t.NewItem || t.newItem)),
          has_QuoteItem: !!(isObj && (t.QuoteItem || t.quoteItem)),
          list_len: list ? list.length : 0,
          text_len: 0,
          List: list,
          via: "jquery_ajax"
        });
      },
      error: function(xhr) {
        resolve({
          has_antiforgery: true,
          af_names: af_names,
          status: (xhr && xhr.status) || 0,
          body_keys: [],
          body_type: "empty",
          has_NewItem: false,
          has_QuoteItem: false,
          list_len: 0,
          text_len: 0,
          List: null,
          via: "jquery_ajax"
        });
      }
    });
  });
})"""


def _part_create_tab(
    *,
    base: str | None = None,
    quote_id: str | None = None,
) -> dict[str, Any] | None:
    """EDIT for the minted id (page DoCreateDXFParts Referer), else Quotes list."""
    qid = str(quote_id or "").strip()
    if qid:
        edit = quote_edit_tab(base, quote_id=qid)
        if isinstance(edit, dict) and edit.get("webSocketDebuggerUrl"):
            return edit
    return quotes_tab(base)


def post_part_create_from_quotes_tab(
    form_pairs: list[tuple[str, str]],
    *,
    base: str | None = None,
    quote_id: str | None = None,
) -> dict[str, Any]:
    """DoCreateDXFParts via page $.ajax on EDIT when the minted tab matches.

    Live Skin Assembly 5b622a0d: jquery_ajax + EDIT Referer + #img H/W
    still returned InternalData empty 8/8. Server never fills InternalData
    on explode. Same six form keys. Never invent InternalData. Never logs AF.
    """
    tab = _part_create_tab(base=base, quote_id=quote_id)
    from_edit = bool(tab and _is_quote_edit_tab(tab))
    spec = {"form": [[str(k), str(v)] for k, v in (form_pairs or []) if k]}
    expression = (
        _DO_CREATE_DXF_PARTS_AJAX_JS + "(" + json.dumps(spec, separators=(",", ":")) + ")"
    )
    value = _cdp_evaluate_promise(
        expression,
        timeout=_PART_CREATE_TIMEOUT_S,
        base=base,
        tab=tab,
        fallback=False,
    )
    if isinstance(value, dict) and str(value.get("via") or "") == "jquery_ajax":
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
            "via": "jquery_ajax",
            "from_edit": from_edit,
            "List": value.get("List") if isinstance(value.get("List"), list) else None,
        }
        return out
    fetched = quotes_tab_fetch(
        path="/part/create",
        form_pairs=form_pairs,
        include_list=True,
        base=base,
    )
    fetched["from_edit"] = from_edit
    return fetched


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
      i.dataSource.data(t.List);
    }
    function copyIdent(src, dest) {
      var keys = [
        "CadType", "Stock_X", "Stock_Y", "Stock_Z", "Stock_Units",
        "Stock_Length", "Stock_Diameter",
        "InternalData", "InternalHTML", "ImageString", "HadOpenContours",
        "OutsidePerimeter", "OutsidePerimeter_Units", "OutsidePerimeter_UseLocal"
      ];
      if (!src || !dest) return;
      for (var ki = 0; ki < keys.length; ki++) {
        var k = keys[ki];
        if (src[k] === undefined) continue;
        if (dest[k] !== undefined) continue;
        if (typeof dest.set === "function") dest.set(k, src[k]);
        else dest[k] = src[k];
      }
    }
    var live = i.dataSource.data();
    for (var bi = 0; bi < t.List.length; bi++) {
      var src = t.List[bi] || {};
      var sid = String(src.SourceDataID || src.ID || src.FileID || "");
      for (var ri = 0; ri < live.length; ri++) {
        var rid = String(live[ri].SourceDataID || live[ri].ID || live[ri].FileID || "");
        if (sid && rid && sid === rid) copyIdent(src, live[ri]);
      }
    }
    var first = {};
    try {
      first = (live[0] && live[0].toJSON) ? live[0].toJSON() : (live[0] || {});
      copyIdent(live[0] || {}, first);
    } catch (e3) {}
    var logKeys = [
      "CadType", "Stock_X", "Stock_Y", "Stock_Z", "Stock_Units",
      "Stock_Length", "Stock_Diameter", "FileType", "SourceDataID", "FileID", "ID",
      "InternalData", "InternalHTML", "ImageString", "HadOpenContours",
      "OutsidePerimeter"
    ];
    var kendoKeys = [];
    for (var lk = 0; lk < logKeys.length; lk++) {
      if (first && first[logKeys[lk]] !== undefined) kendoKeys.push(logKeys[lk]);
    }
    try { gridWin().jQuery('#ulDXFTab a[href="#dxfparts"]').tab("show"); } catch (e2) {}
    return {
      grid_present: true,
      has_gridDXFParts: true,
      grid_dxf_row_count: gridCount(),
      bound: true,
      list_len: t.List.length,
      kendo_row_keys: kendoKeys
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
  function sidEmpty(v) {
    return v == null || v === "" || v === 0 || v === "0";
  }
  function fillRowSid(r) {
    if (!r || typeof r !== "object") return r;
    if (!sidEmpty(r.SourceDataID)) return r;
    var id = r.ID;
    if (sidEmpty(id)) id = r.FileID;
    if (sidEmpty(id)) return r;
    if (typeof r.set === "function") r.set("SourceDataID", id);
    else r.SourceDataID = id;
    return r;
  }
  function persistFileType(r) {
    if (!r || typeof r !== "object") return r;
    if (r.FileType != null && String(r.FileType) !== "") return r;
    var cat = String(r.ItemType || r.Category || "");
    if (cat !== "Cad" && cat !== "Linear" && cat !== "Assembly" && cat !== "Component") {
      var mode = Number(r.PartMode);
      if (mode === 0) cat = "Cad";
      else if (mode === 1) cat = "Linear";
      else if (mode === 2) cat = "Component";
      else return r;
    }
    if (typeof r.set === "function") r.set("FileType", cat);
    else r.FileType = cat;
    return r;
  }
  function payloadEmpty(v) {
    if (v == null) return true;
    if (typeof v === "string") {
      var s = String(v).trim().toLowerCase();
      return !s || s === "[]" || s === "{}" || s === "null" || s === "undefined" || s === "none";
    }
    if (typeof v === "object") {
      if (Array.isArray(v)) return v.length === 0;
      return Object.keys(v).length === 0;
    }
    return false;
  }
  function isCadRow(r) {
    if (!r || typeof r !== "object") return false;
    var ft = String(r.FileType || "");
    if (ft === "Cad") return true;
    var cat = String(r.ItemType || r.Category || "");
    if (cat === "Cad") return true;
    return Number(r.PartMode) === 0;
  }
  function keepIdentity(src, dest) {
    var keys = [
      "CadType", "Stock_X", "Stock_Y", "Stock_Z", "Stock_Units",
      "Stock_Length", "Stock_Diameter", "FileType", "SourceDataID", "FileID", "ID",
      "InternalData", "InternalHTML", "ImageString", "HadOpenContours",
      "OutsidePerimeter", "OutsidePerimeter_Units", "OutsidePerimeter_UseLocal"
    ];
    if (!src || !dest) return dest;
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (src[k] === undefined) continue;
      if (dest[k] !== undefined) continue;
      dest[k] = src[k];
    }
    return dest;
  }
  function gridData() {
    try {
      var g = window.jQuery && jQuery("#gridDXFParts").data("kendoGrid");
      if (!g || !g.dataSource) return [];
      var raw = g.dataSource.data();
      if ((!raw || !raw.length) && g.dataSource.view) raw = g.dataSource.view();
      var out = [];
      for (var i = 0; i < (raw ? raw.length : 0); i++) {
        fillRowSid(raw[i]);
        persistFileType(raw[i]);
        var json = (raw[i] && raw[i].toJSON) ? raw[i].toJSON() : raw[i];
        if (json && typeof json === "object") {
          keepIdentity(raw[i], json);
          persistFileType(json);
          fillRowSid(json);
          out.push(json);
        }
      }
      return out;
    } catch (e) { return []; }
  }
  function countField(fl, field) {
    var n = 0;
    for (var i = 0; i < (fl ? fl.length : 0); i++) {
      if (!sidEmpty((fl[i] || {})[field])) n++;
    }
    return n;
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
      grid_dxf_row_count: gridData().length
    };
  }
  function kendoGridPresent() {
    try {
      return !!(window.jQuery && jQuery("#gridDXFParts").data("kendoGrid"));
    } catch (e) { return false; }
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
  function rowKeys(row) {
    if (!row || typeof row !== "object") return [];
    return Object.keys(row).filter(function(k) { return k !== "uid"; }).sort();
  }
  var COMPARE_KEYS = [
    "Status", "Thickness", "Material", "Width", "Length",
    "CadType", "FileType", "SourceDataID", "FileID", "Stock_X", "Stock_Y"
  ];
  var IDENTITY_KEYS = ["CadType", "Stock_X", "Stock_Y"];
  function missingOf(keys, need) {
    var have = {};
    for (var i = 0; i < keys.length; i++) have[keys[i]] = true;
    var miss = [];
    for (var j = 0; j < need.length; j++) {
      if (!have[need[j]]) miss.push(need[j]);
    }
    return miss;
  }
  function finishWhy(fromKendo, afOnDoc, afInReq, krows, sid_n, n, identMiss) {
    var why = [];
    if (!kendoGridPresent()) why.push("wrong_document");
    if (kendoGridPresent() && !krows.length) why.push("empty_dataSource");
    if (n > 0 && sid_n === 0) why.push("filelist_missing_ids");
    else if (!fromKendo) why.push("filelist_not_kendo");
    if (!afOnDoc) why.push("af_missing_on_document");
    else if (!afInReq) why.push("af_not_in_request");
    if (identMiss && identMiss.length) {
      why.push("filelist_missing_keys=" + identMiss.join("+"));
    }
    return why.join(",");
  }
  var rows = gridData();
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
  var kendoIdentKeys = rowKeys(rows[0]);
  var kendoIdentMiss = missingOf(kendoIdentKeys, IDENTITY_KEYS);
  if (kendoIdentMiss.length) {
    return Promise.resolve(Object.assign(summarize(0, null), {
      via: "skipped",
      finish_fn: "",
      reads_kendo: kendoGridPresent(),
      grid_dxf_row_count: count,
      filelist_from_kendo: false,
      finish_af_present: false,
      kendo_row_keys: kendoIdentKeys,
      filelist_row_keys: kendoIdentKeys,
      filelist_missing_keys: missingOf(kendoIdentKeys, COMPARE_KEYS),
      filelist_missing_identity: kendoIdentMiss,
      filelist_errorstatus: Number((rows[0] || {}).ErrorStatus != null ? rows[0].ErrorStatus : 0),
      filelist_qty: Number((rows[0] || {}).Qty != null ? rows[0].Qty : ((rows[0] || {}).Quantity != null ? rows[0].Quantity : 0)),
      filelist_filetype_value: ((rows[0] || {}).FileType == null) ? "" : String(rows[0].FileType),
      filelist_filetype_type: ((rows[0] || {}).FileType === undefined) ? "missing" : typeof rows[0].FileType,
      filelist_cad_path_keys: [],
      filelist_internaldata_empty: payloadEmpty((rows[0] || {}).InternalData),
      filelist_imagestring_empty: payloadEmpty((rows[0] || {}).ImageString),
      finish_why: "filelist_missing_keys=" + kendoIdentMiss.join("+")
    }));
  }
  if (isCadRow(rows[0]) && (
      (rows[0].InternalData !== undefined && payloadEmpty(rows[0].InternalData))
      || (rows[0].ImageString !== undefined && payloadEmpty(rows[0].ImageString))
  )) {
    return Promise.resolve(Object.assign(summarize(0, null), {
      via: "skipped",
      finish_fn: "",
      reads_kendo: kendoGridPresent(),
      grid_dxf_row_count: count,
      filelist_from_kendo: false,
      finish_af_present: false,
      kendo_row_keys: kendoIdentKeys,
      filelist_row_keys: kendoIdentKeys,
      filelist_missing_keys: missingOf(kendoIdentKeys, COMPARE_KEYS),
      filelist_missing_identity: [],
      filelist_errorstatus: Number((rows[0] || {}).ErrorStatus != null ? rows[0].ErrorStatus : 0),
      filelist_qty: Number((rows[0] || {}).Qty != null ? rows[0].Qty : ((rows[0] || {}).Quantity != null ? rows[0].Quantity : 0)),
      filelist_filetype_value: ((rows[0] || {}).FileType == null) ? "" : String(rows[0].FileType),
      filelist_filetype_type: ((rows[0] || {}).FileType === undefined) ? "missing" : typeof rows[0].FileType,
      filelist_cad_path_keys: [],
      filelist_internaldata_empty: payloadEmpty((rows[0] || {}).InternalData),
      filelist_imagestring_empty: payloadEmpty((rows[0] || {}).ImageString),
      finish_why: "filelist_cad_payload_empty"
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
        var krows = gridData();
        if (krows.length) {
          opts.data.FileList = krows;
        }
        attachChromeDomAf(opts.data);
        arguments[0] = opts;
        var d = opts.data;
        var fl = d.FileList || d.fileList || [];
        var n = Array.isArray(fl) ? fl.length : 0;
        var req_keys = Object.keys(d);
        var sid_n = countField(fl, "SourceDataID");
        var id_n = countField(fl, "ID");
        var fileid_n = countField(fl, "FileID");
        var ft = {Cad: 0, Linear: 0, Assembly: 0, Component: 0, blank: 0};
        for (var fi = 0; fi < n; fi++) {
          var r = fl[fi] || {};
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
        var fromThisDs = kendoGridPresent() && krows.length > 0 && fl === krows;
        var fromKendo = fromThisDs && n > 0 && sid_n === n;
        var afOnDoc = hasChromeDomAf();
        var afInReq = hasAf(d);
        var postedKeys = n > 0 ? rowKeys(fl[0]) : [];
        var identMiss = missingOf(postedKeys, IDENTITY_KEYS);
        var first = n > 0 ? (fl[0] || {}) : {};
        var ftRaw = first.FileType;
        var ftType = (ftRaw === undefined) ? "missing" : typeof ftRaw;
        var qtyRaw = first.Qty != null ? first.Qty : first.Quantity;
        var cadPath = [
          "InternalData", "InternalHTML", "ImageString", "HadOpenContours",
          "OutsidePerimeter", "OutsidePerimeter_Units", "OutsidePerimeter_UseLocal",
          "Unfold", "HasUnfold", "Unfolded",
          "DXF", "DxfId", "DXFID", "DxfFileID", "HasDXF"
        ];
        var cadPathHave = [];
        for (var ck = 0; ck < cadPath.length; ck++) {
          if (first[cadPath[ck]] !== undefined) cadPathHave.push(cadPath[ck]);
        }
        var cap = {
          finish_filelist_n: n,
          request_keys: req_keys,
          kendo_row_keys: kendoIdentKeys,
          filelist_errorstatus: Number(first.ErrorStatus != null ? first.ErrorStatus : 0),
          filelist_qty: Number(qtyRaw != null ? qtyRaw : 0),
          filelist_filetype_value: (ftRaw === undefined || ftRaw === null) ? "" : String(ftRaw),
          filelist_filetype_type: ftType,
          filelist_cad_path_keys: cadPathHave,
          filelist_internaldata_empty: payloadEmpty(first.InternalData),
          filelist_imagestring_empty: payloadEmpty(first.ImageString),
          filelist_from_kendo: fromKendo,
          filelist_sourcedataid_n: sid_n,
          filelist_id_n: id_n,
          filelist_fileid_n: fileid_n,
          filelist_filetype: ft,
          filelist_row_keys: postedKeys,
          filelist_missing_keys: missingOf(postedKeys, COMPARE_KEYS),
          filelist_missing_identity: identMiss,
          finish_af_present: afInReq,
          finish_why: finishWhy(
            fromKendo, afOnDoc, afInReq, krows, sid_n, n, identMiss
          )
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
        finish_why: finishWhy(false, hasChromeDomAf(), false, rows, 0, 0, []),
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
    extra.filelist_id_n = Number(hit.filelist_id_n || 0);
    extra.filelist_fileid_n = Number(hit.filelist_fileid_n || 0);
    extra.kendo_row_keys = hit.kendo_row_keys || kendoIdentKeys || [];
    extra.filelist_row_keys = hit.filelist_row_keys || [];
    extra.filelist_missing_keys = hit.filelist_missing_keys || [];
    extra.filelist_missing_identity = hit.filelist_missing_identity || [];
    extra.filelist_filetype = hit.filelist_filetype || {};
    extra.filelist_errorstatus = hit.filelist_errorstatus;
    extra.filelist_qty = hit.filelist_qty;
    extra.filelist_filetype_value = String(hit.filelist_filetype_value || "");
    extra.filelist_filetype_type = String(hit.filelist_filetype_type || "");
    extra.filelist_cad_path_keys = hit.filelist_cad_path_keys || [];
    extra.filelist_internaldata_empty = !!hit.filelist_internaldata_empty;
    extra.filelist_imagestring_empty = !!hit.filelist_imagestring_empty;
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
    from .website import part_create_list_payload_empty_bools

    payload = part_create_list_payload_empty_bools(kids)
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
        "kendo_row_keys": [],
        "internaldata_empty": payload["internaldata_empty"],
        "imagestring_empty": payload["imagestring_empty"],
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
    raw_keys = value.get("kendo_row_keys") if present else None
    kendo_keys = (
        [str(k) for k in raw_keys if str(k)] if isinstance(raw_keys, list) else []
    )
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
        "kendo_row_keys": kendo_keys,
        "internaldata_empty": payload["internaldata_empty"],
        "imagestring_empty": payload["imagestring_empty"],
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
        "filelist_sourcedataid_n": 0,
        "filelist_id_n": 0,
        "filelist_fileid_n": 0,
        "filelist_row_keys": [],
        "filelist_missing_keys": [],
        "filelist_missing_identity": [],
        "kendo_row_keys": [],
        "filelist_errorstatus": None,
        "filelist_qty": None,
        "filelist_filetype_value": "",
        "filelist_filetype_type": "",
        "filelist_cad_path_keys": [],
        "filelist_internaldata_empty": True,
        "filelist_imagestring_empty": True,
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
        "filelist_id_n": int(value.get("filelist_id_n") or 0),
        "filelist_fileid_n": int(value.get("filelist_fileid_n") or 0),
        "filelist_row_keys": [
            str(k) for k in (value.get("filelist_row_keys") or [])
        ],
        "filelist_missing_keys": [
            str(k) for k in (value.get("filelist_missing_keys") or [])
        ],
        "filelist_missing_identity": [
            str(k) for k in (value.get("filelist_missing_identity") or [])
        ],
        "kendo_row_keys": [
            str(k) for k in (value.get("kendo_row_keys") or [])
        ],
        "filelist_filetype": (
            value.get("filelist_filetype")
            if isinstance(value.get("filelist_filetype"), dict)
            else {}
        ),
        "filelist_errorstatus": value.get("filelist_errorstatus"),
        "filelist_qty": value.get("filelist_qty"),
        "filelist_filetype_value": str(value.get("filelist_filetype_value") or ""),
        "filelist_filetype_type": str(value.get("filelist_filetype_type") or ""),
        "filelist_cad_path_keys": [
            str(k) for k in (value.get("filelist_cad_path_keys") or [])
        ],
        "filelist_internaldata_empty": bool(value.get("filelist_internaldata_empty")),
        "filelist_imagestring_empty": bool(value.get("filelist_imagestring_empty")),
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


# QuoteOrderEdit Image Files: GetPDFData() / #gridPDF → OnAddPDFClick
# POST /Quote/AddItem_PDFFiles { ID, ItemID, FileList } Status>0.
# Live 1001898-5: reconstructed FileList is not this path.
_PAGE_PDF_FINISH_JS = """(function() {
  function pdfGrid() {
    var ids = ["#gridPDF", "#gridPdf", "#grid_PDF", "#gridPDFFiles", "#grid"];
    for (var i = 0; i < ids.length; i++) {
      try {
        var g = window.jQuery && jQuery(ids[i]).data("kendoGrid");
        if (g && g.dataSource) return {id: ids[i], grid: g};
      } catch (e) {}
    }
    return null;
  }
  function toRows(raw) {
    if (!raw) return [];
    try { if (raw.toJSON) return raw.toJSON(); } catch (e) {}
    var out = [];
    var n = raw.length || 0;
    for (var i = 0; i < n; i++) {
      var r = raw[i];
      try { out.push(r && r.toJSON ? r.toJSON() : r); } catch (e2) { out.push(r); }
    }
    return out;
  }
  function statusOf(r) {
    var s = r && (r.Status != null ? r.Status : r.status);
    return Number(s || 0);
  }
  function getPdfDataFromTbody() {
    var hit = pdfGrid();
    if (!hit || !window.jQuery) return [];
    var out = [];
    try {
      jQuery(hit.id + " tbody tr").each(function() {
        var item = hit.grid.dataItem(this);
        if (item && statusOf(item) > 0) out.push(toRows([item])[0] || item);
      });
    } catch (e) {}
    return out;
  }
  function overlayStatusFromDataItem(rows) {
    var hit = pdfGrid();
    if (!hit) return rows;
    var data = toRows(hit.grid.dataSource.data());
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i] || {};
      if (r.Status != null && Number(r.Status) > 0) continue;
      var name = String(r.FileName || r.fileName || "");
      for (var j = 0; j < data.length; j++) {
        var d = data[j] || {};
        var fn = String(d.FileName || d.fileName || "");
        if (name && fn && fn.toLowerCase() === name.toLowerCase() && statusOf(d) > 0) {
          r.Status = d.Status != null ? d.Status : d.status;
          rows[i] = r;
          break;
        }
      }
    }
    return rows;
  }
  function getPdfData() {
    if (typeof window.GetPDFData === "function") {
      try {
        var d = window.GetPDFData();
        // bag omits Status — do not overlay onto posted FileList
        if (Array.isArray(d) && d.length) return d.slice();
      } catch (e) {}
    }
    var rows = getPdfDataFromTbody();
    rows = overlayStatusFromDataItem(rows);
    return rows.filter(function(r) { return statusOf(r) > 0; });
  }
  function fnSource(fn) {
    try { return Function.prototype.toString.call(fn); } catch (e) { return ""; }
  }
  function postsPdfFinish(src) {
    return String(src || "").indexOf("/Quote/AddItem_PDFFiles") >= 0;
  }
  function readsPdfKendo(src) {
    src = String(src || "");
    return src.indexOf("GetPDFData") >= 0
      || src.indexOf("gridPDF") >= 0
      || src.indexOf("gridPdf") >= 0
      || src.indexOf("dataSource") >= 0;
  }
  function findFinishName() {
    var preferred = ["OnAddPDFClick", "OnAddPDFFilesClick", "AddPDFFiles", "AddItemPDFFiles"];
    for (var i = 0; i < preferred.length; i++) {
      if (typeof window[preferred[i]] === "function") return preferred[i];
    }
    try {
      for (var k in window) {
        var fn = window[k];
        if (typeof fn === "function" && postsPdfFinish(fnSource(fn))) return k;
      }
    } catch (e) {}
    return "";
  }
  function rowKeys(row) {
    if (!row || typeof row !== "object") return [];
    return Object.keys(row).filter(function(k) { return k !== "uid"; }).sort();
  }
  var BAG_KEYS = [
    "Machine", "ProductID", "Qty", "Weight", "Weight_UseLocal",
    "OutsidePerimeter", "OutsidePerimeter_UseLocal", "NumberOfHeads",
    "WeightBorder", "Material", "Thickness", "Length", "Width"
  ];
  function bagSnap(row) {
    var o = {};
    if (!row || typeof row !== "object") return o;
    for (var bi = 0; bi < BAG_KEYS.length; bi++) {
      var bk = BAG_KEYS[bi];
      if (row[bk] !== undefined) o[bk] = row[bk];
    }
    return o;
  }
  function oclNames(row) {
    var ocl = row.OperationCostList || row.operationCostList || [];
    var out = [];
    if (!Array.isArray(ocl)) return out;
    for (var i = 0; i < ocl.length; i++) {
      var op = ocl[i] || {};
      var n = op.CalculatorName || op.calculatorName || "";
      if (n) out.push(String(n));
    }
    return out;
  }
  function list0Pack(data) {
    var o = {
      list_n: 0, tag: "", badge_string: "", production_ready: false,
      ocl_n: 0, ocl_names: [], unit_cost: 0, unit_weight_cost: 0,
      number_of_contours: 0, number_of_pierces: 0
    };
    if (!data || typeof data !== "object") return o;
    var list = data.List || data.list;
    if (!Array.isArray(list)) return o;
    o.list_n = list.length;
    if (!list.length) return o;
    var row = list[0] || {};
    o.tag = row.Tag != null ? String(row.Tag) : "";
    o.badge_string = row.BadgeString != null ? String(row.BadgeString) : "";
    o.production_ready = !!(row.ProductionReady === true || row.ProductionReady === "true");
    var ocl = row.OperationCostList || row.operationCostList || [];
    o.ocl_names = oclNames(row);
    o.ocl_n = Array.isArray(ocl) ? ocl.length : 0;
    var uc = parseFloat(row.UnitCost != null ? row.UnitCost : 0);
    o.unit_cost = isFinite(uc) ? uc : 0;
    var uwc = parseFloat(row.UnitWeightCost != null ? row.UnitWeightCost : 0);
    o.unit_weight_cost = isFinite(uwc) ? uwc : 0;
    var dpp = row.DataPartPDF || row.dataPartPDF || {};
    var nc = parseInt(dpp.NumberOfContours || dpp.numberOfContours || 0, 10);
    var np = parseInt(dpp.NumberOfPierces || dpp.numberOfPierces || 0, 10);
    o.number_of_contours = isFinite(nc) ? nc : 0;
    o.number_of_pierces = isFinite(np) ? np : 0;
    return o;
  }
  function hasAf(d) {
    if (!d || typeof d !== "object") return false;
    var keys = Object.keys(d);
    for (var i = 0; i < keys.length; i++) {
      if (/requestverificationtoken|__requestverificationtoken/i.test(keys[i]) && d[keys[i]]) {
        return true;
      }
    }
    return false;
  }
  function attachChromeDomAf(data) {
    try {
      if (window.kendo && typeof kendo.antiForgeryTokens === "function") {
        var t = kendo.antiForgeryTokens();
        if (t && typeof t === "object") {
          var tk = Object.keys(t);
          for (var j = 0; j < tk.length; j++) {
            if (t[tk[j]]) { data[tk[j]] = t[tk[j]]; return; }
          }
        }
      }
    } catch (e) {}
  }
  function rowHasPerimeter(r) {
    if (!r || typeof r !== "object") return false;
    var op = r.OutsidePerimeter != null ? r.OutsidePerimeter : r.outsidePerimeter;
    var wt = r.Weight != null ? r.Weight : r.weight;
    var opN = parseFloat(op);
    var wtN = parseFloat(wt);
    if (isFinite(opN) && opN > 0) return true;
    if (isFinite(wtN) && wtN > 0) return true;
    return false;
  }
  var krows = getPdfData();
  var count = krows.length;
  var hit = pdfGrid();
  var gridId = hit ? hit.id : "";
  if (count < 1) {
    return Promise.resolve({
      via: "skipped",
      finish_fn: "",
      reads_kendo: false,
      filelist_from_kendo: false,
      finish_filelist_n: 0,
      grid_pdf_row_count: hit && hit.grid && hit.grid.dataSource
        ? (hit.grid.dataSource.data() || []).length : 0,
      grid_id: gridId,
      finish_af_present: false,
      finish_why: hit ? "empty_dataSource" : "wrong_document",
      request_keys: [],
      filelist_row_keys: [],
      kendo_row_keys: [],
      status: 0,
      body_keys: [],
      body_type: "empty",
      has_NewItem: false,
      has_QuoteItem: false,
      text_len: 0,
      List: [],
      response_list_n: 0,
      response_tag: "",
      response_badge_string: "",
      response_production_ready: false,
      response_ocl_n: 0,
      response_ocl_names: [],
      response_unit_cost: 0,
      response_unit_weight_cost: 0,
      response_number_of_contours: 0,
      response_number_of_pierces: 0
    });
  }
  var perimN = 0;
  for (var pi = 0; pi < krows.length; pi++) {
    if (rowHasPerimeter(krows[pi])) perimN += 1;
  }
  if (perimN < 1) {
    return Promise.resolve({
      via: "skipped",
      finish_fn: "",
      reads_kendo: false,
      filelist_from_kendo: false,
      finish_filelist_n: 0,
      grid_pdf_row_count: hit && hit.grid && hit.grid.dataSource
        ? (hit.grid.dataSource.data() || []).length : 0,
      grid_id: gridId,
      finish_af_present: false,
      finish_why: "empty_perimeter",
      request_keys: [],
      filelist_row_keys: [],
      kendo_row_keys: krows.length ? rowKeys(krows[0]) : [],
      status: 0,
      body_keys: [],
      body_type: "empty",
      has_NewItem: false,
      has_QuoteItem: false,
      text_len: 0,
      List: [],
      response_list_n: 0,
      response_tag: "",
      response_badge_string: "",
      response_production_ready: false,
      response_ocl_n: 0,
      response_ocl_names: [],
      response_unit_cost: 0,
      response_unit_weight_cost: 0,
      response_number_of_contours: 0,
      response_number_of_pierces: 0
    });
  }
  var finishName = findFinishName();
  var finishSrc = finishName ? fnSource(window[finishName]) : "";
  var reads_kendo = readsPdfKendo(finishSrc) || typeof window.GetPDFData === "function" || !!hit;
  var hooked = new Promise(function(resolve) {
    if (!window.jQuery || !jQuery.ajax) {
      resolve(null);
      return;
    }
    var orig = jQuery.ajax;
    var done = false;
    jQuery.ajax = function(opts) {
      var url = String((opts && opts.url) || "");
      if (!done && url.indexOf("/Quote/AddItem_PDFFiles") >= 0) {
        done = true;
        jQuery.ajax = orig;
        if (!opts || typeof opts !== "object") opts = {url: url};
        if (typeof opts.data === "string") {
          try { opts.data = JSON.parse(opts.data); } catch (e) { opts.data = {}; }
        }
        if (!opts.data || typeof opts.data !== "object" || Array.isArray(opts.data)) {
          opts.data = {};
        }
        var pageRows = getPdfData();
        if (pageRows.length) opts.data.FileList = pageRows;
        attachChromeDomAf(opts.data);
        arguments[0] = opts;
        var d = opts.data;
        var fl = d.FileList || d.fileList || [];
        var n = Array.isArray(fl) ? fl.length : 0;
        var fromKendo = n > 0 && fl === pageRows;
        var first = n > 0 ? (fl[0] || {}) : {};
        var cap = {
          finish_filelist_n: n,
          request_keys: Object.keys(d),
          filelist_from_kendo: fromKendo,
          filelist_row_keys: n > 0 ? rowKeys(first) : [],
          filelist_bag: n > 0 ? bagSnap(first) : {},
          kendo_row_keys: krows.length ? rowKeys(krows[0]) : [],
          finish_af_present: hasAf(d),
          finish_why: fromKendo ? "" : "filelist_not_kendo",
          grid_id: gridId,
          response_list_n: 0,
          response_tag: "",
          response_badge_string: "",
          response_production_ready: false,
          response_ocl_n: 0,
          response_ocl_names: [],
          response_unit_cost: 0,
          response_unit_weight_cost: 0,
          response_number_of_contours: 0,
          response_number_of_pierces: 0
        };
        var ret = orig.apply(this, arguments);
        Promise.resolve(ret).then(function(data) {
          cap.status = 200;
          cap.data = data;
          var pack = list0Pack(data);
          cap.response_list_n = pack.list_n;
          cap.response_tag = pack.tag;
          cap.response_badge_string = pack.badge_string;
          cap.response_production_ready = pack.production_ready;
          cap.response_ocl_n = pack.ocl_n;
          cap.response_ocl_names = pack.ocl_names;
          cap.response_unit_cost = pack.unit_cost;
          cap.response_unit_weight_cost = pack.unit_weight_cost;
          cap.response_number_of_contours = pack.number_of_contours;
          cap.response_number_of_pierces = pack.number_of_pierces;
          resolve(cap);
        }).catch(function(xhr) {
          cap.status = (xhr && xhr.status) || 0;
          cap.data = (xhr && xhr.responseJSON) || null;
          var packE = list0Pack(xhr && xhr.responseJSON);
          cap.response_list_n = packE.list_n;
          cap.response_tag = packE.tag;
          cap.response_badge_string = packE.badge_string;
          cap.response_production_ready = packE.production_ready;
          cap.response_ocl_n = packE.ocl_n;
          cap.response_ocl_names = packE.ocl_names;
          cap.response_unit_cost = packE.unit_cost;
          cap.response_unit_weight_cost = packE.unit_weight_cost;
          cap.response_number_of_contours = packE.number_of_contours;
          cap.response_number_of_pierces = packE.number_of_pierces;
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
        if (blob.indexOf("onaddpdf") >= 0 || blob.indexOf("new line item") >= 0) {
          el.click();
          via = "page_fn";
          break;
        }
      }
    } catch (e) {}
  }
  if (!via) {
    return Promise.resolve({
      via: "",
      finish_fn: "",
      reads_kendo: reads_kendo,
      filelist_from_kendo: false,
      finish_filelist_n: 0,
      grid_pdf_row_count: count,
      grid_id: gridId,
      finish_af_present: false,
      finish_why: "no_onaddpdfclick",
      request_keys: [],
      filelist_row_keys: krows.length ? rowKeys(krows[0]) : [],
      kendo_row_keys: krows.length ? rowKeys(krows[0]) : [],
      status: 0,
      body_keys: [],
      body_type: "empty",
      has_NewItem: false,
      has_QuoteItem: false,
      text_len: 0,
      List: krows,
      response_list_n: 0,
      response_tag: "",
      response_badge_string: "",
      response_production_ready: false,
      response_ocl_n: 0,
      response_ocl_names: [],
      response_unit_cost: 0,
      response_unit_weight_cost: 0,
      response_number_of_contours: 0,
      response_number_of_pierces: 0
    });
  }
  return hooked.then(function(hitCap) {
    var extra = hitCap || {};
    extra.via = via || "page_fn";
    extra.finish_fn = finishName || "OnAddPDFClick";
    extra.reads_kendo = reads_kendo;
    extra.grid_pdf_row_count = count;
    extra.grid_id = extra.grid_id || gridId;
    extra.List = krows;
    if (!extra.filelist_from_kendo) extra.filelist_from_kendo = false;
    return extra;
  });
})"""


_STAMP_PDF_KENDO_JS = """(function(spec) {
  function pdfGrid() {
    var ids = ["#gridPDF", "#gridPdf", "#grid_PDF", "#gridPDFFiles", "#grid"];
    for (var i = 0; i < ids.length; i++) {
      try {
        var g = window.jQuery && jQuery(ids[i]).data("kendoGrid");
        if (g && g.dataSource) return {id: ids[i], grid: g};
      } catch (e) {}
    }
    return null;
  }
  var emptyStamp = {
    ok: false,
    stamped: 0,
    cell_edit: 0,
    grid_id: "",
    grid_pdf_row_count: 0,
    outside_perimeter_n: 0,
    cutting_length_n: 0,
    weight_n: 0,
    productid_n: 0,
    internaldata_n: 0,
    getperimeter_xhr: false,
    perimeter_via: "",
    feature_via: "",
    picker_via: "",
    picker_sku: "",
    picker_apply: ""
  };
  var hit = pdfGrid();
  if (!hit) return Promise.resolve(emptyStamp);
  var rows = (spec && spec.rows) || [];
  var data = hit.grid.dataSource.data() || [];
  var stamped = 0;
  var viaCell = 0;
  var lastVia = "";
  var lastFeature = "";
  var lastPicker = "";
  var lastPickerSku = "";
  var lastApply = "";
  function setField(r, k, v) {
    if (v == null || v === "") return;
    if (typeof r.set === "function") r.set(k, v);
    else r[k] = v;
  }
  function editSet(grid, r, field, value) {
    if (value == null || value === "") return;
    try {
      var tr = grid.tbody.find("tr").filter(function() {
        return grid.dataItem(this) === r;
      }).first();
      if (tr.length && typeof grid.editCell === "function") {
        var cell = tr.find("td[data-field='" + field + "']");
        if (!cell.length) {
          var cols = grid.columns || [];
          for (var c = 0; c < cols.length; c++) {
            if ((cols[c].field || "") === field) {
              cell = tr.find("td").eq(c);
              break;
            }
          }
        }
        if (cell.length) {
          grid.editCell(cell);
          var editor = cell.find("input, select, textarea").first();
          if (editor.length) {
            editor.val(value).trigger("change").trigger("blur");
            if (typeof grid.closeCell === "function") grid.closeCell();
            viaCell += 1;
            return;
          }
          if (typeof grid.closeCell === "function") grid.closeCell();
        }
      }
    } catch (e) {}
    setField(r, field, value);
  }
  function hookGetPerimeter() {
    if (window.__kannonGetPerimHooked) return;
    if (!window.jQuery || !jQuery.ajax) return;
    window.__kannonGetPerimHooked = true;
    var orig = jQuery.ajax;
    jQuery.ajax = function(opts) {
      var url = String((opts && (opts.url || opts)) || "");
      var method = String((opts && (opts.type || opts.method)) || "GET").toUpperCase();
      if (url.indexOf("/Quote/GetPerimeterAndWeight") >= 0) {
        window.__kannonGetPerim = window.__kannonGetPerim || {};
        window.__kannonGetPerim.xhr = true;
        window.__kannonGetPerim.any = true;
        window.__kannonGetPerim.url = url;
        window.__kannonGetPerim.method = method;
        if (opts && typeof opts === "object") {
          var prev = opts.success;
          opts.success = function(data) {
            try {
              var w = data && (data.Weight != null ? data.Weight : data.weight);
              if (w != null && parseFloat(w) > 0) {
                window.__kannonGetPerim.weight = parseFloat(w);
              }
            } catch (e0) {}
            if (typeof prev === "function") return prev.apply(this, arguments);
          };
        }
      }
      return orig.apply(this, arguments);
    };
  }
  function waitGetPerimeter(timeoutMs) {
    return new Promise(function(resolve) {
      var t0 = Date.now();
      (function poll() {
        if (window.__kannonGetPerim && window.__kannonGetPerim.xhr) {
          resolve(true);
          return;
        }
        if (Date.now() - t0 > timeoutMs) {
          resolve(false);
          return;
        }
        setTimeout(poll, 40);
      })();
    });
  }
  function fireUpdatePerimeterWeight() {
    try {
      if (typeof window.UpdatePerimeterWeight === "function") {
        window.UpdatePerimeterWeight(true, true);
        return "UpdatePerimeterWeight";
      }
    } catch (e) {}
    try {
      if (typeof window.onLength === "function") {
        window.onLength();
        return "onLength";
      }
    } catch (e2) {}
    try {
      if (typeof window.onWidth === "function") {
        window.onWidth();
        return "onWidth";
      }
    } catch (e3) {}
    try {
      if (window.jQuery) {
        var $len = jQuery("#Length");
        if ($len.length) {
          $len.trigger("change");
          return "#Length.change";
        }
        var $w = jQuery("#Width");
        if ($w.length) {
          $w.trigger("change");
          return "#Width.change";
        }
        var $op = jQuery("#OutsidePerimeter");
        if ($op.length) {
          $op.trigger("change");
          return "#OutsidePerimeter.change";
        }
      }
    } catch (e4) {}
    return "";
  }
  function parseNum(v) {
    var n = parseFloat(v);
    if (!isFinite(n) || n <= 0) return "";
    return String(n);
  }
  function copyPerimeterOntoRow(grid, r) {
    var op = "";
    var wt = "";
    try {
      if (window.jQuery) {
        op = String(jQuery("#OutsidePerimeter").val() || "");
        wt = parseNum(jQuery("#Weight").val())
          || parseNum(window.__kannonGetPerim && window.__kannonGetPerim.weight);
      }
    } catch (e) {}
    if (op) {
      setField(r, "OutsidePerimeter", op);
      setField(r, "OutsidePerimeter_UseLocal", true);
    }
    if (wt) {
      setField(r, "Weight", wt);
      setField(r, "Weight_UseLocal", true);
    }
    return {op: op, wt: wt};
  }
  function pidOf(r) {
    var v = r && (r.ProductID != null ? r.ProductID : r.productID);
    if (v == null) return "";
    var s = String(v).trim();
    if (!s || s.toLowerCase() === "null" || s === "undefined") return "";
    return s;
  }
  function emptyVal(v) {
    if (v == null) return true;
    if (typeof v === "string") return !String(v).trim();
    if (Array.isArray(v)) return v.length === 0;
    return false;
  }
  function isProductTypeBar(id, url) {
    var s = (String(id || "") + " " + String(url || "")).toLowerCase();
    return s.indexOf("producttype") >= 0
      || s.indexOf("product_type") >= 0
      || s.indexOf("productsubtype") >= 0
      || s.indexOf("linearlookup") >= 0;
  }
  function isThicknessGauge(id, url) {
    // ThicknessPDF is gauge Read_DataThicknessGauge2 — not the plate picker
    var s = (String(id || "") + " " + String(url || "")).toLowerCase();
    return s.indexOf("thicknesspdf") >= 0
      || s.indexOf("thicknessgauge") >= 0
      || s.indexOf("read_datathickness") >= 0
      || s.indexOf("gauge") >= 0;
  }
  function isPlateProductWidget(id, url) {
    if (isProductTypeBar(id, url)) return false;
    if (isThicknessGauge(id, url)) return false;
    var s = (String(id || "") + " " + String(url || "")).toLowerCase();
    if (s.indexOf("gridselectproductplate") >= 0) return false;
    if (s.indexOf("plate") >= 0) return true;
    if (s.indexOf("/product/read") >= 0 && s.indexOf("type") < 0
        && s.indexOf("linear") < 0 && s.indexOf("thickness") < 0
        && s.indexOf("gauge") < 0) return true;
    var idl = String(id || "").toLowerCase();
    if (idl.indexOf("pdfproduct") >= 0) return true;
    if (idl.indexOf("cmbproduct") >= 0) return true;
    if (idl.indexOf("txtproduct") >= 0) return true;
    if (idl.indexOf("productid") >= 0 && idl.indexOf("type") < 0) return true;
    return false;
  }
  function widgetOf($el) {
    if (!$el || !$el.length) return null;
    return $el.data("kendoComboBox") || $el.data("kendoDropDownList")
      || $el.data("kendoAutoComplete") || $el.data("kendoMultiColumnComboBox")
      || null;
  }
  function widgetUrl(w) {
    try {
      return String((w && w.dataSource && w.dataSource.transport
        && w.dataSource.transport.options && w.dataSource.transport.options.read
        && w.dataSource.transport.options.read.url) || "");
    } catch (e) { return ""; }
  }
  function findProductWidget() {
    var ids = ["#Product", "#ProductID", "#cmbProduct", "#pdfProduct",
               "#txtProduct", "input[name='ProductID']", "input[name='Product']"];
    for (var i = 0; i < ids.length; i++) {
      try {
        var $el = window.jQuery && jQuery(ids[i]);
        var w = widgetOf($el);
        if (!w) continue;
        var id = String($el.attr("id") || $el.attr("name") || ids[i] || "");
        var url = widgetUrl(w);
        if (!isPlateProductWidget(id, url)) continue;
        return {el: $el, widget: w, via: ids[i]};
      } catch (e) {}
    }
    try {
      var widgets = jQuery("[data-role='combobox'], [data-role='dropdownlist']");
      for (var j = 0; j < widgets.length; j++) {
        var $w = jQuery(widgets[j]);
        var ww = widgetOf($w);
        if (!ww) continue;
        var wid = String($w.attr("id") || $w.attr("name") || "");
        var wurl = widgetUrl(ww);
        if (!isPlateProductWidget(wid, wurl)) continue;
        return {el: $w, widget: ww, via: wid || wurl};
      }
    } catch (e3) {}
    return null;
  }
  function itemSku(it) {
    if (!it) return "";
    return String(it.ProductName || it.SKU || it.ProductCode || it.Text
      || it.Name || it.text || it.DisplayName || "");
  }
  function itemValue(it) {
    if (!it) return "";
    var v = it.Value != null ? it.Value : (it.ID != null ? it.ID : it.ProductID);
    if (v == null) v = it.ProductId || it.productId || it.ListValue;
    if (v == null) return "";
    var s = String(v).trim();
    if (!s || s.toLowerCase() === "null") return "";
    return s;
  }
  function normSku(s) {
    return String(s || "").toLowerCase().replace(/[\\s_\\-]+/g, "");
  }
  function plateModalGrid() {
    var ids = ["#gridSelectProductPlate"];
    for (var i = 0; i < ids.length; i++) {
      try {
        var g = window.jQuery && jQuery(ids[i]).data("kendoGrid");
        if (g && g.dataSource) return {id: ids[i], grid: g};
      } catch (e) {}
    }
    return null;
  }
  function clickSheetsAndPlates() {
    try {
      if (!window.jQuery) return "";
      var nodes = document.querySelectorAll("a, button, li, span, label, div");
      for (var i = 0; i < nodes.length; i++) {
        var t = String(nodes[i].textContent || "").replace(/\\s+/g, " ").trim().toLowerCase();
        if (t.indexOf("sheet") >= 0 && t.indexOf("plate") >= 0 && t.length < 40) {
          nodes[i].click();
          return "sheets_and_plates";
        }
      }
    } catch (e) {}
    return "";
  }
  function openPlateModal() {
    var names = ["SelectProductPlate", "OnSelectProductPlate",
                 "OpenSelectProductPlate", "ShowSelectProductPlate"];
    for (var i = 0; i < names.length; i++) {
      try {
        if (typeof window[names[i]] === "function") {
          window[names[i]]();
          return names[i];
        }
      } catch (e) {}
    }
    try {
      if (!window.jQuery) return "";
      var nodes = document.querySelectorAll(
        "button, a, input[type=button], span, i"
      );
      for (var j = 0; j < nodes.length; j++) {
        var el = nodes[j];
        var blob = (
          (el.getAttribute("onclick") || "") + " " + (el.id || "")
          + " " + (el.className || "") + " " + (el.textContent || "")
        ).toLowerCase();
        if (blob.indexOf("selectproductplate") >= 0
            || blob.indexOf("gridselectproductplate") >= 0) {
          el.click();
          return "click";
        }
      }
    } catch (e2) {}
    return "";
  }
  function pickPlateModal(sku, pdfRow) {
    lastPickerSku = sku;
    lastApply = "search_only";
    var hit = plateModalGrid();
    if (!hit) {
      openPlateModal();
      hit = plateModalGrid();
    }
    if (!hit) {
      lastPicker = "none_plate_widget";
      return Promise.resolve("");
    }
    lastPicker = hit.id;
    clickSheetsAndPlates();
    var g = hit.grid;
    var want = String(sku).toLowerCase();
    var wantN = normSku(sku);
    function matchRow(it) {
      var nm = itemSku(it).toLowerCase();
      var nn = normSku(itemSku(it));
      return !!(nm && (nm === want || nm.indexOf(want) >= 0 || want.indexOf(nm) >= 0
        || (nn && nn === wantN)));
    }
    function modalApplyClick() {
      try {
        var $root = jQuery(hit.id).closest(".k-window, .k-widget, .modal, .k-dialog");
        if (!$root || !$root.length) $root = jQuery(hit.id).parent();
        var btns = $root.find("button, a, input[type=button], input[type=submit]");
        for (var b = 0; b < btns.length; b++) {
          var t = String(btns[b].textContent || btns[b].value || "").toLowerCase().trim();
          var oid = String(btns[b].id || "").toLowerCase();
          if (t === "select" || t === "ok" || t === "apply"
              || oid.indexOf("selectproduct") >= 0
              || oid.indexOf("apply") >= 0) {
            btns[b].click();
            return true;
          }
        }
      } catch (e) {}
      return false;
    }
    function pageApplyFn() {
      var names = ["OnSelectProductPlate", "SelectProductPlateOK",
                   "ApplySelectProductPlate", "gridSelectProductPlate_Change"];
      for (var i = 0; i < names.length; i++) {
        try {
          if (typeof window[names[i]] === "function") {
            window[names[i]]();
            return names[i];
          }
        } catch (e) {}
      }
      return "";
    }
    function applyRow(it) {
      lastApply = "modal_apply";
      try {
        var tr = g.tbody.find("tr").filter(function() {
          return g.dataItem(this) === it;
        }).first();
        if (tr.length && typeof g.select === "function") g.select(tr);
        try { if (typeof g.trigger === "function") g.trigger("change"); } catch (e0) {}
        if (tr.length) {
          tr.trigger("dblclick");
          tr.trigger("click");
        }
      } catch (e) {}
      modalApplyClick();
      pageApplyFn();
      return new Promise(function(resolve) {
        setTimeout(function() {
          var landed = pidOf(pdfRow) || itemValue(it);
          resolve(landed || "");
        }, 250);
      });
    }
    try {
      if (g.dataSource && typeof g.dataSource.filter === "function") {
        g.dataSource.filter({field: "ProductName", operator: "contains", value: sku});
      }
    } catch (e3) {}
    function scan() {
      var rows = [];
      try { rows = (g.dataSource.data && g.dataSource.data()) || []; } catch (e4) {}
      for (var i = 0; i < rows.length; i++) {
        if (matchRow(rows[i])) return applyRow(rows[i]);
      }
      return Promise.resolve("");
    }
    return scan().then(function(now) {
      if (now) return now;
      if (g.dataSource && typeof g.dataSource.read === "function") {
        return Promise.resolve(g.dataSource.read()).then(function() {
          return scan();
        }).catch(function() { return ""; });
      }
      return "";
    });
  }
  function pickProduct(sku, pdfRow) {
    lastPicker = "";
    lastPickerSku = "";
    lastApply = "";
    if (!sku || !window.jQuery) return Promise.resolve("");
    var hitW = findProductWidget();
    if (!hitW) return pickPlateModal(sku, pdfRow);
    var w = hitW.widget;
    lastPicker = hitW.via;
    lastPickerSku = sku;
    try {
      if (typeof w.search === "function") w.search(sku);
    } catch (e) {}
    function applyItem(it) {
      var val = itemValue(it);
      if (!val) return "";
      try {
        if (typeof w.value === "function") w.value(val);
        if (typeof w.trigger === "function") w.trigger("change");
        else if (hitW.el && hitW.el.trigger) hitW.el.trigger("change");
      } catch (e2) {}
      return val;
    }
    var data = [];
    try { data = (w.dataSource && w.dataSource.data && w.dataSource.data()) || []; } catch (e3) {}
    var want = String(sku).toLowerCase();
    for (var i = 0; i < data.length; i++) {
      var nm = itemSku(data[i]).toLowerCase();
      if (nm && (nm === want || nm.indexOf(want) >= 0 || want.indexOf(nm) >= 0)) {
        return Promise.resolve(applyItem(data[i]));
      }
    }
    if (w.dataSource && typeof w.dataSource.filter === "function") {
      try {
        w.dataSource.filter({field: "ProductName", operator: "contains", value: sku});
      } catch (e4) {}
    }
    if (w.dataSource && typeof w.dataSource.read === "function") {
      return Promise.resolve(w.dataSource.read()).then(function() {
        var rows = [];
        try { rows = (w.dataSource.data && w.dataSource.data()) || []; } catch (e5) {}
        for (var j = 0; j < rows.length; j++) {
          var nm2 = itemSku(rows[j]).toLowerCase();
          if (nm2 && (nm2 === want || nm2.indexOf(want) >= 0 || want.indexOf(nm2) >= 0)) {
            return applyItem(rows[j]);
          }
        }
        return "";
      }).catch(function() { return ""; });
    }
    return Promise.resolve("");
  }
  function pagePdfGetData() {
    try {
      if (typeof window.PDFGetData === "function") {
        var feat = window.PDFGetData();
        if (feat == null) return "";
        if (typeof feat === "string") return feat;
        return JSON.stringify(feat);
      }
    } catch (e) {}
    return "";
  }
  function addPdfHoleFeature(r) {
    // Kyle Loom: Add Feature Hole then green New Line Item.
    // Do not cookie-POST AddFeature (item-level). Do not invent JSON.
    lastFeature = "";
    if (typeof window.AddNewPDFFeature !== "function") {
      lastFeature = "none_addnewpdffeature";
      return Promise.resolve("");
    }
    try {
      window.AddNewPDFFeature("Hole", "cad");
      lastFeature = "AddNewPDFFeature";
    } catch (e) {
      lastFeature = "AddNewPDFFeature_err";
      return Promise.resolve("");
    }
    return new Promise(function(resolve) {
      setTimeout(function() {
        var raw = pagePdfGetData();
        if (raw && raw !== "[]" && raw !== "{}" && raw !== "null") {
          setField(r, "InternalData", raw);
        }
        try {
          if (typeof window.onInternalDataChange === "function") {
            window.onInternalDataChange();
          }
        } catch (e2) {}
        resolve(lastFeature);
      }, 400);
    });
  }
  function stampPerimeter(grid, r) {
    try {
      var tr = grid.tbody.find("tr").filter(function() {
        return grid.dataItem(this) === r;
      }).first();
      if (tr.length && typeof grid.select === "function") grid.select(tr);
    } catch (e) {}
    if (window.__kannonGetPerim) window.__kannonGetPerim.xhr = false;
    lastVia = fireUpdatePerimeterWeight() || lastVia;
    return waitGetPerimeter(8000).then(function() {
      copyPerimeterOntoRow(grid, r);
    });
  }
  function countFilled(src) {
    var opN = 0;
    var clN = 0;
    var wtN = 0;
    var pidN = 0;
    var idN = 0;
    var n = src.length || 0;
    for (var i = 0; i < n; i++) {
      var r = src[i] || {};
      if (Number(r.OutsidePerimeter) > 0) opN += 1;
      if (parseFloat(r.Weight) > 0) wtN += 1;
      if (pidOf(r)) pidN += 1;
      if (!emptyVal(r.InternalData)) idN += 1;
    }
    return {opN: opN, clN: clN, wtN: wtN, pidN: pidN, idN: idN};
  }
  hookGetPerimeter();
  window.__kannonGetPerim = window.__kannonGetPerim || {
    xhr: false, url: "", method: "", any: false
  };
  var chain = Promise.resolve();
  for (var i = 0; i < rows.length; i++) {
    (function(s, idx) {
      chain = chain.then(function() {
        var name = String(s.FileName || "");
        for (var j = 0; j < data.length; j++) {
          var r = data[j];
          var fn = String((r.FileName || r.fileName || ""));
          if (name && fn && fn.toLowerCase() !== name.toLowerCase()
              && fn.toLowerCase().indexOf(name.toLowerCase()) < 0
              && name.toLowerCase().indexOf(fn.toLowerCase()) < 0) {
            continue;
          }
          if (!name && idx !== j) continue;
          var keepPid = pidOf(r);
          editSet(hit.grid, r, "Length", s.Length);
          editSet(hit.grid, r, "Width", s.Width);
          editSet(hit.grid, r, "Thickness", s.Thickness);
          editSet(hit.grid, r, "Machine", s.Machine || "Laser - Bay1");
          editSet(hit.grid, r, "Status", s.Status != null ? s.Status : 1);
          editSet(hit.grid, r, "ItemType", s.ItemType || "cad");
          editSet(hit.grid, r, "Material", s.Material);
          if (s.Qty != null) editSet(hit.grid, r, "Qty", s.Qty);
          if (s.PartName) editSet(hit.grid, r, "PartName", s.PartName);
          stamped += 1;
          return addPdfHoleFeature(r).then(function() {
            return stampPerimeter(hit.grid, r).then(function() {
              if (keepPid) setField(r, "ProductID", keepPid);
              return pickProduct(s.ProductSku, r).then(function(val) {
                if (val) setField(r, "ProductID", val);
              });
            });
          });
        }
      });
    })(rows[i] || {}, i);
  }
  return chain.then(function() {
    var filled = countFilled(data);
    return {
      ok: stamped > 0,
      stamped: stamped,
      cell_edit: viaCell,
      grid_id: hit.id,
      grid_pdf_row_count: data.length,
      outside_perimeter_n: filled.opN,
      cutting_length_n: filled.clN,
      weight_n: filled.wtN,
      productid_n: filled.pidN,
      internaldata_n: filled.idN,
      getperimeter_xhr: !!(window.__kannonGetPerim && window.__kannonGetPerim.any),
      perimeter_via: lastVia,
      feature_via: lastFeature,
      picker_via: lastPicker,
      picker_sku: lastPickerSku,
      picker_apply: lastApply
    };
  });
})"""


def invoke_page_pdf_finish(
    *,
    base: str | None = None,
    quote_id: str | None = None,
) -> dict[str, Any]:
    """Kyle Image Files Finish: page OnAddPDFClick posts GetPDFData FileList."""
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    skipped = {
        "via": "skipped",
        "finish_fn": "",
        "reads_kendo": False,
        "grid_pdf_row_count": 0,
        "grid_id": "",
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
        "filelist_row_keys": [],
        "filelist_bag": {},
        "kendo_row_keys": [],
        "finish_af_present": False,
        "finish_why": "wrong_document",
        "ok": False,
        "response_list_n": 0,
        "response_tag": "",
        "response_badge_string": "",
        "response_production_ready": False,
        "response_ocl_n": 0,
        "response_ocl_names": [],
        "response_unit_cost": 0.0,
        "response_unit_weight_cost": 0.0,
        "response_number_of_contours": 0,
        "response_number_of_pierces": 0,
    }
    if not gate.get("ok"):
        return skipped
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    value = _cdp_evaluate_promise(
        _PAGE_PDF_FINISH_JS + "()", base=base, tab=tab, fallback=False
    )
    if not isinstance(value, dict):
        skipped["edit_gate"] = "finish_eval_empty"
        return skipped
    via = str(value.get("via") or "")
    if via and via not in {"page_fn", "skipped"}:
        via = "page_fn"
    from_kendo = bool(value.get("filelist_from_kendo")) and via == "page_fn"
    try:
        response_list_n = int(value.get("response_list_n") or 0)
    except (TypeError, ValueError):
        response_list_n = 0
    try:
        response_ocl_n = int(value.get("response_ocl_n") or 0)
    except (TypeError, ValueError):
        response_ocl_n = 0
    try:
        response_unit_cost = float(value.get("response_unit_cost") or 0)
    except (TypeError, ValueError):
        response_unit_cost = 0.0
    try:
        response_unit_weight_cost = float(value.get("response_unit_weight_cost") or 0)
    except (TypeError, ValueError):
        response_unit_weight_cost = 0.0
    try:
        response_number_of_contours = int(value.get("response_number_of_contours") or 0)
    except (TypeError, ValueError):
        response_number_of_contours = 0
    try:
        response_number_of_pierces = int(value.get("response_number_of_pierces") or 0)
    except (TypeError, ValueError):
        response_number_of_pierces = 0
    ocl_names = [
        str(n) for n in (value.get("response_ocl_names") or []) if str(n).strip()
    ]
    return {
        "via": via,
        "finish_fn": str(value.get("finish_fn") or ""),
        "reads_kendo": bool(value.get("reads_kendo")),
        "grid_pdf_row_count": int(value.get("grid_pdf_row_count") or 0),
        "grid_id": str(value.get("grid_id") or ""),
        "finish_filelist_n": int(value.get("finish_filelist_n") or 0),
        "request_keys": [str(k) for k in (value.get("request_keys") or [])],
        "filelist_from_kendo": from_kendo,
        "filelist_row_keys": [str(k) for k in (value.get("filelist_row_keys") or [])],
        "filelist_bag": (
            dict(value["filelist_bag"])
            if isinstance(value.get("filelist_bag"), dict)
            else {}
        ),
        "kendo_row_keys": [str(k) for k in (value.get("kendo_row_keys") or [])],
        "finish_af_present": bool(value.get("finish_af_present")),
        "finish_why": str(value.get("finish_why") or ""),
        "status": int(value.get("status") or 0),
        "body_keys": [str(k) for k in (value.get("body_keys") or [])],
        "body_type": str(value.get("body_type") or "empty"),
        "has_NewItem": bool(value.get("has_NewItem")),
        "has_QuoteItem": bool(value.get("has_QuoteItem")),
        "text_len": int(value.get("text_len") or 0),
        "List": [r for r in (value.get("List") or []) if isinstance(r, dict)],
        "edit_quote_id": str(gate.get("edit_quote_id") or ""),
        "minted_id": str(gate.get("minted_id") or quote_id or ""),
        "edit_gate": "",
        "ok": from_kendo,
        "response_list_n": response_list_n,
        "response_tag": str(value.get("response_tag") or ""),
        "response_badge_string": str(value.get("response_badge_string") or ""),
        "response_production_ready": bool(value.get("response_production_ready")),
        "response_ocl_n": response_ocl_n,
        "response_ocl_names": ocl_names,
        "response_unit_cost": response_unit_cost,
        "response_unit_weight_cost": response_unit_weight_cost,
        "response_number_of_contours": response_number_of_contours,
        "response_number_of_pierces": response_number_of_pierces,
    }


def stamp_pdf_kendo_flats(
    rows: list[dict[str, Any]],
    *,
    quote_id: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """Type L×W in kendo cells, then UpdatePerimeterWeight(true,true).

    Live 29743-1: dataItem.set skipped UpdatePerimeterWeight /
    POST /Quote/GetPerimeterAndWeight. Posted OutsidePerimeter
    empty → server List no PR/laser pack. Do not invent perimeter.
    Live 1002323-1: bare UpdatePerimeterWeight() does not copy
    (n/t falsy). XHR OutsidePerimeter landed; List CuttingLength
    stayed 0. GetPDFData omits CuttingLength — do not invent
    that key and do not set dataItem.CuttingLength.     Copy bag
    Weight / Weight_UseLocal from #Weight / the XHR. Upload List
    ProductID is always null on Image Files PDFs (live 21681-1) —
    keepPid has nothing to restore. Stamp drawing Material /
    Thickness / Machine=Laser Bay 1 (overwrite 316 Polished /
    0.0178) and Status>0. Drive the plate Product kendo (not
    the ProductType bar) by tenant SKU text so GetPDFData
    ProductID is the selected List Value. Do not invent a GUID.
    Named hole step is ``AddNewPDFFeature(feature, "cad")``
    then page ``PDFGetData()`` onto the selected #gridPDF
    InternalData (do not invent JSON; do not cookie-POST
    /Quote/AddFeature). Then UpdatePerimeterWeight(true,true)
    / onInternalDataChange. AddNewPDFFeature() with no args
    is not gold. Empty InternalData is still expected for
    no-hole rectangles. Live 1007092-1: first
    ``#Product`` is ProductType — skip it. Live 33204-1:
    ThicknessPDF is gauge (Read_DataThicknessGauge2). Drive
    ``#gridSelectProductPlate`` modal apply/select (dblclick +
    modal Select), not search-only. Live 1009213-1: modal SKU
    did not land FileList ProductID. ProductID is not the pack.
    """
    spec_rows: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        spec_rows.append(
            {
                "FileName": str(row.get("FileName") or ""),
                "Length": row.get("Length"),
                "Width": row.get("Width"),
                "Thickness": row.get("Thickness"),
                "Machine": str(row.get("Machine") or "Laser - Bay1"),
                "Status": row.get("Status") if row.get("Status") not in (None, "") else 1,
                "ItemType": str(row.get("ItemType") or "cad"),
                "Material": row.get("Material"),
                "Qty": row.get("Qty"),
                "PartName": row.get("PartName") or row.get("Description") or "",
                "ProductSku": str(row.get("ProductSku") or row.get("SKU") or "").strip(),
            }
        )
    empty = {
        "ok": False,
        "stamped": 0,
        "cell_edit": 0,
        "grid_id": "",
        "grid_pdf_row_count": 0,
        "edit_gate": "",
        "outside_perimeter_n": 0,
        "cutting_length_n": 0,
        "weight_n": 0,
        "productid_n": 0,
        "internaldata_n": 0,
        "getperimeter_xhr": False,
        "perimeter_via": "",
        "feature_via": "",
        "picker_via": "",
        "picker_sku": "",
        "picker_apply": "",
    }
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    empty["edit_gate"] = str(gate.get("reason") or "")
    if not gate.get("ok"):
        return empty
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    expression = (
        _STAMP_PDF_KENDO_JS
        + "("
        + json.dumps({"rows": spec_rows}, separators=(",", ":"))
        + ")"
    )
    value = _cdp_evaluate_promise(
        expression, base=base, tab=tab, fallback=False
    )
    if not isinstance(value, dict):
        return empty
    return {
        "ok": bool(value.get("ok")),
        "stamped": int(value.get("stamped") or 0),
        "cell_edit": int(value.get("cell_edit") or 0),
        "grid_id": str(value.get("grid_id") or ""),
        "grid_pdf_row_count": int(value.get("grid_pdf_row_count") or 0),
        "edit_gate": "",
        "outside_perimeter_n": int(value.get("outside_perimeter_n") or 0),
        "cutting_length_n": int(value.get("cutting_length_n") or 0),
        "weight_n": int(value.get("weight_n") or 0),
        "productid_n": int(value.get("productid_n") or 0),
        "internaldata_n": int(value.get("internaldata_n") or 0),
        "getperimeter_xhr": bool(value.get("getperimeter_xhr")),
        "perimeter_via": str(value.get("perimeter_via") or ""),
        "feature_via": str(value.get("feature_via") or ""),
        "picker_via": str(value.get("picker_via") or ""),
        "picker_sku": str(value.get("picker_sku") or ""),
        "picker_apply": str(value.get("picker_apply") or ""),
    }


_STAMP_DXF_STOCK_JS = """(function(spec) {
  function dxfGrid() {
    try {
      var g = window.jQuery && jQuery("#gridDXFParts").data("kendoGrid");
      if (g && g.dataSource) return g;
    } catch (e) {}
    return null;
  }
  var emptyStamp = {
    ok: false, stamped: 0, cell_edit: 0, grid_id: "#gridDXFParts",
    grid_dxf_row_count: 0, outside_perimeter_n: 0, cutting_length_n: 0,
    internaldata_n: 0, getperimeter_xhr: false, perimeter_via: ""
  };
  var grid = dxfGrid();
  if (!grid) return Promise.resolve(emptyStamp);
  var rows = (spec && spec.rows) || [];
  var data = grid.dataSource.data() || [];
  var stamped = 0;
  var viaCell = 0;
  var lastVia = "";
  function setField(r, k, v) {
    if (v == null || v === "") return;
    if (typeof r.set === "function") r.set(k, v);
    else r[k] = v;
  }
  function editSet(r, field, value) {
    if (value == null || value === "") return;
    try {
      var tr = grid.tbody.find("tr").filter(function() {
        return grid.dataItem(this) === r;
      }).first();
      if (tr.length && typeof grid.editCell === "function") {
        var cell = tr.find("td[data-field='" + field + "']");
        if (!cell.length) {
          var cols = grid.columns || [];
          for (var c = 0; c < cols.length; c++) {
            if ((cols[c].field || "") === field) {
              cell = tr.find("td").eq(c);
              break;
            }
          }
        }
        if (cell.length) {
          grid.editCell(cell);
          var editor = cell.find("input, select, textarea").first();
          if (editor.length) {
            editor.val(value).trigger("change").trigger("blur");
            if (typeof grid.closeCell === "function") grid.closeCell();
            viaCell += 1;
            return;
          }
          if (typeof grid.closeCell === "function") grid.closeCell();
        }
      }
    } catch (e) {}
    setField(r, field, value);
  }
  function hookGetPerimeter() {
    if (window.__kannonDxfPerimHooked) return;
    if (!window.jQuery || !jQuery.ajax) return;
    window.__kannonDxfPerimHooked = true;
    var orig = jQuery.ajax;
    jQuery.ajax = function(opts) {
      var url = String((opts && (opts.url || opts)) || "");
      if (url.indexOf("/Quote/GetPerimeterAndWeight") >= 0) {
        window.__kannonDxfPerim = window.__kannonDxfPerim || {};
        window.__kannonDxfPerim.xhr = true;
        window.__kannonDxfPerim.any = true;
      }
      return orig.apply(this, arguments);
    };
  }
  function waitGetPerimeter(timeoutMs) {
    return new Promise(function(resolve) {
      var t0 = Date.now();
      (function poll() {
        if (window.__kannonDxfPerim && window.__kannonDxfPerim.xhr) {
          resolve(true); return;
        }
        if (Date.now() - t0 > timeoutMs) { resolve(false); return; }
        setTimeout(poll, 40);
      })();
    });
  }
  function fireUpdatePerimeterWeight() {
    try {
      if (typeof window.UpdatePerimeterWeight === "function") {
        window.UpdatePerimeterWeight(true, true);
        return "UpdatePerimeterWeight";
      }
    } catch (e) {}
    try {
      if (typeof window.GridDXFPart_OnChangeUpdate === "function") {
        window.GridDXFPart_OnChangeUpdate();
        return "GridDXFPart_OnChangeUpdate";
      }
    } catch (e2) {}
    try {
      if (window.jQuery) {
        var $sx = jQuery("[data-field='Stock_X'] input, #Stock_X");
        if ($sx.length) { $sx.trigger("change"); return "Stock_X.change"; }
      }
    } catch (e3) {}
    return "";
  }
  function copyPerimeterOntoRow(r) {
    var op = "";
    var cl = "";
    try {
      if (window.jQuery) {
        op = String(jQuery("#OutsidePerimeter").val() || "");
        cl = String(
          jQuery(".pdfcuttinglength").val()
          || jQuery("#CuttingLengthDisp").val()
          || ""
        );
      }
    } catch (e) {}
    if (op) {
      setField(r, "OutsidePerimeter", op);
      setField(r, "OutsidePerimeter_UseLocal", true);
    }
    if (cl) {
      setField(r, "CuttingLengthDisp", cl);
      setField(r, "CuttingLength", cl);
    }
  }
  function stampPerimeter(r) {
    try {
      var tr = grid.tbody.find("tr").filter(function() {
        return grid.dataItem(this) === r;
      }).first();
      if (tr.length && typeof grid.select === "function") grid.select(tr);
    } catch (e) {}
    if (window.__kannonDxfPerim) window.__kannonDxfPerim.xhr = false;
    lastVia = fireUpdatePerimeterWeight() || lastVia;
    return waitGetPerimeter(8000).then(function() {
      copyPerimeterOntoRow(r);
    });
  }
  hookGetPerimeter();
  window.__kannonDxfPerim = window.__kannonDxfPerim || {
    xhr: false, any: false
  };
  var chain = Promise.resolve();
  for (var i = 0; i < rows.length; i++) {
    (function(s, idx) {
      chain = chain.then(function() {
        var name = String(s.FileName || s.Name || "");
        for (var j = 0; j < data.length; j++) {
          var r = data[j];
          var fn = String((r.FileName || r.Name || r.PartName || ""));
          if (name && fn && fn.toLowerCase() !== name.toLowerCase()
              && fn.toLowerCase().indexOf(name.toLowerCase()) < 0
              && name.toLowerCase().indexOf(fn.toLowerCase()) < 0) {
            continue;
          }
          if (!name && idx !== j) continue;
          editSet(r, "Stock_X", s.Stock_X);
          editSet(r, "Stock_Y", s.Stock_Y);
          editSet(r, "Length", s.Length || s.Stock_X);
          editSet(r, "Width", s.Width || s.Stock_Y);
          stamped += 1;
          return stampPerimeter(r);
        }
      });
    })(rows[i] || {}, i);
  }
  return chain.then(function() {
    var opN = 0, clN = 0, idN = 0;
    for (var k = 0; k < data.length; k++) {
      var row = data[k] || {};
      if (Number(row.OutsidePerimeter) > 0) opN += 1;
      if (Number(row.CuttingLengthDisp || row.CuttingLength) > 0) clN += 1;
      var idata = row.InternalData;
      if (idata != null && String(idata).replace(/\\s+/g, "") !== "") idN += 1;
    }
    return {
      ok: stamped > 0,
      stamped: stamped,
      cell_edit: viaCell,
      grid_id: "#gridDXFParts",
      grid_dxf_row_count: data.length,
      outside_perimeter_n: opN,
      cutting_length_n: clN,
      internaldata_n: idN,
      getperimeter_xhr: !!(window.__kannonDxfPerim && window.__kannonDxfPerim.any),
      perimeter_via: lastVia
    };
  });
})"""


def stamp_dxf_kendo_stock(
    rows: list[dict[str, Any]],
    *,
    quote_id: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """Type Stock_X/Y on #gridDXFParts, then UpdatePerimeterWeight before Finish.

    DXF analog of Image Files L×W. Uses explode Stock values — do not invent.
    Do not fire UpdateDataNext.
    """
    spec_rows: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        sx = row.get("Stock_X")
        sy = row.get("Stock_Y")
        if sx in (None, "") and sy in (None, ""):
            continue
        spec_rows.append(
            {
                "FileName": str(row.get("FileName") or row.get("Name") or ""),
                "Name": str(row.get("Name") or row.get("FileName") or ""),
                "Stock_X": sx,
                "Stock_Y": sy,
                "Length": row.get("Length") or sx,
                "Width": row.get("Width") or sy,
            }
        )
    empty = {
        "ok": False,
        "stamped": 0,
        "cell_edit": 0,
        "grid_id": "#gridDXFParts",
        "grid_dxf_row_count": 0,
        "edit_gate": "",
        "outside_perimeter_n": 0,
        "cutting_length_n": 0,
        "internaldata_n": 0,
        "getperimeter_xhr": False,
        "perimeter_via": "",
    }
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    empty["edit_gate"] = str(gate.get("reason") or "")
    if not gate.get("ok"):
        return empty
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    expression = (
        _STAMP_DXF_STOCK_JS
        + "("
        + json.dumps({"rows": spec_rows}, separators=(",", ":"))
        + ")"
    )
    value = _cdp_evaluate_promise(
        expression, base=base, tab=tab, fallback=False
    )
    if not isinstance(value, dict):
        return empty
    return {
        "ok": bool(value.get("ok")),
        "stamped": int(value.get("stamped") or 0),
        "cell_edit": int(value.get("cell_edit") or 0),
        "grid_id": str(value.get("grid_id") or "#gridDXFParts"),
        "grid_dxf_row_count": int(value.get("grid_dxf_row_count") or 0),
        "edit_gate": "",
        "outside_perimeter_n": int(value.get("outside_perimeter_n") or 0),
        "cutting_length_n": int(value.get("cutting_length_n") or 0),
        "internaldata_n": int(value.get("internaldata_n") or 0),
        "getperimeter_xhr": bool(value.get("getperimeter_xhr")),
        "perimeter_via": str(value.get("perimeter_via") or ""),
    }


_OPEN_IMAGE_FILES_JS = """(function() {
  function pdfGrid() {
    var ids = ["#gridPDF", "#gridPdf", "#grid_PDF", "#gridPDFFiles"];
    for (var i = 0; i < ids.length; i++) {
      try {
        var g = window.jQuery && jQuery(ids[i]).data("kendoGrid");
        if (g && g.dataSource) return true;
      } catch (e) {}
    }
    return false;
  }
  var via = "";
  try {
    if (typeof window.AddNewItemHTML === "function") {
      window.AddNewItemHTML("pdf", "top");
      via = "AddNewItemHTML";
    }
  } catch (e) {}
  if (!via) {
    try {
      if (window.jQuery && jQuery("#but_pdf").length) {
        jQuery("#but_pdf").click();
        via = "#but_pdf";
      }
    } catch (e2) {}
  }
  if (!via) {
    try {
      var nodes = document.querySelectorAll("button, a, input[type=button], span");
      for (var i = 0; i < nodes.length; i++) {
        var t = String(nodes[i].textContent || nodes[i].value || "").toLowerCase();
        if (t.indexOf("image files") >= 0) {
          nodes[i].click();
          via = "image-files";
          break;
        }
      }
    } catch (e3) {}
  }
  return Promise.resolve({opened_via: via, grid_present: pdfGrid()});
})"""


_FIND_PDF_ADD_FILES_INPUT_JS = """(function() {
  function pdfGrid() {
    var ids = ["#gridPDF", "#gridPdf", "#grid_PDF", "#gridPDFFiles"];
    for (var i = 0; i < ids.length; i++) {
      try {
        var g = window.jQuery && jQuery(ids[i]).data("kendoGrid");
        if (g && g.dataSource) return ids[i];
      } catch (e) {}
    }
    return "";
  }
  function filesKendo() {
    try {
      return !!(window.jQuery && jQuery("#files").data("kendoUpload"));
    } catch (e) { return false; }
  }
  var dropZone = !!document.querySelector(".dropZoneElement");
  var files = document.querySelector("#files");
  if (files && String(files.tagName || "").toLowerCase() === "input") {
    return Promise.resolve({
      selector: "#files",
      grid_id: pdfGrid(),
      files_kendo: filesKendo(),
      drop_zone: dropZone
    });
  }
  if (files) {
    var inner = files.querySelector("input[type=file]");
    if (inner) {
      if (!inner.id) inner.setAttribute("data-kannon-add-files", "1");
      return Promise.resolve({
        selector: inner.id ? ("#" + inner.id) : "input[type=file][data-kannon-add-files='1']",
        grid_id: pdfGrid(),
        files_kendo: filesKendo(),
        drop_zone: dropZone
      });
    }
  }
  var drop = document.querySelector(".dropZoneElement");
  if (drop) {
    var wrap = drop.closest(".k-upload, .k-widget") || drop.parentElement;
    var dropInput = (wrap && wrap.querySelector("input[type=file]"))
      || drop.querySelector("input[type=file]");
    if (dropInput) {
      if (!dropInput.id) dropInput.setAttribute("data-kannon-add-files", "1");
      return Promise.resolve({
        selector: dropInput.id ? ("#" + dropInput.id) : "input[type=file][data-kannon-add-files='1']",
        grid_id: pdfGrid(),
        files_kendo: filesKendo(),
        drop_zone: true
      });
    }
  }
  var inputs = document.querySelectorAll("input[type=file]");
  var addFiles = null;
  for (var i = 0; i < inputs.length; i++) {
    var el = inputs[i];
    var elWrap = el.closest(".k-upload, .k-widget, label, div, span, td") || el.parentElement;
    var text = elWrap ? String(elWrap.textContent || "").toLowerCase() : "";
    var blob = ((el.id || "") + " " + (el.name || "") + " " + (el.className || "")).toLowerCase();
    if (text.indexOf("select files") >= 0 && text.indexOf("add files") < 0) {
      continue;
    }
    if (text.indexOf("add files") >= 0 || text.indexOf("+add") >= 0
        || blob.indexOf("addfile") >= 0 || blob.indexOf("add-files") >= 0) {
      addFiles = el;
      break;
    }
  }
  if (!addFiles) {
    return Promise.resolve({
      selector: "",
      grid_id: pdfGrid(),
      files_kendo: filesKendo(),
      drop_zone: dropZone
    });
  }
  if (addFiles.id) {
    return Promise.resolve({
      selector: "#" + addFiles.id,
      grid_id: pdfGrid(),
      files_kendo: filesKendo(),
      drop_zone: dropZone
    });
  }
  addFiles.setAttribute("data-kannon-add-files", "1");
  return Promise.resolve({
    selector: "input[type=file][data-kannon-add-files='1']",
    grid_id: pdfGrid(),
    files_kendo: filesKendo(),
    drop_zone: dropZone
  });
})"""


_READ_GRID_PDF_COUNT_JS = """(function() {
  function statusOf(r) {
    var s = r && (r.Status != null ? r.Status : r.status);
    return Number(s || 0);
  }
  function toJSON(r) {
    try { if (r && r.toJSON) return r.toJSON(); } catch (e) {}
    return r;
  }
  function walkTbody(grid, id) {
    var out = [];
    if (!grid || !window.jQuery) return out;
    try {
      jQuery(id + " tbody tr").each(function() {
        var item = grid.dataItem(this);
        if (item) out.push(toJSON(item));
      });
    } catch (e) {}
    return out;
  }
  var gridId = "";
  var rows = [];
  var getpdf = typeof window.GetPDFData === "function";
  if (getpdf) {
    try {
      var d = window.GetPDFData();
      if (Array.isArray(d)) rows = d;
    } catch (e) {}
  }
  var ids = ["#gridPDF", "#gridPdf", "#grid_PDF", "#gridPDFFiles"];
  var transportRead = "";
  var filesKendo = false;
  try {
    filesKendo = !!(window.jQuery && jQuery("#files").data("kendoUpload"));
  } catch (e3) {}
  for (var i = 0; i < ids.length; i++) {
    try {
      var g = window.jQuery && jQuery(ids[i]).data("kendoGrid");
      if (g && g.dataSource) {
        gridId = ids[i];
        try {
          transportRead = String((g.dataSource.transport && g.dataSource.transport.options
            && g.dataSource.transport.options.read && g.dataSource.transport.options.read.url) || "");
        } catch (e4) { transportRead = ""; }
        if (!rows.length) rows = walkTbody(g, ids[i]);
        break;
      }
    } catch (e2) {}
  }
  var statusN = 0;
  var pidN = 0;
  for (var j = 0; j < rows.length; j++) {
    if (statusOf(rows[j]) > 0) statusN += 1;
    var pid = rows[j] && (rows[j].ProductID != null ? rows[j].ProductID : rows[j].productID);
    if (pid != null && String(pid).trim() && String(pid).toLowerCase() !== "null") {
      pidN += 1;
    }
  }
  return Promise.resolve({
    grid_id: gridId,
    grid_pdf_row_count: rows.length,
    status_gt0_n: statusN,
    getpdfdata_n: getpdf ? statusN : 0,
    getpdfdata_is_xhr: false,
    productid_n: pidN,
    files_kendo: filesKendo,
    transport_read_url: transportRead
  });
})"""


_DISPATCH_FILES_CHANGE_JS = """(function() {
  var el = document.querySelector("#files")
    || document.querySelector("input[type=file][data-kannon-add-files='1']");
  if (!el) return Promise.resolve({changed: false, files_kendo: false});
  try {
    el.dispatchEvent(new Event("change", {bubbles: true}));
  } catch (e) {}
  var ku = false;
  try { ku = !!(window.jQuery && jQuery("#files").data("kendoUpload")); } catch (e2) {}
  return Promise.resolve({changed: true, files_kendo: ku});
})"""


def _cdp_set_file_input_files(
    ws: str,
    selector: str,
    paths: list[str],
) -> bool:
    """DOM.setFileInputFiles on in-page #files kendoUpload. Never logs paths."""
    if not ws or not selector or not paths:
        return False
    cdp_call(ws, "DOM.enable", {}, call_id=80)
    doc = cdp_call(ws, "DOM.getDocument", {"depth": 1}, call_id=81)
    if not isinstance(doc, dict):
        return False
    root = (doc.get("root") or {}).get("nodeId") if isinstance(doc.get("root"), dict) else None
    if not root:
        return False
    found = cdp_call(
        ws,
        "DOM.querySelector",
        {"nodeId": root, "selector": selector},
        call_id=82,
    )
    node_id = found.get("nodeId") if isinstance(found, dict) else None
    if not node_id:
        return False
    result = cdp_call(
        ws,
        "DOM.setFileInputFiles",
        {"files": list(paths), "nodeId": node_id},
        call_id=83,
    )
    return result is not None


def upload_pdf_via_page_add_files(
    files: list[Any],
    *,
    quote_id: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """In-page #files kendoUpload so onSuccess_PDFUpload fills #gridPDF.

    Leftover dialog: cookie POST /Attachment/UploadItem_PDFFiles is only
    the widget saveUrl. Off-page cookie HTTP does not run
    onSuccess_PDFUpload. Drag onto +Add Files (dropZoneElement).
    """
    paths = [str(Path(p).resolve()) for p in (files or []) if p]
    empty = {
        "bound": False,
        "upload_via": "skipped",
        "files_kendo": False,
        "grid_pdf_row_count": 0,
        "status_gt0_n": 0,
        "getpdfdata_n": 0,
        "getpdfdata_is_xhr": False,
        "productid_n": 0,
        "grid_id": "",
        "opened_via": "",
        "finish_why": "wrong_document",
        "edit_gate": "",
    }
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    empty["edit_gate"] = str(gate.get("reason") or "")
    if not gate.get("ok"):
        return empty
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    opened = _cdp_evaluate_promise(
        _OPEN_IMAGE_FILES_JS + "()", base=base, tab=tab, fallback=False
    )
    opened_via = ""
    if isinstance(opened, dict):
        opened_via = str(opened.get("opened_via") or "")
    time.sleep(0.35)
    found = _cdp_evaluate_promise(
        _FIND_PDF_ADD_FILES_INPUT_JS + "()", base=base, tab=tab, fallback=False
    )
    selector = str((found or {}).get("selector") or "") if isinstance(found, dict) else ""
    files_kendo = bool((found or {}).get("files_kendo")) if isinstance(found, dict) else False
    if not selector or not paths:
        return {
            **empty,
            "upload_via": "skipped",
            "files_kendo": files_kendo,
            "opened_via": opened_via,
            "finish_why": "no_add_files_input",
            "grid_id": str((found or {}).get("grid_id") or "") if isinstance(found, dict) else "",
        }
    ws = str((tab or {}).get("webSocketDebuggerUrl") or "")
    if not _cdp_set_file_input_files(ws, selector, paths):
        return {
            **empty,
            "upload_via": "page_add_files",
            "files_kendo": files_kendo,
            "opened_via": opened_via,
            "finish_why": "set_files_failed",
        }
    changed = _cdp_evaluate_promise(
        _DISPATCH_FILES_CHANGE_JS + "()", base=base, tab=tab, fallback=False
    )
    if isinstance(changed, dict) and changed.get("files_kendo"):
        files_kendo = True
    last = {
        "grid_id": "",
        "grid_pdf_row_count": 0,
        "status_gt0_n": 0,
        "getpdfdata_n": 0,
        "files_kendo": files_kendo,
    }
    for _ in range(24):
        count = _cdp_evaluate_promise(
            _READ_GRID_PDF_COUNT_JS + "()", base=base, tab=tab, fallback=False
        )
        if isinstance(count, dict):
            last = count
            if count.get("files_kendo"):
                files_kendo = True
            try:
                n = int(
                    count.get("getpdfdata_n")
                    or count.get("status_gt0_n")
                    or count.get("grid_pdf_row_count")
                    or 0
                )
            except (TypeError, ValueError):
                n = 0
            if n > 0 and files_kendo:
                return {
                    "bound": True,
                    "upload_via": "page_add_files",
                    "files_kendo": True,
                    "grid_pdf_row_count": int(count.get("grid_pdf_row_count") or n),
                    "status_gt0_n": int(count.get("status_gt0_n") or n),
                    "getpdfdata_n": int(count.get("getpdfdata_n") or n),
                    "getpdfdata_is_xhr": False,
                    "productid_n": int(count.get("productid_n") or 0),
                    "grid_id": str(count.get("grid_id") or ""),
                    "opened_via": opened_via,
                    "finish_why": "",
                    "edit_gate": "",
                }
        time.sleep(0.25)
    return {
        "bound": False,
        "upload_via": "page_add_files",
        "files_kendo": files_kendo,
        "grid_pdf_row_count": int(last.get("grid_pdf_row_count") or 0),
        "status_gt0_n": int(last.get("status_gt0_n") or 0),
        "getpdfdata_n": int(last.get("getpdfdata_n") or 0),
        "getpdfdata_is_xhr": False,
        "productid_n": int(last.get("productid_n") or 0),
        "grid_id": str(last.get("grid_id") or ""),
        "opened_via": opened_via,
        "finish_why": "empty_dataSource",
        "edit_gate": "",
    }


_OPEN_CAD_FILES_JS = """(function() {
  function dxfGrid() {
    try {
      var g = window.jQuery && jQuery("#gridDXF").data("kendoGrid");
      return !!(g && g.dataSource);
    } catch (e) { return false; }
  }
  var via = "";
  try {
    if (typeof window.AddNewItemHTML === "function") {
      window.AddNewItemHTML("dxf", "top");
      via = "AddNewItemHTML";
    }
  } catch (e) {}
  if (!via) {
    try {
      if (window.jQuery && jQuery("#but_dxf").length) {
        jQuery("#but_dxf").click();
        via = "#but_dxf";
      }
    } catch (e2) {}
  }
  if (!via) {
    try {
      var nodes = document.querySelectorAll("button, a, input[type=button], span");
      for (var i = 0; i < nodes.length; i++) {
        var t = String(nodes[i].textContent || nodes[i].value || "").toLowerCase();
        if (t.indexOf("cad files") >= 0) {
          nodes[i].click();
          via = "cad-files";
          break;
        }
      }
    } catch (e3) {}
  }
  return Promise.resolve({opened_via: via, grid_present: dxfGrid()});
})"""


_FIND_DXF_ADD_FILES_INPUT_JS = """(function() {
  function filesKendo() {
    try {
      var zone = document.querySelector("#dxfupload_Zone");
      var el = zone && zone.querySelector("#files");
      if (!el || !window.jQuery) return false;
      return !!jQuery(el).data("kendoUpload");
    } catch (e) { return false; }
  }
  function saveUrl() {
    try {
      var zone = document.querySelector("#dxfupload_Zone");
      var el = zone && zone.querySelector("#files");
      var ku = el && window.jQuery && jQuery(el).data("kendoUpload");
      var opts = ku && ku.options && ku.options.async;
      return String((opts && opts.saveUrl) || "");
    } catch (e) { return ""; }
  }
  var zone = document.querySelector("#dxfupload_Zone");
  var dropZone = !!(zone && zone.querySelector(".dropZoneElement"));
  var files = zone ? zone.querySelector("#files") : null;
  if (files && String(files.tagName || "").toLowerCase() === "input") {
    return Promise.resolve({
      selector: "#dxfupload_Zone #files",
      grid_id: "#gridDXF",
      files_kendo: filesKendo(),
      drop_zone: dropZone,
      save_url: saveUrl(),
      zone: "#dxfupload_Zone"
    });
  }
  if (files) {
    var inner = files.querySelector("input[type=file]");
    if (inner) {
      if (!inner.id) inner.setAttribute("data-kannon-dxf-add-files", "1");
      return Promise.resolve({
        selector: inner.id ? ("#dxfupload_Zone #" + inner.id)
          : "#dxfupload_Zone input[type=file][data-kannon-dxf-add-files='1']",
        grid_id: "#gridDXF",
        files_kendo: filesKendo(),
        drop_zone: dropZone,
        save_url: saveUrl(),
        zone: "#dxfupload_Zone"
      });
    }
  }
  var drop = zone && zone.querySelector(".dropZoneElement");
  if (drop) {
    var wrap = drop.closest(".k-upload, .k-widget") || drop.parentElement;
    var dropInput = (wrap && wrap.querySelector("input[type=file]"))
      || drop.querySelector("input[type=file]");
    if (dropInput) {
      if (!dropInput.id) dropInput.setAttribute("data-kannon-dxf-add-files", "1");
      return Promise.resolve({
        selector: dropInput.id ? ("#dxfupload_Zone #" + dropInput.id)
          : "#dxfupload_Zone input[type=file][data-kannon-dxf-add-files='1']",
        grid_id: "#gridDXF",
        files_kendo: filesKendo(),
        drop_zone: true,
        save_url: saveUrl(),
        zone: "#dxfupload_Zone"
      });
    }
  }
  return Promise.resolve({
    selector: "",
    grid_id: "",
    files_kendo: filesKendo(),
    drop_zone: dropZone,
    save_url: saveUrl(),
    zone: zone ? "#dxfupload_Zone" : ""
  });
})"""


_READ_GRID_DXF_COUNT_JS = """(function() {
  function toJSON(r) {
    try { if (r && r.toJSON) return r.toJSON(); } catch (e) {}
    return r;
  }
  var gridId = "";
  var rows = [];
  var filesKendo = false;
  var saveUrl = "";
  try {
    var zone = document.querySelector("#dxfupload_Zone");
    var el = zone && zone.querySelector("#files");
    filesKendo = !!(el && window.jQuery && jQuery(el).data("kendoUpload"));
    var ku = el && window.jQuery && jQuery(el).data("kendoUpload");
    var opts = ku && ku.options && ku.options.async;
    saveUrl = String((opts && opts.saveUrl) || "");
  } catch (e) {}
  try {
    var g = window.jQuery && jQuery("#gridDXF").data("kendoGrid");
    if (g && g.dataSource) {
      gridId = "#gridDXF";
      var raw = g.dataSource.data();
      var arr = (raw && raw.toJSON) ? raw.toJSON() : raw;
      if (Array.isArray(arr)) {
        for (var i = 0; i < arr.length; i++) rows.push(toJSON(arr[i]));
      }
    }
  } catch (e2) {}
  return Promise.resolve({
    grid_id: gridId,
    gridDXF_n: rows.length,
    files_kendo: filesKendo,
    save_url: saveUrl,
    List: rows
  });
})"""


_DISPATCH_DXF_FILES_CHANGE_JS = """(function() {
  var zone = document.querySelector("#dxfupload_Zone");
  var el = (zone && (zone.querySelector("#files")
    || zone.querySelector("input[type=file][data-kannon-dxf-add-files='1']")))
    || document.querySelector("#dxfupload_Zone #files");
  if (!el) return Promise.resolve({changed: false, files_kendo: false});
  try {
    el.dispatchEvent(new Event("change", {bubbles: true}));
  } catch (e) {}
  var ku = false;
  try {
    ku = !!(window.jQuery && jQuery(el).data("kendoUpload"));
  } catch (e2) {}
  return Promise.resolve({changed: true, files_kendo: ku});
})"""


_INVOKE_CREATE_ALL_PARTS_JS = """(function() {
  var gridN = 0;
  try {
    var g = window.jQuery && jQuery("#gridDXF").data("kendoGrid");
    if (g && g.dataSource) gridN = g.dataSource.data().length;
  } catch (e) {}
  if (gridN <= 0) {
    return Promise.resolve({
      invoked: false,
      via: "",
      gridDXF_n: 0,
      why: "empty_gridDXF"
    });
  }
  if (typeof window.createAllParts === "function") {
    window.createAllParts();
    return Promise.resolve({
      invoked: true,
      via: "createAllParts",
      gridDXF_n: gridN,
      why: ""
    });
  }
  return Promise.resolve({
    invoked: false,
    via: "",
    gridDXF_n: gridN,
    why: "no_createAllParts"
  });
})"""


_READ_GRID_DXF_PARTS_AFTER_NEXT_JS = """(function() {
  function toJSON(r) {
    try { if (r && r.toJSON) return r.toJSON(); } catch (e) {}
    return r;
  }
  function emptyVal(v) {
    if (v == null) return true;
    if (typeof v === "string") return !String(v).trim();
    if (Array.isArray(v)) return v.length === 0;
    return false;
  }
  var rows = [];
  var present = false;
  try {
    var g = window.jQuery && jQuery("#gridDXFParts").data("kendoGrid");
    if (g && g.dataSource) {
      present = true;
      var raw = g.dataSource.data();
      var arr = (raw && raw.toJSON) ? raw.toJSON() : raw;
      if (Array.isArray(arr)) {
        for (var i = 0; i < arr.length; i++) rows.push(toJSON(arr[i]));
      }
    }
  } catch (e) {}
  var emptyN = 0;
  var keyN = 0;
  for (var j = 0; j < rows.length; j++) {
    if (rows[j] && Object.prototype.hasOwnProperty.call(rows[j], "InternalData")) {
      keyN += 1;
      if (emptyVal(rows[j].InternalData)) emptyN += 1;
    }
  }
  return Promise.resolve({
    grid_present: present,
    has_gridDXFParts: present,
    grid_dxf_row_count: rows.length,
    list_len: rows.length,
    List: rows,
    internaldata_key_n: keyN,
    internaldata_empty_n: emptyN,
    internaldata_nonempty_n: keyN - emptyN
  });
})"""


def upload_dxf_via_page_add_files(
    files: list[Any],
    *,
    quote_id: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """In-page #files in #dxfupload_Zone so onSuccess_Upload fills #gridDXF.

    Leftover dialog: cookie POST /CadImport/UploadItem_DXFFiles is only
    the widget saveUrl. Off-page cookie HTTP does not run
    onSuccess_Upload. Drive CAD Files +Add Files (dropZoneElement).
    """
    paths = [str(Path(p).resolve()) for p in (files or []) if p]
    empty = {
        "bound": False,
        "upload_via": "skipped",
        "files_kendo": False,
        "gridDXF_n": 0,
        "grid_dxf_row_count": 0,
        "grid_id": "",
        "opened_via": "",
        "finish_why": "wrong_document",
        "edit_gate": "",
        "List": [],
        "save_url": "",
        "zone": "",
    }
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    empty["edit_gate"] = str(gate.get("reason") or "")
    if not gate.get("ok"):
        return empty
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    opened = _cdp_evaluate_promise(
        _OPEN_CAD_FILES_JS + "()", base=base, tab=tab, fallback=False
    )
    opened_via = ""
    if isinstance(opened, dict):
        opened_via = str(opened.get("opened_via") or "")
    time.sleep(0.35)
    found = _cdp_evaluate_promise(
        _FIND_DXF_ADD_FILES_INPUT_JS + "()", base=base, tab=tab, fallback=False
    )
    selector = str((found or {}).get("selector") or "") if isinstance(found, dict) else ""
    files_kendo = bool((found or {}).get("files_kendo")) if isinstance(found, dict) else False
    save_url = str((found or {}).get("save_url") or "") if isinstance(found, dict) else ""
    if not selector or not paths:
        return {
            **empty,
            "upload_via": "skipped",
            "files_kendo": files_kendo,
            "opened_via": opened_via,
            "finish_why": "no_add_files_input",
            "grid_id": str((found or {}).get("grid_id") or "") if isinstance(found, dict) else "",
            "save_url": save_url,
            "zone": str((found or {}).get("zone") or ""),
        }
    ws = str((tab or {}).get("webSocketDebuggerUrl") or "")
    if not _cdp_set_file_input_files(ws, selector, paths):
        return {
            **empty,
            "upload_via": "page_add_files",
            "files_kendo": files_kendo,
            "opened_via": opened_via,
            "finish_why": "set_files_failed",
            "save_url": save_url,
            "zone": "#dxfupload_Zone",
        }
    changed = _cdp_evaluate_promise(
        _DISPATCH_DXF_FILES_CHANGE_JS + "()", base=base, tab=tab, fallback=False
    )
    if isinstance(changed, dict) and changed.get("files_kendo"):
        files_kendo = True
    last: dict[str, Any] = {
        "grid_id": "",
        "gridDXF_n": 0,
        "files_kendo": files_kendo,
        "List": [],
        "save_url": save_url,
    }
    for _ in range(24):
        count = _cdp_evaluate_promise(
            _READ_GRID_DXF_COUNT_JS + "()", base=base, tab=tab, fallback=False
        )
        if isinstance(count, dict):
            last = count
            if count.get("files_kendo"):
                files_kendo = True
            try:
                n = int(count.get("gridDXF_n") or 0)
            except (TypeError, ValueError):
                n = 0
            rows = [r for r in (count.get("List") or []) if isinstance(r, dict)]
            if n > 0 and files_kendo:
                return {
                    "bound": True,
                    "upload_via": "page_add_files",
                    "files_kendo": True,
                    "gridDXF_n": n,
                    "grid_dxf_row_count": n,
                    "grid_id": str(count.get("grid_id") or "#gridDXF"),
                    "opened_via": opened_via,
                    "finish_why": "",
                    "edit_gate": "",
                    "List": rows,
                    "save_url": str(count.get("save_url") or save_url),
                    "zone": "#dxfupload_Zone",
                }
        time.sleep(0.25)
    return {
        "bound": False,
        "upload_via": "page_add_files",
        "files_kendo": files_kendo,
        "gridDXF_n": int(last.get("gridDXF_n") or 0),
        "grid_dxf_row_count": int(last.get("gridDXF_n") or 0),
        "grid_id": str(last.get("grid_id") or ""),
        "opened_via": opened_via,
        "finish_why": "empty_gridDXF",
        "edit_gate": "",
        "List": [r for r in (last.get("List") or []) if isinstance(r, dict)],
        "save_url": str(last.get("save_url") or save_url),
        "zone": "#dxfupload_Zone",
    }


def create_all_parts_from_grid_dxf(
    *,
    quote_id: str | None = None,
    base: str | None = None,
) -> dict[str, Any]:
    """Page Next createAllParts on minted EDIT after #gridDXF bind.

    Do not eval createAllParts on the Quotes list (live 34632-2 empty
    #gridDXF IDList). Cookie HTTP /part/create is not the gold bind.
    InternalData appears on t.List only if the server already stamped it.
    Do not invent InternalData. Do not fire UpdateDataNext.
    """
    empty = {
        "invoked": False,
        "via": "",
        "List": [],
        "grid_present": False,
        "has_gridDXFParts": False,
        "grid_dxf_row_count": 0,
        "list_len": 0,
        "gridDXF_n": 0,
        "why": "wrong_document",
        "internaldata_key_n": 0,
        "internaldata_empty_n": 0,
        "internaldata_nonempty_n": 0,
    }
    gate = minted_edit_tab_ready(quote_id, base=base, navigate=True)
    if not gate.get("ok"):
        empty["why"] = str(gate.get("reason") or "wrong_document")
        return empty
    tab = gate.get("tab") if isinstance(gate.get("tab"), dict) else None
    invoked = _cdp_evaluate_promise(
        _INVOKE_CREATE_ALL_PARTS_JS + "()", base=base, tab=tab, fallback=False
    )
    if not isinstance(invoked, dict) or not invoked.get("invoked"):
        why = str((invoked or {}).get("why") or "no_createAllParts") if isinstance(invoked, dict) else "no_createAllParts"
        empty["why"] = why
        empty["gridDXF_n"] = int((invoked or {}).get("gridDXF_n") or 0) if isinstance(invoked, dict) else 0
        return empty
    last: dict[str, Any] = {}
    for _ in range(32):
        count = _cdp_evaluate_promise(
            _READ_GRID_DXF_PARTS_AFTER_NEXT_JS + "()", base=base, tab=tab, fallback=False
        )
        if isinstance(count, dict):
            last = count
            try:
                n = int(count.get("grid_dxf_row_count") or count.get("list_len") or 0)
            except (TypeError, ValueError):
                n = 0
            if n > 0 and count.get("grid_present"):
                rows = [r for r in (count.get("List") or []) if isinstance(r, dict)]
                return {
                    "invoked": True,
                    "via": "createAllParts",
                    "List": rows,
                    "grid_present": True,
                    "has_gridDXFParts": True,
                    "grid_dxf_row_count": n,
                    "list_len": int(count.get("list_len") or n),
                    "gridDXF_n": int(invoked.get("gridDXF_n") or 0),
                    "why": "",
                    "internaldata_key_n": int(count.get("internaldata_key_n") or 0),
                    "internaldata_empty_n": int(count.get("internaldata_empty_n") or 0),
                    "internaldata_nonempty_n": int(count.get("internaldata_nonempty_n") or 0),
                }
        time.sleep(0.25)
    rows = [r for r in (last.get("List") or []) if isinstance(r, dict)]
    return {
        "invoked": True,
        "via": "createAllParts",
        "List": rows,
        "grid_present": bool(last.get("grid_present")),
        "has_gridDXFParts": bool(last.get("has_gridDXFParts")),
        "grid_dxf_row_count": int(last.get("grid_dxf_row_count") or 0),
        "list_len": int(last.get("list_len") or 0),
        "gridDXF_n": int(invoked.get("gridDXF_n") or 0),
        "why": "empty_gridDXFParts",
        "internaldata_key_n": int(last.get("internaldata_key_n") or 0),
        "internaldata_empty_n": int(last.get("internaldata_empty_n") or 0),
        "internaldata_nonempty_n": int(last.get("internaldata_nonempty_n") or 0),
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
      row.set("FileType", cat);
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
      row.FileType = cat;
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
      var logKeys = [
        "CadType", "Stock_X", "Stock_Y", "Stock_Z", "Stock_Units",
        "Stock_Length", "Stock_Diameter", "FileType", "SourceDataID", "FileID", "ID",
        "InternalData", "InternalHTML", "ImageString", "HadOpenContours",
        "OutsidePerimeter"
      ];
      var first = {};
      try {
        first = (fresh[0] && fresh[0].toJSON) ? fresh[0].toJSON() : (fresh[0] || {});
      } catch (eK) { first = fresh[0] || {}; }
      var kendoKeys = [];
      for (var lk = 0; lk < logKeys.length; lk++) {
        if (first && first[logKeys[lk]] !== undefined) kendoKeys.push(logKeys[lk]);
      }
      return {
        grid_present: true,
        cad: counts.Cad,
        linear: counts.Linear,
        assembly: counts.Assembly,
        component: counts.Component,
        set_count: setCount,
        setpartmode_via: via || (fnName ? "page_fn" : (setCount ? "grid_set" : "")),
        grid_dxf_row_count: fresh.length,
        kendo_row_keys: kendoKeys
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
        "kendo_row_keys": [],
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
    raw_keys = value.get("kendo_row_keys") if present else None
    kendo_keys = (
        [str(k) for k in raw_keys if str(k)] if isinstance(raw_keys, list) else []
    )
    out = {
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
    if present:
        out["kendo_row_keys"] = kendo_keys
    return out


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
