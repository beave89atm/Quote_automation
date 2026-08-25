"""Kyle New Line Item / Long calculator packs (not grafted Profile + DataPart).

Image Files (``AddItem_PDFFiles``) and Long (``AddItem_Linear``) stamp these
packs when the MVC route accepts the API bearer. Cookie-less v1/quote
``New Line Item`` POSTs the same shop calculators with sane default times —
never DataPart page-outline cut time (22×28 → 3h+).
"""

from __future__ import annotations

import copy
import re
import uuid
from pathlib import Path
from typing import Any

# Kyle UI New Line Item (21678-1 class). Times are hours; none are 0 or 3h+.
# Source minutes: Laser 1.97, Drafting 3, Laser-Setup 10, Sheet Loading 3, Deburr 2.
_CAD_NEW_LINE_TEMPLATES: list[dict[str, Any]] = [
    {
        "OperationName": "Laser",
        "Operation": "Laser",
        "OperationLabel": "Laser",
        "CalculatorName": "Laser",
        "CostCategory": "Laser-CO2",
        "Equipment": "Laser",
        "Machine": "Laser",
        "PrimaryOperation": True,
        "CostType": 1,
        "CostCalcType": 4,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "LabourRate": 200.0,
        "UnitTime": 1.97 / 60.0,
        "Value": 1.97 / 60.0,
        "Time": 1.97 / 60.0,
        "ValueUnits": "hour",
        "SortSequence": 1,
    },
    {
        "OperationName": "Drafting",
        "Operation": "Drafting",
        "OperationLabel": "Drafting",
        "CalculatorName": "Drafting",
        "CostCategory": "Drafting",
        "Equipment": "Laser",
        "Machine": "",
        "PrimaryOperation": False,
        "CostType": 1,
        "CostCalcType": 6,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "LabourRate": 65.0,
        "UnitTime": 3.0 / 60.0,
        "Value": 3.0 / 60.0,
        "Time": 3.0 / 60.0,
        "ValueUnits": "hour",
        "SortSequence": 2,
    },
    {
        "OperationName": "Laser-Setup",
        "Operation": "Laser-Setup",
        "OperationLabel": "Laser-Setup",
        "CalculatorName": "Laser-Setup",
        "CostCategory": "Laser-CO2-Setup",
        "Equipment": "Laser",
        "Machine": "",
        "PrimaryOperation": False,
        "CostType": 1,
        "CostCalcType": 6,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "LabourRate": 200.0,
        "UnitTime": 10.0 / 60.0,
        "Value": 10.0 / 60.0,
        "Time": 10.0 / 60.0,
        "ValueUnits": "hour",
        "SortSequence": 3,
    },
    {
        "OperationName": "Sheet Loading",
        "Operation": "Sheet Loading",
        "OperationLabel": "Sheet Loading",
        "CalculatorName": "Sheet Loading",
        "CostCategory": "Laser-CO2-Setup",
        "Equipment": "Laser",
        "Machine": "",
        "PrimaryOperation": False,
        "CostType": 1,
        "CostCalcType": 14,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "LabourRate": 200.0,
        "UnitTime": 3.0 / 60.0,
        "Value": 3.0 / 60.0,
        "Time": 3.0 / 60.0,
        "ValueUnits": "hour",
        "SortSequence": 4,
    },
    {
        "OperationName": "Deburr",
        "Operation": "Deburr",
        "OperationLabel": "Deburr",
        "CalculatorName": "Deburr",
        "CostCategory": "Laser-CO2",
        "Equipment": "Deburr",
        "Machine": "Deburr",
        "PrimaryOperation": False,
        "CostType": 1,
        "CostCalcType": 19,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "LabourRate": 200.0,
        "UnitTime": 2.0 / 60.0,
        "Value": 2.0 / 60.0,
        "Time": 2.0 / 60.0,
        "ValueUnits": "hour",
        "SortSequence": 5,
    },
]

