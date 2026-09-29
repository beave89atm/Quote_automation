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
from .weld_ops import _desc_token, is_assembly_item, pick_weld_target_item

_ASSEMBLY_TYPE = 300


def _is_assembly_type(item: dict[str, Any]) -> bool:
    return is_assembly_item(item)


def needs_assembly_structure(
    item_list: list[dict[str, Any]] | None,
    bom_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """
    True when a STEP quote should use lesson-02 Assembly structure.

    Single-solid plate STEPs (one ItemList line, no multi-row BOM) stay as Part
    so Profile can attach. Multi-body imports or multi-row BOMs need Assembly.
    """
    items = list(item_list or [])
    if len(items) > 1:
        return True
    bom_with_qty = 0
    for row in bom_rows or []:
        try:
            qty = float(row.get("qty") or row.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0
        if qty > 0:
            bom_with_qty += 1
            if bom_with_qty > 1:
                return True
    return False


def _attach_children(
    items: list[dict[str, Any]],
    *,
    assembly_id: str,
    assembly_name: str,
    assembly_qty: int,
) -> int:
    """Set AssemblyID / Level / Name / Qty on every non-root line. Returns count."""
    root_qty = max(1, int(assembly_qty or 1))
    assembly_ids = {
        str(it.get("ID") or "")
        for it in items
        if is_assembly_item(it) and it.get("ID")
    }
    linked = 0
    for it in items:
        if it.get("ID") == assembly_id:
            it["AssemblyID"] = None
            it["AssemblyLevel"] = 1
            it["AssemblyName"] = None
            it["AssemblyQty"] = 0
            it["isAssemblyItem"] = False
            continue
        existing_parent = str(it.get("AssemblyID") or "")
        if (
            existing_parent
            and existing_parent in assembly_ids
            and existing_parent != assembly_id
        ):
            # Nested weldment already owns this kid — do not flatten to root.
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
    description: str | None = None,
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
    # Prefer an existing Assembly line (may already have the drawing title as Description).
    for it in items:
        if _is_assembly_type(it):
            target = it
            break
    if target is None:
        for it in items:
            if _desc_token(str(it.get("Description") or "")) == key:
                target = it
                break
    if target is None:
        target = pick_weld_target_item(items, part_key=key)
    if not target or not target.get("ID"):
        return [f"Could not find root item for assembly PN {key}"]

    tid = str(target["ID"])
    prior_desc = str(target.get("Description") or "").strip()

    # Rewrite root to match Kyle's assembly line — ``{PN} - {weldment title}``.
    from secturafab.item_desc import format_assembly_description, is_bare_part_number

    target["ProductType"] = _ASSEMBLY_TYPE
    wanted = (description or "").strip()
    if wanted and not is_bare_part_number(wanted, key):
        target["Description"] = wanted[:500]
    elif prior_desc and prior_desc != key and not is_bare_part_number(prior_desc, key):
        target["Description"] = format_assembly_description(key, prior_desc)[:500]
    else:
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
    from .browser_session import effective_website_cookie
    from .website import SecturaFabWebsiteAuthError

    cookie = effective_website_cookie(getattr(client, "config", None))
    if cookie and hasattr(client, "copy_move_item_to_assembly"):
        from .website import copy_move_from_page_fn

        moved = 0
        assembly_ids = {
            str(it.get("ID") or "")
            for it in items
            if is_assembly_item(it) and it.get("ID")
        }
        for it in items:
            cid = str(it.get("ID") or "")
            if not cid or cid == tid:
                continue
            parent = str(it.get("AssemblyID") or "")
            if parent and parent in assembly_ids and parent != tid:
                # Nested weldment already owns this kid — do not flatten.
                continue
            try:
                posted = client.copy_move_item_to_assembly(
                    quote_id=quote_id,
                    item_id=cid,
                    assembly_id=tid,
                    mode="Move",
                )
            except SecturaFabWebsiteAuthError as exc:
                return [
                    f"WARNING: Copy/Move into Assembly fail-closed ({exc})"
                ]
            except Exception as exc:  # noqa: BLE001
                return [f"WARNING: Copy/Move into Assembly failed ({exc})"]
            skipped = isinstance(posted, dict) and (
                posted.get("via") == "skipped" or posted.get("ok") is False
            )
            if skipped and not copy_move_from_page_fn(posted):
                return [
                    "WARNING: Copy/Move into Assembly fail-closed "
                    "(in-page page_fn required) — kids stay at quote root"
                ]
            moved += 1
        check = client.get_json(f"v1/quote/{quote_id}")
        ok = sum(
            1
            for it in (check.get("ItemList") or [])
            if it.get("ID") != tid and it.get("AssemblyID") == tid
        )
        notes = [f"Copy/Move {moved} child item(s) into Assembly"]
        if ok < moved:
            notes.append(
                f"WARNING: only {ok}/{moved} children retained AssemblyID — "
                "flat root kids fail QA"
            )
        return notes

    detail["ItemList"] = items
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        return [f"Re-linking assembly children failed ({save.status_code})"]
    return [f"Re-linked {linked} child item(s) under Assembly"]
