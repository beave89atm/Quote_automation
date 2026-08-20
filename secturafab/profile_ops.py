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
        "UnitCost": 7.5,
        "UnitPrice": 16.25,
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
        "UnitCost": 7.5,
        "UnitPrice": 50.0,
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
        "UnitCost": 2.0,
        "UnitPrice": 13.33333333333334,
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


def _build_profile_ops(item_id: str, cut_time_hours: float) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    laser_cut_filled = False
    for tmpl in _PROFILE_OP_TEMPLATES:
        op = copy.deepcopy(tmpl)
        op["ID"] = str(uuid.uuid4())
        op["QuoteOperationID"] = str(uuid.uuid4())
        op["ItemID"] = item_id
        # Put Nest/CAD cut time on the primary Laser calculator row.
        if (
            not laser_cut_filled
            and op.get("CalculatorName") == "Laser"
            and float(op.get("UnitTime") or 0) == 0.0
        ):
            op["UnitTime"] = float(cut_time_hours or 0.0)
            op["Value"] = float(cut_time_hours or 0.0)
            laser_cut_filled = True
        ops.append(op)
    return ops


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


def _item_has_profile(it: dict[str, Any]) -> bool:
    ops = it.get("OperationCostList") or []
    return any(o.get("OperationName") == "Profile" for o in ops)


def count_profile_items(detail: dict[str, Any]) -> int:
    n = 0
    for it in detail.get("ItemList") or []:
        if not _is_laser_plate(it):
            continue
        if _item_has_profile(it):
            n += 1
    return n


def laser_plates_missing_profile(detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Laser plate ItemList rows that do not currently have a Profile op."""
    return [
        it
        for it in (detail.get("ItemList") or [])
        if _is_laser_plate(it) and not _item_has_profile(it)
    ]


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

        profile_ops = _build_profile_ops(iid, cut)
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
        from .quote_update import safe_quote_post

        save = safe_quote_post(client, quote_id, detail)
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
    missing = laser_plates_missing_profile(check)
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
    still = len(laser_plates_missing_profile(check2))
    if still:
        notes.append(
            f"WARNING: Profile still missing on {still} laser item(s) after retry"
        )
    else:
        notes.append("Profile verified on laser plate item(s) after retry")
    return notes
