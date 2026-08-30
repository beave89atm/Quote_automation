"""CadImport XHRs from /bundles/QuoteOrderEdit (not in-repo .js).

Live fetch 2026-08-29: GET /bundles/QuoteOrderEdit 200, 353603 bytes
(text/javascript) on api.secturafab.com. GetDXFData does not appear.

Kyle CAD Files Next is createAllParts → DoCreateDXFParts. That POST's
success ``t.List`` is pushed onto #gridDXFParts (child FileList rows).

ConvertTo / UpdateDataNext are different functions (units / editor next
file). Live 34887-1 posted those with a JSON List body and got FileList 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

_SCRIPT_SRC_RE = re.compile(
    r"""<script[^>]+src=["']([^"']+)["']""",
    re.I,
)
_CAD_URL_RE = re.compile(
    r"""['"](/CadImport/[A-Za-z0-9_]+|/part/create|/Part/Create)['"]"""
)
_QUOTE_DXF_URL_RE = re.compile(
    r"""['"](/Quote/(?:GetDXFData|GetDXF\w+|AddItem_DXFFiles))['"]"""
)
_FUNC_RE = re.compile(
    r"""(?:function\s+(\w+)|(?:var|let|const)\s+(\w+)\s*=\s*function|(\w+)\s*[:=]\s*function)"""
)
_TYPE_RE = re.compile(r"""(?:type|method)\s*:\s*['"](GET|POST|PUT)['"]""", re.I)
_CT_RE = re.compile(r"""contentType\s*:\s*['"]([^'"]+)['"]""", re.I)
_KEY_RE = re.compile(
    r"""['"]?(ID|QuoteID|quoteID|quoteRequestID|QuoteRequestID|SourceDataID|"""
    r"""FileID|List|ListOther|status|PartMode|units|Units|IDList|unitList|"""
    r"""OtherFileIDList|Location|Height|Width|ItemList|SourceID|ReturnItemID|"""
    r"""convertTo|ConvertTo|target|Target|format|Format)['"]?\s*:"""
)
_LIT_RE = re.compile(
    r"""['"]?(convertTo|ConvertTo|target|Target|format|Format|to|type|Type)"""
    r"""['"]?\s*:\s*['"]([^'"]+)['"]"""
)

_SKIP_PATHS = frozenset(
    {
        "/CadImport/UploadItem_DXFFiles",
        "/Quote/AddItem_DXFFiles",
        "/CadImport/SetUnits",
    }
)

# Live 34887-1: these 200'd with FileList 0 when posted as JSON List.
# QuoteOrderEdit sends different keys (IDList/Units, ItemList/SourceID).
PROVEN_EMPTY_PATHS = frozenset(
    {
        "/CadImport/ConvertTo",
        "/CadImport/UpdateDataNext",
    }
)

QUOTE_ORDER_EDIT_BUNDLE = "/bundles/QuoteOrderEdit"