# Long / AddItem_Linear stamps Saw + Saw Setup (Q10056). Hours, not 0.
_LINEAR_NEW_LINE_TEMPLATES: list[dict[str, Any]] = [
    {
        "OperationName": "Saw",
        "Operation": "Saw",
        "OperationLabel": "Saw",
        "CalculatorName": "Saw",
        "CostCategory": "Saw",
        "Equipment": "Saw",
        "Machine": "Saw",
        "PrimaryOperation": True,
        "CostType": 1,
        "CostCalcType": 4,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "LabourRate": 80.0,
        "UnitTime": 3.0 / 60.0,
        "Value": 3.0 / 60.0,
        "Time": 3.0 / 60.0,
        "ValueUnits": "hour",
        "SortSequence": 1,
    },
    {
        "OperationName": "Saw Setup",
        "Operation": "Saw Setup",
        "OperationLabel": "Saw Setup",
        "CalculatorName": "Saw Setup",
        "CostCategory": "Saw-Setup",
        "Equipment": "Saw",
        "Machine": "Saw",
        "PrimaryOperation": False,
        "CostType": 1,
        "CostCalcType": 6,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "LabourRate": 80.0,
        "UnitTime": 5.0 / 60.0,
        "Value": 5.0 / 60.0,
        "Time": 5.0 / 60.0,
        "ValueUnits": "hour",
        "SortSequence": 2,
    },
]

_SHARED_OP_DEFAULTS: dict[str, Any] = {
    "OperationType": 0,
    "Margin": 0.0,
    "Multiplier": 1.0,
    "ApplyMargin": True,
    "Burden": 0.0,
    "SequanceNumber": 1,
    "InputSequence": 1,
    "InputType": 0,
    "Quantity": 1,
    "MasterQuantity": 1,
    "HasMinPrice": False,
    "Outsource": False,
    "UsesLocalLabourRate": False,
    "UsesLocalMargin": False,
    "UsesLocalMultiplier": False,
    "UsesLocalPrice": False,
    "UsesLocalValue": False,
    "MinimumCost": 0.0,
    "MinimumPrice": 0.0,
    "MinUnitPrice": 0.0,
    "UnitCost": 0.0,
    "UnitPrice": 0.0,
    "LeadTime": 0.0,
    "Memo": "",
    "Description": "",
    "PriceBookName": "",
    "Outsource_OperationCode": "",
    "OutsourceUnitCost": 0.0,
    "OutsourceUnitPrice": 0.0,
    "ProcessLocation": "Bay1",
}


def cad_new_line_calculators() -> list[str]:
    return [str(t["CalculatorName"]) for t in _CAD_NEW_LINE_TEMPLATES]


def linear_new_line_calculators() -> list[str]:
    return [str(t["CalculatorName"]) for t in _LINEAR_NEW_LINE_TEMPLATES]


def _instantiate(templates: list[dict[str, Any]], item_id: str | None) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    for tmpl in templates:
        op = dict(_SHARED_OP_DEFAULTS)
        op.update(copy.deepcopy(tmpl))
        op["ID"] = str(uuid.uuid4())
        op["QuoteOperationID"] = str(uuid.uuid4())
        if item_id:
            op["ItemID"] = item_id
        ops.append(op)
    return ops


def build_cad_new_line_ops(item_id: str | None = None) -> list[dict[str, Any]]:
    """Laser + Deburr + Laser-Setup + Sheet Loading (+ Drafting). Not Profile."""
    return _instantiate(_CAD_NEW_LINE_TEMPLATES, item_id)


def build_linear_new_line_ops(item_id: str | None = None) -> list[dict[str, Any]]:
    """Saw + Saw Setup from the Long / New Line Item path."""
    return _instantiate(_LINEAR_NEW_LINE_TEMPLATES, item_id)


def _op_text(op: dict[str, Any]) -> str:
    return " ".join(
        str(op.get(k) or "")
        for k in (
            "CalculatorName",
            "OperationName",
            "Operation",
            "CostCategory",
            "OperationLabel",
        )
    ).lower()


def item_has_laser_pack(item: dict[str, Any] | None) -> bool:
    ops = list((item or {}).get("OperationCostList") or [])
    blob = " ".join(_op_text(o) if isinstance(o, dict) else "" for o in ops)
    return (
        "laser" in blob
        and "deburr" in blob
        and ("setup" in blob)
        and ("sheet" in blob and "load" in blob)
    )


