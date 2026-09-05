"""Bind Linear rows to a tenant ProductID (Long / addLinear) on the API path."""

from __future__ import annotations

from typing import Any

from secturafab.item_desc import format_linear_description, item_length_in, normalize_part_token
from secturafab.qty_ops import normalize_part_key
from secturafab.website import linear_website_product_type, pick_closest_linear_product
from secturafab.weld_ops import _desc_token

_LINEAR_TYPE = 10
_ASSEMBLY_TYPE = 300
_LINEAR_TYPE_ENUM = {
    "config",
    "bar",
    "pipe",
    "tube",
    "structural",
    "plate",
    "coil",
    "part",
    "component",
    "assembly",
    "service",
    "software",
    "unknown",
}


def _linear_product_type_enum(product: dict[str, Any]) -> str:
    for raw in (
        product.get("ProductSubType"),
        product.get("Category"),
        product.get("ProductTypeName"),
        product.get("ProductCode"),
        product.get("ShapeName"),
    ):
        text = str(raw or "").strip().lower()
        if text in _LINEAR_TYPE_ENUM:
            return text
        if any(tok in text for tok in ("angle", "beam", "channel")):
            return "structural"
        if "pipe" in text:
            return "pipe"
        if "tube" in text or "hss" in text:
            return "tube"
        if "bar" in text:
            return "bar"
    return "tube"


def _dim(product: dict[str, Any], n: int) -> float:
    try:
        return float(product.get(f"Dim{n}") or 0)
    except (TypeError, ValueError):
        return 0.0


def update_linear_via_api(
    client: Any,
    quote_id: str,
    item_id: str,
    product: dict[str, Any],
    *,
    length_in: float,
    qty: int = 1,
    name: str = "",
    machine: str = "Saw",
) -> bool:
    """POST ``v1/quoteOnline/addLinear`` (API). Caller must GET-verify Machine/Length.

    Website Long (``/Quote/AddItem_Linear``) 302s without a cookie. This is the
    write Q10056 GET reads: Machine=Saw, Length=cut, Material=catalog grade.
    """
    if not item_id or not product.get("ID") or not length_in or length_in <= 0:
        return False
    # "part" is the Long / New Line Item enum that GET-reads as ProductType 10.
    # Catalog enums (structural/pipe/tube) create PT 40/20/30 and fail QA.
    ptype = "part"
    subtype = str(product.get("ProductSubType") or _linear_product_type_enum(product))
    try:
        wl = float(product.get("WeightLength") or 0)
    except (TypeError, ValueError):
        wl = 0.0
    params = {
        "ID": quote_id,
        "ItemID": item_id,
        "productID": product["ID"],
        "productType": ptype,
        "productSubType": subtype,
        "material": product.get("MaterialGrade") or "A36",
        "location": "",
        "dim1": _dim(product, 1),
        "dim1_Unit": product.get("Dim1_Unit") or "inch",
        "dim2": _dim(product, 2),
        "dim2_Unit": product.get("Dim2_Unit") or "inch",
        "dim3": _dim(product, 3),
        "dim3_Unit": product.get("Dim3_Unit") or "inch",
        "dim4": _dim(product, 4),
        "dim4_Unit": product.get("Dim4_Unit") or "inch",
        "weightLength": wl,
        "weightLength_Units": product.get("WeightLength_Unit") or "pound/foot",
        "materialCost": 0,
        "materialCost_Units": "pound",
        "memo": "",
        "name": (name or "")[:80],
        "revisionNumber": "",
        "machine": machine or "Saw",
        "length": float(length_in),
        "length_unit": "inch",
        "qty": max(1, int(qty or 1)),
        "fixedPrice": 0,
        "productionReady": False,
        "customerMaterial": False,
        "outsource": False,
    }
    # QuoteAPI_AddItem_Linear is the Long / New Line Item write.
    for path in ("v1/quote/addLinear", "v1/quoteOnline/addLinear"):
        resp = client.request("POST", path, params=params)
        try:
            status = int(getattr(resp, "status_code", 400) or 400)
        except (TypeError, ValueError):
            status = 400
        if status < 400:
            return True
    return False


