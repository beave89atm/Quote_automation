"""SecturaFAB website MVC helpers — Kyle's CAD Files / Finish / Long / Nest path.

Recovered from QuoteOrderEdit JS (not in public OpenAPI). controllerName = '/Quote'.

CadImport MVC lives on the signed-in UI host (www.secturafab.com), same
cookie as Quotes. api.secturafab.com accepted Upload (200, List=1) on
live 1007756-3 but SetUnits 500, GetDXFData 404, and Next/Data 200 with
a string body the FileList parser treated as 0 rows. Prefer www; do not
treat an API 500/404 as final. CadImport stays on www — do not fall
through SetUnits/GetDXFData 500/404 to the API host (live 1002381-1
logged api after www already failed the same way).

UpdateDataNext List must be a JSON array of objects, never Python
str(list) with single quotes (live 1002381-1 Next 200 empty body).
SetUnits sends one query key `units` (ASP.NET NameValueCollection is
case-insensitive; units+Units 500s "same key has already been added").
Do not Finish the raw STEP upload row.

  GET  /Quote/GetItem_AddView?ID={quoteId}&ItemType=dxf
  POST /Attachment/UploadItem_PDFFiles  (Image Files plates — not CadImport)
  POST /CadImport/UploadItem_DXFFiles   (STEP / DXF CAD Files only)
  GET  /CadImport/Data
  POST /CadImport/UpdateData, UpdateDataNext, SetPartMode, SetUnits, ConvertTo
  GET  /CadImport/GetDXFData then /Quote/GetDXFData  (grid after green Next)
  POST /Quote/AddItem_DXFFiles   data { ID, ItemID, customerMaterial, FileList }
  POST /Quote/AddItem_PDFFiles   urlencoded { ID, ItemID, FileList } one part
  POST /Quote/AddItem_Linear     urlencoded OnAddLinearClick field bag
  GET  /Product/Read_DataLinearlookup?ProductID=  (20ft/21ft productConfigID)
  POST /Quote/NestQuote_Edit
  POST /Quote/NestQuoteMultiPart_Renest

FileList = #gridDXFParts rows with ErrorStatus===0 and Qty>0.
Finish writes Primary Costs (Laser/Drafting/… under PR; Saw + Saw Setup
under the linear calculator). The FileList must be the CadImport upload
grid row (SourceDataID / FileID / Stock_*). Slimming those IDs leaves
AddItem_DXFFiles / AddItem_PDFFiles with nothing to calculate. Cookie-less
addplate / addLinear fill Material/Length/UnitCost but do **not** write
OperationCostList. Do not graft those names as item-level OperationName tags.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

EMPTY_GUID = "00000000-0000-0000-0000-000000000000"
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_FT_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(?:'|ft|feet)\b")


def is_tenant_guid(value: Any) -> bool:
    text = str(value or "").strip()
    if not text or text == EMPTY_GUID:
        return False
    return bool(_GUID_RE.fullmatch(text))

# SetPartMode requires an integer (strings 500). Verified 0..4 HTTP 200 on empty guid.
# Mapping follows Kyle UI categories + Q10056 ProductType (100 Cad, 10/30/40 Linear, 200 Component).
# Long ProductType: 10 bar, 30 tube, 40 angle/channel. 20 (pipe) fails live GET.
# Do not force angles to 10 — QA that says "ProductType is 40, want 10" is wrong.
PART_MODE_CAD = 0
PART_MODE_LINEAR = 1
PART_MODE_COMPONENT = 2
LINEAR_PRODUCT_TYPE_BAR = 10
LINEAR_PRODUCT_TYPE_TUBE = 30
LINEAR_PRODUCT_TYPE_ANGLE = 40
VALID_LINEAR_PRODUCT_TYPES = frozenset(
    {
        LINEAR_PRODUCT_TYPE_BAR,
        LINEAR_PRODUCT_TYPE_TUBE,
        LINEAR_PRODUCT_TYPE_ANGLE,
    }
)

PART_MODE_BY_CATEGORY = {
    "Cad": PART_MODE_CAD,
    "Linear": PART_MODE_LINEAR,
    "Component": PART_MODE_COMPONENT,
}

WEBSITE_FINISH_PATHS = {
    "get_item_add_view": "/Quote/GetItem_AddView",
    "upload_pdf_attachment": "/Attachment/UploadItem_PDFFiles",
    "linear_lookup": "/Product/Read_DataLinearlookup",
    "upload_dxf": "/CadImport/UploadItem_DXFFiles",
    "cadimport_data": "/CadImport/Data",
    "cadimport_update_data": "/CadImport/UpdateData",
    "cadimport_update_data_next": "/CadImport/UpdateDataNext",
    "cadimport_set_part_mode": "/CadImport/SetPartMode",
    "cadimport_set_units": "/CadImport/SetUnits",
    "cadimport_convert_to": "/CadImport/ConvertTo",
    "cadimport_get_dxf_data": "/CadImport/GetDXFData",
    "quote_get_dxf_data": "/Quote/GetDXFData",
    "add_item_dxf_files": "/Quote/AddItem_DXFFiles",
    "add_item_pdf_files": "/Quote/AddItem_PDFFiles",
    "add_item_linear": "/Quote/AddItem_Linear",
    "add_operation": "/Quote/AddOperation",
    "copy_move_to_assembly": "/Quote/CopyMoveItemToAssembly",
    "add_feature": "/Quote/AddFeature",
    "quote_item_read": "/Quote/QuoteItem_Read",
    "nest_quote_edit": "/Quote/NestQuote_Edit",
    "nest_quote_renest": "/Quote/NestQuoteMultiPart_Renest",
}

# Q10056 Weld calculator shape (website AddOperation, not grafted Laser).
WELD_CALC_PARAM_TYPE = "weld|perunittime|perunittime|fixedtime|perunitcost"
WELD_OPERATION_CODE = "op_weld"
WELD_EQUIPMENT = "Welding"
WELD_APPLY_TO = "ITEM"

WELD_ADD_FIELDS = (
    "ID",
    "ItemID",
    "operation_code",
    "Equipment",
    "ApplyTo",
    "CalcParamType",
    "weld",
    "perunittime",
    "perunittime2",
    "fixedtime",
    "perunitcost",
)

COPY_MOVE_FIELDS = (
    "ID",
    "ItemID",
    "AssemblyID",
    "Mode",
)

ADD_FEATURE_FIELDS = (
    "ID",
    "ItemID",
    "FeatureType",
    "Diameter",
    "Qty",
)

WEBSITE_SESSION_EXPIRED = "website session expired"

WEBSITE_AUTH_GAP = (
    "Finish needs SECTURA_WEBSITE_COOKIE (env or file) from the signed-in "
    "www.secturafab.com Chrome on this Linux box. "
    "Do not paste a cookie. Do not unwrap Windows Chrome. "
    "Do not use Kyle's quoting PC. "
    "GET /Quote/GetItem_AddView and POST /Quote/AddItem_DXFFiles, "
    "AddItem_PDFFiles, and AddItem_Linear 302 to /Account/Login or hit "
    "Cloudflare without that session (website session expired). "
    "Do not fall back to quickAddCAD. "
    "Do not graft Laser/Drafting/Saw Setup as item tags."
)

# Identity keys CadImport/UploadItem_DXFFiles returns. Finish needs these
# to attach DataPart and run the Profile / Saw calculators. Do not drop.
CADIMPORT_IDENTITY_FIELDS = (
    "SourceDataID",
    "FileID",
    "CadType",
    "FileType",
    "PartCount",
    "OpenContourCount",
    "Stock_X",
    "Stock_Y",
    "Stock_Z",
    "Stock_Units",
    "Stock_Length",
    "Stock_Diameter",
    "PartID",
    "ParentName",
    "Error",
)

# Field bag the JS copies from #gridDXFParts into FileList.
FILELIST_FIELDS = (
    "ErrorStatus",
    "Qty",
    "Quantity",
    "Machine",
    "Material",
    "MaterialGrade",
    "Thickness",
    "Thickness_Units",
    "ProductID",
    "SKU",
    "Name",
    "PartName",
    "FileName",
    "Description",
    "PartMode",
    "IsLinear",
    "IsPlate",
    "IsPart",
    "ItemType",
    "Category",
    "Length",
    "Width",
    "LinearLength",
    "LinearWidth",
    "LinearHeight",
    "Dim1",
    "Dim2",
    "Dim3",
    "Dim4",
    "Dim1_Units",
    "Dim2_Units",
    "Dim3_Units",
    "Dim4_Units",
    "ID",
    "ItemID",
    "Units",
    *CADIMPORT_IDENTITY_FIELDS,
)


class SecturaFabWebsiteAuthError(RuntimeError):
    """MVC Finish / Quote dialog requires a website session cookie."""

    def __init__(
        self,
        message: str = WEBSITE_AUTH_GAP,
        *,
        status_code: int | None = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def _qty_of(row: dict[str, Any]) -> float:
    for key in ("Qty", "Quantity", "qty"):
        if key in row and row.get(key) is not None:
            try:
                return float(row.get(key) or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _error_status(row: dict[str, Any]) -> int:
    raw = row.get("ErrorStatus", row.get("errorStatus", 0))
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def filter_finish_filelist(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """JS: #gridDXFParts rows with ErrorStatus===0 and Qty>0."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if _error_status(row) != 0:
            continue
        if _qty_of(row) <= 0:
            continue
        out.append(dict(row))
    return out