def item_has_saw_pack(item: dict[str, Any] | None) -> bool:
    ops = list((item or {}).get("OperationCostList") or [])
    names = [_op_text(o) if isinstance(o, dict) else "" for o in ops]
    has_saw = any("saw" in n and "setup" not in n for n in names)
    has_setup = any("saw" in n and "setup" in n for n in names)
    return has_saw and has_setup


def apply_cad_new_line_ops(item: dict[str, Any]) -> bool:
    """Attach the New Line Item laser pack when missing. Returns True if written."""
    if item_has_laser_pack(item):
        return False
    item_id = str(item.get("ID") or "") or None
    ops = build_cad_new_line_ops(item_id)
    item["OperationCostList"] = ops
    laser_h = next(
        (float(o.get("UnitTime") or 0) for o in ops if o.get("CalculatorName") == "Laser"),
        1.97 / 60.0,
    )
    item["PrimaryTime"] = laser_h
    item["UnitPrimaryTime"] = laser_h
    item["Machine"] = item.get("Machine") or "Laser"
    return True


def apply_linear_new_line_ops(item: dict[str, Any]) -> bool:
    """Attach Long Saw + Saw Setup when missing. Returns True if written."""
    if item_has_saw_pack(item):
        return False
    item_id = str(item.get("ID") or "") or None
    ops = build_linear_new_line_ops(item_id)
    item["OperationCostList"] = ops
    saw_h = next(
        (float(o.get("UnitTime") or 0) for o in ops if o.get("CalculatorName") == "Saw"),
        3.0 / 60.0,
    )
    item["PrimaryTime"] = saw_h
    item["UnitPrimaryTime"] = saw_h
    item["Machine"] = "Saw"
    return True


def _is_assembly(item: dict[str, Any]) -> bool:
    return bool(
        item.get("IsAssembly")
        or item.get("ProductType") in (300, "300", "assembly")
    )


def _is_linear(item: dict[str, Any]) -> bool:
    if _is_assembly(item):
        return False
    if item.get("ProductType") in (100, "100", 200, "200"):
        return False
    cat = str(item.get("Category") or item.get("ItemType") or "").strip()
    if item.get("IsLinear") or cat == "Linear" or item.get("ProductType") in (10, "10"):
        return True
    return cat.lower() in {"pipe", "tube", "bar", "structural"}


def _is_component(item: dict[str, Any]) -> bool:
    if _is_assembly(item) or _is_linear(item):
        return False
    cat = str(item.get("Category") or item.get("ItemType") or "").strip()
    return cat == "Component" or item.get("ProductType") in (200, "200")


def stamp_new_line_item_packs(client: Any, quote_id: str) -> list[str]:
    """
    Cookie-less fallback: v1/quote New Line Item packs on Cad / Linear lines.

    Does not graft Profile or read DataPart. Skips lines that already have
    Image Files / Long packs.
    """
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    cad_n = 0
    lin_n = 0
    for it in items:
        if not isinstance(it, dict) or _is_assembly(it) or _is_component(it):
            continue
        if _is_linear(it):
            if apply_linear_new_line_ops(it):
                lin_n += 1
            continue
        if apply_cad_new_line_ops(it):
            cad_n += 1
    if not cad_n and not lin_n:
        return []
    detail["ItemList"] = items
    save = client.request("POST", "v1/quote", json=detail)
    try:
        status = int(getattr(save, "status_code", 200) or 200)
    except (TypeError, ValueError):
        status = 200
    if status >= 400:
        return [f"WARNING: New Line Item pack save failed ({save.status_code})"]
    bits = []
    if cad_n:
        bits.append(f"{cad_n} Cad Laser/Deburr/Setup/Sheet Loading")
    if lin_n:
        bits.append(f"{lin_n} Linear Saw + Saw Setup")
    return [
        "New Line Item stamped "
        + " and ".join(bits)
        + " (Image Files / Long bearer fallback; not grafted Profile)"
    ]


