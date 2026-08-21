"""Attach SecturaFAB Profile (laser primary) ops after quickAddCAD.

API CAD import computes DataPart cut time but only attaches Bend (secondary).
Kyle's UI quotes get Profile ops with Drafting/Setup UnitTimes that drive
PrimaryTime. Nest/quote is broken on their API (optional IDList binder), so we
clone the shop's Profile template onto laser plate items and set PrimaryTime.
"""

from __future__ import annotations

import copy
import json
import re
import uuid
from typing import Any

from .client import SecturaFabClient
from .quote_update import quote_online_update

# Kyle Time 28106-2 / 1007922-2 Profile 5-pack (job times, amortized per Cad line).
_DRAFTING_JOB_HOURS = 0.25  # 15 min
_SETUP_JOB_HOURS = 0.25  # 15 min
_SHEET_LOAD_JOB_HOURS = 4.0 / 60.0  # ~4 min
PROFILE_5PACK_CALCS = ("Laser", "Drafting", "Laser-Setup", "Sheet Loading", "Deburr")

# Captured from a good Kyle UI quote (21678-1). Shop rates / calculators.
_PROFILE_OP_TEMPLATES: list[dict[str, Any]] = [
    {
        "OperationName": "Profile",
        "OperationLabel": "PR",
        "Operation_code": "op_prf",
        "OperationType": 0,
        "CostCategory": "Laser-CO2",
        "CostType": 1,
        "CostCalcType": 4,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "CalculatorName": "Laser",
        "Equipment": "Laser",
        "PrimaryOperation": True,
        "ProcessLocation": "Bay1",
        "LabourRate": 200.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 1,
        "SortSequence": 1,
        "InputSequence": 1,
        "InputType": 0,
        "Quantity": 1,
        "MasterQuantity": 1,
        "ValueUnits": "hour",
        "HasMinPrice": False,
        "Outsource": False,
        "UsesLocalLabourRate": False,
        "UsesLocalMargin": False,
        "UsesLocalMultiplier": False,
        "UsesLocalPrice": False,
        "UsesLocalValue": False,
        "UnitTime": 0.0,
        "Value": 0.0,
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
    },
    {
        "OperationName": "Profile",
        "OperationLabel": "PR",
        "Operation_code": "op_prf",
        "OperationType": 0,
        "CostCategory": "Drafting",
        "CostType": 1,
        "CostCalcType": 6,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "CalculatorName": "Drafting",
        "Equipment": "Laser",
        "PrimaryOperation": True,
        "ProcessLocation": "Bay1",
        "LabourRate": 65.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 1,
        "SortSequence": 2,
        "InputSequence": 1,
        "InputType": 0,
        "Quantity": 1,
        "MasterQuantity": 1,
        "ValueUnits": "hour",
        "HasMinPrice": False,
        "Outsource": False,
        "UsesLocalLabourRate": False,
        "UsesLocalMargin": False,
        "UsesLocalMultiplier": False,
        "UsesLocalPrice": False,
        "UsesLocalValue": False,
        "UnitTime": 0.25,
        "Value": 0.25,
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
    },
    {
        "OperationName": "Profile",
        "OperationLabel": "PR",
        "Operation_code": "op_prf",
        "OperationType": 20,
        "CostCategory": "Laser-CO2-Setup",
        "CostType": 1,
        "CostCalcType": 6,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "CalculatorName": "Laser-Setup",
        "Equipment": "Laser",
        "PrimaryOperation": True,
        "ProcessLocation": "Bay1",
        "LabourRate": 200.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 1,
        "SortSequence": 3,
        "InputSequence": 1,
        "InputType": 0,
        "Quantity": 1,
        "MasterQuantity": 1,
        "ValueUnits": "hour",
        "HasMinPrice": False,
        "Outsource": False,
        "UsesLocalLabourRate": False,
        "UsesLocalMargin": False,
        "UsesLocalMultiplier": False,
        "UsesLocalPrice": False,
        "UsesLocalValue": False,
        "UnitTime": 0.25,
        "Value": 0.25,
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
    },
    {
        "OperationName": "Profile",
        "OperationLabel": "PR",
        "Operation_code": "op_prf",
        "OperationType": 0,
        "CostCategory": "Laser-CO2-Setup",
        "CostType": 1,
        "CostCalcType": 14,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "CalculatorName": "Sheet Loading",
        "Equipment": "Laser",
        "PrimaryOperation": True,
        "ProcessLocation": "Bay1",
        "LabourRate": 200.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 1,
        "SortSequence": 4,
        "InputSequence": 1,
        "InputType": 0,
        "Quantity": 1,
        "MasterQuantity": 1,
        "ValueUnits": "hour",
        "HasMinPrice": False,
        "Outsource": False,
        "UsesLocalLabourRate": False,
        "UsesLocalMargin": False,
        "UsesLocalMultiplier": False,
        "UsesLocalPrice": False,
        "UsesLocalValue": False,
        "UnitTime": 0.06666666666666667,
        "Value": 0.06666666666666667,
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
    },
    {
        "OperationName": "Profile",
        "OperationLabel": "PR",
        "Operation_code": "op_prf",
        "OperationType": 0,
        "CostCategory": "Laser-CO2",
        "CostType": 1,
        "CostCalcType": 19,
        "Cost": 30.0,
        "Cost_Units": "hour",
        "CalculatorName": "Deburr",
        "Equipment": "Laser",
        "PrimaryOperation": True,
        "ProcessLocation": "Bay1",
        "LabourRate": 200.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 1,
        "SortSequence": 5,
        "InputSequence": 1,
        "InputType": 0,
        "Quantity": 1,
        "MasterQuantity": 1,
        "ValueUnits": "hour",
        "HasMinPrice": False,
        "Outsource": False,
        "UsesLocalLabourRate": False,
        "UsesLocalMargin": False,
        "UsesLocalMultiplier": False,
        "UsesLocalPrice": False,
        "UsesLocalValue": False,
        "UnitTime": 0.0,
        "Value": 0.0,
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
    },
]