# Quoted from /bundles/QuoteOrderEdit (2026-08-29):
#   function createAllParts(){ ... DoCreateDXFParts(r,u) ...
#     $('#ulDXFTab a[href="#dxfparts"]').tab("show") }
#   function DoCreateDXFParts(n,t){ ...
#     $.ajax({type:"POST",url:"/part/create",dataType:"json",
#       data:{Location:f,IDList:n,unitList:t,OtherFileIDList:r,Height:e,Width:o},
#       success:function(t){ ... #gridDXFParts ... t.List[e] ... }}) }
# No traditional / ajaxSetup in QuoteOrderEdit or tenant scripts — jQuery
# default traditional=false → IDList[] / unitList[] (live 34639-1 form).
# Token is not in data:{}; kendo.core antiForgeryTokens (2023.3) is:
#   e("input[name^='__RequestVerificationToken']").each(...)
#   + meta csrf-token/_csrf with csrf-param/_csrf_header as the data key
# It returns an object merged into $.ajax data — no RequestVerificationToken
# header. Those inputs live on the Quote layout (GET /Quote?ID=), not the
# GetItem_AddView partial (live 11791-2 af_extracted=false). CadImport none.
CREATE_DXF_PARTS_FUNCTION = "DoCreateDXFParts"
CREATE_DXF_PARTS_CALLER = "createAllParts"
CREATE_DXF_PARTS_PATH = "/part/create"
CREATE_DXF_PARTS_CONTENT_TYPE = "application/x-www-form-urlencoded"
CREATE_DXF_PARTS_BODY_KEYS = (
    "Location",
    "IDList",
    "unitList",
    "OtherFileIDList",
    "Height",
    "Width",
)
# Live QuoteOrderEdit DoCreateDXFParts data:{} is exactly these six keys
# (Location from #InventoryLocation, Height/Width from #img, IDList/unitList
# from #gridDXF, OtherFileIDList from #gridOther). No missing form key.
# Do not invent Height/Width/InternalData. AF is merged by
# kendo.antiForgeryTokens, not this bag.
CREATE_DXF_PARTS_SNIPPET = (
    'function DoCreateDXFParts(n,t){$.ajax({type:"POST",url:"/part/create",'
    'dataType:"json",data:{Location:f,IDList:n,unitList:t,'
    "OtherFileIDList:r,Height:e,Width:o}})}"
)

# ConvertTo(n) is units on selected #gridDXF rows — not explode:
#   data:{IDList:t, Units:n} → FastUpdateRowGridDXF (same SourceDataID)
CONVERT_TO_SNIPPET = (
    'function ConvertTo(n){$.ajax({type:"POST",url:"/CadImport/ConvertTo",'
    'dataType:"json",data:{IDList:t,Units:n}})}'
)

# UpdateDXF_LoadNew is the CAD editor next-file, not Kyle Next:
#   data:{ItemList:i, SourceID:t, ReturnItemID:n}
UPDATE_DATA_NEXT_SNIPPET = (
    'function UpdateDXF_LoadNew(n){$.ajax({type:"POST",'
    'url:"/CadImport/UpdateDataNext",dataType:"json",'
    "data:{ItemList:i,SourceID:t,ReturnItemID:n}})}"
)

# QuoteOrderEdit Finish — same controllerName='/Quote' as GetItem_AddView.
#   data:{ID, ItemID, customerMaterial, FileList}
# FileList = #gridDXFParts rows (ErrorStatus===0, Qty>0), not the raw STEP.
# Cited OnAddDXFClick has no FileType=Cad vs Component branch and no
# unfold / InternalData emptiness check. Live 10098-1 posted FileType=Cad
# (string) plus InternalData/ImageString *keys* and still empty.
# Unfold*/DXF* child keys were absent. Bundle hunt: DoCreateDXFParts
# success pushes t.List as-is; GridDXFPart_OnChangeUpdate only *reads*
# InternalData/ImageString; GET /part/PartImage is preview only; no
# later Cad fill XHR (0 Unfold*/GetDXF*). InternalData/ImageString must
# arrive on server t.List. Live SC0600 weldment explode n=143 still
# InternalData empty 143/143 (ImageString empty 2/143). Not leftover
# plate. Live FA Assembly 0d4b8a46: #img H/W copied (nonzero float) +
# AF + IDList[] still empty 28/28. #img is not the miss. Remaining
# delta is chrome fetch on the Quotes list vs page $.ajax (Referer
# /Quote/EDIT + XHR / kendo.antiForgeryTokens). Content-Type, Accept,
# traditional IDList[], and form keys already match. InternalData is
# required for Cad Finish. Do not invent InternalData, Height/Width,
# or a FileType enum (not CAD / 100).
# unfold, Status, Height/Width, or a FileType enum (not CAD / 100).
# Live 34137-1: cookie-HTTP POST 200 empty str / ItemList 0.
# Live 34137-2: fetch('/part/create') with Upload IDs → t.List=31, but
# success never ran so #gridDXFParts stayed empty; reconstructed Finish
# empty 200.
# Live 34632-2: page createAllParts on the Quotes list (empty #gridDXF)
# → t.List=0. Live 106386-1: fetch t.List=26 but cookie GetItem_AddView
# never put #gridDXFParts in Chrome. Explode = fetch with Upload IDs;
# bind = click CAD Files in the Quotes tab, then DoCreateDXFParts success
# only if grid_present. Do not invent a route.
ADD_ITEM_DXF_FILES_PATH = "/Quote/AddItem_DXFFiles"
ADD_ITEM_DXF_FILES_BODY_KEYS = ("ID", "ItemID", "customerMaterial", "FileList")
ADD_ITEM_DXF_FILES_SNIPPET = (
    '$.ajax({type:"POST",url:"/Quote/AddItem_DXFFiles",'
    "data:{ID:id,ItemID:itemId,customerMaterial:cm,FileList:rows}})"
)