_INCH_NUM = r"(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
_LG_RE = re.compile(
    rf"(?i)(?:^|[x×\s,;])\s*{_INCH_NUM}\s*(?:\"|″|in(?:ch(?:es)?)?)?\s*L\s*G\.?"
)
_LG_AFTER_RE = re.compile(
    rf"(?i)L\s*G\.?\s*[:=]?\s*{_INCH_NUM}"
)
_LENGTH_PHRASE_RE = re.compile(
    rf"(?i)(?:cut\s*length|overall(?:\s*length)?|o\.?a\.?l\.?|length)"
    rf"\s*[:=]?\s*{_INCH_NUM}\s*(?:\"|″|in(?:ch(?:es)?)?)?"
)
_LONG_RE = re.compile(
    rf"(?i){_INCH_NUM}\s*(?:\"|″|in(?:ch(?:es)?)?)?\s*LONG\b"
)


def _inch_token_to_float(raw: str | None) -> float | None:
    text = re.sub(r"\s+", " ", str(raw or "")).strip()
    if not text:
        return None
    if " " in text and "/" in text:
        whole, frac = text.split(" ", 1)
        num, den = frac.split("/", 1)
        try:
            val = float(whole) + float(num) / float(den)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return val if val > 0 else None
    if "/" in text:
        num, den = text.split("/", 1)
        try:
            val = float(num) / float(den)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return val if val > 0 else None
    try:
        val = float(text)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def _sane_cut_length(val: float | None) -> float | None:
    if val is None or val <= 0:
        return None
    if val < 0.5 or val > 600:
        return None
    return float(val)


def parse_length_lg(text: str | None) -> float | None:
    """``91 1/8 LG.`` / ``X 4 LG`` / ``LG. 12`` → inches."""
    if not text:
        return None
    for rx in (_LG_RE, _LG_AFTER_RE):
        m = rx.search(str(text))
        if not m:
            continue
        val = _inch_token_to_float(m.group(1))
        if val:
            return val
    return None


def parse_cut_length(text: str | None) -> float | None:
    """Cut length from ``LG.`` / LENGTH / OAL / CUT LENGTH / LONG (not plate dims)."""
    got = _sane_cut_length(parse_length_lg(text))
    if got:
        return got
    if not text:
        return None
    for rx in (_LENGTH_PHRASE_RE, _LONG_RE):
        m = rx.search(str(text))
        if not m:
            continue
        got = _sane_cut_length(_inch_token_to_float(m.group(1)))
        if got:
            return got
    return None


def _length_near_part(text: str | None, part_no: str | None) -> float | None:
    blob = str(text or "")
    pn = str(part_no or "").strip()
    if not blob or not pn:
        return None
    tokens = [pn]
    if "-" in pn:
        base = pn.rsplit("-", 1)[0]
        if len(base) >= 4:
            tokens.append(base)
    for token in tokens:
        for m in re.finditer(re.escape(token), blob, re.I):
            window = blob[max(0, m.start() - 24) : m.end() + 200]
            got = parse_cut_length(window)
            if got:
                return got
    return None


def _drawing_text(pdf: Path) -> str:
    try:
        from quote_core.weight import _read_pdf_text

        text = _read_pdf_text(pdf) or ""
    except Exception:  # noqa: BLE001
        text = ""
    if parse_cut_length(text):
        return text
    try:
        from quote_core.ocr import ocr_pdf_pages

        ocr = ocr_pdf_pages(pdf, max_pages=2, dpi=180, only_when_sparse=False)
        extra = str((ocr or {}).get("text") or "")
    except Exception:  # noqa: BLE001
        extra = ""
    if extra:
        return f"{text}\n{extra}" if text else extra
    return text


def _item_cut_length(item: dict[str, Any] | None) -> float | None:
    """Cut length only — never Dim1 (that is profile size, e.g. 4x4 HSS)."""
    item = item or {}
    for key in ("Length", "FlatLength", "LinearLength"):
        try:
            val = float(item.get(key))
        except (TypeError, ValueError):
            continue
        if val > 0.05:
            return val
    return None