def slim_filelist_row(row: dict[str, Any]) -> dict[str, Any]:
    """Keep the CadImport / #gridDXFParts row. JS Finish posts the whole row."""
    slim: dict[str, Any] = dict(row)
    if "Qty" not in slim and "Quantity" in slim:
        slim["Qty"] = slim["Quantity"]
    if "Quantity" not in slim and "Qty" in slim:
        slim["Quantity"] = slim["Qty"]
    return slim


_CADIMPORT_ROW_KEYS = (
    "List",
    "FileList",
    "Data",
    "data",
    "Result",
    "Items",
    "rows",
    "d",
)

# #gridDXFParts / Next JSON embedded in an HTML dialog or Kendo init.
_FILELIST_JSON_RE = re.compile(
    r'"(?:FileList|List)"\s*:\s*(\[(?:[^[\]]|\[[^[\]]*\])*\])',
    re.DOTALL,
)
_SOURCEDATA_OBJ_RE = re.compile(
    r'\{[^{}]*"SourceDataID"\s*:\s*"(?:[^"\\]|\\.)+"[^{}]*\}',
)


def cadimport_payload_preview(payload: Any, *, limit: int = 160) -> str:
    """Short type/len note for explode logs. Never include cookies."""
    if payload is None:
        return "null"
    if isinstance(payload, dict):
        keys = ",".join(list(payload)[:8])
        return f"dict keys={keys!r} n={len(payload)}"
    if isinstance(payload, list):
        return f"list len={len(payload)}"
    text = str(payload).replace("\r", " ").replace("\n", " ").strip()
    return f"string {text[:limit]!r}"


def _filelist_rows_from_html(text: str) -> list[dict[str, Any]]:
    """Pull #gridDXFParts / FileList rows out of an HTML or JS-string body."""
    if not text:
        return []
    blob = text
    if "SourceDataID" not in blob and "FileList" not in blob and "gridDXFParts" not in blob:
        return []
    for match in _FILELIST_JSON_RE.finditer(blob):
        try:
            rows = json.loads(match.group(1))
        except ValueError:
            continue
        if isinstance(rows, list) and any(isinstance(r, dict) for r in rows):
            return [dict(r) for r in rows if isinstance(r, dict)]
    objs: list[dict[str, Any]] = []
    for match in _SOURCEDATA_OBJ_RE.finditer(blob):
        try:
            obj = json.loads(match.group(0))
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("SourceDataID") not in (None, ""):
            objs.append(obj)
    return objs


def _coerce_cadimport_payload(payload: Any) -> Any:
    """Unwrap JSON-as-string / nested Data strings from Next and CadImport/Data."""
    cur: Any = payload
    for _ in range(5):
        if isinstance(cur, (bytes, bytearray)):
            cur = cur.decode("utf-8", errors="replace")
            continue
        if isinstance(cur, str):
            text = cur.strip()
            if not text:
                return cur
            try:
                cur = json.loads(text)
                continue
            except ValueError:
                html_rows = _filelist_rows_from_html(text)
                return html_rows if html_rows else cur
        if isinstance(cur, dict):
            for key in ("d", "Data", "data", "Result"):
                val = cur.get(key)
                if isinstance(val, str) and val.strip()[:1] in "{[":
                    try:
                        cur = json.loads(val)
                        break
                    except ValueError:
                        continue
            else:
                return cur
            continue
        return cur
    return cur


def _rows_from_cadimport_container(rows: Any) -> list[dict[str, Any]] | None:
    if isinstance(rows, str):
        try:
            rows = json.loads(rows)
        except ValueError:
            extracted = _filelist_rows_from_html(rows)
            return extracted or None
    if isinstance(rows, dict):
        for inner in _CADIMPORT_ROW_KEYS:
            val = rows.get(inner)
            if isinstance(val, list):
                rows = val
                break
        else:
            return None
    if isinstance(rows, list) and any(isinstance(r, dict) for r in rows):
        return [dict(r) for r in rows if isinstance(r, dict)]
    return None


def filelist_from_cadimport_upload(payload: Any) -> list[dict[str, Any]]:
    """Rows from CadImport Upload / Next / Data / GetDXFData / GetItem_AddView.

    Live Next/Data on the API host returned HTTP 200 with a *string* body
    (HTML dialog, JSON-as-string, or Kendo init). Unwrap those so FileList
    kids are visible; a dict/list with List/FileList/Data still wins.
    """
    payload = _coerce_cadimport_payload(payload)
    if isinstance(payload, list):
        return [dict(r) for r in payload if isinstance(r, dict)]
    if isinstance(payload, str):
        return _filelist_rows_from_html(payload)
    if not isinstance(payload, dict):
        return []
    for key in _CADIMPORT_ROW_KEYS:
        found = _rows_from_cadimport_container(payload.get(key))
        if found:
            return found
    return _filelist_rows_from_html(json.dumps(payload)) if payload else []


_REQUEST_VERIFICATION_RE = re.compile(
    r'name=["\']__RequestVerificationToken["\'][^>]*value=["\']([^"\']+)["\']'
    r'|value=["\']([^"\']+)["\'][^>]*name=["\']__RequestVerificationToken["\']',
    re.I,
)


def request_verification_token(html: Any) -> str | None:
    """Hidden field from GetItem_AddView — QuoteOrderEdit posts it with MVC ajax."""
    text = html if isinstance(html, str) else ""
    if not text:
        return None
    match = _REQUEST_VERIFICATION_RE.search(text)
    if not match:
        return None
    return (match.group(1) or match.group(2) or "").strip() or None


