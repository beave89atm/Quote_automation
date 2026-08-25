"""Bind Linear rows to a tenant ProductID (Long / addLinear) on the API path."""

from __future__ import annotations

import uuid
from typing import Any

from secturafab.item_desc import format_linear_description, item_length_in, normalize_part_token
from secturafab.line_item_ops import apply_linear_new_line_ops
from secturafab.qty_ops import normalize_part_key
from secturafab.website import pick_closest_linear_product
from secturafab.weld_ops import _desc_token

_LINEAR_TYPE = 10
_ASSEMBLY_TYPE = 300


def fetch_linear_catalog(client: Any) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    try:
        page = 1
        while page <= 40:
            data = client.get_json(f"v1/product/linear?pageNumber={page}&pageSize=200")
            if isinstance(data, list):
                products.extend(r for r in data if isinstance(r, dict))
                break
            if not isinstance(data, dict):
                break
            batch = list(data.get("Results") or [])
            products.extend(r for r in batch if isinstance(r, dict))
            if not data.get("HasNext"):
                break
            page += 1
    except Exception:  # noqa: BLE001 — catalog is optional on a failed tenant
        return []
    return products


def match_linear_product(
    catalog: list[dict[str, Any]],
    description: str,
    *,
    material: str | None = None,
    row: dict[str, Any] | None = None,
) -> tuple[str | None, str | None, str | None]:
    product, note = pick_closest_linear_product(
        catalog, description=description, material=material, row=row
    )
    if not product:
        return None, None, note
    pid = str(product.get("ID") or "") or None
    sku = (
        str(
            product.get("ProductName")
            or product.get("SKU")
            or product.get("ProductCode")
            or ""
        ).strip()
        or None
    )
    return pid, sku, note


def _is_linear_item(item: dict[str, Any]) -> bool:
    if item.get("ProductType") in (_ASSEMBLY_TYPE, "300", "assembly"):
        return False
    cat = str(item.get("Category") or item.get("ItemType") or "").strip()
    return bool(item.get("IsLinear")) or cat == "Linear"


def bind_linear_product_ids(
    client: Any,
    quote_id: str,
    *,
    material: str | None = None,
    bom_rows: list[dict[str, Any]] | None = None,
    catalog: list[dict[str, Any]] | None = None,
) -> list[str]:
    """
    Set ProductID (not ProductName) + Saw on Linear lines.

    Works on the API quote POST. addLinear is tried only when a website
    session exists; a missing cookie still binds ProductID on the item.
    """
    products = list(catalog) if catalog is not None else fetch_linear_catalog(client)
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

    changed = 0
    notes: list[str] = []
    for it in items:
        if not _is_linear_item(it):
            continue
        raw_token = _desc_token(str(it.get("Description") or ""))
        token = normalize_part_key(raw_token)
        hint = f"{it.get('Description') or ''} {bom_desc.get(token, '')}".strip()
        pid, sku, mismatch = match_linear_product(
            products, hint or raw_token, material=material, row=it
        )
        if mismatch:
            notes.append(f"WARNING: {mismatch}")
        if pid:
            it["ProductID"] = pid
            if "ProductName" in it:
                # Bind ID, not a typed product name.
                it["ProductName"] = None
        if sku:
            it["SKU"] = sku
        it["Machine"] = "Saw"
        it["IsLinear"] = True
        it["IsPlate"] = False
        it["IsPart"] = True
        it["ProductType"] = _LINEAR_TYPE
        length = item_length_in(it)
        pn = normalize_part_token(raw_token) or raw_token
        if pn:
            it["Description"] = format_linear_description(
                pn, sku=sku, length_in=length, noun=bom_desc.get(token, "")
            )
        if apply_linear_new_line_ops(it):
            notes.append(f"New Line Item Saw + Saw Setup on {pn or raw_token}")
        changed += 1

    if changed:
        save = client.request("POST", "v1/quote", json=detail)
        if save.status_code >= 400:
            notes.append(f"Linear ProductID bind save failed ({save.status_code})")
        else:
            notes.append(
                f"Bound ProductID on {changed} Linear item(s) (Saw / Long catalog)"
            )
    elif any(_is_linear_item(it) for it in items):
        notes.append("Linear rows present but catalog returned no ProductID")
    return notes


def add_linear_item_from_bom(
    client: Any,
    quote_id: str,
    *,
    part_no: str,
    description: str,
    qty: int,
    material: str | None = None,
    length_in: float | None = None,
    catalog: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Create a Linear line without quickAddCAD (tube/angle PDF is not a plate)."""
    products = list(catalog) if catalog is not None else fetch_linear_catalog(client)
    hint = f"{part_no} {description}".strip()
    pid, sku, mismatch = match_linear_product(
        products, hint, material=material
    )
    notes: list[str] = []
    if mismatch:
        notes.append(f"WARNING: {mismatch}")
    if pid:
        try:
            from secturafab.client import SecturaFabWebsiteAuthError

            client.add_item_linear(
                quote_id=quote_id,
                product_id=pid,
                qty=max(1, int(qty or 1)),
                length=length_in,
                material=material,
                machine="Saw",
                name=format_linear_description(
                    part_no, sku=sku, length_in=length_in, noun=description
                ),
            )
            notes.append(
                f"Long addLinear ProductID={pid} SKU={sku or '?'} "
                f"{part_no} qty={qty} length={length_in}"
            )
            return notes
        except SecturaFabWebsiteAuthError:
            notes.append(
                "Long AddItem_Linear 302'd — New Line Item Saw pack on API item"
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"WARNING: addLinear failed for {part_no}: {exc}")

    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    desc = format_linear_description(
        part_no, sku=sku, length_in=length_in, noun=description
    )
    line = {
        "ID": str(uuid.uuid4()),
        "Description": desc[:500],
        "Quantity": max(1, int(qty or 1)),
        "ProductType": _LINEAR_TYPE,
        "ItemType": "Linear",
        "Category": "Linear",
        "IsLinear": True,
        "IsPlate": False,
        "IsPart": True,
        "Machine": "Saw",
        "ProductID": pid,
        "SKU": sku,
        "Length": length_in,
        "OperationCostList": [],
    }
    apply_linear_new_line_ops(line)
    detail["ItemList"] = items + [line]
    save = client.request("POST", "v1/quote", json=detail)
    if save.status_code >= 400:
        notes.append(f"Adding Linear {part_no} failed ({save.status_code})")
    else:
        notes.append(
            f"Added Linear {part_no} ProductID={pid or 'unset'} SKU={sku or '?'} qty={qty}"
        )
    return notes