def parse_datapart(raw: Any) -> dict[str, Any]:
    """SecturaFAB stores item CAD payload as ``DataPart:{json}``."""
    if not raw or not isinstance(raw, str):
        return {}
    m = re.match(r"^DataPart:(.*)$", raw, re.S)
    blob = m.group(1) if m else raw
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _is_laser_machine(machine: str | None) -> bool:
    m = str(machine or "").strip().lower()
    return not m or m == "laser" or m.startswith("laser")


def _is_cad_plate(item: dict[str, Any]) -> bool:
    """Cad / plate / sheet line that must keep the Profile 5-pack (ProductType 100)."""
    pt = item.get("ProductType")
    if pt in (300, "300", "assembly") or item.get("IsAssembly"):
        return False
    if pt in (200, "200", "component"):
        return False
    if pt in (50, "50"):  # addplate-as-new Plate — never create these
        return False
    cat = str(item.get("Category") or item.get("ItemType") or "").strip().lower()
    if cat in {"component", "linear"} or item.get("IsLinear"):
        return False
    if pt in (100, "100"):
        return True
    return cat == "cad" or bool(item.get("IsPlate"))


def _is_laser_plate(item: dict[str, Any]) -> bool:
    pt = item.get("ProductType")
    if pt in (300, "300", "assembly") or item.get("IsAssembly"):
        return False
    if pt in (200, "200", "component"):
        return False
    cat = str(item.get("Category") or item.get("ItemType") or "").strip().lower()
    if cat == "component":
        return False
    if item.get("IsLinear") or cat == "linear":
        return False
    machine = str(item.get("Machine") or "").strip().lower()
    # "Laser - Bay1" must count as laser (exact == "laser" was a recurring miss).
    if machine and not _is_laser_machine(machine):
        return False
    # Skip obvious hardware-only lines with no NestedArea / DataPart.
    ops = item.get("OperationCostList") or []
    if any(o.get("OperationName") == "Profile" for o in ops):
        return True
    data = parse_datapart(item.get("Data"))
    if data.get("CuttingLength") or data.get("Time") or data.get("PartLength"):
        return True
    # Plate flag from categorization
    if item.get("IsPlate") and _is_laser_machine(machine):
        return True
    # Single-PDF quickAddCAD often sets IsPart=True, IsPlate=False, Machine=Laser.
    if item.get("IsPart") and _is_laser_machine(machine):
        return True
    return _is_laser_machine(machine) and bool(machine)


