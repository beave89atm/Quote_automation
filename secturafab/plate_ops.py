"""Bind Cad plates to tenant plate products (``POST v1/quoteOnline/addplate``).

Kyle's UI quote (21678-1 / Q10056) stores Cad Material / Thickness /
ThicknessDisp / WeightCategory from a plate product (e.g. ``PL1/4-A36``,
``Material=A36``, ``Thickness=0.25``, ``ThicknessDisp='0.25 in'``), not from
``POST v1/quote`` or a 200 on ``UpdateItem_Part``. New Line items have no
DataPart, so UpdateItem_Part is a no-op — addplate is the write GET reads.

Image Files ProductID is the Quotes UI plate picker
(``POST /Product/ReadData_PlateConfig`` → ``#gridSelectProductPlate``).
Gold 14501-1 binds ``PL7 Ga-A36``. Live 21682-1 filtered that XHR too
tight (Total=3: PL3-A572 thk=3 + PL0.125-Tread) and missed
PL050-100K / 0.5 Domex — fail-close ``plate_sku_missing``, do not
invent a GUID or bind the wrong SKU.
"""

from __future__ import annotations

import re
from typing import Any

from quote_core.part_materials import _parse_thickness_token

from .website import EMPTY_GUID

_PLATE_PAGE = 200
PLATE_SKU_MISSING = "plate_sku_missing"
PLATE_CONFIG_PATH = "/Product/ReadData_PlateConfig"

# Quotes UI class names (gold 14501-1 is PL7 Ga-A36, not PL3/16-A36).
# USS 7 ga ≈ 0.1793 in — close enough to 3/16 (0.1875) for picker match.
_PLATE_GAUGE_IN: dict[str, float] = {
    "7": 0.1793,
    "8": 0.1644,
    "9": 0.1495,
    "10": 0.1345,
    "11": 0.1196,
    "12": 0.1046,
    "14": 0.0747,
    "16": 0.0598,
}

_PLATE_NAME_RE = re.compile(
    r"(?i)\bPL\s*"
    r"(?:"
    r"(?P<ga>\d+)\s*Ga(?:uge)?"
    r"|(?P<frac>\d+\s*/\s*\d+)"
    r"|(?P<dec>\d+\.\d+)"
    r"|(?P<hun>0\d{2,3})"
    r")?"
    r"\s*-?\s*"
    r"(?P<grade>A\s*36|A\s*572|100\s*K|DOMEX|WELDOX|TREAD|[A-Z0-9]+)?",
)

# Broad kendo read — no Thickness / Material / ProductName filter.
# Live 21682-1 Total=3 was a too-tight filter (wrong grid / thk / grade).
KENDO_PLATE_CONFIG_READ: dict[str, Any] = {
    "take": _PLATE_PAGE,
    "skip": 0,
    "page": 1,
    "pageSize": _PLATE_PAGE,
    "sort": "",
    "group": "",
    "filter": "",
}


def catalog_plate_grade(drawing: str | None) -> str:
    """Map a drawing grade to a ``v1/material`` / plate ``MaterialGrade``."""
    compact = (
        str(drawing or "")
        .upper()
        .replace("GRADE", "G")
        .replace(" ", "")
        .replace("-", "")
    )
    if "TREAD" in compact:
        return "Tread"
    if "100K" in compact:
        return "100k"
    if "DOMEX" in compact or "WELDOX" in compact:
        return "100k"
    if "A572" in compact:
        return "A572"
    if "A36" in compact:
        return "A36"
    if "A656" in compact:
        return "A656 GR 80"
    text = str(drawing or "").strip()
    return text.split()[0] if text else "A36"


def _grades_equivalent(left: str | None, right: str | None) -> bool:
    a = catalog_plate_grade(left).casefold()
    b = catalog_plate_grade(right).casefold()
    if not a or not b:
        return False
    if a == b:
        return True
    aliases = {"100k", "domex", "weldox"}
    return a in aliases and b in aliases


def _wanted_thickness(thickness: str | float | None) -> float | None:
    thk = (
        _parse_thickness_token(str(thickness or ""))
        if thickness not in (None, "")
        else None
    )
    if isinstance(thickness, (int, float)) and float(thickness) > 0:
        thk = float(thickness)
    if not thk or thk <= 0:
        return None
    return thk