def normalize_cadimport_list(value: Any) -> list[dict[str, Any]]:
    """Coerce List / ListOther to a list of row dicts.

    Live 1002381-1 request preview had List as Python ``str(rows)``
    (single quotes) and ListOther as ``\"[]\"``. That is not a JSON array
    and UpdateDataNext 200s with an empty body (no explode).
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [dict(r) for r in value if isinstance(r, dict)]
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        text = value.strip()
        if not text or text in {"[]", "null", "None"}:
            return []
        parsed: Any
        try:
            parsed = json.loads(text)
        except ValueError:
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                return []
        if parsed is value:
            return []
        return normalize_cadimport_list(parsed)
    if isinstance(value, dict):
        for key in _CADIMPORT_ROW_KEYS:
            found = value.get(key)
            if found is not None and found is not value:
                rows = normalize_cadimport_list(found)
                if rows:
                    return rows
        if any(k in value for k in ("SourceDataID", "FileID", "FileName", "Name")):
            return [dict(value)]
    return []


def build_cadimport_next_payload(
    quote_id: str,
    rows: Any,
    *,
    list_other: Any = None,
) -> dict[str, Any]:
    """Green Next body: List is a JSON array of objects, not str(list)."""
    return {
        "ID": quote_id,
        "List": normalize_cadimport_list(rows),
        "ListOther": normalize_cadimport_list(list_other),
    }


def cadimport_next_form(
    payload: dict[str, Any],
    *,
    token: str | None = None,
) -> list[tuple[str, str]]:
    """urlencoded Next — List/ListOther are JSON arrays (double quotes)."""
    rows = normalize_cadimport_list(payload.get("List"))
    other = normalize_cadimport_list(payload.get("ListOther"))
    form: list[tuple[str, str]] = []
    qid = str(payload.get("ID") or payload.get("quoteID") or "").strip()
    if qid:
        form.append(("ID", qid))
    form.append(("List", json.dumps(rows, default=str)))
    form.append(("ListOther", json.dumps(other, default=str)))
    if token:
        form.append(("__RequestVerificationToken", token))
    return form


def _step_like_name(text: str | None) -> bool:
    raw = str(text or "").strip().lower()
    return raw.endswith(".step") or raw.endswith(".stp")


def is_raw_step_upload_row(
    row: dict[str, Any] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> bool:
    """True when the row is the STEP file itself, not an exploded child PN."""
    if not isinstance(row, dict):
        return False
    from .item_desc import normalize_part_token

    fname = str(row.get("FileName") or row.get("Name") or "")
    cad_name = cad_filename or fname
    is_step = _step_like_name(fname) or _step_like_name(cad_name)
    if not is_step:
        return False
    try:
        part_count = int(row.get("PartCount") or 0)
    except (TypeError, ValueError):
        part_count = 0
    if part_count > 1:
        return True
    name = str(
        row.get("Name") or row.get("Description") or row.get("PartName") or ""
    )
    stem = Path(cad_name).stem if cad_name else Path(fname).stem
    name_tok = normalize_part_token(name)
    stem_tok = normalize_part_token(stem)
    pk_tok = normalize_part_token(part_key)
    if _step_like_name(name):
        return True
    if name_tok in {"", stem_tok, pk_tok, normalize_part_token(Path(fname).stem)}:
        return True
    return False


def cadimport_filelist_exploded(
    rows: list[dict[str, Any]] | None,
    *,
    part_key: str = "",
    cad_filename: str = "",
) -> bool:
    """True when CadImport split the STEP into child FileList rows (Kyle Next)."""
    kids = [r for r in (rows or []) if isinstance(r, dict)]
    if not kids:
        return False
    if len(kids) >= 2:
        return True
    return not is_raw_step_upload_row(
        kids[0], part_key=part_key, cad_filename=cad_filename
    )


def build_dxf_finish_payload(
    quote_id: str,
    file_list: list[dict[str, Any]],
    *,
    item_id: str | None = None,
    customer_material: bool = False,
) -> dict[str, Any]:
    """POST /Quote/AddItem_DXFFiles body from the QuoteOrderEdit JS contract."""
    rows = [slim_filelist_row(r) for r in filter_finish_filelist(file_list)]
    return {
        "ID": quote_id,
        "ItemID": item_id or EMPTY_GUID,
        "customerMaterial": bool(customer_material),
        "FileList": rows,
    }


# GetPDFData() row keys from QuoteOrderEdit OnAddPDFClick, plus Status
# (grid filter Status>0) so New Line Item actually commits.
PDF_GETDATA_FIELDS = (
    "Status",
    "ItemType",
    "ItemID",
    "FileID",
    "SourceDataID",
    "ImageID",
    "FileName",
    "RevisionNumber",
    "Description",
    "PageNumber",
    "PartName",
    "Machine",
    "Memo",
    "Material",
    "Thickness",
    "Thickness_Units",
    "Location",
    "ProcessLocation",
    "Qty",
    "FixedCost",
    "FixedPrice",
    "HasFixedPrice",
    "CustomerMaterial",
    "Grain",
    "Outsource",
    "OutsourceMargin",
    "MaterialCost",
    "MaterialCost_Units",
    "VendorID",
    "VendorName",
    "WeightBorder",
    "WeightBorder_Units",
    "NumberOfHeads",
    "Length",
    "Length_Units",
    "Width",
    "Width_Units",
    "OutsideArea",
    "OutsideArea_Units",
    "OutsidePerimeter",
    "OutsidePerimeter_Units",
    "OutsidePerimeter_UseLocal",
    "Weight",
    "Weight_Units",
    "Weight_UseLocal",
    "TrueWeight",
    "TrueWeight_Units",
    "InternalData",
    "ProductID",
    "ProductType",
    "ProductSubType",
    "Dim1",
    "Dim1_Units",
    "Dim2",
    "Dim2_Units",
    "Dim3",
    "Dim3_Units",
    "Dim4",
    "Dim4_Units",
    "WeightLength",
    "WeightLength_Units",
    "LinearMaterialCost",
    "LinearMaterialCost_Units",
    "LinearMachine",
    "LinearTrimLeft",
    "LinearLeftMiterAngle",
    "LinearTrimRight",
    "LinearRightMiterAngle",
    "PriceListID",
    "PriceListItemID",
    "MarginMarkup",
)

# OnAddLinearClick body keys. Do not add others.
LINEAR_ADD_FIELDS = (
    "ID",
    "ItemID",
    "productID",
    "productType",
    "productSubType",
    "productConfigID",
    "material",
    "location",
    "dim1",
    "dim1_Unit",
    "dim2",
    "dim2_Unit",
    "dim3",
    "dim3_Unit",
    "dim4",
    "dim4_Unit",
    "weightLength",
    "weightLength_Units",
    "materialCost",
    "materialCost_Units",
    "memo",
    "name",
    "revisionNumber",
    "machine",
    "length",
    "length_unit",
    "qty",
    "fixedPrice",
    "productionReady",
    "customerMaterial",
    "outsource",
    "outsourceCustomerMaterial",
    "outsourceUnitCost",
    "outsourceMargin",
    "vendorID",
    "FileID",
    "ImageID",
    "MiterLeft",
    "MiterLeftAngle1",
    "MiterLeftAngle2",
    "MiterLeftOffset",
    "MiterRight",
    "MiterRightAngle1",
    "MiterRightAngle2",
    "MiterRightOffset",
    "Internal",
    "processLocation",
)


def _pdf_row_status(row: dict[str, Any]) -> float:
    raw = row.get("Status", row.get("status"))
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def filter_pdf_filelist(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """GetPDFData(): gridPDF rows with Status>0."""
    out: list[dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if _pdf_row_status(row) <= 0:
            continue
        out.append(dict(row))
    return out


def prepare_pdf_newline_fields(row: dict[str, Any]) -> dict[str, Any]:
    """Commit Image Files New Line Item fields (not CadImport list-only).

    Drawing flat is Length/Width (or CadImport Stock_X/Y). Never a PDF page outline.
    Proven Image Files FileList uses ItemType=cad, Machine=Laser - Bay1, Status>0.
    """
    out = dict(row)
    try:
        status = float(out.get("Status") or 0)
    except (TypeError, ValueError):
        status = 0.0
    if status <= 0:
        out["Status"] = 1
    machine = str(out.get("Machine") or "").strip()
    if not machine or machine.casefold() in {"laser", "laser - bay1", "laser-bay1"}:
        out["Machine"] = "Laser - Bay1"
    if str(out.get("ItemType") or "").casefold() != "linear":
        out["ItemType"] = "cad"
    out["ProductType"] = out.get("ProductType") or 100
    try:
        if int(out["ProductType"]) != 100 and not out.get("IsLinear"):
            out["ProductType"] = 100
    except (TypeError, ValueError):
        out["ProductType"] = 100
    out["Location"] = out.get("Location") or "Bay1"
    out["ProcessLocation"] = out.get("ProcessLocation") or out.get("Location") or "Bay1"
    if not out.get("PartName") and out.get("Name"):
        out["PartName"] = out["Name"]
    if not out.get("Description") and (out.get("Name") or out.get("PartName")):
        out["Description"] = out.get("Name") or out.get("PartName")
    length = out.get("Length") or out.get("Stock_Y") or out.get("Stock_Length")
    width = out.get("Width") or out.get("Stock_X")
    if length not in (None, ""):
        out["Length"] = length
        out["Length_Units"] = out.get("Length_Units") or "inch"
    if width not in (None, ""):
        out["Width"] = width
        out["Width_Units"] = out.get("Width_Units") or "inch"
    if _qty_of(out) <= 0:
        out["Qty"] = 1
    return out


def slim_pdf_grid_row(row: dict[str, Any]) -> dict[str, Any]:
    """Deprecated helper. AddItem_PDFFiles must keep the full upload List row."""
    return prepare_pdf_newline_fields(row)


def _first_upload_row(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                return row
        return {}
    if not isinstance(payload, dict):
        return {}
    for key in ("List", "Data", "Results", "Result", "File", "NewItem"):
        inner = payload.get(key)
        if isinstance(inner, list):
            for row in inner:
                if isinstance(row, dict):
                    return row
        if isinstance(inner, dict):
            nested = inner.get("NewItem") or inner.get("File") or inner.get("Result")
            if isinstance(nested, dict):
                return nested
            if inner.get("FileID") or inner.get("ID") or inner.get("ImageID"):
                return inner
    if payload.get("FileID") or payload.get("ImageID") or payload.get("ID"):
        return payload
    return {}


def filelist_row_from_attachment_upload(
    payload: Any,
    *,
    part_name: str,
    description: str = "",
    qty: int = 1,
    material: str = "A36",
    thickness: Any = None,
    length: Any = None,
    width: Any = None,
    file_name: str = "",
) -> dict[str, Any]:
    """FileList row after POST /Attachment/UploadItem_PDFFiles (not CadImport).

    Merge the upload List row so calculator identity fields stay on FileList.
    Keep whatever the upload actually returned. Do not invent SourceDataID
    (live Upload List often has none). Live 7a555ac2 posted an 85-key
    jquery.param FileList[0][Field] + Laser - Bay1 and still left Badge
    empty — do not switch that encoding to JSON.
    """
    src = dict(_first_upload_row(payload))
    file_id = src.get("FileID") or src.get("ID") or src.get("ImageID") or ""
    image_id = src.get("ImageID") or file_id
    length = length if length not in (None, "") else (
        src.get("Length") or src.get("Stock_Y")
    )
    width = width if width not in (None, "") else (
        src.get("Width") or src.get("Stock_X")
    )
    thickness = thickness if thickness not in (None, "") else src.get("Thickness")
    row = dict(src)
    row.update(
        {
            "Status": 1,
            "ItemType": "cad",
            "ItemID": src.get("ItemID") or EMPTY_GUID,
            "FileID": file_id,
            "ImageID": image_id,
            "FileName": file_name or src.get("FileName") or "",
            "PartName": part_name,
            "Description": description or part_name,
            "Qty": max(1, int(qty or 1)),
            "Machine": "Laser - Bay1",
            "Material": material or "A36",
            "Thickness": thickness,
            "Thickness_Units": src.get("Thickness_Units") or "inch",
            "Length": length,
            "Length_Units": src.get("Length_Units") or "inch",
            "Width": width,
            "Width_Units": src.get("Width_Units") or "inch",
            "ProductType": src.get("ProductType") or 100,
        }
    )
    if src.get("SourceDataID") not in (None, ""):
        row["SourceDataID"] = src["SourceDataID"]
    if src.get("FileID") not in (None, ""):
        row["FileID"] = src["FileID"]
    return prepare_pdf_newline_fields(row)


def _filelist_dim(val: Any) -> float:
    """Numeric FileList Thickness / Length / Width (fractions ok)."""
    if val in (None, ""):
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        text = str(val).strip().replace('"', "").replace("″", "").replace("'", "")
        if "/" in text:
            try:
                num, den = text.split("/", 1)
                den_f = float(den)
                if den_f:
                    return float(num) / den_f
            except (TypeError, ValueError, ZeroDivisionError):
                return 0.0
        return 0.0


def attachment_pdf_filelist_ready(row: dict[str, Any] | None) -> bool:
    """True only when Image Files New Line Item fields are present."""
    if not isinstance(row, dict):
        return False
    if str(row.get("ItemType") or "").strip().casefold() != "cad":
        return False
    try:
        thickness = _filelist_dim(row.get("Thickness"))
        length = _filelist_dim(row.get("Length"))
        width = _filelist_dim(row.get("Width"))
        status = float(row.get("Status") or 0)
    except (TypeError, ValueError):
        return False
    return thickness > 0 and length > 0 and width > 0 and status > 0


def is_cadimport_only_filelist_row(row: dict[str, Any] | None) -> bool:
    """CadImport identity without Attachment New Line Item fields."""
    if not isinstance(row, dict):
        return False
    has_cadimport = bool(row.get("SourceDataID")) or "CadType" in row
    return has_cadimport and not attachment_pdf_filelist_ready(
        prepare_pdf_newline_fields(row)
    )


def quote_item_rows(payload: Any) -> list[dict[str, Any]]:
    """Rows from v1/quote ItemList or QuoteItem_Read Data."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("ItemList", "Data", "Results"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def count_cad_product_type(payload: Any) -> int:
    n = 0
    for it in quote_item_rows(payload):
        try:
            if int(it.get("ProductType")) == 100:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def count_linear_product_type(payload: Any) -> int:
    n = 0
    for it in quote_item_rows(payload):
        try:
            if int(it.get("ProductType")) in VALID_LINEAR_PRODUCT_TYPES:
                n += 1
        except (TypeError, ValueError):
            continue
    return n


