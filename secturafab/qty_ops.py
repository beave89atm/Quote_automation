"""Apply PDF BOM quantities onto SecturaFAB quote lines.

quickAddCAD often imports one solid per unique PN at Qty=1 even when the
drawing BOM calls for 2+. Lesson 02 / shop: child Qty and AssemblyQty must
match the BOM pieces-per-assembly.
"""

from __future__ import annotations

import re
from typing import Any

from .client import SecturaFabClient
from .weld_ops import _desc_token, pick_weld_target_item

_ASSEMBLY_TYPE = 300


def normalize_part_key(value: str | None) -> str:
    """Strip dashes/spaces so ``7300056-7`` matches ``73000567``."""
    return re.sub(r"[^0-9A-Za-z]", "", str(value or "")).upper()


def extract_bom_rows(takeoff: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Pull BOM row dicts from takeoff (handles nested weight_calc.bom)."""
    takeoff = takeoff or {}
    bom = ((takeoff.get("fitup_drivers") or {}).get("weight_calc") or {}).get("bom")
    if isinstance(bom, dict):
        rows = bom.get("rows") or bom.get("bom_rows") or []
        if isinstance(rows, list) and rows:
            return [r for r in rows if isinstance(r, dict)]
    if isinstance(bom, list):
        return [r for r in bom if isinstance(r, dict)]
    rows = (takeoff.get("pdf_bom") or {}).get("bom_rows") or []
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    return []


def bom_qty_map(bom_rows: list[dict[str, Any]] | None) -> dict[str, int]:
    """Map normalized PN → quantity (sum if duplicate rows)."""
    out: dict[str, int] = {}
    for row in bom_rows or []:
        key = normalize_part_key(row.get("part_no") or row.get("part_number") or "")
        if not key:
            continue
        try:
            qty = int(float(row.get("qty") or row.get("quantity") or 1))
        except (TypeError, ValueError):
            qty = 1
        qty = max(1, qty)
        out[key] = out.get(key, 0) + qty
    return out


def bom_qty_mismatches(
    detail: dict[str, Any],
    bom_rows: list[dict[str, Any]] | None,
    *,
    part_key: str | None = None,
) -> list[str]:
    """Return PN tokens whose Quantity does not match BOM × assembly qty."""
    qty_by_pn = bom_qty_map(bom_rows)
    if not qty_by_pn:
        return []
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
    root_id = str(root.get("ID")) if root and root.get("ID") else None
    root_qty = max(1, int((root or {}).get("Quantity") or (root or {}).get("Qty") or 1))
    bad: list[str] = []
    for it in items:
        if root_id and it.get("ID") == root_id:
            continue
        token = _desc_token(str(it.get("Description") or ""))
        key = normalize_part_key(token)
        if not key or key not in qty_by_pn:
            continue
        want = qty_by_pn[key] * root_qty
        have = int(it.get("Quantity") or it.get("Qty") or 1)
        if have != want:
            bad.append(token)
    return bad


def apply_bom_quantities(
    client: SecturaFabClient,
    quote_id: str,
    *,
    bom_rows: list[dict[str, Any]] | None,
    part_key: str | None = None,
) -> list[str]:
    """
    Set each child line's Quantity / AssemblyQty from the PDF BOM.

    Assembly root qty stays as-is (usually 1). Child Quantity = BOM qty × root qty;
    AssemblyQty = pieces per one assembly (BOM qty).
    """
    qty_by_pn = bom_qty_map(bom_rows)
    if not qty_by_pn:
        return ["No BOM quantities to apply"]

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    if not items:
        return ["No items — skipped BOM quantities"]

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
    root_id = str(root.get("ID")) if root and root.get("ID") else None
    root_qty = max(1, int((root or {}).get("Quantity") or (root or {}).get("Qty") or 1))

    updated: list[str] = []
    for it in items:
        if root_id and it.get("ID") == root_id:
            continue
        token = _desc_token(str(it.get("Description") or ""))
        key = normalize_part_key(token)
        if not key or key not in qty_by_pn:
            continue
        per = qty_by_pn[key]
        total = per * root_qty
        prev_q = int(it.get("Quantity") or it.get("Qty") or 1)
        prev_a = int(it.get("AssemblyQty") or 0)
        if prev_q == total and prev_a == per:
            continue
        it["Quantity"] = total
        it["Qty"] = total
        it["AssemblyQty"] = per
        it["isAssemblyItem"] = True
        if root_id:
            it["AssemblyID"] = root_id
            it["AssemblyLevel"] = 2
            it["AssemblyName"] = (
                part_key
                or _desc_token(str((root or {}).get("Description") or ""))
                or None
            )
        updated.append(f"{token}→{total} (AsmQty {per})")

    if not updated:
        return ["BOM quantities already matched quote lines"]

    detail["ItemList"] = items
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Saving BOM quantities failed ({save.status_code})"]
    return [f"Applied BOM quantities on {len(updated)} item(s): " + ", ".join(updated)]
