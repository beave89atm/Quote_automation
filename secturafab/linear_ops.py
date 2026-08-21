"""Bind Linear stock via ProductID + ProductConfigID + SKU, then addLinear.

Never set ProductName — SecturaFAB MaterialCost for Linear only calculates
when the product IDs/SKU are bound and addLinear is called.
"""

from __future__ import annotations

from typing import Any

from .client import SecturaFabClient


def _is_linear_item(item: dict[str, Any]) -> bool:
    pt = item.get("ProductType")
    if pt in (300, "300", "assembly") or item.get("IsAssembly"):
        return False
    cat = str(item.get("Category") or item.get("ItemType") or "").strip().lower()
    return bool(item.get("IsLinear") or cat == "linear")


def _linear_bind_ids(item: dict[str, Any]) -> tuple[str, str, str] | None:
    product_id = str(item.get("ProductID") or "").strip()
    config_id = str(item.get("ProductConfigID") or "").strip()
    sku = str(item.get("SKU") or item.get("Sku") or "").strip()
    if not product_id or not config_id or not sku:
        return None
    if product_id in {"00000000-0000-0000-0000-000000000000"}:
        return None
    return product_id, config_id, sku


def bind_linear_products(client: SecturaFabClient, quote_id: str) -> list[str]:
    """
    For each Linear line: persist ProductID + ProductConfigID + SKU (not
    ProductName), then POST quoteOnline/addLinear so MaterialCost calculates.
    """
    notes: list[str] = []
    detail = client.get_json(f"v1/quote/{quote_id}")
    items = list(detail.get("ItemList") or [])
    targets = [it for it in items if _is_linear_item(it)]
    if not targets:
        return ["No Linear items to bind"]

    bound = 0
    for it in targets:
        iid = str(it.get("ID") or "")
        ids = _linear_bind_ids(it)
        label = (it.get("Description") or "")[:40]
        if not iid or not ids:
            notes.append(
                f"WARNING: Linear {(label or iid)!r} missing ProductID/"
                f"ProductConfigID/SKU — skipped addLinear (do not bind by ProductName)"
            )
            continue
        product_id, config_id, sku = ids
        # Write IDs only — never ProductName.
        it["ProductID"] = product_id
        it["ProductConfigID"] = config_id
        it["SKU"] = sku
        if "ProductName" in it:
            it.pop("ProductName", None)
        addl = client.request(
            "POST",
            "v1/quoteOnline/addLinear",
            params={
                "quoteID": quote_id,
                "itemID": iid,
                "productID": product_id,
                "productConfigID": config_id,
                "sku": sku,
            },
        )
        status = getattr(addl, "status_code", 500)
        if status >= 400:
            notes.append(
                f"WARNING: addLinear failed on {label!r} ({status})"
            )
            continue
        bound += 1

    notes.append(f"addLinear bound MaterialCost on {bound}/{len(targets)} Linear item(s)")
    return notes