def linear_lookup_rows(payload: Any) -> list[dict[str, Any]]:
    """Rows from /Product/Read_DataLinearlookup or a catalog product.Configs.

    Do not stop at Data. Live 7a555ac2 Data was the product-shaped row
    (Value == productID); the 20ft/21ft config GUIDs sat on List.
    """
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    out: list[dict[str, Any]] = []
    seen: set[int] = set()

    def _add(rows: Any) -> None:
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, dict):
                continue
            marker = id(row)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(row)
            for nested_key in (
                "Configs",
                "ProductConfigList",
                "ProductConfigs",
                "List",
            ):
                inner = row.get(nested_key)
                if inner is not None and inner is not row:
                    _add(inner)

    for key in (
        "Data",
        "Results",
        "List",
        "Configs",
        "ProductConfigList",
        "ProductConfigs",
        "ItemList",
    ):
        _add(payload.get(key))
    if not out and any(payload.get(k) not in (None, "") for k in ("Value", "ID", "Text", "Name")):
        out.append(payload)
    return out


def _linear_config_guid(
    row: dict[str, Any] | None,
    *,
    not_id: str | None = None,
) -> str | None:
    """Stock-length config GUID. Never the product GUID (that 500s)."""
    if not isinstance(row, dict):
        return None
    skip = {
        EMPTY_GUID,
        str(not_id or "").strip(),
        str(row.get("ProductID") or "").strip(),
        str(row.get("productID") or "").strip(),
    }
    skip.discard("")
    for key in (
        "Value",
        "ProductConfigID",
        "ConfigID",
        "ConfigValue",
        "Key",
    ):
        val = row.get(key)
        if is_tenant_guid(val) and str(val) not in skip:
            return str(val)
    val = row.get("ID")
    if is_tenant_guid(val) and str(val) not in skip:
        return str(val)
    for key, val in row.items():
        if key in {"ProductID", "productID", "ID"}:
            continue
        if is_tenant_guid(val) and str(val) not in skip:
            return str(val)
    return None


