"""Convert the top-level STEP root into an Assembly and attach children.

quickAddCAD imports solids as flat quote lines. Kyle's UI STEP import sets:
- root: ProductType assembly (300), AssemblyLevel 1
- children: AssemblyID = root ID, AssemblyLevel 2, AssemblyName, AssemblyQty,
  isAssemblyItem true

Without those child fields, SecturaFAB leaves parts on the left side of the
assembly editor (not rolled up under the parent).
"""

from __future__ import annotations

from typing import Any

from .client import SecturaFabClient
from .weld_ops import _desc_token, pick_weld_target_item

_ASSEMBLY_TYPE = 300


def _is_assembly_type(item: dict[str, Any]) -> bool:
    pt = item.get("ProductType")
    return pt in (_ASSEMBLY_TYPE, "300", "assembly") or bool(item.get("IsAssembly"))


def _attach_children(
    items: list[dict[str, Any]],
    *,
    assembly_id: str,
    assembly_name: str,
    assembly_qty: int,
) -> int:
    """Set AssemblyID / Level / Name / Qty on every non-root line. Returns count."""
    root_qty = max(1, int(assembly_qty or 1))
    linked = 0
    for it in items:
        if it.get("ID") == assembly_id:
            it["AssemblyID"] = None
            it["AssemblyLevel"] = 1
            it["AssemblyName"] = None
            it["AssemblyQty"] = 0
            it["isAssemblyItem"] = False
            continue
        qty = max(1, int(it.get("Quantity") or it.get("Qty") or 1))
        # Pieces per one assembly (Kyle: qty 20 with assembly 10 → AssemblyQty 2).
        per = max(1, qty // root_qty) if qty >= root_qty else qty
        it["AssemblyID"] = assembly_id
        it["AssemblyLevel"] = 2
        it["AssemblyName"] = assembly_name
        it["AssemblyQty"] = per
        it["isAssemblyItem"] = True
        linked += 1
    return linked


def ensure_assembly_root(
    client: SecturaFabClient,
    quote_id: str,
    *,
    part_key: str | None,
) -> list[str]:
    """
    Mark the top-level PN line as Assembly and attach all other lines under it.
    """
    key = (part_key or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    if not key:
        return ["No part key — skipped assembly root conversion"]

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    if not items:
        return ["No items — skipped assembly root conversion"]

    target = None
    for it in items:
        if _is_assembly_type(it) and _desc_token(str(it.get("Description") or "")) == key:
            target = it
            break
    if target is None:
        target = pick_weld_target_item(items, part_key=key)
    if not target or not target.get("ID"):
        return [f"Could not find root item for assembly PN {key}"]

    tid = str(target["ID"])

    # Rewrite root to match Kyle's assembly line.
    target["ProductType"] = _ASSEMBLY_TYPE
    target["Description"] = key
    target["Machine"] = None
    target["IsPlate"] = False
    target["IsPart"] = False
    target["IsLinear"] = False
    target["ProductSubType"] = None
    target["Thickness"] = 0.0
    target["ThicknessDisp"] = None
    target["WeightCategory"] = None
    keep_ops = [
        o
        for o in (target.get("OperationCostList") or [])
        if o.get("OperationName") == "Weld"
    ]
    target["OperationCostList"] = keep_ops
    target["BadgeString"] = "Weld" if keep_ops else ""
    target["PrimaryTime"] = 0.0
    target["UnitPrimaryTime"] = 0.0
    if isinstance(target.get("Data"), str) and target["Data"].startswith("DataPart:"):
        target["Data"] = None

    for it in items:
        if it.get("ID") == tid:
            it.update(target)
            break

    linked = _attach_children(
        items,
        assembly_id=tid,
        assembly_name=key,
        assembly_qty=int(target.get("Quantity") or target.get("Qty") or 1),
    )
    detail["ItemList"] = items

    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Saving assembly root / child links failed ({save.status_code})"]

    # Verify links stuck
    check = client.get_json(f"v1/quote/{quote_id}")
    ok = sum(
        1
        for it in (check.get("ItemList") or [])
        if it.get("ID") != tid and it.get("AssemblyID") == tid
    )
    notes = [
        f"Converted root line to Assembly ({key}) and attached {linked} child item(s)"
    ]
    if ok < linked:
        notes.append(
            f"Warning: only {ok}/{linked} children retained AssemblyID after save — "
            f"check assembly editor in SecturaFAB"
        )
    return notes


def relink_assembly_children(
    client: SecturaFabClient,
    quote_id: str,
    *,
    part_key: str | None,
) -> list[str]:
    """Re-attach children after later mutations (e.g. Component conversion)."""
    key = (part_key or "").strip()
    if key.upper().startswith("PN "):
        key = key[3:].strip()
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    root = next((it for it in items if _is_assembly_type(it)), None)
    if root is None and key:
        root = pick_weld_target_item(items, part_key=key)
    if not root or not root.get("ID"):
        return []
    tid = str(root["ID"])
    linked = _attach_children(
        items,
        assembly_id=tid,
        assembly_name=key or _desc_token(str(root.get("Description") or "")) or tid[:8],
        assembly_qty=int(root.get("Quantity") or root.get("Qty") or 1),
    )
    if not linked:
        return []
    detail["ItemList"] = items
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Re-linking assembly children failed ({save.status_code})"]
    return [f"Re-linked {linked} child item(s) under Assembly"]