def _item_area_sqin(item: dict[str, Any] | None) -> float:
    if not item:
        return 0.0
    dp = parse_datapart(item.get("Data"))
    for src in (item, dp):
        for key in ("NestedArea", "Area", "PartArea"):
            try:
                val = float(src.get(key) or 0)
            except (TypeError, ValueError):
                val = 0.0
            if val > 0:
                # SecturaFAB sometimes stores mm² after a metric CAD import.
                if val > 5000:
                    val = val / (25.4 * 25.4)
                return val
    length, width, _thk = _flat_dims(item, default_thk=None)
    if length and width and length > 0 and width > 0:
        return float(length) * float(width)
    return 0.0


def _deburr_hours_from_area(item: dict[str, Any] | None) -> float:
    """Per-part Deburr time from flat area. 0 if area is unknown (do not invent)."""
    area = _item_area_sqin(item)
    if area <= 0:
        return 0.0
    # Shop Deburr calculator is area-based (CostCalcType 19). Seed minutes from
    # sq ft so the row is not blank; leave UnitPrice at 0 for the calculator.
    sq_ft = area / 144.0
    minutes = min(30.0, max(0.25, sq_ft * 0.75))
    return minutes / 60.0


def _as_float(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if val <= 0:
        return None
    return val


def _flat_dims(
    item: dict[str, Any],
    *,
    default_thk: str | float | None,
) -> tuple[float | None, float | None, str]:
    """Length × width × thickness in inches for in-place addplate."""
    dp = parse_datapart(item.get("Data"))
    length = None
    width = None
    thk = None
    for src in (item, dp):
        if length is None:
            length = _as_float(src.get("Length")) or _as_float(src.get("PartLength"))
        if width is None:
            width = _as_float(src.get("Width")) or _as_float(src.get("PartWidth"))
        if thk is None:
            thk = _as_float(src.get("Thickness")) or _as_float(src.get("PartThickness"))
    box = dp.get("box") or item.get("box") or []
    if isinstance(box, (list, tuple)) and len(box) >= 2:
        axes = sorted(_as_float(x) or 0.0 for x in box[:3])
        if width is None and axes:
            width = axes[0] or None
        if length is None and len(axes) > 1:
            length = axes[-1] or None
        if thk is None and len(axes) >= 3 and axes[0] > 0:
            thk = axes[0]
    thk_text = "0.25"
    if default_thk is not None:
        thk_text = str(default_thk).strip() or "0.25"
    if thk is not None:
        thk_text = f"{thk:.4f}".rstrip("0").rstrip(".")
    return length, width, thk_text


def _build_profile_ops(
    item_id: str,
    cut_time_hours: float,
    *,
    cad_count: int = 1,
    item: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Profile 5-pack. Laser cut minutes stay 0 unless Nest/CAD already computed one.
    Drafting / Laser-Setup / Sheet Loading are job times amortized across Cad lines.
    Deburr is per-part from flat area. UnitPrice is left 0 (shop calculator).
    """
    n = max(1, int(cad_count or 1))
    drafting_h = _DRAFTING_JOB_HOURS / n
    setup_h = _SETUP_JOB_HOURS / n
    load_h = _SHEET_LOAD_JOB_HOURS / n
    deburr_h = _deburr_hours_from_area(item)
    ops: list[dict[str, Any]] = []
    for tmpl in _PROFILE_OP_TEMPLATES:
        op = copy.deepcopy(tmpl)
        op["ID"] = str(uuid.uuid4())
        op["QuoteOperationID"] = str(uuid.uuid4())
        op["ItemID"] = item_id
        calc = op.get("CalculatorName")
        if calc == "Laser":
            # Do not invent cut minutes — 0 is OK until the shop calculator has a time.
            cut = float(cut_time_hours or 0.0)
            op["UnitTime"] = cut
            op["Value"] = cut
        elif calc == "Drafting":
            op["UnitTime"] = drafting_h
            op["Value"] = drafting_h
        elif calc == "Laser-Setup":
            op["UnitTime"] = setup_h
            op["Value"] = setup_h
        elif calc == "Sheet Loading":
            op["UnitTime"] = load_h
            op["Value"] = load_h
        elif calc == "Deburr":
            op["UnitTime"] = deburr_h
            op["Value"] = deburr_h
        op["UnitCost"] = 0.0
        op["UnitPrice"] = 0.0
        ops.append(op)
    return ops


def profile_5pack_names(item: dict[str, Any]) -> set[str]:
    return {
        str(o.get("CalculatorName") or "")
        for o in (item.get("OperationCostList") or [])
        if o.get("OperationName") == "Profile"
    }


def profile_5pack_present(item: dict[str, Any]) -> bool:
    names = profile_5pack_names(item)
    return all(calc in names for calc in PROFILE_5PACK_CALCS)


def cad_plate_ready(item: dict[str, Any]) -> bool:
    """True only when MaterialCost calculated *and* the Profile 5-pack is on the Cad line."""
    if not _is_cad_plate(item):
        return True
    try:
        mat_cost = float(item.get("MaterialCost") or 0)
    except (TypeError, ValueError):
        mat_cost = 0.0
    return mat_cost > 0 and profile_5pack_present(item)


def _ops_fingerprint(detail: dict[str, Any]) -> str:
    """Cheap signature so we can detect UpdateItem_Part CAD recalcs finishing."""
    parts: list[str] = []
    for it in detail.get("ItemList") or []:
        ops = it.get("OperationCostList") or []
        names = ",".join(str(o.get("OperationName") or "") for o in ops)
        qty = it.get("Quantity") if it.get("Quantity") is not None else it.get("Qty")
        dp = parse_datapart(it.get("Data"))
        cut = dp.get("Time")
        wcat = it.get("WeightCategory")
        thk = it.get("Thickness")
        parts.append(f"{it.get('ID')}:{qty}:{cut}:{wcat}:{thk}:{len(ops)}:{names}")
    return "|".join(parts)


def wait_for_quote_settle(
    client: SecturaFabClient,
    quote_id: str,
    *,
    timeout_s: float = 120.0,
    stable_s: float = 15.0,
    poll_s: float = 3.0,
    min_wait_s: float = 0.0,
) -> list[str]:
    """
    Wait until quote ops/quantities/CAD times stop changing.

    ``UpdateItem_Part`` (and Material/Thickness via quoteOnline/update) returns
    HTTP 200 before CAD recalc finishes; that recalc wipes Profile/Weld about
    ~30–60s later if we attach ops too early.
    """
    import time

    started = time.monotonic()
    if min_wait_s > 0:
        time.sleep(min_wait_s)

    deadline = time.monotonic() + max(1.0, timeout_s)
    last = _ops_fingerprint(client.get_json(f"v1/quote/{quote_id}"))
    stable_since = time.monotonic()
    polls = 0
    while time.monotonic() < deadline:
        time.sleep(max(0.5, poll_s))
        polls += 1
        cur = _ops_fingerprint(client.get_json(f"v1/quote/{quote_id}"))
        if cur == last:
            if time.monotonic() - stable_since >= stable_s:
                elapsed = time.monotonic() - started
                return [
                    f"Quote CAD settle OK after {polls} poll(s) "
                    f"(stable ≥{stable_s:.0f}s, elapsed {elapsed:.0f}s)"
                ]
        else:
            last = cur
            stable_since = time.monotonic()
    elapsed = time.monotonic() - started
    return [
        f"Quote CAD settle timed out after {elapsed:.0f}s "
        f"({polls} polls) — continuing anyway"
    ]


def apply_part_materials(
    client: SecturaFabClient,
    quote_id: str,
    *,
    material: str,
    thickness: str,
    part_materials: dict[str, Any] | None = None,
    bom_rows: list[dict[str, Any]] | None = None,
) -> list[str]:
    """
    Push per-part material/thickness/qty via UpdateItem_Part.

    BOM piece counts must be baked into this call — UpdateItem_Part resets
    Quantity to 1 unless ``qty`` is passed, and later CAD rebuilds keep that qty.

    Must run *before* Profile/Weld attach, then ``wait_for_quote_settle``.
    Never call this after ops are attached — UpdateItem_Part wipes them.
    """
    from quote_core.part_materials import PartMaterial, lookup_part_material

    from .qty_ops import bom_qty_map, normalize_part_key
    from .weld_ops import _desc_token

    notes: list[str] = []
    detail = client.get_json(f"v1/quote/{quote_id}")
    targets = [it for it in (detail.get("ItemList") or []) if _is_laser_plate(it)]
    if not targets:
        return ["No laser plate items for material update"]

    mat_map: dict[str, PartMaterial] = {}
    if part_materials:
        for k, v in part_materials.items():
            if isinstance(v, PartMaterial):
                mat_map[k] = v
            elif isinstance(v, dict) and v.get("material"):
                mat_map[k] = PartMaterial(
                    part_key=str(k),
                    material_key=str(v.get("material_key") or "a36"),
                    material=str(v["material"]),
                    thickness_in=(
                        float(v["thickness_in"])
                        if v.get("thickness_in") is not None
                        else None
                    ),
                    source=str(v.get("source") or "map"),
                )

    qty_by_pn = bom_qty_map(bom_rows)
    mat_updates = 0
    qty_updates = 0
    import time

    for it in targets:
        iid = it.get("ID")
        if not iid:
            continue
        pm = lookup_part_material(mat_map, str(it.get("Description") or ""))
        use_mat = pm.material if pm else material
        use_thk = (pm.thickness_param() if pm else None) or thickness
        use_thk = re.sub(r"(?i)\s*(inches|inch|in)\s*$", "", str(use_thk).strip())
        use_thk = use_thk.replace('"', "").replace("″", "").strip() or str(thickness)
        token = _desc_token(str(it.get("Description") or ""))
        bom_q = qty_by_pn.get(normalize_part_key(token), 1)
        params: dict[str, Any] = {
            "quoteID": quote_id,
            "itemID": iid,
            "material": use_mat,
            "thickness": use_thk,
            "machine": "Laser",
            "qty": int(bom_q),
        }
        ok = False
        last_status = None
        for attempt in range(1, 5):
            upd = client.request(
                "POST",
                "v1/quoteOnline/UpdateItem_Part",
                params=params,
            )
            last_status = upd.status_code
            if upd.status_code < 400:
                ok = True
                break
            if upd.status_code not in {429, 500, 502, 503, 504}:
                break
            time.sleep(min(8.0, 1.5 * attempt))
        if not ok:
            notes.append(
                f"UpdateItem_Part failed for {(it.get('Description') or '')[:40]!r}: "
                f"{last_status}"
            )
            continue
        if pm:
            mat_updates += 1
        if bom_q > 1:
            qty_updates += 1
        # Brief pause so SecturaFAB is less likely to 502 the next part.
        time.sleep(0.75)

    if mat_updates:
        notes.append(
            f"Applied per-part material/thickness from component PDFs on "
            f"{mat_updates} laser item(s)"
        )
    else:
        notes.append(
            f"UpdateItem_Part ran on {len(targets)} laser item(s) "
            f"(default {material} @ {thickness}\")"
        )
    if qty_updates:
        notes.append(
            f"Baked BOM qty into UpdateItem_Part on {qty_updates} item(s) "
            f"(survives CAD rebuild)"
        )
    return notes


def count_profile_items(detail: dict[str, Any]) -> int:
    n = 0
    for it in detail.get("ItemList") or []:
        if not _is_laser_plate(it):
            continue
        ops = it.get("OperationCostList") or []
        if any(o.get("OperationName") == "Profile" for o in ops):
            n += 1
    return n


def _attach_laser_profile_ops_once(
    client: SecturaFabClient,
    quote_id: str,
    *,
    material: str,
    thickness: str,
) -> list[str]:
    notes: list[str] = []
    detail = client.get_json(f"v1/quote/{quote_id}")
    targets = [it for it in (detail.get("ItemList") or []) if _is_laser_plate(it)]
    if not targets:
        return ["No laser plate items found for Profile ops"]

    patched = 0
    changed = False
    cad_count = max(1, len(targets))
    for it in detail.get("ItemList") or []:
        if not _is_laser_plate(it):
            continue
        iid = str(it.get("ID") or "")
        existing = list(it.get("OperationCostList") or [])
        has_profile = any(o.get("OperationName") == "Profile" for o in existing)
        dp = parse_datapart(it.get("Data"))
        cut = float(dp.get("Time") or 0.0)

        if has_profile:
            primary_sum = sum(
                float(o.get("UnitTime") or 0.0)
                for o in existing
                if o.get("PrimaryOperation")
            )
            if float(it.get("PrimaryTime") or 0) <= 0 and primary_sum > 0:
                it["PrimaryTime"] = primary_sum
                it["UnitPrimaryTime"] = primary_sum
                changed = True
                patched += 1
            continue

        profile_ops = _build_profile_ops(iid, cut, cad_count=cad_count, item=it)
        other = [o for o in existing if o.get("OperationName") != "Profile"]
        new_ops = profile_ops + other
        primary_sum = sum(
            float(o.get("UnitTime") or 0.0) for o in new_ops if o.get("PrimaryOperation")
        )
        it["OperationCostList"] = new_ops
        it["PrimaryTime"] = primary_sum
        it["UnitPrimaryTime"] = primary_sum
        badge = str(it.get("BadgeString") or "")
        if "Profile" not in badge:
            it["BadgeString"] = ("Profile " + badge).strip()
        changed = True
        patched += 1

    if changed:
        save = client.request("POST", "v1/quote", json=detail)
        if save.status_code >= 400:
            notes.append(f"Saving Profile ops failed ({save.status_code})")
        else:
            notes.append(
                f"Attached Profile primary ops on {patched} laser plate item(s) "
                f"(default material {material} @ {thickness})"
            )
    elif patched == 0:
        notes.append("Laser plate items already had Profile ops")

    return notes


def ensure_laser_profile_ops(
    client: SecturaFabClient,
    quote_id: str,
    *,
    material: str,
    thickness: str,
    part_materials: dict[str, Any] | None = None,
    verify: bool = True,
) -> list[str]:
    """
    Ensure laser plate items have Profile primary ops and PrimaryTime.

    Does **not** call UpdateItem_Part (that wipes ops). Apply materials via
    ``apply_part_materials`` + ``wait_for_quote_settle`` first.

    After save, optionally re-reads the quote and retries once if Profile is missing
    (stale full-quote POSTs have wiped ops more than once).

    ``part_materials`` is accepted for API compatibility but ignored here.
    """
    del part_materials  # materials must be applied earlier — see apply_part_materials
    notes: list[str] = []
    notes.extend(
        _attach_laser_profile_ops_once(
            client, quote_id, material=material, thickness=thickness
        )
    )
    if not verify:
        return notes

    check = client.get_json(f"v1/quote/{quote_id}")
    missing = [
        it
        for it in (check.get("ItemList") or [])
        if _is_laser_plate(it)
        and not any(
            o.get("OperationName") == "Profile"
            for o in (it.get("OperationCostList") or [])
        )
    ]
    if not missing:
        return notes

    notes.append(
        f"WARNING: Profile missing on {len(missing)} laser item(s) after save — retrying"
    )
    notes.extend(
        _attach_laser_profile_ops_once(
            client, quote_id, material=material, thickness=thickness
        )
    )
    check2 = client.get_json(f"v1/quote/{quote_id}")
    still = sum(
        1
        for it in (check2.get("ItemList") or [])
        if _is_laser_plate(it)
        and not any(
            o.get("OperationName") == "Profile"
            for o in (it.get("OperationCostList") or [])
        )
    )
    if still:
        notes.append(
            f"WARNING: Profile still missing on {still} laser item(s) after retry"
        )
    else:
        notes.append("Profile verified on laser plate item(s) after retry")
    return notes


def _persist_profile_ops(
    client: SecturaFabClient,
    quote_id: str,
    item_id: str,
    ops: list[dict[str, Any]],
    *,
    fresh_detail: dict[str, Any] | None = None,
) -> bool:
    """Write OperationCostList after addplate. Prefer quoteOnline/update (no CAD rebuild)."""
    ok = quote_online_update(
        client,
        quote_id,
        [{"ID": item_id, "ParamName": "OperationCostList", "Value": json.dumps(ops)}],
    )
    check = client.get_json(f"v1/quote/{quote_id}")
    item = next(
        (it for it in (check.get("ItemList") or []) if str(it.get("ID")) == str(item_id)),
        None,
    )
    if item and (
        profile_5pack_present(item)
        or any(o.get("OperationName") == "Profile" for o in (item.get("OperationCostList") or []))
    ):
        return True
    # Fallback: POST the *fresh* post-addplate quote so MaterialCost is not wiped.
    detail = dict(fresh_detail or check)
    items = list(detail.get("ItemList") or [])
    for it in items:
        if str(it.get("ID")) == str(item_id):
            it["OperationCostList"] = ops
            badge = str(it.get("BadgeString") or "")
            if "Profile" not in badge:
                it["BadgeString"] = ("Profile " + badge).strip()
            break
    detail["ItemList"] = items
    save = client.request("POST", "v1/quote", json=detail)
    try:
        status = int(getattr(save, "status_code", 500) or 500)
    except (TypeError, ValueError):
        return False
    return status < 400


def addplate_bind_and_restore_profile(
    client: SecturaFabClient,
    quote_id: str,
    *,
    material: str,
    thickness: str,
) -> list[str]:
    """
    In-place addplate on each Cad/PT 100 item, then immediately restore the
    Profile 5-pack. addplate fills MaterialCost but wipes ops — never treat
    the item as done after addplate. Never leave Cad at 0 ops.
    """
    notes: list[str] = []
    detail = client.get_json(f"v1/quote/{quote_id}")
    targets = [it for it in (detail.get("ItemList") or []) if _is_cad_plate(it)]
    if not targets:
        return ["No Cad/plate/sheet items for addplate + Profile"]

    cad_count = len(targets)
    bound = 0
    restored = 0
    for seed in targets:
        iid = str(seed.get("ID") or "")
        if not iid:
            continue
        length, width, thk = _flat_dims(seed, default_thk=thickness)
        use_mat = str(
            seed.get("WeightCategory") or seed.get("Material") or material or "A36"
        ).strip() or "A36"
        if use_mat.upper().replace(" ", "").replace("-", "") in {"A569", "SAEA569"}:
            use_mat = "A36"

        if length and width:
            qty = seed.get("Quantity") or seed.get("Qty") or 1
            params = {
                "quoteID": quote_id,
                "itemID": iid,  # existing Cad line — never a new PT 50 Plate
                "material": use_mat,
                "thickness": thk,
                "length": length,
                "width": width,
                "qty": int(qty) if str(qty).replace(".", "", 1).isdigit() else 1,
                "units": "inch",
                "thickness_Units": "inch",
            }
            addp = client.request("POST", "v1/quoteOnline/addplate", params=params)
            status = getattr(addp, "status_code", 500)
            if status >= 400:
                notes.append(
                    f"WARNING: addplate failed on {(seed.get('Description') or '')[:40]!r} "
                    f"({status}) — still restoring Profile"
                )
            else:
                bound += 1
        else:
            notes.append(
                f"WARNING: {(seed.get('Description') or '')[:40]!r} has no L×W "
                f"for addplate — still restoring Profile"
            )

        # addplate wipes the Profile 5-pack. Never consider the item done here.
        fresh = client.get_json(f"v1/quote/{quote_id}")
        item = next(
            (it for it in (fresh.get("ItemList") or []) if str(it.get("ID")) == iid),
            seed,
        )
        if cad_plate_ready(item):
            continue
        dp = parse_datapart(item.get("Data"))
        cut = float(dp.get("Time") or 0.0)
        ops = _build_profile_ops(iid, cut, cad_count=cad_count, item=item)
        if not _persist_profile_ops(
            client, quote_id, iid, ops, fresh_detail=fresh
        ):
            notes.append(
                f"WARNING: Profile restore failed on {(item.get('Description') or '')[:40]!r}"
            )
            continue
        restored += 1

        verify = client.get_json(f"v1/quote/{quote_id}")
        checked = next(
            (it for it in (verify.get("ItemList") or []) if str(it.get("ID")) == iid),
            None,
        )
        if checked is None:
            notes.append(f"WARNING: Cad item {iid} missing after Profile restore")
            continue
        if not any(
            o.get("OperationName") == "Profile"
            for o in (checked.get("OperationCostList") or [])
        ):
            notes.append(
                f"WARNING: Cad item left at 0 ops after addplate "
                f"({(checked.get('Description') or '')[:40]!r}) — Profile restore did not stick"
            )
        elif not cad_plate_ready(checked):
            try:
                mc = float(checked.get("MaterialCost") or 0)
            except (TypeError, ValueError):
                mc = 0.0
            if mc <= 0:
                notes.append(
                    f"WARNING: {(checked.get('Description') or '')[:40]!r} "
                    f"has Profile but MaterialCost={mc}"
                )

    notes.append(
        f"addplate bound material on {bound}/{cad_count} Cad item(s); "
        f"restored Profile 5-pack on {restored}"
    )
    return notes