def _linear_stock_feet(row: dict[str, Any] | None) -> float | None:
    if not isinstance(row, dict):
        return None
    label = " ".join(
        str(row.get(k) or "")
        for k in ("Name", "Text", "Display", "Description", "Length", "StockLength")
    )
    match = _FT_RE.search(label)
    if not match:
        return None
    try:
        return float(match.group(1))
    except (TypeError, ValueError):
        return None


def _lookup_row_belongs_to_product(
    row: dict[str, Any] | None,
    product: dict[str, Any] | None,
) -> bool:
    """True when a Read_DataLinearlookup row is this SKU — not the first 20ft row."""
    if not isinstance(row, dict) or not isinstance(product, dict):
        return False
    pid = str(product.get("ID") or product.get("ProductID") or "").strip()
    row_pid = str(row.get("ProductID") or row.get("productID") or "").strip()
    if pid and row_pid and row_pid == pid:
        return True
    sku = str(
        product.get("ProductName") or product.get("SKU") or product.get("ProductCode") or ""
    ).strip().upper()
    if not sku:
        return False
    blob = " ".join(
        str(row.get(k) or "")
        for k in ("ProductName", "SKU", "Name", "Text", "Display", "Description")
    ).upper()
    compact = sku.replace(" ", "")
    return bool(sku and (sku in blob or compact in blob.replace(" ", "")))


