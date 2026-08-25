"""SecturaFAB website MVC helpers — Kyle's CAD Files / Finish / Long / Nest path.

Recovered from QuoteOrderEdit JS (not in public OpenAPI). controllerName = '/Quote'.

  GET  /Quote/GetItem_AddView?ID={quoteId}&ItemType=dxf
  POST /CadImport/UploadItem_DXFFiles
  GET  /CadImport/Data
  POST /CadImport/UpdateData, UpdateDataNext, SetPartMode, SetUnits, ConvertTo
  POST /Quote/AddItem_DXFFiles   data { ID, ItemID, customerMaterial, FileList }
  POST /Quote/AddItem_PDFFiles   (Image Files Finish)
  POST /Quote/AddItem_Linear     (Long)
  POST /Quote/NestQuote_Edit
  POST /Quote/NestQuoteMultiPart_Renest

FileList = #gridDXFParts rows with ErrorStatus===0 and Qty>0.
Finish writes Primary Costs (Laser/Drafting/… under PR; Saw + Saw Setup
under the linear calculator). Cookie-less addplate / addLinear do the same
writes GET reads. Do not graft those names as item-level OperationName tags.
"""

from __future__ import annotations

import re
from typing import Any

EMPTY_GUID = "00000000-0000-0000-0000-000000000000"

# SetPartMode requires an integer (strings 500). Verified 0..4 HTTP 200 on empty guid.
# Mapping follows Kyle UI categories + Q10056 ProductType (100 Cad, 10/30 Linear, 200 Component).
PART_MODE_CAD = 0
PART_MODE_LINEAR = 1
PART_MODE_COMPONENT = 2

PART_MODE_BY_CATEGORY = {
    "Cad": PART_MODE_CAD,
    "Linear": PART_MODE_LINEAR,
    "Component": PART_MODE_COMPONENT,
}

WEBSITE_FINISH_PATHS = {
    "get_item_add_view": "/Quote/GetItem_AddView",
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
    "nest_quote_edit": "/Quote/NestQuote_Edit",
    "nest_quote_renest": "/Quote/NestQuoteMultiPart_Renest",
}

WEBSITE_AUTH_GAP = (
    "Website session required for /Quote/AddItem_DXFFiles (CAD Files Finish). "
    "GetItem_AddView / AddItem_DXFFiles redirect to /Account/Login without a "
    "www cookie. Image Files (AddItem_PDFFiles) and Long (AddItem_Linear) are "
    "called with the API bearer (same as CadImport); if they 302, cookie-less "
    "addplate / addLinear fill MaterialCost and let the calculator write "
    "Primary Costs. Do not graft Laser/Drafting/Saw Setup as item tags. "
    "Set SECTURAFAB_WEBSITE_COOKIE only for DXF Finish."
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
    """Keep the Finish field bag; pass through extra Linear* / grid keys."""
    slim: dict[str, Any] = {}
    for key, val in row.items():
        if key in FILELIST_FIELDS or key.startswith("Linear") or key.startswith("Dim"):
            slim[key] = val
    if "Qty" not in slim and "Quantity" in slim:
        slim["Qty"] = slim["Quantity"]
    if "Quantity" not in slim and "Qty" in slim:
        slim["Quantity"] = slim["Qty"]
    return slim


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


def build_pdf_finish_payload(
    quote_id: str,
    file_list: list[dict[str, Any]],
    *,
    item_id: str | None = None,
    customer_material: bool = False,
) -> dict[str, Any]:
    """POST /Quote/AddItem_PDFFiles (OnAddPDFClick) — same ID / ItemID / FileList bag."""
    return build_dxf_finish_payload(
        quote_id,
        file_list,
        item_id=item_id,
        customer_material=customer_material,
    )


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
    """POST /Quote/AddItem_Linear (Long) — website form bag."""
    payload: dict[str, Any] = {
        "ID": quote_id,
        "ItemID": item_id or EMPTY_GUID,
        "ProductID": product_id,
        "productID": product_id,
        "Qty": max(1, int(qty)),
        "qty": max(1, int(qty)),
        "Machine": machine,
        "machine": machine,
        "customerMaterial": bool(customer_material),
    }
    if length is not None:
        payload["Length"] = length
        payload["length"] = length
        payload["length_unit"] = "inch"
    if material:
        payload["Material"] = material
        payload["material"] = material
    if name:
        payload["Name"] = name
        payload["name"] = name
    if extra:
        payload.update(extra)
    return payload


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
        out["Machine"] = machine or out.get("Machine") or "Laser"
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
