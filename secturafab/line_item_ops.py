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
    cat = str(item.get("Category") or item.get("ItemType") or "").strip()
    return bool(item.get("IsLinear") or cat == "Linear" or item.get("ProductType") in (10, "10"))


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


_LG_RE = re.compile(
    r"(?i)(?:^|[x×\s])(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*(?:\"|″|in)?\s*LG\.?"
)


def parse_length_lg(text: str | None) -> float | None:
    """``91 1/8 LG.`` / ``X 4 LG`` → inches."""
    if not text:
        return None
    m = _LG_RE.search(str(text))
    if not m:
        return None
    raw = re.sub(r"\s+", " ", m.group(1)).strip()
    if " " in raw and "/" in raw:
        whole, frac = raw.split(" ", 1)
        num, den = frac.split("/", 1)
        try:
            return float(whole) + float(num) / float(den)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    if "/" in raw:
        num, den = raw.split("/", 1)
        try:
            return float(num) / float(den)
        except (TypeError, ValueError, ZeroDivisionError):
            return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    return val if val > 0 else None


def persist_classified_item_fields(
    client: Any,
    quote_id: str,
    *,
    bom_rows: list[dict[str, Any]] | None = None,
    part_materials: dict | None = None,
    default_material: str = "A36",
    default_thickness: str | None = "0.25",
) -> list[str]:
    """Write Material / Thickness / Length / Width / Machine onto items (not just Description)."""
    from quote_core.part_materials import lookup_part_material

    from secturafab.item_desc import format_component_line, item_flat_dims, item_length_in
    from secturafab.qty_ops import normalize_part_key
    from secturafab.weld_ops import _desc_token

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    bom_desc: dict[str, str] = {}
    for row in bom_rows or []:
        pn = str(row.get("part_no") or row.get("part_number") or "").strip()
        key = normalize_part_key(pn)
        if key:
            bom_desc[key] = str(row.get("description") or "")
    changed = 0
    for it in items:
        if not isinstance(it, dict) or _is_assembly(it):
            continue
        token = normalize_part_key(_desc_token(str(it.get("Description") or "")))
        noun = bom_desc.get(token, "")
        if _is_component(it):
            pn = token or _desc_token(str(it.get("Description") or ""))
            line = format_component_line(pn, noun or str(it.get("Description") or ""))
            if line and str(it.get("Description") or "") != line:
                it["Description"] = line[:500]
                changed += 1
            continue
        if _is_linear(it):
            it["Machine"] = "Saw"
            length = item_length_in(it) or parse_length_lg(noun) or parse_length_lg(
                str(it.get("Description") or "")
            )
            if length and length > 0:
                it["Length"] = length
                it["LinearLength"] = length
            changed += 1
            continue
        pm = lookup_part_material(part_materials or {}, token) if token else None
        grade = (pm.material if pm else None) or str(it.get("Material") or "").strip() or default_material
        thk = (pm.thickness_param() if pm else None) or it.get("Thickness") or default_thickness
        it["Material"] = grade
        it["MaterialGrade"] = grade
        it["Thickness"] = thk
        it["Machine"] = it.get("Machine") or "Laser"
        width, length = item_flat_dims(it)
        if width and length:
            it["Width"] = width
            it["Length"] = length
        changed += 1
    if not changed:
        return []
    detail["ItemList"] = items
    save = client.request("POST", "v1/quote", json=detail)
    try:
        status = int(getattr(save, "status_code", 200) or 200)
    except (TypeError, ValueError):
        status = 200
    if status >= 400:
        return [f"WARNING: Item field persist failed ({status})"]
    return [f"Persisted Material/Thickness/Length/Machine on {changed} line(s)"]