def pick_linear_config_row(
    rows: list[dict[str, Any]] | None,
    *,
    product_id: str | None = None,
    product: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Prefer the 20ft/21ft stock config row. Never a row whose GUID is productID."""
    wanted = str(product_id or (product or {}).get("ID") or "").strip()
    pool = [r for r in (rows or []) if isinstance(r, dict)]
    stock = [
        r
        for r in pool
        if _linear_stock_feet(r) in (20.0, 21.0)
        and _linear_config_guid(r, not_id=wanted)
    ]
    if stock:
        pool = stock
    elif product is not None or wanted:
        owned = [
            r
            for r in pool
            if _linear_config_guid(r, not_id=wanted)
            and (
                _lookup_row_belongs_to_product(r, product)
                or (
                    wanted
                    and str(r.get("ProductID") or r.get("productID") or "") == wanted
                )
            )
        ]
        distinct = [r for r in pool if _linear_config_guid(r, not_id=wanted)]
        pool = owned or distinct
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in pool:
        cid = _linear_config_guid(row, not_id=wanted)
        if not cid or (wanted and cid == wanted):
            continue
        feet = _linear_stock_feet(row)
        score = 10.0
        if feet in (20.0, 21.0):
            score = 100.0
        elif feet:
            score = 20.0
        ranked.append((score, row))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def pick_linear_config_id(
    rows: list[dict[str, Any]] | None,
    *,
    product_id: str | None = None,
    product: dict[str, Any] | None = None,
) -> str | None:
    """20ft/21ft config GUID. Never the product GUID (live 7a555ac2 500)."""
    wanted = str(product_id or (product or {}).get("ID") or "").strip()
    row = pick_linear_config_row(rows, product_id=product_id, product=product)
    if not row:
        return None
    cid = _linear_config_guid(row, not_id=wanted)
    if not cid or (wanted and cid == wanted):
        return None
    return cid


def _linear_bind_val(*rows: dict[str, Any] | None, keys: tuple[str, ...]) -> Any:
    """First non-empty value from the given rows in order."""
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in keys:
            val = row.get(key)
            if val not in (None, ""):
                return val
    return None


def _sku_num_token(raw: str) -> float | None:
    text = str(raw or "").strip().replace("-", " ")
    if not text:
        return None
    try:
        if " " in text and "/" in text:
            whole, frac = text.split(None, 1)
            num, den = frac.split("/", 1)
            return float(whole) + float(num) / float(den)
        if "/" in text:
            num, den = text.split("/", 1)
            den_f = float(den)
            if den_f == 0:
                return None
            return float(num) / den_f
        return float(text)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def parse_linear_sku_dims(sku: str | None) -> dict[str, float]:
    """Dim1-4 from this SKU only (C3X4.1 / L1/2X1/2X1/8 / RT1/8X0.022)."""
    raw = str(sku or "").upper().replace(" ", "")
    raw = re.sub(r"-[A-Z][A-Z0-9]*$", "", raw)
    rest = raw
    for prefix in ("HSS", "DOM", "RCT", "RT", "L", "C", "P"):
        if raw.startswith(prefix):
            rest = raw[len(prefix) :]
            break
    nums: list[float] = []
    for tok in re.split(r"[X×]", rest):
        num = _sku_num_token(tok)
        if num is None:
            continue
        nums.append(num)
        if len(nums) >= 4:
            break
    out: dict[str, float] = {}
    for idx, num in enumerate(nums, start=1):
        out[f"dim{idx}"] = num
    return out


def infer_linear_subtype(sku: str | None, description: str | None = None) -> str:
    """Website productSubType for this SKU — never copy another SKU's struct_ang."""
    text = f" {sku or ''} {description or ''} ".upper()
    compact = str(sku or "").upper().replace(" ", "")
    if "CHANNEL" in text or re.match(r"^C\d", compact):
        return "channel"
    if "ANGLE" in text or (compact.startswith("L") and "X" in compact):
        return "struct_ang"
    if compact.startswith(("RT", "RCT", "HSS", "DOM")) or " TUBE" in text:
        return "tube"
    if re.match(r"^P[\d/]", compact) or " PIPE" in text:
        return "pipe"
    if "HOSE GUARD" in text or " BAR" in text:
        return "bar"
    return "bar"


def linear_bind_fields(
    product: dict[str, Any] | None,
    configs: list[dict[str, Any]] | None = None,
    *,
    lookup_scoped: bool = False,
) -> dict[str, Any] | None:
    """productID + this SKU's subtype/dims/weightLength + its productConfigID.

    Never overlay another SKU's lookup row (live 51e017e reused L1/2 angle
    struct_ang / dim1=0.5 / wl=0.37275 on C3X4.1 and RT*). Lookup supplies
    the 20ft/21ft GUID; dims come from the catalog product or this SKU parse.
    """
    if not isinstance(product, dict):
        return None
    pid = product.get("ID") or product.get("ProductID")
    if not is_tenant_guid(pid):
        return None
    nested = list(configs or [])
    if not nested:
        nested = linear_lookup_rows(product)
    del lookup_scoped  # lookup List/Data is always scanned; never owned-only
    # Config GUIDs live on anonymous {Value, Text: "20 ft"} rows. A
    # product-shaped Data row (SKU in ProductName, Value==productID) is
    # "owned" and used to hide those Values — that 500'd live 7a555ac2.
    cfg_row = pick_linear_config_row(nested, product_id=str(pid), product=product) or {}
    cfg = _linear_config_guid(cfg_row, not_id=str(pid))
    if not cfg or cfg == str(pid):
        return None
    sku = str(
        product.get("ProductName")
        or product.get("SKU")
        or product.get("ProductCode")
        or ""
    )
    sku_dims = parse_linear_sku_dims(sku)
    owned_row = cfg_row if _lookup_row_belongs_to_product(cfg_row, product) else {}
    subtype = str(
        _linear_bind_val(
            product,
            owned_row,
            keys=("productSubType", "ProductSubType", "SubType", "ProductSubTypeName"),
        )
        or infer_linear_subtype(sku, str(product.get("Name") or ""))
    ).strip()

    def _dim(n: int) -> Any:
        got = _linear_bind_val(
            product,
            owned_row,
            keys=(f"dim{n}", f"Dim{n}", f"DIM{n}", f"Size{n}"),
        )
        if got not in (None, ""):
            return got
        if sku_dims.get(f"dim{n}") is not None:
            return sku_dims[f"dim{n}"]
        return 0

    return {
        "productID": str(pid),
        "productConfigID": cfg,
        "productSubType": subtype,
        "dim1": _dim(1),
        "dim1_Unit": _linear_bind_val(
            product, owned_row, keys=("dim1_Unit", "Dim1_Unit", "dim1_Units", "Dim1_Units")
        )
        or "inch",
        "dim2": _dim(2),
        "dim2_Unit": _linear_bind_val(
            product, owned_row, keys=("dim2_Unit", "Dim2_Unit", "dim2_Units", "Dim2_Units")
        )
        or "inch",
        "dim3": _dim(3),
        "dim3_Unit": _linear_bind_val(
            product, owned_row, keys=("dim3_Unit", "Dim3_Unit", "dim3_Units", "Dim3_Units")
        )
        or "inch",
        "dim4": _dim(4),
        "dim4_Unit": _linear_bind_val(
            product, owned_row, keys=("dim4_Unit", "Dim4_Unit", "dim4_Units", "Dim4_Units")
        )
        or "inch",
        "weightLength": _linear_bind_val(
            product,
            owned_row,
            keys=(
                "weightLength",
                "WeightLength",
                "WeightPerFoot",
                "WtPerFt",
                "Weight_Length",
            ),
        )
        or 0,
        "weightLength_Units": _linear_bind_val(
            product,
            owned_row,
            keys=("weightLength_Units", "WeightLength_Unit", "WeightLength_Units"),
        )
        or "pound/foot",
        "sku": sku or None,
    }


def redact_linear_add_keys(payload: dict[str, Any] | None) -> str:
    """Redacted OnAddLinearClick bag for 500 dumps (no full GUIDs)."""
    bits: list[str] = []
    for key in LINEAR_ADD_FIELDS:
        val = (payload or {}).get(key, "")
        if val in ("", None):
            bits.append(f"{key}=<empty>")
            continue
        if is_tenant_guid(val):
            bits.append(f"{key}=guid…{str(val)[-4:]}")
            continue
        bits.append(f"{key}={val}")
    return " ".join(bits)


def jquery_ajax_form(value: Any, prefix: str = "") -> list[tuple[str, str]]:
    """jQuery $.param (traditional=false) — ajax default urlencoding."""
    pairs: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            name = f"{prefix}[{key}]" if prefix else str(key)
            pairs.extend(jquery_ajax_form(inner, name))
        return pairs
    if isinstance(value, (list, tuple)):
        for idx, inner in enumerate(value):
            pairs.extend(jquery_ajax_form(inner, f"{prefix}[{idx}]"))
        return pairs
    if value is None:
        return [(prefix, "")]
    if isinstance(value, bool):
        return [(prefix, "true" if value else "false")]
    return [(prefix, str(value))]


def build_pdf_finish_payload(
    quote_id: str,
    file_list: list[dict[str, Any]],
    *,
    item_id: str | None = None,
    customer_material: bool = False,
) -> dict[str, Any]:
    """POST /Quote/AddItem_PDFFiles — { ID, ItemID, FileList } one part."""
    del customer_material  # row field only; not a top-level OnAddPDFClick key
    prepared = [
        prepare_pdf_newline_fields(r)
        for r in (file_list or [])
        if isinstance(r, dict)
    ]
    # Keep every upload List key. Slimming drops calculator identity that is
    # not named SourceDataID (live 51e017e Upload List never had SourceDataID).
    rows = [
        r
        for r in filter_pdf_filelist(prepared)
        if attachment_pdf_filelist_ready(r)
    ]
    return {
        "ID": quote_id,
        "ItemID": item_id or EMPTY_GUID,
        "FileList": rows,
    }


def build_linear_add_payload(
    quote_id: str,
    *,
    product_id: str,
    qty: int = 1,
    length: float | None = None,
    material: str | None = None,
    machine: str = "Saw",
    name: str = "",
    item_id: str | None = None,
    customer_material: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """POST /Quote/AddItem_Linear (OnAddLinearClick) — exact form keys."""
    payload: dict[str, Any] = {key: "" for key in LINEAR_ADD_FIELDS}
    payload["ID"] = quote_id
    payload["ItemID"] = item_id or EMPTY_GUID
    payload["productID"] = product_id
    payload["productType"] = linear_add_product_type(
        name, sku=str((extra or {}).get("sku") or "")
    )
    payload["qty"] = max(1, int(qty))
    payload["machine"] = machine
    payload["customerMaterial"] = bool(customer_material)
    if length is not None:
        payload["length"] = length
        payload["length_unit"] = "inch"
    if material:
        payload["material"] = material
    if name:
        payload["name"] = name
    if extra:
        for key, val in extra.items():
            if key in payload:
                payload[key] = val
    payload["productType"] = coerce_linear_add_product_type(
        payload.get("productType"),
        name=name,
        sku=str((extra or {}).get("sku") or ""),
    )
    cid = str(payload.get("productConfigID") or "")
    pid = str(payload.get("productID") or product_id or "")
    if not is_tenant_guid(payload.get("productConfigID")):
        raise ValueError(
            "AddItem_Linear requires a tenant productConfigID from "
            "/Product/Read_DataLinearlookup (empty GUID 500s)"
        )
    if cid == pid:
        raise ValueError("linear bind productConfigID must not equal productID")
    if str(payload.get("productSubType") or "").strip() == "":
        raise ValueError(
            "AddItem_Linear requires productSubType from the catalog lookup"
        )
    if not any(payload.get(k) not in ("", None) for k in ("dim1", "dim2", "dim3", "dim4")):
        raise ValueError(
            "AddItem_Linear requires dim1-4 from the catalog lookup"
        )
    if payload.get("weightLength") in ("", None):
        raise ValueError(
            "AddItem_Linear requires weightLength from the catalog lookup"
        )
    return payload


def build_weld_add_operation_payload(
    quote_id: str,
    item_id: str,
    *,
    weld_inches: float,
    weld_hours: float,
    fitup_hours: float,
    setup_hours: float,
    grind_cost: float = 0.0,
) -> dict[str, Any]:
    """POST /Quote/AddOperation — Q10056 CalcParamType on the assembly only."""
    payload: dict[str, Any] = {key: "" for key in WELD_ADD_FIELDS}
    payload["ID"] = quote_id
    payload["ItemID"] = item_id
    payload["operation_code"] = WELD_OPERATION_CODE
    payload["Equipment"] = WELD_EQUIPMENT
    payload["ApplyTo"] = WELD_APPLY_TO
    payload["CalcParamType"] = WELD_CALC_PARAM_TYPE
    payload["weld"] = float(weld_inches or 0)
    payload["perunittime"] = float(weld_hours or 0)
    payload["perunittime2"] = float(fitup_hours or 0)
    payload["fixedtime"] = float(setup_hours or 0)
    payload["perunitcost"] = float(grind_cost or 0)
    return payload


def build_copy_move_assembly_payload(
    quote_id: str,
    item_id: str,
    assembly_id: str,
    *,
    mode: str = "Move",
) -> dict[str, Any]:
    """POST /Quote/CopyMoveItemToAssembly — kids under the top-level assembly."""
    return {
        "ID": quote_id,
        "ItemID": item_id,
        "AssemblyID": assembly_id,
        "Mode": mode or "Move",
    }


def build_add_feature_payload(
    quote_id: str,
    item_id: str,
    *,
    diameter: float,
    qty: int = 1,
    feature_type: str = "Internal",
) -> dict[str, Any]:
    """POST /Quote/AddFeature — Internal hole when the drawing has one."""
    return {
        "ID": quote_id,
        "ItemID": item_id,
        "FeatureType": feature_type or "Internal",
        "Diameter": float(diameter),
        "Qty": max(1, int(qty or 1)),
    }


def internal_data_from_holes(holes: list[dict[str, Any]] | None) -> str:
    """Serialize hole features for Image Files FileList InternalData."""
    import json

    rows: list[dict[str, Any]] = []
    for hole in holes or []:
        if not isinstance(hole, dict):
            continue
        try:
            dia = float(hole.get("diameter") or hole.get("Diameter") or 0)
        except (TypeError, ValueError):
            continue
        if dia <= 0:
            continue
        try:
            qty = max(1, int(hole.get("qty") or hole.get("Qty") or 1))
        except (TypeError, ValueError):
            qty = 1
        rows.append({"Type": "Circle", "Diameter": dia, "Qty": qty})
    return json.dumps(rows) if rows else ""


def is_website_login_redirect(status_code: int, location: str | None) -> bool:
    loc = str(location or "")
    return status_code in {301, 302, 303, 307, 308} and "Login" in loc


def is_cloudflare_challenge(status_code: int, text: str | None) -> bool:
    blob = str(text or "")
    return status_code == 403 and (
        "Just a moment" in blob or "cf-challenge" in blob.lower()
    )


def part_mode_int(category: str) -> int:
    return PART_MODE_BY_CATEGORY.get(str(category or "Cad"), PART_MODE_CAD)


def coerce_product_type(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_valid_linear_product_type(value: Any) -> bool:
    return coerce_product_type(value) in VALID_LINEAR_PRODUCT_TYPES


def linear_website_product_type(
    description: str | None,
    sku: str | None = None,
) -> int:
    """GET ItemList ProductType: 10 bar, 30 tube, 40 angle/channel."""
    text = f" {str(description or '').upper()} {str(sku or '').upper()} "
    if any(h in text for h in (" ANGLE", " CHANNEL")):
        return LINEAR_PRODUCT_TYPE_ANGLE
    # Hose guards bind Round Bar (bar), not tube.
    if "HOSE GUARD" in text or "HOSEGUARD" in text:
        return LINEAR_PRODUCT_TYPE_BAR
    if any(h in text for h in (" TUBE", " HSS", " PIPE", " DOM")):
        return LINEAR_PRODUCT_TYPE_TUBE
    sku_u = str(sku or "").upper().strip()
    compact_sku = sku_u.replace(" ", "")
    if sku_u.startswith("L") and "X" in sku_u:
        return LINEAR_PRODUCT_TYPE_ANGLE
    if sku_u.startswith(("RT", "RCT", "HSS", "DOM")):
        return LINEAR_PRODUCT_TYPE_TUBE
    # Tenant pipe SKUs (P5-40-A36 / P1 1/4-40-A36) are Long tube, not bar.
    if re.match(r"^P[\d/]+-\d+", compact_sku):
        return LINEAR_PRODUCT_TYPE_TUBE
    return LINEAR_PRODUCT_TYPE_BAR


LINEAR_ADD_TYPE_STRUCTURAL = "structural"
LINEAR_ADD_TYPE_PIPE = "pipe"
LINEAR_ADD_TYPE_TUBE = "tube"
LINEAR_ADD_TYPE_BAR = "bar"
_LINEAR_ADD_TYPES = frozenset(
    {
        LINEAR_ADD_TYPE_STRUCTURAL,
        LINEAR_ADD_TYPE_PIPE,
        LINEAR_ADD_TYPE_TUBE,
        LINEAR_ADD_TYPE_BAR,
    }
)
_INT_TO_LINEAR_ADD_TYPE = {
    10: LINEAR_ADD_TYPE_BAR,
    20: LINEAR_ADD_TYPE_PIPE,
    30: LINEAR_ADD_TYPE_TUBE,
    40: LINEAR_ADD_TYPE_STRUCTURAL,
}


def linear_add_product_type(
    description: str | None,
    sku: str | None = None,
) -> str:
    """OnAddLinearClick productType: structural / pipe / tube / bar (not 10/30/40)."""
    text = f" {str(description or '').upper()} {str(sku or '').upper()} "
    compact = text.replace(" ", "")
    if "CHANNEL" in text or re.search(r"C\d+X", compact):
        return LINEAR_ADD_TYPE_STRUCTURAL
    if "ANGLE" in text or re.search(r"L\d", compact) and "X" in compact:
        return LINEAR_ADD_TYPE_STRUCTURAL
    if "PIPE" in text or re.search(r"(^|[^A-Z])P[\d/]", compact):
        return LINEAR_ADD_TYPE_PIPE
    if (
        "TUBE" in text
        or "RT" in compact
        or "RCT" in compact
        or "HSS" in compact
        or "DOM" in compact
    ):
        return LINEAR_ADD_TYPE_TUBE
    if "HOSE GUARD" in text or "HOSEGUARD" in text or " BAR" in text:
        return LINEAR_ADD_TYPE_BAR
    return LINEAR_ADD_TYPE_BAR


def coerce_linear_add_product_type(
    value: Any,
    *,
    name: str = "",
    sku: str = "",
) -> str:
    """Force the proven-script strings. Int 10/30/40 500s on AddItem_Linear."""
    if isinstance(value, str) and value.strip().casefold() in _LINEAR_ADD_TYPES:
        return value.strip().casefold()
    try:
        mapped = _INT_TO_LINEAR_ADD_TYPE.get(int(value))
        if mapped:
            return mapped
    except (TypeError, ValueError):
        pass
    return linear_add_product_type(name, sku=sku)


def overlay_classified_row(
    row: dict[str, Any],
    *,
    category: str,
    material: str | None = None,
    thickness: str | float | None = None,
    product_id: str | None = None,
    sku: str | None = None,
    qty: int | float | None = None,
    machine: str | None = None,
) -> dict[str, Any]:
    """Apply Cad / Linear / Component + SKU/grade onto a CadImport grid row."""
    out = dict(row)
    cat = category if category in {"Cad", "Linear", "Component"} else "Cad"
    out["PartMode"] = part_mode_int(cat)
    out["ItemType"] = cat
    out["Category"] = cat
    if qty is not None:
        out["Qty"] = qty
        out["Quantity"] = qty
    elif _qty_of(out) <= 0:
        out["Qty"] = 1
        out["Quantity"] = 1
    if material:
        out["Material"] = material
        out["MaterialGrade"] = material
    if thickness is not None and str(thickness) != "":
        out["Thickness"] = thickness
        out["Thickness_Units"] = out.get("Thickness_Units") or "inch"
    if product_id:
        out["ProductID"] = product_id
    if sku:
        out["SKU"] = sku
    if cat == "Linear":
        out["IsLinear"] = True
        out["IsPlate"] = False
        out["IsPart"] = True
        out["ProductType"] = linear_website_product_type(
            row_name(out), sku=sku
        )
        out["Machine"] = machine or out.get("Machine") or "Saw"
    elif cat == "Component":
        out["IsLinear"] = False
        out["IsPlate"] = False
        out["IsPart"] = True
        out["Machine"] = machine
    else:
        out["IsLinear"] = False
        out["IsPlate"] = True
        out["IsPart"] = True
        out["ProductType"] = 100
        out["Machine"] = machine or out.get("Machine") or "Laser - Bay1"
        if str(out["Machine"]).casefold() == "laser":
            out["Machine"] = "Laser - Bay1"
    out["ErrorStatus"] = _error_status(out)
    if out.get("Status") in (None, "", 0, "0"):
        out["Status"] = 1
    return out


def row_name(row: dict[str, Any]) -> str:
    for key in ("Name", "PartName", "Description", "FileName"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return ""


_DIM_TOKEN_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:x|X|×)\s*(\d+(?:\.\d+)?)(?:\s*(?:x|X|×)\s*(\d+(?:\.\d+)?))?"
)


def _as_float(val: Any) -> float | None:
    try:
        if val is None or val == "":
            return None
        return float(val)
    except (TypeError, ValueError):
        return None


def score_linear_product(
    product: dict[str, Any],
    *,
    description: str,
    material: str | None,
    dims: list[float] | None = None,
) -> float:
    """Higher is closer. Hose guards prefer Round Bar; tubes prefer Mechanical Tube."""
    text = f" {str(description or '').upper()} "
    pname = str(product.get("ProductName") or "").upper()
    pdesc = str(product.get("ProductDescription") or "").upper()
    shape = str(product.get("ShapeName") or product.get("Category") or "").upper()
    sub = str(product.get("SubCategory") or "").upper()
    grade = str(product.get("MaterialGrade") or product.get("Property") or "").upper()
    blob = f"{pname} {pdesc} {shape} {sub}"
    score = 0.0

    if "HOSE GUARD" in text or "HOSEGUARD" in text:
        if "ROUND BAR" in blob or "RB" in pname:
            score += 40
        elif "TUBE" in blob or "PIPE" in blob:
            score -= 10
    elif any(h in text for h in (" TUBE", " HSS", " PIPE", " DOM")):
        if "TUBE" in blob or "PIPE" in blob:
            score += 30
        if "MECHANICAL TUBE" in blob:
            score += 8
        if pname.startswith("RT") or pname.startswith("RCT") or " RCT" in blob:
            score += 12
        # Prior 1001898 binds of P1/8-5-A36 / P1/4-5-A36 on tubes are suspect.
        if " TUBE" in text and " PIPE" not in text:
            compact_name = pname.replace(" ", "")
            if re.match(r"^P[\d/]", compact_name):
                score -= 25
    elif "ANGLE" in text:
        if "ANGLE" in blob:
            score += 30
    elif "CHANNEL" in text:
        if "CHANNEL" in blob:
            score += 30
    elif "BAR" in text:
        if "BAR" in blob:
            score += 25

    want_grade = (material or "").strip().upper().split()[0] if material else ""
    if want_grade and grade:
        if want_grade == grade or want_grade in grade or grade in want_grade:
            score += 20
        else:
            score -= 8
    elif want_grade == "A36" and not grade:
        score += 4

    want_dims = [d for d in (dims or []) if d and d > 0]
    prod_dims = [
        x
        for x in (
            _as_float(product.get("Dim1")),
            _as_float(product.get("Dim2")),
            _as_float(product.get("Dim3")),
            _as_float(product.get("Dim4")),
        )
        if x and x > 0
    ]
    if want_dims and prod_dims:
        # Closest primary dim (OD / leg / bar diameter).
        best = min(abs(want_dims[0] - p) for p in prod_dims)
        score += max(0.0, 15.0 - best * 20.0)
        if len(want_dims) > 1 and len(prod_dims) > 1:
            best2 = min(abs(want_dims[1] - p) for p in prod_dims)
            score += max(0.0, 8.0 - best2 * 20.0)

    if product.get("Active") is False:
        score -= 50
    return score


def extract_linear_dims(description: str, row: dict[str, Any] | None = None) -> list[float]:
    dims: list[float] = []
    row = row or {}
    for key in ("Dim1", "Dim2", "Thickness", "LinearWidth"):
        val = _as_float(row.get(key))
        if val and val > 0:
            dims.append(val)
    text = str(description or "")
    m = _DIM_TOKEN_RE.search(text.replace('"', "").replace("″", ""))
    if m:
        for g in m.groups():
            if not g:
                continue
            try:
                dims.append(float(g))
            except ValueError:
                pass
    # Fraction OD like 3/8 on hose guards.
    frac = re.search(r"\b(\d+)\s*/\s*(\d+)\b", text)
    if frac:
        try:
            dims.append(int(frac.group(1)) / int(frac.group(2)))
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    # unique preserve order
    seen: set[float] = set()
    out: list[float] = []
    for d in dims:
        key = round(d, 4)
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def pick_closest_linear_product(
    products: list[dict[str, Any]],
    *,
    description: str,
    material: str | None = None,
    row: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (product, mismatch_note)."""
    if not products:
        return None, "No linear ProductID catalog available"
    dims = extract_linear_dims(description, row)
    ranked = sorted(
        products,
        key=lambda p: score_linear_product(
            p, description=description, material=material, dims=dims
        ),
        reverse=True,
    )
    best = ranked[0]
    best_score = score_linear_product(
        best, description=description, material=material, dims=dims
    )
    if best_score < 8:
        return best, (
            f"Closest linear SKU {best.get('ProductName') or best.get('ID')} "
            f"is a weak match for {description!r} — confirm ProductID in SecturaFAB"
        )
    want_grade = (material or "").strip().upper().split()[0] if material else ""
    got_grade = str(best.get("MaterialGrade") or "").upper()
    note = None
    if want_grade and got_grade and want_grade not in got_grade and got_grade not in want_grade:
        note = (
            f"Linear grade mismatch: drawing {want_grade} vs SKU "
            f"{best.get('ProductName')} ({got_grade})"
        )
    return best, note
