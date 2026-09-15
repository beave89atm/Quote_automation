"""Kyle-locked Job 92 / 1001898-1 child-PDF classify and sizes.

LOM nouns are not category truth (PEDESTAL TUBE is rolled plate; two
plates are outsource rings). Do not invent Component dollars.
"""

from __future__ import annotations

import re
from typing import Any

# Cad Image Files (child-PDF flats, not page-outline).
# Linear Long. Component purchased/outsource — no invented UnitCost.
LOCKED_CATEGORY: dict[str, str] = {
    "14501-1": "Cad",
    "1001880-2": "Cad",
    "9905-1": "Cad",
    "1005940-1": "Cad",
    "29860-3": "Linear",
    "29860-4": "Linear",
    "10081-2": "Linear",
    "33637-1": "Linear",
    "14500-1": "Component",
    "1005966-1": "Component",
    "50137-5": "Component",
    "50115-7": "Component",
    "50030-5": "Component",
    "8166-1": "Component",
    "50006-5": "Component",
    "50122-1": "Component",
    "50029-7": "Component",
}

LOCKED_CAD: dict[str, dict[str, Any]] = {
    "14501-1": {
        "thickness": 0.1875,
        "grade": "A36",
        "noun": "Ø21.875",
    },
    "1001880-2": {
        "thickness": 0.25,
        "grade": "A572",
        "width_in": 69.875,
        "length_in": 48.75,
        "noun": "ROLLED",
    },
    "9905-1": {
        "thickness": 0.1875,
        "grade": "A572",
        "width_in": 5.0,
        "length_in": 3.0,
    },
    "1005940-1": {
        "thickness": 0.5,
        "grade": "100K Domex",
        "width_in": 12.0,
        "length_in": 2.75,
    },
}

LOCKED_LINEAR: dict[str, dict[str, Any]] = {
    "29860-3": {"sku": "L2X2X3/8-A36", "length_in": 27.75},
    "29860-4": {"sku": "L2X2X3/8-A36", "length_in": 27.75},
    "10081-2": {"sku": "P5-40-A36", "length_in": 20.25, "grade_note": "A53F vs A36"},
    "33637-1": {"sku": "P1 1/4-40-A36", "length_in": 24.8125},
}

LOCKED_COMPONENT_NOUN: dict[str, str] = {
    "14500-1": "1.25 A572 RING Ø23.5/Ø12 OUTSOURCE",
    "1005966-1": "1 A572 26.375 SQ OUTSOURCE",
}

_PN_TOKEN = re.compile(r"\b(\d{4,}(?:-\d+[A-Za-z]?)?)\b", re.IGNORECASE)


def _norm_pn(value: str | None) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", str(value or "")).upper()


def locked_part_no(text: str | None) -> str | None:
    """Return the locked 1001898-1 PN mentioned in text, if any."""
    compact_map = {_norm_pn(pn): pn for pn in LOCKED_CATEGORY}
    for m in _PN_TOKEN.finditer(str(text or "")):
        hit = compact_map.get(_norm_pn(m.group(1)))
        if hit:
            return hit
    return None


def locked_category(part_no: str | None = None, *, text: str | None = None) -> str | None:
    pn = str(part_no or "").strip()
    if pn:
        if pn in LOCKED_CATEGORY:
            return LOCKED_CATEGORY[pn]
        compact = _norm_pn(pn)
        for key, cat in LOCKED_CATEGORY.items():
            if _norm_pn(key) == compact:
                return cat
    found = locked_part_no(text)
    if found:
        return LOCKED_CATEGORY[found]
    return None


def locked_linear_bind(part_no: str | None = None, *, text: str | None = None) -> dict[str, Any] | None:
    pn = locked_part_no(part_no or text) or str(part_no or "").strip()
    return LOCKED_LINEAR.get(pn)


def locked_cad_spec(part_no: str | None = None, *, text: str | None = None) -> dict[str, Any] | None:
    pn = locked_part_no(part_no or text) or str(part_no or "").strip()
    return LOCKED_CAD.get(pn)


def locked_component_noun(part_no: str | None, fallback: str = "") -> str:
    pn = locked_part_no(part_no) or str(part_no or "").strip()
    return LOCKED_COMPONENT_NOUN.get(pn) or fallback
