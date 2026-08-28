"""Attach SecturaFAB Weld secondary ops from Cursor weld/fit-up minutes.

Mirrors Kyle's manual flow (lesson 02): after STEP import, add Weld on the
assembly / top-level part using Quote Automation times — not from STEP geometry.
"""

from __future__ import annotations

import copy
import os
import uuid
from typing import Any

from .client import SecturaFabClient

# Captured from Kyle Cleaver quote Q9836 (73476004) — shop Weld calculators.
_WELD_OP_TEMPLATES: list[dict[str, Any]] = [
    {
        "OperationName": "Weld",
        "OperationLabel": "Weld",
        "Operation_code": "op_weld",
        "OperationType": 10,
        "CostCategory": "Weld",
        "CostType": 1,
        "CostCalcType": 9,
        "Cost": 35.0,
        "Cost_Units": "hour",
        "CalculatorName": "Weld-Time",
        "Equipment": "Welding",
        "PrimaryOperation": False,
        "ProcessLocation": None,
        "LabourRate": 70.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 0,
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
        "OperationName": "Weld",
        "OperationLabel": "Weld",
        "Operation_code": "op_weld",
        "OperationType": 10,
        "CostCategory": "Weld",
        "CostType": 1,
        "CostCalcType": 9,
        "Cost": 35.0,
        "Cost_Units": "hour",
        "CalculatorName": "Weld-Fitting",
        "Equipment": "Welding",
        "PrimaryOperation": False,
        "ProcessLocation": None,
        "LabourRate": 70.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 0,
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
        "OperationName": "Weld",
        "OperationLabel": "Weld",
        "Operation_code": "op_weld",
        "OperationType": 10,
        "CostCategory": "Weld-Setup",
        "CostType": 1,
        "CostCalcType": 6,
        "Cost": 35.0,
        "Cost_Units": "hour",
        "CalculatorName": "Weld-Setup",
        "Equipment": "Welding",
        "PrimaryOperation": False,
        "ProcessLocation": None,
        "LabourRate": 70.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 0,
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
        "UnitTime": 0.25,  # 15 minutes (lesson 02 default)
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
        "OperationName": "Weld",
        "OperationLabel": "Weld",
        "Operation_code": "op_weld",
        "OperationType": 20,
        "CostCategory": "Weld",
        "CostType": 1,
        "CostCalcType": 9,
        "Cost": 35.0,
        "Cost_Units": "hour",
        "CalculatorName": "Weld Grind Finish",
        "Equipment": "Welding",
        "PrimaryOperation": False,
        "ProcessLocation": None,
        "LabourRate": 70.0,
        "Margin": 0.0,
        "Multiplier": 1.0,
        "ApplyMargin": True,
        "Burden": 0.0,
        "SequanceNumber": 0,
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
        "UnitTime": 0.03333333333333333,  # ~2 min shop default from Q9836
        "Value": 0.03333333333333333,
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

_DEFAULT_SETUP_MINUTES = 15.0


def minutes_to_hours(minutes: float) -> float:
    return float(minutes or 0.0) / 60.0


def resolve_weld_times(times: dict[str, Any] | None) -> tuple[float, float, float] | None:
    """
    Return (weld_hours, fitup_hours, setup_hours) or None if nothing to add.

    Prefers with-fixture fit-up (lesson 02). Override with
    SECTURAFAB_FITUP_MODE=no for no-fixture minutes.
    """
    times = times or {}
    weld_min = float(times.get("weld_minutes") or 0.0)
    if weld_min <= 0:
        return None

    mode = (os.getenv("SECTURAFAB_FITUP_MODE") or "with").strip().lower()
    if mode in {"no", "none", "no_fixture", "nofixture"}:
        fit_min = float(times.get("fitup_no_fixture_minutes") or 0.0)
    else:
        fit_min = float(times.get("fitup_with_fixture_minutes") or 0.0)

    setup_min = float(os.getenv("SECTURAFAB_WELD_SETUP_MINUTES") or _DEFAULT_SETUP_MINUTES)
    return minutes_to_hours(weld_min), minutes_to_hours(fit_min), minutes_to_hours(setup_min)


def _desc_token(description: str) -> str:
    text = (description or "").strip()
    if not text:
        return ""
    # "73476004  - 3/16..." or bare "73476004"
    return text.split()[0].strip()


def pick_weld_target_item(
    items: list[dict[str, Any]],
    *,
    part_key: str | None = None,
) -> dict[str, Any] | None:
    """Prefer assembly line; else item matching part_key; else first item."""
    if not items:
        return None
    for it in items:
        pt = it.get("ProductType")
        if pt in (300, "300", "assembly") or it.get("IsAssembly"):
            return it
    key = (part_key or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    if key:
        for it in items:
            if _desc_token(str(it.get("Description") or "")) == key:
                return it
        # softer: description startswith
        for it in items:
            if str(it.get("Description") or "").startswith(key):
                return it
    return items[0]


def build_weld_ops(
    item_id: str,
    *,
    weld_hours: float,
    fitup_hours: float,
    setup_hours: float,
    quantity: int = 1,
) -> list[dict[str, Any]]:
    qty = max(1, int(quantity or 1))
    ops: list[dict[str, Any]] = []
    for tmpl in _WELD_OP_TEMPLATES:
        op = copy.deepcopy(tmpl)
        op["ID"] = str(uuid.uuid4())
        op["QuoteOperationID"] = str(uuid.uuid4())
        op["ItemID"] = item_id
        op["Quantity"] = qty
        op["MasterQuantity"] = qty
        calc = op.get("CalculatorName")
        if calc == "Weld-Time":
            op["UnitTime"] = float(weld_hours)
            op["Value"] = float(weld_hours)
        elif calc == "Weld-Fitting":
            op["UnitTime"] = float(fitup_hours)
            op["Value"] = float(fitup_hours)
        elif calc == "Weld-Setup":
            # Lesson 02: 15 min setup on the quote. When qty>1, store per-unit
            # like Kyle's Q9836 (15 min / 10 = 0.025 hr).
            per_unit = float(setup_hours) / qty
            op["UnitTime"] = per_unit
            op["Value"] = per_unit
        ops.append(op)
    return ops


def assembly_has_weld(detail: dict[str, Any], *, part_key: str | None = None) -> bool:
    target = pick_weld_target_item(list(detail.get("ItemList") or []), part_key=part_key)
    if not target:
        return False
    return any(
        o.get("OperationName") == "Weld" for o in (target.get("OperationCostList") or [])
    )


def ensure_weld_ops(
    client: SecturaFabClient,
    quote_id: str,
    *,
    times: dict[str, Any] | None,
    part_key: str | None = None,
    force: bool = False,
) -> list[str]:
    """
    Attach Weld secondary ops from Cursor times onto the assembly / top part.

    Does nothing when weld_minutes is missing or zero.
    When ``force`` is True, replace existing Weld ops (used after CAD wipe recovery).
    """
    resolved = resolve_weld_times(times)
    if not resolved:
        return ["No weld minutes on job — skipped SecturaFAB Weld ops"]

    weld_h, fit_h, setup_h = resolved
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    kids = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            pt = int(it.get("ProductType"))
        except (TypeError, ValueError):
            continue
        if pt in (100, 10, 30, 40):
            kids.append(it)
    if not kids:
        return [
            "WARNING: AddOperation weld skipped — no Cad/Linear kids yet"
        ]
    target = pick_weld_target_item(items, part_key=part_key)
    if not target or not target.get("ID"):
        return ["No quote item found to attach Weld ops"]

    existing = list(target.get("OperationCostList") or [])
    has_weld = any(o.get("OperationName") == "Weld" for o in existing)
    if has_weld and not force:
        return [
            f"Weld ops already present on {(target.get('Description') or '')[:40]!r} — left unchanged"
        ]

    qty = int(target.get("Quantity") or target.get("Qty") or 1)
    weld_inches = float((times or {}).get("total_inches") or 0.0)
    from .browser_session import effective_website_cookie
    from .website import (
        SecturaFabWebsiteAuthError,
        WELD_CALC_PARAM_TYPE,
        WELD_OPERATION_CODE,
    )

    cookie = effective_website_cookie(getattr(client, "config", None))
    if cookie and hasattr(client, "add_operation"):
        try:
            posted = client.add_operation(
                quote_id=quote_id,
                item_id=str(target["ID"]),
                weld_inches=weld_inches,
                weld_hours=weld_h,
                fitup_hours=fit_h,
                setup_hours=setup_h,
            )
            if posted in (None, "", {}, []):
                return [
                    "WARNING: AddOperation weld returned empty — "
                    "not grafting a 3h laser; session path only"
                ]
            fit_label = "with fixture"
            mode = (os.getenv("SECTURAFAB_FITUP_MODE") or "with").strip().lower()
            if mode in {"no", "none", "no_fixture", "nofixture"}:
                fit_label = "no fixture"
            return [
                f"AddOperation {WELD_OPERATION_CODE} on "
                f"{(target.get('Description') or '')[:40]!r} "
                f"CalcParamType={WELD_CALC_PARAM_TYPE} ApplyTo=ITEM: "
                f"{weld_h * 60:.1f} min weld, {fit_h * 60:.1f} min fit-up "
                f"({fit_label}), {setup_h * 60:.0f} min setup"
            ]
        except SecturaFabWebsiteAuthError as exc:
            return [
                f"WARNING: AddOperation weld fail-closed ({exc}) — "
                "not grafting Laser"
            ]

    weld_ops = build_weld_ops(
        str(target["ID"]),
        weld_hours=weld_h,
        fitup_hours=fit_h,
        setup_hours=setup_h,
        quantity=qty,
    )
    # Keep non-Weld ops; replace Weld if force-rebuilding after a CAD wipe.
    kept = [o for o in existing if o.get("OperationName") != "Weld"]
    target["OperationCostList"] = kept + weld_ops

    # Cookie absent: public quote POST (do not refuse the whole push).
    for it in detail.get("ItemList") or []:
        if it.get("ID") == target["ID"]:
            it["OperationCostList"] = target["OperationCostList"]
            break

    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Saving Weld ops failed ({save.status_code})"]

    fit_label = "with fixture"
    mode = (os.getenv("SECTURAFAB_FITUP_MODE") or "with").strip().lower()
    if mode in {"no", "none", "no_fixture", "nofixture"}:
        fit_label = "no fixture"
    verb = "Re-attached" if (has_weld and force) else "Attached"
    return [
        f"{verb} Weld on {(target.get('Description') or '')[:40]!r}: "
        f"{weld_h * 60:.1f} min weld, {fit_h * 60:.1f} min fit-up ({fit_label}), "
        f"{setup_h * 60:.0f} min setup"
    ]