# CadImport classify (Kyle Cad / Linear / Component dropdown → PartMode).
# SetPartMode: ID + integer PartMode (strings 500). 0 Cad, 1 Linear, 2 Component.
# Kyle STP Loom: Component→CAD sets Machine=Laser; Structural→Linear + Product Type.
# Live 105918-1: page Finish without grid SetPartMode → 66 Component/Assembly, 0 Cad.
# Apply PartMode on #gridDXFParts (EDIT) before Finish. UpdateData JSON List.
SET_PART_MODE_PATH = "/CadImport/SetPartMode"
SET_PART_MODE_SNIPPET = (
    '$.ajax({type:"POST",url:"/CadImport/SetPartMode",'
    "data:{ID:id,PartMode:mode}})"
)
UPDATE_DATA_PATH = "/CadImport/UpdateData"
UPDATE_DATA_SNIPPET = (
    '$.ajax({type:"POST",url:"/CadImport/UpdateData",'
    "dataType:\"json\",data:{List:rows}})"
)


@dataclass
class CadImportXhr:
    function: str
    method: str
    path: str
    content_type: str
    query_keys: list[str] = field(default_factory=list)
    body_keys: list[str] = field(default_factory=list)
    literals: dict[str, str] = field(default_factory=dict)
    snippet: str = ""

    def cite(self) -> str:
        keys = ",".join(self.body_keys or self.query_keys) or "-"
        return (
            f"{self.function} {self.method} {self.path} "
            f"content-type={self.content_type} keys={keys}"
        )


def create_dxf_parts_xhr() -> CadImportXhr:
    """The XHR whose success List is written to #gridDXFParts."""
    return CadImportXhr(
        function=CREATE_DXF_PARTS_FUNCTION,
        method="POST",
        path=CREATE_DXF_PARTS_PATH,
        content_type=CREATE_DXF_PARTS_CONTENT_TYPE,
        body_keys=list(CREATE_DXF_PARTS_BODY_KEYS),
        snippet=CREATE_DXF_PARTS_SNIPPET,
    )


def script_srcs(html: str, *, base: str = "https://www.secturafab.com") -> list[str]:
    """Absolute script URLs from GetItem_AddView / Quote HTML."""
    out: list[str] = []
    seen: set[str] = set()
    for match in _SCRIPT_SRC_RE.finditer(html or ""):
        raw = (match.group(1) or "").strip()
        if not raw or raw.startswith("data:"):
            continue
        url = urljoin(base.rstrip("/") + "/", raw.lstrip("/"))
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def _function_near(text: str, pos: int) -> str:
    window = text[max(0, pos - 500) : pos]
    found = list(_FUNC_RE.finditer(window))
    if not found:
        return "anonymous"
    last = found[-1]
    return next((g for g in last.groups() if g), "anonymous")


def _window(text: str, start: int, end: int, *, radius: int = 420) -> str:
    return text[max(0, start - radius) : min(len(text), end + radius)]


