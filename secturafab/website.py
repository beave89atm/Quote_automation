"""SecturaFAB website MVC helpers — Kyle's CAD Files / Finish / Long / Nest path.

Recovered from QuoteOrderEdit JS (not in public OpenAPI). controllerName = '/Quote'.

  GET  /Quote/GetItem_AddView?ID={quoteId}&ItemType=dxf
  POST /Attachment/UploadItem_PDFFiles  (Image Files plates — not CadImport)
  POST /CadImport/UploadItem_DXFFiles   (STEP / DXF CAD Files only)
  GET  /CadImport/Data
  POST /CadImport/UpdateData, UpdateDataNext, SetPartMode, SetUnits, ConvertTo
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

import re
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

WEBSITE_AUTH_GAP = (
    "Finish needs SECTURA_WEBSITE_COOKIE (env or file) from the signed-in "
    "www.secturafab.com Chrome on this Linux box. "
    "Do not paste a cookie. Do not unwrap Windows Chrome. "
    "Do not use Kyle's quoting PC. "
    "GET /Quote/GetItem_AddView and POST /Quote/AddItem_DXFFiles, "
    "AddItem_PDFFiles, and AddItem_Linear 302 to /Account/Login or hit "
    "Cloudflare without that session. Do not fall back to quickAddCAD. "
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


def filelist_from_cadimport_upload(payload: Any) -> list[dict[str, Any]]:
    """Rows from POST /CadImport/UploadItem_DXFFiles (status=OK, List=[...])."""
    if isinstance(payload, list):
        return [dict(r) for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("List", "FileList", "Data", "Result"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [dict(r) for r in rows if isinstance(r, dict)]
    return []


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
    Proven Image Files FileList uses ItemType=cad, Machine=Laser, Status>0.
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
        out["Machine"] = "Laser"
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
    """GetPDFData() field bag after New Line Item fields are filled."""
    src = prepare_pdf_newline_fields(row)
    slim: dict[str, Any] = {}
    for key in PDF_GETDATA_FIELDS:
        slim[key] = src[key] if key in src and src[key] is not None else ""
    return slim


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
    """FileList row after POST /Attachment/UploadItem_PDFFiles (not CadImport)."""
    src = _first_upload_row(payload)
    file_id = src.get("FileID") or src.get("ID") or src.get("ImageID") or ""
    image_id = src.get("ImageID") or file_id
    length = length if length not in (None, "") else (
        src.get("Length") or src.get("Stock_Y")
    )
    width = width if width not in (None, "") else (
        src.get("Width") or src.get("Stock_X")
    )
    thickness = thickness if thickness not in (None, "") else src.get("Thickness")
    return prepare_pdf_newline_fields(
        {
            "Status": 1,
            "ItemType": "cad",
            "ItemID": EMPTY_GUID,
            "FileID": file_id,
            "ImageID": image_id,
            "FileName": file_name or src.get("FileName") or "",
            "PartName": part_name,
            "Description": description or part_name,
            "Qty": max(1, int(qty or 1)),
            "Machine": "Laser",
            "Material": material or "A36",
            "Thickness": thickness,
            "Thickness_Units": "inch",
            "Length": length,
            "Length_Units": "inch",
            "Width": width,
            "Width_Units": "inch",
            "ProductType": 100,
        }
    )


def attachment_pdf_filelist_ready(row: dict[str, Any] | None) -> bool:
    """True only when Image Files New Line Item fields are present."""
    if not isinstance(row, dict):
        return False
    if str(row.get("ItemType") or "").strip().casefold() != "cad":
        return False
    try:
        thickness = float(row.get("Thickness") or 0)
        length = float(row.get("Length") or 0)
        width = float(row.get("Width") or 0)
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
    """Rows from /Product/Read_DataLinearlookup or a catalog product.Configs."""
    rows = quote_item_rows(payload)
    if rows:
        return rows
    if isinstance(payload, dict):
        for key in ("Configs", "ProductConfigList", "ProductConfigs", "List"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return [r for r in inner if isinstance(r, dict)]
    return []


def _linear_config_guid(row: dict[str, Any]) -> str | None:
    """Config GUID from a Read_DataLinearlookup row (Value, not only ID)."""
    product_id = str(row.get("ProductID") or row.get("productID") or "")
    for key in (
        "Value",
        "ProductConfigID",
        "ConfigID",
        "ConfigValue",
        "Key",
        "ID",
    ):
        val = row.get(key)
        if not is_tenant_guid(val):
            continue
        if product_id and str(val) == product_id:
            continue
        return str(val)
    for key, val in row.items():
        if key in {"ProductID", "productID", "ID"}:
            continue
        if is_tenant_guid(val) and str(val) != product_id:
            return str(val)
    return None


def pick_linear_config_id(
    rows: list[dict[str, Any]] | None,
    *,
    product_id: str | None = None,
) -> str | None:
    """Prefer the 20ft/21ft stock config GUID. Empty GUID is never a bind."""
    wanted = str(product_id or "").strip()
    pool = [r for r in (rows or []) if isinstance(r, dict)]
    if wanted:
        matched = [
            r
            for r in pool
            if str(r.get("ProductID") or r.get("productID") or "") == wanted
        ]
        if matched:
            pool = matched
    ranked: list[tuple[float, str]] = []
    for row in pool:
        if not isinstance(row, dict):
            continue
        cid = _linear_config_guid(row)
        if not cid:
            continue
        label = " ".join(
            str(row.get(k) or "")
            for k in ("Name", "Text", "Display", "Description", "Length", "StockLength")
        )
        feet = None
        match = _FT_RE.search(label)
        if match:
            try:
                feet = float(match.group(1))
            except (TypeError, ValueError):
                feet = None
        score = 10.0
        if feet in (20.0, 21.0):
            score = 100.0
        elif feet:
            score = 20.0
        ranked.append((score, str(cid)))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def linear_bind_fields(
    product: dict[str, Any] | None,
    configs: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """productID + productConfigID + subtype/dims/weightLength for AddItem_Linear."""
    if not isinstance(product, dict):
        return None
    pid = product.get("ID") or product.get("ProductID")
    if not is_tenant_guid(pid):
        return None
    nested = list(configs or [])
    if not nested:
        nested = linear_lookup_rows(product)
    cfg = pick_linear_config_id(nested, product_id=str(pid) if pid else None)
    if not cfg:
        return None
    sku = str(
        product.get("ProductName")
        or product.get("SKU")
        or product.get("ProductCode")
        or ""
    )
    subtype = str(
        product.get("ProductSubType") or product.get("productSubType") or ""
    ).strip()
    if not subtype:
        pt = linear_website_product_type(sku or str(product.get("Name") or ""))
        subtype = {10: "bar", 30: "tube", 40: "angle"}.get(int(pt), "tube")
    def _dim(n: int) -> Any:
        return product.get(f"Dim{n}") or product.get(f"dim{n}") or 0

    return {
        "productID": str(pid),
        "productConfigID": cfg,
        "productSubType": subtype,
        "dim1": _dim(1),
        "dim1_Unit": product.get("Dim1_Unit") or product.get("dim1_Unit") or "inch",
        "dim2": _dim(2),
        "dim2_Unit": product.get("Dim2_Unit") or product.get("dim2_Unit") or "inch",
        "dim3": _dim(3),
        "dim3_Unit": product.get("Dim3_Unit") or product.get("dim3_Unit") or "inch",
        "dim4": _dim(4),
        "dim4_Unit": product.get("Dim4_Unit") or product.get("dim4_Unit") or "inch",
        "weightLength": product.get("WeightLength") or product.get("weightLength") or 0,
        "weightLength_Units": (
            product.get("WeightLength_Unit")
            or product.get("weightLength_Units")
            or "pound/foot"
        ),
        "sku": sku or None,
    }


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
    rows = [
        slim_pdf_grid_row(r)
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
    payload["productType"] = linear_website_product_type(name)
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
    if not is_tenant_guid(payload.get("productConfigID")):
        raise ValueError(
            "AddItem_Linear requires a tenant productConfigID from "
            "/Product/Read_DataLinearlookup (empty GUID 500s)"
        )
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
    """Website Long ProductType: 10 bar, 30 tube, 40 angle/channel."""
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