def _length_from_library(
    part_no: str,
    *,
    library_folder: Any = None,
    related_pdf_names: list[str] | None = None,
    extra_pdfs: list[Any] | None = None,
) -> float | None:
    if not part_no:
        return None
    try:
        from secturafab.pdf_assembly_ops import resolve_component_pdf
    except Exception:  # noqa: BLE001
        resolve_component_pdf = None  # type: ignore[assignment]
    component = None
    if resolve_component_pdf and library_folder:
        try:
            component = resolve_component_pdf(
                part_no,
                library_folder=library_folder,
                related_pdf_names=related_pdf_names,
            )
        except Exception:  # noqa: BLE001
            component = None
    if component:
        text = _drawing_text(Path(component))
        got = parse_cut_length(text) or _length_near_part(text, part_no)
        if got:
            return got
    seen: set[str] = set()
    if component:
        seen.add(str(Path(component).resolve()).lower())
    for raw in extra_pdfs or []:
        try:
            path = Path(raw)
        except TypeError:
            continue
        if not path.is_file():
            continue
        key = str(path.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        text = _drawing_text(path)
        got = _length_near_part(text, part_no)
        if got:
            return got
    return None


def _cad_fields_on_get(item: dict[str, Any]) -> bool:
    mat = str(item.get("Material") or item.get("MaterialGrade") or "").strip()
    try:
        thk_ok = float(item.get("Thickness") or 0) > 0
    except (TypeError, ValueError):
        thk_ok = bool(str(item.get("Thickness") or item.get("ThicknessDisp") or "").strip())
    return bool(mat) and thk_ok


def _linear_fields_on_get(item: dict[str, Any]) -> bool:
    machine = str(item.get("Machine") or "").strip().casefold() == "saw"
    try:
        length = float(item.get("Length") or item.get("LinearLength") or 0)
    except (TypeError, ValueError):
        length = 0.0
    return machine and length > 0


def persist_classified_item_fields(
    client: Any,
    quote_id: str,
    *,
    bom_rows: list[dict[str, Any]] | None = None,
    part_materials: dict | None = None,
    default_material: str = "A36",
    default_thickness: str | None = "0.25",
    library_folder: Any = None,
    related_pdf_names: list[str] | None = None,
    extra_pdfs: list[Any] | None = None,
    plate_catalog: list[dict[str, Any]] | None = None,
    linear_catalog: list[dict[str, Any]] | None = None,
    persist_cad: bool = True,
    persist_linear: bool = True,
    retry_linear: bool = False,
) -> list[str]:
    """Persist Cad/Linear fields on the APIs a live GET actually reads.

    New Line items have no DataPart, so ``UpdateItem_Part`` / ``v1/quote`` POST
    and ``quoteOnline/update`` of Material/Thickness/Machine/Length are no-ops
    (HTTP 200, GET still empty). Bind tenant products instead:

    * Cad: ``POST v1/quoteOnline/addplate`` (PL1/4-A36 class)
    * Linear: in-place ``POST v1/quoteOnline/addLinear`` on the existing itemID
      (Machine=Saw, cut Length from drawing / ``LG.`` / component PDF)

    Success is a follow-up GET — never a 200 on the write. Linear should run
    *after* ``stamp_new_line_item_packs`` so a full-quote POST cannot wipe it.
    """
    from quote_core.part_materials import lookup_part_material

    from secturafab.item_desc import (
        format_component_line,
        format_linear_description,
        is_catalog_part_no,
        item_flat_dims,
        match_bom_part_no,
        parse_cad_desc_fields,
    )
    from secturafab.linear_ops import (
        fetch_linear_catalog,
        fetch_linear_product,
        match_linear_product,
        product_from_bound_item,
        update_linear_via_api,
    )
    from secturafab.plate_ops import addplate_item, fetch_plate_catalog, match_plate_product
    from secturafab.push import classify_sectura_item
    from secturafab.qty_ops import normalize_part_key
    from secturafab.quote_update import quote_online_update

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    bom_desc: dict[str, str] = {}
    bom_qty: dict[str, int] = {}
    for row in bom_rows or []:
        pn = str(row.get("part_no") or row.get("part_number") or "").strip()
        key = normalize_part_key(pn)
        if not key:
            continue
        bom_desc[key] = str(row.get("description") or "")
        try:
            bom_qty[key] = max(1, int(row.get("qty") or 1))
        except (TypeError, ValueError):
            bom_qty[key] = 1
    plates = (
        (list(plate_catalog) if plate_catalog is not None else fetch_plate_catalog(client))
        if persist_cad
        else []
    )
    linears = (
        (list(linear_catalog) if linear_catalog is not None else fetch_linear_catalog(client))
        if persist_linear
        else []
    )
    notes: list[str] = []
    update_params: list[dict[str, Any]] = []
    cad_wrote = 0
    lin_wrote = 0
    desc_n = 0
    linear_plans: dict[str, tuple[dict[str, Any], float, str, int]] = {}

    def _resolve_linear_product(
        it: dict[str, Any],
        *,
        pid: str | None,
        sku: str | None,
        hint: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        product = None
        if pid:
            product = next(
                (p for p in linears if str(p.get("ID") or "") == pid),
                None,
            )
            if product is None:
                product = fetch_linear_product(client, pid)
        if product is None:
            new_pid, new_sku, _mismatch = match_linear_product(
                linears, hint, material=default_material, row=it
            )
            pid = new_pid or pid
            sku = new_sku or sku
            if pid:
                product = next(
                    (p for p in linears if str(p.get("ID") or "") == pid),
                    None,
                ) or fetch_linear_product(client, pid)
        if product is None:
            product = product_from_bound_item(it)
        return product, sku

    def _write_linear(
        it: dict[str, Any],
        *,
        iid: str,
        pn: str,
        noun: str,
        raw_desc: str,
        qty: int,
    ) -> None:
        nonlocal lin_wrote, desc_n
        length = (
            _item_cut_length(it)
            or parse_cut_length(noun)
            or parse_cut_length(raw_desc)
            or _length_from_library(
                pn or "",
                library_folder=library_folder,
                related_pdf_names=related_pdf_names,
                extra_pdfs=extra_pdfs,
            )
        )
        sku = str(it.get("SKU") or "").strip() or None
        pid = str(it.get("ProductID") or "").strip() or None
        hint = f"{pn or ''} {noun} {raw_desc}".strip()
        product, sku = _resolve_linear_product(it, pid=pid, sku=sku, hint=hint or raw_desc)
        if product:
            sku = sku or str(
                product.get("ProductName") or product.get("SKU") or ""
            ).strip() or None
        line = raw_desc
        if pn:
            line = format_linear_description(
                pn, sku=sku, length_in=length, noun=noun
            )
        if iid and product and length and length > 0:
            linear_plans[iid] = (product, float(length), line or raw_desc, qty)
            if update_linear_via_api(
                client,
                quote_id,
                iid,
                product,
                length_in=float(length),
                qty=qty,
                name=line or raw_desc,
            ):
                lin_wrote += 1
        elif iid and line and line != raw_desc:
            update_params.append(
                {"ID": iid, "ParamName": "Description", "Value": line[:500]}
            )
            desc_n += 1

    for it in items:
        if not isinstance(it, dict) or _is_assembly(it):
            continue
        iid = str(it.get("ID") or "")
        raw_desc = str(it.get("Description") or "")
        pn = match_bom_part_no(raw_desc, bom_rows)
        if not pn and is_catalog_part_no(raw_desc.split()[0] if raw_desc.split() else ""):
            pn = raw_desc.split()[0].rstrip(".,;:")
        noun = bom_desc.get(normalize_part_key(pn or ""), "")
        want_cat = classify_sectura_item(f"{pn or ''} {noun} {raw_desc}")
        qty = bom_qty.get(normalize_part_key(pn or ""), 1)
        if persist_cad and (_is_component(it) or want_cat == "Component"):
            line = format_component_line(pn or "", noun or raw_desc)
            if iid and it.get("ProductType") not in (200, "200"):
                update_params.append({"ID": iid, "ParamName": "ProductType", "Value": "200"})
                update_params.append({"ID": iid, "ParamName": "Category", "Value": "Component"})
                update_params.append({"ID": iid, "ParamName": "ItemType", "Value": "Component"})
            if line and line != raw_desc and iid:
                it["Description"] = line[:500]
                update_params.append({"ID": iid, "ParamName": "Description", "Value": line[:500]})
                desc_n += 1
            continue
        if persist_linear and (_is_linear(it) or want_cat == "Linear"):
            _write_linear(
                it, iid=iid, pn=pn or "", noun=noun, raw_desc=raw_desc, qty=qty
            )
            continue
        if not persist_cad:
            continue
        if _is_linear(it) or want_cat == "Linear" or _is_component(it) or want_cat == "Component":
            continue
        parsed = parse_cad_desc_fields(raw_desc)
        pm = lookup_part_material(part_materials or {}, pn or "") if pn else None
        grade = (
            (pm.material if pm else None)
            or parsed.get("material")
            or str(it.get("Material") or "").strip()
            or default_material
        )
        thk = (
            (pm.thickness_param() if pm else None)
            or parsed.get("thickness")
            or it.get("Thickness")
            or default_thickness
        )
        width, length = item_flat_dims(it)
        if not width:
            width = parsed.get("width_in")
        if not length:
            length = parsed.get("length_in")
        plate = match_plate_product(plates, thickness=thk, material=grade)
        if iid and plate:
            if addplate_item(
                client,
                quote_id,
                iid,
                plate,
                name=raw_desc,
                qty=qty,
                width_in=width,
                length_in=length,
            ):
                cad_wrote += 1
        if iid and raw_desc:
            update_params.append(
                {"ID": iid, "ParamName": "Description", "Value": raw_desc[:500]}
            )
    if update_params:
        quote_online_update(client, quote_id, update_params)

    def _verify(payload: dict[str, Any]) -> tuple[int, int, int, int, list[str]]:
        cad_ok = lin_ok = cad_miss = lin_miss = 0
        miss_ids: list[str] = []
        for it in payload.get("ItemList") or []:
            if not isinstance(it, dict) or _is_assembly(it):
                continue
            desc = str(it.get("Description") or "")
            pn = match_bom_part_no(desc, bom_rows)
            noun = bom_desc.get(normalize_part_key(pn or ""), "")
            want = classify_sectura_item(f"{pn or ''} {noun} {desc}")
            if _is_component(it) or want == "Component":
                continue
            if persist_linear and (_is_linear(it) or want == "Linear"):
                if _linear_fields_on_get(it):
                    lin_ok += 1
                else:
                    lin_miss += 1
                    iid = str(it.get("ID") or "")
                    if iid:
                        miss_ids.append(iid)
                continue
            if persist_cad:
                if _cad_fields_on_get(it):
                    cad_ok += 1
                else:
                    cad_miss += 1
        return cad_ok, lin_ok, cad_miss, lin_miss, miss_ids

    verified = client.get_json(f"v1/quote/{quote_id}")
    cad_ok, lin_ok, cad_miss, lin_miss, miss_ids = _verify(verified)
    if retry_linear and persist_linear and miss_ids:
        for iid in miss_ids:
            plan = linear_plans.get(iid)
            if not plan:
                continue
            product, length, name, qty = plan
            if update_linear_via_api(
                client,
                quote_id,
                iid,
                product,
                length_in=length,
                qty=qty,
                name=name,
            ):
                lin_wrote += 1
        verified = client.get_json(f"v1/quote/{quote_id}")
        cad_ok, lin_ok, cad_miss, lin_miss, _miss = _verify(verified)
    if persist_cad and cad_ok:
        notes.append(
            f"GET-verified Material/Thickness on {cad_ok} Cad line(s) (addplate)"
        )
    if persist_linear and lin_ok:
        notes.append(
            f"GET-verified Machine=Saw + Length on {lin_ok} Linear line(s) (addLinear)"
        )
    if persist_cad and cad_miss:
        notes.append(
            f"Cad Material/Thickness empty on GET after addplate ({cad_miss} line(s))"
        )
    if persist_linear and lin_miss:
        notes.append(
            f"WARNING: Linear Machine/Length empty on GET after addLinear "
            f"({lin_miss} line(s))"
        )
    if desc_n:
        notes.append(f"quoteOnline/update Description on {desc_n} line(s)")
    if cad_wrote or lin_wrote:
        notes.append(
            f"Wrote addplate×{cad_wrote} addLinear×{lin_wrote} "
            "(success is GET-verified fields, not HTTP 200)"
        )
    return notes
