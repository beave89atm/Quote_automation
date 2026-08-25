"""Bind Cad plates to tenant plate products (``POST v1/quoteOnline/addplate``).

Kyle's UI quote (21678-1 / Q10056) stores Cad Material / Thickness /
ThicknessDisp / WeightCategory from a plate product (e.g. ``PL1/4-A36``,
``Material=A36``, ``Thickness=0.25``, ``ThicknessDisp='0.25 in'``), not from
``POST v1/quote`` or a 200 on ``UpdateItem_Part``. New Line items have no
DataPart, so UpdateItem_Part is a no-op — addplate is the write GET reads.
"""

from __future__ import annotations

from typing import Any

from quote_core.part_materials import _parse_thickness_token

from .website import EMPTY_GUID

_PLATE_PAGE = 200


def catalog_plate_grade(drawing: str | None) -> str:
    """Map a drawing grade to a ``v1/material`` / plate ``MaterialGrade``."""
    compact = (
        str(drawing or "")
        .upper()
        .replace("GRADE", "G")
        .replace(" ", "")
        .replace("-", "")
    )
    if "100K" in compact:
        return "100k"
    if "A572" in compact:
        return "A572"
    if "A36" in compact:
        return "A36"
    if "A656" in compact:
        return "A656 GR 80"
    text = str(drawing or "").strip()
    return text.split()[0] if text else "A36"


def fetch_plate_catalog(client: Any) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    try:
        page = 1
        while page <= 20:
            data = client.get_json(f"v1/product/plate?pageNumber={page}&pageSize={_PLATE_PAGE}")
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
    except Exception:  # noqa: BLE001
        return []
    return products


def match_plate_product(
    catalog: list[dict[str, Any]],
    *,
    thickness: str | float | None,
    material: str | None,
) -> dict[str, Any] | None:
    """Closest active plate SKU for a grade + thickness (PL1/4-A36 class)."""
    thk = _parse_thickness_token(str(thickness or "")) if thickness not in (None, "") else None
    if isinstance(thickness, (int, float)) and float(thickness) > 0:
        thk = float(thickness)
    if not thk or thk <= 0:
        return None
    want = catalog_plate_grade(material)
    want_l = want.casefold()
    scored: list[tuple[float, dict[str, Any]]] = []
    for product in catalog or []:
        if not isinstance(product, dict) or product.get("Active") is False:
            continue
        grade = str(product.get("MaterialGrade") or "").strip()
        if grade.casefold() != want_l:
            continue
        try:
            pthk = float(product.get("Thickness") or 0)
        except (TypeError, ValueError):
            continue
        if pthk <= 0:
            continue
        delta = abs(pthk - thk)
        if delta > 0.02:
            continue
        name = str(product.get("ProductName") or "")
        bonus = 1.0 if name.upper().startswith("PL") else 0.0
        scored.append((delta - bonus * 0.001, product))
    if not scored:
        return None
    scored.sort(key=lambda row: row[0])
    return scored[0][1]


def addplate_item(
    client: Any,
    quote_id: str,
    item_id: str,
    product: dict[str, Any],
    *,
    name: str,
    qty: int = 1,
    width_in: float | None = None,
    length_in: float | None = None,
) -> bool:
    """POST addplate. Returns True only on HTTP <400 — caller must GET-verify."""
    try:
        thk = float(product.get("Thickness") or 0)
    except (TypeError, ValueError):
        return False
    if thk <= 0:
        return False
    width = float(width_in) if width_in and width_in > 0 else 1.0
    length = float(length_in) if length_in and length_in > 0 else 1.0
    resp = client.request(
        "POST",
        "v1/quoteOnline/addplate",
        params={
            "quoteID": quote_id,
            "itemID": item_id,
            "productID": product.get("ID"),
            "productConfigID": EMPTY_GUID,
            "memo": "",
            "name": (name or "")[:80],
            "material": product.get("MaterialGrade") or "A36",
            "thickness": thk,
            "thickness_Units": product.get("Thickness_Unit") or "inch",
            "width": width,
            "width_unit": "inch",
            "length": length,
            "length_unit": "inch",
            "qty": max(1, int(qty or 1)),
            "fixedPrice": 0,
            "customerMaterial": False,
        },
    )
    try:
        status = int(getattr(resp, "status_code", 400) or 400)
    except (TypeError, ValueError):
        status = 400
    return status < 400