def extract_cadimport_xhrs(js_or_html: str) -> list[CadImportXhr]:
    """Find CadImport / /part/create ajax URLs and the function that owns them."""
    text = js_or_html or ""
    found: list[CadImportXhr] = []
    seen: set[tuple[str, str, str]] = set()
    for regex in (_CAD_URL_RE, _QUOTE_DXF_URL_RE):
        for match in regex.finditer(text):
            path = match.group(1)
            if path in _SKIP_PATHS:
                continue
            blob = _window(text, match.start(), match.end())
            func = _function_near(text, match.start())
            method_m = _TYPE_RE.search(blob)
            method = (method_m.group(1) if method_m else "POST").upper()
            if path.endswith("/Data") or path.startswith("/Quote/Get"):
                method = "GET"
            ct_m = _CT_RE.search(blob)
            if ct_m:
                content_type = ct_m.group(1).split(";")[0]
            elif "JSON.stringify" in blob or "application/json" in blob:
                content_type = "application/json"
            else:
                # QuoteOrderEdit $.ajax data:{...} with no contentType → form.
                content_type = "application/x-www-form-urlencoded"
            keys = [m.group(1) for m in _KEY_RE.finditer(blob)]
            uniq: list[str] = []
            for key in keys:
                if key not in uniq:
                    uniq.append(key)
            literals = {m.group(1): m.group(2) for m in _LIT_RE.finditer(blob)}
            rec = CadImportXhr(
                function=func,
                method=method,
                path=path,
                content_type=content_type,
                query_keys=uniq if method == "GET" else [],
                body_keys=uniq if method != "GET" else [],
                literals=literals,
                snippet=re.sub(r"\s+", " ", blob)[:220],
            )
            sig = (rec.function, rec.method, rec.path)
            if sig in seen:
                continue
            seen.add(sig)
            found.append(rec)
    return found


def explode_xhrs(xhrs: list[CadImportXhr]) -> list[CadImportXhr]:
    """Only DoCreateDXFParts /part/create — that response fills #gridDXFParts.

    Cleanup tools (RemoveTitleBlock, DetectBendLines, …) also POST IDList
    but they do not create child rows. ConvertTo / UpdateDataNext are not
    explode (live 34887-1 FileList 0).
    """
    out: list[CadImportXhr] = []
    for xhr in xhrs:
        path_l = xhr.path.lower()
        if path_l == CREATE_DXF_PARTS_PATH or xhr.function == CREATE_DXF_PARTS_FUNCTION:
            out.append(xhr)
    return out


def cite_xhrs(xhrs: list[CadImportXhr]) -> list[str]:
    return [x.cite() for x in xhrs]


def jquery_ajax_form(fields: dict[str, Any]) -> list[tuple[str, str]]:
    """jQuery.param (traditional=false) pairs for $.ajax data:{...}.

    Arrays become ``IDList[]=`` / ``unitList[]=``. Empty arrays are omitted.
    """
    pairs: list[tuple[str, str]] = []
    for key, value in fields.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                pairs.append((f"{key}[]", "" if item is None else str(item)))
        elif value is None:
            continue
        else:
            pairs.append((key, str(value)))
    return pairs


def jquery_ajax_form_body(fields: dict[str, Any]) -> str:
    return urlencode(jquery_ajax_form(fields))


def build_create_dxf_parts_fields(
    rows: list[dict[str, Any]],
    *,
    location: str = "",
    other_file_ids: list[str] | None = None,
    height: int | float = 0,
    width: int | float = 0,
) -> dict[str, Any]:
    """DoCreateDXFParts body keys from #gridDXF upload rows."""
    id_list: list[str] = []
    unit_list: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = str(row.get("SourceDataID") or row.get("ID") or "").strip()
        if not sid:
            continue
        id_list.append(sid)
        units = str(
            row.get("Units") or row.get("Length_Units") or row.get("units") or "inch"
        ).strip()
        unit_list.append(units or "inch")
    return {
        "Location": location or "",
        "IDList": id_list,
        "unitList": unit_list,
        "OtherFileIDList": [str(x) for x in (other_file_ids or []) if x],
        "Height": int(height or 0),
        "Width": int(width or 0),
    }