def parse_plate_product_name(name: str | None) -> tuple[float | None, str | None]:
    """Thickness + grade from Quotes UI names (PL7 Ga-A36 / PL1/4-A36 / PL050-100K)."""
    text = str(name or "").strip()
    if not text:
        return None, None
    match = _PLATE_NAME_RE.search(text)
    if not match:
        return None, None
    thk: float | None = None
    if match.group("ga"):
        thk = _PLATE_GAUGE_IN.get(str(int(match.group("ga"))))
    elif match.group("frac"):
        thk = _parse_thickness_token(match.group("frac"))
    elif match.group("dec"):
        thk = _parse_thickness_token(match.group("dec"))
    elif match.group("hun"):
        raw = match.group("hun")
        try:
            thk = int(raw) / (100.0 if len(raw) <= 3 else 1000.0)
        except (TypeError, ValueError):
            thk = None
        if thk is not None and thk >= 10:
            thk = None
    grade = match.group("grade")
    if grade:
        grade = catalog_plate_grade(grade)
    return thk, grade


def plate_sku_candidates(
    *,
    thickness: str | float | None,
    material: str | None,
) -> list[str]:
    """Names the Quotes UI picker can select (gold PL7 Ga-A36 / PL1/4-A36)."""
    thk = _wanted_thickness(thickness)
    grade = catalog_plate_grade(material)
    if not thk or not grade:
        return []
    grade_u = "100K" if grade.casefold() == "100k" else grade
    out: list[str] = []

    def _add(name: str) -> None:
        if name and name not in out:
            out.append(name)

    for ga, inches in _PLATE_GAUGE_IN.items():
        if abs(inches - thk) <= 0.02:
            _add(f"PL{ga} Ga-{grade_u}")
            _add(f"PL{ga}Ga-{grade_u}")
    frac_map = (
        (0.125, "1/8"),
        (0.1875, "3/16"),
        (0.25, "1/4"),
        (0.3125, "5/16"),
        (0.375, "3/8"),
        (0.5, "1/2"),
        (0.625, "5/8"),
        (0.75, "3/4"),
    )
    for inches, label in frac_map:
        if abs(inches - thk) <= 0.02:
            _add(f"PL{label}-{grade_u}")
    hun = int(round(thk * 100))
    if 1 <= hun <= 99:
        _add(f"PL{hun:03d}-{grade_u}")
    return out


