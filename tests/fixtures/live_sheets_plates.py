"""Live Products → Sheets & Plates catalog (GET v1/product/plate).

Captured 2026-09-07. TotalCount=1341 unique names. Includes
PL7 Ga-A36, PL1/4-A36, PL3/4-A36. No Domex / PL050.

Quote-time POST /Product/ReadData_PlateConfig Total=3 is the
wrong source. Do not invent ProductIDs — IDs below are tenant
rows from that GET.
"""

from __future__ import annotations

from typing import Any

SHEETS_PLATES_PATH = "v1/product/plate"
SHEETS_PLATES_UNIQUE_NAMES = 1341

# Tenant ProductIDs from GET v1/product/plate (do not invent).
PL7_GA_A36_ID = "08de955f-2f89-483c-8ff6-aa7f7ec5da32"
PL14_A36_ID = "f64de87d-bce0-4461-ad15-b0c130425715"
PL34_A36_ID = "e98b940b-8bc1-49aa-8b99-a48a7e86f8c5"
PL12_A36_ID = "265d41e9-68c9-4992-95e6-24c91634bc3c"

PL7_GA_A36: dict[str, Any] = {
    "ID": PL7_GA_A36_ID,
    "ProductName": "PL7 Ga-A36",
    "MaterialGrade": "A36",
    "Thickness": 0.1874,
    "Active": True,
}

PL14_A36: dict[str, Any] = {
    "ID": PL14_A36_ID,
    "ProductName": "PL1/4-A36",
    "MaterialGrade": "A36",
    "Thickness": 0.25,
    "Active": True,
}

PL34_A36: dict[str, Any] = {
    "ID": PL34_A36_ID,
    "ProductName": "PL3/4-A36",
    "MaterialGrade": "A36",
    "Thickness": 0.75,
    "Active": True,
}

PL12_A36: dict[str, Any] = {
    "ID": PL12_A36_ID,
    "ProductName": "PL1/2-A36",
    "MaterialGrade": "A36",
    "Thickness": 0.5,
    "Active": True,
}


def sheets_plates_catalog_rows() -> list[dict[str, Any]]:
    """Stand-in for the 1341-name Sheets & Plates list (no Domex)."""
    return [dict(PL7_GA_A36), dict(PL14_A36), dict(PL34_A36), dict(PL12_A36)]


def sheets_plates_page_payload(
    rows: list[dict[str, Any]] | None = None,
    *,
    total_count: int = SHEETS_PLATES_UNIQUE_NAMES,
) -> dict[str, Any]:
    data = list(rows) if rows is not None else sheets_plates_catalog_rows()
    return {
        "CurrentPage": 1,
        "PageSize": 200,
        "TotalPages": 7,
        "TotalCount": total_count,
        "HasNext": False,
        "HasPrevious": False,
        "Results": data,
    }