def fetch_linear_product(client: Any, product_id: str | None) -> dict[str, Any] | None:
    """``GET v1/product/linear/{id}`` when the paged catalog missed a bound ProductID."""
    pid = str(product_id or "").strip()
    if not pid:
        return None
    try:
        data = client.get_json(f"v1/product/linear/{pid}")
    except Exception:  # noqa: BLE001 — live GET may 404 a retired SKU
        return None
    if isinstance(data, dict) and data.get("ID"):
        return data
    if isinstance(data, dict):
        for key in ("Result", "Product", "Data"):
            inner = data.get(key)
            if isinstance(inner, dict) and inner.get("ID"):
                return inner
    return None


def product_from_bound_item(item: dict[str, Any] | None) -> dict[str, Any] | None:
    """Minimal addLinear product from an ItemList row that already has ProductID."""
    item = item or {}
    pid = str(item.get("ProductID") or "").strip()
    if not pid:
        return None
    return {
        "ID": pid,
        "ProductName": item.get("SKU") or item.get("ProductName") or "",
        "MaterialGrade": item.get("Material") or item.get("MaterialGrade") or "A36",
        "ProductSubType": item.get("ProductSubType") or item.get("Category") or "tube",
        "Category": item.get("Category") or "Linear",
        "Dim1": item.get("Dim1") or 0,
        "Dim2": item.get("Dim2") or 0,
        "Dim3": item.get("Dim3") or 0,
        "Dim4": item.get("Dim4") or 0,
        "Dim1_Unit": item.get("Dim1_Unit") or "inch",
        "Dim2_Unit": item.get("Dim2_Unit") or "inch",
        "Dim3_Unit": item.get("Dim3_Unit") or "inch",
        "Dim4_Unit": item.get("Dim4_Unit") or "inch",
        "WeightLength": item.get("WeightLength") or 0,
        "WeightLength_Unit": item.get("WeightLength_Unit") or "pound/foot",
    }


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
    from secturafab.locked_1001898 import locked_linear_bind

    locked = locked_linear_bind(text=description)
    if locked and locked.get("sku"):
        want = str(locked["sku"]).upper()
        exact = next(
            (
                p
                for p in catalog
                if str(p.get("ProductName") or p.get("SKU") or "").upper() == want
            ),
            None,
        )
        note = None
        if locked.get("grade_note"):
            note = f"Linear catalog {locked['sku']} ({locked['grade_note']})"
        if exact:
            return str(exact.get("ID") or "") or None, str(
                exact.get("ProductName") or locked["sku"]
            ), note
        return None, str(locked["sku"]), note
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
        it["ProductType"] = linear_website_product_type(hint or raw_token, sku)
        length = item_length_in(it)
        pn = normalize_part_token(raw_token) or raw_token
        if pn:
            it["Description"] = format_linear_description(
                pn, sku=sku, length_in=length, noun=bom_desc.get(token, "")
            )
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
            from secturafab.website import linear_finish_from_page_fn

            result = client.add_item_linear(
                quote_id=quote_id,
                product_id=pid,
                qty=max(1, int(qty or 1)),
                length=length_in,
                material=material,
                machine="Saw",
                name=format_linear_description(
                    part_no, sku=sku, length_in=length_in, noun=description
                ),
                extra={"sku": sku or ""},
            )
            if linear_finish_from_page_fn(
                result if isinstance(result, dict) else None
            ):
                notes.append(
                    f"Long in-page OnAddLinearClick ProductID={pid} SKU={sku or '?'} "
                    f"{part_no} qty={qty} length={length_in}"
                )
                return notes
            notes.append(
                "WARNING: Long without page Long click / cookie HTTP "
                "AddItem_Linear fail-closed — not v1/quote (live 29340-1)"
            )
            return notes
        except SecturaFabWebsiteAuthError as exc:
            notes.append(
                f"WARNING: Long AddItem_Linear fail-closed ({exc}) — "
                "not v1/quote then cookie Long"
            )
            return notes
        except Exception as exc:  # noqa: BLE001
            notes.append(f"WARNING: addLinear failed for {part_no}: {exc}")
            return notes
    notes.append(
        f"WARNING: Linear {part_no} has no catalog ProductID — skipped Long"
    )
    return notes
