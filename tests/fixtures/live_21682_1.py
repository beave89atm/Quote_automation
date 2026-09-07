"""Spent 21682-1 KNUCKLE PLATE, LB INSIDE — plate_sku_missing.

Minted 9be15b62-a824-442c-b911-50ca1016cc5e Time Waco on PR 18
2026-09-07. Leave it. Do not PATCH. Do not remint.

What worked: in-page mint, Time Waco org bind, Image Files upload,
L×W 15×14.5 UPW OP=59 Wt=30.885, AddNewPDFFeature Hole +
PDFInternal InternalData true.

Fail-close: ProductID null. Tenant POST /Product/ReadData_PlateConfig
returned Total=3 only (PL3-A572 thk=3; PL0.125-Tread). No
PL050-100K / 0.5 Domex row. Correctly did not invent GUID or bind
wrong SKU. OnAddPDFClick skipped.

Gold 1001898-1 Cad 14501-1 has ProductName PL7 Ga-A36 and ProductID
present — A36 gauge plates exist in tenant. Named reason is
plate_sku_missing (not silent ProductID null).
"""

from __future__ import annotations

from typing import Any

from secturafab.plate_ops import PLATE_SKU_MISSING

SPENT_QUOTE_ID = "9be15b62-a824-442c-b911-50ca1016cc5e"
SPENT_QUOTE_NUMBER = "21682-1"
HEADER_TITLE = "KNUCKLE PLATE, LB INSIDE"
ORG = "Time Waco"

LENGTH_IN = 15.0
WIDTH_IN = 14.5
OUTSIDE_PERIMETER = 59
WEIGHT = 30.885
DRAWING_MATERIAL = "DOMEX/WELDOX"
DRAWING_THICKNESS = 0.5

PLATE_CONFIG_TOTAL = 3
PLATE_CONFIG_ROWS: list[dict[str, Any]] = [
    {
        "ID": "pl3-a572",
        "ProductName": "PL3-A572",
        "MaterialGrade": "A572",
        "Thickness": 3,
        "Active": True,
    },
    {
        "ID": "pl0125-tread",
        "ProductName": "PL0.125-Tread",
        "MaterialGrade": "Tread",
        "Thickness": 0.125,
        "Active": True,
    },
    {
        "ID": "pl-other",
        "ProductName": "PL-OTHER",
        "MaterialGrade": "A36",
        "Thickness": 1.0,
        "Active": True,
    },
]

FILELIST_BAG: dict[str, Any] = {
    "Machine": "Laser - Bay1",
    "ProductID": None,
    "Qty": 1,
    "Weight": WEIGHT,
    "Weight_UseLocal": True,
    "OutsidePerimeter": OUTSIDE_PERIMETER,
    "OutsidePerimeter_UseLocal": True,
    "Material": DRAWING_MATERIAL,
    "Thickness": DRAWING_THICKNESS,
    "Length": LENGTH_IN,
    "Width": WIDTH_IN,
}


def plate_config_miss_payload() -> dict[str, Any]:
    """Live filtered ReadData_PlateConfig — Total=3, no 0.5 Domex row."""
    return {"Data": list(PLATE_CONFIG_ROWS), "Total": PLATE_CONFIG_TOTAL}


def leftover_plate_sku_missing_dump() -> dict[str, Any]:
    """Leftover: L×W/hole/InternalData ok; ProductID null; OnAddPDFClick skipped."""
    return {
        "quote_id": SPENT_QUOTE_ID,
        "quote_number": SPENT_QUOTE_NUMBER,
        "readonly": True,
        "finish_posted": False,
        "finish_skipped": True,
        "skip_reason": PLATE_SKU_MISSING,
        "filelist_bag": dict(FILELIST_BAG),
        "GetPDFData": {
            "is_xhr": False,
            "omits": ("CuttingLength", "NumberOfContours", "NumberOfPierces"),
        },
        "plate_config": {
            "path": "/Product/ReadData_PlateConfig",
            "total": PLATE_CONFIG_TOTAL,
            "rows": list(PLATE_CONFIG_ROWS),
            "has_pl050_100k": False,
            "invented_guid": False,
            "wrong_sku_bound": False,
        },
        "live_21682_1": {
            "files_kendo": True,
            "grid_pdf_n": 1,
            "length": LENGTH_IN,
            "width": WIDTH_IN,
            "outside_perimeter": OUTSIDE_PERIMETER,
            "weight": WEIGHT,
            "hole": True,
            "pdfinternal": True,
            "internaldata": True,
            "productid": None,
            "plate_config_total": PLATE_CONFIG_TOTAL,
            "skip_reason": PLATE_SKU_MISSING,
            "invented_guid": False,
            "onaddpdfclick": False,
        },
    }