def plate_config_rows(payload: Any) -> list[dict[str, Any]]:
    """Rows from ``POST /Product/ReadData_PlateConfig`` (Data / List / Results)."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return []
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for key in ("Data", "List", "Results", "ItemList"):
        rows = payload.get(key)
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            marker = id(row)
            if marker in seen:
                continue
            seen.add(marker)
            out.append(row)
    return out


def plate_config_total(payload: Any) -> int:
    if isinstance(payload, dict):
        try:
            return int(payload.get("Total") or 0)
        except (TypeError, ValueError):
            pass
    return len(plate_config_rows(payload))


def _catalog_key(row: dict[str, Any]) -> str:
    pid = str(row.get("ID") or row.get("ProductID") or "").strip().casefold()
    if pid:
        return f"id:{pid}"
    name = str(row.get("ProductName") or row.get("SKU") or "").strip().casefold()
    return f"name:{name}" if name else ""


def merge_plate_catalogs(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for row in group or []:
            if not isinstance(row, dict):
                continue
            key = _catalog_key(row)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            out.append(row)
    return out


def fetch_plate_config_catalog(client: Any) -> list[dict[str, Any]]:
    """Quotes UI picker catalog — unfiltered ``ReadData_PlateConfig`` pages."""
    reader = getattr(client, "read_data_plate_config", None)
    if not callable(reader):
        return []
    products: list[dict[str, Any]] = []
    try:
        page = 1
        while page <= 20:
            payload = reader(page=page, page_size=_PLATE_PAGE)
            rows = plate_config_rows(payload)
            products.extend(rows)
            total = plate_config_total(payload)
            if not rows:
                break
            if total and len(products) >= total:
                break
            if len(rows) < _PLATE_PAGE:
                break
            page += 1
    except Exception:  # noqa: BLE001
        return products
    return products


def fetch_plate_api_catalog(client: Any) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    try:
        page = 1
        while page <= 20:
            data = client.get_json(
                f"v1/product/plate?pageNumber={page}&pageSize={_PLATE_PAGE}"
            )
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


def fetch_plate_catalog(client: Any) -> list[dict[str, Any]]:
    """Tenant plate SKUs: Quotes UI PlateConfig first, then ``v1/product/plate``."""
    config_rows = fetch_plate_config_catalog(client)
    api_rows = fetch_plate_api_catalog(client)
    return merge_plate_catalogs(config_rows, api_rows)


def match_plate_product(
    catalog: list[dict[str, Any]],
    *,
    thickness: str | float | None,
    material: str | None,
) -> dict[str, Any] | None:
    """Closest active plate SKU (PL7 Ga-A36 / PL1/4-A36 class).

    Match MaterialGrade **or** ProductName grade tokens. 7 Ga matches 3/16.
    Do not invent a GUID. Do not bind Tread / 3 in plate to 1/2 Domex.
    """
    thk = _wanted_thickness(thickness)
    if not thk or thk <= 0:
        return None
    want = catalog_plate_grade(material)
    want_l = want.casefold()
    if want_l == "tread":
        return None
    scored: list[tuple[float, dict[str, Any]]] = []
    for product in catalog or []:
        if not isinstance(product, dict) or product.get("Active") is False:
            continue
        name = str(product.get("ProductName") or product.get("SKU") or "")
        name_thk, name_grade = parse_plate_product_name(name)
        grade = str(product.get("MaterialGrade") or product.get("Material") or "").strip()
        if not grade and name_grade:
            grade = name_grade
        if not _grades_equivalent(grade, want) and not _grades_equivalent(
            name_grade, want
        ):
            continue
        try:
            pthk = float(product.get("Thickness") or 0)
        except (TypeError, ValueError):
            pthk = 0.0
        if pthk <= 0 and name_thk:
            pthk = name_thk
        if pthk <= 0:
            continue
        if pthk > 2.0:
            continue
        delta = abs(pthk - thk)
        if name_thk:
            delta = min(delta, abs(name_thk - thk))
        if delta > 0.02:
            continue
        bonus = 1.0 if name.upper().startswith("PL") else 0.0
        if "GA" in name.upper():
            bonus += 0.5
        scored.append((delta - bonus * 0.001, product))
    if not scored:
        return None
    scored.sort(key=lambda row: row[0])
    return scored[0][1]


def plate_sku_missing_after_lookup(
    catalog: list[dict[str, Any]] | None,
    *,
    thickness: str | float | None = None,
    material: str | None = None,
    stamp_rows: list[dict[str, Any]] | None = None,
) -> bool:
    """True when a real catalog was read and no tenant SKU matches.

    Empty catalog (cookie/API miss, MagicMock) is not this gate.
    Live 21682-1 Total=3 (PL3-A572 / PL0.125-Tread) vs 0.5 Domex.
    """
    if not catalog:
        return False
    rows = [r for r in (stamp_rows or []) if isinstance(r, dict)]
    if rows:
        for row in rows:
            hit = match_plate_product(
                catalog,
                thickness=row.get("Thickness") if row.get("Thickness") not in (None, "") else thickness,
                material=row.get("Material") or material,
            )
            if hit is None:
                return True
        return False
    if thickness in (None, "") and not material:
        return False
    return match_plate_product(catalog, thickness=thickness, material=material) is None


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
    params = {
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
    }
    # QuoteAPI_AddItem_Plate is the New Line Item write. quoteOnline/addplate
    # is the overlay that fills Material/Thickness without calculators.
    resp = None
    for path in ("v1/quote/addplate", "v1/quoteOnline/addplate"):
        resp = client.request("POST", path, params=params)
        try:
            status = int(getattr(resp, "status_code", 400) or 400)
        except (TypeError, ValueError):
            status = 400
        if status < 400:
            return True
    return False