def create_dxf_parts_missing_form_keys(fields: dict[str, Any] | None) -> list[str]:
    """UI DoCreateDXFParts keys absent from the posted form — do not invent."""
    have = {str(k) for k in (fields or {})}
    return [k for k in CREATE_DXF_PARTS_BODY_KEYS if k not in have]


def part_create_form_shape(
    form_pairs: list[tuple[str, str]] | None,
    *,
    height: Any = None,
    width: Any = None,
) -> dict[str, Any]:
    """UI-click compare: IDList shape + Height/Width type/zero — never values.

    jQuery traditional=false posts ``IDList[]``. UI Height/Width are
    ``$("#img").height()`` / ``width()`` numbers. Live FA Assembly
    proved #img copy is not the InternalData miss — remaining delta is
    fetch vs page ``$.ajax`` (Referer + XHR).
    """
    pairs = list(form_pairs or [])
    keys = [str(k) for k, _ in pairs]
    if any(k == "IDList[]" for k in keys):
        idlist_shape = "IDList[]"
    elif any(k == "IDList" for k in keys):
        idlist_shape = "IDList"
    else:
        idlist_shape = "missing"

    def _zero(val: Any) -> bool:
        try:
            return float(val or 0) == 0
        except (TypeError, ValueError):
            return True

    def _typ(val: Any) -> str:
        if val is None:
            return "missing"
        if isinstance(val, bool):
            return "bool"
        if isinstance(val, int) and not isinstance(val, bool):
            return "int"
        if isinstance(val, float):
            return "float"
        if isinstance(val, str):
            return "str"
        return type(val).__name__

    return {
        "idlist_shape": idlist_shape,
        "height_type": _typ(height),
        "width_type": _typ(width),
        "height_zero": _zero(height),
        "width_zero": _zero(width),
    }


def build_xhr_payload(
    xhr: CadImportXhr,
    *,
    quote_id: str,
    rows: list[dict[str, Any]],
    quote_request_id: str | None = None,
    next_body: dict[str, Any] | None = None,
    location: str = "",
) -> dict[str, Any]:
    """Fill only keys the JS referenced."""
    if xhr.path.lower() == CREATE_DXF_PARTS_PATH:
        return build_create_dxf_parts_fields(rows, location=location)
    row = next((r for r in rows if isinstance(r, dict)), {})
    keys = list(xhr.body_keys or xhr.query_keys)
    if not keys and next_body:
        return dict(next_body)
    out: dict[str, Any] = {}
    for key in keys:
        kl = key.lower()
        if kl in {"id", "quoteid"}:
            out[key] = quote_id
        elif kl in {"quoterequestid"}:
            if quote_request_id:
                out[key] = quote_request_id
        elif key == "List" and next_body and isinstance(next_body.get("List"), list):
            out["List"] = next_body["List"]
        elif key == "ListOther" and next_body:
            out["ListOther"] = next_body.get("ListOther") or []
        elif key == "status" and next_body:
            out["status"] = next_body.get("status") or "OK"
        elif key == "IDList":
            out["IDList"] = [
                str(r.get("SourceDataID") or r.get("ID") or "")
                for r in rows
                if isinstance(r, dict) and (r.get("SourceDataID") or r.get("ID"))
            ]
        elif key == "unitList":
            out["unitList"] = [
                str(r.get("Units") or r.get("Length_Units") or "inch")
                for r in rows
                if isinstance(r, dict)
            ]
        elif key in row and row.get(key) not in (None, ""):
            out[key] = row[key]
        elif key in xhr.literals:
            out[key] = xhr.literals[key]
    if not out and next_body:
        return dict(next_body)
    return out


def same_origin_script(url: str, *, website_root: str) -> bool:
    host = (urlparse(url).netloc or "").lower()
    root = (urlparse(website_root).netloc or "").lower()
    return bool(host) and host == root
