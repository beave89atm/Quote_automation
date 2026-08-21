"""Safe property updates via PUT quoteOnline/update (no CAD rebuild).

Material/Thickness updates go through UpdateItem_Part and wipe Profile.
UnitCost / UnitPrice / Quantity updates via this endpoint do not.
"""

from __future__ import annotations

from typing import Any

from .client import SecturaFabClient
from .weld_ops import _desc_token, pick_weld_target_item

_ASSEMBLY_TYPE = 300


def quote_online_update(
    client: SecturaFabClient,
    quote_id: str,
    params: list[dict[str, Any]],
) -> bool:
    """PUT ParamName/Value updates. Returns True on success."""
    if not params:
        return True
    # Ensure ParentID is the quote for item-scoped updates.
    body: list[dict[str, Any]] = []
    for p in params:
        row = dict(p)
        if row.get("ID") and not row.get("ParentID"):
            row["ParentID"] = quote_id
        # Values must be strings per OpenAPI.
        if "Value" in row and row["Value"] is not None and not isinstance(row["Value"], str):
            row["Value"] = str(row["Value"])
        body.append(row)
    resp = client.request("PUT", "v1/quoteOnline/update", json=body)
    try:
        status = int(getattr(resp, "status_code", 500) or 500)
    except (TypeError, ValueError):
        return False
    return status < 400 and str(getattr(resp, "text", "")).strip().lower() in {
        "true",
        '"true"',
    }


def rollup_assembly_costs(
    client: SecturaFabClient,
    quote_id: str,
    *,
    part_key: str | None = None,
) -> list[str]:
    """
    Sum child UnitCost/UnitPrice into the assembly (Kyle's assembly-editor Update).

    Uses quoteOnline/update so Profile/Weld ops are not wiped.
    """
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    root = next(
        (
            it
            for it in items
            if it.get("ProductType") in (_ASSEMBLY_TYPE, "300", "assembly")
            or it.get("IsAssembly")
        ),
        None,
    )
    if root is None and part_key:
        root = pick_weld_target_item(items, part_key=part_key)
    if not root or not root.get("ID"):
        return ["No assembly root for cost rollup"]

    rid = str(root["ID"])
    root_qty = max(1, int(root.get("Quantity") or root.get("Qty") or 1))
    linked = [it for it in items if it.get("ID") != rid and it.get("AssemblyID") == rid]
    children = linked or [it for it in items if it.get("ID") != rid]

    cost = 0.0
    price = 0.0
    for it in children:
        qty = float(it.get("Quantity") or it.get("Qty") or 1)
        cost += float(it.get("UnitCost") or 0.0) * qty
        price += float(it.get("UnitPrice") or 0.0) * qty

    # Assembly's own secondary ops (Weld) — UnitCost on ops when present.
    for op in root.get("OperationCostList") or []:
        oq = float(op.get("Quantity") or op.get("MasterQuantity") or 1)
        cost += float(op.get("UnitCost") or 0.0) * oq
        price += float(op.get("UnitPrice") or 0.0) * oq

    # Per-assembly unit figures.
    unit_cost = cost / root_qty
    unit_price = price / root_qty

    ok = quote_online_update(
        client,
        quote_id,
        [
            {"ID": rid, "ParamName": "UnitCost", "Value": f"{unit_cost:.2f}"},
            {"ID": rid, "ParamName": "TotalCost", "Value": f"{cost:.2f}"},
            {"ID": rid, "ParamName": "UnitPrice", "Value": f"{unit_price:.2f}"},
            {"ID": rid, "ParamName": "TotalPrice", "Value": f"{price:.2f}"},
        ],
    )
    if not ok:
        return ["Assembly cost rollup via quoteOnline/update failed"]
    return [
        f"Rolled up assembly costs on {_desc_token(str(root.get('Description') or ''))}: "
        f"UnitCost ${unit_cost:.2f}, UnitPrice ${unit_price:.2f}"
    ]
